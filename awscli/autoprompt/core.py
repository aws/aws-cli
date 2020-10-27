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
from botocore.exceptions import ProfileNotFound

from awscli.customizations.exceptions import ParamValidationError
from awscli.autoprompt.prompttoolkit import PromptToolkitPrompter
from awscli.autocomplete.main import create_autocompleter
from awscli.autocomplete.filters import fuzzy_filter
from awscli.errorhandler import SilenceParamValidationMsgErrorHandler


class AutoPromptDriver:

    _NO_PROMPT_ARGS = ['help', '--version']
    _CLI_AUTO_PROMPT_OPTION = '--cli-auto-prompt'
    _NO_CLI_AUTO_PROMPT_OPTION = '--no-cli-auto-prompt'

    def __init__(self, driver, completion_source=None, prompter=None):
        self._completion_source = completion_source
        self._prompter = prompter
        self._session = driver.session
        self._driver = driver
        if self._completion_source is None:
            self._completion_source = create_autocompleter(
                driver=self._driver, response_filter=fuzzy_filter)

    @property
    def prompter(self):
        if self._prompter is None:
            self._prompter = AutoPrompter(self._completion_source,
                                          self._driver)
        return self._prompter

    def validate_auto_prompt_args_are_mutually_exclusive(self, args):
        no_cli_auto_prompt = self._NO_CLI_AUTO_PROMPT_OPTION in args
        cli_auto_prompt = self._CLI_AUTO_PROMPT_OPTION in args
        if cli_auto_prompt and no_cli_auto_prompt:
            raise ParamValidationError(
                'Both --cli-auto-prompt and --no-cli-auto-prompt cannot be '
                'specified at the same time.'
            )

    def resolve_mode(self, args):
        # Order of precedence to check:
        # - check if any arg rom NO_PROMPT_ARGS in args
        # - check if '--no-cli-auto-prompt' was specified
        # - check if '--cli-auto-prompt' was specified
        # - check configuration chain
        self.validate_auto_prompt_args_are_mutually_exclusive(args)
        if any(arg in args for arg in self._NO_PROMPT_ARGS):
            return 'off'
        if self._NO_CLI_AUTO_PROMPT_OPTION in args:
            return 'off'
        if self._CLI_AUTO_PROMPT_OPTION in args:
            return 'on'
        try:
            config = self._session.get_config_variable('cli_auto_prompt')
            return config.lower()
        except ProfileNotFound:
            return 'off'

    def inject_silence_param_error_msg_handler(self, driver):
        driver.error_handler.inject_handler(
            0, SilenceParamValidationMsgErrorHandler()
        )

    def prompt_for_args(self, args):
        return self.prompter.prompt_for_values(args)


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
