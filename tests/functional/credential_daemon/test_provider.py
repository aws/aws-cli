# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for profiles that get credentials from the credential daemon, run
against the fake credential daemon."""

import contextlib
import functools
import json
import os
import pickle
import socket
import tempfile
import textwrap
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore import credential_daemon
from botocore.context import get_context, start_as_current_context
from botocore.credential_daemon.client import CredentialDaemonClient
from botocore.credential_daemon.messages import START_HINT
from botocore.credential_daemon.model import CredentialRow, SocketChecks
from botocore.credential_daemon.transport import _Connection
from botocore.credentials import (
    ContainerProvider,
    CredentialDaemonFetcher,
    CredentialDaemonProvider,
    InstanceMetadataProvider,
    RefreshableCredentials,
)
from botocore.exceptions import (
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonCredentialUnusableError,
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonProviderUnavailableError,
    CredentialDaemonReauthRequiredError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonUnsupportedMaterialError,
    CredentialDaemonUnsupportedPlatformError,
    CredentialDaemonUntrustedSocketError,
    InvalidConfigError,
)
from botocore.session import Session
from botocore.stub import ANY

import awscli
from awscli.clidriver import AWSCLIEntryPoint, create_clidriver
from awscli.testutils import BaseAWSCommandParamsTest, skip_if_windows
from tests import CLIRunner, HTTPResponse, StubbedSession, mock
from tests.functional.botocore.test_useragent import (
    parse_registered_feature_ids,
)
from tests.functional.credential_daemon.sso_helpers import (
    no_credential_daemon_calls,
)
from tests.utils.credential_daemon import (
    DEFAULT_ACCOUNT_ID,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    NO_SESSION,
    FakeCredentialDaemon,
)

DEV_PROFILE = '''
    [profile dev]
    credential_daemon = dev
'''
# The fake's credentials last 15 minutes, as aws login's do, so they start
# inside botocore's 15 minute advisory window and every use asks the
# credential daemon again. Tests that count calls use an hour.
ONE_HOUR = pytest.mark.parametrize(
    'fake', [{'credential_lifetime': 3600}], indirect=True
)


@pytest.fixture
def aws_dir(aws_dir, daemon_env, monkeypatch):
    monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')
    return aws_dir


def write_config(aws_dir, config, credentials=''):
    (aws_dir / 'config').write_text(textwrap.dedent(config))
    (aws_dir / 'credentials').write_text(textwrap.dedent(credentials))


def credential_gets(fake):
    return [
        params for method, params in fake.calls if method == 'credential/get'
    ]


@pytest.fixture
def no_host_credentials():
    """Fail the test if the chain goes on to container or instance
    credentials."""
    with (
        mock.patch.object(
            ContainerProvider, 'load', side_effect=AssertionError('fell back')
        ),
        mock.patch.object(
            InstanceMetadataProvider,
            'load',
            side_effect=AssertionError('fell back'),
        ),
    ):
        yield


class TestGettingCredentials:
    @ONE_HOUR
    def test_credentials_come_from_credential_daemon(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        credentials = Session(profile='dev').get_credentials()
        frozen = credentials.get_frozen_credentials()
        assert credentials.method == 'credential-daemon'
        assert isinstance(credentials, RefreshableCredentials)
        assert frozen.access_key.startswith('ASIA')
        assert frozen.token
        assert frozen.account_id == DEFAULT_ACCOUNT_ID
        assert credential_gets(fake) == [{'credential': 'dev'}]

    def test_the_name_can_differ_from_the_profile(self, fake, aws_dir):
        fake.seed('dev')
        write_config(
            aws_dir,
            '''
            [profile staging]
            credential_daemon = dev
            ''',
        )
        credentials = Session(profile='staging').get_credentials()
        assert credentials.method == 'credential-daemon'
        assert credential_gets(fake) == [{'credential': 'dev'}]

    def test_comes_before_the_web_identity_environment_variables(
        self, fake, aws_dir, monkeypatch
    ):
        # The SEP's env-web-identity-and-daemon-profile: the daemon provider
        # is the first profile-based provider, so it comes before
        # AWS_ROLE_ARN and AWS_WEB_IDENTITY_TOKEN_FILE. AWS_PROFILE, not
        # Session(profile=...), so the chain reads those variables.
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        monkeypatch.setenv('AWS_PROFILE', 'dev')
        monkeypatch.setenv(
            'AWS_ROLE_ARN', 'arn:aws:iam::123456789012:role/WebIdentity'
        )
        monkeypatch.setenv(
            'AWS_WEB_IDENTITY_TOKEN_FILE', str(aws_dir / 'missing-token')
        )
        credentials = Session().get_credentials()
        assert credentials.method == 'credential-daemon'
        assert credential_gets(fake) == [{'credential': 'dev'}]

    def test_profiles_without_credential_daemon_are_unchanged(
        self, fake, aws_dir
    ):
        write_config(
            aws_dir,
            '''
            [profile keys]
            aws_access_key_id = AKIDEXAMPLE
            aws_secret_access_key = secret
            ''',
        )
        credentials = Session(profile='keys').get_credentials()
        assert credentials.method == 'config-file'
        assert credential_gets(fake) == []

    @ONE_HOUR
    def test_credentials_are_cached_until_near_expiry(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        credentials = Session(profile='dev').get_credentials()
        for _ in range(5):
            credentials.get_frozen_credentials()
        assert len(credential_gets(fake)) == 1

    @pytest.mark.parametrize(
        'fake', [{'credential_lifetime': 45}], indirect=True
    )
    def test_credentials_are_refreshed_near_expiry(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        credentials = Session(profile='dev').get_credentials()
        credentials.get_frozen_credentials()
        assert len(credential_gets(fake)) == 2

    @pytest.mark.parametrize('storage', ['daemon', 'file'])
    def test_credential_storage_is_ignored(
        self, fake, aws_dir, monkeypatch, storage
    ):
        # A profile moves back to files at its next sign-in, not before.
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE + 'credential_storage = file\n')
        monkeypatch.setenv('AWS_CREDENTIAL_STORAGE', storage)
        assert Session(profile='dev').get_credentials().method == (
            'credential-daemon'
        )


class TestPrecedence:
    @pytest.mark.parametrize(
        'other_settings',
        [
            'aws_access_key_id = AKIDEXAMPLE\naws_secret_access_key = s\n',
            'credential_process = /bin/false\n',
            'login_session = arn:aws:sts::123456789012:assumed-role/A/a\n',
            'sso_session = acme\nsso_account_id = 111111111111\n'
            'sso_role_name = Admin\n',
        ],
    )
    def test_credential_daemon_wins_within_the_profile(
        self, fake, aws_dir, other_settings
    ):
        fake.seed('dev')
        write_config(
            aws_dir,
            '[profile dev]\ncredential_daemon = dev\n'
            + other_settings
            + '[sso-session acme]\nsso_start_url = https://a.awsapps.com/start'
            '\nsso_region = us-east-1\n',
        )
        assert Session(profile='dev').get_credentials().method == (
            'credential-daemon'
        )

    def test_credential_daemon_wins_over_the_credentials_file(
        self, fake, aws_dir
    ):
        fake.seed('dev')
        write_config(
            aws_dir,
            DEV_PROFILE,
            credentials='''
            [dev]
            aws_access_key_id = AKIDEXAMPLE
            aws_secret_access_key = secret
            ''',
        )
        assert Session(profile='dev').get_credentials().method == (
            'credential-daemon'
        )

    def test_credential_daemon_in_the_credentials_file_is_ignored(
        self, fake, aws_dir
    ):
        # The SEP reads credential_daemon only from the config file, so
        # the next provider (here the credentials file's keys) runs.
        fake.seed('dev')
        write_config(
            aws_dir,
            '[profile dev]\nregion = us-east-1\n',
            credentials='''
            [dev]
            credential_daemon = dev
            aws_access_key_id = AKIDNEXTPROVIDER
            aws_secret_access_key = secret
            ''',
        )
        session = Session(profile='dev')
        credentials = session.get_credentials()
        assert credentials.method == 'shared-credentials-file'
        assert credentials.access_key == 'AKIDNEXTPROVIDER'
        assert fake.calls == []
        # The session's own config still has what the files say.
        assert session.full_config['profiles']['dev']['credential_daemon'] == (
            'dev'
        )

    def test_the_config_files_credential_daemon_wins(self, fake, aws_dir):
        fake.seed('dev')
        write_config(
            aws_dir,
            DEV_PROFILE,
            credentials='''
            [dev]
            credential_daemon = other
            ''',
        )
        assert Session(profile='dev').get_credentials().method == (
            'credential-daemon'
        )
        assert credential_gets(fake) == [{'credential': 'dev'}]

    def test_a_role_next_to_a_credentials_file_credential_daemon(
        self, fake, aws_dir
    ):
        # Ignored in the credentials file, it doesn't make role_arn a
        # conflict either: the role is assumed.
        write_config(
            aws_dir,
            '''
            [profile dev]
            role_arn = arn:aws:iam::123456789012:role/Dev
            source_profile = base
            ''',
            credentials='''
            [dev]
            credential_daemon = dev
            ''',
        )
        with mock.patch(
            'botocore.credentials.AssumeRoleProvider.'
            '_load_creds_via_assume_role',
            return_value='assumed',
        ) as assume:
            assert Session(profile='dev').get_credentials() == 'assumed'
        assume.assert_called_once_with('dev')
        assert fake.calls == []

    def test_environment_keys_still_win_with_aws_profile(
        self, fake, aws_dir, monkeypatch
    ):
        # As today: AWS_PROFILE doesn't stop the environment variables.
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        monkeypatch.setenv('AWS_PROFILE', 'dev')
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDENV')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
        assert Session().get_credentials().method == 'env'

    def test_an_explicit_profile_ignores_environment_keys(
        self, fake, aws_dir, monkeypatch
    ):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDENV')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
        assert Session(profile='dev').get_credentials().method == (
            'credential-daemon'
        )


class TestNoFallback:
    @pytest.mark.parametrize(
        'seed, error_class, message',
        [
            (
                {'status': NO_SESSION},
                CredentialDaemonReauthRequiredError,
                "Session for profile 'dev' has ended. Run 'aws login --profile dev'. "
                "The credential daemon said: credential 'dev' requires "
                're-authentication (complete SSO sign-in in a browser)',
            ),
            (
                None,
                CredentialDaemonCredentialNotFoundError,
                'The credential daemon has no credential named '
                "'dev'. Sign in again with 'aws login --profile dev', or "
                'remove credential_daemon from the profile and enter its keys '
                "with 'aws configure --profile dev'. The credential daemon "
                'said: No credential named dev',
            ),
        ],
    )
    def test_credential_daemon_errors_stop_the_chain(
        self,
        fake,
        aws_dir,
        no_host_credentials,
        seed,
        error_class,
        message,
    ):
        if seed is not None:
            fake.seed('dev', **seed)
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(error_class) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value) == message

    def test_credential_daemon_not_running(
        self, aws_dir, no_host_credentials, sock_dir
    ):
        missing = str(sock_dir / 'missing.sock')
        write_config(aws_dir, DEV_PROFILE)
        with mock.patch.dict(
            'os.environ', AWS_CREDENTIAL_DAEMON_SOCKET=missing
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                Session(profile='dev').get_credentials()
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{missing}: No such file or directory. Start the credential '
            'daemon, or install it with \'aws configure credential-daemon '
            'install\', link its socket with \'aws configure '
            'credential-daemon link\', or set AWS_CREDENTIAL_DAEMON_SOCKET.'
        )

    @pytest.mark.parametrize('socket_env', [None, '/x/credsd.sock'])
    def test_a_platform_without_the_credential_daemon(
        self, aws_dir, no_host_credentials, socket_env
    ):
        # Such as Windows: no Unix sockets. Only files can help, whatever
        # AWS_CREDENTIAL_DAEMON_SOCKET says, and nothing else is used.
        write_config(aws_dir, DEV_PROFILE)
        environ = {}
        if socket_env is not None:
            environ['AWS_CREDENTIAL_DAEMON_SOCKET'] = socket_env
        with (
            mock.patch.dict('os.environ', environ),
            mock.patch('botocore.credential_daemon.transport.socket') as sock,
            mock.patch('sys.platform', 'win32'),
        ):
            del sock.AF_UNIX
            with pytest.raises(CredentialDaemonUnsupportedPlatformError) as e:
                Session(profile='dev').get_credentials()
        assert str(e.value) == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile '
            'and any credential_storage = daemon (or set it to file), then '
            "sign in again or enter its keys with 'aws configure'."
        )

    def test_a_platform_without_the_credential_daemon_and_the_variable(
        self, aws_dir, no_host_credentials
    ):
        # AWS_CREDENTIAL_STORAGE=daemon wins over the profile, so editing
        # the profile alone would be refused again at the next sign-in.
        write_config(aws_dir, DEV_PROFILE)
        with (
            mock.patch.dict('os.environ', AWS_CREDENTIAL_STORAGE=' Daemon '),
            mock.patch('botocore.credential_daemon.transport.socket') as sock,
            mock.patch('sys.platform', 'win32'),
        ):
            del sock.AF_UNIX
            with pytest.raises(CredentialDaemonUnsupportedPlatformError) as e:
                Session(profile='dev').get_credentials()
        assert str(e.value) == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile and '
            'run the command again with AWS_CREDENTIAL_STORAGE=file.'
        )

    def test_control_characters_are_stripped_from_the_socket_path(
        self, aws_dir, no_host_credentials, sock_dir
    ):
        missing = str(sock_dir / 'missing\x1b[2K.sock')
        write_config(aws_dir, DEV_PROFILE)
        with mock.patch.dict(
            'os.environ', AWS_CREDENTIAL_DAEMON_SOCKET=missing
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                Session(profile='dev').get_credentials()
        assert '\x1b' not in str(e.value)
        assert f'to {sock_dir}/missing[2K.sock: ' in str(e.value)

    def test_provider_unavailable(self, fake, aws_dir, no_host_credentials):
        fake.seed('dev')
        fake.fail_next('credential/get', 'PROVIDER_UNAVAILABLE')
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonProviderUnavailableError) as e:
            Session(profile='dev').get_credentials()
        # credsd uses this code for refused keys and bad regions too, so the
        # message doesn't say AWS couldn't be reached.
        assert str(e.value) == (
            'The credential daemon couldn\'t get credentials from AWS. The '
            'credential daemon said: Injected PROVIDER_UNAVAILABLE. If you '
            'use a proxy, set HTTPS_PROXY (and AWS_CA_BUNDLE, if the proxy '
            'inspects TLS) in the credential daemon\'s service settings. '
            'Settings in your shell don\'t reach it.'
        )
        assert e.value.code == 'PROVIDER_UNAVAILABLE'
        assert 'creds' not in str(e.value)

    def test_daemon_message_is_stripped(
        self, fake, aws_dir, no_host_credentials
    ):
        fake.seed('dev')
        fake.fail_next(
            'credential/get', 'REAUTH_REQUIRED', message='Revoked\x1b[2K\x07.'
        )
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value).endswith(
            ' The credential daemon said: Revoked[2K.'
        )
        assert e.value.code == 'REAUTH_REQUIRED'

    @pytest.mark.parametrize(
        'code, error_class',
        [
            ('REAUTH_REQUIRED', CredentialDaemonReauthRequiredError),
            ('CREDENTIAL_NOT_FOUND', CredentialDaemonCredentialNotFoundError),
            ('CONFIG_DRIFTED', CredentialDaemonCredentialUnusableError),
        ],
    )
    def test_daemon_message_is_always_appended(
        self, fake, aws_dir, no_host_credentials, code, error_class
    ):
        # The SEP: an error from a daemon error reply MUST also include the
        # daemon's message, even where the CLI's own text covers it.
        fake.seed('dev')
        fake.fail_next('credential/get', code, message='dev is not usable')
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(error_class) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value).endswith(
            ' The credential daemon said: dev is not usable'
        )
        assert e.value.daemon_message == 'dev is not usable'

    def test_unknown_codes_keep_the_daemon_message(
        self, fake, aws_dir, no_host_credentials
    ):
        fake.seed('dev')
        fake.fail_next(
            'credential/get', 'SOMETHING_NEW', message='Something new'
        )
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonError) as e:
            Session(profile='dev').get_credentials()
        assert 'Something new' in str(e.value)

    @skip_if_windows('The link is for Linux and macOS.')
    def test_refresh_looks_for_the_socket_again(self, monkeypatch):
        # SEP: look for the socket on each fetch. A refresh after the link
        # changes, or goes, dials where a new process would. A short HOME
        # keeps the link under sun_path's limit.
        with tempfile.TemporaryDirectory(dir='/tmp', prefix='h') as home:
            monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
            monkeypatch.setenv('HOME', home)
            link = Path(home, '.aws', 'credential-daemon.sock')
            link.parent.mkdir(mode=0o700)
            provider = CredentialDaemonProvider(
                load_config=lambda: {
                    'profiles': {'dev': {'credential_daemon': 'dev'}}
                },
                profile_name='dev',
                credential_daemon_client=CredentialDaemonClient(timeout=2),
            )
            with (
                FakeCredentialDaemon() as first,
                FakeCredentialDaemon() as second,
            ):
                first.seed('dev')
                second.seed('dev')
                link.symlink_to(first.socket_path)
                credentials = provider.load()
                # The link now points at another daemon.
                link.unlink()
                link.symlink_to(second.socket_path)
                credentials._refresh_using()
                assert [m for m, _ in first.calls] == ['credential/get']
                assert [m for m, _ in second.calls] == ['credential/get']
                # And when it goes, nothing is dialed.
                link.unlink()
                with pytest.raises(CredentialDaemonNotRunningError) as e:
                    credentials._refresh_using()
                assert 'there\'s no socket at' in str(e.value)
                assert len(first.calls) == len(second.calls) == 1

    def test_unknown_error_code(self, fake, aws_dir, no_host_credentials):
        fake.seed('dev')
        fake.fail_next('credential/get', 'SOMETHING_NEW', 'Something new')
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonRequestRejectedError) as e:
            Session(profile='dev').get_credentials()
        # The SEP's REQUEST_REJECTED: the credential daemon's message and
        # code.
        assert str(e.value) == 'Something new (SOMETHING_NEW)'
        assert e.value.code == 'SOMETHING_NEW'

    @pytest.mark.parametrize(
        'code', ['CONFIG_DRIFTED', 'INTEGRITY_UNVERIFIABLE', 'CUSTODY_BROKEN']
    )
    def test_unusable_credential(
        self, fake, aws_dir, no_host_credentials, code
    ):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            code,
            "environment 'dev' credential sources have drifted",
        )
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonCredentialUnusableError) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value) == (
            "The credential daemon can't use credential 'dev' for profile "
            "'dev': its settings changed, or its stored data can't be "
            'checked. The credential daemon said: environment \'dev\' '
            'credential sources have drifted'
        )
        assert e.value.code == code

    def test_config_that_doesnt_validate_is_unusable(
        self, fake, aws_dir, no_host_credentials
    ):
        fake.seed('dev')
        fake.set_config_invalid('bad tag key')
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonCredentialUnusableError) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value) == (
            "The credential daemon can't use credential 'dev' for profile "
            "'dev': its settings changed, or its stored data can't be "
            'checked. The credential daemon said: caller configuration does '
            'not validate: bad tag key; fix it, then run: creds revalidate'
        )
        assert e.value.code == 'CONFIG_INVALID'

    @ONE_HOUR
    def test_a_fetch_is_one_credential_get(
        self, fake, aws_dir, no_host_credentials
    ):
        # A fetch sends only credential/get, so a daemon's protocol version
        # doesn't stop it.
        fake.protocol_version = 2
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        assert Session(profile='dev').get_credentials().access_key
        assert [m for m, _ in fake.calls] == ['credential/get']

    def test_a_timeout_is_not_running(
        self, aws_dir, no_host_credentials, sock_dir
    ):
        # The SEP maps a call with no reply before the timeout to
        # NOT_RUNNING.
        path = str(sock_dir / 'silent.sock')
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.bind(path)
        silent.listen(1)
        write_config(aws_dir, DEV_PROFILE)
        try:
            with mock.patch.dict(
                'os.environ', AWS_CREDENTIAL_DAEMON_SOCKET=path
            ):
                with mock.patch(
                    'botocore.credentials.CredentialDaemonClient',
                    functools.partial(CredentialDaemonClient, timeout=0.2),
                ):
                    session = Session(profile='dev')
                    with pytest.raises(CredentialDaemonNotRunningError) as e:
                        session.get_credentials()
        finally:
            silent.close()
        assert str(e.value) == (
            f'The credential daemon on {path} didn\'t respond within the '
            '0.2-second call timeout. Start the credential daemon, or '
            'install it with \'aws configure credential-daemon install\', '
            'link its socket with \'aws configure credential-daemon link\', '
            'or set AWS_CREDENTIAL_DAEMON_SOCKET.'
        )


@pytest.fixture(
    params=[
        'group-writable-folder',
        'socket-owned-by-another-user',
        'peer-runs-as-another-user',
    ]
)
def untrusted_socket(request, fake):
    """The fake's socket fails one of the checks the credential provider's
    credential/get makes. Yields the reason the error gives."""
    other_uid = os.geteuid() + 4242
    if request.param == 'group-writable-folder':
        folder = os.path.dirname(fake.socket_path)
        os.chmod(folder, 0o770)
        try:
            yield f'the folder {folder} is writable by other users (mode 0770)'
        finally:
            os.chmod(folder, 0o700)
    elif request.param == 'socket-owned-by-another-user':
        real_lstat = os.lstat

        def lstat_(path, *args, **kwargs):
            st = real_lstat(path, *args, **kwargs)
            if str(path) == fake.socket_path:
                fields = list(st)
                fields[4] = other_uid
                return os.stat_result(fields)
            return st

        with mock.patch('botocore.credential_daemon.trust.os.lstat', lstat_):
            yield f'the socket is owned by uid {other_uid}, not by you or root'
    else:
        with mock.patch(
            'botocore.credential_daemon.trust._peer_uid',
            return_value=other_uid,
        ):
            yield (
                f'the process serving it runs as uid {other_uid}, not as '
                'you, root or the socket\'s owner'
            )


@skip_if_windows
class TestSocketChecks:
    """The credential provider's credential/get checks the socket's
    folders, its owner and the user serving it (SocketChecks.PEER), and
    fails closed."""

    def test_the_provider_refuses_an_untrusted_socket(
        self, fake, aws_dir, no_host_credentials, untrusted_socket
    ):
        fake.seed('dev')
        fake.calls.clear()
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            Session(profile='dev').get_credentials()
        assert e.value.code == 'UNTRUSTED_SOCKET'
        assert str(e.value) == (
            'The CLI didn\'t trust the credential daemon socket '
            f'{fake.socket_path}, so it sent nothing to it: '
            f'{untrusted_socket}.'
        )
        assert START_HINT not in str(e.value)
        assert fake.calls == []

    def test_the_provider_checks_a_trusted_socket(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        with (
            mock.patch(
                'botocore.credential_daemon.transport.check_socket',
                wraps=credential_daemon.check_socket,
            ) as check_socket,
            mock.patch(
                'botocore.credential_daemon.transport.check_peer',
                wraps=credential_daemon.check_peer,
            ) as check_peer,
        ):
            credentials = Session(profile='dev').get_credentials()
            assert credentials.get_frozen_credentials().access_key
        assert check_socket.call_count == check_peer.call_count == 1
        assert credential_gets(fake) == [{'name': 'dev'}]

    def test_the_provider_asks_for_the_peer_checks(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        with mock.patch.object(
            _Connection, 'open', wraps=_Connection.open
        ) as open_:
            Session(profile='dev').get_credentials()
        assert open_.call_args.kwargs == {'checks': SocketChecks.PEER}

    def test_the_provider_never_checks_the_code_signature(self, fake, aws_dir):
        # On macOS, the signature check is for calls that send secrets or
        # start sign-ins, not credential/get.
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        with (
            mock.patch(
                'botocore.credential_daemon.transport.checks_code_signature',
                return_value=True,
            ),
            mock.patch(
                'botocore.credential_daemon.transport.check_code_signature'
            ) as check,
        ):
            Session(profile='dev').get_credentials()
        check.assert_not_called()
        assert credential_gets(fake) == [{'name': 'dev'}]

    def test_other_calls_keep_the_full_checks(self, fake):
        # Commands that send secrets or start sign-ins use the default.
        with mock.patch.object(
            _Connection, 'open', wraps=_Connection.open
        ) as open_:
            CredentialDaemonClient(socket_path=fake.socket_path).probe()
        assert open_.call_args.kwargs == {'checks': SocketChecks.FULL}


class TestErrorAdviceByKind:
    """The advice must work for the kind of profile it's given to."""

    SSO_CONFIG = '''
        [profile admin]
        credential_daemon = acme
        sso_session = acme
        sso_account_id = 111111111111
        sso_role_name = Admin

        [sso-session acme]
        sso_start_url = https://acme.awsapps.com/start
        sso_region = us-east-1
    '''
    KEYS_CONFIG = '''
        [profile ci]
        credential_storage = daemon
        credential_daemon = ci
    '''
    # An older SSO profile, with no sso-session.
    LEGACY_SSO_CONFIG = '''
        [profile legacy]
        credential_daemon = legacy
        sso_start_url = https://acme.awsapps.com/start
        sso_region = us-east-1
        sso_account_id = 111111111111
        sso_role_name = Admin
    '''

    def not_running(self, aws_dir, sock_dir, config, profile):
        missing = str(sock_dir / 'missing.sock')
        write_config(aws_dir, config)
        with mock.patch.dict(
            'os.environ', AWS_CREDENTIAL_DAEMON_SOCKET=missing
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                Session(profile=profile).get_credentials()
        return str(e.value)

    @pytest.mark.parametrize(
        'config, profile',
        [
            (DEV_PROFILE, 'dev'),
            (KEYS_CONFIG, 'ci'),
            (SSO_CONFIG, 'admin'),
            (LEGACY_SSO_CONFIG, 'legacy'),
        ],
    )
    def test_not_running_says_only_that(
        self, aws_dir, no_host_credentials, sock_dir, config, profile
    ):
        # Say only that the credential daemon isn't running, for every kind,
        # with no move-back advice.
        message = self.not_running(aws_dir, sock_dir, config, profile)
        missing = sock_dir / 'missing.sock'
        assert message == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{missing}: No such file or directory. Start the credential '
            'daemon, or install it with \'aws configure credential-daemon '
            'install\', link its socket with \'aws configure '
            'credential-daemon link\', or set AWS_CREDENTIAL_DAEMON_SOCKET.'
        )

    @pytest.mark.parametrize(
        'config, profile', [('KEYS_CONFIG', 'ci'), ('SSO_CONFIG', 'admin')]
    )
    def test_not_found_names_every_way_to_sign_in(
        self, fake, aws_dir, no_host_credentials, config, profile
    ):
        # With no row, nothing says what the credential held, and nothing
        # is guessed from the profile's config: following "Run aws login"
        # would turn a keys profile into an aws login profile, possibly for
        # another identity.
        write_config(aws_dir, getattr(self, config))
        with pytest.raises(CredentialDaemonCredentialNotFoundError) as e:
            Session(profile=profile).get_credentials()
        name = 'ci' if profile == 'ci' else 'acme'
        assert str(e.value) == (
            f"The credential daemon has no credential named '{name}'. Sign "
            f"in again with 'aws login --profile {profile}', or remove "
            'credential_daemon from the profile and enter its keys with '
            f"'aws configure --profile {profile}'. The credential daemon "
            f'said: No credential named {name}'
        )

    def test_reauth_advice_comes_from_the_source(
        self, fake, aws_dir, no_host_credentials
    ):
        # The credential daemon's row says what the credential holds,
        # whatever the profile's settings.
        fake.seed('dev', kind='aws_login', status=NO_SESSION)
        fake.seed('ci', kind='aws_iam_user', status=NO_SESSION)
        write_config(
            aws_dir,
            textwrap.dedent(DEV_PROFILE) + textwrap.dedent(self.KEYS_CONFIG),
        )
        with pytest.raises(CredentialDaemonReauthRequiredError) as login_error:
            Session(profile='dev').get_credentials()
        with pytest.raises(CredentialDaemonReauthRequiredError) as keys_error:
            Session(profile='ci').get_credentials()
        assert str(login_error.value) == (
            "Session for profile 'dev' has ended. Run 'aws login --profile dev'."
            " The credential daemon said: credential 'dev' requires "
            're-authentication (complete SSO sign-in in a browser)'
        )
        assert str(keys_error.value) == (
            "The access keys for profile 'ci' can't be used. To use files "
            'for it, remove credential_daemon from the profile, then enter '
            "its keys with 'aws configure --profile ci'. Or store them in a "
            "new profile with 'aws configure --profile NEW-NAME'."
            " The credential daemon said: credential 'ci' requires "
            're-authentication (complete SSO sign-in in a browser)'
        )

    def test_an_sso_credential_on_a_login_profile_gets_the_sso_advice(
        self, fake, aws_dir, no_host_credentials
    ):
        fake.seed('dev', kind=KIND_SSO, principal=None, status=NO_SESSION)
        write_config(aws_dir, DEV_PROFILE)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile='dev').get_credentials()
        assert str(e.value).startswith(
            "Session for profile 'dev' has ended. Sign in again with the "
            "tool that stored credential 'dev', or remove credential_daemon "
            "from the profile and run 'aws sso login --profile dev'."
        )

    @pytest.mark.parametrize(
        'source, advice',
        [
            ('aws_login', "Run 'aws login --profile ci'."),
            (
                'aws_idc_sso',
                "Sign in again with the tool that stored credential 'ci', or "
                'remove credential_daemon from the profile and run '
                "'aws sso login --profile ci'.",
            ),
            (
                'aws_iam_user',
                'To use files for it, remove credential_daemon from the '
                "profile, then enter its keys with 'aws configure --profile "
                "ci'. Or store them in a new profile with 'aws configure "
                "--profile NEW-NAME'.",
            ),
        ],
    )
    def test_not_found_with_a_listed_source_follows_it(
        self, fake, aws_dir, no_host_credentials, source, advice
    ):
        # Such as keys that were signed out: the list still has the row.
        write_config(aws_dir, self.KEYS_CONFIG)
        row = [CredentialRow.from_wire({'credential': 'ci', 'source': source})]
        with (
            mock.patch.object(
                CredentialDaemonClient, 'list_credentials', return_value=row
            ),
            pytest.raises(CredentialDaemonCredentialNotFoundError) as e,
        ):
            Session(profile='ci').get_credentials()
        assert str(e.value) == (
            f"The credential daemon has no credential named 'ci'. {advice} "
            'The credential daemon said: No credential named ci'
        )

    @pytest.mark.parametrize(
        'config, profile, name',
        [
            ('DEV_PROFILE', 'dev', 'dev'),
            ('SSO_CONFIG', 'admin', 'acme'),
            ('LEGACY_SSO_CONFIG', 'legacy', 'legacy'),
            ('KEYS_CONFIG', 'ci', 'ci'),
        ],
    )
    @pytest.mark.parametrize('listed', ['failed', 'no row', 'no source'])
    def test_reauth_advice_without_a_source_names_every_way_to_sign_in(
        self,
        fake,
        aws_dir,
        no_host_credentials,
        config,
        profile,
        name,
        listed,
    ):
        # Only the row's source says what the credential holds. When the
        # list can't say, nothing is guessed from the profile's SSO
        # settings, and the credential daemon's error still shows.
        fake.seed(name, kind=KIND_SSO, principal=None, status=NO_SESSION)
        text = (
            DEV_PROFILE if config == 'DEV_PROFILE' else getattr(self, config)
        )
        write_config(aws_dir, text)
        if listed == 'failed':
            fake.fail_next('credential/list', 'INTERNAL', 'busy')
            rows = contextlib.nullcontext()
        else:
            row = (
                []
                if listed == 'no row'
                else [CredentialRow.from_wire({'credential': name})]
            )
            rows = mock.patch.object(
                CredentialDaemonClient, 'list_credentials', return_value=row
            )
        with rows, pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile=profile).get_credentials()
        # Only a failed list says the CLI couldn't ask, and nothing calls
        # it a session, since it may hold keys.
        why = (
            ", and the CLI couldn't ask the credential daemon how it was "
            'stored'
            if listed == 'failed'
            else ''
        )
        assert str(e.value) == (
            f"The credential for profile '{profile}' can't be used{why}. Sign "
            f"in again with 'aws login --profile {profile}', or remove "
            'credential_daemon from the profile and enter its keys with '
            f"'aws configure --profile {profile}'. The credential daemon "
            f"said: credential '{name}' requires "
            're-authentication (complete SSO sign-in in a browser)'
        )
        assert e.value.code == 'REAUTH_REQUIRED'

    def test_a_login_credential_on_an_sso_profile_says_aws_login(
        self, fake, aws_dir, no_host_credentials
    ):
        # The source wins over the profile's SSO settings too.
        fake.seed('acme', kind='aws_login', status=NO_SESSION)
        write_config(aws_dir, self.SSO_CONFIG)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            "Session for profile 'admin' has ended. Run 'aws login "
            "--profile admin'. The credential daemon said: credential 'acme' "
            'requires re-authentication (complete SSO sign-in in a browser)'
        )

    def test_sso_reauth_names_the_tool_that_stored_it(
        self, fake, aws_dir, no_host_credentials
    ):
        # This release never stores SSO credentials and aws sso login
        # writes files only, so the advice doesn't send the customer there
        # while credential_daemon is set.
        fake.seed('acme', kind=KIND_SSO, principal=None, status=NO_SESSION)
        write_config(aws_dir, self.SSO_CONFIG)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            "Session for profile 'admin' has ended. Sign in again with the "
            "tool that stored credential 'acme', or remove credential_daemon "
            "from the profile and run 'aws sso login --profile admin'."
            " The credential daemon said: credential 'acme' requires "
            're-authentication (complete SSO sign-in in a browser)'
        )


