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
import mock
from six.moves import queue

from awscli.testutils import unittest, temporary_file
from awscli.customizations.s3.executor import IOWriterThread
from awscli.customizations.s3.executor import ShutdownThreadRequest
from awscli.customizations.s3.executor import Executor
from awscli.customizations.s3.utils import IORequest, IOCloseRequest


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
        self.queue.put(IORequest(self.filename, 0, b'foobar'))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')

    def test_out_of_order_io_requests(self):
        self.queue.put(IORequest(self.filename, 6, b'morestuff'))
        self.queue.put(IORequest(self.filename, 0, b'foobar'))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())
        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobarmorestuff')

    def test_multiple_files_in_queue(self):
        second_file = os.path.join(self.temp_dir, 'bar')
        open(second_file, 'w').close()
        self.queue.put(IORequest(self.filename, 0, b'foobar'))
        self.queue.put(IORequest(second_file, 0, b'otherstuff'))
        self.queue.put(IOCloseRequest(second_file))
        self.queue.put(IOCloseRequest(self.filename))
        self.queue.put(ShutdownThreadRequest())

        self.io_thread.run()
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), b'foobar')
        with open(second_file, 'rb') as f:
            self.assertEqual(f.read(), b'otherstuff')


class TestExecutor(unittest.TestCase):
    def test_shutdown_does_not_hang(self):
        executor = Executor(2, queue.Queue(), False,
                            10, queue.Queue(maxsize=1))
        with temporary_file('rb+') as f:
            executor.start()
            class FloodIOQueueTask(object):
                PRIORITY = 10

                def __call__(self):
                    for i in range(50):
                        executor.write_queue.put(IORequest(f.name, 0, b'foobar'))
            executor.submit(FloodIOQueueTask())
            executor.initiate_shutdown()
            executor.wait_until_shutdown()
            self.assertEqual(open(f.name, 'rb').read(), b'foobar')
