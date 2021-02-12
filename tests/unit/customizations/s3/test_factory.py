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
from awscli.testutils import unittest, mock

from botocore.session import Session
from botocore.config import Config
from s3transfer.manager import TransferManager
from s3transfer.crt import CRTTransferManager

from awscli.customizations.s3.factory import (
    ClientFactory, TransferManagerFactory
)
from awscli.customizations.s3.transferconfig import RuntimeConfig


class TestClientFactory(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)
        self.factory = ClientFactory(self.session)

    def test_create_client(self):
        params = {
            'region': 'us-west-2',
            'endpoint_url': 'https://myendpoint',
            'verify_ssl': True,
        }
        self.factory.create_client(params=params)
        self.session.create_client.assert_called_with(
            's3', region_name='us-west-2', endpoint_url='https://myendpoint',
            verify=True
        )

    def test_create_client_sets_sigv4_for_sse_kms(self):
        params = {
            'region': 'us-west-2',
            'endpoint_url': None,
            'verify_ssl': None,
            'sse': 'aws:kms',
        }
        self.factory.create_client(params)
        self.assertEqual(
            self.session.create_client.call_args[
                1]['config'].signature_version,
            's3v4'
        )

    def test_create_client_with_no_source_region(self):
        params = {
            'region': 'us-west-2',
            'endpoint_url': 'https://myendpoint',
            'verify_ssl': True,
            'source_region': None,
        }
        self.factory.create_client(params, is_source_client=True)
        self.session.create_client.assert_called_with(
            's3', region_name='us-west-2', endpoint_url='https://myendpoint',
            verify=True
        )

    def test_create_client_respects_source_region_for_copies(self):
        params = {
            'region': 'us-west-2',
            'endpoint_url': 'https://myendpoint',
            'verify_ssl': True,
            'source_region': 'us-west-1',
            'paths_type': 's3s3',
        }
        self.factory.create_client(params, is_source_client=True)
        self.session.create_client.assert_called_with(
            's3', region_name='us-west-1', endpoint_url=None,
            verify=True
        )


class TestTransferManagerFactory(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)
        self.session.get_config_variable.return_value = 'var'
        self.session.get_default_client_config.return_value = None
        self.factory = TransferManagerFactory(self.session)
        self.params = {
            'region': 'us-west-2',
            'endpoint_url': None,
            'verify_ssl': None,
        }
        self.runtime_config = self.get_runtime_config()

    def get_runtime_config(self, **kwargs):
        return RuntimeConfig().build_config(**kwargs)

    def assert_is_default_manager(self, manager):
        self.assertIsInstance(manager, TransferManager)

    def assert_is_crt_manager(self, manager):
        self.assertIsInstance(manager, CRTTransferManager)

    def test_create_transfer_manager_default(self):
        transfer_client = mock.Mock()
        self.session.create_client.return_value = transfer_client
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_default_manager(transfer_manager)
        self.session.create_client.assert_called_with(
            's3', region_name='us-west-2', endpoint_url=None,
            verify=None,
        )
        self.assertIs(transfer_manager.client, transfer_client)

    def test_proxies_transfer_config_to_default_transfer_manager(self):
        MB = 1024 ** 2
        self.runtime_config = self.get_runtime_config(
            multipart_chunksize=5 * MB,
            multipart_threshold=20 * MB,
            max_concurrent_requests=20,
            max_queue_size=5000,
            max_bandwidth=10 * MB,
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assertEqual(transfer_manager.config.multipart_chunksize, 5 * MB)
        self.assertEqual(transfer_manager.config.multipart_threshold, 20 * MB)
        self.assertEqual(transfer_manager.config.max_request_concurrency, 20)
        self.assertEqual(transfer_manager.config.max_request_queue_size, 5000)
        self.assertEqual(transfer_manager.config.max_bandwidth, 10 * MB)
        # These configurations are hardcoded and not configurable but
        # we just want to make sure they are being set by the factory.
        self.assertEqual(
            transfer_manager.config.max_in_memory_upload_chunks, 6)
        self.assertEqual(
            transfer_manager.config.max_in_memory_upload_chunks, 6)

    def test_can_provide_botocore_client_to_default_manager(self):
        transfer_client = mock.Mock()
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config, botocore_client=transfer_client)
        self.assert_is_default_manager(transfer_manager)
        self.session.create_client.assert_not_called()
        self.assertIs(transfer_manager.client, transfer_client)

    def test_creates_default_manager_when_explicitly_set_to_default(self):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='default')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_default_manager(transfer_manager)

    def test_creates_crt_manager_when_preferred_transfer_client_is_crt(self):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)

    def test_creates_default_manager_for_copies(self):
        self.params['paths_type'] = 's3s3'
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_default_manager(transfer_manager)

    def test_creates_default_manager_when_streaming_operation(self):
        self.params['is_stream'] = True
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_default_manager(transfer_manager)

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_region_parameter_for_crt_manager(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['region'] = 'param-region'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['region'], 'param-region'
        )
        self.assertEqual(
            self.session.create_client.call_args[1]['region_name'],
            'param-region'
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_falls_back_to_session_region_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        if 'region' in self.params:
            self.params.pop('region')
        self.session.get_config_variable.return_value = 'config-region'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['region'], 'config-region'
        )
        self.assertEqual(
            self.session.create_client.call_args[1]['region_name'],
            'config-region'
        )

    def test_uses_endpoint_url_parameter_for_crt_manager(self):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['endpoint_url'] = 'https://my.endpoint.com'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            self.session.create_client.call_args[1]['endpoint_url'],
            'https://my.endpoint.com'
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_botocore_credential_provider_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.session.get_component.assert_called_with('credential_provider')
        self.assertIsNotNone(
            mock_crt_client.call_args[1]['credential_provider']
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_disable_botocore_credential_provider_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['sign_request'] = False
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.session.get_component.assert_not_called()
        self.assertIsNone(
            mock_crt_client.call_args[1]['credential_provider']
        )