class TestProfileErrors:
    def test_invalid_name(self, aws_dir):
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_daemon = me@corp
            ''',
        )
        with pytest.raises(InvalidConfigError) as e:
            Session(profile='dev').get_credentials()
        assert '"me@corp"' in str(e.value)

    @pytest.mark.parametrize(
        'key, value',
        [
            ('role_arn', 'arn:aws:iam::123456789012:role/Admin'),
            ('web_identity_token_file', '/tmp/token'),
        ],
    )
    def test_conflicting_keys(self, fake, aws_dir, key, value):
        fake.seed('dev')
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_daemon = dev
            {key} = {value}
            ''',
        )
        with pytest.raises(InvalidConfigError) as e:
            Session(profile='dev').get_credentials()
        assert 'credential_daemon' in str(e.value)
        assert key in str(e.value)
        assert credential_gets(fake) == []


class TestSso:
    SSO_CONFIG = '''
        [profile admin]
        credential_daemon = acme
        sso_session = acme
        sso_account_id = 111111111111
        sso_role_name = Admin

        [sso-session acme]
        sso_start_url = https://acme.awsapps.com/start
        sso_region = us-east-1
    '''

    def test_sends_the_profiles_account_and_role(self, fake, aws_dir):
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(aws_dir, self.SSO_CONFIG)
        credentials = Session(profile='admin').get_credentials()
        frozen = credentials.get_frozen_credentials()
        assert frozen.account_id == '111111111111'
        assert credential_gets(fake) == [
            {
                'credential': 'acme',
                'account_id': '111111111111',
                'role_name': 'Admin',
            }
        ]

    @pytest.mark.parametrize('kind', [KIND_LOGIN, KIND_IAM_USER])
    def test_other_profiles_ignore_stray_sso_account_and_role(
        self, fake, aws_dir, kind
    ):
        # Only an SSO profile sends its account and role.
        fake.seed('dev', kind=kind, principal=None)
        write_config(
            aws_dir,
            DEV_PROFILE
            + '''
    sso_account_id = 111111111111
    sso_role_name = Admin
''',
        )
        Session(profile='dev').get_credentials()
        assert credential_gets(fake) == [{'credential': 'dev'}]

    def test_a_profile_without_account_and_role_falls_through(
        self, fake, aws_dir
    ):
        # Such a profile is for bearer-token services, such as CodeCatalyst.
        # As in SSOProvider, the next credential source is tried.
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            """
            [profile codecatalyst]
            credential_daemon = acme
            sso_session = acme

            [sso-session acme]
            sso_start_url = https://acme.awsapps.com/start
            sso_region = us-east-1
            """,
            """
            [codecatalyst]
            aws_access_key_id = AKIDFILE
            aws_secret_access_key = file-secret
            """,
        )
        with no_credential_daemon_calls() as call:
            credentials = Session(profile='codecatalyst').get_credentials()
        assert credentials.access_key == 'AKIDFILE'
        assert credentials.method == 'shared-credentials-file'
        call.assert_not_called()

    def test_a_profile_without_account_and_role_falls_through_to_a_process(
        self, fake, aws_dir
    ):
        write_config(
            aws_dir,
            """
            [profile codecatalyst]
            credential_daemon = acme
            sso_start_url = https://acme.awsapps.com/start
            sso_region = us-east-1
            credential_process = make-credentials
            """,
        )
        process = mock.Mock(
            return_value=RefreshableCredentials.create_from_metadata(
                {
                    'access_key': 'AKIDPROCESS',
                    'secret_key': 'process-secret',
                    'token': None,
                    'expiry_time': '2100-01-01T00:00:00Z',
                },
                refresh_using=None,
                method='custom-process',
            )
        )
        with (
            mock.patch('botocore.credentials.ProcessProvider.load', process),
            no_credential_daemon_calls() as call,
        ):
            credentials = Session(profile='codecatalyst').get_credentials()
        assert credentials.access_key == 'AKIDPROCESS'
        assert credentials.method == 'custom-process'
        call.assert_not_called()

    @pytest.mark.parametrize(
        'present, missing',
        [
            ('sso_role_name = Admin', 'sso_account_id'),
            ('sso_account_id = 111111111111', 'sso_role_name'),
        ],
        ids=['no-account', 'no-role'],
    )
    def test_a_profile_with_half_a_role_is_an_error(
        self, fake, aws_dir, present, missing
    ):
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            f"""
            [profile admin]
            credential_daemon = acme
            sso_session = acme
            {present}

            [sso-session acme]
            sso_start_url = https://acme.awsapps.com/start
            sso_region = us-east-1
            """,
        )
        with pytest.raises(InvalidConfigError) as e:
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            'The profile "admin" is configured to use SSO but is missing '
            f'required configuration: {missing}'
        )
        assert credential_gets(fake) == []

    @pytest.mark.parametrize(
        'config, missing',
        [
            (
                """
                [profile admin]
                credential_daemon = acme
                sso_start_url = https://acme.awsapps.com/start
                sso_role_name = Admin
                """,
                'sso_account_id, sso_region',
            ),
            (
                """
                [profile admin]
                credential_daemon = acme
                sso_session = acme
                sso_account_id = 111111111111
                sso_role_name = Admin

                [sso-session acme]
                sso_start_url = https://acme.awsapps.com/start
                """,
                'sso_region',
            ),
        ],
        ids=['legacy-keys', 'sso-session'],
    )
    def test_lists_missing_settings_as_sso_provider_does(
        self, fake, aws_dir, config, missing
    ):
        write_config(aws_dir, config)
        with (
            no_credential_daemon_calls() as call,
            pytest.raises(InvalidConfigError) as e,
        ):
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            'The profile "admin" is configured to use SSO but is missing '
            f'required configuration: {missing}'
        )
        call.assert_not_called()

    def test_a_missing_sso_session_section_is_an_error(self, fake, aws_dir):
        write_config(
            aws_dir,
            """
            [profile admin]
            credential_daemon = acme
            sso_session = acme
            sso_account_id = 111111111111
            sso_role_name = Admin
            """,
        )
        with (
            no_credential_daemon_calls() as call,
            pytest.raises(InvalidConfigError) as e,
        ):
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            'The specified sso-session does not exist: "acme"'
        )
        call.assert_not_called()

    MISMATCH_CONFIG = '''
        [profile admin]
        credential_storage = {profile}
        {daemon}
        sso_session = acme
        {region}
        sso_account_id = 111111111111
        sso_role_name = Admin

        [profile other]
        {daemon}
        sso_session = acme
        sso_account_id = 111111111111
        sso_role_name = Admin

        [sso-session acme]
        credential_storage = {session}
        sso_start_url = https://acme.awsapps.com/start
        sso_region = us-east-1
    '''

    def test_the_sso_sessions_storage_wins_when_it_is_the_daemon(
        self, fake, aws_dir
    ):
        # The profile says files, the sso-session says the daemon: aws sso
        # login signed in to the daemon and wrote credential_daemon to each
        # profile on the session.
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            self.MISMATCH_CONFIG.format(
                profile='file',
                session='daemon',
                daemon='credential_daemon = acme',
                region='',
            ),
        )
        for profile in ('admin', 'other'):
            credentials = Session(profile=profile).get_credentials()
            assert credentials.get_frozen_credentials().access_key
        assert {get['credential'] for get in credential_gets(fake)} == {'acme'}

    def test_the_sso_sessions_storage_wins_when_it_is_files(
        self, fake, aws_dir
    ):
        # The profile says the daemon, the sso-session says files: aws sso
        # login signed in with files and wrote no credential_daemon, so the
        # SSO provider is used and doesn't refuse the mismatch.
        write_config(
            aws_dir,
            self.MISMATCH_CONFIG.format(
                profile='daemon', session='file', daemon='', region=''
            ),
        )
        with no_credential_daemon_calls() as call:
            for profile in ('admin', 'other'):
                credentials = Session(profile=profile).get_credentials()
                assert credentials.method == 'sso'
        call.assert_not_called()

    @pytest.mark.parametrize(
        'daemon', ['', 'credential_daemon = acme'], ids=['files', 'daemon']
    )
    def test_another_sso_setting_that_differs_is_still_an_error(
        self, fake, aws_dir, daemon
    ):
        write_config(
            aws_dir,
            self.MISMATCH_CONFIG.format(
                profile='file',
                session='file',
                daemon=daemon,
                region='sso_region = eu-west-1',
            ),
        )
        with (
            no_credential_daemon_calls() as call,
            pytest.raises(InvalidConfigError) as e,
        ):
            Session(profile='admin').get_credentials()
        assert str(e.value) == (
            'The value for sso_region is inconsistent between '
            'profile (eu-west-1) and sso-session (us-east-1).'
        )
        call.assert_not_called()

    def test_the_profiles_credential_daemon_wins_over_the_sessions(
        self, fake, aws_dir
    ):
        # credential_daemon names the profile's own credential, so a
        # different one on the sso-session is no conflict and isn't used.
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            self.SSO_CONFIG.replace(
                'sso_region = us-east-1',
                'sso_region = us-east-1\n        credential_daemon = other',
            ),
        )
        credentials = Session(profile='admin').get_credentials()
        assert credentials.get_frozen_credentials().access_key
        assert [get['credential'] for get in credential_gets(fake)] == ['acme']

    def test_an_empty_value_counts_as_set(self, fake, aws_dir):
        # As in SSOProvider, only a missing key counts as missing, so the
        # empty value goes to the credential daemon, which rejects it.
        fake.seed('acme', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            """
            [profile admin]
            credential_daemon = acme
            sso_session = acme
            sso_account_id =
            sso_role_name = Admin

            [sso-session acme]
            sso_start_url = https://acme.awsapps.com/start
            sso_region = us-east-1
            """,
        )
        with pytest.raises(CredentialDaemonRequestRejectedError):
            Session(profile='admin').get_credentials()
        assert credential_gets(fake) == [
            {'credential': 'acme', 'account_id': '', 'role_name': 'Admin'}
        ]

    def test_reauth_names_the_tool_that_stored_it(self, fake, aws_dir):
        fake.seed('acme', kind=KIND_SSO, principal=None, status=NO_SESSION)
        write_config(aws_dir, self.SSO_CONFIG)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            Session(profile='admin').get_credentials()
        assert (
            "Sign in again with the tool that stored credential 'acme', or "
            'remove credential_daemon from the profile and run '
            "'aws sso login --profile admin'."
        ) in str(e.value)


