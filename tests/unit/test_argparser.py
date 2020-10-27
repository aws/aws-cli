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

from awscli.testutils import unittest
from awscli.argparser import CommandAction, FirstPassGlobalArgParser


class TestCommandAction(unittest.TestCase):
    def setUp(self):
        self.parser = ArgumentParser()

    def test_choices(self):
        command_table = {'pre-existing': object()}
        self.parser.add_argument(
            'command', action=CommandAction, command_table=command_table)
        parsed_args = self.parser.parse_args(['pre-existing'])
        self.assertEqual(parsed_args.command, 'pre-existing')

    def test_choices_added_after(self):
        command_table = {'pre-existing': object()}
        self.parser.add_argument(
            'command', action=CommandAction, command_table=command_table)
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
