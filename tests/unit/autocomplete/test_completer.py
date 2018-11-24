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
from awscli.autocomplete import completer, parser
from awscli.autocomplete.local import basic
from awscli.autocomplete.completer import CompletionResult

from tests.unit.autocomplete import InMemoryIndex


class TestAutoCompleter(unittest.TestCase):
    def setUp(self):
        self.parser = mock.Mock(spec=parser.CLIParser)
        self.parsed_result = parser.ParsedResult()
        self.parser.parse.return_value = self.parsed_result

    def test_delegates_to_autocompleters(self):
        mock_complete = mock.Mock(spec=completer.BaseCompleter)
        expected = [
            CompletionResult('ec2', -1),
            CompletionResult('ecs', -1)
        ]
        mock_complete.complete.return_value = expected
        auto_complete = completer.AutoCompleter(
            self.parser, completers=[mock_complete])

        results = auto_complete.autocomplete('aws e')
        self.assertEqual(results, expected)
        self.parser.parse.assert_called_with('aws e', None)
        mock_complete.complete.assert_called_with(self.parsed_result)

    def test_stops_processing_when_list_returned(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        expected = [
            CompletionResult('ec2', -1),
            CompletionResult('ecs', -1)
        ]
        second.complete.return_value = expected

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), expected)

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)

    def test_returns_empty_list_if_no_completers_have_results(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        second.complete.return_value = None

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), [])

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)

    def test_first_result_wins(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = [CompletionResult('ec2', -1)]
        second.complete.return_value = [CompletionResult('ecs', -1)]

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(
            auto_complete.autocomplete('aws e'),
            [CompletionResult('ec2', -1)]
        )

        first.complete.assert_called_with(self.parsed_result)
        self.assertFalse(second.complete.called)


class TestModelIndexCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': ['ec2', 'ecs', 's3'],
                'aws.ec2': ['describe-instances'],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'endpoint-url'],
                },
                'aws.ec2': {
                    'describe-instances': [
                        'instance-ids', 'reserve', 'positional'],
                }
            },
            'arg_data': {
                '': {
                    'aws': {
                        'endpoint-url': ('endpoint-url', 'string',
                                         'aws', '', None, False),
                        'region': ('region', 'string', 'aws', '', None, False),
                    }
                },
                'aws.ec2': {
                    'describe-instances': {
                        'instance-ids': (
                            'instance-ids', 'string',
                            'describe-instances', 'aws.ec2.', None, False),
                        'reserve': (
                            'reserve', 'string',
                            'describe-instances', 'aws.ec2.', None, False),
                        'positional': (
                            'positional', 'string',
                            'describe-instances', 'aws.ec2.', None, True),
                    }
                }
            }
        })
        self.parser = parser.CLIParser(self.index)


        self.completer = basic.ModelIndexCompleter(self.index)

    def test_does_not_complete_if_unparsed_items(self):
        parsed = self.parser.parse('aws foo ')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_complete_if_current_fragment_is_none(self):
        parsed = self.parser.parse('aws')
        self.assertIsNone(self.completer.complete(parsed))

    def test_can_prefix_match_services(self):
        parsed = parser.ParsedResult(
            current_command='aws', lineage=[],
            current_fragment='e',
        )
        parsed = self.parser.parse('aws e')
        expected = [
            # The -1 is because we need to replace the string starting
            # 1 character back  (the last fragment is the string 'e').
            CompletionResult('ec2', starting_index=-1),
            CompletionResult('ecs', starting_index=-1),
        ]
        self.assertEqual(self.completer.complete(parsed), expected)

    def test_returns_all_results_when_current_fragment_empty(self):
        parsed = self.parser.parse('aws ')
        expected = [
            # The -1 is because we need to replace the string starting
            # 1 character back  (the last fragment is the string 'e').
            CompletionResult('ec2', starting_index=0),
            CompletionResult('ecs', starting_index=0),
            CompletionResult('s3', starting_index=0),
        ]
        self.assertEqual(self.completer.complete(parsed), expected)

    def test_can_autocomplete_global_param(self):
        parsed = self.parser.parse('aws --re')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--region', -4)]
        )

    def test_can_combine_global_and_command_params(self):
        parsed = self.parser.parse('aws ec2 describe-instances --r')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--reserve', -3),
             CompletionResult('--region', -3)]
        )

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = self.parser.parse('aws --foo')
        self.assertEqual(self.completer.complete(parsed), [])

    def test_no_complete_positional_arguments(self):
        parsed = self.parser.parse('aws ec2 describe-instances --pos')
        self.assertEqual(self.completer.complete(parsed), [])
