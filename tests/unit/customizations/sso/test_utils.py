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
import socket
import threading
import webbrowser

import pytest
import urllib3
from botocore.exceptions import PendingAuthorizationExpiredError
from botocore.session import Session

from awscli.compat import BytesIO, StringIO
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.sso.utils import (
    AuthCodeFetcher,
    OAuthCallbackHandler,
    OpenBrowserHandler,
    PrintOnlyHandler,
    do_sso_login,
    open_browser_with_original_ld_path,
    parse_sso_registration_scopes,
    validate_redirect_port,
)
from awscli.testutils import mock, unittest


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
        ('scope-1,scope-2,scope-3', ['scope-1', 'scope-2', 'scope-3']),
    ],
)
def test_parse_registration_scopes(raw_scopes, parsed_scopes):
    assert parse_sso_registration_scopes(raw_scopes) == parsed_scopes


@pytest.mark.parametrize('redirect_port', [None, 1, 34535, 65535])
def test_validate_redirect_port(redirect_port):
    validate_redirect_port(redirect_port)


@pytest.mark.parametrize('redirect_port', [-1, 0, 65536])
def test_validate_redirect_port_invalid(redirect_port):
    with pytest.raises(ParamValidationError, match='--redirect-port'):
        validate_redirect_port(redirect_port)


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
            'sso-oidc', region_name=self.region
        )
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
            },
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
            len(self.on_pending_authorization_mock.call_args_list), 1
        )

    def test_do_sso_login(self):
        do_sso_login(
            session=self.session,
            sso_region=self.region,
            parsed_globals=mock.Mock(),
            start_url=self.start_url,
            token_cache=self.token_cache,
            on_pending_authorization=self.on_pending_authorization_mock,
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
            session=self.session,
            sso_region=self.region,
            parsed_globals=mock.Mock(),
            start_url=self.start_url,
            token_cache=self.token_cache,
            on_pending_authorization=self.on_pending_authorization_mock,
        )
        self.assert_client_called_with_start_url()
        self.assert_used_sso_region()
        self.assert_token_cache_was_filled()
        # Handler should not have been invoked as client was pre-authorized
        self.on_pending_authorization_mock.assert_not_called()

    def test_do_sso_login_passes_redirect_port_to_auth_code_fetcher(self):
        with mock.patch(
            'awscli.customizations.sso.utils.AuthCodeFetcher'
        ) as auth_code_fetcher:
            with mock.patch(
                'awscli.customizations.sso.utils.SSOTokenFetcherAuth'
            ) as token_fetcher:
                do_sso_login(
                    session=self.session,
                    sso_region=self.region,
                    parsed_globals=mock.Mock(),
                    start_url=self.start_url,
                    session_name='test-session',
                    redirect_port=34535,
                )

        auth_code_fetcher.assert_called_once_with(redirect_port=34535)
        token_fetcher.return_value.fetch_token.assert_called_once_with(
            start_url=self.start_url,
            session_name='test-session',
            force_refresh=False,
            registration_scopes=None,
            resolved_start_url=None,
        )


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
            'cross_device_flag': '--use-device-code',
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
        self.assert_text_in_output('Attempting', 'open')
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
                    os.environ
                )
                open_browser_with_original_ld_path('http://example.com')
        self.assertIsNone(captured_env.get('LD_LIBRARY_PATH'))


class MockRequest:
    def __init__(self, request):
        self._request = request

    def makefile(self, *args, **kwargs):
        return BytesIO(self._request)

    def sendall(self, data):
        pass

    def settimeout(self, timeout):
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


def _create_mock_fetcher():
    fetcher = mock.Mock(AuthCodeFetcher)
    fetcher._REQUEST_TIMEOUT = AuthCodeFetcher._REQUEST_TIMEOUT
    fetcher._REDIRECT_PATH = AuthCodeFetcher._REDIRECT_PATH
    return fetcher


