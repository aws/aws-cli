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
from nose.tools import assert_equal, assert_is_instance, assert_true

from awscli.testutils import unittest
from awscli.autocomplete import parser
from tests.unit.autocomplete import InMemoryIndex


# This models an 'aws ec2 stop-instances' command
# along with the 'region', 'endpoint-url', and 'debug' global params.
SAMPLE_MODEL = InMemoryIndex(
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
            },
            'aws.logs': {
                'tail': ['group_name', 'filter-pattern']
            }
        },
        'command_names': {
            '': ['aws'],
            'aws': ['ec2', 'logs'],
            'aws.ec2': ['stop-instances'],
            'aws.logs': ['tail']
        },
        'arg_data': {
            '': {
                'aws': {
                    'debug': ('debug', 'boolean', 'aws', '', None, False),
                    'endpoint-url': ('endpoint-url', 'string',
                                     'aws', '', None, False),
                    'region': ('region', 'string', 'aws', '', None, False),
                }
            },
            'aws.ec2': {
                'stop-instances': {
                    'instance-ids': (
                        'instance-ids', 'string',
                        'stop-instances', 'aws.ec2.', '*', False),
                    'foo-arg': (
                        'foo-arg', 'string', 'stop-instances',
                        'aws.ec2', None, False),
                    'positional': (
                        'positional', 'string', 'stop-instances',
                        'aws.ec2', None, True),
                }
            },
            'aws.logs': {
                'tail': {
                    'group_name': (
                        'group_name', 'string',
                        'tail', 'aws.logs.', None, True),
                    'filter-pattern': (
                        'filter-pattern', 'string', 'tail',
                        'aws.logs', None, False),
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
        parsed_params={'instance-ids': ['i-123', 'i-124'],
                        'foo-arg': 'value'},
        lineage=['aws', 'ec2'],
        current_fragment='',
    )
    test = partial(_assert_parses_to, expected=expected)
    yield test, ('aws ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value --debug '
                 '--endpoint-url https://foo ')
    yield test, ('aws --debug ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value '
                 '--endpoint-url https://foo ')
    yield test, ('aws --endpoint-url https://foo --debug ec2 stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value ')
    yield test, ('aws ec2 --debug --endpoint-url https://foo stop-instances '
                 '--instance-ids i-123 i-124 --foo-arg value ')
    yield test, ('aws ec2 stop-instances --debug --endpoint-url https://foo '
                 '--instance-ids i-123 i-124 --foo-arg value ')
    yield test, ('aws ec2 --endpoint-url https://foo stop-instances --debug '
                 '--instance-ids i-123 i-124 --foo-arg value ')


def _assert_parses_to(command_line, expected):
    p = parser.CLIParser(SAMPLE_MODEL)
    result = p.parse(command_line)
    for key, value in vars(expected).items():
        actual = getattr(result, key)
        assert_equal(getattr(result, key), value, '%r != %r for attribute: %r'
                     % (actual, value, key))


def test_properties_of_unparsed_results():
    # The parser should never raise an exception.  If it can't
    # understand something it should still return a ParsedResult
    # with the parts it doesn't understand addded to the unparsed_items
    # attribute.  The ParsedResult should always have some basic invariants
    # we can verify which are called out in the tests below.
    # This test ensures that at every single slice of the full command_line
    # we always produce a sensical ParsedResult.
    command_line = (
        'aws ec2 stop-instances --instance-ids i-123 i-124 '
        '--foo-arg value --debug --endpoint-url https://foo'
    )
    cli_parser = parser.CLIParser(SAMPLE_MODEL)
    for i in range(1, len(command_line)):
        chunk = command_line[:i]
        yield _assert_parsed_properties, chunk, cli_parser


def _assert_parsed_properties(chunk, cli_parser):
    result = cli_parser.parse(chunk)
    assert_is_instance(result, parser.ParsedResult)
    if chunk[-1].isspace():
        # If there's a space as the last char, then we should have
        # a current_fragment of an empty string.  This results in
        # all results being returned from the prefix match in the
        # auto-completer.
        assert_equal(result.current_fragment, '')
    elif result.current_fragment is not None:
        # The current_fragment, if not None is always the last part
        # of the command line.
        assert_true(chunk.endswith(result.current_fragment))


class TestCanParseCLICommand(unittest.TestCase):
    def setUp(self):
        self.cli_parser = self.create_parser()

    def create_parser(self):
        return parser.CLIParser(SAMPLE_MODEL)

    def assert_parsed_results_equal(self, actual, **expected):
        # Asserts that every kwargs in expected matches what was actually
        # parsed.
        for key, value in expected.items():
            actual_value = getattr(actual, key)
            self.assertEqual(actual_value, value, '%r != %r (attr: %r)'
                             % (actual_value, value, key))

    def test_parsed_result_not_equal(self):
        self.assertFalse(parser.ParsedResult(current_command='ec2') == 'ec2')

    def test_can_handle_empty_string_for_command(self):
        result = self.cli_parser.parse('')
        self.assert_parsed_results_equal(
            result,
            current_command=None,
            global_params={},
            parsed_params={},
            lineage=[],
            unparsed_items=[],
        )

    def test_result_if_aws_exe_alias(self):
        result = self.cli_parser.parse('aws2 ec2')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            global_params={},
            parsed_params={},
            lineage=['aws'],
            unparsed_items=[],
        )

    def test_can_parse_operation_command_accepts_single_value_arg(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --foo-arg bar ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            parsed_params={'foo-arg': 'bar'},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_operation_command_with_param(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            parsed_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_bool_param(self):
        result = self.cli_parser.parse(
            'aws --debug ec2 stop-instances --instance-ids i-1 ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={'debug': None},
            parsed_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_bool_param_in_any_location(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 --debug')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={'debug': None},
            parsed_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_operation_command(self):
        result = self.cli_parser.parse('aws ec2 stop-instances')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            global_params={},
            parsed_params={},
            lineage=['aws', 'ec2']
        )

    def test_can_parse_service_command(self):
        result = self.cli_parser.parse('aws ec2')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            parsed_params={},
            lineage=['aws'],
        )

    def test_can_parse_aws_command(self):
        result = self.cli_parser.parse('aws')
        self.assert_parsed_results_equal(
            result,
            current_command='aws',
            parsed_params={},
            global_params={},
            lineage=[],
        )

    def test_ignores_unknown_args(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --unknown-arg bar')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
        )

    def test_can_consume_one_or_more_nargs(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 i-2 i-3 ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={'instance-ids': ['i-1', 'i-2', 'i-3']},
            lineage=['aws', 'ec2'],
        )

    def test_can_consume_zero_or_one_nargs(self):
        model = copy.deepcopy(SAMPLE_MODEL)
        nargs_one_or_more = '?'
        model.index['arg_data']['aws.ec2']['stop-instances']['foo-arg'] = (
            'foo-arg', 'string',
            'stop-instances', 'aws.ec2', nargs_one_or_more, False)
        p = parser.CLIParser(model)
        self.assertEqual(
            p.parse(
                'aws ec2 stop-instances --foo-arg --debug'
            ).parsed_params['foo-arg'], None)
        self.assertEqual(
            p.parse(
                'aws ec2 stop-instances --foo-arg bar --debug'
            ).parsed_params['foo-arg'], 'bar')

    def test_truncates_line_based_on_location(self):
        # The 22nd index cuts off right after `stop-instances`.
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 i-2 i-3', 22)
        # We should not have parsed the 'instance-ids'.
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
        )

    def test_preserves_current_word(self):
        result = self.cli_parser.parse('aws ec2 stop-')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            parsed_params={},
            global_params={},
            lineage=['aws'],
            current_fragment='stop-',
        )

    def test_word_not_preserved_if_not_adjacent_to_word(self):
        result = self.cli_parser.parse('aws ec2 stop- ')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            parsed_params={},
            global_params={},
            lineage=['aws'],
            current_fragment='',
            unparsed_items=['stop-'],
        )

    def test_current_fragment_populated_on_work_break(self):
        result = self.cli_parser.parse('aws ec2 ')
        self.assert_parsed_results_equal(
            result,
            current_command='ec2',
            parsed_params={},
            global_params={},
            lineage=['aws'],
            current_fragment='',
        )

    def test_current_fragment_can_be_option(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst')
        # We should not have parsed the 'instance-ids'.
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
            current_fragment='--inst',
        )

    def test_option_not_preserved_when_space_separated(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
            current_fragment='',
            unparsed_items=['--inst'],
        )

    def test_can_have_unparsed_option_with_current_fragment(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst foo')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
            current_fragment='foo',
            unparsed_items=['--inst'],
        )

    def test_unknown_option_does_not_consume_arg(self):
        # In this case we're unlikely to offer any helpful
        # auto-completion, but we still need to decided where
        # we should put the 'foo' value.  I think it makes the
        # most sense to put this under "unparsed_items".
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst foo ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
            current_fragment='',
            unparsed_items=['--inst', 'foo'],
        )

    def test_can_handle_multiple_unknown_options(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --inst --foo ')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            parsed_params={},
            lineage=['aws', 'ec2'],
            current_fragment='',
            unparsed_items=['--inst', '--foo'],
        )

    def test_can_handle_unparsed_values(self):
        result = self.cli_parser.parse('aws ec stop-insta ')
        self.assert_parsed_results_equal(
            result,
            current_command='aws',
            current_fragment='',
            unparsed_items=['ec', 'stop-insta']
        )

    def test_can_handle_error_cases_gracefully(self):
        # The --foo-arg has nargs of None so this is an invalid command.
        # It would normally generate a parser error.  We should make sure
        # we handle this gracefully.
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --foo-arg a b --')
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            lineage=['aws', 'ec2'],
            current_fragment=None,
            unparsed_items=['b', '--'],
        )

    def test_current_fragment_populated_for_param_value(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-'
        )
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_param='instance-ids',
            parsed_params={'instance-ids': None},
            lineage=['aws', 'ec2'],
            current_fragment='i-',
            unparsed_items=[],
        )

    def test_params_populated_unless_last_value(self):
        result = self.cli_parser.parse(
            'aws ec2 stop-instances --instance-ids i-1 i-'
        )
        self.assert_parsed_results_equal(
            result,
            current_command='stop-instances',
            current_param='instance-ids',
            # Here i-1 is in the parsed params because we've already moved
            # on from that word, however, 'i-' is not added to the parsed
            # params dict because we're still parsing that value.  It goes in
            # the ``current_fragment`` attribute.
            parsed_params={'instance-ids': ['i-1']},
            lineage=['aws', 'ec2'],
            current_fragment='i-',
            unparsed_items=[],
        )

    def test_curent_fragment_works_for_global_params(self):
        result = self.cli_parser.parse(
            'aws --endpoint-url http',
        )
        self.assert_parsed_results_equal(
            result,
            current_command='aws',
            current_param='endpoint-url',
            # Here i-1 is in the parsed params because we've already moved
            # on from that word, however, 'i-' is not added to the parsed
            # params dict because we're still parsing that value.  It goes in
            # the ``current_fragment`` attribute.
            parsed_params={},
            lineage=[],
            current_fragment='http',
            unparsed_items=[],
        )

    def test_parses_positional(self):
        result = self.cli_parser.parse(
            'aws logs tail mygroup',
        )
        self.assert_parsed_results_equal(
            result,
            current_command='tail',
            current_param='group_name',
            parsed_params={},
            lineage=['aws', 'logs'],
            current_fragment='mygroup',
            unparsed_items=[],
        )

    def test_parses_positional_done(self):
        result = self.cli_parser.parse(
            'aws logs tail mygroup ',
        )
        self.assert_parsed_results_equal(
            result,
            current_command='tail',
            current_param=None,
            parsed_params={'group_name': 'mygroup'},
            lineage=['aws', 'logs'],
            current_fragment='',
            unparsed_items=[],
        )

    def test_parses_positional_parsed_only_once(self):
        result = self.cli_parser.parse(
            'aws logs tail mygroup random-content ',
        )
        self.assert_parsed_results_equal(
            result,
            current_command='tail',
            current_param=None,
            parsed_params={'group_name': 'mygroup'},
            lineage=['aws', 'logs'],
            current_fragment='',
            unparsed_items=['random-content'],
        )

    def test_parse_positional_with_option(self):
        result = self.cli_parser.parse(
            'aws logs tail mygroup --filter-pattern pat',
            )
        self.assert_parsed_results_equal(
            result,
            current_command='tail',
            current_param='filter-pattern',
            parsed_params={
                'filter-pattern': None,
                'group_name': 'mygroup'
            },
            lineage=['aws', 'logs'],
            current_fragment='pat',
            unparsed_items=[],
        )

    def test_parse_positional_with_option_before(self):
        result = self.cli_parser.parse(
            'aws logs tail --filter-pattern pattern mygroup',
            )
        self.assert_parsed_results_equal(
            result,
            current_command='tail',
            current_param='group_name',
            parsed_params={
                'filter-pattern': 'pattern',
            },
            lineage=['aws', 'logs'],
            current_fragment='mygroup',
            unparsed_items=[],
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
