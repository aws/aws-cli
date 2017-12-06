# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestAlias(BaseAWSCommandParamsTest):
    def test_alias(self):
        # This command was aliased, both should work
        command_template = '%s invoke-endpoint --endpoint-name foo --body bar f'
        old_command = command_template % 'runtime.sagemaker'
        new_command = command_template % 'sagemaker-runtime'
        self.run_cmd(old_command, expected_rc=0)
        self.run_cmd(new_command, expected_rc=0)
