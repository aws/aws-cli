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
from awscli.autocomplete import completer, parser, model
from awscli.clidriver import CLIDriver


class TestAutoCompleter(unittest.TestCase):
    def setUp(self):
        self.parser = mock.Mock(spec=parser.CLIParser)
        self.parsed_result = parser.ParsedResult()
        self.parser.parse.return_value = self.parsed_result

    def test_delegates_to_autocompleters(self):
        mock_complete = mock.Mock(spec=completer.BaseCompleter)
        mock_complete.complete.return_value = ['ec2', 'ecs']
        auto_complete = completer.AutoCompleter(
            self.parser, completers=[mock_complete])

        results = auto_complete.autocomplete('aws e')
        self.assertEqual(results, ['ec2', 'ecs'])
        self.parser.parse.assert_called_with('aws e', None)
        mock_complete.complete.assert_called_with(self.parsed_result)

    def test_stops_processing_when_list_returned(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        second.complete.return_value = ['ec2', 'ecs']

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), ['ec2', 'ecs'])

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


class TestModelIndexCompleter(unittest.TestCase):
    def setUp(self):
        self.index = mock.Mock(spec=model.ModelIndex)
        self.completer = completer.ModelIndexCompleter(self.index)

    def test_does_not_complete_if_unparsed_items(self):
        parsed = parser.ParsedResult(
            current_command='aws', lineage=[],
            unparsed_items=['foo'], last_fragment='')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_complete_if_last_fragment_is_none(self):
        parsed = parser.ParsedResult(
            lineage=[],
            unparsed_items=[],
            current_command='aws',
            last_fragment=None,
        )
        self.assertIsNone(self.completer.complete(parsed))

    def test_can_prefix_match_services(self):
        parsed = parser.ParsedResult(
            current_command='aws', lineage=[],
            last_fragment='e',
        )
        self.index.command_names.return_value = ['ec2', 'ecs', 's3']
        self.assertEqual(self.completer.complete(parsed), ['ec2', 'ecs'])

    def test_returns_all_results_when_last_fragment_empty(self):
        parsed = parser.ParsedResult(
            current_command='aws', lineage=[],
            last_fragment='',
        )
        self.index.command_names.return_value = ['ec2', 'ecs', 's3']
        self.assertEqual(self.completer.complete(parsed), ['ec2', 'ecs', 's3'])

    def test_can_autocomplete_global_param(self):
        parsed = parser.ParsedResult(
            lineage=[],
            unparsed_items=[],
            current_command=u'aws',
            last_fragment=u'--re',
        )
        self.index.arg_names.return_value = ['region', 'endpoint-url']
        self.assertEqual(self.completer.complete(parsed), ['--region'])

    def test_can_combine_global_and_command_params(self):
        parsed = parser.ParsedResult(
            lineage=['aws', 'ec2'],
            unparsed_items=[],
            current_params={},
            current_command='describe-instances',
            last_fragment='--r',
        )
        self.index.arg_names.side_effect = [
            ['foo', 'reserve'],
            ['region', 'endpoint-url'],
        ]
        self.assertEqual(self.completer.complete(parsed),
                         ['--reserve', '--region'])
        # Because there were multiple calls to arg_names() we'll also
        # assert the call args and the call orders.
        self.assertEqual(
            self.index.arg_names.call_args_list,
            [mock.call(lineage=['aws', 'ec2'],
                       command_name='describe-instances'),
             mock.call(lineage=[], command_name='aws')]
        )

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = parser.ParsedResult(
            lineage=[],
            unparsed_items=[],
            current_command=u'aws',
            last_fragment=u'--foo',
        )
        self.index.arg_names.return_value = ['region', 'endpoint-url']
        self.assertEqual(self.completer.complete(parsed), [])
