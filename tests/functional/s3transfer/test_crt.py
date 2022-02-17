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
import threading
import time
from concurrent.futures import Future

from botocore.session import Session

from s3transfer.subscribers import BaseSubscriber
from tests import HAS_CRT, FileCreator, mock, requires_crt, unittest

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
        self.files = FileCreator()
        self.filename = self.files.create_file('myfile', 'my content')
        self.expected_path = "/" + self.bucket + "/" + self.key
        self.expected_host = "s3.%s.amazonaws.com" % (self.region)
        self.s3_request = mock.Mock(awscrt.s3.S3Request)
        self.s3_crt_client = mock.Mock(awscrt.s3.S3Client)
        self.s3_crt_client.make_request.return_value = self.s3_request
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

    def _invoke_done_callbacks(self, **kwargs):
        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        on_done = callargs_kwargs["on_done"]
        on_done(error=None)

    def _simulate_file_download(self, recv_filepath):
        self.files.create_file(recv_filepath, "fake response")

    def _simulate_make_request_side_effect(self, **kwargs):
        if kwargs.get('recv_filepath'):
            self._simulate_file_download(kwargs['recv_filepath'])
        self._invoke_done_callbacks()
        return mock.DEFAULT

    def test_upload(self):
        self.s3_crt_client.make_request.side_effect = (
            self._simulate_make_request_side_effect
        )
        future = self.transfer_manager.upload(
            self.filename, self.bucket, self.key, {}, [self.record_subscriber]
        )
        future.result()

        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        self.assertEqual(callargs_kwargs["send_filepath"], self.filename)
        self.assertIsNone(callargs_kwargs["recv_filepath"])
        self.assertEqual(
            callargs_kwargs["type"], awscrt.s3.S3RequestType.PUT_OBJECT
        )
        crt_request = callargs_kwargs["request"]
        self.assertEqual("PUT", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self._assert_subscribers_called(future)

    def test_download(self):
        self.s3_crt_client.make_request.side_effect = (
            self._simulate_make_request_side_effect
        )
        future = self.transfer_manager.download(
            self.bucket, self.key, self.filename, {}, [self.record_subscriber]
        )
        future.result()

        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        # the recv_filepath will be set to a temporary file path with some
        # random suffix
        self.assertTrue(
            fnmatch.fnmatch(
                callargs_kwargs["recv_filepath"],
                f'{self.filename}.*',
            )
        )
        self.assertIsNone(callargs_kwargs["send_filepath"])
        self.assertEqual(
            callargs_kwargs["type"], awscrt.s3.S3RequestType.GET_OBJECT
        )
        crt_request = callargs_kwargs["request"]
        self.assertEqual("GET", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self._assert_subscribers_called(future)
        with open(self.filename, 'rb') as f:
            # Check the fake response overwrites the file because of download
            self.assertEqual(f.read(), b'fake response')

    def test_delete(self):
        self.s3_crt_client.make_request.side_effect = (
            self._simulate_make_request_side_effect
        )
        future = self.transfer_manager.delete(
            self.bucket, self.key, {}, [self.record_subscriber]
        )
        future.result()

        callargs = self.s3_crt_client.make_request.call_args
        callargs_kwargs = callargs[1]
        self.assertIsNone(callargs_kwargs["send_filepath"])
        self.assertIsNone(callargs_kwargs["recv_filepath"])
        self.assertEqual(
            callargs_kwargs["type"], awscrt.s3.S3RequestType.DEFAULT
        )
        crt_request = callargs_kwargs["request"]
        self.assertEqual("DELETE", crt_request.method)
        self.assertEqual(self.expected_path, crt_request.path)
        self.assertEqual(self.expected_host, crt_request.headers.get("host"))
        self._assert_subscribers_called(future)

    def test_blocks_when_max_requests_processes_reached(self):
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
