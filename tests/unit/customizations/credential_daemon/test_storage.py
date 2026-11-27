# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import inspect
import os
import sys

import botocore.session
import pytest
from botocore.credential_daemon import (
    DEFAULT_TIMEOUT,
    CredentialDaemonClient,
    HomeSocketPath,
)
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonTimeoutError,
    InvalidConfigError,
)

from awscli.compat import compat_shell_quote
from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
    StorageChoice,
    known_decision,
    stores_in_credential_daemon,
)
from awscli.customizations.credential_daemon.storage.kinds import (
    CredentialKind,
)
from awscli.customizations.credential_daemon.storage.policy import (
    DAEMON,
    FILE,
    DecisionSource,
    Storage,
    StorageDecision,
    decide_storage,
)
from awscli.customizations.credential_daemon.storage.presence import (
    Presence,
    credential_daemon_absent,
    credential_daemon_runs_here,
    detect_presence,
)
from awscli.customizations.credential_daemon.storage.profiles import (
    resolve_credential_storage,
)
from awscli.customizations.exceptions import ConfigurationError
from tests import mock
from tests.markers import skip_if_windows

# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'

CHOOSER = 'awscli.customizations.credential_daemon.storage.chooser'


def make_session(profiles=None, sso_sessions=None, files=None):
    """A session with these profiles. ``files`` maps ``config_file`` and
    ``credentials_file`` to paths. By default no file exists."""
    session = mock.Mock()
    session.full_config = {
        'profiles': profiles or {},
        'sso_sessions': sso_sessions or {},
    }
    if files is None:
        session.get_config_variable.return_value = '/nonexistent/aws-file'
    else:
        session.get_config_variable.side_effect = files.get
    return session


def real_session(tmp_path, config, credentials=None):
    """A botocore session that reads these config and credentials files."""
    config_file = tmp_path / 'config'
    config_file.write_text(config)
    credentials_file = tmp_path / 'credentials'
    if credentials is not None:
        credentials_file.write_text(credentials)
    session = botocore.session.Session()
    session.set_config_variable('config_file', str(config_file))
    session.set_config_variable('credentials_file', str(credentials_file))
    return session


SSO_PROFILES = {
    'admin': {
        'sso_session': 'acme',
        'sso_account_id': '111111111111',
        'sso_role_name': 'Admin',
        'credential_storage': 'daemon',
    },
    'legacy': {
        'sso_start_url': 'https://acme.awsapps.com/start',
        'sso_region': 'us-east-1',
        'sso_account_id': '111111111111',
        'sso_role_name': 'Admin',
        'credential_storage': 'daemon',
    },
}
# An SSO profile's account and role. One without them has only a token,
# and tools skip credential_daemon for it (TestSsoProfileWithoutRole).
ROLE = {'sso_account_id': '111111111111', 'sso_role_name': 'Admin'}


class TestResolveCredentialStorage:
    def test_no_answer_yet(self):
        session = make_session({'dev': {'region': 'us-west-2'}})
        assert resolve_credential_storage(session, 'dev', environ={}) is None

    def test_missing_profile_has_no_answer(self):
        session = make_session()
        assert resolve_credential_storage(session, 'new', environ={}) is None

    @pytest.mark.parametrize('value', [DAEMON, FILE])
    def test_profile_answer(self, value):
        session = make_session({'dev': {'credential_storage': value}})
        assert resolve_credential_storage(session, 'dev', environ={}) == value

    def test_env_var_overrides_the_answer(self):
        session = make_session({'dev': {'credential_storage': 'daemon'}})
        environ = {'AWS_CREDENTIAL_STORAGE': 'file'}
        assert resolve_credential_storage(session, 'dev', environ) == FILE

    def test_env_var_applies_without_an_answer(self):
        session = make_session({'dev': {}})
        environ = {'AWS_CREDENTIAL_STORAGE': 'daemon'}
        assert resolve_credential_storage(session, 'dev', environ) == DAEMON

    @pytest.mark.parametrize('value', ['', ' ', '\t\n'])
    def test_empty_or_blank_env_var_is_ignored(self, value):
        session = make_session({'dev': {'credential_storage': 'daemon'}})
        environ = {'AWS_CREDENTIAL_STORAGE': value}
        assert resolve_credential_storage(session, 'dev', environ) == DAEMON

    @pytest.mark.parametrize('value', ['', ' '])
    def test_empty_or_blank_env_var_without_an_answer(self, value):
        session = make_session({'dev': {}})
        environ = {'AWS_CREDENTIAL_STORAGE': value}
        assert resolve_credential_storage(session, 'dev', environ) is None

    def test_reads_os_environ_by_default(self):
        session = make_session({'dev': {}})
        with mock.patch.dict('os.environ', {'AWS_CREDENTIAL_STORAGE': 'file'}):
            assert resolve_credential_storage(session, 'dev') == FILE

    def test_values_ignore_case_and_spaces(self):
        session = make_session({'dev': {'credential_storage': ' Daemon '}})
        assert resolve_credential_storage(session, 'dev', environ={}) == DAEMON

    def test_invalid_profile_value(self):
        session = make_session({'dev': {'credential_storage': 'yes'}})
        with pytest.raises(ConfigurationError) as e:
            resolve_credential_storage(session, 'dev', environ={})
        assert '"yes"' in str(e.value)
        assert 'profile "dev"' in str(e.value)

    @pytest.mark.parametrize('value', ['y\x1b[2Kes', {'x': 'y'}])
    def test_invalid_value_strips_control_characters(self, value):
        session = make_session({'d\x1bev': {'credential_storage': value}})
        with pytest.raises(ConfigurationError) as e:
            resolve_credential_storage(session, 'd\x1bev', environ={})
        assert '\x1b' not in str(e.value)
        assert 'profile ' in str(e.value)
        assert 'dev' in str(e.value)

    def test_invalid_env_value(self):
        session = make_session({'dev': {}})
        environ = {'AWS_CREDENTIAL_STORAGE': 'keychain'}
        with pytest.raises(ConfigurationError) as e:
            resolve_credential_storage(session, 'dev', environ)
        assert 'AWS_CREDENTIAL_STORAGE' in str(e.value)

    @pytest.mark.parametrize('value', [DAEMON, FILE])
    def test_no_profile_selected_reads_the_default_profile(self, value):
        session = make_session({'default': {'credential_storage': value}})
        assert resolve_credential_storage(session, None, environ={}) == value

    def test_default_profile_is_not_inherited(self):
        session = make_session(
            {'default': {'credential_storage': 'daemon'}, 'dev': {}}
        )
        assert resolve_credential_storage(session, 'dev', environ={}) is None

    def test_sso_profile_uses_its_own_answer(self):
        # The answer is read from the profile, never its sso-session.
        session = make_session(
            SSO_PROFILES, {'acme': {'credential_storage': 'file'}}
        )
        assert resolve_credential_storage(session, 'admin', environ={}) == (
            DAEMON
        )

    def test_sso_profile_without_sso_session_uses_the_profile(self):
        session = make_session(SSO_PROFILES)
        result = resolve_credential_storage(session, 'legacy', environ={})
        assert result == DAEMON

    def test_the_credentials_file_does_not_override_the_answer(self, tmp_path):
        # aws configure set writes credential_storage to the config file,
        # so a value in the credentials file never counts.
        session = real_session(
            tmp_path,
            '[profile dev]\ncredential_storage = daemon\n',
            '[dev]\ncredential_storage = file\n',
        )
        assert resolve_credential_storage(session, 'dev', environ={}) == (
            DAEMON
        )

    def test_an_answer_only_in_the_credentials_file_is_ignored(self, tmp_path):
        session = real_session(
            tmp_path, '[profile dev]\n', '[dev]\ncredential_storage = file\n'
        )
        assert resolve_credential_storage(session, 'dev', environ={}) is None

    def test_an_indented_value_is_a_config_error(self, tmp_path):
        # The config parser reads an indented line after the key as a
        # dict.
        session = real_session(
            tmp_path, '[profile dev]\ncredential_storage =\n  foo = bar\n'
        )
        with pytest.raises(ConfigurationError) as e:
            resolve_credential_storage(session, 'dev', environ={})
        assert 'profile "dev"' in str(e.value)
        assert 'single value' in str(e.value)


