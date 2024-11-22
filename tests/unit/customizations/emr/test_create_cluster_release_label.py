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

import copy
import os

from botocore.compat import json
from botocore.compat import OrderedDict

from tests.unit.customizations.emr import test_constants as \
    CONSTANTS
from tests.unit.customizations.emr import test_constants_instance_fleets as \
    CONSTANTS_FLEET
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
from awscli.testutils import mock

DEFAULT_CLUSTER_NAME = "Development Cluster"

DEFAULT_INSTANCE_GROUPS_ARG = (
    'InstanceGroupType=MASTER,Name=MASTER,'
    'InstanceCount=1,InstanceType=m1.large '
    'InstanceGroupType=CORE,Name=CORE,'
    'InstanceCount=1,InstanceType=m1.large '
    'InstanceGroupType=TASK,Name=TASK,'
    'InstanceCount=1,InstanceType=m1.large ')

HA_INSTANCE_GROUPS_ARG = (
    'InstanceGroupType=MASTER,Name=MASTER,'
    'InstanceCount=3,InstanceType=m1.large '
    'InstanceGroupType=CORE,Name=CORE,'
    'InstanceCount=1,InstanceType=m1.large ')

DEFAULT_INSTANCE_GROUPS = \
    [{'InstanceRole': 'MASTER',
      'InstanceCount': 1,
      'Name': 'MASTER',
      'Market': 'ON_DEMAND',
      'InstanceType': 'm1.large'
      },
     {'InstanceRole': 'CORE',
      'InstanceCount': 1,
      'Name': 'CORE',
      'Market': 'ON_DEMAND',
      'InstanceType': 'm1.large'
      },
     {'InstanceRole': 'TASK',
      'InstanceCount': 1,
      'Name': 'TASK',
      'Market': 'ON_DEMAND',
      'InstanceType': 'm1.large'
      }]

HA_INSTANCE_GROUPS = \
    [{'InstanceRole': 'MASTER',
      'InstanceCount': 3,
      'Name': 'MASTER',
      'Market': 'ON_DEMAND',
      'InstanceType': 'm1.large'
      },
     {'InstanceRole': 'CORE',
      'InstanceCount': 1,
      'Name': 'CORE',
      'Market': 'ON_DEMAND',
      'InstanceType': 'm1.large'
      }]


DEFAULT_CMD = ('emr create-cluster --release-label emr-4.0.0'
               ' --use-default-roles'
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG + ' ')

DEFAULT_INSTANCES = {'KeepJobFlowAliveWhenNoSteps': True,
                     'TerminationProtected': False,
                     'InstanceGroups': DEFAULT_INSTANCE_GROUPS
                     }

HA_INSTANCES = {'KeepJobFlowAliveWhenNoSteps': True,
                'TerminationProtected': False,
                'InstanceGroups': HA_INSTANCE_GROUPS
                }

EC2_ROLE_NAME = "EMR_EC2_DefaultRole"
EMR_ROLE_NAME = "EMR_DefaultRole"

DEFAULT_KERBEROS_ATTRIBUTES_ARGS = 'Realm=EC2.INTERNAL,' \
                                   'KdcAdminPassword=123,' \
                                   'CrossRealmTrustPrincipalPassword=123,' \
                                   'ADDomainJoinUser=aws,' \
                                   'ADDomainJoinPassword=123'

KERBEROS_ATTRIBUTES = {'Realm': 'EC2.INTERNAL',
                       'KdcAdminPassword': '123',
                       'CrossRealmTrustPrincipalPassword': '123',
                       'ADDomainJoinUser': 'aws',
                       'ADDomainJoinPassword': '123'
                      }

TEST_BA = [
    {
        'ScriptBootstrapAction': {
            'Path': 's3://test/ba1',
            'Args': ['arg1', 'arg2', 'arg3']
        },
        'Name': 'ba1'
    },
    {
        'ScriptBootstrapAction': {
            'Path': 's3://test/ba2',
            'Args': ['arg1', 'arg2', 'arg3']
        },
        'Name': 'ba2'
    }
]

CUSTOM_JAR_STEP = {
    'Name': 'Custom JAR',
    'ActionOnFailure': 'CONTINUE',
    'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
}

STREAMING_ARGS = (
    'Args=-files,'
    's3://elasticmapreduce/samples/wordcount/wordSplitter.py,'
    '-mapper,wordSplitter.py,'
    '-reducer,aggregate,'
    '-input,s3://elasticmapreduce/samples/wordcount/input,'
    '-output,s3://mybucket/wordcount/output/2014-04-18/12-15-24')

STREAMING_HADOOP_JAR_STEP = {
    'Jar': 'command-runner.jar',
    'Args': [
        'hadoop-streaming',
        '-files',
        's3://elasticmapreduce/samples/wordcount/wordSplitter.py',
        '-mapper',
        'wordSplitter.py',
        '-reducer',
        'aggregate',
        '-input',
        's3://elasticmapreduce/samples/wordcount/input',
        '-output',
        's3://mybucket/wordcount/output/2014-04-18/12-15-24']
}

CREATE_CLUSTER_RESULT = {
    "JobFlowId": "j-XXXX",
    "ClusterArn": "arn:aws:elasticmapreduce:region:012345678910:cluster/j-XXXX"
}

CONSTRUCTED_RESULT = {
    "ClusterId": "j-XXXX",
    "ClusterArn": "arn:aws:elasticmapreduce:region:012345678910:cluster/j-XXXX"
}

DEFAULT_RESULT = \
    {
        'Name': DEFAULT_CLUSTER_NAME,
        'Instances': DEFAULT_INSTANCES,
        'ReleaseLabel': 'emr-4.0.0',
        'VisibleToAllUsers': True,
        'JobFlowRole': EC2_ROLE_NAME,
        'ServiceRole': EMR_ROLE_NAME,
        'Tags': []
    }

EMR_MANAGED_MASTER_SECURITY_GROUP = 'sg-master1'

EMR_MANAGED_SLAVE_SECURITY_GROUP = 'sg-slave1'

