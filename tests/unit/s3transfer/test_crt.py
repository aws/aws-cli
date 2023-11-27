# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import io

import pytest
from botocore.credentials import Credentials, ReadOnlyCredentials
from botocore.exceptions import NoCredentialsError
from botocore.session import Session

from s3transfer.exceptions import TransferNotDoneError
from s3transfer.utils import CallArgs
from tests import HAS_CRT, FileCreator, mock, requires_crt, unittest

if HAS_CRT:
    import awscrt.auth
    import awscrt.s3

    import s3transfer.crt


requires_crt_pytest = pytest.mark.skipif(
    not HAS_CRT, reason="Test requires awscrt to be installed."
)


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
def mock_s3_crt_client():
    with mock.patch('s3transfer.crt.S3Client', spec=True) as mock_client:
        yield mock_client


@pytest.fixture
def mock_get_recommended_throughput_target_gbps():
    with mock.patch(
        's3transfer.crt.get_recommended_throughput_target_gbps'
    ) as mock_get_target_gbps:
        yield mock_get_target_gbps


class CustomFutureException(Exception):
    pass


@requires_crt_pytest
class TestCRTProcessLock:
    def test_acquire_crt_s3_process_lock(self, mock_crt_process_lock):
        lock = s3transfer.crt.acquire_crt_s3_process_lock('app-name')
        assert lock is s3transfer.crt.CRT_S3_PROCESS_LOCK
        assert lock is mock_crt_process_lock.return_value
        mock_crt_process_lock.assert_called_once_with('app-name')
        mock_crt_process_lock.return_value.acquire.assert_called_once_with()

    def test_unable_to_acquire_lock_returns_none(self, mock_crt_process_lock):
        mock_crt_process_lock.return_value.acquire.side_effect = RuntimeError
        assert s3transfer.crt.acquire_crt_s3_process_lock('app-name') is None
        assert s3transfer.crt.CRT_S3_PROCESS_LOCK is None
        mock_crt_process_lock.assert_called_once_with('app-name')
        mock_crt_process_lock.return_value.acquire.assert_called_once_with()

    def test_multiple_acquires_return_same_lock(self, mock_crt_process_lock):
        lock = s3transfer.crt.acquire_crt_s3_process_lock('app-name')
        assert s3transfer.crt.acquire_crt_s3_process_lock('app-name') is lock
        assert lock is s3transfer.crt.CRT_S3_PROCESS_LOCK

        # The process lock should have only been instantiated and acquired once
        mock_crt_process_lock.assert_called_once_with('app-name')
        mock_crt_process_lock.return_value.acquire.assert_called_once_with()


