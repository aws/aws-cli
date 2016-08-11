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
from collections import namedtuple
import logging
import math
import os
import sys

from s3transfer.manager import TransferManager

from awscli.customizations.s3.utils import (
    find_chunksize, adjust_chunksize_to_upload_limits, MAX_UPLOAD_SIZE,
    find_bucket_key, relative_path, PrintTask, create_warning,
    NonSeekableStream)
from awscli.customizations.s3.executor import Executor
from awscli.customizations.s3 import tasks
from awscli.customizations.s3.transferconfig import RuntimeConfig, \
    create_transfer_config_from_runtime_config
from awscli.customizations.s3.utils import RequestParamsMapper
from awscli.customizations.s3.utils import StdoutBytesWriter
from awscli.customizations.s3.utils import ProvideSizeSubscriber
from awscli.customizations.s3.utils import uni_print
from awscli.compat import queue
from awscli.compat import binary_stdin


LOGGER = logging.getLogger(__name__)

CommandResult = namedtuple('CommandResult',
                           ['num_tasks_failed', 'num_tasks_warned'])


class BaseS3Handler(object):
    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        self.session = session
        if runtime_config is None:
            runtime_config = RuntimeConfig.defaults()
        self._runtime_config = runtime_config
        self.result_queue = result_queue
        if not self.result_queue:
            self.result_queue = queue.Queue()

        self.params = {
            'dryrun': False, 'quiet': False, 'acl': None,
            'guess_mime_type': True, 'sse_c_copy_source': None,
            'sse_c_copy_source_key': None, 'sse': None,
            'sse_c': None, 'sse_c_key': None, 'sse_kms_key_id': None,
            'storage_class': None, 'website_redirect': None,
            'content_type': None, 'cache_control': None,
            'content_disposition': None, 'content_encoding': None,
            'content_language': None, 'expires': None, 'grants': None,
            'only_show_errors': False, 'is_stream': False,
            'paths_type': None, 'expected_size': None, 'metadata': None,
            'metadata_directive': None, 'ignore_glacier_warnings': False,
            'force_glacier_transfer': False
        }
        self.params['region'] = params['region']
        for key in self.params.keys():
            if key in params:
                self.params[key] = params[key]


