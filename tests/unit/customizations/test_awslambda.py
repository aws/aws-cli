# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class TestCreateFunction(BaseAWSCommandParamsTest):

    prefix = 'lambda create-function'

    def setUp(self):
        super(TestCreateFunction, self).setUp()

        # Make a temporary file
        self.files = FileCreator()
        self.contents_of_file = 'myzipcontents'
        self.temp_file = self.files.create_file(
            'foo', self.contents_of_file)

    def tearDown(self):
        super(TestCreateFunction, self).tearDown()
        self.files.remove_all()

    def test_create_function(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler --zip-file myzip'
        result = {
            'FunctionName': 'myfunction',
            'Runtime': 'myruntime',
            'Role': 'myrole',
            'Handler': 'myhandler',
            'Code': {'ZipFile': 'myzip'}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_with_file(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --zip-file file://%s' % self.temp_file
        result = {
            'FunctionName': 'myfunction',
            'Runtime': 'myruntime',
            'Role': 'myrole',
            'Handler': 'myhandler',
            'Code': {'ZipFile': self.contents_of_file}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_code_argument_cause_error(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler --zip-file myzip'
        cmdline += ' --code mycode'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Unknown options: --code', stderr)
