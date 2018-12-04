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

import os
import copy
import mock

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


class TestAddSteps(BaseAWSCommandParamsTest):
    prefix = 'emr add-steps --cluster-id j-ABC --steps '

    STREAMING_ARGS = 'Args=-files,' + \
        's3://elasticmapreduce/samples/wordcount/wordSplitter.py,' + \
        '-mapper,wordSplitter.py,' + \
        '-reducer,aggregate,' + \
        '-input,s3://elasticmapreduce/samples/wordcount/input,' + \
        '-output,s3://mybucket/wordcount/output/2014-04-18/12-15-24'
    STREAMING_HADOOP_SCRIPT_RUNNER_STEP = \
        {'Jar': '/home/hadoop/contrib/streaming/hadoop-streaming.jar',
         'Args':
            ['-files',
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
    STREAMING_HADOOP_COMMAND_RUNNER_STEP = \
        {'Jar': 'command-runner.jar',
         'Args':
            ['hadoop-streaming',
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

    HIVE_BASIC_ARGS = 'Args=-f,' + \
        's3://elasticmapreduce/samples/hive-ads/libs/model-build.q'

    HIVE_DEFAULT_SCRIPT_RUNNER_STEP = \
        {'Jar':
            ('s3://us-east-1.elasticmapreduce/'
             'libs/script-runner/script-runner.jar'),
         'Args':
            ['s3://us-east-1.elasticmapreduce/libs/hive/hive-script',
             '--run-hive-script',
             '--hive-versions',
             'latest',
             '--args',
             '-f',
             's3://elasticmapreduce/samples/hive-ads/libs/model-build.q'
             ]
         }

    HIVE_DEFAULT_COMMAND_RUNNER_STEP = \
        {'Jar':
            ('command-runner.jar'),
         'Args':
            ['hive-script',
             '--run-hive-script',
             '--args',
             '-f',
             's3://elasticmapreduce/samples/hive-ads/libs/model-build.q'
             ]
         }

    PIG_BASIC_ARGS = 'Args=-f,' + \
        's3://elasticmapreduce/samples/pig-apache/do-reports2.pig'

    PIG_DEFAULT_SCRIPT_RUNNER_STEP = \
        {'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
         'Args':
            ['s3://us-east-1.elasticmapreduce/libs/pig/pig-script',
             '--run-pig-script',
             '--pig-versions',
             'latest',
             '--args',
             '-f',
             's3://elasticmapreduce/samples/'
             'pig-apache/do-reports2.pig',
             ]}

    PIG_DEFAULT_COMMAND_RUNNER_STEP = \
        {'Jar':
            ('command-runner.jar'),
         'Args':
            ['pig-script',
             '--run-pig-script',
             '--args',
             '-f',
             's3://elasticmapreduce/samples/'
             'pig-apache/do-reports2.pig',
             ]}

    IMPALA_BASIC_ARGS = 'Args=' + \
        '--impala-script,s3://myimpala/input,' + \
        '--console-output-path,s3://myimpala/output'

    IMPALA_BASIC_SCRIPT_RUNNER_STEP = \
        {'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
         'Args':
            ['s3://us-east-1.elasticmapreduce/libs/impala/setup-impala',
             '--run-impala-script',
             '--impala-script',
             's3://myimpala/input',
             '--console-output-path',
             's3://myimpala/output'
             ]
         }

    SPARK_SUBMIT_BASIC_ARGS = 'Args=' + \
        '[--deploy-mode,' + \
        'cluster,' + \
        '--conf,' + \
        'k1=v1,' + \
        's3://mybucket/myfolder/app.jar,' + \
        'k2=v2]'

    SPARK_SUBMIT_SCRIPT_RUNNER_STEP = \
        {
            'Jar':
            ('s3://us-east-1.elasticmapreduce/libs/'
             'script-runner/script-runner.jar'),
            'Args':
            ['/home/hadoop/spark/bin/spark-submit',
             '--deploy-mode',
             'cluster',
             '--conf',
             'k1=v1',
             's3://mybucket/myfolder/app.jar',
             'k2=v2'
             ]
        }

    SPARK_SUBMIT_COMMAND_RUNNER_STEP = \
        {
            'Jar': 'command-runner.jar',
            'Args':
            ['spark-submit',
             '--deploy-mode',
             'cluster',
             '--conf',
             'k1=v1',
             's3://mybucket/myfolder/app.jar',
             'k2=v2'
             ]
        }

    def test_unknown_step_type(self):
        cmd = self.prefix + 'Type=unknown'
        expected_error_msg = '\naws: error: ' + \
            'The step type unknown is not supported.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_default_step_type_name_action_on_failure(self):
        cmd = self.prefix + 'Jar=s3://mybucket/mytest.jar'
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 }
            ]
        }

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result)

    def test_custom_jar_step_missing_jar(self):
        cmd = self.prefix + 'Name=CustomJarMissingJar'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for CustomJARStepConfig: Jar.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_custom_jar_step_with_all_fields(self):
        cmd = self.prefix + (
            'Name=Custom,Type=Custom_jar,'
            'Jar=s3://mybucket/mytest.jar,'
            'Args=arg1,arg2,MainClass=mymainclass,'
            'ActionOnFailure=TERMINATE_CLUSTER,'
            'Properties=k1=v1\,k2=v2\,k3')
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom',
                 'ActionOnFailure': 'TERMINATE_CLUSTER',
                 'HadoopJarStep':
                    {'Jar': 's3://mybucket/mytest.jar',
                     'Args': ['arg1', 'arg2'],
                     'MainClass': 'mymainclass',
                     'Properties':
                        [{'Key': 'k1', 'Value': 'v1'},
                         {'Key': 'k2', 'Value': 'v2'},
                         {'Key': 'k3', 'Value': ''}
                         ]
                     }
                 }
            ]
        }

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result)

    def test_streaming_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Streaming,' + self.STREAMING_ARGS
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Streaming program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.STREAMING_HADOOP_SCRIPT_RUNNER_STEP
                 }
            ]
        }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.STREAMING_HADOOP_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_streaming_step_missing_args(self):
        cmd = self.prefix + 'Type=Streaming'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for StreamingStepConfig: Args.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_streaming_jar_with_all_fields(self):
        test_step_config = 'Type=Streaming,' + \
            'Name=StreamingStepAllFields,' + \
            'ActionOnFailure=CANCEL_AND_WAIT,' + \
            self.STREAMING_ARGS
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'StreamingStepAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.STREAMING_HADOOP_SCRIPT_RUNNER_STEP
                 }
            ]
        }

        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.STREAMING_HADOOP_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_hive_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Hive,' + self.HIVE_BASIC_ARGS
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Hive program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.HIVE_DEFAULT_SCRIPT_RUNNER_STEP
                 }]
            }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.HIVE_DEFAULT_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_hive_step_missing_args(self):
        cmd = self.prefix + 'Type=Hive'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for HiveStepConfig: Args.\n'

        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_hive_step_with_all_fields(self):
        test_step_config = \
            'Type=Hive,' + \
            'ActionOnFailure=CANCEL_AND_WAIT,' + \
            'Name=HiveWithAllFields,' + \
            self.HIVE_BASIC_ARGS
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'HiveWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.HIVE_DEFAULT_SCRIPT_RUNNER_STEP
                 }]
        }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.HIVE_DEFAULT_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_pig_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Pig,' + self.PIG_BASIC_ARGS
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Pig program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.PIG_DEFAULT_SCRIPT_RUNNER_STEP
                 }]
        }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.PIG_DEFAULT_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_pig_missing_args(self):
        cmd = self.prefix + 'Type=Pig'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for PigStepConfig: Args.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_pig_step_with_all_fields(self):
        test_step_config = \
            'Name=PigWithAllFields,' + \
            'Type=Pig,' + \
            self.PIG_BASIC_ARGS + ',' + \
            'ActionOnFailure=CANCEL_AND_WAIT'
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'PigWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.PIG_DEFAULT_SCRIPT_RUNNER_STEP
                 }
            ]
        }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.PIG_DEFAULT_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_impala_step_with_default_fields(self):
        test_step_config = 'Type=Impala,' + \
            self.IMPALA_BASIC_ARGS
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Impala program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.IMPALA_BASIC_SCRIPT_RUNNER_STEP
                 }]
        }
        self.assert_params_for_cmd(cmd, expected_result)

    def test_SPARK_SUBMIT_SCRIPT_RUNNER_STEP(self):
        cmd = self.prefix + 'Type=SPARK,' + \
            self.SPARK_SUBMIT_BASIC_ARGS
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Spark application',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.SPARK_SUBMIT_SCRIPT_RUNNER_STEP
                 }]
        }
        expected_result_release = copy.deepcopy(expected_result)
        expected_result_release['Steps'][0]['HadoopJarStep'] = \
            self.SPARK_SUBMIT_COMMAND_RUNNER_STEP

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=expected_result_release)

    def test_spark_missing_arg(self):
        cmd = self.prefix + 'Type=SPARK'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for SparkStepConfig: Args.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_impala_missing_args(self):
        cmd = self.prefix + 'Type=Impala'
        expected_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for ImpalaStepConfig: Args.\n'
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=None)

    def test_impala_step_with_all_fields(self):
        test_step_config = \
            'Name=ImpalaWithAllFields,' + \
            'Type=Impala,' + \
            self.IMPALA_BASIC_ARGS + ',' + \
            'ActionOnFailure=CANCEL_AND_WAIT'
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'ImpalaWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.IMPALA_BASIC_SCRIPT_RUNNER_STEP
                 }
            ]
        }
        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=None)

    def test_impala_step_with_release(self):
        test_step_config = 'Type=Impala,' + self.IMPALA_BASIC_ARGS
        cmd = self.prefix + test_step_config
        expected_result_release = '\naws: error: The step type impala ' + \
            'is not supported.\n'

        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=None,
            expected_result_release=expected_result_release)

    def test_empty_step_args(self):
        cmd = self.prefix + 'Type=Streaming,Args='
        expected_error_msg = ('\naws: error: The prameter Args cannot '
                              'be an empty list.\n')
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

        cmd = self.prefix + 'Type=Pig,Args='
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

        cmd = self.prefix + 'Type=Hive,Args='
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

        cmd = self.prefix + 'Args='
        expected_error_msg = ('\naws: error: The following required parameters'
                              ' are missing for CustomJARStepConfig: Jar.\n')
        self.assert_error_for_ami_and_release_based_clusters(
            cmd=cmd, expected_error_msg=expected_error_msg,
            expected_result_release=expected_error_msg)

    def test_all_step_types(self):
        test_step_config = 'Jar=s3://mybucket/mytest.jar ' + \
            ' Type=Streaming,' + self.STREAMING_ARGS + \
            ' Type=Hive,' + self.HIVE_BASIC_ARGS + \
            ' Type=Pig,' + self.PIG_BASIC_ARGS + \
            ' Type=Impala,' + self.IMPALA_BASIC_ARGS
        cmd = self.prefix + test_step_config
        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 },
                {'Name': 'Streaming program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.STREAMING_HADOOP_SCRIPT_RUNNER_STEP
                 },
                {'Name': 'Hive program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.HIVE_DEFAULT_SCRIPT_RUNNER_STEP
                 },
                {'Name': 'Pig program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.PIG_DEFAULT_SCRIPT_RUNNER_STEP
                 },
                {'Name': 'Impala program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.IMPALA_BASIC_SCRIPT_RUNNER_STEP
                 }
            ]
        }

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=expected_result,
            expected_result_release=None)

    def test_all_step_types_release(self):
        test_step_config = 'Jar=s3://mybucket/mytest.jar ' + \
            ' Type=Streaming,' + self.STREAMING_ARGS + \
            ' Type=Hive,' + self.HIVE_BASIC_ARGS + \
            ' Type=Pig,' + self.PIG_BASIC_ARGS

        cmd = self.prefix + test_step_config
        expected_result_release = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 },
                {'Name': 'Streaming program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.STREAMING_HADOOP_COMMAND_RUNNER_STEP
                 },
                {'Name': 'Hive program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.HIVE_DEFAULT_COMMAND_RUNNER_STEP
                 },
                {'Name': 'Pig program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.PIG_DEFAULT_COMMAND_RUNNER_STEP
                 }
            ]
        }

        self.assert_params_for_ami_and_release_based_clusters(
            cmd=cmd, expected_result=None,
            expected_result_release=expected_result_release)

    def test_all_step_types_from_json(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_steps.json')
        cmd = self.prefix + 'file://' + data_path
        hive_script_runner_step = copy.deepcopy(
            self.HIVE_DEFAULT_SCRIPT_RUNNER_STEP)
        hive_script_runner_step['Args'] += \
            ['-d',
             'INPUT=s3://elasticmapreduce/samples/hive-ads/tables',
             '-d',
             'OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32',
             '-d',
             'LIBS=s3://elasticmapreduce/samples/hive-ads/libs'
             ]
        pig_script_runner_step = copy.deepcopy(
            self.PIG_DEFAULT_SCRIPT_RUNNER_STEP)
        pig_script_runner_step['Args'] += \
            ['-p',
             'INPUT=s3://elasticmapreduce/samples/pig-apache/input',
             '-p',
             'OUTPUT=s3://mybucket/pig-apache/output/2014-04-21/20-09-28'
             ]

        expected_result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 },
                {'Name': 'Streaming step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.STREAMING_HADOOP_SCRIPT_RUNNER_STEP
                 },
                {'Name': 'Hive step',
                 'ActionOnFailure': 'TERMINATE_CLUSTER',
                 'HadoopJarStep': hive_script_runner_step
                 },
                {'Name': 'Pig step',
                 'ActionOnFailure': 'TERMINATE_CLUSTER',
                 'HadoopJarStep': pig_script_runner_step
                 },
                {'Name': 'Impala step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.IMPALA_BASIC_SCRIPT_RUNNER_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, expected_result)

    @mock.patch('awscli.customizations.emr.'
                'emrutils.get_release_label')
    def assert_params_for_ami_and_release_based_clusters(
            self, grl_patch, cmd, expected_result, expected_result_release):
        if expected_result:
            grl_patch.return_value = None
            self.assert_params_for_cmd(cmd, expected_result)
        if expected_result_release:
            grl_patch.return_value = 'emr-4.0'
            self.assert_params_for_cmd(cmd, expected_result_release)

    @mock.patch('awscli.customizations.emr.'
                'emrutils.get_release_label')
    def assert_error_for_ami_and_release_based_clusters(
            self, grl_patch, cmd, expected_error_msg,
            expected_result_release):
        if expected_error_msg:
            grl_patch.return_value = None
            result = self.run_cmd(cmd, 255)
            self.assertEquals(expected_error_msg, result[1])
        if expected_result_release:
            grl_patch.return_value = 'emr-4.0'
            result = self.run_cmd(cmd, 255)
            self.assertEquals(expected_result_release, result[1])

if __name__ == "__main__":
    unittest.main()
