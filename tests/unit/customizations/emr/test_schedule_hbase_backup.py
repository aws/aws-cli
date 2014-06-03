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
from nose.tools import raises
from copy import deepcopy


class TestScheduleHBaseBackup(BaseAWSCommandParamsTest):
    prefix = 'emr schedule-hbase-backup'
    default_steps = [{
        'HadoopJarStep': {
            'Args': [
                'emr.hbase.backup.Main',
                '--set-scheduled-backup',
                'true',
                '--backup-dir',
                's3://abc/',
                '--full-backup-time-interval',
                '10',
                '--full-backup-time-unit',
                'minutes',
                '--start-time',
                'now'
            ],
            'Jar': '/home/hadoop/lib/hbase.jar'
        },
        'Name': 'Modify Backup Schedule',
        'ActionOnFailure': 'CANCEL_AND_WAIT'
    }]

    def test_schedule_hbase_backup_full(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/ --type full' +\
               ' --interval 10 --unit minutes'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABCD', 'Steps': self.default_steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_schedule_hbase_backup_full_upper_case(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/ --type FULL' +\
               ' --interval 10 --unit minutes'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABCD', 'Steps': self.default_steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_schedule_hbase_backup_incremental_upper_case(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/  --type INCREMENTAL' +\
               ' --interval 10 --unit HOURS'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        args = steps[0]['HadoopJarStep']['Args']
        args[5] = '--incremental-backup-time-interval'
        args[7] = '--incremental-backup-time-unit'
        args[8] = 'hours'
        steps[0]['HadoopJarStep']['Args'] = args

        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

    def test_schedule_hbase_backup_incremental(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/  --type incremental' +\
               ' --interval 10 --unit minutes'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        args = steps[0]['HadoopJarStep']['Args']
        args[5] = '--incremental-backup-time-interval'
        args[7] = '--incremental-backup-time-unit'
        steps[0]['HadoopJarStep']['Args'] = args

        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_schedule_hbase_backup_wrong_type(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/  --type wrong_type' +\
               ' --interval 10 --unit minutes'
        cmdline = self.prefix + args
        expected_error_msg = '\naws: error: invalid type. type should be' +\
                             ' either full or incremental.\n'
        result = self.run_cmd(cmdline, 255)

        self.assertEquals(expected_error_msg, result[1])

    def test_schedule_hbase_backup_wrong_unit(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/  --type full' +\
               ' --interval 10 --unit wrong_unit'
        cmdline = self.prefix + args
        expected_error_msg = '\naws: error: invalid unit. unit should be' +\
                             ' one of the following values: minutes,' +\
                             ' hours or days.\n'
        result = self.run_cmd(cmdline, 255)

        self.assertEquals(expected_error_msg, result[1])

    def test_schedule_hbase_backup_consistent(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/ --type full' +\
               ' --interval 10 --unit minutes --consistent'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        steps[0]['HadoopJarStep']['Args'].insert(5, '--consistent')

        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}
        self.assert_params_for_cmd(cmdline, result)

    def test_schedule_hbase_backup_start_time(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/ --type full --interval' +\
               ' 10 --unit minutes --start-time 2014-04-18T10:43:24-07:00'
        cmdline = self.prefix + args

        steps = deepcopy(self.default_steps)
        steps[0]['HadoopJarStep']['Args'][10] = '2014-04-18T10:43:24-07:00'

        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
