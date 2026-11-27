# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for aws logout with the credential daemon, run against the fake
credential daemon."""

import contextlib
import json
import os
import socket
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import (
    CLI_TAGS,
    CredentialDaemonClient,
    LogoutResult,
)
from botocore.exceptions import (
    CredentialDaemonTimeoutError,
    InvalidConfigError,
)
from botocore.session import Session
from botocore.utils import generate_login_cache_key

from awscli.customizations.login.logout import LogoutCommand
from tests import mock
from tests.functional.credential_daemon.login_helpers import (
    login,
    rendered_help,
)
from tests.utils.credential_daemon import (
    ACTIVE,
    KIND_IAM_USER,
    KIND_SSO,
    NO_SESSION,
    FakeCredentialDaemon,
    identity_credential_name,
)

OLD_SESSION = 'arn:aws:sts::123456789012:assumed-role/Admin/old'
LEFTOVER_PROFILES = {
    'dev': {'credential_daemon': 'dev', 'login_session': OLD_SESSION}
}


def write_session_file(cache_dir, name):
    path = cache_dir / f'{name}.json'
    path.write_text(
        json.dumps(
            {'accessToken': {'accessKeyId': 'AKID', 'secretAccessKey': 's'}}
        )
    )
    return path


def write_leftover(cache_dir):
    leftover = cache_dir / f'{generate_login_cache_key(OLD_SESSION)}.json'
    leftover.write_text('{}')
    return leftover


def logout(fake, profiles, profile='dev', all_=False, cache_dir='/nowhere'):
    session = mock.Mock()
    session.profile = profile
    session.full_config = {'profiles': profiles}
    session.get_config_variable.return_value = '/nonexistent/aws-file'
    socket_path = fake.socket_path if fake is not None else '/nowhere.sock'
    command = LogoutCommand(
        session,
        cache_dir=str(cache_dir),
        credential_daemon_client=CredentialDaemonClient(
            socket_path=socket_path, timeout=5
        ),
    )
    return command._run_main(Namespace(all=all_), mock.Mock())


_MISSING = object()


def _logout_reply(signed_out):
    """A ``CredentialDaemonClient._call`` whose credential/logout replies
    carry ``signed_out``, or leave it out for ``_MISSING``."""
    real_call = CredentialDaemonClient._call

    def call(client, method, *args, **kwargs):
        result = real_call(client, method, *args, **kwargs)
        if method == 'credential/logout':
            result = dict(result)
            result.pop('signed_out', None)
            if signed_out is not _MISSING:
                result['signed_out'] = signed_out
        return result

    return call


class TestOneProfile:
    def test_clears_the_session(self, fake, capsys):
        fake.seed('dev')
        assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 0
        credential = fake.credential('dev')
        assert credential.status == NO_SESSION
        assert credential.principal is not None
        assert (
            "Signed out of profile 'dev' in the credential daemon."
            in capsys.readouterr().out
        )

    def test_credential_daemon_in_the_credentials_file_is_ignored(
        self, fake, tmp_path, capsys
    ):
        # credential_daemon counts only in the config file, so this
        # profile signs out of files.
        fake.seed('dev')
        (tmp_path / 'config').write_text('[profile dev]\n')
        (tmp_path / 'credentials').write_text(
            '[dev]\ncredential_daemon = dev\n'
        )
        session = Session(profile='dev')
        session.set_config_variable('config_file', str(tmp_path / 'config'))
        session.set_config_variable(
            'credentials_file', str(tmp_path / 'credentials')
        )
        command = LogoutCommand(
            session,
            cache_dir=str(tmp_path),
            credential_daemon_client=CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            ),
        )
        assert command._run_main(Namespace(all=False), mock.Mock()) == 0
        assert fake.credential('dev').status == ACTIVE
        assert 'no login session found' in capsys.readouterr().err

    def test_names_the_other_profiles_it_signs_out(self, fake, capsys):
        fake.seed('login.shared')
        profiles = {
            'rem': {'credential_daemon': 'login.shared'},
            'dev': {'credential_daemon': 'login.shared'},
            'qa': {'credential_daemon': 'login.shared'},
            'other': {'credential_daemon': 'login.other'},
        }
        assert logout(fake, profiles, profile='rem') == 0
        assert (
            "Signed out of profile 'rem' in the credential daemon (also "
            "signed out: 'dev', 'qa'). Note"
        ) in capsys.readouterr().out

    def test_names_the_other_profiles_in_order(self, fake, capsys):
        fake.seed('login.shared')
        profiles = {
            'rem': {'credential_daemon': 'login.shared'},
            'zz': {'credential_daemon': 'login.shared'},
            'aa': {'credential_daemon': 'login.shared'},
        }
        assert logout(fake, profiles, profile='rem') == 0
        assert '(also signed out: \'aa\', \'zz\')' in capsys.readouterr().out

    def test_says_nothing_more_when_no_other_profile_shares_it(
        self, fake, capsys
    ):
        fake.seed('dev')
        profiles = {
            'dev': {'credential_daemon': 'dev'},
            'other': {'credential_daemon': 'login.other'},
        }
        assert logout(fake, profiles) == 0
        assert 'also signed out' not in capsys.readouterr().out

    def test_also_deletes_a_leftover_session_file(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev')
        leftover = write_leftover(tmp_path)
        assert logout(fake, LEFTOVER_PROFILES, cache_dir=tmp_path) == 0
        assert not leftover.exists()
        assert fake.credential('dev').status == NO_SESSION
        out = capsys.readouterr().out
        assert "Removed the cached login session file for profile 'dev'." in (
            out
        )
        assert "Signed out of profile 'dev'" in out

    def test_keeps_a_session_file_another_profile_names(
        self, fake, tmp_path, capsys
    ):
        # [profile other] has the same login_session, so an older CLI
        # signed in as it still reads the file: it stays, with a note.
        fake.seed('dev')
        leftover = write_leftover(tmp_path)
        profiles = dict(
            LEFTOVER_PROFILES, other={'login_session': OLD_SESSION}
        )
        assert logout(fake, profiles, cache_dir=tmp_path) == 0
        assert leftover.exists()
        assert fake.credential('dev').status == NO_SESSION
        captured = capsys.readouterr()
        assert 'Removed the cached login session file' not in captured.out
        assert (
            "Kept the cached login session file for profile 'dev', "
            "because 'other' still uses it.\n"
        ) in captured.err
        assert "Signed out of profile 'dev'" in captured.out

    def test_says_nothing_of_a_shared_session_file_that_isnt_there(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev')
        profiles = dict(
            LEFTOVER_PROFILES, other={'login_session': OLD_SESSION}
        )
        assert logout(fake, profiles, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert 'session file' not in captured.out + captured.err
        assert "Signed out of profile 'dev'" in captured.out

    def test_deletes_a_leftover_file_that_is_a_dangling_symlink(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev')
        leftover = tmp_path / f'{generate_login_cache_key(OLD_SESSION)}.json'
        leftover.symlink_to(tmp_path / 'gone.json')
        assert logout(fake, LEFTOVER_PROFILES, cache_dir=tmp_path) == 0
        assert not os.path.lexists(leftover)
        assert "Removed the cached login session file for profile 'dev'." in (
            capsys.readouterr().out
        )

    def test_deletes_the_leftover_file_when_the_daemon_has_no_credential(
        self, fake, tmp_path, capsys
    ):
        leftover = write_leftover(tmp_path)
        assert logout(fake, LEFTOVER_PROFILES, cache_dir=tmp_path) == 0
        assert not leftover.exists()
        captured = capsys.readouterr()
        assert 'Removed the cached login session file' in captured.out
        assert "has no credential named 'dev'" in captured.err

    def test_deletes_the_leftover_file_when_credential_daemon_is_down(
        self, tmp_path, capsys
    ):
        leftover = write_leftover(tmp_path)
        assert logout(None, LEFTOVER_PROFILES, cache_dir=tmp_path) == 1
        assert not leftover.exists()
        captured = capsys.readouterr()
        assert 'Removed the cached login session file' in captured.out
        assert "The session for profile 'dev' in the credential daemon " in (
            captured.err
        )
        assert "wasn't cleared" in captured.err
        assert (
            'Start the credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout\' again.'
        ) in captured.err

    def test_deletes_the_leftover_file_on_an_unknown_credential_daemon_error(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev')
        fake.fail_next('credential/logout', 'SOMETHING_NEW', 'Something new')
        leftover = write_leftover(tmp_path)
        assert logout(fake, LEFTOVER_PROFILES, cache_dir=tmp_path) == 1
        assert not leftover.exists()
        assert fake.credential('dev').status == ACTIVE
        captured = capsys.readouterr()
        assert 'Removed the cached login session file' in captured.out
        assert (
            "wasn't cleared: Something new (SOMETHING_NEW). Run 'aws logout' "
            'again.\n'
        ) in captured.err
        assert 'Start the credential daemon' not in captured.err

    def test_credential_gone_before_clear(self, fake, capsys):
        fake.seed('dev')
        fake.fail_next('credential/logout', 'CREDENTIAL_NOT_FOUND')
        assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 0
        assert "has no credential named 'dev'" in capsys.readouterr().err

    def test_still_signs_out_when_the_leftover_file_cant_be_deleted(
        self, fake, tmp_path, capsys
    ):
        # Exit 1: the plaintext session is still on disk.
        fake.seed('dev')
        leftover = write_leftover(tmp_path)
        with mock.patch('os.remove', side_effect=PermissionError('denied')):
            assert logout(fake, LEFTOVER_PROFILES, cache_dir=tmp_path) == 1
        assert fake.credential('dev').status == NO_SESSION
        captured = capsys.readouterr()
        assert (
            f"Couldn't remove the cached login session file {leftover}"
            in captured.err
        )
        assert 'Delete it by hand.' in captured.err
        assert "Signed out of profile 'dev'" in captured.out

    def test_file_cant_be_deleted_and_credential_daemon_is_down(
        self, tmp_path, capsys
    ):
        write_leftover(tmp_path)
        with mock.patch('os.remove', side_effect=PermissionError('denied')):
            assert logout(None, LEFTOVER_PROFILES, cache_dir=tmp_path) == 1
        err = capsys.readouterr().err
        assert "Couldn't remove the cached login session file" in err
        assert (
            'Start the credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout\' again.'
        ) in err

    def test_clears_without_reading_the_list(self, fake):
        # The credential daemon decides what it holds, so the list isn't
        # read.
        fake.seed('dev')
        assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 0
        assert [method for method, _ in fake.calls] == ['credential/logout']

    def test_access_keys_have_no_session_to_clear(self, fake, capsys):
        fake.seed('ci', kind=KIND_IAM_USER)
        assert (
            logout(fake, {'ci': {'credential_daemon': 'ci'}}, profile='ci')
            == 0
        )
        assert fake.credential('ci').status == ACTIVE
        # credsd refuses it: access keys have no sign-in to clear.
        assert ('credential/logout', {'credential': 'ci'}) in fake.calls
        captured = capsys.readouterr()
        assert captured.out == ''
        assert captured.err == (
            "warning: profile 'ci' has no sign-in session to clear in the "
            'credential daemon.\n'
        )

    @pytest.mark.parametrize('signed_out', [_MISSING, None, 'true'])
    def test_a_reply_without_a_true_or_false_signed_out_is_an_error(
        self, fake, capsys, signed_out
    ):
        # credsd always sends signed_out as true or false, so anything else
        # is a reply the CLI can't read, never a sign-out.
        fake.seed('dev')
        with mock.patch.object(
            CredentialDaemonClient, '_call', _logout_reply(signed_out)
        ):
            rc = logout(fake, {'dev': {'credential_daemon': 'dev'}})
        assert rc != 0
        captured = capsys.readouterr()
        assert 'Signed out' not in captured.out
        assert 'Traceback' not in captured.err
        assert "sign-out reply the CLI can't read" in captured.err

    def test_already_signed_out(self, fake, capsys):
        # credential/logout says there was no session to end.
        fake.seed('dev', status=NO_SESSION)
        assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 0
        assert ('credential/logout', {'credential': 'dev'}) in fake.calls
        captured = capsys.readouterr()
        assert 'Signed out' not in captured.out
        assert captured.err == (
            "warning: no login session found for profile 'dev' in the "
            'credential daemon\n'
        )

    def test_the_credential_daemon_tells_a_session_from_keys(
        self, fake, capsys
    ):
        # The list's kind is session_credentials for both, and
        # credential/logout decides.
        fake.seed('dev')
        fake.seed('ci', kind=KIND_IAM_USER)
        assert {row['kind'] for row in fake.list_rows()} == {
            'session_credentials'
        }
        profiles = {
            'dev': {'credential_daemon': 'dev'},
            'ci': {'credential_daemon': 'ci'},
        }
        assert logout(fake, profiles, profile='dev') == 0
        assert logout(fake, profiles, profile='ci') == 0
        assert fake.credential('dev').status == NO_SESSION
        assert fake.credential('ci').status == ACTIVE
        assert "profile 'ci' has no sign-in session to clear" in (
            capsys.readouterr().err
        )

    def test_no_such_credential(self, fake, capsys):
        assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 0
        assert "has no credential named 'dev'" in capsys.readouterr().err

    @pytest.mark.usefixtures('aws_dir', 'browser')
    def test_names_that_convert_the_same_stay_apart(self, fake):
        # Role names the credential daemon cleans up to the same text get
        # their own credentials.
        arn = 'arn:aws:sts::123456789012:assumed-role/'
        fake.next_principal = arn + 'me-corp/alice'
        login(fake, profile='a', storage_answer=True)
        fake.next_principal = arn + 'me@corp/alice'
        login(fake, profile='b', storage_answer=True)
        profiles = Session().full_config['profiles']
        plain = profiles['a']['credential_daemon']
        cleaned = profiles['b']['credential_daemon']
        assert plain == 'login.123456789012-role-me-corp'
        assert cleaned == identity_credential_name(
            'login.', arn + 'me@corp/alice'
        )
        assert cleaned != plain
        logout(fake, profiles, profile='b')
        assert fake.credential(cleaned).status == NO_SESSION
        assert fake.credential(plain).status == ACTIVE

    def test_credential_daemon_timeout_gets_the_start_hint(self, fake, capsys):
        # The SEP counts a timeout as NOT_RUNNING.
        fake.seed('dev')
        with mock.patch.object(
            CredentialDaemonClient,
            'logout',
            side_effect=CredentialDaemonTimeoutError(
                error_msg='The credential daemon didn\'t respond in time.'
            ),
        ):
            assert logout(fake, {'dev': {'credential_daemon': 'dev'}}) == 1
        assert (
            "wasn't cleared: The credential daemon didn't respond "
            "in time. Start the "
            'credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout\' again.'
        ) in capsys.readouterr().err

    def test_credential_daemon_not_running(self, capsys):
        assert logout(None, {'dev': {'credential_daemon': 'dev'}}) == 1
        captured = capsys.readouterr()
        assert captured.out == ''
        assert (
            'Start the credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout\' again.'
        ) in captured.err


class TestSsoProfileWithoutRole:
    """A profile with sso_session and neither sso_account_id nor
    sso_role_name keeps its aws login session in files, beside the
    session's credential_daemon that tools skip for it."""

    @pytest.mark.parametrize('name', ['sso.acme', 'login.ci'])
    def test_its_session_file_is_signed_out(
        self, fake, tmp_path, capsys, name
    ):
        fake.seed(name, kind=KIND_SSO)
        session_file = write_session_file(
            tmp_path, generate_login_cache_key(OLD_SESSION)
        )
        profiles = {
            'ci': {
                'sso_session': 'acme',
                'credential_daemon': name,
                'login_session': OLD_SESSION,
            }
        }
        assert logout(fake, profiles, 'ci', cache_dir=tmp_path) == 0
        assert not session_file.exists()
        # The daemon's credential is left alone.
        assert fake.calls == []
        assert 'aws sso logout' not in capsys.readouterr().err


