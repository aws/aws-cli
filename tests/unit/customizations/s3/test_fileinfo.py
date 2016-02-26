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

from awscli.compat import six
import mock

from awscli.testutils import unittest
from awscli.customizations.s3 import fileinfo
from awscli.customizations.s3.utils import MD5Error
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.fileinfo import TaskInfo


class TestSaveFile(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'dir1', 'dir2', 'foo.txt')
        etag = '3858f62230ac3c915f300c664312c63f'
        self.response_data = {
            'Body': six.BytesIO(b'foobar'),
            'ETag': '"%s"' % etag,
        }
        self.last_update = datetime.now()

        # Setup MD5 patches
        self.md5_object = mock.Mock()
        self.md5_object.hexdigest.return_value = etag
        md5_builder = mock.Mock(return_value=self.md5_object)
        self.md5_patch = mock.patch('hashlib.md5', md5_builder)
        self.md5_patch.start()
        self._md5_available_patch = None
        self.set_md5_available()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

        # Tear down MD5 patches
        self.md5_patch.stop()
        if self._md5_available_patch:
            self._md5_available_patch.stop()

    def set_md5_available(self, is_available=True):
        if self._md5_available_patch:
            self._md5_available_patch.stop()

        self._md5_available_patch = mock.patch(
            'awscli.customizations.s3.fileinfo.MD5_AVAILABLE', is_available)
        self._md5_available_patch.start()

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

    def test_no_raise_md5_when_md5_unavailable(self):
        self.response_data['ETag'] = '"0"'
        self.response_data['ServerSideEncryption'] = 'AES256'
        self.set_md5_available(False)
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


class TestIsGlacierCompatible(unittest.TestCase):
    def setUp(self):
        self.file_info = FileInfo('bucket/key')
        self.file_info.associated_response_data = {'StorageClass': 'GLACIER'}

    def test_operation_is_glacier_compatible(self):
        self.file_info.operation_name = 'delete'
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_download_operation_is_not_glacier_compatible(self):
        self.file_info.operation_name = 'download'
        self.assertFalse(self.file_info.is_glacier_compatible())

    def test_copy_operation_is_not_glacier_compatible(self):
        self.file_info.operation_name = 'copy'
        self.assertFalse(self.file_info.is_glacier_compatible())

    def test_operation_is_glacier_compatible_for_non_glacier(self):
        self.file_info.operation_name = 'download'
        self.file_info.associated_response_data = {'StorageClass': 'STANDARD'}
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_move_operation_is_not_glacier_compatible_for_s3_source(self):
        self.file_info.operation_name = 'move'
        self.file_info.src_type = 's3'
        self.assertFalse(self.file_info.is_glacier_compatible())

    def test_move_operation_is_glacier_compatible_for_local_source(self):
        self.file_info.operation_name = 'move'
        self.file_info.src_type = 'local'
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_response_is_not_glacier(self):
        self.file_info.associated_response_data = {'StorageClass': 'STANDARD'}
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_response_missing_storage_class(self):
        self.file_info.associated_response_data = {'Key': 'Foo'}
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_task_info_glacier_compatibility(self):
        task_info = TaskInfo('bucket/key', 's3', 'remove_bucket', None)
        self.assertTrue(task_info.is_glacier_compatible())

    def test_restored_object_is_glacier_compatible(self):
        self.file_info.operation_name = 'download'
        self.file_info.associated_response_data = {
            'StorageClass': 'GLACIER',
            'Restore': 'ongoing-request="false", expiry-date="..."'
        }
        self.assertTrue(self.file_info.is_glacier_compatible())

    def test_ongoing_restore_is_not_glacier_compatible(self):
        self.file_info.operation_name = 'download'
        self.file_info.associated_response_data = {
            'StorageClass': 'GLACIER',
            'Restore': 'ongoing-request="true", expiry-date="..."'
        }
        self.assertFalse(self.file_info.is_glacier_compatible())
