# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pprint
import difflib

import mock

from botocore.compat import OrderedDict
from botocore.model import OperationModel
from awscli.clidriver import (
    CLIDriver, ServiceCommand, ServiceOperation, CLICommand)
from awscli.arguments import BaseCLIArgument, CustomArgument
from awscli.help import ProviderHelpCommand
from awscli.completer import Completer
from awscli.testutils import unittest
from awscli.customizations.commands import BasicCommand


class BaseCompleterTest(unittest.TestCase):
    def setUp(self):
        self.clidriver_creator = MockCLIDriverFactory()

    def assert_completion(self, completer, cmdline, expected_results,
                          point=None):
        if point is None:
            point = len(cmdline)
        actual = set(completer.complete(cmdline, point))
        expected = set(expected_results)

        if not actual == expected:
            # Borrowed from assertDictEqual, though this doesn't
            # handle the case when unicode literals are used in one
            # dict but not in the other (and we want to consider them
            # as being equal).
            pretty_d1 = pprint.pformat(actual, width=1).splitlines()
            pretty_d2 = pprint.pformat(expected, width=1).splitlines()
            diff = ('\n' + '\n'.join(difflib.ndiff(pretty_d1, pretty_d2)))
            raise AssertionError("Results are not equal:\n%s" % diff)
        self.assertEqual(actual, expected)


