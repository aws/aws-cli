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


class TestRemoveTags(BaseAWSCommandParamsTest):

    prefix = 'elb remove-tags'

    def test_shorthand(self):
        command = self.prefix + ' --load-balancer-names foo'
        command += ' --tags bar baz'
        expected_params = {
            'LoadBalancerNames': ['foo'],
            'Tags': [
                {'Key': 'bar'},
                {'Key': 'baz'}
            ]
        }
        self.assert_params_for_cmd(command, expected_params)
