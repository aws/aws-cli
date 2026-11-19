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
"""HTTPS is required for every endpoint, redirects are never followed, and
certificates are verified against the CLI's CA bundle."""

import argparse
import http.client
import io
import shutil
import ssl
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

import botocore.session
import pytest
from botocore.httpsession import get_cert_path

from awscli.customizations.agentregistry import (
    browserflow,
    cache,
    reject_bearer_over_plain_http,
    utils,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError


@pytest.mark.parametrize(
    'url',
    [
        'https://idp.example.com',
        'https://idp.example.com/oauth2/token',
        'https://bucket.s3.us-west-2.amazonaws.com/key?X-Amz-Signature=x',
    ],
)
def test_require_https_accepts_https(url):
    assert utils.require_https(url, 'endpoint') == url


@pytest.mark.parametrize(
    'url',
    [
        'http://idp.example.com',
        'file:///etc/passwd',
        'ftp://idp.example.com/x',
        'HTTP://idp.example.com',
        'https://',
        '//idp.example.com',
        'idp.example.com',
        '',
        None,
    ],
)
def test_require_https_rejects_everything_else(url):
    with pytest.raises(AgentRegistryJWTError, match='only https'):
        utils.require_https(url, 'endpoint')


@pytest.mark.parametrize(
    'url',
    [
        'https://idp.example.com/\x1b[2J',
        'https://idp.example.com/authorize\x07',
        'https://idp.example.com/\u202egnp.exe',
    ],
)
def test_require_https_rejects_control_characters(url):
    # These URLs come from discovery documents and are printed.
    with pytest.raises(AgentRegistryJWTError, match='only https') as e:
        utils.require_https(url, 'endpoint')
    assert '\x1b' not in str(e.value)
    assert '\x07' not in str(e.value)
    assert '\u202e' not in str(e.value)


def test_urlopen_rejects_http_before_any_network_call():
    with patch.object(utils, '_opener') as opener:
        with pytest.raises(AgentRegistryJWTError):
            utils.urlopen('http://idp.example.com/token')
        request = urllib.request.Request('http://idp.example.com/token')
        with pytest.raises(AgentRegistryJWTError):
            utils.urlopen(request)
    opener.assert_not_called()


def test_opener_refuses_redirects_instead_of_following_them():
    handlers = utils._opener().handlers
    redirect_handlers = [
        h
        for h in handlers
        if isinstance(h, urllib.request.HTTPRedirectHandler)
    ]
    # build_opener replaces the default redirect handler with ours.
    assert len(redirect_handlers) == 1
    assert isinstance(redirect_handlers[0], utils._RefuseRedirects)
    request = urllib.request.Request('https://idp.example.com/a')
    with pytest.raises(AgentRegistryJWTError, match='redirect'):
        redirect_handlers[0].redirect_request(
            request, None, 302, 'Found', {}, 'http://evil.example/b'
        )


def test_opener_keeps_proxy_support(monkeypatch):
    # urllib only installs its proxy handler when a proxy is configured, and
    # reads the environment when the opener is built.
    monkeypatch.setenv('HTTPS_PROXY', 'http://proxy.example:3128')
    opener = utils._opener()
    proxies = [
        h
        for h in opener.handlers
        if isinstance(h, urllib.request.ProxyHandler)
    ]
    assert (
        proxies and proxies[0].proxies['https'] == 'http://proxy.example:3128'
    )


# --- CA bundle --------------------------------------------------------------


@pytest.fixture
def corporate_bundle(tmp_path):
    # Any valid PEM bundle will do; its location is what is under test.
    path = tmp_path / 'corporate.pem'
    shutil.copyfile(get_cert_path(True), path)
    return str(path)


@pytest.fixture
def isolated_session(tmp_path, monkeypatch):
    config = tmp_path / 'config'
    config.write_text('')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(config))
    monkeypatch.delenv('AWS_CA_BUNDLE', raising=False)
    monkeypatch.delenv('AWS_PROFILE', raising=False)
    return config


def test_ca_bundle_flag_wins_over_environment_and_config(
    isolated_session, monkeypatch
):
    isolated_session.write_text('[default]\nca_bundle = /config.pem\n')
    monkeypatch.setenv('AWS_CA_BUNDLE', '/env.pem')
    session = botocore.session.Session()
    flag = argparse.Namespace(ca_bundle='/flag.pem')
    assert utils.resolve_ca_bundle(session, flag) == '/flag.pem'
    no_flag = argparse.Namespace(ca_bundle=None)
    assert utils.resolve_ca_bundle(session, no_flag) == '/env.pem'


