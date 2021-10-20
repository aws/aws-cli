# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy
import os
import shutil
import tempfile

from tests import BaseTaskTest
from tests import BaseSubmissionTaskTest
from tests import StreamWithError
from tests import FileCreator
from tests import mock
from tests import unittest
from tests import RecordingExecutor
from tests import NonSeekableWriter
from s3transfer.compat import six
from s3transfer.compat import SOCKET_ERROR
from s3transfer.exceptions import RetriesExceededError
from s3transfer.bandwidth import BandwidthLimiter
from s3transfer.download import DownloadFilenameOutputManager
from s3transfer.download import DownloadSpecialFilenameOutputManager
from s3transfer.download import DownloadSeekableOutputManager
from s3transfer.download import DownloadNonSeekableOutputManager
from s3transfer.download import DownloadSubmissionTask
from s3transfer.download import GetObjectTask
from s3transfer.download import ImmediatelyWriteIOGetObjectTask
from s3transfer.download import IOWriteTask
from s3transfer.download import IOStreamingWriteTask
from s3transfer.download import IORenameFileTask
from s3transfer.download import IOCloseTask
from s3transfer.download import CompleteDownloadNOOPTask
from s3transfer.download import DownloadChunkIterator
from s3transfer.download import DeferQueue
from s3transfer.futures import IN_MEMORY_DOWNLOAD_TAG
from s3transfer.futures import BoundedExecutor
from s3transfer.utils import OSUtils
from s3transfer.utils import CallArgs


class DownloadException(Exception):
    pass


class WriteCollector(object):
    """A utility to collect information about writes and seeks"""
    def __init__(self):
        self._pos = 0
        self.writes = []

    def seek(self, pos, whence=0):
        self._pos = pos

    def write(self, data):
        self.writes.append((self._pos, data))
        self._pos += len(data)


class AlwaysIndicatesSpecialFileOSUtils(OSUtils):
    """OSUtil that always returns True for is_special_file"""
    def is_special_file(self, filename):
        return True


class CancelledStreamWrapper(object):
    """A wrapper to trigger a cancellation while stream reading

    Forces the transfer coordinator to cancel after a certain amount of reads
    :param stream: The underlying stream to read from
    :param transfer_coordinator: The coordinator for the transfer
    :param num_reads: On which read to sigal a cancellation. 0 is the first
        read.
    """
    def __init__(self, stream, transfer_coordinator, num_reads=0):
        self._stream = stream
        self._transfer_coordinator = transfer_coordinator
        self._num_reads = num_reads
        self._count = 0

    def read(self, *args, **kwargs):
        if self._num_reads == self._count:
            self._transfer_coordinator.cancel()
        self._stream.read(*args, **kwargs)
        self._count += 1


class BaseDownloadOutputManagerTest(BaseTaskTest):
    def setUp(self):
        super(BaseDownloadOutputManagerTest, self).setUp()
        self.osutil = OSUtils()

        # Create a file to write to
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')

        self.call_args = CallArgs(fileobj=self.filename)
        self.future = self.get_transfer_future(self.call_args)
        self.io_executor = BoundedExecutor(1000, 1)

    def tearDown(self):
        super(BaseDownloadOutputManagerTest, self).tearDown()
        shutil.rmtree(self.tempdir)


