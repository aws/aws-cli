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
import logging
import math
import os
import threading

from awscli.customizations.s3.constants import MULTI_THRESHOLD, CHUNKSIZE, \
    NUM_THREADS, QUEUE_TIMEOUT_GET, MAX_UPLOAD_SIZE, \
    MAX_QUEUE_SIZE
from awscli.customizations.s3.utils import NoBlockQueue, find_chunksize, \
    operate, find_bucket_key, relative_path
from awscli.customizations.s3.executer import Executer
from awscli.customizations.s3 import tasks

LOGGER = logging.getLogger(__name__)


class S3Handler(object):
    """
    This class sets up the process to perform the tasks sent to it.  It
    sources the ``self.executer`` from which threads inside the
    class pull tasks from to complete.
    """
    def __init__(self, session, params, multi_threshold=MULTI_THRESHOLD,
                 chunksize=CHUNKSIZE):
        self.session = session
        self.done = threading.Event()
        self.interrupt = threading.Event()
        self.result_queue = NoBlockQueue()
        self.params = {'dryrun': False, 'quiet': False, 'acl': None,
                       'guess_mime_type': True, 'sse': False,
                       'storage_class': None, 'website_redirect': None,
                       'content_type': None, 'cache_control': None,
                       'content_disposition': None, 'content_encoding': None,
                       'content_language': None, 'expires': None,
                       'grants': None}
        self.params['region'] = params['region']
        for key in self.params.keys():
            if key in params:
                self.params[key] = params[key]
        self.multi_threshold = multi_threshold
        self.chunksize = chunksize
        self.executer = Executer(
            done=self.done, num_threads=NUM_THREADS,
            timeout=QUEUE_TIMEOUT_GET, result_queue=self.result_queue,
            quiet=self.params['quiet'], interrupt=self.interrupt,
            max_queue_size=MAX_QUEUE_SIZE,
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
        tasks are then submitted to the main executer.
        """
        self.done.clear()
        self.interrupt.clear()
        try:
            self.executer.start()
            total_files, total_parts = self._enqueue_tasks(files)
            self.executer.print_thread.set_total_files(total_files)
            self.executer.print_thread.set_total_parts(total_parts)
            self.executer.wait()
            self.result_queue.join()

        except Exception as e:
            LOGGER.error('Exception caught during task execution: %s',
                          str(e))
            # Log the traceback at DEBUG level.
            LOGGER.debug(str(e), exc_info=True)
        except KeyboardInterrupt:
            self.interrupt.set()
            self.result_queue.put({'message': "Cleaning up. Please wait...",
                                   'error': False})
        self._shutdown()
        return self.executer.num_tasks_failed

    def _shutdown(self):
        # self.done will tell threads to shutdown.
        self.done.set()
        # This waill wait until all the threads are joined.
        self.executer.join()
        # And finally we need to make a pass through all the existing
        # multipart uploads and abort any pending multipart uploads.
        self._abort_pending_multipart_uploads()
        self._remove_pending_downloads()

    def _abort_pending_multipart_uploads(self):
        # For the purpose of aborting uploads, we consider any
        # upload context with an upload id.
        for upload, filename in self._multipart_uploads:
            if upload.is_cancelled():
                try:
                    upload.wait_for_upload_id()
                except tasks.UploadCancelledError:
                    pass
                else:
                    # This means that the upload went from STARTED -> CANCELLED.
                    # This could happen if a part thread decided to cancel the
                    # upload.  We need to explicitly abort the upload here.
                    self._cancel_upload(upload.wait_for_upload_id(), filename)
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

    def _cancel_upload(self, upload_id, filename):
        bucket, key = find_bucket_key(filename.dest)
        params = {
            'bucket': bucket,
            'key': key,
            'upload_id': upload_id,
            'endpoint': filename.endpoint,
        }
        LOGGER.debug("Aborting multipart upload for: %s", key)
        response_data, http = operate(
            filename.service, 'AbortMultipartUpload', params)

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
                warning = "Warning %s exceeds 5 TB and upload is " \
                            "being skipped" % relative_path(filename.src)
                self.result_queue.put({'message': warning, 'error': True})
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
                self.executer.submit(task)
            total_files += 1
            total_parts += num_uploads
        return total_files, total_parts

    def _is_multipart_task(self, filename):
        # First we need to determine if it's an operation that even
        # qualifies for multipart upload.
        if hasattr(filename, 'size'):
            above_multipart_threshold = filename.size > self.multi_threshold
            if above_multipart_threshold:
                if filename.operation_name in ('upload', 'download', 'move'):
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
            else:
                num_uploads = self._enqueue_range_download_tasks(
                    filename, remove_remote_file=True)
        elif filename.operation_name == 'download':
            num_uploads = self._enqueue_range_download_tasks(filename)
        return num_uploads

    def _enqueue_range_download_tasks(self, filename, remove_remote_file=False):
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_downloads = int(filename.size / chunksize)
        context = tasks.MultipartDownloadContext(num_downloads)
        create_file_task = tasks.CreateLocalFileTask(context=context,
                                                     filename=filename)
        self.executer.submit(create_file_task)
        for i in range(num_downloads):
            task = tasks.DownloadPartTask(
                part_number=i, chunk_size=chunksize,
                result_queue=self.result_queue, service=filename.service,
                filename=filename, context=context)
            self.executer.submit(task)
        complete_file_task = tasks.CompleteDownloadTask(
            context=context, filename=filename, result_queue=self.result_queue,
            params=self.params)
        self.executer.submit(complete_file_task)
        self._multipart_downloads.append((context, filename.dest))
        if remove_remote_file:
            remove_task = tasks.RemoveRemoteObjectTask(
                filename=filename, context=context)
            self.executer.submit(remove_task)
        return num_downloads

    def _enqueue_multipart_upload_tasks(self, filename,
                                        remove_local_file=False):
        # First we need to create a CreateMultipartUpload task,
        # then create UploadTask objects for each of the parts.
        # And finally enqueue a CompleteMultipartUploadTask.
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_uploads = int(math.ceil(filename.size /
                                    float(chunksize)))
        upload_context = tasks.MultipartUploadContext(
            expected_parts=num_uploads)
        create_multipart_upload_task = tasks.CreateMultipartUploadTask(
            session=self.session, filename=filename,
            parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executer.submit(create_multipart_upload_task)

        for i in range(1, (num_uploads + 1)):
            task = tasks.UploadPartTask(
                part_number=i, chunk_size=chunksize,
                result_queue=self.result_queue, upload_context=upload_context,
                filename=filename)
            self.executer.submit(task)

        complete_multipart_upload_task = tasks.CompleteMultipartUploadTask(
            session=self.session, filename=filename, parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executer.submit(complete_multipart_upload_task)
        self._multipart_uploads.append((upload_context, filename))
        if remove_local_file:
            remove_task = tasks.RemoveFileTask(local_filename=filename.src,
                                               upload_context=upload_context)
            self.executer.submit(remove_task)
        return num_uploads