class TestDecideStorage:
    @pytest.mark.parametrize(
        'env_value, section_value, has_credential_daemon, expected',
        [
            ('daemon', 'file', False, (Storage.DAEMON, DecisionSource.ENV)),
            (' File ', None, True, (Storage.FILE, DecisionSource.ENV)),
            ('', 'daemon', False, (Storage.DAEMON, DecisionSource.SAVED)),
            (None, 'FILE', True, (Storage.FILE, DecisionSource.SAVED)),
            (' ', None, True, (Storage.DAEMON, DecisionSource.PROFILE)),
            (None, None, False, (None, None)),
        ],
    )
    def test_decides_in_order(
        self, env_value, section_value, has_credential_daemon, expected
    ):
        decision = decide_storage(
            env_value, section_value, "profile 'dev'", has_credential_daemon
        )
        assert decision == StorageDecision(*expected)

    def test_a_bad_variable_fails_before_the_setting(self):
        with pytest.raises(ConfigurationError) as e:
            decide_storage('x', 'also bad', "profile 'dev'", False)
        assert 'AWS_CREDENTIAL_STORAGE' in str(e.value)

    def test_a_bad_setting_names_where(self):
        with pytest.raises(ConfigurationError) as e:
            decide_storage(None, 'x', "profile 'dev'", False)
        assert "credential_storage in profile 'dev'" in str(e.value)

    def test_values_are_the_settings(self):
        assert [s.value for s in Storage] == [DAEMON, FILE]


class TestKnownDecision:
    def test_credential_daemon_counts_without_an_answer(self):
        session = make_session({'dev': {'credential_daemon': 'x'}})
        assert known_decision(session, 'dev', {}) == StorageDecision(
            Storage.DAEMON, DecisionSource.PROFILE
        )

    def test_the_answer_wins(self):
        session = make_session(
            {'dev': {'credential_daemon': 'x', 'credential_storage': 'file'}}
        )
        assert known_decision(session, 'dev', {}) == StorageDecision(
            Storage.FILE, DecisionSource.SAVED
        )

    def test_nothing_known(self):
        session = make_session({'dev': {}})
        assert known_decision(session, 'dev', {}) == StorageDecision(
            None, None
        )


class TestStoresInCredentialDaemon:
    @pytest.mark.parametrize(
        'profile, expected',
        [
            ({'credential_storage': 'daemon'}, True),
            ({'credential_storage': 'file'}, False),
            ({'credential_daemon': 'keys.dev'}, True),
            (
                {
                    'credential_daemon': 'keys.dev',
                    'credential_storage': 'file',
                },
                False,
            ),
            # No answer yet: the storage question checks the daemon itself.
            ({'region': 'us-west-2'}, False),
        ],
    )
    def test_profile(self, profile, expected):
        session = make_session({'dev': profile})
        assert stores_in_credential_daemon(session, 'dev', {}) is expected

    @pytest.mark.parametrize(
        'value, expected', [(DAEMON, True), (FILE, False)]
    )
    def test_env_var(self, value, expected):
        session = make_session({'dev': {'credential_daemon': 'keys.dev'}})
        environ = {'AWS_CREDENTIAL_STORAGE': value}
        assert stores_in_credential_daemon(session, 'dev', environ) is expected

    def test_sso_profile_uses_its_own_answer(self):
        session = make_session(
            SSO_PROFILES, {'acme': {'credential_storage': 'file'}}
        )
        assert stores_in_credential_daemon(session, 'admin', {}) is True

    def test_none_is_the_default_profile(self):
        session = make_session({'default': {'credential_storage': 'daemon'}})
        assert stores_in_credential_daemon(session, None, {}) is True


