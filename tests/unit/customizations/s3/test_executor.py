# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import tempfile
import shutil
import time
import sys

import mock

from awscli.compat import six
from six.moves import queue
from awscli.testutils import unittest, temporary_file
from awscli.customizations.s3.executor import IOWriterThread
from awscli.customizations.s3.executor import ShutdownThreadRequest
from awscli.customizations.s3.executor import Executor, PrintThread
from awscli.customizations.s3.filegenerator import FileDecodingError
from awscli.customizations.s3.utils import IORequest, IOCloseRequest, \
    PrintTask


class TestIOWriterThread(unittest.TestCase):

    def setUp(self):
        self.queue = queue.Queue()
        self.io_thread = IOWriterThread(self.queue)
        self.temp_dir = tempfile.mkdtemp()
        self.filename = os.path.join(self.temp_dir, 'foo')
        # Create the file, since IOWriterThread expects
        # files to exist, we need to first creat the file.
        open(self.filename, 'w').close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_handles_io_request(self):
        self.queue.put(IORequest(self.filename, 0, b'foobar', False))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')

    def test_out_of_order_io_requests(self):
        self.queue.put(IORequest(self.filename, 6, b'morestuff', False))
        self.queue.put(IORequest(self.filename, 0, b'foobar', False))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobarmorestuff')

    def test_multiple_files_in_queue(self):
        second_file = os.path.join(self.temp_dir, 'bar')
        open(second_file, 'w').close()
        self.queue.put(IORequest(self.filename, 0, b'foobar', False))
        self.queue.put(IORequest(second_file, 0, b'otherstuff', False))
        self.queue.put(IOCloseRequest(second_file))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())

        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')
        with open(second_file, 'rb') as f:
            self.assertEqual(f.read(), b'otherstuff')

    def test_mtime_set_at_file_close_time(self):
        # We're picking something other than the close time so that can verify
        # that the IOCloseRequest can specify what the mtime should be.
        now_time = int(time.time() - 100)
        self.queue.put(IORequest(self.filename, 0, b'foobar', False))
        self.queue.put(IOCloseRequest(self.filename, now_time))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        actual_mtime = int(os.stat(self.filename).st_mtime)
        self.assertEqual(actual_mtime, now_time)

    def test_stream_requests(self):
        # Test that offset has no affect on the order in which requests
        # are written to stdout. The order of requests for a stream are
        # first in first out.
        self.queue.put(IORequest('nonexistant-file', 10, b'foobar', True))
        self.queue.put(IORequest('nonexistant-file', 6, b'otherstuff', True))
        # The thread should not try to close the file name because it is
        # writing to stdout.  If it does, the thread will fail because
        # the file does not exist.
        self.queue.put(ShutdownThreadRequest())
        with mock.patch('sys.stdout', new=six.StringIO()) as mock_stdout:
            self.io_thread.run()
            self.assertEqual(mock_stdout.getvalue(), 'foobarotherstuff')

    def test_io_thread_moves_on_after_failed_task(self):
        # This first request will fail because 'unknown-file' does not exist.
        self.queue.put(IORequest('unknown-file', 0, b'foobar', False))
        # But the IO thread should move on to these requests and not
        # exit it's run loop.
        self.queue.put(IORequest(self.filename, 0, b'foobar', False))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')


class TestExecutor(unittest.TestCase):
    def test_shutdown_does_not_hang(self):
        executor = Executor(2, queue.Queue(), False, False,
                            10, queue.Queue(maxsize=1))
        with temporary_file('rb+') as f:
            executor.start()
            class FloodIOQueueTask(object):
                PRIORITY = 10

                def __call__(self):
                    for i in range(50):
                        executor.write_queue.put(IORequest(f.name, 0,
                                                           b'foobar', False))
            executor.submit(FloodIOQueueTask())
            executor.initiate_shutdown()
            executor.wait_until_shutdown()
            self.assertEqual(open(f.name, 'rb').read(), b'foobar')


class TestPrintThread(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()

    def assert_expected_output(self, print_task, expected_output, thread,
                               out_file):
        with mock.patch(out_file, new=six.StringIO()) as mock_out:
            self.result_queue.put(print_task)
            self.result_queue.put(ShutdownThreadRequest())
            thread.run()
            self.assertIn(expected_output, mock_out.getvalue())

    def test_print(self):
        print_task = PrintTask(message="Success", error=False)

        # Ensure a successful task is printed to stdout when
        # ``quiet`` and ``only_show_errors`` is False.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=False)
        self.assert_expected_output(print_task, 'Success', thread,
                                    'sys.stdout')

    def test_print_quiet(self):
        print_task = PrintTask(message="Success", error=False)

        # Ensure a succesful task is not printed to stdout when
        # ``quiet`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=True, only_show_errors=False)
        self.assert_expected_output(print_task, '', thread, 'sys.stdout')

    def test_print_only_show_errors(self):
        print_task = PrintTask(message="Success", error=False)

        # Ensure a succesful task is not printed to stdout when
        # ``only_show_errors`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=True)
        self.assert_expected_output(print_task, '', thread, 'sys.stdout')

    def test_print_error(self):
        print_task = PrintTask(message="Fail File.", error=True)

        # Ensure a failed task is printed to stderr when
        # ``quiet`` and ``only_show_errors`` is False.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=False)
        self.assert_expected_output(print_task, 'Fail File.', thread,
                                    'sys.stderr')

    def test_print_error_quiet(self):
        print_task = PrintTask(message="Fail File.", error=True)

        # Ensure a failed task is not printed to stderr when
        # ``quiet`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=True, only_show_errors=False)
        self.assert_expected_output(print_task, '', thread, 'sys.stderr')

    def test_print_error_only_show_errors(self):
        print_task = PrintTask(message="Fail File.", error=True)

        # Ensure a failed task is printed to stderr when
        # ``only_show_errors`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=True)
        self.assert_expected_output(print_task, 'Fail File.', thread,
                                    'sys.stderr')

    def test_print_warning(self):
        print_task = PrintTask(message="Bad File.", warning=True)

        # Ensure a warned task is printed to stderr when
        # ``quiet`` and ``only_show_errors`` is False.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=False)
        self.assert_expected_output(print_task, 'Bad File.', thread,
                                    'sys.stderr')

    def test_print_warning_quiet(self):
        print_task = PrintTask(message="Bad File.", warning=True)

        # Ensure a warned task is not printed to stderr when
        # ``quiet`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=True, only_show_errors=False)
        self.assert_expected_output(print_task, '', thread, 'sys.stderr')

    def test_print_warning_only_show_errors(self):
        print_task = PrintTask(message="Bad File.", warning=True)

        # Ensure a warned task is printed to stderr when
        # ``only_show_errors`` is True.
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=True)
        self.assert_expected_output(print_task, 'Bad File.', thread,
                                    'sys.stderr')

    def test_print_decoding_error_message(self):
        # This ensures that if the message being passed to the print string
        # is from a decoding error. It can be outputted properly.
        decoding_error = FileDecodingError('temp',
                                           b'\xe2\x9c\x93')
        print_task = PrintTask(message=decoding_error.error_message,
                               warning=True)
        thread = PrintThread(result_queue=self.result_queue,
                             quiet=False, only_show_errors=False)
        self.assert_expected_output(print_task,
                                    decoding_error.error_message,
                                    thread, 'sys.stderr')
