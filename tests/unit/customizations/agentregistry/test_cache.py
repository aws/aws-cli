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
"""Token cache: one file per entry, permissions, expiry, and silent refresh."""

import hashlib
import http.client
import io
import json
import logging
import os
import socket
import stat
import time
import urllib.error
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from awscli.customizations.agentregistry import cache
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    RegistryAuthorization,
)
from tests.unit.customizations.agentregistry.utils import make_jwe, make_jwt

posix_only = pytest.mark.skipif(os.name == 'nt', reason='POSIX modes')

ENDPOINT = 'https://agent-registry.us-west-2.api.aws'
OTHER_ENDPOINT = 'https://agent-registry.eu-west-1.api.aws'
REG = 'abcDEF123456'
OTHER_REG = 'xyzXYZ9876543210'
TOKEN_ENDPOINT = 'https://idp.example.com/token'
COGNITO_REFRESH = (
    'awscli.customizations.agentregistry.providers.CognitoProvider.refresh'
)


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    directory = tmp_path / 'agent-registry' / 'cache'
    monkeypatch.setattr(cache, 'CACHE_DIR', str(directory))
    return directory


@pytest.fixture(autouse=True)
def registry_metadata():
    """Protected Resource Metadata, never fetched from the network here.

    By default it cannot be read, so a refresh goes ahead as before.
    """
    with patch.object(
        cache,
        'discover_registry',
        side_effect=AgentRegistryJWTError('not in unit tests'),
    ) as discover:
        yield discover


def _registry(metadata, issuer='https://idp.example.com', scopes=()):
    """Have the registry's metadata name ``issuer`` and ``scopes``."""
    metadata.side_effect = None
    metadata.return_value = RegistryAuthorization(issuer, list(scopes))


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def _save(registry_id=REG, endpoint=ENDPOINT, **kwargs):
    kwargs.setdefault('token', make_jwt())
    kwargs.setdefault('expires_in', 3600)
    kwargs.setdefault('refresh_token', 'rt')
    cache.save_token(endpoint, registry_id, **kwargs)


def _entry(registry_id=REG, endpoint=ENDPOINT):
    return cache.read_entry(endpoint, registry_id)


def _expired(**kwargs):
    """An entry whose token has expired, ready to refresh."""
    kwargs.setdefault('token_endpoint', TOKEN_ENDPOINT)
    _save(token=make_jwt(exp=1), expires_in=1, **kwargs)


def _expired_cognito():
    _expired(client_id='client', pool_region='us-west-2', token_endpoint=None)


class _UnreadableBody(io.BytesIO):
    def __init__(self, error):
        super().__init__()
        self._error = error

    def read(self, *args):
        raise self._error


def _http_error(code, body=b''):
    """What the token endpoint's reply raises: an HTTP error and its body."""
    fp = body if isinstance(body, io.IOBase) else io.BytesIO(body)
    return urllib.error.HTTPError(TOKEN_ENDPOINT, code, 'Error', {}, fp)


def _invalid_grant(code=400, description='Refresh token expired'):
    body = {'error': 'invalid_grant', 'error_description': description}
    return _http_error(code, json.dumps(body).encode())


def _cognito_error(code):
    return ClientError(
        {'Error': {'Code': code, 'Message': 'Refresh Token has expired'}},
        'GetTokensFromRefreshToken',
    )


def _assert_refresh_error(error, shown):
    """``error`` is the one a refresh raises instead of signing in again."""
    message = str(error)
    assert message.startswith(
        f'Could not refresh the cached sign-in for registry {REG} ('
    )
    assert shown in message
    assert message.endswith(
        '). Try again; to sign in from scratch instead, run aws '
        f'agent-registry sign-out --registry-id {REG} first.'
    )


# --- Files ------------------------------------------------------------------


def test_entry_file_is_named_by_the_hash_of_endpoint_and_registry(cache_dir):
    _save()
    digest = hashlib.sha256(f'{ENDPOINT}|{REG}'.encode()).hexdigest()
    assert os.listdir(cache_dir) == [f'{digest}.json']
    assert cache.entry_path(ENDPOINT, REG) == str(cache_dir / f'{digest}.json')


@posix_only
def test_entry_file_is_0600_and_directory_0700(cache_dir):
    _save()
    assert _mode(cache.entry_path(ENDPOINT, REG)) == 0o600
    assert _mode(cache_dir) == 0o700


@posix_only
def test_existing_world_readable_directory_is_tightened(cache_dir):
    cache_dir.mkdir(parents=True)
    os.chmod(cache_dir, 0o755)
    _save()
    assert _mode(cache_dir) == 0o700


