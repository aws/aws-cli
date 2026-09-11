# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging
import os
import sys

import awscrt.s3
from botocore.client import Config
from botocore.httpsession import DEFAULT_CA_BUNDLE
from s3transfer.crt import (
    BotocoreCRTCredentialsWrapper,
    BotocoreCRTRequestSerializer,
    CRTTransferManager,
    acquire_crt_s3_process_lock,
    create_s3_crt_client,
)
from s3transfer.manager import TransferManager

from awscli.compat import urlparse
from awscli.customizations.s3 import constants
from awscli.customizations.s3.transferconfig import (
    DEFAULTS,
    create_transfer_config_from_runtime_config,
)
from awscli.customizations.utils import uni_print

LOGGER = logging.getLogger(__name__)

ADAPTIVE_RETRY_MODE = 'adaptive'

WARN_IGNORED = 'warn_ignored'

EXCLUDE_FROM_AUTO = 'exclude_from_auto'

UNSUPPORTED_OPTIONS = {
    constants.CRT_TRANSFER_CLIENT: {
        'max_bandwidth': EXCLUDE_FROM_AUTO,
        'max_queue_size': WARN_IGNORED,
        'io_chunksize': WARN_IGNORED,
    },
    constants.CLASSIC_TRANSFER_CLIENT: {
        'target_bandwidth': WARN_IGNORED,
        'should_stream': WARN_IGNORED,
        'disk_throughput': WARN_IGNORED,
        'direct_io': WARN_IGNORED,
    },
}

CRT_CLIENT_KWARG_MAP = {
    'multipart_chunksize': 'part_size',
    'multipart_threshold': 'multipart_upload_threshold',
    'max_concurrent_requests': 'max_active_connections_override',
}


class ClientFactory:
    def __init__(self, session):
        self._session = session

    def create_client(self, params, is_source_client=False):
        create_client_kwargs = {'verify': params['verify_ssl']}
        if params.get('sse') == 'aws:kms':
            create_client_kwargs['config'] = Config(signature_version='s3v4')
        region = params['region']
        endpoint_url = params['endpoint_url']
        if is_source_client and params['source_region']:
            if params['paths_type'] == 's3s3':
                region = params['source_region']
                endpoint_url = None

        create_client_kwargs['region_name'] = region
        create_client_kwargs['endpoint_url'] = endpoint_url
        return self._session.create_client('s3', **create_client_kwargs)


