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
import threading
import time

from awscli.customizations.s3.constants import MULTI_THRESHOLD, CHUNKSIZE, \
    NUM_THREADS, NUM_MULTI_THREADS, QUEUE_TIMEOUT_GET
from awscli.customizations.s3.utils import NoBlockQueue
from awscli.customizations.s3.executer import Executer
from awscli.customizations.s3.tasks import BasicTask

LOGGER = logging.getLogger(__name__)


class S3Handler(object):
    """
    This class sets up the process to perform the tasks sent to it.  It
    sources the main queue ``self.queue`` from which threads in the
    ``Executer`` class pull tasks from to complete.
    """
    def __init__(self, session, params=None, multi_threshold=MULTI_THRESHOLD,
                 chunksize=CHUNKSIZE):
        self.session = session
        self.done = threading.Event()
        self.interrupt = threading.Event()
        self.queue = NoBlockQueue(self.interrupt)
        self.printQueue = NoBlockQueue()
        self.params = {'dryrun': False, 'quiet': False, 'acl': None}
        self.params['region'] = self.session.get_config()['region']
        for key in self.params.keys():
            if params and key in params:
                self.params[key] = params[key]
        self.multi_threshold = multi_threshold
        self.chunksize = chunksize
        self.executer = Executer(queue=self.queue, done=self.done,
                                 num_threads=NUM_THREADS,
                                 timeout=QUEUE_TIMEOUT_GET,
                                 printQueue=self.printQueue,
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
        tasks are then added to the main queue.
        """
        self.done.clear()
        self.interrupt.clear()
        current_time = time.time()
        try:
            self.executer.start()
            tot_files = 0
            tot_parts = 0
            for filename in files:
                num_uploads = 1
                is_larger = False
                if hasattr(filename, 'size'):
                    is_larger = filename.size > self.multi_threshold
                if is_larger:
                    if filename.operation == 'upload':
                        num_uploads = int(math.ceil(filename.size /
                                                    float(self.chunksize)))
                        filename.set_multi(queue=self.queue,
                                           printQueue=self.printQueue,
                                           interrupt=self.interrupt,
                                           chunksize=self.chunksize)
                    elif filename.operation == 'download':
                        num_uploads = int(filename.size/self.chunksize)
                        filename.set_multi(queue=self.queue,
                                           printQueue=self.printQueue,
                                           interrupt=self.interrupt,
                                           chunksize=self.chunksize)
                task = BasicTask(session=self.session, filename=filename,
                                 queue=self.queue, done=self.done,
                                 parameters=self.params,
                                 multi_threshold=self.multi_threshold,
                                 chunksize=self.chunksize,
                                 printQueue=self.printQueue,
                                 interrupt=self.interrupt)
                self.queue.put(task)
                tot_files += 1
                tot_parts += num_uploads
            self.executer.print_thread.totalFiles = tot_files
            self.executer.print_thread.totalParts = tot_parts
            self.queue.join()
            self.printQueue.join()

        except Exception as e:
            LOGGER.debug('%s' % str(e))
        except KeyboardInterrupt:
            self.interrupt.set()
            self.printQueue.put({'result': "Cleaning up. Please wait..."})

        self.done.set()
        self.executer.join()
        total_time = time.time() - current_time
