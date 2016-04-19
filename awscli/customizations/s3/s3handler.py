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

from awscli.customizations.s3.utils import (
    find_chunksize, adjust_chunksize_to_upload_limits, MAX_UPLOAD_SIZE,
    find_bucket_key, relative_path, PrintTask, create_warning)
from awscli.customizations.s3.executor import Executor
from awscli.customizations.s3 import tasks
from awscli.customizations.s3.transferconfig import RuntimeConfig
from awscli.compat import six
from awscli.compat import queue


LOGGER = logging.getLogger(__name__)

CommandResult = namedtuple('CommandResult',
                           ['num_tasks_failed', 'num_tasks_warned'])


class S3Handler(object):
    """
    This class sets up the process to perform the tasks sent to it.  It
    sources the ``self.executor`` from which threads inside the
    class pull tasks from to complete.
    """
    MAX_IO_QUEUE_SIZE = 20

    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        self.session = session
        if runtime_config is None:
            runtime_config = RuntimeConfig.defaults()
        self._runtime_config = runtime_config
        # The write_queue has potential for optimizations, so the constant
        # for maxsize is scoped to this class (as opposed to constants.py)
        # so we have the ability to change this value later.
        self.write_queue = queue.Queue(maxsize=self.MAX_IO_QUEUE_SIZE)
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


class S3StreamHandler(S3Handler):
    """
    This class is an alternative ``S3Handler`` to be used when the operation
    involves a stream since the logic is different when uploading and
    downloading streams.
    """
    # This ensures that the number of multipart chunks waiting in the
    # executor queue and in the threads is limited.
    MAX_EXECUTOR_QUEUE_SIZE = 2
    EXECUTOR_NUM_THREADS = 6

    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        if runtime_config is None:
            # Rather than using the .defaults(), streaming
            # has different default values so that it does not
            # consume large amounts of memory.
            runtime_config = RuntimeConfig().build_config(
                max_queue_size=self.MAX_EXECUTOR_QUEUE_SIZE,
                max_concurrent_requests=self.EXECUTOR_NUM_THREADS)
        super(S3StreamHandler, self).__init__(session, params, result_queue,
                                              runtime_config)

    def _enqueue_tasks(self, files):
        total_files = 0
        total_parts = 0
        for filename in files:
            num_uploads = 1
            # If uploading stream, it is required to read from the stream
            # to determine if the stream needs to be multipart uploaded.
            payload = None
            if filename.operation_name == 'upload':
                payload, is_multipart_task = \
                    self._pull_from_stream(self.multi_threshold)
            else:
                # Set the file size for the ``FileInfo`` object since
                # streams do not use a ``FileGenerator`` that usually
                # determines the size.
                filename.set_size_from_s3()
                is_multipart_task = self._is_multipart_task(filename)
            if is_multipart_task and not self.params['dryrun']:
                # If we're in dryrun mode, then we don't need the
                # real multipart tasks.  We can just use a BasicTask
                # in the else clause below, which will print out the
                # fact that it's transferring a file rather than
                # the specific part tasks required to perform the
                # transfer.
                num_uploads = self._enqueue_multipart_tasks(filename, payload)
            else:
                task = tasks.BasicTask(
                    session=self.session, filename=filename,
                    parameters=self.params,
                    result_queue=self.result_queue,
                    payload=payload)
                self.executor.submit(task)
            total_files += 1
            total_parts += num_uploads
        return total_files, total_parts

    def _pull_from_stream(self, amount_requested):
        """
        This function pulls data from stdin until it hits the amount
        requested or there is no more left to pull in from stdin.  The
        function wraps the data into a ``BytesIO`` object that is returned
        along with a boolean telling whether the amount requested is
        the amount returned.
        """
        stream_filein = sys.stdin
        if six.PY3:
            stream_filein = sys.stdin.buffer
        payload = stream_filein.read(amount_requested)
        payload_file = six.BytesIO(payload)
        return payload_file, len(payload) == amount_requested

    def _enqueue_multipart_tasks(self, filename, payload=None):
        num_uploads = 1
        if filename.operation_name == 'upload':
            num_uploads = self._enqueue_multipart_upload_tasks(filename,
                                                               payload=payload)
        elif filename.operation_name == 'download':
            num_uploads = self._enqueue_range_download_tasks(filename)
        return num_uploads

    def _enqueue_range_download_tasks(self, filename, remove_remote_file=False):

        # Create the context for the multipart download.
        num_downloads = int(filename.size / self.chunksize)
        context = tasks.MultipartDownloadContext(num_downloads)

        # No file is needed for downloading a stream.  So just announce
        # that it has been made since it is required for the context to
        # begin downloading.
        context.announce_file_created()

        # Submit download part tasks to the executor.
        self._do_enqueue_range_download_tasks(
            filename=filename, chunksize=self.chunksize,
            num_downloads=num_downloads, context=context,
            remove_remote_file=remove_remote_file
        )
        return num_downloads

    def _enqueue_multipart_upload_tasks(self, filename, payload=None):
        # First we need to create a CreateMultipartUpload task,
        # then create UploadTask objects for each of the parts.
        # And finally enqueue a CompleteMultipartUploadTask.
        if self.params['expected_size']:
            # If we have the expected size, we can calculate an appropriate
            # chunksize based on max parts and chunksize limits
            chunksize = find_chunksize(int(self.params['expected_size']),
                                       self.chunksize)
        else:
            # Otherwise, we can still adjust for chunksize limits
            chunksize = adjust_chunksize_to_upload_limits(self.chunksize)

        num_uploads = '...'

        # Submit a task to begin the multipart upload.
        upload_context = self._enqueue_upload_start_task(
            chunksize, num_uploads, filename)

        # Now submit a task to upload the initial chunk of data pulled
        # from the stream that was used to determine if a multipart upload
        # was needed.
        self._enqueue_upload_single_part_task(
            part_number=1, chunk_size=chunksize,
            upload_context=upload_context, filename=filename,
            task_class=tasks.UploadPartTask, payload=payload
        )

        # Submit tasks to upload the rest of the chunks of the data coming in
        # from standard input.
        num_uploads = self._enqueue_upload_tasks(
            num_uploads, chunksize, upload_context,
            filename, tasks.UploadPartTask
        )

        # Submit a task to notify the multipart upload is complete.
        self._enqueue_upload_end_task(filename, upload_context)

        return num_uploads

    def _enqueue_upload_tasks(self, num_uploads, chunksize, upload_context,
                              filename, task_class):
        # The previous upload occured right after the multipart
        # upload started for a stream.
        num_uploads = 1
        while True:
            # Pull more data from standard input.
            payload, is_remaining = self._pull_from_stream(chunksize)
            # Submit an upload part task for the recently pulled data.
            self._enqueue_upload_single_part_task(
                part_number=num_uploads+1,
                chunk_size=chunksize,
                upload_context=upload_context,
                filename=filename,
                task_class=task_class,
                payload=payload
            )
            num_uploads += 1
            if not is_remaining:
                break
        # Once there is no more data left, announce to the context how
        # many parts are being uploaded so it knows when it can quit.
        upload_context.announce_total_parts(num_uploads)
        return num_uploads
