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

from awscli.customizations.s3.utils import NoBlockQueue, uni_print


LOGGER = logging.getLogger(__name__)


class Executer(object):
    """
    This class is in charge of all of the threads.  It starts up the threads
    and cleans up the threads when done.  The two type of threads the
    ``Executer``runs is a worker and a print thread.
    """
    def __init__(self, done, num_threads, timeout,
                 result_queue, quiet, interrupt, max_queue_size):
        self.queue = None
        self.done = done
        self.num_threads = num_threads
        self.timeout = timeout
        self.result_queue = result_queue
        self.quiet = quiet
        self.interrupt = interrupt
        self.threads_list = []
        self._max_queue_size = max_queue_size
        self.print_thread = None

    @property
    def num_tasks_failed(self):
        tasks_failed = 0
        if self.print_thread is not None:
            tasks_failed = self.print_thread.num_errors_seen
        return tasks_failed

    def start(self):
        self.print_thread = PrintThread(self.result_queue, self.done,
                                        self.quiet, self.interrupt,
                                        self.timeout)
        self.print_thread.daemon = True
        self.queue = NoBlockQueue(self.interrupt, maxsize=self._max_queue_size)
        self.threads_list.append(self.print_thread)
        self.print_thread.start()
        for i in range(self.num_threads):
            worker = Worker(queue=self.queue, done=self.done,
                            timeout=self.timeout)
            worker.setDaemon(True)
            self.threads_list.append(worker)
            worker.start()

    def submit(self, task):
        """
        This is the function used to submit a task to the ``Executer``.
        """
        LOGGER.debug("Submitting task: %s", task)
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
    the main queue ``queue``.
    """
    def __init__(self, queue, done, timeout):
        threading.Thread.__init__(self)
        # This is the queue where work (tasks) are submitted.
        self.queue = queue
        self.done = done
        self.timeout = timeout

    def run(self):
        while True:
            try:
                function = self.queue.get(True, self.timeout)
                try:
                    function()
                except Exception as e:
                    LOGGER.debug('Error calling task: %s', e,
                                    exc_info=True)
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.done.isSet():
                break


class PrintThread(threading.Thread):
    """
    This thread controls the printing of results.  When a task is
    completely finished it is permanently write the result to standard
    out. Otherwise, it is a part of a multipart upload/download and
    only shows the most current part upload/download.

    Result Queue
    ------------

    Result queue items are dictionaries that have the following keys:

        * message: An arbitrary string associated with the entry.   This
            can be used to communicate the result of the task.
        * error: Boolean indicating whether or not the task completely
            successfully.
        * total_parts: The total number of parts for multipart transfers (
            deprecated, will be removed in the future).

    """
    def __init__(self, result_queue, done, quiet, interrupt, timeout):
        threading.Thread.__init__(self)
        self._progress_dict = {}
        self._interrupt = interrupt
        self._result_queue = result_queue
        self._done = done
        self._quiet = quiet
        self._timeout = timeout
        self._progress_length = 0
        self._num_parts = 0
        self._file_count = 0
        self._lock = threading.Lock()

        self._total_parts = 0
        self._total_files = '...'

        # This is a public attribute that clients can inspect to determine
        # whether or not we saw any results indicating that an error occurred.
        self.num_errors_seen = 0

    def set_total_parts(self, total_parts):
        with self._lock:
            self._total_parts = total_parts

    def set_total_files(self, total_files):
        with self._lock:
            self._total_files = total_files

    def run(self):
        while True:
            try:
                print_task = self._result_queue.get(True, self._timeout)
                LOGGER.debug("Received print task: %s", print_task)
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
                    self._result_queue.task_done()
            except Queue.Empty:
                pass
            if self._done.isSet():
                break

    def _process_print_task(self, print_task):
        print_str = print_task['message']
        if print_task['error']:
            self.num_errors_seen += 1
        final_str = ''
        if 'total_parts' in print_task:
            # Normalize keys so failures and sucess
            # look the same.
            op_list = print_str.split(':')
            print_str = ':'.join(op_list[1:])
            total_part = print_task['total_parts']
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
