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
from six.moves import queue
import sys
import threading

from awscli.customizations.s3.utils import uni_print, \
        IORequest, IOCloseRequest, StablePriorityQueue
from awscli.customizations.s3.tasks import OrderableTask


LOGGER = logging.getLogger(__name__)


class ShutdownThreadRequest(OrderableTask):
    PRIORITY = 11

    def __init__(self, priority_override=None):
        if priority_override is not None:
            self.PRIORITY = priority_override


class Executor(object):
    """
    This class is in charge of all of the threads.  It starts up the threads
    and cleans up the threads when finished.  The two type of threads the
    ``Executor``runs is a worker and a print thread.
    """
    STANDARD_PRIORITY = 11
    IMMEDIATE_PRIORITY= 1

    def __init__(self, num_threads, result_queue,
                 quiet, max_queue_size, write_queue):
        self._max_queue_size = max_queue_size
        self.queue = StablePriorityQueue(maxsize=self._max_queue_size,
                                         max_priority=20)
        self.num_threads = num_threads
        self.result_queue = result_queue
        self.quiet = quiet
        self.threads_list = []
        self.write_queue = write_queue
        self.print_thread = PrintThread(self.result_queue,
                                        self.quiet)
        self.print_thread.daemon = True
        self.io_thread = IOWriterThread(self.write_queue)

    @property
    def num_tasks_failed(self):
        tasks_failed = 0
        if self.print_thread is not None:
            tasks_failed = self.print_thread.num_errors_seen
        return tasks_failed

    def start(self):
        self.io_thread.start()
        # Note that we're *not* adding the IO thread to the threads_list.
        # There's a specific shutdown order we need and we're going to be
        # explicit about it rather than relying on the threads_list order.
        # See .join() for more info.
        self.print_thread.start()
        for i in range(self.num_threads):
            worker = Worker(queue=self.queue)
            worker.setDaemon(True)
            self.threads_list.append(worker)
            worker.start()

    def submit(self, task):
        """
        This is the function used to submit a task to the ``Executor``.
        """
        LOGGER.debug("Submitting task: %s", task)
        self.queue.put(task)

    def initiate_shutdown(self, priority=STANDARD_PRIORITY):
        """Instruct all threads to shutdown.

        This is a graceful shutdown.  It will wait until all
        currently queued tasks have been completed before the threads
        shutdown.  If the task queue is completely full, it may
        take a while for the threads to shutdown.

        This method does not block.  Once ``initiate_shutdown`` has
        been called, you can all ``wait_until_shutdown`` to block
        until the Executor has been shutdown.

        """
        # Implementation detail:  we only queue the worker threads
        # to shutdown.  The print/io threads are shutdown in the
        # ``wait_until_shutdown`` method.
        for i in range(self.num_threads):
            LOGGER.debug(
                "Queueing end sentinel for worker thread (priority: %s)",
                priority)
            self.queue.put(ShutdownThreadRequest(priority))

    def wait_until_shutdown(self):
        """Block until the Executor is fully shutdown.

        This will wait until all worker threads are shutdown, along
        with any additional helper threads used by the executor.

        """
        for thread in self.threads_list:
            LOGGER.debug("Waiting for thread to shutdown: %s", thread)
            while True:
                thread.join(timeout=1)
                if not thread.is_alive():
                    break
            LOGGER.debug("Thread has been shutdown: %s", thread)

        LOGGER.debug("Queueing end sentinel for result thread.")
        self.result_queue.put(ShutdownThreadRequest())
        LOGGER.debug("Queueing end sentinel for IO thread.")
        self.write_queue.put(ShutdownThreadRequest())

        LOGGER.debug("Waiting for result thread to shutdown.")
        self.print_thread.join()
        LOGGER.debug("Waiting for IO thread to shutdown.")
        self.io_thread.join()
        LOGGER.debug("All threads have been shutdown.")


class IOWriterThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.fd_descriptor_cache = {}

    def run(self):
        while True:
            task = self.queue.get(True)
            if isinstance(task, ShutdownThreadRequest):
                LOGGER.debug("Shutdown request received in IO thread, "
                             "shutting down.")
                self._cleanup()
                return
            elif isinstance(task, IORequest):
                filename, offset, data = task
                fileobj = self.fd_descriptor_cache.get(filename)
                if fileobj is None:
                    fileobj = open(filename, 'rb+')
                    self.fd_descriptor_cache[filename] = fileobj
                fileobj.seek(offset)
                LOGGER.debug("Writing data to: %s, offset: %s",
                             filename, offset)
                fileobj.write(data)
                fileobj.flush()
            elif isinstance(task, IOCloseRequest):
                LOGGER.debug("IOCloseRequest received for %s, closing file.",
                             task.filename)
                fileobj = self.fd_descriptor_cache.get(task.filename)
                if fileobj is not None:
                    fileobj.close()
                    del self.fd_descriptor_cache[task.filename]

    def _cleanup(self):
        for fileobj in self.fd_descriptor_cache.values():
            fileobj.close()


class Worker(threading.Thread):
    """
    This thread is in charge of performing the tasks provided via
    the main queue ``queue``.
    """
    def __init__(self, queue):
        threading.Thread.__init__(self)
        # This is the queue where work (tasks) are submitted.
        self.queue = queue

    def run(self):
        while True:
            try:
                function = self.queue.get(True)
                if isinstance(function, ShutdownThreadRequest):
                    LOGGER.debug("Shutdown request received in worker thread, "
                                 "shutting down worker thread.")
                    break
                try:
                    LOGGER.debug("Worker thread invoking task: %s", function)
                    function()
                except Exception as e:
                    LOGGER.debug('Error calling task: %s', e, exc_info=True)
            except queue.Empty:
                pass


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
    def __init__(self, result_queue, quiet):
        threading.Thread.__init__(self)
        self._progress_dict = {}
        self._result_queue = result_queue
        self._quiet = quiet
        self._progress_length = 0
        self._num_parts = 0
        self._file_count = 0
        self._lock = threading.Lock()
        self._needs_newline = False

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
                print_task = self._result_queue.get(True)
                if isinstance(print_task, ShutdownThreadRequest):
                    if self._needs_newline:
                        sys.stdout.write('\n')
                    LOGGER.debug("Shutdown request received in print thread, "
                                 "shutting down print thread.")
                    break
                LOGGER.debug("Received print task: %s", print_task)
                try:
                    self._process_print_task(print_task)
                except Exception as e:
                    LOGGER.debug("Error processing print task: %s", e,
                                 exc_info=True)
            except queue.Empty:
                pass

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
        if not is_done:
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
            self._needs_newline = not final_str.endswith('\n')
            sys.stdout.flush()
