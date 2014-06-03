# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


class TestAddTags(BaseAWSCommandParamsTest):
    prefix = 'emr add-tags'

    def test_add_tags_key_value(self):
        args = ' --resource-id j-ABC123456 --tags k1=v1 k2=v2'
        cmdline = self.prefix + args
        result = {'ResourceId': 'j-ABC123456',
                  'Tags': [{'Key': 'k1', 'Value': 'v1'},
                           {'Key': 'k2', 'Value': 'v2'}]}
        self.assert_params_for_cmd(cmdline, result)

    def test_add_tags_key_with_empty_value(self):
        args = ' --resource-id j-ABC123456 --tags k1=v1 k2 k3=v3'
        cmdline = self.prefix + args
        result = {'ResourceId': 'j-ABC123456',
                  'Tags': [{'Key': 'k1', 'Value': 'v1'},
                           {'Key': 'k2', 'Value': ''},
                           {'Key': 'k3', 'Value': 'v3'}]}
        self.assert_params_for_cmd(cmdline, result)

    def test_add_tags_key_value_space(self):
        cmdline = ['emr', 'add-tags', '--resource-id', 'j-ABC123456', '--tags',
                   'k1=v1', 'k2', 'k3=v3 v4']
        result = {'ResourceId': 'j-ABC123456',
                  'Tags': [{'Key': 'k1', 'Value': 'v1'},
                           {'Key': 'k2', 'Value': ''},
                           {'Key': 'k3', 'Value': 'v3 v4'}]}
        self.assert_params_for_cmd(cmdline, result)

if __name__ == "__main__":
    unittest.main()