class TestSsoProfileWithoutRole:
    """A profile with sso_session or sso_start_url and neither
    sso_account_id nor sso_role_name keeps its own credentials in files:
    tools skip credential_daemon for it. Nothing asks or saves."""

    @pytest.mark.parametrize(
        'profile',
        [
            {'sso_session': 'acme'},
            {'sso_start_url': 'https://x', 'credential_storage': 'daemon'},
            # From before this rule: still skipped by tools.
            {'sso_session': 'acme', 'credential_daemon': 'keys.ci'},
        ],
    )
    def test_files_whatever_the_profile_says(self, profile):
        session = make_session({'ci': profile})
        assert known_decision(session, 'ci', {}) == StorageDecision(
            Storage.FILE, DecisionSource.SSO_WITHOUT_ROLE
        )
        assert resolve_credential_storage(session, 'ci', {}) == FILE
        assert not stores_in_credential_daemon(session, 'ci', {})

    @pytest.mark.parametrize('key', ['sso_account_id', 'sso_role_name'])
    def test_an_account_or_a_role_reads_the_profile(self, key):
        # Not the guard: the profile's own answer decides.
        session = make_session(
            {
                'ci': {
                    'sso_session': 'acme',
                    key: 'x',
                    'credential_storage': 'daemon',
                }
            },
            {'acme': {}},
        )
        assert stores_in_credential_daemon(session, 'ci', {})

    def test_the_variable_saying_daemon_is_refused(self):
        session = make_session({'ci': {'sso_session': 'acme'}})
        environ = {'AWS_CREDENTIAL_STORAGE': 'daemon'}
        with pytest.raises(ConfigurationError) as e:
            stores_in_credential_daemon(session, 'ci', environ)
        assert str(e.value) == (
            "Profile 'ci' has sso_session without an account or role, so "
            "the credential daemon can't serve its credentials. Nothing was "
            'changed. To store them in files, run the command again with '
            'AWS_CREDENTIAL_STORAGE=file.'
        )

    def test_the_variable_saying_file_decides(self):
        session = make_session({'ci': {'sso_session': 'acme'}})
        environ = {'AWS_CREDENTIAL_STORAGE': 'file'}
        assert known_decision(session, 'ci', environ) == StorageDecision(
            Storage.FILE, DecisionSource.ENV
        )

    @pytest.mark.parametrize(
        'kind', [CredentialKind.SESSION, CredentialKind.STATIC_KEYS]
    )
    def test_nothing_is_asked_or_saved(self, config_file, capsys, kind):
        chooser, _, ask = make_chooser(
            config_file,
            {'ci': {'sso_session': 'acme'}},
            {'acme': {}},
            answer=True,
        )
        for _ in range(2):
            choice = chooser.choose('ci', kind=kind)
            assert (choice.storage, choice.source) == (
                Storage.FILE,
                DecisionSource.SSO_WITHOUT_ROLE,
            )
            assert chooser.unsaved_values(choice) == {}
            chooser.save(choice)
            chooser.mark_saved(choice)
            assert choice.saved_line is None
        assert not ask.called
        assert config_file.read_text() == ''
        # Once per command.
        assert capsys.readouterr().err == (
            "Note: Profile 'ci' has sso_session without an account or role, "
            "so the credential daemon can't serve its credentials. They're "
            'stored in ~/.aws.\n'
        )

    @pytest.mark.parametrize('tty, available', [(False, True), (True, False)])
    def test_no_note_for_scripts_or_without_a_daemon(
        self, config_file, capsys, tty, available
    ):
        chooser, _, _ = make_chooser(
            config_file,
            {'ci': {'sso_start_url': 'https://x'}},
            tty=tty,
            available=available,
        )
        assert chooser.choose('ci').storage is Storage.FILE
        assert capsys.readouterr().err == ''

    def test_no_storage_line_after_the_note(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'ci': {'sso_session': 'a'}})
        assert chooser.storage_line(chooser.choose('ci')) is None

    def test_names_in_the_note_are_stripped(self, config_file, capsys):
        chooser, _, _ = make_chooser(
            config_file, {'c\x1b[2Ji': {'sso_session': 'acme'}}
        )
        chooser.choose('c\x1b[2Ji')
        err = capsys.readouterr().err
        assert "Profile 'c[2Ji' has sso_session" in err
        assert '\x1b' not in err


class FakeCredentialDaemonClient:
    def __init__(self, available=True, socket_path=None):
        self.available = available
        # Where a socket is when available: what storage_line() checks.
        self.socket_path = socket_path
        self.list_calls = 0

    def list_credentials(self):
        self.list_calls += 1
        if not self.available:
            raise CredentialDaemonNotRunningError(error_msg='not running')
        return []


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / 'config'
    path.write_text('')
    return path


def make_chooser(
    config_file,
    profiles=None,
    sso_sessions=None,
    environ=None,
    tty=True,
    answer=None,
    available=True,
):
    session = make_session(profiles, sso_sessions)
    session.get_config_variable.return_value = str(config_file)
    socket_path = config_file.parent / 'daemon.sock'
    if available:
        socket_path.write_text('')
    client = FakeCredentialDaemonClient(available, str(socket_path))
    ask = mock.Mock(return_value=answer)
    chooser = CredentialStorageChooser(
        session,
        credential_daemon_client=client,
        environ=environ or {},
        is_tty=lambda: tty,
        ask=ask,
    )
    return chooser, client, ask


def use_credentials_file(chooser, config_file, credentials_file):
    variables = {
        'config_file': str(config_file),
        'credentials_file': credentials_file,
    }
    chooser._session.get_config_variable.side_effect = variables.get


