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


class TestModifyInstanceAttribute(BaseAWSCommandParamsTest):

    prefix = 'ec2 modify-instance-attribute '

    def setUp(self):
        super(TestModifyInstanceAttribute, self).setUp()
        self.expected_result = {
            'InstanceId': 'i-1234',
            'InstanceInitiatedShutdownBehavior': {'Value': 'terminate'}
        }

    def test_json_version(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--instance-initiated-shutdown-behavior {"Value":"terminate"}'
        self.assert_params_for_cmd(cmdline, self.expected_result)

    def test_shorthand_version(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--instance-initiated-shutdown-behavior Value=terminate'
        self.assert_params_for_cmd(cmdline, self.expected_result)

    def test_value_not_needed(self):
        # For structs of a single param value, you can skip the keep name,
        # so instead of Value=terminate, you can just say terminate.
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--instance-initiated-shutdown-behavior terminate'
        self.assert_params_for_cmd(cmdline, self.expected_result)

    def test_boolean_value_in_top_level_true(self):
        # Just like everything else in argparse, the last value provided
        # for a destination has precedence.
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--ebs-optimized Value=true'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': True}}
        self.assert_params_for_cmd(cmdline, result)

    def test_boolean_value_is_top_level_false(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--ebs-optimized Value=false'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': False}}
        self.assert_params_for_cmd(cmdline, result)

    def test_boolean_value_in_top_level_true_json(self):
        # Just like everything else in argparse, the last value provided
        # for a destination has precedence.
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--ebs-optimized {"Value":true}'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': True}}
        self.assert_params_for_cmd(cmdline, result)

    def test_boolean_value_is_top_level_false_json(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--ebs-optimized {"Value":false}'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': False}}
        self.assert_params_for_cmd(cmdline, result)

    def test_boolean_param_top_level_true_no_value(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--ebs-optimized'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': True}}
        self.assert_params_for_cmd(cmdline, result)

    def test_boolean_param_top_level_false_no_value(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--no-ebs-optimized'
        result = {'InstanceId': 'i-1234',
                  'EbsOptimized': {'Value': False}}
        self.assert_params_for_cmd(cmdline, result)

    def test_mix_value_non_value_boolean_param(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        # Can't mix non-value + value version of the arg.
        cmdline += '--no-ebs-optimized '
        cmdline += '--ebs-optimized Value=true'
        self.assert_params_for_cmd(cmdline, expected_rc=252,
                                    stderr_contains='Cannot specify both')

    def test_mix_non_value_bools_not_allowed(self):
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        # Can't mix non-value + value version of the arg.
        cmdline += '--no-ebs-optimized '
        cmdline += '--ebs-optimized '
        self.assert_params_for_cmd(cmdline, expected_rc=252,
                                    stderr_contains='Cannot specify both')


if __name__ == "__main__":
    unittest.main()
