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
from awscli.testutils import mock

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
from tests.unit.customizations.emr import test_constants as \
    CONSTANTS
import json


INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,'
    'AutoScalingPolicy={Constraints={MinCapacity=1,MaxCapacity=2},'
    'Rules=[{Name=TestRule,Description=TestDescription,Action={Market=ON_DEMAND,'
    'SimpleScalingPolicyConfiguration={AdjustmentType=EXACT_CAPACITY,ScalingAdjustment=2,CoolDown=5}},'
    'Trigger={CloudWatchAlarmDefinition={ComparisonOperator=GREATER_THAN,'
    'EvaluationPeriods=5,MetricName=TestMetric,Namespace=EMR,Period=3,Statistic=MAXIMUM,'
    'Threshold=4.565,Unit=NONE,Dimensions=[{Key=TestKey,Value=TestValue}]}}}]}'
)

INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100},VolumesPerInstance=4},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100}}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLTYPE_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={SizeInGB=100,Iops=100},VolumesPerInstance=4},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100}}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_SIZE_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,Iops=100},VolumesPerInstance=4},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100}}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100},VolumesPerInstance=4}]}')

MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES_VOLUME_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100},VolumesPerInstance=4}]} InstanceGroupType=CORE,InstanceType=d2.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=20}},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=40}}]}')

INSTANCE_GROUPS_WITH_CUSTOM_AMI_ARG = (
    ' InstanceGroupType=TASK,InstanceType=d2.xlarge,InstanceCount=2,CustomAmiId=ami-deadbeef'
)

DEFAULT_INSTANCE_GROUPS = [{'InstanceRole': 'TASK',
                            'InstanceCount': 10,
                            'Name': 'TASK',
                            'Market': 'ON_DEMAND',
                            'InstanceType': 'm2.large'
                            }]


DEFAULT_INSTANCE_GROUPS_WITH_CUSTOM_AMI = \
    [{'CustomAmiId':'ami-deadbeef',
    'InstanceRole': 'TASK',
    'InstanceCount': 2,
    'Name': 'TASK',
    'Market': 'ON_DEMAND',
    'InstanceType': 'd2.xlarge'}]

DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG = \
    [{'EbsConfiguration': 
        {'EbsOptimized': True,
            'EbsBlockDeviceConfigs': 
                [
                 {'VolumeSpecification':
                      {'Iops': 100,
                      'SizeInGB': 100,
                      'VolumeType': 'gp2'},
                      'VolumesPerInstance': 4},
                  {'VolumeSpecification':
                     {'Iops': 100,
                      'SizeInGB': 100,
                      'VolumeType': 'gp2'}}]},
    'InstanceCount': 2,
    'InstanceRole': 'TASK',
    'InstanceType': 'd2.xlarge',
    'Market': 'ON_DEMAND',
    'Name': 'TASK'}]

DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG_MISSING_IOPS = \
    [{'EbsConfiguration': 
        {'EbsOptimized': True,
            'EbsBlockDeviceConfigs': 
                [{'VolumeSpecification':
                  {'SizeInGB': 100,
                  'VolumeType': 'gp2'},
                  'VolumesPerInstance': 4}]},

     'InstanceCount': 2,
     'InstanceRole': 'TASK',
     'InstanceType': 'd2.xlarge',
     'Market': 'ON_DEMAND',
     'Name': 'TASK'}]

DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG_MISSING_VOLSPEC = \
    [{'EbsConfiguration': {'EbsOptimized': True},
    'InstanceCount': 2,
    'InstanceRole': 'TASK',
    'InstanceType': 'd2.xlarge',
    'Market': 'ON_DEMAND',
    'Name': 'TASK'}]

DEFAULT_INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY = \
[{'InstanceCount': 2,
  'InstanceRole': 'TASK',
  'InstanceType': 'd2.xlarge',
  'Market': 'ON_DEMAND',
  'Name': 'TASK',
  'AutoScalingPolicy': {
      'Constraints': {
          'MinCapacity': 1,
          'MaxCapacity': 2
      },
      'Rules': [
          {
             'Name': 'TestRule',
             'Description': 'TestDescription',
             'Action': {
                 'Market': 'ON_DEMAND',
                 'SimpleScalingPolicyConfiguration': {
                     'AdjustmentType': 'EXACT_CAPACITY',
                     'ScalingAdjustment': 2,
                     'CoolDown': 5
                 }
             },
             'Trigger': {
                 'CloudWatchAlarmDefinition': {
                     'ComparisonOperator': 'GREATER_THAN',
                     'Dimensions': [
                         {
                             'Key': 'TestKey',
                             'Value': 'TestValue'
                         }],
                     'EvaluationPeriods': 5,
                     'MetricName': 'TestMetric',
                     'Namespace': 'EMR',
                     'Period': 3,
                     'Statistic': 'MAXIMUM',
                     'Threshold': 4.565,
                     'Unit': 'NONE'
                 }
             }
          }
      ]
  }
  }]

