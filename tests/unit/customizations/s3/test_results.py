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
from s3transfer.exceptions import CancelledError
from s3transfer.exceptions import FatalError

from awscli.testutils import unittest
from awscli.testutils import mock
from awscli.compat import queue
from awscli.compat import StringIO
from awscli.customizations.s3.results import ShutdownThreadRequest
from awscli.customizations.s3.results import QueuedResult
from awscli.customizations.s3.results import ProgressResult
from awscli.customizations.s3.results import SuccessResult
from awscli.customizations.s3.results import FailureResult
from awscli.customizations.s3.results import ErrorResult
from awscli.customizations.s3.results import CtrlCResult
from awscli.customizations.s3.results import DryRunResult
from awscli.customizations.s3.results import FinalTotalSubmissionsResult
from awscli.customizations.s3.results import UploadResultSubscriber
from awscli.customizations.s3.results import UploadStreamResultSubscriber
from awscli.customizations.s3.results import DownloadResultSubscriber
from awscli.customizations.s3.results import DownloadStreamResultSubscriber
from awscli.customizations.s3.results import CopyResultSubscriber
from awscli.customizations.s3.results import DeleteResultSubscriber
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.results import ResultPrinter
from awscli.customizations.s3.results import OnlyShowErrorsResultPrinter
from awscli.customizations.s3.results import ResultProcessor
from awscli.customizations.s3.results import CommandResultRecorder
from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.utils import WarningResult
from tests.unit.customizations.s3 import FakeTransferFuture
from tests.unit.customizations.s3 import FakeTransferFutureMeta
from tests.unit.customizations.s3 import FakeTransferFutureCallArgs


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
        # Simulate a queue result (i.e. submitting and processing the result)
        # before processing the progress result.
        self.result_subscriber.on_queued(self.future)
        self.assertEqual(
            self.get_queued_result(),
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )
        self.assert_result_queue_is_empty()

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
                total_transfer_size=self.size,
                timestamp=mock.ANY
            )
        )

    def test_on_done_success(self):
        # Simulate a queue result (i.e. submitting and processing the result)
        # before processing the progress result.
        self.result_subscriber.on_queued(self.future)
        self.assertEqual(
            self.get_queued_result(),
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )
        self.assert_result_queue_is_empty()

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
        # Simulate a queue result (i.e. submitting and processing the result)
        # before processing the progress result.
        self.result_subscriber.on_queued(self.future)
        self.assertEqual(
            self.get_queued_result(),
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )
        self.assert_result_queue_is_empty()

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

    def test_on_done_unexpected_cancelled(self):
        # Simulate a queue result (i.e. submitting and processing the result)
        # before processing the progress result.
        self.result_subscriber.on_queued(self.future)
        self.assertEqual(
            self.get_queued_result(),
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )
        self.assert_result_queue_is_empty()

        cancelled_exception = FatalError('some error')
        cancelled_future = self.get_failed_transfer_future(cancelled_exception)
        self.result_subscriber.on_done(cancelled_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assertEqual(result, ErrorResult(exception=cancelled_exception))

    def test_on_done_cancelled_for_ctrl_c(self):
        # Simulate a queue result (i.e. submitting and processing the result)
        # before processing the progress result.
        self.result_subscriber.on_queued(self.future)
        self.assertEqual(
            self.get_queued_result(),
            QueuedResult(
                transfer_type=self.transfer_type,
                src=self.src,
                dest=self.dest,
                total_transfer_size=self.size
            )
        )
        self.assert_result_queue_is_empty()

        cancelled_exception = CancelledError('KeyboardInterrupt()')
        cancelled_future = self.get_failed_transfer_future(cancelled_exception)
        self.result_subscriber.on_done(cancelled_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        self.assertEqual(result, CtrlCResult(exception=cancelled_exception))


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

    def test_transfer_type_override(self):
        new_transfer_type = 'move'
        self.result_subscriber = CopyResultSubscriber(
            self.result_queue, new_transfer_type)
        self.result_subscriber.on_queued(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        expected = QueuedResult(
            transfer_type=new_transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size
        )
        self.assertEqual(result, expected)


class TestDeleteResultSubscriber(TestUploadResultSubscriber):
    def setUp(self):
        super(TestDeleteResultSubscriber, self).setUp()
        self.src = 's3://' + self.bucket + '/' + self.key
        self.dest = None
        self.transfer_type = 'delete'
        self.result_subscriber = DeleteResultSubscriber(self.result_queue)

    def _get_transfer_future_call_args(self):
        return FakeTransferFutureCallArgs(
            bucket=self.bucket, key=self.key)


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
        self.result_recorder.start_time = 0

    def test_queued_result(self):
        self.result_recorder(
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
            self.result_recorder(
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

    def test_queued_result_with_no_full_transfer_size(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=None
            )
        )
        # Since we do not know how many bytes are expected to be transferred
        # do not incremenent the count as we have no idea how much it may be.
        self.assertEqual(
            self.result_recorder.expected_bytes_transferred, 0)
        self.assertEqual(
            self.result_recorder.expected_files_transferred, 1)

    def test_progress_result(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size,
                timestamp=0
            )
        )

        self.assertEqual(
            self.result_recorder.bytes_transferred, bytes_transferred)

    def test_multiple_progress_results(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        num_results = 5
        for i in range(num_results):
            self.result_recorder(
                ProgressResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest, bytes_transferred=bytes_transferred,
                    total_transfer_size=self.total_transfer_size,
                    timestamp=i
                )
            )

        self.assertEqual(
            self.result_recorder.bytes_transferred,
            num_results * bytes_transferred
        )

    def test_progress_result_with_no_known_transfer_size(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=None
            )
        )

        bytes_transferred = 1024 * 1024
        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=None, timestamp=0
            )
        )
        # Because the transfer size is still not known, update the
        # expected bytes transferred with what was actually transferred.
        self.assertEqual(
            self.result_recorder.bytes_transferred, bytes_transferred)
        self.assertEqual(
            self.result_recorder.expected_bytes_transferred, bytes_transferred)

    def test_progress_result_with_transfer_size_provided_during_progress(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=None
            )
        )

        bytes_transferred = 1024 * 1024
        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size,
                timestamp=0
            )
        )

        self.assertEqual(
            self.result_recorder.bytes_transferred, bytes_transferred)
        # With the total size provided in the progress result, it should
        # accurately be reflected in the expected bytes transferred.
        self.assertEqual(
            self.result_recorder.expected_bytes_transferred,
            self.total_transfer_size)

    def test_captures_start_time_on_queued(self):
        result_recorder = ResultRecorder()
        self.assertIsNone(result_recorder.start_time)
        result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        self.assertIsInstance(result_recorder.start_time, float)

    def test_progress_calculates_transfer_speed(self):
        start_time = 0
        self.result_recorder.start_time = start_time
        self.total_transfer_size = 10
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        # At this point nothing should have been uploaded so transfer speed
        # is zero
        self.assertEqual(self.result_recorder.bytes_transfer_speed, 0)

        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=1,
                total_transfer_size=self.total_transfer_size,
                timestamp=(start_time + 1)
            )
        )

        # One bytes has been transferred in one second
        self.assertEqual(self.result_recorder.bytes_transfer_speed, 1)

        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=4,
                total_transfer_size=self.total_transfer_size,
                timestamp=(start_time + 2)
            )
        )

        # Five bytes have been transferred in two seconds
        self.assertEqual(self.result_recorder.bytes_transfer_speed, 2.5)

        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=1,
                total_transfer_size=self.total_transfer_size,
                timestamp=(start_time + 3)
            )
        )

        # Six bytes have been transferred in three seconds
        self.assertEqual(self.result_recorder.bytes_transfer_speed, 2.0)

    def test_success_result(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        self.result_recorder(
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
            self.result_recorder(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    total_transfer_size=self.total_transfer_size
                )
            )

        for i in range(num_results):
            self.result_recorder(
                SuccessResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                )
            )

        self.assertEqual(self.result_recorder.files_transferred, num_results)
        self.assertEqual(self.result_recorder.files_failed, 0)

    def test_failure_result(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        self.result_recorder(
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
            self.result_recorder(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src + str(i),
                    dest=self.dest + str(i),
                    total_transfer_size=self.total_transfer_size
                )
            )

        for i in range(num_results):
            self.result_recorder(
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
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )

        bytes_transferred = 1024 * 1024  # 1MB
        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size,
                timestamp=0
            )
        )

        self.result_recorder(
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

    def test_failure_result_still_did_not_know_transfer_size(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=None
            )
        )
        self.result_recorder(
            FailureResult(
                transfer_type=self.transfer_type, src=self.src, dest=self.dest,
                exception=self.exception
            )
        )
        self.assertEqual(self.result_recorder.files_transferred, 1)
        self.assertEqual(self.result_recorder.files_failed, 1)
        # Because we never knew how many bytes to expect, do not make
        # any adjustments to bytes failed to transfer because it is impossible
        # to know that.
        self.assertEqual(
            self.result_recorder.bytes_failed_to_transfer, 0)

    def test_failure_result_and_learned_of_transfer_size_in_progress(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=None
            )
        )

        bytes_transferred = 1024 * 1024
        self.result_recorder(
            ProgressResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, bytes_transferred=bytes_transferred,
                total_transfer_size=self.total_transfer_size,
                timestamp=0
            )
        )
        self.result_recorder(
            FailureResult(
                transfer_type=self.transfer_type, src=self.src, dest=self.dest,
                exception=self.exception
            )
        )
        self.assertEqual(self.result_recorder.files_transferred, 1)
        self.assertEqual(self.result_recorder.files_failed, 1)
        # Since we knew how many bytes to expect at some point, it should
        # be accurately reflected in the amount failed to send when the
        # failure result is processed.
        self.assertEqual(
            self.result_recorder.bytes_failed_to_transfer,
            self.total_transfer_size - bytes_transferred)

    def test_can_handle_results_with_no_dest(self):
        # This is just a quick smoke test to make sure that a result with
        # no destination like deletes can be handled for the lifecycle of
        # a transfer (i.e. being queued and finishing)
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=None, total_transfer_size=None))
        self.result_recorder(
            SuccessResult(
                transfer_type=self.transfer_type, src=self.src, dest=None))
        self.assertEqual(self.result_recorder.expected_files_transferred, 1)
        self.assertEqual(self.result_recorder.files_transferred, 1)

    def test_warning_result(self):
        self.result_recorder(
            WarningResult(message=self.warning_message))
        self.assertEqual(self.result_recorder.files_warned, 1)

    def test_multiple_warning_results(self):
        num_results = 5
        for _ in range(num_results):
            self.result_recorder(
                WarningResult(message=self.warning_message))
        self.assertEqual(self.result_recorder.files_warned, num_results)

    def test_error_result(self):
        self.result_recorder(ErrorResult(exception=self.exception))
        self.assertEqual(self.result_recorder.errors, 1)

    def test_ctrl_c_result(self):
        self.result_recorder(CtrlCResult(Exception()))
        self.assertEqual(self.result_recorder.errors, 1)

    def test_expected_totals_are_final(self):
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        self.result_recorder(FinalTotalSubmissionsResult(1))
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred, 1)
        self.assertTrue(self.result_recorder.expected_totals_are_final())

    def test_expected_totals_are_final_reaches_final_after_notification(self):
        self.result_recorder(FinalTotalSubmissionsResult(1))
        self.assertFalse(self.result_recorder.expected_totals_are_final())
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        self.assertTrue(self.result_recorder.expected_totals_are_final())

    def test_expected_totals_are_final_is_false_with_no_notification(self):
        self.assertIsNone(
            self.result_recorder.final_expected_files_transferred)
        self.assertFalse(self.result_recorder.expected_totals_are_final())
        self.result_recorder(
            QueuedResult(
                transfer_type=self.transfer_type, src=self.src,
                dest=self.dest, total_transfer_size=self.total_transfer_size
            )
        )
        # It should still be None because it has not yet been notified
        # of finals.
        self.assertIsNone(
            self.result_recorder.final_expected_files_transferred)
        # This should remain False as well.
        self.assertFalse(self.result_recorder.expected_totals_are_final())

    def test_unknown_result_object(self):
        self.result_recorder(object())
        # Nothing should have been affected
        self.assertEqual(self.result_recorder.bytes_transferred, 0)
        self.assertEqual(self.result_recorder.expected_bytes_transferred, 0)
        self.assertEqual(self.result_recorder.expected_files_transferred, 0)
        self.assertEqual(self.result_recorder.files_transferred, 0)