@posix_only
def test_entry_is_written_0600_to_a_temp_file_then_renamed(cache_dir):
    seen = {}
    real_replace = os.replace

    def replace(source, destination):
        seen['source'] = source
        seen['mode'] = _mode(source)
        seen['destination'] = destination
        return real_replace(source, destination)

    with patch.object(cache.os, 'replace', side_effect=replace):
        _save()
    assert os.path.dirname(seen['source']) == str(cache_dir)
    assert seen['mode'] == 0o600
    assert seen['destination'] == cache.entry_path(ENDPOINT, REG)
    assert len(os.listdir(cache_dir)) == 1


def test_failed_write_leaves_no_temp_file_and_warns(cache_dir, capsys):
    with patch.object(cache.os, 'replace', side_effect=OSError('disk full')):
        _save()
    assert os.listdir(cache_dir) == []
    err = capsys.readouterr().err
    assert 'Warning' in err
    assert 'disk full' in err
    assert 'fresh sign-in will be needed next time' in err


def test_unwritable_cache_folder_warns(cache_dir, capsys):
    cache_dir.parent.mkdir(parents=True)
    cache_dir.write_text('not a folder')
    _save()
    assert 'fresh sign-in will be needed' in capsys.readouterr().err


def test_registries_and_endpoints_get_separate_entries(cache_dir):
    tokens = {
        (ENDPOINT, REG): make_jwt(sub='a'),
        (ENDPOINT, OTHER_REG): make_jwt(sub='b'),
        (OTHER_ENDPOINT, REG): make_jwt(sub='c'),
    }
    for (endpoint, registry_id), token in tokens.items():
        _save(registry_id, endpoint, token=token)
    assert len(os.listdir(cache_dir)) == 3
    for (endpoint, registry_id), token in tokens.items():
        assert cache.load_token(endpoint, registry_id) == token


def test_entry_fields(cache_dir):
    _save(
        client_id='client',
        issuer='https://idp.example.com/',
        revocation_endpoint='https://idp.example.com/revoke',
        token_endpoint=TOKEN_ENDPOINT,
    )
    entry = json.loads(open(cache.entry_path(ENDPOINT, REG)).read())
    assert set(entry) == {
        'registryId',
        'endpoint',
        'clientId',
        'issuer',
        'accessToken',
        'expiresAt',
        'refreshToken',
        'revocationEndpoint',
        'tokenEndpoint',
    }
    assert entry['registryId'] == REG
    assert entry['endpoint'] == ENDPOINT
    assert entry['issuer'] == 'https://idp.example.com/'


def test_cognito_entry_records_the_pool_region():
    _save(client_id='client', pool_region='us-west-2')
    entry = _entry()
    assert entry['poolRegion'] == 'us-west-2'
    assert 'tokenEndpoint' not in entry


def test_entry_whose_content_names_another_key_is_ignored(cache_dir):
    _save()
    # Moved or copied under another registry's name.
    os.rename(
        cache.entry_path(ENDPOINT, REG), cache.entry_path(ENDPOINT, OTHER_REG)
    )
    assert _entry(OTHER_REG) is None
    assert cache.load_token(ENDPOINT, OTHER_REG) is None


@pytest.mark.parametrize('content', ['not json', '[]', '"x"', ''])
def test_unreadable_entry_is_a_miss(cache_dir, content):
    cache_dir.mkdir(parents=True)
    with open(cache.entry_path(ENDPOINT, REG), 'w') as f:
        f.write(content)
    assert cache.load_token(ENDPOINT, REG) is None


def test_list_entries_returns_entry_files_only(cache_dir):
    _save()
    _save(OTHER_REG)
    (cache_dir / 'notes.json').write_text('{}')
    (cache_dir / '.tmp-abc.json').write_text('{}')
    broken = cache_dir / ('0' * 64 + '.json')
    broken.write_text('not json')
    entries = dict(cache.list_entries())
    assert set(entries) == {
        cache.entry_path(ENDPOINT, REG),
        cache.entry_path(ENDPOINT, OTHER_REG),
        str(broken),
    }
    assert entries[str(broken)] is None
    assert entries[cache.entry_path(ENDPOINT, REG)]['registryId'] == REG


def test_list_entries_and_read_entry_ignore_kept_refresh_tokens(cache_dir):
    _save(client_id='client', revocation_endpoint='https://idp/revoke')
    cache.add_pending_revocation(_entry())
    os.remove(cache.entry_path(ENDPOINT, REG))
    assert os.path.isfile(cache.pending_revocation_path(ENDPOINT, REG))
    assert cache.list_entries() == []
    assert _entry() is None
    assert cache.load_token(ENDPOINT, REG) is None


def test_list_entries_without_a_cache_folder():
    assert cache.list_entries() == []


# --- Client id --------------------------------------------------------------