class TestDownloadFilenameOutputManager(BaseDownloadOutputManagerTest):
    def setUp(self):
        super(TestDownloadFilenameOutputManager, self).setUp()
        self.download_output_manager = DownloadFilenameOutputManager(
            self.osutil, self.transfer_coordinator,
            io_executor=self.io_executor)

    def test_is_compatible(self):
        self.assertTrue(
            self.download_output_manager.is_compatible(
                self.filename, self.osutil)
        )

    def test_get_download_task_tag(self):
        self.assertIsNone(self.download_output_manager.get_download_task_tag())

    def test_get_fileobj_for_io_writes(self):
        with self.download_output_manager.get_fileobj_for_io_writes(
                self.future) as f:
            # Ensure it is a file like object returned
            self.assertTrue(hasattr(f, 'read'))
            self.assertTrue(hasattr(f, 'seek'))
            # Make sure the name of the file returned is not the same as the
            # final filename as we should be writing to a temporary file.
            self.assertNotEqual(f.name, self.filename)

    def test_get_final_io_task(self):
        ref_contents = b'my_contents'
        with self.download_output_manager.get_fileobj_for_io_writes(
                self.future) as f:
            temp_filename = f.name
            # Write some data to test that the data gets moved over to the
            # final location.
            f.write(ref_contents)
            final_task = self.download_output_manager.get_final_io_task()
            # Make sure it is the appropriate task.
            self.assertIsInstance(final_task, IORenameFileTask)
            final_task()
            # Make sure the temp_file gets removed
            self.assertFalse(os.path.exists(temp_filename))
        # Make sure what ever was written to the temp file got moved to
        # the final filename
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), ref_contents)

    def test_can_queue_file_io_task(self):
        fileobj = WriteCollector()
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='foo', offset=0)
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='bar', offset=3)
        self.io_executor.shutdown()
        self.assertEqual(fileobj.writes, [(0, 'foo'), (3, 'bar')])

    def test_get_file_io_write_task(self):
        fileobj = WriteCollector()
        io_write_task = self.download_output_manager.get_io_write_task(
            fileobj=fileobj, data='foo', offset=3)
        self.assertIsInstance(io_write_task, IOWriteTask)

        io_write_task()
        self.assertEqual(fileobj.writes, [(3, 'foo')])


class TestDownloadSpecialFilenameOutputManager(BaseDownloadOutputManagerTest):
    def setUp(self):
        super(TestDownloadSpecialFilenameOutputManager, self).setUp()
        self.osutil = AlwaysIndicatesSpecialFileOSUtils()
        self.download_output_manager = DownloadSpecialFilenameOutputManager(
            self.osutil, self.transfer_coordinator,
            io_executor=self.io_executor)

    def test_is_compatible_for_special_file(self):
        self.assertTrue(
            self.download_output_manager.is_compatible(
                self.filename, AlwaysIndicatesSpecialFileOSUtils()))

    def test_is_not_compatible_for_non_special_file(self):
        self.assertFalse(
            self.download_output_manager.is_compatible(
                self.filename, OSUtils()))

    def test_get_fileobj_for_io_writes(self):
        with self.download_output_manager.get_fileobj_for_io_writes(
                self.future) as f:
            # Ensure it is a file like object returned
            self.assertTrue(hasattr(f, 'read'))
            # Make sure the name of the file returned is the same as the
            # final filename as we should not be writing to a temporary file.
            self.assertEqual(f.name, self.filename)

    def test_get_final_io_task(self):
        self.assertIsInstance(
            self.download_output_manager.get_final_io_task(), IOCloseTask)

    def test_can_queue_file_io_task(self):
        fileobj = WriteCollector()
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='foo', offset=0)
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='bar', offset=3)
        self.io_executor.shutdown()
        self.assertEqual(fileobj.writes, [(0, 'foo'), (3, 'bar')])


class TestDownloadSeekableOutputManager(BaseDownloadOutputManagerTest):
    def setUp(self):
        super(TestDownloadSeekableOutputManager, self).setUp()
        self.download_output_manager = DownloadSeekableOutputManager(
            self.osutil, self.transfer_coordinator,
            io_executor=self.io_executor)

        # Create a fileobj to write to
        self.fileobj = open(self.filename, 'wb')

        self.call_args = CallArgs(fileobj=self.fileobj)
        self.future = self.get_transfer_future(self.call_args)

    def tearDown(self):
        self.fileobj.close()
        super(TestDownloadSeekableOutputManager, self).tearDown()

    def test_is_compatible(self):
        self.assertTrue(
            self.download_output_manager.is_compatible(
                self.fileobj, self.osutil)
        )

    def test_is_compatible_bytes_io(self):
        self.assertTrue(
            self.download_output_manager.is_compatible(
                six.BytesIO(), self.osutil)
        )

    def test_not_compatible_for_non_filelike_obj(self):
        self.assertFalse(self.download_output_manager.is_compatible(
            object(), self.osutil)
        )

    def test_get_download_task_tag(self):
        self.assertIsNone(self.download_output_manager.get_download_task_tag())

    def test_get_fileobj_for_io_writes(self):
        self.assertIs(
            self.download_output_manager.get_fileobj_for_io_writes(
                self.future),
            self.fileobj
        )

    def test_get_final_io_task(self):
        self.assertIsInstance(
            self.download_output_manager.get_final_io_task(),
            CompleteDownloadNOOPTask
        )

    def test_can_queue_file_io_task(self):
        fileobj = WriteCollector()
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='foo', offset=0)
        self.download_output_manager.queue_file_io_task(
            fileobj=fileobj, data='bar', offset=3)
        self.io_executor.shutdown()
        self.assertEqual(fileobj.writes, [(0, 'foo'), (3, 'bar')])

    def test_get_file_io_write_task(self):
        fileobj = WriteCollector()
        io_write_task = self.download_output_manager.get_io_write_task(
            fileobj=fileobj, data='foo', offset=3)
        self.assertIsInstance(io_write_task, IOWriteTask)

        io_write_task()
        self.assertEqual(fileobj.writes, [(3, 'foo')])


