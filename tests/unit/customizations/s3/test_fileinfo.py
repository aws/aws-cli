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
from awscli.testutils import unittest
from awscli.customizations.s3.fileinfo import FileInfo


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
