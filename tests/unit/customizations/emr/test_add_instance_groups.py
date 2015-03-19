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
import json
from mock import patch
from botocore.vendored import requests


DEFAULT_INSTANCE_GROUPS = [{'InstanceRole': 'TASK',
                            'InstanceCount': 10,
                            'Name': 'TASK',
                            'Market': 'ON_DEMAND',
                            'InstanceType': 'm2.large'
                            }]

ADD_INSTANCE_GROUPS_RESULT = {
    "InstanceGroupIds": [
        "ig-XXXX"
    ],
    "JobFlowId": "j-YYYY"
}

CONSTRUCTED_RESULT = {
    "InstanceGroupIds": [
        "ig-XXXX"
    ],
    "ClusterId": "j-YYYY"
}


class TestAddInstanceGroups(BaseAWSCommandParamsTest):
    prefix = 'emr add-instance-groups --cluster-id J-ABCD --instance-groups'

    def assert_error_message_has_field_name(self, error_msg, field_name):
        self.assertIn('Missing required parameter', error_msg)
        self.assertIn(field_name, error_msg)

    def test_instance_groups_default_name_market(self):
        cmd = self.prefix
        cmd += ' InstanceGroupType=TASK,InstanceCount=10,InstanceType=m2.large'
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS}

        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_missing_instance_group_type_error(self):
        cmd = self.prefix + ' Name=Task,InstanceType=m1.small,' +\
            'InstanceCount=5'
        result = self.run_cmd(cmd, 255)
        self.assert_error_message_has_field_name(result[1],
                                                 'InstanceGroupType')

    def test_instance_groups_missing_instance_type_error(self):
        cmd = self.prefix + ' Name=Task,InstanceGroupType=Task,' +\
            'InstanceCount=5'
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceType')

    def test_instance_groups_missing_instance_count_error(self):
        cmd = self.prefix + ' Name=Task,InstanceGroupType=Task,' +\
            'InstanceType=m1.xlarge'
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceCount')

    def test_instance_groups_all_fields(self):
        cmd = self.prefix + ' InstanceGroupType=MASTER,Name="MasterGroup",' +\
            'InstanceCount=1,InstanceType=m1.large'
        cmd += ' InstanceGroupType=CORE,Name="CoreGroup",InstanceCount=1,' +\
            'InstanceType=m1.xlarge,BidPrice=1.234'
        cmd += ' InstanceGroupType=TASK,Name="TaskGroup",InstanceCount=2,' +\
            'InstanceType=m1.large'

        expected_instance_groups = [
            {'InstanceRole': 'MASTER',
             'InstanceCount': 1,
             'Name': 'MasterGroup',
             'Market': 'ON_DEMAND',
             'InstanceType': 'm1.large'
             },
            {'InstanceRole': 'CORE',
             'InstanceCount': 1,
             'Name': 'CoreGroup',
             'Market': 'SPOT',
             'BidPrice': '1.234',
             'InstanceType': 'm1.xlarge'
             },
            {'InstanceRole': 'TASK',
             'InstanceCount': 2,
             'Name': 'TaskGroup',
             'Market': 'ON_DEMAND',
             'InstanceType': 'm1.large'
             }
            ]
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': expected_instance_groups}

        self.assert_params_for_cmd(cmd, result)

    @patch('awscli.customizations.emr.emrutils.call')
    def test_constructed_result(self, call_patch):
        call_patch.return_value = ADD_INSTANCE_GROUPS_RESULT
        cmd = self.prefix
        cmd += ' InstanceGroupType=TASK,InstanceCount=10,InstanceType=m2.large'

        result = self.run_cmd(cmd, expected_rc=0)
        result_json = json.loads(result[0])

        self.assertEquals(result_json, CONSTRUCTED_RESULT)

if __name__ == "__main__":
    unittest.main()
