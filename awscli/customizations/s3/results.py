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
from __future__ import division
import logging
import sys
import threading
import time
from collections import namedtuple
from collections import defaultdict

from s3transfer.exceptions import CancelledError
from s3transfer.exceptions import FatalError
from s3transfer.subscribers import BaseSubscriber

from awscli.compat import queue
from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.utils import human_readable_size
from awscli.customizations.s3.utils import uni_print
from awscli.customizations.s3.utils import WarningResult
from awscli.customizations.s3.utils import OnDoneFilteredSubscriber


LOGGER = logging.getLogger(__name__)


BaseResult = namedtuple('BaseResult', ['transfer_type', 'src', 'dest'])


def _create_new_result_cls(name, extra_fields=None, base_cls=BaseResult):
    # Creates a new namedtuple class that subclasses from BaseResult for the
    # benefit of filtering by type and ensuring particular base attrs.

    # NOTE: _fields is a public attribute that has an underscore to avoid
    # naming collisions for namedtuples:
    # https://docs.python.org/2/library/collections.html#collections.somenamedtuple._fields
    fields = list(base_cls._fields)
    if extra_fields:
        fields += extra_fields
    return type(name, (namedtuple(name, fields), base_cls), {})


QueuedResult = _create_new_result_cls('QueuedResult', ['total_transfer_size'])

ProgressResult = _create_new_result_cls(
    'ProgressResult', ['bytes_transferred', 'total_transfer_size',
                       'timestamp'])

SuccessResult = _create_new_result_cls('SuccessResult')

FailureResult = _create_new_result_cls('FailureResult', ['exception'])

DryRunResult = _create_new_result_cls('DryRunResult')

ErrorResult = namedtuple('ErrorResult', ['exception'])

CtrlCResult = _create_new_result_cls('CtrlCResult', base_cls=ErrorResult)

CommandResult = namedtuple(
    'CommandResult', ['num_tasks_failed', 'num_tasks_warned'])

FinalTotalSubmissionsResult = namedtuple(
    'FinalTotalSubmissionsResult', ['total_submissions'])


class ShutdownThreadRequest(object):
    pass


class BaseResultSubscriber(OnDoneFilteredSubscriber):
    TRANSFER_TYPE = None

    def __init__(self, result_queue, transfer_type=None):
        """Subscriber to send result notifications during transfer process

        :param result_queue: The queue to place results to be processed later
            on.
        """
        self._result_queue = result_queue
        self._result_kwargs_cache = {}
        self._transfer_type = transfer_type
        if transfer_type is None:
            self._transfer_type = self.TRANSFER_TYPE

    def on_queued(self, future, **kwargs):
        self._add_to_result_kwargs_cache(future)
        result_kwargs = self._result_kwargs_cache[future.meta.transfer_id]
        queued_result = QueuedResult(**result_kwargs)
        self._result_queue.put(queued_result)

    def on_progress(self, future, bytes_transferred, **kwargs):
        result_kwargs = self._result_kwargs_cache[future.meta.transfer_id]
        progress_result = ProgressResult(
            bytes_transferred=bytes_transferred, timestamp=time.time(),
            **result_kwargs)
        self._result_queue.put(progress_result)

    def _on_success(self, future):
        result_kwargs = self._on_done_pop_from_result_kwargs_cache(future)
        self._result_queue.put(SuccessResult(**result_kwargs))

    def _on_failure(self, future, e):
        result_kwargs = self._on_done_pop_from_result_kwargs_cache(future)
        if isinstance(e, CancelledError):
            error_result_cls = CtrlCResult
            if isinstance(e, FatalError):
                error_result_cls = ErrorResult
            self._result_queue.put(error_result_cls(exception=e))
        else:
            self._result_queue.put(FailureResult(exception=e, **result_kwargs))

    def _add_to_result_kwargs_cache(self, future):
        src, dest = self._get_src_dest(future)
        result_kwargs = {
            'transfer_type': self._transfer_type,
            'src': src,
            'dest': dest,
            'total_transfer_size': future.meta.size
        }
        self._result_kwargs_cache[future.meta.transfer_id] = result_kwargs

    def _on_done_pop_from_result_kwargs_cache(self, future):
        result_kwargs = self._result_kwargs_cache.pop(future.meta.transfer_id)
        result_kwargs.pop('total_transfer_size')
        return result_kwargs

    def _get_src_dest(self, future):
        raise NotImplementedError('_get_src_dest()')


