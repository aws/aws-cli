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


class TestPutIntegration(BaseAWSCommandParamsTest):

    prefix = 'apigateway put-integration '

    def test_put_integration(self):
        cmdline = self.prefix
        cmdline += '--rest-api-id api-id '
        cmdline += '--resource-id resource-id '
        cmdline += '--http-method GET '
        cmdline += '--type HTTP '
        cmdline += '--integration-http-method GET '
        cmdline += '--uri https://api.endpoint.com'
        result = {
            'restApiId': 'api-id', 'resourceId': 'resource-id',
            'httpMethod': 'GET', 'type': 'HTTP',
            'integrationHttpMethod': 'GET',
            'uri': 'https://api.endpoint.com'
        }
        self.assert_params_for_cmd(cmdline, result)
