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
import awscrt.exceptions
import awscrt.s3
import pytest
import s3transfer.crt
from awscrt.s3 import S3FileIoOptions, S3RequestTlsMode
from botocore.config import Config
from botocore.context import get_context, start_as_current_context
from botocore.credentials import Credentials
from botocore.exceptions import InvalidConfigError
from botocore.httpsession import DEFAULT_CA_BUNDLE
from botocore.session import Session
from s3transfer.crt import CRTTransferManager, create_s3_crt_client
from s3transfer.manager import TransferManager

from awscli.customizations.s3 import constants
from awscli.customizations.s3.factory import (
    ADAPTIVE_RETRY_MODE,
    CRT_PART_SIZE_EXCEEDS_MEMORY_LIMIT,
    MAX_CRT_MAX_ATTEMPTS,
    MIN_CRT_MAX_ATTEMPTS,
    MINIMUM_TARGET_THROUGHPUT_GBPS,
    ClientFactory,
    TransferManagerFactory,
)
from awscli.customizations.s3.transferconfig import (
    InvalidConfigError as InvalidTransferConfigError,
)
from awscli.customizations.s3.transferconfig import RuntimeConfig
from awscli.testutils import FileCreator, mock, unittest


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
def registered_feature_ids():
    with start_as_current_context():
        yield get_context().features


@pytest.fixture
def mock_crt_s3_client():
    with mock.patch('s3transfer.crt.S3Client', spec=True) as mock_client:
        yield mock_client


def stub_config_variables(session, **values):
    """Resolves the named config variables and everything else to None"""
    session.get_config_variable.side_effect = values.get


def stub_configured_variables(session, *names):
    """Marks the named config variables as explicitly configured"""
    session.get_component.return_value.is_explicitly_set.side_effect = (
        lambda name: name in names
    )


@pytest.fixture
def transfer_manager_factory():
    session = mock.Mock(Session)
    stub_config_variables(session)
    stub_configured_variables(session)
    session.get_default_client_config.return_value = None
    session.get_scoped_config.return_value = {}
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
        'p5e.48xlarge',
        'p5en.48xlarge',
        'p6-b200.48xlarge',
        'p6-b300.48xlarge',
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
            's3',
            region_name='us-west-2',
            endpoint_url='https://myendpoint',
            verify=True,
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
            self.session.create_client.call_args[1][
                'config'
            ].signature_version,
            's3v4',
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
            's3',
            region_name='us-west-2',
            endpoint_url='https://myendpoint',
            verify=True,
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
            's3', region_name='us-west-1', endpoint_url=None, verify=True
        )


