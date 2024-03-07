# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import BaseAWSHelpOutputTest, BaseAWSCommandParamsTest


class TestSetUnhealthyNodeReplacement(BaseAWSCommandParamsTest):
    prefix = 'emr set-unhealthy-node-replacement'

    def test_unhealthy_node_replacement(self):
        args = ' --cluster-id j-ABC123456 --unhealthy-node-replacement'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'UnhealthyNodeReplacement': True}
        self.assert_params_for_cmd(cmdline, result)


class TestSetUnhealthyNodeReplacementHelp(BaseAWSHelpOutputTest):
    def test_set_unhealthy_node_replacement_is_undocumented(self):
        self.driver.main(['emr', 'help'])
        self.assert_not_contains('set-unhealthy-node-replacement')
