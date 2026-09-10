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
from concurrent.futures import Future

import pytest
from botocore.credentials import Credentials, ReadOnlyCredentials
from botocore.exceptions import (
    ClientError,
    InvalidConfigError,
    InvalidRegionError,
    NoCredentialsError,
)
from botocore.session import Session
from s3transfer.constants import GB
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


@requires_crt()
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
        self.expected_host = f"s3.{self.region}.amazonaws.com"

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

    def _create_crt_response_error(
        self, status_code, body, operation_name=None, headers=None
    ):
        if headers is None:
            headers = [
                ('x-amz-request-id', 'QSJHJJZR2EDYD4GQ'),
                (
                    'x-amz-id-2',
                    'xDbgdKdvYZTjgpOTzm7yNP2JPrOQl+eaQvUkFdOjdJoWkIC643fgHxdsHpUKvVAfjKf5F6otEYA=',
                ),
                ('Content-Type', 'application/xml'),
                ('Transfer-Encoding', 'chunked'),
                ('Date', 'Fri, 10 Nov 2023 23:22:47 GMT'),
                ('Server', 'AmazonS3'),
            ]
        return awscrt.s3.S3ResponseError(
            code=14343,
            name='AWS_ERROR_S3_INVALID_RESPONSE_STATUS',
            message='Invalid response status from request',
            status_code=status_code,
            headers=headers,
            body=body,
            operation_name=operation_name,
        )

    def _create_serializer_with_redirect_client(self):
        redirect_client = mock.Mock()
        client_factory = mock.Mock(return_value=redirect_client)
        serializer = s3transfer.crt.BotocoreCRTRequestSerializer(
            self.session,
            region_redirect_client_factory=client_factory,
        )
        return serializer, redirect_client, client_factory

    def test_translate_get_object_404(self):
        body = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n<Error>'
            b'<Code>NoSuchKey</Code>'
            b'<Message>The specified key does not exist.</Message>'
            b'<Key>obviously-no-such-key.txt</Key>'
            b'<RequestId>SBJ7ZQY03N1WDW9T</RequestId>'
            b'<HostId>SomeHostId</HostId></Error>'
        )
        crt_exc = self._create_crt_response_error(404, body, 'GetObject')
        boto_err = self.request_serializer.translate_crt_exception(crt_exc)
        self.assertIsInstance(
            boto_err, self.session.create_client('s3').exceptions.NoSuchKey
        )

    def test_translate_head_object_404(self):
        # There's no body in a HEAD response, so we can't map it to a modeled S3 exception.
        # But it should still map to a botocore ClientError
        body = None
        crt_exc = self._create_crt_response_error(
            404, body, operation_name='HeadObject'
        )
        boto_err = self.request_serializer.translate_crt_exception(crt_exc)
        self.assertIsInstance(boto_err, ClientError)

    def test_translate_unknown_operation_404(self):
        body = None
        crt_exc = self._create_crt_response_error(404, body)
        boto_err = self.request_serializer.translate_crt_exception(crt_exc)
        self.assertIsInstance(boto_err, ClientError)

    def test_cached_bucket_region_changes_serialized_endpoint(self):
        self.request_serializer.cache_bucket_region(
            self.bucket, 'eu-central-1'
        )
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

        self.assertEqual(
            crt_request.headers.get("host"),
            "s3.eu-central-1.amazonaws.com",
        )

    def test_redirect_region_does_not_create_fallback_client(self):
        serializer, redirect_client, client_factory = (
            self._create_serializer_with_redirect_client()
        )
        error = self._create_crt_response_error(
            301,
            None,
            operation_name='GetObject',
            headers=[('x-amz-bucket-region', 'eu-central-1')],
        )

        region = serializer.get_bucket_region(self.bucket, 'get_object', error)

        self.assertEqual(region, 'eu-central-1')
        client_factory.assert_not_called()
        redirect_client.head_bucket.assert_not_called()

    def test_redirect_region_creates_fallback_client(self):
        serializer, redirect_client, client_factory = (
            self._create_serializer_with_redirect_client()
        )
        redirect_client.head_bucket.return_value = {
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        }
        error = self._create_crt_response_error(
            301,
            b'<Error><Code>PermanentRedirect</Code></Error>',
            operation_name='DeleteObject',
        )

        region = serializer.get_bucket_region(
            self.bucket, 'delete_object', error
        )

        self.assertEqual(region, 'eu-central-1')
        client_factory.assert_called_once_with()
        redirect_client.head_bucket.assert_called_once_with(Bucket=self.bucket)

    def test_redirect_region_rejects_invalid_region(self):
        error = self._create_crt_response_error(
            301,
            b'<Error><Code>PermanentRedirect</Code></Error>',
            operation_name='GetObject',
            headers=[('x-amz-bucket-region', 'invalid region!')],
        )
        with self.assertRaises(InvalidRegionError):
            self.request_serializer.get_bucket_region(
                self.bucket, 'get_object', error
            )

    def test_redirect_region_ignores_arn_bucket(self):
        error = self._create_crt_response_error(
            301,
            b'<Error><Code>PermanentRedirect</Code></Error>',
            operation_name='GetObject',
            headers=[('x-amz-bucket-region', 'eu-central-1')],
        )
        bucket = 'arn:aws:s3:us-west-2:123456789012:accesspoint/myendpoint'

        region = self.request_serializer.get_bucket_region(
            bucket, 'get_object', error
        )

        self.assertIsNone(region)


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