class TestRoleChaining:
    @ONE_HOUR
    def test_role_profile_uses_credential_daemon_source_credentials(
        self, fake, aws_dir
    ):
        fake.seed('dev')
        write_config(
            aws_dir,
            '''
            [profile admin]
            role_arn = arn:aws:iam::123456789012:role/Admin
            source_profile = dev
            region = us-east-1

            [profile dev]
            credential_daemon = dev
            ''',
        )
        session = StubbedSession(profile='admin')
        stubber = session.stub(
            'sts', aws_access_key_id='x', aws_secret_access_key='y'
        )
        stubber.add_response(
            'assume_role',
            {
                'Credentials': {
                    'AccessKeyId': 'ASIAROLEEXAMPLE12345',
                    'SecretAccessKey': 'role-secret',
                    'SessionToken': 'role-token',
                    'Expiration': datetime(2099, 1, 1, tzinfo=timezone.utc),
                },
                'AssumedRoleUser': {
                    'AssumedRoleId': 'AROA:a',
                    'Arn': 'arn:aws:sts::123456789012:assumed-role/Admin/a',
                },
            },
            {
                'RoleArn': 'arn:aws:iam::123456789012:role/Admin',
                'RoleSessionName': ANY,
            },
        )
        stubber.activate()
        create_client = mock.Mock(wraps=session.create_client)
        session.create_client = create_client

        credentials = session.get_credentials()
        assert (
            credentials.get_frozen_credentials().access_key
            == 'ASIAROLEEXAMPLE12345'
        )
        assert credential_gets(fake) == [{'credential': 'dev'}]
        sts_calls = [
            call
            for call in create_client.call_args_list
            if call[0] == ('sts',)
        ]
        source_key = sts_calls[-1][1]['aws_access_key_id']
        assert source_key.startswith('ASIA')
        assert source_key != 'ASIAROLEEXAMPLE12345'


