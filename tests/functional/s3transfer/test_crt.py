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
        self.bytes_transferred = 0
        self.on_queued_future = None
        self.on_done_future = None

    def on_queued(self, future, **kwargs):
        self.on_queued_called = True
        self.on_queued_future = future

    def on_done(self, future, **kwargs):
        self.on_done_called = True
        self.on_done_future = future


@requires_crt
class TestCRTTransferManager(unittest.TestCase):
    def setUp(self):
        self.region = 'us-west-2'
        self.bucket = "test_bucket"
        self.key = "test_key"
        self.expected_content = b'my content'
        self.expected_download_content = b'new content'
        self.files = FileCreator()
        self.filename = self.files.create_file(
            'myfile', self.expected_content, mode='wb'
        )
        self.expected_path = "/" + self.bucket + "/" + self.key
        self.expected_host = "s3.%s.amazonaws.com" % (self.region)
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
        self.transfer_manager = s3transfer.crt.CRTTransferManager(
            crt_s3_client=self.s3_crt_client,
            crt_request_serializer=self.request_serializer,
        )
        self.record_subscriber = RecordingSubscriber()

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
        if expected_missing_headers is not None:
            header_names = [
                header[0].lower() for header in crt_http_request.headers
            ]
            for expected_missing_header in expected_missing_headers:
                self.assertNotIn(expected_missing_header.lower(), header_names)

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
            'algorithm': awscrt.s3.S3ChecksumAlgorithm.CRC32,
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
        on_done(error=None)

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
        self.s3_request.finished_future.set_exception(
            awscrt.exceptions.from_code(0)
        )
        self._invoke_done_callbacks()

    def test_cancel(self):
        self.s3_request.finished_future = Future()
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
            crt_s3_client=self.s3_crt_client,
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
