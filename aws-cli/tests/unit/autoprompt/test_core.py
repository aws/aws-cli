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
from collections import namedtuple

import pytest

from awscli.autoprompt import core
from awscli.clidriver import create_clidriver
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import mock, unittest


class TestCLIAutoPrompt(unittest.TestCase):
    def setUp(self):
        self.driver = mock.Mock()
        self.prompter = mock.Mock(spec=core.AutoPrompter)
        self.prompt_driver = core.AutoPromptDriver(
            self.driver, prompter=self.prompter
        )


class TestAutoPrompter(unittest.TestCase):
    def setUp(self):
        completion_source = mock.Mock()
        driver = mock.Mock()
        prompter = mock.Mock()
        prompter.prompt_for_args = lambda x: x
        driver.arg_table = []
        self.auto_prompter = core.AutoPrompter(
            completion_source, driver, prompter
        )

    def test_auto_prompter_returns_args(self):
        original_args = ['aws', 'ec2', 'help']
        prompted_values = self.auto_prompter.prompt_for_values(original_args)
        self.assertEqual(prompted_values, original_args)
