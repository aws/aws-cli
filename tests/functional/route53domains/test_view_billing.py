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


class TestViewBilling(BaseAWSCommandParamsTest):

    prefix = 'route53domains view-billing'

    def test_accepts_start_time(self):
        command = self.prefix + ' --start-time 2'
        expected_params = {
            'Start': '2'
        }
        self.assert_params_for_cmd(command, expected_params)

    def test_accepts_end_time(self):
        command = self.prefix + ' --end-time 2'
        expected_params = {
            'End': '2'
        }
        self.assert_params_for_cmd(command, expected_params)
