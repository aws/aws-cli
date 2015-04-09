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
import tempfile
import sys
import os
import shutil

from awscli.compat import six
from awscli.testutils import unittest
from awscli.testutils import BaseAWSCommandParamsTest


class TestCreateFunction(BaseAWSCommandParamsTest):

    prefix = 'lambda create-function'

    def setUp(self):
        super(TestCreateFunction, self).setUp()

        # Make a temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'foo.json')
        self.contents_of_file = 'myzip'
        with open(self.temp_file, 'w') as f:
            f.write(self.contents_of_file)

    def tearDown(self):
        super(TestCreateFunction, self).tearDown()
        shutil.rmtree(self.temp_dir)

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
            'Code': {'ZipFile': 'myzip'}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_code_argument_cause_error(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler --zip-file myzip'
        cmdline += ' --code mycode'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Unknown options: --code', stderr)
