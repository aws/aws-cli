# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import Namespace
from unittest.mock import Mock

import pytest

from awscli.commands import CLICommand, call_command, help_requested


class RecordingCommand(CLICommand):
    def __init__(self, handles_help_flag=None):
        if handles_help_flag is not None:
            self._HANDLES_HELP_FLAG = handles_help_flag
        self.calls = []

    def __call__(self, args, parsed_globals):
        self.calls.append(args)
        return 0


class TestHelpRequested:
    @pytest.mark.parametrize(
        'parsed_globals, expected',
        [
            (Namespace(help=True), True),
            (Namespace(help=False), False),
            (Namespace(), False),
            (None, False),
            # A mock creates a truthy help attribute on access, but no
            # one asked for help.
            (Mock(), False),
        ],
        ids=['true', 'false', 'no-help-attribute', 'none', 'mock'],
    )
    def test_help_requested(self, parsed_globals, expected):
        assert help_requested(parsed_globals) is expected


class TestCallCommand:
    def test_passes_help_flag_to_command_that_does_not_handle_it(self):
        command = RecordingCommand()
        call_command(command, ['--foo', 'bar'], Namespace(help=True))
        assert command.calls == [['--foo', 'bar', '--help']]

    def test_does_not_pass_help_flag_to_command_that_handles_it(self):
        command = RecordingCommand(handles_help_flag=True)
        call_command(command, ['--foo', 'bar'], Namespace(help=True))
        assert command.calls == [['--foo', 'bar']]

    @pytest.mark.parametrize(
        'parsed_globals',
        [Namespace(help=False), Namespace(), None],
        ids=['help-false', 'no-help-attribute', 'no-parsed-globals'],
    )
    def test_args_unchanged_without_help(self, parsed_globals):
        command = RecordingCommand()
        call_command(command, ['--foo'], parsed_globals)
        assert command.calls == [['--foo']]

    def test_command_without_marker_gets_help_flag(self):
        # Objects that aren't CLICommand subclasses, such as plugin
        # commands written as plain classes, default to receiving --help.
        command = Mock(spec=['__call__'])
        call_command(command, [], Namespace(help=True))
        command.assert_called_once_with(['--help'], Namespace(help=True))

    def test_mock_parsed_globals_does_not_add_help_flag(self):
        command = RecordingCommand()
        call_command(command, ['--foo'], Mock())
        assert command.calls == [['--foo']]

    def test_does_not_modify_caller_args(self):
        command = RecordingCommand()
        args = ['--foo']
        call_command(command, args, Namespace(help=True))
        assert args == ['--foo']

    def test_returns_command_result(self):
        command = Mock(spec=['__call__'], return_value=7)
        assert call_command(command, [], Namespace(help=False)) == 7
