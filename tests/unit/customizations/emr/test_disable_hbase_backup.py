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

import mock

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
from copy import deepcopy


class TestDisableHBaseBackups(BaseAWSCommandParamsTest):
    prefix = 'emr disable-hbase-backups'
    DISABLE_FULL_BACKUP = '--disable-full-backups'
    DISABLE_INCR_BACKUP = '--disable-incremental-backups'
    default_steps = [{
        'HadoopJarStep': {
            'Args': [
                'emr.hbase.backup.Main',
                '--set-scheduled-backup',
                'false'
            ],
            'Jar': '/home/hadoop/lib/hbase.jar'
        },
        'Name': 'Modify Backup Schedule',
        'ActionOnFailure': 'CANCEL_AND_WAIT'
    }]

    def test_disable_hbase_backups_full(self):
        args = ' --cluster-id j-ABCD --full'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        steps[0]['HadoopJarStep']['Args'].append(self.DISABLE_FULL_BACKUP)
        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_disable_hbase_backups_incremental(self):
        args = ' --cluster-id j-ABCD --incremental'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        steps[0]['HadoopJarStep']['Args'].append(self.DISABLE_INCR_BACKUP)
        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_disable_hbase_backups_both(self):
        args = ' --cluster-id j-ABCD --full --incremental'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        steps[0]['HadoopJarStep']['Args'].append(self.DISABLE_FULL_BACKUP)
        steps[0]['HadoopJarStep']['Args'].append(self.DISABLE_INCR_BACKUP)
        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_disable_hbase_backups_none(self):
        args = ' --cluster-id j-ABCD'
        cmdline = self.prefix + args
        expected_error_msg = '\nShould specify at least one of --full' +\
                             ' and --incremental.\n'
        result = self.run_cmd(cmdline, 255)

        self.assertEquals(expected_error_msg, result[1])

    @mock.patch('awscli.customizations.emr.'
                'emrutils.get_release_label')
    def test_unsupported_command_on_release_based_cluster_error(
            self, grl_patch):
        grl_patch.return_value = 'emr-4.0'
        args = ' --cluster-id j-ABCD --full'
        cmdline = self.prefix + args
        expected_error_msg = ("\naws: error: disable-hbase-backups"
                              " is not supported with 'emr-4.0' release.\n")
        result = self.run_cmd(cmdline, 255)

        self.assertEqual(result[1], expected_error_msg)

if __name__ == "__main__":
    unittest.main()