def test_ca_bundle_from_config_file(isolated_session):
    isolated_session.write_text('[default]\nca_bundle = /config.pem\n')
    session = botocore.session.Session()
    assert utils.resolve_ca_bundle(session) == '/config.pem'


def test_no_ca_bundle_configured(isolated_session):
    session = botocore.session.Session()
    globals_ = argparse.Namespace(ca_bundle=None)
    assert utils.resolve_ca_bundle(session, globals_) is None


def test_tls_context_trusts_the_configured_bundle(corporate_bundle):
    with patch.object(
        utils.ssl, 'create_default_context', wraps=ssl.create_default_context
    ) as create:
        context = utils._ssl_context(corporate_bundle)
    create.assert_called_once_with(cafile=corporate_bundle)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_tls_context_defaults_to_the_bundle_botocore_uses():
    with patch.object(
        utils.ssl, 'create_default_context', wraps=ssl.create_default_context
    ) as create:
        utils._ssl_context(None)
    create.assert_called_once_with(cafile=get_cert_path(True))


def test_tls_context_accepts_a_certificate_directory(tmp_path):
    with patch.object(utils.ssl, 'create_default_context') as create:
        utils._ssl_context(str(tmp_path))
    create.assert_called_once_with(capath=str(tmp_path))


def test_unreadable_ca_bundle_is_reported(tmp_path):
    missing = str(tmp_path / 'missing.pem')
    with pytest.raises(AgentRegistryJWTError, match='CA bundle'):
        utils._ssl_context(missing)
    garbage = tmp_path / 'garbage.pem'
    garbage.write_text('not a certificate')
    with pytest.raises(AgentRegistryJWTError, match='CA bundle'):
        utils._ssl_context(str(garbage))


def test_no_verify_ssl_does_not_turn_off_verification(isolated_session):
    # --no-verify-ssl leaves verify_ssl False; it must not reach the context.
    session = botocore.session.Session()
    globals_ = argparse.Namespace(verify_ssl=False, ca_bundle=None)
    ca_bundle = utils.resolve_ca_bundle(session, globals_)
    assert ca_bundle is None
    context = utils._ssl_context(ca_bundle)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_opener_uses_the_tls_context(corporate_bundle):
    context = ssl.create_default_context()
    with patch.object(utils, '_ssl_context', return_value=context) as made:
        opener = utils._opener(corporate_bundle)
    made.assert_called_once_with(corporate_bundle)
    https = [
        h
        for h in opener.handlers
        if isinstance(h, urllib.request.HTTPSHandler)
    ]
    assert len(https) == 1
    assert https[0]._context is context


def test_urlopen_passes_the_ca_bundle_to_the_opener():
    with patch.object(utils, '_opener') as opener:
        utils.urlopen('https://idp.example.com/x', ca_bundle='/corp.pem')
    opener.assert_called_once_with('/corp.pem')
    opener.return_value.open.assert_called_once()


@pytest.mark.parametrize(
    'call',
    [
        lambda: utils.http_get_json(
            'https://idp.example.com/x', ca_bundle='/corp.pem'
        ),
        lambda: utils.http_post_form(
            'https://idp.example.com/x', {'a': 'b'}, ca_bundle='/corp.pem'
        ),
        lambda: utils.discover_registry(
            'https://registry.example', 'reg1', ca_bundle='/corp.pem'
        ),
        lambda: utils.fetch_oidc_metadata(
            'https://idp.example.com', ca_bundle='/corp.pem'
        ),
    ],
)
def test_http_helpers_pass_the_ca_bundle(call):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = (
        b'{"authorization_servers": ["https://idp.example.com"], '
        b'"issuer": "https://idp.example.com"}'
    )
    with patch.object(utils, 'urlopen', return_value=response) as opened:
        call()
    assert opened.call_args.kwargs['ca_bundle'] == '/corp.pem'


def test_issuer_from_resource_metadata_must_be_https():
    document = {'authorization_servers': ['http://idp.example.com']}
    with patch.object(utils, 'http_get_json', return_value=document):
        with pytest.raises(
            AgentRegistryJWTError, match='authorization server'
        ):
            utils.discover_registry('https://registry.example', 'reg1')