class TestStrictOAuthCallbackHandler:
    """Tests for OAuthCallbackHandler when it is given an expected state"""

    def _handle(self, request_line, expected_state='123'):
        fetcher = _create_mock_fetcher()
        request = MockRequest(request_line + b' HTTP/1.1\r\n\r\n')
        handler = mock.MagicMock()
        with (
            mock.patch.object(
                OAuthCallbackHandler, 'send_response'
            ) as send_response,
            mock.patch.object(OAuthCallbackHandler, 'send_header'),
            mock.patch.object(OAuthCallbackHandler, 'end_headers'),
        ):
            OAuthCallbackHandler(
                fetcher,
                request,
                mock.MagicMock(),
                handler,
                expected_state=expected_state,
            )
        return fetcher, send_response

    def test_expected_state_and_code(self):
        fetcher, send_response = self._handle(
            b'GET /oauth/callback?state=123&code=456'
        )
        fetcher.set_auth_code_and_state.assert_called_once_with('456', '123')
        send_response.assert_called_once_with(200)

    @pytest.mark.parametrize(
        'path',
        [
            b'/?state=123&code=456',
            b'/callback?state=123&code=456',
            b'/oauth/callback/extra?state=123&code=456',
        ],
    )
    def test_other_path_is_rejected(self, path):
        fetcher, send_response = self._handle(b'GET ' + path)
        fetcher.set_auth_code_and_state.assert_not_called()
        fetcher.set_error_and_state.assert_not_called()
        send_response.assert_called_once_with(404)

    @pytest.mark.parametrize(
        'query',
        [
            b'code=456',
            b'state=999&code=456',
            b'state=1234&code=456',
            b'state=&code=456',
            b'error=access_denied',
            b'state=999&error=access_denied',
        ],
    )
    def test_missing_or_wrong_state_is_rejected(self, query):
        fetcher, send_response = self._handle(b'GET /oauth/callback?' + query)
        fetcher.set_auth_code_and_state.assert_not_called()
        fetcher.set_error_and_state.assert_not_called()
        send_response.assert_called_once_with(400)

    def test_error_with_expected_state(self):
        fetcher, send_response = self._handle(
            b'GET /oauth/callback?state=123&error=access_denied'
            b'&error_description=User%20denied'
        )
        fetcher.set_error_and_state.assert_called_once_with(
            'access_denied', 'User denied', '123'
        )
        fetcher.set_auth_code_and_state.assert_not_called()
        send_response.assert_called_once_with(200)

    def test_error_without_description(self):
        fetcher, _ = self._handle(
            b'GET /oauth/callback?state=123&error=access_denied'
        )
        fetcher.set_error_and_state.assert_called_once_with(
            'access_denied', None, '123'
        )

    def test_neither_code_nor_error_is_rejected(self):
        fetcher, send_response = self._handle(b'GET /oauth/callback?state=123')
        fetcher.set_auth_code_and_state.assert_not_called()
        fetcher.set_error_and_state.assert_not_called()
        send_response.assert_called_once_with(400)

    def test_sets_per_connection_timeout_only_when_strict(self):
        # setup() applies self.timeout to the connection, so it must be
        # set before BaseRequestHandler.__init__ calls setup()
        timeouts = []

        def record_timeout(handler):
            timeouts.append(handler.timeout)

        fetcher = _create_mock_fetcher()
        fetcher._REQUEST_TIMEOUT = 7
        patch = mock.patch.object
        with (
            patch(OAuthCallbackHandler, 'setup', record_timeout),
            patch(OAuthCallbackHandler, 'handle'),
            patch(OAuthCallbackHandler, 'finish'),
        ):
            for expected_state in ('123', None):
                OAuthCallbackHandler(
                    fetcher,
                    MockRequest(b''),
                    mock.MagicMock(),
                    mock.MagicMock(),
                    expected_state=expected_state,
                )
        assert timeouts == [7, None]

    def test_uses_the_fetchers_redirect_path(self):
        fetcher = _create_mock_fetcher()
        fetcher._REDIRECT_PATH = '/custom/callback'
        with (
            mock.patch.object(
                OAuthCallbackHandler, 'send_response'
            ) as send_response,
            mock.patch.object(OAuthCallbackHandler, 'send_header'),
            mock.patch.object(OAuthCallbackHandler, 'end_headers'),
        ):
            for path in (b'/oauth/callback', b'/custom/callback'):
                OAuthCallbackHandler(
                    fetcher,
                    MockRequest(
                        b'GET '
                        + path
                        + b'?state=123&code=456 HTTP/1.1\r\n\r\n'
                    ),
                    mock.MagicMock(),
                    mock.MagicMock(),
                    expected_state='123',
                )
        assert send_response.call_args_list == [mock.call(404), mock.call(200)]
        fetcher.set_auth_code_and_state.assert_called_once_with('456', '123')


def _create_auth_code_fetcher(**kwargs):
    # Binding the fetcher's HTTPServer does a reverse DNS lookup of the host,
    # which can stall for seconds. The resulting server name is unused.
    with mock.patch('socket.getfqdn', return_value='localhost'):
        return AuthCodeFetcher(**kwargs)


class TestAuthCodeFetcher:
    """Tests for the AuthCodeFetcher class, which is the local
    web server we use to handle the OAuth 2.0 callback
    """

    def setup_method(self):
        self.fetcher = _create_auth_code_fetcher()
        self.url = (
            f'http://127.0.0.1:{self.fetcher.http_server.server_address[1]}/'
        )

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
    'awscli.customizations.sso.utils.AuthCodeFetcher._REQUEST_TIMEOUT', 0.1
)
@mock.patch(
    'awscli.customizations.sso.utils.AuthCodeFetcher._OVERALL_TIMEOUT', 0.1
)
def test_get_auth_code_and_state_timeout():
    """Tests the timeout case separately of TestAuthCodeFetcher,
    since we need to override the constants
    """
    with pytest.raises(PendingAuthorizationExpiredError):
        _create_auth_code_fetcher().get_auth_code_and_state()


