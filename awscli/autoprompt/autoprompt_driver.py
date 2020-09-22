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
import contextlib
import io
import signal
import sys

from botocore.exceptions import (
    ParamValidationError as BotocoreParamValidationError
)

from awscli import constants
from awscli.argparser import ArgTableArgParser, ArgParseException
from awscli.arguments import UnknownArgumentError
from awscli.autocomplete.main import create_autocompleter
from awscli.customizations.exceptions import ParamValidationError
from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.autoprompt.prompttoolkit import PromptToolkitPrompter


PARAM_VALIDATION_ERRORS = (
    ParamError, ParamSyntaxError, UnknownArgumentError, ArgParseException,
    ParamValidationError, BotocoreParamValidationError,
)


def validate_auto_prompt_args_are_mutually_exclusive(parsed_args, **kwargs):
    cli_auto_prompt = getattr(parsed_args, 'cli_auto_prompt', False)
    no_cli_auto_prompt = getattr(parsed_args, 'no_cli_auto_prompt', False)
    if cli_auto_prompt and no_cli_auto_prompt:
        raise ParamValidationError(
            'Both --cli-auto-prompt and --no-cli-auto-prompt cannot be '
            'specified at the same time.'
        )


class AutoPromptDriver:
    NO_PROMPT_ARGS = ['help', '--version']

    def __init__(self, driver, completion_source=None, prompter=None):
        self._completion_source = completion_source
        self._prompter = prompter
        self._session = driver.session
        self._driver = driver
        if self._completion_source is None:
            self._completion_source = create_autocompleter(driver=self._driver)

    @property
    def prompter(self):
        if self._prompter is None:
            self._prompter = AutoPrompter(self._completion_source,
                                          self._driver)
        return self._prompter

    def prompt_for_args(self, args=None):
        if args is None:
            args = sys.argv[1:]

        option_parser = ArgTableArgParser(self._driver.arg_table)
        filtered_args = self._filter_out_options(args)
        parsed_options, _ = option_parser.parse_known_args(filtered_args)
        validate_auto_prompt_args_are_mutually_exclusive(parsed_options)
        return self.auto_prompt_arguments(args, parsed_options)

    def _filter_out_options(self, args):
        override_options = ['--cli-auto-prompt', '--no-cli-auto-prompt']
        return [
                arg for arg in args
                if (not arg.startswith('--') or arg in override_options)
            ]

    def _try_command(self, args):
        """Try to run command with these args and store rc, exception and
        stderr output.
        In case if:
        -- "prompt_on_error" == False and there was an error - print out
            error messages back to stderr and raise an exception of there was
            amu; if there was no error just return the rc
        -- "prompt_on_error" == True and there was a validation error - swallow
            exception and stderr output and run prompt mode; if there was no
            error just return the rc
        """
        try:
            rc = self._driver.main(args)
        except PARAM_VALIDATION_ERRORS:
            return constants.RERUN_RC
        return rc

    def _get_autoprompt_mode(self, parsed_args, args):
        # Order of precedence to check:
        # - check if any arg rom NO_PROMPT_ARGS in args
        # - check if '--no-cli-auto-prompt' was specified
        # - check if '--cli-auto-prompt' was specified
        # - check configuration chain
        if any(arg in args for arg in self.NO_PROMPT_ARGS):
            return 'off'
        if getattr(parsed_args, 'no_cli_auto_prompt', False):
            return 'off'
        if getattr(parsed_args, 'cli_auto_prompt', False):
            return 'on'
        config = self._session.get_config_variable('cli_auto_prompt')
        return config.lower()

    def auto_prompt_arguments(self, args, parsed_args):
        """Prompts the user for input while providing autoprompt support along
        the way.

        :type args: list
        :param args: The list of command line args entered at the command line
            just before entering into the autoprompt workflow.

        :type parsed_args: ``argparse.Namespace``
        :param parsed_args: The parsed options at the `aws` entrypoint. This is
            primarily used to check if the autoprompt override arguments
            ``--cli-auto-prompt`` or ``--no-cli-auto-prompt`` were specified.

        :rtype: list of strings
        :return: A list of the arguments that the user typed into the buffer
            (aka "construction zone").
            Example: ['ec2', 'describe-instances']

        """
        autoprompt_mode = self._get_autoprompt_mode(parsed_args, args)
        rc = constants.RUN_RC
        if autoprompt_mode == 'on':
            args = self.prompter.prompt_for_values(args)
        elif autoprompt_mode == 'on-partial':
            rc = self._try_command(args)
            if rc == constants.RERUN_RC:
                args = self.prompter.prompt_for_values(args)
        return rc, args


class AutoPrompter:
    """Fills out the arguments list by calling out to the UI prompt backend to
    do the actual prompting of arguments. This makes it easy to swap out
    the UI prompt backend easily if needed.

    """
    def __init__(self, completion_source, driver, prompter=None):
        self._completion_source = completion_source
        self._driver = driver
        if prompter is None:
            prompter = PromptToolkitPrompter(self._completion_source,
                                             self._driver)
        self._prompter = prompter

    def prompt_for_values(self, original_args):
        return self._prompter.prompt_for_args(original_args)
