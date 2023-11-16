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

import awscrt.s3
from botocore.client import Config
from botocore.httpsession import DEFAULT_CA_BUNDLE
from s3transfer.manager import TransferManager
from s3transfer.crt import (
    acquire_crt_s3_process_lock, create_s3_crt_client,
    BotocoreCRTRequestSerializer, CRTTransferManager,
    BotocoreCRTCredentialsWrapper
)

from awscli.compat import urlparse
from awscli.customizations.s3 import constants
from awscli.customizations.s3.transferconfig import \
    create_transfer_config_from_runtime_config


LOGGER = logging.getLogger(__name__)


class ClientFactory:
    def __init__(self, session):
        self._session = session

    def create_client(self, params, is_source_client=False):
        create_client_kwargs = {
            'verify': params['verify_ssl']
        }
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

    def create_transfer_manager(self, params, runtime_config,
                                botocore_client=None):
        client_type = self._compute_transfer_client_type(
            params, runtime_config)
        if client_type == constants.CRT_TRANSFER_CLIENT:
            return self._create_crt_transfer_manager(params, runtime_config)
        else:
            return self._create_classic_transfer_manager(
                params, runtime_config, botocore_client)

    def _compute_transfer_client_type(self, params, runtime_config):
        if params.get('paths_type') == 's3s3':
            return constants.CLASSIC_TRANSFER_CLIENT
        preferred_transfer_client = runtime_config.get(
            'preferred_transfer_client',
            constants.AUTO_RESOLVE_TRANSFER_CLIENT
        )
        if preferred_transfer_client == constants.AUTO_RESOLVE_TRANSFER_CLIENT:
            return self._resolve_transfer_client_type_for_system()
        return preferred_transfer_client

    def _resolve_transfer_client_type_for_system(self):
        transfer_client_type = constants.CLASSIC_TRANSFER_CLIENT
        is_optimized_for_system = awscrt.s3.is_optimized_for_system()
        LOGGER.debug(
            'S3 CRT client optimized for system: %s', is_optimized_for_system
        )
        if is_optimized_for_system:
            is_running = self._is_crt_client_running_in_other_aws_cli_process()
            LOGGER.debug(
                'S3 CRT client running in different AWS CLI process: %s',
                is_running
            )
            if not is_running:
                transfer_client_type = constants.CRT_TRANSFER_CLIENT
        LOGGER.debug(
            'Auto resolved s3 transfer client to: %s', transfer_client_type
        )
        return transfer_client_type

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
            self._create_crt_request_serializer(params)
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
        multipart_chunksize = runtime_config.get('multipart_chunksize', None)
        if target_throughput:
            create_crt_client_kwargs['target_throughput'] = target_throughput
        if multipart_chunksize:
            create_crt_client_kwargs['part_size'] = multipart_chunksize
        if params.get('sign_request', True):
            crt_credentials_provider = self._get_crt_credentials_provider()
            create_crt_client_kwargs[
                'crt_credentials_provider'] = crt_credentials_provider

        return create_s3_crt_client(**create_crt_client_kwargs)

    def _create_crt_request_serializer(self, params):
        return BotocoreCRTRequestSerializer(
            self._session,
            {
                'region_name': self._resolve_region(params),
                'endpoint_url': params.get('endpoint_url'),
            }
        )

    def _create_classic_transfer_manager(self, params, runtime_config,
                                         client=None):
        if client is None:
            client = self._botocore_client_factory.create_client(params)
        transfer_config = create_transfer_config_from_runtime_config(
            runtime_config)
        transfer_config.max_in_memory_upload_chunks = \
            self._MAX_IN_MEMORY_CHUNKS
        transfer_config.max_in_memory_download_chunks = \
            self._MAX_IN_MEMORY_CHUNKS
        LOGGER.debug(
            "Using a multipart threshold of %s and a part size of %s",
            transfer_config.multipart_threshold,
            transfer_config.multipart_chunksize
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
