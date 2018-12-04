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


class TestAttachInternetGateway(BaseAWSCommandParamsTest):

    prefix = 'ec2 attach-internet-gateway'

    def test_both_params(self):
        cmdline = self.prefix
        cmdline += ' --vpc-id vpc-12345678'
        cmdline += ' --internet-gateway-id igw-12345678'
        result = {'VpcId': 'vpc-12345678',
                  'InternetGatewayId': 'igw-12345678'}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
