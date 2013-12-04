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

from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.filters import Filter


class FiltersTest(unittest.TestCase):
    def setUp(self):
        self.local_files = [
            self.file_info('test.txt'),
            self.file_info('test.jpg'),
            self.file_info(os.path.join('directory', 'test.jpg')),
        ]
        self.s3_files = [
            self.file_info('bucket/test.txt'),
            self.file_info('bucket/test.jpg'),
            self.file_info('bucket/key/test.jpg'),
        ]

    def file_info(self, filename, src_type='local'):
        if src_type == 'local':
            dest_type = 's3'
        else:
            dest_type = 'local'
        return FileInfo(src=os.path.abspath(filename), dest='',
                        compare_key='', size=10,
                        last_update=0, src_type=src_type,
                        dest_type=dest_type, operation_name='',
                        service=None, endpoint=None)

    def test_no_filter(self):
        exc_inc_filter = Filter({})
        matched_files = list(exc_inc_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(exc_inc_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_include(self):
        patterns = [['--include', '*.txt']]
        include_filter = Filter({'filters': [['--include', '*.txt']]})
        matched_files = list(include_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(include_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_exclude(self):
        exclude_filter = Filter({'filters': [['--exclude', '*']]})
        matched_files = list(exclude_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])

    def test_exclude_include(self):
        patterns = [['--exclude', '*'], ['--include', '*.txt']]
        exclude_include_filter = Filter({'filters': patterns})
        matched_files = list(exclude_include_filter.call(self.local_files))
        self.assertEqual(matched_files, [self.local_files[0]])

        matched_files = list(exclude_include_filter.call(self.s3_files))
        self.assertEqual(matched_files, [self.s3_files[0]])

    def test_include_exclude(self):
        patterns = [['--include', '*.txt'], ['--exclude', '*']]
        exclude_all_filter = Filter({'filters': patterns})
        matched_files = list(exclude_all_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_all_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])


if __name__ == "__main__":
    unittest.main()
