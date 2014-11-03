# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest
from awscli.customizations.arguments import OverrideRequiredArgsArgument


class TestOverrideRequiredArgsArgument(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.argument = OverrideRequiredArgsArgument(self.session)

        # Set up a sample argument_table
        self.argument_table = {}
        self.mock_arg = mock.Mock()
        self.mock_arg.required = True
        self.argument_table['mock-arg'] = self.mock_arg

    def test_register_argument_action(self):
        register_args = self.session.register.call_args
        self.assertEqual(register_args[0][0],
                         'before-building-argument-table-parser')
        self.assertEqual(register_args[0][1],
                         self.argument.override_required_args)

    def test_override_required_args_if_in_cmdline(self):
        args = ['--no-required-args']
        self.argument.override_required_args(self.argument_table, args)
        self.assertFalse(self.mock_arg.required)

    def test_no_override_required_args_if_not_in_cmdline(self):
        args = []
        self.argument.override_required_args(self.argument_table, args)
        self.assertTrue(self.mock_arg.required)
