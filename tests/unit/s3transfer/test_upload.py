# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from __future__ import division
import os
import tempfile
import shutil
import math

from botocore.stub import ANY

from tests import unittest
from tests import BaseTaskTest
from tests import BaseSubmissionTaskTest
from tests import FileSizeProvider
from tests import RecordingSubscriber
from tests import RecordingExecutor
from tests import NonSeekableReader
from s3transfer.compat import six
from s3transfer.futures import IN_MEMORY_UPLOAD_TAG
from s3transfer.manager import TransferConfig
from s3transfer.upload import AggregatedProgressCallback
from s3transfer.upload import InterruptReader
from s3transfer.upload import UploadFilenameInputManager
from s3transfer.upload import UploadSeekableInputManager
from s3transfer.upload import UploadNonSeekableInputManager
from s3transfer.upload import UploadSubmissionTask
from s3transfer.upload import PutObjectTask
from s3transfer.upload import UploadPartTask
from s3transfer.utils import CallArgs
from s3transfer.utils import OSUtils
from s3transfer.utils import MIN_UPLOAD_CHUNKSIZE


class InterruptionError(Exception):
    pass


class OSUtilsExceptionOnFileSize(OSUtils):
    def get_file_size(self, filename):
        raise AssertionError(
            "The file %s should not have been stated" % filename)


class BaseUploadTest(BaseTaskTest):
    def setUp(self):
        super(BaseUploadTest, self).setUp()
        self.bucket = 'mybucket'
        self.key = 'foo'
        self.osutil = OSUtils()

        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')
        self.content = b'my content'
        self.subscribers = []

        with open(self.filename, 'wb') as f:
            f.write(self.content)

        # A list to keep track of all of the bodies sent over the wire
        # and their order.
        self.sent_bodies = []
        self.client.meta.events.register(
            'before-parameter-build.s3.*', self.collect_body)

    def tearDown(self):
        super(BaseUploadTest, self).tearDown()
        shutil.rmtree(self.tempdir)

    def collect_body(self, params, **kwargs):
        if 'Body' in params:
            self.sent_bodies.append(params['Body'].read())


class TestAggregatedProgressCallback(unittest.TestCase):
    def setUp(self):
        self.aggregated_amounts = []
        self.threshold = 3
        self.aggregated_progress_callback = AggregatedProgressCallback(
            [self.callback], self.threshold)

    def callback(self, bytes_transferred):
        self.aggregated_amounts.append(bytes_transferred)

    def test_under_threshold(self):
        one_under_threshold_amount = self.threshold - 1
        self.aggregated_progress_callback(one_under_threshold_amount)
        self.assertEqual(self.aggregated_amounts, [])
        self.aggregated_progress_callback(1)
        self.assertEqual(self.aggregated_amounts, [self.threshold])

    def test_at_threshold(self):
        self.aggregated_progress_callback(self.threshold)
        self.assertEqual(self.aggregated_amounts, [self.threshold])

    def test_over_threshold(self):
        over_threshold_amount = self.threshold + 1
        self.aggregated_progress_callback(over_threshold_amount)
        self.assertEqual(self.aggregated_amounts, [over_threshold_amount])

    def test_flush(self):
        under_threshold_amount = self.threshold - 1
        self.aggregated_progress_callback(under_threshold_amount)
        self.assertEqual(self.aggregated_amounts, [])
        self.aggregated_progress_callback.flush()
        self.assertEqual(self.aggregated_amounts, [under_threshold_amount])

    def test_flush_with_nothing_to_flush(self):
        under_threshold_amount = self.threshold - 1
        self.aggregated_progress_callback(under_threshold_amount)
        self.assertEqual(self.aggregated_amounts, [])
        self.aggregated_progress_callback.flush()
        self.assertEqual(self.aggregated_amounts, [under_threshold_amount])
        # Flushing again should do nothing as it was just flushed
        self.aggregated_progress_callback.flush()
        self.assertEqual(self.aggregated_amounts, [under_threshold_amount])


class TestInterruptReader(BaseUploadTest):
    def test_read_raises_exception(self):
        with open(self.filename, 'rb') as f:
            reader = InterruptReader(f, self.transfer_coordinator)
            # Read some bytes to show it can be read.
            self.assertEqual(reader.read(1), self.content[0:1])
            # Then set an exception in the transfer coordinator
            self.transfer_coordinator.set_exception(InterruptionError())
            # The next read should have the exception propograte
            with self.assertRaises(InterruptionError):
                reader.read()

    def test_seek(self):
        with open(self.filename, 'rb') as f:
            reader = InterruptReader(f, self.transfer_coordinator)
            # Ensure it can seek correctly
            reader.seek(1)
            self.assertEqual(reader.read(1), self.content[1:2])

    def test_tell(self):
        with open(self.filename, 'rb') as f:
            reader = InterruptReader(f, self.transfer_coordinator)
            # Ensure it can tell correctly
            reader.seek(1)
            self.assertEqual(reader.tell(), 1)


