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
from tests.unit.customizations.emr import test_constants as \
    CONSTANTS
from tests.unit.customizations.emr import test_constants_instance_fleets as \
    CONSTANTS_FLEET
import copy
import os
import json
from mock import patch


DEFAULT_CLUSTER_NAME = "Development Cluster"

DEFAULT_INSTANCE_GROUPS_ARG = (
    'InstanceGroupType=MASTER,Name=MASTER,'
    'InstanceCount=1,InstanceType=m1.large '
    'InstanceGroupType=CORE,Name=CORE,'
    'InstanceCount=1,InstanceType=m1.large '
    'InstanceGroupType=TASK,Name=TASK,'
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

DEFAULT_CMD = ('emr create-cluster --ami-version 3.0.4 --use-default-roles'
               ' --instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG + ' ')

DEFAULT_INSTANCES = {'KeepJobFlowAliveWhenNoSteps': True,
                     'TerminationProtected': False,
                     'InstanceGroups': DEFAULT_INSTANCE_GROUPS
                     }

EC2_ROLE_NAME = "EMR_EC2_DefaultRole"
EMR_ROLE_NAME = "EMR_DefaultRole"

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

INSTALL_HIVE_STEP = {
    'HadoopJarStep': {
        'Args': ['s3://us-east-1.elasticmapreduce/libs/hive/hive-script',
                 '--install-hive', '--base-path',
                 's3://us-east-1.elasticmapreduce/libs/hive',
                 '--hive-versions', 'latest'],
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar')
    },
    'Name': 'Install Hive',
    'ActionOnFailure': 'TERMINATE_CLUSTER'
}

INSTALL_HIVE_SITE_STEP = {
    'HadoopJarStep': {
        'Args': ['s3://us-east-1.elasticmapreduce/libs/hive/hive-script',
                 '--base-path',
                 's3://us-east-1.elasticmapreduce/libs/hive',
                 '--install-hive-site',
                 '--hive-site=s3://test/hive-conf/hive-site.xml',
                 '--hive-versions', 'latest'],
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar')
    },
    'Name': 'Install Hive Site Configuration',
    'ActionOnFailure': 'CANCEL_AND_WAIT'
}

INSTALL_PIG_STEP = {
    'HadoopJarStep': {
        'Args': ['s3://us-east-1.elasticmapreduce/libs/pig/pig-script',
                 '--install-pig', '--base-path',
                 's3://us-east-1.elasticmapreduce/libs/pig',
                 '--pig-versions', 'latest'],
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar')
    },
    'Name': 'Install Pig',
    'ActionOnFailure': 'TERMINATE_CLUSTER'
}

INSTALL_HBASE_STEP = {
    'HadoopJarStep': {
        'Args': ['emr.hbase.backup.Main',
                 '--start-master'],
        'Jar': '/home/hadoop/lib/hbase.jar'
    },
    'Name': 'Start HBase',
    'ActionOnFailure': 'TERMINATE_CLUSTER'
}

INSTALL_GANGLIA_BA = {
    'ScriptBootstrapAction': {
        'Path':
            ('s3://us-east-1.elasticmapreduce/'
             'bootstrap-actions/install-ganglia')
    },
    'Name': 'Install Ganglia'
}

INSTALL_HBASE_BA = {
    'ScriptBootstrapAction': {
        'Path': 's3://us-east-1.elasticmapreduce/bootstrap-actions/setup-hbase'
    },
    'Name': 'Install HBase'
}

INSTALL_IMPALA_BA = {
    'ScriptBootstrapAction': {
        'Path': 's3://us-east-1.elasticmapreduce/libs/impala/setup-impala',
        'Args': ['--base-path', 's3://us-east-1.elasticmapreduce',
                 '--impala-version', 'latest']
    },
    'Name': 'Install Impala'
}

INSTALL_MAPR_PRODUCT = {
    'Name': 'mapr',
    'Args': ['--edition', 'm5', '--version', '3.0.2']
}

INSTALL_SUPPORTED_PRODUCTS = [
    {
        'Name': 'hue',
        'Args': ['--hue-config', 's3://elasticmapreduce/hue-config']
    },
    {
        'Name': 'mapr',
        'Args': ['--edition', 'm7']
    },
    {
        'Name': 'unknown',
        'Args': ['arg1', 'k1=v1']
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
    'Jar': '/home/hadoop/contrib/streaming/hadoop-streaming.jar',
    'Args': [
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

HIVE_BASIC_ARGS = (
    'Args=-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q')

HIVE_DEFAULT_STEP = {
    'Name': 'Hive program',
    'ActionOnFailure': 'CONTINUE',
    'HadoopJarStep': {
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
        'Args': [
            's3://us-east-1.elasticmapreduce/libs/hive/hive-script',
            '--run-hive-script',
            '--hive-versions',
            'latest',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/hive-ads/libs/model-build.q']}
}

HIVE_BASIC_STEP = {
    'Name': 'HiveBasicStep',
    'ActionOnFailure': 'CANCEL_AND_WAIT',
    'HadoopJarStep': {
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
        'Args': [
            's3://us-east-1.elasticmapreduce/libs/hive/hive-script',
            '--run-hive-script',
            '--hive-versions',
            'latest',
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
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
        'Args': [
            's3://us-east-1.elasticmapreduce/libs/pig/pig-script',
            '--run-pig-script',
            '--pig-versions',
            'latest',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/'
            'pig-apache/do-reports2.pig']}
}

PIG_BASIC_STEP = {
    'Name': 'PigBasicStep',
    'ActionOnFailure': 'CANCEL_AND_WAIT',
    'HadoopJarStep': {
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
        'Args': [
            's3://us-east-1.elasticmapreduce/libs/pig/pig-script',
            '--run-pig-script',
            '--pig-versions',
            'latest',
            '--args',
            '-f',
            's3://elasticmapreduce/samples/'
            'pig-apache/do-reports2.pig']}
}
IMPALA_BASIC_ARGS = (
    'Args=--impala-script,s3://myimpala/input,'
    '--console-output-path,s3://myimpala/output')

IMPALA_DEFAULT_STEP = {
    'Name': 'Impala program',
    'ActionOnFailure': 'CONTINUE',
    'HadoopJarStep': {
        'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
        'Args': [
            's3://us-east-1.elasticmapreduce/libs/impala/setup-impala',
            '--run-impala-script',
            '--impala-script',
            's3://myimpala/input',
            '--console-output-path',
            's3://myimpala/output']}
}

CREATE_CLUSTER_RESULT = {
    "JobFlowId": "j-XXXX"
}

CONSTRUCTED_RESULT = {
    "ClusterId": "j-XXXX"
}

DEFAULT_RESULT = \
    {
        'Name': DEFAULT_CLUSTER_NAME,
        'Instances': DEFAULT_INSTANCES,
        'AmiVersion': '3.0.4',
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


class TestCreateCluster(BaseAWSCommandParamsTest):
    prefix = 'emr create-cluster '

    def test_quick_start(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'AmiVersion': '3.1.0',
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
        cmd = ('emr create-cluster --ami-version 3.0.4 '
               '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = copy.deepcopy(DEFAULT_RESULT)
        del result['JobFlowRole']
        del result['ServiceRole']
        self.assert_params_for_cmd(cmd, result)

    def test_cluster_with_service_role_and_instance_profile(self):
        cmd = ('emr create-cluster --ami-version 3.0.4'
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
        self.assertEquals(expected_error_msg, result[1])

    def test_mutual_exclusive_use_default_roles_and_instance_profile(self):
        cmd = (DEFAULT_CMD + '--service-role ServiceRole '
               '--ec2-attributes InstanceProfile=Ec2_InstanceProfile')
        expected_error_msg = (
            '\naws: error: You cannot specify both --use-default-roles '
            'and --service-role options together. Either choose '
            '--use-default-roles or use both --service-role <roleName> '
            'and --ec2-attributes InstanceProfile=<profileName>.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

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
        cmd = DEFAULT_CMD + '--ami-version 3.0.4'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['AmiVersion'] = '3.0.4'
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
        cmd = ('emr create-cluster --use-default-roles --ami-version 3.0.4 '
               '--auto-terminate --instance-groups ' +
               DEFAULT_INSTANCE_GROUPS_ARG)
        result = copy.deepcopy(DEFAULT_RESULT)
        instances = copy.deepcopy(DEFAULT_INSTANCES)
        instances['KeepJobFlowAliveWhenNoSteps'] = False
        result['Instances'] = instances
        self.assert_params_for_cmd(cmd, result)

    def test_auto_terminate_and_no_auto_terminate(self):
        cmd = (DEFAULT_CMD + '--ami-version 3.0.4 ' +
               '--auto-terminate --no-auto-terminate')
        expected_error_msg = (
            '\naws: error: cannot use both --no-auto-terminate and'
            ' --auto-terminate options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

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
        self.assertEquals(expected_error_msg, result[1])

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
        self.assertEquals(expected_error_msg, result[1])

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
                {'Args':
                    [('s3://us-east-1.elasticmapreduce/libs/'
                      'state-pusher/0.1/fetch')],
                 'Jar':
                    's3://us-east-1.elasticmapreduce/libs/' +
                    'script-runner/script-runner.jar'
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
                {'Args':
                    [('s3://us-west-2.elasticmapreduce/libs/'
                      'state-pusher/0.1/fetch')],
                 'Jar':
                    's3://us-west-2.elasticmapreduce/libs/' +
                    'script-runner/script-runner.jar'
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
        self.assertEquals(expected_error_msg, result[1])

    def test_enable_debugging_and_no_enable_debugging(self):
        cmd = DEFAULT_CMD + '--enable-debugging --no-enable-debugging' + \
            ' --log-uri s3://test/logs'
        expected_error_msg = (
            '\naws: error: cannot use both --enable-debugging and '
            '--no-enable-debugging options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

    def test_instance_groups_default_name_market(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--instance-groups '
            'InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m1.large '
            'InstanceGroupType=CORE,InstanceCount=1,InstanceType=m1.large '
            'InstanceGroupType=TASK,InstanceCount=1,InstanceType=m1.large ')
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_instance_groups_instance_group_type_mismatch_cases(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--instance-groups '
            'Name=MASTER,InstanceGroupType=MaSter,InstanceCount=1,'
            'InstanceType=m1.large Name=CORE,InstanceGroupType=cORE,'
            'InstanceCount=1,InstanceType=m1.large Name=TASK,'
            'InstanceGroupType=tAsK,InstanceCount=1,InstanceType=m1.large')
        self.assert_params_for_cmd(cmd, DEFAULT_RESULT)

    def test_instance_groups_instance_type_and_count(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
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
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
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
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 ')
        expect_error_msg = (
            '\naws: error: Must specify either --instance-groups or '
            '--instance-type with --instance-count(optional) to '
            'configure instance groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--instance-count 2')
        expect_error_msg = (
            '\naws: error: Must specify either --instance-groups or '
            '--instance-type with --instance-count(optional) to '
            'configure instance groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_instance_groups_exclusive_parameter_validation_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--instance-type m1.large --instance-groups ' +
            DEFAULT_INSTANCE_GROUPS_ARG)
        expect_error_msg = (
            '\naws: error: You may not specify --instance-type '
            'or --instance-count with --instance-groups, '
            'because --instance-type and --instance-count are '
            'shortcut options for --instance-groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--instance-type m1.large --instance-count 2 '
            '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        expect_error_msg = (
            '\naws: error: You may not specify --instance-type '
            'or --instance-count with --instance-groups, '
            'because --instance-type and --instance-count are '
            'shortcut options for --instance-groups.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_instance_groups_missing_instance_group_type_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--auto-terminate '
            '--instance-groups '
            'Name=Master,InstanceCount=1,InstanceType=m1.small')
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceGroupType')

    def test_instance_groups_missing_instance_type_error(self):
        cmd = (
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
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
            'emr create-cluster --use-default-roles --ami-version 3.0.4 '
            '--auto-terminate '
            '--instance-groups '
            'Name=Master,InstanceGroupType=MASTER,InstanceType=m1.xlarge')
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'InstanceCount')

    def test_instance_groups_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_groups.json')
        cmd = ('emr create-cluster --use-default-roles --ami-version 3.0.4  '
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
        cmd = ('emr create-cluster --use-default-roles --ami-version 3.0.4  '
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

    def test_ec2_attributes_no_az(self):
        cmd = ('emr create-cluster --ami-version 3.0.4 '
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
        self.assertEquals(expect_error_msg, result[1])

    def test_ec2_attributes_with_subnet_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_ec2_attributes_with_subnet.json')
        cmd = ('emr create-cluster --ami-version 3.0.4 '
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
        cmd = ('emr create-cluster --ami-version 3.0.4 '
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

        self.assertEquals(expected_error_msg, result[1])

    def test_bootstrap_actions_exceed_maximum_with_applications_error(self):
        cmd = DEFAULT_CMD + ' --applications Name=GANGLIA Name=HBASE' +\
            ' Name=IMPALA,Args=arg1,arg2 --bootstrap-actions'
        ba_cmd = ' Path=s3://test/ba1,Name=ba1,Args=arg1,arg2,arg3'
        for i in range(1, 15):
            cmd += ba_cmd
        expected_error_msg = '\naws: error: maximum number of ' +\
                             'bootstrap actions for a cluster exceeded.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

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

    # Applications test cases
    def test_install_hive_with_defaults(self):
        cmd = DEFAULT_CMD + '--applications Name=Hive'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [INSTALL_HIVE_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_install_hive_with_profile_region(self):
        self.driver.session.set_config_variable('region', 'cn-north-1')
        cmd = DEFAULT_CMD + '--applications Name=Hive'
        HIVE_STEP = json.dumps(INSTALL_HIVE_STEP).\
            replace('us-east-1', 'cn-north-1')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [json.loads(HIVE_STEP)]
        self.assert_params_for_cmd(cmd, result)

    def test_install_hive_site(self):
        cmdline = (DEFAULT_CMD + '--applications Name=Hive,'
                   'Args=[--hive-site=s3://test/hive-conf/hive-site.xml]')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [INSTALL_HIVE_STEP, INSTALL_HIVE_SITE_STEP]
        self.assert_params_for_cmd(cmdline, result)
        cmdline = (DEFAULT_CMD + '--applications Name=Hive,'
                   'Args=[--hive-site=s3://test/hive-conf/hive-site.xml,k1]')
        self.assert_params_for_cmd(cmdline, result)

    def test_install_pig_with_defaults(self):
        cmd = DEFAULT_CMD + '--applications Name=Pig'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [INSTALL_PIG_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_install_ganglia(self):
        cmd = DEFAULT_CMD + '--applications Name=Ganglia'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_GANGLIA_BA]
        self.assert_params_for_cmd(cmd, result)

    def test_install_impala_with_defaults(self):
        cmd = DEFAULT_CMD + '--applications Name=Impala'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_IMPALA_BA]
        self.assert_params_for_cmd(cmd, result)

    def test_install_impala_with_all_fields(self):
        cmd = DEFAULT_CMD + \
            '--applications Name=Impala,Args=arg1,arg2'
        result = copy.deepcopy(DEFAULT_RESULT)
        ba = copy.deepcopy(INSTALL_IMPALA_BA)
        ba['ScriptBootstrapAction']['Args'] += \
            ['--impala-conf', 'arg1,arg2']
        result['BootstrapActions'] = [ba]
        self.assert_params_for_cmd(cmd, result)

    def test_install_hbase(self):
        cmd = DEFAULT_CMD + '--applications Name=hbase'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_HBASE_BA]
        result['Steps'] = [INSTALL_HBASE_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_install_mapr_with_args(self):
        cmd = DEFAULT_CMD + \
            '--applications Name=mapr,Args=--edition,m5,--version,3.0.2'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['NewSupportedProducts'] = [INSTALL_MAPR_PRODUCT]
        self.assert_params_for_cmd(cmd, result)

    def test_install_mapr_without_args(self):
        cmd = DEFAULT_CMD + \
            '--applications Name=mapr'
        result = copy.deepcopy(DEFAULT_RESULT)
        result['NewSupportedProducts'] =  \
            [
                {'Name': 'mapr',
                 'Args': []}
        ]
        self.assert_params_for_cmd(cmd, result)

    def test_supported_products(self):
        cmd = DEFAULT_CMD + (
            '--applications '
            'Name=hue,Args=--hue-config,s3://elasticmapreduce/hue-config '
            'Name=mapr,Args=--edition,m7 '
            'Name=unknown,Args=[arg1,k1=v1]')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['NewSupportedProducts'] = INSTALL_SUPPORTED_PRODUCTS
        self.assert_params_for_cmd(cmd, result)

    def test_applications_all_types(self):
        cmd = DEFAULT_CMD + (
            '--applications '
            'Name=hive Name=pig Name=ganglia Name=hbase Name=impala '
            'Name=mapr,Args=--edition,m5,--version,3.0.2')
        ba_list = [INSTALL_GANGLIA_BA, INSTALL_HBASE_BA,
                   INSTALL_IMPALA_BA]
        step_list = [INSTALL_HIVE_STEP, INSTALL_PIG_STEP, INSTALL_HBASE_STEP]
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = step_list
        result['BootstrapActions'] = ba_list
        result['NewSupportedProducts'] = [INSTALL_MAPR_PRODUCT]
        self.assert_params_for_cmd(cmd, result)

    def test_applications_all_types_from_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_applications.json')
        cmd = DEFAULT_CMD + '--applications file://' + data_path
        impala_ba = copy.deepcopy(INSTALL_IMPALA_BA)
        impala_ba['ScriptBootstrapAction']['Args'] += \
            ['--impala-conf',
             'IMPALA_BACKEND_PORT=22001,IMPALA_MEM_LIMIT=70%']
        ba_list = [INSTALL_GANGLIA_BA, INSTALL_HBASE_BA,
                   impala_ba]
        step_list = [INSTALL_HIVE_STEP, INSTALL_PIG_STEP, INSTALL_HBASE_STEP]
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = step_list
        result['BootstrapActions'] = ba_list
        result['NewSupportedProducts'] = [INSTALL_MAPR_PRODUCT]
        self.assert_params_for_cmd(cmd, result)

    # Steps test cases
    def test_wrong_step_type_error(self):
        cmd = DEFAULT_CMD + '--steps Type=unknown'
        expected_error_msg = (
            '\naws: error: The step type unknown is not supported.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

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
        self.assertEquals(expect_error_msg, result[1])

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
        self.assertEquals(expect_error_msg, result[1])

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
        result['Steps'] = [INSTALL_HIVE_STEP, HIVE_DEFAULT_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_hive_step_missing_args(self):
        cmd = DEFAULT_CMD + '--applications Name=Hive --steps Type=Hive'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for HiveStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_hive_step_with_all_fields(self):
        test_step_config = (
            'Type=Hive,ActionOnFailure=CANCEL_AND_WAIT,'
            'Name=HiveBasicStep,' + HIVE_BASIC_ARGS)
        cmd = DEFAULT_CMD + (
            '--applications Name=Hive --steps ' + test_step_config)
        result = copy.deepcopy(DEFAULT_RESULT)
        install_step = copy.deepcopy(INSTALL_HIVE_STEP)
        result['Steps'] = [install_step, HIVE_BASIC_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_pig_step_with_default_fields(self):
        cmd = DEFAULT_CMD + (
            '--applications Name=Pig --steps Type=Pig,' + PIG_BASIC_ARGS)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['Steps'] = [INSTALL_PIG_STEP, PIG_DEFAULT_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_pig_missing_args(self):
        cmd = DEFAULT_CMD + '--applications Name=Pig --steps Type=Pig'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for PigStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_pig_step_with_all_fields(self):
        test_step_config = (
            'Name=PigBasicStep,Type=Pig,' + PIG_BASIC_ARGS +
            ',ActionOnFailure=CANCEL_AND_WAIT')
        cmd = DEFAULT_CMD + (
            '--applications Name=Pig --steps ' + test_step_config)
        result = copy.deepcopy(DEFAULT_RESULT)
        install_step = copy.deepcopy(INSTALL_PIG_STEP)
        result['Steps'] = [install_step, PIG_BASIC_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_impala_step_with_default_fields(self):
        cmd = DEFAULT_CMD + (
            '--applications Name=Impala --steps Type=Impala,' +
            IMPALA_BASIC_ARGS)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_IMPALA_BA]
        result['Steps'] = [IMPALA_DEFAULT_STEP]
        self.assert_params_for_cmd(cmd, result)

    def test_impala_missing_args(self):
        cmd = DEFAULT_CMD + '--applications Name=Impala --steps Type=Impala'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for ImpalaStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_impala_step_with_all_fields(self):
        test_step_config = (
            'Name=ImpalaBasicStep,Type=Impala,' + IMPALA_BASIC_ARGS +
            ',ActionOnFailure=CANCEL_AND_WAIT')
        cmd = DEFAULT_CMD + (
            '--applications Name=Impala --steps ' + test_step_config)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_IMPALA_BA]
        step = copy.deepcopy(IMPALA_DEFAULT_STEP)
        step['Name'] = 'ImpalaBasicStep'
        step['ActionOnFailure'] = 'CANCEL_AND_WAIT'
        result['Steps'] = [step]
        self.assert_params_for_cmd(cmd, result)

    def test_restore_from_hbase(self):
        cmd = DEFAULT_CMD + (
            '--applications Name=hbase --restore-from-hbase-backup '
            'Dir=s3://mybucket/test,BackupVersion=test_version')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [INSTALL_HBASE_BA]
        result['Steps'] = [
            INSTALL_HBASE_STEP,
            {
                'Name': 'Restore HBase',
                'ActionOnFailure': 'CANCEL_AND_WAIT',
                'HadoopJarStep': {
                    'Args': [
                        'emr.hbase.backup.Main',
                        '--restore',
                        '--backup-dir',
                        's3://mybucket/test',
                        '--backup-version',
                        'test_version'],
                    'Jar': '/home/hadoop/lib/hbase.jar'}
            }
        ]
        self.assert_params_for_cmd(cmd, result)
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_hbase_restore_from_backup.json')
        cmd = DEFAULT_CMD + (
            '--applications Name=hbase --restore-from-hbase-backup '
            'file://' + data_path)
        self.assert_params_for_cmd(cmd, result)

    def test_empty_step_args(self):
        cmd = DEFAULT_CMD + '--steps Type=Streaming,Args= '
        expect_error_msg = ('\naws: error: The prameter Args cannot '
                            'be an empty list.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = DEFAULT_CMD + '--steps Type=Pig,Args= '
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = DEFAULT_CMD + '--steps Type=Hive,Args= '
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = DEFAULT_CMD + '--steps Args= '
        expect_error_msg = ('\naws: error: The following required parameters '
                            'are missing for CustomJARStepConfig: Jar.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_missing_applications_for_steps(self):
        cmd = DEFAULT_CMD +\
            '--steps Jar=s3://test/customJar.jar ' +\
            'Type=HIVE,Args=-f,s3://test/hive ' +\
            'Type=PIG,Args=-f,s3://test/pig ' +\
            'Type=IMPALA,Args=--impala-script,s3://test/impala ' +\
            'Type=Streaming,Args=-files,s3://test/mapper.py,-mapper,' +\
            'mapper.py,-reducer,aggregator,-input,s3://test/input,-output,' +\
            's3://test/output ' +\
            'Type=PIG,Args=-f,s3://test/pig2 ' +\
            'Type=IMPALA,Args=--impala-script,s3://test/impala2 ' +\
            'Type=PIG,Args=-f,s3://test/pig3 ' +\
            ' Jar=s3://test/customJar2.jar ' +\
            ' --applications Name=Hive'

        expected_error_msg1 = (
            '\naws: error: Some of the steps require the following'
            ' applications to be installed: Impala, Pig. '
            'Please install the applications using --applications.\n')
        expected_error_msg2 = (
            '\naws: error: Some of the steps require the following'
            ' applications to be installed: Pig, Impala. '
            'Please install the applications using --applications.\n')
        result = self.run_cmd(cmd, 255)

        if(result[1] == expected_error_msg1 or
           result[1] == expected_error_msg2):
            self.assertTrue(True)
        else:
            self.assertTrue(False)

    def test_missing_applications_with_hbase(self):
        cmd = DEFAULT_CMD +\
            '--steps Jar=s3://test/customJar.jar ' +\
            'Type=HIVE,Args=-f,s3://test/hive ' +\
            'Type=PIG,Args=-f,s3://test/pig ' +\
            'Type=IMPALA,Args=--impala-script,s3://test/impala ' +\
            'Type=Streaming,Args=-files,s3://test/mapper.py,-mapper,' +\
            'mapper.py,-reducer,aggregator,-input,s3://test/input,-output,' +\
            's3://test/output' + ' --applications Name=Hive Name=Pig' +\
            ' --restore-from-hbase-backup Dir=s3://myBucket/myDir'

        expected_error_msg1 = (
            '\naws: error: Some of the steps require the following'
            ' applications to be installed: Hbase, Impala. '
            'Please install the applications using --applications.\n')
        expected_error_msg2 = (
            '\naws: error: Some of the steps require the following'
            ' applications to be installed: Impala, Hbase. '
            'Please install the applications using --applications.\n')
        result = self.run_cmd(cmd, 255)

        if(result[1] == expected_error_msg1 or
           result[1] == expected_error_msg2):
            self.assertTrue(True)
        else:
            self.assertTrue(False)

    @patch('awscli.customizations.emr.emrutils.call')
    def test_constructed_result(self, call_patch):
        call_patch.return_value = CREATE_CLUSTER_RESULT
        cmd = DEFAULT_CMD
        result = self.run_cmd(cmd, expected_rc=0)
        result_json = json.loads(result[0])
        self.assertEquals(result_json, CONSTRUCTED_RESULT)

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
        instances['AdditionalMasterSecurityGroups'] = \
            ADDITIONAL_MASTER_SECURITY_GROUPS
        instances['ServiceAccessSecurityGroup'] = \
            SERVICE_ACCESS_SECURITY_GROUP
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
        cmd = (self.prefix + '--ami-version 3.1.0 --auto-scaling-role EMR_AUTOSCALING_ROLE --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY
                              },
                'AmiVersion': '3.1.0',
                'AutoScalingRole': 'EMR_AUTOSCALING_ROLE',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_autoscaling_policy_missing_autoscaling_role(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_AUTOSCALING_POLICY_ARG)
        expected_error_msg = (
            '\naws: error: Must specify --auto-scaling-role when'
            ' configuring an AutoScaling policy for an instance group.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

    def test_scale_down_behavior(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --scale-down-behavior TERMINATE_AT_TASK_COMPLETION '
                             '--instance-groups ' + DEFAULT_INSTANCE_GROUPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': DEFAULT_INSTANCES,
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'ScaleDownBehavior': 'TERMINATE_AT_TASK_COMPLETION',
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_ebs_config(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups':
                                                CONSTANTS.INSTANCE_GROUPS_WITH_EBS
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_volume_type(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLTYPE_ARG)
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'VolumeType')

    def test_instance_groups_with_ebs_config_missing_size(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_SIZE_ARG)
        stderr = self.run_cmd(cmd, 255)[1]
        self.assert_error_message_has_field_name(stderr, 'SizeInGB')

    def test_instance_groups_with_ebs_config_missing_volume_spec(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC
                                      },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_missing_iops(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS
                             },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_groups_with_ebs_config_multiple_instance_groups(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-groups ' +
               CONSTANTS.MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES_VOLUME_ARG)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceGroups': CONSTANTS.MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES
                             },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_group_with_ebs_config_from_json(self):
           data_path = os.path.join(
               os.path.dirname(__file__), 'input_instance_groups_ebs_config.json')
           cmd = ('emr create-cluster --use-default-roles --ami-version 3.0.4  '
                  '--instance-groups file://' + data_path)
           result = copy.deepcopy(DEFAULT_RESULT)
           result['Instances']['InstanceGroups'] = \
               [
                   {'InstanceRole': 'MASTER',
                    'InstanceCount': 1,
                    'Name': 'Master Instance Group',
                    'Market': 'ON_DEMAND',
                    'InstanceType': 'd2.xlarge',
                    'EbsConfiguration':
                   {'EbsBlockDeviceConfigs':
                         [
                           {'VolumeSpecification':
                            {'VolumeType': 'standard',
                            'SizeInGB': 10},
                            'VolumesPerInstance': 4
                            }
                         ],
                        'EbsOptimized': True}
                    },
                   {'InstanceRole': 'CORE',
                    'InstanceCount': 2,
                    'Name': 'Core Instance Group',
                    'Market': 'ON_DEMAND',
                    'InstanceType': 'd2.xlarge'
                    },
                   {'InstanceRole': 'TASK',
                    'InstanceCount': 3,
                    'Name': 'Task Instance Group',
                    'Market': 'SPOT',
                    'BidPrice': '3.45',
                    'InstanceType': 'd2.xlarge'
                    }
           ]
           self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_on_demand_master_only(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_only(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_only_with_ebs_conf(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_specific_azs(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
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
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_subnet_ids(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
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
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_spot_master_core_cluster_multiple_instance_types(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': []
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_complex_config_from_json(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_instance_fleets.json')
        cmd = ('emr create-cluster --use-default-roles --ami-version 3.1.0  '
                '--instance-fleets file://' + data_path)
        result = \
            {
                'Name': DEFAULT_CLUSTER_NAME,
                'Instances': {'KeepJobFlowAliveWhenNoSteps': True,
                              'TerminationProtected': False,
                              'InstanceFleets':
                                                CONSTANTS_FLEET.RES_INSTANCE_FLEETS_WITH_COMPLEX_CONFIG_FROM_JSON
                            },
                'AmiVersion': '3.1.0',
                'VisibleToAllUsers': True,
                'Tags': [],
                'JobFlowRole': 'EMR_EC2_DefaultRole',
                'ServiceRole': 'EMR_DefaultRole'
            }
        self.assert_params_for_cmd(cmd, result)

    def test_instance_fleets_with_both_az_azs_specified(self):
        cmd = (self.prefix + '--ami-version 3.1.0 --instance-fleets ' +
               CONSTANTS_FLEET.INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY +
               ' --ec2-attributes AvailabilityZone=us-east-1a,AvailabilityZones=[us-east-1a,us-east-1b]')
        expected_error_msg = (
            '\naws: error: You cannot specify both AvailabilityZone'
            ' and AvailabilityZones options together.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expected_error_msg, result[1])

if __name__ == "__main__":
    unittest.main()