def test_another_client_id_is_a_miss():
    token = make_jwt()
    _save(token=token, client_id='client-a', token_endpoint=TOKEN_ENDPOINT)
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG, client_id='client-b') is None
    refresh.assert_not_called()
    assert cache.load_token(ENDPOINT, REG, client_id='client-a') == token
    # Without --client-id, the cached sign-in is used whatever its client.
    assert cache.load_token(ENDPOINT, REG) == token


def test_another_client_id_does_not_refresh_an_expired_entry():
    _expired(client_id='client-a')
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG, client_id='client-b') is None
    refresh.assert_not_called()


# --- Expiry -----------------------------------------------------------------


def test_expiry_is_the_earlier_of_expires_in_and_the_token_exp():
    now = int(time.time())
    # id_token cached while expires_in describes a 24 hour access token.
    _save(token=make_jwt(exp=now + 36000), expires_in=86400)
    assert abs(_entry()['expiresAt'] - (now + 36000)) <= 2
    _save(token=make_jwt(exp=now + 86400), expires_in=600)
    assert abs(_entry()['expiresAt'] - (now + 600)) <= 2


@pytest.mark.parametrize(
    'expires_in',
    [
        None,
        'soon',
        '',
        '1h',
        '3600.5',
        [],
        {},
        True,
        -60,
        '-60',
        float('inf'),
        float('nan'),
    ],
)
def test_unusable_expires_in_falls_back_to_the_token_exp(expires_in):
    exp = int(time.time()) + 1800
    _save(token=make_jwt(exp=exp), expires_in=expires_in)
    assert _entry()['expiresAt'] == exp


def test_numeric_string_expires_in_is_used():
    now = int(time.time())
    _save(token=make_jwt(exp=now + 86400), expires_in='600')
    assert abs(_entry()['expiresAt'] - (now + 600)) <= 2


@pytest.mark.parametrize('expires_at', ['soon', None, True, [1]])
def test_unusable_cached_expiry_counts_as_expired(cache_dir, expires_at):
    _save()
    path = cache.entry_path(ENDPOINT, REG)
    entry = json.loads(open(path).read())
    entry['expiresAt'] = expires_at
    with open(path, 'w') as f:
        json.dump(entry, f)
    with patch.object(cache, '_refresh', return_value=(None, None, None)):
        assert cache.load_token(ENDPOINT, REG) is None


# --- Refresh ----------------------------------------------------------------


def test_refresh_with_unusable_expires_in_still_returns_the_token():
    _expired()
    exp = int(time.time()) + 1800
    fresh = make_jwt(exp=exp)
    with patch.object(cache, '_refresh', return_value=(fresh, 'soon', None)):
        assert cache.load_token(ENDPOINT, REG) == fresh
    assert _entry()['expiresAt'] == exp


def test_valid_cached_token_is_used_without_refreshing():
    token = make_jwt()
    _save(token=token)
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) == token
    refresh.assert_not_called()


def test_token_near_expiry_is_refreshed():
    _save(
        token=make_jwt(exp=int(time.time()) + 30),
        expires_in=30,
        token_endpoint=TOKEN_ENDPOINT,
    )
    fresh = make_jwt()
    with patch.object(cache, '_refresh', return_value=(fresh, 3600, None)):
        assert cache.load_token(ENDPOINT, REG) == fresh


def test_cached_encrypted_token_is_treated_as_unusable():
    _save(token=make_jwe(), token_endpoint=TOKEN_ENDPOINT)
    fresh = make_jwt()
    with patch.object(
        cache, '_refresh', return_value=(fresh, 3600, None)
    ) as r:
        assert cache.load_token(ENDPOINT, REG) == fresh
    r.assert_called_once()


def test_refresh_selects_signed_id_token_and_keeps_rotated_refresh_token():
    now = int(time.time())
    _save(
        token=make_jwt(exp=now - 10),
        expires_in=1,
        refresh_token='old-rt',
        client_id='client',
        issuer='https://idp.example.com/',
        revocation_endpoint='https://idp.example.com/revoke',
        token_endpoint=TOKEN_ENDPOINT,
    )
    id_token = make_jwt(exp=now + 36000, aud='client')
    reply = {
        'access_token': make_jwe(),
        'id_token': id_token,
        'expires_in': 86400,
        'refresh_token': 'new-rt',
    }
    with patch.object(cache, 'http_post_form', return_value=reply) as post:
        assert cache.load_token(ENDPOINT, REG, ca_bundle='/corp.pem') == (
            id_token
        )
    assert post.call_args.kwargs['ca_bundle'] == '/corp.pem'
    assert post.call_args.args == (
        TOKEN_ENDPOINT,
        {
            'grant_type': 'refresh_token',
            'refresh_token': 'old-rt',
            'client_id': 'client',
        },
    )
    entry = _entry()
    assert entry['accessToken'] == id_token
    assert entry['refreshToken'] == 'new-rt'
    assert abs(entry['expiresAt'] - (now + 36000)) <= 2
    # Everything the next refresh and sign-out need is carried forward.
    assert entry['tokenEndpoint'] == TOKEN_ENDPOINT
    assert entry['clientId'] == 'client'
    assert entry['issuer'] == 'https://idp.example.com/'
    assert entry['revocationEndpoint'] == 'https://idp.example.com/revoke'


