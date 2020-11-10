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
import nose
from collections import namedtuple

from awscli.clidriver import create_clidriver
from awscli.autoprompt import core
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import unittest


class TestCLIAutoPrompt(unittest.TestCase):
    def setUp(self):
        self.driver = mock.Mock()
        self.prompter = mock.Mock(spec=core.AutoPrompter)
        self.prompt_driver = core.AutoPromptDriver(self.driver,
                                                   prompter=self.prompter)

    def test_throw_error_if_both_args_specified(self):
        args = ['--cli-auto-prompt', '--no-cli-auto-prompt']
        self.assertRaises(
            ParamValidationError,
            self.prompt_driver.validate_auto_prompt_args_are_mutually_exclusive,
            args
        )


def test_auto_prompt_resolve_mode():
    # Each case is a 5-namedtuple with the following meaning:
    # "args" is a list of arguments that command got as input from
    #   command line
    # "config_variable" is the result from get_config_variable
    #   This takes a value of either 'on' , 'off' or 'on-partial'
    # "expected_result" is a boolean indicating whether auto-prompt
    #   should be used or not.
    #
    # Note: This set of tests assumes that only one of --no-cli-auto-prompt
    # or --cli-auto-prompt overrides can be specified.
    # TestCLIAutoPrompt.test_throw_error_if_both_args_specified tests
    # that these command line overrides are mutually exclusive.
    Case = namedtuple('Case', [
        'args',
        'config_variable',
        'expected_result',
    ])
    cases = [
        Case([], 'off', 'off'),
        Case([], 'on', 'on'),
        Case(['--cli-auto-prompt'], 'off', 'on'),
        Case(['--cli-auto-prompt'], 'on', 'on'),
        Case(['--no-cli-auto-prompt'], 'off', 'off'),
        Case(['--no-cli-auto-prompt'], 'on', 'off'),
        Case([], 'on', 'on'),
        Case([], 'on-partial', 'on-partial'),
        Case(['--cli-auto-prompt'], 'on-partial', 'on'),
        Case(['--no-cli-auto-prompt'], 'on-partial', 'off'),
        Case(['--version'], 'on', 'off'),
        Case(['help'], 'on', 'off'),
    ]
    for case in cases:
        yield (_assert_auto_prompt_runs_as_expected, case)


def _assert_auto_prompt_runs_as_expected(case):
    driver = create_clidriver()
    driver.session.set_config_variable('cli_auto_prompt',
                                       case.config_variable)
    prompter = mock.Mock(spec=core.AutoPrompter)
    prompt_driver = core.AutoPromptDriver(driver, prompter=prompter)
    result = prompt_driver.resolve_mode(args=case.args)
    nose.tools.eq_(result, case.expected_result)


def test_auto_prompt_resolve_mode_on_non_existing_profile():
    driver = create_clidriver()
    driver.session.set_config_variable('profile', 'not_exist')
    prompter = mock.Mock(spec=core.AutoPrompter)
    prompt_driver = core.AutoPromptDriver(driver, prompter=prompter)
    result = prompt_driver.resolve_mode(args=[])
    nose.tools.eq_(result, 'off')


class TestAutoPrompter(unittest.TestCase):
    def setUp(self):
        completion_source = mock.Mock()
        driver = mock.Mock()
        prompter = mock.Mock()
        prompter.prompt_for_args = lambda x: x
        driver.arg_table = []
        self.auto_prompter = core.AutoPrompter(
            completion_source, driver, prompter)

    def test_auto_prompter_returns_args(self):
        original_args = ['aws', 'ec2', 'help']
        prompted_values = self.auto_prompter.prompt_for_values(original_args)
        self.assertEqual(prompted_values, original_args)