class TestDownloadNonSeekableOutputManager(BaseDownloadOutputManagerTest):
    def setUp(self):
        super(TestDownloadNonSeekableOutputManager, self).setUp()
        self.download_output_manager = DownloadNonSeekableOutputManager(
            self.osutil, self.transfer_coordinator, io_executor=None)

    def test_is_compatible_with_seekable_stream(self):
        with open(self.filename, 'wb') as f:
            self.assertTrue(self.download_output_manager.is_compatible(
                f, self.osutil)
            )

    def test_not_compatible_with_filename(self):
        self.assertFalse(self.download_output_manager.is_compatible(
            self.filename, self.osutil))

    def test_compatible_with_non_seekable_stream(self):
        class NonSeekable(object):
            def write(self, data):
                pass

        f = NonSeekable()
        self.assertTrue(self.download_output_manager.is_compatible(
            f, self.osutil)
        )

    def test_is_compatible_with_bytesio(self):
        self.assertTrue(
            self.download_output_manager.is_compatible(
                six.BytesIO(), self.osutil)
        )

    def test_get_download_task_tag(self):
        self.assertIs(
            self.download_output_manager.get_download_task_tag(),
            IN_MEMORY_DOWNLOAD_TAG)

    def test_submit_writes_from_internal_queue(self):
        class FakeQueue(object):
            def request_writes(self, offset, data):
                return [
                    {'offset': 0, 'data': 'foo'},
                    {'offset': 3, 'data': 'bar'},
                ]

        q = FakeQueue()
        io_executor = BoundedExecutor(1000, 1)
        manager = DownloadNonSeekableOutputManager(
            self.osutil, self.transfer_coordinator, io_executor=io_executor,
            defer_queue=q)
        fileobj = WriteCollector()
        manager.queue_file_io_task(
            fileobj=fileobj, data='foo', offset=1)
        io_executor.shutdown()
        self.assertEqual(fileobj.writes, [(0, 'foo'), (3, 'bar')])

    def test_get_file_io_write_task(self):
        fileobj = WriteCollector()
        io_write_task = self.download_output_manager.get_io_write_task(
            fileobj=fileobj, data='foo', offset=1)
        self.assertIsInstance(io_write_task, IOStreamingWriteTask)

        io_write_task()
        self.assertEqual(fileobj.writes, [(0, 'foo')])


