# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import subprocess

from botocore.session import Session

from awscli.testutils import unittest
from awscli.testutils import mock
from awscli.testutils import FileCreator
from awscli.alias import InvalidAliasException
from awscli.alias import AliasLoader
from awscli.alias import AliasCommandInjector
from awscli.alias import BaseAliasCommand
from awscli.alias import ServiceAliasCommand
from awscli.alias import ExternalAliasCommand
from awscli.argparser import MainArgParser
from awscli.commands import CLICommand


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __contains__(self, key):
        return key in self.__dict__


class TestAliasLoader(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.alias_file = self.files.create_file('alias', '[toplevel]\n')

    def tearDown(self):
        self.files.remove_all()

    def test_get_aliases_non_existent_file(self):
        nonexistent_file = os.path.join(self.files.rootdir, 'no-exists')
        alias_interface = AliasLoader(nonexistent_file)
        self.assertEqual(alias_interface.get_aliases(), {})

    def test_get_aliases_empty_file(self):
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(alias_interface.get_aliases(), {})

    def test_get_aliases_missing_toplevel(self):
        with open(self.alias_file, 'w') as f:
            f.write('[unrelated-section]\n')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(alias_interface.get_aliases(), {})

    def test_get_aliases(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = my-alias-value')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(), {'my-alias': 'my-alias-value'})

    def test_get_aliases_with_alias_that_includes_parameter(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = my-alias-value --my-parameter my-value')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(),
            {'my-alias': 'my-alias-value --my-parameter my-value'})

    def test_get_aliases_with_alias_that_includes_newlines(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = my-alias-value\n')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(), {'my-alias': 'my-alias-value'})

    def test_get_aliases_with_alias_that_is_indented(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = \n  my-alias-value\n')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(), {'my-alias': 'my-alias-value'})

    def test_get_aliases_with_multiple_lines(self):
        with open(self.alias_file, 'a+') as f:
            f.write(
                'my-alias = \n'
                '  my-alias-value \ \n'
                '  --parameter foo\n')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(),
            # The backslash and newline should be preserved, but
            # still have the beginning and end newlines removed.
            {'my-alias': 'my-alias-value \\\n--parameter foo'})

    def test_get_aliases_with_multiple_aliases(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = my-alias-value\n')
            f.write('my-second-alias = my-second-alias-value\n')
        alias_interface = AliasLoader(self.alias_file)
        self.assertEqual(
            alias_interface.get_aliases(),
            {'my-alias': 'my-alias-value',
             'my-second-alias': 'my-second-alias-value'})


class TestAliasCommandInjector(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.alias_file = self.files.create_file('alias', '[toplevel]\n')
        self.alias_loader = AliasLoader(self.alias_file)
        self.session = mock.Mock(spec=Session)
        self.alias_cmd_injector = AliasCommandInjector(
            self.session, self.alias_loader)
        self.command_table = {}
        self.parser = MainArgParser(
            command_table=self.command_table,
            version_string='version',
            description='description',
            argument_table={}
        )

    def tearDown(self):
        self.files.remove_all()

    def test_service_alias_command(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = my-alias-value\n')

        self.alias_cmd_injector.inject_aliases(
            self.command_table, self.parser)
        self.assertIn('my-alias', self.command_table)
        self.assertIsInstance(
            self.command_table['my-alias'], ServiceAliasCommand)

    def test_external_alias_command(self):
        with open(self.alias_file, 'a+') as f:
            f.write('my-alias = !my-alias-value\n')

        self.alias_cmd_injector.inject_aliases(
            self.command_table, self.parser)
        self.assertIn('my-alias', self.command_table)
        self.assertIsInstance(
            self.command_table['my-alias'], ExternalAliasCommand)

    def test_clobbers_builtins(self):
        builtin_cmd = mock.Mock(spec=CLICommand)
        self.command_table['builtin'] = builtin_cmd

        with open(self.alias_file, 'a+') as f:
            f.write('builtin = my-alias-value\n')

        self.alias_cmd_injector.inject_aliases(
            self.command_table, self.parser)
        self.assertIn('builtin', self.command_table)
        self.assertIsInstance(
            self.command_table['builtin'], ServiceAliasCommand)

    def test_shadow_proxy_command(self):
        builtin_cmd = mock.Mock(spec=CLICommand)
        builtin_cmd.name = 'builtin'
        self.command_table['builtin'] = builtin_cmd

        with open(self.alias_file, 'a+') as f:
            f.write('builtin = builtin\n')

        self.alias_cmd_injector.inject_aliases(
            self.command_table, self.parser)

        self.command_table['builtin'](
            [], FakeParsedArgs(command='builtin'))
        # The builtin command should be passed to the alias
        # command when added to the table.
        builtin_cmd.assert_called_with(
            [], FakeParsedArgs(command='builtin'))


class TestBaseAliasCommand(unittest.TestCase):
    def test_name(self):
        alias_cmd = BaseAliasCommand('alias-name', 'alias-value')
        self.assertEqual(alias_cmd.name, 'alias-name')
        alias_cmd.name = 'new-alias-name'
        self.assertEqual(alias_cmd.name, 'new-alias-name')


class TestServiceAliasCommand(unittest.TestCase):
    def setUp(self):
        self.alias_name = 'myalias'
        self.session = mock.Mock(spec=Session)

    def create_command_table(self, services):
        command_table = {}
        for service in services:
            command_table[service] = mock.Mock(spec=CLICommand)
        return command_table

    def create_parser(self, command_table, extra_params=None):
        parser = MainArgParser(
            command_table=command_table,
            version_string='version',
            description='description',
            argument_table={}
        )
        if extra_params:
            for extra_param in extra_params:
                parser.add_argument('--'+extra_param)
        return parser

    def test_alias_with_only_service_command(self):
        alias_value = 'myservice'

        command_table = self.create_command_table([alias_value])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            [], FakeParsedArgs(command='myservice'))

    def tests_alias_with_shadow_proxy_command(self):
        alias_value = 'some-service'
        self.alias_name = alias_value

        shadow_proxy_command = mock.Mock(spec=CLICommand)
        shadow_proxy_command.name = alias_value

        command_table = {}
        parser = self.create_parser(command_table)

        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table,
            parser, shadow_proxy_command)
        command_table[self.alias_name] = alias_cmd

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        shadow_proxy_command.assert_called_with(
            [], FakeParsedArgs(command=alias_value))

    def test_alias_with_shadow_proxy_command_no_match(self):
        alias_value = 'some-other-command'
        self.alias_name = 'some-service'

        shadow_proxy_command = mock.Mock(spec=CLICommand)
        shadow_proxy_command.name = 'some-service'

        command_table = self.create_command_table([alias_value])
        parser = self.create_parser(command_table)

        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table,
            parser, shadow_proxy_command)
        command_table[self.alias_name] = alias_cmd

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table[alias_value].assert_called_with(
            [], FakeParsedArgs(command=alias_value))
        # Even though it was provided, it should not be called because
        # the alias value did not match the shadow command name.
        self.assertFalse(shadow_proxy_command.called)

    def test_alias_with_operation_command(self):
        alias_value = 'myservice myoperation'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        parsed_globals = FakeParsedArgs(command=self.alias_name)
        alias_cmd([], parsed_globals)
        command_table['myservice'].assert_called_with(
            ['myoperation'], FakeParsedArgs(command='myservice'))

    def test_alias_then_help_command(self):
        alias_value = 'myservice myoperation'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        parsed_globals = FakeParsedArgs(command=self.alias_name)
        alias_cmd(['help'], parsed_globals)
        command_table['myservice'].assert_called_with(
            ['myoperation', 'help'], FakeParsedArgs(command='myservice'))

    def test_alias_then_additional_parameters(self):
        alias_value = 'myservice myoperation'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        parsed_globals = FakeParsedArgs(command=self.alias_name)
        alias_cmd(['--parameter', 'val'], parsed_globals)
        command_table['myservice'].assert_called_with(
            ['myoperation', '--parameter', 'val'],
            FakeParsedArgs(command='myservice')
        )

    def test_alias_with_operation_and_parameters(self):
        alias_value = 'myservice myoperation --my-parameter val'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation', '--my-parameter', 'val'],
            FakeParsedArgs(command='myservice')
        )

    def test_alias_with_operation_and_global_parameters(self):
        alias_value = 'myservice myoperation --global-param val'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(
            command_table, extra_params=['global-param'])
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation'],
            FakeParsedArgs(command='myservice', global_param='val')
        )

    def test_maintains_global_defaults_when_missing_from_alias(self):
        alias_value = 'myservice myoperation'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        parser.add_argument('--global-with-default', default='default')
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)
        alias_cmd(
            [],
            FakeParsedArgs(
                command=self.alias_name, global_with_default='default')
        )
        command_table['myservice'].assert_called_with(
            ['myoperation'],
            FakeParsedArgs(
                command='myservice', global_with_default='default')
        )

    def test_sets_global_parameters_when_differs_from_defaults(self):
        alias_value = 'myservice myoperation --global-with-default non-default'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        parser.add_argument('--global-with-default', default='default')
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation'],
            FakeParsedArgs(
                command='myservice', global_with_default='non-default')
        )

    def test_global_parameters_can_be_emitted_and_modified(self):
        alias_value = 'myservice myoperation --global-param val'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(
            command_table, extra_params=['global-param'])
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        def replace_global_param_value_with_foo(event_name, **kwargs):
            parsed_args = kwargs['parsed_args']
            parsed_args.global_param = 'foo'

        self.session.emit.side_effect = replace_global_param_value_with_foo
        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        self.session.emit.assert_called_with(
            'top-level-args-parsed', parsed_args=mock.ANY,
            session=self.session)

        command_table['myservice'].assert_called_with(
            ['myoperation'],
            FakeParsedArgs(command='myservice', global_param='foo')
        )

    def test_properly_handles_multiple_spaces(self):
        alias_value = (
            'myservice myoperation    --my-parameter val'
        )

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation', '--my-parameter', 'val'],
            FakeParsedArgs(command='myservice')
        )

    def test_properly_parses_aliases_broken_by_multiple_lines(self):
        alias_value = (
            'myservice myoperation \\'
            '\n--my-parameter val'
        )

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation', '--my-parameter', 'val'],
            FakeParsedArgs(command='myservice')
        )

    def test_properly_preserves_quoted_values(self):
        alias_value = (
            'myservice myoperation --my-parameter \' \n$""\''
        )

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        alias_cmd([], FakeParsedArgs(command=self.alias_name))
        command_table['myservice'].assert_called_with(
            ['myoperation', '--my-parameter', ' \n$""'],
            FakeParsedArgs(command='myservice')
        )

    def test_errors_when_service_command_is_invalid(self):
        alias_value = 'non-existent-service myoperation'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        with self.assertRaises(SystemExit):
            # Even though we catch the system exit, a message will always
            # be forced to screen because it happened at system exit.
            # The patch is to ensure it does not get displayed by nosetests.
            with mock.patch('sys.stderr'):
                alias_cmd([], FakeParsedArgs(command=self.alias_name))

    def test_errors_when_no_service_command(self):
        alias_value = '--global-param=val'

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(
            command_table, extra_params=['global-param'])
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        with self.assertRaises(SystemExit):
            # Even though we catch the system exit, a message will always
            # be forced to screen because it happened at system exit.
            # The patch is to ensure it does not get displayed by nosetests.
            with mock.patch('sys.stderr'):
                alias_cmd([], FakeParsedArgs(command=self.alias_name))

    def test_errors_when_shell_cannot_parse_alias(self):
        # Ending with a escape character that does not escape anything
        # is invalid and cannot be properly parsed.
        alias_value = (
            'myservice myoperation \\'
        )

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(command_table)
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        with self.assertRaises(InvalidAliasException):
            alias_cmd([], FakeParsedArgs(command=self.alias_name))

    def test_errors_when_unsupported_global_parameter_in_alias(self):
        # Unsupported global parameters are: --profile and --debug
        alias_value = (
            'myservice myoperation --profile value'
        )

        command_table = self.create_command_table(['myservice'])
        parser = self.create_parser(
            command_table, extra_params=['profile'])
        alias_cmd = ServiceAliasCommand(
            self.alias_name, alias_value, self.session, command_table, parser)

        with self.assertRaises(InvalidAliasException):
            alias_cmd([], FakeParsedArgs(command=self.alias_name))