class TestSsoProfileWithoutRoleAndARole:
    """An SSO daemon profile with neither sso_account_id nor sso_role_name
    resolves as if credential_daemon weren't set, so its role_arn or
    web_identity_token_file is used."""

    SSO_SESSION = '''
        [sso-session corp]
        sso_start_url = https://corp.awsapps.com/start
        sso_region = us-east-1
    '''
    BASE = '''
        [profile base]
        aws_access_key_id = AKIDBASE
        aws_secret_access_key = s
    '''
    ROLE_ARN = 'arn:aws:iam::123456789012:role/Admin'

    def stub_assume_role(self, session, operation='assume_role'):
        stubber = session.stub(
            'sts', aws_access_key_id='x', aws_secret_access_key='y'
        )
        expected = {'RoleArn': self.ROLE_ARN, 'RoleSessionName': ANY}
        if operation == 'assume_role_with_web_identity':
            expected['WebIdentityToken'] = 'token'
        stubber.add_response(
            operation,
            {
                'Credentials': {
                    'AccessKeyId': 'ASIAROLEEXAMPLE12345',
                    'SecretAccessKey': 'role-secret',
                    'SessionToken': 'role-token',
                    'Expiration': datetime(2099, 1, 1, tzinfo=timezone.utc),
                },
                'AssumedRoleUser': {
                    'AssumedRoleId': 'AROA:a',
                    'Arn': 'arn:aws:sts::123456789012:assumed-role/Admin/a',
                },
            },
            expected,
        )
        stubber.activate()
        create_client = mock.Mock(wraps=session.create_client)
        session.create_client = create_client
        return stubber, create_client

    def source_key(self, create_client):
        sts_calls = [
            call
            for call in create_client.call_args_list
            if call[0] == ('sts',)
        ]
        return sts_calls[-1][1].get('aws_access_key_id')

    @pytest.mark.parametrize(
        'sso_keys',
        [
            'sso_session = corp',
            'sso_start_url = https://corp.awsapps.com/start\n'
            '            sso_region = us-east-1',
        ],
        ids=['sso-session', 'legacy-keys'],
    )
    def test_assumes_the_role_without_calling_credential_daemon(
        self, fake, aws_dir, sso_keys
    ):
        fake.seed('corp', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            f'''
            [profile dev]
            {sso_keys}
            credential_daemon = corp
            role_arn = {self.ROLE_ARN}
            source_profile = base
            '''
            + self.BASE
            + self.SSO_SESSION,
        )
        session = StubbedSession(profile='dev')
        stubber, create_client = self.stub_assume_role(session)
        with no_credential_daemon_calls() as call:
            credentials = session.get_credentials()
            frozen = credentials.get_frozen_credentials()
        assert frozen.access_key == 'ASIAROLEEXAMPLE12345'
        assert credentials.method == 'assume-role'
        assert self.source_key(create_client) == 'AKIDBASE'
        stubber.assert_no_pending_responses()
        call.assert_not_called()
        assert fake.calls == []

    def test_a_role_profile_can_source_it(self, fake, aws_dir):
        # The rules apply to a profile reached through source_profile too.
        write_config(
            aws_dir,
            f'''
            [profile top]
            role_arn = {self.ROLE_ARN}
            source_profile = dev

            [profile dev]
            sso_session = corp
            credential_daemon = corp
            role_arn = {self.ROLE_ARN}
            source_profile = base
            '''
            + self.BASE
            + self.SSO_SESSION,
        )
        session = StubbedSession(profile='top')
        stubber = session.stub(
            'sts', aws_access_key_id='x', aws_secret_access_key='y'
        )
        for key in ('ASIADEVEXAMPLE123456', 'ASIATOPEXAMPLE123456'):
            stubber.add_response(
                'assume_role',
                {
                    'Credentials': {
                        'AccessKeyId': key,
                        'SecretAccessKey': 'role-secret',
                        'SessionToken': 'role-token',
                        'Expiration': datetime(
                            2099, 1, 1, tzinfo=timezone.utc
                        ),
                    },
                },
                {'RoleArn': self.ROLE_ARN, 'RoleSessionName': ANY},
            )
        stubber.activate()
        with no_credential_daemon_calls() as call:
            credentials = session.get_credentials()
            frozen = credentials.get_frozen_credentials()
        assert frozen.access_key == 'ASIATOPEXAMPLE123456'
        stubber.assert_no_pending_responses()
        call.assert_not_called()

    def test_uses_web_identity_without_calling_credential_daemon(
        self, fake, aws_dir
    ):
        token_file = aws_dir / 'token'
        token_file.write_text('token')
        write_config(
            aws_dir,
            f'''
            [profile dev]
            sso_session = corp
            credential_daemon = corp
            role_arn = {self.ROLE_ARN}
            web_identity_token_file = {token_file}
            '''
            + self.SSO_SESSION,
        )
        session = StubbedSession(profile='dev')
        stubber, _ = self.stub_assume_role(
            session, 'assume_role_with_web_identity'
        )
        with no_credential_daemon_calls() as call:
            credentials = session.get_credentials()
            frozen = credentials.get_frozen_credentials()
        assert frozen.access_key == 'ASIAROLEEXAMPLE12345'
        assert credentials.method == 'assume-role-with-web-identity'
        stubber.assert_no_pending_responses()
        call.assert_not_called()

    @pytest.mark.parametrize(
        'sso_role_keys',
        [
            'sso_account_id = 111111111111\n            sso_role_name = Admin',
            'sso_account_id = 111111111111',
            'sso_role_name = Admin',
        ],
        ids=['both-keys', 'account-only', 'role-only'],
    )
    @pytest.mark.parametrize(
        'key, value',
        [
            ('role_arn', ROLE_ARN),
            ('web_identity_token_file', '/tmp/token'),
        ],
    )
    def test_a_profile_with_a_key_is_still_an_error(
        self, fake, aws_dir, sso_role_keys, key, value
    ):
        fake.seed('corp', kind=KIND_SSO, principal=None)
        write_config(
            aws_dir,
            f'''
            [profile dev]
            sso_session = corp
            credential_daemon = corp
            {sso_role_keys}
            {key} = {value}
            source_profile = base
            '''
            + self.BASE
            + self.SSO_SESSION,
        )
        with pytest.raises(InvalidConfigError) as e:
            Session(profile='dev').get_credentials()
        assert 'credential_daemon' in str(e.value)
        assert key in str(e.value)
        assert credential_gets(fake) == []


