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
import fnmatch
import io
import threading
import time
from concurrent.futures import Future

from botocore.exceptions import ClientError
from botocore.session import Session
from s3transfer.subscribers import BaseSubscriber

from tests import (
    HAS_CRT,
    FileCreator,
    NonSeekableReader,
    NonSeekableWriter,
    mock,
    requires_crt,
    unittest,
)

if HAS_CRT:
    import awscrt
    import s3transfer.crt

# Bound on waiting for a transfer that completes from another thread, so a
# transfer that never completes fails the test instead of hanging it.
RESULT_TIMEOUT = 20


class submitThread(threading.Thread):
    def __init__(self, transfer_manager, futures, callargs):
        threading.Thread.__init__(self)
        self._transfer_manager = transfer_manager
        self._futures = futures
        self._callargs = callargs

    def run(self):
        self._futures.append(self._transfer_manager.download(*self._callargs))


class RecordingSubscriber(BaseSubscriber):
    def __init__(self):
        self.on_queued_called = False
        self.on_done_called = False
        self.on_queued_calls = 0
        self.on_done_calls = 0
        self.bytes_transferred = 0
        self.on_queued_future = None
        self.on_done_future = None

    def on_queued(self, future, **kwargs):
        self.on_queued_called = True
        self.on_queued_calls += 1
        self.on_queued_future = future

    def on_done(self, future, **kwargs):
        self.on_done_called = True
        self.on_done_calls += 1
        self.on_done_future = future


