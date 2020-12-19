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
from awscli.autocomplete.serverside.custom_completers.logs.autocomplete import GroupNameCompleter
from tests.unit.autocomplete import InMemoryIndex


class TestGroupNameCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('logs', None)],
                'aws.logs': [('tail', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'profile'],
                },
                'aws.logs': {
                    'tail': ['group_name'],
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
                'aws.logs': {
                    'tail': {
                        'group_name': (
                            'group_name', 'string',
                            'tail', 'aws.logs.', None, True, False),
                    },
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.mock_client = mock.Mock()
        self.mock_create_client = mock.Mock()
        self.mock_create_client.create_client.return_value = self.mock_client
        self.completer = GroupNameCompleter(self.mock_create_client)

    def test_complete_group_name(self):
        self.mock_client.describe_log_groups.return_value = {
            'logGroups': [
                {'logGroupName': 'group'},
                {'logGroupName': 'mygroup'},
            ]
        }
        parsed = self.parser.parse('aws logs tail ')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('group', 0),
             CompletionResult('mygroup', 0)]
        )

    def test_complete_group_name_filters_startswith(self):
        self.mock_client.describe_log_groups.return_value = {
            'logGroups': [
                {'logGroupName': 'group'},
                {'logGroupName': 'mygroup'},
            ]
        }
        parsed = self.parser.parse('aws logs tail my')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('mygroup', -2)]
        )

    def test_complete_group_name_handles_errors(self):
        self.mock_client.describe_log_groups.side_effect = Exception(
            "Something went wrong.")
        parsed = self.parser.parse('aws logs tail ')
        results = self.completer.complete(parsed)
        self.assertEqual(results, [])

    def test_client_created_with_region_and_profiles_from_parsed(self):
        self.mock_client.describe_log_groups.return_value = {'logGroups': []}
        parsed = self.parser.parse(
            'aws --profile foo --region us-west-2 logs tail ')
        self.completer.complete(parsed)
        self.mock_create_client.create_client.assert_called_with(
            'logs', parsed_profile='foo', parsed_region='us-west-2')