class TestUserAgent:
    @pytest.mark.parametrize(
        'kind,config,profile',
        [
            (KIND_LOGIN, DEV_PROFILE, 'dev'),
            (KIND_IAM_USER, DEV_PROFILE, 'dev'),
            (KIND_SSO, TestSso.SSO_CONFIG, 'admin'),
        ],
    )
    def test_the_feature_id_is_credential_daemon(
        self, fake, aws_dir, kind, config, profile
    ):
        # SEP Feature ID: CREDENTIAL_DAEMON (Aq in FEATURES.md), for
        # every source, from one credential/get and no credential/list.
        name = 'acme' if profile == 'admin' else 'dev'
        fake.seed(name, kind=kind, principal=None)
        write_config(aws_dir, config)
        with start_as_current_context():
            Session(profile=profile).get_credentials()
            assert get_context().features == {'Aq'}
        assert [method for method, _ in fake.calls] == ['credential/get']

    def test_keys_in_files_dont_send_the_feature_id(self, fake, aws_dir):
        write_config(
            aws_dir,
            '''
            [profile dev]
            region = us-west-2
            ''',
            '''
            [dev]
            aws_access_key_id = AKIDFILE
            aws_secret_access_key = file-secret
            ''',
        )
        with start_as_current_context():
            credentials = Session(profile='dev').get_credentials()
            assert credentials.access_key == 'AKIDFILE'
            assert 'Aq' not in get_context().features
        assert fake.calls == []

    def test_every_fetch_is_one_credential_get(self, fake, aws_dir):
        fake.seed('dev', kind=KIND_LOGIN)
        write_config(aws_dir, DEV_PROFILE)
        for _ in range(2):
            with start_as_current_context():
                Session(profile='dev').get_credentials()
                assert get_context().features == {'Aq'}
        assert [method for method, _ in fake.calls] == [
            'credential/get',
            'credential/get',
        ]

    def test_requests_carry_the_feature_ids(self, fake, aws_dir):
        fake.seed('dev')
        write_config(aws_dir, DEV_PROFILE)
        data_path = os.path.join(os.path.dirname(awscli.__file__), 'data')
        runner = CLIRunner(
            env={
                'AWS_DATA_PATH': data_path,
                'AWS_DEFAULT_REGION': 'us-west-2',
                'AWS_CONFIG_FILE': str(aws_dir / 'config'),
                'AWS_SHARED_CREDENTIALS_FILE': str(aws_dir / 'credentials'),
                'AWS_EC2_METADATA_DISABLED': 'true',
                'AWS_CREDENTIAL_DAEMON_SOCKET': fake.socket_path,
                'HOME': str(aws_dir / 'home'),
                'AWS_LOGIN_CACHE_DIRECTORY': str(aws_dir / 'cache'),
            }
        )
        runner.add_response(
            HTTPResponse(
                body=(
                    b'<GetCallerIdentityResponse><GetCallerIdentityResult>'
                    b'<Account>123456789012</Account>'
                    b'</GetCallerIdentityResult></GetCallerIdentityResponse>'
                )
            )
        )
        result = runner.run(['sts', 'get-caller-identity', '--profile', 'dev'])
        assert result.rc == 0, result.stderr
        user_agent = (
            result.aws_requests[0].http_requests[0].headers['User-Agent']
        )
        features = set(parse_registered_feature_ids(user_agent))
        assert 'Aq' in features


