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

from awscli.customizations.s3.fileformat import FileFormat


class FileFormatTest(unittest.TestCase):
    def setUp(self):
        self.file_format = FileFormat()

    def test_op_dir(self):
        """
        Format a paths for directory operation.  There are slashes at the
        end of the paths.
        """
        src = '.' + os.sep
        dest = 's3://kyknapp/golfVid/'
        parameters = {'dir_op': True}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': os.path.abspath(src) + os.sep,
                             'type': 'local'},
                     'dest': {'path': 'kyknapp/golfVid/', 'type': 's3'},
                     'dir_op': True, 'use_src_name': True}
        self.assertEqual(files, ref_files)

    def test_op_dir_noslash(self):
        """
        Format a paths for directory operation.  There are no slashes at the
        end of the paths.
        """
        src = '.'
        dest = 's3://kyknapp/golfVid'
        parameters = {'dir_op': True}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': os.path.abspath(src) + os.sep,
                             'type': 'local'},
                     'dest': {'path': 'kyknapp/golfVid/', 'type': 's3'},
                     'dir_op': True, 'use_src_name': True}
        self.assertEqual(files, ref_files)

    def test_local_use_src_name(self):
        """
        No directory operation. S3 source name given. Existing local
        destination directory given.
        """
        src = 's3://kyknapp/golfVid/hello.txt'
        dest = '.'
        parameters = {'dir_op': False}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': 'kyknapp/golfVid/hello.txt',
                             'type': 's3'},
                     'dest': {'path': os.path.abspath(dest) + os.sep,
                              'type': 'local'},
                     'dir_op': False, 'use_src_name': True}
        self.assertEqual(files, ref_files)

    def test_local_noexist_file(self):
        """
        No directory operation. S3 source name given. Nonexisting local
        destination directory given.
        """
        src = 's3://kyknapp/golfVid/hello.txt'
        dest = 'someFile' + os.sep
        parameters = {'dir_op': False}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': 'kyknapp/golfVid/hello.txt',
                             'type': 's3'},
                     'dest': {'path': os.path.abspath(dest) + os.sep,
                              'type': 'local'},
                     'dir_op': False, 'use_src_name': True}
        self.assertEqual(files, ref_files)

    def test_local_keep_dest_name(self):
        """
        No directory operation. S3 source name given. Local
        destination filename given.
        """
        src = 's3://kyknapp/golfVid/hello.txt'
        dest = 'hello.txt'
        parameters = {'dir_op': False}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': 'kyknapp/golfVid/hello.txt',
                             'type': 's3'},
                     'dest': {'path': os.path.abspath(dest),
                              'type': 'local'},
                     'dir_op': False, 'use_src_name': False}
        self.assertEqual(files, ref_files)

    def test_s3_use_src_name(self):
        """
        No directory operation. Local source name given. S3
        common prefix given.
        """
        src = 'fileformat_test.py'
        dest = 's3://kyknapp/golfVid/'
        parameters = {'dir_op': False}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': os.path.abspath(src),
                             'type': 'local'},
                     'dest': {'path': 'kyknapp/golfVid/', 'type': 's3'},
                     'dir_op': False, 'use_src_name': True}
        self.assertEqual(files, ref_files)

    def test_s3_keep_dest_name(self):
        """
        No directory operation. Local source name given. S3
        full key given.
        """
        src = 'fileformat_test.py'
        dest = 's3://kyknapp/golfVid/file.py'
        parameters = {'dir_op': False}
        files = self.file_format.format(src, dest, parameters)

        ref_files = {'src': {'path': os.path.abspath(src),
                             'type': 'local'},
                     'dest': {'path': 'kyknapp/golfVid/file.py', 'type': 's3'},
                     'dir_op': False, 'use_src_name': False}
        self.assertEqual(files, ref_files)


if __name__ == "__main__":
    unittest.main()