class TestExternalAliasCommand(unittest.TestCase):
    def setUp(self):
        self.subprocess_call = mock.Mock(spec=subprocess.call)

    def test_run_external_command(self):
        alias_value = '!ls'
        alias_cmd = ExternalAliasCommand(
            'alias-name', alias_value, invoker=self.subprocess_call)
        alias_cmd([], FakeParsedArgs(command='alias-name'))
        self.subprocess_call.assert_called_with('ls', shell=True)

    def test_external_command_returns_rc_of_subprocess_call(self):
        alias_value = '!ls'
        alias_cmd = ExternalAliasCommand(
            'alias-name', alias_value, invoker=self.subprocess_call)
        self.subprocess_call.return_value = 1
        self.assertEqual(
            alias_cmd([], FakeParsedArgs(command='alias-name')), 1)

    def test_external_command_uses_literal_alias_value(self):
        alias_value = (
            '!f () {\n'
            '  ls .\n'
            '}; f'
        )
        alias_cmd = ExternalAliasCommand(
            'alias-name', alias_value, invoker=self.subprocess_call)
        alias_cmd([], FakeParsedArgs(command='alias-name'))
        self.subprocess_call.assert_called_with(alias_value[1:], shell=True)

    def test_external_command_then_additional_args(self):
        alias_value = '!f () { ls "$1" }; f'
        alias_cmd = ExternalAliasCommand(
            'alias-name', alias_value, invoker=self.subprocess_call)
        alias_cmd(['extra'], FakeParsedArgs(command='alias-name'))
        self.subprocess_call.assert_called_with(
            'f () { ls "$1" }; f extra', shell=True)