class UploadResultSubscriber(BaseResultSubscriber):
    TRANSFER_TYPE = 'upload'

    def _get_src_dest(self, future):
        call_args = future.meta.call_args
        src = self._get_src(call_args.fileobj)
        dest = 's3://' + call_args.bucket + '/' + call_args.key
        return src, dest

    def _get_src(self, fileobj):
        return relative_path(fileobj)


class UploadStreamResultSubscriber(UploadResultSubscriber):
    def _get_src(self, fileobj):
        return '-'


class DownloadResultSubscriber(BaseResultSubscriber):
    TRANSFER_TYPE = 'download'

    def _get_src_dest(self, future):
        call_args = future.meta.call_args
        src = 's3://' + call_args.bucket + '/' + call_args.key
        dest = self._get_dest(call_args.fileobj)
        return src, dest

    def _get_dest(self, fileobj):
        return relative_path(fileobj)


class DownloadStreamResultSubscriber(DownloadResultSubscriber):
    def _get_dest(self, fileobj):
        return '-'


class CopyResultSubscriber(BaseResultSubscriber):
    TRANSFER_TYPE = 'copy'

    def _get_src_dest(self, future):
        call_args = future.meta.call_args
        copy_source = call_args.copy_source
        src = 's3://' + copy_source['Bucket'] + '/' + copy_source['Key']
        dest = 's3://' + call_args.bucket + '/' + call_args.key
        return src, dest


class DeleteResultSubscriber(BaseResultSubscriber):
    TRANSFER_TYPE = 'delete'

    def _get_src_dest(self, future):
        call_args = future.meta.call_args
        src = 's3://' + call_args.bucket + '/' + call_args.key
        return src, None


class BaseResultHandler(object):
    """Base handler class to be called in the ResultProcessor"""
    def __call__(self, result):
        raise NotImplementedError('__call__()')


