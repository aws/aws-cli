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
"""sign-out: revoke the refresh token, then delete the cache entry."""

import argparse
import hashlib
import http.client
import io
import json
import os
import stat
import time
import urllib.error
from unittest.mock import Mock, patch

import botocore.loaders
import botocore.session
import pytest

from awscli.customizations.agentregistry import (
    cache,
    providers,
    sign_out,
    utils,
)
from awscli.customizations.agentregistry.sign_out import SignOutCommand
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agentregistry.utils import make_jwt

ENDPOINT = 'https://agent-registry.us-west-2.api.aws'
OTHER_ENDPOINT = 'https://agent-registry.eu-west-1.api.aws'
REG = 'abcDEF123456'
OTHER_REG = 'xyzXYZ9876543210'
REVOKE = 'https://idp.example.com/oauth2/revoke'
ISSUER = 'https://idp.example.com'

posix_only = pytest.mark.skipif(os.name == 'nt', reason='POSIX modes')


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    directory = tmp_path / 'agent-registry' / 'cache'
    monkeypatch.setattr(cache, 'CACHE_DIR', str(directory))
    return directory


@pytest.fixture
def revoke():
    with patch.object(sign_out, 'http_post_form', return_value=None) as post:
        yield post


def _signed_in(
    registry_id=REG,
    endpoint=ENDPOINT,
    refresh_token='rt',
    revocation_endpoint=REVOKE,
    client_id='client',
):
    cache.save_token(
        endpoint,
        registry_id,
        token=make_jwt(),
        expires_in=3600,
        refresh_token=refresh_token,
        client_id=client_id,
        issuer=ISSUER,
        revocation_endpoint=revocation_endpoint,
        token_endpoint='https://idp.example.com/oauth2/token',
    )
    return cache.entry_path(endpoint, registry_id)


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """An isolated environment with an empty config file."""
    path = tmp_path / 'config'
    path.write_text('')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(path))
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'creds'))
    for name in list(os.environ):
        if name.startswith('AWS_ENDPOINT_URL') or name in (
            'AWS_PROFILE',
            'AWS_DEFAULT_PROFILE',
            'AWS_REGION',
            'AWS_DEFAULT_REGION',
        ):
            monkeypatch.delenv(name)
    return path


def _botocore_session():
    session = botocore.session.Session()
    # Only the models shipped with the CLI, never a local ~/.aws/models
    # overlay.
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[botocore.loaders.Loader.BUILTIN_DATA_PATH],
            include_default_search_paths=False,
        ),
    )
    return session


def _pending(endpoint=ENDPOINT, registry_id=REG):
    """The kept refresh tokens of ``registry_id`` at ``endpoint``, as saved."""
    with open(cache.pending_revocation_path(endpoint, registry_id)) as f:
        return json.load(f)


def _kept(refresh_token='rt', client_id='client'):
    """A refresh token as a failed revocation keeps it."""
    return {
        'refreshToken': refresh_token,
        'revocationEndpoint': REVOKE,
        'clientId': client_id,
        'issuer': ISSUER,
    }


def _fail_to_revoke(*sign_ins):
    """Sign in with each of ``sign_ins`` and fail to sign out of each."""
    for kwargs in sign_ins:
        _signed_in(**kwargs)
        with patch.object(
            sign_out,
            'http_post_form',
            side_effect=urllib.error.URLError('connection refused'),
        ):
            assert _run(kwargs.get('registry_id', REG))[0] == 1


def _run(
    registry_id=None,
    all_=False,
    endpoint_url=None,
    ca_bundle=None,
    session=None,
    region=None,
):
    if session is None:
        session = Mock()
        session.get_config_variable.return_value = None
    command = SignOutCommand(session)
    args = argparse.Namespace(registry_id=registry_id, all=all_)
    globals_ = argparse.Namespace(
        endpoint_url=endpoint_url, ca_bundle=ca_bundle, region=region
    )
    return command._run_main(args, globals_), session


def test_sign_out_revokes_then_deletes(revoke, capsys):
    path = _signed_in()
    rc, session = _run(REG, ca_bundle='/corp.pem')
    assert rc == 0
    assert not os.path.exists(path)
    revoke.assert_called_once_with(
        REVOKE,
        {
            'token': 'rt',
            'token_type_hint': 'refresh_token',
            'client_id': 'client',
        },
        ca_bundle='/corp.pem',
        expect_json=False,
    )
    err = capsys.readouterr().err
    assert err.strip() == (
        f'Registry {REG} at {ENDPOINT}: revoked the refresh token; removed '
        'the sign-in.'
    )
    # No AWS credentials and no AWS client.
    session.create_client.assert_not_called()
    session.get_credentials.assert_not_called()


def test_registry_id_matches_every_endpoint_and_nothing_else(revoke):
    here = _signed_in()
    there = _signed_in(endpoint=OTHER_ENDPOINT)
    other = _signed_in(OTHER_REG)
    assert _run(REG)[0] == 0
    assert not os.path.exists(here)
    assert not os.path.exists(there)
    assert os.path.exists(other)
    assert revoke.call_count == 2


@pytest.mark.parametrize(
    'endpoint_url',
    [
        ENDPOINT,
        ENDPOINT + '/',
        'https://Agent-Registry.US-West-2.api.aws',
        'https://agent-registry.us-west-2.api.aws:443',
        'HTTPS://AGENT-REGISTRY.us-west-2.api.aws:443/',
    ],
)
def test_endpoint_url_narrows_to_the_endpoint_it_resolves_to(
    config_file, revoke, endpoint_url
):
    here = _signed_in()
    there = _signed_in(endpoint=OTHER_ENDPOINT)
    session = _botocore_session()
    with patch.object(session, 'get_credentials') as credentials:
        rc, _ = _run(
            REG,
            endpoint_url=endpoint_url,
            session=session,
            region='us-west-2',
        )
    assert rc == 0
    assert not os.path.exists(here)
    assert os.path.exists(there)
    credentials.assert_not_called()


