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
import copy
from functools import partial
from nose.tools import assert_equal

from awscli.testutils import unittest
from awscli.autocomplete import parser, model



class FakeModelIndex(model.ModelIndex):
    # An in-memory version of a model index.

    def __init__(self, index):
        self.index = index

    def command_names(self, lineage):
        parent = '.'.join(lineage)
        return self.index['command_names'].get(parent, [])

    def arg_names(self, lineage, command_name):
        parent = '.'.join(lineage)
        return self.index['arg_names'].get(parent, {}).get(command_name, [])

    def get_argument_data(self, lineage, command_name, arg_name):
        parent = '.'.join(lineage)
        arg_data = self.index['arg_data'].get(parent, {}).get(
            command_name, {}).get(arg_name)
        if arg_data is not None:
            return model.CLIArgument(*arg_data)


# This models an 'aws ec2 stop-instances' command
# along with the 'region', 'endpoint-url', and 'debug' global params.
SAMPLE_MODEL = FakeModelIndex(
    # This format is intended to match the structure you'd get from
    # querying the index db to minimize any parity issues between
    # the tests and the real indexer.
    index={
        'arg_names': {
            '': {
                'aws': ['region', 'endpoint-url', 'debug'],
            },
            'aws.ec2': {
                'stop-instances': ['instance-ids', 'foo-arg'],
            }
        },
        'command_names': {
            '': ['aws'],
            'aws': ['ec2'],
            'aws.ec2': ['stop-instances'],
        },
        'arg_data': {
            '': {
                'aws': {
                    'debug': ('debug', 'boolean', 'aws', '', None),
                    'endpoint-url': ('endpoint-url', 'string',
                                     'aws', '', None),
                    'region': ('region', 'string', 'aws', '', None),
                }
            },
            'aws.ec2': {
                'stop-instances': {
                    'instance-ids': (
                        'instance-ids', 'string',
                        'stop-instances', 'aws.ec2.', '*'),
                    'foo-arg': (
                        'foo-arg', 'string', 'stop-instances',
                        'aws.ec2', None),
                }
            }
        }
    },
)


def test_can_handle_arbitrary_ordering():
    # This test verifies that parse to the same result given a command
    # with its arguments in varying orders.  For more detailed testing,
    # see TestCanParseCLICommand below.
    expected = parser.ParsedResult(
        current_command='stop-instances',
        global_params={'debug': None, 'endpoint-url': 'https://foo'},
        current_params={'instance-ids': ['i-123', 'i-124'],
                        'foo-arg': 'value'},
        lineage=['aws', 'ec2'],
    )
    test = partial(_assert_parses_to, expected=expected)
    yield test, ('aws ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value --debug '
                 '--endpoint-url https://foo')
    yield test, ('aws --debug ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value '
                 '--endpoint-url https://foo')
    yield test, ('aws --endpoint-url https://foo --debug ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value')
    yield test, ('aws ec2 --debug --endpoint-url https://foo stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value')
    yield test, ('aws ec2 stop-instances --debug --endpoint-url https://foo '
                 '--instance-ids i-123 i-124 --foo-arg value')
    yield test, ('aws ec2 --endpoint-url https://foo stop-instances --debug '
                 '--instance-ids i-123 i-124 --foo-arg value')


def _assert_parses_to(command_line, expected):
    p = parser.CLIParser(SAMPLE_MODEL)
    result = p.parse(command_line)
    assert_equal(result, expected)