def test_oidc_discovery_requires_https_issuer():
    with patch.object(utils, 'http_get_json') as get:
        with pytest.raises(AgentRegistryJWTError, match='issuer'):
            utils.fetch_oidc_metadata('http://idp.example.com')
    get.assert_not_called()


@pytest.mark.parametrize(
    'authorize,token',
    [
        ('http://idp.example.com/authorize', 'https://idp.example.com/token'),
        ('https://idp.example.com/authorize', 'http://idp.example.com/token'),
        ('javascript:alert(1)', 'https://idp.example.com/token'),
    ],
)
def test_sign_in_rejects_non_https_endpoints_before_listening(
    authorize, token
):
    with patch.object(browserflow, 'AuthCodeFetcher') as fetcher:
        with pytest.raises(AgentRegistryJWTError, match='only https'):
            browserflow.run_browser_login(
                authorize, token, 'client', ['openid']
            )
    fetcher.assert_not_called()


def test_refresh_rejects_non_https_token_endpoint():
    entry = {
        'refreshToken': 'rt',
        'clientId': 'client',
        'tokenEndpoint': 'http://idp.example.com/token',
    }
    with patch.object(utils, '_opener') as opener:
        with pytest.raises(AgentRegistryJWTError):
            cache._refresh(entry, session=None)
    opener.assert_not_called()


# --- Presigned URLs in messages ---------------------------------------------

PRESIGNED = (
    'https://bucket.s3.us-west-2.amazonaws.com/skills/pkg.zip'
    '?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAEXAMPLE'
    '&X-Amz-Security-Token=IQoJsession&X-Amz-Signature=deadbeef'
)
PLAIN_PRESIGNED = PRESIGNED.replace('https://', 'http://')


def _assert_no_query(message):
    for secret in (
        'X-Amz',
        'ASIAEXAMPLE',
        'IQoJsession',
        'deadbeef',
        'pkg.zip',
    ):
        assert secret not in message


@pytest.mark.parametrize(
    'url,expected',
    [
        (PRESIGNED, 'https://bucket.s3.us-west-2.amazonaws.com'),
        ('https://host.example:8443/a?b=c', 'https://host.example:8443'),
        ('https://user:pw@host.example/a?b=c', 'https://host.example'),
        ('https://idp.example.com/token', 'https://idp.example.com/token'),
        ('https://idp.example.com/a#frag', 'https://idp.example.com/a#frag'),
        ('', ''),
        (None, None),
    ],
)
def test_printable_url_drops_the_path_and_query_of_a_query_url(url, expected):
    assert utils.printable_url(url) == expected


def test_url_origin():
    assert utils.url_origin(PRESIGNED) == (
        'https://bucket.s3.us-west-2.amazonaws.com'
    )
    assert utils.url_origin('https://h.example:bad/x') == 'https://h.example'


def test_plain_http_presigned_url_is_refused_without_its_query():
    with pytest.raises(AgentRegistryJWTError, match='only https') as e:
        utils.require_https(PLAIN_PRESIGNED, 'download URL')
    assert 'http://bucket.s3.us-west-2.amazonaws.com' in str(e.value)
    _assert_no_query(str(e.value))


def test_urlopen_refuses_plain_http_presigned_url_without_its_query():
    with patch.object(utils, '_opener') as opener:
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.urlopen(PLAIN_PRESIGNED, purpose='download URL')
    opener.assert_not_called()
    _assert_no_query(str(e.value))


@pytest.mark.parametrize('code', [301, 302, 303, 307, 308])
def test_redirect_refusal_does_not_repeat_a_presigned_url(code):
    handler = utils._RefuseRedirects()
    request = urllib.request.Request(PRESIGNED)
    with pytest.raises(AgentRegistryJWTError, match='redirect') as e:
        handler.redirect_request(
            request, None, code, 'Moved', {}, 'https://evil.example/x'
        )
    message = str(e.value)
    assert f'HTTP {code}' in message
    assert 'https://bucket.s3.us-west-2.amazonaws.com' in message
    _assert_no_query(message)


def _request(url, authorization):
    request = Mock()
    request.url = url
    request.headers = {'Authorization': authorization} if authorization else {}
    return request