def test_entry_signed_in_through_an_endpoint_url_matches_its_default_form(
    config_file, revoke
):
    custom = _signed_in(endpoint='https://Registry.Example:443')
    rc, _ = _run(
        REG,
        endpoint_url='https://registry.example/',
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 0
    assert not os.path.exists(custom)


@pytest.mark.parametrize(
    'endpoint_url', [ENDPOINT, 'https://AGENT-registry.us-west-2.api.aws:443/']
)
def test_endpoint_url_without_a_region_is_used_as_given(
    config_file, revoke, endpoint_url
):
    here = _signed_in()
    there = _signed_in(endpoint=OTHER_ENDPOINT)
    rc, _ = _run(REG, endpoint_url=endpoint_url, session=_botocore_session())
    assert rc == 0
    assert not os.path.exists(here)
    assert os.path.exists(there)


@pytest.mark.parametrize(
    'other',
    [
        'https://agent-registry.us-west-2.api.aws:8443',
        'https://agent-registry.us-west-2.api.aws/prefix',
        'https://agent-registry.us-west-2.api.aws.example',
    ],
)
def test_a_different_endpoint_does_not_match(config_file, revoke, other):
    kept = _signed_in(endpoint=other)
    rc, _ = _run(
        REG,
        endpoint_url=ENDPOINT,
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 0
    assert os.path.exists(kept)
    revoke.assert_not_called()


def test_endpoint_url_is_resolved_as_for_the_api_call(revoke):
    path = _signed_in()
    with patch.object(
        sign_out, 'resolve_data_plane_endpoint', return_value=ENDPOINT
    ) as resolve:
        rc, session = _run(
            REG, endpoint_url='https://alias.example', region='us-west-2'
        )
    assert rc == 0
    assert not os.path.exists(path)
    globals_ = resolve.call_args.args[1]
    assert resolve.call_args.args[0] is session
    assert globals_.endpoint_url == 'https://alias.example'
    assert resolve.call_args.args[2] == 'us-west-2'


def test_without_endpoint_url_nothing_is_resolved(revoke):
    _signed_in()
    with patch.object(sign_out, 'resolve_data_plane_endpoint') as resolve:
        _run(REG)
    resolve.assert_not_called()


def test_no_match_at_an_endpoint_names_it(config_file, revoke, capsys):
    kept = _signed_in(endpoint=OTHER_ENDPOINT)
    rc, _ = _run(
        REG,
        endpoint_url=ENDPOINT + ':443/',
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 0
    assert os.path.exists(kept)
    assert capsys.readouterr().err.strip() == (
        f'No cached sign-in for {REG} at {ENDPOINT}:443.'
    )


@pytest.mark.parametrize('region', [None, 'us-west-2'])
def test_plain_http_endpoint_url_is_refused(config_file, revoke, region):
    path = _signed_in()
    with pytest.raises(utils.AgentRegistryJWTError, match='only https'):
        _run(
            REG,
            endpoint_url='http://registry.example',
            session=_botocore_session(),
            region=region,
        )
    assert os.path.exists(path)


@pytest.mark.parametrize('region', [None, 'us-west-2'])
@pytest.mark.parametrize('suffix', ['?x=1', '/#x'])
def test_endpoint_url_with_a_query_or_fragment_is_refused(
    config_file, revoke, region, suffix
):
    path = _signed_in()
    with pytest.raises(utils.AgentRegistryJWTError) as e:
        _run(
            REG,
            endpoint_url=ENDPOINT + suffix,
            session=_botocore_session(),
            region=region,
        )
    assert str(e.value) == (
        f'Refusing registry endpoint {ENDPOINT}: it has a query string or '
        'fragment, and a registry endpoint can only have a scheme, host and '
        'path. Remove the query string or fragment from --endpoint-url.'
    )
    assert os.path.exists(path)
    revoke.assert_not_called()


def test_registry_arn_is_accepted(revoke):
    path = _signed_in()
    arn = f'arn:aws:agent-registry:us-west-2:123456789012:registry/{REG}'
    assert _run(arn)[0] == 0
    assert not os.path.exists(path)


def test_malformed_registry_id_is_refused(revoke):
    path = _signed_in()
    with pytest.raises(
        utils.AgentRegistryJWTError, match='registry identifier'
    ):
        _run('../x')
    assert os.path.exists(path)


def test_entry_without_revocation_endpoint_is_still_removed(
    cache_dir, revoke, capsys
):
    path = _signed_in(revocation_endpoint=None)
    assert _run(REG)[0] == 0
    assert not os.path.exists(path)
    assert not (cache_dir / 'pending-revocation').exists()
    revoke.assert_not_called()
    err = capsys.readouterr().err
    assert err.strip() == (
        f'Registry {REG} at {ENDPOINT}: did not revoke the refresh token '
        '(the identity provider does not advertise a revocation endpoint); '
        'removed the sign-in.'
    )


def test_entry_without_refresh_token_is_still_removed(
    cache_dir, revoke, capsys
):
    path = _signed_in(refresh_token=None)
    assert _run(REG)[0] == 0
    assert not os.path.exists(path)
    assert not (cache_dir / 'pending-revocation').exists()
    revoke.assert_not_called()
    err = capsys.readouterr().err
    assert err.strip() == (
        f'Registry {REG} at {ENDPOINT}: did not revoke the refresh token '
        '(there is no refresh token); removed the sign-in.'
    )


class _UnreadableBody(io.BytesIO):
    def __init__(self, error):
        super().__init__()
        self._error = error

    def read(self, *args):
        raise self._error


@pytest.mark.parametrize(
    'error,shown',
    [
        (
            urllib.error.HTTPError(
                REVOKE,
                400,
                'Bad Request',
                {},
                io.BytesIO(b'{"error": "unsupported_token_type\x1b[2J"}'),
            ),
            'HTTP 400 from the identity provider: {"error": '
            '"unsupported_token_type [2J"}',
        ),
        (
            urllib.error.HTTPError(
                REVOKE, 503, 'Service Unavailable', {}, io.BytesIO(b'')
            ),
            'HTTP 503 from the identity provider',
        ),
        (
            urllib.error.HTTPError(
                REVOKE,
                500,
                'Internal Server Error',
                {},
                _UnreadableBody(TimeoutError('The read operation timed out')),
            ),
            'HTTP 500 from the identity provider',
        ),
        (
            urllib.error.HTTPError(
                REVOKE,
                502,
                'Bad Gateway',
                {},
                _UnreadableBody(http.client.IncompleteRead(b'{"err', 100)),
            ),
            'HTTP 502 from the identity provider',
        ),
        (urllib.error.URLError('connection refused'), 'connection refused'),
        (TimeoutError('timed out'), 'timed out'),
        (
            utils.AgentRegistryJWTError('Refusing to follow a redirect'),
            'Refusing to follow a redirect',
        ),
    ],
)
def test_failed_revocation_keeps_the_refresh_token_and_fails(
    capsys, error, shown
):
    path = _signed_in()
    with patch.object(sign_out, 'http_post_form', side_effect=error):
        assert _run(REG)[0] == 1
    # Signed out of this machine all the same.
    assert not os.path.exists(path)
    assert cache.read_entry(ENDPOINT, REG) is None
    # But the refresh token is kept, to revoke later.
    assert _pending() == {
        'registryId': REG,
        'endpoint': ENDPOINT,
        'tokens': [_kept()],
    }
    err = capsys.readouterr().err
    assert err.strip() == (
        f'Registry {REG} at {ENDPOINT}: could not revoke the refresh token '
        f'({shown}). Removed the sign-in from this machine and kept the '
        'refresh token so the revocation can be retried: run aws '
        f'agent-registry sign-out --registry-id {REG} again.'
    )
    assert '\x1b' not in err


def test_all_tries_every_revocation_and_fails_if_any_failed(cache_dir, capsys):
    paths = [
        _signed_in(),
        _signed_in(OTHER_REG),
        _signed_in(endpoint=OTHER_ENDPOINT),
    ]
    outcomes = [None, urllib.error.URLError('connection refused'), None]
    with patch.object(
        sign_out, 'http_post_form', side_effect=outcomes
    ) as post:
        assert _run(all_=True)[0] == 1
    assert post.call_count == 3
    for path in paths:
        assert not os.path.exists(path)
    err = capsys.readouterr().err
    assert err.count('revoked the refresh token; removed the sign-in.') == 2
    assert err.count('kept the refresh token') == 1
    assert len(cache.list_pending_revocations()) == 1


def test_all_without_a_revocation_endpoint_succeeds(cache_dir, revoke):
    _signed_in(revocation_endpoint=None)
    _signed_in(OTHER_REG, refresh_token=None)
    assert _run(all_=True)[0] == 0
    revoke.assert_not_called()
    assert cache.list_entries() == []


def test_revocation_goes_through_the_https_only_helper(capsys):
    # The real helper: https only, before any connection is made.
    path = _signed_in(revocation_endpoint='http://idp.example.com/revoke')
    with patch.object(utils, '_opener') as opener:
        # Not revoked, so the refresh token is still valid.
        assert _run(REG)[0] == 1
        # Nor when it is retried.
        assert _run(REG)[0] == 1
    opener.assert_not_called()
    assert not os.path.exists(path)
    assert _pending()['tokens'][0]['revocationEndpoint'] == (
        'http://idp.example.com/revoke'
    )
    assert 'only https URLs are allowed' in capsys.readouterr().err


def test_revocation_sends_the_form_with_no_redirects(capsys):
    path = _signed_in()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    with patch.object(utils, '_opener') as opener:
        opener.return_value.open.return_value = response
        assert _run(REG, ca_bundle='/corp.pem')[0] == 0
    opener.assert_called_once_with('/corp.pem')
    request = opener.return_value.open.call_args.args[0]
    assert request.full_url == REVOKE
    assert request.data == (
        b'token=rt&token_type_hint=refresh_token&client_id=client'
    )
    # An empty 200 reply is success; it is never parsed.
    response.read.assert_not_called()
    assert not os.path.exists(path)


def test_all_removes_every_entry(cache_dir, revoke, capsys):
    paths = [
        _signed_in(),
        _signed_in(OTHER_REG),
        _signed_in(endpoint=OTHER_ENDPOINT),
    ]
    unreadable = cache_dir / ('0' * 64 + '.json')
    unreadable.write_text('not json')
    unrelated = cache_dir / 'notes.txt'
    unrelated.write_text('keep')
    assert _run(all_=True)[0] == 0
    for path in paths:
        assert not os.path.exists(path)
    assert not unreadable.exists()
    assert unrelated.exists()
    assert revoke.call_count == 3
    err = capsys.readouterr().err
    assert (
        'Unreadable cache entry: did not revoke the refresh token (the CLI '
        'cannot read the entry); removed the sign-in.'
    ) in err


def test_no_cached_sign_in_for_the_registry(revoke, capsys):
    _signed_in(OTHER_REG)
    assert _run(REG)[0] == 0
    assert capsys.readouterr().err.strip() == f'No cached sign-in for {REG}.'
    revoke.assert_not_called()


def test_nothing_to_sign_out_of(revoke, capsys):
    assert _run(all_=True)[0] == 0
    assert capsys.readouterr().err.strip() == 'Not signed in.'
    revoke.assert_not_called()


def test_all_removes_unfinished_writes(cache_dir, revoke, capsys):
    path = _signed_in()
    leftover = cache_dir / '.tmp-k3j2x9.json'
    leftover.write_text('{"accessToken": "eyJ.a.b"}')
    unrelated = cache_dir / '.tmp-notes.txt'
    unrelated.write_text('keep')
    assert _run(all_=True)[0] == 0
    assert not os.path.exists(path)
    assert not leftover.exists()
    assert unrelated.exists()
    assert f'Removed the unfinished cache write {leftover}.' in (
        capsys.readouterr().err
    )


def test_all_with_only_an_unfinished_write(cache_dir, revoke):
    cache_dir.mkdir(parents=True)
    leftover = cache_dir / '.tmp-abc.json'
    leftover.write_text('{}')
    assert _run(all_=True)[0] == 0
    assert not leftover.exists()


def test_registry_id_leaves_unfinished_writes_alone(cache_dir, revoke):
    _signed_in()
    leftover = cache_dir / '.tmp-abc.json'
    leftover.write_text('{}')
    # A fresh one may belong to a write in progress in another process.
    os.utime(leftover, (time.time(), time.time()))
    _run(REG)
    assert leftover.exists()


@pytest.mark.parametrize('kwargs', [{}, {'registry_id': REG, 'all_': True}])
def test_exactly_one_of_registry_id_and_all(revoke, kwargs):
    path = _signed_in()
    with pytest.raises(ParamValidationError, match='exactly one'):
        _run(**kwargs)
    assert os.path.exists(path)


def test_failure_to_delete_is_reported(revoke, capsys):
    _signed_in()
    with patch.object(
        sign_out.os, 'remove', side_effect=PermissionError('denied')
    ):
        assert _run(REG)[0] == 1
    err = capsys.readouterr().err
    assert 'could not remove' in err
    assert 'denied' in err


def test_help_text():
    names = [arg['name'] for arg in SignOutCommand.ARG_TABLE]
    assert names == ['registry-id', 'all']
    description = SignOutCommand.DESCRIPTION
    assert 'revokes' in description
    assert (
        'If the sign-in has no refresh token, or the identity provider does '
        'not advertise a revocation endpoint, the command deletes the '
        'sign-in, reports why it did not revoke the refresh token, and '
        'succeeds.'
    ) in description
    assert 'sends no requests to AWS' in description
    assert (
        'If a revocation request fails, the command still deletes the '
        'sign-in, so later commands sign in again, but keeps the refresh '
        'token in ``~/.aws/agent-registry/cache/pending-revocation`` and '
        'exits with status 1.'
    ) in description
    assert 'first retries the revocations kept for it' in description
    assert (
        'The command never deletes a file of kept refresh tokens that it '
        "cannot read, or whose contents don't match its name, and reports it "
        'instead. Such a file makes ``--all`` exit with status 1, and makes '
        '``--registry-id`` exit with status 1 if the file is named for that '
        'registry, at any endpoint, even with ``--endpoint-url``. For any '
        'other such file, ``--registry-id`` only warns.'
    ) in description
    assert 'until it expires or you revoke it there' not in description


# --- Refresh tokens kept for a retry ---------------------------------------


def test_the_next_sign_out_revokes_the_kept_token_and_clears_it(
    cache_dir, revoke, capsys
):
    _fail_to_revoke({})
    capsys.readouterr()
    # Nothing is signed in now, but a revocation is pending.
    assert _run(REG)[0] == 0
    revoke.assert_called_once_with(
        REVOKE,
        {
            'token': 'rt',
            'token_type_hint': 'refresh_token',
            'client_id': 'client',
        },
        ca_bundle=None,
        expect_json=False,
    )
    assert os.listdir(cache_dir / 'pending-revocation') == []
    assert capsys.readouterr().err.strip() == (
        f'Registry {REG} at {ENDPOINT}: revoked a refresh token that an '
        'earlier sign-out could not revoke.'
    )
    # Nothing left to do.
    assert _run(REG)[0] == 0
    assert revoke.call_count == 1


def test_a_retry_that_fails_again_keeps_the_token(capsys):
    _fail_to_revoke({})
    capsys.readouterr()
    with patch.object(
        sign_out,
        'http_post_form',
        side_effect=urllib.error.HTTPError(
            REVOKE, 503, 'Unavailable', {}, io.BytesIO(b'')
        ),
    ):
        assert _run(REG)[0] == 1
    assert _pending()['tokens'] == [_kept()]
    assert capsys.readouterr().err.strip() == (
        f'Registry {REG} at {ENDPOINT}: could not revoke a refresh token that '
        'an earlier sign-out could not revoke either (HTTP 503 from the '
        'identity provider). Kept it so the revocation can be retried: run '
        f'aws agent-registry sign-out --registry-id {REG} again.'
    )


def test_several_tokens_can_be_pending_for_one_registry(capsys):
    _fail_to_revoke({'refresh_token': 'rt-1'}, {'refresh_token': 'rt-2'})
    # The second sign-out retried the first token, and failed again.
    assert _pending()['tokens'] == [_kept('rt-1'), _kept('rt-2')]
    capsys.readouterr()
    outcomes = [None, urllib.error.URLError('connection refused')]
    with patch.object(sign_out, 'http_post_form', side_effect=outcomes):
        assert _run(REG)[0] == 1
    assert _pending()['tokens'] == [_kept('rt-2')]
    err = capsys.readouterr().err
    assert err.count('revoked a refresh token that an earlier') == 1
    assert err.count('could not revoke a refresh token') == 1
    with patch.object(sign_out, 'http_post_form', return_value=None):
        assert _run(REG)[0] == 0
    assert cache.list_pending_revocations() == []


def test_retries_come_before_the_sign_in_is_revoked(capsys):
    _fail_to_revoke({'refresh_token': 'old'})
    _signed_in(refresh_token='new')
    with patch.object(sign_out, 'http_post_form', return_value=None) as post:
        assert _run(REG)[0] == 0
    sent = [call.args[1]['token'] for call in post.call_args_list]
    assert sent == ['old', 'new']
    assert cache.list_pending_revocations() == []
    assert cache.list_entries() == []


def test_a_token_is_kept_once(cache_dir):
    _signed_in()
    entry = cache.read_entry(ENDPOINT, REG)
    cache.add_pending_revocation(entry)
    cache.add_pending_revocation(entry)
    assert _pending()['tokens'] == [_kept()]


def test_all_retries_every_kept_token(cache_dir, capsys):
    _fail_to_revoke(
        {},
        {'registry_id': OTHER_REG},
        {'endpoint': OTHER_ENDPOINT, 'refresh_token': 'rt-eu'},
    )
    assert len(cache.list_pending_revocations()) == 3
    assert cache.list_entries() == []
    capsys.readouterr()
    with patch.object(sign_out, 'http_post_form', return_value=None) as post:
        assert _run(all_=True)[0] == 0
    assert post.call_count == 3
    assert cache.list_pending_revocations() == []
    err = capsys.readouterr().err
    assert 'Not signed in' not in err
    assert err.count('revoked a refresh token that an earlier') == 3


def test_all_fails_while_a_kept_token_cannot_be_revoked(capsys):
    _fail_to_revoke({}, {'registry_id': OTHER_REG})
    outcomes = [None, urllib.error.URLError('connection refused')]
    with patch.object(sign_out, 'http_post_form', side_effect=outcomes):
        assert _run(all_=True)[0] == 1
    # The one revoked is gone, and the other kept.
    [(_, document, _)] = cache.list_pending_revocations()
    assert document['tokens'] == [_kept()]


def test_registry_id_retries_only_that_registrys_tokens(revoke):
    _fail_to_revoke({}, {'registry_id': OTHER_REG})
    assert _run(REG)[0] == 0
    assert revoke.call_count == 1
    remaining = cache.list_pending_revocations()
    assert [document['registryId'] for _, document, _ in remaining] == [
        OTHER_REG
    ]


def test_registry_id_retries_the_tokens_of_every_endpoint(revoke):
    _fail_to_revoke({}, {'endpoint': OTHER_ENDPOINT})
    assert _run(REG)[0] == 0
    assert revoke.call_count == 2
    assert cache.list_pending_revocations() == []


@pytest.mark.parametrize(
    'endpoint_url', [ENDPOINT, 'https://AGENT-registry.us-west-2.api.aws:443/']
)
def test_endpoint_url_retries_only_that_endpoints_tokens(
    config_file, revoke, endpoint_url
):
    _fail_to_revoke({}, {'endpoint': OTHER_ENDPOINT})
    rc, _ = _run(
        REG,
        endpoint_url=endpoint_url,
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 0
    assert revoke.call_count == 1
    remaining = cache.list_pending_revocations()
    assert [document['endpoint'] for _, document, _ in remaining] == [
        OTHER_ENDPOINT
    ]


def test_no_sign_in_and_nothing_kept_for_the_registry(revoke, capsys):
    _fail_to_revoke({'registry_id': OTHER_REG})
    capsys.readouterr()
    assert _run(REG)[0] == 0
    assert capsys.readouterr().err.strip() == f'No cached sign-in for {REG}.'
    revoke.assert_not_called()


def test_kept_tokens_are_never_used_to_sign_in(cache_dir):
    _fail_to_revoke({})
    assert cache.read_entry(ENDPOINT, REG) is None
    assert cache.list_entries() == []
    with patch.object(cache, '_refresh') as refresh:
        assert cache.load_token(ENDPOINT, REG) is None
        assert cache.load_token(ENDPOINT, REG, client_id='client') is None
    refresh.assert_not_called()
    # Nor is their client id reused for the next sign-in.
    assert providers._previous_client_id(ENDPOINT, REG, ISSUER) is None


def test_a_new_sign_in_leaves_the_kept_tokens_alone(cache_dir):
    _fail_to_revoke({})
    _signed_in(refresh_token='new')
    assert cache.read_entry(ENDPOINT, REG)['refreshToken'] == 'new'
    assert _pending()['tokens'] == [_kept()]


def test_kept_tokens_are_redacted_from_logs_and_history_when_loaded():
    _fail_to_revoke({'refresh_token': 'kept-refresh-token'})
    with patch.object(cache, 'redact_logs_and_history') as redact:
        cache.list_pending_revocations()
    redact.assert_called_once_with('kept-refresh-token')


@posix_only
def test_kept_tokens_are_0600_in_a_0700_folder(cache_dir):
    _fail_to_revoke({})
    folder = cache_dir / 'pending-revocation'
    assert stat.S_IMODE(os.stat(folder).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(cache_dir).st_mode) == 0o700
    path = cache.pending_revocation_path(ENDPOINT, REG)
    assert os.path.dirname(path) == str(folder)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_a_file_of_kept_tokens_is_named_for_its_registry(cache_dir):
    _fail_to_revoke({})
    digest = hashlib.sha256(f'{ENDPOINT}|{REG}'.encode()).hexdigest()
    path = cache.pending_revocation_path(ENDPOINT, REG)
    assert os.path.basename(path) == f'{REG}.{digest}.json'
    assert os.listdir(cache_dir / 'pending-revocation') == [
        f'{REG}.{digest}.json'
    ]
    assert cache.pending_revocation_registry(path) == REG


@pytest.mark.parametrize(
    'registry_id',
    ['bad.id', 'a/../../x', 'short', 'a' * 17, 'abcDEF12345\n', None, 7],
)
def test_a_registry_id_not_in_bare_form_is_kept_out_of_the_name(
    registry_id,
):
    digest = hashlib.sha256(f'{ENDPOINT}|{registry_id}'.encode()).hexdigest()
    path = cache.pending_revocation_path(ENDPOINT, registry_id)
    assert os.path.basename(path) == f'{digest}.json'
    assert cache.pending_revocation_registry(path) is None


def test_kept_tokens_without_a_registry_in_the_name_are_still_retried(
    cache_dir, revoke
):
    cache.add_pending_revocation(
        {
            'registryId': 'not-a-bare-id',
            'endpoint': ENDPOINT,
            'refreshToken': 'rt',
            'revocationEndpoint': REVOKE,
        }
    )
    [(path, document, problem)] = cache.list_pending_revocations()
    assert problem is None
    assert cache.pending_revocation_registry(path) is None
    assert _run(all_=True)[0] == 0
    revoke.assert_called_once()
    assert cache.list_pending_revocations() == []


@pytest.mark.parametrize(
    'name',
    [
        'notes.json',
        f'{REG}.json',
        f'{REG}.{"0" * 63}.json',
        f'{"a" * 17}.{"0" * 64}.json',
        f'short.{"0" * 64}.json',
        f'{REG}.{"0" * 64}.json.bak',
    ],
)
def test_other_files_in_the_folder_are_not_kept_tokens(cache_dir, name):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    (folder / name).write_text('not json')
    assert cache.list_pending_revocations() == []


@posix_only
def test_kept_tokens_are_written_0600_to_a_temp_file_then_renamed(cache_dir):
    _signed_in()
    folder = cache_dir / 'pending-revocation'
    folder.mkdir()
    os.chmod(folder, 0o755)
    seen = {}
    real_replace = os.replace

    def replace(source, destination):
        seen['source'] = source
        seen['mode'] = stat.S_IMODE(os.stat(source).st_mode)
        return real_replace(source, destination)

    with patch.object(cache.os, 'replace', side_effect=replace):
        cache.add_pending_revocation(cache.read_entry(ENDPOINT, REG))
    assert os.path.dirname(seen['source']) == str(folder)
    assert os.path.basename(seen['source']).startswith('.tmp-')
    assert seen['mode'] == 0o600
    # An existing folder is tightened too.
    assert stat.S_IMODE(os.stat(folder).st_mode) == 0o700
    assert os.listdir(folder) == [
        os.path.basename(cache.pending_revocation_path(ENDPOINT, REG))
    ]


def test_a_token_that_cannot_be_kept_leaves_the_sign_in_in_place(capsys):
    path = _signed_in()
    with (
        patch.object(
            sign_out,
            'http_post_form',
            side_effect=urllib.error.URLError('connection refused'),
        ),
        patch.object(
            cache.tempfile, 'mkstemp', side_effect=OSError('disk full')
        ),
    ):
        assert _run(REG)[0] == 1
    assert os.path.exists(path)
    assert cache.list_pending_revocations() == []
    assert capsys.readouterr().err.strip() == (
        f'Registry {REG} at {ENDPOINT}: could not revoke the refresh token '
        '(connection refused), and could not keep it to retry the revocation '
        'later (disk full). Left the sign-in in place so the revocation can '
        f'be retried: run aws agent-registry sign-out --registry-id {REG} '
        'again.'
    )


def test_a_kept_token_that_is_revoked_but_cannot_be_cleared_fails(
    revoke, capsys
):
    _fail_to_revoke({})
    capsys.readouterr()
    with patch.object(
        cache.os, 'remove', side_effect=PermissionError('denied')
    ):
        assert _run(REG)[0] == 1
    assert _pending()['tokens'] == [_kept()]
    assert 'could not remove the revoked refresh tokens from' in (
        capsys.readouterr().err
    )


def test_a_token_kept_meanwhile_is_not_cleared(cache_dir):
    _fail_to_revoke({'refresh_token': 'rt-1'})
    path = cache.pending_revocation_path(ENDPOINT, REG)
    # Kept by another sign-out after this one read the file.
    _signed_in(refresh_token='rt-2')
    cache.add_pending_revocation(cache.read_entry(ENDPOINT, REG))
    cache.remove_pending_revocations(path, ['rt-1'])
    assert _pending()['tokens'] == [_kept('rt-2')]


def test_all_removes_unfinished_writes_of_kept_tokens(cache_dir, revoke):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    leftover = folder / '.tmp-k3j2x9.json'
    leftover.write_text('{"tokens": [{"refreshToken": "rt"}]}')
    assert _run(all_=True)[0] == 0
    assert not leftover.exists()


_KEY = os.path.basename(cache.pending_revocation_path(ENDPOINT, REG))

# Files of kept refresh tokens that can't be read, or placed under the
# registry and endpoint they name, and why.
_CORRUPT = [
    ('not json', 'it is not valid JSON'),
    ('', 'it is not valid JSON'),
    ('[]', 'it is not a JSON object'),
    ('{}', 'it names no registry or no endpoint'),
    (
        json.dumps({'registryId': REG, 'endpoint': ENDPOINT}),
        'it holds no list of refresh tokens to revoke',
    ),
    (
        json.dumps({'registryId': REG, 'endpoint': ENDPOINT, 'tokens': []}),
        'it holds no list of refresh tokens to revoke',
    ),
    (
        json.dumps(
            {
                'registryId': REG,
                'endpoint': ENDPOINT,
                'tokens': [{'revocationEndpoint': REVOKE}],
            }
        ),
        'it holds no list of refresh tokens to revoke',
    ),
    (
        json.dumps(
            {
                'registryId': REG,
                'endpoint': ENDPOINT,
                'tokens': [dict(_kept(), clientId=7)],
            }
        ),
        'it holds no list of refresh tokens to revoke',
    ),
    (
        json.dumps(
            {
                'registryId': OTHER_REG,
                'endpoint': ENDPOINT,
                'tokens': [_kept()],
            }
        ),
        'its name does not match the registry and endpoint in it',
    ),
]


def _corrupt_file(cache_dir, content):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    corrupt = folder / _KEY
    corrupt.write_text(content)
    return corrupt


def _unreadable_report(path, problem, warning=False):
    return (
        f'{"Warning: could" if warning else "Could"} not read the refresh '
        f'tokens kept for revocation in {path} ({problem}). Left it in '
        'place: check it, and delete it once its refresh tokens are revoked '
        'or have expired.'
    )


@pytest.mark.parametrize('content,problem', _CORRUPT)
def test_a_corrupt_file_of_kept_tokens_fails_all_and_is_kept(
    cache_dir, revoke, capsys, content, problem
):
    corrupt = _corrupt_file(cache_dir, content)
    _signed_in(OTHER_REG)
    assert _run(all_=True)[0] == 1
    assert corrupt.read_text() == content
    # Everything else is still signed out of.
    assert revoke.call_count == 1
    assert cache.list_entries() == []
    err = capsys.readouterr().err
    assert _unreadable_report(corrupt, problem) in err
    assert 'Warning' not in err


@pytest.mark.parametrize('content,problem', _CORRUPT)
def test_a_corrupt_file_named_for_the_registry_fails_its_sign_out(
    cache_dir, revoke, capsys, content, problem
):
    corrupt = _corrupt_file(cache_dir, content)
    path = _signed_in()
    assert _run(REG)[0] == 1
    assert corrupt.read_text() == content
    # The sign-in is signed out of all the same.
    assert not os.path.exists(path)
    revoke.assert_called_once()
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(corrupt, problem),
        f'Registry {REG} at {ENDPOINT}: revoked the refresh token; removed '
        'the sign-in.',
    ]


@pytest.mark.parametrize('content,problem', _CORRUPT)
def test_a_corrupt_file_named_for_another_registry_is_a_warning(
    cache_dir, revoke, capsys, content, problem
):
    corrupt = _corrupt_file(cache_dir, content)
    path = _signed_in(OTHER_REG)
    # Not this registry's, so it can't fail this sign-out.
    assert _run(OTHER_REG)[0] == 0
    assert corrupt.read_text() == content
    assert not os.path.exists(path)
    revoke.assert_called_once()
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(corrupt, problem, warning=True),
        f'Registry {OTHER_REG} at {ENDPOINT}: revoked the refresh token; '
        'removed the sign-in.',
    ]


def test_a_mismatched_file_belongs_to_the_registry_in_its_name(
    cache_dir, revoke, capsys
):
    # REG's tokens, in the file named for OTHER_REG.
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    named = cache.pending_revocation_path(ENDPOINT, OTHER_REG)
    content = json.dumps(
        {'registryId': REG, 'endpoint': ENDPOINT, 'tokens': [_kept()]}
    )
    with open(named, 'w') as f:
        f.write(content)
    problem = 'its name does not match the registry and endpoint in it'
    assert _run(REG)[0] == 0
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(named, problem, warning=True),
        f'No cached sign-in for {REG}.',
    ]
    assert _run(OTHER_REG)[0] == 1
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(named, problem)
    ]
    revoke.assert_not_called()
    assert open(named).read() == content