class TestCanParseCLICommand(unittest.TestCase):
    def setUp(self):
        self.cli_parser = self.create_parser()

    def create_parser(self):
        return parser.CLIParser(SAMPLE_MODEL)

    def assert_parsed_results_equal(self, actual, **expected):
        # Asserts that every kwargs in expected matches what was actually
        # parsed.
        for key, value in expected.items():
            self.assertEqual(getattr(actual, key), value)

    def test_parsed_result_not_equal(self):
        self.assertFalse(parser.ParsedResult(current_command='ec2') == 'ec2')

    def test_no_result_if_not_aws_command(self):
        result = self.cli_parser.parse('notaws ec2 foo')
        self.assertEqual(
            result,
            parser.ParsedResult(
                unparsed_items=['notaws', 'ec2', 'foo'],
            )
        )

    def test_can_parse_operation_command_accepts_single_value_arg(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --foo-arg bar')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            current_params={'foo-arg': 'bar'},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_operation_command_with_param(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            current_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_bool_param(self):
        result = self.cli_parser.parse(
            'aws --debug ec2 stop-instances --instance-ids i-1')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={'debug': None},
            current_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_bool_param_in_any_location(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 --debug')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={'debug': None},
            current_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_operation_command(self):
        result = self.cli_parser.parse('aws ec2 stop-instances')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            current_params={},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_service_command(self):
        result = self.cli_parser.parse('aws ec2')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            current_params={},
            lineage=['aws'],
        )

    def test_can_parse_aws_command(self):
        result = self.cli_parser.parse('aws')
        self.assert_parsed_results_equal(
            result,
            current_command='aws',
            current_params={},
            global_params={},
            lineage=[],
        )

    def test_ignores_unknown_args(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --unknown-arg bar')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_params={},
            lineage=['aws', 'ec2'],
        )

    def test_can_consume_one_or_more_nargs(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 i-2 i-3')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_params={'instance-ids': ['i-1', 'i-2', 'i-3']},
            lineage=['aws', 'ec2'],
        )

    def test_can_consume_zero_or_one_nargs(self):
        model = copy.deepcopy(SAMPLE_MODEL)
        nargs_one_or_more = '?'
        model.index['arg_data']['aws.ec2']['stop-instances']['foo-arg'] = (
            'foo-arg', 'string',
            'stop-instances', 'aws.ec2', nargs_one_or_more)
        p = parser.CLIParser(model)
        self.assertEqual(
            p.parse(
                'aws ec2 stop-instances --foo-arg --debug'
            ).current_params['foo-arg'], None)
        self.assertEqual(
            p.parse(
                'aws ec2 stop-instances --foo-arg bar --debug'
            ).current_params['foo-arg'], 'bar')

    def test_truncates_line_based_on_location(self):
        # The 22nd index cuts off right after `stop-instances`.
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 i-2 i-3', 22)
        # We should not have parsed the 'instance-ids'.
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_params={},
            lineage=['aws', 'ec2'],
        )

    def test_preserves_current_word(self):
        result = self.cli_parser.parse('aws ec2 stop-')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            current_params={},
            global_params={},
            lineage=['aws'],
            last_fragment='stop-',
        )

    def test_word_not_preserved_if_not_adjacent_to_word(self):
        result = self.cli_parser.parse('aws ec2 stop- ')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            current_params={},
            global_params={},
            lineage=['aws'],
            last_fragment=None,
            unparsed_items=['stop-', ''],
        )

    def test_last_fragment_populated_on_work_break(self):
        result = self.cli_parser.parse('aws ec2 ')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            current_params={},
            global_params={},
            lineage=['aws'],
            last_fragment='',
        )

    def test_last_fragment_can_be_option(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst')
        # We should not have parsed the 'instance-ids'.
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_params={},
            lineage=['aws', 'ec2'],
            last_fragment='--inst',
        )

    def test_option_not_preserved_when_space_separated(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_params={},
            lineage=['aws', 'ec2'],
            last_fragment='',
            unparsed_items=['--inst'],
        )

    def test_can_handle_unparsed_values(self):
        result = self.cli_parser.parse('aws ec stop-insta')
        self.assert_parsed_results_equal(
            result,
            current_command='aws',
            unparsed_items=['ec', 'stop-insta']
        )


class TestParseState(unittest.TestCase):
    def test_can_set_initial_state(self):
        state = parser.ParseState()
        self.assertIsNone(state.current_command)
        self.assertEqual(state.lineage, [])
        self.assertEqual(state.full_lineage, [])

    def test_initial_starting_command_has_correct_lineage(self):
        state = parser.ParseState()
        state.current_command = 'aws'
        self.assertEqual(state.current_command, 'aws')
        self.assertEqual(state.lineage, [])
        self.assertEqual(state.full_lineage, ['aws'])

    def test_can_add_new_state(self):
        state = parser.ParseState()
        state.current_command = 'aws'
        state.current_command = 'ec2'
        self.assertEqual(state.current_command, 'ec2')
        self.assertEqual(state.lineage, ['aws'])
        self.assertEqual(state.full_lineage, ['aws', 'ec2'])

    def test_multiple_lineage_has_dotted_name(self):
        state = parser.ParseState()
        state.current_command = 'aws'
        state.current_command = 'ec2'
        state.current_command = 'describe-instances'
        self.assertEqual(state.current_command, 'describe-instances')
        self.assertEqual(state.lineage, ['aws', 'ec2'])
        self.assertEqual(state.full_lineage,
                         ['aws', 'ec2', 'describe-instances'])
