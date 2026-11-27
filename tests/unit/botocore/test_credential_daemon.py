# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import contextlib
import hashlib
import os
import pathlib
import shutil
import socket
import stat
import struct
import sys
import tempfile

import botocore.credential_daemon
import botocore.session
import pytest
from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_CODE_REQUIREMENT,
    CREDENTIAL_DAEMON_PACKAGE_ID,
    CREDENTIAL_DAEMON_TEAM_ID,
    HOME_SOCKET_DIR_NAME,
    HOME_SOCKET_FILE_NAME,
    KEYS_TAG,
    LINUX_OWN_SOCKET_PATH,
    LOGIN_TAG,
    MACOS_OWN_SOCKET_PATH,
    OVERFLOW_UID,
    SSO_TAG,
    START_HINT,
    CredentialDaemonClient,
    CredentialRow,
    HomeSocketPath,
    LogoutResult,
    NoSocketPath,
    SocketChecks,
    Source,
    Status,
    check_code_signature,
    check_home_socket,
    check_peer,
    check_socket,
    check_socket_folders,
    credential_daemon_value,
    credential_names,
    credential_status,
    default_socket_path,
    find_credential_row,
    full_config_with_config_file_keys,
    get_credential_daemon_name,
    home_socket_path,
    is_logout_unsupported,
    is_valid_credential_name,
    own_socket_path,
    probe_socket,
    profiles_with_config_file_keys,
    socket_discovery_notes,
    socket_override,
    start_hint,
    system_socket_paths,
    tagged_credential_name,
)
from botocore.credential_daemon.codesign import _CodeSigning
from botocore.credential_daemon.transport import _Connection
from botocore.credential_daemon.trust import _peer_uid
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonTimeoutError,
    CredentialDaemonUntrustedSocketError,
    InvalidConfigError,
)

from awscli.compat import is_macos
from tests import mock
from tests.markers import skip_if_windows
from tests.utils.credential_daemon.skips import (
    skip_if_root,
    skip_unless_linux,
)


@pytest.mark.parametrize(
    'name',
    ['dev', 'Admin-123456789012', 'a.b_c-d', '-dev', 'dev.', 'a' * 64],
)
def test_valid_names(name):
    assert is_valid_credential_name(name)


@pytest.mark.parametrize(
    'name',
    ['', '.dev', 'me@corp', 'my profile', 'a' * 65, 'dev\n', 'ré', None, 1],
)
def test_invalid_names(name):
    assert not is_valid_credential_name(name)


def short_hash(name):
    return hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]


@pytest.mark.parametrize(
    'name, expected',
    [
        ('me@corp', 'me-corp'),
        ('my profile', 'my-profile'),
        ('ré', 'r-'),
        ('a/b:c', 'a-b-c'),
    ],
)
def test_disallowed_characters_become_dashes_with_a_hash(name, expected):
    tagged = LOGIN_TAG + name
    assert tagged_credential_name(LOGIN_TAG, name) == (
        f'{LOGIN_TAG}{expected}-{short_hash(tagged)}'
    )


@pytest.mark.parametrize(
    'first, second',
    [
        ('me@corp', 'me-corp'),
        ('me@corp', 'me/corp'),
        ('foo bar', 'foo:bar'),
        ('foo bar', 'foo-bar'),
    ],
)
def test_names_that_convert_the_same_stay_different(first, second):
    assert tagged_credential_name(LOGIN_TAG, first) != tagged_credential_name(
        LOGIN_TAG, second
    )


def test_long_names_with_disallowed_characters_are_cut_with_a_hash():
    tagged = LOGIN_TAG + 'me@corp ' * 10
    converted = tagged_credential_name(LOGIN_TAG, 'me@corp ' * 10)
    expected = (LOGIN_TAG + 'me-corp-' * 10)[:55]
    assert converted == f'{expected}-{short_hash(tagged)}'
    assert len(converted) == 64


def test_long_names_that_start_the_same_stay_different():
    assert tagged_credential_name(
        LOGIN_TAG, 'x' * 70 + 'a'
    ) != tagged_credential_name(LOGIN_TAG, 'x' * 70 + 'b')


@pytest.mark.parametrize(
    'name', ['me@corp', '.dev', 'a' * 65, '.' + 'é' * 80, 'x y' * 30]
)
def test_converted_names_are_valid(name):
    assert is_valid_credential_name(tagged_credential_name(LOGIN_TAG, name))


@pytest.mark.parametrize(
    'tag, name, expected',
    [
        (LOGIN_TAG, 'dev', 'login.dev'),
        (KEYS_TAG, 'ci', 'keys.ci'),
        (SSO_TAG, 'acme', 'sso.acme'),
        (LOGIN_TAG, 'Admin-111111111111', 'login.Admin-111111111111'),
        # A profile named like another type's tag keeps its own tag.
        (LOGIN_TAG, 'sso.acme', 'login.sso.acme'),
        (LOGIN_TAG, '.dev', 'login..dev'),
    ],
)
def test_tagged_names(tag, name, expected):
    assert tagged_credential_name(tag, name) == expected


@pytest.mark.parametrize('tag', [LOGIN_TAG, KEYS_TAG, SSO_TAG])
def test_tagged_names_are_cleaned_as_one_string(tag):
    name = tagged_credential_name(tag, 'me@corp')
    assert name == f'{tag}me-corp-{short_hash(tag + "me@corp")}'


@pytest.mark.parametrize('tag', [LOGIN_TAG, KEYS_TAG, SSO_TAG])
def test_long_tagged_names_are_cut_with_a_hash(tag):
    name = 'AdministratorAccess-' * 4
    tagged = tagged_credential_name(tag, name)
    assert tagged == f'{(tag + name)[:55]}-{short_hash(tag + name)}'
    assert len(tagged) == 64
    assert is_valid_credential_name(tagged)


@pytest.mark.parametrize('tag', [LOGIN_TAG, KEYS_TAG, SSO_TAG])
def test_tagged_name_at_the_limit_is_unchanged(tag):
    name = 'a' * (64 - len(tag))
    assert tagged_credential_name(tag, name) == tag + name


def test_same_name_under_different_tags_stays_different():
    names = {
        tagged_credential_name(tag, 'acme')
        for tag in (LOGIN_TAG, KEYS_TAG, SSO_TAG)
    }
    assert len(names) == 3


def test_empty_tagged_name_is_refused():
    with pytest.raises(ValueError):
        tagged_credential_name(LOGIN_TAG, '')


@pytest.mark.parametrize('name', [None, 1, b'dev'])
def test_non_string_tagged_name_is_refused(name):
    with pytest.raises(TypeError):
        tagged_credential_name(LOGIN_TAG, name)


@pytest.mark.parametrize(
    'status, signed_in, signed_out',
    [
        ('active', True, False),
        ('expiring', True, False),
        ('expired', False, False),
        ('sign_in_required', False, False),
        ('no_session', False, True),
        ('corrupt', False, False),
        ('unreadable', False, False),
        ('decrypt_failed', False, False),
        ('unknown', False, False),
        # creds list's spelling.
        ('no session', False, True),
        ('sign in required', False, False),
        # The CLI's old statuses aren't credsd's.
        ('signed_in', False, False),
        ('signed_out', False, False),
        (None, False, False),
        (1, False, False),
    ],
)
def test_credential_list_statuses(status, signed_in, signed_out):
    row = CredentialRow.from_wire({'credential': 'dev', 'status': status})
    assert row.signed_in is signed_in
    assert row.signed_out is signed_out


def test_credential_row_keeps_the_wire_values():
    item = {
        'credential': 'dev',
        'source': 'aws_login',
        'status': 'no session',
        'tags': {'created-by': 'aws-cli'},
    }
    row = CredentialRow.from_wire(item)
    assert row == CredentialRow(
        'dev', 'aws_login', 'no_session', {'created-by': 'aws-cli'}, item
    )
    assert row.source == Source.AWS_LOGIN
    assert row.status == Status.NO_SESSION


@pytest.mark.parametrize('item', ['dev', None, ['dev'], 1])
def test_credential_row_that_is_not_an_object(item):
    assert CredentialRow.from_wire(item) == CredentialRow(
        None, None, None, None, item
    )


def test_credential_row_name_is_not_checked():
    item = {'credential': ['dev'], 'source': 1}
    row = CredentialRow.from_wire(item)
    assert row.name == ['dev']
    assert row.source is None


def test_find_credential_row():
    rows = [
        CredentialRow.from_wire(item)
        for item in ('dev', {'source': 'aws_login'}, {'credential': 'dev'})
    ]
    assert find_credential_row(rows, 'dev') is rows[2]
    assert find_credential_row(rows, 'ci') is None
    # A row without a name matches None, as the dict lookup did, and a row
    # that isn't an object matches nothing.
    assert find_credential_row(rows[:1], None) is None
    assert find_credential_row(rows[1:2], None) is rows[1]


def test_credential_names():
    rows = [
        CredentialRow.from_wire(item)
        for item in (
            'dev',
            {'credential': 'a', 'status': 'active'},
            {'credential': 'b', 'status': 'no_session'},
            {'status': 'active'},
        )
    ]
    assert credential_names(rows) == {'a', 'b', None}
    assert credential_names(rows, signed_out=False) == {'a', None}


def test_status_spaces_read_as_underscores():
    assert credential_status({'status': 'decrypt failed'}) == 'decrypt_failed'
    assert credential_status({}) is None


class TestGetCredentialDaemonName:
    def test_profile_without_credential_daemon(self):
        assert (
            get_credential_daemon_name('dev', {'region': 'us-west-2'}) is None
        )

    def test_profile_with_credential_daemon(self):
        config = {'credential_daemon': 'dev', 'region': 'us-west-2'}
        assert get_credential_daemon_name('dev', config) == 'dev'

    def test_name_can_differ_from_the_profile(self):
        config = {'credential_daemon': 'dev'}
        assert get_credential_daemon_name('staging', config) == 'dev'

    def test_invalid_name(self):
        with pytest.raises(InvalidConfigError) as e:
            get_credential_daemon_name('dev', {'credential_daemon': 'me@corp'})
        assert 'me@corp' in str(e.value)
        assert '"dev"' in str(e.value)

    def test_role_arn_suggests_source_profile(self):
        config = {'credential_daemon': 'dev', 'role_arn': 'value'}
        with pytest.raises(InvalidConfigError) as e:
            get_credential_daemon_name('dev', config)
        assert str(e.value) == (
            'The profile "dev" contains both credential_daemon and role_arn. '
            'To assume a role with daemon credentials, set source_profile = '
            'dev in a separate profile.'
        )

    @pytest.mark.parametrize(
        'extra', [{}, {'role_arn': 'value'}], ids=['alone', 'with-role-arn']
    )
    def test_web_identity_token_file_is_a_second_source(self, extra):
        # SEP rule 2: two credential sources, so remove one. It's checked
        # before role_arn, and doesn't suggest source_profile.
        config = {
            'credential_daemon': 'dev',
            'web_identity_token_file': 'value',
            **extra,
        }
        with pytest.raises(InvalidConfigError) as e:
            get_credential_daemon_name('dev', config)
        assert str(e.value) == (
            'The profile "dev" has two credential sources, credential_daemon '
            'and web_identity_token_file. Remove one.'
        )
        assert 'source_profile' not in str(e.value)

    @pytest.mark.parametrize('key', ['role_arn', 'web_identity_token_file'])
    def test_second_source_errors_strip_control_characters(self, key):
        config = {'credential_daemon': 'dev', key: 'value'}
        with pytest.raises(InvalidConfigError) as e:
            get_credential_daemon_name('d\x1bev', config)
        assert '\x1b' not in str(e.value)
        assert '"dev"' in str(e.value)

    @pytest.mark.parametrize('key', ['role_arn', 'web_identity_token_file'])
    @pytest.mark.parametrize(
        'sso_keys',
        [{'sso_session': 'corp'}, {'sso_start_url': 'https://corp/start'}],
        ids=['sso-session', 'legacy-keys'],
    )
    def test_sso_profile_without_account_and_role_allows_them(
        self, key, sso_keys
    ):
        # The credential daemon isn't used for such a profile, so it may
        # set these keys (SEP rule 3).
        config = {'credential_daemon': 'corp', key: 'value', **sso_keys}
        assert get_credential_daemon_name('dev', config) == 'corp'

    @pytest.mark.parametrize('key', ['role_arn', 'web_identity_token_file'])
    @pytest.mark.parametrize(
        'role_keys',
        [
            {'sso_account_id': '111111111111', 'sso_role_name': 'Admin'},
            {'sso_account_id': '111111111111'},
            {'sso_role_name': 'Admin'},
        ],
        ids=['both-keys', 'account-only', 'role-only'],
    )
    def test_sso_profile_with_account_or_role_still_conflicts(
        self, key, role_keys
    ):
        config = {
            'credential_daemon': 'corp',
            'sso_session': 'corp',
            key: 'value',
            **role_keys,
        }
        with pytest.raises(InvalidConfigError) as e:
            get_credential_daemon_name('dev', config)
        assert key in str(e.value)

    @pytest.mark.parametrize(
        'key', ['credential_process', 'login_session', 'sso_session']
    )
    def test_keys_it_takes_precedence_over_are_allowed(self, key):
        config = {'credential_daemon': 'dev', key: 'value'}
        assert get_credential_daemon_name('dev', config) == 'dev'


