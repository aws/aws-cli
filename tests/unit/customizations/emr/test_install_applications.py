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


import json
import mock
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


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


class TestInstallApplications(BaseAWSCommandParamsTest):
    prefix = ('emr install-applications --cluster-id '
              'j-ABC123456 --applications ')

    def test_install_hive_site(self):
        cmdline = (self.prefix + 'Name=Hive,'
                   'Args=[--hive-site=s3://test/hive-conf/hive-site.xml]')
        result = {'JobFlowId': 'j-ABC123456',
                  'Steps': [INSTALL_HIVE_STEP, INSTALL_HIVE_SITE_STEP]
                  }
        self.assert_params_for_cmd(cmdline, result)
        cmdline = (self.prefix + 'Name=Hive,'
                   'Args=[--hive-site=s3://test/hive-conf/hive-site.xml,k1]')
        self.assert_params_for_cmd(cmdline, result)

    def test_install_hive_and_pig(self):
        cmdline = self.prefix + 'Name=Hive Name=Pig'
        result = {'JobFlowId': 'j-ABC123456', 'Steps': [INSTALL_HIVE_STEP,
                                                        INSTALL_PIG_STEP]}
        self.assert_params_for_cmd(cmdline, result)

    def test_install_pig_with_profile_region(self):
        self.driver.session.set_config_variable('region', 'cn-north-1')
        cmdline = self.prefix + 'Name=Pig'
        PIG_STEP = json.dumps(INSTALL_PIG_STEP).\
            replace('us-east-1', 'cn-north-1')
        result = {'JobFlowId': 'j-ABC123456',
                  'Steps': [json.loads(PIG_STEP)]}
        self.assert_params_for_cmd(cmdline, result)

    def test_install_impala_error(self):
        cmdline = self.prefix + ' Name=Impala'

        expected_error_msg = "\naws: error: Impala cannot be installed on" +\
            " a running cluster. 'Name' should be one of the following:" +\
            " HIVE, PIG\n"
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(result[1], expected_error_msg)

    def test_install_unknown_app_error(self):
        cmdline = self.prefix + 'Name=unknown'

        expected_error_msg = "\naws: error: Unknown application: unknown." +\
            " 'Name' should be one of the following: HIVE, PIG, HBASE," +\
            " GANGLIA, IMPALA, SPARK, MAPR, MAPR_M3, MAPR_M5, MAPR_M7\n"
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(result[1], expected_error_msg)

    @mock.patch('awscli.customizations.emr.'
                'emrutils.get_release_label')
    def test_unsupported_command_on_release_based_cluster_error(
            self, grl_patch):
        grl_patch.return_value = 'emr-4.0'
        cmdline = (self.prefix + 'Name=Hive,'
                   'Args=[--hive-site=s3://test/hive-conf/hive-site.xml]')

        expected_error_msg = ("\naws: error: install-applications"
                              " is not supported with 'emr-4.0' release.\n")
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(result[1], expected_error_msg)

if __name__ == "__main__":
    unittest.main()
