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

import awscrt.s3
from awscrt.s3 import S3RequestTlsMode
from botocore.session import Session
from botocore.config import Config
from botocore.credentials import Credentials
from botocore.httpsession import DEFAULT_CA_BUNDLE
from s3transfer.manager import TransferManager
import s3transfer.crt
from s3transfer.crt import CRTTransferManager
import pytest

from awscli.customizations.s3.factory import (
    ClientFactory, TransferManagerFactory
)
from awscli.customizations.s3.transferconfig import RuntimeConfig


@pytest.fixture
def mock_crt_is_optimized_for_system():
    with mock.patch('awscrt.s3.is_optimized_for_system') as mock_is_optimized:
        mock_is_optimized.return_value = False
        yield mock_is_optimized


@pytest.fixture
def mock_crt_process_lock(monkeypatch):
    # The process lock is cached at the module layer whenever the
    # cross process lock is successfully acquired. This patch ensures that
    # test cases will start off with no previously cached process lock and
    # if a cross process is instantiated/acquired it will be the mock that
    # can be used for controlling lock behavior.
    monkeypatch.setattr('s3transfer.crt.CRT_S3_PROCESS_LOCK', None)
    with mock.patch('awscrt.s3.CrossProcessLock', spec=True) as mock_lock:
        yield mock_lock


@pytest.fixture
def mock_crt_s3_client():
    with mock.patch('s3transfer.crt.S3Client', spec=True) as mock_client:
        yield mock_client


@pytest.fixture
def transfer_manager_factory():
    session = mock.Mock(Session)
    session.get_config_variable.return_value = None
    session.get_default_client_config.return_value = None
    return TransferManagerFactory(session)


@pytest.fixture
def s3_params():
    return {
        'region': 'us-west-2',
        'endpoint_url': None,
        'verify_ssl': None,
    }


def test_crt_get_optimized_platforms_match_expected_platforms():
    expected_platforms = {
        'p4d.24xlarge',
        'p4de.24xlarge',
        'p5.48xlarge',
        'trn1n.32xlarge',
        'trn1.32xlarge',
    }
    actual_platforms = set(awscrt.s3.get_optimized_platforms())
    assert expected_platforms == actual_platforms, (
        'Expected set of CRT optimized platforms does not match result from '
        'CRT. The result from CRT determines which platforms the CLI will '
        'automatically use the S3 CRT client for. If the change in optimized '
        'platforms is expected/appropriate, update the expected_platforms '
        'set in this test and the list of CRT optimized platforms in the '
        'documentation located at: awscli/topics/s3-config.rst'
    )


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
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='classic'
        )
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

    def assert_is_classic_manager(self, manager):
        self.assertIsInstance(manager, TransferManager)

    def assert_is_crt_manager(self, manager):
        self.assertIsInstance(manager, CRTTransferManager)

    def assert_expected_throughput_target_gbps(
            self, mock_crt_client, expected_throughput_target_gbps):
        self.assertEqual(
            mock_crt_client.call_args[1]['throughput_target_gbps'],
            expected_throughput_target_gbps
        )

    def test_create_transfer_manager_classic(self):
        transfer_client = mock.Mock()
        self.session.create_client.return_value = transfer_client
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_classic_manager(transfer_manager)
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

    def test_can_provide_botocore_client_to_classic_manager(self):
        transfer_client = mock.Mock()
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config, botocore_client=transfer_client)
        self.assert_is_classic_manager(transfer_manager)
        self.session.create_client.assert_not_called()
        self.assertIs(transfer_manager.client, transfer_client)

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
    def test_uses_botocore_credentials_for_crt_manager(
            self, mock_crt_client):
        credentials = Credentials('access_key', 'secret_key', 'token')
        self.session.get_credentials.return_value = credentials
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.session.get_credentials.assert_called_with()
        crt_credential_provider = mock_crt_client.call_args[1][
            'credential_provider'
        ]
        self.assertIsNotNone(crt_credential_provider)

        # Ensure the credentials returned by the CRT credential provider
        # match the session's credentials
        future = crt_credential_provider.get_credentials()
        crt_credentials = future.result()
        assert crt_credentials.access_key_id == 'access_key'
        assert crt_credentials.secret_access_key == 'secret_key'
        assert crt_credentials.session_token == 'token'

    @mock.patch('s3transfer.crt.S3Client')
    def test_disable_botocore_credentials_for_crt_manager(
            self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt')
        self.params['sign_request'] = False
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.session.get_credentials.assert_not_called()
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
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
            target_bandwidth=1_000_000_000)
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assert_expected_throughput_target_gbps(mock_crt_client, 8)

    @mock.patch('s3transfer.crt.get_recommended_throughput_target_gbps')
    @mock.patch('s3transfer.crt.S3Client')
    def test_target_bandwidth_uses_crt_recommended_throughput(
            self, mock_crt_client, mock_get_target_gbps):
        mock_get_target_gbps.return_value = 100
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        self.assert_expected_throughput_target_gbps(mock_crt_client, 100)

    @mock.patch('s3transfer.crt.get_recommended_throughput_target_gbps')
    @mock.patch('s3transfer.crt.S3Client')
    def test_crt_recommended_target_throughput_default(
            self, mock_crt_client, mock_get_target_gbps):
        mock_get_target_gbps.return_value = None
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config)
        self.assert_is_crt_manager(transfer_manager)
        # Default when CRT is unable to recommend a throughput
        # should be 10 gbps
        self.assert_expected_throughput_target_gbps(mock_crt_client, 10)

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