def test_a_file_named_for_another_endpoint_is_still_the_registrys(
    cache_dir, revoke, capsys
):
    # REG's tokens at OTHER_ENDPOINT, in REG's file for ENDPOINT.
    corrupt = _corrupt_file(
        cache_dir,
        json.dumps(
            {
                'registryId': REG,
                'endpoint': OTHER_ENDPOINT,
                'tokens': [_kept()],
            }
        ),
    )
    assert _run(REG)[0] == 1
    assert capsys.readouterr().err.startswith(
        f'Could not read the refresh '
        f'tokens kept for revocation in {corrupt} (its name does not match'
    )
    revoke.assert_not_called()


@pytest.mark.parametrize(
    'endpoint_url',
    [
        ENDPOINT,
        OTHER_ENDPOINT,
        # Another spelling of ENDPOINT, whose file would have another name.
        'https://AGENT-registry.us-west-2.api.aws:443/',
    ],
)
def test_with_endpoint_url_the_registrys_unreadable_file_still_fails(
    config_file, cache_dir, revoke, capsys, endpoint_url
):
    # Its endpoint can't be read either, so it counts at every endpoint.
    corrupt = _corrupt_file(cache_dir, 'not json')
    rc, _ = _run(
        REG,
        endpoint_url=endpoint_url,
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 1
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(corrupt, 'it is not valid JSON')
    ]
    assert corrupt.read_text() == 'not json'
    revoke.assert_not_called()


