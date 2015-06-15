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


class TestUpdateConfigurationTemplate(BaseAWSCommandParamsTest):

    prefix = 'elasticbeanstalk update-configuration-template'

    def test_file(self):
        data_path = os.path.join(os.path.dirname(__file__),
                                 'new_keypair_config.json')
        cmdline = self.prefix
        cmdline += ' --application-name FooBar'
        cmdline += ' --template-name x86_64_m1_medium_config'
        cmdline += ' --option-settings file://%s' % data_path
        cmdline += ' --description This_is_a_test'
        result = {
            'ApplicationName': 'FooBar',
            'TemplateName': 'x86_64_m1_medium_config',
            'Description': 'This_is_a_test',
            'OptionSettings': [
                {'Namespace': 'aws:autoscaling:launchconfiguration',
                 'OptionName': 'EC2KeyName',
                 'Value': 'webapps'},
                {'Namespace': 'aws:elasticbeanstalk:container:tomcat:jvmoptions',
                 'OptionName': 'Xms',
                 'Value': '1256m'}]}
        self.assert_params_for_cmd(cmdline, result)
