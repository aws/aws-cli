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
import os
import webbrowser
from awscli.testutils import mock
from awscli.testutils import unittest

from botocore.session import Session

from awscli.compat import StringIO
from awscli.customizations.sso.utils import do_sso_login
from awscli.customizations.sso.utils import OpenBrowserHandler
from awscli.customizations.sso.utils import open_browser_with_original_ld_path


class TestDoSSOLogin(unittest.TestCase):
    def setUp(self):
        self.region = 'us-west-2'
        self.start_url = 'https://mystarturl.com'
        self.token_cache = {}
        self.on_pending_authorization_mock = mock.Mock()
        self.session = mock.Mock(Session)
        self.oidc_client = self.get_mock_sso_oidc_client()
        self.session.create_client.return_value = self.oidc_client

    def get_mock_sso_oidc_client(self):
        client = mock.Mock()
        client.register_client.return_value = {
            'clientSecretExpiresAt': 1000,
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
        }
        client.start_device_authorization.return_value = {
            'interval': 1,
            'expiresIn': 600,
            'userCode': 'foo',
            'deviceCode': 'foo-device-code',
            'verificationUri': 'https://sso.fake/device',
            'verificationUriComplete': 'https://sso.verify',
        }
        client.create_token.return_value = {
            'expiresIn': 28800,
            'tokenType': 'Bearer',
            'accessToken': 'access.token',
        }
        return client

    def assert_client_called_with_start_url(self):
        call_args = self.oidc_client.start_device_authorization.call_args
        self.assertEqual(call_args[1]['startUrl'], self.start_url)

    def assert_used_sso_region(self):
        config = self.session.create_client.call_args[1]['config']
        self.assertEqual(config.region_name, self.region)

    def assert_token_cache_was_filled(self):
        self.assertGreater(len(self.token_cache), 0)

    def assert_on_pending_authorization_called(self):
        self.assertEqual(
            len(self.on_pending_authorization_mock.call_args_list), 1)

    def test_do_sso_login(self):
        do_sso_login(
            session=self.session, sso_region=self.region,
            start_url=self.start_url, token_cache=self.token_cache,
            on_pending_authorization=self.on_pending_authorization_mock
        )
        # We just want to make some quick checks to make sure all of the
        # parameters were plumbed in correctly.
        self.assert_client_called_with_start_url()
        self.assert_used_sso_region()
        self.assert_token_cache_was_filled()
        self.assert_on_pending_authorization_called()


class TestOpenBrowserHandler(unittest.TestCase):
    def setUp(self):
        self.stream = StringIO()
        self.user_code = '12345'
        self.verification_uri = 'https://verification.com'
        self.verification_uri_complete = 'https://verification.com?code=12345'
        self.pending_authorization = {
            'userCode': self.user_code,
            'verificationUri': self.verification_uri,
            'verificationUriComplete': self.verification_uri_complete,
        }
        self.open_browser = mock.Mock(spec=webbrowser.open_new_tab)
        self.handler = OpenBrowserHandler(
            self.stream,
            open_browser=self.open_browser,
        )

    def assert_text_in_output(self, *args):
        output = self.stream.getvalue()
        for text in args:
            self.assertIn(text, output)

    def test_call_no_browser(self):
        handler = OpenBrowserHandler(self.stream, open_browser=False)
        handler(**self.pending_authorization)
        self.assert_text_in_output(self.user_code, self.verification_uri)

    def test_call_browser_success(self):
        self.handler(**self.pending_authorization)
        self.open_browser.assert_called_with(self.verification_uri_complete)
        self.assert_text_in_output('automatically', 'open')
        # assert the URI and user coe are still displayed
        self.assert_text_in_output(self.user_code, self.verification_uri)

    def test_call_browser_fails(self):
        self.open_browser.side_effect = webbrowser.Error()
        self.handler(**self.pending_authorization)
        self.assert_text_in_output(self.user_code, self.verification_uri)
        self.open_browser.assert_called_with(self.verification_uri_complete)


class TestOpenBrowserWithPatchedEnv(unittest.TestCase):

    def test_can_patch_env(self):
        # The various edge case are tested in original_ld_library_path,
        # we're just checking that we're integrating everything together
        # correctly.
        env = {'LD_LIBRARY_PATH': '/foo'}
        with mock.patch('os.environ', env):
            with mock.patch('webbrowser.open_new_tab') as open_new_tab:
                captured_env = {}
                open_new_tab.side_effect = lambda x: captured_env.update(
                    os.environ)
                open_browser_with_original_ld_path('http://example.com')
        self.assertIsNone(captured_env.get('LD_LIBRARY_PATH'))