class TestCompleter(BaseCompleterTest):
    def test_complete_services(self):
        commands = {
            'subcommands': {
                'foo': {},
                'bar': {
                    'subcommands': {
                        'baz': {}
                    }
                }
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws ', ['foo', 'bar'])

    def test_complete_partial_service_name(self):
        commands = {
            'subcommands': {
                'cloudfront': {},
                'cloudformation': {},
                'cloudhsm': {},
                'sts': {}
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws cloud', [
            'cloudfront', 'cloudformation', 'cloudhsm'])
        self.assert_completion(completer, 'aws cloudf', [
            'cloudfront', 'cloudformation'])
        self.assert_completion(completer, 'aws cloudfr', ['cloudfront'])
        self.assert_completion(completer, 'aws cloudfront', [])

    def test_complete_on_invalid_service(self):
        commands = {
            'subcommands': {
                'foo': {},
                'bar': {
                    'subcommands': {
                        'baz': {}
                    }
                }
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws bin', [])

    def test_complete_top_level_args(self):
        commands = {
            'subcommands': {},
            'arguments': ['foo', 'bar']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws --', ['--foo', '--bar'])

    def test_complete_partial_top_level_arg(self):
        commands = {
            'subcommands': {},
            'arguments': ['foo', 'bar', 'foobar', 'fubar']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws --f', [
            '--foo', '--fubar', '--foobar'])
        self.assert_completion(completer, 'aws --fo', [
            '--foo', '--foobar'])
        self.assert_completion(completer, 'aws --foob', ['--foobar'])
        self.assert_completion(completer, 'aws --foobar', [])

    def test_complete_top_level_arg_with_arg_already_used(self):
        commands = {
            'subcommands': {
                'baz': {}
            },
            'arguments': ['foo', 'bar']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws --foo --f', [])

    def test_complete_service_commands(self):
        commands = {
            'subcommands': {
                'foo': {
                    'subcommands': {
                        'bar': {
                            'arguments': ['bin']
                        },
                        'baz': {}
                    }
                }
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo ', ['bar', 'baz'])

    def test_complete_partial_service_commands(self):
        commands = {
            'subcommands': {
                'foo': {
                    'subcommands': {
                        'barb': {
                            'arguments': ['nil']
                        },
                        'baz': {},
                        'biz': {},
                        'foobar': {}
                    }
                }
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo b', ['barb', 'baz', 'biz'])
        self.assert_completion(completer, 'aws foo ba', ['barb', 'baz'])
        self.assert_completion(completer, 'aws foo bar', ['barb'])
        self.assert_completion(completer, 'aws foo barb', [])

    def test_complete_service_arguments(self):
        commands = {
            'subcommands': {
                'foo': {}
            },
            'arguments': ['baz', 'bin']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo --', ['--baz', '--bin'])

    def test_complete_partial_service_arguments(self):
        commands = {
            'subcommands': {
                'biz': {}
            },
            'arguments': ['foo', 'bar', 'foobar', 'fubar']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws biz --f', [
            '--foo', '--fubar', '--foobar'])
        self.assert_completion(completer, 'aws biz --fo', [
            '--foo', '--foobar'])
        self.assert_completion(completer, 'aws biz --foob', ['--foobar'])

    def test_complete_service_arg_with_arg_already_used(self):
        commands = {
            'subcommands': {
                'baz': {}
            },
            'arguments': ['foo', 'bar']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws baz --foo --f', [])

    def test_complete_operation_arguments(self):
        commands = {
            'subcommands': {
                'foo': {'subcommands': {
                    'bar': {'arguments': ['baz']}
                }}
            },
            'arguments': ['bin']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo bar --', ['--baz', '--bin'])

    def test_complete_partial_operation_arguments(self):
        commands = {
            'subcommands': {
                'foo': {'subcommands': {
                    'bar': {'arguments': ['base', 'baz', 'air']}
                }}
            },
            'arguments': ['bin']
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo bar --b', [
            '--base', '--baz', '--bin'])
        self.assert_completion(completer, 'aws foo bar --ba', [
            '--base', '--baz'])
        self.assert_completion(completer, 'aws foo bar --bas', ['--base'])
        self.assert_completion(completer, 'aws foo bar --base', [])

    def test_complete_operation_arg_when_arg_already_used(self):
        commands = {
            'subcommands': {
                'foo': {'subcommands': {
                    'bar': {'arguments': ['baz']}
                }}
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo bar --baz --b', [])

    def test_complete_positional_argument(self):
        commands = {
            'subcommands': {
                'foo': {'subcommands': {
                    'bar': {'arguments': [
                        'baz',
                        CustomArgument('bin', positional_arg=True)
                    ]}
                }}
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws foo bar --bin ', [])
        self.assert_completion(completer, 'aws foo bar --bin blah --',
                               ['--baz'])

    def test_complete_undocumented_command(self):
        class UndocumentedCommand(CLICommand):
            _UNDOCUMENTED = True
        commands = {
            'subcommands': {
                'foo': {},
                'bar': UndocumentedCommand()
            },
            'arguments': []
        }
        completer = Completer(
            self.clidriver_creator.create_clidriver(commands))
        self.assert_completion(completer, 'aws ', ['foo'])


class TestCompleteCustomCommands(BaseCompleterTest):
    def setUp(self):
        super(TestCompleteCustomCommands, self).setUp()
        custom_arguments = [
            {'name': 'recursive'},
            {'name': 'sse'}
        ]
        custom_commands = [
            self.create_custom_command('mb'),
            self.create_custom_command('mv'),
            self.create_custom_command('cp', arguments=custom_arguments)
        ]
        custom_service = self.create_custom_command('s3', custom_commands)
        clidriver = self.clidriver_creator.create_clidriver({
            'subcommands': {
                's3': custom_service['command_class'](mock.Mock()),
                'foo': {}
            },
            'arguments': ['bar']
        })
        self.completer = Completer(clidriver)

    def create_custom_command(self, name, sub_commands=None, arguments=None):
        arg_table = arguments
        if arg_table is None:
            arg_table = []

        subs = sub_commands
        if subs is None:
            subs = []

        class CustomCommand(BasicCommand):
            NAME = name
            ARG_TABLE = arg_table
            SUBCOMMANDS = subs
        return {'name': name, 'command_class': CustomCommand}

    def test_complete_custom_service(self):
        self.assert_completion(self.completer, 'aws ', ['s3', 'foo'])

    def test_complete_custom_command(self):
        self.assert_completion(self.completer, 'aws s3 ', ['mb', 'mv', 'cp'])

    def test_complete_partial_custom_command(self):
        self.assert_completion(self.completer, 'aws s3 m', ['mb', 'mv'])

    def test_complete_custom_command_arguments(self):
        self.assert_completion(self.completer, 'aws s3 cp --', [
            '--bar', '--recursive', '--sse'])

    def test_complete_custom_command_arguments_with_arg_already_used(self):
        self.assert_completion(self.completer, 'aws s3 cp --recursive --', [
            '--bar', '--sse'])


class MockCLIDriverFactory(object):
    def create_clidriver(self, commands=None, profiles=None):
        session = mock.Mock()
        session.get_data.return_value = None
        if profiles is not None and isinstance(profiles, list):
            session.available_profiles = profiles
        else:
            session.available_profiles = ['default']
        clidriver = mock.Mock(spec=CLIDriver)
        clidriver.create_help_command.return_value = \
            self._create_top_level_help(commands, session)

        clidriver.session = session
        return clidriver

    def _create_top_level_help(self, commands, session):
        command_table = self.create_command_table(
            commands.get('subcommands', {}), self._create_service_command)
        argument_table = self.create_argument_table(
            commands.get('arguments', []))
        return ProviderHelpCommand(
            session, command_table, argument_table, None, None, None)

    def _create_service_command(self, name, command):
        command_table = self.create_command_table(
            command.get('subcommands', {}), self._create_operation_command)
        service_command = ServiceCommand(name, None)
        service_command._service_model = {}
        service_command._command_table = command_table
        return service_command

    def _create_operation_command(self, name, command):
        argument_table = self.create_argument_table(
            command.get('arguments', []))
        mock_operation = mock.Mock(spec=OperationModel)
        mock_operation.deprecated = False
        operation = ServiceOperation(name, 'parent', None, mock_operation,
                                     None)
        operation._arg_table = argument_table
        return operation

    def create_command_table(self, commands, command_creator):
        if not commands:
            return OrderedDict()
        command_table = OrderedDict()
        for name, command in commands.items():
            if isinstance(command, CLICommand):
                # Already a valid command, no need to fake one
                command_table[name] = command
            else:
                command_table[name] = command_creator(name, command)
        return command_table

    def create_argument_table(self, arguments):
        if not arguments:
            return OrderedDict()
        argument_table = OrderedDict()
        for arg in arguments:
            if isinstance(arg, BaseCLIArgument):
                argument_table[arg.name] = arg
            else:
                argument_table[arg] = BaseCLIArgument(arg)
        return argument_table