class S3Handler(BaseS3Handler):
    """
    This class sets up the process to perform the tasks sent to it.  It
    sources the ``self.executor`` from which threads inside the
    class pull tasks from to complete.
    """
    MAX_IO_QUEUE_SIZE = 20

    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        super(S3Handler, self).__init__(
            session, params, result_queue, runtime_config)
        # The write_queue has potential for optimizations, so the constant
        # for maxsize is scoped to this class (as opposed to constants.py)
        # so we have the ability to change this value later.
        self.write_queue = queue.Queue(maxsize=self.MAX_IO_QUEUE_SIZE)
        self.multi_threshold = self._runtime_config['multipart_threshold']
        self.chunksize = self._runtime_config['multipart_chunksize']
        LOGGER.debug("Using a multipart threshold of %s and a part size of %s",
                     self.multi_threshold, self.chunksize)
        self.executor = Executor(
            num_threads=self._runtime_config['max_concurrent_requests'],
            result_queue=self.result_queue,
            quiet=self.params['quiet'],
            only_show_errors=self.params['only_show_errors'],
            max_queue_size=self._runtime_config['max_queue_size'],
            write_queue=self.write_queue
        )
        self._multipart_uploads = []
        self._multipart_downloads = []

    def call(self, files):
        """
        This function pulls a ``FileInfo`` or ``TaskInfo`` object from
        a list ``files``.  Each object is then deemed if it will be a
        multipart operation and add the necessary attributes if so.  Each
        object is then wrapped with a ``BasicTask`` object which is
        essentially a thread of execution for a thread to follow.  These
        tasks are then submitted to the main executor.
        """
        try:
            self.executor.start()
            total_files, total_parts = self._enqueue_tasks(files)
            self.executor.print_thread.set_total_files(total_files)
            self.executor.print_thread.set_total_parts(total_parts)
            self.executor.initiate_shutdown()
            self._finalize_shutdown()
        except Exception as e:
            LOGGER.debug('Exception caught during task execution: %s',
                         str(e), exc_info=True)
            self.result_queue.put(PrintTask(message=str(e), error=True))
            self.executor.initiate_shutdown(
                priority=self.executor.IMMEDIATE_PRIORITY)
            self._finalize_shutdown()
        except KeyboardInterrupt:
            self.result_queue.put(PrintTask(message=("Cleaning up. "
                                                     "Please wait..."),
                                            error=True))
            self.executor.initiate_shutdown(
                priority=self.executor.IMMEDIATE_PRIORITY)
            self._finalize_shutdown()
        return CommandResult(self.executor.num_tasks_failed,
                             self.executor.num_tasks_warned)

    def _finalize_shutdown(self):
        # Run all remaining tasks needed to completely shutdown the
        # S3 handler.  This method will block until shutdown is complete.
        # The order here is important.  We need to wait until all the
        # tasks have been completed before we can cleanup.  Otherwise
        # we can have race conditions where we're trying to cleanup
        # uploads/downloads that are still in progress.
        self.executor.wait_until_shutdown()
        self._cleanup()

    def _cleanup(self):
        # And finally we need to make a pass through all the existing
        # multipart uploads and abort any pending multipart uploads.
        self._abort_pending_multipart_uploads()
        self._remove_pending_downloads()

    def _abort_pending_multipart_uploads(self):
        # precondition: this method is assumed to be called when there are no ongoing
        # uploads (the executor has been shutdown).
        for upload, filename in self._multipart_uploads:
            if upload.is_cancelled() or upload.in_progress():
                # Cancel any upload that's not unstarted and not complete.
                upload.cancel_upload(self._cancel_upload, args=(filename,))

    def _remove_pending_downloads(self):
        # The downloads case is easier than the uploads case because we don't
        # need to make any service calls.  To properly cleanup we just need
        # to go through the multipart downloads that were in progress but
        # cancelled and remove the local file.
        for context, local_filename in self._multipart_downloads:
            if (context.is_cancelled() or context.is_started()) and \
                    os.path.exists(local_filename):
                # The file is in an inconsistent state (not all the parts
                # were written to the file) so we should remove the
                # local file rather than leave it in a bad state.  We don't
                # want to remove the files if the download has *not* been
                # started because we haven't touched the file yet, so it's
                # better to leave the old version of the file rather than
                # deleting the file entirely.
                os.remove(local_filename)
            context.cancel()

    def _cancel_upload(self, upload_id, filename):
        bucket, key = find_bucket_key(filename.dest)
        params = {
            'Bucket': bucket,
            'Key': key,
            'UploadId': upload_id,
        }
        LOGGER.debug("Aborting multipart upload for: %s", key)
        filename.client.abort_multipart_upload(**params)

    def _enqueue_tasks(self, files):
        total_files = 0
        total_parts = 0
        for filename in files:
            num_uploads = 1
            is_multipart_task = self._is_multipart_task(filename)
            too_large = False
            if hasattr(filename, 'size'):
                too_large = filename.size > MAX_UPLOAD_SIZE
            if too_large and filename.operation_name == 'upload':
                warning_message = "File exceeds s3 upload limit of 5 TB."
                warning = create_warning(relative_path(filename.src),
                                         warning_message)
                self.result_queue.put(warning)
            # Warn and skip over glacier incompatible tasks.
            elif not self.params.get('force_glacier_transfer') and \
                    not filename.is_glacier_compatible():
                LOGGER.debug(
                    'Encountered glacier object s3://%s. Not performing '
                    '%s on object.' % (filename.src, filename.operation_name))
                if not self.params['ignore_glacier_warnings']:
                    warning = create_warning(
                        's3://'+filename.src,
                        'Object is of storage class GLACIER. Unable to '
                        'perform %s operations on GLACIER objects. You must '
                        'restore the object to be able to the perform '
                        'operation.' %
                        filename.operation_name
                    )
                    self.result_queue.put(warning)
                continue
            elif is_multipart_task and not self.params['dryrun']:
                # If we're in dryrun mode, then we don't need the
                # real multipart tasks.  We can just use a BasicTask
                # in the else clause below, which will print out the
                # fact that it's transferring a file rather than
                # the specific part tasks required to perform the
                # transfer.
                num_uploads = self._enqueue_multipart_tasks(filename)
            else:
                task = tasks.BasicTask(
                    session=self.session, filename=filename,
                    parameters=self.params,
                    result_queue=self.result_queue)
                self.executor.submit(task)
            total_files += 1
            total_parts += num_uploads
        return total_files, total_parts

    def _is_multipart_task(self, filename):
        # First we need to determine if it's an operation that even
        # qualifies for multipart upload.
        if hasattr(filename, 'size'):
            above_multipart_threshold = filename.size > self.multi_threshold
            if above_multipart_threshold:
                if filename.operation_name in ('upload', 'download',
                                               'move', 'copy'):
                    return True
                else:
                    return False
        else:
            return False

    def _enqueue_multipart_tasks(self, filename):
        num_uploads = 1
        if filename.operation_name == 'upload':
            num_uploads = self._enqueue_multipart_upload_tasks(filename)
        elif filename.operation_name == 'move':
            if filename.src_type == 'local' and filename.dest_type == 's3':
                num_uploads = self._enqueue_multipart_upload_tasks(
                    filename, remove_local_file=True)
            elif filename.src_type == 's3' and filename.dest_type == 'local':
                num_uploads = self._enqueue_range_download_tasks(
                    filename, remove_remote_file=True)
            elif filename.src_type == 's3' and filename.dest_type == 's3':
                num_uploads = self._enqueue_multipart_copy_tasks(
                    filename, remove_remote_file=True)
            else:
                raise ValueError("Unknown transfer type of %s -> %s" %
                                 (filename.src_type, filename.dest_type))
        elif filename.operation_name == 'copy':
            num_uploads = self._enqueue_multipart_copy_tasks(
                filename, remove_remote_file=False)
        elif filename.operation_name == 'download':
            num_uploads = self._enqueue_range_download_tasks(filename)
        return num_uploads

    def _enqueue_range_download_tasks(self, filename, remove_remote_file=False):
        num_downloads = int(filename.size / self.chunksize)
        context = tasks.MultipartDownloadContext(num_downloads)
        create_file_task = tasks.CreateLocalFileTask(
            context=context, filename=filename,
            result_queue=self.result_queue)
        self.executor.submit(create_file_task)
        self._do_enqueue_range_download_tasks(
            filename=filename, chunksize=self.chunksize,
            num_downloads=num_downloads, context=context,
            remove_remote_file=remove_remote_file
        )
        complete_file_task = tasks.CompleteDownloadTask(
            context=context, filename=filename, result_queue=self.result_queue,
            params=self.params, io_queue=self.write_queue)
        self.executor.submit(complete_file_task)
        self._multipart_downloads.append((context, filename.dest))
        if remove_remote_file:
            remove_task = tasks.RemoveRemoteObjectTask(
                filename=filename, context=context)
            self.executor.submit(remove_task)
        return num_downloads

    def _do_enqueue_range_download_tasks(self, filename, chunksize,
                                         num_downloads, context,
                                         remove_remote_file=False):
        for i in range(num_downloads):
            task = tasks.DownloadPartTask(
                part_number=i, chunk_size=chunksize,
                result_queue=self.result_queue, filename=filename,
                context=context, io_queue=self.write_queue,
                params=self.params)
            self.executor.submit(task)

    def _enqueue_multipart_upload_tasks(self, filename,
                                        remove_local_file=False):
        # First we need to create a CreateMultipartUpload task,
        # then create UploadTask objects for each of the parts.
        # And finally enqueue a CompleteMultipartUploadTask.
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_uploads = int(math.ceil(filename.size /
                                    float(chunksize)))
        upload_context = self._enqueue_upload_start_task(
            chunksize, num_uploads, filename)
        self._enqueue_upload_tasks(
            num_uploads, chunksize, upload_context, filename, tasks.UploadPartTask)
        self._enqueue_upload_end_task(filename, upload_context)
        if remove_local_file:
            remove_task = tasks.RemoveFileTask(local_filename=filename.src,
                                               upload_context=upload_context)
            self.executor.submit(remove_task)
        return num_uploads

    def _enqueue_multipart_copy_tasks(self, filename,
                                      remove_remote_file=False):
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_uploads = int(math.ceil(filename.size / float(chunksize)))
        upload_context = self._enqueue_upload_start_task(
            chunksize, num_uploads, filename)
        self._enqueue_upload_tasks(
            num_uploads, chunksize, upload_context, filename, tasks.CopyPartTask)
        self._enqueue_upload_end_task(filename, upload_context)
        if remove_remote_file:
            remove_task = tasks.RemoveRemoteObjectTask(
                filename=filename, context=upload_context)
            self.executor.submit(remove_task)
        return num_uploads

    def _enqueue_upload_start_task(self, chunksize, num_uploads, filename):
        upload_context = tasks.MultipartUploadContext(
            expected_parts=num_uploads)
        create_multipart_upload_task = tasks.CreateMultipartUploadTask(
            session=self.session, filename=filename,
            parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executor.submit(create_multipart_upload_task)
        self._multipart_uploads.append((upload_context, filename))
        return upload_context

    def _enqueue_upload_tasks(self, num_uploads, chunksize, upload_context,
                              filename, task_class):
        for i in range(1, (num_uploads + 1)):
            self._enqueue_upload_single_part_task(
                part_number=i,
                chunk_size=chunksize,
                upload_context=upload_context,
                filename=filename,
                task_class=task_class
            )

    def _enqueue_upload_single_part_task(self, part_number, chunk_size,
                                         upload_context, filename, task_class,
                                         payload=None):
        kwargs = {'part_number': part_number, 'chunk_size': chunk_size,
                  'result_queue': self.result_queue,
                  'upload_context': upload_context, 'filename': filename,
                  'params': self.params}
        if payload:
            kwargs['payload'] = payload
        task = task_class(**kwargs)
        self.executor.submit(task)

    def _enqueue_upload_end_task(self, filename, upload_context):
        complete_multipart_upload_task = tasks.CompleteMultipartUploadTask(
            session=self.session, filename=filename, parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executor.submit(complete_multipart_upload_task)


class S3TransferStreamHandler(BaseS3Handler):
    """
    This class is an alternative ``S3Handler`` to be used when the operation
    involves a stream since the logic is different when uploading and
    downloading streams.
    """
    MAX_IN_MEMORY_CHUNKS = 6

    def __init__(self, session, params, result_queue=None,
                 runtime_config=None, manager=None):
        super(S3TransferStreamHandler, self).__init__(
            session, params, result_queue, runtime_config)
        self.config = create_transfer_config_from_runtime_config(
            self._runtime_config)

        # Restrict the maximum chunks to 1 per thread.
        self.config.max_in_memory_upload_chunks = \
            self.MAX_IN_MEMORY_CHUNKS
        self.config.max_in_memory_download_chunks = \
            self.MAX_IN_MEMORY_CHUNKS

        self._manager = manager

    def call(self, files):
        # There is only ever one file in a stream transfer.
        file = files[0]
        if self._manager is not None:
            manager = self._manager
        else:
            manager = TransferManager(file.client, self.config)

        if file.operation_name == 'upload':
            bucket, key = find_bucket_key(file.dest)
            return self._upload(manager, bucket, key)
        elif file.operation_name == 'download':
            bucket, key = find_bucket_key(file.src)
            return self._download(manager, bucket, key)

    def _download(self, manager, bucket, key):
        """
        Download the specified object and print it to stdout.

        :type manager: s3transfer.manager.TransferManager
        :param manager: The transfer manager to use for the download.

        :type bucket: str
        :param bucket: The bucket to download the object from.

        :type key: str
        :param key: The name of the key to download.

        :return: A CommandResult representing the download status.
        """
        params = {}
        # `download` performs the head_object as well, but the params are
        # the same for both operations, so there's nothing missing here.
        RequestParamsMapper.map_get_object_params(params, self.params)

        with manager:
            future = manager.download(
                fileobj=StdoutBytesWriter(), bucket=bucket,
                key=key, extra_args=params)

            return self._process_transfer(future)

    def _upload(self, manager, bucket, key):
        """
        Upload stdin using to the specified location.

        :type manager: s3transfer.manager.TransferManager
        :param manager: The transfer manager to use for the upload.

        :type bucket: str
        :param bucket: The bucket to upload the stream to.

        :type key: str
        :param key: The name of the key to upload the stream to.

        :return: A CommandResult representing the upload status.
        """
        expected_size = self.params.get('expected_size', None)
        subscribers = None
        if expected_size is not None:
            # `expected_size` comes in as a string
            expected_size = int(expected_size)

            # set the size of the transfer if we know it ahead of time.
            subscribers = [ProvideSizeSubscriber(expected_size)]

            # TODO: remove when this happens in s3transfer
            # If we have the expected size, we can calculate an appropriate
            # chunksize based on max parts and chunksize limits
            chunksize = find_chunksize(
                expected_size, self.config.multipart_chunksize)
        else:
            # TODO: remove when this happens in s3transfer
            # Otherwise, we can still adjust for chunksize limits
            chunksize = adjust_chunksize_to_upload_limits(
                self.config.multipart_chunksize)
        self.config.multipart_chunksize = chunksize

        params = {}
        RequestParamsMapper.map_put_object_params(params, self.params)

        fileobj = NonSeekableStream(binary_stdin)
        with manager:
            future = manager.upload(
                fileobj=fileobj, bucket=bucket,
                key=key, extra_args=params, subscribers=subscribers)

            return self._process_transfer(future)

    def _process_transfer(self, future):
        """
        Execute and process a transfer future.

        :type future: s3transfer.futures.TransferFuture
        :param future: A future representing an S3 Transfer

        :return: A CommandResult representing the transfer status.
        """
        try:
            future.result()
            return CommandResult(0, 0)
        except Exception as e:
            LOGGER.debug('Exception caught during task execution: %s',
                         str(e), exc_info=True)
            # TODO: Update when S3Handler is refactored
            uni_print("Transfer failed: %s \n" % str(e))
            return CommandResult(1, 0)