class TestDefaultSocketPath:
    @pytest.fixture(autouse=True)
    def home(self, sock_dir, monkeypatch):
        # A short HOME of its own, so this machine's ~/.aws stays out of
        # the tests and the link path stays under sun_path's limit.
        home = sock_dir / 'home'
        (home / '.aws').mkdir(parents=True, mode=0o700)
        # HOME is read from the environ passed in; os.environ gets it too
        # for CredentialDaemonClient's own lookup.
        monkeypatch.setenv('HOME', str(home))
        self._home_dir = home
        return home

    def _env(self, **extra):
        return {'HOME': str(self._home_dir), **extra}

    def _link_path(self):
        return self._home_dir / '.aws' / 'credential-daemon.sock'

    @pytest.fixture(autouse=True)
    def sockets(self):
        sockets = []
        self._sockets = sockets
        yield sockets
        for sock in sockets:
            sock.close()

    def _make_socket(self, path):
        # A real socket. Bound by its relative name, so a long sock_dir
        # can't hit sun_path's limit.
        path.parent.mkdir(parents=True, exist_ok=True)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sockets.append(sock)
        cwd = os.getcwd()
        os.chdir(path.parent)
        try:
            sock.bind(path.name)
        finally:
            os.chdir(cwd)
        return str(path)

    def _make_link(self, sock_dir):
        target = self._make_socket(sock_dir / 'daemon' / 'd.sock')
        self._link_path().symlink_to(target)
        return str(self._link_path()), target

    def test_paths_are_the_seps(self):
        # SEP, Socket location.
        assert HOME_SOCKET_DIR_NAME == '.aws'
        assert HOME_SOCKET_FILE_NAME == 'credential-daemon.sock'
        assert LINUX_OWN_SOCKET_PATH == '/run/credsd/credsd.sock'
        assert MACOS_OWN_SOCKET_PATH == '/var/run/credsd/credsd.sock'

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_the_link_is_used(self, sock_dir, platform):
        link, _ = self._make_link(sock_dir)
        path = default_socket_path(environ=self._env(), platform=platform)
        assert path == link
        assert isinstance(path, HomeSocketPath)

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_a_socket_at_the_path_is_used(self, platform):
        # Not a link: a daemon can listen there itself.
        sock = self._make_socket(self._link_path())
        path = default_socket_path(environ=self._env(), platform=platform)
        assert path == sock
        assert isinstance(path, HomeSocketPath)

    @pytest.mark.parametrize(
        'leftover', ['dangling link', 'regular file', 'directory']
    )
    def test_anything_at_the_path_is_used(self, leftover):
        # Location 2 applies if anything is there; the connection then
        # reports what's wrong with it, and nothing else is tried.
        link = self._link_path()
        if leftover == 'dangling link':
            link.symlink_to(self._home_dir / 'missing.sock')
        elif leftover == 'regular file':
            link.touch()
        else:
            link.mkdir()
        path = default_socket_path(environ=self._env(), platform='linux')
        assert path == str(link)
        assert isinstance(path, HomeSocketPath)

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_nothing_there_is_no_socket(self, platform):
        path = default_socket_path(environ=self._env(), platform=platform)
        assert isinstance(path, NoSocketPath)
        assert path == str(self._link_path())

    @pytest.mark.skipif(
        hasattr(os, 'geteuid') and os.geteuid() == 0,
        reason='Root can search any folder.',
    )
    def test_an_aws_folder_the_cli_cant_search_isnt_no_socket(self):
        # A permissions problem isn't "nothing there": the connection's
        # check reports it.
        aws = self._link_path().parent
        aws.chmod(0o600)
        try:
            path = default_socket_path(environ=self._env(), platform='linux')
        finally:
            aws.chmod(0o700)
        assert isinstance(path, HomeSocketPath)

    def test_no_aws_folder_is_no_socket(self):
        self._link_path().parent.rmdir()
        path = default_socket_path(environ=self._env(), platform='linux')
        assert isinstance(path, NoSocketPath)

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_credsd_own_sockets_are_never_looked_at(
        self, sock_dir, monkeypatch, platform
    ):
        # Not its per-user socket, not its system socket, not the old
        # generic paths: only the variable and the link.
        for parts in (
            ('Library', 'Application Support', 'credsd', 'credsd.sock'),
            ('.local', 'share', 'credsd', 'credsd.sock'),
            ('.local', 'share', 'aws-credential-daemon', 'daemon.sock'),
            (
                'Library',
                'Application Support',
                'aws-credential-daemon',
                'daemon.sock',
            ),
        ):
            self._make_socket(self._home_dir.joinpath(*parts))
        environ = self._env(
            XDG_DATA_HOME=str(self._home_dir / '.local' / 'share')
        )
        path = default_socket_path(environ=environ, platform=platform)
        assert isinstance(path, NoSocketPath)

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    @pytest.mark.parametrize('home_value', [None, '', 'rel', 'rel/home'])
    def test_home_that_isnt_absolute_is_no_socket(
        self, sock_dir, monkeypatch, platform, home_value
    ):
        # Not resolved against the cwd, where another user could put a
        # link, and not from the passwd entry.
        cwd = sock_dir / 'cwd'
        (cwd / '.aws').mkdir(parents=True)
        self._make_socket(cwd / '.aws' / 'credential-daemon.sock')
        if home_value:
            (cwd / home_value / '.aws').mkdir(parents=True, exist_ok=True)
            self._make_socket(
                cwd / home_value / '.aws' / 'credential-daemon.sock'
            )
        monkeypatch.chdir(cwd)
        environ = {} if home_value is None else {'HOME': home_value}
        path = default_socket_path(environ=environ, platform=platform)
        assert isinstance(path, NoSocketPath)
        assert path == ''

    def test_home_unset_ignores_the_passwd_home(self, monkeypatch):
        monkeypatch.setattr(
            'os.path.expanduser',
            mock.Mock(side_effect=AssertionError('passwd home used')),
        )
        path = default_socket_path(environ={}, platform='linux')
        assert path == ''

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_daemon_socket_overrides(self, sock_dir, platform):
        # Even over a link, and with nothing listening there.
        self._make_link(sock_dir)
        environ = self._env(
            AWS_CREDENTIAL_DAEMON_SOCKET='/tmp/credsd-dev/credsd.sock'
        )
        path = default_socket_path(environ=environ, platform=platform)
        assert path == '/tmp/credsd-dev/credsd.sock'
        # A path from the variable isn't checked as the link is.
        assert not isinstance(path, HomeSocketPath)

    def test_daemon_socket_at_the_link_path_isnt_checked_as_the_link(self):
        environ = self._env(
            AWS_CREDENTIAL_DAEMON_SOCKET=str(self._link_path())
        )
        path = default_socket_path(environ=environ, platform='linux')
        assert not isinstance(path, (HomeSocketPath, NoSocketPath))

    @pytest.mark.parametrize('value', ['', 'credsd.sock', './credsd.sock'])
    def test_empty_or_relative_daemon_socket_counts_as_unset(
        self, sock_dir, value
    ):
        link, _ = self._make_link(sock_dir)
        environ = self._env(**{'AWS_CREDENTIAL_DAEMON_SOCKET': value})
        path = default_socket_path(environ=environ, platform='linux')
        assert path == link

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_relative_daemon_socket_with_no_link(self, platform):
        environ = self._env(**{'AWS_CREDENTIAL_DAEMON_SOCKET': 'credsd.sock'})
        path = default_socket_path(environ=environ, platform=platform)
        assert isinstance(path, NoSocketPath)

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_the_old_variable_is_ignored(self, platform):
        # SDKs and the CLI read only AWS_CREDENTIAL_DAEMON_SOCKET. The
        # old name is built so git grep for it stays clean.
        environ = self._env(
            **{'CREDSD' + '_SOCKET': '/tmp/credsd-dev/credsd.sock'}
        )
        path = default_socket_path(environ=environ, platform=platform)
        assert isinstance(path, NoSocketPath)

    def test_debug_names_the_link_and_its_target(self, sock_dir, caplog):
        link, target = self._make_link(sock_dir)
        with caplog.at_level('DEBUG', logger='botocore.credential_daemon'):
            default_socket_path(environ=self._env(), platform='linux')
        assert f"Using '{link}' -> '{os.path.realpath(target)}'" in (
            caplog.text
        )

    def test_debug_says_nothing_is_there(self, caplog):
        with caplog.at_level('DEBUG', logger='botocore.credential_daemon'):
            default_socket_path(environ=self._env(), platform='linux')
        assert f"Nothing is at '{self._link_path()}'" in caplog.text

    def test_debug_says_the_env_var_was_chosen(self, caplog):
        environ = self._env(AWS_CREDENTIAL_DAEMON_SOCKET='/tmp/x.sock')
        with caplog.at_level('DEBUG', logger='botocore.credential_daemon'):
            default_socket_path(environ=environ, platform='linux')
        assert (
            'from AWS_CREDENTIAL_DAEMON_SOCKET: '
            "'/tmp/x.sock'" in caplog.text
        )

    def test_debug_says_home_isnt_absolute(self, caplog):
        with caplog.at_level('DEBUG', logger='botocore.credential_daemon'):
            default_socket_path(environ={'HOME': 'rel'}, platform='linux')
        assert "HOME='rel' isn't an absolute path" in caplog.text

    def test_looked_up_again_on_each_call(self, sock_dir):
        # Nothing is cached: the link appears, then goes.
        assert isinstance(
            default_socket_path(environ=self._env(), platform='linux'),
            NoSocketPath,
        )
        link, _ = self._make_link(sock_dir)
        assert default_socket_path(environ=self._env(), platform='linux') == (
            link
        )
        os.unlink(link)
        assert isinstance(
            default_socket_path(environ=self._env(), platform='linux'),
            NoSocketPath,
        )

    def test_no_socket_is_never_dialed(self, monkeypatch):
        connect = mock.Mock()
        monkeypatch.setattr(socket.socket, 'connect', connect)
        path = default_socket_path(environ=self._env(), platform='linux')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert connect.call_args_list == []
        assert str(e.value) == (
            'The credential daemon isn\'t running: there\'s no socket at '
            f'{self._link_path()}. To use the credential daemon, install it '
            'with \'aws configure credential-daemon install\', link its '
            'socket with \'aws configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET.'
        )
        # The message says what to do; nothing is added.
        assert start_hint(e.value) == ''

    def test_no_home_is_never_dialed(self, monkeypatch):
        connect = mock.Mock()
        monkeypatch.setattr(socket.socket, 'connect', connect)
        path = default_socket_path(environ={}, platform='linux')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert connect.call_args_list == []
        assert str(e.value).startswith(
            'The credential daemon isn\'t running: HOME isn\'t an absolute '
            'path, so there\'s no ~/.aws/credential-daemon.sock to connect '
            'to. To use the credential daemon, install it'
        )
        assert 'AWS_CREDENTIAL_DAEMON_SOCKET' in str(e.value)

    def test_dangling_link_names_the_link_and_its_target(self, sock_dir):
        link = self._link_path()
        missing = sock_dir / 'gone' / 'missing-daemon.sock'
        link.symlink_to(missing)
        path = default_socket_path(environ=self._env(), platform='linux')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert str(e.value) == (
            f'The credential daemon isn\'t running: {link} points to '
            f'{missing}, which isn\'t there. {START_HINT} If you uninstalled '
            'it, remove the link with \'aws configure credential-daemon link '
            '--remove\'.'
        )
        assert start_hint(e.value) == ''

    def test_link_gone_after_the_lookup_is_not_running(self, sock_dir):
        link, _ = self._make_link(sock_dir)
        path = default_socket_path(environ=self._env(), platform='linux')
        os.unlink(link)
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert 'No such file or directory' in str(e.value)

    def test_link_to_a_stale_socket_mentions_link_remove(self, sock_dir):
        # On macOS the per-user socket file stays after an uninstall, so
        # the dial is refused rather than finding nothing.
        link, _ = self._make_link(sock_dir)
        for sock in self._sockets:
            sock.close()
        path = default_socket_path(environ=self._env(), platform='linux')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert str(e.value) == (
            f'The credential daemon isn\'t running: can\'t connect to {link}: '
            'Connection refused.'
        )
        assert start_hint(e.value) == (
            f'{START_HINT} If you uninstalled it, remove the link with '
            '\'aws configure credential-daemon link --remove\'.'
        )

    def test_a_stale_socket_at_the_path_gets_the_start_hint(self):
        # Not a link, so there's no link to remove.
        self._make_socket(self._link_path())
        for sock in self._sockets:
            sock.close()
        path = default_socket_path(environ=self._env(), platform='linux')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        assert start_hint(e.value) == START_HINT

    def test_other_failures_get_the_start_hint(self, sock_dir):
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(str(sock_dir / 'missing.sock'), 1)
        assert start_hint(e.value) == START_HINT


