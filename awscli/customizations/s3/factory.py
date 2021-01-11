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

from botocore.client import Config
from s3transfer.manager import TransferManager
from s3transfer.crt import CRTTransferManager

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

    def __init__(self, session):
        self._session = session
        self._botocore_client_factory = ClientFactory(self._session)

    def create_transfer_manager(self, params, runtime_config,
                                botocore_client=None):
        client_type = self._compute_transfer_client_type(
            params, runtime_config)
        if client_type == constants.CRT_TRANSFER_CLIENT:
            return self._create_crt_transfer_manager()
        else:
            return self._create_default_transfer_manager(
                params, runtime_config, botocore_client)

    def _compute_transfer_client_type(self, params, runtime_config):
        if params.get('paths_type') == 's3s3':
            return constants.DEFAULT_TRANSFER_CLIENT
        if params.get('is_stream'):
            return constants.DEFAULT_TRANSFER_CLIENT
        return runtime_config.get(
            'preferred_transfer_client', constants.DEFAULT_TRANSFER_CLIENT)

    def _create_crt_transfer_manager(self):
        return CRTTransferManager(self._session)

    def _create_default_transfer_manager(self, params, runtime_config,
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
