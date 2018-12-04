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
import unittest
from awscli.testutils import BaseAWSCommandParamsTest
import os
import awscli.clidriver


class TestCreateLayer(BaseAWSCommandParamsTest):

    prefix = 'opsworks create-layer'

    def test_attributes_file(self):
        data_path = os.path.join(os.path.dirname(__file__),
                                 'create_layer_attributes.json')
        cmdline = self.prefix
        cmdline += ' --stack-id 35959772-cd1e-4082-8346-79096d4179f2'
        cmdline += ' --type rails-app'
        cmdline += ' --name Rails_App_Server'
        cmdline += ' --enable-auto-healing'
        cmdline += ' --attributes file://%s' % data_path
        cmdline += ' --shortname foo'
        result = {'StackId': '35959772-cd1e-4082-8346-79096d4179f2',
                  'Type': 'rails-app',
                  'Name': 'Rails_App_Server',
                  'EnableAutoHealing': True,
                  'Shortname': 'foo',
                  'Attributes': {"RubygemsVersion": "1.8.24",
                                 "RailsStack": "apache_passenger",
                                 "RubyVersion": "1.9.3",
                                 "BundlerVersion": "1.2.3",
                                 "PassengerVersion": "3.0.17",
                                 "ManageBundler": "true",
                                 }
                  }
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