class TestCredentialStorageChooser:
    def test_env_var_decides_without_asking(self, config_file):
        chooser, client, ask = make_chooser(
            config_file,
            {'dev': {}},
            environ={'AWS_CREDENTIAL_STORAGE': 'daemon'},
        )
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.DAEMON,
            DecisionSource.ENV,
        )
        assert not ask.called
        assert config_file.read_text() == ''

    def test_saved_answer_decides_without_asking(self, config_file):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {'credential_storage': 'file'}}
        )
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.SAVED,
        )
        assert not ask.called

    def test_a_profile_already_in_credential_daemon_isnt_asked(
        self, config_file
    ):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {'credential_daemon': 'dev'}}
        )
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.DAEMON,
            DecisionSource.PROFILE,
        )
        assert not ask.called

    def test_a_saved_no_beats_credential_daemon(self, config_file):
        # The profile moves back to files at its next sign-in.
        chooser, _, _ = make_chooser(
            config_file,
            {
                'dev': {
                    'credential_daemon': 'dev',
                    'credential_storage': 'file',
                }
            },
        )
        assert chooser.choose('dev').storage == Storage.FILE

    def test_no_terminal_means_files_and_nothing_saved(self, config_file):
        chooser, client, ask = make_chooser(
            config_file, {'dev': {}}, tty=False
        )
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )
        assert not ask.called
        assert client.list_calls == 0
        assert config_file.read_text() == ''

    def test_no_credential_daemon_means_files_and_nothing_saved(
        self, config_file
    ):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {}}, available=False
        )
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )
        assert not ask.called
        assert config_file.read_text() == ''

    def test_without_asking_an_undecided_profile_uses_files(self, config_file):
        chooser, client, ask = make_chooser(
            config_file, {'dev': {}}, answer=True
        )
        choice = chooser.choose_without_asking('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )
        assert not choice.unsaved
        assert not ask.called
        assert client.list_calls == 0
        assert config_file.read_text() == ''

    @pytest.mark.parametrize(
        'profile, environ, expected',
        [
            (
                {'credential_storage': 'daemon'},
                {},
                (Storage.DAEMON, DecisionSource.SAVED),
            ),
            (
                {'credential_daemon': 'dev'},
                {},
                (Storage.DAEMON, DecisionSource.PROFILE),
            ),
            (
                {},
                {'AWS_CREDENTIAL_STORAGE': 'daemon'},
                (Storage.DAEMON, DecisionSource.ENV),
            ),
        ],
    )
    def test_without_asking_keeps_a_known_choice(
        self, config_file, profile, environ, expected
    ):
        chooser, client, ask = make_chooser(
            config_file, {'dev': profile}, environ=environ
        )
        choice = chooser.choose_without_asking('dev')
        assert (choice.storage, choice.source) == expected
        assert not ask.called
        assert client.list_calls == 0

    def test_yes_is_saved(self, config_file):
        chooser, _, ask = make_chooser(config_file, {'dev': {}}, answer=True)
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.DAEMON,
            DecisionSource.NEW_ANSWER,
        )
        question = ask.call_args[0][0]
        assert 'Store this profile\'s session there' in question
        assert ask.call_args[1] == {'default': True}
        # Nothing is saved until the sign-in succeeds.
        assert config_file.read_text() == ''
        chooser.save(choice)
        assert config_file.read_text() == (
            '[profile dev]\ncredential_storage = daemon\n'
        )

    def test_no_is_saved_and_explained(self, config_file, capsys):
        chooser, _, _ = make_chooser(config_file, {'dev': {}}, answer=False)
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.NEW_ANSWER,
        )
        chooser.save(choice)
        assert config_file.read_text() == (
            '[profile dev]\ncredential_storage = file\n'
        )
        # The command prints it at the end of the sign-in.
        assert capsys.readouterr().out == ''
        chooser.print_saved_line(choice)
        chooser.print_saved_line(choice)
        assert capsys.readouterr().out == (
            'Saved credential_storage = file for \'dev\'. To use the '
            'credential daemon from the next sign-in: aws configure set '
            'credential_storage daemon --profile dev\n'
        )

    def test_choose_never_saves(self, config_file, capsys):
        chooser, _, _ = make_chooser(config_file, {'new': {}}, answer=False)
        choice = chooser.choose('new')
        assert choice.unsaved
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.NEW_ANSWER,
        )
        assert config_file.read_text() == ''
        assert capsys.readouterr().out == ''
        chooser.save(choice)
        assert config_file.read_text() == (
            '[profile new]\ncredential_storage = file\n'
        )
        assert choice.saved_line.startswith(
            'Saved credential_storage = file for \'new\'.'
        )

    def test_save_writes_only_a_new_answer_once(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'new': {}}, answer=True)
        choice = chooser.choose('new')
        chooser.save(choice)
        assert config_file.read_text() == (
            '[profile new]\ncredential_storage = daemon\n'
        )
        saved, _, _ = make_chooser(
            config_file, {'dev': {'credential_storage': 'file'}}
        )
        saved.save(saved.choose('dev'))
        assert 'dev' not in config_file.read_text()

    def test_default_profile_answer(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'default': {}}, answer=True)
        chooser.save(chooser.choose('default'))
        assert config_file.read_text() == (
            '[default]\ncredential_storage = daemon\n'
        )

    def test_sso_answer_goes_on_the_profile(self, config_file):
        chooser, _, _ = make_chooser(
            config_file,
            {'admin': dict(ROLE, sso_session='acme')},
            {'acme': {}},
            answer=False,
        )
        choice = chooser.choose('admin')
        chooser.save(choice)
        assert config_file.read_text() == (
            '[profile admin]\ncredential_storage = file\n'
        )
        assert choice.saved_line.endswith('--profile admin')

    def test_static_keys_question(self, config_file):
        chooser, _, ask = make_chooser(config_file, {'ci': {}}, answer=True)
        chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        question = ask.call_args[0][0]
        assert 'Store these keys in the credential daemon' in question
        assert 'IAM calls without MFA' in question

    def test_static_keys_question_without_a_device_has_no_mfa_line(
        self, config_file
    ):
        chooser, _, ask = make_chooser(config_file, {'ci': {}}, answer=True)
        chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        assert 'MFA device' not in ask.call_args[0][0]

    def test_static_keys_question_says_a_device_means_no_credentials(
        self, config_file
    ):
        chooser, _, ask = make_chooser(
            config_file,
            {'ci': {'mfa_serial': 'arn:aws:iam::1:mfa/ci'}},
            answer=True,
        )
        chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        assert (
            'long presigned URLs).\n'
            'This profile has an MFA device (mfa_serial), so programs using '
            'it get no credentials until you run \'aws configure mfa-login\', '
            'and again after each MFA session ends.\n'
            'Older AWS SDKs can\'t use this profile (see docs for a '
            'workaround). [Y/n] '
        ) in ask.call_args[0][0]

    def test_session_question_has_no_mfa_line(self, config_file):
        chooser, _, ask = make_chooser(
            config_file,
            {'ci': {'mfa_serial': 'arn:aws:iam::1:mfa/ci'}},
            answer=True,
        )
        chooser.choose('ci')
        assert 'MFA device' not in ask.call_args[0][0]

    def test_static_keys_question_names_the_credentials_file(
        self, config_file
    ):
        chooser, _, ask = make_chooser(config_file, {'ci': {}}, answer=True)
        use_credentials_file(chooser, config_file, '~/.aws/credentials')
        chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        assert ask.call_args[0][0].startswith(
            'Store these keys in the credential daemon instead of '
            '~/.aws/credentials?\n'
        )
        use_credentials_file(chooser, config_file, '~/work/aws-keys')
        chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        assert ask.call_args[0][0].startswith(
            'Store these keys in the credential daemon instead of '
            '~/work/aws-keys?\n'
        )

    def test_static_keys_no_says_the_keys_stay(self, config_file, capsys):
        chooser, _, _ = make_chooser(config_file, {'ci': {}}, answer=False)
        use_credentials_file(chooser, config_file, '~/.aws/credentials')
        choice = chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        chooser.save(choice)
        assert choice.saved_line == (
            'Saved credential_storage = file for \'ci\'. The keys stay in '
            '~/.aws/credentials.'
        )

    def test_static_keys_no_names_custom_credentials_file(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'ci': {}}, answer=False)
        use_credentials_file(chooser, config_file, '~/work/aws-keys')
        choice = chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        chooser.save(choice)
        assert choice.saved_line == (
            'Saved credential_storage = file for \'ci\'. The keys stay in '
            '~/work/aws-keys.'
        )

    def test_static_keys_no_saved_later_says_the_keys_stay(
        self, config_file, capsys
    ):
        chooser, _, _ = make_chooser(config_file, {'ci': {}}, answer=False)
        use_credentials_file(chooser, config_file, '~/.aws/credentials')
        choice = chooser.choose('ci', kind=CredentialKind.STATIC_KEYS)
        assert capsys.readouterr().out == ''
        chooser.save(choice)
        assert choice.saved_line == (
            'Saved credential_storage = file for \'ci\'. The keys stay in '
            '~/.aws/credentials.'
        )

    def test_availability_is_checked_once(self, config_file):
        chooser, client, _ = make_chooser(config_file, {'dev': {}})
        chooser.is_credential_daemon_available()
        chooser.is_credential_daemon_available()
        assert client.list_calls == 1

    def test_default_client_uses_the_call_timeout(self, config_file):
        session = make_session({'dev': {}})
        chooser = CredentialStorageChooser(session, is_tty=lambda: True)
        with (
            mock.patch(f'{CHOOSER}.CredentialDaemonClient') as client_class,
            # Where the credential daemon doesn't run, such as Windows, no
            # client is built.
            mock.patch(
                f'{CHOOSER}.credential_daemon_runs_here', return_value=True
            ),
        ):
            client_class.return_value.list_credentials.side_effect = (
                CredentialDaemonNotRunningError(error_msg='not running')
            )
            assert chooser.is_credential_daemon_available() is False
        # The client's default, DEFAULT_TIMEOUT.
        client_class.assert_called_once_with()
        timeout = inspect.signature(CredentialDaemonClient).parameters[
            'timeout'
        ]
        assert timeout.default == DEFAULT_TIMEOUT

    def test_sso_profile_answer_is_read_from_the_profile(
        self, config_file, capsys
    ):
        # The sso-session's value isn't read, and nothing warns about it.
        chooser, _, ask = make_chooser(
            config_file,
            {'sso': dict(ROLE, sso_session='acme', credential_storage='File')},
            {'acme': {'credential_storage': 'daemon'}},
        )
        choice = chooser.choose('sso')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.SAVED,
        )
        ask.assert_not_called()
        assert capsys.readouterr().err == ''