def test_refresh_without_rotation_keeps_existing_refresh_token():
    _expired()
    reply = {'access_token': make_jwt(), 'expires_in': 3600}
    with patch.object(cache, 'http_post_form', return_value=reply):
        cache.load_token(ENDPOINT, REG)
    assert _entry()['refreshToken'] == 'rt'


@pytest.mark.parametrize('rotated', [None, '', 1, ['rt']])
def test_unusable_rotated_refresh_token_keeps_the_existing_one(rotated):
    _expired()
    with patch.object(
        cache, '_refresh', return_value=(make_jwt(), 3600, rotated)
    ):
        cache.load_token(ENDPOINT, REG)
    assert _entry()['refreshToken'] == 'rt'


@pytest.mark.parametrize(
    'code,body',
    [
        (400, None),
        (401, None),
        # Auth0's reply to an unknown or revoked refresh token.
        (
            403,
            b'{"error":"invalid_grant","error_description":"Unknown or '
            b'invalid refresh token."}',
        ),
    ],
    ids=['400', '401', 'auth0-403'],
)
def test_refresh_token_the_provider_rejects_means_sign_in_again(
    capsys, code, body
):
    _expired()
    error = _invalid_grant(code) if body is None else _http_error(code, body)
    with patch.object(cache, 'http_post_form', side_effect=error):
        assert cache.load_token(ENDPOINT, REG) is None
    err = capsys.readouterr().err
    assert err.startswith(
        f'The identity provider no longer accepts the cached sign-in for '
        f'registry {REG} (HTTP {code} from the token endpoint: '
    )
    assert 'invalid_grant' in err
    assert err.strip().endswith('); signing in again.')


@pytest.mark.parametrize(
    'error,shown',
    [
        # A 5xx is the server failing, whatever its body says.
        (
            lambda: _http_error(500, b'{"error": "invalid_grant"}'),
            'HTTP 500 from the token endpoint: {"error": "invalid_grant"}',
        ),
        (lambda: _http_error(503), 'HTTP 503 from the token endpoint)'),
        (
            lambda: _http_error(400, b'{"error": "invalid_client"}'),
            'HTTP 400 from the token endpoint: {"error": "invalid_client"}',
        ),
        (
            lambda: _http_error(400, b'{"error": "invalid_request"}'),
            '"invalid_request"',
        ),
        (
            lambda: _http_error(401, b'{"error": "unauthorized_client"}'),
            '"unauthorized_client"',
        ),
        (
            lambda: _http_error(400, b'<html>invalid_grant</html>'),
            '<html>invalid_grant</html>',
        ),
        (
            lambda: _http_error(400, b'{"error": ["invalid_grant"]}'),
            'HTTP 400 from the token endpoint',
        ),
        # The body could not be read, so its error code is unknown.
        (
            lambda: _http_error(
                400, _UnreadableBody(TimeoutError('The read timed out'))
            ),
            'HTTP 400 from the token endpoint)',
        ),
        (
            lambda: _http_error(
                401, _UnreadableBody(http.client.IncompleteRead(b'{', 10))
            ),
            'HTTP 401 from the token endpoint)',
        ),
        (
            lambda: urllib.error.URLError(socket.timeout('timed out')),
            '(timed out)',
        ),
        (
            lambda: urllib.error.URLError('connection refused'),
            '(connection refused)',
        ),
        (lambda: TimeoutError('The read timed out'), 'The read timed out'),
        (lambda: OSError('Network is unreachable'), 'Network is unreachable'),
        (lambda: http.client.RemoteDisconnected(), 'RemoteDisconnected'),
        (
            lambda: AgentRegistryJWTError(
                'Refusing to follow a redirect (HTTP 302) from '
                f'{TOKEN_ENDPOINT}.'
            ),
            'Refusing to follow a redirect',
        ),
    ],
    ids=[
        '500-invalid-grant',
        '503',
        'invalid-client',
        'invalid-request',
        'unauthorized-client',
        'not-json',
        'error-not-a-string',
        'body-read-timeout',
        'body-incomplete',
        'urlopen-timeout',
        'connection-refused',
        'read-timeout',
        'oserror',
        'disconnected',
        'redirect',
    ],
)
def test_other_refresh_failures_raise_instead_of_signing_in_again(
    capsys, error, shown
):
    _expired()
    with patch.object(cache, 'http_post_form', side_effect=error()):
        with pytest.raises(AgentRegistryJWTError) as e:
            cache.load_token(ENDPOINT, REG)
    _assert_refresh_error(e.value, shown)
    # Kept, so trying again can still refresh it.
    assert _entry()['refreshToken'] == 'rt'
    assert 'signing in again' not in capsys.readouterr().err