@requires_crt()
class TestCRTTransferFuture(unittest.TestCase):
    def setUp(self):
        self.mock_s3_request = mock.Mock(awscrt.s3.S3RequestType)
        self.mock_crt_future = mock.Mock(awscrt.s3.Future)
        self.mock_s3_request.finished_future = self.mock_crt_future
        self.coordinator = s3transfer.crt.CRTTransferCoordinator(
            completion_future=self.mock_crt_future
        )
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


@requires_crt_pytest
class TestCRTTransferCoordinator:
    def setup_method(self):
        self.completion_future = Future()
        self.coordinator = s3transfer.crt.CRTTransferCoordinator(
            completion_future=self.completion_future
        )

    def create_s3_request(self):
        s3_request = mock.Mock(awscrt.s3.S3Request)
        s3_request.finished_future = Future()
        return s3_request

    def test_set_s3_request(self):
        s3_request = self.create_s3_request()
        self.coordinator.set_s3_request(s3_request)
        assert self.coordinator.s3_request is s3_request

    def test_original_request_cannot_replace_redirect(self):
        first_request = self.create_s3_request()
        second_request = self.create_s3_request()
        # The redirect started before the original request registered its
        # native request, so the original request must not become active.
        self.coordinator.set_s3_request(second_request, is_region_redirect=True)
        self.coordinator.set_s3_request(first_request)

        assert self.coordinator.s3_request is second_request

    def test_cancel_cancels_redirected_request(self):
        first_request = self.create_s3_request()
        second_request = self.create_s3_request()
        self.coordinator.set_s3_request(first_request)
        self.coordinator.set_s3_request(second_request, is_region_redirect=True)

        self.coordinator.cancel()

        second_request.cancel.assert_called_once_with()
        first_request.cancel.assert_not_called()

    def test_cancel_before_request_cancels_request(self):
        self.coordinator.cancel()
        s3_request = self.create_s3_request()

        self.coordinator.set_s3_request(s3_request)

        assert self.coordinator.cancelled
        s3_request.cancel.assert_called_once_with()

    def test_default_completion_future_can_complete_without_request(self):
        coordinator = s3transfer.crt.CRTTransferCoordinator()

        coordinator.complete()

        assert coordinator.done()
        assert coordinator.result() is None

    def test_complete_resolves_completion_future(self):
        self.coordinator.complete()
        assert self.completion_future.done()
        assert self.coordinator.result() is None

    def test_complete_with_error(self):
        self.coordinator.complete(CustomFutureException())
        with pytest.raises(CustomFutureException):
            self.coordinator.result()

    def test_complete_is_idempotent(self):
        self.coordinator.complete()
        self.coordinator.complete(CustomFutureException())
        assert self.coordinator.result() is None

    def test_not_done_until_completed(self):
        s3_request = self.create_s3_request()
        self.coordinator.set_s3_request(s3_request)
        # A native CRT request failing does not complete the transfer,
        # since it may still be redirected to another region.
        s3_request.finished_future.set_exception(CustomFutureException())

        assert not self.coordinator.done()

        self.coordinator.complete()
        assert self.coordinator.done()


