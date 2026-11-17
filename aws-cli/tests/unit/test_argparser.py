# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import ArgumentParser

from awscli.argparser import (
    ArgParseException,
    CommandAction,
    FirstPassGlobalArgParser,
    MainArgParser,
    ServiceArgParser,
    format_unknown_options_error,
    get_option_suggestion_candidates,
)
from awscli.arguments import CustomArgument
from awscli.testutils import mock, unittest


class TestCommandAction(unittest.TestCase):
    def setUp(self):
        self.parser = ArgumentParser()

    def test_choices(self):
        command_table = {'pre-existing': object()}
        self.parser.add_argument(
            'command', action=CommandAction, command_table=command_table
        )
        parsed_args = self.parser.parse_args(['pre-existing'])
        self.assertEqual(parsed_args.command, 'pre-existing')

    def test_choices_added_after(self):
        command_table = {'pre-existing': object()}
        self.parser.add_argument(
            'command', action=CommandAction, command_table=command_table
        )
        command_table['after'] = object()

        # The pre-existing command should still be able to be parsed
        parsed_args = self.parser.parse_args(['pre-existing'])
        self.assertEqual(parsed_args.command, 'pre-existing')

        # The command added after the argument's creation should be
        # able to be parsed as well.
        parsed_args = self.parser.parse_args(['after'])
        self.assertEqual(parsed_args.command, 'after')


class TestPartialGlobalArgsParser(unittest.TestCase):
    def setUp(self):
        self.parser = FirstPassGlobalArgParser()

    def test_can_parse_profile(self):
        parsed_args, _ = self.parser.parse_known_args(['--profile', 'foo'])
        self.assertEqual(parsed_args.profile, 'foo')

    def test_can_parse_debug(self):
        parsed_args, _ = self.parser.parse_known_args(['--debug'])
        self.assertTrue(parsed_args.debug)

    def test_debug_if_false_by_default(self):
        parsed_args, _ = self.parser.parse_known_args(['--foo'])
        self.assertFalse(parsed_args.debug)

    def test_not_parse_unknown_args(self):
        parsed_args, remains = self.parser.parse_known_args(
            ['--debug', '--foo', 'bar']
        )
        self.assertEqual(parsed_args.debug, True)
        self.assertEqual(remains, ['--foo', 'bar'])


class TestMainArgParserHelp(unittest.TestCase):
    def setUp(self):
        argument_table = {
            'help': CustomArgument('help', action='store_true'),
            'query': CustomArgument('query'),
            'region': CustomArgument('region'),
        }
        self.parser = MainArgParser(
            command_table={'ec2': object()},
            version_string='aws-cli/0.0.0',
            description='',
            argument_table=argument_table,
        )

    def test_help_parsed_like_other_global_args(self):
        parsed, remaining = self.parser.parse_known_args(
            ['ec2', '--region', 'us-west-2', 'describe-instances', '--help']
        )
        self.assertTrue(parsed.help)
        self.assertEqual(parsed.command, 'ec2')
        self.assertEqual(parsed.region, 'us-west-2')
        self.assertEqual(remaining, ['describe-instances'])

    def test_help_abbreviation(self):
        parsed, _ = self.parser.parse_known_args(['ec2', '--he'])
        self.assertTrue(parsed.help)

    def test_command_not_required_with_help(self):
        parsed, remaining = self.parser.parse_known_args(
            ['--region', 'us-west-2', '--help']
        )
        self.assertTrue(parsed.help)
        self.assertIsNone(parsed.command)
        self.assertEqual(parsed.region, 'us-west-2')
        self.assertEqual(remaining, [])

    def test_command_required_without_help(self):
        with self.assertRaisesRegex(
            ArgParseException, 'the following arguments are required: command'
        ):
            self.parser.parse_known_args(['--region', 'us-west-2'])

    def test_missing_option_value_allowed_with_help(self):
        parsed, remaining = self.parser.parse_known_args(
            ['ec2', 'describe-instances', '--query', '--help']
        )
        self.assertTrue(parsed.help)
        self.assertIsNone(parsed.query)
        self.assertEqual(parsed.command, 'ec2')
        self.assertEqual(remaining, ['describe-instances'])

    def test_missing_option_value_errors_without_help(self):
        with self.assertRaisesRegex(
            ArgParseException, 'argument --query: expected one argument'
        ):
            self.parser.parse_known_args(['ec2', '--query'])

    def test_invalid_command_errors_with_help(self):
        with self.assertRaisesRegex(ArgParseException, 'invalid choice'):
            self.parser.parse_known_args(['fake-service', '--help'])

    def test_help_after_end_of_options_is_not_help(self):
        parsed, remaining = self.parser.parse_known_args(
            ['ec2', '--', '--help']
        )
        self.assertFalse(parsed.help)
        self.assertIn('--help', remaining)

    def test_explicit_option_value_is_not_help(self):
        parsed, _ = self.parser.parse_known_args(['ec2', '--query=--help'])
        self.assertFalse(parsed.help)
        self.assertEqual(parsed.query, '--help')