class TestAuthCodeFetcherWithExpectedState:
    """Tests for the AuthCodeFetcher when waiting for a specific state"""

    expected_state = 'expected-state'

    def setup_method(self):
        self.fetcher = _create_auth_code_fetcher()
        self.url = self.fetcher.redirect_uri_with_port()
        self.result = {}

        def wait():
            try:
                self.result['value'] = self.fetcher.get_auth_code_and_state(
                    expected_state=self.expected_state
                )
            except Exception as e:
                self.result['error'] = e

        self.server_thread = threading.Thread(target=wait)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.http = urllib3.PoolManager(retries=False)

    def teardown_method(self):
        if self.server_thread.is_alive():
            self.fetcher.set_auth_code_and_state(None, None)
            # Wake up handle_request so the wait loop sees it's done
            try:
                urllib3.PoolManager(retries=False).request(
                    'GET', self.url, timeout=1
                )
            except urllib3.exceptions.HTTPError:
                pass
            self.server_thread.join(timeout=5)

    def _get_result(self):
        self.server_thread.join(timeout=5)
        assert not self.server_thread.is_alive()
        return self.result['value']

    def test_expected_auth_code(self):
        response = self.http.request(
            'GET', f'{self.url}?code=1234&state={self.expected_state}'
        )
        assert response.status == 200
        assert self._get_result() == ('1234', self.expected_state)
        assert self.fetcher.error is None

    def test_stray_requests_do_not_end_the_wait(self):
        base = self.url.replace('/oauth/callback', '')
        stray = [
            (f'{base}/?code=1&state={self.expected_state}', 404),
            (f'{base}/favicon.ico', 404),
            (f'{self.url}?code=1&state=wrong', 400),
            (f'{self.url}?code=1', 400),
            (f'{self.url}?error=access_denied', 400),
        ]
        for url, status in stray:
            assert self.http.request('GET', url).status == status
            assert self.server_thread.is_alive()

        response = self.http.request(
            'GET', f'{self.url}?code=1234&state={self.expected_state}'
        )
        assert response.status == 200
        assert self._get_result() == ('1234', self.expected_state)

    def test_error_with_expected_state(self):
        response = self.http.request(
            'GET',
            f'{self.url}?error=access_denied&error_description=Denied'
            f'&state={self.expected_state}',
        )
        assert response.status == 200
        assert self._get_result() == (None, self.expected_state)
        assert self.fetcher.error == {
            'error': 'access_denied',
            'error_description': 'Denied',
        }


@mock.patch(
    'awscli.customizations.sso.utils.AuthCodeFetcher._REQUEST_TIMEOUT', 0.2
)
def test_idle_connection_does_not_block_strict_wait():
    fetcher = _create_auth_code_fetcher()
    result = {}

    def wait():
        result['value'] = fetcher.get_auth_code_and_state(expected_state='abc')

    thread = threading.Thread(target=wait, daemon=True)
    thread.start()
    port = fetcher.http_server.server_port
    # Open a connection and never send a request
    with socket.create_connection(('127.0.0.1', port)):
        thread.join(timeout=0.5)
        response = urllib3.PoolManager(retries=False).request(
            'GET',
            f'http://127.0.0.1:{port}/oauth/callback?code=1&state=abc',
            timeout=5,
        )
    assert response.status == 200
    thread.join(timeout=5)
    assert result['value'] == ('1', 'abc')


def test_auth_code_fetcher_server_logs_handler_errors_at_debug(capsys):
    fetcher = _create_auth_code_fetcher()
    try:
        try:
            raise BrokenPipeError('client went away')
        except BrokenPipeError:
            with mock.patch('awscli.customizations.sso.utils.LOG') as log:
                fetcher.http_server.handle_error(
                    mock.Mock(), ('127.0.0.1', 1234)
                )
        log.debug.assert_called_once_with(
            'Auth callback request failed', exc_info=True
        )
        assert capsys.readouterr().err == ''
    finally:
        fetcher.http_server.server_close()


def test_auth_code_fetcher_uses_redirect_port():
    redirect_port = _get_available_port()
    fetcher = _create_auth_code_fetcher(redirect_port=redirect_port)
    try:
        assert fetcher.http_server.server_port == redirect_port
        assert fetcher.redirect_uri_with_port() == (
            f'http://127.0.0.1:{redirect_port}/oauth/callback'
        )
    finally:
        fetcher.http_server.server_close()


def test_auth_code_fetcher_binds_to_loopback_only():
    fetcher = _create_auth_code_fetcher()
    try:
        assert fetcher.http_server.server_address[0] == '127.0.0.1'
    finally:
        fetcher.http_server.server_close()


def _get_available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]