class TestDownloadSubmissionTask(BaseSubmissionTaskTest):
    def setUp(self):
        super(TestDownloadSubmissionTask, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')

        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.extra_args = {}
        self.subscribers = []

        # Create a stream to read from
        self.content = b'my content'
        self.stream = six.BytesIO(self.content)

        # A list to keep track of all of the bodies sent over the wire
        # and their order.

        self.call_args = self.get_call_args()
        self.transfer_future = self.get_transfer_future(self.call_args)
        self.io_executor = BoundedExecutor(1000, 1)
        self.submission_main_kwargs = {
            'client': self.client,
            'config': self.config,
            'osutil': self.osutil,
            'request_executor': self.executor,
            'io_executor': self.io_executor,
            'transfer_future': self.transfer_future
        }
        self.submission_task = self.get_download_submission_task()

    def tearDown(self):
        super(TestDownloadSubmissionTask, self).tearDown()
        shutil.rmtree(self.tempdir)

    def get_call_args(self, **kwargs):
        default_call_args = {
            'fileobj': self.filename, 'bucket': self.bucket,
            'key': self.key, 'extra_args': self.extra_args,
            'subscribers': self.subscribers
        }
        default_call_args.update(kwargs)
        return CallArgs(**default_call_args)

    def wrap_executor_in_recorder(self):
        self.executor = RecordingExecutor(self.executor)
        self.submission_main_kwargs['request_executor'] = self.executor

    def use_fileobj_in_call_args(self, fileobj):
        self.call_args = self.get_call_args(fileobj=fileobj)
        self.transfer_future = self.get_transfer_future(self.call_args)
        self.submission_main_kwargs['transfer_future'] = self.transfer_future

    def assert_tag_for_get_object(self, tag_value):
        submissions_to_compare = self.executor.submissions
        if len(submissions_to_compare) > 1:
            # If it was ranged get, make sure we do not include the join task.
            submissions_to_compare = submissions_to_compare[:-1]
        for submission in submissions_to_compare:
            self.assertEqual(
                submission['tag'], tag_value)

    def add_head_object_response(self):
        self.stubber.add_response(
            'head_object', {'ContentLength': len(self.content)})

    def add_get_responses(self):
        chunksize = self.config.multipart_chunksize
        for i in range(0, len(self.content), chunksize):
            if i + chunksize > len(self.content):
                stream = six.BytesIO(self.content[i:])
                self.stubber.add_response('get_object', {'Body': stream})
            else:
                stream = six.BytesIO(self.content[i:i+chunksize])
                self.stubber.add_response('get_object', {'Body': stream})

    def configure_for_ranged_get(self):
        self.config.multipart_threshold = 1
        self.config.multipart_chunksize = 4

    def get_download_submission_task(self):
        return self.get_task(
            DownloadSubmissionTask, main_kwargs=self.submission_main_kwargs)

    def wait_and_assert_completed_successfully(self, submission_task):
        submission_task()
        self.transfer_future.result()
        self.stubber.assert_no_pending_responses()

    def test_submits_no_tag_for_get_object_filename(self):
        self.wrap_executor_in_recorder()
        self.add_head_object_response()
        self.add_get_responses()

        self.submission_task = self.get_download_submission_task()
        self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(None)

    def test_submits_no_tag_for_ranged_get_filename(self):
        self.wrap_executor_in_recorder()
        self.configure_for_ranged_get()
        self.add_head_object_response()
        self.add_get_responses()

        self.submission_task = self.get_download_submission_task()
        self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(None)

    def test_submits_no_tag_for_get_object_fileobj(self):
        self.wrap_executor_in_recorder()
        self.add_head_object_response()
        self.add_get_responses()

        with open(self.filename, 'wb') as f:
            self.use_fileobj_in_call_args(f)
            self.submission_task = self.get_download_submission_task()
            self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(None)

    def test_submits_no_tag_for_ranged_get_object_fileobj(self):
        self.wrap_executor_in_recorder()
        self.configure_for_ranged_get()
        self.add_head_object_response()
        self.add_get_responses()

        with open(self.filename, 'wb') as f:
            self.use_fileobj_in_call_args(f)
            self.submission_task = self.get_download_submission_task()
            self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(None)

    def tests_submits_tag_for_get_object_nonseekable_fileobj(self):
        self.wrap_executor_in_recorder()
        self.add_head_object_response()
        self.add_get_responses()

        with open(self.filename, 'wb') as f:
            self.use_fileobj_in_call_args(NonSeekableWriter(f))
            self.submission_task = self.get_download_submission_task()
            self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(IN_MEMORY_DOWNLOAD_TAG)

    def tests_submits_tag_for_ranged_get_object_nonseekable_fileobj(self):
        self.wrap_executor_in_recorder()
        self.configure_for_ranged_get()
        self.add_head_object_response()
        self.add_get_responses()

        with open(self.filename, 'wb') as f:
            self.use_fileobj_in_call_args(NonSeekableWriter(f))
            self.submission_task = self.get_download_submission_task()
            self.wait_and_assert_completed_successfully(self.submission_task)

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_for_get_object(IN_MEMORY_DOWNLOAD_TAG)


class TestGetObjectTask(BaseTaskTest):
    def setUp(self):
        super(TestGetObjectTask, self).setUp()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.extra_args = {}
        self.callbacks = []
        self.max_attempts = 5
        self.io_executor = BoundedExecutor(1000, 1)
        self.content = b'my content'
        self.stream = six.BytesIO(self.content)
        self.fileobj = WriteCollector()
        self.osutil = OSUtils()
        self.io_chunksize = 64 * (1024 ** 2)
        self.task_cls = GetObjectTask
        self.download_output_manager = DownloadSeekableOutputManager(
            self.osutil, self.transfer_coordinator, self.io_executor)

    def get_download_task(self, **kwargs):
        default_kwargs = {
            'client': self.client, 'bucket': self.bucket, 'key': self.key,
            'fileobj': self.fileobj, 'extra_args': self.extra_args,
            'callbacks': self.callbacks,
            'max_attempts': self.max_attempts,
            'download_output_manager': self.download_output_manager,
            'io_chunksize': self.io_chunksize,
        }
        default_kwargs.update(kwargs)
        self.transfer_coordinator.set_status_to_queued()
        return self.get_task(self.task_cls, main_kwargs=default_kwargs)

    def assert_io_writes(self, expected_writes):
        # Let the io executor process all of the writes before checking
        # what writes were sent to it.
        self.io_executor.shutdown()
        self.assertEqual(self.fileobj.writes, expected_writes)

    def test_main(self):
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task()
        task()

        self.stubber.assert_no_pending_responses()
        self.assert_io_writes([(0, self.content)])

    def test_extra_args(self):
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key, 'Range': 'bytes=0-'
            }
        )
        self.extra_args['Range'] = 'bytes=0-'
        task = self.get_download_task()
        task()

        self.stubber.assert_no_pending_responses()
        self.assert_io_writes([(0, self.content)])

    def test_control_chunk_size(self):
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task(io_chunksize=1)
        task()

        self.stubber.assert_no_pending_responses()
        expected_contents = []
        for i in range(len(self.content)):
            expected_contents.append((i, bytes(self.content[i:i+1])))

        self.assert_io_writes(expected_contents)

    def test_start_index(self):
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task(start_index=5)
        task()

        self.stubber.assert_no_pending_responses()
        self.assert_io_writes([(5, self.content)])

    def test_uses_bandwidth_limiter(self):
        bandwidth_limiter = mock.Mock(BandwidthLimiter)

        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task(bandwidth_limiter=bandwidth_limiter)
        task()

        self.stubber.assert_no_pending_responses()
        self.assertEqual(
            bandwidth_limiter.get_bandwith_limited_stream.call_args_list,
            [mock.call(mock.ANY, self.transfer_coordinator)]
        )

    def test_retries_succeeds(self):
        self.stubber.add_response(
            'get_object', service_response={
                'Body': StreamWithError(self.stream, SOCKET_ERROR)
            },
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task()
        task()

        # Retryable error should have not affected the bytes placed into
        # the io queue.
        self.stubber.assert_no_pending_responses()
        self.assert_io_writes([(0, self.content)])

    def test_retries_failure(self):
        for _ in range(self.max_attempts):
            self.stubber.add_response(
                'get_object', service_response={
                    'Body': StreamWithError(self.stream, SOCKET_ERROR)
                },
                expected_params={'Bucket': self.bucket, 'Key': self.key}
            )

        task = self.get_download_task()
        task()
        self.transfer_coordinator.announce_done()

        # Should have failed out on a RetriesExceededError
        with self.assertRaises(RetriesExceededError):
            self.transfer_coordinator.result()
        self.stubber.assert_no_pending_responses()

    def test_retries_in_middle_of_streaming(self):
        # After the first read a retryable error will be thrown
        self.stubber.add_response(
            'get_object', service_response={
                'Body': StreamWithError(
                    copy.deepcopy(self.stream), SOCKET_ERROR, 1)
            },
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        self.stubber.add_response(
            'get_object', service_response={'Body': self.stream},
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task(io_chunksize=1)
        task()

        self.stubber.assert_no_pending_responses()
        expected_contents = []
        # This is the content initially read in before the retry hit on the
        # second read()
        expected_contents.append((0, bytes(self.content[0:1])))

        # The rest of the content should be the entire set of data partitioned
        # out based on the one byte stream chunk size. Note the second
        # element in the list should be a copy of the first element since
        # a retryable exception happened in between.
        for i in range(len(self.content)):
            expected_contents.append((i, bytes(self.content[i:i+1])))
        self.assert_io_writes(expected_contents)

    def test_cancels_out_of_queueing(self):
        self.stubber.add_response(
            'get_object',
            service_response={
                'Body': CancelledStreamWrapper(
                    self.stream, self.transfer_coordinator)
            },
            expected_params={'Bucket': self.bucket, 'Key': self.key}
        )
        task = self.get_download_task()
        task()

        self.stubber.assert_no_pending_responses()
        # Make sure that no contents were added to the queue because the task
        # should have been canceled before trying to add the contents to the
        # io queue.
        self.assert_io_writes([])

    def test_handles_callback_on_initial_error(self):
        # We can't use the stubber for this because we need to raise
        # a S3_RETRYABLE_DOWNLOAD_ERRORS, and the stubber only allows
        # you to raise a ClientError.
        self.client.get_object = mock.Mock(side_effect=SOCKET_ERROR())
        task = self.get_download_task()
        task()
        self.transfer_coordinator.announce_done()
        # Should have failed out on a RetriesExceededError because
        # get_object keeps raising a socket error.
        with self.assertRaises(RetriesExceededError):
            self.transfer_coordinator.result()


class TestImmediatelyWriteIOGetObjectTask(TestGetObjectTask):
    def setUp(self):
        super(TestImmediatelyWriteIOGetObjectTask, self).setUp()
        self.task_cls = ImmediatelyWriteIOGetObjectTask
        # When data is written out, it should not use the io executor at all
        # if it does use the io executor that is a deviation from expected
        # behavior as the data should be written immediately to the file
        # object once downloaded.
        self.io_executor = None
        self.download_output_manager = DownloadSeekableOutputManager(
            self.osutil, self.transfer_coordinator, self.io_executor)

    def assert_io_writes(self, expected_writes):
        self.assertEqual(self.fileobj.writes, expected_writes)


class BaseIOTaskTest(BaseTaskTest):
    def setUp(self):
        super(BaseIOTaskTest, self).setUp()
        self.files = FileCreator()
        self.osutil = OSUtils()
        self.temp_filename = os.path.join(self.files.rootdir, 'mytempfile')
        self.final_filename = os.path.join(self.files.rootdir, 'myfile')

    def tearDown(self):
        super(BaseIOTaskTest, self).tearDown()
        self.files.remove_all()


class TestIOStreamingWriteTask(BaseIOTaskTest):
    def test_main(self):
        with open(self.temp_filename, 'wb') as f:
            task = self.get_task(
                IOStreamingWriteTask,
                main_kwargs={
                    'fileobj': f,
                    'data': b'foobar'
                }
            )
            task()
            task2 = self.get_task(
                IOStreamingWriteTask,
                main_kwargs={
                    'fileobj': f,
                    'data': b'baz'
                }
            )
            task2()
        with open(self.temp_filename, 'rb') as f:
            # We should just have written to the file in the order
            # the tasks were executed.
            self.assertEqual(f.read(), b'foobarbaz')


class TestIOWriteTask(BaseIOTaskTest):
    def test_main(self):
        with open(self.temp_filename, 'wb') as f:
            # Write once to the file
            task = self.get_task(
                IOWriteTask,
                main_kwargs={
                    'fileobj': f,
                    'data': b'foo',
                    'offset': 0
                }
            )
            task()

            # Write again to the file
            task = self.get_task(
                IOWriteTask,
                main_kwargs={
                    'fileobj': f,
                    'data': b'bar',
                    'offset': 3
                }
            )
            task()

        with open(self.temp_filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')


class TestIORenameFileTask(BaseIOTaskTest):
    def test_main(self):
        with open(self.temp_filename, 'wb') as f:
            task = self.get_task(
                IORenameFileTask,
                main_kwargs={
                    'fileobj': f,
                    'final_filename': self.final_filename,
                    'osutil': self.osutil
                }
            )
            task()
        self.assertTrue(os.path.exists(self.final_filename))
        self.assertFalse(os.path.exists(self.temp_filename))


class TestIOCloseTask(BaseIOTaskTest):
    def test_main(self):
        with open(self.temp_filename, 'w') as f:
            task = self.get_task(IOCloseTask, main_kwargs={'fileobj': f})
            task()
            self.assertTrue(f.closed)


class TestDownloadChunkIterator(unittest.TestCase):
    def test_iter(self):
        content = b'my content'
        body = six.BytesIO(content)
        ref_chunks = []
        for chunk in DownloadChunkIterator(body, len(content)):
            ref_chunks.append(chunk)
        self.assertEqual(ref_chunks, [b'my content'])

    def test_iter_chunksize(self):
        content = b'1234'
        body = six.BytesIO(content)
        ref_chunks = []
        for chunk in DownloadChunkIterator(body, 3):
            ref_chunks.append(chunk)
        self.assertEqual(ref_chunks, [b'123', b'4'])

    def test_empty_content(self):
        body = six.BytesIO(b'')
        ref_chunks = []
        for chunk in DownloadChunkIterator(body, 3):
            ref_chunks.append(chunk)
        self.assertEqual(ref_chunks, [b''])


class TestDeferQueue(unittest.TestCase):
    def setUp(self):
        self.q = DeferQueue()

    def test_no_writes_when_not_lowest_block(self):
        writes = self.q.request_writes(offset=1, data='bar')
        self.assertEqual(writes, [])

    def test_writes_returned_in_order(self):
        self.assertEqual(self.q.request_writes(offset=3, data='d'), [])
        self.assertEqual(self.q.request_writes(offset=2, data='c'), [])
        self.assertEqual(self.q.request_writes(offset=1, data='b'), [])

        # Everything at this point has been deferred, but as soon as we
        # send offset=0, that will unlock offsets 0-3.
        writes = self.q.request_writes(offset=0, data='a')
        self.assertEqual(
            writes,
            [
                {'offset': 0, 'data': 'a'},
                {'offset': 1, 'data': 'b'},
                {'offset': 2, 'data': 'c'},
                {'offset': 3, 'data': 'd'}
            ]
        )

    def test_unlocks_partial_range(self):
        self.assertEqual(self.q.request_writes(offset=5, data='f'), [])
        self.assertEqual(self.q.request_writes(offset=1, data='b'), [])

        # offset=0 unlocks 0-1, but offset=5 still needs to see 2-4 first.
        writes = self.q.request_writes(offset=0, data='a')
        self.assertEqual(
            writes,
            [
                {'offset': 0, 'data': 'a'},
                {'offset': 1, 'data': 'b'},
            ]
        )

    def test_data_can_be_any_size(self):
        self.q.request_writes(offset=5, data='hello world')
        writes = self.q.request_writes(offset=0, data='abcde')
        self.assertEqual(
            writes,
            [
                {'offset': 0, 'data': 'abcde'},
                {'offset': 5, 'data': 'hello world'},
            ]
        )

    def test_data_queued_in_order(self):
        # This immediately gets returned because offset=0 is the
        # next range we're waiting on.
        writes = self.q.request_writes(offset=0, data='hello world')
        self.assertEqual(writes, [{'offset': 0, 'data': 'hello world'}])
        # Same thing here but with offset
        writes = self.q.request_writes(offset=11, data='hello again')
        self.assertEqual(writes, [{'offset': 11, 'data': 'hello again'}])

    def test_writes_below_min_offset_are_ignored(self):
        self.q.request_writes(offset=0, data='a')
        self.q.request_writes(offset=1, data='b')
        self.q.request_writes(offset=2, data='c')

        # At this point we're expecting offset=3, so if a write
        # comes in below 3, we ignore it.
        self.assertEqual(self.q.request_writes(offset=0, data='a'), [])
        self.assertEqual(self.q.request_writes(offset=1, data='b'), [])

        self.assertEqual(
            self.q.request_writes(offset=3, data='d'),
            [{'offset': 3, 'data': 'd'}]
        )

    def test_duplicate_writes_are_ignored(self):
        self.q.request_writes(offset=2, data='c')
        self.q.request_writes(offset=1, data='b')

        # We're still waiting for offset=0, but if
        # a duplicate write comes in for offset=2/offset=1
        # it's ignored.  This gives "first one wins" behavior.
        self.assertEqual(self.q.request_writes(offset=2, data='X'), [])
        self.assertEqual(self.q.request_writes(offset=1, data='Y'), [])

        self.assertEqual(
            self.q.request_writes(offset=0, data='a'),
            [
                {'offset': 0, 'data': 'a'},
                # Note we're seeing 'b' 'c', and not 'X', 'Y'.
                {'offset': 1, 'data': 'b'},
                {'offset': 2, 'data': 'c'},
            ]
        )
