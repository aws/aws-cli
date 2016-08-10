# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.compat import queue
from awscli.customizations.s3.results import QueuedResult
from awscli.customizations.s3.results import ProgressResult
from awscli.customizations.s3.results import SuccessResult
from awscli.customizations.s3.results import FailureResult
from awscli.customizations.s3.results import UploadResultSubscriber
from awscli.customizations.s3.results import UploadStreamResultSubscriber
from awscli.customizations.s3.results import DownloadResultSubscriber
from awscli.customizations.s3.results import DownloadStreamResultSubscriber
from awscli.customizations.s3.results import CopyResultSubscriber
from awscli.customizations.s3.utils import relative_path


class FakeTransferFuture(object):
    def __init__(self, result=None, exception=None, meta=None):
        self._result = result
        self._exception = exception
        self.meta = meta

    def result(self):
        if self._exception:
            raise self._exception
        return self._result


class FakeTransferFutureMeta(object):
    def __init__(self, size=None, call_args=None):
        self.size = size
        self.call_args = call_args


class FakeTransferFutureCallArgs(object):
    def __init__(self, **kwargs):
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)


class BaseResultSubscriberTest(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()

        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.filename = 'myfile'
        self.size = 20 * (1024 * 1024)  # 20 MB

        self.ref_exception = Exception()
        self.set_ref_transfer_futures()

        self.src = None
        self.dest = None
        self.transfer_type = None

    def set_ref_transfer_futures(self):
        self.future = self.get_success_transfer_future('foo')
        self.failure_future = self.get_failed_transfer_future(
            self.ref_exception)

    def get_success_transfer_future(self, result):
        return self._get_transfer_future(result=result)

    def get_failed_transfer_future(self, exception):
        return self._get_transfer_future(exception=exception)

    def _get_transfer_future(self, result=None, exception=None):
        call_args = self._get_transfer_future_call_args()
        meta = FakeTransferFutureMeta(size=self.size, call_args=call_args)
        return FakeTransferFuture(
            result=result, exception=exception, meta=meta)

    def _get_transfer_future_call_args(self):
        return FakeTransferFutureCallArgs(
            fileobj=self.filename, key=self.key, bucket=self.bucket)

    def get_queued_result(self):
        return self.result_queue.get(block=False)

    def assert_result_queue_is_empty(self):
        self.assertTrue(self.result_queue.empty())

    def assert_expected_transfer_type(self, result):
        self.assertEqual(result.transfer_type, self.transfer_type)

    def assert_expected_src_and_dest(self, result):
        self.assertEqual(result.src, self.src)
        self.assertEqual(result.dest, self.dest)

    def assert_expected_total_transfer_size(self, result):
        self.assertEqual(result.total_transfer_size, self.size)

    def assert_correct_queued_result(self, result):
        self.assertIsInstance(result, QueuedResult)
        self.assert_expected_transfer_type(result)
        self.assert_expected_src_and_dest(result)
        self.assert_expected_total_transfer_size(result)

    def assert_correct_progress_result(self, result, ref_bytes_transferred):
        self.assertIsInstance(result, ProgressResult)
        self.assert_expected_transfer_type(result)
        self.assert_expected_src_and_dest(result)
        self.assertEqual(result.bytes_transferred, ref_bytes_transferred)
        self.assert_expected_total_transfer_size(result)

    def assert_correct_success_result(self, result):
        self.assertIsInstance(result, SuccessResult)
        self.assert_expected_transfer_type(result)
        self.assert_expected_src_and_dest(result)

    def assert_correct_exception_result(self, result, ref_exception):
        self.assertIsInstance(result, FailureResult)
        self.assert_expected_transfer_type(result)
        self.assert_expected_src_and_dest(result)
        self.assertEqual(result.exception, ref_exception)


class TestUploadResultSubscriber(BaseResultSubscriberTest):
    def setUp(self):
        super(TestUploadResultSubscriber, self).setUp()
        self.src = relative_path(self.filename)
        self.dest = 's3://' + self.bucket + '/' + self.key
        self.transfer_type = 'upload'
        self.result_subscriber = UploadResultSubscriber(self.result_queue)

    def test_on_queued(self):
        self.result_subscriber.on_queued(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assert_correct_queued_result(result)

    def test_on_progress(self):
        ref_bytes_transferred = 1024 * 1024  # 1MB
        self.result_subscriber.on_progress(self.future, ref_bytes_transferred)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assert_correct_progress_result(result, ref_bytes_transferred)

    def test_on_done_success(self):
        self.result_subscriber.on_done(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assert_correct_success_result(result)

    def test_on_done_failure(self):
        self.result_subscriber.on_done(self.failure_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assert_correct_exception_result(result, self.ref_exception)


class TestUploadStreamResultSubscriber(TestUploadResultSubscriber):
    def setUp(self):
        super(TestUploadStreamResultSubscriber, self).setUp()
        self.src = '-'
        self.result_subscriber = UploadStreamResultSubscriber(
            self.result_queue)


class TestDownloadResultSubscriber(TestUploadResultSubscriber):
    def setUp(self):
        super(TestDownloadResultSubscriber, self).setUp()
        self.src = 's3://' + self.bucket + '/' + self.key
        self.dest = relative_path(self.filename)
        self.transfer_type = 'download'
        self.result_subscriber = DownloadResultSubscriber(self.result_queue)


class TestDownloadStreamResultSubscriber(TestDownloadResultSubscriber):
    def setUp(self):
        super(TestDownloadStreamResultSubscriber, self).setUp()
        self.dest = '-'
        self.result_subscriber = DownloadStreamResultSubscriber(
            self.result_queue)


class TestCopyResultSubscriber(TestUploadResultSubscriber):
    def setUp(self):
        self.source_bucket = 'sourcebucket'
        self.source_key = 'sourcekey'
        self.copy_source = {
            'Bucket': self.source_bucket,
            'Key': self.source_key,
        }
        super(TestCopyResultSubscriber, self).setUp()
        self.src = 's3://' + self.source_bucket + '/' + self.source_key
        self.dest = 's3://' + self.bucket + '/' + self.key
        self.transfer_type = 'copy'
        self.result_subscriber = CopyResultSubscriber(self.result_queue)

    def _get_transfer_future_call_args(self):
        return FakeTransferFutureCallArgs(
            copy_source=self.copy_source, key=self.key, bucket=self.bucket)
