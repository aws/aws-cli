# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestCreateReplicationGroup(BaseAWSCommandParamsTest):
    GROUP_ID = 'a' * 50
    GROUP_DESCRIPTION = 'b' * 50
    PREFERRED_AZ = 'az'
    PREFIX = (
        f'elasticache create-replication-group'
        f' --replication-group-id {GROUP_ID}'
        f' --replication-group-description {GROUP_DESCRIPTION}'
    )

    def test_accepts_old_argname(self):
        cmdline = (
            f'{self.PREFIX} --preferred-cache-cluster-a-zs {self.PREFERRED_AZ}'
        )
        params = {
            'ReplicationGroupId': self.GROUP_ID,
            'ReplicationGroupDescription': self.GROUP_DESCRIPTION,
            'PreferredCacheClusterAZs': [self.PREFERRED_AZ]
        }
        self.assert_params_for_cmd(cmdline, params)

    def test_accepts_fixed_param_name(self):
        cmdline = (
            f'{self.PREFIX} --preferred-cache-cluster-azs {self.PREFERRED_AZ}'
        )
        params = {
            'ReplicationGroupId': self.GROUP_ID,
            'ReplicationGroupDescription': self.GROUP_DESCRIPTION,
            'PreferredCacheClusterAZs': [self.PREFERRED_AZ]
        }
        self.assert_params_for_cmd(cmdline, params)
