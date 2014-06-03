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
from copy import deepcopy


class TestCreateHBaseBackup(BaseAWSCommandParamsTest):
    prefix = 'emr create-hbase-backup'
    steps = [{
        'HadoopJarStep': {
            'Args': [
                'emr.hbase.backup.Main',
                '--backup',
                '--backup-dir',
                's3://abc/'
            ],
            'Jar': '/home/hadoop/lib/hbase.jar'
        },
        'Name': 'Backup HBase',
        'ActionOnFailure': 'CANCEL_AND_WAIT'
    }]

    def test_create_hbase_backup(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABCD', 'Steps': self.steps}

        self.assert_params_for_cmd(cmdline, result)

    def test_create_hbase_backup_consitent(self):
        args = ' --cluster-id j-ABCD --dir s3://abc/ --consistent'
        cmdline = self.prefix + args

        steps = deepcopy(self.steps)
        steps[0]['HadoopJarStep']['Args'].append('--consistent')
        result = {'JobFlowId': 'j-ABCD', 'Steps': steps}

        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
