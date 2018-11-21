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


# Note that all of these functions can be found in the unit tests.
# The only difference is that these tests use botocore's actual session
# variables to communicate with s3 as these are integration tests.  Therefore,
# only tests that use sessions are included as integration tests.

import unittest
import os
import itertools

import botocore.session
from awscli.customizations.s3.filegenerator import FileGenerator, FileStat
from tests.unit.customizations.s3 import compare_files
from tests.integration.customizations.s3 import make_s3_files, s3_cleanup


class S3FileGeneratorIntTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        # Use the datetime and and blob parsing of the CLI
        factory = self.session.get_component('response_parser_factory')
        factory.set_parser_defaults(
            blob_parser=lambda x: x,
            timestamp_parser=lambda x: x)
        self.client = self.session.create_client('s3', region_name='us-west-2')
        self.bucket = make_s3_files(self.session)
        self.file1 = self.bucket + '/' + 'text1.txt'
        self.file2 = self.bucket + '/' + 'another_directory/text2.txt'

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)

    def test_s3_file(self):
        #
        # Generate a single s3 file
        # Note: Size and last update are not tested because s3 generates them.
        #
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        expected_file_size = 15
        result_list = list(
            FileGenerator(self.client, '').call(input_s3_file))
        file_stat = FileStat(src=self.file1, dest='text1.txt',
                             compare_key='text1.txt',
                             size=expected_file_size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation_name='')

        expected_list = [file_stat]
        self.assertEqual(len(result_list), 1)
        compare_files(self, result_list[0], expected_list[0])

    def test_s3_directory(self):
        #
        # Generates s3 files under a common prefix. Also it ensures that
        # zero size files are ignored.
        # Note: Size and last update are not tested because s3 generates them.
        #
        input_s3_file = {'src': {'path': self.bucket+'/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        result_list = list(
            FileGenerator(self.client, '').call(input_s3_file))
        file_stat = FileStat(src=self.file2,
                             dest='another_directory' + os.sep + 'text2.txt',
                             compare_key='another_directory/text2.txt',
                             size=21,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation_name='')
        file_stat2 = FileStat(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=15,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation_name='')

        expected_result = [file_stat, file_stat2]
        self.assertEqual(len(result_list), 2)
        compare_files(self, result_list[0], expected_result[0])
        compare_files(self, result_list[1], expected_result[1])

    def test_s3_delete_directory(self):
        #
        # Generates s3 files under a common prefix. Also it ensures that
        # the directory itself is included because it is a delete command
        # Note: Size and last update are not tested because s3 generates them.
        #
        input_s3_file = {'src': {'path': self.bucket+'/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        result_list = list(
            FileGenerator(self.client, 'delete').call(input_s3_file))

        file_stat1 = FileStat(
            src=self.bucket + '/another_directory/',
            dest='another_directory' + os.sep,
            compare_key='another_directory/',
            size=0,
            last_update=result_list[0].last_update,
            src_type='s3',
            dest_type='local', operation_name='delete')
        file_stat2 = FileStat(
            src=self.file2,
            dest='another_directory' + os.sep + 'text2.txt',
            compare_key='another_directory/text2.txt',
            size=21,
            last_update=result_list[1].last_update,
            src_type='s3',
            dest_type='local', operation_name='delete')
        file_stat3 = FileStat(
            src=self.file1,
            dest='text1.txt',
            compare_key='text1.txt',
            size=15,
            last_update=result_list[2].last_update,
            src_type='s3',
            dest_type='local', operation_name='delete')

        expected_list = [file_stat1, file_stat2, file_stat3]
        self.assertEqual(len(result_list), 3)
        compare_files(self, result_list[0], expected_list[0])
        compare_files(self, result_list[1], expected_list[1])
        compare_files(self, result_list[2], expected_list[2])

    def test_page_size(self):
        input_s3_file = {'src': {'path': self.bucket+'/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        file_gen = FileGenerator(self.client, '',
                                 page_size=1).call(input_s3_file)
        limited_file_gen = itertools.islice(file_gen, 1)
        result_list = list(limited_file_gen)
        file_stat = FileStat(src=self.file2,
                             dest='another_directory' + os.sep + 'text2.txt',
                             compare_key='another_directory/text2.txt',
                             size=21,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation_name='')
        # Ensure only one item is returned from ``ListObjects``
        self.assertEqual(len(result_list), 1)
        compare_files(self, result_list[0], file_stat)


if __name__ == "__main__":
    unittest.main()