@pytest.mark.parametrize('authorization', [b'Bearer abc', 'Bearer abc'])
def test_bearer_token_never_sent_over_plain_http(authorization):
    with pytest.raises(AgentRegistryJWTError, match='registry endpoint'):
        reject_bearer_over_plain_http(
            _request('http://registry.example/x', authorization)
        )


def test_bearer_token_allowed_over_https():
    reject_bearer_over_plain_http(
        _request('https://registry.example/x', b'Bearer abc')
    )


def test_non_bearer_requests_are_not_affected():
    reject_bearer_over_plain_http(
        _request('http://registry.example/x', b'AWS4-HMAC-SHA256 Credential=x')
    )
    reject_bearer_over_plain_http(_request('http://registry.example/x', None))


# --- Response size ----------------------------------------------------------


def _responding(body):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read = Mock(
        side_effect=lambda n=-1: body[: n if n >= 0 else None]
    )
    return response


@pytest.mark.parametrize(
    'call',
    [
        lambda: utils.http_get_json('https://idp.example.com/x?a=secret'),
        lambda: utils.http_post_form(
            'https://idp.example.com/x?a=secret', {'a': 'b'}
        ),
    ],
    ids=['get', 'post'],
)
def test_responses_larger_than_1_mib_are_refused(call):
    body = b'{"a": "' + b'x' * (1024 * 1024) + b'"}'
    with patch.object(utils, 'urlopen', return_value=_responding(body)):
        with pytest.raises(AgentRegistryJWTError) as e:
            call()
    message = str(e.value)
    assert 'too large' in message
    assert 'https://idp.example.com' in message
    assert 'secret' not in message


@pytest.mark.parametrize(
    'call',
    [
        lambda: utils.http_get_json('https://idp.example.com/x'),
        lambda: utils.http_post_form('https://idp.example.com/x', {}),
    ],
    ids=['get', 'post'],
)
def test_a_response_of_exactly_1_mib_is_read(call):
    body = b'{}' + b' ' * (1024 * 1024 - 2)
    response = _responding(body)
    with patch.object(utils, 'urlopen', return_value=response):
        assert call() == {}
    # Reads one byte past the cap, to tell "exactly" from "more".
    response.read.assert_called_once_with(1024 * 1024 + 1)


# --- Error bodies -----------------------------------------------------------


class _UnreadableBody(io.BytesIO):
    def __init__(self, error):
        super().__init__()
        self._error = error

    def read(self, *args):
        raise self._error


def _http_error(fp):
    return urllib.error.HTTPError('https://idp.example.com', 400, 'x', {}, fp)


def test_error_body_is_read_up_to_the_limit():
    error = _http_error(io.BytesIO(b'{"error": "invalid_grant"}' + b'x' * 99))
    assert utils.read_error_body(error, 10) == '{"error": '


def test_error_body_that_is_not_utf8_is_still_text():
    assert utils.read_error_body(_http_error(io.BytesIO(b'\xff')), 10) == (
        '\ufffd'
    )


@pytest.mark.parametrize(
    'failure',
    [
        TimeoutError('The read operation timed out'),
        ConnectionResetError(54, 'Connection reset by peer'),
        http.client.IncompleteRead(b'{"err', 100),
        ValueError('I/O operation on closed file.'),
    ],
    ids=['timeout', 'reset', 'incomplete', 'closed'],
)
def test_error_body_that_cannot_be_read_is_empty(failure):
    error = _http_error(_UnreadableBody(failure))
    assert utils.read_error_body(error, 1024) == ''


@pytest.mark.parametrize(
    'body,code',
    [
        ('{"error": "invalid_grant"}', 'invalid_grant'),
        (
            '{"error": "invalid_client", "error_description": "x"}',
            'invalid_client',
        ),
        ('{"error": ["invalid_grant"]}', None),
        ('{"error_description": "invalid_grant"}', None),
        ('["invalid_grant"]', None),
        ('invalid_grant', None),
        ('{"error": "invalid_grant"', None),
        ('[' * 100000, None),
        ('', None),
    ],
    ids=[
        'invalid-grant',
        'other-code',
        'not-a-string',
        'no-error',
        'not-an-object',
        'not-json',
        'truncated',
        'deeply-nested',
        'empty',
    ],
)
def test_oauth_error_code(body, code):
    assert utils.oauth_error_code(body) == code