class TestTransferManagerFactory(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)
        stub_config_variables(self.session)
        stub_configured_variables(self.session)
        self.session.get_default_client_config.return_value = None
        self.session.get_scoped_config.return_value = {}
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
            mock_crt_client.call_args[1]['tls_mode'], S3RequestTlsMode.ENABLED
        )

    def assert_tls_disabled_for_crt_client(self, mock_crt_client):
        self.assertEqual(
            mock_crt_client.call_args[1]['tls_mode'], S3RequestTlsMode.DISABLED
        )

    def assert_uses_client_tls_context_options(
        self, mock_crt_client, mock_client_tls_context_options
    ):
        mock_connection_options = mock_client_tls_context_options.return_value.new_connection_options.return_value
        self.assertIs(
            mock_crt_client.call_args[1]['tls_connection_options'],
            mock_connection_options,
        )

    def assert_is_classic_manager(self, manager):
        self.assertIsInstance(manager, TransferManager)

    def assert_is_crt_manager(self, manager):
        self.assertIsInstance(manager, CRTTransferManager)

    def assert_expected_throughput_target_gbps(
        self, mock_crt_client, expected_throughput_target_gbps
    ):
        self.assertEqual(
            mock_crt_client.call_args[1]['throughput_target_gbps'],
            expected_throughput_target_gbps,
        )

    def test_create_transfer_manager_classic(self):
        transfer_client = mock.Mock()
        self.session.create_client.return_value = transfer_client
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_classic_manager(transfer_manager)
        self.session.create_client.assert_called_with(
            's3',
            region_name='us-west-2',
            endpoint_url=None,
            verify=None,
        )
        self.assertIs(transfer_manager.client, transfer_client)

    def test_proxies_transfer_config_to_default_transfer_manager(self):
        MB = 1024**2
        self.runtime_config = self.get_runtime_config(
            multipart_chunksize=5 * MB,
            multipart_threshold=20 * MB,
            max_concurrent_requests=20,
            max_queue_size=5000,
            max_bandwidth=10 * MB,
            io_chunksize=1 * MB,
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assertEqual(transfer_manager.config.multipart_chunksize, 5 * MB)
        self.assertEqual(transfer_manager.config.multipart_threshold, 20 * MB)
        self.assertEqual(transfer_manager.config.max_request_concurrency, 20)
        self.assertEqual(transfer_manager.config.max_request_queue_size, 5000)
        self.assertEqual(transfer_manager.config.max_bandwidth, 10 * MB)
        self.assertEqual(transfer_manager.config.io_chunksize, 1 * MB)
        # These configurations are hardcoded and not configurable but
        # we just want to make sure they are being set by the factory.
        self.assertEqual(
            transfer_manager.config.max_in_memory_upload_chunks, 6
        )
        self.assertEqual(
            transfer_manager.config.max_in_memory_upload_chunks, 6
        )

    def test_can_provide_botocore_client_to_classic_manager(self):
        transfer_client = mock.Mock()
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config, botocore_client=transfer_client
        )
        self.assert_is_classic_manager(transfer_manager)
        self.session.create_client.assert_not_called()
        self.assertIs(transfer_manager.client, transfer_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_region_parameter_for_crt_manager(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['region'] = 'param-region'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['region'], 'param-region'
        )
        self.assertEqual(
            self.session.create_client.call_args[1]['region_name'],
            'param-region',
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_creates_crt_client_for_redirected_region(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )

        # The client for the configured region is created up front, and each
        # selected region is cached.
        self.assertEqual(mock_crt_client.call_count, 1)
        self.assertIs(
            transfer_manager.get_crt_client(),
            transfer_manager.get_crt_client(),
        )
        self.assertIs(
            transfer_manager.get_crt_client('eu-central-1'),
            transfer_manager.get_crt_client('eu-central-1'),
        )

        self.assertEqual(mock_crt_client.call_count, 2)
        self.assertEqual(
            mock_crt_client.call_args_list[0].kwargs['region'],
            'us-west-2',
        )
        self.assertEqual(
            mock_crt_client.call_args_list[1].kwargs['region'],
            'eu-central-1',
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_falls_back_to_session_region_for_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        params = {'verify_ssl': DEFAULT_CA_BUNDLE}
        stub_config_variables(self.session, region='config-region')
        transfer_manager = self.factory.create_transfer_manager(
            params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['region'], 'config-region'
        )
        self.assertEqual(
            self.session.create_client.call_args[1]['region_name'],
            'config-region',
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_tls_by_default_for_crt_manager(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assert_tls_enabled_for_crt_client(mock_crt_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_endpoint_url_parameter_for_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['endpoint_url'] = 'https://my.endpoint.com'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            self.session.create_client.call_args[1]['endpoint_url'],
            'https://my.endpoint.com',
        )
        self.assert_tls_enabled_for_crt_client(mock_crt_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_can_disable_tls_using_endpoint_scheme_for_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['endpoint_url'] = 'http://my.endpoint.com'
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            self.session.create_client.call_args[1]['endpoint_url'],
            'http://my.endpoint.com',
        )
        self.assert_tls_disabled_for_crt_client(mock_crt_client)

    @mock.patch('s3transfer.crt.S3Client')
    def test_uses_botocore_credentials_for_crt_manager(self, mock_crt_client):
        credentials = Credentials('access_key', 'secret_key', 'token')
        self.session.get_credentials.return_value = credentials
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
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
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['sign_request'] = False
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.session.get_credentials.assert_not_called()
        self.assertIsNone(mock_crt_client.call_args[1]['credential_provider'])

    @mock.patch('s3transfer.crt.S3Client')
    def test_invalid_client_config_raises_when_creating_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['verify_ssl'] = ' '

        # Reported once here rather than once per submitted transfer.
        with self.assertRaises(InvalidConfigError):
            self.factory.create_transfer_manager(
                self.params, self.runtime_config
            )

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_for_crt_manager(
        self, mock_client_tls_context_options, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        fake_ca_contents = b"fake ca content"
        fake_ca_bundle = self.files.create_file(
            "fake_ca", fake_ca_contents, mode='wb'
        )
        self.params['verify_ssl'] = fake_ca_bundle
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertEqual(tls_context_options.ca_buffer, fake_ca_contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options
        )

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_ca_bundle_from_session_for_crt_manager(
        self, mock_client_tls_context_options, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        fake_ca_contents = b"fake ca content"
        fake_ca_bundle = self.files.create_file(
            "fake_ca", fake_ca_contents, mode='wb'
        )
        stub_config_variables(self.session, ca_bundle=fake_ca_bundle)
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertEqual(tls_context_options.ca_buffer, fake_ca_contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options
        )

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_none_for_crt_manager(
        self, mock_client_tls_context_options, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['verify_ssl'] = None
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        with open(DEFAULT_CA_BUNDLE, mode='rb') as fh:
            contents = fh.read()
            self.assertEqual(tls_context_options.ca_buffer, contents)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options
        )

    @mock.patch('s3transfer.crt.S3Client')
    @mock.patch('s3transfer.crt.ClientTlsContext')
    def test_use_verify_ssl_parameter_false_for_crt_manager(
        self, mock_client_tls_context_options, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        self.params['verify_ssl'] = False
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        tls_context_options = mock_client_tls_context_options.call_args[0][0]
        self.assertFalse(tls_context_options.verify_peer)
        self.assert_uses_client_tls_context_options(
            mock_crt_client, mock_client_tls_context_options
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_target_bandwidth_configure_for_crt_manager(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt', target_bandwidth=1_000_000_000
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assert_expected_throughput_target_gbps(mock_crt_client, 8)

    @mock.patch('s3transfer.crt.S3Client')
    def test_fio_options_configure_for_crt_manager(self, mock_crt_client):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
            should_stream=True,
            disk_throughput=1000**3,
            direct_io=True,
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        expected_fio_options = S3FileIoOptions(
            should_stream=True,
            disk_throughput_gbps=8.0,
            direct_io=True,
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['fio_options'], expected_fio_options
        )

    @mock.patch('awscrt.s3.get_recommended_throughput_target_gbps')
    @mock.patch('s3transfer.crt.S3Client')
    def test_target_bandwidth_uses_crt_recommended_throughput(
        self, mock_crt_client, mock_get_target_gbps
    ):
        mock_get_target_gbps.return_value = 100
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assert_expected_throughput_target_gbps(mock_crt_client, 100)

    @mock.patch('s3transfer.crt.get_recommended_throughput_target_gbps')
    @mock.patch('s3transfer.crt.S3Client')
    def test_crt_recommended_target_throughput_default(
        self, mock_crt_client, mock_get_target_gbps
    ):
        mock_get_target_gbps.return_value = None
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        # Default when CRT is unable to recommend a throughput
        # should be 10 gbps
        self.assert_expected_throughput_target_gbps(mock_crt_client, 10)

    @mock.patch('s3transfer.crt.S3Client')
    def test_multipart_chunksize_configure_for_crt_manager(
        self, mock_crt_client
    ):
        part_size = 16 * (1024**2)
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt', multipart_chunksize=part_size
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(mock_crt_client.call_args[1]['part_size'], part_size)

    @mock.patch('s3transfer.crt.S3Client')
    def test_default_part_size_for_crt_manager(self, mock_crt_client):
        # `multipart_chunksize` is not provided, so it is not explicitly
        # configured even though the runtime config still resolves a default.
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        # When `multipart_chunksize` isn't explicitly provided, configure
        # `part_size` to `None`.
        self.assertEqual(mock_crt_client.call_args[1]['part_size'], None)

    @mock.patch('s3transfer.crt.S3Client')
    def test_multipart_threshold_configure_for_crt_manager(
        self, mock_crt_client
    ):
        threshold = 64 * (1024**2)
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt', multipart_threshold=threshold
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['multipart_upload_threshold'],
            threshold,
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_max_concurrent_requests_configure_for_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt', max_concurrent_requests=3
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['max_active_connections_override'], 3
        )

    def test_optimized_system_does_not_use_transfer_config_defaults(self):
        runtime_config = self.get_runtime_config()
        with mock.patch(
            'awscrt.s3.is_optimized_for_system', return_value=True
        ):
            self.assertFalse(
                self.factory._should_use_transfer_config_defaults(
                    runtime_config
                )
            )

    def test_explicit_crt_does_not_use_transfer_config_defaults(self):
        runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        with mock.patch(
            'awscrt.s3.is_optimized_for_system', return_value=False
        ):
            self.assertFalse(
                self.factory._should_use_transfer_config_defaults(
                    runtime_config
                )
            )

    def test_newly_eligible_system_uses_transfer_config_defaults(self):
        runtime_config = self.get_runtime_config()
        with mock.patch(
            'awscrt.s3.is_optimized_for_system', return_value=False
        ):
            self.assertTrue(
                self.factory._should_use_transfer_config_defaults(
                    runtime_config
                )
            )

    @mock.patch('awscrt.s3.is_optimized_for_system', return_value=False)
    @mock.patch('s3transfer.crt.S3Client')
    def test_transfer_config_defaults_passed_for_newly_eligible_system(
        self, mock_crt_client, mock_is_optimized
    ):
        self.runtime_config = self.get_runtime_config()
        with mock.patch.object(
            self.factory,
            '_resolve_transfer_client_type_for_system',
            return_value=constants.CRT_TRANSFER_CLIENT,
        ):
            transfer_manager = self.factory.create_transfer_manager(
                self.params, self.runtime_config
            )
        self.assert_is_crt_manager(transfer_manager)
        call_kwargs = mock_crt_client.call_args[1]
        defaults = RuntimeConfig.defaults()
        self.assertEqual(
            call_kwargs['part_size'], defaults['multipart_chunksize']
        )
        self.assertEqual(
            call_kwargs['multipart_upload_threshold'],
            defaults['multipart_threshold'],
        )
        self.assertEqual(
            call_kwargs['max_active_connections_override'],
            defaults['max_concurrent_requests'],
        )

    @mock.patch('s3transfer.crt.S3Client')
    def test_unconfigured_options_not_passed_to_crt_manager(
        self, mock_crt_client
    ):
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt'
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        call_kwargs = mock_crt_client.call_args[1]
        self.assertIsNone(call_kwargs['part_size'])
        self.assertIsNone(call_kwargs['multipart_upload_threshold'])
        self.assertIsNone(call_kwargs['max_active_connections_override'])

    @mock.patch('s3transfer.crt.S3Client')
    def test_part_size_configured_when_matching_default(self, mock_crt_client):
        # Explicitly configuring the same value as the default still counts
        # as explicitly configured.
        default_chunksize = RuntimeConfig.defaults()['multipart_chunksize']
        self.runtime_config = self.get_runtime_config(
            preferred_transfer_client='crt',
            multipart_chunksize=default_chunksize,
        )
        transfer_manager = self.factory.create_transfer_manager(
            self.params, self.runtime_config
        )
        self.assert_is_crt_manager(transfer_manager)
        self.assertEqual(
            mock_crt_client.call_args[1]['part_size'], default_chunksize
        )


@pytest.fixture
def auto_resolve_session():
    session = mock.Mock(Session)
    stub_config_variables(session)
    stub_configured_variables(session)
    session.get_default_client_config.return_value = None
    session.get_scoped_config.return_value = {}
    return session


@pytest.fixture
def auto_resolve_factory(auto_resolve_session, monkeypatch):
    monkeypatch.setenv('AWS_CLI_AUTO_RESOLVE_CLIENT', 'crt')
    return TransferManagerFactory(auto_resolve_session)


@pytest.fixture
def mock_crt_lock_held(auto_resolve_factory):
    with mock.patch.object(
        auto_resolve_factory,
        '_is_crt_client_running_in_other_aws_cli_process',
        return_value=False,
    ) as mock_lock_held:
        yield mock_lock_held


@pytest.fixture
def resolve_client_type(
    auto_resolve_factory,
    s3_params,
    mock_crt_is_optimized_for_system,
    mock_crt_recommended_throughput,
    mock_crt_lock_held,
):
    def _resolve(**kwargs):
        runtime_config = RuntimeConfig().build_config(**kwargs)
        return auto_resolve_factory._compute_transfer_client_type(
            s3_params, runtime_config
        )

    return _resolve


class TestAutoResolveCrtClient:
    def test_resolves_to_crt_when_enabled(self, resolve_client_type):
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_resolves_to_classic_when_env_var_unset(
        self, resolve_client_type, monkeypatch
    ):
        monkeypatch.delenv('AWS_CLI_AUTO_RESOLVE_CLIENT')
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_resolves_to_classic_when_env_var_is_other_value(
        self, resolve_client_type, monkeypatch
    ):
        monkeypatch.setenv('AWS_CLI_AUTO_RESOLVE_CLIENT', 'classic')
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_optimized_system_resolves_to_crt_without_env_var(
        self,
        resolve_client_type,
        monkeypatch,
        mock_crt_is_optimized_for_system,
    ):
        monkeypatch.delenv('AWS_CLI_AUTO_RESOLVE_CLIENT')
        mock_crt_is_optimized_for_system.return_value = True
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_resolves_to_classic_when_max_bandwidth_configured(
        self, resolve_client_type
    ):
        assert (
            resolve_client_type(max_bandwidth=1024)
            == constants.CLASSIC_TRANSFER_CLIENT
        )

    def test_resolves_to_classic_for_adaptive_retry_mode(
        self, resolve_client_type, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, retry_mode='adaptive')
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_resolves_to_crt_for_standard_retry_mode(
        self, resolve_client_type, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, retry_mode='standard')
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_resolves_to_classic_for_stream_upload(
        self, resolve_client_type, s3_params
    ):
        s3_params['is_stream'] = True
        s3_params['paths_type'] = 'locals3'
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_resolves_to_crt_for_stream_download(
        self, resolve_client_type, s3_params
    ):
        s3_params['is_stream'] = True
        s3_params['paths_type'] = 's3local'
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_optimized_system_resolves_to_crt_for_stream_upload(
        self,
        resolve_client_type,
        s3_params,
        mock_crt_is_optimized_for_system,
    ):
        mock_crt_is_optimized_for_system.return_value = True
        s3_params['is_stream'] = True
        s3_params['paths_type'] = 'locals3'
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_resolves_to_classic_when_lock_held(
        self, resolve_client_type, mock_crt_lock_held
    ):
        mock_crt_lock_held.return_value = True
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_explicit_crt_ignores_unsupported_settings(
        self, resolve_client_type
    ):
        assert (
            resolve_client_type(
                preferred_transfer_client='crt', max_bandwidth=1024
            )
            == constants.CRT_TRANSFER_CLIENT
        )

    def test_s3s3_always_resolves_to_classic(
        self, resolve_client_type, s3_params
    ):
        s3_params['paths_type'] = 's3s3'
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT


class TestClassicOnlySettingsWarning:
    def test_warns_when_routed_away_for_max_bandwidth(
        self, resolve_client_type, capsys
    ):
        resolve_client_type(max_bandwidth=1024)
        warning = capsys.readouterr().err
        assert 'max_bandwidth' in warning
        assert 'A future version of the AWS CLI' in warning
        assert 'preferred_transfer_client' in warning

    def test_does_not_warn_for_adaptive_retry_mode(
        self, resolve_client_type, auto_resolve_session, capsys
    ):
        # The crt transfer client will eventually support adaptive retries, so
        # there is nothing for the user to act on.
        stub_config_variables(auto_resolve_session, retry_mode='adaptive')
        resolve_client_type()
        assert capsys.readouterr().err == ''

    def test_does_not_warn_for_stream_upload_fallback(
        self, resolve_client_type, s3_params, capsys
    ):
        s3_params['is_stream'] = True
        s3_params['paths_type'] = 'locals3'
        resolve_client_type()
        assert capsys.readouterr().err == ''

    def test_does_not_warn_when_crt_is_resolved(
        self, resolve_client_type, capsys
    ):
        resolve_client_type()
        assert capsys.readouterr().err == ''

    def test_does_not_warn_when_auto_resolve_disabled(
        self, resolve_client_type, monkeypatch, capsys
    ):
        monkeypatch.delenv('AWS_CLI_AUTO_RESOLVE_CLIENT')
        resolve_client_type(max_bandwidth=1024)
        assert capsys.readouterr().err == ''

    def test_does_not_warn_on_optimized_system(
        self,
        resolve_client_type,
        mock_crt_is_optimized_for_system,
        capsys,
    ):
        mock_crt_is_optimized_for_system.return_value = True
        resolve_client_type(max_bandwidth=1024)
        assert capsys.readouterr().err == ''

    def test_does_not_warn_when_classic_explicitly_preferred(
        self, resolve_client_type, capsys
    ):
        resolve_client_type(
            preferred_transfer_client='classic', max_bandwidth=1024
        )
        assert capsys.readouterr().err == ''


@pytest.fixture
def mock_crt_get_ec2_instance_type():
    with mock.patch('awscrt.s3.get_ec2_instance_type') as mock_instance_type:
        mock_instance_type.return_value = None
        yield mock_instance_type


@pytest.fixture
def mock_crt_recommended_throughput():
    # The factory and s3transfer each hold their own reference, and which one
    # resolves the target depends on the transfer client being created.
    with (
        mock.patch(
            'awscrt.s3.get_recommended_throughput_target_gbps'
        ) as mock_recommended,
        mock.patch(
            's3transfer.crt.get_recommended_throughput_target_gbps',
            new=mock_recommended,
        ),
    ):
        mock_recommended.return_value = None
        yield mock_recommended


@pytest.fixture
def crt_s3_client_kwargs(
    auto_resolve_factory,
    s3_params,
    mock_crt_is_optimized_for_system,
    mock_crt_get_ec2_instance_type,
    mock_crt_recommended_throughput,
    mock_crt_s3_client,
    mock_crt_process_lock,
):
    """Creates a crt transfer manager and returns the S3Client kwargs"""

    def _create(**kwargs):
        runtime_config = RuntimeConfig().build_config(**kwargs)
        auto_resolve_factory._create_crt_transfer_manager(
            s3_params, runtime_config
        )
        return mock_crt_s3_client.call_args[1]

    return _create


@pytest.fixture
def crt_client_kwargs(auto_resolve_factory, mock_crt_is_optimized_for_system):
    def _resolve(**kwargs):
        runtime_config = RuntimeConfig().build_config(**kwargs)
        return auto_resolve_factory._resolve_crt_client_config_kwargs(
            runtime_config
        )

    return _resolve


@pytest.fixture
def warn_unsupported_settings(auto_resolve_factory, capsys):
    def _warn(client_type, **kwargs):
        runtime_config = RuntimeConfig().build_config(**kwargs)
        auto_resolve_factory.warn_unsupported_settings(
            client_type, runtime_config
        )
        return capsys.readouterr().err

    return _warn


class TestWarnUnsupportedSettings:
    def test_warns_for_options_crt_ignores(self, warn_unsupported_settings):
        warning = warn_unsupported_settings(
            constants.CRT_TRANSFER_CLIENT,
            max_queue_size=500,
            io_chunksize=1024,
        )
        assert 'max_queue_size' in warning
        assert 'io_chunksize' in warning
        assert constants.CRT_TRANSFER_CLIENT in warning

    def test_warns_for_options_classic_ignores(
        self, warn_unsupported_settings
    ):
        warning = warn_unsupported_settings(
            constants.CLASSIC_TRANSFER_CLIENT,
            target_bandwidth=1024,
            direct_io=True,
        )
        assert 'target_bandwidth' in warning
        assert 'direct_io' in warning
        assert constants.CLASSIC_TRANSFER_CLIENT in warning

    def test_warns_for_max_bandwidth_when_crt_resolved(
        self, warn_unsupported_settings
    ):
        warning = warn_unsupported_settings(
            constants.CRT_TRANSFER_CLIENT, max_bandwidth=1024
        )
        assert 'max_bandwidth' in warning

    def test_does_not_warn_for_max_bandwidth_when_classic_resolved(
        self, warn_unsupported_settings
    ):
        assert (
            warn_unsupported_settings(
                constants.CLASSIC_TRANSFER_CLIENT, max_bandwidth=1024
            )
            == ''
        )

    def test_warns_for_adaptive_retry_mode_under_crt(
        self, warn_unsupported_settings, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, retry_mode='adaptive')
        warning = warn_unsupported_settings(constants.CRT_TRANSFER_CLIENT)
        assert f'retry_mode = {ADAPTIVE_RETRY_MODE}' in warning

    def test_does_not_warn_for_supported_retry_mode(
        self, warn_unsupported_settings, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, retry_mode='standard')
        assert warn_unsupported_settings(constants.CRT_TRANSFER_CLIENT) == ''

    def test_does_not_warn_for_adaptive_retry_mode_under_classic(
        self, warn_unsupported_settings, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, retry_mode='adaptive')
        assert (
            warn_unsupported_settings(constants.CLASSIC_TRANSFER_CLIENT) == ''
        )

    def test_does_not_warn_when_nothing_configured(
        self, warn_unsupported_settings
    ):
        assert warn_unsupported_settings(constants.CRT_TRANSFER_CLIENT) == ''

    def test_does_not_warn_for_supported_options(
        self, warn_unsupported_settings
    ):
        assert (
            warn_unsupported_settings(
                constants.CRT_TRANSFER_CLIENT,
                multipart_chunksize=8 * (1024**2),
                max_concurrent_requests=5,
            )
            == ''
        )

    def test_does_not_warn_across_clients(self, warn_unsupported_settings):
        assert (
            warn_unsupported_settings(
                constants.CLASSIC_TRANSFER_CLIENT,
                max_queue_size=500,
                io_chunksize=1024,
            )
            == ''
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
    ],
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
    ],
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
    ],
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
    transfer_manager_factory, params, preferred_transfer_client=None
):
    runtime_config_kwargs = {}
    if preferred_transfer_client is not None:
        runtime_config_kwargs['preferred_transfer_client'] = (
            preferred_transfer_client
        )
    runtime_config = RuntimeConfig().build_config(**runtime_config_kwargs)
    return transfer_manager_factory.create_transfer_manager(
        params, runtime_config
    )


@pytest.mark.parametrize(
    'preferred_transfer_client,extra_params,crt_is_optimized_for_system,'
    'expected_feature_id',
    [
        ('classic', {}, False, 'Ad'),
        ('crt', {}, False, 'Ae'),
        (None, {}, False, 'Af'),
        ('auto', {}, False, 'Af'),
        (None, {}, True, 'Ag'),
        ('auto', {}, True, 'Ag'),
        # S3 copies always use the classic client.
        ('crt', {'paths_type': 's3s3'}, True, 'Ad'),
        ('classic', {'paths_type': 's3s3'}, True, 'Ad'),
        (None, {'paths_type': 's3s3'}, True, 'Af'),
    ],
)
def test_registers_transfer_client_feature_id(
    preferred_transfer_client,
    extra_params,
    crt_is_optimized_for_system,
    expected_feature_id,
    transfer_manager_factory,
    s3_params,
    registered_feature_ids,
    mock_crt_is_optimized_for_system,
    mock_crt_process_lock,
    mock_crt_s3_client,
):
    s3_params.update(extra_params)
    mock_crt_is_optimized_for_system.return_value = crt_is_optimized_for_system
    _create_transfer_manager_from_factory(
        transfer_manager_factory, s3_params, preferred_transfer_client
    )
    assert expected_feature_id in registered_feature_ids


class TestMaxAttempts:
    def test_resolves_to_classic_when_retries_disabled(
        self, resolve_client_type, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=1)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    def test_resolves_to_crt_when_retries_enabled(
        self, resolve_client_type, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=2)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    def test_does_not_warn_when_falling_back_for_disabled_retries(
        self, resolve_client_type, auto_resolve_session, capsys
    ):
        stub_config_variables(auto_resolve_session, max_attempts=1)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        resolve_client_type()
        assert capsys.readouterr().err == ''

    def test_warns_when_crt_explicitly_preferred_with_retries_disabled(
        self, warn_unsupported_settings, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=1)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        warning = warn_unsupported_settings(
            constants.CRT_TRANSFER_CLIENT,
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT,
        )
        assert 'max_attempts = 1' in warning

    def test_maps_configured_max_attempts_to_crt_client(
        self, crt_client_kwargs, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=5)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        assert crt_client_kwargs()['retry_options'] == {'max_retries': 4}

    def test_applies_default_max_attempts_for_newly_eligible_hosts(
        self, crt_client_kwargs, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=3)
        assert crt_client_kwargs()['retry_options'] == {'max_retries': 2}

    def test_omits_max_attempts_when_crt_explicitly_preferred(
        self, crt_client_kwargs, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=3)
        kwargs = crt_client_kwargs(
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT
        )
        assert 'retry_options' not in kwargs

    def test_maps_configured_max_attempts_when_crt_explicitly_preferred(
        self, crt_client_kwargs, auto_resolve_session
    ):
        stub_config_variables(auto_resolve_session, max_attempts=5)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        kwargs = crt_client_kwargs(
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT
        )
        assert kwargs['retry_options'] == {'max_retries': 4}


class TestTargetThroughput:
    def test_targets_less_when_crt_has_no_recommendation(
        self, crt_s3_client_kwargs
    ):
        assert crt_s3_client_kwargs()['throughput_target_gbps'] == 4.0

    def test_defers_to_crt_recommendation_when_it_has_one(
        self, crt_s3_client_kwargs, mock_crt_recommended_throughput
    ):
        mock_crt_recommended_throughput.return_value = 50.0
        assert crt_s3_client_kwargs()['throughput_target_gbps'] == 50.0

    def test_targets_less_on_ec2_hosts_crt_cannot_recommend_for(
        self, crt_s3_client_kwargs, mock_crt_get_ec2_instance_type
    ):
        # Being on EC2 does not mean the crt client sized a pool for this
        # host, so the instance type must not decide the throughput target.
        mock_crt_get_ec2_instance_type.return_value = 't3.micro'
        assert crt_s3_client_kwargs()['throughput_target_gbps'] == 4.0

    def test_configured_target_bandwidth_wins(self, crt_s3_client_kwargs):
        kwargs = crt_s3_client_kwargs(target_bandwidth=1_250_000_000)
        assert kwargs['throughput_target_gbps'] == 10.0

    def test_floors_throughput_when_crt_explicitly_preferred(
        self, crt_s3_client_kwargs, mock_crt_recommended_throughput
    ):
        mock_crt_recommended_throughput.return_value = 3.0

        kwargs = crt_s3_client_kwargs(
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT
        )
        assert (
            kwargs['throughput_target_gbps'] == MINIMUM_TARGET_THROUGHPUT_GBPS
        )

    def test_keeps_higher_recommendation_when_crt_explicitly_preferred(
        self, crt_s3_client_kwargs, mock_crt_recommended_throughput
    ):
        mock_crt_recommended_throughput.return_value = 50.0
        kwargs = crt_s3_client_kwargs(
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT
        )
        assert kwargs['throughput_target_gbps'] == 50.0

    def test_does_not_floor_configured_target_bandwidth(
        self, crt_s3_client_kwargs
    ):
        kwargs = crt_s3_client_kwargs(
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT,
            target_bandwidth=125_000_000,
        )
        assert kwargs['throughput_target_gbps'] == 1.0

    def test_defers_to_crt_on_optimized_host(
        self,
        crt_s3_client_kwargs,
        mock_crt_is_optimized_for_system,
        mock_crt_recommended_throughput,
    ):
        mock_crt_is_optimized_for_system.return_value = True
        mock_crt_recommended_throughput.return_value = 3.0
        assert crt_s3_client_kwargs()['throughput_target_gbps'] == 3.0


class TestChunksizeExceedingCrtMemoryPool:
    """The crt client only reports an oversized chunksize while constructing."""

    @pytest.fixture
    def part_size_error(self):
        return RuntimeError(
            f'{CRT_PART_SIZE_EXCEEDS_MEMORY_LIMIT} '
            f'(AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT): Part size '
            f'exceeds the configured memory limit.'
        )

    @pytest.fixture
    def create_manager(self, auto_resolve_factory, s3_params):
        def _create(**kwargs):
            runtime_config = RuntimeConfig().build_config(**kwargs)
            return auto_resolve_factory.create_transfer_manager(
                s3_params, runtime_config, mock.Mock()
            )

        return _create

    @pytest.fixture
    def crt_manager_raises(self, auto_resolve_factory, part_size_error):
        with mock.patch.object(
            auto_resolve_factory,
            '_create_crt_transfer_manager',
            side_effect=part_size_error,
        ) as mock_create:
            yield mock_create

    def test_error_code_still_means_what_we_match_on(self):
        # Guards against awscrt renumbering the code out from under us.
        assert (
            awscrt.exceptions.from_code(
                CRT_PART_SIZE_EXCEEDS_MEMORY_LIMIT
            ).name
            == 'AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT'
        )

    def test_falls_back_to_classic_when_auto_resolved(
        self, create_manager, crt_manager_raises, mock_crt_lock_held
    ):
        assert isinstance(create_manager(), TransferManager)

    def test_releases_process_lock_when_falling_back(
        self, create_manager, crt_manager_raises, mock_crt_lock_held
    ):
        # Holding the lock while running classic denies the crt client to
        # every other process of the same application.
        with mock.patch(
            'awscli.customizations.s3.factory.release_crt_s3_process_lock'
        ) as mock_release:
            create_manager()
        assert mock_release.called

    def test_reports_classic_feature_id_when_falling_back(
        self,
        create_manager,
        crt_manager_raises,
        mock_crt_lock_held,
        registered_feature_ids,
    ):
        create_manager()
        assert 'Af' in registered_feature_ids

    def test_does_not_warn_when_falling_back(
        self, create_manager, crt_manager_raises, mock_crt_lock_held, capsys
    ):
        # Classic honors the configured chunksize, so nothing is lost.
        create_manager()
        assert capsys.readouterr().err == ''

    def test_raises_when_crt_explicitly_preferred(
        self, create_manager, crt_manager_raises
    ):
        with pytest.raises(InvalidTransferConfigError) as excinfo:
            create_manager(
                preferred_transfer_client=constants.CRT_TRANSFER_CLIENT
            )
        message = str(excinfo.value)
        assert 'multipart_chunksize' in message
        assert 'AWS_CRT_S3_MEMORY_LIMIT_IN_GIB' in message
        # Explicit crt must never be told to switch to classic.
        assert constants.CLASSIC_TRANSFER_CLIENT not in message

    def test_reraises_unrelated_runtime_errors(
        self, create_manager, auto_resolve_factory, mock_crt_lock_held
    ):
        with mock.patch.object(
            auto_resolve_factory,
            '_create_crt_transfer_manager',
            side_effect=RuntimeError('something else entirely'),
        ):
            with pytest.raises(RuntimeError, match='something else entirely'):
                create_manager()

    def test_uses_crt_when_the_chunksize_fits(
        self, create_manager, mock_crt_lock_held, mock_crt_s3_client
    ):
        manager = create_manager(multipart_chunksize=8 * 1024 * 1024)
        assert not isinstance(manager, TransferManager)


class TestMaxAttemptsBounds:
    """The crt rejects max_retries of 0 and of 64 or more."""

    @pytest.mark.parametrize(
        'max_attempts', [MIN_CRT_MAX_ATTEMPTS, 3, MAX_CRT_MAX_ATTEMPTS]
    )
    def test_resolves_to_crt_within_bounds(
        self, resolve_client_type, auto_resolve_session, max_attempts
    ):
        stub_config_variables(auto_resolve_session, max_attempts=max_attempts)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        assert resolve_client_type() == constants.CRT_TRANSFER_CLIENT

    @pytest.mark.parametrize(
        'max_attempts',
        [MIN_CRT_MAX_ATTEMPTS - 1, MAX_CRT_MAX_ATTEMPTS + 1, 1000],
    )
    def test_resolves_to_classic_outside_bounds(
        self, resolve_client_type, auto_resolve_session, max_attempts
    ):
        stub_config_variables(auto_resolve_session, max_attempts=max_attempts)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        assert resolve_client_type() == constants.CLASSIC_TRANSFER_CLIENT

    @pytest.mark.parametrize(
        'max_attempts', [MAX_CRT_MAX_ATTEMPTS, MAX_CRT_MAX_ATTEMPTS + 1]
    )
    def test_only_maps_retries_within_bounds(
        self, crt_client_kwargs, auto_resolve_session, max_attempts
    ):
        stub_config_variables(auto_resolve_session, max_attempts=max_attempts)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        kwargs = crt_client_kwargs()
        if max_attempts == MAX_CRT_MAX_ATTEMPTS:
            assert kwargs['retry_options'] == {'max_retries': max_attempts - 1}
        else:
            assert 'retry_options' not in kwargs

    def test_warns_when_crt_explicitly_preferred_above_bounds(
        self, warn_unsupported_settings, auto_resolve_session
    ):
        too_many = MAX_CRT_MAX_ATTEMPTS + 1
        stub_config_variables(auto_resolve_session, max_attempts=too_many)
        stub_configured_variables(auto_resolve_session, 'max_attempts')
        warning = warn_unsupported_settings(
            constants.CRT_TRANSFER_CLIENT,
            preferred_transfer_client=constants.CRT_TRANSFER_CLIENT,
        )
        assert f'max_attempts = {too_many}' in warning
        assert (
            f'must be between {MIN_CRT_MAX_ATTEMPTS} and '
            f'{MAX_CRT_MAX_ATTEMPTS}'
        ) in warning

    def test_upper_bound_matches_what_awscrt_accepts(self):
        # Guards against awscrt moving the limit out from under us.
        create_s3_crt_client(
            region='us-west-2',
            retry_options={'max_retries': MAX_CRT_MAX_ATTEMPTS - 1},
        )
        with pytest.raises(RuntimeError):
            create_s3_crt_client(
                region='us-west-2',
                retry_options={'max_retries': MAX_CRT_MAX_ATTEMPTS},
            )
