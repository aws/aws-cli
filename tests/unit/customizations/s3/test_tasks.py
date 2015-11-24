# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
import random
import threading
import mock
import socket
import os
import tempfile
import shutil
from six.moves import queue

from botocore.exceptions import IncompleteReadError
from botocore.vendored.requests.packages.urllib3.exceptions import \
    ReadTimeoutError

from awscli.customizations.s3 import transferconfig
from awscli.customizations.s3.tasks import CreateLocalFileTask
from awscli.customizations.s3.tasks import CompleteDownloadTask
from awscli.customizations.s3.tasks import DownloadPartTask
from awscli.customizations.s3.tasks import MultipartUploadContext
from awscli.customizations.s3.tasks import MultipartDownloadContext
from awscli.customizations.s3.tasks import UploadCancelledError
from awscli.customizations.s3.tasks import print_operation
from awscli.customizations.s3.tasks import RetriesExeededError
from awscli.customizations.s3.executor import ShutdownThreadRequest
from awscli.customizations.s3.utils import StablePriorityQueue
from awscli.testutils import skip_if_windows


class TestMultipartUploadContext(unittest.TestCase):

    def setUp(self):
        self.context = MultipartUploadContext(expected_parts=1)
        self.calls = []
        self.threads = []
        self.call_lock = threading.Lock()
        self.caught_exception = None

    def tearDown(self):
        self.join_threads()

    def join_threads(self):
        for thread in self.threads:
            thread.join()

    def upload_part(self, part_number):
        # This simulates what a thread would do if it wanted to upload
        # a part.  First it would wait for the upload id.
        try:
            upload_id = self.context.wait_for_upload_id()
        except Exception as e:
            self.caught_exception = e
            return
        with self.call_lock:
            self.calls.append(('upload_part', part_number, upload_id))
        # Then it would call UploadPart here.
        # Then it would announce that it's finished with a part.
        self.context.announce_finished_part(etag='etag%s' % part_number,
                                            part_number=part_number)

    def complete_upload(self):
        try:
            upload_id = self.context.wait_for_upload_id()
            parts = self.context.wait_for_parts_to_finish()
        except Exception as e:
            self.caught_exception = e
            return
        with self.call_lock:
            self.calls.append(('complete_upload', upload_id, parts))
            self.context.announce_completed()

    def wait_for_upload_complete(self):
        try:
            self.context.wait_for_completion()
        except Exception as e:
            self.caught_exception = e
            return
        with self.call_lock:
            self.calls.append(('arbitrary_post_complete_operation',))

    def create_upload(self, upload_id):
        with self.call_lock:
            self.calls.append(('create_multipart_upload', 'my_upload_id'))
        self.context.announce_upload_id(upload_id)

    def start_thread(self, thread):
        thread.start()
        self.threads.append(thread)

    def test_normal_non_threaded(self):
        # The context object is pretty straightforward.
        # This shows the non threaded usage of this object.
        context = MultipartUploadContext(expected_parts=3)
        # First you can announce an upload id.
        context.announce_upload_id('my_upload_id')
        # Then a thread that was waiting on the id would be notified.
        self.assertEqual(context.wait_for_upload_id(), 'my_upload_id')
        # Then thread would chug away at the parts.
        context.announce_finished_part(etag='etag1', part_number=1)
        context.announce_finished_part(etag='etag2', part_number=2)
        context.announce_finished_part(etag='etag3', part_number=3)
        # Then a thread that was waiting for all the parts to finish
        # would be notified.
        self.assertEqual(context.wait_for_parts_to_finish(), [
            {'ETag': 'etag1', 'PartNumber': 1},
            {'ETag': 'etag2', 'PartNumber': 2},
            {'ETag': 'etag3', 'PartNumber': 3}])
        context.announce_completed()
        # This will return right away since we've already announced completion.
        self.assertIsNone(context.wait_for_completion())

    def test_basic_threaded_parts(self):
        # Now while test_normal_non_threaded showed the conceptual idea,
        # the real strength of MultipartUploadContext is that it works
        # when there are threads and when these threads operate out of
        # sequence.
        # For example, let's say a thread comes along that wants
        # to upload a part.  It needs to wait until the upload id
        # is announced.
        upload_part_thread = threading.Thread(target=self.upload_part,
                                              args=(1,))
        # Once this thread starts it will immediately block.
        self.start_thread(upload_part_thread)

        # Also, let's start the thread that will do the complete
        # multipart upload.  It will also block because it needs all
        # the parts so it's blocked up the upload_part_thread.  It also
        # needs the upload_id so it's blocked on that as well.
        complete_upload_thread = threading.Thread(target=self.complete_upload)
        self.start_thread(complete_upload_thread)

        # We'll also have some other arbitrary thread that's just waiting for
        # the whole upload to be complete.  This is not the same as
        # complete_upload_thread, as that thread is used to complete the
        # upload.  This thread wants to know when *that* process is all done.
        arbitrary_waiting_thread = threading.Thread(target=self.wait_for_upload_complete)
        self.start_thread(arbitrary_waiting_thread)

        # Then finally the CreateMultipartUpload completes and we
        # announce the upload id.
        self.create_upload('my_upload_id')
        # The upload_part thread can now proceed as well as the complete
        # multipart upload thread.
        self.join_threads()

        self.assertIsNone(self.caught_exception)
        # We can verify that the invariants still hold.
        self.assertEqual(len(self.calls), 4)
        # First there should be three calls, create, upload, complete.
        self.assertEqual(self.calls[0][0], 'create_multipart_upload')
        self.assertEqual(self.calls[1][0], 'upload_part')
        self.assertEqual(self.calls[2][0], 'complete_upload')
        # Then anything that was waiting for the operation to complete should
        # be called afterwards.
        self.assertEqual(self.calls[3][0], 'arbitrary_post_complete_operation')

        # Verify the correct args were used.
        self.assertEqual(self.calls[0][1], 'my_upload_id')
        self.assertEqual(self.calls[1][1:], (1, 'my_upload_id'))
        self.assertEqual(
            self.calls[2][1:],
            ('my_upload_id', [{'ETag': 'etag1', 'PartNumber': 1}]))

    def test_streaming_threaded_parts(self):
        # This is similar to the basic threaded parts test but instead
        # the thread has to wait to know exactly how many parts are 
        # expected from the stream.  This is indicated when the expected
        # parts of the context changes from ... to an integer.

        self.context = MultipartUploadContext(expected_parts='...')
        upload_part_thread = threading.Thread(target=self.upload_part,
                                              args=(1,))
        # Once this thread starts it will immediately block.
        self.start_thread(upload_part_thread)

        # Also, let's start the thread that will do the complete
        # multipart upload.  It will also block because it needs all
        # the parts so it's blocked up the upload_part_thread.  It also
        # needs the upload_id so it's blocked on that as well.
        complete_upload_thread = threading.Thread(target=self.complete_upload)
        self.start_thread(complete_upload_thread)

        # Then finally the CreateMultipartUpload completes and we
        # announce the upload id.
        self.create_upload('my_upload_id')
        # The complete upload thread should still be waiting for an expect
        # parts number.
        with self.call_lock:
            was_completed = (len(self.calls) > 2)

        # The upload_part thread can now proceed as well as the complete
        # multipart upload thread.
        self.context.announce_total_parts(1)
        self.join_threads()

        self.assertIsNone(self.caught_exception)

        # Make sure that the completed task was never called since it was
        # waiting to announce the parts.
        self.assertFalse(was_completed)        

        # We can verify that the invariants still hold.
        self.assertEqual(len(self.calls), 3)
        # First there should be three calls, create, upload, complete.
        self.assertEqual(self.calls[0][0], 'create_multipart_upload')
        self.assertEqual(self.calls[1][0], 'upload_part')
        self.assertEqual(self.calls[2][0], 'complete_upload')

        # Verify the correct args were used.
        self.assertEqual(self.calls[0][1], 'my_upload_id')
        self.assertEqual(self.calls[1][1:], (1, 'my_upload_id'))
        self.assertEqual(
            self.calls[2][1:],
            ('my_upload_id', [{'ETag': 'etag1', 'PartNumber': 1}]))

    def test_randomized_stress_test(self):
        # Now given that we've verified the functionality from
        # the two tests above, we randomize the threading to ensure
        # that the order doesn't actually matter.  The invariant that
        # the CreateMultipartUpload is called first, then UploadPart
        # operations are called with the appropriate upload_id, then
        # CompleteMultipartUpload with the appropriate upload_id and
        # parts list should hold true regardless of how the threads
        # are ordered.

        # I've run this with much larger values, but 100 is a good
        # tradeoff with coverage vs. execution time.
        for i in range(100):
            expected_parts = random.randint(2, 50)
            self.context = MultipartUploadContext(expected_parts=expected_parts)
            self.threads = []
            self.calls = []
            all_threads = [
                threading.Thread(target=self.complete_upload),
                threading.Thread(target=self.create_upload,
                                args=('my_upload_id',)),
                threading.Thread(target=self.wait_for_upload_complete),
            ]
            for i in range(1, expected_parts + 1):
                all_threads.append(
                    threading.Thread(target=self.upload_part, args=(i,))
                )
            random.shuffle(all_threads)
            for thread in all_threads:
                self.start_thread(thread)
            self.join_threads()
            self.assertEqual(self.calls[0][0], 'create_multipart_upload')
            self.assertEqual(self.calls[-1][0],
                             'arbitrary_post_complete_operation')
            self.assertEqual(self.calls[-2][0], 'complete_upload')
            parts = set()
            for call in self.calls[1:-2]:
                self.assertEqual(call[0], 'upload_part')
                self.assertEqual(call[2], 'my_upload_id')
                parts.add(call[1])
            self.assertEqual(len(parts), expected_parts)

    def test_can_cancel_tasks(self):
        # Let's say that we want have a thread waiting for the upload id.
        upload_part_thread = threading.Thread(target=self.upload_part,
                                            args=(1,))
        self.start_thread(upload_part_thread)
        # But for whatever reason we aren't able to call CreateMultipartUpload.
        # We'd like to let the other thread know that it should abort.
        self.context.cancel_upload()
        # The start thread should be finished.
        self.join_threads()
        # No s3 calls should have been made.
        self.assertEqual(self.calls, [])
        # And any thread that tries to wait for data will get an exception.
        with self.assertRaises(UploadCancelledError):
            self.context.wait_for_upload_id()
        with self.assertRaises(UploadCancelledError):
            self.context.wait_for_parts_to_finish()

    def test_cancel_after_upload_id(self):
        # We want have a thread waiting for the upload id.
        upload_part_thread = threading.Thread(target=self.upload_part,
                                              args=(1,))
        self.start_thread(upload_part_thread)

        # We announce the upload id.
        self.create_upload('my_upload_id')
        # The upload_part thread can now proceed,
        # now, let's cancel this upload.
        self.context.cancel_upload()

        # The upload_part_thread should be finished.
        self.join_threads()

        # In a cancelled multipart upload task any subsequent
        # call to wait_for_upload_id must raise an UploadCancelledError
        with self.assertRaises(UploadCancelledError):
            self.context.wait_for_upload_id()

    def test_cancel_threads_waiting_for_completion(self):
        # So we have a thread waiting for the entire upload to complete.
        arbitrary_waiting_thread = threading.Thread(target=self.wait_for_upload_complete)
        self.start_thread(arbitrary_waiting_thread)

        # And as it's waiting, something happens and we cancel the upload.
        self.context.cancel_upload()

        # The thread should exit.
        self.join_threads()

        # And we should have seen an exception being raised.
        self.assertIsInstance(self.caught_exception, UploadCancelledError)