class TestServiceArgParserHelp(unittest.TestCase):
    def test_operation_required_by_default(self):
        parser = ServiceArgParser({'describe-instances': object()}, 'ec2')
        with self.assertRaisesRegex(
            ArgParseException,
            'the following arguments are required: operation',
        ):
            parser.parse_known_args([])

    def test_operation_optional_in_help_mode(self):
        parser = ServiceArgParser(
            {'describe-instances': object()}, 'ec2', help_mode=True
        )
        parsed, remaining = parser.parse_known_args(['--unknown'])
        self.assertIsNone(parsed.operation)
        self.assertEqual(remaining, ['--unknown'])


class TestGetOptionSuggestionCandidates(unittest.TestCase):
    def test_includes_documented_options_and_globals_only(self):
        # Suggest options and globals, excluding positional and hidden args.
        hidden = CustomArgument('marker')
        hidden._UNDOCUMENTED = True
        arg_table = {
            'instance-ids': CustomArgument('instance-ids'),
            'outfile': CustomArgument('outfile', positional_arg=True),
            'marker': hidden,
        }
        session = mock.Mock()
        session.get_data.return_value = {
            'options': {'region': {}, 'debug': {}}
        }

        candidates = get_option_suggestion_candidates(arg_table, session)

        self.assertCountEqual(candidates, ['instance-ids', 'region', 'debug'])


class TestFormatUnknownOptionsError(unittest.TestCase):
    def setUp(self):
        self.candidates = ['region', 'instance-ids', 'dry-run', 'no-dry-run']

    def test_no_suggestions(self):
        msg = format_unknown_options_error(['--foo', 'bar'], self.candidates)
        self.assertEqual(msg, 'Unknown options: --foo, bar')

    def test_suggests_close_match(self):
        msg = format_unknown_options_error(
            ['--regoin', 'us-west-2'], self.candidates
        )
        self.assertEqual(
            msg,
            'Unknown options: --regoin, us-west-2\n\n'
            'Maybe you meant:\n'
            '  * --region (instead of --regoin)',
        )

    def test_suggests_for_each_unknown_option(self):
        msg = format_unknown_options_error(
            ['--regoin', '--instance-idz'], self.candidates
        )
        self.assertIn('  * --region (instead of --regoin)', msg)
        self.assertIn('  * --instance-ids (instead of --instance-idz)', msg)

    def test_deduplicates_repeated_unknown_option(self):
        msg = format_unknown_options_error(
            ['--regoin', 'a', '--regoin', 'b'], self.candidates
        )
        self.assertEqual(
            msg,
            'Unknown options: --regoin, a, --regoin, b\n\n'
            'Maybe you meant:\n'
            '  * --region (instead of --regoin)',
        )

    def test_ignores_value_after_equals(self):
        msg = format_unknown_options_error(
            ['--regoin=us-west-2'], self.candidates
        )
        self.assertIn('  * --region (instead of --regoin)', msg)

    def test_does_not_match_values(self):
        msg = format_unknown_options_error(['region'], self.candidates)
        self.assertNotIn('Maybe you meant', msg)
