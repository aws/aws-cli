# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import botocore.session
import pytest
from botocore.exceptions import CredentialDaemonNotRunningError

from awscli.customizations.credential_daemon.storage.policy import (
    DecisionSource,
    Storage,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.login.credential_daemon import DaemonSignIn
from awscli.customizations.login.login import FilesSignIn
from awscli.customizations.login.signup import SignupCommand
from tests import mock
from tests.markers import skip_if_windows


@pytest.fixture(autouse=True)
def login_cache_dir(tmp_path, monkeypatch):
    # The session-file checks look in the login cache, so keep them off the
    # real ~/.aws.
    monkeypatch.setenv(
        'AWS_LOGIN_CACHE_DIRECTORY', str(tmp_path / 'login-cache')
    )


def daemon_client(socket_path=__file__):
    """A mock client whose socket has something at it, as a credential
    daemon that's there."""
    return mock.Mock(socket_path=socket_path)


def make_session(tmp_path, config=''):
    config_file = tmp_path / 'config'
    config_file.write_text(config)
    session = botocore.session.Session()
    session.set_config_variable('config_file', str(config_file))
    session.set_config_variable(
        'credentials_file', str(tmp_path / 'credentials')
    )
    return session, config_file


class TestFilesSignInCheck:
    def test_access_keys_refuse_a_session_in_files(self, tmp_path):
        session, _ = make_session(
            tmp_path, '[profile dev]\naws_access_key_id = AKIA\n'
        )
        with pytest.raises(ConfigurationError, match='Access Key'):
            FilesSignIn(session, None).check('dev', 'login')

    def test_a_profile_without_keys_passes(self, tmp_path):
        session, _ = make_session(
            tmp_path, '[profile dev]\nregion = us-west-2\n'
        )
        FilesSignIn(session, None).check('dev', 'login')


class TestSignupStorage:
    def test_signup_chooses_files_without_asking(self, tmp_path):
        session, _ = make_session(tmp_path)
        choice = SignupCommand(session)._choose_storage('dev', None, None)
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )


class TestCheckReady:
    def test_only_a_profile_that_stores_in_the_daemon_is_checked(
        self, tmp_path
    ):
        client = mock.Mock()
        session, _ = make_session(
            tmp_path,
            '[profile in]\ncredential_storage = daemon\n'
            '[profile out]\ncredential_storage = file\n',
        )
        daemon = DaemonSignIn(session, None, client=client)
        daemon.check_ready_if_stored('out')
        client.probe.assert_not_called()
        # As where the credential daemon runs, Windows too.
        with mock.patch(
            'awscli.customizations.credential_daemon.command.'
            'credential_daemon_runs_here',
            return_value=True,
        ):
            daemon.check_ready_if_stored('in')
        client.probe.assert_called_once_with()


class TestSessionMove:
    def moved(self, tmp_path, config, before):
        session, config_file = make_session(tmp_path, config)
        move = FilesSignIn(session, None).leave('dev', before)
        lines = move.release()
        return move, move, lines, config_file.read_text()

    def test_a_profile_with_no_session_file_to_move_is_left_alone(
        self, tmp_path
    ):
        config = '[profile dev]\ncredential_storage = daemon\n'
        _, move, lines, written = self.moved(tmp_path, config, {})
        assert written == config
        assert lines == []
        assert not move.keeps_login_session

    def test_an_older_cli_without_a_file_lets_the_sign_in_drop_login_session(
        self, tmp_path
    ):
        config = (
            '[profile dev]\ncredential_storage = daemon\n'
            'credential_daemon = login.dev\nlogin_session = arn:x\n'
        )
        before = {'credential_daemon': 'login.dev', 'login_session': 'arn:x'}
        _, move, lines, written = self.moved(tmp_path, config, before)
        # The sign-in writes it with credential_daemon, so nothing moves here.
        assert not move.keeps_login_session
        assert lines == []
        assert written == config

    def test_the_first_move_deletes_the_file_then_login_session(
        self, tmp_path
    ):
        config = (
            '[profile dev]\ncredential_daemon = login.dev\n'
            'login_session = arn:x\n'
        )
        with mock.patch(
            'awscli.customizations.login.utils.delete_session_file',
            return_value=True,
        ) as delete:
            _, move, lines, written = self.moved(
                tmp_path, config, {'login_session': 'arn:x'}
            )
        delete.assert_called_once()
        assert move.keeps_login_session
        assert 'login_session' not in written
        assert 'deleted its file' in lines[0]
        assert move.exit_code is None

    def test_a_file_that_cant_be_deleted_sets_the_exit_code(
        self, tmp_path, capsys
    ):
        config = '[profile dev]\nlogin_session = arn:x\n'
        with mock.patch(
            'awscli.customizations.login.utils.delete_session_file',
            side_effect=PermissionError('denied'),
        ):
            _, move, lines, written = self.moved(
                tmp_path, config, {'login_session': 'arn:x'}
            )
        assert 'login_session = arn:x' in written
        assert "wasn't deleted" in lines[0]
        assert "couldn't delete the session file" in capsys.readouterr().err
        assert move.exit_code == 1


