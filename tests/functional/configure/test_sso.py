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
from unittest.mock import patch

from awscli.customizations.configure.sso import ConfigureSSOCommand
from awscli.testutils import BaseAWSCommandParamsTest, mock
from tests.functional.sso import BaseSSOTest


class TestConfigureSSO(BaseAWSCommandParamsTest):
    prefix = 'configure sso'

    def test_sso_logout_do_not_exist(self):
        cmdline = self.prefix + ' logout'
        _, err, _ = self.run_cmd(cmdline, 252)
        self.assertIn('Unknown options', err)


class TestConfigureSSOCommand(BaseSSOTest):
    def setUp(self):
        super().setUp()

        self.registration_args_prompt = patch.object(
            ConfigureSSOCommand,
            '_prompt_for_sso_registration_args',
            return_value={
                'session_name': 'my-session',
                'sso_region': 'us-east-1',
                'start_url': 'https://identitycenter.amazonaws.com/ssoins-1234',
            },
        )

        self.account_and_role_prompt = patch.object(
            ConfigureSSOCommand,
            '_prompt_for_sso_account_and_role',
            return_value=('123456789012', 'role'),
        )

        self.region_prompt = patch.object(
            ConfigureSSOCommand,
            '_prompt_for_cli_default_region',
            return_value='us-west-2',
        )

        self.output_prompt = patch.object(
            ConfigureSSOCommand,
            '_prompt_for_cli_output_format',
            return_value='json',
        )

        self.profile_prompt = patch.object(
            ConfigureSSOCommand,
            '_prompt_for_profile',
            return_value='my-profile',
        )

        self.registration_args_prompt.start()
        self.account_and_role_prompt.start()
        self.region_prompt.start()
        self.output_prompt.start()
        self.profile_prompt.start()

    def tearDown(self):
        super().tearDown()
        self.registration_args_prompt.stop()
        self.account_and_role_prompt.stop()
        self.region_prompt.stop()
        self.output_prompt.stop()
        self.profile_prompt.stop()

    def test_configure_sso_implicit_auth(self):
        self.add_oidc_auth_code_responses(
            self.access_token,
            include_register_response=True,
        )
        self.run_cmd('configure sso')

    def test_configure_sso_explicit_device(self):
        self.add_oidc_device_responses(
            self.access_token,
            include_register_response=True,
        )
        self.run_cmd('configure sso --use-device-code')

    def test_configure_sso_implicit_device(self):
        self.add_oidc_device_responses(
            self.access_token,
            include_register_response=True,
        )

        # The lack of a session_name should trigger the device flow
        with patch.object(
            ConfigureSSOCommand,
            '_prompt_for_sso_registration_args',
            return_value={
                'session_name': None,
                'sso_region': 'us-east-1',
                'start_url': 'https://identitycenter.amazonaws.com/ssoins-1234',
            },
        ):
            self.run_cmd('configure sso')

    @patch('awscli.botocore.session.Session.create_client')
    def test_configure_sso_custom_ca(self, create_client_patch):
        # Profile and mock responses aren't wired up so this fails with 255,
        # but it does get far enough to verify that the internal SSO-OIDC
        # client is created with the custom CA bundle
        self.run_cmd(
            'configure sso --ca-bundle /path/to/ca/bundle.pem',
            expected_rc=255,
        )

        create_client_patch.assert_called_once_with(
            'sso-oidc',
            config=mock.ANY,
            verify='/path/to/ca/bundle.pem',
        )

    @patch('awscli.botocore.session.Session.create_client')
    def test_configure_sso_no_verify_ssl(self, create_client_patch):
        # Profile and mock responses aren't wired up so this fails with 255,
        # but it does get far enough to verify that the internal SSO-OIDC
        # client is created with verify=False
        self.run_cmd(
            'configure sso --no-verify-ssl',
            expected_rc=255,
        )

        create_client_patch.assert_called_once_with(
            'sso-oidc',
            config=mock.ANY,
            verify=False,
        )
