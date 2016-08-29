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
import logging
import sys
import threading
from collections import namedtuple
from collections import defaultdict

from s3transfer.subscribers import BaseSubscriber

from awscli.compat import queue
from awscli.customizations.s3.executor import ShutdownThreadRequest
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
    'ProgressResult', ['bytes_transferred', 'total_transfer_size'])

SuccessResult = _create_new_result_cls('SuccessResult')

FailureResult = _create_new_result_cls('FailureResult', ['exception'])

ErrorResult = namedtuple('ErrorResult', ['exception'])

CommandResult = namedtuple(
    'CommandResult', ['num_tasks_failed', 'num_tasks_warned'])


class BaseResultSubscriber(OnDoneFilteredSubscriber):
    TRANSFER_TYPE = None

    def __init__(self, result_queue):
        """Subscriber to send result notifications during transfer process

        :param result_queue: The queue to place results to be processed later
            on.
        """
        self._result_queue = result_queue

    def on_queued(self, future, **kwargs):
        src, dest = self._get_src_dest(future)
        queued_result = QueuedResult(
            self.TRANSFER_TYPE, src, dest, future.meta.size)
        self._result_queue.put(queued_result)

    def on_progress(self, future, bytes_transferred, **kwargs):
        src, dest = self._get_src_dest(future)
        progress_result = ProgressResult(
            self.TRANSFER_TYPE, src, dest, bytes_transferred, future.meta.size)
        self._result_queue.put(progress_result)

    def _on_success(self, future):
        src, dest = self._get_src_dest(future)
        self._result_queue.put(
            SuccessResult(self.TRANSFER_TYPE, src, dest))

    def _on_failure(self, future, e):
        src, dest = self._get_src_dest(future)
        self._result_queue.put(
            FailureResult(self.TRANSFER_TYPE, src, dest, e))

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

        self._ongoing_progress = defaultdict(int)
        self._ongoing_total_sizes = {}

        self._result_handler_map = {
            QueuedResult: self._record_queued_result,
            ProgressResult: self._record_progress_result,
            SuccessResult: self._record_success_result,
            FailureResult: self._record_failure_result,
            WarningResult: self._record_warning_result,
            ErrorResult: self._record_error_result
        }

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
        return ':'.join([result.transfer_type, result.src, result.dest])

    def _pop_result_from_ongoing_dicts(self, result):
        ongoing_key = self._get_ongoing_dict_key(result)
        total_progress = self._ongoing_progress.pop(ongoing_key, 0)
        total_file_size = self._ongoing_total_sizes.pop(ongoing_key, None)
        return total_progress, total_file_size

    def _record_noop(self, **kwargs):
        # If the result does not have a handler, then do nothing with it.
        pass

    def _record_queued_result(self, result, **kwargs):
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


class ResultPrinter(BaseResultHandler):
    PROGRESS_FORMAT = (
        'Completed {bytes_completed}/{expected_bytes_completed} with '
        '{remaining_files} file(s) remaining.'
    )
    SUCCESS_FORMAT = (
        '{transfer_type}: {src} to {dest}'
    )
    FAILURE_FORMAT = (
        '{transfer_type} failed: {src} to {dest} {exception}'
    )
    # TODO: Add "warning: " prefix once all commands are converted to using
    # result printer and remove "warning: " prefix from ``create_warning``.
    WARNING_FORMAT = (
        '{message}'
    )
    ERROR_FORMAT = (
        '{exception}'
    )

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
        }

    def __call__(self, result):
        """Print the progress of the ongoing transfer based on a result"""
        self._result_handler_map.get(type(result), self._print_noop)(
            result=result)

    def _print_noop(self, **kwargs):
        # If the result does not have a handler, then do nothing with it.
        pass

    def _print_success(self, result, **kwargs):
        success_statement = self.SUCCESS_FORMAT.format(
            transfer_type=result.transfer_type, src=result.src,
            dest=result.dest)
        success_statement = self._adjust_statement_padding(success_statement)
        self._print_to_out_file(success_statement)
        self._redisplay_progress()

    def _print_failure(self, result, **kwargs):
        failure_statement = self.FAILURE_FORMAT.format(
            transfer_type=result.transfer_type, src=result.src,
            dest=result.dest, exception=result.exception)
        failure_statement = self._adjust_statement_padding(failure_statement)
        self._print_to_error_file(failure_statement)
        self._redisplay_progress()

    def _print_warning(self, result, **kwargs):
        warning_statement = self.WARNING_FORMAT.format(message=result.message)
        warning_statement = self._adjust_statement_padding(warning_statement)
        self._print_to_error_file(warning_statement)
        self._redisplay_progress()

    def _print_error(self, result, **kwargs):
        error_statement = self.ERROR_FORMAT.format(exception=result.exception)
        error_statement = self._adjust_statement_padding(error_statement)
        self._print_to_error_file(error_statement)

    def _redisplay_progress(self):
        # Reset to zero because done statements are printed with new lines
        # meaning there are no carriage returns to take into account when
        # printing the next line.
        self._progress_length = 0
        self._add_progress_if_needed()

    def _add_progress_if_needed(self):
        if not self._has_remaining_progress():
            self._print_progress()

    def _print_progress(self, **kwargs):
        # Get all of the statistics in the correct form.
        bytes_completed = human_readable_size(
            self._result_recorder.bytes_transferred +
            self._result_recorder.bytes_failed_to_transfer
        )
        expected_bytes_completed = human_readable_size(
            self._result_recorder.expected_bytes_transferred)
        remaining_files = str(
            self._result_recorder.expected_files_transferred -
            self._result_recorder.files_transferred
        )

        # Create the display statement.
        progress_statement = self.PROGRESS_FORMAT.format(
            bytes_completed=bytes_completed,
            expected_bytes_completed=expected_bytes_completed,
            remaining_files=remaining_files
        )

        # Make sure that it overrides any previous progress bar.
        progress_statement = self._adjust_statement_padding(
                progress_statement, ending_char='\r')
        # We do not want to include the carriage return in this calculation
        # as progress length is used for determining whitespace padding.
        # So we subtract one off of the length.
        self._progress_length = len(progress_statement) - 1

        # Print the progress out.
        self._print_to_out_file(progress_statement)

    def _adjust_statement_padding(self, print_statement, ending_char='\n'):
        print_statement = print_statement.ljust(self._progress_length, ' ')
        return print_statement + ending_char

    def _has_remaining_progress(self):
        actual = self._result_recorder.files_transferred
        expected = self._result_recorder.expected_files_transferred
        return actual == expected

    def _print_to_out_file(self, statement):
        uni_print(statement, self._out_file)

    def _print_to_error_file(self, statement):
        uni_print(statement, self._error_file)


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

    def run(self):
        while True:
            try:
                result = self._result_queue.get(True)
                if isinstance(result, ShutdownThreadRequest):
                    LOGGER.debug(
                        'Shutdown request received in result processing '
                        'thread, shutting down result thread.')
                    break
                LOGGER.debug('Received result: %s', result)
                self._process_result(result)
            except queue.Empty:
                pass

    def _process_result(self, result):
        for result_handler in self._result_handlers:
            try:
                LOGGER.debug('Processing %s with %s', result, result_handler)
                result_handler(result)
            except Exception as e:
                LOGGER.debug(
                    'Error processing result %s with handler %s: %s',
                    result, result_handler, e, exc_info=True)