class TestMoveToFiles:
    def test_a_profile_not_in_the_daemon_moves_without_asking(self, tmp_path):
        session, _ = make_session(tmp_path, '[profile dev]\nregion = x\n')
        leaving = DaemonSignIn(session, None, client=mock.Mock()).leave('dev')
        values = leaving.values_to_clear()
        assert values == {}

    @skip_if_windows
    def test_the_credential_the_profile_left_is_dropped_with_the_write(
        self, tmp_path
    ):
        client = daemon_client()
        client.list_credentials.return_value = []
        session, _ = make_session(
            tmp_path,
            '[profile dev]\ncredential_daemon = login.dev\n',
        )
        leaving = DaemonSignIn(session, None, client=client).leave('dev')
        values = leaving.values_to_clear()
        assert values == {'credential_daemon': None}
        leaving.release()
        client.logout.assert_called_once_with('login.dev')
        assert leaving.exit_code is None

    @skip_if_windows
    def test_a_clear_that_fails_sets_the_exit_code(self, tmp_path, capsys):
        client = daemon_client()
        client.list_credentials.return_value = []
        client.logout.side_effect = CredentialDaemonNotRunningError(
            error_msg='not running'
        )
        session, _ = make_session(
            tmp_path,
            '[profile dev]\ncredential_daemon = login.dev\n',
        )
        leaving = DaemonSignIn(session, None, client=client).leave('dev')
        leaving.release()
        assert leaving.exit_code == 1
        assert (
            "but the copy in the credential daemon wasn't cleared: not "
            "running. It's still there as credential 'login.dev'."
        ) in capsys.readouterr().err

    @skip_if_windows
    def test_an_absent_daemon_isnt_asked_to_clear(self, tmp_path, capsys):
        # Nothing at the socket, such as after an uninstall: nothing is
        # sent, and the move back still works.
        client = daemon_client(str(tmp_path / 'missing.sock'))
        session, _ = make_session(
            tmp_path,
            '[profile dev]\ncredential_daemon = login.dev\n',
        )
        leaving = DaemonSignIn(session, None, client=client).leave('dev')
        leaving.release()
        assert not client.logout.called
        assert leaving.exit_code is None
        captured = capsys.readouterr()
        assert captured.out == ''
        assert captured.err == (
            'note: no credential daemon is running at '
            f"{tmp_path / 'missing.sock'}, so "
            "its old copy of this profile's credential wasn't cleared. "
            'If the credential daemon runs elsewhere (for example, on the '
            'host of this container), '
            "clear credential 'login.dev' there.\n"
        )

    def test_a_platform_without_the_daemon_warns(self, tmp_path, capsys):
        client = daemon_client()
        session, _ = make_session(
            tmp_path,
            '[profile dev]\ncredential_daemon = login.dev\n',
        )
        leaving = DaemonSignIn(session, None, client=client).leave('dev')
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            leaving.release()
        assert not client.logout.called
        assert leaving.exit_code is None
        err = capsys.readouterr().err
        assert err.startswith("warning: profile 'dev' moved to ")
        assert err.endswith(
            ". Its copy in the credential daemon (credential 'login.dev') "
            "can't be cleared on this platform; clear it on the machine "
            'where the credential daemon runs.\n'
        )
