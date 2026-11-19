# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""The browser sign-in: PKCE, state, and the loopback listener."""

import base64
import hashlib
import http.client
import io
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

import pytest

from awscli.customizations.agentregistry import browserflow, constants
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from awscli.customizations.sso.utils import AuthCodeFetcher, PrintOnlyHandler
from tests.unit.customizations.agentregistry.utils import make_jwt

AUTHORIZE = 'https://idp.example.com/authorize'
TOKEN = 'https://idp.example.com/oauth/token'
CALLBACK_PATH = '/oauth/callback'


def STATE(sign_in):
    """The state from the sign-in link, as the real provider echoes it."""
    return sign_in['state'][0]


@pytest.fixture
def port(monkeypatch):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        free = s.getsockname()[1]
    monkeypatch.setenv('AWS_AGENT_REGISTRY_CALLBACK_PORT', str(free))
    return free


@pytest.fixture(autouse=True)
def short_waits(monkeypatch):
    # Seconds rather than minutes, so a test that times out does so quickly.
    # The request timeout is also how often the overall deadline is checked.
    monkeypatch.setattr(AuthCodeFetcher, '_OVERALL_TIMEOUT', 3)
    monkeypatch.setattr(AuthCodeFetcher, '_REQUEST_TIMEOUT', 0.5)


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Never send loopback requests through a proxy from the environment.
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class _Statuses(list):
    """HTTP statuses the stand-in browser saw, complete once it is done."""

    def __init__(self):
        super().__init__()
        self.threads = []

    def __eq__(self, other):
        for thread in self.threads:
            thread.join(timeout=5)
        return list(self) == other


def _browser(port, *visits):
    """Stand in for the browser: make each request in turn.

    A visit is ``(path, params)`` or ``(method, path, params)``. A callable
    param value is given the sign-in link's query. Returns the stand-in and
    the list the HTTP statuses are collected in.
    """
    statuses = _Statuses()

    def open_browser(url):
        sign_in = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

        def run():
            for visit in visits:
                method, path, params = (
                    visit if len(visit) == 3 else ('GET', *visit)
                )
                query = urllib.parse.urlencode(
                    {
                        key: (value(sign_in) if callable(value) else value)
                        for key, value in params.items()
                    }
                )
                request = urllib.request.Request(
                    f'http://127.0.0.1:{port}{path}?{query}',
                    method=method,
                    data=b'' if method == 'POST' else None,
                )
                try:
                    # Bounded, so a request can never outlive the test.
                    with _DIRECT.open(request, timeout=5) as response:
                        statuses.append(response.status)
                except urllib.error.HTTPError as e:
                    statuses.append(e.code)
                except OSError as e:
                    # The listener is gone, for example after a timeout.
                    statuses.append(type(e).__name__)
                    return

        thread = threading.Thread(target=run, daemon=True)
        statuses.threads.append(thread)
        thread.start()

    return open_browser, statuses


def _opening(opener):
    """The browser launch, which the CLI's OpenBrowserHandler calls."""
    return patch.object(
        browserflow, 'open_browser_with_original_ld_path', side_effect=opener
    )


def _token_endpoint(seen, payload=None):
    payload = payload or {
        'access_token': make_jwt(sub='user'),
        'expires_in': 3600,
        'refresh_token': 'rt',
    }

    def respond(request, timeout, purpose, ca_bundle):
        seen['form'] = urllib.parse.parse_qs(request.data.decode())
        seen['url'] = request.full_url
        seen['ca_bundle'] = ca_bundle
        return _FakeResponse(json.dumps(payload).encode())

    return respond


def _login(**kwargs):
    return browserflow.run_browser_login(
        AUTHORIZE, TOKEN, 'client', ['openid'], **kwargs
    )


def test_pkce_pair_uses_s256():
    verifier, challenge = browserflow.pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b'=')
        .decode()
    )
    assert challenge == expected
    assert browserflow.pkce_pair()[0] != verifier


