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
from collections import namedtuple

from s3transfer.subscribers import BaseSubscriber

from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.utils import WarningResult


LOGGER = logging.getLogger(__name__)


def _create_new_result_cls(name, extra_fields=None):
    # Creates a new namedtuple class that subclasses from BaseResult for the
    # benefit of filtering by type and ensuring particular base attrs.

    # NOTE: _fields is a public attribute that has an underscore to avoid
    # naming collisions for namedtuples:
    # https://docs.python.org/2/library/collections.html#collections.somenamedtuple._fields
    fields = list(BaseResult._fields)
    if extra_fields:
        fields += extra_fields
    return type(name, (namedtuple(name, fields), BaseResult), {})


BaseResult = namedtuple('BaseResult', ['transfer_type', 'src', 'dest'])

QueuedResult = _create_new_result_cls('QueuedResult', ['total_transfer_size'])

ProgressResult = _create_new_result_cls(
    'ProgressResult', ['bytes_transferred', 'total_transfer_size'])

SuccessResult = _create_new_result_cls('SuccessResult')

FailureResult = _create_new_result_cls('FailureResult', ['exception'])

CommandResult = namedtuple(
    'CommandResult', ['num_tasks_failed', 'num_tasks_warned'])


class BaseResultSubscriber(BaseSubscriber):
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

    def on_done(self, future, **kwargs):
        src, dest = self._get_src_dest(future)
        try:
            future.result()
            self._result_queue.put(
                SuccessResult(self.TRANSFER_TYPE, src, dest))
        except Exception as e:
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


class ResultRecorder(object):
    """Records and track transfer statistics based on results receieved"""
    def __init__(self):
        self.bytes_transferred = 0
        self.bytes_failed_to_transfer = 0
        self.files_transferred = 0
        self.files_failed = 0
        self.files_warned = 0
        self.expected_bytes_transferred = 0
        self.expected_files_transferred = 0

        # Keys: result from _get_progress_cache_key()
        # Values: number of bytes left for a particular transfer
        self._progress_remaining_cache = {}

        self._result_handler_map = {
            QueuedResult: self._record_queued_result,
            ProgressResult: self._record_progress_result,
            SuccessResult: self._record_success_result,
            FailureResult: self._record_failure_result,
            WarningResult: self._record_warning_result,
        }

    def record_result(self, result):
        """Record the result of an individual Result object"""
        self._result_handler_map.get(type(result), self._record_noop)(
            result=result)

    def _get_progress_cache_key(self, result):
        if not isinstance(result, BaseResult):
            raise ValueError(
                'Any result using _get_progress_cache_key must subclass from '
                'BaseResult. Provided result is of type: %s' % type(result)
            )
        return ':'.join([result.transfer_type, result.src, result.dest])

    def _pop_result_from_caches(self, result):
        total_progress = self._progress_cache.pop(
            self._get_progress_cache_key(result))
        total_file_size = self._total_size_cache.pop(
            self._get_progress_cache_key(result))
        return total_progress, total_file_size

    def _record_noop(self, **kwargs):
        # If the result does not have a handler, then do nothing with it.
        pass

    def _record_queued_result(self, result, **kwargs):
        self._progress_remaining_cache[
            self._get_progress_cache_key(result)] = result.total_transfer_size
        self.expected_files_transferred += 1
        self.expected_bytes_transferred += result.total_transfer_size

    def _record_progress_result(self, result, **kwargs):
        self._progress_remaining_cache[
            self._get_progress_cache_key(result)] -= result.bytes_transferred
        self.bytes_transferred += result.bytes_transferred

    def _record_success_result(self, result, **kwargs):
        self._progress_remaining_cache.pop(
            self._get_progress_cache_key(result))
        self.files_transferred += 1

    def _record_failure_result(self, result, **kwargs):
        # If there was a failure, we want to account for the failure in
        # the count for bytes transferred by just adding on the remaining bytes
        # that did not get transferred.
        progress_left = self._progress_remaining_cache.pop(
            self._get_progress_cache_key(result))

        self.bytes_failed_to_transfer += progress_left

        self.files_failed += 1
        self.files_transferred += 1

    def _record_warning_result(self, **kwargs):
        self.files_warned += 1