class TransferManagerFactory:
    _MAX_IN_MEMORY_CHUNKS = 6
    _CRT_PROCESS_LOCK_NAME = 'aws-cli'

    def __init__(self, session):
        self._session = session
        self._botocore_client_factory = ClientFactory(self._session)

    def create_transfer_manager(
        self, params, runtime_config, botocore_client=None
    ):
        client_type = self._compute_transfer_client_type(
            params, runtime_config
        )
        self.warn_unsupported_settings(client_type, runtime_config)
        if client_type == constants.CRT_TRANSFER_CLIENT:
            return self._create_crt_transfer_manager(params, runtime_config)
        else:
            return self._create_classic_transfer_manager(
                params, runtime_config, botocore_client
            )

    def _compute_transfer_client_type(self, params, runtime_config):
        if params.get('paths_type') == 's3s3':
            return constants.CLASSIC_TRANSFER_CLIENT
        preferred_transfer_client = runtime_config.get(
            'preferred_transfer_client', constants.AUTO_RESOLVE_TRANSFER_CLIENT
        )
        if preferred_transfer_client == constants.AUTO_RESOLVE_TRANSFER_CLIENT:
            return self._resolve_transfer_client_type_for_system(
                params, runtime_config
            )
        return preferred_transfer_client

    def _resolve_transfer_client_type_for_system(self, params, runtime_config):
        transfer_client_type = constants.CLASSIC_TRANSFER_CLIENT
        if self._is_eligible_for_crt_client(params, runtime_config):
            is_running = self._is_crt_client_running_in_other_aws_cli_process()
            LOGGER.debug(
                'S3 CRT client running in different AWS CLI process: %s',
                is_running,
            )
            if not is_running:
                transfer_client_type = constants.CRT_TRANSFER_CLIENT
        LOGGER.debug(
            'Auto resolved s3 transfer client to: %s', transfer_client_type
        )
        return transfer_client_type

    def _is_eligible_for_crt_client(self, params, runtime_config):
        is_optimized_for_system = awscrt.s3.is_optimized_for_system()
        LOGGER.debug(
            f'S3 CRT client optimized for system: {is_optimized_for_system}'
        )
        if is_optimized_for_system:
            return True
        if not self._is_crt_auto_resolve_enabled():
            return False
        unsupported = self._get_unsupported_settings(params, runtime_config)
        if unsupported:
            LOGGER.debug(
                f'Not auto resolving to the crt s3 transfer client because '
                f'it does not support: {", ".join(unsupported)}'
            )
            self._warn_classic_only_settings(runtime_config)
            return False
        return True

    def _is_crt_auto_resolve_enabled(self):
        return (
            os.environ.get('AWS_CLI_AUTO_RESOLVE_CLIENT')
            == constants.CRT_TRANSFER_CLIENT
        )

    def _get_unsupported_settings(self, params, runtime_config):
        unsupported = self._get_classic_only_settings(runtime_config)
        if self._is_adaptive_retry_mode():
            unsupported.append(f'retry_mode = {ADAPTIVE_RETRY_MODE}')
        if self._is_non_seekable_stream_upload(params):
            unsupported.append('uploads from a non-seekable stream')
        return unsupported

    def _get_classic_only_settings(self, runtime_config):
        return self._get_unsupported_options(
            constants.CRT_TRANSFER_CLIENT,
            runtime_config,
            action=EXCLUDE_FROM_AUTO,
        )

    def _get_unsupported_options(
        self, client_type, runtime_config, action=None
    ):
        return [
            name
            for name, option_action in UNSUPPORTED_OPTIONS.get(
                client_type, {}
            ).items()
            if (action is None or option_action == action)
            and runtime_config.is_explicitly_set(name)
        ]

    def _is_adaptive_retry_mode(self):
        return (
            self._session.get_config_variable('retry_mode')
            == ADAPTIVE_RETRY_MODE
        )

    def _warn_classic_only_settings(self, runtime_config):
        classic_only = self._get_classic_only_settings(runtime_config)
        if not classic_only:
            return
        uni_print(
            f"warning: Using the '{constants.CLASSIC_TRANSFER_CLIENT}' s3 "
            f"transfer client because the "
            f"'{constants.CRT_TRANSFER_CLIENT}' s3 transfer client does not "
            f"support: {', '.join(classic_only)}. A future version of the AWS "
            f"CLI will use the '{constants.CRT_TRANSFER_CLIENT}' s3 transfer "
            f"client by default, at which point these values will be "
            f"ignored. Set the preferred_transfer_client configuration value "
            f"to '{constants.CLASSIC_TRANSFER_CLIENT}' to continue using the "
            f"'{constants.CLASSIC_TRANSFER_CLIENT}' s3 transfer client.\n",
            sys.stderr,
        )

    def warn_unsupported_settings(self, client_type, runtime_config):
        unsupported = self._get_unsupported_options(
            client_type, runtime_config
        )
        if (
            client_type == constants.CRT_TRANSFER_CLIENT
            and self._is_adaptive_retry_mode()
        ):
            unsupported.append(f'retry_mode = {ADAPTIVE_RETRY_MODE}')
        if not unsupported:
            return
        uni_print(
            f"warning: The following configuration values are not supported "
            f"by the '{client_type}' s3 transfer client and will be ignored: "
            f"{', '.join(unsupported)}.\n",
            sys.stderr,
        )

    def _is_non_seekable_stream_upload(self, params):
        return bool(
            params.get('is_stream') and params.get('paths_type') == 'locals3'
        )

    def _is_crt_client_running_in_other_aws_cli_process(self):
        # If None is returned from acquiring the CRT process lock, it
        # means the CRT S3 client is currently being used in a different
        # AWS CLI process.
        return self._acquire_crt_s3_process_lock() is None

    def _acquire_crt_s3_process_lock(self):
        return acquire_crt_s3_process_lock(self._CRT_PROCESS_LOCK_NAME)

    def _create_crt_transfer_manager(self, params, runtime_config):
        self._acquire_crt_s3_process_lock()
        return CRTTransferManager(
            self._create_crt_client(params, runtime_config),
            self._create_crt_request_serializer(params),
        )

    def _create_crt_client(self, params, runtime_config):
        create_crt_client_kwargs = {
            'region': self._resolve_region(params),
            'verify': self._resolve_verify(params),
        }
        endpoint_url = params.get('endpoint_url')
        if endpoint_url and urlparse.urlparse(endpoint_url).scheme == 'http':
            create_crt_client_kwargs['use_ssl'] = False
        target_throughput = runtime_config.get('target_bandwidth', None)
        if target_throughput:
            create_crt_client_kwargs['target_throughput'] = target_throughput
        create_crt_client_kwargs.update(
            self._resolve_crt_client_config_kwargs(runtime_config)
        )
        if params.get('sign_request', True):
            crt_credentials_provider = self._get_crt_credentials_provider()
            create_crt_client_kwargs['crt_credentials_provider'] = (
                crt_credentials_provider
            )
        fio_options = {}
        if (val := runtime_config.get('should_stream')) is not None:
            fio_options['should_stream'] = val
        if (val := runtime_config.get('disk_throughput')) is not None:
            # Convert bytes to gigabits.
            fio_options['disk_throughput_gbps'] = val * 8 / 1_000_000_000
        if (val := runtime_config.get('direct_io')) is not None:
            fio_options['direct_io'] = val
        create_crt_client_kwargs['fio_options'] = fio_options

        return create_s3_crt_client(**create_crt_client_kwargs)

    def _resolve_crt_client_config_kwargs(self, runtime_config):
        use_defaults = self._should_use_transfer_config_defaults(
            runtime_config
        )
        kwargs = {}
        for config_name, crt_name in CRT_CLIENT_KWARG_MAP.items():
            if runtime_config.is_explicitly_set(config_name):
                kwargs[crt_name] = runtime_config[config_name]
            elif use_defaults:
                kwargs[crt_name] = DEFAULTS[config_name]
        if 'part_size' not in kwargs:
            # `create_s3_crt_client` defaults this to 8MB, so `None` has to be
            # passed to opt into the CRT's dynamic part size calculation.
            kwargs['part_size'] = None
        return kwargs

    def _should_use_transfer_config_defaults(self, runtime_config):
        preferred = runtime_config.get('preferred_transfer_client')
        if preferred == constants.CRT_TRANSFER_CLIENT:
            return False
        return not awscrt.s3.is_optimized_for_system()

    def _create_crt_request_serializer(self, params):
        return BotocoreCRTRequestSerializer(
            self._session,
            {
                'region_name': self._resolve_region(params),
                'endpoint_url': params.get('endpoint_url'),
            },
        )

    def _create_classic_transfer_manager(
        self, params, runtime_config, client=None
    ):
        if client is None:
            client = self._botocore_client_factory.create_client(params)
        transfer_config = create_transfer_config_from_runtime_config(
            runtime_config
        )
        transfer_config.max_in_memory_upload_chunks = (
            self._MAX_IN_MEMORY_CHUNKS
        )
        transfer_config.max_in_memory_download_chunks = (
            self._MAX_IN_MEMORY_CHUNKS
        )
        LOGGER.debug(
            "Using a multipart threshold of %s and a part size of %s",
            transfer_config.multipart_threshold,
            transfer_config.multipart_chunksize,
        )
        return TransferManager(client, transfer_config)

    def _get_crt_credentials_provider(self):
        botocore_credentials = self._session.get_credentials()
        wrapper = BotocoreCRTCredentialsWrapper(botocore_credentials)
        return wrapper.to_crt_credentials_provider()

    def _resolve_region(self, params):
        region = params.get('region')
        if region is None:
            region = self._session.get_config_variable('region')
        return region

    def _resolve_verify(self, params):
        verify = params.get('verify_ssl')
        if verify is None:
            verify = self._session.get_config_variable('ca_bundle')
        if verify is None:
            verify = DEFAULT_CA_BUNDLE
        return verify
