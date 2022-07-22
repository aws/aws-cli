# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestPutAccountDetails(BaseAWSCommandParamsTest):

    prefix = 'sesv2 put-account-details'

    def test_put_account_details(self):
        cmdline = self.prefix
        cmdline += '  --website-url https://example.com '
        cmdline += '--mail-type MARKETING '
        cmdline += '--use-case-description Description'

        result = {
            'WebsiteURL': 'https://example.com',
            'MailType': 'MARKETING',
            'UseCaseDescription': 'Description'
        }
        self.assert_params_for_cmd(cmdline, result)
