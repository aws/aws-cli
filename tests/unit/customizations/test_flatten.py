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
from awscli.testutils import unittest

import mock

from awscli.arguments import CLIArgument
from awscli.customizations import utils
from awscli.customizations.flatten import FlattenedArgument, FlattenArguments

from botocore.operation import Operation


def _hydrate(params, container, cli_type, key, value):
    """
    An example to hydrate a complex structure with custom value logic. In this
    case we create a nested structure and divide the value by 100.
    """
    params['bag'] = {
        'ArgumentBaz': {
            'SomeValueAbc': value / 100.0
        }
    }


FLATTEN_CONFIG = {
    'command-name': {
        'original-argument': {
            "keep": False,
            "flatten": {
                "ArgumentFoo": {
                    "name": "foo"
                },
                "ArgumentBar": {
                    "name": "bar",
                    "help_text": "Some help text",
                    "required": True,
                    "hydrate_value": lambda x: x.upper()
                }
            }
        },
        'another-original-argument': {
            "keep": True,
            "flatten": {
                "ArgumentBaz.SomeValue": {
                    "name": "baz",
                    "hydrate": _hydrate
                }
            }
        }
    }
}

class TestFlattenedArgument(unittest.TestCase):
    def test_basic_argument(self):
        container = mock.Mock()
        container.argument_model.name = 'bag'
        kwargs = {
            'container': container,
            'prop': 'ArgumentFoo'
        }
        kwargs['container'].py_name = 'bag'
        kwargs.update(FLATTEN_CONFIG['command-name']['original-argument']
                                    ['flatten']['ArgumentFoo'])
        arg = FlattenedArgument(**kwargs)

        self.assertEqual('foo', arg.name)
        self.assertEqual('', arg.documentation)
        self.assertEqual(False, arg.required)

        params = {}
        arg.add_to_params(params, 'value')
        self.assertEqual('value', params['bag']['ArgumentFoo'])

    def test_hydrate_value_argument(self):
        container = mock.Mock()
        container.argument_model.name = 'bag'
        kwargs = {
            'container': container,
            'prop': 'ArgumentBar'
        }
        kwargs['container'].py_name = 'bag'
        kwargs['container'].cli_type_name = 'list'
        kwargs.update(FLATTEN_CONFIG['command-name']['original-argument']
                                    ['flatten']['ArgumentBar'])
        arg = FlattenedArgument(**kwargs)

        self.assertEqual('bar', arg.name)
        self.assertEqual('Some help text', arg.documentation)
        self.assertEqual(True, arg.required)

        params = {}
        arg.add_to_params(params, 'value')
        self.assertEqual('VALUE', params['bag'][0]['ArgumentBar'])

    def test_hydrate_function_argument(self):
        container = mock.Mock()
        container.argument_model.name = 'bag'
        kwargs = {
            'container': container,
            'prop': 'ArgumentBaz:SomeValue'
        }
        kwargs['container'].py_name = 'bag'
        kwargs.update(FLATTEN_CONFIG['command-name']
                                    ['another-original-argument']
                                    ['flatten']['ArgumentBaz.SomeValue'])
        arg = FlattenedArgument(**kwargs)

        self.assertEqual('baz', arg.name)
        self.assertEqual('', arg.documentation)
        self.assertEqual(False, arg.required)

        params = {}
        arg.add_to_params(params, 1020)
        self.assertEqual(10.2, params['bag']['ArgumentBaz']['SomeValueAbc'])


class TestFlattenCommands(unittest.TestCase):
    def test_flatten_register(self):
        cli = mock.Mock()

        flatten = FlattenArguments('my-service', FLATTEN_CONFIG)
        flatten.register(cli)

        cli.register.assert_called_with(\
            'building-argument-table.my-service.command-name',
            flatten.flatten_args)

    def test_flatten_modify_args(self):
        # Mock operation, arguments, and members for a service
        command = mock.Mock()
        command.name = 'command-name'

        argument_model1 = mock.Mock()
        argument_model1.required_members = []

        member_foo = mock.Mock()
        member_foo.name = 'ArgumentFoo'
        member_foo.documentation = 'Original docs'
        member_foo.required_members = []

        member_bar = mock.Mock()
        member_bar.name = 'ArgumentBar'
        member_bar.documentation = 'More docs'
        member_bar.required_members = []

        argument_model1.members = {
            'ArgumentFoo': member_foo,
            'ArgumentBar': member_bar
        }

        argument_model2 = mock.Mock()
        argument_model2.required_members = []

        member_baz = mock.Mock()
        member_baz.name = 'ArgumentBaz'
        member_baz.documentation = ''
        member_baz.required_members = []

        member_some_value = mock.Mock()
        member_some_value.name = 'SomeValue'
        member_some_value.documenation = ''
        member_some_value.required_members = []

        member_baz.members = {
            'SomeValue': member_some_value
        }

        argument_model2.members = {
            'ArgumentBaz': member_baz
        }

        cli_argument1 = mock.Mock(spec=CLIArgument)
        cli_argument1.argument_model = argument_model1

        cli_argument2 = mock.Mock(spec=CLIArgument)
        cli_argument2.argument_model = argument_model2

        argument_table = {
            'original-argument': cli_argument1,
            'another-original-argument': cli_argument2
        }

        # Create the flattened argument table
        cli = mock.Mock()
        flatten = FlattenArguments('my-service', FLATTEN_CONFIG)
        flatten.flatten_args(command, argument_table)

        # Make sure new arguments and any with keep=True are there
        self.assertIn('foo', argument_table)
        self.assertIn('bar', argument_table)
        self.assertNotIn('original-argument', argument_table)
        self.assertIn('baz', argument_table)
        self.assertIn('another-original-argument', argument_table)

        # Make sure the new arguments are the class we expect
        self.assertIsInstance(argument_table['foo'], FlattenedArgument)
        self.assertIsInstance(argument_table['bar'], FlattenedArgument)
        self.assertIsInstance(argument_table['baz'], FlattenedArgument)
        self.assertNotIsInstance(argument_table['another-original-argument'],
                                 FlattenedArgument)

        # Make sure original required trait can be overridden
        self.assertEqual(False, argument_table['foo'].required)
        self.assertEqual(True, argument_table['bar'].required)

        # Make sure docs can be overriden and get the defaults
        self.assertEqual('Original docs', argument_table['foo'].documentation)
        self.assertEqual('Some help text', argument_table['bar'].documentation)