class ResultRecorder(BaseResultHandler):
    """Records and track transfer statistics based on results receieved"""
    def __init__(self):
        self.bytes_transferred = 0
        self.bytes_failed_to_transfer = 0
        self.files_transferred = 0
        self.files_failed = 0
        self.files_warned = 0
        self.errors = 0
        self.expected_bytes_transferred = 0
        self.expected_files_transferred = 0
        self.final_expected_files_transferred = None

        self.start_time = None
        self.bytes_transfer_speed = 0

        self._ongoing_progress = defaultdict(int)
        self._ongoing_total_sizes = {}

        self._result_handler_map = {
            QueuedResult: self._record_queued_result,
            ProgressResult: self._record_progress_result,
            SuccessResult: self._record_success_result,
            FailureResult: self._record_failure_result,
            WarningResult: self._record_warning_result,
            ErrorResult: self._record_error_result,
            CtrlCResult: self._record_error_result,
            FinalTotalSubmissionsResult: self._record_final_expected_files,
        }

    def expected_totals_are_final(self):
        return (
            self.final_expected_files_transferred ==
            self.expected_files_transferred
        )

    def __call__(self, result):
        """Record the result of an individual Result object"""
        self._result_handler_map.get(type(result), self._record_noop)(
            result=result)

    def _get_ongoing_dict_key(self, result):
        if not isinstance(result, BaseResult):
            raise ValueError(
                'Any result using _get_ongoing_dict_key must subclass from '
                'BaseResult. Provided result is of type: %s' % type(result)
            )
        return ':'.join(
            str(el) for el in [result.transfer_type, result.src, result.dest])

    def _pop_result_from_ongoing_dicts(self, result):
        ongoing_key = self._get_ongoing_dict_key(result)
        total_progress = self._ongoing_progress.pop(ongoing_key, 0)
        total_file_size = self._ongoing_total_sizes.pop(ongoing_key, None)
        return total_progress, total_file_size

    def _record_noop(self, **kwargs):
        # If the result does not have a handler, then do nothing with it.
        pass

    def _record_queued_result(self, result, **kwargs):
        if self.start_time is None:
            self.start_time = time.time()
        total_transfer_size = result.total_transfer_size
        self._ongoing_total_sizes[
            self._get_ongoing_dict_key(result)] = total_transfer_size
        # The total transfer size can be None if we do not know the size
        # immediately so do not add to the total right away.
        if total_transfer_size:
            self.expected_bytes_transferred += total_transfer_size
        self.expected_files_transferred += 1

    def _record_progress_result(self, result, **kwargs):
        bytes_transferred = result.bytes_transferred
        self._update_ongoing_transfer_size_if_unknown(result)
        self._ongoing_progress[
            self._get_ongoing_dict_key(result)] += bytes_transferred
        self.bytes_transferred += bytes_transferred
        # Since the start time is captured in the result recorder and
        # capture timestamps in the subscriber, there is a chance that if
        # a progress result gets created right after the queued result
        # gets created that the timestamp on the progress result is less
        # than the timestamp of when the result processor actually
        # processes that initial queued result. So this will avoid
        # negative progress being displayed or zero divison occuring.
        if result.timestamp > self.start_time:
            self.bytes_transfer_speed = self.bytes_transferred / (
                result.timestamp - self.start_time)

    def _update_ongoing_transfer_size_if_unknown(self, result):
        # This is a special case when the transfer size was previous not
        # known but was provided in a progress result.
        ongoing_key = self._get_ongoing_dict_key(result)

        # First, check if the total size is None, meaning its size is
        # currently unknown.
        if self._ongoing_total_sizes[ongoing_key] is None:
            total_transfer_size = result.total_transfer_size
            # If the total size is no longer None that means we just learned
            # of the size so let's update the appropriate places with this
            # knowledge
            if result.total_transfer_size is not None:
                self._ongoing_total_sizes[ongoing_key] = total_transfer_size
                # Figure out how many bytes have been unaccounted for as
                # the recorder has been keeping track of how many bytes
                # it has seen so far and add it to the total expected amount.
                ongoing_progress = self._ongoing_progress[ongoing_key]
                unaccounted_bytes = total_transfer_size - ongoing_progress
                self.expected_bytes_transferred += unaccounted_bytes
            # If we still do not know what the total transfer size is
            # just update the expected bytes with the know bytes transferred
            # as we know at the very least, those bytes are expected.
            else:
                self.expected_bytes_transferred += result.bytes_transferred

    def _record_success_result(self, result, **kwargs):
        self._pop_result_from_ongoing_dicts(result)
        self.files_transferred += 1

    def _record_failure_result(self, result, **kwargs):
        # If there was a failure, we want to account for the failure in
        # the count for bytes transferred by just adding on the remaining bytes
        # that did not get transferred.
        total_progress, total_file_size = self._pop_result_from_ongoing_dicts(
            result)
        if total_file_size is not None:
            progress_left = total_file_size - total_progress
            self.bytes_failed_to_transfer += progress_left

        self.files_failed += 1
        self.files_transferred += 1

    def _record_warning_result(self, **kwargs):
        self.files_warned += 1

    def _record_error_result(self, **kwargs):
        self.errors += 1

    def _record_final_expected_files(self, result, **kwargs):
        self.final_expected_files_transferred = result.total_submissions


