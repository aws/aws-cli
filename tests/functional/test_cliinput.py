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
import ruamel.yaml as yaml


from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class TestCLIInputYAML(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestCLIInputYAML, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestCLIInputYAML, self).tearDown()
        self.files.remove_all()

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
        self.run_cmd(command, expected_rc=255)

    def test_required_params_missing(self):
        command = [
            's3api', 'list-objects-v2', '--cli-input-yaml',
            'EncodingType: url'
        ]
        self.run_cmd(command, expected_rc=255)

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
