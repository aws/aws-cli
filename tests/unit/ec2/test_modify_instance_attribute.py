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
from tests.unit import BaseAWSCommandParamsTest


class TestModifyInstanceAttribute(BaseAWSCommandParamsTest):

    prefix = 'ec2 modify-instance-attribute '

    def setUp(self):
        super(TestModifyInstanceAttribute, self).setUp()
        self.expected_result = {
            'InstanceId': 'i-1234',
            'InstanceInitiatedShutdownBehavior.Value': 'terminate',
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
        result = {'InstanceId': 'i-1234',
                  'InstanceInitiatedShutdownBehavior.Value': 'terminate',
                  }
        self.assert_params_for_cmd(cmdline, self.expected_result)

    def test_value_not_needed(self):
        # For structs of a single param value, you can skip the keep name,
        # so instead of Value=terminate, you can just say terminate.
        cmdline = self.prefix
        cmdline += '--instance-id i-1234 '
        cmdline += '--instance-initiated-shutdown-behavior terminate'
        result = {'InstanceId': 'i-1234',
                  'InstanceInitiatedShutdownBehavior.Value': 'terminate',
                  }
        self.assert_params_for_cmd(cmdline, self.expected_result)


if __name__ == "__main__":
    unittest.main()