class ResultPrinter(BaseResultHandler):
    _FILES_REMAINING = "{remaining_files} file(s) remaining"
    _ESTIMATED_EXPECTED_TOTAL = "~{expected_total}"
    _STILL_CALCULATING_TOTALS = " (calculating...)"
    BYTE_PROGRESS_FORMAT = (
        'Completed {bytes_completed}/{expected_bytes_completed} '
        '({transfer_speed}) with ' + _FILES_REMAINING
    )
    FILE_PROGRESS_FORMAT = (
        'Completed {files_completed} file(s) with ' + _FILES_REMAINING
    )
    SUCCESS_FORMAT = (
        '{transfer_type}: {transfer_location}'
    )
    DRY_RUN_FORMAT = '(dryrun) ' + SUCCESS_FORMAT
    FAILURE_FORMAT = (
        '{transfer_type} failed: {transfer_location} {exception}'
    )
    # TODO: Add "warning: " prefix once all commands are converted to using
    # result printer and remove "warning: " prefix from ``create_warning``.
    WARNING_FORMAT = (
        '{message}'
    )
    ERROR_FORMAT = (
        'fatal error: {exception}'
    )
    CTRL_C_MSG = 'cancelled: ctrl-c received'

    SRC_DEST_TRANSFER_LOCATION_FORMAT = '{src} to {dest}'
    SRC_TRANSFER_LOCATION_FORMAT = '{src}'

    def __init__(self, result_recorder, out_file=None, error_file=None):
        """Prints status of ongoing transfer

        :type result_recorder: ResultRecorder
        :param result_recorder: The associated result recorder

        :type out_file: file-like obj
        :param out_file: Location to write progress and success statements.
            By default, the location is sys.stdout.

        :type error_file: file-like obj
        :param error_file: Location to write warnings and errors.
            By default, the location is sys.stderr.
        """
        self._result_recorder = result_recorder
        self._out_file = out_file
        if self._out_file is None:
            self._out_file = sys.stdout
        self._error_file = error_file
        if self._error_file is None:
            self._error_file = sys.stderr
        self._progress_length = 0
        self._result_handler_map = {
            ProgressResult: self._print_progress,
            SuccessResult: self._print_success,
            FailureResult: self._print_failure,
            WarningResult: self._print_warning,
            ErrorResult: self._print_error,
            CtrlCResult: self._print_ctrl_c,
            DryRunResult: self._print_dry_run,
            FinalTotalSubmissionsResult:
                self._clear_progress_if_no_more_expected_transfers,
        }

    def __call__(self, result):
        """Print the progress of the ongoing transfer based on a result"""
        self._result_handler_map.get(type(result), self._print_noop)(
            result=result)

    def _print_noop(self, **kwargs):
        # If the result does not have a handler, then do nothing with it.
        pass

    def _print_dry_run(self, result, **kwargs):
        statement = self.DRY_RUN_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result)
        )
        statement = self._adjust_statement_padding(statement)
        self._print_to_out_file(statement)

    def _print_success(self, result, **kwargs):
        success_statement = self.SUCCESS_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result)
        )
        success_statement = self._adjust_statement_padding(success_statement)
        self._print_to_out_file(success_statement)
        self._redisplay_progress()

    def _print_failure(self, result, **kwargs):
        failure_statement = self.FAILURE_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result),
            exception=result.exception
        )
        failure_statement = self._adjust_statement_padding(failure_statement)
        self._print_to_error_file(failure_statement)
        self._redisplay_progress()

    def _print_warning(self, result, **kwargs):
        warning_statement = self.WARNING_FORMAT.format(message=result.message)
        warning_statement = self._adjust_statement_padding(warning_statement)
        self._print_to_error_file(warning_statement)
        self._redisplay_progress()

    def _print_error(self, result, **kwargs):
        self._flush_error_statement(
            self.ERROR_FORMAT.format(exception=result.exception))

    def _print_ctrl_c(self, result, **kwargs):
        self._flush_error_statement(self.CTRL_C_MSG)

    def _flush_error_statement(self, error_statement):
        error_statement = self._adjust_statement_padding(error_statement)
        self._print_to_error_file(error_statement)

    def _get_transfer_location(self, result):
        if result.dest is None:
            return self.SRC_TRANSFER_LOCATION_FORMAT.format(src=result.src)
        return self.SRC_DEST_TRANSFER_LOCATION_FORMAT.format(
            src=result.src, dest=result.dest)

    def _redisplay_progress(self):
        # Reset to zero because done statements are printed with new lines
        # meaning there are no carriage returns to take into account when
        # printing the next line.
        self._progress_length = 0
        self._add_progress_if_needed()

    def _add_progress_if_needed(self):
        if self._has_remaining_progress():
            self._print_progress()

    def _print_progress(self, **kwargs):
        # Get all of the statistics in the correct form.
        remaining_files = self._get_expected_total(
            str(self._result_recorder.expected_files_transferred -
                self._result_recorder.files_transferred)
        )

        # Create the display statement.
        if self._result_recorder.expected_bytes_transferred > 0:
            bytes_completed = human_readable_size(
                self._result_recorder.bytes_transferred +
                self._result_recorder.bytes_failed_to_transfer
            )
            expected_bytes_completed = self._get_expected_total(
                human_readable_size(
                    self._result_recorder.expected_bytes_transferred))

            transfer_speed = human_readable_size(
                self._result_recorder.bytes_transfer_speed) + '/s'
            progress_statement = self.BYTE_PROGRESS_FORMAT.format(
                bytes_completed=bytes_completed,
                expected_bytes_completed=expected_bytes_completed,
                transfer_speed=transfer_speed,
                remaining_files=remaining_files
            )
        else:
            # We're not expecting any bytes to be transferred, so we should
            # only print of information about number of files transferred.
            progress_statement = self.FILE_PROGRESS_FORMAT.format(
                files_completed=self._result_recorder.files_transferred,
                remaining_files=remaining_files
            )

        if not self._result_recorder.expected_totals_are_final():
            progress_statement += self._STILL_CALCULATING_TOTALS

        # Make sure that it overrides any previous progress bar.
        progress_statement = self._adjust_statement_padding(
                progress_statement, ending_char='\r')
        # We do not want to include the carriage return in this calculation
        # as progress length is used for determining whitespace padding.
        # So we subtract one off of the length.
        self._progress_length = len(progress_statement) - 1

        # Print the progress out.
        self._print_to_out_file(progress_statement)

    def _get_expected_total(self, expected_total):
        if not self._result_recorder.expected_totals_are_final():
            return self._ESTIMATED_EXPECTED_TOTAL.format(
                expected_total=expected_total)
        return expected_total

    def _adjust_statement_padding(self, print_statement, ending_char='\n'):
        print_statement = print_statement.ljust(self._progress_length, ' ')
        return print_statement + ending_char

    def _has_remaining_progress(self):
        if not self._result_recorder.expected_totals_are_final():
            return True
        actual = self._result_recorder.files_transferred
        expected = self._result_recorder.expected_files_transferred
        return actual != expected

    def _print_to_out_file(self, statement):
        uni_print(statement, self._out_file)

    def _print_to_error_file(self, statement):
        uni_print(statement, self._error_file)

    def _clear_progress_if_no_more_expected_transfers(self, **kwargs):
        if self._progress_length and not self._has_remaining_progress():
            uni_print(self._adjust_statement_padding(''), self._out_file)


