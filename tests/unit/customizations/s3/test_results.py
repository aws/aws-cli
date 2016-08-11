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
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.utils import WarningResult


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
        self.assertEqual(
            result,
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )

    def test_on_progress(self):
        ref_bytes_transferred = 1024 * 1024  # 1MB
        self.result_subscriber.on_progress(self.future, ref_bytes_transferred)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assertEqual(
            result,
            ProgressResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                bytes_transferred=ref_bytes_transferred,
                total_transfer_size=self.size
            )
        )

    def test_on_done_success(self):
        self.result_subscriber.on_done(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assertEqual(
            result,
            SuccessResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
            )
        )

    def test_on_done_failure(self):
        self.result_subscriber.on_done(self.failure_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assertEqual(
            result,
            FailureResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                exception=self.ref_exception
            )
        )


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


class ResultRecorderTest(unittest.TestCase):
    def setUp(self):
        self.transfer_type = 'upload'
        self.src = 'file'
        self.dest = 's3://mybucket/mykey'
        self.total_transfer_size = 20 * (1024 ** 1024)  # 20MB
        self.warning_message = 'a dummy warning message'
        self.exception_message = 'a dummy exception message'
        self.exception = Exception(self.exception_message)
        self.result_recorder = ResultRecorder()

    def test_queued_result(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        self.assertEqual(
            self.result_recorder.expected_bytes_transferred,
            self.total_transfer_size
        )
        self.assertEqual(self.result_recorder.expected_files_transferred, 1)

    def test_multiple_queued_results(self):
        num_results = 5
        for i in range(num_results):
            self.result_recorder.record_result(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    total_transfer_size=self.total_transfer_size
                )
            )

        self.assertEqual(
            self.result_recorder.expected_bytes_transferred,
            num_results * self.total_transfer_size
        )
        self.assertEqual(
            self.result_recorder.expected_files_transferred, num_results)

    def test_progress_result(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        self.result_recorder.record_result(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size
            )
        )

        self.assertEqual(
            self.result_recorder.bytes_transferred, bytes_transferred)

    def test_multiple_progress_results(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        num_results = 5
        for _ in range(num_results):
            self.result_recorder.record_result(
                ProgressResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest, bytes_transferred=bytes_transferred,
                    total_transfer_size=self.total_transfer_size
                )
            )

        self.assertEqual(
            self.result_recorder.bytes_transferred,
            num_results * bytes_transferred
        )

    def test_success_result(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        self.result_recorder.record_result(
            SuccessResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest
            )
        )
        self.assertEqual(self.result_recorder.files_transferred, 1)
        self.assertEqual(self.result_recorder.files_failed, 0)

    def test_multiple_success_results(self):
        num_results = 5
        for i in range(num_results):
            self.result_recorder.record_result(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    total_transfer_size=self.total_transfer_size
                )
            )

        for i in range(num_results):
            self.result_recorder.record_result(
                SuccessResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                )
            )

        self.assertEqual(self.result_recorder.files_transferred, num_results)
        self.assertEqual(self.result_recorder.files_failed, 0)

    def test_failure_result(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        self.result_recorder.record_result(
            FailureResult(
                transfer_type=self.transfer_type, src=self.src, dest=self.dest,
                exception=self.exception
            )
        )

        self.assertEqual(self.result_recorder.files_transferred, 1)
        self.assertEqual(self.result_recorder.files_failed, 1)
        self.assertEqual(
            self.result_recorder.bytes_failed_to_transfer,
            self.total_transfer_size)
        self.assertEqual(self.result_recorder.bytes_transferred, 0)

    def test_multiple_failure_results(self):
        num_results = 5
        for i in range(num_results):
            self.result_recorder.record_result(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    total_transfer_size=self.total_transfer_size
                )
            )

        for i in range(num_results):
            self.result_recorder.record_result(
                FailureResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    exception=self.exception
                )
            )

        self.assertEqual(self.result_recorder.files_transferred, num_results)
        self.assertEqual(self.result_recorder.files_failed, num_results)
        self.assertEqual(
            self.result_recorder.bytes_failed_to_transfer,
            self.total_transfer_size * num_results)
        self.assertEqual(self.result_recorder.bytes_transferred, 0)

    def test_failure_result_mid_progress(self):
        self.result_recorder.record_result(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        self.result_recorder.record_result(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size
            )
        )

        self.result_recorder.record_result(
            FailureResult(
                transfer_type=self.transfer_type, src=self.src, dest=self.dest,
                exception=self.exception
            )
        )

        self.assertEqual(self.result_recorder.files_transferred, 1)
        self.assertEqual(self.result_recorder.files_failed, 1)
        self.assertEqual(
            self.result_recorder.bytes_failed_to_transfer,
            self.total_transfer_size - bytes_transferred)
        self.assertEqual(
            self.result_recorder.bytes_transferred, bytes_transferred)

    def test_warning_result(self):
        self.result_recorder.record_result(
            WarningResult(message=self.warning_message))
        self.assertEqual(self.result_recorder.files_warned, 1)

    def test_multiple_warning_results(self):
        num_results = 5
        for _ in range(num_results):
            self.result_recorder.record_result(
                WarningResult(message=self.warning_message))
        self.assertEqual(self.result_recorder.files_warned, num_results)

    def test_unknown_result_object(self):
        self.result_recorder.record_result(object())
        # Nothing should have been affected
        self.assertEqual(self.result_recorder.bytes_transferred, 0)
        self.assertEqual(self.result_recorder.expected_bytes_transferred, 0)
        self.assertEqual(self.result_recorder.expected_files_transferred, 0)
        self.assertEqual(self.result_recorder.files_transferred, 0)