class BaseResultPrinterTest(unittest.TestCase):
    def setUp(self):
        self.result_recorder = ResultRecorder()
        self.out_file = StringIO()
        self.error_file = StringIO()
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=self.out_file,
            error_file=self.error_file
        )

    def get_progress_result(self):
        # NOTE: The actual values are not important for the purpose
        # of printing as the ResultPrinter only looks at the type and
        # the ResultRecorder to determine what to print out on progress.
        return ProgressResult(
            transfer_type=None, src=None, dest=None, bytes_transferred=None,
            total_transfer_size=None, timestamp=0
        )


class TestResultPrinter(BaseResultPrinterTest):
    def test_unknown_result_object(self):
        self.result_printer(object())
        # Nothing should have been printed because of it.
        self.assertEqual(self.out_file.getvalue(), '')
        self.assertEqual(self.error_file.getvalue(), '')

    def test_progress(self):
        mb = 1024 * 1024

        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1

        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) '
            'remaining\r')
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_progress_with_no_expected_transfer_bytes(self):
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = 0
        self.result_recorder.expected_bytes_transferred = 0

        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1 file(s) with 3 file(s) remaining\r')
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_progress_then_more_progress(self):
        mb = 1024 * 1024

        progress_result = self.get_progress_result()

        # Add the first progress update and print it out
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1

        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

        # Add the second progress update
        self.result_recorder.bytes_transferred += mb
        self.result_printer(progress_result)

        # The result should be the combination of the two
        ref_progress_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
            'Completed 2.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_progress_still_calculating_totals(self):
        mb = 1024 * 1024

        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1

        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1.0 MiB/~20.0 MiB (0 Bytes/s) with ~3 file(s) '
            'remaining (calculating...)\r')
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_progress_still_calculating_totals_no_bytes(self):
        self.result_recorder.expected_bytes_transferred = 0
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.bytes_transferred = 0
        self.result_recorder.files_transferred = 1

        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r')
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_progress_with_transfer_speed_reporting(self):
        mb = 1024 * 1024

        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_recorder.bytes_transfer_speed = 1024 * 7

        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        ref_progress_statement = (
            'Completed 1.0 MiB/20.0 MiB (7.0 KiB/s) with 3 file(s) '
            'remaining\r')
        self.assertEqual(self.out_file.getvalue(), ref_progress_statement)

    def test_success(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        # Pretend that this is the final result in the result queue that
        # is processed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_printer(success_result)

        ref_success_statement = (
            'upload: file to s3://mybucket/mykey\n'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_success_with_progress(self):
        mb = 1024 * 1024

        progress_result = self.get_progress_result()

        # Add the first progress update and print it out
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)

        # Add a success result and print it out.
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'
        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_recorder.files_transferred += 1
        self.result_printer(success_result)

        # The statement should consist of:
        # * The first progress statement
        # * The success statement
        # * And the progress again since the transfer is still ongoing
        ref_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
            'upload: file to s3://mybucket/mykey                            \n'
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_statement)

    def test_success_with_files_remaining(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = 4 * mb
        self.result_recorder.bytes_transferred = mb

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_printer(success_result)

        ref_success_statement = (
            'upload: file to s3://mybucket/mykey\n'
            'Completed 1.0 MiB/~4.0 MiB (0 Bytes/s) with ~3 file(s) '
            'remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_success_but_no_expected_files_transferred_provided(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_printer(success_result)

        ref_success_statement = (
            'upload: file to s3://mybucket/mykey\n'
            'Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) '
            'remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_success_for_delete(self):
        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        # Pretend that this is the final result in the result queue that
        # is processed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=None)

        self.result_printer(success_result)

        ref_success_statement = (
            'delete: s3://mybucket/mykey\n'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_delete_success_with_files_remaining(self):
        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=None)

        self.result_printer(success_result)

        ref_success_statement = (
            'delete: s3://mybucket/mykey\n'
            'Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_delete_success_but_no_expected_files_transferred_provided(self):
        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=None)

        self.result_printer(success_result)

        ref_success_statement = (
            'delete: s3://mybucket/mykey\n'
            'Completed 1 file(s) with ~0 file(s) remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_failure(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        # Pretend that this is the final result in the result queue that
        # is processed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=dest,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_failure_statement = (
            'upload failed: file to s3://mybucket/mykey my exception\n'
        )
        self.assertEqual(self.error_file.getvalue(), ref_failure_statement)
        self.assertEqual(self.out_file.getvalue(), '')

    def test_failure_with_files_remaining(self):
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = 4 * mb
        self.result_recorder.bytes_transferred = mb

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=dest,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_statement = (
            'upload failed: file to s3://mybucket/mykey my exception\n'
            'Completed 1.0 MiB/~4.0 MiB (0 Bytes/s) with ~3 file(s) '
            'remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_statement)

    def test_failure_but_no_expected_files_transferred_provided(self):
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=dest,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_statement = (
            'upload failed: file to s3://mybucket/mykey my exception\n'
            'Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) '
            'remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_statement)

    def test_failure_with_progress(self):
        # Make errors and regular outprint go to the same file to track order.
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        mb = 1024 * 1024

        progress_result = self.get_progress_result()

        # Add the first progress update and print it out
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)

        # Add a success result and print it out.
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'
        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=dest,
            exception=Exception('my exception'))

        self.result_recorder.bytes_failed_to_transfer = 3 * mb
        self.result_recorder.files_transferred += 1
        self.result_printer(failure_result)

        # The statement should consist of:
        # * The first progress statement
        # * The failure statement
        # * And the progress again since the transfer is still ongoing
        ref_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
            'upload failed: file to s3://mybucket/mykey my exception        \n'
            'Completed 4.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining\r'
        )
        self.assertEqual(shared_file.getvalue(), ref_statement)

    def test_failure_for_delete(self):
        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        # Pretend that this is the final result in the result queue that
        # is processed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=None,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_failure_statement = (
            'delete failed: s3://mybucket/mykey my exception\n'
        )
        self.assertEqual(self.error_file.getvalue(), ref_failure_statement)
        self.assertEqual(self.out_file.getvalue(), '')

    def test_delete_failure_with_files_remaining(self):
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=None,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_statement = (
            'delete failed: s3://mybucket/mykey my exception\n'
            'Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_statement)

    def test_delete_failure_but_no_expected_files_transferred_provided(self):
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        transfer_type = 'delete'
        src = 's3://mybucket/mykey'

        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=None,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_statement = (
            'delete failed: s3://mybucket/mykey my exception\n'
            'Completed 1 file(s) with ~0 file(s) remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_statement)

    def test_warning(self):
        # Pretend that this is the final result in the result queue that
        # is processed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1

        self.result_printer(WarningResult('warning: my warning'))
        ref_warning_statement = 'warning: my warning\n'
        self.assertEqual(self.error_file.getvalue(), ref_warning_statement)
        self.assertEqual(self.out_file.getvalue(), '')

    def test_warning_with_progress(self):
        # Make errors and regular outprint go to the same file to track order.
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file
        )

        mb = 1024 * 1024

        progress_result = self.get_progress_result()

        # Add the first progress update and print it out
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)

        self.result_printer(WarningResult('warning: my warning'))

        # The statement should consist of:
        # * The first progress statement
        # * The warning statement
        # * And the progress again since the transfer is still ongoing
        ref_statement = (
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
            'warning: my warning                                            \n'
            'Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r'
        )

        self.assertEqual(shared_file.getvalue(), ref_statement)

    def test_error(self):
        self.result_printer(ErrorResult(Exception('my exception')))
        ref_error_statement = 'fatal error: my exception\n'
        self.assertEqual(self.error_file.getvalue(), ref_error_statement)

    def test_ctrl_c_error(self):
        self.result_printer(CtrlCResult(Exception()))
        ref_error_statement = 'cancelled: ctrl-c received\n'
        self.assertEqual(self.error_file.getvalue(), ref_error_statement)

    def test_error_while_progress(self):
        mb = 1024 * 1024
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1

        self.result_printer(ErrorResult(Exception('my exception')))
        ref_error_statement = 'fatal error: my exception\n'
        # Even though there was progress, we do not want to print the
        # progress because errors are really only seen when the entire
        # s3 command fails.
        self.assertEqual(self.error_file.getvalue(), ref_error_statement)

    def test_dry_run(self):
        result = DryRunResult(
            transfer_type='upload',
            src='s3://mybucket/key',
            dest='./local/file'
        )
        self.result_printer(result)
        expected = '(dryrun) upload: s3://mybucket/key to ./local/file\n'
        self.assertEqual(self.out_file.getvalue(), expected)

    def test_final_total_notification_with_no_more_expected_progress(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_printer(success_result)

        ref_success_statement = (
            'upload: file to s3://mybucket/mykey\n'
            'Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) '
            'remaining (calculating...)\r'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

        # Now the result recorder/printer is notified it was just
        # there will be no more queueing. Therefore it should
        # clear out remaining progress if the expected number of files
        # transferred is equal to the number of files that has completed
        # because this is the final task meaning we want to clear any progress
        # that is displayed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_printer(FinalTotalSubmissionsResult(1))
        ref_success_statement = (
            'upload: file to s3://mybucket/mykey\n'
            'Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) '
            'with ~0 file(s) remaining (calculating...)\r'
            '                                             '
            '                                    \n'
        )
        self.assertEqual(self.out_file.getvalue(), ref_success_statement)

    def test_final_total_does_not_print_out_newline_for_no_transfers(self):
        self.result_recorder.final_expected_files_transferred = 0
        self.result_printer(FinalTotalSubmissionsResult(0))
        self.assertEqual(self.out_file.getvalue(), '')


class TestOnlyShowErrorsResultPrinter(BaseResultPrinterTest):
    def setUp(self):
        super(TestOnlyShowErrorsResultPrinter, self).setUp()
        self.result_printer = OnlyShowErrorsResultPrinter(
            result_recorder=self.result_recorder,
            out_file=self.out_file,
            error_file=self.error_file
        )

    def test_does_not_print_progress_result(self):
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        self.assertEqual(self.out_file.getvalue(), '')

    def test_does_not_print_sucess_result(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'
        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)

        self.result_printer(success_result)
        self.assertEqual(self.out_file.getvalue(), '')

    def test_print_failure_result(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'
        failure_result = FailureResult(
            transfer_type=transfer_type, src=src, dest=dest,
            exception=Exception('my exception'))

        self.result_printer(failure_result)

        ref_failure_statement = (
            'upload failed: file to s3://mybucket/mykey my exception\n'
        )
        self.assertEqual(self.error_file.getvalue(), ref_failure_statement)

    def test_print_warnings_result(self):
        self.result_printer(WarningResult('warning: my warning'))
        ref_warning_statement = 'warning: my warning\n'
        self.assertEqual(self.error_file.getvalue(), ref_warning_statement)

    def test_final_total_does_not_try_to_clear_empty_progress(self):
        transfer_type = 'upload'
        src = 'file'
        dest = 's3://mybucket/mykey'

        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb

        success_result = SuccessResult(
            transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        ref_statement = ''
        self.assertEqual(self.out_file.getvalue(), ref_statement)

        self.result_recorder.final_expected_files_transferred = 1
        self.result_printer(FinalTotalSubmissionsResult(1))
        # The final total submission result should be a noop and
        # not print anything out.
        self.assertEqual(self.out_file.getvalue(), ref_statement)


class TestResultProcessor(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.result_recorder = mock.Mock()
        self.result_printer = mock.Mock()
        self.results_handled = []

        self.result_processor = ResultProcessor(
            self.result_queue, [self.results_handled.append])

    def _handle_result_with_exception(self, result):
        raise Exception()

    def test_run(self):
        transfer_type = 'upload'
        src = 'src'
        dest = 'dest'
        total_transfer_size = 1024 * 1024
        results_to_process = [
            QueuedResult(transfer_type, src, dest, total_transfer_size),
            SuccessResult(transfer_type, src, dest)
        ]
        results_with_shutdown = results_to_process + [ShutdownThreadRequest()]

        for result in results_with_shutdown:
            self.result_queue.put(result)
        self.result_processor.run()

        self.assertEqual(self.results_handled, results_to_process)

    def test_run_without_result_handlers(self):
        transfer_type = 'upload'
        src = 'src'
        dest = 'dest'
        total_transfer_size = 1024 * 1024
        results_to_process = [
            QueuedResult(transfer_type, src, dest, total_transfer_size),
            SuccessResult(transfer_type, src, dest)
        ]
        results_with_shutdown = results_to_process + [ShutdownThreadRequest()]

        for result in results_with_shutdown:
            self.result_queue.put(result)
        self.result_processor = ResultProcessor(self.result_queue)
        self.result_processor.run()

        # Ensure that the entire result queue got processed even though
        # there was no handlers provided.
        self.assertTrue(self.result_queue.empty())

    def test_exception_handled_in_loop(self):
        transfer_type = 'upload'
        src = 'src'
        dest = 'dest'
        total_transfer_size = 1024 * 1024
        results_to_process = [
            QueuedResult(transfer_type, src, dest, total_transfer_size),
            SuccessResult(transfer_type, src, dest)
        ]
        results_with_shutdown = results_to_process + [ShutdownThreadRequest()]

        for result in results_with_shutdown:
            self.result_queue.put(result)

        results_handled_after_exception = []
        self.result_processor = ResultProcessor(
            self.result_queue,
            [self.results_handled.append, self._handle_result_with_exception,
             results_handled_after_exception.append])

        self.result_processor.run()

        self.assertEqual(self.results_handled, results_to_process)
        # The exception happens in the second handler, the exception being
        # thrown should result in the first handler and the ResultProcessor
        # continuing to process through the result queue despite the exception.
        # However, any handlers after the exception should not be run just
        # in case order of the handlers mattering and an unhandled exception
        # in one affects another handler.
        self.assertEqual(results_handled_after_exception, results_to_process)

    def test_does_not_handle_results_after_receiving_error_result(self):
        transfer_type = 'upload'
        src = 'src'
        dest = 'dest'
        results_to_be_handled = [
            SuccessResult(transfer_type, src, dest),
            ErrorResult(Exception('my exception'))
        ]
        result_not_to_be_handled = [
            ErrorResult(Exception('my second exception'))
        ]
        results_with_shutdown = results_to_be_handled + \
            result_not_to_be_handled + [ShutdownThreadRequest()]

        for result in results_with_shutdown:
            self.result_queue.put(result)

        self.result_processor.run()
        # Only the results including and before the first the ErrorResult
        # should be handled. Any results after the first ErrorResult should
        # be ignored because ErrorResults are considered fatal meaning the
        # ResultProcessor needs to consume through the rest of result queue
        # to shutdown as quickly as possible.
        self.assertEqual(self.results_handled, results_to_be_handled)

    def test_does_not_process_results_after_shutdown(self):
        transfer_type = 'upload'
        src = 'src'
        dest = 'dest'
        total_transfer_size = 1024 * 1024
        results_to_process = [
            QueuedResult(transfer_type, src, dest, total_transfer_size),
            SuccessResult(transfer_type, src, dest)
        ]
        results_with_shutdown = results_to_process + [
            ShutdownThreadRequest(), WarningResult('my warning')]

        for result in results_with_shutdown:
            self.result_queue.put(result)
        self.result_processor.run()
        # Because a ShutdownThreadRequest was sent the processor should
        # not have processed anymore results stored after it.
        self.assertEqual(self.results_handled, results_to_process)


class TestCommandResultRecorder(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.result_recorder = ResultRecorder()
        self.result_processor = ResultProcessor(
            self.result_queue, [self.result_recorder])
        self.command_result_recorder = CommandResultRecorder(
            self.result_queue, self.result_recorder, self.result_processor)

        self.transfer_type = 'upload'
        self.src = 'file'
        self.dest = 's3://mybucket/mykey'
        self.total_transfer_size = 20 * (1024 ** 1024)

    def test_success(self):
        with self.command_result_recorder:
            self.result_queue.put(
                QueuedResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest,
                    total_transfer_size=self.total_transfer_size
                )
            )
            self.result_queue.put(
                SuccessResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest
                )
            )
        self.assertEqual(
            self.command_result_recorder.get_command_result(), (0, 0))

    def test_fail(self):
        with self.command_result_recorder:
            self.result_queue.put(
                QueuedResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest,
                    total_transfer_size=self.total_transfer_size
                )
            )
            self.result_queue.put(
                FailureResult(
                    transfer_type=self.transfer_type, src=self.src,
                    dest=self.dest, exception=Exception('my exception')
                )
            )
        self.assertEqual(
            self.command_result_recorder.get_command_result(), (1, 0))

    def test_warning(self):
        with self.command_result_recorder:
            self.result_queue.put(WarningResult(message='my warning'))
        self.assertEqual(
            self.command_result_recorder.get_command_result(), (0, 1))

    def test_error(self):
        with self.command_result_recorder:
            raise Exception('my exception')
        self.assertEqual(
            self.command_result_recorder.get_command_result(), (1, 0))

    def test_notify_total_submissions(self):
        total = 5
        self.command_result_recorder.notify_total_submissions(total)
        self.assertEqual(
            self.result_queue.get(), FinalTotalSubmissionsResult(total))