# The Linux and macOS paths are joined with os.path, so on Windows, where
# the credential daemon doesn't run, they'd have backslashes.
@skip_if_windows
@pytest.mark.parametrize(
    'platform, expected',
    [
        ('darwin', '/h/Library/Application Support/credsd/credsd.sock'),
        ('linux', '/run/credsd/credsd.sock'),
        ('win32', None),
    ],
)
def test_own_socket_path(platform, expected):
    assert own_socket_path({'HOME': '/h'}, platform) == expected


@skip_if_windows  # The Linux path, as above.
@pytest.mark.parametrize('home', [None, '', 'rel'])
def test_own_socket_path_needs_an_absolute_home_on_macos(home):
    environ = {} if home is None else {'HOME': home}
    assert own_socket_path(environ, 'darwin') is None
    # Linux's is the system socket, whatever HOME is.
    assert own_socket_path(environ, 'linux') == '/run/credsd/credsd.sock'


@pytest.mark.parametrize('home', [None, '', 'rel'])
def test_home_socket_path_needs_an_absolute_home(home):
    environ = {} if home is None else {'HOME': home}
    assert home_socket_path(environ) is None


@skip_if_windows  # As above.
def test_home_socket_path():
    assert home_socket_path({'HOME': '/h'}) == '/h/.aws/credential-daemon.sock'


class TestSocketOverride:
    # The one reader of AWS_CREDENTIAL_DAEMON_SOCKET.
    def test_unset(self):
        assert socket_override({}) is None

    def test_empty_counts_as_unset(self):
        assert socket_override({'AWS_CREDENTIAL_DAEMON_SOCKET': ''}) is None

    @pytest.mark.parametrize('value', ['/x/credsd.sock', 'credsd.sock'])
    def test_set_is_returned_as_is(self, value):
        environ = {'AWS_CREDENTIAL_DAEMON_SOCKET': value}
        assert socket_override(environ) == value

    def test_reads_os_environ_without_an_environ(self, monkeypatch):
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', '/x/credsd.sock')
        assert socket_override() == '/x/credsd.sock'
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET')
        assert socket_override() is None


class TestWindowsDaemonSocket:
    # The credential daemon doesn't run on Windows. The variable follows
    # the same absolute-path rule as elsewhere, and connecting fails.
    def test_no_socket_where_credential_daemon_does_not_run(self):
        assert default_socket_path(environ={}, platform='win32') is None

    @skip_if_windows
    def test_absolute_daemon_socket_is_used_as_elsewhere(self):
        environ = {'AWS_CREDENTIAL_DAEMON_SOCKET': '/x/credsd.sock'}
        with mock.patch('os.name', 'nt'):
            path = default_socket_path(environ=environ, platform='win32')
        assert path == '/x/credsd.sock'

    def test_relative_daemon_socket_counts_as_unset(self):
        environ = {'AWS_CREDENTIAL_DAEMON_SOCKET': 'credsd.sock'}
        with mock.patch('os.name', 'nt'):
            path = default_socket_path(environ=environ, platform='win32')
            notes = socket_discovery_notes(environ, 'win32')
        assert path is None
        assert notes == [
            'AWS_CREDENTIAL_DAEMON_SOCKET isn\'t an absolute path, so it was '
            'ignored: credsd.sock'
        ]

    @pytest.mark.parametrize('path', [None, '/x/credsd.sock'])
    def test_connecting_without_unix_sockets_fails(self, path):
        with mock.patch.object(
            botocore.credential_daemon.transport, 'socket'
        ) as sock:
            del sock.AF_UNIX
            with pytest.raises(CredentialDaemonConnectionError) as e:
                _Connection.open(path, 1)
        assert str(e.value) == (
            'The credential daemon isn\'t available on this platform.'
        )


@skip_if_windows
class TestSocketDiscoveryNotes:
    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_an_absolute_short_home_has_no_notes(self, platform):
        assert socket_discovery_notes({'HOME': '/h'}, platform) == []

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    @pytest.mark.parametrize('home', [None, '', 'rel'])
    def test_home_that_isnt_absolute(self, platform, home):
        environ = {} if home is None else {'HOME': home}
        assert socket_discovery_notes(environ, platform) == [
            'HOME isn\'t an absolute path, so ~/.aws/credential-daemon.sock '
            'was skipped.'
        ]

    def test_xdg_data_home_doesnt_count(self):
        # Discovery no longer looks under XDG_DATA_HOME.
        assert socket_discovery_notes({'XDG_DATA_HOME': '/d'}, 'linux') == [
            'HOME isn\'t an absolute path, so ~/.aws/credential-daemon.sock '
            'was skipped.'
        ]

    @pytest.mark.parametrize('platform', ['linux', 'darwin'])
    def test_a_path_too_long_to_dial(self, platform):
        notes = socket_discovery_notes({'HOME': '/' + 'h' * 100}, platform)
        assert len(notes) == 1
        assert 'over the limit of' in notes[0]
        assert notes[0].endswith(
            "so it can't be dialed: /"
            + 'h' * 100
            + '/.aws/credential-daemon.sock'
        )

    def test_an_absolute_override_has_no_notes(self):
        environ = {'AWS_CREDENTIAL_DAEMON_SOCKET': '/s.sock'}
        assert socket_discovery_notes(environ, 'linux') == []

    def test_a_relative_override_is_named(self):
        environ = {'AWS_CREDENTIAL_DAEMON_SOCKET': 's\x1b.sock', 'HOME': '/h'}
        assert socket_discovery_notes(environ, 'linux') == [
            'AWS_CREDENTIAL_DAEMON_SOCKET isn\'t an absolute path, so it '
            'was ignored: s.sock'
        ]

    def test_other_platforms_have_no_notes(self):
        assert socket_discovery_notes({}, 'win32') == []


@skip_if_windows
class TestConnectionErrorsStripThePath:
    # The path comes from the customer's environment; its control
    # characters never reach the terminal.
    BAD = '\x1b[31m\x07\u202e'

    def _assert_clean(self, error):
        for character in '\x1b\x07\u202e':
            assert character not in str(error)

    def test_nothing_listening(self, sock_dir):
        path = str(sock_dir / f'a{self.BAD}b.sock')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        self._assert_clean(e.value)
        assert 'a[31mb.sock' in str(e.value)

    def test_path_too_long(self, tmp_path):
        path = str(tmp_path / (self.BAD + 'x' * 200))
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(path, 1)
        self._assert_clean(e.value)
        assert 'too long' in str(e.value)

    def _no_socket_file_to_check(self, path):
        # Only the connect is mocked, so there's no socket file to check.
        return mock.patch(
            f'{CD}.transport.check_socket', return_value=(path, os.geteuid())
        )

    def test_timeout(self, sock_dir):
        path = str(sock_dir / f'a{self.BAD}b.sock')
        with (
            mock.patch.object(
                socket.socket, 'connect', side_effect=socket.timeout
            ),
            self._no_socket_file_to_check(path),
        ):
            with pytest.raises(CredentialDaemonTimeoutError) as e:
                _Connection.open(path, 1)
        self._assert_clean(e.value)

    def test_other_os_error(self, sock_dir):
        path = str(sock_dir / f'a{self.BAD}b.sock')
        with (
            mock.patch.object(
                socket.socket,
                'connect',
                side_effect=PermissionError(13, f'denied{self.BAD}'),
            ),
            self._no_socket_file_to_check(path),
        ):
            with pytest.raises(CredentialDaemonConnectionError) as e:
                _Connection.open(path, 1)
        self._assert_clean(e.value)
        assert 'denied' in str(e.value)


# credential_daemon and credential_storage are read from the config file
# alone, never from the shared credentials file.
def config_file_session(tmp_path, config, credentials=None):
    config_file = tmp_path / 'config'
    config_file.write_text(config)
    credentials_file = tmp_path / 'credentials'
    if credentials is not None:
        credentials_file.write_text(credentials)
    session = botocore.session.Session()
    session.set_config_variable('config_file', str(config_file))
    session.set_config_variable('credentials_file', str(credentials_file))
    return session


@pytest.mark.parametrize(
    'key, config_value, credentials_value',
    [
        ('credential_storage', 'daemon', 'file'),
        ('credential_daemon', 'login.dev', 'keys.dev'),
    ],
)
def test_the_config_file_wins_over_the_credentials_file(
    tmp_path, key, config_value, credentials_value
):
    session = config_file_session(
        tmp_path,
        f'[profile dev]\n{key} = {config_value}\n',
        f'[dev]\n{key} = {credentials_value}\n',
    )
    # full_config lets the credentials file win.
    assert session.full_config['profiles']['dev'][key] == credentials_value
    assert profiles_with_config_file_keys(session)['dev'][key] == config_value


@pytest.mark.parametrize('key', ['credential_storage', 'credential_daemon'])
def test_a_key_only_in_the_credentials_file_is_ignored(tmp_path, key):
    session = config_file_session(
        tmp_path,
        '[profile dev]\nregion = us-west-2\n',
        f'[dev]\n{key} = daemon\naws_access_key_id = AKIDEXAMPLE\n',
    )
    profile = profiles_with_config_file_keys(session)['dev']
    assert key not in profile
    # The credentials file's other keys are still merged.
    assert profile['aws_access_key_id'] == 'AKIDEXAMPLE'
    assert profile['region'] == 'us-west-2'


def test_a_profile_only_in_the_credentials_file(tmp_path):
    session = config_file_session(
        tmp_path, '', '[ci]\ncredential_daemon = keys.ci\nregion = eu-west-1\n'
    )
    assert profiles_with_config_file_keys(session)['ci'] == {
        'region': 'eu-west-1'
    }


def test_the_session_config_is_not_changed(tmp_path):
    session = config_file_session(
        tmp_path,
        '[profile dev]\ncredential_storage = daemon\n',
        '[dev]\ncredential_storage = file\n',
    )
    full_config_with_config_file_keys(session)
    assert session.full_config['profiles']['dev']['credential_storage'] == (
        'file'
    )


def test_no_credentials_file(tmp_path):
    session = config_file_session(
        tmp_path, '[profile dev]\ncredential_daemon = a\n'
    )
    assert full_config_with_config_file_keys(session) is session.full_config


class TestDaemonCredentialValue:
    def test_no_value(self):
        assert credential_daemon_value('dev', {}) is None

    def test_valid_name(self):
        config = {'credential_daemon': 'login.dev'}
        assert credential_daemon_value('dev', config) == 'login.dev'

    def test_invalid_name(self):
        config = {'credential_daemon': 'not valid'}
        with pytest.raises(InvalidConfigError, match='"not valid"'):
            credential_daemon_value('dev', config)

    @pytest.mark.parametrize(
        'config',
        [{'credential_daemon': 'a\x1bb'}, {'credential_daemon': {'x': 'y'}}],
        ids=['invalid', 'indented'],
    )
    def test_control_characters_are_stripped_from_the_error(self, config):
        # Config values, so an escape sequence in them can't rewrite what
        # the terminal shows.
        with pytest.raises(InvalidConfigError) as e:
            credential_daemon_value('d\x1bev', config)
        assert '\x1b' not in str(e.value)
        assert '"dev"' in str(e.value)

    def test_indented_value_is_a_config_error(self, tmp_path):
        # The config parser reads an indented line after the key as a
        # dict.
        session = config_file_session(
            tmp_path, '[profile dev]\ncredential_daemon =\n  foo = bar\n'
        )
        config = session.full_config['profiles']['dev']
        assert config['credential_daemon'] == {'foo': 'bar'}
        with pytest.raises(InvalidConfigError, match='not a single value'):
            credential_daemon_value('dev', config)
        with pytest.raises(InvalidConfigError, match='not a single value'):
            get_credential_daemon_name('dev', config)


class TestLogoutResult:
    @pytest.mark.parametrize(
        'provider', ['ended', 'token_rejected', 'local_only']
    )
    def test_signed_out(self, provider):
        result = LogoutResult.from_reply(
            {'signed_out': True, 'provider': provider}
        )
        assert result == LogoutResult(True, provider)
        assert not result.provider_failed

    def test_no_session(self):
        result = LogoutResult.from_reply(
            {'signed_out': False, 'provider': 'none'}
        )
        assert result == LogoutResult(False, 'none')

    def test_failed(self):
        result = LogoutResult.from_reply(
            {
                'signed_out': True,
                'provider': 'failed',
                'start_url': 'https://acme.awsapps.com/start',
                'access_token_expires_at': '2026-11-19T18:00:00Z',
            }
        )
        assert result.provider_failed
        assert result.start_url == 'https://acme.awsapps.com/start'
        assert result.access_token_expires_at == '2026-11-19T18:00:00Z'

    def test_start_url_is_read_only_for_failed(self):
        result = LogoutResult.from_reply(
            {
                'signed_out': True,
                'provider': 'ended',
                'start_url': 'https://acme.awsapps.com/start',
            }
        )
        assert result.start_url is None

    @pytest.mark.parametrize(
        'reply',
        [
            {},
            {'provider': 'local_only'},
            {'signed_out': None},
            {'signed_out': 'false'},
            {'signed_out': 'true'},
            {'signed_out': 0},
            {'signed_out': 1},
            None,
            [],
        ],
    )
    def test_signed_out_must_be_true_or_false(self, reply):
        # credsd always sends it as a bool; anything else is a reply the
        # CLI can't read, never a sign-out.
        with pytest.raises(CredentialDaemonProtocolError):
            LogoutResult.from_reply(reply)

    @pytest.mark.parametrize('value', [1, '', ['x'], {'a': 'b'}])
    def test_fields_that_arent_strings_are_dropped(self, value):
        result = LogoutResult.from_reply(
            {
                'signed_out': True,
                'provider': 'failed',
                'start_url': value,
                'access_token_expires_at': value,
            }
        )
        assert result.provider_failed
        assert result.start_url is None
        assert result.access_token_expires_at is None


