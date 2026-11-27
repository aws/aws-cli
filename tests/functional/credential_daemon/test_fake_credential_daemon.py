# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the fake credential daemon that the CLI's credential daemon
tests run against."""

import datetime
import json
import os
import shutil
import socket
import stat
import tempfile
import threading
import time
from pathlib import Path

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from tests.utils.credential_daemon import (
    ACTIVE,
    DEFAULT_ACCOUNT_ID,
    DEFAULT_IAM_USER_PRINCIPAL,
    DEFAULT_PRINCIPAL,
    DEFAULT_START_URL,
    EXPIRED,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    LOGIN_METHOD,
    MAX_LINE_BYTES,
    NO_SESSION,
    PROTOCOL_VERSION,
    FakeCredentialDaemon,
    RawClient,
    RawRpcError,
    identity_credential_name,
)
from tests.utils.credential_daemon.__main__ import main

BOB = f'arn:aws:sts::{DEFAULT_ACCOUNT_ID}:assumed-role/ReadOnly/bob'
SERIAL = 'arn:aws:iam::123456789012:mfa/alice'
CLI = 'aws-cli'


@pytest.fixture
def sock_dir():
    # A short directory for sockets: pytest's tmp_path can pass sun_path's
    # limit (104 bytes on macOS, 108 on Linux), and bind() then fails.
    path = tempfile.mkdtemp(dir='/tmp', prefix='cd')
    yield Path(path)
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def client(fake):
    with RawClient(fake.socket_path) as client:
        yield client


def login(client, name='dev', on_notification=None, **provider):
    provider = dict({'type': 'aws_login', 'region': 'us-west-2'}, **provider)
    return client.call(
        'credential/bootstrap',
        {'credential': name, 'provider': provider, 'creator': CLI},
        on_notification=on_notification,
    )


def login_by_identity(
    client, name_prefix='login.', on_notification=None, **provider
):
    provider = dict({'type': 'aws_login', 'region': 'us-west-2'}, **provider)
    return client.call(
        'credential/bootstrap',
        {'name_prefix': name_prefix, 'provider': provider, 'creator': CLI},
        on_notification=on_notification,
    )


def import_keys(client, name='ci', **extra):
    return client.call(
        'credential/import',
        dict(
            {
                'credential': name,
                'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-east-1',
                'creator': CLI,
            },
            **extra,
        ),
    )


def mfa_login(client, name='ci', code='123456', seen=None):
    def answer(client, notification):
        if seen is not None:
            seen.append(notification)
        client.respond(notification['request_id'], selection=code)

    return client.call(
        LOGIN_METHOD, {'credential': name}, on_notification=answer
    )


def sso_login(client, name='acme', on_notification=None, **provider):
    provider = dict(
        {
            'type': 'sso',
            'start_url': 'https://acme.awsapps.com/start',
            'sso_region': 'us-east-1',
        },
        **provider,
    )
    return client.call(
        'credential/bootstrap',
        {'credential': name, 'provider': provider, 'creator': CLI},
        on_notification=on_notification,
    )


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


NEW_SECRET = 'new-secret-EXAMPLEKEY'


def bootstrap_keys(client, name='ci', **provider):
    provider = dict(
        {
            'type': 'aws_iam_user',
            'access_key_id': 'AKIANEWEXAMPLE123456',
            'secret_access_key': NEW_SECRET,
            'region': 'us-east-1',
        },
        **provider,
    )
    provider = {k: v for k, v in provider.items() if v is not None}
    return client.call(
        'credential/bootstrap',
        {'credential': name, 'provider': provider, 'creator': CLI},
    )


def domain_error(call, *args, **kwargs):
    with pytest.raises(RawRpcError) as e:
        call(*args, **kwargs)
    assert e.value.code == -32000
    return e.value


def eventually(condition, timeout=2):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, 'condition never became true'
        time.sleep(0.01)


class TestProtocol:
    def test_health_reports_protocol(self, client):
        result = client.call('system/health')
        assert result['protocol'] == PROTOCOL_VERSION

    def test_parse_error(self, client):
        client.send_raw(b'not json\n')
        assert client.read()['error']['code'] == -32700

    def test_batches_are_refused(self, client):
        client.send([{'jsonrpc': '2.0', 'id': 1, 'method': 'system/health'}])
        assert client.read()['error']['code'] == -32602

    def test_unknown_method(self, client):
        with pytest.raises(RawRpcError) as e:
            client.call('credential/nope')
        assert e.value.code == -32601

    def test_unknown_params_are_refused(self, client):
        with pytest.raises(RawRpcError) as e:
            client.call(
                'credential/get', {'credential': 'dev', 'environment': 'x'}
            )
        assert e.value.code == -32602

    def test_get_refuses_name(self, client):
        # As the credential daemon does,
        # credential/get takes the credential's name in credential, not name.
        with pytest.raises(RawRpcError) as e:
            client.call('credential/get', {'name': 'dev'})
        assert e.value.code == -32602

    @pytest.mark.parametrize('name', ['.dev', 'me@corp', 'a' * 65, ''])
    def test_invalid_names_are_refused(self, client, name):
        with pytest.raises(RawRpcError) as e:
            client.call('credential/get', {'credential': name})
        assert e.value.code == -32602

    def test_notifications_get_no_response(self, client):
        client.send({'jsonrpc': '2.0', 'method': 'system/health'})
        request_id = client.request('system/health')
        assert client.read()['id'] == request_id

    def test_oversized_message_closes_the_connection(self, client):
        client.send_raw(b'x' * (MAX_LINE_BYTES + 1))
        assert client.read()['error']['code'] == -32600
        with pytest.raises(EOFError):
            client.read()

    def test_progress_carries_the_request_id(self, client):
        request_id = client.request(
            'credential/bootstrap',
            {
                'credential': 'dev',
                'provider': {'type': 'aws_login'},
                'creator': CLI,
            },
        )
        client.wait_for(request_id)
        assert client.notifications[0]['request_id'] == request_id


class TestSocket:
    def test_socket_is_owner_only(self, fake):
        socket_mode = os.stat(fake.socket_path).st_mode
        dir_mode = os.stat(os.path.dirname(fake.socket_path)).st_mode
        assert stat.S_IMODE(socket_mode) == 0o600
        assert stat.S_IMODE(dir_mode) == 0o700

    def test_refuses_a_shared_directory(self, sock_dir):
        shared = sock_dir / 'shared'
        shared.mkdir()
        shared.chmod(0o755)
        with pytest.raises(RuntimeError):
            FakeCredentialDaemon(
                socket_path=str(shared / 'credsd.sock')
            ).start()

    def test_refuses_to_replace_a_running_daemon(self, fake):
        with pytest.raises(RuntimeError):
            FakeCredentialDaemon(socket_path=fake.socket_path).start()

    def test_replaces_a_stale_socket(self, sock_dir):
        directory = sock_dir / 'private'
        directory.mkdir(mode=0o700)
        path = str(directory / 'credsd.sock')
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(path)
        stale.close()
        with FakeCredentialDaemon(socket_path=path) as fake:
            with RawClient(fake.socket_path) as client:
                assert client.call('system/health')['protocol'] == 1

    def test_serve_forever_after_start(self):
        fake = FakeCredentialDaemon().start()
        thread = threading.Thread(target=fake.serve_forever, daemon=True)
        thread.start()
        with RawClient(fake.socket_path) as client:
            assert client.call('system/health')['protocol'] == 1
        fake.stop()
        thread.join(5)
        assert not thread.is_alive()

    def test_stop_removes_the_socket(self):
        fake = FakeCredentialDaemon().start()
        path = fake.socket_path
        fake.stop()
        assert not os.path.exists(path)


class TestStaticKeys:
    def test_get_returns_temporary_credentials_not_the_keys(self, client):
        import_keys(client)
        result = client.call('credential/get', {'credential': 'ci'})
        material = result['material']
        assert material['type'] == 'session_credentials'
        assert material['access_key_id'].startswith('ASIA')
        assert material['account_id'] == DEFAULT_ACCOUNT_ID
        assert 'EXAMPLE' not in json.dumps(material)
        assert result['expires_at'].endswith('Z')

    def test_list_has_no_secrets(self, client):
        import_keys(client)
        rows = client.call('credential/list')['credentials']
        assert rows == [
            {
                'credential': 'ci',
                'kind': 'session_credentials',
                'source': KIND_IAM_USER,
                'status': ACTIVE,
                'tags': {},
            }
        ]

    def test_import_says_imported(self, client):
        result = import_keys(client)
        assert result['credential'] == 'ci'
        assert result['status'] == 'imported'

    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_LOGIN])
    def test_import_skips_a_name_that_exists(self, fake, client, kind):
        fake.seed('ci', kind=kind)
        before = fake.credential('ci')
        assert import_keys(client) == {
            'credential': 'ci',
            'status': 'skipped',
            'reason': 'a credential with this name already exists',
        }
        # Nothing is stored or replaced.
        assert fake.credential('ci') is before

    def test_import_drops_the_mfa_device(self, fake, client):
        # As credsd's ImportProfile does, with no error.
        result = import_keys(client, mfa_serial=SERIAL, duration_seconds=1)
        assert result['status'] == 'imported'
        assert fake.credential('ci').mfa_serial is None
        assert client.call(LOGIN_METHOD, {'credential': 'ci'}) == {}
        client.call('credential/get', {'credential': 'ci'})

    def test_mfa_device_needs_a_login_before_credentials(self, client):
        bootstrap_keys(client, mfa_serial=SERIAL)
        error = domain_error(
            client.call, 'credential/get', {'credential': 'ci'}
        )
        assert error.data_code == 'REAUTH_REQUIRED'

    def test_mfa_session_is_served_until_it_expires(self, fake, client):
        bootstrap_keys(client, mfa_serial=SERIAL, duration_seconds=900)
        seen = []
        # Like the credential daemon's environment/login, the reply has no
        # expiry.
        assert mfa_login(client, seen=seen) == {}
        assert [(n['type'], n['serial']) for n in seen] == [
            ('mfa_required', SERIAL)
        ]
        result = client.call('credential/get', {'credential': 'ci'})
        expires_at = fake.credential('ci').mfa_expires_at
        assert result['expires_at'] == expires_at.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        fake.expire('ci')
        error = domain_error(
            client.call, 'credential/get', {'credential': 'ci'}
        )
        assert error.data_code == 'REAUTH_REQUIRED'

    def test_mfa_code_is_redacted_from_recorded_calls(self, fake, client):
        bootstrap_keys(client, mfa_serial=SERIAL)
        mfa_login(client)
        [answer] = [p for m, p in fake.calls if m.endswith('/respond')]
        assert answer['selection'] == '<redacted>'

    def test_login_without_a_device_does_nothing(self, client):
        import_keys(client)
        assert client.call(LOGIN_METHOD, {'credential': 'ci'}) == {}
        client.call('credential/get', {'credential': 'ci'})

    def test_wrong_mfa_code_is_an_internal_error(self, client):
        bootstrap_keys(client, mfa_serial=SERIAL)
        for code in ('000000', '12'):
            error = domain_error(mfa_login, client, code=code)
            assert error.data_code == 'INTERNAL'
            assert error.message == (
                'provider error: MultiFactorAuthentication failed with '
                'invalid MFA one time pass code.'
            )
        error = domain_error(
            client.call, 'credential/get', {'credential': 'ci'}
        )
        assert error.data_code == 'REAUTH_REQUIRED'

    def test_login_on_an_aws_login_credential_starts_its_sign_in(self, client):
        login(client)
        seen = []

        def note(client, notification):
            seen.append(notification['type'])

        assert (
            client.call(
                LOGIN_METHOD, {'credential': 'dev'}, on_notification=note
            )
            == {}
        )
        assert seen == ['authorize_url']

    def test_login_as_another_principal_is_an_identity_mismatch(
        self, fake, client
    ):
        # As credsd's login_identity_check: nothing is saved.
        login(client)
        fake.next_principal = BOB
        error = domain_error(client.call, LOGIN_METHOD, {'credential': 'dev'})
        assert error.data_code == 'IDENTITY_MISMATCH'
        assert error.message == (
            f"credential 'dev' signed in as role ReadOnly in account "
            f'{DEFAULT_ACCOUNT_ID}, but it is recorded for role Admin in '
            f'account {DEFAULT_ACCOUNT_ID}; nothing was saved. Signing in as '
            'another account or role replaces the credential, which needs '
            "approval: re-run 'creds bootstrap --credential dev' with its "
            'aws-login provider'
        )
        assert fake.credential('dev').principal == DEFAULT_PRINCIPAL
        assert fake.approval_requests() == []

    def test_login_on_a_credential_with_no_record_is_a_mismatch(
        self, fake, client
    ):
        fake.seed('dev', principal=None)
        error = domain_error(client.call, LOGIN_METHOD, {'credential': 'dev'})
        assert error.data_code == 'IDENTITY_MISMATCH'
        assert 'but it has no recorded sign-in; nothing was saved' in (
            error.message
        )

    def test_login_as_the_same_principal_records_the_new_session(
        self, fake, client
    ):
        login(client)
        fake.next_principal = DEFAULT_PRINCIPAL.replace('/alice', '/alice-2')
        assert client.call(LOGIN_METHOD, {'credential': 'dev'}) == {}
        assert fake.credential('dev').principal == fake.next_principal

    def test_login_on_an_sso_credential_renews_it_unattended(
        self, fake, client
    ):
        # As credsd's login_sso: the refresh token renews it, with no
        # device code and no approval.
        sso_login(client)
        fake.expire('acme')
        seen = []

        def note(client, notification):
            seen.append(notification['type'])

        assert (
            client.call(
                LOGIN_METHOD, {'credential': 'acme'}, on_notification=note
            )
            == {}
        )
        assert seen == []
        assert fake.credential('acme').status == ACTIVE
        assert fake.approval_requests() == []
        client.call(
            'credential/get',
            {
                'credential': 'acme',
                'account_id': '111111111111',
                'role_name': 'Admin',
            },
        )

    @pytest.mark.parametrize('status', ['no_session', 'sign_in_required'])
    def test_login_on_a_spent_sso_credential_shows_a_device_code(
        self, fake, client, status
    ):
        fake.seed('acme', kind=KIND_SSO, principal=None, status=status)
        seen = []

        def note(client, notification):
            seen.append(notification)

        assert (
            client.call(
                LOGIN_METHOD, {'credential': 'acme'}, on_notification=note
            )
            == {}
        )
        assert [n['type'] for n in seen] == ['device_code']
        assert seen[0]['user_code']
        assert seen[0]['verification_uri']
        assert fake.credential('acme').status == ACTIVE

    def test_login_on_signed_out_keys_is_not_found(self, fake, client):
        fake.seed(
            'ci', kind=KIND_IAM_USER, mfa_serial=SERIAL, status='no_session'
        )
        error = domain_error(mfa_login, client)
        assert error.data_code == 'CREDENTIAL_NOT_FOUND'

    def test_list_rows_say_each_credentials_source(self, fake):
        # As credsd's CredentialSummary with credential tags: the kind is the
        # same for all three, the source says what each holds, and no row has
        # a creator.
        fake.seed('dev', kind=KIND_LOGIN)
        fake.seed('ci', kind=KIND_IAM_USER)
        fake.seed('acme', kind=KIND_SSO, principal=None)
        with RawClient(fake.socket_path) as client:
            rows = client.call('credential/list', {})['credentials']
        assert [(r['credential'], r['kind'], r['source']) for r in rows] == [
            ('acme', 'session_credentials', KIND_SSO),
            ('ci', 'session_credentials', KIND_IAM_USER),
            ('dev', 'session_credentials', KIND_LOGIN),
        ]
        for row in rows:
            assert row['tags'] == {}
            assert 'creator' not in row

    def test_get_sends_credential_daemons_material_kind(self, fake):
        fake.seed('keys.ci', kind=KIND_IAM_USER)
        with RawClient(fake.socket_path) as client:
            result = client.call('credential/get', {'credential': 'keys.ci'})
        assert result['kind'] == 'session_credentials'
        assert 'source' not in result

    def test_iam_user_bootstrap_checks_the_mfa_session_length(self, client):
        for duration in (899, 129601, '900'):
            with pytest.raises(RawRpcError) as e:
                bootstrap_keys(
                    client, mfa_serial=SERIAL, duration_seconds=duration
                )
            assert e.value.code == -32602

    def test_backing_profile_supplies_the_credentials(
        self, tmp_path, monkeypatch
    ):
        credentials_file = tmp_path / 'credentials'
        credentials_file.write_text(
            '[backing]\n'
            'aws_access_key_id = AKIDBACKING\n'
            'aws_secret_access_key = backing-secret\n'
        )
        monkeypatch.setenv(
            'AWS_SHARED_CREDENTIALS_FILE', str(credentials_file)
        )
        monkeypatch.setenv('AWS_CONFIG_FILE', str(tmp_path / 'config'))
        with FakeCredentialDaemon(backing_profile='backing') as fake:
            with RawClient(fake.socket_path) as client:
                import_keys(client)
                result = client.call('credential/get', {'credential': 'ci'})
        assert result['material']['access_key_id'] == 'AKIDBACKING'
        assert result['material']['secret_access_key'] == 'backing-secret'

    def test_a_region_that_isnt_a_string_is_refused(self, client):
        with pytest.raises(RawRpcError) as e:
            import_keys(client, region=None)
        assert e.value.code == -32602

    def test_import_without_a_region_is_refused(self, fake, client):
        params = {
            'credential': 'ci',
            'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'secret_access_key': 'secret',
        }
        with pytest.raises(RawRpcError) as e:
            client.call('credential/import', params)
        assert e.value.code == -32602
        assert 'missing field `region`' in str(e.value)
        assert fake.credential('ci') is None

    def test_import_takes_any_region_string(self, fake, client):
        import_keys(client, region='no_network')
        assert fake.credential('ci') is not None

    def test_secrets_are_redacted_from_recorded_calls(self, fake, client):
        import_keys(client)
        method, params = fake.calls[-1]
        assert method == 'credential/import'
        assert params['secret_access_key'] == '<redacted>'

    def test_iam_user_bootstrap_stores_a_new_name(self, fake, client):
        assert bootstrap_keys(client, mfa_serial=SERIAL) == {}
        credential = fake.credential('ci')
        assert credential.kind == KIND_IAM_USER
        assert credential.secrets['secret_access_key'] == NEW_SECRET
        assert credential.mfa_serial == SERIAL
        assert not fake.approval_requests()

    def test_iam_user_bootstrap_over_a_name_needs_approval(self, fake, client):
        import_keys(client)
        before = fake.credential('ci')
        error = domain_error(bootstrap_keys, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert isinstance(error.data['challenge'], dict)
        request_id = error.data['challenge']['id']
        assert error.data['remediation'].endswith(request_id)
        assert fake.approval_requests() == [request_id]
        # Nothing changes until it's approved.
        assert fake.credential('ci') is before

    def test_approved_iam_user_bootstrap_replaces_the_keys(self, fake, client):
        import_keys(client)
        domain_error(bootstrap_keys, client)
        fake.approve()
        assert bootstrap_keys(client) == {}
        assert fake.credential('ci').secrets['secret_access_key'] == NEW_SECRET
        # An approval is used once.
        error = domain_error(bootstrap_keys, client)
        assert error.data_code == 'APPROVAL_REQUIRED'

    def test_approval_is_for_the_same_params_only(self, fake, client):
        import_keys(client)
        domain_error(bootstrap_keys, client)
        fake.approve()
        error = domain_error(bootstrap_keys, client, region='eu-west-1')
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert fake.credential('ci').secrets['secret_access_key'] != NEW_SECRET

    def test_approve_over_rpc(self, fake, client):
        import_keys(client)
        error = domain_error(bootstrap_keys, client)
        request_id = error.data['challenge']['id']
        assert client.call('mock/approve', {}) == {'request_id': request_id}
        assert bootstrap_keys(client) == {}

    def test_iam_user_bootstrap_needs_a_region(self, client):
        with pytest.raises(RawRpcError) as e:
            bootstrap_keys(client, region=None)
        assert e.value.code == -32602
        assert e.value.message == 'missing field `region`'

    def test_iam_user_bootstrap_refuses_unknown_fields(self, client):
        with pytest.raises(RawRpcError) as e:
            bootstrap_keys(client, session_token='x')
        assert e.value.code == -32602

    def test_iam_user_bootstrap_keys_are_redacted(self, fake, client):
        bootstrap_keys(client)
        [(method, params)] = fake.calls
        assert method == 'credential/bootstrap'
        assert params['provider']['access_key_id'] == '<redacted>'
        assert params['provider']['secret_access_key'] == '<redacted>'


class TestTags:
    # credsd's credential tags.
    TAGS = {'created-by': 'aws-cli'}

    def rows(self, client, **params):
        return {
            row['credential']: row['tags']
            for row in client.call('credential/list', params)['credentials']
        }

    def store_keys(self, client, **params):
        provider = {
            'type': 'aws_iam_user',
            'access_key_id': 'AKIANEWEXAMPLE123456',
            'secret_access_key': NEW_SECRET,
            'region': 'us-east-1',
        }
        return client.call(
            'credential/bootstrap',
            dict({'credential': 'ci', 'provider': provider}, **params),
        )

    def test_bootstrap_sets_exactly_its_tags(self, fake, client):
        fake.seed('ci', kind=KIND_IAM_USER, tags={'team': 'pay'})
        with pytest.raises(RawRpcError):
            self.store_keys(client, tags=self.TAGS)
        fake.approve()
        self.store_keys(client, tags=self.TAGS)
        assert self.rows(client) == {'ci': self.TAGS}

    @pytest.mark.parametrize('params', [{}, {'tags': None}])
    def test_bootstrap_without_tags_keeps_them(self, fake, client, params):
        fake.seed('ci', kind=KIND_IAM_USER, tags=self.TAGS)
        with pytest.raises(RawRpcError):
            self.store_keys(client, **params)
        fake.approve()
        self.store_keys(client, **params)
        assert self.rows(client) == {'ci': self.TAGS}

    def test_a_new_credential_without_tags_has_none(self, client):
        self.store_keys(client)
        assert self.rows(client) == {'ci': {}}

    def test_sign_ins_set_their_tags(self, fake, client):
        client.call(
            'credential/bootstrap',
            {
                'credential': 'dev',
                'provider': {'type': 'aws_login', 'region': 'us-west-2'},
                'tags': self.TAGS,
            },
        )
        login_by_identity(client)
        assert self.rows(client) == {
            'dev': self.TAGS,
            identity_credential_name('login.', DEFAULT_PRINCIPAL): {},
        }

    def test_bootstrap_folds_keys_and_keeps_values(self, client):
        self.store_keys(client, tags={'Created-By': 'AWS-CLI'})
        assert self.rows(client) == {'ci': {'created-by': 'AWS-CLI'}}

    @pytest.mark.parametrize(
        'tags',
        [
            {'-x': 'y'},
            {'a b': 'y'},
            {'k' * 64: 'y'},
            {'x': 'tab\there'},
            {'x': 'v' * 257},
            {'x': 1},
            {'Env': 'a', 'env': 'b'},
            {f'k{i}': 'v' for i in range(33)},
            ['created-by'],
        ],
    )
    def test_bad_bootstrap_tags_are_refused(self, client, tags):
        with pytest.raises(RawRpcError) as e:
            self.store_keys(client, tags=tags)
        assert e.value.code == -32602
        assert 'tag' in str(e.value)
        assert self.rows(client) == {}

    def test_list_filters_by_every_pair(self, fake, client):
        fake.seed('a', tags={'created-by': 'aws-cli', 'team': 'pay'})
        fake.seed('b', tags={'created-by': 'other'})
        fake.seed('c')
        assert list(self.rows(client, tags={'created-by': 'aws-cli'})) == ['a']
        assert list(self.rows(client, tags={'Created-By': None})) == [
            'a',
            'b',
        ]
        assert (
            self.rows(client, tags={'created-by': 'aws-cli', 'x': None}) == {}
        )
        assert list(self.rows(client, tags={})) == ['a', 'b', 'c']

    @pytest.mark.parametrize(
        'tags', [{'-x': 'y'}, {'x': 'tab\there'}, {'X': 'a', 'x': 'a'}, []]
    )
    def test_bad_list_filter_is_refused(self, fake, client, tags):
        fake.seed('a')
        with pytest.raises(RawRpcError) as e:
            client.call('credential/list', {'tags': tags})
        assert e.value.code == -32602

    def test_tag_sets_then_unsets_with_no_approval(self, fake, client):
        fake.seed('a', tags={'created-by': 'aws-cli', 'team': 'pay'})
        assert (
            client.call(
                'credential/tag',
                {
                    'credential': 'a',
                    'set': {'Stage': 'prod'},
                    'unset': ['team', 'missing'],
                },
            )
            == {}
        )
        assert self.rows(client) == {
            'a': {'created-by': 'aws-cli', 'stage': 'prod'}
        }

    @pytest.mark.parametrize(
        'params',
        [
            {'set': {'env': 'a'}, 'unset': ['Env']},
            {'set': {'-x': 'a'}},
            {'unset': ['-x']},
            {'set': {f'k{i}': 'v' for i in range(32)}},
        ],
    )
    def test_bad_tag_edits_change_nothing(self, fake, client, params):
        fake.seed('a', tags={'created-by': 'aws-cli'})
        with pytest.raises(RawRpcError) as e:
            client.call('credential/tag', dict(params, credential='a'))
        assert e.value.code == -32602
        assert self.rows(client) == {'a': {'created-by': 'aws-cli'}}

    def test_tag_on_an_unknown_credential(self, client):
        error = domain_error(
            client.call, 'credential/tag', {'credential': 'a', 'unset': ['x']}
        )
        assert error.data['code'] == 'CREDENTIAL_NOT_FOUND'

    def test_logout_keeps_tags(self, fake, client):
        fake.seed('a', tags={'created-by': 'aws-cli'})
        client.call('credential/logout', {'credential': 'a'})
        assert self.rows(client) == {'a': {'created-by': 'aws-cli'}}


class TestLogout:
    def test_logout_keeps_the_entry_and_principal(self, fake, client):
        login(client)
        client.call('credential/logout', {'credential': 'dev'})
        [row] = client.call('credential/list')['credentials']
        assert row['status'] == NO_SESSION
        # Rows don't carry it, but the credential keeps who it was.
        assert fake.credential('dev').principal == DEFAULT_PRINCIPAL
        error = domain_error(
            client.call, 'credential/get', {'credential': 'dev'}
        )
        assert error.data_code == 'REAUTH_REQUIRED'
        assert 'remediation' in error.data

    def test_logout_says_whether_it_signed_out(self, client):
        # credsd's shape: signed_out is false only with none.
        login(client)
        result = client.call('credential/logout', {'credential': 'dev'})
        assert result == {'signed_out': True, 'provider': 'local_only'}
        result = client.call('credential/logout', {'credential': 'dev'})
        assert result == {'signed_out': False, 'provider': 'none'}

    @pytest.mark.parametrize('kind', [KIND_LOGIN, KIND_SSO])
    def test_logout_signs_out_sign_in_sources(self, fake, client, kind):
        fake.seed('dev', kind=kind)
        client.call('credential/logout', {'credential': 'dev'})
        assert fake.credential('dev').status == NO_SESSION

    def test_sso_logout_ends_the_session_at_sso(self, fake, client):
        fake.seed('acme', kind=KIND_SSO)
        result = client.call('credential/logout', {'credential': 'acme'})
        assert result == {'signed_out': True, 'provider': 'ended'}

    def test_sso_logout_whose_token_sso_rejected(self, fake, client):
        fake.seed('acme', kind=KIND_SSO)
        fake.set_sso_logout('token_rejected')
        result = client.call('credential/logout', {'credential': 'acme'})
        assert result == {'signed_out': True, 'provider': 'token_rejected'}

    def test_failed_sso_logout_says_where_to_sign_out(self, fake, client):
        # The local session is still deleted.
        credential = fake.seed('acme', kind=KIND_SSO)
        expires_at = credential.session_expires_at
        fake.set_sso_logout('failed')
        result = client.call('credential/logout', {'credential': 'acme'})
        assert result == {
            'signed_out': True,
            'provider': 'failed',
            'start_url': DEFAULT_START_URL,
            'access_token_expires_at': expires_at.astimezone(
                datetime.timezone.utc
            ).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        assert fake.credential('acme').status == NO_SESSION

    def test_failed_sso_logout_names_the_credentials_start_url(
        self, fake, client
    ):
        fake.seed('acme', kind=KIND_SSO)
        fake.credential('acme').provider['start_url'] = (
            'https://acme.awsapps.com/start'
        )
        fake.set_sso_logout('failed', access_token_expires_at=None)
        result = client.call('credential/logout', {'credential': 'acme'})
        # No expiry when the token can't be read.
        assert result == {
            'signed_out': True,
            'provider': 'failed',
            'start_url': 'https://acme.awsapps.com/start',
        }

    def test_sso_logout_of_a_signed_out_session_sends_nothing(
        self, fake, client
    ):
        fake.seed('acme', kind=KIND_SSO, status=NO_SESSION)
        fake.set_sso_logout('failed')
        result = client.call('credential/logout', {'credential': 'acme'})
        assert result == {'signed_out': False, 'provider': 'none'}

    def test_reset_ends_sso_sessions_again(self, fake, client):
        fake.set_sso_logout('failed')
        fake.reset()
        fake.seed('acme', kind=KIND_SSO)
        result = client.call('credential/logout', {'credential': 'acme'})
        assert result['provider'] == 'ended'

    def test_unknown_sso_logout_result(self, fake):
        with pytest.raises(ValueError):
            fake.set_sso_logout('local_only')

    def test_logout_refuses_access_keys(self, fake, client):
        # As credsd does: keys have no sign-in to log out of.
        import_keys(client)
        error = domain_error(
            client.call, 'credential/logout', {'credential': 'ci'}
        )
        assert error.data_code == 'LOGOUT_UNSUPPORTED_SOURCE'
        assert 'no sign-in to log out of' in str(error)
        assert fake.credential('ci').status == ACTIVE

    def test_logout_refuses_name(self, client):
        login(client)
        with pytest.raises(RawRpcError) as e:
            client.call('credential/logout', {'name': 'dev'})
        assert e.value.code == -32602

    @pytest.mark.parametrize(
        'source',
        ['unsupported', 'aws_roles_anywhere', 'static_secret'],
    )
    def test_other_sources_are_listed_and_not_logged_out(
        self, fake, client, source
    ):
        # Sources the CLI never creates: the row says what it is, and
        # logout refuses it, as credsd does for anything but a sign-in.
        fake.seed('other', kind=source)
        [row] = client.call('credential/list')['credentials']
        assert row['source'] == source
        error = domain_error(
            client.call, 'credential/logout', {'credential': 'other'}
        )
        assert error.data_code == 'LOGOUT_UNSUPPORTED_SOURCE'
        assert fake.credential('other').status == ACTIVE

    def test_web_identity_is_logged_out(self, fake, client):
        fake.seed('wif', kind='aws_web_identity')
        result = client.call('credential/logout', {'credential': 'wif'})
        assert result['signed_out'] is True
        assert fake.credential('wif').status == NO_SESSION

    def test_remove_deletes_the_credential(self, fake, client):
        import_keys(client)
        assert client.call('credential/remove', {'credential': 'ci'}) == {}
        assert fake.credential('ci') is None
        assert client.call('credential/list')['credentials'] == []

    @pytest.mark.parametrize(
        'method', ['credential/get', 'credential/logout', 'credential/remove']
    )
    def test_unknown_name(self, client, method):
        error = domain_error(client.call, method, {'credential': 'nope'})
        assert error.data_code == 'CREDENTIAL_NOT_FOUND'


class TestLogin:
    def test_local_sign_in(self, client):
        result = login(client)
        # credsd's shape: the name and who signed in, no expiry.
        assert result == {
            'credential': 'dev',
            'identity': {
                'arn': DEFAULT_PRINCIPAL,
                'partition': 'aws',
                'account': DEFAULT_ACCOUNT_ID,
                'kind': 'role',
                'name': 'Admin',
                'session': 'alice',
            },
        }
        [notification] = client.notifications
        assert notification['type'] == 'authorize_url'
        assert notification['url'].startswith(
            'https://us-west-2.signin.aws.amazon.com/v1/authorize?'
        )
        result = client.call('credential/get', {'credential': 'dev'})
        assert result['material']['account_id'] == DEFAULT_ACCOUNT_ID

    def test_get_names_the_credential_in_credential(self, client):
        login(client)
        result = client.call('credential/get', {'credential': 'dev'})
        assert result['credential'] == 'dev'
        assert 'name' not in result
        assert result['provenance'] == 'cached_shared'

    def test_listens_on_the_callback_port(self):
        port = free_port()
        with FakeCredentialDaemon(signin='manual') as fake:
            with RawClient(fake.socket_path) as client:
                request_id = client.request(
                    'credential/bootstrap',
                    {
                        'credential': 'dev',
                        'provider': {
                            'type': 'aws_login',
                            'region': 'us-west-2',
                            'callback_port': port,
                        },
                        'creator': CLI,
                    },
                )
                url = client.read()['params']['url']
                assert (
                    f'redirect_uri=http%3A%2F%2F127.0.0.1%3A{port}%2F' in url
                )
                socket.create_connection(('127.0.0.1', port), 1).close()
                fake.complete_signin('dev')
                assert client.wait_for(request_id)['credential'] == 'dev'
        with pytest.raises(OSError):
            socket.create_connection(('127.0.0.1', port), 1)

    def test_callback_port_in_use(self, client):
        with socket.socket() as taken:
            taken.bind(('127.0.0.1', 0))
            taken.listen(1)
            port = taken.getsockname()[1]
            error = domain_error(login, client, callback_port=port)
        assert error.data_code == 'REDIRECT_PORT_IN_USE'

    @pytest.mark.parametrize('port', [0, 80, 1023, 65536])
    def test_refuses_a_callback_port_outside_1024_to_65535(self, client, port):
        # As real credsd does (bootstrap.rs, 066082d).
        with pytest.raises(RawRpcError) as e:
            login(client, callback_port=port)
        assert e.value.code == -32602
        assert e.value.message == (
            'callback_port must be 1024\u201365535; omit the field for an '
            'ephemeral port'
        )
        assert client.notifications == []

    def test_same_person_signs_in_again_without_a_prompt(self, client):
        login(client)
        login(client)
        types = [n['type'] for n in client.notifications]
        assert types == ['authorize_url', 'authorize_url']

    def test_a_different_person_needs_approval(self, fake, client):
        # As credsd: checked after the sign-in, with no progress
        # message, and nothing saved.
        login(client)
        fake.next_principal = BOB
        error = domain_error(login, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert set(error.data) == {'code', 'challenge', 'remediation'}
        challenge = error.data['challenge']
        assert challenge['description'] == (
            "replace existing credential 'dev' with a new aws-login (region "
            'us-west-2) signed in as role ReadOnly in account '
            f'{DEFAULT_ACCOUNT_ID} (aws); it was role Admin in account '
            f'{DEFAULT_ACCOUNT_ID} (aws)'
        )
        assert error.data['remediation'] == (
            'this sign-in is for a different account or role than the '
            'credential records, so nothing was saved. sudo creds request '
            f'approve {challenge["id"]}, then re-run the same bootstrap and '
            'sign in as the same account and role again'
        )
        assert [n['type'] for n in client.notifications] == [
            'authorize_url',
            'authorize_url',
        ]
        assert fake.credential('dev').principal == DEFAULT_PRINCIPAL

    def test_an_approved_change_is_saved_on_the_re_run(self, fake, client):
        login(client)
        fake.next_principal = BOB
        domain_error(login, client)
        fake.approve()
        assert login(client)['identity']['arn'] == BOB
        assert fake.credential('dev').principal == BOB
        # Each approval is used once.
        assert fake.approval_requests() == []

    def test_an_approval_is_bound_to_who_signed_in(self, fake, client):
        # An approval shown one account and role doesn't approve a re-run
        # that signs in as another.
        login(client)
        fake.next_principal = BOB
        first = domain_error(login, client).data['challenge']['id']
        fake.approve(first)
        fake.next_principal = (
            f'arn:aws:sts::{DEFAULT_ACCOUNT_ID}:assumed-role/Ops/carol'
        )
        second = domain_error(login, client).data['challenge']
        assert second['id'] != first
        assert 'role Ops' in second['description']
        assert fake.credential('dev').principal == DEFAULT_PRINCIPAL

    def test_another_session_of_the_same_role_is_the_same_person(
        self, fake, client
    ):
        login(client)
        fake.next_principal = DEFAULT_PRINCIPAL.replace('/alice', '/alice-2')
        login(client)
        assert fake.credential('dev').principal == fake.next_principal
        assert fake.approval_requests() == []

    def test_a_credential_with_no_record_needs_approval(self, fake, client):
        # Made before credsd recorded who signed in.
        fake.seed('dev', principal=None)
        error = domain_error(login, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert error.data['challenge']['description'].endswith(
            '; it was no recorded sign-in'
        )
        assert fake.credential('dev').principal is None

    def test_signing_in_after_logout_still_checks_identity(self, fake, client):
        login(client)
        client.call('credential/logout', {'credential': 'dev'})
        fake.next_principal = BOB
        error = domain_error(login, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert fake.credential('dev').status == NO_SESSION

    def test_another_region_needs_approval_before_the_sign_in(
        self, fake, client
    ):
        # credsd's same_provider_source compares the region.
        login(client)
        error = domain_error(login, client, region='eu-west-1')
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert [n['type'] for n in client.notifications] == ['authorize_url']

    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_SSO])
    def test_another_kind_of_credential_needs_approval(
        self, fake, client, kind
    ):
        # As credsd's same_provider_source: only an aws login session is
        # replaced with no approval.
        fake.seed('dev', kind=kind)
        error = domain_error(login, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert client.notifications == []
        # credsd's data: the challenge and its remediation, nothing else.
        assert set(error.data) == {'code', 'challenge', 'remediation'}
        assert fake.credential('dev').kind == kind

    def test_an_aws_login_session_is_replaced_without_approval(
        self, fake, client
    ):
        # Signed in as the principal it records.
        fake.seed('dev')
        login(client)
        assert fake.credential('dev').kind == KIND_LOGIN
        assert fake.approval_requests() == []

    @pytest.mark.parametrize(
        'method', ['credential/bootstrap', 'credential/import']
    )
    def test_the_old_client_object_is_refused(self, client, method):
        params = {
            'credential/bootstrap': {
                'credential': 'dev',
                'provider': {'type': 'aws_login'},
            },
            'credential/import': {
                'credential': 'ci',
                'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'secret_access_key': 'secret',
                'region': 'us-east-1',
            },
        }[method]
        params['client'] = {'name': 'aws-cli', 'version': '2.38.6'}
        with pytest.raises(RawRpcError) as e:
            client.call(method, params)
        assert e.value.code == -32602

    def test_a_sign_in_with_or_without_a_creator_is_the_same(
        self, fake, client
    ):
        client.call(
            'credential/bootstrap',
            {
                'credential': 'dev',
                'provider': {'type': 'aws_login', 'region': 'us-west-2'},
            },
        )
        login(client)
        rows = client.call('credential/list')['credentials']
        assert 'creator' not in rows[0]
        assert fake.approval_requests() == []

    def test_remote_sign_in_reads_the_code(self, client):
        def paste(client, notification):
            if notification['type'] == 'authorize_code':
                client.respond(notification['request_id'], selection='abc123')

        assert login(client, remote=True, on_notification=paste)
        assert [n['type'] for n in client.notifications] == ['authorize_code']
        url = client.notifications[0]['url']
        assert 'devtools%2Fcross-device' in url
        assert 'v1%2Fsessions%2Fconfirmation' in url

    @pytest.mark.parametrize(
        'code, message',
        [
            # Base64, but not this sign-in's state.
            ('invalid-code', 'start over'),
            ('  ', 'start over'),
            # Not base64: the credential daemon fails it at decode.
            ('invalid-1', 'not the value Sign-In displayed'),
            ('abc!', 'not the value Sign-In displayed'),
        ],
    )
    def test_remote_sign_in_takes_one_code(self, fake, client, code, message):
        def paste(client, notification):
            if notification['type'] == 'authorize_code':
                client.respond(notification['request_id'], selection=code)

        error = domain_error(login, client, remote=True, on_notification=paste)
        assert error.data_code == 'PROVIDER_UNAVAILABLE'
        assert message in str(error)
        assert [n['type'] for n in client.notifications] == ['authorize_code']
        assert fake.credential('dev') is None

    def test_remote_sign_in_refuses_a_callback_port(self, client):
        error = domain_error(login, client, remote=True, callback_port=8400)
        assert error.data_code == 'PROVIDER_UNAVAILABLE'
        assert client.notifications == []

    def test_refuses_redirect_port(self, client):
        # The credential daemon names the field callback_port and drops
        # unknown ones.
        with pytest.raises(RawRpcError) as e:
            login(client, redirect_port=8400)
        assert e.value.code == -32602

    def test_remote_code_is_redacted(self, fake, client):
        def paste(client, notification):
            if notification['type'] == 'authorize_code':
                client.respond(notification['request_id'], selection='abc123')

        login(client, remote=True, on_notification=paste)
        assert 'abc123' not in repr(fake.calls)

    def test_manual_sign_in_waits_until_completed(self):
        with FakeCredentialDaemon(signin='manual') as fake:
            with RawClient(fake.socket_path) as client:
                request_id = client.request(
                    'credential/bootstrap',
                    {
                        'credential': 'dev',
                        'provider': {'type': 'aws_login'},
                        'creator': CLI,
                    },
                )
                assert client.read()['params']['type'] == 'authorize_url'
                with RawClient(fake.socket_path) as other:
                    state = other.call('mock/state')
                    assert state['waiting_signins'] == ['dev']
                    completed = other.call(
                        'mock/complete_signin', {'name': 'dev'}
                    )
                    assert completed == {'completed': 1}
                assert client.wait_for(request_id)['credential'] == 'dev'

    def test_sign_in_times_out(self):
        with FakeCredentialDaemon(signin='manual', auth_timeout=0.2) as fake:
            with RawClient(fake.socket_path) as client:
                error = domain_error(login, client)
        assert error.data_code == 'AUTH_TIMEOUT'

    def test_hanging_up_cancels_the_sign_in(self):
        with FakeCredentialDaemon(signin='manual') as fake:
            client = RawClient(fake.socket_path)
            client.request(
                'credential/bootstrap',
                {'credential': 'dev', 'provider': {'type': 'aws_login'}},
            )
            client.read()
            assert fake.waiting_signins() == ['dev']
            client.close()
            eventually(lambda: fake.waiting_signins() == [])
            assert fake.credential('dev') is None

    def test_expired_session_needs_a_new_sign_in(self, fake, client):
        login(client)
        fake.expire('dev')
        error = domain_error(
            client.call, 'credential/get', {'credential': 'dev'}
        )
        assert error.data_code == 'REAUTH_REQUIRED'
        [row] = client.call('credential/list')['credentials']
        assert row['status'] == EXPIRED

    def test_injected_failure(self, fake, client):
        login(client)
        fake.fail_next('credential/get', 'PROVIDER_UNAVAILABLE')
        error = domain_error(
            client.call, 'credential/get', {'credential': 'dev'}
        )
        assert error.data_code == 'PROVIDER_UNAVAILABLE'
        assert client.call('credential/get', {'credential': 'dev'})['material']

    def test_config_that_doesnt_validate_refuses_reads(self, fake, client):
        login(client)
        fake.set_config_invalid('bad tag key')
        for method, params in [
            ('credential/get', {'credential': 'dev'}),
            ('credential/list', {}),
            ('credential/tag', {'credential': 'dev', 'set': {'a': 'b'}}),
        ]:
            error = domain_error(client.call, method, params)
            assert error.data_code == 'CONFIG_INVALID'
            assert str(error) == (
                'caller configuration does not validate: bad tag key; fix '
                'it, then run: creds revalidate'
            )
        # Methods that don't read the configuration still work.
        assert client.call('credential/logout', {'credential': 'dev'})
        fake.set_config_invalid(None)
        assert client.call('credential/list')['credentials']
        fake.set_config_invalid('bad tag key')
        fake.reset()
        assert client.call('credential/list') == {'credentials': []}

    def test_mock_controls_over_the_socket(self, client):
        client.call('mock/set_principal', {'principal': BOB})
        assert login(client)['identity']['arn'] == BOB
        client.call(
            'mock/fail',
            {'method': 'credential/get', 'code': 'PROVIDER_UNAVAILABLE'},
        )
        error = domain_error(
            client.call, 'credential/get', {'credential': 'dev'}
        )
        assert error.data_code == 'PROVIDER_UNAVAILABLE'
        client.call(
            'mock/seed', {'name': 'tool', 'kind': KIND_LOGIN, 'creator': 'x'}
        )
        client.call('mock/reset')
        assert client.call('credential/list') == {'credentials': []}


class TestIdentityCredentialName:
    @pytest.mark.parametrize(
        'principal, name',
        [
            (
                'arn:aws:sts::111111111111:assumed-role/Admin/alice',
                'login.111111111111-role-Admin',
            ),
            # As credsd's name_under: the session isn't part of it.
            (
                'arn:aws:sts::111111111111:assumed-role/Admin/a.b_c-d',
                'login.111111111111-role-Admin',
            ),
            # A user's path is dropped.
            (
                'arn:aws:iam::111111111111:user/bob',
                'login.111111111111-user-bob',
            ),
            (
                'arn:aws:iam::111111111111:user/team/dev/bob',
                'login.111111111111-user-bob',
            ),
            ('arn:aws:iam::111111111111:root', 'login.111111111111-root'),
            (
                'arn:aws-us-gov:iam::111111111111:root',
                'login.111111111111-root',
            ),
        ],
    )
    def test_plain(self, principal, name):
        assert identity_credential_name('login.', principal) == name

    def test_characters_credential_daemon_doesnt_take(self):
        principal = 'arn:aws:sts::111111111111:assumed-role/me@corp.com/s'
        name = identity_credential_name('login.', principal)
        assert name.startswith('login.111111111111-role-me-corp.com-')
        assert len(name) == len('login.111111111111-role-me-corp.com-') + 8
        # Names that clean up to the same text stay different.
        other = principal.replace('@', '=')
        assert identity_credential_name('login.', other) != name

    def test_longer_than_64_is_cut(self):
        role = 'A' * 60
        principal = f'arn:aws:sts::111111111111:assumed-role/{role}/b'
        name = identity_credential_name('login.', principal)
        assert len(name) == 64
        assert name.startswith(f'login.111111111111-role-{role}'[:55])
        assert name[55] == '-'
        other = f'arn:aws:sts::111111111111:assumed-role/{role}x/b'
        assert identity_credential_name('login.', other) != name


class TestLoginByIdentity:
    def test_names_the_credential_after_the_principal(self, fake, client):
        fake.next_principal = (
            'arn:aws:sts::111111111111:assumed-role/Admin/alice'
        )
        result = login_by_identity(client)
        assert result['credential'] == 'login.111111111111-role-Admin'
        assert result['identity']['arn'] == fake.next_principal
        assert 'expires_at' not in result
        cred = fake.credential('login.111111111111-role-Admin')
        assert cred.kind == KIND_LOGIN

    def test_another_identity_gets_its_own_credential(self, fake, client):
        login_by_identity(client)
        fake.next_principal = BOB
        result = login_by_identity(client)
        assert (
            result['credential'] == f'login.{DEFAULT_ACCOUNT_ID}-role-ReadOnly'
        )
        names = [
            r['credential']
            for r in client.call('credential/list')['credentials']
        ]
        assert names == [
            f'login.{DEFAULT_ACCOUNT_ID}-role-Admin',
            f'login.{DEFAULT_ACCOUNT_ID}-role-ReadOnly',
        ]
        assert fake.approval_requests() == []

    @pytest.mark.parametrize('status', [ACTIVE, NO_SESSION])
    def test_same_identity_refreshes_in_place(self, fake, client, status):
        name = f'login.{DEFAULT_ACCOUNT_ID}-role-Admin'
        old = fake.seed(name, status=status)
        result = login_by_identity(client)
        assert result['credential'] == name
        assert fake.credential(name) is not old
        assert fake.credential(name).status == ACTIVE
        assert [n['type'] for n in client.notifications] == ['authorize_url']

    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_SSO])
    def test_another_kind_of_credential_needs_approval(
        self, fake, client, kind
    ):
        name = f'login.{DEFAULT_ACCOUNT_ID}-role-Admin'
        fake.seed(name, kind=kind)
        error = domain_error(login_by_identity, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert set(error.data) == {'code', 'challenge', 'remediation'}
        assert fake.credential(name).kind == kind

    def test_a_name_clash_with_another_principal_needs_approval(
        self, fake, client
    ):
        # Two principals whose names clean up to the same text.
        name = f'login.{DEFAULT_ACCOUNT_ID}-role-Admin'
        fake.seed(name, principal=BOB)
        error = domain_error(login_by_identity, client)
        assert error.data_code == 'APPROVAL_REQUIRED'
        assert (
            f"replace existing credential '{name}'"
            in (error.data['challenge']['description'])
        )
        assert fake.credential(name).principal == BOB

    def test_name_and_prefix_together_are_refused(self, client):
        with pytest.raises(RawRpcError) as e:
            client.call(
                'credential/bootstrap',
                {
                    'credential': 'dev',
                    'name_prefix': 'login.',
                    'provider': {'type': 'aws_login'},
                    'creator': CLI,
                },
            )
        assert e.value.code == -32602

    @pytest.mark.parametrize('prefix', ['', '.login', 'a/b', 'x' * 33, 1])
    def test_invalid_prefixes_are_refused(self, client, prefix):
        with pytest.raises(RawRpcError) as e:
            login_by_identity(client, name_prefix=prefix)
        assert e.value.code == -32602

    def test_sso_doesnt_take_a_prefix(self, client):
        with pytest.raises(RawRpcError) as e:
            client.call(
                'credential/bootstrap',
                {
                    'name_prefix': 'sso.',
                    'provider': {
                        'type': 'sso',
                        'start_url': 'https://acme.awsapps.com/start',
                        'sso_region': 'us-east-1',
                    },
                    'creator': CLI,
                },
            )
        assert e.value.code == -32602

    def test_manual_sign_in_waits_under_the_prefix(self):
        with FakeCredentialDaemon(signin='manual') as fake:
            with RawClient(fake.socket_path) as client:
                request_id = client.request(
                    'credential/bootstrap',
                    {
                        'name_prefix': 'login.',
                        'provider': {'type': 'aws_login'},
                        'creator': CLI,
                    },
                )
                client.read()
                assert fake.waiting_signins() == ['login.']
                fake.complete_signin('login.')
                assert client.wait_for(request_id)['credential'] == (
                    f'login.{DEFAULT_ACCOUNT_ID}-role-Admin'
                )


class TestMultiRole:
    def sign_in(self, client, roles):
        def pick(client, notification):
            if notification['type'] == 'select_role':
                client.respond(notification['request_id'], roles=roles)

        return client.call(
            'credential/bootstrap',
            {
                'provider': {'type': 'aws_login', 'multi_role': True},
                'creator': CLI,
            },
            on_notification=pick,
        )

    def test_one_credential_per_chosen_role(self, client):
        result = self.sign_in(
            client,
            [
                {'account_id': '123456789012', 'role_name': 'Admin'},
                {'account_id': '555555555555', 'role_name': 'ReadOnly'},
            ],
        )
        names = [c['name'] for c in result['credentials']]
        assert names == ['Admin-123456789012', 'ReadOnly-555555555555']
        assert result['credentials'][0]['principal'] == (
            'arn:aws:sts::123456789012:assumed-role/Admin/alice'
        )
        rows = client.call('credential/list')['credentials']
        assert [r['credential'] for r in rows] == names

    def test_configured_roles_are_marked(self, client):
        admin = {'account_id': '123456789012', 'role_name': 'Admin'}
        self.sign_in(client, [admin])
        self.sign_in(client, [admin])
        roles = client.notifications[-1]['roles']
        configured = {r['name']: r['configured'] for r in roles}
        assert configured == {
            'Admin-123456789012': True,
            'ReadOnly-123456789012': False,
            'ReadOnly-555555555555': False,
        }

    def test_the_client_can_name_the_credentials(self, client):
        result = self.sign_in(
            client,
            [
                {
                    'account_id': '123456789012',
                    'role_name': 'Admin',
                    'name': 'a',
                }
            ],
        )
        assert result['credentials'][0]['name'] == 'a'

    def test_choosing_nothing_cancels(self, client):
        error = domain_error(self.sign_in, client, [])
        assert error.data_code == 'AUTH_CANCELLED'


class TestSso:
    def test_role_credentials_for_each_profile(self, client):
        sso_login(client)
        result = client.call(
            'credential/get',
            {
                'credential': 'acme',
                'account_id': '111111111111',
                'role_name': 'Admin',
            },
        )
        assert result['material']['account_id'] == '111111111111'
        with pytest.raises(RawRpcError) as e:
            client.call('credential/get', {'credential': 'acme'})
        assert e.value.code == -32602

    def test_device_code(self, client):
        sso_login(client, use_device_code=True)
        [notification] = client.notifications
        assert notification['type'] == 'device_code'
        assert notification['user_code']

    def test_listens_on_the_callback_port(self):
        port = free_port()
        with FakeCredentialDaemon(signin='manual') as fake:
            with RawClient(fake.socket_path) as client:
                request_id = client.request(
                    'credential/bootstrap',
                    {
                        'credential': 'acme',
                        'provider': {
                            'type': 'sso',
                            'start_url': 'https://acme.awsapps.com/start',
                            'sso_region': 'us-east-1',
                            'callback_port': port,
                        },
                        'creator': CLI,
                    },
                )
                url = client.read()['params']['url']
                assert (
                    f'redirect_uri=http%3A%2F%2F127.0.0.1%3A{port}%2F' in url
                )
                socket.create_connection(('127.0.0.1', port), 1).close()
                fake.complete_signin('acme')
                assert client.wait_for(request_id)['name'] == 'acme'
        with pytest.raises(OSError):
            socket.create_connection(('127.0.0.1', port), 1)

    def test_without_a_callback_port_listens_on_any_port(self, client):
        sso_login(client)
        [notification] = client.notifications
        assert 'redirect_uri=http%3A%2F%2F127.0.0.1%3A' in notification['url']

    def test_callback_port_in_use(self, client):
        with socket.socket() as taken:
            taken.bind(('127.0.0.1', 0))
            taken.listen(1)
            port = taken.getsockname()[1]
            error = domain_error(sso_login, client, callback_port=port)
        assert error.data_code == 'REDIRECT_PORT_IN_USE'

    @pytest.mark.parametrize('port', [0, 65536, '8080', True])
    def test_invalid_callback_port(self, client, port):
        with pytest.raises(RawRpcError) as e:
            sso_login(client, callback_port=port)
        assert e.value.code == -32602

    @pytest.mark.parametrize('name', ['acme', 'dev'])
    def test_access_token_is_never_handed_out(self, client, name):
        sso_login(client)
        login(client)
        with pytest.raises(RawRpcError) as e:
            client.call(
                'credential/get',
                {'credential': name, 'material': 'access_token'},
            )
        assert e.value.code == -32602


class TestCommandLine:
    def test_call_prints_the_result(self, fake, capsys):
        assert (
            main(['call', '--socket', fake.socket_path, 'system/health']) == 0
        )
        assert json.loads(capsys.readouterr().out)['protocol'] == 1

    def test_call_reports_errors(self, fake, capsys):
        args = ['call', '--socket', fake.socket_path, 'credential/get']
        assert main(args + ['{"credential": "nope"}']) == 1
        error = json.loads(capsys.readouterr().err)
        assert error['data']['code'] == 'CREDENTIAL_NOT_FOUND'
