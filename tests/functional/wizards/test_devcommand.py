# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest, temporary_file


class TestRunWizard(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestRunWizard, self).setUp()
        self.parsed_responses = [{"Roles": []}]

    def test_can_run_wizard(self):
        with temporary_file('r+') as f:
            f.write(
                'version: "0.9"\n'
                'plan:\n'
                '  start:\n'
                '    values:\n'
                '      foo:\n'
                '        type: static\n'
                '        value: myvalue\n'
                'execute:\n'
                '  default:\n'
                '    - type: apicall\n'
                '      operation: iam.ListRoles\n'
                '      params: {}\n'
            )
            f.flush()
            stdout, _, _ = self.assert_params_for_cmd(
                'cli-dev wizard-dev --run-wizard file://%s' % f.name, params={}
            )
