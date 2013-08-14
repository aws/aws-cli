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
from tests.unit import BaseAWSCommandParamsTest


class TestModifyInstanceAttribute(BaseAWSCommandParamsTest):

    prefix = 'ec2 modify-image-attribute'

    def test_one(self):
        cmdline = self.prefix
        cmdline += ' --image-id ami-d00dbeef'
        cmdline += ' --operation-type add'
        cmdline += ' --user-ids 0123456789012'
        result = {'ImageId': 'ami-d00dbeef',
                  'OperationType': 'add',
                  'UserId.1': '0123456789012'}
        self.assert_params_for_cmd(cmdline, result)

    def test_two(self):
        cmdline = self.prefix
        cmdline += ' --image-id ami-d00dbeef'
        cmdline += (' --launch-permission {"Add":[{"UserId":"123456789012"}],'
                    '"Remove":[{"Group":"all"}]}')
        result = {'ImageId': 'ami-d00dbeef',
                  'LaunchPermission.Add.1.UserId': '123456789012',
                  'LaunchPermission.Remove.1.Group': 'all',
                  }
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
