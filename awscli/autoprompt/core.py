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
from awscli.autocomplete.filters import fuzzy_filter
from awscli.autocomplete.main import create_autocompleter
from awscli.autoprompt.prompttoolkit import PromptToolkitPrompter
from awscli.errorhandler import SilenceParamValidationMsgErrorHandler


class AutoPromptDriver:
    def __init__(self, driver, completion_source=None, prompter=None):
        self._completion_source = completion_source
        self._prompter = prompter
        self._session = driver.session
        self._driver = driver
        if self._completion_source is None:
            self._completion_source = create_autocompleter(
                driver=self._driver, response_filter=fuzzy_filter
            )

    @property
    def prompter(self):
        if self._prompter is None:
            self._prompter = AutoPrompter(
                self._completion_source, self._driver
            )
        return self._prompter

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
            prompter = PromptToolkitPrompter(
                self._completion_source, self._driver
            )
        self._prompter = prompter

    def prompt_for_values(self, original_args):
        return self._prompter.prompt_for_args(original_args)