@pytest.mark.parametrize(
    'reply,shown',
    [
        ({}, 'returned no access token'),
        ({'access_token': 'opaque'}, 'not a signed JWT'),
        (['not', 'an', 'object'], 'not a JSON object'),
    ],
)
def test_malformed_refresh_reply_raises(reply, shown):
    _expired()
    with patch.object(cache, 'http_post_form', return_value=reply):
        with pytest.raises(AgentRegistryJWTError) as e:
            cache.load_token(ENDPOINT, REG)
    _assert_refresh_error(e.value, shown)


def test_unexpected_refresh_error_raises():
    _expired()
    with patch.object(cache, '_refresh', side_effect=KeyError()):
        with pytest.raises(AgentRegistryJWTError) as e:
            cache.load_token(ENDPOINT, REG)
    _assert_refresh_error(e.value, 'KeyError')


def test_rejected_refresh_text_is_printed_without_control_characters(capsys):
    _expired()
    error = _invalid_grant(description='expired\x1b[2J\x1b]0;title\x07')
    with patch.object(cache, 'http_post_form', side_effect=error):
        assert cache.load_token(ENDPOINT, REG) is None
    err = capsys.readouterr().err
    assert 'invalid_grant' in err
    assert '\x1b' not in err and '\x07' not in err