@pytest.mark.parametrize(
    'code, unsupported',
    [
        ('LOGOUT_UNSUPPORTED_SOURCE', True),
        ('CREDENTIAL_NOT_FOUND', False),
        # Invalid params: a bad request, not a source with no sign-in.
        (-32602, False),
        (None, False),
    ],
)
def test_is_logout_unsupported(code, unsupported):
    error = CredentialDaemonRequestRejectedError(error_msg='x', code=code)
    assert is_logout_unsupported(error) is unsupported


def test_is_logout_unsupported_needs_a_daemon_error():
    assert not is_logout_unsupported(ValueError('LOGOUT_UNSUPPORTED_SOURCE'))
    assert is_logout_unsupported(
        CredentialDaemonError(error_msg='x', code='LOGOUT_UNSUPPORTED_SOURCE')
    )


# The checks every connection makes before anything is sent on it
# (SocketChecks).

CD = 'botocore.credential_daemon'
OTHER_UID = 4242


def listen(path):
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(4)
    server.setblocking(False)
    return server


def linux_system_rule():
    # The Linux rule at a system socket: its folder may be the socket
    # owner's, so a socket the test owns passes on any platform.
    # TestMacosSystemSocketOwner and TestMacosSystemSocketPeer have the
    # macOS rule.
    return mock.patch(
        f'{CD}.trust._system_socket_root_only', return_value=False
    )


def macos_system_rule():
    # The macOS rule at a system socket: root must own it and its folder,
    # and serve it.
    return mock.patch(
        f'{CD}.trust._system_socket_root_only', return_value=True
    )


def assert_never_connected(server):
    # The checks run before connect, so nothing reached the listener.
    with pytest.raises(BlockingIOError):
        server.accept()


def foreign_uid():
    return os.geteuid() + OTHER_UID


