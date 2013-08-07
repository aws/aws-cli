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
import os
import unittest

from awscli import EnvironmentVariables
from awscli.customizations.s3.filegenerator import FileInfo, \
    FileGenerator, get_file_stat, find_bucket_key
import botocore.session
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    make_s3_files, s3_cleanup, compare_files
from tests.unit.customizations.s3.fake_session import FakeSession


class FindBucketKey(unittest.TestCase):
    """
    This test ensures the find_bucket_key function works when
    unicode is used
    """
    def test_unicode(self):
        s3_path = '\u1234' + u'/' + '\u5678'
        bucket, key = find_bucket_key(s3_path)
        self.assertEqual(bucket, '\u1234')
        self.assertEqual(key, '\u5678')


class LocalFileGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.local_file = os.path.abspath('.') + os.sep + 'some_directory' \
            + os.sep + 'text1.txt'
        self.local_dir = os.path.abspath('.') + os.sep + 'some_directory' \
            + os.sep
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.files = make_loc_files()

    def tearDown(self):
        clean_loc_files(self.files)

    def test_local_file(self):
        """
        Generate a single local file.
        """
        input_local_file = {'src': {'path': self.local_file,
                                    'type': 'local'},
                            'dest': {'path': 'bucket/text1.txt',
                                     'type': 's3'},
                            'dir_op': False, 'use_src_name': False}
        files = FileGenerator(self.session).call(input_local_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        size, last_update = get_file_stat(self.local_file)
        file_info = FileInfo(src=self.local_file, dest='bucket/text1.txt',
                             compare_key='text1.txt', size=size,
                             last_update=last_update, src_type='local',
                             dest_type='s3', operation='')
        ref_list = [file_info]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_local_directory(self):
        """
        Generate an entire local directory.
        """
        input_local_dir = {'src': {'path': self.local_dir,
                                   'type': 'local'},
                           'dest': {'path': 'bucket/',
                                    'type': 's3'},
                           'dir_op': True, 'use_src_name': True}
        files = FileGenerator(self.session).call(input_local_dir)
        result_list = []
        for filename in files:
            result_list.append(filename)
        size, last_update = get_file_stat(self.local_file)
        file_info = FileInfo(src=self.local_file, dest='bucket/text1.txt',
                             compare_key='text1.txt', size=size,
                             last_update=last_update, src_type='local',
                             dest_type='s3', operation='')
        path = self.local_dir + 'another_directory' + os.sep \
            + 'text2.txt'
        size, last_update = get_file_stat(path)
        file_info2 = FileInfo(src=path,
                              dest='bucket/another_directory/text2.txt',
                              compare_key='another_directory/text2.txt',
                              size=size, last_update=last_update,
                              src_type='local',
                              dest_type='s3', operation='')
        ref_list = [file_info2, file_info]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])


class S3FileGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.bucket = make_s3_files(self.session)
        self.file1 = self.bucket + '/' + 'text1.txt'
        self.file2 = self.bucket + '/' + 'another_directory/text2.txt'

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)

    def test_nonexist_s3_file(self):
        """
        This tests to make sure that files are not misproperly yielded by
        ensuring the file prefix is the exact same as what was inputted.
        """
        input_s3_file = {'src': {'path': self.file1[:-1], 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        files = FileGenerator(self.session).call(input_s3_file)
        self.assertEqual(len(list(files)), 0)

    def test_s3_file(self):
        """
        Generate a single s3 file
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        files = FileGenerator(self.session).call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_info = FileInfo(src=self.file1, dest='text1.txt',
                             compare_key='text1.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation='')

        ref_list = [file_info]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        zero size files are ignored.
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket + '/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        files = FileGenerator(self.session).call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_info = FileInfo(src=self.file2,
                             dest='another_directory' + os.sep + 'text2.txt',
                             compare_key='another_directory/text2.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation='')
        file_info2 = FileInfo(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation='')

        ref_list = [file_info, file_info2]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_delete_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        the directory itself is included because it is a delete command
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket + '/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        files = FileGenerator(self.session, 'delete').call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)

        file_info1 = FileInfo(src=self.bucket + '/another_directory/',
                              dest='another_directory' + os.sep,
                              compare_key='another_directory/',
                              size=result_list[0].size,
                              last_update=result_list[0].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')
        file_info2 = FileInfo(src=self.file2,
                              dest='another_directory' + os.sep + 'text2.txt',
                              compare_key='another_directory/text2.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')
        file_info3 = FileInfo(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[2].size,
                              last_update=result_list[2].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')

        ref_list = [file_info1, file_info2, file_info3]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])


if __name__ == "__main__":
    unittest.main()
