# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestSigninOAuth2Alias(BaseAWSCommandParamsTest):
    def test_create_oauth2_token_alias(self):
        # create-o-auth2-token was released without a rename, so we keep a
        # hidden alias for backwards compatibility.
        command_template = (
            'signin %s --token-input '
            'clientId=c,grantType=authorization_code'
        )
        self.run_cmd(command_template % 'create-o-auth2-token', expected_rc=0)
        self.run_cmd(command_template % 'create-oauth2-token', expected_rc=0)

    def test_create_oauth2_token_with_iam_rename(self):
        args = '--grant-type client_credentials --resource r'
        self.run_cmd(
            f'signin create-oauth2-token-with-iam {args}', expected_rc=0
        )
        self.run_cmd(
            f'signin create-o-auth2-token-with-iam {args}', expected_rc=2
        )

    def test_introspect_oauth2_token_with_iam_rename(self):
        args = '--token t'
        self.run_cmd(
            f'signin introspect-oauth2-token-with-iam {args}', expected_rc=0
        )
        self.run_cmd(
            f'signin introspect-o-auth2-token-with-iam {args}', expected_rc=2
        )

    def test_revoke_oauth2_token_with_iam_rename(self):
        args = '--token t'
        self.run_cmd(
            f'signin revoke-oauth2-token-with-iam {args}', expected_rc=0
        )
        self.run_cmd(
            f'signin revoke-o-auth2-token-with-iam {args}', expected_rc=2
        )