class TestResponsesTheFakeDoesNotSend:
    PROFILE = {'profiles': {'dev': {'credential_daemon': 'dev'}}}

    def provider(self, result):
        client = mock.Mock()
        client.get_credentials.return_value = result
        return CredentialDaemonProvider(
            load_config=lambda: self.PROFILE,
            profile_name='dev',
            credential_daemon_client=client,
        )

    @pytest.mark.parametrize(
        'expiry', [{'expires_at': None}, {'expires_at': ''}, {}]
    )
    def test_credentials_of_unknown_lifetime_are_refused(self, expiry):
        # Like credsd's own client: the credential daemon always sends an
        # expiry for session credentials.
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
                'session_token': 'token',
            },
            **expiry,
        }
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.provider(result).load()
        assert str(e.value) == (
            "The credential daemon sent a reply the CLI can't use for 'dev': "
            'expires_at is missing.'
        )

    def test_refresh_refuses_credentials_of_unknown_lifetime(self):
        client = mock.Mock()
        client.get_credentials.return_value = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': '2000-01-01T00:00:00Z',
        }
        credentials = CredentialDaemonProvider(
            load_config=lambda: self.PROFILE,
            profile_name='dev',
            credential_daemon_client=client,
        ).load()
        client.get_credentials.return_value = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID2',
                'secret_access_key': 'secret2',
            },
            'expires_at': None,
        }
        with pytest.raises(CredentialDaemonProtocolError):
            credentials.get_frozen_credentials()

    @pytest.mark.parametrize(
        'result',
        [
            {},
            {'material': {'type': 'session_credentials'}},
            {
                'material': {
                    'type': 'session_credentials',
                    'access_key_id': 'AKID',
                    'secret_access_key': '',
                }
            },
            {
                'material': {
                    'type': 'session_credentials',
                    'access_key_id': 'AKID',
                    'secret_access_key': 'secret',
                },
                'expires_at': '2026-10-27T20:00:00',
            },
            {
                'material': {
                    'type': 'session_credentials',
                    'access_key_id': 'AKID',
                    'secret_access_key': 'secret',
                },
                'expires_at': 'soon',
            },
        ],
    )
    def test_unusable_responses(self, result):
        with pytest.raises(CredentialDaemonProtocolError):
            self.provider(result).load()

    def test_unsupported_material_type_names_it(self):
        # SEP: name the type and say to update.
        result = {
            'material': {'type': 'bearer\x1b[2K', 'token': 't'},
            'expires_at': '2099-01-01T00:00:00Z',
        }
        with pytest.raises(CredentialDaemonUnsupportedMaterialError) as e:
            self.provider(result).load()
        assert str(e.value) == (
            'This version of the AWS CLI doesn\'t support material type '
            "bearer[2K from the credential daemon for 'dev'. Update the AWS "
            'CLI.'
        )
        assert e.value.code == 'UNSUPPORTED_MATERIAL'
        assert not isinstance(e.value, CredentialDaemonProtocolError)

    @pytest.mark.parametrize(
        'material',
        [
            {'type': 'access_token', 'token': 't'},
            # Whatever the other fields hold.
            {
                'type': 'access_token',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
        ],
    )
    def test_other_material_is_unsupported_material(self, material):
        result = {'material': material, 'expires_at': None}
        with pytest.raises(CredentialDaemonUnsupportedMaterialError) as e:
            self.provider(result).load()
        assert 'access_token' in str(e.value)

    @pytest.mark.parametrize(
        'material, field',
        [
            ({'access_key_id': 'AKID', 'secret_access_key': 's'}, 'type'),
            (
                {
                    'type': None,
                    'access_key_id': 'AKID',
                    'secret_access_key': 's',
                },
                'type',
            ),
            (
                {
                    'type': '',
                    'access_key_id': 'AKID',
                    'secret_access_key': 's',
                },
                'type',
            ),
            (
                {
                    'type': 'session_credentials',
                    'access_key_id': None,
                    'secret_access_key': 's',
                },
                'access_key_id',
            ),
            (
                {
                    'type': 'session_credentials',
                    'access_key_id': 'AKID',
                    'secret_access_key': '',
                },
                'secret_access_key',
            ),
            (
                {
                    'type': 'session_credentials',
                    'access_key_id': 'AKID',
                    'secret_access_key': 7,
                },
                'secret_access_key',
            ),
        ],
    )
    def test_a_missing_field_is_named(self, material, field):
        result = {'material': material, 'expires_at': '2099-01-01T00:00:00Z'}
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.provider(result).load()
        assert str(e.value) == (
            "The credential daemon sent a reply the CLI can't use for 'dev': "
            f'material.{field} is missing.'
        )

    def test_errors_dont_quote_the_reply(self):
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'ASIASECRETKEYID',
                'secret_access_key': 'topsecret',
                'session_token': 'tokensecret',
            },
            'expires_at': 'soon-topsecret',
        }
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.provider(result).load()
        for value in ('ASIASECRETKEYID', 'topsecret', 'tokensecret'):
            assert value not in str(e.value)
        assert 'expires_at isn\'t a time with a time zone' in str(e.value)

    @pytest.mark.parametrize(
        'expires_at, expected',
        [
            ('2026-10-27T20:27:02Z', '2026-10-27T20:27:02+00:00'),
            ('2026-10-27T20:27:02.5Z', '2026-10-27T20:27:02.500000+00:00'),
            (
                '2026-10-27T20:27:02.123456789Z',
                '2026-10-27T20:27:02.123456+00:00',
            ),
            # Any time with a time zone counts, in UTC.
            ('2026-10-27T20:27:02+00:00', '2026-10-27T20:27:02+00:00'),
            ('2026-10-27T21:27:02+01:00', '2026-10-27T20:27:02+00:00'),
            ('2026-10-27T15:27:02-05:00', '2026-10-27T20:27:02+00:00'),
            ('2026-10-27 20:27:02Z', '2026-10-27T20:27:02+00:00'),
            (
                '2026-10-27T20:27:02.1234567890Z',
                '2026-10-27T20:27:02.123456+00:00',
            ),
        ],
    )
    def test_expiry_is_any_time_with_a_time_zone_in_utc(
        self, expires_at, expected
    ):
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': expires_at,
        }
        fetcher = CredentialDaemonFetcher(mock.Mock(), 'dev', 'dev')
        assert fetcher._to_metadata(result)['expiry_time'] == expected

    @pytest.mark.parametrize(
        'expires_at',
        [
            'soon',
            7,
            # No time zone.
            '2026-10-27T20:27:02',
            '2026-10-27T20:27:02.Z',
            '2026-13-27T20:27:02Z',
            '2026-02-30T20:27:02Z',
            # Out of range once in UTC.
            '9999-12-31T23:59:59-01:00',
            # A zone name other than UTC has no offset, wherever the host is.
            '2026-10-27T20:27:02 EST',
            '2026-10-27T20:27:02 QWERT',
            # Longer than any time.
            '2026-10-27T20:27:02' + '0' * 64 + 'Z',
        ],
    )
    def test_an_unparseable_expiry_is_a_protocol_error(self, expires_at):
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': expires_at,
        }
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.provider(result).load()
        assert 'expires_at' in str(e.value)

    @pytest.mark.parametrize('zone', ['EST', 'QWERT'])
    def test_an_unknown_zone_name_prints_no_warning(self, zone):
        # dateutil warns about a zone name it doesn't know, and the warning
        # would show part of expires_at on stderr.
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': f'2026-10-27T20:27:02 {zone}',
        }
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with pytest.raises(CredentialDaemonProtocolError):
                self.provider(result).load()

    def test_the_hosts_own_zone_name_isnt_local_time(self, monkeypatch):
        # dateutil reads a name in time.tzname as the host's local zone, so
        # the same reply would work on one host and not another.
        monkeypatch.setattr('time.tzname', ('PST', 'PDT'))
        result = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': '2026-10-27T20:27:02 PST',
        }
        with pytest.raises(CredentialDaemonProtocolError):
            self.provider(result).load()

    def test_the_reply_credential_isnt_compared(self):
        # The reply on a connection answers its one request.
        result = {
            'credential': 'someone-else',
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': '2099-01-01T00:00:00Z',
        }
        credentials = self.provider(result).load()
        assert credentials.get_frozen_credentials().access_key == 'AKID'

    def test_account_and_role_are_sent_only_together(self):
        client = mock.Mock()
        client.list_credentials.return_value = []
        client.get_credentials.return_value = {
            'material': {
                'type': 'session_credentials',
                'access_key_id': 'AKID',
                'secret_access_key': 'secret',
            },
            'expires_at': '2099-01-01T00:00:00Z',
        }
        # An SSO profile with an account and no role. Its SSO check is
        # stubbed out here, so the fetch runs, and sends neither.
        profile = {
            'credential_daemon': 'dev',
            'sso_session': 'acme',
            'sso_account_id': '111111111111',
        }
        provider = CredentialDaemonProvider(
            lambda: {'profiles': {'dev': profile}},
            'dev',
            credential_daemon_client=client,
        )
        with mock.patch(
            'botocore.credentials.load_sso_profile_config', return_value={}
        ):
            provider.load()
        client.get_credentials.assert_called_with(
            'dev', account_id=None, role_name=None
        )


