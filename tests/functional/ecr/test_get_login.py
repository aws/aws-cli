# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestGetLoginCommand(BaseAWSCommandParamsTest):
    def test_prints_get_login_command(self):
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
        stdout, _, rc = self.run_cmd("ecr get-login")
        self.assertIn(
            'docker login -u foo -p bar -e none 1235.ecr.us-east-1.io', stdout)
        self.assertEquals(1, len(self.operations_called))
        self.assertNotIn('registryIds', self.operations_called[0][1])

    def test_prints_multiple_get_login_commands(self):
        self.parsed_responses = [
            {
                'authorizationData': [
                    {
                        "authorizationToken": "Zm9vOmJhcg==",
                        "proxyEndpoint": "1235.ecr.us-east-1.io",
                        "expiresAt": "2015-10-16T00:00:00Z"
                    },
                    {
                        "authorizationToken": "YWJjOjEyMw==",
                        "proxyEndpoint": "4567.ecr.us-east-1.io",
                        "expiresAt": "2015-10-16T00:00:00Z"
                    }
                ]
            },
        ]
        stdout, _, rc = self.run_cmd("ecr get-login --registry-ids 1234 5678")
        self.assertIn(
            'docker login -u foo -p bar -e none 1235.ecr.us-east-1.io\n',
            stdout)
        self.assertIn(
            'docker login -u abc -p 123 -e none 4567.ecr.us-east-1.io\n',
            stdout)
        self.assertEquals(1, len(self.operations_called))
        self.assertEquals([u'1234', u'5678'],
                          self.operations_called[0][1]['registryIds'])