def test_with_endpoint_url_another_registrys_unreadable_file_is_a_warning(
    config_file, cache_dir, revoke, capsys
):
    corrupt = _corrupt_file(cache_dir, 'not json')
    rc, _ = _run(
        OTHER_REG,
        endpoint_url=ENDPOINT,
        session=_botocore_session(),
        region='us-west-2',
    )
    assert rc == 0
    assert capsys.readouterr().err.splitlines()[0] == _unreadable_report(
        corrupt, 'it is not valid JSON', warning=True
    )


def test_a_corrupt_file_with_no_registry_in_its_name_is_a_warning(
    cache_dir, revoke, capsys
):
    folder = cache_dir / 'pending-revocation'
    folder.mkdir(parents=True)
    digest = hashlib.sha256(f'{ENDPOINT}|{REG}'.encode()).hexdigest()
    corrupt = folder / f'{digest}.json'
    corrupt.write_text('not json')
    assert _run(REG)[0] == 0
    assert capsys.readouterr().err.splitlines()[0] == _unreadable_report(
        corrupt, 'it is not valid JSON', warning=True
    )
    assert _run(all_=True)[0] == 1
    assert corrupt.read_text() == 'not json'


def test_a_corrupt_file_alone_is_a_warning_for_any_registry(
    cache_dir, revoke, capsys
):
    corrupt = _corrupt_file(cache_dir, 'not json')
    assert _run(OTHER_REG)[0] == 0
    assert corrupt.read_text() == 'not json'
    revoke.assert_not_called()
    assert capsys.readouterr().err.splitlines() == [
        _unreadable_report(corrupt, 'it is not valid JSON', warning=True),
        f'No cached sign-in for {OTHER_REG}.',
    ]