class TestQuestionAndShownNames:
    """The question's gate, Ctrl-D, the default profile, and names in what
    the chooser prints."""

    def test_asks_only_when_stdin_and_stdout_are_terminals(self, config_file):
        session = make_session({'dev': {}})
        session.get_config_variable.return_value = str(config_file)
        ask = mock.Mock(return_value=True)
        chooser = CredentialStorageChooser(
            session,
            credential_daemon_client=FakeCredentialDaemonClient(),
            environ={},
            ask=ask,
        )
        # The question goes to stdout: redirected, nobody sees it.
        with (
            mock.patch(f'{CHOOSER}.is_stdin_a_tty', return_value=True),
            mock.patch(f'{CHOOSER}.is_a_tty', return_value=False),
        ):
            choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )
        ask.assert_not_called()
        assert config_file.read_text() == ''
        with (
            mock.patch(f'{CHOOSER}.is_stdin_a_tty', return_value=True),
            mock.patch(f'{CHOOSER}.is_a_tty', return_value=True),
        ):
            assert chooser.choose('dev').source is DecisionSource.NEW_ANSWER

    def test_ctrl_d_stops_like_ctrl_c(self, config_file):
        chooser, _, ask = make_chooser(config_file, {'dev': {}})
        ask.side_effect = EOFError
        with pytest.raises(KeyboardInterrupt):
            chooser.choose('dev')
        assert config_file.read_text() == ''

    def test_none_is_the_default_profile(self, config_file):
        chooser, _, ask = make_chooser(
            config_file, {'default': {'credential_storage': 'file'}}
        )
        for choose in (chooser.choose, chooser.choose_without_asking):
            choice = choose(None)
            assert (choice.storage, choice.source) == (
                Storage.FILE,
                DecisionSource.SAVED,
            )
            assert choice.profile_name == 'default'
        ask.assert_not_called()

    def test_names_in_the_saved_line_are_stripped_and_quoted(
        self, config_file
    ):
        chooser, _, _ = make_chooser(
            config_file, {'my\x1b[2J dev': {}}, answer=False
        )
        choice = chooser.choose('my\x1b[2J dev')
        chooser.save(choice)
        assert choice.saved_line == (
            "Saved credential_storage = file for 'my[2J dev'. To use the "
            'credential daemon from the next sign-in: aws configure set '
            'credential_storage daemon --profile '
            + compat_shell_quote('my[2J dev')
        )

    def test_names_in_the_static_keys_lines_are_stripped_and_quoted(
        self, config_file
    ):
        chooser, _, ask = make_chooser(
            config_file, {'my ci': {}}, answer=False
        )
        use_credentials_file(chooser, config_file, '~/.aws/cred\x1b[2Jentials')
        choice = chooser.choose('my ci', kind=CredentialKind.STATIC_KEYS)
        assert 'instead of ~/.aws/cred[2Jentials?' in ask.call_args[0][0]
        chooser.save(choice)
        assert choice.saved_line == (
            "Saved credential_storage = file for 'my ci'. The keys stay in "
            '~/.aws/cred[2Jentials.'
        )

    def test_windows_quoting_in_commands(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'my dev': {}}, answer=False)
        choice = chooser.choose('my dev')
        with mock.patch('sys.platform', 'win32'):
            chooser.save(choice)
        assert choice.saved_line.endswith('--profile "my dev"')

    @pytest.mark.parametrize(
        'source', [DecisionSource.SAVED, DecisionSource.ENV]
    )
    def test_storage_line_checks_the_socket_without_a_call(
        self, config_file, source
    ):
        chooser, client, _ = make_chooser(config_file, {'dev': {}})
        line = chooser.storage_line(
            StorageChoice(Storage.FILE, source, profile_name='dev')
        )
        assert line.startswith(
            'Credentials are stored in ~/.aws, in plaintext'
        )
        assert client.list_calls == 0

    def test_storage_line_without_a_socket(self, config_file):
        chooser, client, _ = make_chooser(
            config_file, {'dev': {}}, available=False
        )
        line = chooser.storage_line(
            StorageChoice(
                Storage.FILE,
                DecisionSource.SAVED,
                profile_name='dev',
            )
        )
        assert line is None
        assert client.list_calls == 0