SERVICE_ACCESS_SECURITY_GROUP = "sg-service-access"

ADDITIONAL_MASTER_SECURITY_GROUPS = \
    ['sg-addMaster1', 'sg-addMaster2', 'sg-addMaster3', 'sg-addMaster4']

ADDITIONAL_SLAVE_SECURITY_GROUPS = \
    ['sg-addSlave1', 'sg-addSlave2', 'sg-addSlave3', 'sg-addSlave4']

HIVE_BASIC_ARGS = (
    'Args=-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q')

HIVE_DEFAULT_STEP = {
    'Name': 'Hive program',
    'ActionOnFailure': 'CONTINUE',
    'HadoopJarStep': {
        'Jar':
            ('command-runner.jar'),
        'Args': [
            'hive-script',
            '--run-hive-script',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/hive-ads/libs/model-build.q']}
}

HIVE_STEP = {
    'Name': 'HiveBasicStep',
    'ActionOnFailure': 'CANCEL_AND_WAIT',
    'HadoopJarStep': {
        'Jar':
            ('command-runner.jar'),
        'Args': [
            'hive-script',
            '--run-hive-script',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/hive-ads/libs/model-build.q']}
}

PIG_BASIC_ARGS = 'Args=-f,' + \
    's3://elasticmapreduce/samples/pig-apache/do-reports2.pig'

PIG_DEFAULT_STEP = {
    'Name': 'Pig program',
    'ActionOnFailure': 'CONTINUE',
    'HadoopJarStep': {
        'Jar':
            ('command-runner.jar'),
        'Args': [
            'pig-script',
            '--run-pig-script',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/'
            'pig-apache/do-reports2.pig']}
}

PIG_STEP = {
    'Name': 'PigBasicStep',
    'ActionOnFailure': 'CANCEL_AND_WAIT',
    'HadoopJarStep': {
        'Jar':
            ('command-runner.jar'),
        'Args': [
            'pig-script',
            '--run-pig-script',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/'
            'pig-apache/do-reports2.pig']}
}


class TestCreateCluster(BaseAWSCommandParamsTest):
    prefix = 'emr create-cluster '

    def test_ami_version_release_label_exclusive_validation(self):
        cmd = (self.prefix + '--ami-version 3.8.0 --release-label '
               'emr-4.0.0 --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        expected_error_msg = (
            '\naws: error: You cannot specify both --ami-version'
            ' and --release-label options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_if_ami_version_or_release_label_is_provided(self):
        cmd = (self.prefix + ' --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        expected_error_msg = ('\naws: error: Either --ami-version or'
                              ' --release-label is required.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_no_special_steps_added_for_applications(self):
        cmd = (DEFAULT_CMD + '--applications Name=MapR')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'MapR'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=HUE')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'HUE'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=HIVE')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'HIVE'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=PIG')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'PIG'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=HBASE')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'HBASE'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=IMPALA')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'IMPALA'}]
        self.assert_params_for_cmd(cmd, result)

        cmd = (DEFAULT_CMD + '--applications Name=GANGLIA')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'GANGLIA'}]
        self.assert_params_for_cmd(cmd, result)

    def test_configurations(self):
        cmd = (DEFAULT_CMD + ' --configurations '
               '[{\"Classification\":\"hadoop-env\",\"Properties\":{'
               '\"someProperty\":\"someValue\"},\"Configurations\":[]}]')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Configurations'] = [
            {
                'Classification': 'hadoop-env',
                'Configurations': [],
                'Properties': {'someProperty': 'someValue'}
            }
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_quick_start(self):
        cmd = (self.prefix + '--release-label emr-4.0.0 --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.0.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def assert_error_message_has_field_name(self, error_msg, field_name):
        self.assertIn('Missing required parameter', error_msg)
        self.assertIn(field_name, error_msg)

    def test_default_cmd(self):
        self.assert_params_for_cmd(DEFAULT_CMD, DEFAULT_RESULT)

    def test_cluster_without_service_role_and_instance_profile(self):
        cmd = ('emr create-cluster --release-label emr-4.0.0 '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = copy.deepcopy(DEFAULT_RESULT)
        del result['JobFlowRole']
        del result['ServiceRole']
        self.assert_params_for_cmd(cmd, result)

    def test_cluster_with_service_role_and_instance_profile(self):
        cmd = ('emr create-cluster --release-label emr-4.0.0'
               ' --service-role ServiceRole --ec2-attributes '
               'InstanceProfile=Ec2_InstanceProfile '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['JobFlowRole'] = 'Ec2_InstanceProfile'
        result['ServiceRole'] = 'ServiceRole'
        self.assert_params_for_cmd(cmd, result)

    def test_mutual_exclusive_use_default_roles_and_service_role(self):
        cmd = (DEFAULT_CMD +
               '--ec2-attributes InstanceProfile=Ec2_InstanceProfile')
        expected_error_msg = (
            '\naws: error: You cannot specify both --use-default-roles '
            'and --ec2-attributes InstanceProfile options together. Either '
            'choose --use-default-roles or use both --service-role <roleName>'
            ' and --ec2-attributes InstanceProfile=<profileName>.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_mutual_exclusive_use_default_roles_and_instance_profile(self):
        cmd = (DEFAULT_CMD + '--service-role ServiceRole '
               '--ec2-attributes InstanceProfile=Ec2_InstanceProfile')
        expected_error_msg = (
            '\naws: error: You cannot specify both --use-default-roles '
            'and --service-role options together. Either choose '
            '--use-default-roles or use both --service-role <roleName> '
            'and --ec2-attributes InstanceProfile=<profileName>.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_cluster_name_no_space(self):
        cmd = DEFAULT_CMD + '--name MyCluster'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Name'] = 'MyCluster'
        self.assert_params_for_cmd(cmd, result)

    def test_cluster_name_with_space(self):
        cmd = DEFAULT_CMD.split() + ['--name', 'My Cluster']
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Name'] = 'My Cluster'
        self.assert_params_for_cmd(cmd, result)

    def test_ami_version(self):
        cmd = DEFAULT_CMD + '--release-label emr-4.0.0'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['ReleaseLabel'] = 'emr-4.0.0'
        self.assert_params_for_cmd(cmd, result)

    def test_log_uri(self):
        test_log_uri = 's3://test/logs'
        cmd = DEFAULT_CMD + '--log-uri ' + test_log_uri
        result = copy.deepcopy(DEFAULT_RESULT)
        result['LogUri'] = test_log_uri
        self.assert_params_for_cmd(cmd, result)

    def test_additional_info(self):
        test_info = '{ami32: "ami-82e305f5"}'
        cmd = DEFAULT_CMD.split() + ['--additional-info', test_info]
        result = copy.deepcopy(DEFAULT_RESULT)
        result['AdditionalInfo'] = test_info
        self.assert_params_for_cmd(cmd, result)

    def test_auto_terminte(self):
        cmd = ('emr create-cluster --use-default-roles'
               ' --release-label emr-4.0.0 '
               '--auto-terminate --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        result = copy.deepcopy(DEFAULT_RESULT)
        instances = copy.deepcopy(DEFAULT_INSTANCES)
        instances['KeepJobFlowAliveWhenNoSteps'] = False
        result['Instances'] = instances
        self.assert_params_for_cmd(cmd, result)

    def test_auto_terminate_and_no_auto_terminate(self):
        cmd = (DEFAULT_CMD + '--release-label emr-4.0.0 ' +
               '--auto-terminate --no-auto-terminate')
        expected_error_msg = (
            '\naws: error: cannot use both --no-auto-terminate and'
            ' --auto-terminate options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_termination_protected(self):
        cmd = DEFAULT_CMD + '--termination-protected'
        result = copy.deepcopy(DEFAULT_RESULT)
        instances = copy.deepcopy(DEFAULT_INSTANCES)
        instances['TerminationProtected'] = True
        result['Instances'] = instances
        self.assert_params_for_cmd(cmd, result)

    def test_no_termination_protected(self):
        cmd = DEFAULT_CMD + '--no-termination-protected'
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_termination_protected_and_no_termination_protected(self):
        cmd = DEFAULT_CMD + \
            '--termination-protected --no-termination-protected'
        expected_error_msg = (
            '\naws: error: cannot use both --termination-protected'
            ' and --no-termination-protected options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_unhealthy_node_replacement(self):
        cmd = DEFAULT_CMD + '--unhealthy-node-replacement'
        result = copy.deepcopy(DEFAULT_RESULT)
        instances = copy.deepcopy(DEFAULT_INSTANCES)
        instances['UnhealthyNodeReplacement'] = True
        result['Instances'] = instances
        self.assert_params_for_cmd(cmd, result)

    def test_no_unhealthy_node_replacement(self):
        cmd = DEFAULT_CMD + '--no-unhealthy-node-replacement'
        result = copy.deepcopy(DEFAULT_RESULT)
        instances = copy.deepcopy(DEFAULT_INSTANCES)
        instances['UnhealthyNodeReplacement'] = False
        result['Instances'] = instances
        self.assert_params_for_cmd(cmd, result)

    def test_unhealthy_node_replacement_and_no_unhealthy_node_replacement(self):
        cmd = DEFAULT_CMD + \
            '--unhealthy-node-replacement --no-unhealthy-node-replacement'
        expected_error_msg = (
            '\naws: error: cannot use both --unhealthy-node-replacement'
            ' and --no-unhealthy-node-replacement options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_visible_to_all_users(self):
        cmd = DEFAULT_CMD + '--visible-to-all-users'
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_no_visible_to_all_users(self):
        cmd = DEFAULT_CMD + '--no-visible-to-all-users'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['VisibleToAllUsers'] = False
        self.assert_params_for_cmd(cmd, result)

    def test_visible_to_all_users_and_no_visible_to_all_users(self):
        cmd = DEFAULT_CMD + '--visible-to-all-users --no-visible-to-all-users'
        expected_error_msg = (
            '\naws: error: cannot use both --visible-to-all-users and '
            '--no-visible-to-all-users options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_tags(self):
        cmd = DEFAULT_CMD.split() + ['--tags', 'k1=v1', 'k2', 'k3=spaces  v3']
        result = copy.deepcopy(DEFAULT_RESULT)
        tags = [{'Key': 'k1', 'Value': 'v1'},
                {'Key': 'k2', 'Value': ''},
                {'Key': 'k3', 'Value': 'spaces  v3'}]
        result['Tags'] = tags
        self.assert_params_for_cmd(cmd, result)

    def test_enable_debugging(self):
        cmd = DEFAULT_CMD + '--log-uri s3://test/logs --enable-debugging'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['LogUri'] = 's3://test/logs'
        debugging_config = \
            [{'Name': 'Setup Hadoop Debugging',
              'ActionOnFailure': 'TERMINATE_CLUSTER',
              'HadoopJarStep':
                {'Args': ['state-pusher-script'],
                 'Jar': 'command-runner.jar'
                 }
              }]
        result['Steps'] = debugging_config
        self.assert_params_for_cmd(cmd, result)

        cmd = DEFAULT_CMD + ('--log-uri s3://test/logs --enable-debugging '
                             '--region us-west-2')
        debugging_config = \
            [{'Name': 'Setup Hadoop Debugging',
              'ActionOnFailure': 'TERMINATE_CLUSTER',
              'HadoopJarStep':
                {'Args': ['state-pusher-script'],
                 'Jar': 'command-runner.jar'
                 }
              }]
        result['Steps'] = debugging_config
        self.assert_params_for_cmd(cmd, result)

    def test_enable_debugging_no_log_uri(self):
        cmd = DEFAULT_CMD + '--enable-debugging'
        expected_error_msg = (
            '\naws: error: LogUri not specified. You must specify a logUri'
            ' if you enable debugging when creating a cluster.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_enable_debugging_and_no_enable_debugging(self):
        cmd = DEFAULT_CMD + '--enable-debugging --no-enable-debugging' + \
            ' --log-uri s3://test/logs'
        expected_error_msg = (
            '\naws: error: cannot use both --enable-debugging and '
            '--no-enable-debugging options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_instance_groups_default_name_market(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-groups '
            'InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m1.large '
            'InstanceGroupType=CORE,InstanceCount=1,InstanceType=m1.large '
            'InstanceGroupType=TASK,InstanceCount=1,InstanceType=m1.large ')
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_instance_groups_instance_group_type_mismatch_cases(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-groups '
            'Name=MASTER,InstanceGroupType=MaSter,InstanceCount=1,'
            'InstanceType=m1.large Name=CORE,InstanceGroupType=cORE,'
            'InstanceCount=1,InstanceType=m1.large Name=TASK,'
            'InstanceGroupType=tAsK,InstanceCount=1,InstanceType=m1.large')
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_instance_groups_instance_type_and_count(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-type m1.large')
        expected_result = copy.deepcopy(DEFAULT_RESULT)
        expected_result['Instances'] = \
            {'KeepJobFlowAliveWhenNoSteps': True,
             'TerminationProtected': False,
             'InstanceGroups':
                [{'InstanceRole': 'MASTER',
                  'InstanceCount': 1,
                  'Name': 'MASTER',
                  'Market': 'ON_DEMAND',
                  'InstanceType': 'm1.large'}]
             }
        self.assert_params_for_cmd(cmd, expected_result)
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-type m1.large --instance-count 3')
        expected_result = copy.deepcopy(DEFAULT_RESULT)
        expected_result['Instances'] = \
            {'KeepJobFlowAliveWhenNoSteps': True,
             'TerminationProtected': False,
             'InstanceGroups':
                [{'InstanceRole': 'MASTER',
                  'InstanceCount': 1,
                  'Name': 'MASTER',
                  'Market': 'ON_DEMAND',
                  'InstanceType': 'm1.large'
                  },
                 {'InstanceRole': 'CORE',
                  'InstanceCount': 2,
                  'Name': 'CORE',
                  'Market': 'ON_DEMAND',
                  'InstanceType': 'm1.large'
                  }]
             }
        self.assert_params_for_cmd(cmd, expected_result)

    def test_instance_groups_missing_required_parameter_error(self):
        cmd = ('emr create-cluster --use-default-roles --release-label'
               ' emr-4.0.0 ')
        expect_error_msg = (
            '\naws: error: Must specify either --instance-groups or '
            '--instance-type with --instance-count(optional) to '
            'configure instance groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-count 2')
        expect_error_msg = (
            '\naws: error: Must specify either --instance-groups or '
            '--instance-type with --instance-count(optional) to '
            'configure instance groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_instance_groups_exclusive_parameter_validation_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label 4.0.0 '
            '--instance-type m1.large --instance-groups ' +
            DEFAULT_INSTANCE_GROUPS_ARG)
        expect_error_msg = (
            '\naws: error: You may not specify --instance-type '
            'or --instance-count with --instance-groups, '
            'because --instance-type and --instance-count are '
            'shortcut options for --instance-groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--instance-type m1.large --instance-count 2 '
            '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        expect_error_msg = (
            '\naws: error: You may not specify --instance-type '
            'or --instance-count with --instance-groups, '
            'because --instance-type and --instance-count are '
            'shortcut options for --instance-groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_instance_groups_missing_instance_group_type_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--auto-terminate '
            '--instance-groups '
            'Name=Master,InstanceCount=1,InstanceType=m1.small')
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceGroupType')

    def test_instance_groups_missing_instance_type_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--auto-terminate '
            '--instance-groups '
            'Name=Master,InstanceGroupType=MASTER,InstanceCount=1')
        expect_error_msg = (
            '\nThe following required parameters are missing'
            ' for structure:: InstanceType\n')
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceType')

    def test_instance_groups_missing_instance_count_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --release-label emr-4.0.0 '
            '--auto-terminate '
            '--instance-groups '
            'Name=Master,InstanceGroupType=MASTER,InstanceType=m1.xlarge')
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceCount')

    def test_instance_groups_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_groups.json')
        cmd = ('emr create-cluster --use-default-roles'
               ' --release-label emr-4.0.0  '
               '--instance-groups file://' + data_path)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['InstanceGroups'] = \
            [
                {'InstanceRole': 'MASTER',
                 'InstanceCount': 1,
                 'Name': 'Master Instance Group',
                 'Market': 'ON_DEMAND',
                 'InstanceType': 'm1.large'
                 },
                {'InstanceRole': 'CORE',
                 'InstanceCount': 2,
                 'Name': 'Core Instance Group',
                 'Market': 'ON_DEMAND',
                 'InstanceType': 'm1.xlarge'
                 },
                {'InstanceRole': 'TASK',
                 'InstanceCount': 3,
                 'Name': 'Task Instance Group',
                 'Market': 'SPOT',
                 'BidPrice': '3.45',
                 'InstanceType': 'm1.xlarge'
                 }
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_from_json_file_spot_bidprice_equals_ondemandprice(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_groups_spot_bidprice_equals_ondemandprice.json')
        cmd = ('emr create-cluster --use-default-roles'
               ' --release-label emr-4.0.0  '
               '--instance-groups file://' + data_path)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['InstanceGroups'] = \
            [
                {'InstanceRole': 'MASTER',
                 'InstanceCount': 1,
                 'Name': 'Master Instance Group',
                 'Market': 'SPOT',
                 'InstanceType': 'm1.large'
                 },
                {'InstanceRole': 'CORE',
                 'InstanceCount': 2,
                 'Name': 'Core Instance Group',
                 'Market': 'SPOT',
                 'InstanceType': 'm1.xlarge'
                 },
                {'InstanceRole': 'TASK',
                 'InstanceCount': 3,
                 'Name': 'Task Instance Group',
                 'Market': 'SPOT',
                 'InstanceType': 'm1.xlarge'
                 }
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_adds_configurations(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_groups_with_configurations.json')
        cmd = ('emr create-cluster --use-default-roles'
                ' --release-label emr-4.0.0 '
                '--instance-groups file://' + data_path)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['InstanceGroups'][1]['Configurations'] = [
            OrderedDict([
                ("Classification", "hdfs-site"),
                ("Properties", OrderedDict([
                    ("test-key1", "test-value1"),
                    ("test-key2", "test-value2")
                ]))
            ])
        ]
        self.assert_params_for_cmd(cmd, result)


    def test_ec2_attributes_no_az(self):
        cmd = ('emr create-cluster --release-label emr-4.0.0 '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG +
               ' --ec2-attributes KeyName=testkey,SubnetId=subnet-123456,'
               'InstanceProfile=EMR_EC2_DefaultRole '
               '--service-role EMR_DefaultRole')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['Ec2KeyName'] = 'testkey'
        result['Instances']['Ec2SubnetId'] = 'subnet-123456'
        result['JobFlowRole'] = 'EMR_EC2_DefaultRole'
        self.assert_params_for_cmd(cmd, result)

    def test_ec2_attributes_az(self):
        cmd = DEFAULT_CMD + '--ec2-attributes AvailabilityZone=us-east-1a'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['Placement'] = {'AvailabilityZone': 'us-east-1a'}
        self.assert_params_for_cmd(cmd, result)

    def test_ec2_attributes_subnet_az_error(self):
        cmd = DEFAULT_CMD + '--ec2-attributes ' + \
            'SubnetId=subnet-123456,AvailabilityZone=us-east-1a'
        expect_error_msg = (
            '\naws: error: You may not specify both a SubnetId and an Availab'
            'ilityZone (placement) because ec2SubnetId implies a placement.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_ec2_attributes_with_subnet_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_ec2_attributes_with_subnet.json')
        cmd = ('emr create-cluster --release-label emr-4.0.0 '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG +
               ' --ec2-attributes file://' + data_path +
               ' --service-role EMR_DefaultRole')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['Ec2KeyName'] = 'testkey'
        result['Instances']['Ec2SubnetId'] = 'subnet-123456'
        result['JobFlowRole'] = 'EMR_EC2_DefaultRole'
        self.assert_params_for_cmd(cmd, result)

    def test_ec2_attributes_with_az_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_ec2_attributes_with_az.json')
        cmd = ('emr create-cluster --release-label emr-4.0.0 '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG +
               ' --ec2-attributes file://' + data_path +
               ' --service-role EMR_DefaultRole')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Instances']['Ec2KeyName'] = 'testkey'
        result['Instances']['Placement'] = {'AvailabilityZone': 'us-east-1a'}
        result['JobFlowRole'] = 'EMR_EC2_DefaultRole'
        self.assert_params_for_cmd(cmd, result)

    # Bootstrap Actions test cases
    def test_bootstrap_actions_missing_path_error(self):
        cmd = DEFAULT_CMD + '--bootstrap-actions Name=ba1,Args=arg1,arg2'
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'Path')

    def test_bootstrap_actions_with_all_fields(self):
        cmd = DEFAULT_CMD + (
            ' --bootstrap-actions '
            'Path=s3://test/ba1,Name=ba1,Args=arg1,arg2,arg3 '
            'Path=s3://test/ba2,Name=ba2,Args=arg1,arg2,arg3')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = TEST_BA

        self.assert_params_for_cmd(cmd, result)

    def test_bootstrap_actions_exceed_maximum_error(self):
        cmd = DEFAULT_CMD + ' --bootstrap-actions'
        ba_cmd = ' Path=s3://test/ba1,Name=ba1,Args=arg1,arg2,arg3'
        for i in range(1, 18):
            cmd += ba_cmd

        expected_error_msg = '\naws: error: maximum number of ' +\
                             'bootstrap actions for a cluster exceeded.\n'
        result = self.run_cmd(cmd, 255)

        self.assertEqual(expected_error_msg, result[1])

    def test_bootstrap_actions_exceed_maximum_with_applications_error(self):
        cmd = DEFAULT_CMD + ' --bootstrap-actions'
        ba_cmd = ' Path=s3://test/ba1,Name=ba1,Args=arg1,arg2,arg3'
        for i in range(1, 20):
            cmd += ba_cmd
        expected_error_msg = '\naws: error: maximum number of ' +\
                             'bootstrap actions for a cluster exceeded.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_boostrap_actions_with_default_fields(self):
        cmd = DEFAULT_CMD + (
            ' --bootstrap-actions Path=s3://test/ba1 Path=s3://test/ba2')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = \
            [
                {'Name': 'Bootstrap action',
                 'ScriptBootstrapAction':
                    {'Path': 's3://test/ba1'}
                 },
                {'Name': 'Bootstrap action',
                 'ScriptBootstrapAction':
                    {'Path': 's3://test/ba2'}
                 }
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_bootstrap_actions_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_bootstrap_actions.json')
        cmd = DEFAULT_CMD + ' --bootstrap-actions file://' + data_path
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = \
            [
                {"Name": "Bootstrap Action 1",
                 "ScriptBootstrapAction":
                    {"Path": "s3://mybucket/test1",
                     "Args": ["arg1", "arg2"]}
                 },
                {"Name": "Bootstrap Action 2",
                 "ScriptBootstrapAction":
                    {"Path": "s3://mybucket/test2",
                     "Args": ["arg1", "arg2"]}
                 }
        ]
        self.assert_params_for_cmd(cmd, result)

    # Steps test cases
    def test_wrong_step_type_error(self):
        cmd = DEFAULT_CMD + '--steps Type=unknown'
        expected_error_msg = (
            '\naws: error: The step type unknown is not supported.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_default_step_type_name_action_on_failure(self):
        cmd = DEFAULT_CMD + '--steps Jar=s3://mybucket/mytest.jar'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [CUSTOM_JAR_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_custom_jar_step_missing_jar(self):
        cmd = DEFAULT_CMD + '--steps Name=CustomJarMissingJar'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for CustomJARStepConfig: Jar.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_custom_jar_step_with_all_fields(self):
        cmd = DEFAULT_CMD + '--steps ' + (
            'Name=Custom,Type=Custom_JAR,'
            'Jar=s3://mybucket/mytest.jar,'
            'Args=arg1,arg2,MainClass=mymainclass,'
            'ActionOnFailure=TERMINATE_CLUSTER')
        expected_steps = [
            {'Name': 'Custom',
             'ActionOnFailure': 'TERMINATE_CLUSTER',
             'HadoopJarStep':
                {'Jar': 's3://mybucket/mytest.jar',
                 'Args': ['arg1', 'arg2'],
                 'MainClass': 'mymainclass'}
             }
        ]
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = expected_steps
        self.assert_params_for_cmd(cmd, result)

    def test_streaming_step_with_default_fields(self):
        cmd = DEFAULT_CMD + '--steps Type=Streaming,' + STREAMING_ARGS
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [
            {'Name': 'Streaming program',
             'ActionOnFailure': 'CONTINUE',
             'HadoopJarStep': STREAMING_HADOOP_JAR_STEP}
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_streaming_step_missing_args(self):
        cmd = DEFAULT_CMD + '--steps Type=Streaming'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for StreamingStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_streaming_jar_with_all_fields(self):
        test_step_config = (
            '--steps Type=Streaming,Name=StreamingStepAllFields,'
            'ActionOnFailure=CANCEL_AND_WAIT,' + STREAMING_ARGS)
        cmd = DEFAULT_CMD + test_step_config
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [
            {'Name': 'StreamingStepAllFields',
             'ActionOnFailure': 'CANCEL_AND_WAIT',
             'HadoopJarStep': STREAMING_HADOOP_JAR_STEP}
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_hive_step_with_default_fields(self):
        cmd = DEFAULT_CMD + (
            '--applications Name=Hive --steps Type=Hive,' + HIVE_BASIC_ARGS)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'Hive'}]
        result['Steps'] = [HIVE_DEFAULT_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_hive_step_missing_args(self):
        cmd = DEFAULT_CMD + '--applications Name=Hive --steps Type=Hive'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for HiveStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_hive_step_with_all_fields(self):
        test_step_config = (
            'Type=Hive,ActionOnFailure=CANCEL_AND_WAIT,'
            'Name=HiveBasicStep,' + HIVE_BASIC_ARGS)
        cmd = DEFAULT_CMD + (
            '--applications Name=Hive --steps ' + test_step_config)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [HIVE_STEP]
        result['Applications'] = [{'Name': 'Hive'}]
        self.assert_params_for_cmd(cmd, result)

    def test_pig_step_with_default_fields(self):
        cmd = DEFAULT_CMD + (
            '--applications Name=Pig --steps Type=Pig,' + PIG_BASIC_ARGS)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [PIG_DEFAULT_STEP]
        result['Applications'] = [{'Name': 'Pig'}]
        self.assert_params_for_cmd(cmd, result)

    def test_pig_missing_args(self):
        cmd = DEFAULT_CMD + '--applications Name=Pig --steps Type=Pig'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for PigStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expect_error_msg, result[1])

    def test_pig_step_with_all_fields(self):
        test_step_config = (
            'Name=PigBasicStep,Type=Pig,' + PIG_BASIC_ARGS +
            ',ActionOnFailure=CANCEL_AND_WAIT')
        cmd = DEFAULT_CMD + (
            '--applications Name=Pig --steps ' + test_step_config)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Applications'] = [{'Name': 'Pig'}]
        result['Steps'] = [PIG_STEP]
        self.assert_params_for_cmd(cmd, result)

    @mock.patch('awscli.customizations.emr.emrutils.call')
    def test_constructed_result(self, call_patch):
        call_patch.return_value = CREATE_CLUSTER_RESULT
        cmd = DEFAULT_CMD
        result = self.run_cmd(cmd, expected_rc=0)
        result_json = json.loads(result[0])
        self.assertEqual(result_json, CONSTRUCTED_RESULT)

    def test_all_security_groups(self):
        cmd = DEFAULT_CMD + (
            '--ec2-attributes EmrManagedMasterSecurityGroup=sg-master1,'
            'EmrManagedSlaveSecurityGroup=sg-slave1,'
            'ServiceAccessSecurityGroup=sg-service-access,'
            'AdditionalMasterSecurityGroups='
            '[sg-addMaster1,sg-addMaster2,sg-addMaster3,'
            'sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,'
            'sg-addSlave2,sg-addSlave3,sg-addSlave4]')

        result = copy.deepcopy(DEFAULT_RESULT)
        instances = result['Instances']
        instances['EmrManagedMasterSecurityGroup'] = \
            EMR_MANAGED_MASTER_SECURITY_GROUP
        instances['EmrManagedSlaveSecurityGroup'] = \
            EMR_MANAGED_SLAVE_SECURITY_GROUP
        instances['ServiceAccessSecurityGroup'] = \
            SERVICE_ACCESS_SECURITY_GROUP
        instances['AdditionalMasterSecurityGroups'] = \
            ADDITIONAL_MASTER_SECURITY_GROUPS
        instances['AdditionalSlaveSecurityGroups'] = \
            ADDITIONAL_SLAVE_SECURITY_GROUPS

        self.assert_params_for_cmd(cmd, result)

    def test_emr_managed_security_groups(self):
        cmd = DEFAULT_CMD + (
            '--ec2-attributes EmrManagedMasterSecurityGroup=sg-master1,'
            'EmrManagedSlaveSecurityGroup=sg-slave1,'
            'ServiceAccessSecurityGroup=sg-service-access')

        result = copy.deepcopy(DEFAULT_RESULT)
        instances = result['Instances']
        instances['EmrManagedMasterSecurityGroup'] = \
            EMR_MANAGED_MASTER_SECURITY_GROUP
        instances['EmrManagedSlaveSecurityGroup'] = \
            EMR_MANAGED_SLAVE_SECURITY_GROUP
        instances['ServiceAccessSecurityGroup'] = \
            SERVICE_ACCESS_SECURITY_GROUP

        self.assert_params_for_cmd(cmd, result)

    def test_additional_security_groups(self):
        cmd = DEFAULT_CMD + (
            '--ec2-attributes AdditionalMasterSecurityGroups=[sg-addMaster1'
            ',sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecu'
            'rityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4]')

        result = copy.deepcopy(DEFAULT_RESULT)
        instances = result['Instances']
        instances['AdditionalMasterSecurityGroups'] = \
            ADDITIONAL_MASTER_SECURITY_GROUPS
        instances['AdditionalSlaveSecurityGroups'] = \
            ADDITIONAL_SLAVE_SECURITY_GROUPS

        self.assert_params_for_cmd(cmd, result)

    def test_security_groups_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__),
            'input_ec2_attributes_with_security_groups.json')
        cmd = DEFAULT_CMD + '--ec2-attributes file://' + data_path

        result = copy.deepcopy(DEFAULT_RESULT)
        instances = result['Instances']
        instances['EmrManagedMasterSecurityGroup'] = \
            EMR_MANAGED_MASTER_SECURITY_GROUP
        instances['EmrManagedSlaveSecurityGroup'] = \
            EMR_MANAGED_SLAVE_SECURITY_GROUP
        instances['ServiceAccessSecurityGroup'] = \
            SERVICE_ACCESS_SECURITY_GROUP
        instances['AdditionalMasterSecurityGroups'] = \
            ADDITIONAL_MASTER_SECURITY_GROUPS
        instances['AdditionalSlaveSecurityGroups'] = \
            ADDITIONAL_SLAVE_SECURITY_GROUPS

        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_autoscaling_policy(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --auto-scaling-role EMR_AUTOSCALING_ROLE --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY
                              },
                'ReleaseLabel': 'emr-4.2.0',
                'AutoScalingRole': 'EMR_AUTOSCALING_ROLE',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_autoscaling_policy_missing_autoscaling_role(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY_ARG)
        expected_error_msg = (
            '\naws: error: Must specify --auto-scaling-role when'
            ' configuring an AutoScaling policy for an instance group.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_scale_down_behavior(self):
        cmd = (self.prefix + '--release-label emr-4.0.0 --scale-down-behavior TERMINATE_AT_INSTANCE_HOUR '
                             '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.0.0',
                'VisibleToAllUsers': True,
                'ScaleDownBehavior': 'TERMINATE_AT_INSTANCE_HOUR',
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_ebs_config(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_EBS
                              },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_volume_type(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLTYPE_ARG)
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'VolumeType')

    def test_instance_groups_with_ebs_config_missing_size(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_SIZE_ARG)
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'SizeInGB')

    def test_instance_groups_with_ebs_config_missing_volume_spec(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC
                              },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_iops(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS
                              },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_multiple_instance_groups(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-groups ' +
               CONSTANTS.MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES_VOLUME_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES
                              },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_on_demand_master_only(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_only_with_ebs_conf(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_specific_azs(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY +
               ' --ec2-attributes AvailabilityZones=[us-east-1a,us-east-1b]')
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY,
                              'Placement': {'AvailabilityZones': ['us-east-1a','us-east-1b']}
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_subnet_ids(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY +
               ' --ec2-attributes SubnetIds=[subnetid-1,subnetid-2]')
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY,
                              'Ec2SubnetIds': ['subnetid-1','subnetid-2']
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_core_cluster_multiple_instance_types(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_complex_config_from_json(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_fleets.json')
        cmd = ('emr create-cluster --use-default-roles --release-label emr-4.2.0  '
                '--instance-fleets file://' + data_path)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_COMPLEX_CONFIG_FROM_JSON
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'JobFlowRole': 'EMR_EC2_DefaultRole',
                'ServiceRole': 'EMR_DefaultRole'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_both_fleet_group_specified(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY +
               ' --instance-groups ' + CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG)
        expected_error_msg = (
            '\naws: error: You cannot specify both --instance-groups'
            ' and --instance-fleets options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_instance_fleets_with_both_subnetid_subnetids_specified(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY +
               ' --ec2-attributes SubnetId=subnetid-1,SubnetIds=[subnetid-1,subnetid-2]')
        expected_error_msg = (
            '\naws: error: You cannot specify both SubnetId'
            ' and SubnetIds options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_create_cluster_with_security_config(self):
        cmd = (self.prefix + '--release-label emr-4.7.2 --security-configuration MySecurityConfig '+
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.7.2',
                'VisibleToAllUsers': True,
                'Tags': [],
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_security_config_and_kerberos_attributes(self):
        cmd = (self.prefix + '--release-label emr-4.7.2 --security-configuration MySecurityConfig' +
               ' --kerberos-attributes ' + DEFAULT_KERBEROS_ATTRIBUTES_ARGS +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'KerberosAttributes': KERBEROS_ATTRIBUTES,
                'ReleaseLabel': 'emr-4.7.2',
                'VisibleToAllUsers': True,
                'Tags': [],
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_custom_ami_id(self):
        cmd = (self.prefix + '--release-label emr-4.7.2 --security-configuration MySecurityConfig '+
               ' --custom-ami-id ami-9be6f38c' +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.7.2',
                'VisibleToAllUsers': True,
                'Tags': [],
                'CustomAmiId': 'ami-9be6f38c',
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_ebs_root_volume_size(self):
        cmd = (self.prefix + '--release-label emr-4.7.2 --security-configuration MySecurityConfig '+
               ' --ebs-root-volume-size 50' +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.7.2',
                'VisibleToAllUsers': True,
                'Tags': [],
                'EbsRootVolumeSize': 50,
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_ebs_root_volume_iops(self):
        cmd = (self.prefix + '--release-label emr-6.15.0 --security-configuration MySecurityConfig '+
               ' --ebs-root-volume-iops 3000' +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-6.15.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'EbsRootVolumeIops': 3000,
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_ebs_root_volume_throughput(self):
        cmd = (self.prefix + '--release-label emr-6.15.0 --security-configuration MySecurityConfig '+
               ' --ebs-root-volume-throughput 125' +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
             {
                 'Name': DEFAULT_CLUSTER_NAME,
                 'Instances': DEFAULT_INSTANCES,
                 'ReleaseLabel': 'emr-6.15.0',
                 'VisibleToAllUsers': True,
                 'Tags': [],
                 'EbsRootVolumeThroughput': 125,
                 'SecurityConfiguration': 'MySecurityConfig'
             }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_repo_upgrade_on_boot(self):
        cmd = (self.prefix + '--release-label emr-4.7.2 --security-configuration MySecurityConfig '+
               ' --repo-upgrade-on-boot NONE' +
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-4.7.2',
                'VisibleToAllUsers': True,
                'Tags': [],
                'RepoUpgradeOnBoot': 'NONE',
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_step_concurrency_level(self):
        cmd = (self.prefix + '--release-label emr-5.28.0 --security-configuration MySecurityConfig ' +
               '--step-concurrency-level 30 ' +
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-5.28.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'StepConcurrencyLevel': 30,
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_managed_scaling_policy(self):
        cmd = (self.prefix + '--release-label emr-5.28.0 --security-configuration MySecurityConfig ' +
               '--managed-scaling-policy ComputeLimits={MinimumCapacityUnits=2,MaximumCapacityUnits=4,UnitType=Instances,MaximumCoreCapacityUnits=1} ' +
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-5.28.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'ManagedScalingPolicy': {
                   'ComputeLimits': {
                       'MinimumCapacityUnits': 2,
                       'MaximumCapacityUnits': 4,
                       'UnitType': 'Instances',
                       'MaximumCoreCapacityUnits': 1
                   }
                },
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_managed_scaling_policy_customer_knobs(self):
        cmd = (self.prefix + '--release-label emr-5.28.0 --security-configuration MySecurityConfig ' +
               '--managed-scaling-policy ComputeLimits={MinimumCapacityUnits=2,MaximumCapacityUnits=4,' +
               'UnitType=Instances,MaximumCoreCapacityUnits=1},ScalingStrategy=ADVANCED,' +
               'UtilizationPerformanceIndex=1 --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-5.28.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'ManagedScalingPolicy': {
                   'ComputeLimits': {
                       'MinimumCapacityUnits': 2,
                       'MaximumCapacityUnits': 4,
                       'UnitType': 'Instances',
                       'MaximumCoreCapacityUnits': 1
                   },
                   'ScalingStrategy': 'ADVANCED',
                   'UtilizationPerformanceIndex': 1,
                },
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_auto_termination_policy(self):
        cmd = (self.prefix + '--release-label emr-5.34.0 ' +
               '--auto-termination-policy IdleTimeout=100 ' +
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'ReleaseLabel': 'emr-5.34.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'AutoTerminationPolicy': {
                    'IdleTimeout': 100,
                }
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_log_encryption_kms_key_id(self):
        test_log_uri = 's3://test/logs'
        test_log_encryption_kms_key_id = 'valid_kms_key'
        cmd = (self.prefix + '--release-label emr-5.30.0 ' + '--log-uri '
                + test_log_uri + ' --log-encryption-kms-key-id '
                + test_log_encryption_kms_key_id
                + ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
             {
                  'Name': DEFAULT_CLUSTER_NAME,
                  'Instances': DEFAULT_INSTANCES,
                  'ReleaseLabel': 'emr-5.30.0',
                  'VisibleToAllUsers': True,
                  'Tags': [],
                  'LogUri': test_log_uri,
                  'LogEncryptionKmsKeyId': test_log_encryption_kms_key_id
             }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_placement_groups(self):
        cmd = (self.prefix + '--release-label emr-5.28.0 --security-configuration ' +
               'MySecurityConfig --placement-group-configs ' +
               'InstanceRole=MASTER,PlacementStrategy=SPREAD ' +
               '--instance-groups ' + HA_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': HA_INSTANCES,
                'ReleaseLabel': 'emr-5.28.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'PlacementGroupConfigs': [{
                    'InstanceRole': 'MASTER',
                    'PlacementStrategy': 'SPREAD'
                }],
                'SecurityConfiguration': 'MySecurityConfig'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_resize_allocation_strategy_spot_od(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD +
               ' --ec2-attributes AvailabilityZones=[us-east-1a,us-east-1b]')
        instance_fleets = CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                instance_fleets,
                              'Placement': {'AvailabilityZones': ['us-east-1a','us-east-1b']}
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_create_cluster_with_os_release_label(self):
        test_os_release_label = '2.0.20220406.1'
        cmd = (self.prefix + '--release-label emr-6.6.0'
                + ' --os-release-label ' + test_os_release_label
                + ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
             {
                  'Name': DEFAULT_CLUSTER_NAME,
                  'Instances': DEFAULT_INSTANCES,
                  'ReleaseLabel': 'emr-6.6.0',
                  'VisibleToAllUsers': True,
                  'Tags': [],
                  'OSReleaseLabel': test_os_release_label
             }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_allocation_strategy(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_ALLOCATION_STRATEGY +
               ' --ec2-attributes AvailabilityZones=[us-east-1a,us-east-1b]')
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_ALLOCATION_STRATEGY,
                              'Placement': {'AvailabilityZones': ['us-east-1a','us-east-1b']}
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_prioritized_allocation_strategy_spot_ondemand(self):
        cmd = (self.prefix + '--release-label emr-4.2.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_PRIORITIZED_ALLOCATION_STRATEGY_SPOT_AND_OD +
               ' --ec2-attributes AvailabilityZones=[us-east-1a,us-east-1b]')
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_PRIORITIZED_ALLOCATION_STRATEGY_SPOT_AND_OD,
                              'Placement': {'AvailabilityZones': ['us-east-1a','us-east-1b']}
                            },
                'ReleaseLabel': 'emr-4.2.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

if __name__ == "__main__":
    unittest.main()
