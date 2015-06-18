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


class TestDescribeInstances(BaseAWSCommandParamsTest):

    prefix = 'ec2 create-image'

    def test_renamed_reboot_arg(self):
        cmdline = self.prefix
        cmdline += ' --instance-id i-12345678 --description foo --name bar'
        # --reboot is a customized renamed arg.  Verifying it still
        # gets mapped as 'NoReboot': 'false'.
        cmdline += ' --reboot'
        result = {'InstanceId': 'i-12345678', 'Description': 'foo',
                  'Name': 'bar', 'NoReboot': False}
        self.assert_params_for_cmd(cmdline, result)