@pytest.mark.parametrize(
    'preferred_transfer_client,extra_params,'
    'crt_is_optimized_for_system,crt_running_in_other_process,'
    'expected_transfer_manager_cls',
    [
        (None, {}, False, False, TransferManager),
        ('auto', {}, False, False, TransferManager),
        ('classic', {}, False, False, TransferManager),
        ('crt', {}, False, False, CRTTransferManager),

        # "default" is a supported alias for "classic"
        ('default', {}, False, False, TransferManager),

        # Cases when CRT is optimized for system
        (None, {}, True, False, CRTTransferManager),
        ('auto', {}, True, False, CRTTransferManager),
        ('classic', {}, True, False, TransferManager),
        ('crt', {}, True, False, CRTTransferManager),

        # Cases when another AWS CLI process is running CRT
        (None, {}, True, True, TransferManager),
        ('auto', {}, True, True, TransferManager),
        ('classic', {}, True, True, TransferManager),
        ('crt', {}, True, True, CRTTransferManager),

        # S3 copies always default to classic transfer manager
        (None, {'paths_type': 's3s3'}, True, False, TransferManager),
        ('auto', {'paths_type': 's3s3'}, True, False, TransferManager),
        ('classic', {'paths_type': 's3s3'}, True, False, TransferManager),
        ('crt', {'paths_type': 's3s3'}, True, False, TransferManager),

        # Streaming operations use requested transfer client
        (None, {'is_stream': True}, False, False, TransferManager),
        ('auto', {'is_stream': True}, False, False, TransferManager),
        ('classic', {'is_stream': True}, False, False, TransferManager),
        ('crt', {'is_stream': True}, False, False, CRTTransferManager),
    ]
)
def test_transfer_manager_cls_resolution(
    preferred_transfer_client,
    extra_params,
    crt_is_optimized_for_system,
    crt_running_in_other_process,
    expected_transfer_manager_cls,
    transfer_manager_factory,
    s3_params,
    mock_crt_is_optimized_for_system,
    mock_crt_process_lock,
    mock_crt_s3_client,
):
    s3_params.update(extra_params)
    mock_crt_is_optimized_for_system.return_value = crt_is_optimized_for_system
    if crt_running_in_other_process:
        mock_crt_process_lock.return_value.acquire.side_effect = RuntimeError

    transfer_manager = _create_transfer_manager_from_factory(
        transfer_manager_factory, s3_params, preferred_transfer_client
    )
    assert isinstance(transfer_manager, expected_transfer_manager_cls)


@pytest.mark.parametrize(
    'preferred_transfer_client,crt_is_optimized_for_system',
    [
        ('auto', True),
        ('crt', False),
        ('crt', True),
    ]
)
def test_factory_always_acquires_crt_transfer_lock_for_crt_manager(
    preferred_transfer_client,
    crt_is_optimized_for_system,
    transfer_manager_factory,
    s3_params,
    mock_crt_is_optimized_for_system,
    mock_crt_process_lock,
    mock_crt_s3_client,
):
    mock_crt_is_optimized_for_system.return_value = crt_is_optimized_for_system
    transfer_manager = _create_transfer_manager_from_factory(
        transfer_manager_factory, s3_params, preferred_transfer_client
    )
    assert isinstance(transfer_manager, CRTTransferManager)
    assert s3transfer.crt.CRT_S3_PROCESS_LOCK
    mock_crt_process_lock.assert_called_once_with('aws-cli')
    mock_crt_process_lock.return_value.acquire.assert_called_once_with()


@pytest.mark.parametrize(
    'preferred_transfer_client,crt_is_optimized_for_system',
    [
        ('auto', False),
        ('classic', False),
        ('classic', True),
    ]
)
def test_factory_never_acquires_crt_transfer_lock_for_classic_manager(
    preferred_transfer_client,
    crt_is_optimized_for_system,
    transfer_manager_factory,
    s3_params,
    mock_crt_is_optimized_for_system,
    mock_crt_process_lock,
    mock_crt_s3_client,
):
    mock_crt_is_optimized_for_system.return_value = crt_is_optimized_for_system
    transfer_manager = _create_transfer_manager_from_factory(
        transfer_manager_factory, s3_params, preferred_transfer_client
    )
    assert isinstance(transfer_manager, TransferManager)
    assert s3transfer.crt.CRT_S3_PROCESS_LOCK is None
    mock_crt_process_lock.assert_not_called()
    mock_crt_process_lock.return_value.acquire.assert_not_called()


def _create_transfer_manager_from_factory(
    transfer_manager_factory,
    params,
    preferred_transfer_client=None
):
    runtime_config_kwargs = {}
    if preferred_transfer_client is not None:
        runtime_config_kwargs[
            'preferred_transfer_client'] = preferred_transfer_client
    runtime_config = RuntimeConfig().build_config(**runtime_config_kwargs)
    return transfer_manager_factory.create_transfer_manager(
        params, runtime_config
    )
