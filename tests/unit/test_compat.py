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
import stat
import socket

from mock import Mock, patch

from awscli.compat import is_special_file
from awscli.testutils import unittest, FileCreator


class TestIsSpecialFile(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.filename = 'foo'
    
    def tearDown(self):
        self.files.remove_all()

    def test_is_character_device(self):
        mock_class = Mock()
        mock_class.return_value = True
        file_path = os.path.join(self.files.rootdir, self.filename)
        self.files.create_file(self.filename, contents='')
        with patch('stat.S_ISCHR') as mock_class: 
            self.assertTrue(is_special_file(file_path))
    
    def test_is_block_device(self):
        mock_class = Mock()
        mock_class.return_value = True
        file_path = os.path.join(self.files.rootdir, self.filename)
        self.files.create_file(self.filename, contents='')
        with patch('stat.S_ISBLK') as mock_class: 
            self.assertTrue(is_special_file(file_path))

    def test_is_fifo(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        mode = 0o600 | stat.S_IFIFO
        os.mknod(file_path, mode)
        self.assertTrue(is_special_file(file_path))


    def test_is_socket(self):
        file_path = os.path.join(self.files.rootdir, self.filename)
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        sock.bind(file_path)
        self.assertTrue(is_special_file(file_path))
        

if __name__ == "__main__":
    unittest.main()