@requires_crt()
class TestCRTTransferManager(unittest.TestCase):
    def setUp(self):
        self.region = 'us-west-2'
        self.bucket = "test_bucket"
        self.s3express_bucket = 's3expressbucket--usw2-az5--x-s3'
        self.mrap_accesspoint = (
            'arn:aws:s3::123456789012:accesspoint/mfzwi23gnjvgw.mrap'
        )
        self.mrap_bucket = 'mfzwi23gnjvgw.mrap'
        self.key = "test_key"
        self.expected_content = b'my content'
        self.expected_download_content = b'new content'
        self.files = FileCreator()
        self.filename = self.files.create_file(
            'myfile', self.expected_content, mode='wb'
        )
        self.expected_path = "/" + self.bucket + "/" + self.key
        self.expected_host = f"s3.{self.region}.amazonaws.com"
        self.expected_s3express_host = f'{self.s3express_bucket}.s3express-usw2-az5.us-west-2.amazonaws.com'
        self.expected_s3express_path = f'/{self.key}'
        self.expected_mrap_host = (
            f'{self.mrap_bucket}.accesspoint.s3-global.amazonaws.com'
        )
        self.expected_mrap_path = f"/{self.key}"
        self.s3_request = mock.Mock(awscrt.s3.S3Request)
        self.s3_crt_client = mock.Mock(awscrt.s3.S3Client)
        self.s3_crt_client.make_request.side_effect = (
            self._simulate_make_request_side_effect
        )
        self.session = Session()
        self.session.set_config_variable('region', self.region)
        self.request_serializer = s3transfer.crt.BotocoreCRTRequestSerializer(
            self.session
        )
        self.crt_client_factory = mock.Mock(return_value=self.s3_crt_client)
        self.transfer_manager = s3transfer.crt.CRTTransferManager(
            crt_client_factory=self.crt_client_factory,
            crt_request_serializer=self.request_serializer,
        )
        self.record_subscriber = RecordingSubscriber()
        self.completion_threads = []

    def tearDown(self):
        self.files.remove_all()

    def _assert_expected_crt_http_request(
        self,
        crt_http_request,
        expected_http_method='GET',
        expected_host=None,
        expected_path=None,
        expected_body_content=None,
        expected_content_length=None,
        expected_missing_headers=None,
        expected_extra_headers=None,
    ):
        if expected_host is None:
            expected_host = self.expected_host
        if expected_path is None:
            expected_path = self.expected_path
        self.assertEqual(crt_http_request.method, expected_http_method)
        self.assertEqual(crt_http_request.headers.get("host"), expected_host)
        self.assertEqual(crt_http_request.path, expected_path)
        if expected_body_content is not None:
            # Note: The underlying CRT awscrt.io.InputStream does not expose
            # a public read method so we have to reach into the private,
            # underlying stream to determine the content. We should update
            # to use a public interface if a public interface is ever exposed.
            self.assertEqual(
                crt_http_request.body_stream._stream.read(),
                expected_body_content,
            )
        if expected_content_length is not None:
            self.assertEqual(
                crt_http_request.headers.get('Content-Length'),
                str(expected_content_length),
            )
        header_names = [
            header[0].lower() for header in crt_http_request.headers
        ]
        if expected_missing_headers is not None:
            for expected_missing_header in expected_missing_headers:
                self.assertNotIn(expected_missing_header.lower(), header_names)

    def _assert_expected_s3express_request(
        self, make_request_kwargs, expected_http_method='GET'
    ):
        self._assert_expected_crt_http_request(
            make_request_kwargs["request"],
            expected_host=self.expected_s3express_host,
            expected_path=self.expected_s3express_path,
            expected_http_method=expected_http_method,
        )
        self.assertIn('signing_config', make_request_kwargs)
        self.assertEqual(
            make_request_kwargs['signing_config'].algorithm,
            awscrt.auth.AwsSigningAlgorithm.V4_S3EXPRESS,
        )
        self.assertFalse(
            make_request_kwargs['signing_config'].use_double_uri_encode,
        )
        self.assertFalse(
            make_request_kwargs['signing_config'].should_normalize_uri_path,
        )

    def _assert_expected_mrap_request(
        self, make_request_kwargs, expected_http_method='GET'
    ):
        self._assert_expected_crt_http_request(
            make_request_kwargs["request"],
            expected_host=self.expected_mrap_host,
            expected_path=self.expected_mrap_path,
            expected_http_method=expected_http_method,
        )
        self.assertIn('signing_config', make_request_kwargs)
        self.assertEqual(
            make_request_kwargs['signing_config'].algorithm,
            awscrt.auth.AwsSigningAlgorithm.V4_ASYMMETRIC,
        )
        self.assertEqual(make_request_kwargs['signing_config'].region, "*")
        self.assertFalse(
            make_request_kwargs['signing_config'].use_double_uri_encode,
        )
        self.assertFalse(
            make_request_kwargs['signing_config'].should_normalize_uri_path,
        )

    def _assert_subscribers_called(self, expected_future=None):
        self.assertTrue(self.record_subscriber.on_queued_called)
        self.assertTrue(self.record_subscriber.on_done_called)
        if expected_future:
            self.assertIs(
                self.record_subscriber.on_queued_future, expected_future
            )
            self.assertIs(
                self.record_subscriber.on_done_future, expected_future
            )

    def _get_expected_upload_checksum_config(self, **overrides):
        checksum_config_kwargs = {
            'algorithm': awscrt.s3.S3ChecksumAlgorithm.CRC64NVME,
            'location': awscrt.s3.S3ChecksumLocation.TRAILER,
        }
        checksum_config_kwargs.update(overrides)
        return awscrt.s3.S3ChecksumConfig(**checksum_config_kwargs)

    def _get_expected_download_checksum_config(self, **overrides):
        checksum_config_kwargs = {
            'validate_response': True,
        }
        checksum_config_kwargs.update(overrides)
        return awscrt.s3.S3ChecksumConfig(**checksum_config_kwargs)

    def _invoke_done_callbacks(self, **kwargs):
        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        on_done = callargs_kwargs["on_done"]
        on_done(error=kwargs.get('error'))

    def _simulate_file_download(self, recv_filepath):
        self.files.create_file(
            recv_filepath, self.expected_download_content, mode='wb'
        )

    def _simulate_on_body_download(self, on_body_callback):
        on_body_callback(chunk=self.expected_download_content, offset=0)

    def _simulate_make_request_side_effect(self, **kwargs):
        if kwargs.get('recv_filepath'):
            self._simulate_file_download(kwargs['recv_filepath'])
        if kwargs.get('on_body'):
            self._simulate_on_body_download(kwargs['on_body'])
        self._invoke_done_callbacks()
        return self.s3_request

    def _create_redirect_error(self, region=None):
        headers = [] if region is None else [('x-amz-bucket-region', region)]
        return awscrt.s3.S3ResponseError(
            code=14343,
            name='AWS_ERROR_S3_INVALID_RESPONSE_STATUS',
            message='Invalid response status from request',
            status_code=301,
            headers=headers,
            body=b'<Error><Code>PermanentRedirect</Code></Error>',
            operation_name='PutObject',
        )

    def _create_redirect_transfer_manager(
        self, initial_client, client_factory
    ):
        def create_client(region=None):
            if region is None:
                return initial_client
            return client_factory(region)

        return s3transfer.crt.CRTTransferManager(
            crt_client_factory=create_client,
            crt_request_serializer=self.request_serializer,
        )

    def _create_redirecting_transfer_manager(
        self, initial_make_request, redirected_make_request=None
    ):
        """Create a manager whose initial region and redirected region differ.

        The clients for both regions and the factory that creates the
        redirected one are recorded as ``self.initial_client``,
        ``self.redirected_client``, and ``self.redirected_client_factory``.
        """
        self.initial_client = mock.Mock(awscrt.s3.S3Client)
        self.initial_client.make_request.side_effect = initial_make_request
        self.redirected_client = mock.Mock(awscrt.s3.S3Client)
        self.redirected_client.make_request.side_effect = (
            redirected_make_request or self._succeed_make_request
        )
        self.redirected_client_factory = mock.Mock(
            return_value=self.redirected_client
        )
        return self._create_redirect_transfer_manager(
            self.initial_client, self.redirected_client_factory
        )

    def _upload_and_wait(self, transfer_manager, subscribers=None):
        future = transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {},
            subscribers if subscribers is not None else [],
        )
        future.result(timeout=RESULT_TIMEOUT)
        return future

    def _fail_make_request(self, error):
        def make_request(**kwargs):
            kwargs['on_done'](error=error)
            return mock.Mock(awscrt.s3.S3Request)

        return make_request

    def _fail_make_request_on_other_thread(self, error):
        """Fail a request from another thread, like a CRT completion thread.

        The thread the request completed on is recorded in
        ``self.completion_threads``.
        """

        def complete_request(on_done):
            self.completion_threads.append(threading.get_ident())
            on_done(error=error)

        def make_request(**kwargs):
            thread = threading.Thread(
                target=complete_request, args=(kwargs['on_done'],)
            )
            self.addCleanup(thread.join)
            thread.start()
            return mock.Mock(awscrt.s3.S3Request)

        return make_request

    def _succeed_make_request(self, **kwargs):
        kwargs['on_done'](error=None)
        return mock.Mock(awscrt.s3.S3Request)

    def test_upload(self):
        future = self.transfer_manager.upload(
            self.filename, self.bucket, self.key, {}, [self.record_subscriber]
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                'send_filepath': self.filename,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'checksum_config': self._get_expected_upload_checksum_config(),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='PUT',
            expected_content_length=len(self.expected_content),
            expected_missing_headers=['Content-MD5'],
        )
        self._assert_subscribers_called(future)

    def test_upload_redirects_and_reuses_cached_region(self):
        redirected_region = 'eu-central-1'
        transfer_manager = self._create_redirecting_transfer_manager(
            self._fail_make_request(
                self._create_redirect_error(redirected_region)
            )
        )

        first_subscriber = RecordingSubscriber()
        first_future = transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {},
            [first_subscriber],
        )
        first_future.result()

        self.assertEqual(self.initial_client.make_request.call_count, 1)
        self.assertEqual(self.redirected_client.make_request.call_count, 1)
        self.redirected_client_factory.assert_called_once_with(
            redirected_region
        )
        initial_call = self.initial_client.make_request.call_args_list[
            0
        ].kwargs
        redirected_call = self.redirected_client.make_request.call_args_list[
            0
        ].kwargs
        self.assertEqual(
            initial_call['request'].headers.get('host'),
            f's3.{self.region}.amazonaws.com',
        )
        self.assertEqual(
            redirected_call['request'].headers.get('host'),
            f's3.{redirected_region}.amazonaws.com',
        )
        # The redirect is internal to one logical transfer, so subscribers
        # only see it once.
        self.assertEqual(first_subscriber.on_queued_calls, 1)
        self.assertEqual(first_subscriber.on_done_calls, 1)

        second_subscriber = RecordingSubscriber()
        second_future = transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {},
            [second_subscriber],
        )
        second_future.result()

        self.assertEqual(self.initial_client.make_request.call_count, 1)
        self.assertEqual(self.redirected_client.make_request.call_count, 2)
        self.redirected_client_factory.assert_called_once_with(
            redirected_region
        )
        self.assertEqual(second_subscriber.on_queued_calls, 1)
        self.assertEqual(second_subscriber.on_done_calls, 1)

    def test_upload_redirect_restores_seekable_stream_position(self):
        redirected_region = 'eu-central-1'
        redirect_error = self._create_redirect_error(redirected_region)
        attempt_bodies = []

        def consume_body_and_finish(error):
            def make_request(**kwargs):
                attempt_bodies.append(
                    kwargs['request'].body_stream._stream.read()
                )
                kwargs['on_done'](error=error)
                return mock.Mock(awscrt.s3.S3Request)

            return make_request

        transfer_manager = self._create_redirecting_transfer_manager(
            consume_body_and_finish(redirect_error),
            consume_body_and_finish(None),
        )

        future = transfer_manager.upload(
            io.BytesIO(self.expected_content), self.bucket, self.key, {}, []
        )
        future.result()

        self.assertEqual(
            attempt_bodies, [self.expected_content, self.expected_content]
        )

    def test_successful_upload_does_not_consult_redirect_policy(self):
        # A transfer that did not fail is never a redirect candidate.
        with mock.patch.object(
            self.transfer_manager._region_redirect_policy,
            'is_error_redirect_candidate',
        ) as is_error_redirect_candidate:
            future = self.transfer_manager.upload(
                self.filename, self.bucket, self.key, {}, []
            )
            future.result(timeout=RESULT_TIMEOUT)

        is_error_redirect_candidate.assert_not_called()

    def test_upload_does_not_redirect_to_configured_region(self):
        # A redirect naming the region the request already used, e.g. from an
        # accelerate or dualstack endpoint, is not worth retrying.
        transfer_manager = self._create_redirecting_transfer_manager(
            self._fail_make_request(self._create_redirect_error(self.region))
        )

        with self.assertRaises(ClientError):
            self._upload_and_wait(transfer_manager)

        # No duplicate client for a region the transfer already used, and no
        # retry that would just fail again.
        self.redirected_client_factory.assert_not_called()
        self.assertEqual(self.initial_client.make_request.call_count, 1)

    def test_upload_does_not_redirect_nonseekable_stream(self):
        transfer_manager = self._create_redirecting_transfer_manager(
            self._fail_make_request(
                self._create_redirect_error('eu-central-1')
            )
        )

        future = transfer_manager.upload(
            NonSeekableReader(self.expected_content),
            self.bucket,
            self.key,
            {},
            [],
        )

        with self.assertRaises(ClientError):
            future.result()
        self.redirected_client_factory.assert_not_called()
        self.redirected_client.make_request.assert_not_called()

    def test_upload_does_not_redirect_after_progress(self):
        redirect_error = self._create_redirect_error('eu-central-1')

        def fail_after_progress(**kwargs):
            kwargs['on_progress'](1)
            kwargs['on_done'](error=redirect_error)
            return mock.Mock(awscrt.s3.S3Request)

        transfer_manager = self._create_redirecting_transfer_manager(
            fail_after_progress
        )

        with self.assertRaises(ClientError):
            self._upload_and_wait(transfer_manager)
        self.redirected_client_factory.assert_not_called()
        self.redirected_client.make_request.assert_not_called()

    def test_concurrent_redirects_discover_region_once(self):
        # Transfers redirected at the same time share one region lookup, and
        # each request is sent on a client for the region it was signed for.
        redirected_region = 'eu-central-1'
        redirect_error = self._create_redirect_error(redirected_region)
        release = threading.Event()

        def fail_when_released(**kwargs):
            def complete_request():
                release.wait(RESULT_TIMEOUT)
                kwargs['on_done'](error=redirect_error)

            thread = threading.Thread(target=complete_request)
            self.addCleanup(thread.join)
            thread.start()
            return mock.Mock(awscrt.s3.S3Request)

        transfer_manager = self._create_redirecting_transfer_manager(
            fail_when_released
        )

        with mock.patch.object(
            self.request_serializer,
            'get_bucket_region',
            wraps=self.request_serializer.get_bucket_region,
        ) as discover_region:
            # Both transfers are in flight before either has a region to
            # reuse, then both fail with a redirect at once.
            futures = [
                transfer_manager.upload(
                    self.filename, self.bucket, f'{self.key}-{i}', {}, []
                )
                for i in range(2)
            ]
            release.set()
            for future in futures:
                future.result(timeout=RESULT_TIMEOUT)

        # The region is discovered once and reused, rather than every
        # redirected transfer paying for its own lookup.
        self.assertEqual(discover_region.call_count, 1)
        self.assertEqual(self.redirected_client.make_request.call_count, 2)
        # Sending a request signed for one region on a client configured for
        # another fails with SignatureDoesNotMatch, so every request has to
        # agree with the client it was sent on.
        for call in self.initial_client.make_request.call_args_list:
            self.assertEqual(
                call.kwargs['request'].headers.get('host'),
                self.expected_host,
            )
        for call in self.redirected_client.make_request.call_args_list:
            self.assertEqual(
                call.kwargs['request'].headers.get('host'),
                f's3.{redirected_region}.amazonaws.com',
            )

    def test_upload_redirect_does_not_block_completion_thread(self):
        # Redirecting must not run on the CRT thread that reported the
        # failure, since it can block on the network.
        redirect_threads = []

        def succeed_and_record_thread(**kwargs):
            redirect_threads.append(threading.get_ident())
            return self._succeed_make_request(**kwargs)

        transfer_manager = self._create_redirecting_transfer_manager(
            self._fail_make_request_on_other_thread(
                self._create_redirect_error('eu-central-1')
            ),
            succeed_and_record_thread,
        )

        self._upload_and_wait(transfer_manager)

        # Discovering the region and serializing the retry can both block on
        # the network, so they must not run on the thread the CRT completed
        # the original request on.
        self.assertEqual(len(redirect_threads), 1)
        self.assertEqual(len(self.completion_threads), 1)
        self.assertNotEqual(redirect_threads[0], self.completion_threads[0])

    def test_cancel_cancels_retry_started_before_original_request_returned(
        self,
    ):
        # A redirect can start before the original request registers, so a
        # cancel has to reach the retry rather than the finished request.
        redirect_error = self._create_redirect_error('eu-central-1')
        original_request = mock.Mock(awscrt.s3.S3Request)
        retry_request = mock.Mock(awscrt.s3.S3Request)
        retry_started = threading.Event()
        retry_callbacks = {}

        def start_retry(**kwargs):
            # Leave the retry in flight so it is the request a cancel has to
            # reach.
            retry_callbacks['on_done'] = kwargs['on_done']
            retry_started.set()
            return retry_request

        def redirect_before_returning(**kwargs):
            kwargs['on_done'](error=redirect_error)
            # The redirect is handled on another thread, so wait for the retry
            # to register before this request reports its own native request.
            self.assertTrue(retry_started.wait(RESULT_TIMEOUT))
            return original_request

        transfer_manager = self._create_redirecting_transfer_manager(
            redirect_before_returning, start_retry
        )

        future = transfer_manager.upload(
            self.filename, self.bucket, self.key, {}, []
        )
        future.cancel()

        # The original request completed and was replaced by the retry, so
        # cancelling must not target the request that already finished.
        retry_request.cancel.assert_called_once_with()
        original_request.cancel.assert_not_called()

        retry_callbacks['on_done'](error=None)
        future.result(timeout=RESULT_TIMEOUT)

    def test_upload_completes_when_redirect_decision_raises(self):
        # A redirect decision that raises must still finish the transfer.
        # The CRT invokes on_done from one of its own threads, so raising
        # there strands the transfer instead of failing make_request().
        transfer_manager = self._create_redirecting_transfer_manager(
            self._fail_make_request_on_other_thread(
                self._create_redirect_error('eu-central-1')
            )
        )
        with mock.patch.object(
            transfer_manager._region_redirect_policy,
            'get_retry_region',
            side_effect=RuntimeError('Unexpected redirect failure'),
        ):
            # The transfer must still finish, and surface the error from the
            # transfer itself instead of the one from the redirect decision.
            with self.assertRaises(ClientError):
                self._upload_and_wait(transfer_manager)
            transfer_manager.shutdown()

        self.redirected_client_factory.assert_not_called()

    def test_upload_from_seekable_stream(self):
        with open(self.filename, 'rb') as f:
            future = self.transfer_manager.upload(
                f, self.bucket, self.key, {}, [self.record_subscriber]
            )
            future.result()

            callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
            self.assertEqual(
                callargs_kwargs,
                {
                    'request': mock.ANY,
                    'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                    'send_filepath': None,
                    'on_progress': mock.ANY,
                    'on_done': mock.ANY,
                    'checksum_config': self._get_expected_upload_checksum_config(),
                },
            )
            self._assert_expected_crt_http_request(
                callargs_kwargs["request"],
                expected_http_method='PUT',
                expected_body_content=self.expected_content,
                expected_content_length=len(self.expected_content),
                expected_missing_headers=['Content-MD5'],
            )
            self._assert_subscribers_called(future)

    def test_upload_from_nonseekable_stream(self):
        nonseekable_stream = NonSeekableReader(self.expected_content)
        future = self.transfer_manager.upload(
            nonseekable_stream,
            self.bucket,
            self.key,
            {},
            [self.record_subscriber],
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                'send_filepath': None,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'checksum_config': self._get_expected_upload_checksum_config(),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='PUT',
            expected_body_content=self.expected_content,
            expected_missing_headers=[
                'Content-MD5',
                'Content-Length',
                'Transfer-Encoding',
            ],
        )
        self._assert_subscribers_called(future)

    def test_upload_override_checksum_algorithm(self):
        future = self.transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {'ChecksumAlgorithm': 'CRC32C'},
            [self.record_subscriber],
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                'send_filepath': self.filename,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'checksum_config': self._get_expected_upload_checksum_config(
                    algorithm=awscrt.s3.S3ChecksumAlgorithm.CRC32C
                ),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='PUT',
            expected_content_length=len(self.expected_content),
            expected_missing_headers=[
                'Content-MD5',
                'x-amz-sdk-checksum-algorithm',
                'X-Amz-Trailer',
            ],
        )
        self._assert_subscribers_called(future)

    def test_upload_override_checksum_algorithm_accepts_lowercase(self):
        future = self.transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {'ChecksumAlgorithm': 'crc32c'},
            [self.record_subscriber],
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                'send_filepath': self.filename,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'checksum_config': self._get_expected_upload_checksum_config(
                    algorithm=awscrt.s3.S3ChecksumAlgorithm.CRC32C
                ),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='PUT',
            expected_content_length=len(self.expected_content),
            expected_missing_headers=[
                'Content-MD5',
                'x-amz-sdk-checksum-algorithm',
                'X-Amz-Trailer',
            ],
        )
        self._assert_subscribers_called(future)

    def test_upload_throws_error_for_unsupported_checksum(self):
        with self.assertRaisesRegex(
            ValueError, 'ChecksumAlgorithm: UNSUPPORTED not supported'
        ):
            self.transfer_manager.upload(
                self.filename,
                self.bucket,
                self.key,
                {'ChecksumAlgorithm': 'UNSUPPORTED'},
                [self.record_subscriber],
            )

    def test_upload_with_s3express(self):
        future = self.transfer_manager.upload(
            self.filename,
            self.s3express_bucket,
            self.key,
            {},
            [self.record_subscriber],
        )
        future.result()
        self._assert_expected_s3express_request(
            self.s3_crt_client.make_request.call_args[1],
            expected_http_method='PUT',
        )

    def test_upload_with_mrap(self):
        future = self.transfer_manager.upload(
            self.filename,
            self.mrap_accesspoint,
            self.key,
            {},
            [self.record_subscriber],
        )
        future.result()
        self._assert_expected_mrap_request(
            self.s3_crt_client.make_request.call_args[1],
            expected_http_method='PUT',
        )

    def test_upload_with_full_checksum(self):
        future = self.transfer_manager.upload(
            self.filename,
            self.bucket,
            self.key,
            {"ChecksumCRC32": "abc123"},
            [self.record_subscriber],
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.PUT_OBJECT,
                'send_filepath': self.filename,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'checksum_config': None,
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='PUT',
            expected_content_length=len(self.expected_content),
            expected_missing_headers=['Content-MD5'],
            expected_extra_headers={"x-amz-checksum-crc32": "abc123"},
        )
        self._assert_subscribers_called(future)

    def test_download(self):
        future = self.transfer_manager.download(
            self.bucket, self.key, self.filename, {}, [self.record_subscriber]
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.GET_OBJECT,
                'recv_filepath': mock.ANY,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'on_body': None,
                'checksum_config': self._get_expected_download_checksum_config(),
            },
        )
        # the recv_filepath will be set to a temporary file path with some
        # random suffix
        self.assertTrue(
            fnmatch.fnmatch(
                callargs_kwargs["recv_filepath"],
                f'{self.filename}.*',
            )
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='GET',
            expected_content_length=0,
        )
        self._assert_subscribers_called(future)
        with open(self.filename, 'rb') as f:
            # Check the fake response overwrites the file because of download
            self.assertEqual(f.read(), self.expected_download_content)

    def test_download_to_seekable_stream(self):
        with open(self.filename, 'wb') as f:
            future = self.transfer_manager.download(
                self.bucket, self.key, f, {}, [self.record_subscriber]
            )
            future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.GET_OBJECT,
                'recv_filepath': None,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'on_body': mock.ANY,
                'checksum_config': self._get_expected_download_checksum_config(),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='GET',
            expected_content_length=0,
        )
        self._assert_subscribers_called(future)
        with open(self.filename, 'rb') as f:
            # Check the fake response overwrites the file because of download
            self.assertEqual(f.read(), self.expected_download_content)

    def test_download_to_nonseekable_stream(self):
        underlying_stream = io.BytesIO()
        nonseekable_stream = NonSeekableWriter(underlying_stream)
        future = self.transfer_manager.download(
            self.bucket,
            self.key,
            nonseekable_stream,
            {},
            [self.record_subscriber],
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.GET_OBJECT,
                'recv_filepath': None,
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
                'on_body': mock.ANY,
                'checksum_config': self._get_expected_download_checksum_config(),
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='GET',
            expected_content_length=0,
        )
        self._assert_subscribers_called(future)
        self.assertEqual(
            underlying_stream.getvalue(), self.expected_download_content
        )

    def test_download_with_s3express(self):
        future = self.transfer_manager.download(
            self.s3express_bucket,
            self.key,
            self.filename,
            {},
            [self.record_subscriber],
        )
        future.result()
        self._assert_expected_s3express_request(
            self.s3_crt_client.make_request.call_args[1],
            expected_http_method='GET',
        )

    def test_download_with_mrap(self):
        future = self.transfer_manager.download(
            self.mrap_accesspoint,
            self.key,
            self.filename,
            {},
            [self.record_subscriber],
        )
        future.result()
        self._assert_expected_mrap_request(
            self.s3_crt_client.make_request.call_args[1],
            expected_http_method='GET',
        )

    def test_delete(self):
        future = self.transfer_manager.delete(
            self.bucket, self.key, {}, [self.record_subscriber]
        )
        future.result()

        callargs_kwargs = self.s3_crt_client.make_request.call_args[1]
        self.assertEqual(
            callargs_kwargs,
            {
                'request': mock.ANY,
                'type': awscrt.s3.S3RequestType.DEFAULT,
                'operation_name': "DeleteObject",
                'on_progress': mock.ANY,
                'on_done': mock.ANY,
            },
        )
        self._assert_expected_crt_http_request(
            callargs_kwargs["request"],
            expected_http_method='DELETE',
            expected_content_length=0,
        )
        self._assert_subscribers_called(future)

    def test_delete_with_s3express(self):
        future = self.transfer_manager.delete(
            self.s3express_bucket, self.key, {}, [self.record_subscriber]
        )
        future.result()
        self._assert_expected_s3express_request(
            self.s3_crt_client.make_request.call_args[1],
            expected_http_method='DELETE',
        )

    def test_blocks_when_max_requests_processes_reached(self):
        self.s3_crt_client.make_request.return_value = self.s3_request
        # We simulate blocking by not invoking the on_done callbacks for
        # all of the requests we send. The default side effect invokes all
        # callbacks so we need to unset the side effect to avoid on_done from
        # being called in the child threads.
        self.s3_crt_client.make_request.side_effect = None
        futures = []
        callargs = (self.bucket, self.key, self.filename, {}, [])
        max_request_processes = 128  # the hard coded max processes
        all_concurrent = max_request_processes + 1
        threads = []
        for i in range(0, all_concurrent):
            thread = submitThread(self.transfer_manager, futures, callargs)
            thread.start()
            threads.append(thread)
        # Sleep until the expected max requests has been reached
        while len(futures) < max_request_processes:
            time.sleep(0.05)
        self.assertLessEqual(
            self.s3_crt_client.make_request.call_count, max_request_processes
        )
        # Release lock
        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        on_done = callargs_kwargs["on_done"]
        on_done(error=None)
        for thread in threads:
            thread.join()
        self.assertEqual(
            self.s3_crt_client.make_request.call_count, all_concurrent
        )

    def _cancel_function(self):
        self.cancel_called = True
        error = awscrt.exceptions.from_code(0)
        self.s3_request.finished_future.set_exception(error)
        self._invoke_done_callbacks(error=error)

    def test_cancel(self):
        self.s3_request.finished_future = Future()
        self.s3_crt_client.make_request.side_effect = None
        self.s3_crt_client.make_request.return_value = self.s3_request
        self.cancel_called = False
        self.s3_request.cancel = self._cancel_function
        try:
            with self.transfer_manager:
                future = self.transfer_manager.upload(
                    self.filename, self.bucket, self.key, {}, []
                )
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass

        with self.assertRaises(awscrt.exceptions.AwsCrtError):
            future.result()
        self.assertTrue(self.cancel_called)

    def test_serializer_error_handling(self):
        class SerializationException(Exception):
            pass

        class ExceptionRaisingSerializer(
            s3transfer.crt.BaseCRTRequestSerializer
        ):
            def serialize_http_request(self, transfer_type, future):
                raise SerializationException()

        not_impl_serializer = ExceptionRaisingSerializer()
        transfer_manager = s3transfer.crt.CRTTransferManager(
            crt_client_factory=self.crt_client_factory,
            crt_request_serializer=not_impl_serializer,
        )
        future = transfer_manager.upload(
            self.filename, self.bucket, self.key, {}, []
        )

        with self.assertRaises(SerializationException):
            future.result()

    def test_crt_s3_client_error_handling(self):
        self.s3_crt_client.make_request.side_effect = (
            awscrt.exceptions.from_code(0)
        )
        future = self.transfer_manager.upload(
            self.filename, self.bucket, self.key, {}, []
        )
        with self.assertRaises(awscrt.exceptions.AwsCrtError):
            future.result()
