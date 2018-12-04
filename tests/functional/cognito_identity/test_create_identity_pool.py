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


class TestCreateIdentityPool(BaseAWSCommandParamsTest):

    PREFIX = 'cognito-identity create-identity-pool'

    def test_accepts_old_argname(self):
        cmdline = (
            self.PREFIX + ' --identity-pool-name foo '
            '--allow-unauthenticated-identities ' +
            '--open-id-connect-provider-ar-ns aaaabbbbccccddddeeee'
        )
        params = {
            'AllowUnauthenticatedIdentities': True,
            'IdentityPoolName': 'foo',
            'OpenIdConnectProviderARNs': ['aaaabbbbccccddddeeee']
        }
        self.assert_params_for_cmd(cmdline, params)

    def test_accepts_fixed_param_name(self):
        cmdline = (
            self.PREFIX + ' --identity-pool-name foo '
            '--allow-unauthenticated-identities ' +
            '--open-id-connect-provider-arns aaaabbbbccccddddeeee'
        )
        params = {
            'AllowUnauthenticatedIdentities': True,
            'IdentityPoolName': 'foo',
            'OpenIdConnectProviderARNs': ['aaaabbbbccccddddeeee']
        }
        self.assert_params_for_cmd(cmdline, params)
