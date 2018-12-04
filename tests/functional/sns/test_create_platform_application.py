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


class TestCreatePlatformApplication(BaseAWSCommandParamsTest):

    prefix = 'sns create-platform-application'

    def test_gcm_shorthand(self):
        cmdline = self.prefix
        cmdline += ' --name gcmpushapp'
        cmdline += ' --platform GCM'
        cmdline += ' --attributes '
        cmdline += 'PlatformCredential=foo,'
        cmdline += 'PlatformPrincipal=bar'
        result = {'Name': 'gcmpushapp',
                  'Platform': 'GCM',
                  'Attributes': {'PlatformCredential': 'foo',
                                 'PlatformPrincipal': 'bar'}}
        self.assert_params_for_cmd(cmdline, result)

    def test_gcm_json(self):
        cmdline = self.prefix
        cmdline += ' --name gcmpushapp'
        cmdline += ' --platform GCM'
        cmdline += ' --attributes '
        cmdline += ('{"PlatformCredential":"AIzaSyClE2lcV2zEKTLYYo645zfk2jhQPFeyxDo",'
                    '"PlatformPrincipal":"There+is+no+principal+for+GCM"}')
        result = {
            'Name': 'gcmpushapp',
            'Platform': 'GCM',
            'Attributes': {
              'PlatformCredential': 'AIzaSyClE2lcV2zEKTLYYo645zfk2jhQPFeyxDo',
              'PlatformPrincipal': 'There+is+no+principal+for+GCM'}
        }
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
