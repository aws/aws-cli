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
import os
import copy


class TestAddSteps(BaseAWSCommandParamsTest):
    prefix = 'emr add-steps --cluster-id j-ABC --steps '

    STREAMING_ARGS = 'Args=-files,' + \
        's3://elasticmapreduce/samples/wordcount/wordSplitter.py,' + \
        '-mapper,wordSplitter.py,' + \
        '-reducer,aggregate,' + \
        '-input,s3://elasticmapreduce/samples/wordcount/input,' + \
        '-output,s3://mybucket/wordcount/output/2014-04-18/12-15-24'
    STREAMING_HADOOP_JAR_STEP = \
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

    HIVE_BASIC_ARGS = 'Args=-f,' + \
        's3://elasticmapreduce/samples/hive-ads/libs/model-build.q'

    HIVE_DEFAULT_HADOOP_JAR_STEP = \
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

    PIG_BASIC_ARGS = 'Args=-f,' + \
        's3://elasticmapreduce/samples/pig-apache/do-reports2.pig'

    PIG_DEFAULT_HADOOP_JAR_STEP = \
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

    IMPALA_BASIC_ARGS = 'Args=' + \
        '--impala-script,s3://myimpala/input,' + \
        '--console-output-path,s3://myimpala/output'

    IMPALA_BASIC_HADOOP_JAR_STEP = \
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

    def test_unknown_step_type(self):
        cmd = self.prefix + 'Type=unknown'
        expect_error_msg = '\naws: error: ' + \
            'The step type unknown is not supported.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_default_step_type_name_action_on_failure(self):
        cmd = self.prefix + 'Jar=s3://mybucket/mytest.jar'
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_custom_jar_step_missing_jar(self):
        cmd = self.prefix + 'Name=CustomJarMissingJar'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for CustomJARStepConfig: Jar.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_custom_jar_step_with_all_fields(self):
        cmd = self.prefix + (
            'Name=Custom,Type=Custom_jar,'
            'Jar=s3://mybucket/mytest.jar,'
            'Args=arg1,arg2,MainClass=mymainclass,'
            'ActionOnFailure=TERMINATE_CLUSTER,'
            'Properties=k1=v1\,k2=v2\,k3')
        result = {
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
        self.assert_params_for_cmd(cmd, result)

    def test_streaming_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Streaming,' + self.STREAMING_ARGS
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Streaming program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.STREAMING_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_streaming_step_missing_args(self):
        cmd = self.prefix + 'Type=Streaming'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for StreamingStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_streaming_jar_with_all_fields(self):
        test_step_config = 'Type=Streaming,' + \
            'Name=StreamingStepAllFields,' + \
            'ActionOnFailure=CANCEL_AND_WAIT,' + \
            self.STREAMING_ARGS
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'StreamingStepAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.STREAMING_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_hive_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Hive,' + self.HIVE_BASIC_ARGS
        result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Hive program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.HIVE_DEFAULT_HADOOP_JAR_STEP
                 }]
            }
        self.assert_params_for_cmd(cmd, result)

    def test_hive_step_missing_args(self):
        cmd = self.prefix + 'Type=Hive'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for HiveStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_hive_step_with_all_fields(self):
        test_step_config = \
            'Type=Hive,' + \
            'ActionOnFailure=CANCEL_AND_WAIT,' + \
            'Name=HiveWithAllFields,' + \
            self.HIVE_BASIC_ARGS
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'HiveWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.HIVE_DEFAULT_HADOOP_JAR_STEP
                 }]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_pig_step_with_default_fields(self):
        cmd = self.prefix + 'Type=Pig,' + self.PIG_BASIC_ARGS
        result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Pig program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.PIG_DEFAULT_HADOOP_JAR_STEP
                 }]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_pig_missing_args(self):
        cmd = self.prefix + 'Type=Pig'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for PigStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_pig_step_with_all_fields(self):
        test_step_config = \
            'Name=PigWithAllFields,' + \
            'Type=Pig,' + \
            self.PIG_BASIC_ARGS + ',' + \
            'ActionOnFailure=CANCEL_AND_WAIT'
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'PigWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.PIG_DEFAULT_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_impala_step_with_default_fields(self):
        test_step_config = 'Type=Impala,' + \
            self.IMPALA_BASIC_ARGS
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps':    [
                {'Name': 'Impala program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.IMPALA_BASIC_HADOOP_JAR_STEP
                 }]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_impala_missing_args(self):
        cmd = self.prefix + 'Type=Impala'
        expect_error_msg = '\naws: error: The following ' + \
            'required parameters are missing for ImpalaStepConfig: Args.\n'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_impala_step_with_all_fields(self):
        test_step_config = \
            'Name=ImpalaWithAllFields,' + \
            'Type=Impala,' + \
            self.IMPALA_BASIC_ARGS + ',' + \
            'ActionOnFailure=CANCEL_AND_WAIT'
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'ImpalaWithAllFields',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.IMPALA_BASIC_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_empty_step_args(self):
        cmd = self.prefix + 'Type=Streaming,Args='
        expect_error_msg = ('\naws: error: The prameter Args cannot '
                            'be an empty list.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = self.prefix + 'Type=Pig,Args='
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = self.prefix + 'Type=Hive,Args='
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

        cmd = self.prefix + 'Args='
        expect_error_msg = ('\naws: error: The following required parameters '
                            'are missing for CustomJARStepConfig: Jar.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    def test_all_step_types(self):
        test_step_config = 'Jar=s3://mybucket/mytest.jar ' + \
            ' Type=Streaming,' + self.STREAMING_ARGS + \
            ' Type=Hive,' + self.HIVE_BASIC_ARGS + \
            ' Type=Pig,' + self.PIG_BASIC_ARGS + \
            ' Type=Impala,' + self.IMPALA_BASIC_ARGS
        cmd = self.prefix + test_step_config
        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 },
                {'Name': 'Streaming program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.STREAMING_HADOOP_JAR_STEP
                 },
                {'Name': 'Hive program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.HIVE_DEFAULT_HADOOP_JAR_STEP
                 },
                {'Name': 'Pig program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.PIG_DEFAULT_HADOOP_JAR_STEP
                 },
                {'Name': 'Impala program',
                 'ActionOnFailure': 'CONTINUE',
                 'HadoopJarStep': self.IMPALA_BASIC_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

    def test_all_step_types_from_json(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_steps.json')
        cmd = self.prefix + 'file://' + data_path
        hive_hadoop_jar_step = copy.deepcopy(self.HIVE_DEFAULT_HADOOP_JAR_STEP)
        hive_hadoop_jar_step['Args'] += \
            ['-d',
             'INPUT=s3://elasticmapreduce/samples/hive-ads/tables',
             '-d',
             'OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32',
             '-d',
             'LIBS=s3://elasticmapreduce/samples/hive-ads/libs'
             ]
        pig_hadoop_jar_step = copy.deepcopy(self.PIG_DEFAULT_HADOOP_JAR_STEP)
        pig_hadoop_jar_step['Args'] += \
            ['-p',
             'INPUT=s3://elasticmapreduce/samples/pig-apache/input',
             '-p',
             'OUTPUT=s3://mybucket/pig-apache/output/2014-04-21/20-09-28'
             ]

        result = {
            'JobFlowId': 'j-ABC',
            'Steps': [
                {'Name': 'Custom JAR step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': {'Jar': 's3://mybucket/mytest.jar'}
                 },
                {'Name': 'Streaming step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.STREAMING_HADOOP_JAR_STEP
                 },
                {'Name': 'Hive step',
                 'ActionOnFailure': 'TERMINATE_CLUSTER',
                 'HadoopJarStep': hive_hadoop_jar_step
                 },
                {'Name': 'Pig step',
                 'ActionOnFailure': 'TERMINATE_CLUSTER',
                 'HadoopJarStep': pig_hadoop_jar_step
                 },
                {'Name': 'Impala step',
                 'ActionOnFailure': 'CANCEL_AND_WAIT',
                 'HadoopJarStep': self.IMPALA_BASIC_HADOOP_JAR_STEP
                 }
            ]
        }
        self.assert_params_for_cmd(cmd, result)

if __name__ == "__main__":
    unittest.main()
