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
from awscli.testutils import unittest, mock
from awscli.autocomplete.completer import CompletionResult
from awscli.autocomplete import parser
from awscli.autocomplete.serverside.custom_completers.ddb.autocomplete import TableNameCompleter
from tests.unit.autocomplete import InMemoryIndex


class TestTableNameCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('ddb', None)],
                'aws.ddb': [('put', None), ('select', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'profile'],
                },
                'aws.ddb': {
                    'put': ['table_name'],
                    'select': ['table_name']
                },
            },
            'arg_data': {
                '': {
                    'aws': {
                        'profile': ('profile', 'string', 'aws', '',
                                         None, False, False),
                        'region': ('region', 'string', 'aws', '', None, False,
                                   False),
                    }
                },
                'aws.ddb': {
                    'put': {
                        'table_name': (
                            'table_name', 'string',
                            'put', 'aws.ddb.', None, True, False),
                    },
                    'select': {
                        'table_name': (
                            'table_name', 'string',
                            'select', 'aws.ddb.', None, True, False),
                    },
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.mock_client = mock.Mock()
        self.mock_create_client = mock.Mock()
        self.mock_create_client.create_client.return_value = self.mock_client
        self.completer = TableNameCompleter(self.mock_create_client)

    def test_complete_table_name(self):
        self.mock_client.list_tables.return_value = {
            'TableNames': [
                'tablename',
                'mytable'
            ]
        }
        parsed = self.parser.parse('aws ddb select ')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('tablename', 0),
             CompletionResult('mytable', 0)]
        )

    def test_complete_table_name_with_put(self):
        self.mock_client.list_tables.return_value = {
            'TableNames': [
                'tablename',
                'mytable'
            ]
        }
        parsed = self.parser.parse('aws ddb put ')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('tablename', 0),
             CompletionResult('mytable', 0)]
        )

    def test_complete_group_name_filters_startswith(self):
        self.mock_client.list_tables.return_value = {
            'TableNames': [
                'tablename',
                'mytable'
            ]
        }
        parsed = self.parser.parse('aws ddb select my')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('mytable', -2)]
        )

    def test_complete_group_name_handles_errors(self):
        self.mock_client.list_tables.side_effect = Exception(
            "Something went wrong.")
        parsed = self.parser.parse('aws ddb select ')
        results = self.completer.complete(parsed)
        self.assertEqual(results, [])

    def test_client_created_with_region_and_profiles_from_parsed(self):
        self.mock_client.list_tables.return_value = {'TableNames': []}
        parsed = self.parser.parse(
            'aws --profile foo --region us-west-2 ddb select ')
        self.completer.complete(parsed)
        self.mock_create_client.create_client.assert_called_with(
            'dynamodb', parsed_profile='foo', parsed_region='us-west-2')
