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
from datetime import datetime
from hashlib import md5

import six
import mock

from awscli.testutils import unittest
from awscli.customizations.s3 import fileinfo


class TestSaveFile(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'dir1', 'dir2', 'foo.txt')
        etag = md5()
        etag.update(b'foobar')
        etag = etag.hexdigest()
        self.response_data = {
            'Body': six.BytesIO(b'foobar'),
            'ETag': '"%s"' % etag,
        }
        self.last_update = datetime.now()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_save_file(self):
        fileinfo.save_file(self.filename, self.response_data, self.last_update)
        self.assertTrue(os.path.isfile(self.filename))

    def test_save_file_dir_exists(self):
        os.makedirs(os.path.dirname(self.filename))
        # We should still be able to save the file.
        fileinfo.save_file(self.filename, self.response_data, self.last_update)
        self.assertTrue(os.path.isfile(self.filename))

    @mock.patch('os.makedirs')
    def test_makedir_other_exception(self, makedirs):
        # If makedirs() raises any other kind of exception, we should
        # propogate the exception.
        makedirs.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            fileinfo.save_file(self.filename, self.response_data,
                               self.last_update)
        self.assertFalse(os.path.isfile(self.filename))