class BaseUploadInputManagerTest(BaseUploadTest):
    def setUp(self):
        super(BaseUploadInputManagerTest, self).setUp()
        self.osutil = OSUtils()
        self.config = TransferConfig()
        self.recording_subscriber = RecordingSubscriber()
        self.subscribers.append(self.recording_subscriber)

    def _get_expected_body_for_part(self, part_number):
        # A helper method for retrieving the expected body for a specific
        # part number of the data
        total_size = len(self.content)
        chunk_size = self.config.multipart_chunksize
        start_index = (part_number - 1) * chunk_size
        end_index = part_number * chunk_size
        if end_index >= total_size:
            return self.content[start_index:]
        return self.content[start_index:end_index]


class TestUploadFilenameInputManager(BaseUploadInputManagerTest):
    def setUp(self):
        super(TestUploadFilenameInputManager, self).setUp()
        self.upload_input_manager = UploadFilenameInputManager(
            self.osutil, self.transfer_coordinator)
        self.call_args = CallArgs(
            fileobj=self.filename, subscribers=self.subscribers)
        self.future = self.get_transfer_future(self.call_args)

    def test_is_compatible(self):
        self.assertTrue(
            self.upload_input_manager.is_compatible(
                self.future.meta.call_args.fileobj)
        )

    def test_stores_bodies_in_memory_put_object(self):
        self.assertFalse(
            self.upload_input_manager.stores_body_in_memory('put_object'))

    def test_stores_bodies_in_memory_upload_part(self):
        self.assertFalse(
            self.upload_input_manager.stores_body_in_memory('upload_part'))

    def test_provide_transfer_size(self):
        self.upload_input_manager.provide_transfer_size(self.future)
        # The provided file size should be equal to size of the contents of
        # the file.
        self.assertEqual(self.future.meta.size, len(self.content))

    def test_requires_multipart_upload(self):
        self.future.meta.provide_transfer_size(len(self.content))
        # With the default multipart threshold, the length of the content
        # should be smaller than the threshold thus not requiring a multipart
        # transfer.
        self.assertFalse(
            self.upload_input_manager.requires_multipart_upload(
                self.future, self.config))
        # Decreasing the threshold to that of the length of the content of
        # the file should trigger the need for a multipart upload.
        self.config.multipart_threshold = len(self.content)
        self.assertTrue(
            self.upload_input_manager.requires_multipart_upload(
                self.future, self.config))

    def test_get_put_object_body(self):
        self.future.meta.provide_transfer_size(len(self.content))
        read_file_chunk = self.upload_input_manager.get_put_object_body(
            self.future)
        read_file_chunk.enable_callback()
        # The file-like object provided back should be the same as the content
        # of the file.
        with read_file_chunk:
            self.assertEqual(read_file_chunk.read(), self.content)
        # The file-like object should also have been wrapped with the
        # on_queued callbacks to track the amount of bytes being transferred.
        self.assertEqual(
            self.recording_subscriber.calculate_bytes_seen(),
            len(self.content))

    def test_get_put_object_body_is_interruptable(self):
        self.future.meta.provide_transfer_size(len(self.content))
        read_file_chunk = self.upload_input_manager.get_put_object_body(
            self.future)

        # Set an exception in the transfer coordinator
        self.transfer_coordinator.set_exception(InterruptionError)
        # Ensure the returned read file chunk can be interrupted with that
        # error.
        with self.assertRaises(InterruptionError):
            read_file_chunk.read()

    def test_yield_upload_part_bodies(self):
        # Adjust the chunk size to something more grainular for testing.
        self.config.multipart_chunksize = 4
        self.future.meta.provide_transfer_size(len(self.content))

        # Get an iterator that will yield all of the bodies and their
        # respective part number.
        part_iterator = self.upload_input_manager.yield_upload_part_bodies(
            self.future, self.config.multipart_chunksize)
        expected_part_number = 1
        for part_number, read_file_chunk in part_iterator:
            # Ensure that the part number is as expected
            self.assertEqual(part_number, expected_part_number)
            read_file_chunk.enable_callback()
            # Ensure that the body is correct for that part.
            with read_file_chunk:
                self.assertEqual(
                    read_file_chunk.read(),
                    self._get_expected_body_for_part(part_number))
            expected_part_number += 1

        # All of the file-like object should also have been wrapped with the
        # on_queued callbacks to track the amount of bytes being transferred.
        self.assertEqual(
            self.recording_subscriber.calculate_bytes_seen(),
            len(self.content))

    def test_yield_upload_part_bodies_are_interruptable(self):
        # Adjust the chunk size to something more grainular for testing.
        self.config.multipart_chunksize = 4
        self.future.meta.provide_transfer_size(len(self.content))

        # Get an iterator that will yield all of the bodies and their
        # respective part number.
        part_iterator = self.upload_input_manager.yield_upload_part_bodies(
            self.future, self.config.multipart_chunksize)

        # Set an exception in the transfer coordinator
        self.transfer_coordinator.set_exception(InterruptionError)
        for _, read_file_chunk in part_iterator:
            # Ensure that each read file chunk yielded can be interrupted
            # with that error.
            with self.assertRaises(InterruptionError):
                read_file_chunk.read()


