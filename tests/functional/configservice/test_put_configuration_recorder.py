# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestPutConfigurationRecorder(BaseAWSCommandParamsTest):
    prefix = 'configservice put-configuration-recorder'

    def test_only_configuration_recorder(self):
        cmdline = self.prefix + ' --configuration-recorder'
        cmdline += ' name=myrecorder,roleARN=myarn'
        result = {
            'ConfigurationRecorder': {
                'name': 'myrecorder',
                'roleARN': 'myarn'
            }
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_no_configuration_recorder(self):
        stdout, stderr, rc = self.run_cmd(self.prefix, expected_rc=252)
        self.assertIn(
            'required',
            stderr
        )
        self.assertIn(
            '--configuration-recorder',
            stderr
        )

    def test_configuration_recorder_with_recording_group(self):
        cmdline = self.prefix + ' --configuration-recorder'
        cmdline += ' name=myrecorder,roleARN=myarn'
        cmdline += ' --recording-group'
        cmdline += ' allSupported=true,resourceTypes='
        cmdline += 'AWS::EC2::Volume,AWS::EC2::VPC'
        result = {
            'ConfigurationRecorder': {
                'name': 'myrecorder',
                'roleARN': 'myarn',
                'recordingGroup': {
                    'allSupported': True,
                    'resourceTypes': ['AWS::EC2::Volume', 'AWS::EC2::VPC']
                }
            }
        }
        self.assert_params_for_cmd(cmdline, result)
