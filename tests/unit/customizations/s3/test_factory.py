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
from awscli.testutils import unittest, mock, FileCreator

from awscrt.s3 import S3RequestTlsMode
from botocore.session import Session
from botocore.config import Config
from botocore.httpsession import DEFAULT_CA_BUNDLE
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
        self.session.get_config_variable.return_value = None
        self.session.get_default_client_config.return_value = None
        self.factory = TransferManagerFactory(self.session)
        self.params = {
            'region': 'us-west-2',
            'endpoint_url': None,
            'verify_ssl': None,
        }
        self.runtime_config = self.get_runtime_config()
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def get_runtime_config(self, **kwargs):
        return RuntimeConfig().build_config(**kwargs)

    def assert_tls_enabled_for_crt_client(self, mock_crt_client):
        self.assertEqual(
            mock_crt_client.call_args[1]['tls_mode'],
            S3RequestTlsMode.ENABLED
        )

    def assert_tls_disabled_for_crt_client(self, mock_crt_client):
        self.assertEqual(
            mock_crt_client.call_args[1]['tls_mode'],
            S3RequestTlsMode.DISABLED
        )

    def assert_uses_client_tls_context_options(
            self, mock_crt_client, mock_client_tls_context_options):
        mock_connection_options = mock_client_tls_context_options. \
            return_value.new_connection_options.return_value
        self.assertIs(
            mock_crt_client.call_args[1]['tls_connection_options'],
            mock_connection_options
        )

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
        params = {
            'verify_ssl': DEFAULT_CA_BUNDLE
        }
        self.session.get_config_variable.return_value = 'config-region'
        transfer_manager = self.factory.create_transfer_manager(
            params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['region'], 'config-region'
        )
        self.assertEqual(
            self.session.create_client.call_args[1]['region_name'],
            'config-region'
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_tls_by_default_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assert_tls_enabled_for_crt_client(mock_crt_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_endpoint_url_parameter_for_crt_manager(
            self, mock_crt_client):
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
        self.assert_tls_enabled_for_crt_client(mock_crt_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_can_disable_tls_using_endpoint_scheme_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['endpoint_url'] = 'http://my.endpoint.com'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            self.session.create_client.call_args[1]['endpoint_url'],
            'http://my.endpoint.com'
        )
        self.assert_tls_disabled_for_crt_client(mock_crt_client)

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

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_for_crt_manager(
            self, mock_client_tls_context_options, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        fake_ca_contents = b"fake ca content"
        fake_ca_bundle = self.files.create_file(
            "fake_ca", fake_ca_contents, mode='wb')
        self.params['verify_ssl'] = fake_ca_bundle
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertEqual(tls_context_options.ca_buffer,
                         fake_ca_contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options)

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_ca_bundle_from_session_for_crt_manager(
            self, mock_client_tls_context_options, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        fake_ca_contents = b"fake ca content"
        fake_ca_bundle = self.files.create_file(
            "fake_ca", fake_ca_contents, mode='wb')
        self.session.get_config_variable.return_value = fake_ca_bundle
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertEqual(tls_context_options.ca_buffer,
                         fake_ca_contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options)

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_none_for_crt_manager(
            self, mock_client_tls_context_options, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['verify_ssl'] = None
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        with open(DEFAULT_CA_BUNDLE, mode='rb') as fh:
            contents = fh.read()
            self.assertEqual(tls_context_options.ca_buffer, contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options)

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_false_for_crt_manager(
            self, mock_client_tls_context_options, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['verify_ssl'] = False
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertFalse(tls_context_options.verify_peer)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options)

    @mock.patch('s3transfer.crt.S3Client')
    def test_target_bandwidth_configure_for_crt_manager(
            self, mock_crt_client):
        GB = 1024 ** 3
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
            target_bandwidth=1*GB)
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['throughput_target_gbps'],
            8
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_multipart_chunksize_configure_for_crt_manager(
            self, mock_crt_client):
        part_size = 16 * (1024**2)
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
            multipart_chunksize=part_size)
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['part_size'],
            part_size
        )
