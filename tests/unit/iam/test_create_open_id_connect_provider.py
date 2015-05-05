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


class TestCreateOpenIDConnectProvider(BaseAWSCommandParamsTest):

    prefix = 'iam create-open-id-connect-provider'

    def test_create_open_id_connect_provider(self):
        cmdline = self.prefix
        cmdline += ' --url https://example.com '
        cmdline += '--thumbprint-list 990F4193972F2BECF12DDEDA5237F9C952F20D9E'

        result = {
            'Url': 'https://example.com',
            'ThumbprintList': ['990F4193972F2BECF12DDEDA5237F9C952F20D9E']
        }
        self.assert_params_for_cmd(cmdline, result)
