#!/usr/bin/env python
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestAddOptionGroup(BaseAWSCommandParamsTest):
    maxDiff = None
    # This tests the customization where modify-option-group
    # was split into two commands add-option-group and
    # remove-option-group.  This class is testing add-option-gruop

    prefix = 'rds add-option-to-option-group '

    def test_add_option(self):
        args = ('--option-group-name myoptiongroup2 '
                '--options {"OptionName":"TDE"}')
        cmdline = self.prefix + args
        result = {'OptionsToInclude': [{'OptionName': 'TDE'}],
                  'OptionGroupName': 'myoptiongroup2'}
        self.assert_params_for_cmd(cmdline, result)

    def test_option_to_remove_is_not_allowed(self):
        args = ('--option-group-name myoptiongroup2 '
                '--options-to-remove foo')
        cmdline = self.prefix + args
        self.assert_params_for_cmd(
            cmdline, expected_rc=255,
            stderr_contains='Unknown options: --options-to-remove')


class TestRemoveOptionGroup(BaseAWSCommandParamsTest):

    prefix = 'rds remove-option-from-option-group '

    def test_remove_options(self):
        args = ('--option-group-name myoptiongroup2 '
                '--options TDE')
        cmdline = self.prefix + args
        result = {'OptionsToRemove': ['TDE'],
                  'OptionGroupName': 'myoptiongroup2'}
        self.assert_params_for_cmd(cmdline, result)

    def test_option_to_add_is_not_allowed(self):
        args = ('--option-group-name myoptiongroup2 '
                '--options-to-include {"OptionName":"TDE"}')
        cmdline = self.prefix + args
        self.assert_params_for_cmd(
            cmdline, expected_rc=255,
            stderr_contains='Unknown options: --options-to-include')
