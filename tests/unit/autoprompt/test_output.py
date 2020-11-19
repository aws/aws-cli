# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json

from awscli.clidriver import create_clidriver
from awscli.autocomplete import parser
from awscli.autoprompt.output import OutputGetter

from awscli.testutils import unittest
from tests.unit.autocomplete import InMemoryIndex


class TestOutputGetter(unittest.TestCase):
    def setUp(self):
        index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [
                    ('s3api', 'Amazon Simple Storage Service'),
                    ('ec2', None)
                ],
                'aws.s3api': [('get-object', None)],
                'aws.ec2': [('bundle-instance', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['query', 'output'],
                },
                'aws.s3api': {
                    'get-object': [],
                },
                'aws.ec2': {
                    'bundle-instance': [],
                },
            },
            'arg_data': {
                '': {
                    'aws': {
                        'query': (
                            'query', 'string', 'aws', '', None, False,
                            False),
                        'output': (
                            'output', 'string', 'aws', '', None, False,
                            False),
                    }
                },
                'aws.s3api': {
                    'get-object': {}
                },
                'aws.ec2': {
                    'bundle-instance': {},
                },
            }
        })
        self.parser = parser.CLIParser(index)
        self.driver = create_clidriver()
        self.driver.session.set_config_variable('output', 'json')
        self.base_output_getter = OutputGetter(self.driver)

    def test_get_output_content(self):
        parsed = self.parser.parse('aws s3api get-object')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('"Body":', content)

    def test_can_return_no_output(self):
        parsed = self.parser.parse('aws s3')
        content = self.base_output_getter.get_output(parsed)
        self.assertEqual('No output', content)

    def test_can_return_json(self):
        parsed = self.parser.parse('aws s3api get-object --output json ')
        content = json.loads(self.base_output_getter.get_output(parsed))
        self.assertIn('Body', content)

    def test_can_take_output_format_wo_trailing_space(self):
        parsed = self.parser.parse('aws s3api get-object --output table')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('------+------', content)

    def test_use_session_output_value_on_partial_input(self):
        parsed = self.parser.parse('aws s3api get-object --output yam')
        content = json.loads(self.base_output_getter.get_output(parsed))
        self.assertIn('Body', content)

    def test_can_use_session_output_format(self):
        parsed = self.parser.parse('aws s3api get-object')
        content = json.loads(self.base_output_getter.get_output(parsed))
        self.assertIn('Body', content)

    def test_can_return_error_message_on_invalid_output_format(self):
        parsed = self.parser.parse('aws s3api get-object --output poem ')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('Bad value for --output: poem', content)

    def test_can_return_error_message_on_invalid_query(self):
        parsed = self.parser.parse('aws s3api get-object --query A[}')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('Bad value for --query: A[}', content)

    def test_can_handle_open_brackets(self):
        parsed = self.parser.parse('aws s3api get-object --query Metadata.[')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('KeyName', content)

    def test_can_handle_trailing_dot(self):
        parsed = self.parser.parse('aws s3api get-object --query Metadata.')
        content = self.base_output_getter.get_output(parsed)
        self.assertIn('KeyName', content)

    def test_not_show_omap_in_yaml_output(self):
        parsed = self.parser.parse('aws s3api get-object --output yaml')
        content = self.base_output_getter.get_output(parsed)
        self.assertNotIn('omap', content)

    def test_yaml_output_can_parse_datetime(self):
        parsed = self.parser.parse('aws ec2 bundle-instance --output yaml '
                                   '--query BundleTask.StartTime')
        content = self.base_output_getter.get_output(parsed)
        self.assertEqual('"1970-01-01T00:00:00"\n', content)