class TestUploadSeekableInputManager(TestUploadFilenameInputManager):
    def setUp(self):
        super(TestUploadSeekableInputManager, self).setUp()
        self.upload_input_manager = UploadSeekableInputManager(
            self.osutil, self.transfer_coordinator)
        self.fileobj = open(self.filename, 'rb')
        self.call_args = CallArgs(
            fileobj=self.fileobj, subscribers=self.subscribers)
        self.future = self.get_transfer_future(self.call_args)

    def tearDown(self):
        self.fileobj.close()
        super(TestUploadSeekableInputManager, self).tearDown()

    def test_is_compatible_bytes_io(self):
        self.assertTrue(
            self.upload_input_manager.is_compatible(six.BytesIO()))

    def test_not_compatible_for_non_filelike_obj(self):
        self.assertFalse(self.upload_input_manager.is_compatible(object()))

    def test_stores_bodies_in_memory_upload_part(self):
        self.assertTrue(
            self.upload_input_manager.stores_body_in_memory('upload_part'))

    def test_get_put_object_body(self):
        start_pos = 3
        self.fileobj.seek(start_pos)
        adjusted_size = len(self.content) - start_pos
        self.future.meta.provide_transfer_size(adjusted_size)
        read_file_chunk = self.upload_input_manager.get_put_object_body(
            self.future)

        read_file_chunk.enable_callback()
        # The fact that the file was seeked to start should be taken into
        # account in length and content for the read file chunk.
        with read_file_chunk:
            self.assertEqual(len(read_file_chunk), adjusted_size)
            self.assertEqual(read_file_chunk.read(), self.content[start_pos:])
        self.assertEqual(
            self.recording_subscriber.calculate_bytes_seen(), adjusted_size)


class TestUploadNonSeekableInputManager(TestUploadFilenameInputManager):
    def setUp(self):
        super(TestUploadNonSeekableInputManager, self).setUp()
        self.upload_input_manager = UploadNonSeekableInputManager(
            self.osutil, self.transfer_coordinator)
        self.fileobj = NonSeekableReader(self.content)
        self.call_args = CallArgs(
            fileobj=self.fileobj, subscribers=self.subscribers)
        self.future = self.get_transfer_future(self.call_args)

    def assert_multipart_parts(self):
        """
        Asserts that the input manager will generate a multipart upload
        and that each part is in order and the correct size.
        """
        # Assert that a multipart upload is required.
        self.assertTrue(
            self.upload_input_manager.requires_multipart_upload(
                self.future, self.config))

        # Get a list of all the parts that would be sent.
        parts = list(
            self.upload_input_manager.yield_upload_part_bodies(
                self.future, self.config.multipart_chunksize))

        # Assert that the actual number of parts is what we would expect
        # based on the configuration.
        size = self.config.multipart_chunksize
        num_parts = math.ceil(len(self.content) / size)
        self.assertEqual(len(parts), num_parts)

        # Run for every part but the last part.
        for i, part in enumerate(parts[:-1]):
            # Assert the part number is correct.
            self.assertEqual(part[0], i + 1)
            # Assert the part contains the right amount of data.
            data = part[1].read()
            self.assertEqual(len(data), size)

        # Assert that the last part is the correct size.
        expected_final_size = len(self.content) - ((num_parts - 1) * size)
        final_part = parts[-1]
        self.assertEqual(len(final_part[1].read()), expected_final_size)

        # Assert that the last part has the correct part number.
        self.assertEqual(final_part[0], len(parts))

    def test_provide_transfer_size(self):
        self.upload_input_manager.provide_transfer_size(self.future)
        # There is no way to get the size without reading the entire body.
        self.assertEqual(self.future.meta.size, None)

    def test_stores_bodies_in_memory_upload_part(self):
        self.assertTrue(
            self.upload_input_manager.stores_body_in_memory('upload_part'))

    def test_stores_bodies_in_memory_put_object(self):
        self.assertTrue(
            self.upload_input_manager.stores_body_in_memory('put_object'))

    def test_initial_data_parts_threshold_lesser(self):
        # threshold < size
        self.config.multipart_chunksize = 4
        self.config.multipart_threshold = 2
        self.assert_multipart_parts()

    def test_initial_data_parts_threshold_equal(self):
        # threshold == size
        self.config.multipart_chunksize = 4
        self.config.multipart_threshold = 4
        self.assert_multipart_parts()

    def test_initial_data_parts_threshold_greater(self):
        # threshold > size
        self.config.multipart_chunksize = 4
        self.config.multipart_threshold = 8
        self.assert_multipart_parts()


