#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import awscli.clidriver


class TestDescribeLayers(BaseAWSCommandParamsTest):

    prefix = 'opsworks describe-layers'

    def test_both_params(self):
        cmdline = self.prefix
        cmdline += ' --stack-id 35959772-cd1e-4082-8346-79096d4179f2'
        result = {'StackId': '35959772-cd1e-4082-8346-79096d4179f2'}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
