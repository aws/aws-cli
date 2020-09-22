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
import argparse
import mock
import nose
from collections import namedtuple

from awscli.clidriver import CLIDriver, create_clidriver
from awscli.constants import PARAM_VALIDATION_ERROR_RC, RERUN_RC, RUN_RC
from awscli.argprocess import ParamSyntaxError
from awscli.autoprompt.autoprompt_driver import PromptToolkitPrompter
from awscli.autoprompt import autoprompt_driver
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import unittest
from botocore.session import Session


class TestCLIAutoPrompt(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.prompter = mock.Mock(spec=autoprompt_driver.AutoPrompter)
        self.driver = create_clidriver()

    def create_args(self, cli_auto_prompt=False, no_cli_auto_prompt=False):
        args = argparse.Namespace()
        args.cli_auto_prompt = cli_auto_prompt
        args.no_cli_auto_prompt = no_cli_auto_prompt
        return args

    def test_throw_error_if_both_args_specified(self):
        args = self.create_args(cli_auto_prompt=True, no_cli_auto_prompt=True)
        self.assertRaises(
            ParamValidationError,
            autoprompt_driver.validate_auto_prompt_args_are_mutually_exclusive,
            args
        )


def test_auto_prompt_config():
    # Each case is a 5-namedtuple with the following meaning:
    # "no_cli_autoprompt" is the command line --no-cli-auto-prompt override:
    #   True means --no-cli-auto-prompt is specified.
    #   False means --no-cli-auto-prompt is not specified.
    # "cli_auto_prompt"is the command line --cli-auto-prompt override:
    #   True means --cli-auto-prompt is specified.
    #   False means --cli-auto-prompt is not specified.
    # "config_variable" is the result from get_config_variable
    #   This takes a value of either 'on' or 'off'.
    # "args" is a list of arguments that command got as input from
    #   command line
    # "expected_result" is a boolean indicating whether auto-prompt
    #   should be used or not.
    #
    # Note: This set of tests assumes that only one of --no-cli-auto-prompt
    # or --cli-auto-prompt overrides can be specified.
    # TestCLIAutoPrompt.test_throw_error_if_both_args_specified tests
    # that these command line overrides are mutually exclusive.
    Case = namedtuple('Case', [
        'no_cli_autoprompt',
        'cli_auto_prompt',
        'config_variable',
        'args',
        'clidriver_exception',
        'expected_result',
    ])
    cases = [
        Case(False, False, 'off', ['aws', 'ec2'], ParamSyntaxError, False),
        Case(False, False, 'on', ['aws', 'ec2'], ParamSyntaxError, True),
        Case(False, True, 'off', ['aws', 'ec2'], ParamSyntaxError, True),
        Case(False, True, 'on', ['aws', 'ec2'], ParamSyntaxError, True),
        Case(True, False, 'off', ['aws', 'ec2'], ParamSyntaxError, False),
        Case(True, False, 'on', ['aws', 'ec2'], ParamSyntaxError, False),
        Case(False, False, 'on', ['aws', 'ec2', 'help'], None, False),
        Case(False, False, 'on', ['aws', '--version'], None, False),
        Case(False, False, 'on-partial', ['aws', '--version'], None, False),
        Case(False, False, 'on-partial', ['aws', 'ec2'], ParamSyntaxError, True),
        Case(True, False, 'on-partial', ['aws', 'ec2'], ParamSyntaxError, False),
        Case(False, True, 'on-partial', ['aws', 'ec2', 'describe-instances'],
             None, True),
    ]
    for case in cases:
        yield (_assert_auto_prompt_runs_as_expected, case)


def _assert_auto_prompt_runs_as_expected(case):
    driver = mock.Mock(spec=CLIDriver)
    driver.main.return_value = 0
    if case.clidriver_exception is not None:
        driver.main.side_effect = case.clidriver_exception()
    driver.session = mock.Mock(spec=Session)
    driver.session.get_config_variable.return_value = case.config_variable
    prompter = mock.Mock(spec=autoprompt_driver.AutoPrompter)
    prompt_driver = autoprompt_driver.AutoPromptDriver(driver,
                                                       prompter=prompter)
    parsed_args = argparse.Namespace()
    parsed_args.no_cli_auto_prompt = case.no_cli_autoprompt
    parsed_args.cli_auto_prompt = case.cli_auto_prompt
    prompt_driver.auto_prompt_arguments(
        args=case.args,
        parsed_args=parsed_args,
    )
    nose.tools.eq_(prompter.prompt_for_values.called, case.expected_result)


def test_auto_prompt_return_correct_rc():
    Case = namedtuple('Case', [
        'no_cli_autoprompt',
        'cli_auto_prompt',
        'config_variable',
        'args',
        'clidriver_exception',
        'expected_rc',
    ])
    cases = [
        Case(False, False, 'off', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(False, False, 'on', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(False, True, 'off', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(False, True, 'on', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(True, False, 'off', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(True, False, 'on', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(False, False, 'on', ['aws', 'ec2', 'help'], None, RUN_RC),
        Case(False, False, 'on', ['aws', '--version'], None, RUN_RC),
        Case(False, False, 'on-partial', ['aws', '--version'], None, RUN_RC),
        Case(False, False, 'on-partial', ['aws', 'ec2'], ParamSyntaxError, RERUN_RC),
        Case(True, False, 'on-partial', ['aws', 'ec2'], ParamSyntaxError, RUN_RC),
        Case(False, False, 'on-partial', ['aws', 'ec2', 'describe-instances'],
             None, 0),
    ]
    for case in cases:
        yield (_assert_auto_prompt_return_rc_as_expected, case)


def _assert_auto_prompt_return_rc_as_expected(case):
    driver = mock.Mock(spec=CLIDriver)
    driver.session = mock.Mock(spec=Session)
    driver.main.return_value = 0
    driver.session.get_config_variable.return_value = case.config_variable
    if case.clidriver_exception is not None:
        driver.main.side_effect = case.clidriver_exception()
    prompter = mock.Mock(spec=autoprompt_driver.AutoPrompter)
    prompt_driver = autoprompt_driver.AutoPromptDriver(driver,
                                                       prompter=prompter)
    parsed_args = argparse.Namespace()
    parsed_args.no_cli_auto_prompt = case.no_cli_autoprompt
    parsed_args.cli_auto_prompt = case.cli_auto_prompt
    rc, _ = prompt_driver.auto_prompt_arguments(
        args=case.args,
        parsed_args=parsed_args,
    )
    nose.tools.eq_(rc, case.expected_rc)


class TestAutoPrompter(unittest.TestCase):
    def setUp(self):
        self.completion_source = mock.Mock()
        self.driver = mock.Mock(spec=CLIDriver)
        self.prompter = mock.Mock(spec=PromptToolkitPrompter)
        self.prompter.prompt_for_args = lambda x: x
        self.auto_prompter = autoprompt_driver.AutoPrompter(
            self.completion_source, self.driver, self.prompter)

    def test_auto_prompter_returns_args(self):
        original_args = ['aws', 'ec2', 'help']
        prompted_values = self.auto_prompter.prompt_for_values(original_args)
        self.assertEqual(prompted_values, original_args)