@skip_if_windows
class TestSocketPathCheck:
    def test_own_socket_in_a_private_folder_passes(self, private_dir):
        path = private_dir / 'd.sock'
        with listen(path):
            canon, owner = check_socket(str(path))
        assert canon == str(path)
        assert owner == os.geteuid()

    @pytest.mark.parametrize('mode', [0o777, 0o770, 0o757])
    def test_socket_in_a_folder_others_can_write_is_refused(
        self, private_dir, mode
    ):
        loose = private_dir / 'pub'
        loose.mkdir()
        path = loose / 'd.sock'
        with listen(path) as server:
            loose.chmod(mode)
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
            assert_never_connected(server)
        assert e.value.code == 'UNTRUSTED_SOCKET'
        assert str(e.value) == (
            f'The CLI didn\'t trust the credential daemon socket {path}, so '
            f'it sent nothing to it: the folder {loose} is writable by other '
            f'users (mode {mode:04o}). Run \'chmod go-w {loose}\', or move '
            'the socket to a folder only you can write to.'
        )

    def test_sticky_folder_like_tmp_passes(self, private_dir):
        sticky = private_dir / 'sticky'
        sticky.mkdir()
        path = sticky / 'd.sock'
        with listen(path):
            sticky.chmod(0o1777)
            assert check_socket(str(path))[0] == str(path)

    def test_symlink_into_a_loose_folder_is_refused(self, private_dir):
        loose = private_dir / 'pub'
        loose.mkdir()
        target = loose / 'd.sock'
        link = private_dir / 'link.sock'
        link.symlink_to(target)
        with listen(target) as server:
            loose.chmod(0o777)
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(link)
                ).list_credentials()
            assert_never_connected(server)
        assert f'the folder {loose} is writable by other users' in str(e.value)

    def test_symlink_to_a_good_socket_dials_the_target(self, private_dir):
        good = private_dir / 'good'
        good.mkdir(mode=0o700)
        target = good / 'd.sock'
        link = private_dir / 'link.sock'
        link.symlink_to(target)
        with listen(target):
            assert check_socket(str(link))[0] == str(target)

    @skip_if_root('Root is trusted as the owner of any socket or folder.')
    def test_folder_another_user_owns_is_refused(self, private_dir):
        path = private_dir / 'd.sock'
        with listen(path) as server:
            with mock.patch('os.geteuid', return_value=foreign_uid()):
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    CredentialDaemonClient(
                        socket_path=str(path)
                    ).list_credentials()
            assert_never_connected(server)
        assert 'is owned by uid' in str(e.value)
        assert 'not by you or root' in str(e.value)

    def test_missing_socket_is_not_running(self, private_dir):
        path = private_dir / 'missing.sock'
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            check_socket(str(path))
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{path}: No such file or directory.'
        )

    def test_null_byte_in_path_is_not_running(self):
        # os.path.realpath raises ValueError for it.
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            check_socket('/run/a\0b.sock')
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        # "byte" before Python 3.12, "character" from 3.12 on.
        assert 'embedded null' in str(e.value)

    def test_path_that_cant_be_resolved_is_not_running(self):
        # A relative path with a deleted working folder, for example.
        error = FileNotFoundError(2, 'No such file or directory')
        with mock.patch('os.path.realpath', side_effect=error):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                check_socket('d.sock')
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        assert str(e.value).endswith('No such file or directory.')

    @pytest.mark.parametrize('system', [False, True])
    def test_folder_the_cli_cant_stat_is_refused(self, private_dir, system):
        # No search permission on a parent: the folder can't be checked.
        folder = private_dir / 'credsd'
        folder.mkdir(mode=0o700)
        path = folder / 'd.sock'
        real_lstat = os.lstat

        def lstat(p, *args, **kwargs):
            if p == str(folder):
                raise PermissionError(13, 'Permission denied', p)
            return real_lstat(p, *args, **kwargs)

        system_paths = {str(path)} if system else frozenset()
        with (
            listen(path) as server,
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value=system_paths
            ),
            linux_system_rule(),
            mock.patch('os.lstat', side_effect=lstat),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
            assert_never_connected(server)
        assert str(e.value).endswith(
            f'the CLI can\'t check the folder {folder}: Permission denied.'
        )

    @pytest.mark.parametrize('system', [False, True])
    def test_folder_gone_after_the_socket_check_is_not_running(
        self, private_dir, system
    ):
        folder = private_dir / 'credsd'
        folder.mkdir(mode=0o700)
        path = folder / 'd.sock'
        real_lstat = os.lstat

        def lstat(p, *args, **kwargs):
            if p == str(folder):
                raise FileNotFoundError(2, 'No such file or directory', p)
            return real_lstat(p, *args, **kwargs)

        system_paths = {str(path)} if system else frozenset()
        with (
            listen(path),
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value=system_paths
            ),
            linux_system_rule(),
            mock.patch('os.lstat', side_effect=lstat),
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                check_socket(str(path))
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{path}: No such file or directory.'
        )

    def test_regular_file_is_not_running(self, private_dir):
        path = private_dir / 'file.sock'
        path.touch()
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            check_socket(str(path))
        assert str(e.value).endswith(': it isn\'t a socket.')

    def test_overflow_uid_caller_is_refused(self, private_dir):
        # In a user namespace that doesn't map it, every unmapped owner
        # looks like the caller.
        path = private_dir / 'd.sock'
        with listen(path) as server:
            with mock.patch('os.geteuid', return_value=65534):
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    CredentialDaemonClient(
                        socket_path=str(path)
                    ).list_credentials()
            assert_never_connected(server)
        assert 'running as uid 65534' in str(e.value)

    def test_other_platforms_are_refused(self, private_dir):
        path = private_dir / 'd.sock'
        with listen(path), mock.patch('sys.platform', 'freebsd14'):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert 'can\'t check it on this platform' in str(e.value)

    @pytest.mark.parametrize(
        'patch',
        [
            lambda: mock.patch('os.geteuid', return_value=65534),
            lambda: mock.patch('sys.platform', 'freebsd14'),
        ],
    )
    def test_no_socket_is_not_running_for_any_caller(self, private_dir, patch):
        # A machine without the credential daemon gets the not-running
        # error, even as uid 65534 or on another platform.
        path = private_dir / 'd.sock'
        with patch(), pytest.raises(CredentialDaemonNotRunningError) as e:
            check_socket(str(path))
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)

    def test_system_socket_owned_by_the_overflow_uid_is_refused(
        self, private_dir
    ):
        # check_peer refuses it too; the path check doesn't pass it.
        path = private_dir / 'd.sock'
        real_lstat = os.lstat

        def lstat(p, *args, **kwargs):
            st = real_lstat(p, *args, **kwargs)
            if p == str(path):
                fields = list(st)
                fields[stat.ST_UID] = 65534
                return os.stat_result(fields)
            return st

        with (
            listen(path),
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            mock.patch('os.lstat', side_effect=lstat),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert 'the socket is owned by uid 65534' in str(e.value)

    def test_control_characters_are_stripped_from_the_message(
        self, private_dir
    ):
        loose = private_dir / 'p\x1b[2K'
        loose.mkdir()
        path = loose / 'd.sock'
        with listen(path):
            loose.chmod(0o777)
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert '\x1b' not in str(e.value)
        assert 'p[2K' in str(e.value)

    @pytest.mark.parametrize('checks', list(SocketChecks))
    def test_every_level_refuses_a_loose_folder(self, private_dir, checks):
        # The credential provider's credential/get (PEER) checks the
        # folders too.
        loose = private_dir / 'pub'
        loose.mkdir()
        path = loose / 'd.sock'
        with listen(path) as server:
            loose.chmod(0o777)
            with mock.patch.object(_Connection, 'call') as call:
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    CredentialDaemonClient(
                        socket_path=str(path), checks=checks
                    ).get_credentials('dev')
            assert f'the folder {loose} is writable' in str(e.value)
            assert e.value.code == 'UNTRUSTED_SOCKET'
            call.assert_not_called()
            assert_never_connected(server)

    def test_checks_cant_be_turned_off(self):
        for off in (False, None, 'none'):
            with pytest.raises(ValueError):
                CredentialDaemonClient(checks=off)
            with pytest.raises(ValueError):
                _Connection.open('/x', 1, checks=off)


@skip_if_windows
class TestHomeSocketCheck:
    """~/.aws/credential-daemon.sock gets no owner or mode checks before
    it's dialed (SEP Socket location): ~/.aws has the same trust as the
    config file next to it. Only a link whose target is missing is caught
    first. Every call checks the daemon behind the link."""

    @pytest.fixture
    def home(self, private_dir, monkeypatch):
        home = private_dir / 'h'
        (home / '.aws').mkdir(parents=True, mode=0o700)
        monkeypatch.setenv('HOME', str(home))
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        return home

    @pytest.fixture
    def target(self, private_dir):
        folder = private_dir / 't'
        folder.mkdir(mode=0o700)
        path = folder / 'd.sock'
        with listen(path) as server:
            yield path, server

    def _link(self, home, target):
        link = home / '.aws' / 'credential-daemon.sock'
        link.symlink_to(target)
        return link

    def _found(self):
        path = default_socket_path()
        assert isinstance(path, HomeSocketPath)
        return path

    def _assert_dialed(self, server):
        server.setblocking(True)
        try:
            server.accept()[0].close()
        finally:
            server.setblocking(False)

    @pytest.mark.parametrize('checks', list(SocketChecks))
    def test_own_link_in_a_private_folder_passes(self, home, target, checks):
        path, server = target
        self._link(home, path)
        _Connection.open(self._found(), 1, checks=checks).close()
        self._assert_dialed(server)

    @pytest.mark.parametrize('checks', list(SocketChecks))
    @pytest.mark.parametrize('mode', [0o775, 0o777, 0o1777])
    def test_a_link_in_an_aws_folder_others_can_write_is_dialed(
        self, home, target, checks, mode
    ):
        # Whoever can write ~/.aws can already change the config file next
        # to it, so the folder isn't checked. Every level checks the
        # folders of the resolved target instead, which this isn't on.
        path, server = target
        self._link(home, path)
        (home / '.aws').chmod(mode)
        try:
            _Connection.open(self._found(), 1, checks=checks).close()
        finally:
            (home / '.aws').chmod(0o700)
        self._assert_dialed(server)
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o700

    @pytest.mark.parametrize('checks', list(SocketChecks))
    @pytest.mark.parametrize('which', ['folder', 'link'])
    def test_an_aws_folder_or_link_another_user_owns_is_dialed(
        self, home, target, checks, which
    ):
        path, server = target
        link = str(self._link(home, path))
        aws = str(home / '.aws')
        real_stat, real_lstat = os.stat, os.lstat

        def stat_(p, *args, **kwargs):
            st = real_stat(p, *args, **kwargs)
            if which == 'folder' and str(p) == aws:
                return _with_uid(st, foreign_uid())
            return st

        def lstat_(p, *args, **kwargs):
            st = real_lstat(p, *args, **kwargs)
            if str(p) == (aws if which == 'folder' else link):
                return _with_uid(st, foreign_uid())
            return st

        with (
            mock.patch('botocore.credential_daemon.trust.os.stat', stat_),
            mock.patch('botocore.credential_daemon.trust.os.lstat', lstat_),
        ):
            _Connection.open(self._found(), 1, checks=checks).close()
        self._assert_dialed(server)

    @pytest.mark.parametrize('checks', list(SocketChecks))
    def test_every_level_refuses_the_overflow_uid(self, home, target, checks):
        # check_socket refuses it: in a user namespace, every unmapped
        # owner looks like the caller.
        path, server = target
        self._link(home, path)
        with mock.patch(
            'botocore.credential_daemon.host.os.geteuid',
            return_value=OVERFLOW_UID,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                _Connection.open(self._found(), 1, checks=checks)
        assert str(e.value) == (
            'The CLI didn\'t trust the credential daemon socket '
            f'{home}/.aws/credential-daemon.sock ({path}), so it sent nothing '
            'to it: the CLI is running as uid 65534, which a user namespace '
            'also shows for users it doesn\'t map, so it can\'t tell who '
            'owns the socket.'
        )
        assert_never_connected(server)

    @pytest.mark.parametrize(
        'geteuid',
        [
            mock.Mock(side_effect=OSError(38, 'Function not implemented')),
            mock.Mock(return_value=None),
            mock.Mock(return_value=-1),
        ],
    )
    @pytest.mark.parametrize('checks', list(SocketChecks))
    def test_no_effective_uid_is_an_unsupported_platform(
        self, home, target, geteuid, checks
    ):
        # A can't-happen on Linux and macOS: the daemon checks are never
        # skipped, at any level.
        path, server = target
        self._link(home, path)
        with mock.patch('botocore.credential_daemon.host.os.geteuid', geteuid):
            with pytest.raises(CredentialDaemonConnectionError) as e:
                _Connection.open(self._found(), 1, checks=checks)
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        assert not isinstance(e.value, CredentialDaemonNotRunningError)
        assert str(e.value) == (
            'The credential daemon isn\'t available on this platform: the '
            'CLI can\'t get its effective user, so the CLI can\'t check its '
            'socket. Nothing was sent to it.'
        )
        assert_never_connected(server)

    def test_no_geteuid_at_all_is_an_unsupported_platform(self, home, target):
        path, server = target
        self._link(home, path)
        with mock.patch.object(
            botocore.credential_daemon.host, 'os', _WithoutGeteuid()
        ):
            with pytest.raises(
                CredentialDaemonConnectionError,
                match='can\'t get its effective user',
            ):
                _Connection.open(self._found(), 1, checks=SocketChecks.FULL)
        assert_never_connected(server)

    def test_a_linked_aws_folder_is_followed(self, home, target, private_dir):
        path, server = target
        real = private_dir / 'real-aws'
        real.mkdir(mode=0o770)
        (home / '.aws').rmdir()
        (home / '.aws').symlink_to(real)
        self._link(home, path)
        _Connection.open(self._found(), 1, checks=SocketChecks.PEER).close()
        self._assert_dialed(server)

    @pytest.mark.parametrize('mode', [0o700, 0o770])
    def test_dangling_link_is_not_running(self, home, mode):
        link = self._link(home, home / 'missing.sock')
        (home / '.aws').chmod(mode)
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(self._found(), 1)
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)
        assert f'{link} points to {home}/missing.sock' in str(e.value)

    def test_aws_folder_gone_is_not_running(self, home, target):
        path, _ = target
        link = self._link(home, path)
        found = self._found()
        link.unlink()
        (home / '.aws').rmdir()
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            _Connection.open(found, 1)
        assert not isinstance(e.value, CredentialDaemonUntrustedSocketError)

    @pytest.mark.parametrize('checks', list(SocketChecks))
    def test_every_level_walks_the_targets_folders(
        self, home, private_dir, checks
    ):
        # The folders of what the link points at are checked, for the
        # credential provider's credential/get too.
        loose = private_dir / 'pub'
        loose.mkdir()
        path = loose / 'd.sock'
        with listen(path) as server:
            loose.chmod(0o777)
            self._link(home, path)
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                _Connection.open(self._found(), 1, checks=checks)
            assert f'the folder {loose} is writable' in str(e.value)
            assert_never_connected(server)

    def test_debug_says_the_checks_passed(self, home, target, caplog):
        path, _ = target
        link = self._link(home, path)
        with caplog.at_level('DEBUG', logger='botocore.credential_daemon'):
            _Connection.open(
                self._found(), 1, checks=SocketChecks.FULL
            ).close()
        assert f"Using '{link}' -> '{path}'" in caplog.text
        assert 'it and its folder are yours' not in caplog.text
        assert f"Checked '{path}': its folders, its owner and the user " in (
            caplog.text
        )

    def test_a_long_target_names_the_target(self, home, private_dir):
        # The link is short, but every level dials its resolved
        # target, which is too long.
        deep = private_dir.joinpath(*['d' * 30] * 4)
        deep.mkdir(parents=True, mode=0o700)
        target = deep / 'd.sock'
        # Only there for the dangling-link check; check_socket is faked.
        target.touch()
        link = self._link(home, target)
        with mock.patch(
            'botocore.credential_daemon.transport.check_socket',
            return_value=(str(target), os.geteuid()),
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                _Connection.open(self._found(), 1, checks=SocketChecks.FULL)
        assert str(e.value) == (
            'The credential daemon isn\'t running: the socket path '
            f'{target}, where {link} points, is too long.'
        )

    @skip_if_root('Root can search any folder.')
    def test_an_aws_folder_the_cli_cant_search_is_not_running(
        self, home, target
    ):
        path, server = target
        link = self._link(home, path)
        aws = home / '.aws'
        aws.chmod(0o600)
        try:
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                _Connection.open(self._found(), 1)
        finally:
            aws.chmod(0o700)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{link}: Permission denied.'
        )
        assert_never_connected(server)


@skip_if_windows
class TestCheckSocketFolders:
    """The folders on the way to a socket that doesn't answer yet, as
    check_socket step 3 checks them."""

    def test_private_folders_pass(self, private_dir):
        folder = private_dir / 'own'
        folder.mkdir(mode=0o700)
        check_socket_folders(str(folder / 'd.sock'))

    def test_a_folder_others_can_write_is_refused(self, private_dir):
        loose = private_dir / 'pub'
        loose.mkdir()
        loose.chmod(0o777)
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_socket_folders(str(loose / 'd.sock'))
        assert (
            f'the folder {loose} is writable by other users (mode 0777)'
            in (str(e.value))
        )

    def test_a_sticky_folder_passes(self, private_dir):
        sticky = private_dir / 'tmp'
        sticky.mkdir()
        sticky.chmod(0o1777)
        check_socket_folders(str(sticky / 'd.sock'))

    def test_the_path_is_resolved_first(self, private_dir):
        loose = private_dir / 'pub'
        loose.mkdir()
        loose.chmod(0o777)
        link = private_dir / 'via'
        link.symlink_to(loose)
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_socket_folders(str(link / 'd.sock'))
        # The socket as given, then resolved; the folder resolved, since
        # that's where the chmod goes.
        assert f'socket {link}/d.sock ({loose}/d.sock)' in str(e.value)
        assert str(e.value).endswith(
            f': the folder {loose} is writable by other users (mode 0777). '
            f'Run \'chmod go-w {loose}\', or move the socket to a folder '
            'only you can write to.'
        )

    def _loose_folder_error(self, private_dir, euid, owner=0):
        # A 0777 folder owner owns, inside private_dir owned by euid, checked
        # by a caller whose effective uid is euid. All are faked, so the
        # result doesn't depend on who runs the tests: CI runs them as root.
        loose = private_dir / 'mnt'
        loose.mkdir()
        loose.chmod(0o777)
        with (
            _owned_by({str(private_dir): euid, str(loose): owner}),
            mock.patch(
                'botocore.credential_daemon.host.os.geteuid',
                return_value=euid,
            ),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket_folders(str(loose / 'd.sock'))
        return loose, str(e.value)

    def test_a_loose_folder_root_owns_says_as_root(self, private_dir):
        # Only root can chmod it, such as a 0777 bind mount.
        loose, message = self._loose_folder_error(private_dir, OTHER_UID)
        assert message.endswith(
            f'. Run \'chmod go-w {loose}\' as root, or move the socket to a '
            'folder only you can write to.'
        )

    def test_a_loose_folder_root_owns_doesnt_say_as_root_to_root(
        self, private_dir
    ):
        # Root runs the chmod itself, so the hint doesn't tell it to.
        loose, message = self._loose_folder_error(private_dir, 0)
        assert message.endswith(
            f'. Run \'chmod go-w {loose}\', or move the socket to a folder '
            'only you can write to.'
        )

    def test_a_loose_folder_you_own_doesnt_say_as_root(self, private_dir):
        loose, message = self._loose_folder_error(
            private_dir, OTHER_UID, owner=OTHER_UID
        )
        assert message.endswith(
            f'. Run \'chmod go-w {loose}\', or move the socket to a folder '
            'only you can write to.'
        )

    def test_the_walk_stops_at_a_folder_that_isnt_there_yet(self, private_dir):
        # A daemon that hasn't started may not have made its folder.
        check_socket_folders(str(private_dir / 'later' / 'd.sock'))

    def test_a_loose_folder_above_a_missing_one_is_refused(self, private_dir):
        loose = private_dir / 'pub'
        loose.mkdir()
        loose.chmod(0o777)
        with pytest.raises(CredentialDaemonUntrustedSocketError):
            check_socket_folders(str(loose / 'later' / 'd.sock'))

    def test_the_overflow_uid_is_refused(self, private_dir):
        with mock.patch(
            'botocore.credential_daemon.host.os.geteuid',
            return_value=OVERFLOW_UID,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError):
                check_socket_folders(str(private_dir / 'd.sock'))


@contextlib.contextmanager
def _as_mode(path, mode):
    # A link or file swapped in for the folder at path after
    # os.path.realpath ran: realpath returns its argument, and os.lstat
    # gives path the file type and mode in mode.
    real_lstat = os.lstat

    def lstat(p, *args, **kwargs):
        st = real_lstat(p, *args, **kwargs)
        if os.fspath(p) != os.fspath(path):
            return st
        fields = list(st)
        fields[stat.ST_MODE] = mode
        return os.stat_result(fields)

    with (
        mock.patch('os.path.realpath', side_effect=lambda p, **kw: p),
        mock.patch('os.lstat', side_effect=lstat),
    ):
        yield


NOT_FOLDERS = [stat.S_IFLNK | 0o755, stat.S_IFREG | 0o755]


@skip_if_windows
class TestFolderMustBeAFolder:
    """A link or a file where a folder on the socket's path should be is
    refused, whatever its owner and mode: the path was resolved first, so
    a link there was swapped in after that."""

    def test_a_real_folder_passes(self, private_dir):
        folder = private_dir / 'own'
        folder.mkdir(mode=0o755)
        path = folder / 'd.sock'
        with listen(path):
            assert check_socket(str(path))[0] == str(path)
        check_socket_folders(str(path))

    def test_a_file_in_place_of_a_folder_is_refused(self, private_dir):
        file = private_dir / 'run'
        file.write_text('')
        file.chmod(0o644)
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_socket_folders(str(file / 'd.sock'))
        assert str(e.value).endswith(f": {file} isn't a folder.")

    def test_a_real_link_on_the_walk_is_refused(self, private_dir):
        # os.path.realpath leaves a link that points at itself in place,
        # so the walk meets a real link.
        loop = private_dir / 'loop'
        loop.symlink_to(loop)
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_socket_folders(str(loop / 'd.sock'))
        assert str(e.value).endswith(f": {loop} isn't a folder.")

    @pytest.mark.parametrize('mode', NOT_FOLDERS, ids=['link', 'file'])
    def test_a_link_or_file_on_the_walk_is_refused(self, private_dir, mode):
        folder = private_dir / 'own'
        folder.mkdir(mode=0o755)
        path = folder / 'd.sock'
        with listen(path) as server, _as_mode(folder, mode):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
            assert_never_connected(server)
        assert e.value.code == 'UNTRUSTED_SOCKET'
        assert str(e.value) == (
            f"The CLI didn't trust the credential daemon socket {path}, so "
            f"it sent nothing to it: {folder} isn't a folder."
        )

    @pytest.mark.parametrize('mode', NOT_FOLDERS, ids=['link', 'file'])
    def test_a_link_or_file_on_the_walk_before_start_is_refused(
        self, private_dir, mode
    ):
        folder = private_dir / 'own'
        folder.mkdir(mode=0o755)
        with _as_mode(folder, mode):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket_folders(str(folder / 'later' / 'd.sock'))
        assert str(e.value).endswith(f": {folder} isn't a folder.")

    @pytest.mark.parametrize('mode', NOT_FOLDERS, ids=['link', 'file'])
    def test_a_link_or_file_as_the_system_folder_is_refused(
        self, private_dir, mode
    ):
        folder = private_dir / 'credsd'
        folder.mkdir(mode=0o755)
        path = folder / 'credsd.sock'
        with (
            listen(path) as server,
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            linux_system_rule(),
            _as_mode(folder, mode),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
            assert_never_connected(server)
        assert str(e.value).endswith(f": {folder} isn't a folder.")


@skip_if_windows
class TestProbeSocket:
    def test_runs_the_checks_and_sends_nothing(self, private_dir):
        path = private_dir / 'd.sock'
        with listen(path) as server:
            with mock.patch(
                'botocore.credential_daemon.transport.check_peer'
            ) as check_peer_:
                probe_socket(str(path))
            server.setblocking(True)
            connection, _ = server.accept()
            with connection:
                connection.setblocking(False)
                # Closed with nothing sent.
                assert connection.recv(1) == b''
        assert check_peer_.called

    def test_loose_folder_is_refused(self, private_dir):
        loose = private_dir / 'pub'
        loose.mkdir()
        path = loose / 'd.sock'
        with listen(path) as server:
            loose.chmod(0o777)
            with pytest.raises(CredentialDaemonUntrustedSocketError):
                probe_socket(str(path))
            assert_never_connected(server)


class _WithoutGeteuid:
    """``os`` without ``geteuid``, as a runtime without a POSIX API has."""

    def __getattr__(self, name):
        if name == 'geteuid':
            raise AttributeError(name)
        return getattr(os, name)


def _with_uid(st, uid):
    fields = list(st)
    fields[4] = uid
    return os.stat_result(fields)


@skip_if_windows
class TestSystemSocketFolder:
    """At a system location, which is trusted by where it is, the socket's
    own folder must be closed to others and, on Linux, owned by root or the
    socket's owner (macOS: TestMacosSystemSocketOwner)."""

    def test_loose_system_folder_is_refused(self, private_dir):
        folder = private_dir / 'aws-credential-daemon'
        folder.mkdir()
        path = folder / 'daemon.sock'
        with (
            listen(path) as server,
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            linux_system_rule(),
        ):
            folder.chmod(0o777)
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
            assert_never_connected(server)
        assert str(e.value).endswith(
            f'its folder {folder} is writable by other users (mode 0777). '
            f'Run \'chmod go-w {folder}\' as root.'
        )

    def test_system_location_skips_the_folders_above(self, private_dir):
        # Trusted by location: the caller needn't own anything there.
        folder = private_dir / 'credsd'
        folder.mkdir(mode=0o755)
        path = folder / 'credsd.sock'
        with (
            listen(path),
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            linux_system_rule(),
            mock.patch('os.geteuid', return_value=foreign_uid()),
        ):
            assert check_socket(str(path)) == (str(path), os.getuid())

    def test_system_paths_are_resolved(self):
        # Only the AWS credential daemon's own: the generic paths are gone.
        assert system_socket_paths('linux') == {
            os.path.realpath(LINUX_OWN_SOCKET_PATH),
        }
        # macOS resolves only /var/run: see the next test.
        assert system_socket_paths('darwin') == {
            os.path.join(
                os.path.realpath('/var/run'), 'credsd', 'credsd.sock'
            ),
        }
        assert system_socket_paths('win32') == frozenset()

    def test_macos_system_path_resolves_only_var_run(self):
        # /private/var/run is writable by the daemon group, so a link put
        # in place of its credsd folder must not move the system socket.
        def realpath(p, *args, **kwargs):
            if p == '/var/run':
                return '/private/var/run'
            if p.startswith('/var/run/credsd'):
                return (
                    '/private/var/run/elsewhere' + p[len('/var/run/credsd') :]
                )
            return p

        with mock.patch('os.path.realpath', side_effect=realpath):
            assert system_socket_paths('darwin') == {
                '/private/var/run/credsd/credsd.sock',
            }


def _owned_by(path_uids):
    # os.lstat, with the owner of each path in path_uids replaced.
    real_lstat = os.lstat

    def lstat(p, *args, **kwargs):
        st = real_lstat(p, *args, **kwargs)
        uid = path_uids.get(os.fspath(p))
        return st if uid is None else _with_uid(st, uid)

    return mock.patch('os.lstat', side_effect=lstat)


@skip_if_windows
class TestMacosSystemSocketOwner:
    """On macOS the system socket and its folder must be owned by root:
    /private/var/run is writable by the daemon group, so "owned by the
    socket's owner" would let that group put its own socket there. Linux
    keeps the socket's owner."""

    @pytest.fixture
    def system_socket(self, private_dir):
        folder = private_dir / 'credsd'
        folder.mkdir(mode=0o755)
        path = folder / 'credsd.sock'
        with (
            listen(path) as server,
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            mock.patch('os.geteuid', return_value=foreign_uid()),
        ):
            yield folder, path, server

    def test_root_owned_folder_and_socket_pass(self, system_socket):
        folder, path, _ = system_socket
        with (
            macos_system_rule(),
            _owned_by({str(folder): 0, str(path): 0}),
        ):
            assert check_socket(str(path)) == (str(path), 0)

    def test_socket_not_owned_by_root_is_refused(self, system_socket):
        folder, path, server = system_socket
        with (
            macos_system_rule(),
            _owned_by({str(folder): 0, str(path): 1}),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
        assert_never_connected(server)
        assert str(e.value).endswith(
            'the socket is owned by uid 1, not by root.'
        )

    def test_folder_not_owned_by_root_is_refused(self, system_socket):
        # Owned by the daemon user (uid 1), which the daemon group could
        # have made.
        folder, path, server = system_socket
        with (
            macos_system_rule(),
            _owned_by({str(folder): 1, str(path): 0}),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
        assert_never_connected(server)
        assert str(e.value).endswith(
            f'its folder {folder} is owned by uid 1, not by root.'
        )

    def test_socket_owners_folder_passes_on_linux_only(self, system_socket):
        # The same socket and folder, both owned by the socket's owner (uid
        # 1, whatever the caller's uid): Linux passes them, macOS doesn't.
        folder, path, _ = system_socket
        with _owned_by({str(folder): 1, str(path): 1}):
            with linux_system_rule():
                assert check_socket(str(path)) == (str(path), 1)
            with macos_system_rule():
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    check_socket(str(path))
        assert str(e.value).endswith(
            'the socket is owned by uid 1, not by root.'
        )

    def test_loose_root_owned_folder_is_still_refused(self, system_socket):
        folder, path, _ = system_socket
        folder.chmod(0o775)
        with (
            macos_system_rule(),
            _owned_by({str(folder): 0, str(path): 0}),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert str(e.value).endswith(
            f'its folder {folder} is writable by other users (mode 0775). '
            f'Run \'chmod go-w {folder}\' as root.'
        )

    def test_linux_folder_owned_by_another_user_is_refused(
        self, system_socket
    ):
        folder, path, _ = system_socket
        with (
            linux_system_rule(),
            _owned_by({str(folder): 1, str(path): 2}),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert str(e.value).endswith(
            f'its folder {folder} is owned by uid 1, not by root or the '
            'socket\'s owner.'
        )

    def test_control_characters_are_stripped_from_the_owner_error(
        self, private_dir
    ):
        folder = private_dir / 'c\x1b[2K'
        folder.mkdir(mode=0o755)
        path = folder / 'credsd.sock'
        with (
            listen(path),
            mock.patch(
                f'{CD}.trust.system_socket_paths', return_value={str(path)}
            ),
            macos_system_rule(),
            _owned_by({str(folder): 1, str(path): 0}),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_socket(str(path))
        assert '\x1b' not in str(e.value)
        assert 'c[2K' in str(e.value)
        assert 'not by root.' in str(e.value)


@skip_if_windows
class TestMacosSystemSocketPeer:
    """On macOS only root may serve the system socket: a daemon-group
    process could swap the credsd folder in /private/var/run after the
    path check, and its socket's peer isn't root. The caller's uid is
    mocked (CALLER), so this holds when the tests run as root."""

    CALLER = 501
    OWNER = 502
    SYSTEM = '/private/var/run/credsd/credsd.sock'
    PER_USER = '/Users/me/.aws/credential-daemon/credsd.sock'

    @pytest.fixture(autouse=True)
    def caller(self):
        with (
            mock.patch('os.geteuid', return_value=self.CALLER),
            mock.patch(
                f'{CD}.trust.system_socket_paths',
                return_value=frozenset((self.SYSTEM,)),
            ),
        ):
            yield

    def check(self, path, peer, owner):
        with mock.patch(f'{CD}.trust._peer_uid', return_value=peer):
            check_peer(mock.Mock(), path, owner)

    def test_root_peer_passes(self):
        with macos_system_rule():
            self.check(self.SYSTEM, 0, 0)

    @pytest.mark.parametrize(
        'peer, owner',
        [(CALLER, 0), (OWNER, OWNER), (CALLER, CALLER)],
        ids=['caller', 'socket-owner', 'caller-owns-the-socket'],
    )
    def test_any_other_peer_is_refused(self, peer, owner):
        with macos_system_rule():
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.check(self.SYSTEM, peer, owner)
        assert str(e.value).endswith(
            f'the process serving it runs as uid {peer}, not as root.'
        )

    @pytest.mark.parametrize('peer', [CALLER, OWNER, 0])
    def test_per_user_socket_is_unchanged(self, peer):
        with macos_system_rule():
            self.check(self.PER_USER, peer, self.OWNER)

    @pytest.mark.parametrize('peer', [CALLER, OWNER, 0])
    def test_linux_rule_at_the_system_socket_is_unchanged(self, peer):
        # The same path with the Linux rule (root_only false).
        with linux_system_rule():
            self.check(self.SYSTEM, peer, self.OWNER)

    def test_other_peers_are_still_refused_elsewhere(self):
        with macos_system_rule():
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.check(self.PER_USER, OTHER_UID, self.OWNER)
        assert 'not as you, root or the socket\'s owner' in str(e.value)

    def test_swapped_socket_gets_no_request(self, private_dir):
        # A root-owned folder and socket pass check_socket, as the real
        # ones did before the swap; the process serving the socket isn't
        # root, so nothing is sent.
        from tests.utils.credential_daemon import FakeCredentialDaemon

        with FakeCredentialDaemon(
            socket_path=str(private_dir / 'credsd' / 'credsd.sock')
        ) as fake:
            path = fake.socket_path
            folder = os.path.dirname(path)
            with (
                mock.patch(
                    f'{CD}.trust.system_socket_paths',
                    return_value=frozenset((path,)),
                ),
                macos_system_rule(),
                _owned_by({folder: 0, path: 0}),
                mock.patch(f'{CD}.trust._peer_uid', return_value=self.CALLER),
            ):
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    CredentialDaemonClient(socket_path=path).store_keys(
                        'keys.ci', 'AKID', 'SECRET', 'us-east-1'
                    )
            assert fake.calls == []
        assert str(e.value).endswith(
            f'runs as uid {self.CALLER}, not as root.'
        )

    def test_link_to_the_system_socket_gets_the_root_rule(self, private_dir):
        # A link dialed (as ~/.aws/credential-daemon.sock or the env var
        # can be) resolves to the system socket, and check_peer is given
        # the resolved path, so the root rule still applies.
        from tests.utils.credential_daemon import FakeCredentialDaemon

        with FakeCredentialDaemon(
            socket_path=str(private_dir / 'credsd' / 'credsd.sock')
        ) as fake:
            path = fake.socket_path
            folder = os.path.dirname(path)
            link = private_dir / 'link.sock'
            link.symlink_to(path)
            with (
                mock.patch(
                    f'{CD}.trust.system_socket_paths',
                    return_value=frozenset((path,)),
                ),
                macos_system_rule(),
                _owned_by({folder: 0, path: 0}),
                mock.patch(f'{CD}.trust._peer_uid', return_value=self.CALLER),
            ):
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    CredentialDaemonClient(socket_path=str(link)).store_keys(
                        'keys.ci', 'AKID', 'SECRET', 'us-east-1'
                    )
            assert fake.calls == []
        assert str(e.value).endswith(
            f'runs as uid {self.CALLER}, not as root.'
        )


@skip_if_windows
class TestPeerCheck:
    """After connect, the peer must be the caller, root or the socket's
    owner, on the connection that carries the request (only root at the
    macOS system socket: TestMacosSystemSocketPeer)."""

    @pytest.fixture
    def fake(self, private_dir):
        from tests.utils.credential_daemon import FakeCredentialDaemon

        with FakeCredentialDaemon(
            socket_path=str(private_dir / 'fake' / 'daemon.sock')
        ) as fake:
            yield fake

    def test_real_peer_is_the_caller(self, fake):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with sock:
            sock.connect(fake.socket_path)
            assert _peer_uid(sock) == os.geteuid()

    def test_disallowed_peer_gets_no_request(self, fake):
        with mock.patch(f'{CD}.trust._peer_uid', return_value=foreign_uid()):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=fake.socket_path
                ).store_keys('keys.ci', 'AKID', 'SECRET', 'us-east-1')
        assert fake.calls == []
        assert str(e.value) == (
            'The CLI didn\'t trust the credential daemon socket '
            f'{fake.socket_path}, so it sent nothing to it: the process '
            f'serving it runs as uid {foreign_uid()}, not as you, root or '
            'the socket\'s owner.'
        )

    @pytest.mark.parametrize('peer', ['caller', 'root'])
    def test_allowed_peers(self, fake, peer):
        uid = os.geteuid() if peer == 'caller' else 0
        with mock.patch(f'{CD}.trust._peer_uid', return_value=uid):
            assert (
                CredentialDaemonClient(
                    socket_path=fake.socket_path
                ).list_credentials()
                == []
            )
        assert [method for method, _ in fake.calls] == ['credential/list']

    def test_socket_owner_is_allowed_at_a_system_location(self, fake):
        # Linux's system daemon runs as the account that owns the socket,
        # not as the caller.
        with (
            mock.patch(
                f'{CD}.trust.system_socket_paths',
                return_value={fake.socket_path},
            ),
            mock.patch('os.geteuid', return_value=foreign_uid()),
            linux_system_rule(),
        ):
            assert (
                CredentialDaemonClient(
                    socket_path=fake.socket_path
                ).list_credentials()
                == []
            )

    def test_linux_peer_uid_is_unsigned(self):
        # SO_PEERCRED's uid and gid are unsigned: a uid of 2**31 or more
        # is the uid, not a negative number, so its owner is allowed.
        uid = 4294967294
        sock = mock.Mock()
        sock.getsockopt.return_value = struct.pack('iII', 1234, uid, uid)
        with (
            mock.patch('sys.platform', 'linux'),
            mock.patch.object(socket, 'SO_PEERCRED', 17, create=True),
        ):
            assert _peer_uid(sock) == uid
            check_peer(sock, '/run/credsd/credsd.sock', uid)
            # Anyone else with a high uid is still refused.
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                check_peer(sock, '/run/credsd/credsd.sock', uid - 1)
        assert f'runs as uid {uid}, not as you' in str(e.value)

    def test_fake_reads_the_linux_peer_uid_as_unsigned(self):
        # The fake daemon reads SO_PEERCRED like the CLI does, so a
        # client whose uid is 2**31 or more isn't refused by the fake.
        from tests.utils.credential_daemon.server import _peer_is_current_user

        uid = 4294967294
        sock = mock.Mock()
        sock.getsockopt.return_value = struct.pack('iII', 1234, uid, uid)
        with mock.patch.object(socket, 'SO_PEERCRED', 17, create=True):
            with mock.patch('os.getuid', return_value=uid):
                assert _peer_is_current_user(sock)
            with mock.patch('os.getuid', return_value=uid - 1):
                assert not _peer_is_current_user(sock)

    def test_refusal_names_the_socket_as_given_and_resolved(self, private_dir):
        # macOS's /tmp is a link to /private/tmp; a link of our own does
        # the same here.
        real = private_dir / 'real'
        real.mkdir()
        link = private_dir / 'link'
        link.symlink_to(real)
        other = os.geteuid() + 1
        with (
            listen(real / 'd.sock'),
            mock.patch(f'{CD}.trust._peer_uid', return_value=other),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(link / 'd.sock')
                ).list_credentials()
        assert f'socket {link}/d.sock ({real}/d.sock)' in str(e.value)
        assert str(e.value).endswith(
            f': the process serving it runs as uid {other}, not as you, root '
            'or the socket\'s owner.'
        )

    def test_refusal_without_a_link_names_the_socket_once(self, private_dir):
        path = private_dir / 'd.sock'
        other = os.geteuid() + 1
        with (
            listen(path),
            mock.patch(f'{CD}.trust._peer_uid', return_value=other),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=str(path)
                ).list_credentials()
        assert f'socket {path}' in str(e.value)
        assert f'{path} (' not in str(e.value)

    def test_overflow_uid_owner_is_never_allowed(self):
        sock = mock.Mock()
        with mock.patch(f'{CD}.trust._peer_uid', return_value=65534):
            with pytest.raises(CredentialDaemonUntrustedSocketError):
                check_peer(sock, '/run/credsd/credsd.sock', 65534)

    def test_unreadable_peer_is_refused(self, fake):
        with mock.patch(
            f'{CD}.trust._peer_uid',
            side_effect=OSError(22, 'Invalid argument'),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=fake.socket_path
                ).list_credentials()
        assert 'couldn\'t read which user serves it: Invalid argument' in (
            str(e.value)
        )
        assert fake.calls == []

    @pytest.mark.parametrize('version, ok', [(0, True), (1, False)])
    def test_macos_peer_credentials_need_the_known_layout(self, version, ok):
        # struct xucred: cr_version, cr_uid, cr_ngroups, cr_groups[16].
        raw = struct.pack('=II', version, os.geteuid()) + bytes(68)
        sock = mock.Mock()
        sock.getsockopt.return_value = raw
        with mock.patch('sys.platform', 'darwin'):
            if ok:
                check_peer(sock, '/tmp/d.sock', os.geteuid())
            else:
                with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                    check_peer(sock, '/tmp/d.sock', os.geteuid())
                assert 'unknown xucred version 1' in str(e.value)

    def test_untrusted_isnt_not_running(self):
        # Commands add the start-the-daemon hint only for NOT_RUNNING.
        error = CredentialDaemonUntrustedSocketError(error_msg='x')
        assert isinstance(error, CredentialDaemonConnectionError)
        assert not isinstance(error, CredentialDaemonNotRunningError)


_UNSHARE_CLIENT = '''
import sys
sys.path.insert(0, sys.argv[1])
import awscli  # noqa: F401 (makes the bundled botocore importable)
from botocore.credential_daemon import CredentialDaemonClient
from botocore.exceptions import CredentialDaemonError
try:
    CredentialDaemonClient(socket_path=sys.argv[2]).list_credentials()
except CredentialDaemonError as e:
    print(e.code)
else:
    print('sent')
'''


@pytest.mark.skipif(
    not sys.platform.startswith('linux') or shutil.which('unshare') is None,
    reason='needs unshare on Linux',
)
@pytest.mark.parametrize(
    'flags',
    [
        # The caller is unmapped, so it runs as 65534.
        [],
        # The caller is another uid, and root and the socket's owner are
        # unmapped: they show as 65534.
        [f'--map-user={OTHER_UID}'],
    ],
    ids=['unmapped', 'another-uid'],
)
def test_real_caller_in_another_user_namespace(private_dir, flags):
    import subprocess

    from tests.utils.credential_daemon import FakeCredentialDaemon

    path = str(private_dir / 'fake' / 'daemon.sock')
    with FakeCredentialDaemon(socket_path=path) as fake:
        # Others may enter the folder, as they may /run/credsd.
        os.chmod(private_dir, 0o755)
        os.chmod(os.path.dirname(path), 0o755)
        root = os.path.dirname(
            os.path.dirname(os.path.dirname(botocore.__file__))
        )
        try:
            run = subprocess.run(
                [
                    'unshare',
                    '--user',
                    *flags,
                    sys.executable,
                    '-c',
                    _UNSHARE_CLIENT,
                    root,
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as e:
            pytest.skip(f'unshare failed: {e}')
        if run.returncode != 0 and 'unshare' in run.stderr:
            pytest.skip(f'unshare isn\'t allowed here: {run.stderr.strip()}')
        assert run.stdout.strip() == 'UNTRUSTED_SOCKET', run.stderr
        assert fake.calls == []


# macOS: the process serving the socket must be the signed credential
# daemon (check_code_signature). These run on any platform, with the
# ctypes layer mocked, except the last, which runs the real one.

SIGNED_RELEASE_REQUIREMENT = (
    'identifier "com.amazon.aws.credsd.daemon" and anchor apple generic and '
    'certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and '
    'certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and '
    'certificate leaf[subject.OU] = "94KV3E626L"'
)
TOKEN = bytes(range(32))


def test_code_requirement_is_the_signed_releases():
    # What `codesign -d -r-` printed for the 2026-11-11 release.
    assert CREDENTIAL_DAEMON_CODE_REQUIREMENT == SIGNED_RELEASE_REQUIREMENT
    assert f'"{CREDENTIAL_DAEMON_PACKAGE_ID}"' in SIGNED_RELEASE_REQUIREMENT
    assert f'"{CREDENTIAL_DAEMON_TEAM_ID}"' in SIGNED_RELEASE_REQUIREMENT


class FakeFrameworks:
    """CoreFoundation and Security.framework, as ``_CodeSigning.load``
    sees them through ctypes. Each made object gets a fresh address, and
    ``released`` lists the ones CFRelease got."""

    AUDIT_KEY = 0x100
    KEY_CALLBACKS = 0x200
    VALUE_CALLBACKS = 0x300

    def __init__(self, validity=0, guest=0, requirement=0, missing=()):
        self.validity = validity
        self.guest = guest
        self.requirement = requirement
        self.missing = set(missing)
        self.made = []
        self.released = []
        self.calls = []
        self._next = 0x1000

    def _make(self, what):
        self._next += 0x10
        self.made.append(self._next)
        self.calls.append((what, self._next))
        return self._next

    def cdll(self, path):
        assert path.startswith('/System/Library/Frameworks/')
        fake = self

        class Lib:
            def __getattr__(self, name):
                if name in fake.missing:
                    raise AttributeError(
                        f'dlsym(..., {name}): symbol not found'
                    )
                function = mock.Mock(side_effect=getattr(fake, name))
                setattr(self, name, function)
                return function

        return Lib()

    def in_dll(self, ctype, lib, name):
        if name in self.missing:
            raise ValueError(f'symbol {name} not found')
        return {
            'kSecGuestAttributeAudit': self.AUDIT_KEY,
            'kCFTypeDictionaryKeyCallBacks': self.KEY_CALLBACKS,
            'kCFTypeDictionaryValueCallBacks': self.VALUE_CALLBACKS,
        }[name]

    def CFDataCreate(self, allocator, data, length):
        assert data == TOKEN and length == 32
        return self._make('data')

    def CFDictionaryCreate(self, allocator, keys, values, n, kcb, vcb):
        assert n == 1
        assert keys[0] == self.AUDIT_KEY
        assert values[0] == self.made[-1]
        assert (kcb, vcb) == (self.KEY_CALLBACKS, self.VALUE_CALLBACKS)
        return self._make('attributes')

    def CFStringCreateWithCString(self, allocator, text, encoding):
        assert text == SIGNED_RELEASE_REQUIREMENT.encode()
        assert encoding == 0x08000100
        return self._make('requirement text')

    def CFRelease(self, ref):
        self.released.append(ref)

    def SecCodeCopyGuestWithAttributes(self, host, attributes, flags, out):
        assert host is None and flags == 0
        self.calls.append(('guest', attributes))
        if self.guest:
            return self.guest
        out._obj.value = self._make('code')
        return 0

    def SecRequirementCreateWithString(self, text, flags, out):
        if self.requirement:
            return self.requirement
        out._obj.value = self._make('requirement')
        return 0

    def SecCodeCheckValidity(self, code, flags, requirement):
        self.calls.append(('validity', code.value, requirement.value))
        return self.validity

    def check(self):
        signing = _CodeSigning.load(cdll=self.cdll, in_dll=self.in_dll)
        return signing.check(TOKEN, SIGNED_RELEASE_REQUIREMENT)


class TestCodeSigningCalls:
    """The Security.framework calls, through a fake ctypes layer."""

    def test_valid_signature_is_0_and_everything_is_released(self):
        fake = FakeFrameworks()
        assert fake.check() == 0
        whats = [c[0] for c in fake.calls]
        assert whats == [
            'data',
            'attributes',
            'guest',
            'code',
            'requirement text',
            'requirement',
            'validity',
        ]
        assert sorted(fake.released) == sorted(fake.made)
        # The attributes dictionary holds the token, the guest is looked up
        # by it, and the requirement is checked against that guest.
        attributes = next(v for w, v in fake.calls if w == 'attributes')
        code = next(v for w, v in fake.calls if w == 'code')
        assert ('guest', attributes) in fake.calls
        assert fake.calls[-1] == ('validity', code, fake.made[-1])

    def test_requirement_not_met_returns_its_status(self):
        fake = FakeFrameworks(validity=-67050)
        assert fake.check() == -67050
        assert sorted(fake.released) == sorted(fake.made)

    def test_no_guest_for_the_token_returns_its_status(self):
        fake = FakeFrameworks(guest=-67065)
        assert fake.check() == -67065
        assert sorted(fake.released) == sorted(fake.made)
        assert 'validity' not in [c[0] for c in fake.calls]

    def test_bad_requirement_returns_its_status(self):
        fake = FakeFrameworks(requirement=-67052)
        assert fake.check() == -67052
        assert sorted(fake.released) == sorted(fake.made)

    @pytest.mark.parametrize(
        'symbol',
        ['SecCodeCheckValidity', 'CFRelease', 'kSecGuestAttributeAudit'],
    )
    def test_missing_symbol_raises(self, symbol):
        fake = FakeFrameworks(missing=[symbol])
        with pytest.raises((AttributeError, ValueError)):
            fake.check()

    def test_null_result_raises_and_releases_what_was_made(self):
        fake = FakeFrameworks()
        fake.CFStringCreateWithCString = lambda *a: None
        with pytest.raises(ValueError, match='CFStringCreateWithCString'):
            fake.check()
        assert fake.made and sorted(fake.released) == sorted(fake.made)


@skip_if_windows
@pytest.mark.real_code_signature
class TestCodeSignatureCheck:
    """check_code_signature on the connection, with the ctypes layer
    mocked, as on macOS: a refusal sends nothing."""

    @pytest.fixture
    def fake(self, private_dir):
        from tests.utils.credential_daemon import FakeCredentialDaemon

        with FakeCredentialDaemon(
            socket_path=str(private_dir / 'fake' / 'daemon.sock')
        ) as fake:
            yield fake

    @pytest.fixture
    def as_macos(self):
        # The platform gate and the audit token, as on macOS; the peer
        # uid check uses the real SO_PEERCRED (or LOCAL_PEERCRED).
        with (
            mock.patch(
                f'{CD}.transport.checks_code_signature', return_value=True
            ),
            mock.patch(f'{CD}.codesign._peer_audit_token', return_value=TOKEN),
        ):
            yield

    def frameworks(self, fake_frameworks):
        signing = _CodeSigning.load(
            cdll=fake_frameworks.cdll, in_dll=fake_frameworks.in_dll
        )
        return mock.patch(f'{CD}.codesign._code_signing', signing)

    def store(self, fake):
        return CredentialDaemonClient(socket_path=fake.socket_path).store_keys(
            'keys.ci', 'AKID', 'SECRET', 'us-east-1'
        )

    def test_signed_daemon_gets_the_request(self, fake, as_macos):
        frameworks = FakeFrameworks()
        with self.frameworks(frameworks):
            self.store(fake)
        assert [method for method, _ in fake.calls] == ['credential/bootstrap']
        assert [c[0] for c in frameworks.calls].count('validity') == 1

    def test_requirement_not_met_is_refused(self, fake, as_macos):
        with self.frameworks(FakeFrameworks(validity=-67050)):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert fake.calls == []
        assert e.value.code == 'UNTRUSTED_SOCKET'
        assert str(e.value) == (
            'The CLI didn\'t trust the credential daemon socket '
            f'{fake.socket_path}, so it sent nothing to it: the process '
            'serving it isn\'t the signed credential daemon (OSStatus '
            '-67050). Install the signed release with "aws configure '
            'credential-daemon install".'
        )

    def test_refusal_names_the_socket_as_given_and_resolved(
        self, fake, as_macos, private_dir
    ):
        link = private_dir / 'link'
        link.symlink_to(private_dir / 'fake')
        given = str(link / 'daemon.sock')
        with self.frameworks(FakeFrameworks(validity=-67050)):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(socket_path=given).store_keys(
                    'keys.ci', 'AKID', 'SECRET', 'us-east-1'
                )
        assert fake.calls == []
        assert f'socket {given} ({fake.socket_path})' in str(e.value)
        assert (
            ': the process serving it isn\'t the signed credential daemon'
            in str(e.value)
        )

    @pytest.mark.parametrize('status', [-67062, -67061, -67063])
    def test_unsigned_or_broken_code_is_refused(self, fake, as_macos, status):
        with self.frameworks(FakeFrameworks(validity=status)):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert fake.calls == []
        assert 'isn\'t the signed credential daemon' in str(e.value)

    def test_other_status_is_refused_as_unchecked(self, fake, as_macos):
        with self.frameworks(FakeFrameworks(guest=-67065)):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert fake.calls == []
        assert str(e.value).endswith(
            'the CLI couldn\'t check the credential daemon\'s signature '
            '(OSStatus -67065).'
        )

    def test_peer_token_unreadable_is_refused(self, fake):
        with (
            mock.patch(
                f'{CD}.transport.checks_code_signature', return_value=True
            ),
            mock.patch(
                f'{CD}.codesign._peer_audit_token',
                side_effect=OSError(22, 'Invalid argument'),
            ),
            self.frameworks(FakeFrameworks()),
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert fake.calls == []
        assert 'couldn\'t read which process serves it: Invalid argument' in (
            str(e.value)
        )

    def test_short_peer_token_is_refused(self, fake):
        sock = mock.Mock()
        sock.getsockopt.return_value = b'\0' * 8
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_code_signature(sock, fake.socket_path)
        sock.getsockopt.assert_called_once_with(0, 6, 32)
        assert 'audit token is 8 bytes, not 32' in str(e.value)

    @pytest.mark.parametrize(
        'symbol', ['SecCodeCheckValidity', 'kSecGuestAttributeAudit']
    )
    def test_missing_security_symbol_is_refused(self, fake, as_macos, symbol):
        frameworks = FakeFrameworks(missing=[symbol])
        # Saved before the patch, so the real loader runs on the fake
        # frameworks rather than the mock calling itself.
        real_load = _CodeSigning.load
        with (
            mock.patch(f'{CD}.codesign._code_signing', None),
            mock.patch(
                f'{CD}.codesign._CodeSigning.load',
                side_effect=lambda *args, **kwargs: real_load(
                    cdll=frameworks.cdll, in_dll=frameworks.in_dll
                ),
            ) as load,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        load.assert_called_once()
        assert fake.calls == []
        assert 'couldn\'t check the credential daemon\'s signature: ' in str(
            e.value
        )
        # The real loader's error, not a TypeError from the patch.
        assert symbol in str(e.value)

    def test_security_framework_missing_is_refused(self, fake, as_macos):
        # Linux has no Security.framework: the real loader fails.
        with mock.patch(f'{CD}.codesign._code_signing', None):
            with mock.patch(
                'ctypes.CDLL', side_effect=OSError('no such file')
            ):
                with pytest.raises(CredentialDaemonUntrustedSocketError):
                    self.store(fake)
        assert fake.calls == []

    def test_peer_level_never_checks_it(self, fake, as_macos, caplog):
        # The credential provider's credential/get gets the folder, owner
        # and peer uid checks, not this one.
        with (
            mock.patch(f'{CD}.transport.check_code_signature') as check,
            mock.patch(f'{CD}.transport.check_peer', wraps=check_peer) as peer,
            caplog.at_level('DEBUG', logger='botocore.credential_daemon'),
        ):
            CredentialDaemonClient(
                socket_path=fake.socket_path, checks=SocketChecks.PEER
            ).list_credentials()
        check.assert_not_called()
        peer.assert_called_once()
        assert 'the user serving it.' in caplog.text
        assert 'code signature' not in caplog.text
        assert fake.calls != []

    def test_full_level_checks_it(self, fake, as_macos, caplog):
        with (
            mock.patch(f'{CD}.transport.check_code_signature') as check,
            caplog.at_level('DEBUG', logger='botocore.credential_daemon'),
        ):
            CredentialDaemonClient(
                socket_path=fake.socket_path, checks=SocketChecks.FULL
            ).list_credentials()
        check.assert_called_once()
        assert 'the user serving it, and its code signature.' in caplog.text

    @pytest.fixture
    def at_system_socket(self, fake):
        # The fake's socket as the macOS system socket: root owns it and
        # its folder, and serves it, as launchd does.
        system = {fake.socket_path}
        with (
            mock.patch(f'{CD}.trust.system_socket_paths', return_value=system),
            macos_system_rule(),
            _owned_by(
                {fake.socket_path: 0, os.path.dirname(fake.socket_path): 0}
            ),
            mock.patch(f'{CD}.trust._peer_uid', return_value=0),
        ):
            yield

    def test_full_level_checks_it_at_the_system_socket(
        self, fake, as_macos, at_system_socket, caplog
    ):
        # Root owning the socket and its folder, and serving it, doesn't
        # prove the peer: launchd reports uid 0 for a user's LaunchAgent
        # socket too.
        with (
            mock.patch(f'{CD}.transport.check_code_signature') as check,
            mock.patch(f'{CD}.transport.check_peer', wraps=check_peer) as peer,
            caplog.at_level('DEBUG', logger='botocore.credential_daemon'),
        ):
            self.store(fake)
        check.assert_called_once()
        peer.assert_called_once()
        assert [method for method, _ in fake.calls] == ['credential/bootstrap']
        assert 'the user serving it, and its code signature.' in caplog.text

    def test_unsigned_daemon_at_the_system_socket_is_refused(
        self, fake, as_macos, at_system_socket
    ):
        # A daemon built from source and installed as a system service
        # isn't signed: it's refused like an unsigned per-user daemon,
        # with the same message and hint.
        with self.frameworks(FakeFrameworks(validity=-67062)):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert fake.calls == []
        assert e.value.code == 'UNTRUSTED_SOCKET'
        assert str(e.value) == (
            'The CLI didn\'t trust the credential daemon socket '
            f'{fake.socket_path}, so it sent nothing to it: the process '
            'serving it isn\'t the signed credential daemon (OSStatus '
            '-67062). Install the signed release with "aws configure '
            'credential-daemon install".'
        )

    def test_signed_daemon_at_the_system_socket_gets_the_request(
        self, fake, as_macos, at_system_socket
    ):
        frameworks = FakeFrameworks()
        with self.frameworks(frameworks):
            self.store(fake)
        assert [method for method, _ in fake.calls] == ['credential/bootstrap']
        assert [c[0] for c in frameworks.calls].count('validity') == 1

    def test_peer_level_at_the_system_socket_is_unchanged(
        self, fake, as_macos, at_system_socket, caplog
    ):
        with (
            mock.patch(f'{CD}.transport.check_code_signature') as check,
            caplog.at_level('DEBUG', logger='botocore.credential_daemon'),
        ):
            CredentialDaemonClient(
                socket_path=fake.socket_path, checks=SocketChecks.PEER
            ).list_credentials()
        check.assert_not_called()
        assert 'the user serving it.' in caplog.text
        assert 'code signature' not in caplog.text

    def test_system_socket_still_gets_the_peer_check(
        self, fake, as_macos, at_system_socket
    ):
        with (
            mock.patch(f'{CD}.trust._peer_uid', return_value=foreign_uid()),
            mock.patch(f'{CD}.transport.check_code_signature') as check,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert 'runs as uid' in str(e.value)
        check.assert_not_called()
        assert fake.calls == []

    def test_home_link_to_the_system_socket_checks_it(
        self, fake, as_macos, at_system_socket, private_dir, monkeypatch
    ):
        # ~/.aws/credential-daemon.sock pointing at /var/run/credsd's
        # socket: the resolved path is the system socket.
        home = private_dir / 'h'
        (home / '.aws').mkdir(parents=True, mode=0o700)
        (home / '.aws' / 'credential-daemon.sock').symlink_to(fake.socket_path)
        monkeypatch.setenv('HOME', str(home))
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        with mock.patch(f'{CD}.transport.check_code_signature') as check:
            CredentialDaemonClient().store_keys(
                'keys.ci', 'AKID', 'SECRET', 'us-east-1'
            )
        check.assert_called_once()
        assert check.call_args.args[1] == fake.socket_path
        assert [method for method, _ in fake.calls] == ['credential/bootstrap']

    def test_link_in_place_of_the_system_folder_gets_the_per_user_rule(
        self, fake, as_macos, private_dir
    ):
        # A link put where the system socket's folder goes resolves
        # somewhere else, so that socket gets the per-user rule: the
        # caller's own folder and socket pass, where the system socket's
        # root-only rule would refuse them.
        (private_dir / 'credsd').symlink_to(os.path.dirname(fake.socket_path))
        system = {str(private_dir / 'credsd' / 'daemon.sock')}
        frameworks = FakeFrameworks()
        with (
            mock.patch(f'{CD}.trust.system_socket_paths', return_value=system),
            macos_system_rule(),
            self.frameworks(frameworks),
        ):
            CredentialDaemonClient(
                socket_path=str(private_dir / 'credsd' / 'daemon.sock')
            ).store_keys('keys.ci', 'AKID', 'SECRET', 'us-east-1')
        assert [method for method, _ in fake.calls] == ['credential/bootstrap']
        assert [c[0] for c in frameworks.calls].count('validity') == 1

    def test_peer_level_still_refuses_another_user(self, fake, as_macos):
        with (
            mock.patch(f'{CD}.trust._peer_uid', return_value=foreign_uid()),
            mock.patch(f'{CD}.transport.check_code_signature') as check,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                CredentialDaemonClient(
                    socket_path=fake.socket_path, checks=SocketChecks.PEER
                ).list_credentials()
        assert 'runs as uid' in str(e.value)
        check.assert_not_called()
        assert fake.calls == []

    @pytest.mark.skipif(is_macos, reason='not macOS')
    def test_not_checked_off_macos(self, fake):
        with mock.patch(f'{CD}.codesign._code_signature_status') as status:
            CredentialDaemonClient(
                socket_path=fake.socket_path
            ).list_credentials()
        status.assert_not_called()

    def test_peer_uid_is_checked_first(self, fake, as_macos):
        with (
            mock.patch(f'{CD}.trust._peer_uid', return_value=foreign_uid()),
            mock.patch(f'{CD}.codesign._code_signature_status') as status,
        ):
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                self.store(fake)
        assert 'runs as uid' in str(e.value)
        status.assert_not_called()


@pytest.mark.skipif(not is_macos, reason='macOS only')
@pytest.mark.real_code_signature
def test_real_check_refuses_this_python():
    # The real ctypes path: the other end of the socketpair is this test
    # process, a Python interpreter, which isn't the signed credential
    # daemon. Refused by the requirement, not by a failure to check.
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with a, b:
        with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
            check_code_signature(a, 'socketpair')
    assert 'isn\'t the signed credential daemon (OSStatus' in str(e.value)
