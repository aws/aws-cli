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
from datetime import datetime
from time import mktime


class TestListClusters(BaseAWSCommandParamsTest):
    prefix = 'emr list-clusters '

    def test_list_active_clusters(self):
        args = '--active'
        cmdline = self.prefix + args
        result = {'ClusterStates': ['STARTING',
                                    'BOOTSTRAPPING',
                                    'RUNNING',
                                    'WAITING',
                                    'TERMINATING'
                                    ]
                  }
        self.assert_params_for_cmd(cmdline, result)

    def test_list_terminated_clusters(self):
        args = '--terminated'
        cmdline = self.prefix + args
        result = {'ClusterStates': ['TERMINATED']}
        self.assert_params_for_cmd(cmdline, result)

    def test_list_failed_clusters(self):
        args = '--failed'
        cmdline = self.prefix + args
        result = {'ClusterStates': ['TERMINATED_WITH_ERRORS']}
        self.assert_params_for_cmd(cmdline, result)

    def test_list_multiple_states(self):
        args = '--cluster-states RUNNING WAITING TERMINATED'
        cmdline = self.prefix + args
        result = {'ClusterStates': ['RUNNING', 'WAITING', 'TERMINATED']}
        self.assert_params_for_cmd(cmdline, result)

    def test_exclusive_states_filters(self):
        args = '--active --failed'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: You can specify only one of the cluster state '
            'filters: --cluster-states, --active, --terminated, --failed.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEquals(expected_error_msg, result[1])

        args = '--cluster-states STARTING RUNNING --terminated'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: You can specify only one of the cluster state '
            'filters: --cluster-states, --active, --terminated, --failed.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEquals(expected_error_msg, result[1])


if __name__ == "__main__":
    unittest.main()
