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
import awscli.clidriver


class TestCreateInstance(BaseAWSCommandParamsTest):

    prefix = 'opsworks create-instance'

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --stack-id f623987f-6303-4bba-a38e-63073e85c726'
        cmdline += ' --layer-ids cb27894d-35f3-4435-b422-6641a785fa4a'
        cmdline += ' --instance-type c1.medium'
        cmdline += ' --hostname aws-client-instance'
        result = {'StackId': 'f623987f-6303-4bba-a38e-63073e85c726',
                  'Hostname': 'aws-client-instance',
                  'LayerIds': ['cb27894d-35f3-4435-b422-6641a785fa4a'],
                  'InstanceType': 'c1.medium'}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
