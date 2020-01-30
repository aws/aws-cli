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
import hashlib
import json
import os
import time

from awscli.testutils import mock
from tests.functional.sso import BaseSSOTest
from awscli.customizations.sso.utils import OpenBrowserHandler


class TestLoginCommand(BaseSSOTest):
    def setUp(self):
        super(TestLoginCommand, self).setUp()
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

    def tearDown(self):
        super(TestLoginCommand, self).tearDown()
        self.token_cache_dir_patch.stop()
        self.open_browser_patch.stop()

    def add_oidc_workflow_responses(self, access_token,
                                    include_register_response=True):
        responses = [
            # StartDeviceAuthorization response
            {
                'interval': 1,
                'expiresIn': 600,
                'userCode': 'foo',
                'deviceCode': 'foo-device-code',
                'verificationUri': 'https://sso.fake/device',
                'verificationUriComplete': 'https://sso.verify',
            },
            # CreateToken response
            {
                'expiresIn': 28800,
                'tokenType': 'Bearer',
                'accessToken': access_token,
            }
        ]
        if include_register_response:
            responses.insert(
                0,
                {
                    'clientSecretExpiresAt': time.time() + 1000,
                    'clientId': 'foo-client-id',
                    'clientSecret': 'foo-client-secret',
                }
            )
        self.parsed_responses = responses

    def assert_used_expected_sso_region(self, expected_region):
        self.assertIn(expected_region, self.last_request_dict['url'])

    def assert_cache_contains_token(self, start_url, expected_token):
        cached_files = os.listdir(self.token_cache_dir)
        # The registration and cached access token
        self.assertEqual(len(cached_files), 2)
        cached_token_filename = self._get_cached_token_filename(start_url)
        self.assertIn(cached_token_filename, cached_files)
        self.assertEqual(
            self._get_token(cached_token_filename),
            expected_token
        )

    def _get_cached_token_filename(self, start_url):
        return hashlib.sha1(start_url.encode('utf-8')).hexdigest() + '.json'

    def _get_token(self, token_filename):
        token_path = os.path.join(self.token_cache_dir, token_filename)
        with open(token_path, 'r') as f:
            cached_response = json.loads(f.read())
            return cached_response['accessToken']

    def test_login(self):
        self.add_oidc_workflow_responses(self.access_token)
        self.run_cmd('sso login')
        self.assert_used_expected_sso_region(expected_region=self.sso_region)
        self.assert_cache_contains_token(
            start_url=self.start_url,
            expected_token=self.access_token
        )

    def test_login_forces_refresh(self):
        self.add_oidc_workflow_responses(self.access_token)
        self.run_cmd('sso login')
        # The register response from the first login should have been
        # cached.
        self.add_oidc_workflow_responses(
            'new.token', include_register_response=False)
        self.run_cmd('sso login')
        self.assert_cache_contains_token(
            start_url=self.start_url,
            expected_token='new.token'
        )

    def test_login_no_sso_configuration(self):
        self.set_config_file_content(content='')
        _, stderr, _ = self.run_cmd('sso login', expected_rc=253)
        self.assertIn(
            'Missing the following required SSO configuration',
            stderr
        )

    def test_login_partially_missing_sso_configuration(self):
        content = (
            '[default]\n'
            'sso_start_url=%s\n' % self.start_url
        )
        self.set_config_file_content(content=content)
        _, stderr, _ = self.run_cmd('sso login', expected_rc=253)
        self.assertIn(
            'Missing the following required SSO configuration',
            stderr
        )
        self.assertIn('sso_region', stderr)
        self.assertNotIn('sso_start_url', stderr)
