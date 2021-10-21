# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import shutil
import socket
import tempfile

from tests import unittest
from tests import skip_if_windows
from s3transfer.utils import OSUtils


@skip_if_windows('Windows does not support UNIX special files')
class TestOSUtilsSpecialFiles(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_character_device(self):
        self.assertTrue(OSUtils().is_special_file('/dev/null'))

    def test_fifo(self):
        os.mkfifo(self.filename)
        self.assertTrue(OSUtils().is_special_file(self.filename))

    def test_socket(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.filename)
        self.assertTrue(OSUtils().is_special_file(self.filename))