class TestAll:
    def test_clears_the_clis_sessions_but_not_sso_ones(
        self, fake, tmp_path, capsys
    ):
        # Only credentials with the CLI's tags, and the rows' source says
        # which are SSO sessions, whatever they're named and whatever the
        # config says: aws sso logout signs those out.
        fake.seed('dev', tags=CLI_TAGS)
        fake.seed('custom-name', tags=dict(CLI_TAGS, team='pay'))
        fake.seed('ci', tags=CLI_TAGS, kind=KIND_IAM_USER)
        fake.seed('sso.corp', tags=CLI_TAGS, kind=KIND_SSO, principal=None)
        fake.seed('login.x', tags=CLI_TAGS, kind=KIND_SSO, principal=None)
        fake.seed('gone', tags=CLI_TAGS, status=NO_SESSION)
        fake.seed('other-tool')
        fake.seed('other-tagged', tags={'created-by': 'another-tool'})
        fake.seed('portal', kind=KIND_SSO, principal=None)
        session = mock.Mock()
        session.profile = None
        session.full_config = {
            'profiles': {
                'a': {'sso_session': 'corp', 'credential_daemon': 'sso.corp'},
            },
            'sso_sessions': {'corp': {}},
        }
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(
            session,
            cache_dir=str(tmp_path),
            credential_daemon_client=CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            ),
        )
        assert command._run_main(Namespace(all=True), mock.Mock()) == 0
        assert ('credential/list', {'tags': CLI_TAGS}) in fake.calls
        assert fake.credential('dev').status == NO_SESSION
        assert fake.credential('custom-name').status == NO_SESSION
        # Refused: access keys have no sign-in.
        assert fake.credential('ci').status == ACTIVE
        for name in (
            'sso.corp',
            'login.x',
            'other-tool',
            'other-tagged',
            'portal',
        ):
            assert fake.credential(name).status == ACTIVE
            assert (
                'credential/logout',
                {'credential': name},
            ) not in fake.calls
        out = capsys.readouterr().out
        assert 'Signed out of 2 sessions in the credential daemon.' in out

    def test_the_credential_daemon_tells_a_session_from_keys(
        self, fake, tmp_path
    ):
        # The credential daemon's list kind is session_credentials for both.
        fake.seed('dev', tags=CLI_TAGS)
        fake.seed('ci', tags=CLI_TAGS, kind=KIND_IAM_USER)
        assert {row['kind'] for row in fake.list_rows()} == {
            'session_credentials'
        }
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert fake.credential('dev').status == NO_SESSION
        assert fake.credential('ci').status == ACTIVE

    @pytest.mark.parametrize(
        'result, counted',
        [
            (LogoutResult(True, 'local_only'), True),
            (LogoutResult(False, 'none'), False),
        ],
    )
    def test_counts_a_logout_as_the_single_profile_path_does(
        self, fake, tmp_path, capsys, result, counted
    ):
        # signed_out: false means nothing was signed out, as it does for
        # aws logout --profile.
        fake.seed('dev', tags=CLI_TAGS)
        with mock.patch.object(
            CredentialDaemonClient, 'logout', return_value=result
        ):
            assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        out = capsys.readouterr().out
        line = 'Signed out of 1 session in the credential daemon.'
        assert (line in out) is counted

    def test_a_session_signed_in_without_a_creator_is_cleared(
        self, fake, tmp_path
    ):
        # A client that sends no creator still adds the CLI's tags after
        # the bootstrap, so aws logout --all clears its session.
        anonymous = CredentialDaemonClient(
            socket_path=fake.socket_path, timeout=5, creator=None
        )
        name = anonymous.bootstrap(
            {'type': 'aws_login', 'region': 'us-west-2'}, name_prefix='login.'
        )['credential']
        assert anonymous.mark_created_by_cli(name)
        assert 'creator' not in dict(fake.calls)['credential/bootstrap']
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert fake.credential(name).status == NO_SESSION

    def test_skips_a_refused_clear(self, fake, tmp_path, capsys):
        # Access keys: the credential daemon refuses to sign them out, and
        # the rest still are, with no error.
        fake.seed('ci', tags=CLI_TAGS, kind=KIND_IAM_USER)
        fake.seed('dev', tags=CLI_TAGS)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert fake.credential('ci').status == ACTIVE
        assert fake.credential('dev').status == NO_SESSION
        captured = capsys.readouterr()
        assert 'Signed out of 1 session in the credential daemon.' in (
            captured.out
        )
        assert captured.err == ''

    def test_clears_expired_sessions(self, fake, tmp_path, capsys):
        # An expired session may still hold a refresh token.
        fake.seed('dev', tags=CLI_TAGS)
        fake.expire('dev')
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert ('credential/logout', {'credential': 'dev'}) in fake.calls
        assert fake.credential('dev').status == NO_SESSION
        out = capsys.readouterr().out
        assert 'Signed out of 1 session in the credential daemon.' in out

    def test_a_daemon_sign_out_alone_skips_the_none_found_line(
        self, fake, tmp_path, capsys
    ):
        # No session files, one daemon session: saying none was found
        # would contradict the sign-out line.
        fake.seed('dev', tags=CLI_TAGS)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert captured.out == (
            'Signed out of 1 session in the credential daemon.\n'
        )
        assert captured.err == ''

    def test_session_files_alone_print_only_the_files_line(
        self, fake, tmp_path, capsys
    ):
        session_file = write_session_file(tmp_path, 'a')
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert not session_file.exists()
        captured = capsys.readouterr()
        assert captured.out == (
            'Removed 1 cached login credential. Note, any local developer '
            'tools that have already loaded access tokens may continue to '
            'use them until their expiration. Access tokens expire in 15 '
            'minutes.\n'
        )
        assert captured.err == ''

    def test_says_none_found_when_neither_has_a_session(
        self, fake, tmp_path, capsys
    ):
        fake.seed('ci', tags=CLI_TAGS, kind=KIND_IAM_USER)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert captured.out == 'No cached login session tokens found.\n'
        assert captured.err == ''

    def test_no_none_found_line_when_the_daemon_cant_be_checked(
        self, fake, tmp_path, capsys
    ):
        # The daemon may still hold sessions, so "none found" would
        # contradict the warning.
        fake.seed('dev', tags=CLI_TAGS)
        with mock.patch.object(
            CredentialDaemonClient,
            'list_credentials',
            side_effect=CredentialDaemonTimeoutError(error_msg='Timed out.'),
        ):
            assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert captured.out == ''
        assert "weren't checked" in captured.err

    def test_says_none_found_without_a_daemon(self, tmp_path, capsys):
        # Files mode, with no credential daemon: the output is as before.
        assert logout(None, {'dev': {}}, all_=True, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert captured.out == 'No cached login session tokens found.\n'
        assert captured.err == ''

    def test_daemon_down_is_quiet_without_daemon_profiles(
        self, tmp_path, capsys
    ):
        # A customer without the credential daemon gets no warning.
        assert logout(None, {'dev': {}}, all_=True, cache_dir=tmp_path) == 0
        assert capsys.readouterr().err == ''

    def test_a_home_link_to_nothing_is_quiet_without_daemon_profiles(
        self, tmp_path, monkeypatch, capsys
    ):
        # What other users have after an uninstall, or a container that
        # mounts ~/.aws but not the socket.
        aws_dir = tmp_path / '.aws'
        aws_dir.mkdir(mode=0o700)
        (aws_dir / 'credential-daemon.sock').symlink_to(tmp_path / 'gone')
        monkeypatch.setenv('HOME', str(tmp_path))
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        session = mock.Mock()
        session.profile = None
        session.full_config = {'profiles': {'dev': {}}}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(
            session,
            cache_dir=str(tmp_path),
            credential_daemon_client=CredentialDaemonClient(timeout=5),
        )
        assert command._run_main(Namespace(all=True), mock.Mock()) == 0
        assert capsys.readouterr().err == ''

    def test_a_hung_daemon_is_a_warning_without_daemon_profiles(
        self, fake, capsys
    ):
        # A session no profile names may stay in a daemon that doesn't
        # answer: --all says so, but scripts on machines that use the
        # daemon only for other tools don't fail.
        fake.seed('other-tool', tags=CLI_TAGS)
        with mock.patch.object(
            CredentialDaemonClient,
            'list_credentials',
            side_effect=CredentialDaemonTimeoutError(
                error_msg="The credential daemon didn't respond in time."
            ),
        ):
            assert logout(fake, {'dev': {}}, all_=True) == 0
        captured = capsys.readouterr()
        assert captured.out == ''
        assert captured.err == (
            "warning: sessions in the credential daemon weren't checked: The "
            "credential daemon didn't respond in time. No profile uses it. "
            'Start the credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            "Then run 'aws logout --all' again to clear them.\n"
        )
        assert fake.credential('other-tool').status == ACTIVE

    def test_a_stopped_daemon_is_a_warning_without_daemon_profiles(
        self, sock_dir, capsys
    ):
        # The socket file is still there, but nothing accepts on it.
        path = os.path.join(sock_dir, 's.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.close()
        session = mock.Mock()
        session.profile = 'dev'
        session.full_config = {'profiles': {'dev': {}}}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(
            session,
            cache_dir=sock_dir,
            credential_daemon_client=CredentialDaemonClient(
                socket_path=path, timeout=5
            ),
        )
        assert command._run_main(Namespace(all=True), mock.Mock()) == 0
        err = capsys.readouterr().err
        assert err.startswith(
            "warning: sessions in the credential daemon weren't checked: "
        )
        assert "No profile uses it." in err
        assert err.endswith("'aws logout --all' again to clear them.\n")
        assert "weren't cleared" not in err

    def test_a_stopped_daemon_fails_with_daemon_profiles(
        self, sock_dir, capsys
    ):
        path = os.path.join(sock_dir, 's.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.close()
        session = mock.Mock()
        session.profile = 'dev'
        session.full_config = {'profiles': {'dev': {'credential_daemon': 'd'}}}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(
            session,
            cache_dir=sock_dir,
            credential_daemon_client=CredentialDaemonClient(
                socket_path=path, timeout=5
            ),
        )
        assert command._run_main(Namespace(all=True), mock.Mock()) == 1
        err = capsys.readouterr().err
        assert "Sessions in the credential daemon weren't cleared" in err
        assert 'warning' not in err

    def test_a_hung_daemon_doesnt_stop_the_files_sweep(
        self, fake, tmp_path, capsys
    ):
        session_file = write_session_file(tmp_path, 'a')
        with mock.patch.object(
            CredentialDaemonClient,
            'list_credentials',
            side_effect=CredentialDaemonTimeoutError(error_msg='Timed out.'),
        ):
            assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert not session_file.exists()
        captured = capsys.readouterr()
        assert 'Removed 1 cached login credential.' in captured.out
        assert "weren't checked: Timed out." in captured.err

    def test_credential_daemon_down_fails_with_credential_daemon_profiles(
        self, tmp_path, capsys
    ):
        session_file = write_session_file(tmp_path, 'a')
        profiles = {'dev': {'credential_daemon': 'dev'}}
        assert logout(None, profiles, all_=True, cache_dir=tmp_path) == 1
        assert not session_file.exists()
        captured = capsys.readouterr()
        assert 'Removed 1 cached login credential.' in captured.out
        assert "Sessions in the credential daemon weren't cleared" in (
            captured.err
        )
        assert (
            'Start the credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout --all\' again.'
        ) in captured.err

    def test_credential_daemon_timeout_gets_the_start_hint(self, fake, capsys):
        fake.seed('dev', tags=CLI_TAGS)
        profiles = {'dev': {'credential_daemon': 'dev'}}
        with mock.patch.object(
            CredentialDaemonClient,
            'list_credentials',
            side_effect=CredentialDaemonTimeoutError(
                error_msg='The credential daemon didn\'t respond in time.'
            ),
        ):
            assert logout(fake, profiles, all_=True) == 1
        assert (
            "weren't cleared: The credential daemon didn't "
            "respond in time. Start the "
            'credential daemon, or install it with \'aws configure '
            'credential-daemon install\', link its socket with \'aws '
            'configure credential-daemon link\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET. '
            'Then run \'aws logout --all\' again.'
        ) in capsys.readouterr().err

    def test_credential_daemon_error_warns_without_credential_daemon_profiles(
        self, fake, tmp_path, capsys
    ):
        # The credential daemon may hold sessions no profile names, so it's
        # a warning.
        fake.seed('dev', tags=CLI_TAGS)
        fake.fail_next('credential/list', 'INTERNAL', 'Broken')
        assert logout(fake, {'dev': {}}, all_=True, cache_dir=tmp_path) == 0
        assert capsys.readouterr().err == (
            "warning: sessions in the credential daemon weren't checked: "
            "Broken (INTERNAL). No profile uses it. Run 'aws logout --all' "
            'again to clear them.\n'
        )

    def test_credential_daemon_error_fails_with_credential_daemon_profiles(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev', tags=CLI_TAGS)
        fake.fail_next('credential/list', 'INTERNAL', 'Broken')
        profiles = {'dev': {'credential_daemon': 'dev'}}
        assert logout(fake, profiles, all_=True, cache_dir=tmp_path) == 1
        assert capsys.readouterr().err == (
            "Sessions in the credential daemon weren't cleared: "
            "Broken (INTERNAL). Run 'aws logout --all' again.\n"
        )

    def test_the_warning_strips_control_characters(
        self, fake, tmp_path, capsys
    ):
        fake.fail_next('credential/list', 'INTERNAL', 'Bro\x1b[2Jken')
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        err = capsys.readouterr().err
        assert '\x1b' not in err
        assert "weren't checked: Bro[2Jken (INTERNAL)." in err

    def test_config_that_doesnt_validate_is_reported(
        self, fake, tmp_path, capsys
    ):
        # credsd refuses credential/list until the caller's configuration
        # validates again, so the sessions are left, not "none found". No
        # profile uses the daemon, so it's a warning.
        fake.seed('dev', tags=CLI_TAGS)
        fake.set_config_invalid('bad tag key')
        assert logout(fake, {'dev': {}}, all_=True, cache_dir=tmp_path) == 0
        captured = capsys.readouterr()
        assert 'No cached login session tokens found' not in captured.out
        assert (
            "warning: sessions in the credential daemon weren't checked: "
            'caller configuration does not validate: bad tag key; fix it, '
            'then run: creds revalidate (CONFIG_INVALID). No profile uses '
            "it. Run 'aws logout --all' again to clear them.\n"
        ) in captured.err
        assert 'Traceback' not in captured.err
        assert fake.credential('dev').status == ACTIVE

    def test_a_failed_clear_doesnt_stop_the_others(
        self, fake, tmp_path, capsys
    ):
        fake.seed('a', tags=CLI_TAGS)
        fake.seed('b', tags=CLI_TAGS)
        fake.seed('c', tags=CLI_TAGS)
        fake.fail_next('credential/logout', 'INTERNAL', 'Broken')
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 1
        statuses = sorted(fake.credential(n).status for n in 'abc')
        assert statuses == sorted([ACTIVE, NO_SESSION, NO_SESSION])
        captured = capsys.readouterr()
        assert 'Signed out of 2 sessions' in captured.out
        assert (
            "weren't cleared: Broken (INTERNAL). Run 'aws logout --all' again.\n"
        ) in captured.err

    def test_a_session_gone_before_clear_isnt_a_failure(
        self, fake, tmp_path, capsys
    ):
        # Nor is it counted: this command didn't sign it out, as in aws sso
        # logout.
        fake.seed('a', tags=CLI_TAGS)
        fake.seed('b', tags=CLI_TAGS)
        fake.fail_next('credential/logout', 'CREDENTIAL_NOT_FOUND')
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert (
            'Signed out of 1 session in the credential daemon.\n'
            in capsys.readouterr().out
        )

    @pytest.mark.parametrize(
        'source', ['unsupported', 'aws_roles_anywhere', 'static_secret']
    )
    def test_other_sources_are_left_alone(
        self, fake, tmp_path, capsys, source
    ):
        # The credential daemon refuses to sign out anything that isn't a
        # sign-in, even with the CLI's tags: it's kept, and that's no
        # failure.
        fake.seed('other', tags=CLI_TAGS, kind=source)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert fake.credential('other').status == ACTIVE
        assert 'credential/remove' not in [m for m, _ in fake.calls]
        captured = capsys.readouterr()
        assert 'Signed out of' not in captured.out
        assert captured.err == ''


def socket_appears_after_first_lookup(first, then):
    """A socket lookup that finds ``first``, then ``then`` ever after, as
    if a per-user daemon started mid-command."""
    paths = [first]

    def lookup():
        path = paths[-1]
        paths.append(then)
        return path

    return mock.patch(
        'botocore.credential_daemon.client.default_socket_path', lookup
    )


def test_all_stays_on_the_daemon_it_listed(tmp_path):
    # The clears go to the daemon whose rows the CLI checked, even if the
    # lookup finds another socket between the list and the clears.
    with FakeCredentialDaemon() as listed, FakeCredentialDaemon() as other:
        listed.seed('dev', tags=CLI_TAGS)
        other.seed('dev', tags=CLI_TAGS)
        session = mock.Mock()
        session.profile = None
        session.full_config = {'profiles': {}}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(session, cache_dir=str(tmp_path))
        with socket_appears_after_first_lookup(
            listed.socket_path, other.socket_path
        ):
            command._run_main(Namespace(all=True), mock.Mock())
        assert listed.credential('dev').status == NO_SESSION
        assert other.credential('dev').status == ACTIVE
        assert other.calls == []


class TestSSOSessionsSSODidntEnd:
    """credsd ends an SSO sign-in at SSO itself. When that fails, the
    session here is still signed out, and aws logout says the SSO session
    may still be live. Only --profile signs out an SSO session: --all
    leaves them to aws sso logout."""

    PROFILES = {'dev': {'credential_daemon': 'acme'}}

    @pytest.mark.parametrize('provider', ['ended', 'token_rejected'])
    def test_no_warning_when_sso_took_the_sign_out(
        self, fake, capsys, provider
    ):
        fake.seed('acme', kind=KIND_SSO)
        if provider != 'ended':
            fake.set_sso_logout(provider)
        assert logout(fake, self.PROFILES) == 0
        captured = capsys.readouterr()
        assert "Signed out of profile 'dev'" in captured.out
        assert captured.err == ''

    def test_no_warning_for_a_local_only_sign_out(
        self, fake, tmp_path, capsys
    ):
        fake.seed('dev', tags=CLI_TAGS)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert capsys.readouterr().err == ''

    def test_all_leaves_sso_sessions_without_a_warning(
        self, fake, tmp_path, capsys
    ):
        fake.seed('acme', tags=CLI_TAGS, kind=KIND_SSO)
        fake.set_sso_logout('failed', access_token_expires_at=None)
        assert logout(fake, {}, all_=True, cache_dir=tmp_path) == 0
        assert fake.credential('acme').status == ACTIVE
        assert capsys.readouterr().err == ''


class TestHelp:
    def test_describes_the_credential_daemon(self):
        text = rendered_help('logout')
        assert 'Clears cached login credentials' in text
        assert (
            'signs the profile\'s session out of the credential daemon' in text
        )
        assert (
            'signs out every session the CLI created in the credential '
            'daemon.' in text
        )
        assert 'aws sso logout' not in text
        assert "Other tools' sessions are left alone." in text


class TestWhereTheCredentialDaemonDoesntRun:
    def test_logout_all_doesnt_dial(self, tmp_path, capsys):
        # Such as Windows, whatever AWS_CREDENTIAL_DAEMON_SOCKET says:
        # nothing looks the socket up.
        session = mock.Mock()
        session.profile = 'dev'
        session.full_config = {'profiles': {'dev': {'region': 'us-west-2'}}}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(session, cache_dir=str(tmp_path))
        with (
            mock.patch(
                'botocore.credential_daemon.host.Host.runs_credential_daemon',
                return_value=False,
            ),
            mock.patch(
                'botocore.credential_daemon.client.default_socket_path',
                side_effect=InvalidConfigError(error_msg='not a pipe'),
            ),
            mock.patch(
                'awscli.customizations.credential_daemon.command.command_client'
            ) as command_client,
        ):
            rc = command._run_main(Namespace(all=True), mock.Mock())
        assert rc == 0
        command_client.assert_not_called()
        captured = capsys.readouterr()
        assert (captured.out, captured.err) == (
            'No cached login session tokens found.\n',
            '',
        )

    @pytest.mark.parametrize(
        'socket_error',
        [None, InvalidConfigError(error_msg='not a pipe')],
        ids=['no-socket-variable', 'invalid-socket-variable'],
    )
    def test_logout_all_warns_about_daemon_profiles_and_exits_0(
        self, tmp_path, capsys, socket_error
    ):
        # A config copied from a Mac: running logout --all again can never
        # help, so it's a warning, not an error, whatever
        # AWS_CREDENTIAL_DAEMON_SOCKET says.
        session = mock.Mock()
        session.profile = 'dev'
        session.full_config = {
            'profiles': {
                'dev': {'credential_daemon': 'login.dev'},
                'qa': {'credential_daemon': 'login.qa'},
                'plain': {'region': 'us-west-2'},
            }
        }
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(session, cache_dir=str(tmp_path))
        patches = [
            mock.patch(
                'botocore.credential_daemon.host.Host.runs_credential_daemon',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.credential_daemon.command.command_client'
            ),
        ]
        if socket_error is not None:
            patches.append(
                mock.patch(
                    'botocore.credential_daemon.client.default_socket_path',
                    side_effect=socket_error,
                )
            )
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            rc = command._run_main(Namespace(all=True), mock.Mock())
        assert rc == 0
        # command_client: nothing dials.
        mocks[1].assert_not_called()
        captured = capsys.readouterr()
        assert captured.out == 'No cached login session tokens found.\n'
        assert captured.err == (
            "warning: profiles 'dev' and 'qa' use the credential daemon, "
            "which isn't available on this platform; their credentials "
            "can't be cleared here.\n"
        )

    @pytest.mark.parametrize(
        'socket_error',
        [None, InvalidConfigError(error_msg='not a pipe')],
        ids=['no-socket-variable', 'invalid-socket-variable'],
    )
    def test_logout_of_one_profile_warns_and_exits_0(
        self, tmp_path, capsys, socket_error
    ):
        # As for logout --all: a config copied from a Mac can't be signed
        # out here, whatever AWS_CREDENTIAL_DAEMON_SOCKET says.
        session = mock.Mock()
        session.profile = 'dev'
        session.full_config = {
            'profiles': {'dev': {'credential_daemon': 'login.dev'}}
        }
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        command = LogoutCommand(session, cache_dir=str(tmp_path))
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch(
                    'botocore.credential_daemon.host.Host.runs_credential_daemon',
                    return_value=False,
                )
            )
            command_client = stack.enter_context(
                mock.patch(
                    'awscli.customizations.credential_daemon.command.'
                    'command_client'
                )
            )
            if socket_error is not None:
                stack.enter_context(
                    mock.patch(
                        'botocore.credential_daemon.client.default_socket_path',
                        side_effect=socket_error,
                    )
                )
            rc = command._run_main(Namespace(all=False), mock.Mock())
        assert rc == 0
        command_client.assert_not_called()
        captured = capsys.readouterr()
        assert (captured.out, captured.err) == (
            '',
            "warning: profile 'dev' uses the credential daemon, which isn't "
            "available on this platform; its credentials can't be cleared "
            "here.\n",
        )