class TestProfileNamesInMessages:
    # Profile names aren't limited to a safe charset, so every provider
    # message shows the name without control characters.
    PROFILE = 'dev\x1b[2K\x07'
    SHOWN = 'dev[2K'

    def explain(self, error, rows=None):
        client = mock.Mock()
        client.get_credentials.side_effect = error
        if rows is None:
            client.list_credentials.side_effect = (
                CredentialDaemonRequestRejectedError(error_msg='busy')
            )
        else:
            client.list_credentials.return_value = rows
        fetcher = CredentialDaemonFetcher(client, self.PROFILE, 'dev')
        with pytest.raises(CredentialDaemonError) as e:
            fetcher.fetch_credentials()
        message = str(e.value)
        assert '\x1b' not in message
        assert '\x07' not in message
        return message

    @pytest.mark.parametrize(
        'source, expected',
        [
            (
                None,
                "The credential for profile 'dev[2K' can't be used, and the "
                "CLI couldn't ask the credential daemon how it was stored. "
                "Sign in again with 'aws login --profile dev[2K', or remove "
                'credential_daemon from the profile and enter its keys with '
                "'aws configure --profile dev[2K'.",
            ),
            (
                'aws_login',
                "Session for profile 'dev[2K' has ended. Run 'aws login "
                "--profile dev[2K'.",
            ),
            (
                'aws_iam_user',
                "The access keys for profile 'dev[2K' can't be used. To use "
                'files for it, remove credential_daemon from the profile, '
                "then enter its keys with 'aws configure --profile dev[2K'. "
                "Or store them in a new profile with 'aws configure "
                "--profile NEW-NAME'.",
            ),
        ],
    )
    def test_reauth(self, source, expected):
        rows = (
            None
            if source is None
            else [
                CredentialRow.from_wire(
                    {'credential': 'dev', 'source': source}
                )
            ]
        )
        error = CredentialDaemonReauthRequiredError(
            error_msg='ended', code='REAUTH_REQUIRED'
        )
        assert self.explain(error, rows) == expected

    @pytest.mark.parametrize(
        'source, advice',
        [
            (
                None,
                "Sign in again with 'aws login --profile dev[2K', or remove "
                'credential_daemon from the profile and enter its keys with '
                "'aws configure --profile dev[2K'.",
            ),
            (
                'aws_idc_sso',
                "Sign in again with the tool that stored credential 'dev', or "
                'remove credential_daemon from the profile and run '
                "'aws sso login --profile dev[2K'.",
            ),
            (
                'aws_iam_user',
                'To use files for it, remove credential_daemon from the '
                "profile, then enter its keys with 'aws configure --profile "
                "dev[2K'. Or store them in a new profile with 'aws configure "
                "--profile NEW-NAME'.",
            ),
        ],
    )
    def test_not_found(self, source, advice):
        rows = (
            None
            if source is None
            else [
                CredentialRow.from_wire(
                    {'credential': 'dev', 'source': source}
                )
            ]
        )
        error = CredentialDaemonCredentialNotFoundError(
            error_msg='gone', code='CREDENTIAL_NOT_FOUND'
        )
        assert self.explain(error, rows) == (
            f"The credential daemon has no credential named 'dev'. {advice}"
        )

    def test_sso_advice_shows_the_credential_name_without_control_characters(
        self,
    ):
        # The provider refuses such names in the config, but the advice
        # strips them all the same, as it does the profile name. (The
        # error's own first sentence is botocore's and isn't checked here.)
        name = 'acme\x1b[2K'
        client = mock.Mock()
        client.get_credentials.side_effect = (
            CredentialDaemonCredentialNotFoundError(
                error_msg='gone', code='CREDENTIAL_NOT_FOUND'
            )
        )
        client.list_credentials.return_value = [
            CredentialRow.from_wire(
                {'credential': name, 'source': 'aws_idc_sso'}
            )
        ]
        fetcher = CredentialDaemonFetcher(client, self.PROFILE, name)
        with pytest.raises(CredentialDaemonError) as e:
            fetcher.fetch_credentials()
        assert (
            "Sign in again with the tool that stored credential 'acme[2K', or "
            'remove credential_daemon from the profile and run '
            "'aws sso login --profile dev[2K'."
        ) in str(e.value)

    def test_unusable(self):
        error = CredentialDaemonCredentialUnusableError(
            error_msg='drifted', code='CONFIG_DRIFTED'
        )
        assert self.explain(error) == (
            "The credential daemon can't use credential 'dev' for profile "
            "'dev[2K': its settings changed, or its stored data can't be "
            'checked.'
        )

    def test_unsupported_platform(self):
        message = self.explain(
            CredentialDaemonUnsupportedPlatformError(error_msg='windows')
        )
        assert "profile 'dev[2K'" in message


class TestErrorFields:
    # The provider's errors are built from fields, as botocore's fmt
    # errors are; error_msg still gives the whole message.
    def test_fields_build_the_message_and_stay_on_the_error(self):
        error = CredentialDaemonCredentialNotFoundError(
            credential_name='dev',
            advice="Run 'aws login --profile dev'.",
            code='CREDENTIAL_NOT_FOUND',
            daemon_message='No credential named dev',
        )
        assert str(error) == (
            "The credential daemon has no credential named 'dev'. Run 'aws "
            "login --profile dev'. The credential daemon said: No credential "
            'named dev'
        )
        assert error.kwargs['credential_name'] == 'dev'
        assert 'daemon_said' not in error.kwargs
        assert error.code == 'CREDENTIAL_NOT_FOUND'

    def test_error_msg_wins_over_the_fields(self):
        error = CredentialDaemonCredentialNotFoundError(
            error_msg='No credential named dev', code='CREDENTIAL_NOT_FOUND'
        )
        assert str(error) == 'No credential named dev'

    @pytest.mark.parametrize(
        'daemon_message, said',
        [
            (None, ''),
            ('timed out', ' The credential daemon said: timed out.'),
            ('timed out!', ' The credential daemon said: timed out!'),
        ],
    )
    def test_provider_unavailable_ends_the_daemons_sentence(
        self, daemon_message, said
    ):
        error = CredentialDaemonProviderUnavailableError(
            daemon_message=daemon_message
        )
        assert str(error) == (
            "The credential daemon couldn't get credentials from AWS."
            f'{said} If you use a proxy, set HTTPS_PROXY (and AWS_CA_BUNDLE, '
            "if the proxy inspects TLS) in the credential daemon's service "
            "settings. Settings in your shell don't reach it."
        )

    @pytest.mark.parametrize(
        'error',
        [
            CredentialDaemonCredentialUnusableError(
                credential_name='dev', profile='dev', daemon_message='x'
            ),
            CredentialDaemonProtocolError(
                credential_name='dev', problem='expires_at is missing'
            ),
            CredentialDaemonProtocolError(error_msg='bad reply'),
        ],
    )
    def test_errors_built_from_fields_can_be_pickled(self, error):
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is type(error)
        assert str(copy) == str(error)
        assert copy.kwargs == error.kwargs