@pytest.mark.parametrize(
    'damage',
    [
        {'refreshToken': ['rt']},
        {'registryId': None},
        {'endpoint': 7},
    ],
)
def test_a_damaged_entry_whose_revocation_fails_is_kept(
    cache_dir, capsys, damage
):
    path = _signed_in()
    with open(path) as f:
        entry = json.load(f)
    entry.update(damage)
    with open(path, 'w') as f:
        json.dump(entry, f)
    with patch.object(
        sign_out,
        'http_post_form',
        side_effect=urllib.error.URLError('connection refused'),
    ):
        assert _run(all_=True)[0] == 1
    assert os.path.exists(path)
    assert cache.list_pending_revocations() == []
    assert 'could not keep it to retry the revocation later' in (
        capsys.readouterr().err
    )


def test_a_corrupt_file_is_not_overwritten_by_a_failed_revocation(
    cache_dir, capsys
):
    corrupt = _corrupt_file(cache_dir, 'not json')
    path = _signed_in()
    with patch.object(
        sign_out,
        'http_post_form',
        side_effect=urllib.error.URLError('connection refused'),
    ):
        assert _run(REG)[0] == 1
    assert corrupt.read_text() == 'not json'
    # The token could not be kept, so the sign-in is.
    assert os.path.exists(path)
    err = capsys.readouterr().err
    assert err.startswith('Could not read the refresh tokens kept')
    assert 'could not keep it to retry the revocation later' in err