@requires_crt_pytest
class TestS3RegionRedirectPolicy:
    def setup_method(self):
        self.bucket = 'mybucket'
        self.error = Exception('wrong region')
        self.serializer = mock.Mock(
            s3transfer.crt.BotocoreCRTRequestSerializer
        )
        self.serializer.get_cached_bucket_region.return_value = None
        self.serializer.get_bucket_region.return_value = 'eu-central-1'
        self.serializer.get_configured_region.return_value = 'us-west-2'
        self.policy = s3transfer.crt.CRTS3RegionRedirectPolicy(self.serializer)

    def is_error_redirect_candidate(self, **overrides):
        kwargs = {
            'bucket': self.bucket,
            'is_region_redirect': False,
            'bytes_transferred': 0,
            'cancelled': False,
            'is_replayable': True,
        }
        kwargs.update(overrides)
        return self.policy.is_error_redirect_candidate(**kwargs)

    def get_retry_region(self, request_region=None):
        return self.policy.get_retry_region(
            self.bucket, 'put_object', self.error, request_region
        )

    def test_returns_and_caches_discovered_region(self):
        assert self.get_retry_region() == 'eu-central-1'
        self.serializer.cache_bucket_region.assert_called_once_with(
            self.bucket, 'eu-central-1'
        )

    def test_returns_none_when_region_not_discovered(self):
        self.serializer.get_bucket_region.return_value = None
        assert self.get_retry_region() is None
        self.serializer.cache_bucket_region.assert_not_called()

    def test_returns_none_when_discovery_raises(self):
        self.serializer.get_bucket_region.side_effect = InvalidRegionError(
            region_name='not a region!'
        )
        assert self.get_retry_region() is None
        self.serializer.cache_bucket_region.assert_not_called()

    def test_returns_none_when_discovered_region_is_configured_region(self):
        # Retrying in the region the request already used would fail the same
        # way, and caching it would build a duplicate client for that region.
        self.serializer.get_bucket_region.return_value = 'us-west-2'
        assert self.get_retry_region() is None
        self.serializer.cache_bucket_region.assert_not_called()

    def test_returns_none_when_discovered_region_is_request_region(self):
        self.serializer.get_bucket_region.return_value = 'eu-west-1'
        assert self.get_retry_region(request_region='eu-west-1') is None
        self.serializer.cache_bucket_region.assert_not_called()

    def test_reuses_region_discovered_by_another_transfer(self):
        # A transfer that failed in the configured region does not need to
        # rediscover a region another transfer already cached.
        self.serializer.get_cached_bucket_region.return_value = 'eu-west-1'
        assert self.get_retry_region() == 'eu-west-1'
        self.serializer.get_bucket_region.assert_not_called()

    def test_rediscovers_region_when_cached_region_failed(self):
        # The failed request already used the cached region, so the cache is
        # stale and retrying there again would just fail the same way.
        self.serializer.get_cached_bucket_region.return_value = 'eu-west-1'
        assert self.get_retry_region(request_region='eu-west-1') == (
            'eu-central-1'
        )
        self.serializer.get_bucket_region.assert_called_once_with(
            self.bucket, 'put_object', self.error
        )

    def test_is_candidate_for_failed_replayable_transfer(self):
        assert self.is_error_redirect_candidate()

    def test_not_candidate_after_redirect(self):
        assert not self.is_error_redirect_candidate(is_region_redirect=True)

    def test_not_candidate_after_bytes_transferred(self):
        assert not self.is_error_redirect_candidate(bytes_transferred=1)

    def test_not_candidate_when_cancelled(self):
        assert not self.is_error_redirect_candidate(cancelled=True)

    def test_not_candidate_when_stream_is_not_replayable(self):
        assert not self.is_error_redirect_candidate(is_replayable=False)

    def test_not_candidate_for_s3express_bucket(self):
        assert not self.is_error_redirect_candidate(
            bucket='mybucket--usw2-az5--x-s3'
        )

    def test_candidate_checks_do_not_discover_region(self):
        self.is_error_redirect_candidate()
        self.serializer.get_bucket_region.assert_not_called()

    def test_get_cached_bucket_region(self):
        self.serializer.get_cached_bucket_region.return_value = 'eu-west-1'
        region = self.policy.get_cached_bucket_region(self.bucket)
        assert region == 'eu-west-1'


@requires_crt()
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

    def test_always_enables_s3express(self, mock_s3_crt_client):
        s3transfer.crt.create_s3_crt_client('us-west-2')
        assert mock_s3_crt_client.call_args[1]['enable_s3express'] is True

    def test_empty_verify_value_raises(self, mock_s3_crt_client):
        with pytest.raises(InvalidConfigError):
            s3transfer.crt.create_s3_crt_client('us-west-2', verify='')

    def test_whitespace_verify_value_raises(self, mock_s3_crt_client):
        with pytest.raises(InvalidConfigError):
            s3transfer.crt.create_s3_crt_client('us-west-2', verify='   ')

    def test_verify_false_disables_verification(self, mock_s3_crt_client):
        with (
            mock.patch('s3transfer.crt.TlsContextOptions') as mock_tls_options,
            mock.patch('s3transfer.crt.ClientTlsContext'),
        ):
            s3transfer.crt.create_s3_crt_client('us-west-2', verify=False)
        assert mock_tls_options.return_value.verify_peer is False

    @pytest.mark.parametrize(
        'fio_options,should_stream,disk_throughput,direct_io',
        [
            ({'should_stream': True}, True, 0.0, False),
            ({'disk_throughput_gbps': 8}, False, 8, False),
            ({'direct_io': True}, False, 0.0, True),
            (
                {'should_stream': True, 'disk_throughput_gbps': 8},
                True,
                8,
                False,
            ),
            ({'should_stream': True, 'direct_io': True}, True, 0.0, True),
            ({'disk_throughput_gbps': 8, 'direct_io': True}, False, 8, True),
            (
                {
                    'should_stream': True,
                    'disk_throughput_gbps': 8,
                    'direct_io': True,
                },
                True,
                8,
                True,
            ),
        ],
    )
    def test_fio_options(
        self,
        fio_options,
        should_stream,
        disk_throughput,
        direct_io,
        mock_s3_crt_client,
    ):
        params = {'fio_options': fio_options}
        s3transfer.crt.create_s3_crt_client(
            'us-west-2',
            **params,
        )
        assert (
            mock_s3_crt_client.call_args[1]['fio_options'].should_stream
            is should_stream
        )
        assert (
            mock_s3_crt_client.call_args[1]['fio_options'].disk_throughput_gbps
            == disk_throughput
        )
        assert (
            mock_s3_crt_client.call_args[1]['fio_options'].direct_io
            is direct_io
        )
