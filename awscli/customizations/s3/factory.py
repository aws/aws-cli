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
from botocore.useragent import register_feature_id
from s3transfer.crt import (
    BotocoreCRTCredentialsWrapper,
    BotocoreCRTRequestSerializer,
    CRTTransferConfig,
    CRTTransferManager,
    acquire_crt_s3_process_lock,
    create_crt_client_bootstrap,
    create_s3_crt_client,
    release_crt_s3_process_lock,
)
from s3transfer.manager import TransferManager

from awscli.compat import urlparse
from awscli.customizations.s3 import constants
from awscli.customizations.s3.transferconfig import (
    DEFAULTS,
    InvalidConfigError,
    create_transfer_config_from_runtime_config,
)
from awscli.customizations.utils import uni_print

LOGGER = logging.getLogger(__name__)

ADAPTIVE_RETRY_MODE = 'adaptive'

# A max_retries of 0 configures the crt client's own retry count instead of
# disabling retries, so it cannot honor a single attempt. It also rejects a
# max_retries of 64 or more outright.
MIN_CRT_MAX_ATTEMPTS = 2
MAX_CRT_MAX_ATTEMPTS = 64

# Throughput target, in gigabits per second, for hosts the crt client has not
# been tuned for. Staying at 4 keeps it in its smallest memory pool tier.
UNTUNED_TARGET_THROUGHPUT_GBPS = 4.0

# Throughput target, in gigabits per second, to fall back to rather than
# accepting a lower recommendation from the crt.
MINIMUM_TARGET_THROUGHPUT_GBPS = 10.0

# The crt client rejects a part size over half of its memory pool while it is
# being constructed. The pool is sized from the throughput target, and neither
# the sizing nor the limit is exposed, so the only way to know a multipart
# chunksize does not fit is to build the client and see. awscrt raises a plain
# RuntimeError for this, leaving the error code as the only thing to match on.
CRT_PART_SIZE_EXCEEDS_MEMORY_LIMIT = 14371

CRT_AUTO_RESOLVE_INSTANCE_FAMILIES = frozenset(
    [
        'dl1',
        'g6e',
        'g6',
        'g5',
        'g5g',
        'g4dn',
        'inf2',
        'inf1',
        'x2iedn',
        'x2idn',
        'x2iezn',
        'x1e',
        'x1',
        'i4i',
        'i3en',
        'i3',
        'is4gen',
        'im4gn',
        'd3en',
        'd3',
        'h1',
        'c9gd',
        'c9g',
        'c8ine',
        'c8in',
        'c8ib',
        'c8id',
        'c8i-flex',
        'c8i',
        'c8gn',
        'c8gb',
        'c8gd',
        'c8g',
        'c8a',
        'c7i-flex',
        'c7i',
        'c7gn',
        'c7gd',
        'c7g',
        'c7a',
        'm8a',
        'm8g',
        'm7i-flex',
        'm7i',
        'm7a',
        'm7g',
        'r7iz',
        'r7i',
        'r7a',
        'r7g',
    ]
)

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


