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
from six.moves import queue as Queue
import sys
import threading

from awscli.customizations.s3.tasks import BasicTask
from awscli.customizations.s3.utils import MultiCounter, NoBlockQueue, \
    uni_print

LOGGER = logging.getLogger(__name__)


class Executer(object):
    """
    This class is in charge of all of the threads.  It starts up the threads
    and cleans up the threads when done.  The two type of threads the
    ``Executer``runs is a worker and a print thread.
    """
    def __init__(self, done, num_threads, timeout,
                 print_queue, quiet, interrupt, max_multi, max_queue_size):
        self.queue = None
        self.done = done
        self.num_threads = num_threads
        self.timeout = timeout
        self.print_queue = print_queue
        self.quiet = quiet
        self.interrupt = interrupt
        self.threads_list = []
        self.max_multi = max_multi
        self.multi_lock = threading.Lock()
        self.multi_counter = MultiCounter()
        self._max_queue_size = max_queue_size

    def start(self):
        self.queue = NoBlockQueue(self.interrupt, maxsize=self._max_queue_size)
        self.multi_counter.count = 0
        self.print_thread = PrintThread(self.print_queue, self.done,
                                        self.quiet, self.interrupt,
                                        self.timeout)
        self.print_thread.setDaemon(True)
        self.threads_list.append(self.print_thread)
        self.print_thread.start()
        for i in range(self.num_threads):
            worker = Worker(queue=self.queue, done=self.done,
                            timeout=self.timeout, multi_lock=self.multi_lock,
                            multi_counter=self.multi_counter,
                            max_multi=self.max_multi)
            worker.setDaemon(True)
            self.threads_list.append(worker)
            worker.start()

    def submit(self, task):
        """
        This is the function used to submit a task to the ``Executer``.
        """
        self.queue.put(task)

    def wait(self):
        """
        This is the function used to wait on all of the tasks to finish
        in the ``Executer``.
        """
        self.queue.join()

    def join(self):
        """
        This is used to clean up the ``Executer``.
        """
        for thread in self.threads_list:
            thread.join()


class Worker(threading.Thread):
    """
    This thread is in charge of performing the tasks provided via
    the main queue ``queue``.  Across all ``worker`` threads, there can
    only be the ``max_multi`` amount of multipart operations at a time or
    deadlock occurs because ``worker`` threads are needed to perform the
    part operations of multipart operations.  The ``worker`` threads share
    a lock in order to accurately track these multipart operations.
    """
    def __init__(self, queue, done, timeout, multi_lock,
                 multi_counter, max_multi):
        threading.Thread.__init__(self)
        self.queue = queue
        self.done = done
        self.timeout = timeout
        self.multi_lock = multi_lock
        self.multi_counter = multi_counter
        self.max_multi = max_multi
        self.is_multi_start = False

    def run(self):
        while True:
            try:
                function = self.queue.get(True, self.timeout)
                with self.multi_lock:
                    putback = self.check_multi(function)
                if not putback:
                    try:
                        function()
                    except Exception as e:
                        LOGGER.debug('Error calling task: %s', e,
                                     exc_info=True)
                else:
                    self.queue.put(function)
                if self.is_multi_start:
                    with self.multi_lock:
                        self.multi_counter.count -= 1
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.done.isSet():
                break

    def check_multi(self, function):
        """
        This is a helper function used to handle the number of in progress
        multipart operations.  The function determines if the number of
        multipart operations in progress ``multi_counter.count`` is equal
        to the maximum ``max_multi``.  If it is not equal it increments
        ``multi_counter.count`` and allows the thread to proceed.
        However if it is at the limit, The thread puts the task back into
        the queue so that it performs a task that is not initiating a
        multipart operation.
        """
        self.is_multi_start = False
        putback = False
        if isinstance(function, BasicTask):
            if hasattr(function.filename, 'is_multi'):
                self.is_multi_start = function.filename.is_multi
            is_maxed = self.multi_counter.count == self.max_multi
            if is_maxed and self.is_multi_start:
                putback = True
                self.is_multi_start = False
            elif not is_maxed and self.is_multi_start:
                self.multi_counter.count += 1
        return putback


class PrintThread(threading.Thread):
    """
    This thread controls the printing of results.  When a task is
    completely finished it is permanently write the result to standard
    out. Otherwise, it is a part of a multipart upload/download and
    only shows the most current part upload/download.
    """
    def __init__(self, print_queue, done, quiet, interrupt, timeout):
        threading.Thread.__init__(self)
        self._progress_dict = {}
        self._interrupt = interrupt
        self._print_queue = print_queue
        self._done = done
        self._quiet = quiet
        self._timeout = timeout
        self._progress_length = 0
        self._num_parts = 0
        self._file_count = 0
        self._lock = threading.Lock()

        self._total_parts = 0
        self._total_files = '...'

    def set_total_parts(self, total_parts):
        with self._lock:
            self._total_parts = total_parts

    def set_total_files(self, total_files):
        with self._lock:
            self._total_files = total_files

    def run(self):
        while True:
            try:
                print_task = self._print_queue.get(True, self._timeout)
                try:
                    self._process_print_task(print_task)
                except Exception as e:
                    LOGGER.debug("Error processing print task: %s", e,
                                 exc_info=True)
                finally:
                    # Because the shutdown logic requires that the print
                    # queue finish, we need to have all the print tasks
                    # finished, even if an exception happens trying to print
                    # them.
                    self._print_queue.task_done()
            except Queue.Empty:
                pass
            if self._done.isSet():
                break

    def _process_print_task(self, print_task):
        print_str = print_task['result']
        final_str = ''
        if print_task.get('part', ''):
            # Normalize keys so failures and sucess
            # look the same.
            op_list = print_str.split(':')
            print_str = ':'.join(op_list[1:])
            print_part = print_task['part']
            total_part = print_part['total']
            self._num_parts += 1
            if print_str in self._progress_dict:
                self._progress_dict[print_str]['parts'] += 1
            else:
                self._progress_dict[print_str] = {}
                self._progress_dict[print_str]['parts'] = 1
                self._progress_dict[print_str]['total'] = total_part
        else:
            print_components = print_str.split(':')
            final_str += print_str.ljust(self._progress_length, ' ')
            final_str += '\n'
            if print_task.get('error', ''):
                final_str += print_task['error'] + '\n'
            key = ':'.join(print_components[1:])
            if key in self._progress_dict:
                self._progress_dict.pop(print_str, None)
            else:
                self._num_parts += 1
            self._file_count += 1

        is_done = self._total_files == self._file_count
        if not self._interrupt.isSet() and not is_done:
            prog_str = "Completed %s " % self._num_parts
            num_files = self._total_files
            if self._total_files != '...':
                prog_str += "of %s " % self._total_parts
                num_files = self._total_files - self._file_count
            prog_str += "part(s) with %s file(s) remaining" % \
                num_files
            length_prog = len(prog_str)
            prog_str += '\r'
            prog_str = prog_str.ljust(self._progress_length, ' ')
            self._progress_length = length_prog
            final_str += prog_str
        if not self._quiet:
            uni_print(final_str)
            sys.stdout.flush()
