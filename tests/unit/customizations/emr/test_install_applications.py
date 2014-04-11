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
from tests.unit import BaseAWSCommandParamsTest


INSTALL_HIVE_STEP = {
    'HadoopJarStep': {
        'Args': ['s3://elasticmapreduce/libs/hive/hive-script',
                 '--install-hive', '--base-path',
                 's3://elasticmapreduce/libs/hive',
                 '--hive-versions', 'latest'],
        'Jar': 's3://elasticmapreduce/libs/script-runner/script-runner.jar'
    },
    'Name': 'Install Hive',
    'ActionOnFailure': 'TERMINATE_CLUSTER'
}

INSTALL_PIG_STEP = {
    'HadoopJarStep': {
        'Args': ['s3://elasticmapreduce/libs/pig/pig-script',
                 '--install-pig', '--base-path',
                 's3://elasticmapreduce/libs/pig',
                 '--pig-versions', 'latest'],
        'Jar': 's3://elasticmapreduce/libs/script-runner/script-runner.jar'
    },
    'Name': 'Install Pig',
    'ActionOnFailure': 'TERMINATE_CLUSTER'
}


class TestInstallApplications(BaseAWSCommandParamsTest):
    prefix = 'emr install-applications  --cluster-id j-ABC123456'

    def test_intall_hive_with_version(self):
        cmdline = self.prefix + ' --apps Name=Hive,Version=0.8.1.8'

        step = copy.deepcopy(INSTALL_HIVE_STEP)
        step['HadoopJarStep']['Args'][5] = '0.8.1.8'

        result = {'JobFlowId': 'j-ABC123456', 'Steps': [step]}
        self.assert_params_for_cmd(cmdline, result)

    def test_intall_pig_with_version(self):
        cmdline = self.prefix + ' --apps Name=Pig,Version=0.9.2.1'

        step = copy.deepcopy(INSTALL_PIG_STEP)
        step['HadoopJarStep']['Args'][5] = '0.9.2.1'

        result = {'JobFlowId': 'j-ABC123456', 'Steps': [step]}
        self.assert_params_for_cmd(cmdline, result)

    def test_intall_hive_and_pig_without_version(self):
        cmdline = self.prefix + ' --cluster-id j-ABC123456 --apps Name=Hive' +\
            ' Name=Pig'
        result = {'JobFlowId': 'j-ABC123456', 'Steps': [INSTALL_HIVE_STEP,
                                                        INSTALL_PIG_STEP]}
        self.assert_params_for_cmd(cmdline, result)

    def test_install_impala_error(self):
        cmdline = self.prefix + ' --cluster-id j-ABC123456 --apps Name=Impala'

        expected_error_msg = "\naws: error: Impala cannot be installed on" +\
            " a running cluster. 'Name' should be one of the following:" +\
            " HIVE, PIG\n"
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(result[1], expected_error_msg)

    def test_install_unknown_app_error(self):
        cmdline = self.prefix + ' --cluster-id j-ABC123456 --apps Name=unknown'

        expected_error_msg = "\naws: error: Unknown application: unknown." +\
            " 'Name' should be one of the following: HIVE, PIG, HBASE," +\
            " GANGLIA, IMPALA, MAPR, MAPR_M3, MAPR_M5, MAPR_M7\n"
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(result[1], expected_error_msg)


if __name__ == "__main__":
    unittest.main()
