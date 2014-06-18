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


class TestTerminateClusters(BaseAWSCommandParamsTest):
    prefix = 'emr terminate-clusters'

    def test_cluster_id(self):
        args = ' --cluster-ids j-ABC123456'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456']}
        self.assert_params_for_cmd(cmdline, result)

    def test_cluster_ids(self):
        args = ' --cluster-ids j-ABC123456 j-AAAAAAA'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456', 'j-AAAAAAA']}
        self.assert_params_for_cmd(cmdline, result)

if __name__ == "__main__":
    unittest.main()
