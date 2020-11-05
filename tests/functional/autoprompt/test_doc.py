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
from awscli.clidriver import create_clidriver
from awscli.autocomplete import parser
from awscli.autoprompt.doc import DocsGetter
from awscli.testutils import unittest, mock

from tests.unit.autocomplete import InMemoryIndex


class TestDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.docs_getter = DocsGetter(self.driver)
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('ec2', None)],
                'aws.ec2': [('describe-instances', None)],
            },
            'arg_names': {
                '': {'aws': ['region']},
                'aws.ec2': {'describe-instances': []},
            },
            'arg_data': {
                '': {
                    'aws': {
                        'region': ('region', 'string', 'aws', '', None, False,
                                   False),
                    }
                },
                'aws.ec2': {'describe-instances': {}}
            }
        })
        self.parser = parser.CLIParser(self.index)

    def test_get_service_command_docs(self):
        parsed_args = self.parser.parse('aws ec2')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)

    def test_get_service_operation_docs(self):
        parsed_args = self.parser.parse('aws ec2 describe-instances')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'Describes the specified instances'
        self.assertIn(expected_docs, actual_docs)

    def test_get_service_command_docs_with_invalid_service_operation(self):
        parsed_args = self.parser.parse('aws ec2 fake')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)

    def test_get_top_level_aws_docs_if_no_command_specified(self):
        parsed_args = self.parser.parse('aws')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'The AWS Command Line Interface'
        self.assertIn(expected_docs, actual_docs)

    def test_get_top_level_aws_docs_if_service_command_is_invalid(self):
        parsed_args = self.parser.parse('aws fake')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'The AWS Command Line Interface'
        self.assertIn(expected_docs, actual_docs)

    def test_get_service_operation_docs_if_input_is_vanild(self):
        parsed_args = self.parser.parse('aws ec2 describe-instances fake')
        actual_docs = self.docs_getter.get_docs(parsed_args)
        expected_docs = 'Describes the specified instances'
        self.assertIn(expected_docs, actual_docs)

    def test_cache_is_used(self):
        parsed_args = self.parser.parse('aws ec2 describe-instances fake')
        self.docs_getter.get_doc_content = mock.Mock()
        self.docs_getter.get_docs(parsed_args)
        self.assertEqual(self.docs_getter.get_doc_content.call_count, 1)
        self.docs_getter.get_docs(parsed_args)
        self.assertEqual(self.docs_getter.get_doc_content.call_count, 1)
