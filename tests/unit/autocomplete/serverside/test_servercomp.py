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
from awscli.autocomplete.serverside.servercomp import ServerSideCompleter
from awscli.autocomplete.serverside.servercomp import LazyClientCreator
from awscli.autocomplete.completer import CompletionResult
from awscli.autocomplete import parser
from tests.unit.autocomplete import InMemoryIndex

import botocore.client


class FakeCompletionLookup(object):
    def __init__(self, completion_data):
        self.completion_data = completion_data

    def get_server_completion_data(self, lineage, command_name, param_name):
        key = (tuple(lineage), command_name, param_name)
        try:
            return self.completion_data[key]
        except KeyError:
            return None


class TestServerSideAutocompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': ['ec2', 'iam', 's3'],
                'aws.iam': ['delete-user-policy', 'delete-user'],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'endpoint-url'],
                },
                'aws.iam': {
                    'delete-user-policy': ['policy-name'],
                    'delete-user': ['user-name'],
                },
            },
            'arg_data': {
                '': {
                    'aws': {
                        'endpoint-url': ('endpoint-url', 'string',
                                         'aws', '', None, False),
                        'region': ('region', 'string', 'aws', '', None, False),
                    }
                },
                'aws.iam': {
                    'delete-user-policy': {
                        'policy-name': (
                            'policy-name', 'string',
                            'delete-user-policy', 'aws.iam.', None, False),
                    },
                    'delete-user': {
                        'user-name': (
                            'user-name', 'string',
                            'delete-user', 'aws.iam.', None, False),
                    }
                }
            }
        })
        key = (('aws', 'iam'), 'delete-user-policy', 'policy-name')
        self.completion_data = {
            key: {
                'completions': [{
                    "parameters": {},
                    "service": "iam",
                    "operation": "list_policies",
                    "jp_expr": "Policies[].PolicyName",
                }]
            }
        }
        self.parser = parser.CLIParser(self.index)
        self.mock_client = mock.Mock()
        self.mock_create_client = mock.Mock()
        self.mock_create_client.create_client.return_value = self.mock_client
        self.completion_lookup = FakeCompletionLookup(self.completion_data)
        self.completer = ServerSideCompleter(self.completion_lookup,
                                             self.mock_create_client)

    def test_does_not_complete_if_unparsed_items(self):
        parsed = self.parser.parse('aws foo ')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_complete_if_current_fragment_is_none(self):
        parsed = self.parser.parse('aws')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_not_complete_if_not_on_param_value(self):
        parsed = self.parser.parse('aws iam delete-user-policy --poli')
        self.assertIsNone(self.completer.complete(parsed))

    def test_no_completion_data_returns_none(self):
        parsed = self.parser.parse('aws iam delete-user --user-name ')
        self.assertIsNone(self.completer.complete(parsed))

    def test_can_prefix_match_results(self):
        self.mock_client.list_policies.return_value = {
            'Policies': [{'PolicyName': 'a1'}, {'PolicyName': 'b1'},
                         {'PolicyName': 'a2'}, {'PolicyName': 'b2'}],
        }
        parsed = self.parser.parse(
            'aws iam delete-user-policy --policy-name a')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('a1', -1), CompletionResult('a2', -1)]
        )

    def test_returns_all_results_when_current_fragment_empty(self):
        self.mock_client.list_policies.return_value = {
            'Policies': [{'PolicyName': 'a1'}, {'PolicyName': 'b1'},
                         {'PolicyName': 'a2'}, {'PolicyName': 'b2'}],
        }
        parsed = self.parser.parse('aws iam delete-user-policy --policy-name ')
        results = self.completer.complete(parsed)
        self.assertEqual(
            results,
            [CompletionResult('a1', 0),
             CompletionResult('b1', 0),
             CompletionResult('a2', 0),
             CompletionResult('b2', 0)],
        )

    def test_returns_empty_list_on_client_error(self):
        self.mock_client.list_policies.side_effect = Exception(
            "Something went wrong.")
        parsed = self.parser.parse('aws iam delete-user-policy --policy-name ')
        results = self.completer.complete(parsed)
        self.assertEqual(results, [])

    def test_returns_empty_list_when_jmespath_doesnt_match(self):
        self.mock_client.list_policies.return_value = {
            'WrongKeySomehow': [],
        }
        parsed = self.parser.parse('aws iam delete-user-policy --policy-name ')
        results = self.completer.complete(parsed)
        self.assertEqual(results, [])


class TestLazyClientCreator(unittest.TestCase):
    def test_can_create_client(self):
        creator = LazyClientCreator()
        client = creator.create_client('iam', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        self.assertIsInstance(client, botocore.client.BaseClient)
        # Sanity check it's an IAM client.
        self.assertTrue(hasattr(client, 'list_users'))
        # Verify we can create another client.
        new_client = creator.create_client('iam', aws_access_key_id='foo',
                                           aws_secret_access_key='bar')
        self.assertIsInstance(new_client, botocore.client.BaseClient)