class OnlyShowErrorsResultPrinter(ResultPrinter):
    """A result printer that only prints out errors"""
    def _print_progress(self, **kwargs):
        pass

    def _print_success(self, result, **kwargs):
        pass


class ResultProcessor(threading.Thread):
    def __init__(self, result_queue, result_handlers=None):
        """Thread to process results from result queue

        This includes recording statistics and printing transfer status

        :param result_queue: The result queue to process results from
        :param result_handlers: A list of callables that take a result in as
            a parameter to process the result for that handler.
        """
        threading.Thread.__init__(self)
        self._result_queue = result_queue
        self._result_handlers = result_handlers
        if self._result_handlers is None:
            self._result_handlers = []
        self._result_handlers_enabled = True

    def run(self):
        while True:
            try:
                result = self._result_queue.get(True)
                if isinstance(result, ShutdownThreadRequest):
                    LOGGER.debug(
                        'Shutdown request received in result processing '
                        'thread, shutting down result thread.')
                    break
                if self._result_handlers_enabled:
                    self._process_result(result)
                # ErrorResults are fatal to the command. If a fatal error
                # is seen, we know that the command is trying to shutdown
                # so disable all of the handlers and quickly consume all
                # of the results in the result queue in order to get to
                # the shutdown request to clean up the process.
                if isinstance(result, ErrorResult):
                    self._result_handlers_enabled = False
            except queue.Empty:
                pass

    def _process_result(self, result):
        for result_handler in self._result_handlers:
            try:
                result_handler(result)
            except Exception as e:
                LOGGER.debug(
                    'Error processing result %s with handler %s: %s',
                    result, result_handler, e, exc_info=True)


class CommandResultRecorder(object):
    def __init__(self, result_queue, result_recorder, result_processor):
        """Records the result for an entire command

        It will fully process all results in a result queue and determine
        a CommandResult representing the entire command.

        :type result_queue: queue.Queue
        :param result_queue: The result queue in which results are placed on
            and processed from

        :type result_recorder: ResultRecorder
        :param result_recorder: The result recorder to track the various
            results sent through the result queue

        :type result_processor: ResultProcessor
        :param result_processor: The result processor to process results
            placed on the queue
        """
        self.result_queue = result_queue
        self._result_recorder = result_recorder
        self._result_processor = result_processor

    def start(self):
        self._result_processor.start()

    def shutdown(self):
        self.result_queue.put(ShutdownThreadRequest())
        self._result_processor.join()

    def get_command_result(self):
        """Get the CommandResult representing the result of a command

        :rtype: CommandResult
        :returns: The CommandResult representing the total result from running
            a particular command
        """
        return CommandResult(
            self._result_recorder.files_failed + self._result_recorder.errors,
            self._result_recorder.files_warned
        )

    def notify_total_submissions(self, total):
        self.result_queue.put(FinalTotalSubmissionsResult(total))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, *args):
        if exc_type:
            LOGGER.debug('Exception caught during command execution: %s',
                         exc_value, exc_info=True)
            self.result_queue.put(ErrorResult(exception=exc_value))
            self.shutdown()
            return True
        self.shutdown()
