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
import threading
import webbrowser
import pytest
import urllib3

from botocore.exceptions import PendingAuthorizationExpiredError
from botocore.session import Session

from awscli.compat import BytesIO, StringIO
from awscli.customizations.sso.utils import OpenBrowserHandler
from awscli.customizations.sso.utils import PrintOnlyHandler
from awscli.customizations.sso.utils import do_sso_login
from awscli.customizations.sso.utils import open_browser_with_original_ld_path
from awscli.customizations.sso.utils import (
    parse_sso_registration_scopes, AuthCodeFetcher, OAuthCallbackHandler
)
from awscli.testutils import mock
from awscli.testutils import unittest


@pytest.mark.parametrize(
    'raw_scopes, parsed_scopes',
    [
        ('scope', ['scope']),
        (' scope ', ['scope']),
        ('', []),
        ('scope, ', ['scope']),
        ('scope-1,scope-2', ['scope-1', 'scope-2']),
        ('scope-1, scope-2', ['scope-1', 'scope-2']),
        (' scope-1, scope-2 ', ['scope-1', 'scope-2']),
        ('scope-1,scope-2,scope-3', ['scope-1', 'scope-2', 'scope-3'])
    ]
)
def test_parse_registration_scopes(raw_scopes, parsed_scopes):
    assert parse_sso_registration_scopes(raw_scopes) == parsed_scopes


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
        real_client = Session().create_client(
            'sso-oidc', region_name=self.region)
        client = mock.Mock()
        client.exceptions = real_client.exceptions
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
        client.create_token.side_effect = [
            client.exceptions.AuthorizationPendingException({}, "CreateToken"),
            {
                'expiresIn': 28800,
                'tokenType': 'Bearer',
                'accessToken': 'access.token',
            }
        ]
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

    def test_do_sso_login_preauthorized(self):
        # First call to create token succeeds because client is pre-authorized
        self.oidc_client.create_token.side_effect = [
            {
                'expiresIn': 28800,
                'tokenType': 'Bearer',
                'accessToken': 'access.token',
            }
        ]
        do_sso_login(
            session=self.session, sso_region=self.region,
            start_url=self.start_url, token_cache=self.token_cache,
            on_pending_authorization=self.on_pending_authorization_mock
        )
        self.assert_client_called_with_start_url()
        self.assert_used_sso_region()
        self.assert_token_cache_was_filled()
        # Handler should not have been invoked as client was pre-authorized
        self.on_pending_authorization_mock.assert_not_called()


class BaseHandlerTest(unittest.TestCase):
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

    def assert_text_in_output(self, *args):
        output = self.stream.getvalue()
        for text in args:
            self.assertIn(text, output)


class TestPrintOnlyHandler(BaseHandlerTest):
    def test_prints_message(self):
        handler = PrintOnlyHandler(self.stream)
        handler(**self.pending_authorization)
        self.assert_text_in_output(
            'Browser will not be automatically opened.',
            self.user_code,
            self.verification_uri,
            self.verification_uri_complete,
        )


class TestOpenBrowserHandler(BaseHandlerTest):
    def setUp(self):
        super().setUp()
        self.open_browser = mock.Mock(spec=webbrowser.open_new_tab)
        self.handler = OpenBrowserHandler(
            self.stream,
            open_browser=self.open_browser,
        )

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


class MockRequest(object):
    def __init__(self, request):
        self._request = request

    def makefile(self, *args, **kwargs):
        return BytesIO(self._request)

    def sendall(self, data):
        pass


class TestOAuthCallbackHandler:
    """Tests for OAuthCallbackHandler, which handles
    individual requests that we receive at the callback uri
    """
    def test_expected_query_params(self):
        fetcher = mock.Mock(AuthCodeFetcher)

        OAuthCallbackHandler(
            fetcher,
            MockRequest(b'GET /?state=123&code=456'),
            mock.MagicMock(),
            mock.MagicMock(),
        )
        fetcher.set_auth_code_and_state.assert_called_once_with('456', '123')

    def test_error(self):
        fetcher = mock.Mock(AuthCodeFetcher)

        OAuthCallbackHandler(
            fetcher,
            MockRequest(b'GET /?error=Error%20message'),
            mock.MagicMock(),
            mock.MagicMock(),
        )

        fetcher.set_auth_code_and_state.assert_called_once_with(None, None)

    def test_missing_expected_query_params(self):
        fetcher = mock.Mock(AuthCodeFetcher)

        # We generally don't expect to be missing the expected query params,
        # but if we do we expect the server to keep waiting for a valid callback
        OAuthCallbackHandler(
            fetcher,
            MockRequest(b'GET /'),
            mock.MagicMock(),
            mock.MagicMock(),
        )

        fetcher.set_auth_code_and_state.assert_not_called()


class TestAuthCodeFetcher:
    """Tests for the AuthCodeFetcher class, which is the local
    web server we use to handle the OAuth 2.0 callback
    """

    def setup_method(self):
        self.fetcher = AuthCodeFetcher()
        self.url = f'http://127.0.0.1:{self.fetcher.http_server.server_address[1]}/'

        # Start the server on a background thread so that
        # the test thread can make the request
        self.server_thread = threading.Thread(
            target=self.fetcher.get_auth_code_and_state
        )
        self.server_thread.daemon = True
        self.server_thread.start()

    def test_expected_auth_code(self):
        expected_code = '1234'
        expected_state = '4567'
        url = self.url + f'?code={expected_code}&state={expected_state}'

        http = urllib3.PoolManager()
        response = http.request("GET", url)

        actual_code, actual_state = self.fetcher.get_auth_code_and_state()
        assert response.status == 200
        assert actual_code == expected_code
        assert actual_state == expected_state

    def test_error(self):
        expected_code = 'Failed'
        url = self.url + f'?error={expected_code}'

        http = urllib3.PoolManager()
        response = http.request("GET", url)

        actual_code, actual_state = self.fetcher.get_auth_code_and_state()
        assert response.status == 200
        assert actual_code is None
        assert actual_state is None


@mock.patch(
    'awscli.customizations.sso.utils.AuthCodeFetcher._REQUEST_TIMEOUT',
    0.1
)
@mock.patch(
    'awscli.customizations.sso.utils.AuthCodeFetcher._OVERALL_TIMEOUT',
    0.1
)
def test_get_auth_code_and_state_timeout():
    """Tests the timeout case separately of TestAuthCodeFetcher,
    since we need to override the constants
    """
    with pytest.raises(PendingAuthorizationExpiredError):
        AuthCodeFetcher().get_auth_code_and_state()
