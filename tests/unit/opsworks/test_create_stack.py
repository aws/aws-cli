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
import os
import awscli.clidriver


class TestCreateStack(BaseAWSCommandParamsTest):

    prefix = 'opsworks create-stack'

    def test_attributes_file(self):
        cmdline = self.prefix
        cmdline += ' --service-role-arn arn-blahblahblah'
        cmdline += ' --name FooStack'
        cmdline += ' --stack-region us-west-2'
        cmdline += ' --default-instance-profile-arn arn-foofoofoo'
        result = {'ServiceRoleArn': 'arn-blahblahblah',
                  'Name': 'FooStack',
                  'Region': 'us-west-2',
                  'DefaultInstanceProfileArn': 'arn-foofoofoo'
                  }
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
