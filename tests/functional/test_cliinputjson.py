# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import shutil
import os

from awscli.testutils import BaseAWSCommandParamsTest


class TestCLIInputJSON(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestCLIInputJSON, self).setUp()
        self.input_json = '{"Bucket": "bucket", "Key": "key"}'
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'foo.json')
        with open(self.temp_file, 'w') as f:
            f.write(self.input_json)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        super(TestCLIInputJSON, self).tearDown()

    def test_cli_input_json_no_exta_args(self):
        # Run a head command using the input json
        cmdline = (
            's3api head-object --cli-input-json file://%s'
        ) % self.temp_file
        self.assert_params_for_cmd(cmdline, params={'Bucket': 'bucket',
                                                    'Key': 'key'})

    def test_cli_input_json_can_override_param(self):
        cmdline = (
            's3api head-object --key bar --cli-input-json file://%s'
        ) % self.temp_file
        self.assert_params_for_cmd(cmdline, {'Bucket': 'bucket', 'Key': 'bar'})

    def test_cli_input_json_not_from_file(self):
        # Check that the input json can be used without having to use a file.
        cmdline = (
            's3api head-object --cli-input-json '
            '{"Bucket":"bucket","Key":"key"}'
        )
        self.assert_params_for_cmd(cmdline, params={'Bucket': 'bucket',
                                                    'Key': 'key'})

    def test_cli_input_json_missing_required(self):
        # Check that the operation properly throws an error if the json is
        # missing any required arguments and the argument is not on the
        # command line.
        cmdline = (
            's3api head-object --cli-input-json {"Key":"foo"}'
        )
        self.assert_params_for_cmd(cmdline, expected_rc=255,
                                   stderr_contains='Missing')

    def test_cli_input_json_has_extra_unknown_args(self):
        # Check that the operation properly throws an error if the json
        # has an extra argument that is not defined by the model.
        cmdline = (
            's3api head-object --cli-input-json '
            '{"Bucket":"bucket","Key":"key","Foo":"bar"}'
        )
        self.assert_params_for_cmd(cmdline, expected_rc=255,
                                   stderr_contains='Unknown')
