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
import prompt_toolkit
from prompt_toolkit.completion import WordCompleter

from awscli.customizations.arguments import OverrideRequiredArgsArgument
from awscli.customizations.utils import get_shape_doc_overview
from awscli.customizations.wizard import selectmenu


def register_autoprompt(cli):
    cli.register('building-argument-table', add_auto_prompt)


def add_auto_prompt(session, argument_table, **kwargs):
    # This argument cannot support operations with streaming output which
    # is designated by the argument name `outfile`.
    if 'outfile' not in argument_table:
        prompter = AutoPrompter()
        auto_prompt_argument = AutoPromptArgument(session, prompter)
        auto_prompt_argument.add_to_arg_table(argument_table)


class AutoPromptArgument(OverrideRequiredArgsArgument):
    """This argument is a boolean to let you prompt for args.

    """
    ARG_DATA = {
        'name': 'cli-auto-prompt',
        'action': 'store_true',
        'help_text': 'Automatically prompt for CLI input parameters.'
    }

    def __init__(self, session, prompter):
        super(AutoPromptArgument, self).__init__(session)
        self._prompter = prompter
        self._arg_table = {}
        self._original_required_args = {}

    def _register_argument_action(self):
        self._session.register(
            'calling-command.*', self.auto_prompt_arguments)
        super(AutoPromptArgument, self)._register_argument_action()

    def override_required_args(self, argument_table, args, **kwargs):
        self._arg_table = argument_table
        self._original_required_args = {
            key: value for key, value in argument_table.items()
            if value.required
        }
        super(AutoPromptArgument, self).override_required_args(
            argument_table, args, **kwargs
        )

    def auto_prompt_arguments(self, call_parameters, parsed_args,
                              parsed_globals, event_name, **kwargs):

        # Check if ``--cli-auto-prompt`` was specified in the command line.
        auto_prompt = getattr(parsed_args, 'cli_auto_prompt', False)
        if auto_prompt:
            return self._prompter.prompt_for_values(
                complete_arg_table=self._arg_table,
                required_arg_table=self._original_required_args,
                apicall_parameters=call_parameters,
                command_name_parts=['aws'] + event_name.split('.')[1:],
            )


class AutoPrompter(object):
    """Handles the logic for prompting for a set of values.

    This class focuses on prompting for values that's separate from
    the integration of this functionality into the CLI
    (e.g. AutoPromptArgument).

    """
    QUIT_SENTINEL = object()
    # These are built-in args that we don't
    # want to prompt the user for.  If they're using
    # --cli-auto-prompt, it's unlikely they want to use any
    # of these args.  Ideally there's a more automatic way to
    # detect this (e.g. some sort of base class), but for now
    # we're maintaining an explicit list.  We hardly ever had
    # to these anyways.
    _BUILT_IN_ARGS_EXCLUDE = [
        'cli-input-json',
        'cli-input-yaml',
        'generate-cli-skeleton',
        'cli-auto-prompt',
    ]

    def __init__(self, prompter=None):
        if prompter is None:
            prompter = Prompter()
        self._prompter = prompter

    def prompt_for_values(self, complete_arg_table, required_arg_table,
                          apicall_parameters, command_name_parts):
        """Prompt for values for a given CLI command.

        :param complete_arg_table:  The arg table for the command
        :param required_arg_table: The subset of the arg table for
            required args.  The prompter ensutres that it prompts for
            all required args.
        :param apicall_parameters: The API call parameters to use for the
            given command.  The values the user enters during the prompting
            process will be added to this dictionary.
        :param command_name_parts: A list of strings of the command.
            This is used to reconstruct the final command if the user
            wants to print the command, e.g. ``['aws', 'iam', 'create-user']``.

        If the user requests that that the CLI command is printed, the
        full command will be returned as a string.  Otherwise ``None``
        is returned.

        """
        cli_command = command_name_parts[:]
        for name, value in required_arg_table.items():
            self._prompt_for_value(
                value, self._get_doc_from_arg(value),
                apicall_parameters, cli_command, {}
            )
        remaining_args = self._get_remaining_args(complete_arg_table,
                                                  required_arg_table)
        if remaining_args:
            while True:
                choices = list(remaining_args)
                choices = [
                    {'actual_value': key,
                     'display': self._get_doc_from_arg(value)}
                    for key, value in remaining_args.items()
                ]
                choices.append({'actual_value': self.QUIT_SENTINEL,
                                'display': '[DONE] Parameter input finished'})
                choice = self._prompter.select_from_choices(
                    choices, display_formatter=lambda x: x['display']
                )
                if choice['actual_value'] is self.QUIT_SENTINEL:
                    break
                arg = remaining_args[choice['actual_value']]
                self._prompt_for_value(
                    arg, choice['display'],
                    apicall_parameters, cli_command,
                    remaining_args
                )
        return self._decide_next_action(cli_command)

    def _decide_next_action(self, cli_command):
        choice = self._prompter.select_from_choices(
            [{'actual_value': 'run-command',
              'display': 'Run CLI command'},
             {'actual_value': 'print-only',
              'display': 'Display CLI command'}],
            display_formatter=lambda x: x['display']
        )['actual_value']
        if choice == 'print-only':
            print(' '.join(cli_command))
            return 0

    def _get_doc_from_arg(self, arg_shape):
        return '--%s [%s]: %s' % (arg_shape.name,
                                  arg_shape.cli_type_name,
                                  get_shape_doc_overview(arg_shape))

    def _get_remaining_args(self, complete_arg_table, required_arg_table):
        remaining_args = {
            key: value for key, value in complete_arg_table.items() if
            key not in required_arg_table and
            key not in self._BUILT_IN_ARGS_EXCLUDE
        }
        return remaining_args

    def _prompt_for_value(self, arg, prompt_display_text,
                          apicall_parameters, cli_command,
                          remaining_args):
        completer = self._try_get_completer(arg)
        while True:
            try:
                v = self._prompter.prompt(
                    "--%s: " % arg.name,
                    completer=completer,
                    bottom_toolbar=prompt_display_text)
                arg.add_to_params(apicall_parameters, v)
                cli_command.extend(['--%s' % arg.name, v])
                remaining_args.pop(arg.name, None)
                break
            except Exception as e:
                print("Error: %s" % e)
                print("Please re-enter this value.\n")

    def _try_get_completer(self, arg):
        # Autocomplete enums if they're modeled.
        model = getattr(arg, 'argument_model', None)
        if model is not None and getattr(model, 'enum', None) is not None:
            choices = model.enum
            completer = WordCompleter(choices)
            return completer


# Note the point of this class isn't really about abstracting away
# prompt toolkit.  It's mostly so there's a single class that groups all
# the prompting functionality together.
class Prompter(object):
    def __init__(self):
        pass

    def prompt(self, prompt_text, completer=None, bottom_toolbar=None):
        value = prompt_toolkit.prompt(
            prompt_text,
            completer=completer,
            bottom_toolbar=bottom_toolbar)
        return value

    def select_from_choices(self, choices, display_formatter=None):
        choice = selectmenu.select_menu(
            choices, display_format=display_formatter
        )
        return choice
