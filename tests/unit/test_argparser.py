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
    CommandAction,
    FirstPassGlobalArgParser,
    is_help_option_present,
    strip_help_options,
)
from awscli.testutils import unittest


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


class TestHelpOptionExactTokenOnly(unittest.TestCase):
    """Only the literal ``--help`` token counts as help.

    Abbreviations ``--he``/``--hel`` (and ``--h``) are NOT help requests. They
    fall through to the normal parser as unknown options.
    ``is_help_option_present`` and ``strip_help_options`` share the single
    :func:`_is_help_option_token` predicate, so they can never disagree:
    detection returns True exactly for the tokens stripping removes.
    """

    def _detects_and_strips_consistently(self, token):
        args = ['ec2', 'describe-instances', token]
        detected = is_help_option_present(args)
        stripped = strip_help_options(args)
        removed = token not in stripped
        # Invariant: a token detected as help is removed by strip, and a token
        # not detected as help is left in place.
        self.assertEqual(
            detected,
            removed,
            f"detection/stripping disagree for {token!r}: "
            f"detected={detected} removed={removed} stripped={stripped}",
        )
        return detected

    def test_exact_help_token_is_recognized(self):
        self.assertTrue(
            self._detects_and_strips_consistently('--help'),
            "the literal '--help' token must be recognized as help",
        )

    def test_abbreviations_are_not_help(self):
        # Exact-token-only: no prefix of --help is accepted, not even --hel.
        for token in ['--he', '--hel', '--h', '--he', '--']:
            self.assertFalse(
                self._detects_and_strips_consistently(token),
                f"{token!r} must NOT be treated as help (exact-token-only)",
            )

    def test_help_with_attached_value_is_not_a_bare_flag(self):
        # '--instance-ids=--help' carries '--help' as a value, not a help token,
        # and '--help=x' is malformed for a store_true flag; neither is help.
        for token in ['--instance-ids=--help', '--help=x']:
            args = ['ec2', 'describe-instances', token]
            self.assertFalse(is_help_option_present(args))
            self.assertEqual(strip_help_options(args), args)