@posix_only
@pytest.mark.skipif(
    hasattr(os, 'geteuid') and os.geteuid() == 0, reason='root reads anything'
)
def test_an_unreadable_file_of_kept_tokens_is_reported_and_kept(
    cache_dir, revoke, capsys
):
    _fail_to_revoke({})
    capsys.readouterr()
    path = cache.pending_revocation_path(ENDPOINT, REG)
    os.chmod(path, 0)
    try:
        # The registry's own file: an error, even though it can't be read.
        assert _run(REG)[0] == 1
        own = capsys.readouterr().err
        assert _run(OTHER_REG)[0] == 0
        other = capsys.readouterr().err
        assert _run(all_=True)[0] == 1
        every = capsys.readouterr().err
    finally:
        os.chmod(path, 0o600)
    assert _pending()['tokens'] == [_kept()]
    revoke.assert_not_called()
    assert own.startswith(
        f'Could not read the refresh tokens kept for '
        f'revocation in {path} ([Errno 13] Permission denied'
    )
    assert other.startswith('Warning: could not read the refresh tokens')
    assert every.startswith('Could not read the refresh tokens')


def test_a_folder_of_kept_tokens_that_cannot_be_listed_is_reported(
    cache_dir, revoke, capsys
):
    cache_dir.mkdir(parents=True)
    (cache_dir / 'pending-revocation').write_text('not a folder')
    assert _run(all_=True)[0] == 1
    assert capsys.readouterr().err.startswith(
        'Could not read the refresh tokens kept for revocation in'
    )
    assert _run(REG)[0] == 0
    assert capsys.readouterr().err.startswith(
        'Warning: could not read the refresh tokens kept for revocation in'
    )
    assert (cache_dir / 'pending-revocation').read_text() == 'not a folder'