def test_successful_sign_in_sends_matching_pkce_verifier(port):
    seen = {}
    opener, statuses = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def capture_link(url):
        seen['query'] = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        return opener(url)

    with (
        _opening(capture_link),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        payload = _login(ca_bundle='/corp.pem')

    link = seen['query']
    form = seen['form']
    assert 'audience' not in link
    assert seen['ca_bundle'] == '/corp.pem'
    assert link['code_challenge_method'] == ['S256']
    # The listener's own address, never 'localhost', and the path the CLI's
    # shared listener serves.
    callback = f'http://127.0.0.1:{port}/oauth/callback'
    assert link['redirect_uri'] == [callback]
    assert form['redirect_uri'] == [callback]
    assert form['grant_type'] == ['authorization_code']
    assert form['code'] == ['good-code']
    challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(form['code_verifier'][0].encode()).digest()
        )
        .rstrip(b'=')
        .decode()
    )
    assert link['code_challenge'] == [challenge]
    assert seen['url'] == TOKEN
    assert payload['access_token'].count('.') == 2
    assert statuses == [200]


def test_mismatched_state_is_ignored_and_the_real_redirect_is_used(port):
    seen = {}
    opener, statuses = _browser(
        port,
        (CALLBACK_PATH, {'code': 'attacker-code', 'state': 'forged'}),
        (CALLBACK_PATH, {'code': 'attacker-code'}),
        (CALLBACK_PATH, {'code': 'good-code', 'state': STATE}),
    )
    with (
        _opening(opener),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    assert seen['form']['code'] == ['good-code']
    assert statuses == [400, 400, 200]


def test_mismatched_state_alone_times_out_without_a_token_request(port):
    opener, statuses = _browser(
        port, (CALLBACK_PATH, {'code': 'attacker-code', 'state': 'forged'})
    )
    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen') as token_call,
    ):
        with pytest.raises(AgentRegistryJWTError, match='Timed out'):
            _login()
    token_call.assert_not_called()
    assert statuses == [400]


def test_other_paths_get_404_and_the_listener_keeps_waiting(port):
    seen = {}
    opener, statuses = _browser(
        port,
        ('/favicon.ico', {}),
        ('/', {'code': 'good-code', 'state': STATE}),
        ('/oauth/callback/extra', {'code': 'good-code', 'state': STATE}),
        # The path of earlier versions of this command.
        ('/callback', {'code': 'good-code', 'state': STATE}),
        ('POST', CALLBACK_PATH, {'code': 'good-code', 'state': STATE}),
        (CALLBACK_PATH, {'code': 'good-code', 'state': STATE}),
    )
    with (
        _opening(opener),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    # Only GET is served; other methods are not implemented.
    assert statuses == [404, 404, 404, 404, 501, 200]
    assert seen['form']['code'] == ['good-code']


def test_provider_error_with_matching_state_ends_sign_in(port):
    opener, _ = _browser(
        port,
        (
            CALLBACK_PATH,
            {
                'error': 'access_denied',
                'error_description': 'User cancelled',
                'state': STATE,
            },
        ),
    )
    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen') as token_call,
    ):
        with pytest.raises(AgentRegistryJWTError, match='access_denied'):
            _login()
    token_call.assert_not_called()


