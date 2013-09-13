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
    NUM_THREADS, NUM_MULTI_THREADS, QUEUE_TIMEOUT_GET, MAX_UPLOAD_SIZE
from awscli.customizations.s3.utils import NoBlockQueue, find_chunksize
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
        self.print_queue = NoBlockQueue()
        self.params = {'dryrun': False, 'quiet': False,
                       'acl': None, 'guess_mime_type': True}
        self.params['region'] = params['region']
        for key in self.params.keys():
            if key in params:
                self.params[key] = params[key]
        self.multi_threshold = multi_threshold
        self.chunksize = chunksize
        self.executer = Executer(done=self.done,
                                 num_threads=NUM_THREADS,
                                 timeout=QUEUE_TIMEOUT_GET,
                                 print_queue=self.print_queue,
                                 quiet=self.params['quiet'],
                                 interrupt=self.interrupt,
                                 max_multi=NUM_MULTI_THREADS)

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
            self.print_queue.join()

        except Exception as e:
            LOGGER.debug('Exception caught during task execution: %s',
                         str(e), exc_info=True)
        except KeyboardInterrupt:
            self.interrupt.set()
            self.print_queue.put({'result': "Cleaning up. Please wait..."})
        self.done.set()
        self.executer.join()

    def _enqueue_tasks(self, files):
        total_files = 0
        total_parts = 0
        for filename in files:
            filename.set_session(self.session, self.params['region'])
            num_uploads = 1
            is_multipart_task = False
            too_large = False
            if hasattr(filename, 'size'):
                is_multipart_task = filename.size > self.multi_threshold
                too_large = filename.size > MAX_UPLOAD_SIZE
            if too_large and filename.operation == 'upload':
                warning = "Warning %s exceeds 5 TB and upload is " \
                            "being skipped" % os.path.relpath(filename.src)
                self.print_queue.put({'result': warning})
            elif is_multipart_task:
                num_uploads = self._enqueue_multipart_tasks(filename)
            else:
                task = tasks.BasicTask(
                    session=self.session, filename=filename,
                    parameters=self.params,
                    print_queue=self.print_queue)
                self.executer.submit(task)
            total_files += 1
            total_parts += num_uploads
        return total_files, total_parts

    def _enqueue_multipart_tasks(self, filename):
        num_uploads = 1
        chunksize = self.chunksize
        if filename.operation == 'upload':
            num_uploads = self._enqueue_multipart_upload_tasks(filename)
        elif filename.operation == 'download':
            num_uploads = int(filename.size / chunksize)
            filename.set_multi(executer=self.executer,
                                print_queue=self.print_queue,
                                interrupt=self.interrupt,
                                chunksize=chunksize)
        return num_uploads

    def _enqueue_multipart_upload_tasks(self, filename):
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
            print_queue=self.print_queue, upload_context=upload_context)
        self.executer.submit(create_multipart_upload_task)

        for i in range(1, (num_uploads + 1)):
            task = tasks.UploadPartTask(
                part_number=i, chunk_size=chunksize,
                print_queue=self.print_queue, upload_context=upload_context,
                filename=filename)
            self.executer.submit(task)

        complete_multipart_upload_task = tasks.CompleteMultipartUploadTask(
            session=self.session, filename=filename, parameters=self.params,
            print_queue=self.print_queue, upload_context=upload_context)
        self.executer.submit(complete_multipart_upload_task)

        return num_uploads
