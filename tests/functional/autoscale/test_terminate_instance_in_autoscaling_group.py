#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestTerminateInstanceInAutoscalingGroup(BaseAWSCommandParamsTest):

    PREFIX = 'autoscaling terminate-instance-in-auto-scaling-group'

    def test_true(self):
        cmdline = self.PREFIX
        cmdline += ' --instance-id i-12345678'
        cmdline += ' --should-decrement-desired-capacity'
        params = {'InstanceId': 'i-12345678',
                  'ShouldDecrementDesiredCapacity': True}
        self.assert_params_for_cmd(cmdline, params)

    def test_false(self):
        cmdline = self.PREFIX
        cmdline += ' --instance-id i-12345678'
        cmdline += ' --no-should-decrement-desired-capacity'
        params = {'InstanceId': 'i-12345678',
                  'ShouldDecrementDesiredCapacity': False}
        self.assert_params_for_cmd(cmdline, params)

    def test_last_arg_wins(self):
        cmdline = self.PREFIX
        cmdline += ' --instance-id i-12345678'
        cmdline += ' --should-decrement-desired-capacity'
        cmdline += ' --no-should-decrement-desired-capacity'
        # Since the --no-should-decrement-desired-capacity was
        # was added last, it wins.
        params = {'InstanceId': 'i-12345678',
                  'ShouldDecrementDesiredCapacity': False}
        self.assert_params_for_cmd(cmdline, params)
