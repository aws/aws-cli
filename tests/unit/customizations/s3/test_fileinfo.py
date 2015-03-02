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

from awscli.compat import six
import mock

from awscli.testutils import unittest
from awscli.customizations.s3 import fileinfo
from awscli.customizations.s3.utils import MD5Error
from awscli.customizations.s3.fileinfo import FileInfo


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

    def test_stream_file(self):
        with mock.patch('sys.stdout', new=six.StringIO()) as mock_stdout:
            fileinfo.save_file(None, self.response_data, None, True)
            self.assertEqual(mock_stdout.getvalue(), "foobar")

    def test_stream_file_md5_error(self):
        with mock.patch('sys.stdout', new=six.StringIO()) as mock_stdout:
            self.response_data['ETag'] = '"0"'
            with self.assertRaises(MD5Error):
                fileinfo.save_file(None, self.response_data, None, True)
            # Make sure nothing is written to stdout.
            self.assertEqual(mock_stdout.getvalue(), "")

    def test_raise_md5_with_no_kms_sse(self):
        # Ensure MD5 is checked if the sse algorithm is not kms.
        self.response_data['ETag'] = '"0"'
        self.response_data['ServerSideEncryption'] = 'AES256'
        # Should raise a md5 error.
        with self.assertRaises(MD5Error):
            fileinfo.save_file(self.filename, self.response_data,
                               self.last_update)
        # The file should not have been saved.
        self.assertFalse(os.path.isfile(self.filename))

    def test_no_raise_md5_with_kms(self):
        # Ensure MD5 is not checked when kms is used by providing a bad MD5.
        self.response_data['ETag'] = '"0"'
        self.response_data['ServerSideEncryption'] = 'aws:kms'
        # Should not raise any md5 error.
        fileinfo.save_file(self.filename, self.response_data, self.last_update)
        # The file should have been saved.
        self.assertTrue(os.path.isfile(self.filename))


class TestSetSizeFromS3(unittest.TestCase):
    def test_set_size_from_s3(self):
        client = mock.Mock()
        client.head_object.return_value = {'ContentLength': 5}
        file_info = FileInfo(src="bucket/key", client=client)
        file_info.set_size_from_s3()
        self.assertEqual(file_info.size, 5)
