# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestDescribeSnapshots(BaseAWSCommandParamsTest):

    prefix = 'ec2 describe-snapshots'

    def test_max_results_set_by_default(self):
        command = self.prefix
        params = {'MaxResults': 1000}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_set_with_snapshot_ids(self):
        command = self.prefix + ' --snapshot-ids snap-example'
        params = {'SnapshotIds': ['snap-example']}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_set_with_filter(self):
        command = self.prefix + ' --filters Name=snapshot-id,Values=snap-snap'
        params = {'Filters': [{
            'Name': 'snapshot-id', 'Values': ['snap-snap']
        }]}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_overwritten(self):
        command = self.prefix + ' --max-results 5'
        params = {'MaxResults': 5}
        self.assert_params_for_cmd(command, params)

        command = self.prefix + ' --page-size 5'
        self.assert_params_for_cmd(command, params)