class TestPrintOperation(unittest.TestCase):
    def test_print_operation(self):
        filename = mock.Mock()
        filename.operation_name = 'upload'
        filename.src = r'e:\foo'
        filename.src_type = 'local'
        filename.dest = r's3://foo'
        filename.dest_type = 's3'
        message = print_operation(filename, failed=False)
        self.assertIn(r'e:\foo', message)


class TestCreateLocalFileTask(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.tempdir = tempfile.mkdtemp()
        self.filename = mock.Mock()
        self.filename.src = 'bucket/key'
        self.filename.dest = os.path.join(self.tempdir, 'local', 'file')
        self.filename.operation_name = 'download'
        self.context = mock.Mock()
        self.task = CreateLocalFileTask(self.context,
                                        self.filename,
                                        self.result_queue)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_creates_file_and_announces(self):
        self.task()
        self.assertTrue(os.path.isfile(self.filename.dest))
        self.context.announce_file_created.assert_called_with()
        self.assertTrue(self.result_queue.empty())

    def test_cancel_command_on_exception(self):
        with mock.patch('awscli.customizations.s3.tasks.open',
                        create=True) as mock_open:
            mock_open.side_effect = OSError("Fake permissions error")
            self.task()
        self.assertFalse(os.path.isfile(self.filename.dest))
        self.context.cancel.assert_called_with()
        self.assertFalse(self.result_queue.empty())
        error_message = self.result_queue.get()
        self.assertIn("download failed", error_message.message)


class TestDownloadPartTask(unittest.TestCase):
    def setUp(self):
        self.result_queue = mock.Mock()
        self.io_queue = mock.Mock()
        self.client = mock.Mock()
        self.filename = mock.Mock()
        self.filename.size = 10 * 1024 * 1024
        self.filename.src = 'bucket/key'
        self.filename.dest = 'local/file'
        self.filename.is_stream = False
        self.filename.client = self.client
        self.filename.operation_name = 'download'
        self.context = mock.Mock()
        self.open = mock.MagicMock()
        self.params = {}

    def test_socket_timeout_is_retried(self):
        self.client.get_object.side_effect = socket.error
        task = DownloadPartTask(0, 1024 * 1024, self.result_queue,
                                self.filename, self.context,
                                self.io_queue, self.params)
        # The mock is configured to keep raising a socket.error
        # so we should cancel the download.
        with self.assertRaises(RetriesExeededError):
            task()
        self.context.cancel.assert_called_with()
        # And we retried the request multiple times.
        self.assertEqual(DownloadPartTask.TOTAL_ATTEMPTS,
                         self.client.get_object.call_count)

    def test_download_succeeds(self):
        body = mock.Mock()
        body.read.return_value = b''
        self.client.get_object.side_effect = [
            socket.error, {'Body': body}]
        task = DownloadPartTask(0, 1024 * 1024, self.result_queue,
                                self.filename, self.context,
                                self.io_queue, self.params)
        task()
        self.assertEqual(self.result_queue.put.call_count, 1)
        # And we tried twice, the first one failed, the second one
        # succeeded.
        self.assertEqual(self.client.get_object.call_count, 2)

    def test_download_queues_io_properly(self):
        body = mock.Mock()
        body.read.side_effect = [b'foobar', b'morefoobar', b'']
        self.client.get_object.side_effect = [{'Body': body}]
        task = DownloadPartTask(0, 1024 * 1024, self.result_queue,
                                self.filename, self.context,
                                self.io_queue, self.params)
        task()
        call_args_list = self.io_queue.put.call_args_list
        self.assertEqual(len(call_args_list), 2)
        self.assertEqual(call_args_list[0],
                         mock.call(('local/file', 0, b'foobar', False)))
        self.assertEqual(call_args_list[1],
                         mock.call(('local/file', 6, b'morefoobar', False)))

    def test_incomplete_read_is_retried(self):
        self.client.get_object.side_effect = \
                IncompleteReadError(actual_bytes=1, expected_bytes=2)
        task = DownloadPartTask(0, 1024 * 1024, self.result_queue,
                                self.filename,
                                self.context, self.io_queue, self.params)
        with self.assertRaises(RetriesExeededError):
            task()
        self.context.cancel.assert_called_with()
        self.assertEqual(DownloadPartTask.TOTAL_ATTEMPTS,
                         self.client.get_object.call_count)

    def test_readtimeout_is_retried(self):
        self.client.get_object.side_effect = \
            ReadTimeoutError(None, None, None)
        task = DownloadPartTask(0, 1024 * 1024, self.result_queue,
                                self.filename,
                                self.context, self.io_queue,
                                self.params)
        with self.assertRaises(RetriesExeededError):
            task()
        self.context.cancel.assert_called_with()
        self.assertEqual(DownloadPartTask.TOTAL_ATTEMPTS,
                         self.client.get_object.call_count)

    def test_retried_requests_dont_enqueue_writes_twice(self):
        error_body = mock.Mock()
        error_body.read.side_effect = socket.timeout
        success_body = mock.Mock()
        success_body.read.side_effect = [b'foobar', b'']

        incomplete_read = {'Body': error_body}
        success_read = {'Body': success_body}
        self.client.get_object.side_effect = [
            # The first request results in an error when reading the request.
            incomplete_read,
            success_read,
        ]
        self.filename.is_stream = True
        task = DownloadPartTask(
            0, transferconfig.DEFAULTS['multipart_chunksize'],
            self.result_queue, self.filename, self.context, self.io_queue,
            self.params)
        task()
        call_args_list = self.io_queue.put.call_args_list
        self.assertEqual(len(call_args_list), 1)
        self.assertEqual(call_args_list[0],
                         mock.call(('local/file', 0, b'foobar', True)))
        success_body.read.assert_called_with()


class TestMultipartDownloadContext(unittest.TestCase):
    def setUp(self):
        self.context = MultipartDownloadContext(num_parts=2)
        self.calls = []
        self.threads = []
        self.call_lock = threading.Lock()
        self.caught_exception = None

    def tearDown(self):
        self.join_threads()

    def join_threads(self):
        for thread in self.threads:
            thread.join()

    def download_stream_part(self, part_number):
        try:
            self.context.wait_for_turn(part_number)
            with self.call_lock:
                self.calls.append(('download_part', str(part_number)))
            self.context.done_with_turn()
        except Exception as e:
            self.caught_exception = e
            return

    def start_thread(self, thread):
        thread.start()
        self.threads.append(thread)

    def test_stream_context(self):
        part_thread = threading.Thread(target=self.download_stream_part,
                                       args=(1,))
        # Once this thread starts it will immediately block becasue it is
        # waiting for part zero to finish submitting its task.
        self.start_thread(part_thread)

        # Now create the thread that should submit its task first.
        part_thread2 = threading.Thread(target=self.download_stream_part,
                                        args=(0,))
        self.start_thread(part_thread2)
        self.join_threads()

        self.assertIsNone(self.caught_exception)

        # We can verify that the invariants still hold.
        self.assertEqual(len(self.calls), 2)
        # First there should be three calls, create, upload, complete.
        self.assertEqual(self.calls[0][0], 'download_part')
        self.assertEqual(self.calls[1][0], 'download_part')

        # Verify the correct order were used.
        self.assertEqual(self.calls[0][1], '0')
        self.assertEqual(self.calls[1][1], '1')


class TestTaskOrdering(unittest.TestCase):
    def setUp(self):
        self.q = StablePriorityQueue(maxsize=10, max_priority=20)

    def create_task(self):
        # We don't actually care about the arguments, we just want to test
        # the ordering of the tasks.
        return CreateLocalFileTask(None, None, None)

    def complete_task(self):
        return CompleteDownloadTask(None, None, None, None, None)

    def download_task(self):
        return DownloadPartTask(None, None, None, mock.Mock(), None, None, {})

    def shutdown_task(self, priority=None):
        return ShutdownThreadRequest(priority)

    def test_order_unchanged_in_same_priority(self):
        create = self.create_task()
        download = self.download_task()
        complete = self.complete_task()

        self.q.put(create)
        self.q.put(download)
        self.q.put(complete)

        self.assertIs(self.q.get(), create)
        self.assertIs(self.q.get(), download)
        self.assertIs(self.q.get(), complete)

    def test_multiple_tasks(self):
        create = self.create_task()
        download = self.download_task()
        complete = self.complete_task()

        create2 = self.create_task()
        download2 = self.download_task()
        complete2 = self.complete_task()

        self.q.put(create)
        self.q.put(download)
        self.q.put(complete)

        self.q.put(create2)
        self.q.put(download2)
        self.q.put(complete2)

        self.assertIs(self.q.get(), create)
        self.assertIs(self.q.get(), download)
        self.assertIs(self.q.get(), complete)

        self.assertIs(self.q.get(), create2)
        self.assertIs(self.q.get(), download2)
        self.assertIs(self.q.get(), complete2)

    def test_shutdown_tasks_are_last(self):
        create = self.create_task()
        download = self.download_task()
        complete = self.complete_task()
        shutdown = self.shutdown_task(priority=11)

        self.q.put(create)
        self.q.put(download)
        self.q.put(complete)
        self.q.put(shutdown)

        self.assertIs(self.q.get(), create)
        self.assertIs(self.q.get(), download)
        self.assertIs(self.q.get(), complete)
        self.assertIs(self.q.get(), shutdown)
