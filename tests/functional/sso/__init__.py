# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import time
import uuid

from awscli.clidriver import AWSCLIEntryPoint
from awscli.customizations.sso.utils import OpenBrowserHandler, AuthCodeFetcher
from awscli.testutils import create_clidriver
from awscli.testutils import FileCreator
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import mock


class BaseSSOTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseSSOTest, self).setUp()
        self.files = FileCreator()
        self.start_url = 'https://mysigin.com'
        self.sso_region = 'us-west-2'
        self.registration_scopes = None
        self.account = '012345678912'
        self.role_name = 'SSORole'
        self.config_file = self.files.full_path('config')
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.set_config_file_content()
        self.access_token = 'foo.token.string'
        self.token_cache_dir = self.files.full_path('token-cache')
        self.token_cache_dir_patch = mock.patch(
            'awscli.customizations.sso.utils.SSO_TOKEN_DIR',
            self.token_cache_dir
        )
        self.token_cache_dir_patch.start()
        self.open_browser_mock = mock.Mock(spec=OpenBrowserHandler)
        self.open_browser_patch = mock.patch(
            'awscli.customizations.sso.utils.OpenBrowserHandler',
            self.open_browser_mock,
        )
        self.open_browser_patch.start()

        self.fetcher_mock = mock.Mock(spec=AuthCodeFetcher)
        self.fetcher_mock.return_value.redirect_uri_without_port.return_value = (
            'http://127.0.0.1/oauth/callback'
        )
        self.fetcher_mock.return_value.redirect_uri_with_port.return_value = (
            'http://127.0.0.1:55555/oauth/callback'
        )
        self.fetcher_mock.return_value.get_auth_code_and_state.return_value = (
            "abc", "00000000-0000-0000-0000-000000000000"
        )
        self.auth_code_fetcher_patch = mock.patch(
            'awscli.customizations.sso.utils.AuthCodeFetcher',
            self.fetcher_mock,
        )
        self.auth_code_fetcher_patch.start()

        self.uuid_mock = mock.Mock(
            return_value=uuid.UUID("00000000-0000-0000-0000-000000000000")
        )
        self.uuid_patch = mock.patch('uuid.uuid4', self.uuid_mock)
        self.uuid_patch.start()

        self.expires_in = 28800
        self.expiration_time = time.time() + 1000

    def tearDown(self):
        super(BaseSSOTest, self).tearDown()
        self.files.remove_all()
        self.open_browser_patch.stop()
        self.auth_code_fetcher_patch.stop()
        self.uuid_patch.stop()
        self.token_cache_dir_patch.stop()

    def assert_used_expected_sso_region(self, expected_region):
        self.assertIn(expected_region, self.last_request_dict['url'])

    def get_legacy_config(self):
        content = (
            f'[default]\n'
            f'sso_start_url={self.start_url}\n'
            f'sso_region={self.sso_region}\n'
            f'sso_role_name={self.role_name}\n'
            f'sso_account_id={self.account}\n'
        )
        return content

    def get_sso_session_config(self, session_name, include_profile=True):
        content = ''
        if include_profile:
            content += (
                f'[default]\n'
                f'sso_session={session_name}\n'
                f'sso_role_name={self.role_name}\n'
                f'sso_account_id={self.account}\n'
            )
        content += (
            f'[sso-session {session_name}]\n'
            f'sso_start_url={self.start_url}\n'
            f'sso_region={self.sso_region}\n'
        )
        if self.registration_scopes:
            scopes = ', '.join(self.registration_scopes)
            content += f'sso_registration_scopes={scopes}'
        return content

    def set_config_file_content(self, content=None):
        if content is None:
            content = self.get_legacy_config()
        self.files.create_file(self.config_file, content)
        # We need to recreate the driver (which includes its session) in order
        # for the config changes to be pulled in by the session.
        self.driver = create_clidriver()
        self.entry_point = AWSCLIEntryPoint(self.driver)