class TestStorageLine:
    @pytest.mark.parametrize(
        'storage, source, tty, available, expected',
        [
            (
                DAEMON,
                DecisionSource.SAVED.value,
                False,
                False,
                'credential daemon.',
            ),
            (FILE, DecisionSource.DEFAULT.value, True, True, None),
            (FILE, DecisionSource.SAVED.value, False, True, None),
            (
                FILE,
                DecisionSource.NEW_ANSWER.value,
                True,
                True,
                'in plaintext.',
            ),
            (
                FILE,
                DecisionSource.SAVED.value,
                True,
                True,
                'aws configure set',
            ),
            (FILE, DecisionSource.SAVED.value, True, False, None),
            (FILE, DecisionSource.ENV.value, True, True, 'in plaintext.'),
        ],
    )
    def test_storage_line(
        self, config_file, storage, source, tty, available, expected
    ):
        chooser, _, _ = make_chooser(
            config_file, {'dev': {}}, tty=tty, available=available
        )
        line = chooser.storage_line(
            StorageChoice(
                Storage(storage),
                DecisionSource(source),
                profile_name='dev',
            )
        )
        if expected is None:
            assert line is None
        else:
            assert line.startswith('Credentials are stored ')
            assert expected in line

    def test_reminder_names_the_profile(self, config_file):
        chooser, _, _ = make_chooser(config_file, {'dev': {}})
        line = chooser.storage_line(
            StorageChoice(
                Storage.FILE,
                DecisionSource.SAVED,
                profile_name='dev',
            )
        )
        assert line == (
            'Credentials are stored in ~/.aws, in plaintext '
            '(credential_storage = file).\n'
            'To use the credential daemon from the next sign-in: '
            'aws configure set credential_storage daemon --profile dev'
        )


class SocketClient:
    """A client whose availability check failed at ``socket_path``."""

    def __init__(self, error, socket_path):
        self._error = error
        self.socket_path = socket_path

    def list_credentials(self):
        raise self._error


