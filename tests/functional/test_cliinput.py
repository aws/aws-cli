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
import os

import ruamel.yaml as yaml

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class BaseCLIInputArgumentTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseCLIInputArgumentTest, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(BaseCLIInputArgumentTest, self).tearDown()
        self.files.remove_all()


class TestCLIInputJSON(BaseCLIInputArgumentTest):
    def setUp(self):
        super(TestCLIInputJSON, self).setUp()
        self.input_json = '{"Bucket": "bucket", "Key": "key"}'
        self.input_file = self.files.create_file('foo.json', self.input_json)

    def test_cli_input_json_no_exta_args(self):
        # Run a head command using the input json
        cmdline = (
            's3api head-object --cli-input-json file://%s'
        ) % self.input_file
        self.assert_params_for_cmd(cmdline, params={'Bucket': 'bucket',
                                                    'Key': 'key'})

    def test_cli_input_json_can_override_param(self):
        cmdline = (
            's3api head-object --key bar --cli-input-json file://%s'
        ) % self.input_file
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
        self.assert_params_for_cmd(cmdline, expected_rc=252,
                                   stderr_contains='Missing')

    def test_cli_input_json_has_extra_unknown_args(self):
        # Check that the operation properly throws an error if the json
        # has an extra argument that is not defined by the model.
        cmdline = (
            's3api head-object --cli-input-json '
            '{"Bucket":"bucket","Key":"key","Foo":"bar"}'
        )
        self.assert_params_for_cmd(cmdline, expected_rc=252,
                                   stderr_contains='Unknown')


class TestCLIInputYAML(BaseCLIInputArgumentTest):
    def test_input_yaml(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'Bucket: test-bucket\nEncodingType: url'
        ]
        self.assert_params_for_cmd(
            command, {'Bucket': 'test-bucket', 'EncodingType': 'url'}
        )

    def test_unknown_params_in_input(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'Bucket: test-bucket\nFoo: bar'
        ]
        self.run_cmd(command, expected_rc=252)

    def test_required_params_missing(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'EncodingType: url'
        ]
        self.run_cmd(command, expected_rc=252)

    def test_input_yaml_file(self):
        filename = self.files.create_file(
            'input.yml', 'Bucket: test-bucket\nEncodingType: url'
        )
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'file://%s' % filename
        ]
        self.assert_params_for_cmd(
            command, {'Bucket': 'test-bucket', 'EncodingType': 'url'}
        )

    def test_input_yaml_bytes(self):
        expected_args = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'Body': b'foo',
        }
        command = [
            's3api', 'put-object', '--cli-input-yaml', yaml.dump(expected_args)
        ]
        self.run_cmd(command)
        self.assertEqual(self.last_kwargs['Body'].getvalue(), b'foo')

    def test_input_yaml_ignores_comments(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'Bucket: test-bucket # Some comment\nEncodingType: url'
        ]
        self.assert_params_for_cmd(
            command, {'Bucket': 'test-bucket', 'EncodingType': 'url'}
        )

    def test_errors_when_both_yaml_and_json_provided(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'Bucket: test-bucket # Some comment\nEncodingType: url',
            '--cli-input-json', '{"Bucket":"bucket","Key":"key"}'
        ]
        self.assert_params_for_cmd(
            command, expected_rc=252,
            stderr_contains='Only one --cli-input- parameter may be specified.'
        )

class TestBinaryInput(BaseCLIInputArgumentTest):
    def test_converts_base64_to_binary_in_base64_mode(self):
        command = [
            'kms', 'encrypt', '--cli-binary-format', 'base64',
            '--key-id', 'test', '--plaintext', 'Zm9v'
        ]
        params = {
            'KeyId': 'test',
            'Plaintext': b'foo',
        }
        self.assert_params_for_cmd(command, params)

    def test_preserved_input_value_in_raw_in_base64_out_mode(self):
        command = [
            'kms', 'encrypt', '--cli-binary-format', 'raw-in-base64-out',
            '--key-id', 'test', '--plaintext', 'Zm9v'
        ]
        params = {
            'KeyId': 'test',
            'Plaintext': 'Zm9v',
        }
        self.assert_params_for_cmd(command, params)
