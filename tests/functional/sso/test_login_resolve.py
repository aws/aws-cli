# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os

from awscli.testutils import mock
from tests.functional.sso import BaseSSOTest


class TestLoginWithVanityUrl(BaseSSOTest):
    def setUp(self):
        super().setUp()
        self.vanity_url = 'https://aws.mycompany.com'
        self.resolved_url = 'https://ssoins-abc.portal.us-east-1.app.aws'
        self.start_url = self.vanity_url
        self.sso_region = 'us-west-2'
        self.set_config_file_content(
            self.get_sso_session_config('vanity-session')
        )
        self.resolve_patch = mock.patch(
            'awscli.customizations.sso.login.resolve_start_url',
            return_value=(self.resolved_url, 'us-east-1'),
        )
        self.mock_resolve = self.resolve_patch.start()
        self.is_aws_owned_patch = mock.patch(
            'awscli.customizations.sso.login.is_aws_owned_domain',
            return_value=False,
        )
        self.mock_is_aws_owned = self.is_aws_owned_patch.start()

    def tearDown(self):
        super().tearDown()
        self.resolve_patch.stop()
        self.is_aws_owned_patch.stop()

    def test_login_uses_resolved_region(self):
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        self.assert_used_expected_sso_region('us-east-1')

    def test_login_passes_resolved_url_to_register_client(self):
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        register_call = self.operations_called[0]
        self.assertEqual(register_call[0].name, 'RegisterClient')
        self.assertEqual(register_call[1]['issuerUrl'], self.resolved_url)

    def test_config_rewritten_after_successful_login(self):
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        with open(self.config_file) as f:
            config_content = f.read()
        self.assertIn('sso_region = us-east-1', config_content)

    def test_config_not_rewritten_on_login_failure(self):
        self.parsed_responses = [
            {
                'Error': {
                    'Code': 'InvalidRequestException',
                    'Message': 'Invalid start url provided',
                }
            }
        ]
        self.run_cmd('sso login', expected_rc=254)
        with open(self.config_file) as f:
            config_content = f.read()
        self.assertIn(f'sso_region={self.sso_region}', config_content)

    def test_config_not_rewritten_when_region_matches(self):
        self.sso_region = 'us-east-1'
        self.set_config_file_content(
            self.get_sso_session_config('vanity-session')
        )
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        with open(self.config_file) as f:
            config_content = f.read()
        self.assertIn('sso_region=us-east-1', config_content)


class TestLoginWithVanityUrlLegacy(BaseSSOTest):
    def setUp(self):
        super().setUp()
        self.vanity_url = 'https://aws.mycompany.com'
        self.resolved_url = 'https://ssoins-abc.portal.us-east-1.app.aws'
        self.start_url = self.vanity_url
        self.sso_region = 'us-west-2'
        self.set_config_file_content(self.get_legacy_config())
        self.resolve_patch = mock.patch(
            'awscli.customizations.sso.login.resolve_start_url',
            return_value=(self.resolved_url, 'us-east-1'),
        )
        self.mock_resolve = self.resolve_patch.start()
        self.is_aws_owned_patch = mock.patch(
            'awscli.customizations.sso.login.is_aws_owned_domain',
            return_value=False,
        )
        self.mock_is_aws_owned = self.is_aws_owned_patch.start()

    def tearDown(self):
        super().tearDown()
        self.resolve_patch.stop()
        self.is_aws_owned_patch.stop()

    def test_legacy_login_uses_resolved_region(self):
        self.add_oidc_device_responses(self.access_token)
        self.run_cmd('sso login')
        self.assert_used_expected_sso_region('us-east-1')

    def test_legacy_config_rewritten_after_successful_login(self):
        self.add_oidc_device_responses(self.access_token)
        self.run_cmd('sso login')
        with open(self.config_file) as f:
            config_content = f.read()
        self.assertIn('sso_region = us-east-1', config_content)

    def test_legacy_passes_resolved_url_to_device_authorization(self):
        self.add_oidc_device_responses(self.access_token)
        self.run_cmd('sso login')
        device_auth_call = None
        for op, params in self.operations_called:
            if op.name == 'StartDeviceAuthorization':
                device_auth_call = params
                break
        self.assertIsNotNone(device_auth_call)
        self.assertEqual(device_auth_call['startUrl'], self.resolved_url)


class TestLoginWithDirectUrl(BaseSSOTest):
    def setUp(self):
        super().setUp()
        self.start_url = 'https://ssoins-abc.portal.us-west-2.app.aws'
        self.sso_region = 'us-west-2'
        self.set_config_file_content(
            self.get_sso_session_config('direct-session')
        )
        self.resolve_patch = mock.patch(
            'awscli.customizations.sso.login.resolve_start_url',
            return_value=(self.start_url, 'us-west-2'),
        )
        self.mock_resolve = self.resolve_patch.start()
        self.is_aws_owned_patch = mock.patch(
            'awscli.customizations.sso.login.is_aws_owned_domain',
            return_value=True,
        )
        self.mock_is_aws_owned = self.is_aws_owned_patch.start()

    def tearDown(self):
        super().tearDown()
        self.resolve_patch.stop()
        self.is_aws_owned_patch.stop()

    def test_config_not_rewritten_for_direct_url(self):
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        with open(self.config_file) as f:
            config_content = f.read()
        self.assertIn(f'sso_region={self.sso_region}', config_content)

    def test_login_uses_configured_region(self):
        self.add_oidc_auth_code_responses(self.access_token)
        self.run_cmd('sso login')
        self.assert_used_expected_sso_region('us-west-2')
