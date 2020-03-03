# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
from collections import OrderedDict

from botocore import model

from awscli.testutils import unittest
from awscli.customizations import autoprompt


class TestCLIAutoPrompt(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.prompter = mock.Mock(spec=autoprompt.AutoPrompter)
        self.argument = autoprompt.AutoPromptArgument(self.session,
                                                      self.prompter)

    def tearDown(self):
        pass

    def create_args(self, cli_auto_prompt=True):
        parsed_args = mock.Mock()
        parsed_args.cli_auto_prompt = cli_auto_prompt
        return parsed_args

    def test_add_arg_if_outfile_not_in_argtable(self):
        arg_table = {}
        autoprompt.add_auto_prompt(self.session, arg_table)
        self.assertIn('cli-auto-prompt', arg_table)
        self.assertIsInstance(arg_table['cli-auto-prompt'],
                              autoprompt.AutoPromptArgument)

    def test_register_argument_action(self):
        self.session.register.assert_any_call(
            'calling-command.*', self.argument.auto_prompt_arguments
        )

    def test_auto_prompter_not_called_if_arg_not_provided(self):
        args = self.create_args(cli_auto_prompt=False)
        self.argument.auto_prompt_arguments(
            call_parameters={},
            parsed_args=args,
            parsed_globals=None,
            event_name='calling-command.iam.create-user'
        )
        self.assertFalse(self.prompter.prompt_for_values.called)

    def test_add_to_call_parameters_no_file(self):
        parsed_args = self.create_args(cli_auto_prompt=True)
        self.argument.auto_prompt_arguments(
            call_parameters={},
            parsed_args=parsed_args,
            parsed_globals=None,
            event_name='calling-command.iam.create-user'
        )
        self.assertTrue(self.prompter.prompt_for_values.called)


class FakeArg(object):
    def __init__(self, name, cli_type_name='string', arg_model=None):
        self.name = name
        self.cli_type_name = cli_type_name
        self.argument_model = arg_model

    @property
    def documentation(self):
        return 'Documentation for %s' % self.name

    def add_to_params(self, call_parameters, value):
        # Our fake instance don't need to map to api call params,
        # so we just use the arg name as they into the api call params.
        call_parameters[self.name] = value


class TestAutoPrompter(unittest.TestCase):
    def setUp(self):
        self.prompter = mock.Mock(spec=autoprompt.Prompter)
        self.auto_prompter = autoprompt.AutoPrompter(prompter=self.prompter)
        self.complete_arg_table = OrderedDict({})
        self.required_arg_table = OrderedDict({})
        self.apicall_parameters = {}
        self.command_name_parts = []
        self.prompter.select_from_choices.return_value = {
            'actual_value': 'print-only',
            'display': 'Display CLI command'
        }

    def prompt_for_values(self):
        return self.auto_prompter.prompt_for_values(
            self.complete_arg_table,
            self.required_arg_table,
            self.apicall_parameters,
            self.command_name_parts
        )

    def add_required_arg(self, arg):
        self.required_arg_table[arg.name] = arg
        self.complete_arg_table[arg.name] = arg

    def add_optional_arg(self, arg):
        self.complete_arg_table[arg.name] = arg

    def test_always_prompts_all_required_args(self):
        self.add_required_arg(FakeArg('my-arg-1'))
        self.add_required_arg(FakeArg('my-arg-2'))
        self.prompter.prompt.side_effect = ['my-value-1', 'my-value-2']
        result = self.prompt_for_values()
        self.assertEqual(result, 0)
        # The prompter should have said the appropriate apicall_parameters
        # based on the return values from the prompt.
        self.assertEqual(self.apicall_parameters, {'my-arg-1': 'my-value-1',
                                                   'my-arg-2': 'my-value-2'})

    def test_can_prompt_optional_args(self):
        # We have two optional args we'll ask the user about.
        self.add_optional_arg(FakeArg('optional-1'))
        self.add_optional_arg(FakeArg('optional-2'))
        # The user will select the first arg.
        self.prompter.select_from_choices.side_effect = [
            # User selects they want to input optional-1
            {'actual_value': 'optional-1', 'display': 'Option 1'},
            # User selects they want to input optional-1
            {'actual_value': 'optional-2', 'display': 'Option 2'},
            # User selects they're done entering params.
            {'actual_value': self.auto_prompter.QUIT_SENTINEL, 'display': ''},
            # User selects they want to print the params.
            {'actual_value': 'print-only', 'display': 'Display CLI command'}
        ]
        self.prompter.prompt.side_effect = ['my-value-1', 'my-value-2']
        self.prompt_for_values()
        self.assertEqual(self.apicall_parameters,
                         {'optional-1': 'my-value-1',
                          'optional-2': 'my-value-2'})

    def test_loops_until_no_exception_on_error(self):
        self.add_required_arg(FakeArg('my-arg-1'))
        self.prompter.prompt.side_effect = [
            # User enters a bad value, so we'll reprompt.
            ValueError("Bad value"),
            # User enters a good value.
            'my-value-1',
        ]
        self.prompt_for_values()
        # The good value should make it to the api call params.
        self.assertEqual(self.apicall_parameters, {'my-arg-1': 'my-value-1'})

    def test_model_with_enum_offers_completer(self):
        arg = FakeArg('my-arg-1')
        arg.argument_model = model.StringShape(
            'MyArg1',
            {'type': 'string', 'enum': ['choice1', 'choice2']}
        )
        self.add_required_arg(arg)
        self.prompter.prompt.return_value = 'my-value-1'
        self.prompt_for_values()
        self.assertEqual(self.apicall_parameters, {'my-arg-1': 'my-value-1'})
        # Because the shape has an enum, we should have used that for the
        # word completer in the prompt.
        completer_arg = self.prompter.prompt.call_args[1].get('completer')
        self.assertIsNotNone(completer_arg)
        self.assertEqual(completer_arg.words, ['choice1', 'choice2'])