@requires_crt
class TestBotocoreCRTRequestSerializer(unittest.TestCase):
    def setUp(self):
        self.region = 'us-west-2'
        self.session = Session()
        self.session.set_config_variable('region', self.region)
        self.request_serializer = s3transfer.crt.BotocoreCRTRequestSerializer(
            self.session
        )
        self.bucket = "test_bucket"
        self.key = "test_key"
        self.files = FileCreator()
        self.filename = self.files.create_file('myfile', 'my content')
        self.expected_path = "/" + self.bucket + "/" + self.key
        self.expected_host = "s3.%s.amazonaws.com" % (self.region)

    def tearDown(self):
        self.files.remove_all()

    def test_upload_request(self):
        callargs = CallArgs(
            bucket=self.bucket,
            key=self.key,
            fileobj=self.filename,
            extra_args={},
            subscribers=[],
        )
        coordinator = s3transfer.crt.CRTTransferCoordinator()
        future = s3transfer.crt.CRTTransferFuture(
            s3transfer.crt.CRTTransferMeta(call_args=callargs), coordinator
        )
        crt_request = self.request_serializer.serialize_http_request(
            "put_object", future
        )
        self.assertEqual("PUT", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self.assertIsNone(crt_request.headers.get("Authorization"))

    def test_download_request(self):
        callargs = CallArgs(
            bucket=self.bucket,
            key=self.key,
            fileobj=self.filename,
            extra_args={},
            subscribers=[],
        )
        coordinator = s3transfer.crt.CRTTransferCoordinator()
        future = s3transfer.crt.CRTTransferFuture(
            s3transfer.crt.CRTTransferMeta(call_args=callargs), coordinator
        )
        crt_request = self.request_serializer.serialize_http_request(
            "get_object", future
        )
        self.assertEqual("GET", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self.assertIsNone(crt_request.headers.get("Authorization"))

    def test_delete_request(self):
        callargs = CallArgs(
            bucket=self.bucket, key=self.key, extra_args={}, subscribers=[]
        )
        coordinator = s3transfer.crt.CRTTransferCoordinator()
        future = s3transfer.crt.CRTTransferFuture(
            s3transfer.crt.CRTTransferMeta(call_args=callargs), coordinator
        )
        crt_request = self.request_serializer.serialize_http_request(
            "delete_object", future
        )
        self.assertEqual("DELETE", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self.assertIsNone(crt_request.headers.get("Authorization"))


@requires_crt_pytest
class TestBotocoreCRTCredentialsWrapper:
    @pytest.fixture
    def botocore_credentials(self):
        return Credentials(
            access_key='access_key', secret_key='secret_key', token='token'
        )

    def assert_crt_credentials(
        self,
        crt_credentials,
        expected_access_key='access_key',
        expected_secret_key='secret_key',
        expected_token='token',
    ):
        assert crt_credentials.access_key_id == expected_access_key
        assert crt_credentials.secret_access_key == expected_secret_key
        assert crt_credentials.session_token == expected_token

    def test_fetch_crt_credentials_successfully(self, botocore_credentials):
        wrapper = s3transfer.crt.BotocoreCRTCredentialsWrapper(
            botocore_credentials
        )
        crt_credentials = wrapper()
        self.assert_crt_credentials(crt_credentials)

    def test_wrapper_does_not_cache_frozen_credentials(self):
        mock_credentials = mock.Mock(Credentials)
        mock_credentials.get_frozen_credentials.side_effect = [
            ReadOnlyCredentials('access_key_1', 'secret_key_1', 'token_1'),
            ReadOnlyCredentials('access_key_2', 'secret_key_2', 'token_2'),
        ]
        wrapper = s3transfer.crt.BotocoreCRTCredentialsWrapper(
            mock_credentials
        )

        crt_credentials_1 = wrapper()
        self.assert_crt_credentials(
            crt_credentials_1,
            expected_access_key='access_key_1',
            expected_secret_key='secret_key_1',
            expected_token='token_1',
        )

        crt_credentials_2 = wrapper()
        self.assert_crt_credentials(
            crt_credentials_2,
            expected_access_key='access_key_2',
            expected_secret_key='secret_key_2',
            expected_token='token_2',
        )

        assert mock_credentials.get_frozen_credentials.call_count == 2

    def test_raises_error_when_resolved_credentials_is_none(self):
        wrapper = s3transfer.crt.BotocoreCRTCredentialsWrapper(None)
        with pytest.raises(NoCredentialsError):
            wrapper()

    def test_to_crt_credentials_provider(self, botocore_credentials):
        wrapper = s3transfer.crt.BotocoreCRTCredentialsWrapper(
            botocore_credentials
        )
        crt_credentials_provider = wrapper.to_crt_credentials_provider()
        assert isinstance(
            crt_credentials_provider, awscrt.auth.AwsCredentialsProvider
        )
        get_credentials_future = crt_credentials_provider.get_credentials()
        crt_credentials = get_credentials_future.result()
        self.assert_crt_credentials(crt_credentials)


@requires_crt
class TestCRTTransferFuture(unittest.TestCase):
    def setUp(self):
        self.mock_s3_request = mock.Mock(awscrt.s3.S3RequestType)
        self.mock_crt_future = mock.Mock(awscrt.s3.Future)
        self.mock_s3_request.finished_future = self.mock_crt_future
        self.coordinator = s3transfer.crt.CRTTransferCoordinator()
        self.coordinator.set_s3_request(self.mock_s3_request)
        self.future = s3transfer.crt.CRTTransferFuture(
            coordinator=self.coordinator
        )

    def test_set_exception(self):
        self.future.set_exception(CustomFutureException())
        with self.assertRaises(CustomFutureException):
            self.future.result()

    def test_set_exception_raises_error_when_not_done(self):
        self.mock_crt_future.done.return_value = False
        with self.assertRaises(TransferNotDoneError):
            self.future.set_exception(CustomFutureException())

    def test_set_exception_can_override_previous_exception(self):
        self.future.set_exception(Exception())
        self.future.set_exception(CustomFutureException())
        with self.assertRaises(CustomFutureException):
            self.future.result()


@requires_crt
class TestOnBodyFileObjWriter(unittest.TestCase):
    def test_call(self):
        fileobj = io.BytesIO()
        writer = s3transfer.crt.OnBodyFileObjWriter(fileobj)
        writer(chunk=b'content')
        self.assertEqual(fileobj.getvalue(), b'content')


@requires_crt_pytest
class TestCreateS3CRTClient:
    @pytest.mark.parametrize(
        'provided_bytes_per_sec,recommended_gbps,expected_gbps',
        [
            (None, 100.0, 100.0),
            (None, None, 10.0),
            # NOTE: create_s3_crt_client() accepts target throughput as bytes
            # per second and it is converted to gigabits per second for the
            # CRT client instantiation.
            (1_000_000_000, None, 8.0),
            (1_000_000_000, 100.0, 8.0),
        ],
    )
    def test_target_throughput(
        self,
        provided_bytes_per_sec,
        recommended_gbps,
        expected_gbps,
        mock_s3_crt_client,
        mock_get_recommended_throughput_target_gbps,
    ):
        mock_get_recommended_throughput_target_gbps.return_value = (
            recommended_gbps
        )
        s3transfer.crt.create_s3_crt_client(
            'us-west-2',
            target_throughput=provided_bytes_per_sec,
        )
        assert (
            mock_s3_crt_client.call_args[1]['throughput_target_gbps']
            == expected_gbps
        )