def test_error_with_wrong_state_is_neither_shown_nor_final(port, capsys):
    seen = {}
    opener, statuses = _browser(
        port,
        (
            CALLBACK_PATH,
            {
                'error': 'access_denied',
                'error_description': 'Call 555-0100 for help',
                'state': 'forged',
            },
        ),
        (CALLBACK_PATH, {'code': 'good-code', 'state': STATE}),
    )
    with (
        _opening(opener),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    assert statuses == [400, 200]
    assert seen['form']['code'] == ['good-code']
    stderr = capsys.readouterr().err
    assert '555-0100' not in stderr
    assert 'access_denied' not in stderr


def test_connection_that_sends_nothing_does_not_block_sign_in(
    port, monkeypatch
):
    monkeypatch.setattr(AuthCodeFetcher, '_REQUEST_TIMEOUT', 0.2)
    seen = {}
    idle = []
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def stall_then_redirect(url):
        # Held open past the overall deadline, so only the per-connection
        # timeout lets the real redirect through in time.
        connection = socket.create_connection(('127.0.0.1', port), timeout=5)
        idle.append(connection)
        closer = threading.Timer(5, connection.close)
        closer.daemon = True
        closer.start()
        opener(url)

    try:
        with (
            _opening(stall_then_redirect),
            patch.object(
                browserflow, 'urlopen', side_effect=_token_endpoint(seen)
            ),
        ):
            _login()
    finally:
        for connection in idle:
            connection.close()
    assert seen['form']['code'] == ['good-code']


def test_documented_redirect_uri_is_the_shared_listeners():
    # The help tells registry owners to register it.
    assert constants.CALLBACK_PATH == AuthCodeFetcher._REDIRECT_PATH
    assert constants.DEFAULT_REDIRECT_URI == (
        'http://127.0.0.1:8484/oauth/callback'
    )


def test_listener_binds_loopback_only(port):
    fetcher = browserflow._listen(port)
    try:
        assert fetcher.http_server.server_address == ('127.0.0.1', port)
        assert fetcher.redirect_uri_with_port() == (
            f'http://127.0.0.1:{port}/oauth/callback'
        )
    finally:
        fetcher.http_server.server_close()


def test_listener_is_closed_when_the_wait_is_interrupted(port):
    with (
        _opening(None),
        patch.object(
            AuthCodeFetcher,
            'get_auth_code_and_state',
            side_effect=KeyboardInterrupt,
        ),
    ):
        with pytest.raises(KeyboardInterrupt):
            _login()
    # The port is free again.
    with socket.socket() as s:
        s.bind(('127.0.0.1', port))


def test_busy_port_is_explained(port):
    with socket.socket() as busy:
        busy.bind(('127.0.0.1', port))
        busy.listen()
        with _opening(None) as browser:
            with pytest.raises(AgentRegistryJWTError) as e:
                _login()
    browser.assert_not_called()
    message = str(e.value)
    assert message.startswith(
        f'Could not listen on 127.0.0.1:{port} for the sign-in redirect ('
    )
    assert message.endswith(
        '). Free the port, or set AWS_AGENT_REGISTRY_CALLBACK_PORT to another '
        'port that is also registered as a callback URL with the identity '
        'provider.'
    )
    # Not the SSO commands' advice.
    assert '--use-device-code' not in message


def test_timeout_message_covers_both_causes(port):
    with _opening(None):
        with pytest.raises(AgentRegistryJWTError) as e:
            _login()
    message = str(e.value)
    callback = f'http://127.0.0.1:{port}/oauth/callback'
    assert message.startswith(
        f'Timed out after 0 minutes waiting for the sign-in redirect to '
        f'{callback}.'
    )
    # The browser is on another machine.
    assert f'ssh -L {port}:127.0.0.1:{port} <host>' in message
    assert 'run the command again with --no-browser' in message
    assert 'AWS_BEARER_TOKEN_AGENT_REGISTRY' in message
    # The sign-in page showed an error the owner has to fix.
    assert 'redirect mismatch' in message
    assert 'not allowed to access this app' in message
    assert f'callback URL {callback} is registered' in message
    assert 'authorization-code flow' in message
    assert 'localhost' not in message


def test_timeout_is_the_shared_listeners(port, monkeypatch):
    monkeypatch.setattr(AuthCodeFetcher, '_OVERALL_TIMEOUT', 600)
    fetcher = browserflow._listen(port)
    try:
        message = browserflow._timeout_message(
            fetcher, port, fetcher.redirect_uri_with_port()
        )
    finally:
        fetcher.http_server.server_close()
    assert message.startswith('Timed out after 10 minutes waiting')


def test_wait_announces_the_shared_listeners_timeout(
    port, monkeypatch, capsys
):
    monkeypatch.setattr(AuthCodeFetcher, '_OVERALL_TIMEOUT', 120)
    seen = {}
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )
    with (
        _opening(opener),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    assert (
        'Waiting for sign-in to complete (up to 2 minutes)...'
        in capsys.readouterr().err
    )


def test_link_is_opened_with_the_sso_helper_and_shown_on_stderr(port, capsys):
    seen = {}
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )
    with (
        _opening(opener) as helper,
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    [url] = helper.call_args.args
    assert url.startswith(AUTHORIZE + '?')
    out, err = capsys.readouterr()
    # stdout is the command's output, which a script may be reading.
    assert out == ''
    assert (
        'Attempting to open your default browser. If the browser does not '
        f'open, open the following URL.\n\n{url}\n'
    ) in err
    # The redirect must come back to this machine, so no other device is
    # suggested.
    assert 'device' not in err
    assert 'Waiting for sign-in to complete' in err


class _UserOpensTheLink(PrintOnlyHandler):
    """The CLI's print-only handler, and a user who follows the link."""

    def __init__(self, opener, outfile=None):
        super().__init__(outfile=outfile)
        self.opener = opener

    def __call__(self, **kwargs):
        super().__call__(**kwargs)
        self.opener(kwargs['verificationUri'])


def test_no_browser_prints_the_link_and_opens_nothing(port, capsys):
    seen = {}
    opener, statuses = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )
    handlers = []

    def print_only(outfile):
        handlers.append(_UserOpensTheLink(opener, outfile))
        return handlers[-1]

    with (
        _opening(None) as helper,
        patch.object(browserflow, 'PrintOnlyHandler', side_effect=print_only),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        payload = _login(open_browser=False)
    helper.assert_not_called()
    assert payload['access_token'].count('.') == 2
    assert statuses == [200]
    out, err = capsys.readouterr()
    assert out == ''
    assert (
        'Browser will not be automatically opened.\n'
        f'Please visit the following URL:\n\n{AUTHORIZE}?'
    ) in err
    assert 'enter the code' not in err


def test_browser_that_cannot_open_still_leaves_the_printed_link(port, capsys):
    seen = {}
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def fail_to_launch(url):
        # The user opens the printed link by hand.
        opener(url)
        raise RuntimeError('could not locate runnable browser')

    with (
        _opening(fail_to_launch),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        _login()
    assert seen['form']['code'] == ['good-code']
    assert AUTHORIZE + '?' in capsys.readouterr().err


def test_provider_error_text_is_stripped_of_control_characters(port):
    opener, _ = _browser(
        port,
        (
            CALLBACK_PATH,
            {
                'error': 'access_denied\x1b[2J',
                'error_description': '\x1b[31mUser\r\ncancelled\x07 '
                + 'x' * 1000,
                'state': STATE,
            },
        ),
    )
    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen') as token_call,
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            _login()
    token_call.assert_not_called()
    message = str(e.value)
    assert 'access_denied' in message
    assert 'User cancelled' in message
    for control in ('\x1b', '\r', '\n', '\x07'):
        assert control not in message
    assert len(message) < 700


def _exchange_failing_with(port, body, scopes=('openid',)):
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def token_endpoint(request, **kwargs):
        raise urllib.error.HTTPError(
            TOKEN, 400, 'Bad Request', {}, io.BytesIO(body)
        )

    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen', side_effect=token_endpoint),
    ):
        with pytest.raises(AgentRegistryJWTError, match='HTTP 400') as e:
            browserflow.run_browser_login(
                AUTHORIZE, TOKEN, 'client', list(scopes)
            )
    return str(e.value)


def test_token_endpoint_error_whose_body_cannot_be_read(port):
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def token_endpoint(request, **kwargs):
        raise urllib.error.HTTPError(
            TOKEN,
            400,
            'Bad Request',
            {},
            _BrokenResponse(TimeoutError('The read operation timed out')),
        )

    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen', side_effect=token_endpoint),
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            browserflow.run_browser_login(AUTHORIZE, TOKEN, 'client', [])
    # The status is still reported, without the body.
    message = str(e.value)
    assert message.startswith(f'Code exchange failed at {TOKEN} (HTTP 400)')
    assert 'timed out' not in message


def test_token_endpoint_error_body_is_stripped_and_capped(port):
    body = b'{"error": "invalid_grant\x1b]0;pwned\x07"}' + b'\x1b[2J' * 5000
    message = _exchange_failing_with(port, body)
    assert 'invalid_grant' in message
    assert '\x1b' not in message and '\x07' not in message
    assert len(message) < 500


@pytest.mark.parametrize(
    'error,hint',
    [
        ('invalid_client', 'public client with no client secret'),
        ('unauthorized_client', 'does not allow the authorization-code'),
        (
            'invalid_scope',
            'does not allow the requested scopes (openid email)',
        ),
    ],
)
def test_token_endpoint_error_names_the_owner_side_setting(port, error, hint):
    body = json.dumps(
        {'error': error, 'error_description': 'from the provider'}
    ).encode()
    message = _exchange_failing_with(port, body, scopes=('openid', 'email'))
    # The provider's own error is still shown, followed by the hint.
    assert error in message
    assert 'from the provider' in message
    assert hint in message
    assert 'registry owner' in message


@pytest.mark.parametrize(
    'body', [b'{"error": "invalid_grant"}', b'not json', b'["invalid_client"]']
)
def test_other_token_endpoint_errors_get_no_owner_hint(port, body):
    message = _exchange_failing_with(port, body)
    assert 'registry owner' not in message


@pytest.mark.parametrize(
    'error,hint',
    [
        ('unauthorized_client', 'does not allow the authorization-code'),
        ('unsupported_response_type', 'does not allow the authorization-code'),
        ('invalid_scope', 'does not allow the requested scopes (openid)'),
    ],
)
def test_redirect_error_names_the_owner_side_setting(port, error, hint):
    # Cognito and Okta report these on the redirect (RFC 6749, section
    # 4.1.2.1), not from the token endpoint.
    opener, _ = _browser(
        port,
        (
            CALLBACK_PATH,
            {
                'error': error,
                'error_description': 'from the provider',
                'state': STATE,
            },
        ),
    )
    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen') as token_call,
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            _login()
    token_call.assert_not_called()
    message = str(e.value)
    assert message.startswith(f'Sign-in failed: {error} from the provider ')
    assert hint in message
    assert 'registry owner' in message


def test_user_cancelling_gets_no_owner_hint(port):
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'error': 'access_denied', 'state': STATE})
    )
    with _opening(opener):
        with pytest.raises(AgentRegistryJWTError) as e:
            _login()
    assert str(e.value) == 'Sign-in failed: access_denied'