class TestRefresh:
    # Until the CLI adopts the newer refresh rules, the provider uses
    # botocore's existing refresh, unchanged: the default 15 minute advisory
    # and 10 minute mandatory windows, as for LoginProvider.
    PROFILE = {'profiles': {'dev': {'credential_daemon': 'dev'}}}

    def client(self, expires_at, access_key='AKID'):
        client = mock.Mock()
        client.list_credentials.return_value = []
        client.get_credentials.return_value = self.result(
            expires_at, access_key
        )
        return client

    def result(self, expires_at, access_key='AKID'):
        return {
            'material': {
                'type': 'session_credentials',
                'access_key_id': access_key,
                'secret_access_key': 'secret',
                'session_token': 'token',
            },
            'expires_at': expires_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

    def load(self, client):
        return CredentialDaemonProvider(
            load_config=lambda: self.PROFILE,
            profile_name='dev',
            credential_daemon_client=client,
        ).load()

    def advance_to(self, credentials, now):
        credentials._time_fetcher = lambda: now

    @pytest.mark.parametrize(
        'lifetime', [timedelta(minutes=15), timedelta(hours=12)]
    )
    def test_default_refresh_windows(self, lifetime):
        expires_at = datetime.now(timezone.utc) + lifetime
        credentials = self.load(self.client(expires_at))
        assert type(credentials) is RefreshableCredentials
        assert credentials.method == 'credential-daemon'
        assert credentials._advisory_refresh_timeout == 15 * 60
        assert credentials._mandatory_refresh_timeout == 10 * 60

    def test_no_refresh_outside_the_advisory_window(self):
        client = self.client(datetime.now(timezone.utc) + timedelta(hours=1))
        credentials = self.load(client)
        for _ in range(5):
            credentials.get_frozen_credentials()
        assert client.get_credentials.call_count == 1

    def test_refresh_in_the_advisory_window(self):
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        client = self.client(expires_at)
        credentials = self.load(client)
        later = expires_at - timedelta(minutes=12)
        self.advance_to(credentials, later)
        client.get_credentials.return_value = self.result(
            later + timedelta(hours=1), access_key='AKID2'
        )
        assert credentials.get_frozen_credentials().access_key == 'AKID2'
        assert client.get_credentials.call_count == 2

    @pytest.mark.parametrize(
        'error',
        [
            CredentialDaemonReauthRequiredError(error_msg='ended'),
            CredentialDaemonNotRunningError(error_msg='not running'),
        ],
    )
    def test_failure_in_the_advisory_window_keeps_the_credentials(
        self, error, caplog
    ):
        # 12 minutes left: in the advisory window. botocore logs the failure
        # and keeps the credentials it has, REAUTH_REQUIRED included.
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        client = self.client(expires_at)
        credentials = self.load(client)
        self.advance_to(credentials, expires_at - timedelta(minutes=12))
        client.get_credentials.side_effect = error
        with caplog.at_level('WARNING', logger='botocore.credentials'):
            frozen = credentials.get_frozen_credentials()
        assert frozen.access_key == 'AKID'
        assert frozen.token == 'token'
        assert client.get_credentials.call_count == 2
        assert 'during advisory refresh period' in caplog.text

    @pytest.mark.parametrize(
        'error_class',
        [CredentialDaemonReauthRequiredError, CredentialDaemonNotRunningError],
    )
    def test_failure_in_the_mandatory_window_raises(self, error_class):
        # 5 minutes left: in the mandatory window.
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        client = self.client(expires_at)
        credentials = self.load(client)
        self.advance_to(credentials, expires_at - timedelta(minutes=5))
        client.get_credentials.side_effect = error_class(error_msg='no')
        with pytest.raises(error_class):
            credentials.get_frozen_credentials()

    def test_expired_credentials_on_the_first_fetch_are_returned(self):
        # Returned as received; the first use refreshes them, as for any
        # other provider's expired credentials.
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        client = self.client(expires_at)
        credentials = self.load(client)
        assert credentials._access_key == 'AKID'
        assert credentials._expiry_time == expires_at.replace(microsecond=0)
        assert client.get_credentials.call_count == 1
        with pytest.raises(RuntimeError, match='still expired'):
            credentials.get_frozen_credentials()
        assert client.get_credentials.call_count == 2

    def test_expired_credentials_on_a_refresh_raise(self):
        # botocore's existing check after a refresh.
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        client = self.client(expires_at)
        credentials = self.load(client)
        later = expires_at - timedelta(minutes=5)
        self.advance_to(credentials, later)
        client.get_credentials.return_value = self.result(
            later - timedelta(minutes=1)
        )
        with pytest.raises(RuntimeError, match='still expired'):
            credentials.get_frozen_credentials()


class TestCommands(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        self.fake = FakeCredentialDaemon().start()
        self.addCleanup(self.fake.stop)
        self.environ['AWS_CREDENTIAL_DAEMON_SOCKET'] = self.fake.socket_path
        with open(self.environ['AWS_CONFIG_FILE'], 'w') as f:
            f.write(textwrap.dedent(DEV_PROFILE))
        # The driver reads the config file when it's created.
        self.driver = create_clidriver()
        self.entry_point = AWSCLIEntryPoint(self.driver)

    def test_api_call(self):
        self.fake.seed('dev')
        self.parsed_response = {'Account': DEFAULT_ACCOUNT_ID}
        self.run_cmd('sts get-caller-identity --profile dev')
        self.assertEqual(credential_gets(self.fake), [{'credential': 'dev'}])

    def test_a_failed_daemon_call_is_not_retried(self):
        # The SEP: the SDK's request retry policies don't apply to the
        # daemon call, so a command whose credential/get fails makes one
        # call, even with more retry attempts configured.
        self.environ['AWS_MAX_ATTEMPTS'] = '5'
        self.environ['AWS_RETRY_MODE'] = 'standard'
        self.fake.seed('dev')
        self.fake.fail_next('credential/get', 'PROVIDER_UNAVAILABLE')
        self.run_cmd('sts get-caller-identity --profile dev', expected_rc=255)
        self.assertEqual(credential_gets(self.fake), [{'credential': 'dev'}])

    def test_debug_output_of_a_reply_that_isnt_json_has_no_secret(self):
        # The decode error holds the whole reply line, with its secrets.
        # --debug logs the error and its traceback, so nothing it chains to
        # can carry the line.
        self.fake.seed('dev')
        line = (
            b'{"jsonrpc":"2.0","id":1,"result":{"material":'
            b'{"type":"session_credentials","access_key_id":"ASIADEBUGKEYID",'
            b'"secret_access_key":"debugsecret","session_token":"debugtoken"'
            b'},"expires_at":"2099-01-01T00:00:00Z"}}x\n'
        )
        with mock.patch.object(_Connection, '_read_line', return_value=line):
            _, stderr, _ = self.run_cmd(
                'sts get-caller-identity --profile dev --debug',
                expected_rc=255,
            )
        self.assertIn('Calling the credential daemon credential/get', stderr)
        self.assertIn("isn't valid JSON", stderr)
        for secret in ('ASIADEBUGKEYID', 'debugsecret', 'debugtoken'):
            self.assertNotIn(secret, stderr)

    def test_api_call_after_logout(self):
        self.fake.seed('dev', status=NO_SESSION)
        _, stderr, _ = self.run_cmd(
            'sts get-caller-identity --profile dev', expected_rc=255
        )
        self.assertIn(
            "Session for profile 'dev' has ended. Run 'aws login --profile dev'.",
            stderr,
        )

    def test_export_credentials(self):
        self.fake.seed('dev')
        stdout, _, _ = self.run_cmd(
            'configure export-credentials --profile dev --format process'
        )
        output = json.loads(stdout)
        self.assertTrue(output['AccessKeyId'].startswith('ASIA'))
        self.assertTrue(output['SessionToken'])
        self.assertTrue(output['Expiration'])

    def assert_export_says_sign_in_again(self, advice):
        # Exit 255 with the sign-in advice, like API calls and an expired
        # aws login session in files, not the 253 configuration error.
        _, stderr, _ = self.run_cmd(
            'configure export-credentials --profile dev', expected_rc=255
        )
        self.assertIn(f'aws: [ERROR]: {advice}', stderr)
        self.assertNotIn('Unable to retrieve credentials', stderr)

    def test_export_credentials_after_the_session_ends(self):
        self.fake.seed('dev', status=NO_SESSION)
        self.assert_export_says_sign_in_again(
            "Session for profile 'dev' has ended. Run "
            "'aws login --profile dev'."
        )

    def test_export_credentials_after_the_sso_session_ends(self):
        self.fake.seed('dev', kind=KIND_SSO, principal=None, status=NO_SESSION)
        self.assert_export_says_sign_in_again(
            "Session for profile 'dev' has ended. Sign in again with the "
            "tool that stored credential 'dev', or remove credential_daemon "
            "from the profile and run 'aws sso login --profile dev'."
        )

    def test_export_credentials_with_keys_that_cant_be_used(self):
        self.fake.seed('dev', kind=KIND_IAM_USER, status=NO_SESSION)
        self.assert_export_says_sign_in_again(
            "The access keys for profile 'dev' can't be used. To use files "
            'for it, remove credential_daemon from the profile, then enter '
            "its keys with 'aws configure --profile dev'. Or store them in a "
            "new profile with 'aws configure --profile NEW-NAME'."
        )

    def test_export_credentials_with_the_daemon_not_running(self):
        # Not a sign-in-again error, so still export-credentials'
        # configuration error.
        self.fake.stop()
        _, stderr, _ = self.run_cmd(
            'configure export-credentials --profile dev', expected_rc=253
        )
        self.assertIn('Unable to retrieve credentials:', stderr)

    def test_configure_list(self):
        self.fake.seed('dev')
        stdout, _, _ = self.run_cmd('configure list --profile dev')
        self.assertIn('credential-daemon', stdout)

    @skip_if_windows('The link is for Linux and macOS.')
    def test_relative_daemon_socket_uses_the_link(self):
        # As the SEP says, a relative value counts as unset, so
        # ~/.aws/credential-daemon.sock is dialed. A short HOME keeps the
        # link under sun_path's limit.
        self.fake.seed('dev')
        home = tempfile.TemporaryDirectory(dir='/tmp', prefix='h')
        self.addCleanup(home.cleanup)
        link = Path(home.name, '.aws', 'credential-daemon.sock')
        link.parent.mkdir(mode=0o700)
        link.symlink_to(self.fake.socket_path)
        self.environ['HOME'] = home.name
        self.environ['AWS_CREDENTIAL_DAEMON_SOCKET'] = 'credsd.sock'
        self.parsed_response = {'Account': DEFAULT_ACCOUNT_ID}
        self.run_cmd('sts get-caller-identity --profile dev')
        self.assertEqual(credential_gets(self.fake), [{'credential': 'dev'}])