def test_refresh_error_text_is_raised_without_control_characters():
    _expired()
    error = _http_error(503, b'down\x1b[2J\x1b]0;title\x07' + b'x' * 5000)
    with patch.object(cache, 'http_post_form', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            cache.load_token(ENDPOINT, REG)
    message = str(e.value)
    assert 'down' in message
    assert '\x1b' not in message and '\x07' not in message
    assert len(message) < 600


def test_no_refresh_token_means_sign_in_again():
    _save(token=make_jwt(exp=1), expires_in=1, refresh_token=None)
    assert cache.load_token(ENDPOINT, REG) is None


def test_cognito_refresh_goes_through_the_provider_and_keeps_rotation():
    _expired(client_id='client', pool_region='us-west-2', token_endpoint=None)
    fresh = make_jwt()
    with patch(
        'awscli.customizations.agentregistry.providers.CognitoProvider.refresh',
        return_value=(fresh, 3600, 'rotated-rt'),
    ) as refresh:
        assert (
            cache.load_token(
                ENDPOINT, REG, session=object(), ca_bundle='/corp.pem'
            )
            == fresh
        )
    assert refresh.call_args.args[1]['poolRegion'] == 'us-west-2'
    assert refresh.call_args.args[2] == '/corp.pem'
    entry = _entry()
    assert entry['refreshToken'] == 'rotated-rt'
    assert entry['poolRegion'] == 'us-west-2'


@pytest.mark.parametrize(
    'issuer',
    [None, 'https://attacker.example/us-west-2_AbC123'],
)
def test_cognito_entry_without_a_usable_issuer_is_a_miss(capsys, issuer):
    # Nowhere to send the refresh token, so sign in again rather than fail.
    _expired(
        client_id='client',
        issuer=issuer,
        pool_region='us-west-2',
        token_endpoint=None,
    )
    session = Mock()
    assert cache.load_token(ENDPOINT, REG, session=session) is None
    session.create_client.assert_not_called()
    assert capsys.readouterr().err == ''
    # Left for the sign-in that follows to replace.
    assert _entry()['refreshToken'] == 'rt'


@pytest.mark.parametrize(
    'code',
    [
        'NotAuthorizedException',
        'RefreshTokenReuseException',
        'UserNotFoundException',
    ],
)
def test_cognito_rejecting_the_refresh_token_means_sign_in_again(capsys, code):
    _expired_cognito()
    with patch(COGNITO_REFRESH, side_effect=_cognito_error(code)):
        assert cache.load_token(ENDPOINT, REG, session=object()) is None
    err = capsys.readouterr().err
    assert (
        f'The identity provider no longer accepts the cached sign-in for '
        f'registry {REG} (An error occurred ({code})'
    ) in err
    assert err.strip().endswith('; signing in again.')


@pytest.mark.parametrize(
    'error,shown',
    [
        (
            lambda: _cognito_error('TooManyRequestsException'),
            'TooManyRequestsException',
        ),
        (
            lambda: _cognito_error('InternalErrorException'),
            'InternalErrorException',
        ),
        (lambda: _cognito_error('ForbiddenException'), 'ForbiddenException'),
        (
            lambda: _cognito_error('ResourceNotFoundException'),
            'ResourceNotFoundException',
        ),
        (
            lambda: _cognito_error('InvalidParameterException'),
            'InvalidParameterException',
        ),
        (
            lambda: EndpointConnectionError(
                endpoint_url='https://cognito-idp.us-west-2.amazonaws.com/'
            ),
            'Could not connect to the endpoint URL',
        ),
        (
            lambda: ReadTimeoutError(
                endpoint_url='https://cognito-idp.us-west-2.amazonaws.com/'
            ),
            'Read timeout on endpoint URL',
        ),
    ],
    ids=[
        'throttled',
        'internal',
        'waf',
        'pool-gone',
        'invalid-parameter',
        'connection',
        'read-timeout',
    ],
)
def test_other_cognito_failures_raise_instead_of_signing_in_again(
    error, shown
):
    _expired_cognito()
    with patch(COGNITO_REFRESH, side_effect=error()):
        with pytest.raises(AgentRegistryJWTError) as e:
            cache.load_token(ENDPOINT, REG, session=object())
    _assert_refresh_error(e.value, shown)
    assert _entry()['refreshToken'] == 'rt'


def test_cache_contents_have_no_password_fields():
    _save(client_id='client', token_endpoint=TOKEN_ENDPOINT)
    assert not {'password', 'Password', 'client_secret'} & set(_entry())


def test_list_temp_files(cache_dir):
    assert cache.list_temp_files() == []
    _save()
    leftover = cache_dir / '.tmp-k3j2x9.json'
    leftover.write_text('{}')
    (cache_dir / '.tmp-notes.txt').write_text('x')
    assert cache.list_temp_files() == [str(leftover)]


def test_list_temp_files_covers_kept_refresh_tokens(cache_dir):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    leftover = folder / '.tmp-k3j2x9.json'
    leftover.write_text('{}')
    (folder / '.tmp-notes.txt').write_text('x')
    assert cache.list_temp_files() == [str(leftover)]


def test_keeping_a_token_removes_stale_unfinished_writes_beside_it(cache_dir):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    stale = folder / '.tmp-stale.json'
    stale.write_text('{}')
    os.utime(stale, (1, 1))
    _save(client_id='client', revocation_endpoint='https://idp/revoke')
    cache.add_pending_revocation(_entry())
    assert not stale.exists()


def test_write_removes_stale_unfinished_writes_only(cache_dir):
    cache_dir.mkdir(parents=True)
    stale = cache_dir / '.tmp-stale.json'
    stale.write_text('{"accessToken": "left by a killed write"}')
    old = time.time() - 600
    os.utime(stale, (old, old))
    # Possibly another process's write in progress.
    fresh = cache_dir / '.tmp-fresh.json'
    fresh.write_text('{}')
    _save()
    assert not stale.exists()
    assert fresh.exists()
    assert _entry()['registryId'] == REG


def test_stale_temp_file_that_cannot_be_removed_does_not_stop_the_write(
    cache_dir,
):
    cache_dir.mkdir(parents=True)
    stale = cache_dir / '.tmp-stale.json'
    stale.write_text('{}')
    os.utime(stale, (1, 1))
    real_remove = os.remove

    def remove(path):
        if path == str(stale):
            raise PermissionError('denied')
        return real_remove(path)

    with patch.object(cache.os, 'remove', side_effect=remove):
        _save()
    assert stale.exists()
    assert _entry()['registryId'] == REG


# --- Scopes -----------------------------------------------------------------


def test_scopes_are_stored_with_the_sign_in():
    _save(scopes=['openid', 'registry:read'])
    assert _entry()['scopes'] == ['openid', 'registry:read']


def test_refresh_keeps_the_scopes_and_does_not_send_them():
    _expired(scopes=['openid', 'registry:read'])
    reply = {'access_token': make_jwt(), 'expires_in': 3600}
    with patch.object(cache, 'http_post_form', return_value=reply) as post:
        cache.load_token(ENDPOINT, REG)
    assert 'scope' not in post.call_args.args[1]
    assert _entry()['scopes'] == ['openid', 'registry:read']


# --- Issuer changed ---------------------------------------------------------


def test_refresh_goes_to_the_issuer_the_registry_still_trusts(
    registry_metadata,
):
    _registry(registry_metadata)
    _expired(issuer='https://idp.example.com/')
    fresh = make_jwt()
    with patch.object(
        cache, '_refresh', return_value=(fresh, 3600, None)
    ) as refresh:
        assert cache.load_token(ENDPOINT, REG, ca_bundle='/corp.pem') == fresh
    refresh.assert_called_once()
    assert registry_metadata.call_args.args == (ENDPOINT, REG)
    assert registry_metadata.call_args.kwargs == {'ca_bundle': '/corp.pem'}


def test_changed_issuer_is_a_miss_and_nothing_is_refreshed(
    registry_metadata, capsys
):
    _registry(registry_metadata, issuer='https://new-idp.example.com')
    _expired(issuer='https://idp.example.com')
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) is None
    # The refresh token never goes to the old issuer.
    refresh.assert_not_called()
    assert capsys.readouterr().err.strip() == (
        'The registry now trusts https://new-idp.example.com, not '
        'https://idp.example.com; signing in again.'
    )


