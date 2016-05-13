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


class TestDescribeInstanceHealth(BaseAWSCommandParamsTest):

    prefix = 'elb describe-instance-health'

    def test_shorthand(self):
        command = self.prefix + ' --load-balancer-name foo'
        command += ' --instances id1 id2 id3'
        expected_params = {
            'LoadBalancerName': 'foo',
            'Instances': [
                {'InstanceId': 'id1'},
                {'InstanceId': 'id2'},
                {'InstanceId': 'id3'}
            ]
        }
        self.assert_params_for_cmd(command, expected_params)