DEFAULT_MULTIPLE_INSTANCE_GROUPS_WITH_EBS_CONFIG = \
    [{'EbsConfiguration': 
        {'EbsOptimized': True,
            'EbsBlockDeviceConfigs': 
                [{'VolumeSpecification':
                  {'SizeInGB': 100,
                  'VolumeType': 'gp2'},
                  'VolumesPerInstance': 4}]},
    'InstanceCount': 2,
    'InstanceRole': 'TASK',
    'InstanceType': 'd2.xlarge',
    'Market': 'ON_DEMAND',
    'Name': 'TASK'},
   {'EbsConfiguration': 
        {'EbsOptimized': True,
            'EbsBlockDeviceConfigs': 
                [{'VolumeSpecification':
                   {'Iops': 20,
                    'SizeInGB': 100,
                    'VolumeType': 'gp2'
                    }},
                   {'VolumeSpecification':
                    {'Iops': 40,
                    'SizeInGB': 100,
                    'VolumeType': 'gp2'}}]},
    'InstanceCount': 2,
    'InstanceRole': 'CORE',
    'InstanceType': 'd2.xlarge',
    'Market': 'ON_DEMAND',
    'Name': 'CORE'}]


ADD_INSTANCE_GROUPS_RESULT = {
    "InstanceGroupIds": [
        "ig-XXXX"
    ],
    "ClusterArn": "arn:aws:elasticmapreduce:region:012345678910:cluster/j-XXXX",
    "JobFlowId": "j-YYYY"
}

CONSTRUCTED_RESULT = {
    "InstanceGroupIds": [
        "ig-XXXX"
    ],
    "ClusterArn": "arn:aws:elasticmapreduce:region:012345678910:cluster/j-XXXX",
    "ClusterId": "j-YYYY"
}


class TestAddInstanceGroups(BaseAWSCommandParamsTest):
    prefix = 'emr add-instance-groups --cluster-id J-ABCD --instance-groups'

    def test_instance_groups_with_autoscaling_policy(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY}
        self.assert_params_for_cmd(cmd, result)

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
        result = self.run_cmd(cmd, 252)
        self.assert_error_message_has_field_name(result[1],
                                                 'InstanceGroupType')

    def test_instance_groups_missing_instance_type_error(self):
        cmd = self.prefix + ' Name=Task,InstanceGroupType=Task,' +\
            'InstanceCount=5'
        stderr = self.run_cmd(cmd, 252)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceType')

    def test_instance_groups_missing_instance_count_error(self):
        cmd = self.prefix + ' Name=Task,InstanceGroupType=Task,' +\
            'InstanceType=m1.xlarge'
        stderr = self.run_cmd(cmd, 252)[1]
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

    def test_instance_groups_spot_bidprice_equals_ondemandprice(self):
        cmd = self.prefix + ' InstanceGroupType=MASTER,Name="MasterGroup",' +\
            'InstanceCount=1,InstanceType=m1.large,BidPrice=OnDemandPrice'
        cmd += ' InstanceGroupType=CORE,Name="CoreGroup",InstanceCount=1,' +\
            'InstanceType=m1.xlarge,BidPrice=OnDemandPrice'
        cmd += ' InstanceGroupType=TASK,Name="TaskGroup",InstanceCount=2,' +\
            'InstanceType=m1.large,BidPrice=OnDemandPrice'

        expected_instance_groups = [
            {'InstanceRole': 'MASTER',
             'InstanceCount': 1,
             'Name': 'MasterGroup',
             'Market': 'SPOT',
             'InstanceType': 'm1.large'
             },
            {'InstanceRole': 'CORE',
             'InstanceCount': 1,
             'Name': 'CoreGroup',
             'Market': 'SPOT',
             'InstanceType': 'm1.xlarge'
             },
            {'InstanceRole': 'TASK',
             'InstanceCount': 2,
             'Name': 'TaskGroup',
             'Market': 'SPOT',
             'InstanceType': 'm1.large'
             }
        ]
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': expected_instance_groups}

        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG}
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_volume_type(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLTYPE_ARG
        stderr = self.run_cmd(cmd, 252)[1]
        self.assert_error_message_has_field_name(stderr, 'VolumeType')

    def test_instance_groups_with_ebs_config_missing_size(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_SIZE_ARG
        stderr = self.run_cmd(cmd, 252)[1]
        self.assert_error_message_has_field_name(stderr, 'SizeInGB')

    def test_instance_groups_with_ebs_config_missing_volume_spec(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC_ARG
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG_MISSING_VOLSPEC}
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_iops(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS_ARG
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS_WITH_EBS_CONFIG_MISSING_IOPS}
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_multiple_instance_groups(self):
        cmd = self.prefix
        cmd += MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES_VOLUME_ARG
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_MULTIPLE_INSTANCE_GROUPS_WITH_EBS_CONFIG}
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_custom_ami_instance_groups(self):
        cmd = self.prefix
        cmd += INSTANCE_GROUPS_WITH_CUSTOM_AMI_ARG
        result = {'JobFlowId': 'J-ABCD',
                  'InstanceGroups': DEFAULT_INSTANCE_GROUPS_WITH_CUSTOM_AMI}
        self.assert_params_for_cmd(cmd, result)

    @mock.patch('awscli.customizations.emr.emrutils.call')
    def test_constructed_result(self, call_patch):
        call_patch.return_value = ADD_INSTANCE_GROUPS_RESULT
        cmd = self.prefix
        cmd += ' InstanceGroupType=TASK,InstanceCount=10,InstanceType=m2.large'

        result = self.run_cmd(cmd, expected_rc=0)
        result_json = json.loads(result[0])

        self.assertEqual(result_json, CONSTRUCTED_RESULT)

if __name__ == "__main__":
    unittest.main()