class TestQuietDowngradeLines:
    """P-5: a sign-in that quietly ends up on files, or on another socket,
    says so on stderr, in a terminal."""

    @pytest.fixture
    def runs_here(self):
        # Where the credential daemon doesn't run, it counts as absent and
        # no note prints: tests of the note run as on Linux or macOS.
        with (
            mock.patch(
                'awscli.customizations.credential_daemon.storage.chooser.'
                'credential_daemon_runs_here',
                return_value=True,
            ),
            mock.patch(
                'awscli.customizations.credential_daemon.storage.presence.'
                'credential_daemon_runs_here',
                return_value=True,
            ),
        ):
            yield

    def chooser(self, config_file, client, tty=True, profiles=None):
        session = make_session(profiles or {'dev': {}})
        session.get_config_variable.return_value = str(config_file)
        return CredentialStorageChooser(
            session,
            credential_daemon_client=client,
            environ={},
            is_tty=lambda: tty,
            ask=mock.Mock(return_value=True),
        )

    def test_an_installed_daemon_that_doesnt_answer(
        self, config_file, tmp_path, capsys, runs_here
    ):
        socket_path = tmp_path / 'daemon.sock'
        socket_path.write_text('')
        error = CredentialDaemonNotRunningError(error_msg='timed out')
        chooser = self.chooser(config_file, SocketClient(error, socket_path))
        assert chooser.choose('dev').storage == Storage.FILE
        assert capsys.readouterr().err == (
            'Note: The credential daemon can\'t be used, so this command '
            'keeps credentials in files, in plaintext: timed out\n'
        )

    def test_the_daemons_text_is_stripped(
        self, config_file, capsys, runs_here
    ):
        error = CredentialDaemonProtocolError(error_msg='bad\x1b[2Jreply')
        self.chooser(config_file, SocketClient(error, None)).choose('dev')
        err = capsys.readouterr().err
        assert '\x1b' not in err
        assert 'bad[2Jreply' in err

    def test_a_daemon_that_answers_wrong(self, config_file, capsys, runs_here):
        error = CredentialDaemonProtocolError(error_msg='bad reply')
        chooser = self.chooser(config_file, SocketClient(error, None))
        chooser.choose('dev')
        assert 'bad reply' in capsys.readouterr().err

    def test_no_socket_is_a_machine_without_the_daemon(
        self, config_file, tmp_path, capsys
    ):
        error = CredentialDaemonNotRunningError(error_msg='not running')
        client = SocketClient(error, tmp_path / 'missing.sock')
        self.chooser(config_file, client).choose('dev')
        assert capsys.readouterr().err == ''

    def test_no_terminal_says_nothing(self, config_file, capsys):
        error = CredentialDaemonProtocolError(error_msg='bad reply')
        chooser = self.chooser(config_file, SocketClient(error, None), False)
        chooser.choose('dev')
        assert capsys.readouterr().err == ''

    def test_once_per_command(self, config_file, capsys, runs_here):
        error = CredentialDaemonProtocolError(error_msg='bad reply')
        chooser = self.chooser(config_file, SocketClient(error, None))
        chooser.choose('dev')
        chooser.choose('dev')
        assert capsys.readouterr().err.count('bad reply') == 1

    def test_skipped_home_socket_before_the_question(
        self, config_file, monkeypatch, capsys
    ):
        monkeypatch.setenv('HOME', 'relative')
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        chooser = self.chooser(config_file, None)
        with mock.patch.object(
            CredentialStorageChooser,
            'is_credential_daemon_available',
            return_value=True,
        ):
            chooser.choose('dev')
            chooser.choose('dev')
        err = capsys.readouterr().err
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            assert err == (
                'Note: HOME isn\'t an absolute path, so '
                '~/.aws/credential-daemon.sock was skipped.\n'
                # Asked twice, so said twice; the note is said once.
                + PREVIEW_LINE
                + PREVIEW_LINE
            )

    def test_skipped_socket_for_a_profile_in_the_daemon(
        self, config_file, monkeypatch, capsys
    ):
        monkeypatch.setenv('HOME', 'relative')
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        chooser = self.chooser(
            config_file,
            None,
            profiles={'dev': {'credential_storage': 'daemon'}},
        )
        chooser.choose('dev')
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            assert 'HOME isn\'t an absolute path' in capsys.readouterr().err

    def test_no_notes_without_the_daemon(
        self, config_file, monkeypatch, capsys
    ):
        # Nothing at any socket: today's output, with no discovery notes.
        monkeypatch.setenv('HOME', 'relative')
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        chooser = self.chooser(config_file, None)
        assert chooser.choose('dev').storage == Storage.FILE
        assert capsys.readouterr().err == ''

    def test_nothing_said_where_the_daemon_doesnt_run(
        self, config_file, monkeypatch, capsys
    ):
        # Such as Windows: today's output.
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        chooser = self.chooser(config_file, None)
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            assert chooser.choose('dev').storage == Storage.FILE
        assert capsys.readouterr().err == ''

    def test_the_daemon_isnt_dialed_where_it_doesnt_run(
        self, config_file, capsys
    ):
        # Such as Windows, whatever AWS_CREDENTIAL_DAEMON_SOCKET says:
        # nothing looks the socket up.
        chooser = self.chooser(config_file, None)
        with (
            mock.patch(
                'botocore.credential_daemon.host.Host.runs_credential_daemon',
                return_value=False,
            ),
            mock.patch(
                'botocore.credential_daemon.client.default_socket_path',
                side_effect=InvalidConfigError(error_msg='not a pipe'),
            ),
        ):
            assert chooser.choose('dev').storage == Storage.FILE
        assert capsys.readouterr().err == ''

    def test_files_by_choice_get_no_notes(
        self, config_file, monkeypatch, capsys
    ):
        monkeypatch.setenv('HOME', 'relative')
        chooser = self.chooser(
            config_file, None, profiles={'dev': {'credential_storage': 'file'}}
        )
        chooser.choose('dev')
        assert capsys.readouterr().err == ''

    @skip_if_windows
    def test_a_socket_variable_with_nothing_there_says_so(
        self, config_file, tmp_path, monkeypatch, capsys, runs_here
    ):
        # The customer chose a socket, so the question's skip is explained.
        missing = str(tmp_path / 'missing.sock')
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', missing)
        monkeypatch.setenv('HOME', str(tmp_path))
        chooser = self.chooser(config_file, None)
        choice = chooser.choose('dev')
        assert (choice.storage, choice.source) == (
            Storage.FILE,
            DecisionSource.DEFAULT,
        )
        err = capsys.readouterr().err
        # One note, naming the variable and the socket the customer set.
        assert err.startswith(
            f'Note: AWS_CREDENTIAL_DAEMON_SOCKET is {missing}, and the '
            'credential daemon can\'t be used there, so this command keeps '
            'credentials in files, in plaintext: '
        )
        assert err.count('\n') == 1
        assert config_file.read_text() == ''

    @skip_if_windows
    def test_a_relative_socket_variable_says_it_was_ignored(
        self, config_file, tmp_path, monkeypatch, capsys, runs_here
    ):
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', 'relative/x.sock')
        monkeypatch.setenv('HOME', str(tmp_path))
        chooser = self.chooser(config_file, None)
        assert chooser.choose('dev').source is DecisionSource.DEFAULT
        err = capsys.readouterr().err
        # Only the discovery notes: nothing at ~/.aws to say more about.
        assert err.startswith(
            'Note: AWS_CREDENTIAL_DAEMON_SOCKET isn\'t an absolute path, so '
            'it was ignored: relative/x.sock\n'
        )
        assert 'can\'t be used' not in err

    @skip_if_windows
    @pytest.mark.parametrize('value', [None, ''])
    def test_no_socket_variable_and_no_socket_says_nothing(
        self, config_file, tmp_path, monkeypatch, capsys, runs_here, value
    ):
        if value is None:
            monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        else:
            monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', value)
        monkeypatch.setenv('HOME', str(tmp_path))
        chooser = self.chooser(config_file, None)
        assert chooser.choose('dev').source is DecisionSource.DEFAULT
        assert capsys.readouterr().err == ''

    def test_a_socket_variable_without_a_terminal_says_nothing(
        self, config_file, tmp_path, monkeypatch, capsys, runs_here
    ):
        monkeypatch.setenv(
            'AWS_CREDENTIAL_DAEMON_SOCKET', str(tmp_path / 'missing.sock')
        )
        chooser = self.chooser(config_file, None, tty=False)
        chooser.choose('dev')
        assert capsys.readouterr().err == ''

    def test_a_socket_variable_where_the_daemon_doesnt_run_says_nothing(
        self, config_file, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', 'relative/x.sock')
        chooser = self.chooser(config_file, None)
        with mock.patch(
            f'{CHOOSER}.credential_daemon_runs_here', return_value=False
        ):
            chooser.choose('dev')
        assert capsys.readouterr().err == ''


class TestCredentialDaemonAbsent:
    def test_no_socket_path_is_absent(self, tmp_path):
        error = CredentialDaemonNotRunningError(error_msg='x')
        assert credential_daemon_absent(error, str(tmp_path / 'gone'))
        assert credential_daemon_absent(error, None)

    def test_no_socket_path_on_this_platform_is_absent(self):
        # The credential daemon doesn't run here, so nothing was dialed.
        error = CredentialDaemonConnectionError(
            error_msg="The credential daemon isn't available on this platform."
        )
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            assert credential_daemon_absent(error, None)

    def test_the_socket_variable_doesnt_count_where_the_daemon_doesnt_run(
        self, tmp_path
    ):
        path = tmp_path / 's'
        path.touch()
        error = CredentialDaemonNotRunningError(error_msg='x')
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            assert not credential_daemon_runs_here()
            assert credential_daemon_absent(error, str(path))

    @pytest.mark.skipif(
        not (sys.platform.startswith('linux') or sys.platform == 'darwin'),
        reason='The credential daemon runs on Linux and macOS.',
    )
    def test_runs_here_on_linux_and_macos(self):
        assert credential_daemon_runs_here()

    @skip_if_windows
    def test_a_timeout_with_no_socket_path_is_not_absent(self):
        error = CredentialDaemonTimeoutError(error_msg='x')
        assert not credential_daemon_absent(error, None)

    @skip_if_windows
    def test_a_socket_that_is_there_is_not_absent(self, tmp_path):
        path = tmp_path / 's'
        path.touch()
        error = CredentialDaemonNotRunningError(error_msg='x')
        assert not credential_daemon_absent(error, str(path))

    @skip_if_windows
    def test_a_dangling_symlink_is_not_absent(self, tmp_path):
        # A path from AWS_CREDENTIAL_DAEMON_SOCKET or a caller.
        path = tmp_path / 's'
        path.symlink_to(tmp_path / 'gone')
        error = CredentialDaemonNotRunningError(error_msg='x')
        assert not credential_daemon_absent(error, str(path))

    @pytest.mark.skipif(
        not hasattr(os, 'geteuid') or os.geteuid() == 0,
        reason='Root can search any folder.',
    )
    def test_a_socket_in_a_folder_it_cant_search_is_not_absent(self, tmp_path):
        # Such as AWS_CREDENTIAL_DAEMON_SOCKET in a folder the user can't
        # search: something may be there that the CLI can't use.
        closed = tmp_path / 'closed'
        closed.mkdir()
        (closed / 'd.sock').touch()
        closed.chmod(0)
        try:
            error = CredentialDaemonNotRunningError(error_msg='x')
            assert not credential_daemon_absent(error, str(closed / 'd.sock'))
        finally:
            closed.chmod(0o700)

    def test_a_home_link_to_nothing_is_absent(self, tmp_path):
        path = tmp_path / 'credential-daemon.sock'
        path.symlink_to(tmp_path / 'gone')
        error = CredentialDaemonNotRunningError(error_msg='x')
        assert credential_daemon_absent(error, HomeSocketPath(str(path)))

    @pytest.mark.skipif(
        not hasattr(os, 'geteuid') or os.geteuid() == 0,
        reason='Root can search any folder.',
    )
    def test_a_home_link_into_a_folder_it_cant_search_is_not_absent(
        self, tmp_path
    ):
        closed = tmp_path / 'closed'
        closed.mkdir()
        path = tmp_path / 'credential-daemon.sock'
        path.symlink_to(closed / 'd.sock')
        closed.chmod(0)
        try:
            error = CredentialDaemonNotRunningError(error_msg='x')
            assert not credential_daemon_absent(
                error, HomeSocketPath(str(path))
            )
        finally:
            closed.chmod(0o700)

    @skip_if_windows
    def test_a_home_link_to_a_socket_that_is_there_is_not_absent(
        self, tmp_path
    ):
        target = tmp_path / 'target'
        target.touch()
        path = tmp_path / 'credential-daemon.sock'
        path.symlink_to(target)
        error = CredentialDaemonNotRunningError(error_msg='x')
        assert not credential_daemon_absent(error, HomeSocketPath(str(path)))

    @skip_if_windows
    def test_a_timeout_is_not_absent(self, tmp_path):
        error = CredentialDaemonTimeoutError(error_msg='x')
        assert not credential_daemon_absent(error, str(tmp_path / 'gone'))

    @skip_if_windows
    def test_another_error_is_not_absent(self, tmp_path):
        error = CredentialDaemonProtocolError(error_msg='x')
        assert not credential_daemon_absent(error, str(tmp_path / 'gone'))


class TestDetectPresence:
    @skip_if_windows
    def test_an_answer_is_running(self, tmp_path):
        assert detect_presence(None, None) is Presence.RUNNING

    @skip_if_windows
    def test_nothing_at_the_socket_is_absent(self, tmp_path):
        error = CredentialDaemonNotRunningError(error_msg='x')
        presence = detect_presence(error, str(tmp_path / 'gone'))
        assert presence is Presence.ABSENT
        assert presence.absent

    @skip_if_windows
    def test_a_socket_that_refuses_is_stopped(self, tmp_path):
        path = tmp_path / 'd.sock'
        path.touch()
        error = CredentialDaemonNotRunningError(error_msg='x')
        presence = detect_presence(error, str(path))
        assert presence is Presence.STOPPED
        assert not presence.absent

    @skip_if_windows
    def test_a_timeout_is_stopped(self, tmp_path):
        error = CredentialDaemonTimeoutError(error_msg='x')
        assert (
            detect_presence(error, str(tmp_path / 'gone')) is Presence.STOPPED
        )

    @skip_if_windows
    def test_an_untrusted_socket(self, tmp_path):
        from botocore.exceptions import CredentialDaemonUntrustedSocketError

        error = CredentialDaemonUntrustedSocketError(error_msg='x')
        presence = detect_presence(error, None)
        assert presence is Presence.UNTRUSTED
        assert not presence.absent

    def test_where_it_doesnt_run(self):
        error = CredentialDaemonNotRunningError(error_msg='x')
        with mock.patch(
            'awscli.customizations.credential_daemon.storage.presence.'
            'credential_daemon_runs_here',
            return_value=False,
        ):
            presence = detect_presence(error, None)
        assert presence is Presence.UNSUPPORTED_PLATFORM
        assert presence.absent


class TestPreviewNotice:
    """Every question about where to store credentials says first, on
    stderr, that credential daemon support is a developer preview."""

    def test_printed_on_stderr_right_before_the_question(
        self, config_file, capsys
    ):
        chooser, _, ask = make_chooser(config_file, {'dev': {}})
        seen = []

        def record(question, default):
            # What stderr and stdout held when the question was asked.
            seen.append(capsys.readouterr())
            return True

        ask.side_effect = record
        chooser.choose('dev')
        [before] = seen
        assert before.err == PREVIEW_LINE
        assert PREVIEW_NOTICE not in before.out
        # Not again after the answer.
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_asked_twice_says_it_twice(self, config_file, capsys):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {}, 'ci': {}}, answer=True
        )
        chooser.choose('dev')
        chooser.choose('ci')
        assert ask.call_count == 2
        assert capsys.readouterr().err == PREVIEW_LINE + PREVIEW_LINE

    def test_no_terminal_says_nothing(self, config_file, capsys):
        chooser, _, ask = make_chooser(config_file, {'dev': {}}, tty=False)
        chooser.choose('dev')
        assert not ask.called
        assert capsys.readouterr().err == ''

    def test_no_credential_daemon_says_nothing(self, config_file, capsys):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {}}, available=False
        )
        chooser.choose('dev')
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_a_saved_answer_says_nothing(self, config_file, capsys):
        chooser, _, ask = make_chooser(
            config_file, {'dev': {'credential_storage': 'daemon'}}
        )
        chooser.choose('dev')
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_where_the_credential_daemon_doesnt_run_says_nothing(
        self, config_file, capsys
    ):
        # Such as Windows: there's no question to ask.
        session = make_session({'dev': {}})
        session.get_config_variable.return_value = str(config_file)
        ask = mock.Mock(return_value=True)
        chooser = CredentialStorageChooser(
            session, environ={}, is_tty=lambda: True, ask=ask
        )
        with mock.patch(
            f'{CHOOSER}.credential_daemon_runs_here', return_value=False
        ):
            chooser.choose('dev')
        assert not ask.called
        assert capsys.readouterr().err == ''