def test_unreadable_registry_metadata_lets_the_refresh_go_ahead(
    registry_metadata, caplog
):
    caplog.set_level(logging.DEBUG, logger=cache.__name__)
    _expired(issuer='https://idp.example.com')
    fresh = make_jwt()
    with patch.object(cache, '_refresh', return_value=(fresh, 3600, None)):
        assert cache.load_token(ENDPOINT, REG) == fresh
    registry_metadata.assert_called_once()
    assert 'Could not check the issuer and scopes' in caplog.text


def test_a_valid_token_needs_no_issuer_check(registry_metadata):
    _save(issuer='https://idp.example.com')
    assert cache.load_token(ENDPOINT, REG)
    registry_metadata.assert_not_called()


# --- Scopes advertised in the registry's metadata ---------------------------


def test_newly_advertised_scope_is_a_miss_and_nothing_is_refreshed(
    registry_metadata, capsys
):
    _registry(registry_metadata, scopes=['registry:read'])
    _expired(issuer='https://idp.example.com', scopes=['openid'])
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) is None
    refresh.assert_not_called()
    assert capsys.readouterr().err.strip() == (
        "The registry now asks for scopes the cached sign-in doesn't have; "
        'signing in again.'
    )


def test_entry_without_an_issuer_lacking_an_advertised_scope_is_a_miss(
    registry_metadata, capsys
):
    _registry(registry_metadata, scopes=['registry:read'])
    _expired(scopes=['openid'])
    assert 'issuer' not in _entry()
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) is None
    refresh.assert_not_called()
    assert "asks for scopes the cached sign-in doesn't have" in (
        capsys.readouterr().err
    )


@pytest.mark.parametrize(
    'advertised', [[], ['registry:read'], ['openid', 'registry:read']]
)
def test_unchanged_advertised_scopes_let_the_refresh_go_ahead(
    registry_metadata, advertised
):
    _registry(registry_metadata, scopes=advertised)
    _expired(
        issuer='https://idp.example.com', scopes=['openid', 'registry:read']
    )
    fresh = make_jwt()
    with patch.object(cache, '_refresh', return_value=(fresh, 3600, None)):
        assert cache.load_token(ENDPOINT, REG) == fresh


@pytest.mark.parametrize('scopes', ['registry:read', None, 7, [1, None]])
def test_unusable_stored_scopes_have_no_advertised_scope(
    cache_dir, registry_metadata, scopes
):
    _registry(registry_metadata, scopes=['registry:read'])
    _expired(issuer='https://idp.example.com')
    path = cache.entry_path(ENDPOINT, REG)
    entry = json.loads(open(path).read())
    entry['scopes'] = scopes
    with open(path, 'w') as f:
        json.dump(entry, f)
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) is None
    refresh.assert_not_called()


def test_a_valid_token_is_used_whatever_the_registry_now_advertises(
    registry_metadata,
):
    _registry(registry_metadata, scopes=['registry:read'])
    token = make_jwt()
    _save(token=token, issuer='https://idp.example.com', scopes=['openid'])
    assert cache.load_token(ENDPOINT, REG) == token
    registry_metadata.assert_not_called()


# --- Refreshes in parallel --------------------------------------------------


@pytest.mark.parametrize(
    'error',
    [
        _invalid_grant,
        lambda: _http_error(503),
        lambda: OSError('connection reset'),
        lambda: _cognito_error('RefreshTokenReuseException'),
    ],
    ids=['invalid-grant', '503', 'oserror', 'cognito-reuse'],
)
def test_sign_in_refreshed_by_another_process_meanwhile_is_used(capsys, error):
    _expired(refresh_token='rt-1')
    theirs = make_jwt(sub='other-process')

    def other_process_wins(entry, session, ca_bundle):
        # It refreshed first, which rotated rt-1 away.
        _save(token=theirs, refresh_token='rt-2')
        raise error()

    with patch.object(cache, '_refresh', side_effect=other_process_wins):
        assert cache.load_token(ENDPOINT, REG) == theirs
    assert capsys.readouterr().err == ''
    assert _entry()['refreshToken'] == 'rt-2'


def test_rejected_refresh_with_nothing_newer_signs_in_again(capsys):
    _expired(refresh_token='rt-1')
    with patch.object(cache, '_refresh', side_effect=_invalid_grant()):
        assert cache.load_token(ENDPOINT, REG) is None
    assert 'signing in again' in capsys.readouterr().err