def _gbps_to_bytes_per_sec(gbps):
    return int(gbps * 1_000_000_000 / 8)


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
        if client_type == constants.CRT_TRANSFER_CLIENT:
            transfer_manager = self._try_create_crt_transfer_manager(
                params, runtime_config
            )
            if transfer_manager is not None:
                self._register_transfer_client_feature_id(
                    client_type, runtime_config
                )
                self.warn_unsupported_settings(client_type, runtime_config)
                return transfer_manager
            client_type = constants.CLASSIC_TRANSFER_CLIENT
        self._register_transfer_client_feature_id(client_type, runtime_config)
        self.warn_unsupported_settings(client_type, runtime_config)
        return self._create_classic_transfer_manager(
            params, runtime_config, botocore_client
        )

    def _register_transfer_client_feature_id(
        self, client_type, runtime_config
    ):
        preferred = runtime_config.get(
            'preferred_transfer_client', constants.AUTO_RESOLVE_TRANSFER_CLIENT
        )
        resolve_type = (
            'AUTO'
            if preferred == constants.AUTO_RESOLVE_TRANSFER_CLIENT
            else 'EXPLICIT'
        )
        register_feature_id(
            f'S3_TRANSFER_{client_type.upper()}_{resolve_type}'
        )

    def _try_create_crt_transfer_manager(self, params, runtime_config):
        try:
            return self._create_crt_transfer_manager(params, runtime_config)
        except RuntimeError as e:
            if str(CRT_PART_SIZE_EXCEEDS_MEMORY_LIMIT) not in str(e):
                raise
            if self._is_preferring_crt_client(runtime_config):
                raise InvalidConfigError(
                    f'The configured multipart_chunksize is too large for the '
                    f"'{constants.CRT_TRANSFER_CLIENT}' s3 transfer client. "
                    f'Lower multipart_chunksize or raise the '
                    f'memory available to the transfer client by setting the '
                    f'AWS_CRT_S3_MEMORY_LIMIT_IN_GIB environment variable.'
                ) from e
            LOGGER.debug(
                f'Not using the crt s3 transfer client because the configured '
                f'multipart_chunksize does not fit its memory pool: {e}'
            )
            release_crt_s3_process_lock()
            return None

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
        if (
            os.environ.get('AWS_CLI_AUTO_RESOLVE_CLIENT')
            == constants.CRT_TRANSFER_CLIENT
        ):
            return True
        return self._is_rolled_out_instance_family()

    def _is_rolled_out_instance_family(self):
        instance_type = awscrt.s3.get_ec2_instance_type()
        if instance_type is None:
            return False
        instance_family = instance_type.split('.')[0].lower()
        return instance_family in CRT_AUTO_RESOLVE_INSTANCE_FAMILIES

    def _get_unsupported_settings(self, params, runtime_config):
        unsupported = self._get_classic_only_settings(runtime_config)
        if self._is_adaptive_retry_mode():
            unsupported.append(f'retry_mode = {ADAPTIVE_RETRY_MODE}')
        if self._is_non_seekable_stream_upload(params):
            unsupported.append('uploads from a non-seekable stream')
        if unsupported_attempts := self._get_unsupported_max_attempts(
            runtime_config
        ):
            unsupported.append(unsupported_attempts)
        return unsupported

    def _get_unsupported_max_attempts(self, runtime_config):
        max_attempts = self._resolve_max_attempts(runtime_config)
        if max_attempts is None or (
            MIN_CRT_MAX_ATTEMPTS <= max_attempts <= MAX_CRT_MAX_ATTEMPTS
        ):
            return None
        return (
            f'max_attempts = {max_attempts} (must be between '
            f'{MIN_CRT_MAX_ATTEMPTS} and {MAX_CRT_MAX_ATTEMPTS})'
        )

    def _resolve_max_attempts(self, runtime_config):
        config_store = self._session.get_component('config_store')
        if config_store.is_explicitly_set('max_attempts') or (
            self._should_use_transfer_config_defaults(runtime_config)
        ):
            return self._session.get_config_variable('max_attempts')
        return None

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
        if client_type == constants.CRT_TRANSFER_CLIENT:
            if self._is_adaptive_retry_mode():
                unsupported.append(f'retry_mode = {ADAPTIVE_RETRY_MODE}')
            if unsupported_attempts := self._get_unsupported_max_attempts(
                runtime_config
            ):
                unsupported.append(unsupported_attempts)
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
        region = self._resolve_region(params)
        bootstrap = create_crt_client_bootstrap()
        config_kwargs = self._resolve_crt_client_config_kwargs(runtime_config)

        transfer_manager = CRTTransferManager(
            crt_client_factory=lambda client_region=None: (
                self._create_crt_client(
                    params,
                    runtime_config,
                    config_kwargs,
                    region=client_region or region,
                    bootstrap=bootstrap,
                )
            ),
            crt_request_serializer=self._create_crt_request_serializer(params),
            transfer_config=self._create_crt_transfer_config(config_kwargs),
        )
        # Clients for redirected regions are created on demand, but create the
        # one for the configured region now. Otherwise invalid client
        # configuration is not reported until a transfer is submitted, which
        # reports it once per object instead of once for the command.
        transfer_manager.get_crt_client()
        return transfer_manager

    def _create_crt_transfer_config(self, config_kwargs):
        # The crt client only applies its multipart threshold to uploads, so
        # downloads rely on the transfer config to match it. Leaving the
        # threshold unset keeps the client's own download behavior.
        return CRTTransferConfig(
            multipart_threshold=config_kwargs.get('multipart_upload_threshold')
        )

    def _create_crt_client(
        self,
        params,
        runtime_config,
        config_kwargs,
        region=None,
        bootstrap=None,
    ):
        create_crt_client_kwargs = {
            'region': region or self._resolve_region(params),
            'verify': self._resolve_verify(params),
            'bootstrap': bootstrap,
        }
        endpoint_url = params.get('endpoint_url')
        if endpoint_url and urlparse.urlparse(endpoint_url).scheme == 'http':
            create_crt_client_kwargs['use_ssl'] = False
        target_throughput = self._resolve_target_throughput(runtime_config)
        if target_throughput:
            create_crt_client_kwargs['target_throughput'] = target_throughput
        create_crt_client_kwargs.update(config_kwargs)
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
        max_attempts = self._resolve_max_attempts(runtime_config)
        if max_attempts is not None and (
            MIN_CRT_MAX_ATTEMPTS <= max_attempts <= MAX_CRT_MAX_ATTEMPTS
        ):
            kwargs['retry_options'] = {'max_retries': max_attempts - 1}
        return kwargs

    def _resolve_target_throughput(self, runtime_config):
        target_throughput = runtime_config.get('target_bandwidth')
        if target_throughput is not None:
            return target_throughput
        if self._is_preferring_crt_client(runtime_config):
            # Users who opted into the crt transfer client keep the throughput
            # they get today, even on hosts the crt recommends less for.
            recommended = awscrt.s3.get_recommended_throughput_target_gbps()
            return _gbps_to_bytes_per_sec(
                max(recommended or 0, MINIMUM_TARGET_THROUGHPUT_GBPS)
            )
        if self._is_newly_eligible_for_crt_client(runtime_config) and (
            self._is_untuned_system()
        ):
            # The crt client sizes its memory pool from the throughput target.
            # Without a recommendation it assumes 10gbps, which maps to a max
            # pool size of 2GiB. Newly-eligible hosts that auto-resolve to crt
            # may not be able to afford 2GiB, so it sets the maximum throughput
            # that maps to the smallest 256MiB tier.
            return _gbps_to_bytes_per_sec(UNTUNED_TARGET_THROUGHPUT_GBPS)
        return None

    def _is_untuned_system(self):
        # The crt client has no throughput recommendation for systems it has
        # not been tuned for.
        return awscrt.s3.get_recommended_throughput_target_gbps() is None

    def _is_preferring_crt_client(self, runtime_config):
        return (
            runtime_config.get('preferred_transfer_client')
            == constants.CRT_TRANSFER_CLIENT
        )

    def _is_newly_eligible_for_crt_client(self, runtime_config):
        if self._is_preferring_crt_client(runtime_config):
            return False
        return not awscrt.s3.is_optimized_for_system()

    def _should_use_transfer_config_defaults(self, runtime_config):
        # Configurations that already resolve to the crt transfer client keep
        # its defaults so their behavior is unchanged.
        return self._is_newly_eligible_for_crt_client(runtime_config)

    def _create_crt_request_serializer(self, params):
        return BotocoreCRTRequestSerializer(
            self._session,
            {
                'region_name': self._resolve_region(params),
                'endpoint_url': params.get('endpoint_url'),
            },
            region_redirect_client_factory=lambda: (
                self._botocore_client_factory.create_client(params)
            ),
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
