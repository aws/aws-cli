# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestDescribeTapes(BaseAWSCommandParamsTest):

    PREFIX = 'storagegateway describe-tapes'

    def test_accepts_old_argname(self):
        foo_arn = 'a' * 50
        bar_arn = 'b' * 50
        cmdline = (
            self.PREFIX + ' --gateway-arn %s --tape-ar-ns %s'
        ) % (foo_arn, bar_arn)
        params = {
            'GatewayARN': foo_arn,
            'TapeARNs': [bar_arn],
        }
        self.assert_params_for_cmd(cmdline, params)

    def test_accepts_fixed_param_name(self):
        foo_arn = 'a' * 50
        bar_arn = 'b' * 50
        cmdline = (
            self.PREFIX + ' --gateway-arn %s --tape-arns %s'
        ) % (foo_arn, bar_arn)
        params = {
            'GatewayARN': foo_arn,
            'TapeARNs': [bar_arn],
        }
        self.assert_params_for_cmd(cmdline, params)