class TestUploadSubmissionTask(BaseSubmissionTaskTest):
    def setUp(self):
        super(TestUploadSubmissionTask, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')
        self.content = b'0' * (MIN_UPLOAD_CHUNKSIZE * 3)
        self.config.multipart_chunksize = MIN_UPLOAD_CHUNKSIZE
        self.config.multipart_threshold = MIN_UPLOAD_CHUNKSIZE * 5

        with open(self.filename, 'wb') as f:
            f.write(self.content)

        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.extra_args = {}
        self.subscribers = []

        # A list to keep track of all of the bodies sent over the wire
        # and their order.
        self.sent_bodies = []
        self.client.meta.events.register(
            'before-parameter-build.s3.*', self.collect_body)

        self.call_args = self.get_call_args()
        self.transfer_future = self.get_transfer_future(self.call_args)
        self.submission_main_kwargs = {
            'client': self.client,
            'config': self.config,
            'osutil': self.osutil,
            'request_executor': self.executor,
            'transfer_future': self.transfer_future
        }
        self.submission_task = self.get_task(
            UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)

    def tearDown(self):
        super(TestUploadSubmissionTask, self).tearDown()
        shutil.rmtree(self.tempdir)

    def collect_body(self, params, **kwargs):
        if 'Body' in params:
            self.sent_bodies.append(params['Body'].read())

    def get_call_args(self, **kwargs):
        default_call_args = {
            'fileobj': self.filename, 'bucket': self.bucket,
            'key': self.key, 'extra_args': self.extra_args,
            'subscribers': self.subscribers
        }
        default_call_args.update(kwargs)
        return CallArgs(**default_call_args)

    def add_multipart_upload_stubbed_responses(self):
        self.stubber.add_response(
            method='create_multipart_upload',
            service_response={'UploadId': 'my-id'}
        )
        self.stubber.add_response(
            method='upload_part',
            service_response={'ETag': 'etag-1'}
        )
        self.stubber.add_response(
            method='upload_part',
            service_response={'ETag': 'etag-2'}
        )
        self.stubber.add_response(
            method='upload_part',
            service_response={'ETag': 'etag-3'}
        )
        self.stubber.add_response(
            method='complete_multipart_upload',
            service_response={}
        )

    def wrap_executor_in_recorder(self):
        self.executor = RecordingExecutor(self.executor)
        self.submission_main_kwargs['request_executor'] = self.executor

    def use_fileobj_in_call_args(self, fileobj):
        self.call_args = self.get_call_args(fileobj=fileobj)
        self.transfer_future = self.get_transfer_future(self.call_args)
        self.submission_main_kwargs['transfer_future'] = self.transfer_future

    def assert_tag_value_for_put_object(self, tag_value):
        self.assertEqual(
            self.executor.submissions[0]['tag'], tag_value)

    def assert_tag_value_for_upload_parts(self, tag_value):
        for submission in self.executor.submissions[1:-1]:
            self.assertEqual(
                submission['tag'], tag_value)

    def test_provide_file_size_on_put(self):
        self.call_args.subscribers.append(FileSizeProvider(len(self.content)))
        self.stubber.add_response(
            method='put_object',
            service_response={},
            expected_params={
                'Body': ANY, 'Bucket': self.bucket,
                'Key': self.key
            }
        )

        # With this submitter, it will fail to stat the file if a transfer
        # size is not provided.
        self.submission_main_kwargs['osutil'] = OSUtilsExceptionOnFileSize()

        self.submission_task = self.get_task(
            UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)
        self.submission_task()
        self.transfer_future.result()
        self.stubber.assert_no_pending_responses()
        self.assertEqual(self.sent_bodies, [self.content])

    def test_submits_no_tag_for_put_object_filename(self):
        self.wrap_executor_in_recorder()
        self.stubber.add_response('put_object', {})

        self.submission_task = self.get_task(
            UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)
        self.submission_task()
        self.transfer_future.result()
        self.stubber.assert_no_pending_responses()

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_value_for_put_object(None)

    def test_submits_no_tag_for_multipart_filename(self):
        self.wrap_executor_in_recorder()

        # Set up for a multipart upload.
        self.add_multipart_upload_stubbed_responses()
        self.config.multipart_threshold = 1

        self.submission_task = self.get_task(
            UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)
        self.submission_task()
        self.transfer_future.result()
        self.stubber.assert_no_pending_responses()

        # Make sure no tag to limit any of the upload part tasks were
        # were associated when submitted to the executor
        self.assert_tag_value_for_upload_parts(None)

    def test_submits_no_tag_for_put_object_fileobj(self):
        self.wrap_executor_in_recorder()
        self.stubber.add_response('put_object', {})

        with open(self.filename, 'rb') as f:
            self.use_fileobj_in_call_args(f)
            self.submission_task = self.get_task(
                UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)
            self.submission_task()
            self.transfer_future.result()
            self.stubber.assert_no_pending_responses()

        # Make sure no tag to limit that task specifically was not associated
        # to that task submission.
        self.assert_tag_value_for_put_object(None)

    def test_submits_tag_for_multipart_fileobj(self):
        self.wrap_executor_in_recorder()

        # Set up for a multipart upload.
        self.add_multipart_upload_stubbed_responses()
        self.config.multipart_threshold = 1

        with open(self.filename, 'rb') as f:
            self.use_fileobj_in_call_args(f)
            self.submission_task = self.get_task(
                UploadSubmissionTask, main_kwargs=self.submission_main_kwargs)
            self.submission_task()
            self.transfer_future.result()
            self.stubber.assert_no_pending_responses()

        # Make sure tags to limit all of the upload part tasks were
        # were associated when submitted to the executor as these tasks will
        # have chunks of data stored with them in memory.
        self.assert_tag_value_for_upload_parts(IN_MEMORY_UPLOAD_TAG)


class TestPutObjectTask(BaseUploadTest):
    def test_main(self):
        extra_args = {'Metadata': {'foo': 'bar'}}
        with open(self.filename, 'rb') as fileobj:
            task = self.get_task(
                PutObjectTask,
                main_kwargs={
                    'client': self.client,
                    'fileobj': fileobj,
                    'bucket': self.bucket,
                    'key': self.key,
                    'extra_args': extra_args
                }
            )
            self.stubber.add_response(
                method='put_object',
                service_response={},
                expected_params={
                    'Body': ANY, 'Bucket': self.bucket, 'Key': self.key,
                    'Metadata': {'foo': 'bar'}
                }
            )
            task()
            self.stubber.assert_no_pending_responses()
            self.assertEqual(self.sent_bodies, [self.content])


class TestUploadPartTask(BaseUploadTest):
    def test_main(self):
        extra_args = {'RequestPayer': 'requester'}
        upload_id = 'my-id'
        part_number = 1
        etag = 'foo'
        with open(self.filename, 'rb') as fileobj:
            task = self.get_task(
                UploadPartTask,
                main_kwargs={
                    'client': self.client,
                    'fileobj': fileobj,
                    'bucket': self.bucket,
                    'key': self.key,
                    'upload_id': upload_id,
                    'part_number': part_number,
                    'extra_args': extra_args
                }
            )
            self.stubber.add_response(
                method='upload_part',
                service_response={'ETag': etag},
                expected_params={
                    'Body': ANY, 'Bucket': self.bucket, 'Key': self.key,
                    'UploadId': upload_id, 'PartNumber': part_number,
                    'RequestPayer': 'requester'
                }
            )
            rval = task()
            self.stubber.assert_no_pending_responses()
            self.assertEqual(rval, {'ETag': etag, 'PartNumber': part_number})
            self.assertEqual(self.sent_bodies, [self.content])
