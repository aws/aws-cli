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

import os
from tests import unittest

from awscli import EnvironmentVariables
from awscli.customizations.s3.s3 import CommandParameters
import botocore.session
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    make_s3_files, s3_cleanup


class CommandParametersTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.loc_files = make_loc_files()
        self.bucket = make_s3_files(self.session)

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_check_src_path_pass(self):
        """
        This tests to see if all of the checks on the source path works.  It
        does so by testing if s3 objects and and prefixes exist as well as
        local files and directories.  All of these should not throw an
        exception
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        s3_prefix = 's3://' + self.bucket
        local_dir = self.loc_files[3]

        # :var files: a list of tuples where the first element is a single
        #     element list of file paths. The second element is a boolean
        #     representing if the operation is a directory operation.
        files = [([s3_file], False), ([local_file], False),
                 ([s3_prefix], True), ([local_dir], True)]

        parameters = {}
        for filename in files:
            parameters['dir_op'] = filename[1]
            cmd_parameter = CommandParameters(self.session, 'put', parameters)
            cmd_parameter.check_region([])
            cmd_parameter.check_src_path(filename[0])

    def test_check_src_path_fail(self):
        """
        This tests to see if all of the checks on the source path works.  It
        does so by testing if s3 objects and and prefixes do not exist as well
        as local files and directories.  All of these should throw an
        exception
        """
        local_file = self.loc_files[0]
        local_dir = self.loc_files[3]
        fake_s3_file = 's3://' + self.bucket + '/' + 'text1.tx'
        fake_local_file = local_file[:-1]
        fake_s3_prefix = 's3://' + self.bucket + '/' + 'fake/'
        fake_local_dir = local_dir + os.sep + 'fake' + os.sep

        # :var files: a list of tuples where the first element is a single
        #     element list of file paths. The second element is a boolean
        #     representing if the operation is a directory operation.
        files = [([fake_s3_file], False), ([fake_local_file], False),
                 ([fake_s3_prefix], True), ([local_file], True),
                 ([local_dir], False), ([fake_s3_file+'dag'], False)]

        parameters = {}
        for filename in files:
            parameters['dir_op'] = filename[1]
            cmd_parameter = CommandParameters(self.session, 'put', parameters)
            cmd_parameter.check_region([])
            with self.assertRaises(Exception):
                cmd_parameter.check_src_path(filename[0])


if __name__ == "__main__":
    unittest.main()
