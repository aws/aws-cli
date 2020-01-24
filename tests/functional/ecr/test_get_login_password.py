# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.testutils import BaseAWSCommandParamsTest


class TestGetLoginPasswordCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestGetLoginPasswordCommand, self).setUp()
        self.parsed_responses = [
            {
                'authorizationData': [
                    {
                        "authorizationToken": "Zm9vOmJhcg==",
                        "proxyEndpoint": "1235.ecr.us-east-1.io",
                        "expiresAt": "2015-10-16T00:00:00Z"
                    }
                ]
            },
        ]

    def test_prints_get_login_command(self):
        stdout = self.run_cmd("ecr get-login-password")[0]
        self.assertIn('bar', stdout)
        self.assertEquals(1, len(self.operations_called))
