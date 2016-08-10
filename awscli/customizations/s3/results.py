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


LOGGER = logging.getLogger(__name__)

QueuedResult = namedtuple(
    'QueuedResult',
    ['transfer_type', 'src', 'dest', 'total_transfer_size']
)
ProgressResult = namedtuple(
    'ProgressResult',
    ['transfer_type', 'src', 'dest', 'bytes_transferred',
     'total_transfer_size']
)
SuccessResult = namedtuple(
    'SuccessResult', ['transfer_type', 'src', 'dest']
)
FailureResult = namedtuple(
    'FailureResult', ['transfer_type', 'src', 'dest', 'exception']
)
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
        self._transfer_type = None

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
        raise NotImplementedError('must implement _get_src_dest()')


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