@pytest.mark.parametrize(
    'value,expected', [(None, 8484), ('', 8484), ('1', 1), ('65535', 65535)]
)
def test_callback_port(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv('AWS_AGENT_REGISTRY_CALLBACK_PORT', raising=False)
    else:
        monkeypatch.setenv('AWS_AGENT_REGISTRY_CALLBACK_PORT', value)
    assert browserflow.callback_port() == expected


@pytest.mark.parametrize(
    'value',
    [
        '0',
        '65536',
        '99999',
        '123456',
        '-1',
        '+8484',
        ' 8484',
        '8_484',
        '８４８４',  # full-width digits
        'http',
        '8484\x1b[2J',
    ],
)
def test_invalid_callback_port_names_the_variable(monkeypatch, value):
    monkeypatch.setenv('AWS_AGENT_REGISTRY_CALLBACK_PORT', value)
    with pytest.raises(AgentRegistryJWTError) as e:
        browserflow.callback_port()
    message = str(e.value)
    assert message.startswith(
        'AWS_AGENT_REGISTRY_CALLBACK_PORT must be a port number from 1 to '
        '65535, got '
    )
    assert '\x1b' not in message


def test_invalid_callback_port_fails_before_listening(monkeypatch):
    monkeypatch.setenv('AWS_AGENT_REGISTRY_CALLBACK_PORT', '70000')
    with (
        patch.object(browserflow, 'AuthCodeFetcher') as fetcher,
        _opening(None) as browser,
    ):
        with pytest.raises(AgentRegistryJWTError, match='1 to 65535'):
            _login()
    fetcher.assert_not_called()
    browser.assert_not_called()


# --- Sign-in link -----------------------------------------------------------

_OURS = {
    'response_type': 'code',
    'client_id': 'client',
    'redirect_uri': 'http://127.0.0.1:8484/oauth/callback',
    'state': 'our-state',
    'code_challenge': 'challenge',
    'code_challenge_method': 'S256',
    'scope': 'openid',
}


def _query(link):
    return urllib.parse.parse_qs(
        urllib.parse.urlsplit(link).query, keep_blank_values=True
    )


def test_sign_in_link_keeps_the_endpoints_own_query():
    link = browserflow.sign_in_link(
        'https://idp.example.com/authorize?p=b2c_signin&tenant=a%20b&empty=',
        _OURS,
    )
    assert link.count('?') == 1
    assert link.startswith('https://idp.example.com/authorize?')
    query = _query(link)
    assert query['p'] == ['b2c_signin']
    assert query['tenant'] == ['a b']
    assert query['empty'] == ['']
    for key, value in _OURS.items():
        assert query[key] == [value]


def test_sign_in_link_without_a_query():
    link = browserflow.sign_in_link('https://idp.example.com/authorize', _OURS)
    assert link.count('?') == 1
    assert {key: values[0] for key, values in _query(link).items()} == _OURS


def test_our_parameters_win_over_the_endpoints():
    # A hostile discovery document cannot preset where the code goes or
    # which state is accepted.
    link = browserflow.sign_in_link(
        'https://idp.example.com/authorize?redirect_uri=https://evil.example'
        '&state=attacker&client_id=evil&scope=admin&response_type=token'
        '&code_challenge=x&code_challenge_method=plain&keep=1',
        _OURS,
    )
    assert link.count('?') == 1
    query = _query(link)
    for key, value in _OURS.items():
        assert query[key] == [value]
    assert query['keep'] == ['1']
    assert 'evil' not in link and 'attacker' not in link


def test_endpoint_parameters_we_do_not_send_are_still_dropped():
    # scope is ours to set even when this flow sends none.
    ours = {k: v for k, v in _OURS.items() if k != 'scope'}
    link = browserflow.sign_in_link(
        'https://idp.example.com/authorize?scope=admin', ours
    )
    assert 'scope' not in _query(link)


def test_sign_in_link_drops_a_fragment():
    link = browserflow.sign_in_link(
        'https://idp.example.com/authorize?a=1#fragment', _OURS
    )
    assert '#' not in link
    assert _query(link)['a'] == ['1']


def test_sign_in_with_an_endpoint_query(port):
    seen = {}
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def capture_link(url):
        seen['link'] = url
        return opener(url)

    with (
        _opening(capture_link),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        browserflow.run_browser_login(
            f'{AUTHORIZE}?tenant=abc&state=preset',
            TOKEN,
            'client',
            ['openid'],
        )
    query = _query(seen['link'])
    assert seen['link'].count('?') == 1
    assert query['tenant'] == ['abc']
    assert query['state'] != ['preset'] and len(query['state']) == 1
    assert seen['form']['code'] == ['good-code']


@pytest.mark.parametrize(
    'authorize', ['http://idp.example.com/authorize?a=1', 'idp.example.com']
)
def test_sign_in_link_is_built_only_for_https(authorize):
    with patch.object(browserflow, 'AuthCodeFetcher') as fetcher:
        with pytest.raises(AgentRegistryJWTError, match='only https'):
            browserflow.run_browser_login(
                authorize, TOKEN, 'client', ['openid']
            )
    fetcher.assert_not_called()


def test_any_parameter_this_flow_sends_wins_even_if_added_later():
    # A parameter not in the fixed list, such as one added to the request
    # in future, is still never duplicated.
    link = browserflow.sign_in_link(
        'https://idp.example.com/authorize?prompt=none&keep=1',
        dict(_OURS, prompt='login'),
    )
    query = _query(link)
    assert query['prompt'] == ['login']
    assert query['keep'] == ['1']


@pytest.mark.parametrize(
    'parameter,value',
    [
        ('request', 'eyJhbGciOiJub25lIn0.eyJyZWRpcmVjdF91cmkiOiJ4In0.'),
        ('request_uri', 'https://evil.example/request.jwt'),
        ('response_mode', 'form_post'),
    ],
)
def test_parameters_that_would_override_ours_are_dropped(parameter, value):
    endpoint = (
        'https://idp.example.com/authorize?keep=1&'
        + urllib.parse.urlencode({parameter: value})
    )
    query = _query(browserflow.sign_in_link(endpoint, _OURS))
    assert parameter not in query
    assert query['keep'] == ['1']


# --- Token endpoint reads ---------------------------------------------------


def _exchange(port, respond):
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )
    with (
        _opening(opener),
        patch.object(browserflow, 'urlopen', side_effect=respond),
    ):
        return _login()


def test_token_response_larger_than_1_mib_is_refused(port):
    huge = b'{"access_token": "' + b'x' * (1024 * 1024) + b'"}'

    def respond(request, **kwargs):
        return _FakeResponse(huge)

    with pytest.raises(AgentRegistryJWTError, match='too large'):
        _exchange(port, respond)


def test_token_response_of_exactly_1_mib_is_read(port):
    token = make_jwt()
    body = json.dumps({'access_token': token}).encode()
    body += b' ' * (1024 * 1024 - len(body))

    def respond(request, **kwargs):
        return _FakeResponse(body)

    assert _exchange(port, respond)['access_token'] == token


class _BrokenResponse(io.BytesIO):
    def __init__(self, error):
        super().__init__()
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def read(self, *args):
        raise self._error


@pytest.mark.parametrize(
    'error',
    [
        TimeoutError('The read operation timed out'),
        socket.timeout('timed out'),
        ConnectionResetError(54, 'Connection reset by peer'),
        http.client.IncompleteRead(b'{"acc', 100),
        http.client.RemoteDisconnected('closed'),
    ],
    ids=['timeout', 'socket-timeout', 'reset', 'incomplete', 'disconnected'],
)
def test_token_endpoint_read_errors_are_reported_cleanly(port, error):
    def respond(request, **kwargs):
        return _BrokenResponse(error)

    with pytest.raises(AgentRegistryJWTError) as e:
        _exchange(port, respond)
    assert str(e.value).startswith(f'Code exchange failed at {TOKEN}: ')


def test_scopes_reach_the_sign_in_link(port):
    seen = {}
    opener, _ = _browser(
        port, (CALLBACK_PATH, {'code': 'good-code', 'state': STATE})
    )

    def capture_link(url):
        seen['link'] = url
        return opener(url)

    with (
        _opening(capture_link),
        patch.object(
            browserflow, 'urlopen', side_effect=_token_endpoint(seen)
        ),
    ):
        browserflow.run_browser_login(
            AUTHORIZE, TOKEN, 'client', ['openid', 'registry:read']
        )
    assert _query(seen['link'])['scope'] == ['openid registry:read']