def test_newer_entry_whose_token_has_also_expired_is_not_used(capsys):
    _expired(refresh_token='rt-1')

    def other_process_wrote_a_stale_token(entry, session, ca_bundle):
        _save(token=make_jwt(exp=2), expires_in=1, refresh_token='rt-2')
        raise _invalid_grant()

    with patch.object(
        cache, '_refresh', side_effect=other_process_wrote_a_stale_token
    ):
        assert cache.load_token(ENDPOINT, REG) is None
    assert 'signing in again' in capsys.readouterr().err


@pytest.mark.parametrize(
    'theirs,lookup',
    [
        (
            {'client_id': 'another-client', 'scopes': ['registry:read']},
            {'client_id': 'client'},
        ),
        ({'scopes': ['openid']}, {}),
    ],
    ids=['other-client-id', 'missing-advertised-scope'],
)
def test_sign_in_stored_meanwhile_must_match_like_the_first(
    capsys, registry_metadata, theirs, lookup
):
    _registry(registry_metadata, scopes=['registry:read'])
    _expired(
        refresh_token='rt-1',
        client_id='client',
        issuer='https://idp.example.com',
        scopes=['openid', 'registry:read'],
    )

    def another_sign_in_meanwhile(entry, session, ca_bundle):
        # Fresh, but for another client or without an advertised scope.
        stored = {'client_id': 'client', **theirs}
        _save(token=make_jwt(), refresh_token='rt-2', **stored)
        raise _invalid_grant()

    with patch.object(
        cache, '_refresh', side_effect=another_sign_in_meanwhile
    ):
        assert cache.load_token(ENDPOINT, REG, **lookup) is None
    assert 'signing in again' in capsys.readouterr().err


# --- Read again right before refreshing -------------------------------------


def _meanwhile(metadata, change, readable=True):
    """Have another process ``change`` the entry during the metadata check."""

    def check(*args, **kwargs):
        change()
        if not readable:
            raise AgentRegistryJWTError('not in unit tests')
        return RegistryAuthorization('https://idp.example.com', [])

    metadata.side_effect = check


@pytest.mark.parametrize('readable', [True, False])
def test_sign_in_refreshed_during_the_metadata_check_is_used_as_is(
    registry_metadata, readable
):
    _expired(refresh_token='rt-1', issuer='https://idp.example.com')
    theirs = make_jwt(sub='other-process')
    _meanwhile(
        registry_metadata,
        lambda: _save(
            token=theirs,
            refresh_token='rt-2',
            issuer='https://idp.example.com',
            token_endpoint=TOKEN_ENDPOINT,
        ),
        readable,
    )
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) == theirs
    # rt-1, which the other process spent, is never sent.
    refresh.assert_not_called()
    assert _entry()['refreshToken'] == 'rt-2'


def test_expired_sign_in_written_meanwhile_is_refreshed_with_its_token(
    registry_metadata,
):
    _expired(refresh_token='rt-1', issuer='https://idp.example.com')
    _meanwhile(
        registry_metadata,
        lambda: _expired(
            refresh_token='rt-2', issuer='https://idp.example.com'
        ),
    )
    fresh = make_jwt()
    with patch.object(
        cache, '_refresh', return_value=(fresh, 3600, None)
    ) as refresh:
        assert cache.load_token(ENDPOINT, REG) == fresh
    # The newest refresh token.
    assert refresh.call_args.args[0]['refreshToken'] == 'rt-2'
    assert _entry()['refreshToken'] == 'rt-2'


@pytest.mark.parametrize(
    'change,lookup',
    [
        (lambda: os.remove(cache.entry_path(ENDPOINT, REG)), {}),
        (
            lambda: _expired(
                refresh_token='rt-b',
                client_id='client-b',
                issuer='https://idp.example.com',
                scopes=['openid', 'registry:read'],
            ),
            {'client_id': 'client-a'},
        ),
        (
            lambda: _expired(
                refresh_token='rt-2',
                client_id='client-a',
                issuer='https://idp.example.com',
                scopes=['openid'],
            ),
            {},
        ),
        (
            lambda: _expired(
                refresh_token='rt-2',
                client_id='client-a',
                issuer='https://other-idp.example.com',
                scopes=['openid', 'registry:read'],
            ),
            {},
        ),
    ],
    ids=['signed-out', 'other-client-id', 'missing-scope', 'other-issuer'],
)
def test_entry_changed_during_the_metadata_check_is_a_miss(
    registry_metadata, change, lookup
):
    _expired(
        refresh_token='rt-1',
        client_id='client-a',
        issuer='https://idp.example.com',
        scopes=['openid', 'registry:read'],
    )

    def check(*args, **kwargs):
        change()
        return RegistryAuthorization(
            'https://idp.example.com', ['registry:read']
        )

    registry_metadata.side_effect = check
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG, **lookup) is None
    refresh.assert_not_called()
