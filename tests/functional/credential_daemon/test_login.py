# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for aws login through the credential daemon, run against the fake
credential daemon."""

import contextlib
import io
import json
import os
import socket
import time
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import (
    CLI_TAGS,
    CredentialDaemonClient,
    CredentialRow,
)
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonTimeoutError,
    CredentialDaemonUntrustedSocketError,
    InvalidConfigError,
    LoginAuthorizationCodeError,
)
from botocore.session import Session
from botocore.utils import generate_login_cache_key

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.credential_daemon.sessions import (
    is_credential_daemon_workaround,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.customizations.login.credential_daemon import (
    CredentialDaemonSignInHandler,
)
from awscli.customizations.login.login import LoginCommand
from awscli.customizations.login.signup import SignupCommand
from awscli.errorhandler import construct_cli_error_handlers_chain
from tests import mock
from tests.functional.credential_daemon.login_helpers import (
    GLOBALS,
    HANDLER,
    SAMPLE_ID_TOKEN,
    daemon_timeout,
    files_sign_in,
    login,
    read_config,
    rendered_help,
    timeout_message,
    write_config,
)
from tests.functional.credential_daemon.sso_helpers import (
    START_HINT_TEXT,
)
from tests.utils.credential_daemon import (
    DEFAULT_PRINCIPAL,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    NO_SESSION,
    FakeCredentialDaemon,
    identity_credential_name,
)
from tests.utils.credential_daemon.skips import skip_if_root

# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'

BOB = 'arn:aws:sts::123456789012:assumed-role/ReadOnly/bob'
PROD_ADMIN = 'arn:aws:sts::111111111111:assumed-role/Admin/alice'
# The names the credential daemon gives DEFAULT_PRINCIPAL's and BOB's aws
# login credentials.
ALICE = 'login.123456789012-role-Admin'
BOB_NAME = 'login.123456789012-role-ReadOnly'
REMOTE_PROMPT = '\nEnter the authorization code displayed in your browser: '
# The same identity the fake signs in as, so moving doesn't ask first.
OLD_SESSION = DEFAULT_PRINCIPAL


def assert_cleared(fake, name):
    credential = fake.credential(name)
    assert credential.status == NO_SESSION
    assert not credential.secrets


class TestFirstSignIn:
    def test_yes_moves_the_profile(self, fake, aws_dir, browser, capsys):
        ask, _ = login(fake, storage_answer=True)
        assert ask.called
        assert read_config(aws_dir) == (
            '[profile dev]\n'
            'credential_storage = daemon\n'
            'credential_daemon = login.123456789012-role-Admin\n'
        )
        assert (
            fake.credential('login.123456789012-role-Admin').kind == KIND_LOGIN
        )
        url = browser.call_args[0][0]
        assert url.startswith('https://us-west-2.signin.aws.amazon.com/')
        out = capsys.readouterr().out
        assert f'Signed in as {DEFAULT_PRINCIPAL}' in out
        assert 'Credentials are stored in the credential daemon.' in out
        # credsd doesn't say when the session ends, so there's no
        # session line.
        assert 'Session:' not in out
        assert 'Moved this profile' not in out

    def test_no_keeps_files(self, fake, aws_dir, capsys):
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            login(fake, storage_answer=False)
        assert read_config(aws_dir) == (
            '[profile dev]\n'
            'credential_storage = file\n'
            f'login_session = {OLD_SESSION}\n'
        )
        assert fake.credential('login.123456789012-role-Admin') is None
        out = capsys.readouterr().out
        assert 'Saved credential_storage = file for \'dev\'.' in out
        assert 'Credentials are stored in ~/.aws, in plaintext.' in out

    def test_no_saved_line_comes_last(self, fake, aws_dir, capsys):
        # The "Saved credential_storage = file" line is the last line,
        # after the sign-in summary, not before the browser opens.
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            login(fake, storage_answer=False)
        out = capsys.readouterr().out
        saved = out.index('Saved credential_storage = file for \'dev\'.')
        assert saved > out.index(
            'Credentials are stored in ~/.aws, in plaintext.'
        )
        assert saved > out.index('Updated profile dev')

    def test_no_saved_line_when_the_sign_in_fails(self, fake, aws_dir, capsys):
        write_config(aws_dir, '[profile dev]\nregion = us-west-2\n')
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                side_effect=RuntimeError('sign-in failed'),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
            pytest.raises(RuntimeError),
        ):
            login(fake, storage_answer=False)
        assert 'Saved credential_storage' not in capsys.readouterr().out

    def test_session_file_is_deleted_on_the_first_move(
        self, fake, aws_dir, browser, capsys
    ):
        write_config(
            aws_dir,
            f'''
            [profile dev]
            login_session = {OLD_SESSION}
            region = us-west-2
            ''',
        )
        cache = aws_dir / 'cache'
        cache.mkdir()
        session_file = cache / f'{generate_login_cache_key(OLD_SESSION)}.json'
        session_file.write_text(json.dumps({'accessToken': {}}))
        login(fake, storage_answer=True)
        assert not session_file.exists()
        config = read_config(aws_dir)
        assert 'login_session' not in config
        assert 'credential_daemon = login.123456789012-role-Admin' in config
        assert 'region = us-west-2' in config
        assert (
            'Moved this profile\'s session into the credential daemon '
            'and deleted its file in'
        ) in capsys.readouterr().out

    def write_dev_with_session_file(self, aws_dir, extra=''):
        write_config(
            aws_dir,
            f'''
            [profile dev]
            login_session = {OLD_SESSION}
            region = us-west-2
            '''
            + extra,
        )
        cache = aws_dir / 'cache'
        cache.mkdir()
        session_file = cache / f'{generate_login_cache_key(OLD_SESSION)}.json'
        session_file.write_text(json.dumps({'accessToken': {}}))
        return session_file

    def test_failed_credential_check_changes_nothing(
        self, fake, aws_dir, browser
    ):
        session_file = self.write_dev_with_session_file(aws_dir)
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        assert (
            'couldn\'t return credentials for \'login.123456789012-role-Admin\': '
            'Injected CREDENTIAL_NOT_FOUND. Profile \'dev\' wasn\'t changed'
            in str(e.value)
        )
        assert (
            'Profile \'dev\' wasn\'t changed and its session file was kept'
        ) in str(e.value)
        config = read_config(aws_dir)
        assert f'login_session = {OLD_SESSION}' in config
        assert 'credential_daemon' not in config
        assert session_file.exists()

    def test_failed_credential_check_signs_out_the_new_credential(
        self, fake, aws_dir, browser
    ):
        self.write_dev_with_session_file(aws_dir)
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        assert (
            'The new session was signed out of the credential daemon.'
        ) in str(e.value)
        credential = fake.credential('login.123456789012-role-Admin')
        assert credential.status == NO_SESSION
        assert not credential.secrets

    def test_failed_credential_check_on_a_new_profile_signs_out(
        self, fake, aws_dir, browser
    ):
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        with pytest.raises(ConfigurationError):
            login(fake, profile='new', storage_answer=True)
        assert (
            fake.credential('login.123456789012-role-Admin').status
            == NO_SESSION
        )

    def test_failed_credential_check_keeps_the_profiles_credential(
        self, fake, aws_dir, browser
    ):
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_storage = daemon
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        fake.seed('login.123456789012-role-Admin')
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        with pytest.raises(ConfigurationError) as e:
            login(fake)
        assert 'signed out' not in str(e.value)
        assert (
            fake.credential('login.123456789012-role-Admin').status
            != NO_SESSION
        )
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_failed_credential_check_keeps_another_profiles_credential(
        self, fake, aws_dir, browser
    ):
        self.write_dev_with_session_file(
            aws_dir,
            '''
            [profile staging]
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        fake.seed('login.123456789012-role-Admin')
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        with pytest.raises(ConfigurationError):
            login(fake, storage_answer=True)
        assert (
            fake.credential('login.123456789012-role-Admin').status
            != NO_SESSION
        )
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_failed_sign_out_is_reported(self, fake, aws_dir, browser):
        session_file = self.write_dev_with_session_file(aws_dir)
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        fake.fail_next('credential/logout', 'INTERNAL_ERROR')
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        assert (
            'Profile \'dev\' wasn\'t changed and its session file was kept.'
        ) in str(e.value)
        assert (
            'The new session is still in the credential daemon, because '
            'it couldn\'t be signed out'
        ) in str(e.value)
        # The error names the command that signs it out.
        assert str(e.value).endswith(
            'Run \'aws logout --all\' to sign it out.'
        )
        assert f'login_session = {OLD_SESSION}' in read_config(aws_dir)
        assert session_file.exists()

    @pytest.mark.parametrize(
        'down',
        [
            CredentialDaemonNotRunningError(
                error_msg='The credential daemon is not running.'
            ),
            # The SEP counts a timeout as NOT_RUNNING.
            CredentialDaemonTimeoutError(
                error_msg='The credential daemon didn\'t respond in time.'
            ),
        ],
    )
    def test_sign_out_with_credential_daemon_down_says_start_credential_daemon(
        self, fake, aws_dir, browser, down
    ):
        self.write_dev_with_session_file(aws_dir)
        fake.fail_next('credential/get', 'REAUTH_REQUIRED')
        with (
            mock.patch.object(
                CredentialDaemonClient, 'logout', side_effect=down
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            login(fake, storage_answer=True)
        assert str(e.value).endswith(
            f'{START_HINT_TEXT} Then run \'aws logout --all\' to sign it out.'
        )

    def test_credential_is_checked_before_the_profile_changes(
        self, fake, aws_dir, browser
    ):
        self.write_dev_with_session_file(aws_dir)
        login(fake, storage_answer=True)
        methods = [method for method, _ in fake.calls]
        assert 'credential/get' in methods
        assert methods.index('credential/get') > methods.index(
            'credential/bootstrap'
        )

    def test_file_is_kept_while_another_profile_uses_it(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_dev_with_session_file(
            aws_dir,
            f'''
            [profile dev-east]
            login_session = {OLD_SESSION}
            [profile dev-moved]
            login_session = {OLD_SESSION}
            credential_daemon = dev-moved
            ''',
        )
        login(fake, storage_answer=True)
        assert session_file.exists()
        assert (
            'credential_daemon = login.123456789012-role-Admin\n'
            in read_config(aws_dir)
        )
        out = capsys.readouterr().out
        assert (
            'Moved this profile\'s session into the credential daemon. '
            'Kept its file in'
        ) in out
        # An older CLI ignores dev-moved's credential_daemon and still
        # reads the file.
        assert 'because \'dev-east\' and \'dev-moved\' still use it.' in out

    def test_file_is_kept_while_other_profiles_use_it(
        self, fake, aws_dir, browser, capsys
    ):
        self.write_dev_with_session_file(
            aws_dir,
            f'''
            [profile dev-west]
            login_session = {OLD_SESSION}
            [profile dev-east]
            login_session = {OLD_SESSION}
            ''',
        )
        login(fake, storage_answer=True)
        out = capsys.readouterr().out
        assert 'because \'dev-east\' and \'dev-west\' still use it.' in out

    def test_delete_error_is_a_warning(self, fake, aws_dir, browser, capsys):
        session_file = self.write_dev_with_session_file(aws_dir)
        with mock.patch(
            'awscli.customizations.login.login.os.remove',
            side_effect=PermissionError('Permission denied'),
        ):
            _, _, rc = login(fake, storage_answer=True, return_rc=True)
        # A failed cleanup exits non-zero and says where the file is.
        assert rc == 1
        assert session_file.exists()
        config = read_config(aws_dir)
        assert 'credential_daemon = login.123456789012-role-Admin' in config
        # The profile still points at the file that's left, as on the
        # leftover path.
        assert f'login_session = {OLD_SESSION}' in config
        captured = capsys.readouterr()
        assert (
            'warning: couldn\'t delete the session file for \'dev\': '
            'Permission denied'
        ) in captured.err
        assert (
            f'The plaintext session file is still at {session_file}. '
            'Delete it by hand.'
        ) in captured.err
        assert f'Signed in as {DEFAULT_PRINCIPAL}' in captured.out
        assert 'Its file in' in captured.out
        assert 'wasn\'t deleted.' in captured.out

    def test_delete_warning_comes_before_the_summary(
        self, fake, aws_dir, browser
    ):
        self.write_dev_with_session_file(aws_dir)
        both = io.StringIO()
        with (
            mock.patch(
                'awscli.customizations.login.login.os.remove',
                side_effect=PermissionError('Permission denied'),
            ),
            mock.patch('sys.stdout', both),
            mock.patch('sys.stderr', both),
        ):
            login(fake, storage_answer=True)
        output = both.getvalue()
        warning = output.index("warning: couldn't delete the session file")
        assert warning < output.index(f'Signed in as {DEFAULT_PRINCIPAL}')

    def test_interrupted_delete_keeps_login_session(
        self, fake, aws_dir, browser
    ):
        # A run killed before the file goes leaves the profile pointing at
        # it, so the file isn't orphaned.
        session_file = self.write_dev_with_session_file(aws_dir)
        with (
            mock.patch(
                'awscli.customizations.login.login.os.remove',
                side_effect=KeyboardInterrupt,
            ),
            pytest.raises(KeyboardInterrupt),
        ):
            login(fake, storage_answer=True)
        assert session_file.exists()
        config = read_config(aws_dir)
        assert 'credential_daemon = login.123456789012-role-Admin' in config
        assert f'login_session = {OLD_SESSION}' in config

    def test_env_var_moves_without_asking_or_saving(
        self, fake, aws_dir, browser
    ):
        ask, _ = login(
            fake, tty=False, environ={'AWS_CREDENTIAL_STORAGE': 'daemon'}
        )
        assert not ask.called
        assert read_config(aws_dir) == (
            '[profile dev]\ncredential_daemon = login.123456789012-role-Admin\n'
        )

    def test_the_name_comes_from_the_identity_not_the_profile(
        self, fake, aws_dir, browser
    ):
        login(fake, profile='me@corp', storage_answer=True)
        assert f'credential_daemon = {ALICE}' in read_config(aws_dir)
        names = [
            r.name
            for r in CredentialDaemonClient(
                socket_path=fake.socket_path
            ).list_credentials()
        ]
        assert names == [ALICE]

    def test_a_role_name_credential_daemon_cleans_up(
        self, fake, aws_dir, browser
    ):
        fake.next_principal = (
            'arn:aws:sts::111111111111:assumed-role/me@corp.com/alice'
        )
        login(fake, storage_answer=True)
        name = identity_credential_name('login.', fake.next_principal)
        assert name.startswith('login.111111111111-role-me-corp.com-')
        assert fake.credential(name).principal == fake.next_principal
        assert f'credential_daemon = {name}\n' in read_config(aws_dir)

    def test_profiles_signed_in_as_one_identity_share_it(
        self, fake, aws_dir, browser
    ):
        fake.next_principal = PROD_ADMIN
        login(fake, profile='prod', storage_answer=True)
        login(fake, profile='prod-east', storage_answer=True)
        config = read_config(aws_dir)
        assert (
            config.count('credential_daemon = login.111111111111-role-Admin\n')
            == 2
        )

    def test_bootstrap_passes_the_login_prefix(self, fake, aws_dir, browser):
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_storage = daemon
            credential_daemon = {ALICE}
            ''',
        )
        login(fake)
        [params] = [p for m, p in fake.calls if m == 'credential/bootstrap']
        assert params['name_prefix'] == 'login.'
        assert 'name' not in params


class TestCancelledFirstSignIn:
    """A new profile is written only after the sign-in succeeds. The
    storage answer must not create it earlier."""

    def test_files_answer_then_cancel_writes_nothing(self, fake, aws_dir):
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                side_effect=KeyboardInterrupt,
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            with pytest.raises(KeyboardInterrupt):
                login(fake, profile='new', storage_answer=False)
        assert read_config(aws_dir) == ''

    def test_credential_daemon_answer_then_cancel_writes_nothing(
        self, fake, aws_dir, browser
    ):
        fake.fail_next('credential/bootstrap', 'AUTH_CANCELLED')
        with pytest.raises(CredentialDaemonError):
            login(fake, profile='new', storage_answer=True)
        assert read_config(aws_dir) == ''

    def test_failed_credential_check_writes_nothing(
        self, fake, aws_dir, browser
    ):
        # A failed credential/get is a failed sign-in.
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError):
            login(fake, profile='new', storage_answer=True)
        assert read_config(aws_dir) == ''
        # Nor in the credential daemon: credential/logout keeps the entry,
        # signed out with no secrets.
        assert_cleared(fake, 'login.123456789012-role-Admin')

    def test_failed_credential_check_clears_a_files_profile_credential(
        self, fake, aws_dir, browser
    ):
        write_config(aws_dir, '[profile dev]\nregion = us-west-2\n')
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError):
            login(fake, profile='dev', storage_answer=True)
        assert 'credential_daemon' not in read_config(aws_dir)
        assert_cleared(fake, 'login.123456789012-role-Admin')

    def test_failed_clear_says_what_is_left_in_credential_daemon(
        self, fake, aws_dir, browser
    ):
        # A failed cleanup exits non-zero and says what's left.
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        fake.fail_next('credential/logout', 'INTERNAL')
        with pytest.raises(ConfigurationError) as e:
            login(fake, profile='new', storage_answer=True)
        assert (
            'Profile \'new\' wasn\'t changed. The new session is still in the '
            'credential daemon, because it couldn\'t be signed out: '
        ) in str(e.value)
        assert str(e.value).endswith(
            'signed out: Injected INTERNAL (INTERNAL). Run \'aws logout --all\' '
            'to sign it out.'
        )
        assert read_config(aws_dir) == ''

    def test_a_second_failed_check_clears_again(self, fake, aws_dir, browser):
        # The first attempt left new signed out, so the retry has nothing
        # to keep either.
        for _ in range(2):
            fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
            with pytest.raises(ConfigurationError):
                login(fake, profile='new', storage_answer=True)
        assert read_config(aws_dir) == ''
        assert_cleared(fake, 'login.123456789012-role-Admin')

    def test_failed_check_clears_a_signed_out_credential_a_profile_names(
        self, fake, aws_dir, browser
    ):
        # Signed out by aws logout: nothing to keep, so it's signed out again.
        fake.seed('login.123456789012-role-Admin', status=NO_SESSION)
        write_config(
            aws_dir,
            '[profile dev]\ncredential_daemon = login.123456789012-role-Admin\n',
        )
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError):
            login(fake)
        assert_cleared(fake, 'login.123456789012-role-Admin')

    def test_failed_check_keeps_a_credential_from_before(
        self, fake, aws_dir, browser
    ):
        # Signing in again: the bootstrap replaced it, so there's
        # nothing to roll back to and nothing is cleared.
        login(fake, profile='new', storage_answer=True)
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError):
            login(fake, profile='new')
        assert (
            fake.credential('login.123456789012-role-Admin').status
            != NO_SESSION
        )
        assert 'credential/logout' not in [method for method, _ in fake.calls]

    def test_existing_profile_saves_no_answer_after_a_cancel(
        self, fake, aws_dir
    ):
        # The answer is saved only once the sign-in succeeds.
        write_config(aws_dir, '[profile dev]\nregion = us-west-2\n')
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                side_effect=KeyboardInterrupt,
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            with pytest.raises(KeyboardInterrupt):
                login(fake, storage_answer=False)
        assert read_config(aws_dir) == '[profile dev]\nregion = us-west-2\n'

    def test_stub_profile_falls_through_to_the_host_role(self, fake, aws_dir):
        # Without the stub, --profile new is ProfileNotFound. With it, the
        # profile exists with no credentials, so the chain reaches the
        # host's role (IMDS or container) without an error.
        from botocore.credentials import (
            ContainerProvider,
            Credentials,
            InstanceMetadataProvider,
        )
        from botocore.exceptions import ProfileNotFound

        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                side_effect=KeyboardInterrupt,
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            with pytest.raises(KeyboardInterrupt):
                login(fake, profile='new', storage_answer=False)
        host = Credentials('ASIAHOSTROLE', 'host-secret', 'host-token')
        with (
            mock.patch.object(ContainerProvider, 'load', return_value=None),
            mock.patch.object(
                InstanceMetadataProvider, 'load', return_value=host
            ),
        ):
            with pytest.raises(ProfileNotFound):
                Session(profile='new').get_credentials()


class TestConfigWriteFails:
    """The profile write fails after the credential daemon stored the new
    session. The profile and its session file stay as they were, and
    signing in again finishes the move."""

    @pytest.fixture
    def failing_write(self):
        update_config = ConfigFileWriter.update_config

        def fail_on_credential_daemon(writer, new_values, config_filename):
            if new_values.get('credential_daemon'):
                raise PermissionError('Permission denied')
            return update_config(writer, new_values, config_filename)

        with mock.patch.object(
            ConfigFileWriter,
            'update_config',
            autospec=True,
            side_effect=fail_on_credential_daemon,
        ):
            yield

    def write_dev_with_session_file(self, aws_dir):
        write_config(
            aws_dir,
            f'''
            [profile dev]
            login_session = {OLD_SESSION}
            ''',
        )
        cache = aws_dir / 'cache'
        cache.mkdir()
        session_file = cache / f'{generate_login_cache_key(OLD_SESSION)}.json'
        session_file.write_text(json.dumps({'accessToken': {}}))
        return session_file

    def test_profile_and_session_file_are_kept(
        self, fake, aws_dir, browser, failing_write
    ):
        session_file = self.write_dev_with_session_file(aws_dir)
        with pytest.raises(PermissionError):
            login(fake, storage_answer=True)
        config = read_config(aws_dir)
        assert f'login_session = {OLD_SESSION}' in config
        assert 'credential_daemon' not in config
        assert session_file.exists()
        # The credential daemon holds the new session; no profile names it
        # yet.
        assert (
            fake.credential('login.123456789012-role-Admin').kind == KIND_LOGIN
        )

    def test_signing_in_again_finishes_the_move(self, fake, aws_dir, browser):
        session_file = self.write_dev_with_session_file(aws_dir)
        update_config = ConfigFileWriter.update_config
        calls = []

        def fail_once(writer, new_values, config_filename):
            if new_values.get('credential_daemon') and not calls:
                calls.append(new_values)
                raise PermissionError('Permission denied')
            return update_config(writer, new_values, config_filename)

        with mock.patch.object(
            ConfigFileWriter,
            'update_config',
            autospec=True,
            side_effect=fail_once,
        ):
            with pytest.raises(PermissionError):
                login(fake, storage_answer=True)
            ask, ask_replace = login(fake, storage_answer=True)
        # The first run's write failed, so it saved no answer and the second
        # asks again. The same identity isn't asked about.
        assert ask.called
        assert not ask_replace.called
        config = read_config(aws_dir)
        assert 'credential_storage = daemon' in config
        assert 'credential_daemon = login.123456789012-role-Admin' in config
        assert 'login_session' not in config
        assert not session_file.exists()

    def test_new_profile_is_not_created(
        self, fake, aws_dir, browser, failing_write
    ):
        # credential_storage goes in the same write as credential_daemon,
        # so there's no stub that falls through to the host's role
        # (see test_stub_profile_falls_through_to_the_host_role).
        with pytest.raises(PermissionError):
            login(fake, profile='new', storage_answer=True)
        assert 'profile new' not in read_config(aws_dir)

    @pytest.mark.parametrize(
        'clear_error', [RuntimeError('unexpected'), KeyboardInterrupt()]
    )
    def test_a_failed_sign_out_keeps_the_original_error(
        self, fake, aws_dir, browser, failing_write, clear_error
    ):
        # Signing out the unused session fails too, with an error that
        # isn't the credential daemon's, or a second Ctrl-C. The write's
        # error is still the one raised.
        with mock.patch.object(
            CredentialDaemonClient,
            'logout',
            autospec=True,
            side_effect=clear_error,
        ) as clear:
            with pytest.raises(PermissionError):
                login(fake, profile='new', storage_answer=True)
        assert clear.called
        assert 'profile new' not in read_config(aws_dir)

    def test_new_profile_on_files_is_not_created(self, fake, aws_dir):
        update_config = ConfigFileWriter.update_config

        def fail_on_login_session(writer, new_values, config_filename):
            if new_values.get('login_session'):
                raise PermissionError('Permission denied')
            return update_config(writer, new_values, config_filename)

        with (
            mock.patch.object(
                ConfigFileWriter,
                'update_config',
                autospec=True,
                side_effect=fail_on_login_session,
            ),
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            with pytest.raises(PermissionError):
                login(fake, profile='new', storage_answer=False)
        assert 'profile new' not in read_config(aws_dir)

    def test_a_failure_after_the_profile_write_keeps_the_credential(
        self, fake, aws_dir, browser
    ):
        # The profile already names the new credential, so a failure
        # after its write mustn't sign it out.
        with mock.patch.object(
            CredentialStorageChooser,
            'mark_saved',
            autospec=True,
            side_effect=PermissionError('Permission denied'),
        ):
            with pytest.raises(PermissionError):
                login(fake, profile='new', storage_answer=True)
        name = 'login.123456789012-role-Admin'
        assert f'credential_daemon = {name}' in read_config(aws_dir)
        assert fake.credential(name).status == 'active'
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_new_profile_gets_both_keys_in_one_write(
        self, fake, aws_dir, browser
    ):
        update_config = ConfigFileWriter.update_config
        writes = []

        def record(writer, new_values, config_filename):
            writes.append(dict(new_values))
            return update_config(writer, new_values, config_filename)

        with mock.patch.object(
            ConfigFileWriter,
            'update_config',
            autospec=True,
            side_effect=record,
        ):
            login(fake, profile='new', storage_answer=True)
        new_profile = [w for w in writes if w['__section__'] == 'profile new']
        assert len(new_profile) == 1
        assert new_profile[0]['credential_storage'] == 'daemon'
        assert (
            new_profile[0]['credential_daemon']
            == 'login.123456789012-role-Admin'
        )


class TestSigningInAgain:
    def test_every_sign_in_tags_the_credential(self, fake, aws_dir, browser):
        # The bootstrap sends no tags, so a sign-in again keeps tags added
        # with creds, and the CLI adds its own after it.
        login(fake, storage_answer=True)
        assert fake.credential(ALICE).tags == CLI_TAGS
        fake.credential(ALICE).tags = {'team': 'x'}
        login(fake)
        bootstraps = [p for m, p in fake.calls if m == 'credential/bootstrap']
        assert len(bootstraps) == 2
        assert all('tags' not in params for params in bootstraps)
        tags = [p for m, p in fake.calls if m == 'credential/tag']
        assert tags == [{'credential': ALICE, 'set': CLI_TAGS}] * 2
        assert fake.credential(ALICE).tags == {'team': 'x', **CLI_TAGS}

    def test_a_stored_name_keeps_its_tags(self, fake, aws_dir, browser):
        # A credential the profile names, such as one made with creds.
        fake.seed('work', tags={'team': 'x'}, status=NO_SESSION)
        write_config(aws_dir, '[profile dev]\ncredential_daemon = work\n')
        login(fake)
        [params] = [p for m, p in fake.calls if m == 'credential/bootstrap']
        assert params['credential'] == 'work'
        assert 'tags' not in params
        assert fake.credential('work').tags == {'team': 'x', **CLI_TAGS}

    def test_a_failed_tag_only_warns(self, fake, aws_dir, browser, capsys):
        # The sign-in worked, so it still succeeds, and says how to tag it.
        fake.fail_next('credential/tag', 'INTERNAL_ERROR')
        _, _, rc = login(fake, storage_answer=True, return_rc=True)
        assert rc == 0
        assert fake.credential(ALICE).tags == {}
        assert f'credential_daemon = {ALICE}' in read_config(aws_dir)
        captured = capsys.readouterr()
        assert 'Signed in as' in captured.out
        assert captured.err.count("didn't tag") == 1
        assert (
            f"Signed in, but the credential daemon didn't tag '{ALICE}' "
            "created-by=aws-cli, so aws logout --all won't sign it out. To "
            f'tag it: creds tag set --credential {ALICE} created-by=aws-cli\n'
        ) in captured.err

    def test_no_question_and_no_move(self, fake, aws_dir, browser, capsys):
        login(fake, storage_answer=True)
        capsys.readouterr()
        ask, _ = login(fake)
        assert not ask.called
        out = capsys.readouterr().out
        assert 'Signed in as' in out
        assert 'Moved' not in out

    def test_profile_with_only_credential_daemon(self, fake, aws_dir, browser):
        write_config(
            aws_dir,
            '''
            [profile staging]
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        ask, _ = login(fake, profile='staging')
        assert not ask.called
        assert fake.credential('login.123456789012-role-Admin') is not None
        assert fake.credential('staging') is None

    def test_credentials_file_settings_are_ignored(
        self, fake, aws_dir, browser
    ):
        # credential_daemon and credential_storage count only in the config
        # file, so the profile is new to the credential daemon: the
        # question comes, and the answers go to the config file.
        write_config(aws_dir, '[profile staging]\n')
        (aws_dir / 'credentials').write_text(
            '[staging]\n'
            'credential_daemon = login.123456789012-role-Admin\n'
            'credential_storage = daemon\n'
        )
        ask, _ = login(fake, profile='staging', storage_answer=True)
        assert ask.called
        config = read_config(aws_dir)
        assert 'credential_storage = daemon' in config
        assert 'credential_daemon = login.123456789012-role-Admin' in config

    def test_an_indented_credential_daemon_is_a_config_error(
        self, fake, aws_dir, browser
    ):
        write_config(
            aws_dir,
            '''
            [profile staging]
            credential_daemon =
              foo = bar
            ''',
        )
        with pytest.raises(InvalidConfigError, match='not a single value'):
            login(fake, profile='staging')

    def test_credential_process_workaround_is_allowed(
        self, fake, aws_dir, browser, capsys
    ):
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_daemon = login.123456789012-role-Admin
            credential_process = aws configure export-credentials --profile dev
            ''',
        )
        login(fake)
        assert fake.credential('login.123456789012-role-Admin') is not None
        assert 'warning' not in capsys.readouterr().err.lower()

    def test_warns_about_another_credential_process(
        self, fake, aws_dir, browser, capsys
    ):
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_daemon = login.123456789012-role-Admin
            credential_process = /usr/local/bin/other-tool --profile dev
            ''',
        )
        login(fake)
        assert fake.credential('login.123456789012-role-Admin') is not None
        err = capsys.readouterr().err
        assert err.lower().count('warning') == 1
        assert (
            'warning: profile \'dev\' also has credential_process = '
            '/usr/local/bin/other-tool --profile dev.'
        ) in err
        assert 'older SDKs and tools use that line instead' in err
        assert 'credential_process = /usr/local/bin/other-tool' in (
            read_config(aws_dir)
        )

    def test_strips_control_characters_from_the_warning(
        self, fake, aws_dir, browser, capsys
    ):
        write_config(
            aws_dir,
            '[profile dev]\ncredential_daemon = login.123456789012-role-Admin\n'
            'credential_process = other-tool\x1b[2K --profile dev\n',
        )
        login(fake)
        err = capsys.readouterr().err
        assert '\x1b' not in err
        assert 'credential_process = other-tool[2K --profile dev.' in err

    def test_ignores_and_warns_about_leftover_keys(
        self, fake, aws_dir, browser, capsys
    ):
        # The credential daemon wins, so leftover keys are ignored, not
        # refused.
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_daemon = login.123456789012-role-Admin
            aws_access_key_id = AKIDLEFTOVER
            aws_secret_access_key = leftover-secret
            ''',
        )
        login(fake)
        assert (
            fake.credential('login.123456789012-role-Admin').status
            != NO_SESSION
        )
        err = capsys.readouterr().err
        assert err.lower().count('warning') == 1
        assert (
            'warning: profile \'dev\' also has access keys (aws_access_key_id). '
            'The AWS CLI ignores them'
        ) in err
        assert 'AKIDLEFTOVER' not in err
        assert 'leftover-secret' not in err
        assert 'aws_access_key_id = AKIDLEFTOVER' in read_config(aws_dir)

    def test_keys_without_credential_daemon_are_still_refused(
        self, fake, aws_dir, browser
    ):
        write_config(
            aws_dir,
            '[profile dev]\naws_access_key_id = AKID\n'
            'aws_secret_access_key = secret\n',
        )
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        assert 'already configured with Access Key credentials' in str(e.value)
        assert fake.credential('login.123456789012-role-Admin') is None

    def test_credential_daemon_in_the_credentials_file_doesnt_excuse_keys(
        self, fake, aws_dir, browser
    ):
        # credential_daemon counts only in the config file, so the keys
        # still win over a login session.
        write_config(aws_dir, '[profile dev]\nregion = us-west-2\n')
        (aws_dir / 'credentials').write_text(
            '[dev]\naws_access_key_id = AKID\n'
            'aws_secret_access_key = secret\n'
            'credential_daemon = login.123456789012-role-Admin\n'
        )
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        assert 'already configured with Access Key credentials' in str(e.value)
        assert fake.credential('login.123456789012-role-Admin') is None


class TestOlderCliLeftover:
    # An older CLI ran aws login on a profile already in the credential
    # daemon and wrote login_session and a session file beside
    # credential_daemon. A new CLI must warn and offer to delete the file,
    # not treat it as a first move.
    def write_leftover(self, fake, aws_dir):
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_storage = daemon
            credential_daemon = login.123456789012-role-Admin
            login_session = {OLD_SESSION}
            region = us-west-2
            ''',
        )
        cache = aws_dir / 'cache'
        cache.mkdir()
        session_file = cache / f'{generate_login_cache_key(OLD_SESSION)}.json'
        session_file.write_text(json.dumps({'accessToken': {}}))
        return session_file

    def test_nothing_is_reported_as_moved(
        self, fake, aws_dir, browser, capsys
    ):
        self.write_leftover(fake, aws_dir)
        login(fake, replace=False)
        assert 'Moved this profile' not in capsys.readouterr().out

    def test_file_is_kept_when_the_offer_is_declined(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        # The offer goes through the login handler's yes_no_choice, which
        # login() answers with replace.
        _, ask = login(fake, replace=False)
        assert ask.called
        assert session_file.exists()

    def test_file_is_not_deleted_silently_without_a_terminal(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        login(fake, tty=False)
        captured = capsys.readouterr()
        if not session_file.exists():
            # Deleting is allowed only with a warning the customer can see.
            assert 'older' in (captured.out + captured.err).lower()

    def test_yes_deletes_the_file_and_says_which(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        login(fake, replace=True)
        captured = capsys.readouterr()
        assert not session_file.exists()
        assert 'login_session' not in read_config(aws_dir)
        assert (
            'credential_daemon = login.123456789012-role-Admin'
            in read_config(aws_dir)
        )
        assert (
            'an older AWS CLI left a plaintext session file for \'dev\': '
            f'{session_file}' in captured.err
        )
        assert f'Deleted {session_file}.' in captured.out

    def test_login_session_goes_in_the_same_write_as_credential_daemon(
        self, fake, aws_dir, browser
    ):
        # The older CLI's session file is already gone.
        session_file = self.write_leftover(fake, aws_dir)
        session_file.unlink()
        writes = []
        real = ConfigFileWriter.update_config

        def record(writer, new_values, *args, **kwargs):
            writes.append(dict(new_values))
            return real(writer, new_values, *args, **kwargs)

        with mock.patch.object(ConfigFileWriter, 'update_config', record):
            login(fake, replace=False)
        dropped = [w for w in writes if 'login_session' in w]
        assert len(dropped) == 1
        assert dropped[0]['login_session'] is None
        assert 'credential_daemon' in dropped[0]
        assert 'login_session' not in read_config(aws_dir)

    def test_a_failed_write_leaves_login_session_and_the_profile(
        self, fake, aws_dir, browser
    ):
        session_file = self.write_leftover(fake, aws_dir)
        session_file.unlink()
        before = read_config(aws_dir)
        real = ConfigFileWriter.update_config

        def fail(writer, new_values, *args, **kwargs):
            if 'login_session' in new_values:
                raise OSError('No space left on device')
            return real(writer, new_values, *args, **kwargs)

        with (
            mock.patch.object(ConfigFileWriter, 'update_config', fail),
            pytest.raises(OSError),
        ):
            login(fake, replace=False)
        assert read_config(aws_dir) == before

    def test_no_keeps_login_session_for_the_older_cli(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        login(fake, replace=False)
        assert f'login_session = {OLD_SESSION}' in read_config(aws_dir)
        assert str(session_file) in capsys.readouterr().err

    def test_without_a_terminal_the_file_is_kept_with_a_warning(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        _, ask = login(fake, tty=False)
        err = capsys.readouterr().err
        assert not ask.called
        assert session_file.exists()
        assert str(session_file) in err
        assert 'aws logout --profile dev' in err

    def test_a_file_another_profile_uses_is_kept_without_asking(
        self, fake, aws_dir, browser, capsys
    ):
        session_file = self.write_leftover(fake, aws_dir)
        with open(aws_dir / 'config', 'a') as f:
            f.write(f'[profile other]\nlogin_session = {OLD_SESSION}\n')
        _, ask = login(fake, replace=True)
        assert not ask.called
        assert session_file.exists()
        assert 'Kept it, because \'other\' still uses it.' in (
            capsys.readouterr().err
        )

    def test_a_file_another_daemon_profile_names_is_kept_without_asking(
        self, fake, aws_dir, browser, capsys
    ):
        # dev2 is in the credential daemon too, but an older CLI still reads
        # the file through its login_session.
        session_file = self.write_leftover(fake, aws_dir)
        fake.seed('dev2')
        with open(aws_dir / 'config', 'a') as f:
            f.write(
                '[profile dev2]\n'
                'credential_storage = daemon\n'
                'credential_daemon = dev2\n'
                f'login_session = {OLD_SESSION}\n'
            )
        _, ask = login(fake, replace=True)
        assert not ask.called
        assert session_file.exists()
        config = read_config(aws_dir)
        assert config.count(f'login_session = {OLD_SESSION}') == 2
        assert 'Kept it, because \'dev2\' still uses it.' in (
            capsys.readouterr().err
        )

    def test_failed_delete_exits_1_and_keeps_login_session(
        self, fake, aws_dir, browser, capsys
    ):
        # The customer said yes, but the file couldn't be deleted.
        session_file = self.write_leftover(fake, aws_dir)
        with mock.patch(
            'awscli.customizations.login.login.os.remove',
            side_effect=PermissionError('Permission denied'),
        ):
            _, _, rc = login(fake, replace=True, return_rc=True)
        assert rc == 1
        assert session_file.exists()
        assert f'login_session = {OLD_SESSION}' in read_config(aws_dir)
        captured = capsys.readouterr()
        assert (
            f'Couldn\'t delete {session_file}: Permission denied. The '
            'plaintext session file is still there. Delete it by hand.'
        ) in captured.err
        assert 'Deleted' not in captured.out

    def test_deleted_file_exits_0(self, fake, aws_dir, browser):
        self.write_leftover(fake, aws_dir)
        _, _, rc = login(fake, replace=True, return_rc=True)
        assert not rc

    def test_no_file_means_no_warning(self, fake, aws_dir, browser, capsys):
        session_file = self.write_leftover(fake, aws_dir)
        session_file.unlink()
        _, ask = login(fake, replace=True)
        assert not ask.called
        assert 'older AWS CLI' not in capsys.readouterr().err
        assert 'login_session' not in read_config(aws_dir)


class TestIdentityChange:
    """Profiles signed in as one identity share its credential, as they
    share a session file. Signing one in as another identity changes
    only that profile, after the question asked for session files."""

    @pytest.fixture(autouse=True)
    def dev_and_staging_on_alice(self, fake, aws_dir):
        fake.seed(ALICE)
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_daemon = {ALICE}
            [profile staging]
            credential_daemon = {ALICE}
            ''',
        )
        fake.next_principal = BOB

    def profile_names(self, aws_dir):
        return {
            profile: Session(profile=profile)
            .get_scoped_config()
            .get('credential_daemon')
            for profile in ('dev', 'staging')
        }

    def test_replacing_needs_a_yes(self, fake, aws_dir, browser, capsys):
        _, ask = login(fake, replace=True)
        # The question asked for session files. The credential daemon's
        # rows don't say who a credential is signed in as, so its name
        # stands for it.
        assert ask.call_args_list == [
            mock.call(
                f'\nProfile dev is already configured to use session '
                f'{ALICE}. Do you want to overwrite it to use '
                f'{BOB} instead? (y/n): '
            )
        ]
        assert fake.credential(BOB_NAME).principal == BOB
        # A yes changes only dev; staging and its credential keep alice.
        assert self.profile_names(aws_dir) == {
            'dev': BOB_NAME,
            'staging': ALICE,
        }
        assert fake.credential(ALICE).principal == DEFAULT_PRINCIPAL
        assert fake.credential(ALICE).status == 'active'
        assert f'Signed in as {BOB}' in capsys.readouterr().out

    def test_no_keeps_the_profile_and_signs_the_new_one_out(
        self, fake, aws_dir, browser, capsys
    ):
        login(fake, replace=False)
        assert self.profile_names(aws_dir) == {'dev': ALICE, 'staging': ALICE}
        assert_cleared(fake, BOB_NAME)
        assert fake.credential(ALICE).status == 'active'
        out = capsys.readouterr().out
        assert f'Kept \'dev\' signed in as {ALICE}.' in out
        assert 'Use "--profile dev"' not in out

    def test_no_keeps_a_credential_another_profile_uses(
        self, fake, aws_dir, browser
    ):
        fake.seed(BOB_NAME, principal=BOB)
        with open(aws_dir / 'config', 'a') as f:
            f.write(f'[profile ops]\ncredential_daemon = {BOB_NAME}\n')
        login(fake, replace=False)
        assert fake.credential(BOB_NAME).status == 'active'
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_no_keeps_a_credential_signed_in_before(
        self, fake, aws_dir, browser
    ):
        # Signed in as bob before, so something may use it.
        fake.seed(BOB_NAME, principal=BOB)
        login(fake, replace=False)
        assert fake.credential(BOB_NAME).status == 'active'
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_failed_sign_out_after_no_exits_1(
        self, fake, aws_dir, browser, capsys
    ):
        fake.fail_next('credential/logout', 'INTERNAL')
        _, _, rc = login(fake, replace=False, return_rc=True)
        assert rc == 1
        err = capsys.readouterr().err
        assert (
            f'still in the credential daemon as \'{BOB_NAME}\': Injected INTERNAL '
            '(INTERNAL). Run \'aws logout --all\' to sign it out.\n'
        ) in err

    def test_without_a_terminal_it_fails_and_signs_the_new_one_out(
        self, fake, aws_dir, browser, capsys
    ):
        # As with session files, a script fails instead of keeping the
        # old identity and exiting 0.
        with pytest.raises(ConfigurationError) as e:
            login(fake, tty=False)
        assert str(e.value) == (
            f'Profile dev is already configured to use session '
            f'{ALICE}. Run \'aws login\' in a terminal to '
            f'overwrite it to use {BOB}. Profile \'dev\' wasn\'t changed.'
        )
        assert self.profile_names(aws_dir) == {'dev': ALICE, 'staging': ALICE}
        assert_cleared(fake, BOB_NAME)
        assert fake.credential(ALICE).status == 'active'
        assert 'Kept' not in capsys.readouterr().out

    def test_without_a_terminal_a_credential_in_use_stays(
        self, fake, aws_dir, browser
    ):
        fake.seed(BOB_NAME, principal=BOB)
        with pytest.raises(ConfigurationError):
            login(fake, tty=False)
        assert fake.credential(BOB_NAME).status == 'active'
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_same_identity_refreshes_without_asking(
        self, fake, aws_dir, browser
    ):
        before = fake.credential(ALICE)
        fake.next_principal = DEFAULT_PRINCIPAL
        config = read_config(aws_dir)
        _, ask = login(fake)
        assert not ask.called
        assert fake.credential(ALICE) is not before
        assert fake.credential(ALICE).status == 'active'
        assert read_config(aws_dir) == config
        assert 'credential/logout' not in [m for m, _ in fake.calls]

    def test_control_characters_are_stripped_from_principals(
        self, fake, aws_dir, browser, capsys
    ):
        fake.next_principal = f'{BOB}\x1b[2K\r'
        _, ask = login(fake, replace=True)
        assert f'use {BOB}[2K  instead?' in ask.call_args[0][0]
        assert f'Signed in as {BOB}[2K \n' in capsys.readouterr().out

    def test_a_signed_out_credential_a_profile_names_still_asks(
        self, fake, aws_dir, browser
    ):
        # Signed out by aws logout: the profile still uses that identity,
        # as login_session stays after aws logout.
        fake.credential(ALICE).status = NO_SESSION
        _, ask = login(fake, replace=False)
        assert ask.called
        assert self.profile_names(aws_dir)['dev'] == ALICE

    def test_a_credential_credential_daemon_lost_still_asks(
        self, fake, aws_dir, browser
    ):
        # Its name stands for the identity the credential daemon can't name
        # any more.
        fake.reset()
        fake.next_principal = BOB
        _, ask = login(fake, replace=False)
        assert ALICE in ask.call_args[0][0]
        assert self.profile_names(aws_dir)['dev'] == ALICE

    @pytest.mark.parametrize('principal', [None, '', 7])
    def test_a_row_that_doesnt_say_who_still_asks(
        self, fake, aws_dir, browser, principal
    ):
        # Like a credential the credential daemon lost, its name stands for
        # the identity.
        fake.credential(ALICE).principal = principal
        fake.next_principal = BOB
        _, ask = login(fake, replace=False)
        assert ask.call_count == 1
        assert ALICE in ask.call_args[0][0]
        assert self.profile_names(aws_dir)['dev'] == ALICE
        assert_cleared(fake, BOB_NAME)

    def test_a_row_that_doesnt_say_who_without_a_terminal_is_a_no(
        self, fake, aws_dir, browser
    ):
        fake.credential(ALICE).principal = None
        fake.next_principal = BOB
        with pytest.raises(ConfigurationError):
            login(fake, tty=False)
        assert self.profile_names(aws_dir)['dev'] == ALICE
        assert_cleared(fake, BOB_NAME)

    def test_a_per_profile_name_moves_to_the_identity_name(
        self, fake, aws_dir, browser
    ):
        # A per-profile name (login.<profile>): the credential daemon's
        # rows don't say who it's signed in as, so the other name is asked
        # about, and a yes gives the profile the identity name.
        fake.seed('login.dev')
        write_config(aws_dir, '[profile dev]\ncredential_daemon = login.dev\n')
        fake.next_principal = DEFAULT_PRINCIPAL
        _, ask = login(fake, replace=True)
        assert 'use session login.dev.' in ask.call_args[0][0]
        assert f'credential_daemon = {ALICE}' in read_config(aws_dir)


class TestNamedByIdentity:
    def test_a_name_clash_with_another_identity_needs_approval(
        self, fake, aws_dir, browser
    ):
        # Two identities whose names clean up to the same text: the
        # credential daemon holds the replace for approval, and
        # nothing is saved, the storage answer included.
        fake.seed(ALICE, principal=BOB)
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        [request_id] = fake.approval_requests()
        assert f'sudo creds request approve {request_id}' in str(e.value)
        assert fake.credential(ALICE).principal == BOB
        assert read_config(aws_dir) == ''
        # Nothing was saved, so nothing is tagged.
        assert 'credential/tag' not in dict(fake.calls)

    @pytest.mark.parametrize('name', [None, 'dev', 'keys.dev', '../x'])
    def test_a_name_that_isnt_a_login_name_is_refused(
        self, fake, aws_dir, browser, name
    ):
        bootstrap = CredentialDaemonClient.bootstrap

        def other_name(self, *args, **kwargs):
            return dict(bootstrap(self, *args, **kwargs), credential=name)

        with (
            mock.patch.object(CredentialDaemonClient, 'bootstrap', other_name),
            pytest.raises(CredentialDaemonProtocolError) as e,
        ):
            login(fake, storage_answer=True)
        assert 'credential_daemon' not in read_config(aws_dir)
        message = str(e.value)
        assert "Profile 'dev' wasn't changed." in message
        if name in ('dev', 'keys.dev'):
            # The credential daemon has nothing under that name here, so
            # nothing was signed out.
            assert message.endswith(
                f'The credential daemon has no credential named \'{name}\'.'
            )
        else:
            # A name that isn't valid can't be cleared or printed.
            assert message.endswith(
                "Remove the new session in the credential daemon if "
                "it's still there."
            )

    def test_a_result_without_an_identity_is_refused(
        self, fake, aws_dir, browser
    ):
        bootstrap = CredentialDaemonClient.bootstrap

        def no_identity(self, *args, **kwargs):
            result = bootstrap(self, *args, **kwargs)
            result.pop('identity')
            return result

        with (
            mock.patch.object(
                CredentialDaemonClient, 'bootstrap', no_identity
            ),
            pytest.raises(CredentialDaemonProtocolError) as e,
        ):
            login(fake, storage_answer=True)
        assert 'credential_daemon' not in read_config(aws_dir)
        message = str(e.value)
        assert 'valid aws login credential name and identity' in message
        # The new session wasn't in use before, so it was signed out.
        assert message.endswith(
            f'The new session (\'{ALICE}\') was signed out of the credential '
            'daemon.'
        )
        assert fake.credential(ALICE).status == NO_SESSION

    def _store_under(self, fake, name):
        bootstrap = CredentialDaemonClient.bootstrap

        def other_name(client, *args, **kwargs):
            # The credential daemon stored the session under a name aws login
            # doesn't use.
            kwargs.pop('name_prefix', None)
            return bootstrap(client, *args, name=name, **kwargs)

        return mock.patch.object(
            CredentialDaemonClient, 'bootstrap', other_name
        )

    def test_an_unexpected_name_is_signed_out(self, fake, aws_dir, browser):
        with (
            self._store_under(fake, 'dev'),
            pytest.raises(CredentialDaemonProtocolError) as e,
        ):
            login(fake, storage_answer=True)
        # The session the credential daemon stored is signed out, and the
        # error says so.
        assert fake.credential('dev').status == 'no_session'
        assert str(e.value).endswith(
            'The new session (\'dev\') was signed out of the credential daemon.'
        )
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_an_unexpected_name_that_cant_be_signed_out(
        self, fake, aws_dir, browser
    ):
        with (
            self._store_under(fake, 'dev'),
            mock.patch.object(
                CredentialDaemonClient,
                'logout',
                side_effect=CredentialDaemonNotRunningError(
                    error_msg='The credential daemon stopped'
                ),
            ),
            pytest.raises(CredentialDaemonProtocolError) as e,
        ):
            login(fake, storage_answer=True)
        # Still signed in, named, and how to remove it; non-zero.
        assert fake.credential('dev').status == 'active'
        assert str(e.value).endswith(
            'The new session is still signed in to the credential '
            "daemon as 'dev', because it couldn't be signed out: "
            'The credential daemon '
            'stopped. Remove it in the credential daemon.'
        )
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_an_unexpected_name_signed_in_before_is_left(
        self, fake, aws_dir, browser
    ):
        # A credential signed in before the sign-in is in use.
        fake.seed('dev')
        with (
            self._store_under(fake, 'dev'),
            pytest.raises(CredentialDaemonProtocolError) as e,
        ):
            login(fake, storage_answer=True)
        assert fake.credential('dev').status == 'active'
        assert str(e.value).endswith(
            "'dev' was signed in to the credential daemon before, so it "
            "wasn't signed out."
        )


class TestLeftoverCredential:
    """A signed-out credential a failed sign-in left.

    credential/logout keeps the entry and its principal. Another identity
    gets its own credential, so the leftover is never replaced.
    """

    def leave_alice(self, fake):
        fake.fail_next('credential/get', 'CREDENTIAL_NOT_FOUND')
        with pytest.raises(ConfigurationError):
            login(fake, profile='new', storage_answer=True)
        assert_cleared(fake, ALICE)
        fake.next_principal = BOB

    def test_signing_in_as_someone_else_does_not_ask(
        self, fake, aws_dir, browser, capsys
    ):
        self.leave_alice(fake)
        capsys.readouterr()
        _, ask = login(fake, profile='new', storage_answer=True)
        assert not ask.called
        out = capsys.readouterr().out
        assert 'overwrite' not in out
        assert 'Kept new' not in out
        assert f'Signed in as {BOB}' in out
        assert fake.credential(BOB_NAME).principal == BOB
        assert_cleared(fake, ALICE)
        assert f'credential_daemon = {BOB_NAME}' in read_config(aws_dir)

    def test_without_a_terminal_it_does_not_ask(
        self, fake, aws_dir, browser, capsys
    ):
        self.leave_alice(fake)
        capsys.readouterr()
        _, ask = login(
            fake,
            profile='new',
            tty=False,
            environ={'AWS_CREDENTIAL_STORAGE': 'daemon'},
        )
        assert not ask.called
        assert 'Run \'aws login\' in a terminal' not in capsys.readouterr().err
        assert fake.credential(BOB_NAME).principal == BOB
        assert f'credential_daemon = {BOB_NAME}' in read_config(aws_dir)

    def test_a_profile_on_the_leftover_keeps_it(self, fake, aws_dir, browser):
        self.leave_alice(fake)
        write_config(
            aws_dir, f'[profile alias]\ncredential_daemon = {ALICE}\n'
        )
        _, ask = login(fake, profile='new', storage_answer=True)
        assert not ask.called
        assert fake.credential(ALICE).principal == DEFAULT_PRINCIPAL
        config = read_config(aws_dir)
        assert config.count(f'credential_daemon = {ALICE}\n') == 1
        assert config.count(f'credential_daemon = {BOB_NAME}\n') == 1


class TestCredentialDaemonErrors:
    """The credential daemon's error reaches the customer when credential/list
    fails."""

    def assert_unchanged(self, aws_dir, browser):
        assert not browser.called
        assert read_config(aws_dir) == (
            '[profile dev]\ncredential_storage = daemon\n'
        )

    @pytest.fixture(autouse=True)
    def daemon_profile(self, aws_dir):
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')

    def test_an_internal_error(self, fake, aws_dir, browser):
        fake.fail_next(
            'credential/list', 'INTERNAL', 'The credential daemon broke'
        )
        with pytest.raises(CredentialDaemonError) as e:
            login(fake)
        assert 'The credential daemon broke' in str(e.value)
        self.assert_unchanged(aws_dir, browser)

    def test_config_that_doesnt_validate(self, fake, aws_dir, browser):
        # credsd refuses credential/list until the caller's configuration
        # validates again, so the sign-in stops before the browser.
        fake.set_config_invalid('bad tag key')
        with pytest.raises(CredentialDaemonError) as e:
            login(fake)
        assert e.value.code == 'CONFIG_INVALID'
        assert str(e.value) == (
            'caller configuration does not validate: bad tag key; fix it, '
            'then run: creds revalidate (CONFIG_INVALID)'
        )
        self.assert_unchanged(aws_dir, browser)
        assert [m for m, _ in fake.calls] == ['credential/list']


class TestWhereTheCredentialDaemonDoesntRun:
    """Such as Windows: a profile that uses the credential daemon is
    refused before the browser, with how to use files for it, and never
    falls back to files."""

    @pytest.fixture(autouse=True)
    def not_here(self):
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            yield

    @pytest.mark.parametrize(
        'config, environ, way_out',
        [
            (
                '[profile dev]\ncredential_daemon = login.dev\n',
                {},
                'To use it on this machine, use files for it: remove '
                'credential_daemon from the profile and any '
                'credential_storage = daemon (or set it to file), then sign '
                "in again or enter its keys with 'aws configure'.",
            ),
            (
                '[profile dev]\ncredential_storage = daemon\n',
                {},
                'To use files for it, set credential_storage = file in the '
                'profile.',
            ),
            (
                '[profile dev]\n',
                {'AWS_CREDENTIAL_STORAGE': 'daemon'},
                'To use files for it, run the command again with '
                'AWS_CREDENTIAL_STORAGE=file.',
            ),
        ],
    )
    def test_refused_with_how_to_use_files(
        self, fake, aws_dir, browser, config, environ, way_out
    ):
        write_config(aws_dir, config)
        with mock.patch.dict('os.environ', environ):
            with pytest.raises(ConfigurationError) as e:
                login(fake, environ=environ)
        assert str(e.value) == (
            "The credential daemon isn't available on this platform, so "
            f"profile 'dev' can't be used here. {way_out}"
        )
        assert not browser.called
        assert fake.calls == []
        assert read_config(aws_dir) == config

    @pytest.mark.parametrize(
        'config, environ, followed, followed_environ',
        [
            (
                '[profile dev]\ncredential_daemon = login.dev\n'
                'credential_storage = daemon\n',
                {},
                '[profile dev]\ncredential_storage = file\n',
                {},
            ),
            (
                '[profile dev]\ncredential_daemon = login.dev\n'
                'credential_storage = daemon\n',
                {},
                '[profile dev]\n',
                {},
            ),
            (
                '[profile dev]\ncredential_daemon = login.dev\n',
                {'AWS_CREDENTIAL_STORAGE': 'daemon'},
                '[profile dev]\n',
                {'AWS_CREDENTIAL_STORAGE': 'file'},
            ),
        ],
    )
    def test_following_the_hint_signs_in_with_files(
        self,
        fake,
        aws_dir,
        browser,
        config,
        environ,
        followed,
        followed_environ,
    ):
        # Removing credential_daemon alone would leave credential_storage
        # (or AWS_CREDENTIAL_STORAGE) saying daemon, and a second refusal.
        write_config(aws_dir, config)
        with mock.patch.dict('os.environ', environ):
            with pytest.raises(ConfigurationError) as e:
                login(fake, environ=environ)
        assert 'remove credential_daemon from the profile' in str(e.value)
        if environ:
            assert 'AWS_CREDENTIAL_STORAGE=file' in str(e.value)
        else:
            assert 'credential_storage = daemon (or set it to file)' in str(
                e.value
            )
        write_config(aws_dir, followed)
        fetch, sign_in_uri, auth_code = files_sign_in()
        with (
            mock.patch.dict('os.environ', followed_environ),
            fetch,
            sign_in_uri,
            auth_code,
        ):
            _, _, rc = login(fake, environ=followed_environ, return_rc=True)
        assert rc == 0
        assert f'login_session = {DEFAULT_PRINCIPAL}' in read_config(aws_dir)


class TestSsoProfileWithoutRole:
    """A profile with sso_session and neither sso_account_id nor
    sso_role_name signs in to files without the question: tools skip
    credential_daemon for it. Its sso-session's credential_storage isn't
    read."""

    CONFIG = """
        [profile ci]
        sso_session = acme

        [profile readonly]
        sso_session = acme
        sso_account_id = 111111111111
        sso_role_name = ReadOnly
        credential_daemon = sso.acme

        [sso-session acme]
        sso_start_url = https://acme.awsapps.com/start
        sso_region = us-east-1
        credential_storage = daemon
        """
    NOTE = (
        "Note: Profile 'ci' has sso_session without an account or role, so "
        "the credential daemon can't serve its credentials. They're stored "
        'in ~/.aws.\n'
    )

    def sign_in(self, fake, **kwargs):
        fetch, sign_in_uri, auth_code = files_sign_in()
        with fetch, sign_in_uri, auth_code:
            return login(fake, profile='ci', return_rc=True, **kwargs)

    def test_files_without_the_question(self, fake, aws_dir, capsys):
        write_config(aws_dir, self.CONFIG)
        for _ in range(2):
            # Not asked the second time either: no answer is needed.
            ask, _, rc = self.sign_in(fake, storage_answer=True)
            assert rc == 0
            assert not ask.called
            assert capsys.readouterr().err.count(self.NOTE) == 1
        config = read_config(aws_dir)
        assert config.startswith(
            '\n[profile ci]\nsso_session = acme\n'
            f'login_session = {DEFAULT_PRINCIPAL}\n'
        )
        assert config.count('credential_storage') == 1
        assert config.count('credential_daemon') == 1
        assert not any(
            method == 'credential/bootstrap' for method, _ in fake.calls
        )

    @pytest.mark.parametrize('stopped', [False, True])
    def test_its_credential_daemon_is_left_alone(self, fake, aws_dir, stopped):
        # aws sso login wrote it: sso.acme is the session's credential,
        # which tools skip for ci, so the sign-in neither asks the daemon
        # nor clears it.
        fake.seed('sso.acme', kind=KIND_SSO)
        config = self.CONFIG.replace(
            'sso_session = acme\n',
            'sso_session = acme\n        credential_daemon = sso.acme\n',
            1,
        )
        write_config(aws_dir, config)
        if stopped:
            fake.stop()
        _, _, rc = self.sign_in(fake, storage_answer=True)
        assert rc == 0
        assert read_config(aws_dir).startswith(
            '\n[profile ci]\nsso_session = acme\n'
            'credential_daemon = sso.acme\n'
            f'login_session = {DEFAULT_PRINCIPAL}\n'
        )
        if not stopped:
            assert fake.calls == []
            assert fake.credential('sso.acme') is not None

    def test_no_note_without_a_terminal(self, fake, aws_dir, capsys):
        write_config(aws_dir, self.CONFIG)
        _, _, rc = self.sign_in(fake, tty=False)
        assert rc == 0
        assert 'Note:' not in capsys.readouterr().err

    def test_a_stopped_daemon_doesnt_fail_it(self, fake, aws_dir):
        # The checks before the prompts agree with the chooser.
        write_config(aws_dir, self.CONFIG)
        fake.stop()
        _, _, rc = self.sign_in(fake, storage_answer=True)
        assert rc == 0
        assert f'login_session = {DEFAULT_PRINCIPAL}' in read_config(aws_dir)

    def test_daemon_from_the_variable_is_refused(self, fake, aws_dir, browser):
        write_config(aws_dir, self.CONFIG)
        before = read_config(aws_dir)
        environ = {'AWS_CREDENTIAL_STORAGE': 'daemon'}
        with pytest.raises(ConfigurationError) as e:
            login(fake, profile='ci', environ=environ)
        assert str(e.value) == (
            "Profile 'ci' has sso_session without an account or role, so the "
            "credential daemon can't serve its credentials. Nothing was "
            'changed. To store them in files, run the command again with '
            'AWS_CREDENTIAL_STORAGE=file.'
        )
        assert read_config(aws_dir) == before
        assert not browser.called
        assert fake.calls == []

    def test_control_characters_are_stripped(self, fake, aws_dir, capsys):
        write_config(
            aws_dir,
            '[profile "c\x1b[31mi"]\nsso_session = acme\n'
            '[sso-session acme]\nsso_start_url = https://x\n'
            'sso_region = us-east-1\n',
        )
        fetch, sign_in_uri, auth_code = files_sign_in()
        with fetch, sign_in_uri, auth_code:
            login(fake, profile='c\x1b[31mi')
        err = capsys.readouterr().err
        assert "Profile 'c[31mi' has sso_session" in err
        assert '\x1b' not in err


class TestRedirectPort:
    """--redirect-port goes to the credential daemon, which listens for the
    browser's redirect, as the file sign-in uses it."""

    def bootstrap_provider(self, fake):
        [params] = [
            params
            for method, params in fake.calls
            if method == 'credential/bootstrap'
        ]
        return params['provider']

    def test_goes_to_credential_daemon(self, fake, aws_dir, browser):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        login(fake, args=['--redirect-port', str(port)], storage_answer=True)
        assert self.bootstrap_provider(fake)['callback_port'] == port
        assert fake.credential('login.123456789012-role-Admin') is not None

    def test_left_out_without_the_flag(self, fake, aws_dir, browser):
        login(fake, storage_answer=True)
        assert 'callback_port' not in self.bootstrap_provider(fake)

    def test_left_out_with_remote(self, fake, aws_dir, capsys):
        # A remote sign-in has no redirect to listen for.
        login(
            fake,
            args=['--remote', '--redirect-port', '8400'],
            storage_answer=True,
            codes=['abc'],
        )
        assert 'callback_port' not in self.bootstrap_provider(fake)

    @pytest.mark.parametrize('port', ['80', '1023'])
    @pytest.mark.parametrize(
        'config, environ',
        [
            ('[profile dev]\ncredential_storage = daemon\n', {}),
            (
                '[profile dev]\ncredential_daemon = login.123456789012-role-Admin\n',
                {},
            ),
            ('', {'AWS_CREDENTIAL_STORAGE': 'daemon'}),
        ],
    )
    def test_below_1024_is_refused_before_anything_changes(
        self, fake, aws_dir, browser, port, config, environ
    ):
        # The credential daemon refuses it with an error naming callback_port,
        # a field the customer never typed. Nothing is saved and the
        # credential daemon isn't called.
        write_config(aws_dir, config)
        before = (aws_dir / 'config').read_bytes()
        with pytest.raises(ParamValidationError) as e:
            login(
                fake,
                args=['--redirect-port', port],
                storage_answer=True,
                environ=environ,
            )
        assert str(e.value) == (
            '--redirect-port must be between 1024 and 65535 when the '
            'credential daemon signs you in.'
        )
        assert (aws_dir / 'config').read_bytes() == before
        assert fake.calls == []
        assert not browser.called

    @pytest.mark.parametrize(
        'config',
        [
            '[profile dev]\ncredential_daemon = login.123456789012-role-Admin\n',
            '[profile dev]\ncredential_storage = daemon\n',
        ],
    )
    def test_below_1024_is_refused_before_the_region_prompt(
        self, fake, aws_dir, browser, config
    ):
        # The profile has no region, so the sign-in would ask for one. The
        # port error comes first, so nothing is asked.
        write_config(aws_dir, config)
        with (
            mock.patch.object(
                LoginCommand,
                '_prompt_for_region',
                side_effect=AssertionError('prompted'),
            ),
            pytest.raises(ParamValidationError) as e,
        ):
            login(
                fake,
                args=['--redirect-port', '80'],
                parsed_globals=Namespace(
                    region=None, endpoint_url=None, verify_ssl=None
                ),
            )
        assert str(e.value) == (
            '--redirect-port must be between 1024 and 65535 when the '
            'credential daemon signs you in.'
        )
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 252
        assert fake.calls == []
        assert not browser.called
        assert read_config(aws_dir) == config

    def test_below_1024_skips_the_storage_question(self, fake, aws_dir):
        # The credential daemon can't sign in on that port, so the undecided
        # profile signs in with files, and its answer stays unsaved.
        write_config(aws_dir, '[profile dev]\nregion = us-west-2\n')
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch(
                'awscli.customizations.login.login.AuthCodeFetcher'
            ) as fetcher,
        ):
            ask, _ = login(
                fake, args=['--redirect-port', '80'], storage_answer=True
            )
        fetcher.assert_called_once_with(redirect_port=80)
        assert not ask.called
        assert fake.calls == []
        assert 'credential_storage' not in read_config(aws_dir)

    def test_files_keep_todays_range(self, fake, aws_dir):
        # The file sign-in takes 1-65535.
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch(
                'awscli.customizations.login.login.AuthCodeFetcher'
            ) as fetcher,
        ):
            login(fake, args=['--redirect-port', '80'], storage_answer=False)
        fetcher.assert_called_once_with(redirect_port=80)
        assert fake.credential('login.123456789012-role-Admin') is None

    def test_out_of_range_keeps_todays_error(self, fake, aws_dir):
        with pytest.raises(ParamValidationError) as e:
            login(fake, args=['--redirect-port', '0'], storage_answer=True)
        assert str(e.value) == (
            'Invalid value for --redirect-port. Value must be between 1 and '
            '65535.'
        )

    def test_remote_ignores_the_port(self, fake, aws_dir):
        # A remote sign-in sends no port, so none is checked.
        login(
            fake,
            args=['--remote', '--redirect-port', '80'],
            storage_answer=True,
            codes=['abc'],
        )
        assert fake.credential('login.123456789012-role-Admin') is not None


class TestRemote:
    def test_prints_the_url_and_reads_the_code(
        self, fake, aws_dir, browser, capsys
    ):
        read_input = mock.Mock(return_value='abc')
        login(
            fake, args=['--remote'], storage_answer=True, read_input=read_input
        )
        assert not browser.called
        out = capsys.readouterr().out
        assert 'https://us-west-2.signin.aws.amazon.com/' in out
        # The prompt the file sign-in shows.
        read_input.assert_called_once_with(REMOTE_PROMPT)
        assert fake.credential('login.123456789012-role-Admin') is not None

    def test_sends_the_code_credential_daemon_asks_for(self, fake, aws_dir):
        login(fake, args=['--remote'], storage_answer=True, codes=[' abc\n'])
        [answer] = [p for m, p in fake.calls if m.endswith('/respond')]
        # The code itself is a secret, so the fake only records its field.
        assert answer == {'selection': '<redacted>'}

    @pytest.mark.parametrize(
        'code, message',
        [
            # Not base64: the credential daemon fails it at decode.
            ('invalid-1', 'that is not the value Sign-In displayed'),
            # Base64, but not this sign-in's state.
            ('invalid-code', 'start over'),
        ],
    )
    def test_a_bad_code_ends_the_sign_in(self, fake, aws_dir, code, message):
        # One code, as with files; the credential daemon says what was wrong.
        read_input = mock.Mock(side_effect=[code, 'abc'])
        with pytest.raises(CredentialDaemonError) as e:
            login(
                fake,
                args=['--remote'],
                storage_answer=True,
                read_input=read_input,
            )
        assert e.value.code == 'PROVIDER_UNAVAILABLE'
        assert message in str(e.value)
        # No second prompt.
        read_input.assert_called_once_with(REMOTE_PROMPT)
        assert fake.credential('login.123456789012-role-Admin') is None
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_a_late_code_times_out(self, aws_dir):
        # The credential daemon gives up waiting for the code; nothing is
        # saved.
        def slow_paste(prompt):
            time.sleep(0.5)
            return 'abc'

        with FakeCredentialDaemon(auth_timeout=0.2) as fake:
            with pytest.raises(CredentialDaemonError) as e:
                login(
                    fake,
                    args=['--remote'],
                    storage_answer=True,
                    read_input=mock.Mock(side_effect=slow_paste),
                )
            assert e.value.code == 'AUTH_TIMEOUT'
            assert fake.credential('login.123456789012-role-Admin') is None
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_a_sign_in_url_without_remote_support_is_refused(self):
        # A credential daemon without --remote ignores it and sends a
        # same-device URL that can't finish on this host.
        read_input = mock.Mock()
        handler = CredentialDaemonSignInHandler(
            remote=True, read_input=read_input
        )
        with pytest.raises(CredentialDaemonProtocolError) as e:
            handler({'type': 'authorize_url', 'url': 'https://example.com'})
        assert str(e.value) == (
            'This version of the credential daemon doesn\'t support \'aws '
            'login --remote\'. Update it, or run \'aws login\' without --remote.'
        )
        assert not read_input.called

    def test_no_code_cancels_the_sign_in(self, fake, aws_dir):
        with pytest.raises(LoginAuthorizationCodeError):
            login(
                fake,
                args=['--remote'],
                storage_answer=True,
                codes=['  '],
            )
        assert fake.credential('login.123456789012-role-Admin') is None
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_no_code_is_asked_for_without_remote(self):
        read_input = mock.Mock()
        handler = CredentialDaemonSignInHandler(
            remote=False, read_input=read_input
        )
        with pytest.raises(CredentialDaemonProtocolError) as e:
            handler({'type': 'authorize_code', 'url': 'https://example.com'})
        assert 'isn\'t --remote' in str(e.value)
        assert not read_input.called

    def test_end_of_input_cancels_the_sign_in(self, fake, aws_dir):
        # stdin closes before a code is entered.
        with pytest.raises(EOFError):
            login(
                fake,
                args=['--remote'],
                storage_answer=True,
                codes=[EOFError()],
            )
        assert fake.credential('login.123456789012-role-Admin') is None
        assert 'credential_daemon' not in read_config(aws_dir)


class TestSignInWithoutAURL:
    @pytest.mark.parametrize('url', [None, '', 5, {'a': 1}, '\x1b'])
    @pytest.mark.parametrize(
        'kind, remote',
        [('authorize_url', False), ('authorize_code', True)],
    )
    def test_is_refused_before_anything_is_shown(
        self, capsys, kind, remote, url
    ):
        # Otherwise the customer is told to open no page, and the sign-in
        # waits until the credential daemon gives up.
        open_browser = mock.Mock()
        read_input = mock.Mock()
        handler = CredentialDaemonSignInHandler(
            remote=remote, open_browser=open_browser, read_input=read_input
        )
        progress = {'type': kind}
        if url is not None:
            progress['url'] = url
        with pytest.raises(CredentialDaemonProtocolError) as e:
            handler(progress)
        assert str(e.value) == (
            'The credential daemon sent a URL sign-in without a URL.'
        )
        assert not open_browser.called
        assert not read_input.called
        out = capsys.readouterr()
        assert out.out == ''
        assert out.err == ''

    def test_exits_255(self):
        handler = CredentialDaemonSignInHandler(remote=False)
        with pytest.raises(CredentialDaemonProtocolError) as e:
            handler({'type': 'authorize_url'})
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 255


def _identity(arn):
    # credsd's identity object.
    return {
        'arn': arn,
        'partition': 'aws',
        'account': '123456789012',
        'kind': 'role',
        'name': 'Admin',
        'session': arn.rsplit('/', 1)[-1],
    }


class TestIdentityRecordedByCredentialDaemon:
    """As in credsd, the credential daemon records who signed in, names
    aws login credentials after the account and role, and holds a replace
    as another account or role, or over a credential with no record, for
    approval. The CLI shows its message and exits 253."""

    def test_same_role_in_a_new_session_isnt_asked_about(
        self, fake, aws_dir, browser
    ):
        fake.seed(ALICE)
        write_config(aws_dir, f'[profile dev]\ncredential_daemon = {ALICE}\n')
        config = read_config(aws_dir)
        fake.next_principal = DEFAULT_PRINCIPAL.replace('/alice', '/alice-2')
        _, ask = login(fake)
        assert not ask.called
        assert fake.approval_requests() == []
        assert read_config(aws_dir) == config
        assert fake.credential(ALICE).principal == fake.next_principal

    def test_another_role_gets_its_own_credential_and_the_question(
        self, fake, aws_dir, browser
    ):
        fake.seed(ALICE)
        write_config(aws_dir, f'[profile dev]\ncredential_daemon = {ALICE}\n')
        fake.next_principal = BOB
        _, ask = login(fake, replace=True)
        assert ask.call_count == 1
        assert fake.approval_requests() == []
        assert f'credential_daemon = {BOB_NAME}' in read_config(aws_dir)
        assert fake.credential(ALICE).principal == DEFAULT_PRINCIPAL

    @pytest.mark.parametrize('recorded', [BOB, None])
    def test_a_stored_name_held_for_approval_exits_253(
        self, fake, aws_dir, browser, capsys, recorded
    ):
        # Another account or role on record, or none (a credential made
        # before credsd recorded who signed in).
        fake.seed('work', principal=recorded)
        config = '[profile dev]\ncredential_daemon = work\n'
        write_config(aws_dir, config)
        with pytest.raises(ConfigurationError) as e:
            login(fake, replace=True)
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 253
        # The approver sees both identities.
        challenge = e.value.__cause__.data['challenge']
        was = 'no recorded sign-in'
        if recorded:
            was = 'role ReadOnly in account 123456789012 (aws)'
        assert challenge['description'].endswith(f'; it was {was}')
        assert str(e.value).endswith(
            "\nOnce it's approved, run this command again. Profile 'dev' "
            "wasn't changed."
        )
        assert read_config(aws_dir) == config
        assert fake.credential('work').principal == recorded

    def test_an_approved_re_run_signs_in(self, fake, aws_dir, browser):
        fake.seed('work', principal=None)
        write_config(aws_dir, '[profile dev]\ncredential_daemon = work\n')
        with pytest.raises(ConfigurationError):
            login(fake)
        fake.approve()
        _, ask = login(fake)
        assert not ask.called
        assert fake.credential('work').principal == DEFAULT_PRINCIPAL
        assert fake.approval_requests() == []


class TestRefusals:
    # The credential daemon names the credential after the sign-in, so it, not
    # the CLI, asks for approval to replace one that isn't an aws login
    # session.
    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_SSO])
    def test_an_identity_name_of_another_kind_needs_approval(
        self, fake, aws_dir, browser, kind
    ):
        fake.seed(ALICE, kind=kind)
        with pytest.raises(ConfigurationError) as e:
            login(fake, storage_answer=True)
        # The credential daemon's message and its instructions for
        # approving, as sent, and that the profile wasn't changed.
        assert e.value.__cause__.code == 'APPROVAL_REQUIRED'
        [request_id] = fake.approval_requests()
        assert str(e.value) == (
            f'Replacing {ALICE} needs approval.\n'
            f'  sudo creds request approve {request_id}\n'
            "Once it's approved, run this command again. Profile 'dev' "
            "wasn't changed."
        )
        assert fake.credential(ALICE).kind == kind
        # Nothing is saved, the storage answer included.
        assert read_config(aws_dir) == ''

    @pytest.mark.parametrize('bad_row', ['work', 7, None, ['work']])
    def test_a_row_that_isnt_an_object_is_skipped(
        self, fake, aws_dir, browser, bad_row
    ):
        # A credential/list row that isn't an object can't be the
        # credential, so it's skipped and the sign-in goes on.
        fake.seed('work')
        rows = [
            CredentialRow.from_wire(row)
            for row in [bad_row, *fake.list_rows()]
        ]
        write_config(aws_dir, '[profile dev]\ncredential_daemon = work\n')
        with mock.patch.object(
            CredentialDaemonClient, 'list_credentials', return_value=rows
        ):
            login(fake)
        assert fake.credential('work').kind == KIND_LOGIN

    @pytest.mark.parametrize('kind', [KIND_LOGIN, KIND_SSO])
    def test_a_stored_name_goes_to_the_credential_daemon(
        self, fake, aws_dir, browser, kind
    ):
        # The list's kind is session_credentials for every credential, and
        # the credential daemon decides: it replaces an aws login session,
        # and asks for approval before the browser step for anything else
        # but access keys, which the CLI refuses first.
        fake.seed('work', kind=kind)
        assert fake.list_rows()[0]['kind'] == 'session_credentials'
        config = '[profile dev]\ncredential_daemon = work\n'
        write_config(aws_dir, config)
        if kind == KIND_LOGIN:
            login(fake)
            assert fake.credential('work').kind == KIND_LOGIN
            return
        with pytest.raises(ConfigurationError) as e:
            login(fake)
        assert e.value.__cause__.code == 'APPROVAL_REQUIRED'
        assert not browser.called
        assert fake.credential('work').kind == kind
        assert read_config(aws_dir) == config

    def test_an_approval_shows_the_credential_daemons_instructions(
        self, fake, aws_dir, browser
    ):
        # The credential daemon's message and challenge, as sent. The
        # credential daemon and the fake send their instructions for
        # approving in data.remediation.
        fake.fail_next(
            'credential/bootstrap',
            'APPROVAL_REQUIRED',
            f'Replacing {ALICE} needs approval',
            challenge={'id': 'req-1'},
            remediation='Approve request req-1.',
        )
        with pytest.raises(ConfigurationError) as e:
            login(fake, profile='ci', storage_answer=True)
        assert e.value.__cause__.code == 'APPROVAL_REQUIRED'
        assert str(e.value) == (
            f'Replacing {ALICE} needs approval.\n'
            '  Approve request req-1.\n'
            "Once it's approved, run this command again. Profile 'ci' "
            "wasn't changed."
        )
        assert read_config(aws_dir) == ''

    @pytest.mark.parametrize('name', [None, 'bad name\x1b[2J'])
    def test_an_error_without_a_usable_name_is_credential_daemons(
        self, fake, aws_dir, browser, name
    ):
        code = 'APPROVAL_REQUIRED'
        # Whatever its data, the credential daemon's error (and its
        # approval challenge) is shown as sent.
        data = {} if name is None else {'name': name}
        fake.fail_next('credential/bootstrap', code, **data)
        with pytest.raises(ConfigurationError) as e:
            login(fake, profile='ci', storage_answer=True)
        assert e.value.__cause__.code == code
        assert read_config(aws_dir) == ''

    def test_other_errors_are_shown_as_credential_daemon_sent_them(
        self, fake, aws_dir, browser
    ):
        fake.fail_next('credential/bootstrap', 'INTERNAL', 'boom', name=ALICE)
        with pytest.raises(CredentialDaemonError) as e:
            login(fake, storage_answer=True)
        assert e.value.code == 'INTERNAL'

    def test_signs_in_again_over_an_aws_login_session(self, fake, aws_dir):
        # Signed in as the account and role it records: the credential
        # daemon replaces it with no approval.
        fake.seed('login.123456789012-role-Admin')
        login(fake, storage_answer=True)
        assert not fake.approval_requests()
        assert (
            'credential_daemon = login.123456789012-role-Admin'
            in read_config(aws_dir)
        )

    def test_the_check_before_prompts_lists_once(self, fake, aws_dir):
        # The sign-in uses the rows the access-key check read before the
        # prompts, so credential/list runs once.
        fake.seed('work')
        write_config(aws_dir, '[profile dev]\ncredential_daemon = work\n')
        login(fake)
        methods = [m for m, _ in fake.calls]
        assert methods.count('credential/list') == 1
        assert methods.index('credential/list') < methods.index(
            'credential/bootstrap'
        )

    @pytest.mark.parametrize(
        'name', ['keys.ci', 'sso.acme', 'login.123456789012-role-Admin']
    )
    @pytest.mark.parametrize('storage', ['', 'credential_storage = daemon\n'])
    @pytest.mark.parametrize(
        'tty, args', [(True, ()), (False, ()), (True, ('--remote',))]
    )
    def test_access_keys_are_refused_before_the_sign_in(
        self, fake, aws_dir, browser, name, storage, tty, args
    ):
        # As with keys in files, aws login refuses a profile whose
        # credential holds access keys, before any prompt (the region
        # prompt included). The credential's source decides, not its
        # name: a login.-tagged name that holds keys is refused too.
        # Nothing is signed in or approved.
        fake.seed(name, kind=KIND_IAM_USER)
        config = f'[profile ci]\ncredential_daemon = {name}\n{storage}'
        write_config(aws_dir, config)
        with (
            mock.patch.object(
                LoginCommand,
                '_prompt_for_region',
                side_effect=AssertionError('prompted'),
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            login(
                fake,
                profile='ci',
                tty=tty,
                args=args,
                parsed_globals=Namespace(
                    region=None, endpoint_url=None, verify_ssl=None
                ),
            )
        assert str(e.value) == (
            "Profile 'ci' is already configured with Access Key "
            "credentials.\n\nYou may run 'aws login --profile "
            "new-profile-name' to create a new profile with the specified "
            "name. Otherwise you must first manually remove the existing "
            "credentials from 'ci'.\n"
        )
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 253
        assert not browser.called
        assert [method for method, _ in fake.calls] == ['credential/list']
        assert fake.approval_requests() == []
        assert fake.credential(name).kind == KIND_IAM_USER
        assert read_config(aws_dir) == config

    @pytest.mark.parametrize(
        'name', ['keys.ci', 'sso.acme', 'login.123456789012-role-Admin']
    )
    @pytest.mark.parametrize('storage', ['', 'credential_storage = daemon\n'])
    def test_another_types_credential_waits_for_approval(
        self, fake, aws_dir, browser, name, storage
    ):
        # The type is never read from the name or the list: a login.-tagged
        # name that holds an SSO session waits for the credential daemon's
        # approval too.
        fake.seed(name, kind=KIND_SSO)
        config = f'[profile ci]\ncredential_daemon = {name}\n{storage}'
        write_config(aws_dir, config)
        with pytest.raises(ConfigurationError) as e:
            login(fake, profile='ci', storage_answer=True)
        assert e.value.__cause__.code == 'APPROVAL_REQUIRED'
        assert fake.credential(name).kind == KIND_SSO
        assert read_config(aws_dir) == config

    @pytest.mark.parametrize('name', ['keys.ci', 'sso.acme'])
    def test_a_tag_says_nothing_about_the_type(
        self, fake, aws_dir, browser, name
    ):
        # Another type's tag on an aws login session isn't refused.
        fake.seed(name, kind=KIND_LOGIN)
        write_config(aws_dir, f'[profile ci]\ncredential_daemon = {name}\n')
        login(fake, profile='ci')
        assert browser.called
        assert f'credential_daemon = {name}' in read_config(aws_dir)

    def test_a_credential_the_daemon_doesnt_have_isnt_refused(
        self, fake, aws_dir, browser
    ):
        write_config(aws_dir, '[profile ci]\ncredential_daemon = keys.ci\n')
        login(fake, profile='ci')
        assert browser.called

    def test_credential_type_is_checked_once_the_daemon_answers(
        self, aws_dir, sock_dir, browser
    ):
        # The type isn't known until the credential daemon answers, so a
        # profile in it gets the credential daemon's error.
        config = '[profile ci]\ncredential_daemon = keys.ci\n'
        write_config(aws_dir, config)
        session = Session(profile='ci')
        client = CredentialDaemonClient(
            socket_path=str(sock_dir / 'gone.sock')
        )
        command = LoginCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        with pytest.raises(ConfigurationError) as e:
            command([], GLOBALS)
        assert str(e.value).startswith('The credential daemon isn\'t running')
        assert not browser.called
        assert read_config(aws_dir) == config

    def test_untagged_name_is_not_refused_by_its_name(
        self, fake, aws_dir, browser
    ):
        # A name made with creds says nothing about what it holds.
        write_config(aws_dir, '[profile dev]\ncredential_daemon = keys\n')
        login(fake, storage_answer=True)
        assert fake.credential('keys').principal == DEFAULT_PRINCIPAL

    def test_profile_named_like_another_tag_gets_the_login_tag(
        self, fake, aws_dir, browser
    ):
        login(fake, profile='sso.acme', storage_answer=True)
        assert f'credential_daemon = {ALICE}' in read_config(aws_dir)

    def test_credential_daemon_not_running(self, aws_dir, sock_dir):
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        session = Session(profile='dev')
        client = CredentialDaemonClient(
            socket_path=str(sock_dir / 'gone.sock')
        )
        command = LoginCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        with pytest.raises(ConfigurationError) as e:
            command([], GLOBALS)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{sock_dir / "gone.sock"}: No such file or directory. '
            f'{START_HINT_TEXT} Then try again.'
        )

    def test_a_stopped_daemon_fails_before_any_prompt(self, aws_dir, sock_dir):
        # No region set, so the region prompt would come first; the ready
        # check fails the command before it, and before the browser.
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        session = Session(profile='dev')
        path = sock_dir / 'gone.sock'
        client = CredentialDaemonClient(socket_path=str(path))
        command = LoginCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        with (
            mock.patch.object(
                LoginCommand,
                '_prompt_for_region',
                side_effect=AssertionError('prompted'),
            ),
            mock.patch(
                'awscli.customizations.login.credential_daemon.'
                'open_browser_with_original_ld_path',
                side_effect=AssertionError('opened a browser'),
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            command([], GLOBALS)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{path}: No such file or directory. '
            f'{START_HINT_TEXT} Then try again.'
        )
        assert 'region' not in read_config(aws_dir)

    @skip_if_root('root ignores the socket\'s mode')
    def test_permission_error_names_the_os_error(self, fake, aws_dir):
        # The SEP counts any failed connect as NOT_RUNNING; the message
        # names the socket and the OS error, as the credential provider's
        # does.
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        os.chmod(fake.socket_path, 0)
        try:
            with pytest.raises(ConfigurationError) as e:
                login(fake)
        finally:
            os.chmod(fake.socket_path, 0o600)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{fake.socket_path}: Permission denied. '
            f'{START_HINT_TEXT} Then try again.'
        )
        assert 'credential_daemon' not in read_config(aws_dir)

    @pytest.mark.parametrize('which', ['connect', 'call'])
    def test_timeout_says_which_timeout_fired(self, aws_dir, sock_dir, which):
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        session = Session(profile='dev')
        path = str(sock_dir / 'slow.sock')
        client = CredentialDaemonClient(socket_path=path)
        command = LoginCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        with (
            # The ready check passes; the list's timeout fires.
            mock.patch.object(CredentialDaemonClient, 'probe'),
            mock.patch.object(
                CredentialDaemonClient,
                'list_credentials',
                side_effect=daemon_timeout(which, path),
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            command([], GLOBALS)
        assert str(e.value) == (
            f'{timeout_message(which, path)} {START_HINT_TEXT} Then try again.'
        )
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_no_socket_on_this_platform(self, aws_dir):
        # Where the credential daemon has no socket path (Windows), the
        # error says the credential daemon isn't available, not the start
        # hint.
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        session = Session(profile='dev')
        client = CredentialDaemonClient()
        command = LoginCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        with (
            mock.patch(
                'botocore.credential_daemon.client.default_socket_path',
                return_value=None,
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            command([], GLOBALS)
        assert str(e.value).startswith(
            "The credential daemon isn't available on this platform"
        )
        assert 'Start the credential daemon' not in str(e.value)
        assert 'credential_daemon' not in read_config(aws_dir)


class TestMovingBack:
    def test_file_storage_moves_the_session_back(self, fake, aws_dir, capsys):
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            login(fake)
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert (
            fake.credential('login.123456789012-role-Admin').status
            == NO_SESSION
        )
        assert 'out of the credential daemon' in capsys.readouterr().out

    def login_ci_as_old_session(self, fake, **kwargs):
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    OLD_SESSION,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            return login(fake, profile='ci', **kwargs)

    def write_keys_profile(self, fake, aws_dir, name='ci'):
        fake.seed(
            name,
            kind=KIND_IAM_USER,
            principal='arn:aws:iam::123456789012:user/ci',
        )
        write_config(
            aws_dir,
            f'''
            [profile ci]
            credential_storage = file
            credential_daemon = {name}
            ''',
        )

    def test_a_session_moves_back_and_is_signed_out(
        self, fake, aws_dir, capsys
    ):
        # The credential daemon signs out an aws login session.
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = KIND_LOGIN
        self.login_ci_as_old_session(fake, replace=True)
        assert_cleared(fake, 'ci')
        assert ('credential/logout', {'credential': 'ci'}) in fake.calls
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert (
            'Moved this profile\'s session out of the credential daemon'
            in capsys.readouterr().out
        )

    def test_a_name_the_daemon_doesnt_have_moves_back(
        self, fake, aws_dir, capsys
    ):
        # Nothing to refuse and nothing to sign out: the profile moves to
        # files as before.
        write_config(
            aws_dir,
            '''
            [profile ci]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        _, _, rc = self.login_ci_as_old_session(fake, return_rc=True)
        assert rc == 0
        methods = [m for m, _ in fake.calls]
        assert methods[0] == 'credential/list'
        assert 'credential/logout' in methods
        assert 'credential/remove' not in methods
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config

    @pytest.mark.parametrize('name', ['ci', 'keys.ci', 'login.ci'])
    @pytest.mark.parametrize('tty', [True, False])
    @pytest.mark.parametrize('from_env', [False, True])
    def test_access_keys_are_refused_before_the_sign_in(
        self, fake, aws_dir, browser, name, tty, from_env
    ):
        # credential_storage = file says where new credentials go; it
        # doesn't move keys. They move back only when credential_daemon is
        # removed and they're entered again with aws configure, so aws login
        # refuses before any prompt or browser, and nothing is signed in,
        # deleted or written. The source decides, never the name.
        self.write_keys_profile(fake, aws_dir, name)
        environ = {}
        if from_env:
            write_config(
                aws_dir, f'[profile ci]\ncredential_daemon = {name}\n'
            )
            environ = {'AWS_CREDENTIAL_STORAGE': 'file'}
        config = read_config(aws_dir)
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
            ) as fetch_token,
            mock.patch.object(
                LoginCommand,
                '_prompt_for_region',
                side_effect=AssertionError('prompted'),
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            login(
                fake,
                profile='ci',
                tty=tty,
                environ=environ,
                parsed_globals=Namespace(
                    region=None, endpoint_url=None, verify_ssl=None
                ),
            )
        assert str(e.value) == (
            "Profile 'ci' is already configured with Access Key "
            "credentials.\n\nTo use files for it, remove credential_daemon "
            "from the profile and enter its keys with 'aws configure "
            "--profile ci'. Or run 'aws login --profile new-profile-name' to "
            "create a new profile.\n"
        )
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 253
        assert not fetch_token.called
        assert not browser.called
        assert [m for m, _ in fake.calls] == ['credential/list']
        assert fake.approval_requests() == []
        assert fake.credential(name).kind == KIND_IAM_USER
        assert read_config(aws_dir) == config
        cache = aws_dir / 'cache'
        assert not cache.exists() or not os.listdir(cache)

    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_LOGIN])
    def test_an_absent_daemon_moves_back_without_asking_it(
        self, fake, aws_dir, capsys, kind
    ):
        # No credential daemon at all, such as after an uninstall: nothing
        # there can be dropped, so the profile signs in to files and loses
        # credential_daemon as before. Nothing reaches the credential
        # daemon, not even credential/logout; its data stays where it is,
        # and a note says so. It may hold keys, so it isn't called a
        # session, and installing it wouldn't clear it.
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = kind
        os.unlink(fake.socket_path)
        _, _, rc = self.login_ci_as_old_session(fake, return_rc=True)
        assert fake.calls == []
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert fake.credential('ci').kind == kind
        assert rc == 0
        assert capsys.readouterr().err == (
            f'note: no credential daemon is running at {fake.socket_path}, so '
            "its old copy of this profile's credential wasn't cleared. "
            'If the credential daemon runs elsewhere (for example, on the '
            'host of this container), '
            "clear credential 'ci' there.\n"
        )

    @pytest.mark.parametrize('link', ['none', 'dangling'])
    @pytest.mark.parametrize('kind', [KIND_IAM_USER, KIND_LOGIN])
    def test_default_discovery_finds_an_absent_daemon_on_move_back(
        self, fake, aws_dir, capsys, monkeypatch, link, kind
    ):
        # No socket variable and no client: the CLI looks for
        # ~/.aws/credential-daemon.sock. Missing, or a link to nothing as
        # an uninstall leaves for other users, both mean absent.
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        home_socket = aws_dir / 'home' / '.aws' / 'credential-daemon.sock'
        if link == 'dangling':
            home_socket.parent.mkdir()
            home_socket.symlink_to(aws_dir / 'gone.sock')
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = kind
        _, _, rc = self.login_ci_as_old_session(
            fake, return_rc=True, discover=True
        )
        assert rc == 0
        assert fake.calls == []
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert capsys.readouterr().err == (
            f'note: no credential daemon is running at {home_socket}, so '
            "its old copy of this profile's credential wasn't cleared. If "
            'the credential daemon runs elsewhere (for example, on the host '
            "of this container), clear credential 'ci' there.\n"
        )

    def test_where_the_daemon_doesnt_run_the_move_back_warns(
        self, fake, aws_dir, capsys
    ):
        # Such as Windows: clearing can never work here, so it's a warning
        # and exit 0, as for aws configure's move back.
        self.write_keys_profile(fake, aws_dir, 'login.ci')
        fake.credential('login.ci').kind = KIND_LOGIN
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            _, _, rc = self.login_ci_as_old_session(fake, return_rc=True)
        assert rc == 0
        # The test's client names the fake's socket, so the storage line
        # still lists; nothing else reaches it.
        assert 'credential/logout' not in [m for m, _ in fake.calls]
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert capsys.readouterr().err == (
            f"warning: profile 'ci' moved to {aws_dir / 'cache'}. Its copy "
            "in the credential daemon (credential 'login.ci') can't be "
            'cleared on this platform; clear it on the machine where the '
            'credential daemon runs.\n'
        )

    def test_where_the_daemon_doesnt_run_its_socket_isnt_needed(
        self, fake, aws_dir, capsys
    ):
        # As on Windows, where no socket is looked up: nothing is listed,
        # so the sign-in moves to files with the same warning instead of
        # failing with the unsupported-platform error.
        self.write_keys_profile(fake, aws_dir, 'login.ci')
        fake.credential('login.ci').kind = KIND_LOGIN
        with mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ):
            _, _, rc = self.login_ci_as_old_session(
                fake, return_rc=True, discover=True
            )
        assert rc == 0
        assert fake.calls == []
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        assert capsys.readouterr().err == (
            f"warning: profile 'ci' moved to {aws_dir / 'cache'}. Its copy "
            "in the credential daemon (credential 'login.ci') can't be "
            'cleared on this platform; clear it on the machine where the '
            'credential daemon runs.\n'
        )

    def test_a_daemon_that_stops_after_the_check_still_fails_the_clear(
        self, fake, aws_dir, capsys
    ):
        # Something is still at the socket when the clear runs, so it may
        # hold the session: exit 1 and say how to sign it out (S3).
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = KIND_LOGIN
        with mock.patch.object(
            CredentialDaemonClient,
            'logout',
            side_effect=CredentialDaemonNotRunningError(
                error_msg='Not running.'
            ),
        ):
            _, _, rc = self.login_ci_as_old_session(fake, return_rc=True)
        assert rc == 1
        assert 'credential_daemon' not in read_config(aws_dir)
        err = capsys.readouterr().err
        assert err.startswith("Moved this profile's session to ")
        assert (
            ", but the copy in the credential daemon wasn't cleared: Not "
            "running. It's still there as credential 'ci'."
        ) in err

    @pytest.mark.parametrize('kind', ['stopped', 'hung', 'untrusted'])
    def test_a_daemon_that_is_there_but_down_refuses_before_the_sign_in(
        self, fake, aws_dir, browser, kind
    ):
        # Something is at the socket, so the credential may hold access
        # keys the CLI can't see. It refuses before any prompt rather than
        # drop them.
        self.write_keys_profile(fake, aws_dir)
        config = read_config(aws_dir)
        if kind == 'stopped':
            # The socket file is still there, but nothing accepts on it.
            os.unlink(fake.socket_path)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(fake.socket_path)
            server.close()
            down = contextlib.nullcontext()
        else:
            error = (
                CredentialDaemonTimeoutError(error_msg='Timed out.')
                if kind == 'hung'
                else CredentialDaemonUntrustedSocketError(
                    error_msg='Untrusted.'
                )
            )
            down = mock.patch.object(
                CredentialDaemonClient, 'list_credentials', side_effect=error
            )
        with (
            down,
            mock.patch.object(
                LoginCommand,
                '_prompt_for_region',
                side_effect=AssertionError('prompted'),
            ),
            pytest.raises(ConfigurationError) as e,
        ):
            login(
                fake,
                profile='ci',
                parsed_globals=Namespace(
                    region=None, endpoint_url=None, verify_ssl=None
                ),
            )
        if kind == 'stopped':
            assert str(e.value) == (
                'The credential daemon isn\'t running: can\'t connect to '
                f'{fake.socket_path}: Connection refused. '
                f'{START_HINT_TEXT} Then try again.'
            )
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=io.StringIO(), stderr=io.StringIO()
        )
        assert rc == 253
        assert not browser.called
        assert read_config(aws_dir) == config
        assert fake.credential('ci').kind == KIND_IAM_USER

    def test_another_list_failure_refuses_before_the_sign_in(
        self, fake, aws_dir, browser
    ):
        # The CLI can't tell what the credential holds, so nothing moves.
        self.write_keys_profile(fake, aws_dir)
        config = read_config(aws_dir)
        fake.fail_next('credential/list', 'INTERNAL', 'busy')
        with pytest.raises(CredentialDaemonError) as e:
            login(fake, profile='ci')
        assert 'busy' in str(e.value)
        assert not browser.called
        assert [m for m, _ in fake.calls] == ['credential/list']
        assert read_config(aws_dir) == config

    def test_where_the_daemon_doesnt_run_nothing_is_asked(self, fake, aws_dir):
        # As an AWS CLI without credential daemon support: nothing to
        # refuse, and nothing is sent.
        self.write_keys_profile(fake, aws_dir)
        session = Session(profile='ci')
        client = CredentialDaemonClient(socket_path=fake.socket_path)
        command = LoginCommand(session, credential_daemon_client=client)
        with mock.patch(
            'awscli.customizations.login.credential_daemon.DaemonSignIn.'
            'runs_here',
            return_value=False,
        ):
            command._credential_daemon.refuse_access_keys('ci', 'login')
        assert fake.calls == []

    @pytest.mark.parametrize(
        'source', ['aws_roles_anywhere', 'static_secret', 'unsupported']
    )
    def test_other_credentials_are_kept_when_moving_back(
        self, fake, aws_dir, capsys, source
    ):
        # The credential daemon refuses the sign-out, and the row's source
        # isn't access keys: the CLI doesn't manage it, so it stays. The
        # profile still moves to files.
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = source
        _, _, rc = self.login_ci_as_old_session(
            fake, replace=True, return_rc=True
        )
        assert rc == 0
        assert fake.credential('ci') is not None
        assert fake.credential('ci').status != NO_SESSION
        assert 'credential/remove' not in [m for m, _ in fake.calls]
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config
        out = capsys.readouterr().out
        assert (
            "Signed in to profile 'ci' with a session file. Kept credential "
            "'ci' in the credential daemon; it isn't a sign-in and the CLI "
            "doesn't manage it.\n"
        ) in out
        assert 'were deleted' not in out

    @pytest.mark.parametrize('kind', [KIND_LOGIN, 'aws_roles_anywhere'])
    def test_a_credential_another_profile_names_is_kept(
        self, fake, aws_dir, capsys, kind
    ):
        self.write_keys_profile(fake, aws_dir)
        fake.credential('ci').kind = kind
        with open(aws_dir / 'config', 'a') as f:
            f.write('[profile ci2]\ncredential_daemon = ci\n')
        self.login_ci_as_old_session(fake, replace=True)
        assert fake.credential('ci').status != NO_SESSION
        assert 'credential/logout' not in [m for m, _ in fake.calls]
        out = capsys.readouterr().out
        assert (
            'Signed in to profile \'ci\' with a session file. Kept credential \'ci\' '
            'in the credential daemon, because \'ci2\' still uses it.'
        ) in out
        assert 'session out' not in out

    def test_leftover_keys_are_refused_when_moving_back(self, fake, aws_dir):
        # On files the keys would win over login_session.
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            aws_access_key_id = AKID
            aws_secret_access_key = secret
            ''',
        )
        with pytest.raises(ConfigurationError) as e:
            login(fake)
        assert 'already configured with Access Key credentials' in str(e.value)
        assert (
            'credential_daemon = login.123456789012-role-Admin'
            in read_config(aws_dir)
        )


class TestMovingBackWithTheWorkaround:
    # Customers add this line next to credential_daemon for older SDKs.
    # The move back removes credential_daemon but not the line, and the
    # next aws login must still work.
    WORKAROUND = (
        'credential_process = aws configure export-credentials '
        '--profile dev --format process'
    )

    def sign_in_with_files(self, fake, session_id=OLD_SESSION):
        with (
            mock.patch(
                'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.'
                'fetch_token',
                return_value=(
                    {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                    session_id,
                ),
            ),
            mock.patch(
                'awscli.customizations.login.utils.get_base_sign_in_uri'
            ),
            mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
        ):
            login(fake)

    def move_back(self, fake, aws_dir):
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            {self.WORKAROUND}
            ''',
        )
        self.sign_in_with_files(fake)
        config = read_config(aws_dir)
        assert 'credential_daemon' not in config
        assert f'login_session = {OLD_SESSION}' in config

    def test_next_aws_login_still_works(self, fake, aws_dir):
        self.move_back(fake, aws_dir)
        self.sign_in_with_files(fake)
        assert f'login_session = {OLD_SESSION}' in read_config(aws_dir)

    def test_move_back_says_what_happened_to_the_workaround(
        self, fake, aws_dir, capsys
    ):
        # The customer hears about the line: it was removed.
        self.move_back(fake, aws_dir)
        out = capsys.readouterr().out
        assert 'credential_process' in out

    def test_move_back_removes_the_workaround(self, fake, aws_dir):
        self.move_back(fake, aws_dir)
        assert 'credential_process' not in read_config(aws_dir)

    @pytest.mark.parametrize(
        'line',
        [
            # Another tool is the customer's own source.
            'credential_process = /usr/local/bin/other-tool --profile dev',
            # The workaround for another profile isn't this profile's.
            'credential_process = aws configure export-credentials '
            '--profile prod --format process',
        ],
    )
    def test_move_back_keeps_other_credential_process_lines(
        self, fake, aws_dir, capsys, line
    ):
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            f'''
            [profile dev]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            {line}
            ''',
        )
        self.sign_in_with_files(fake)
        assert line in read_config(aws_dir)
        assert 'Removed the credential_process' not in capsys.readouterr().out

    def test_move_back_keeps_the_workaround_in_the_credentials_file(
        self, fake, aws_dir, capsys
    ):
        # Only ~/.aws/config is rewritten, so a line in ~/.aws/credentials
        # stays and the CLI doesn't say it was removed.
        fake.seed('login.123456789012-role-Admin')
        write_config(
            aws_dir,
            '''
            [profile dev]
            credential_storage = file
            credential_daemon = login.123456789012-role-Admin
            ''',
        )
        credentials = f'[dev]\n{self.WORKAROUND}\n'
        (aws_dir / 'credentials').write_text(credentials)
        self.sign_in_with_files(fake)
        assert 'Removed the credential_process' not in capsys.readouterr().out
        assert (aws_dir / 'credentials').read_text() == credentials


class TestIsCredentialDaemonWorkaround:
    @pytest.mark.parametrize(
        'line',
        [
            'aws configure export-credentials --profile dev --format process',
            '/usr/local/bin/aws configure export-credentials --profile dev '
            '--format process',
            '"/opt/my tools/aws" configure export-credentials --profile dev',
            'aws configure export-credentials --format=process --profile=dev',
        ],
    )
    def test_matches_the_documented_line(self, line):
        assert is_credential_daemon_workaround(line, 'dev')

    @pytest.mark.parametrize(
        'line',
        [
            None,
            '',
            'other-tool --profile dev',
            'aws configure export-credentials --profile prod',
            'aws configure export-credentials',
            'aws configure export-credentials --profile dev --format env',
            'aws configure export-credentials --profile dev --region x',
            'aws configure export-credentials --profile dev --profile prod',
            'aws configure export-credentials --profile',
            'aws configure export-credentials --profile dev extra',
            'awsx configure export-credentials --profile dev',
            'aws configure export-credentials --profile "dev',
        ],
    )
    def test_does_not_match_anything_else(self, line):
        assert not is_credential_daemon_workaround(line, 'dev')


LOGIN_TTY = 'awscli.customizations.login.login.is_stdin_a_tty'


class TestSignup:
    # aws signup asks Sign-In to create an account, which the credential
    # daemon can't, so it always signs in with files. A profile set up for
    # the credential daemon isn't refused, and nothing is sent to the
    # credential daemon, as with aws sso login.
    def signup(self, fake, environ=None, replace=None, profile='dev'):
        fetch, uri, auth = files_sign_in()
        with fetch, uri, auth, mock.patch(LOGIN_TTY, return_value=True):
            return login(
                fake,
                profile=profile,
                environ=environ,
                replace=replace,
                command_class=SignupCommand,
                return_rc=True,
            )

    def assert_signed_in_with_files(
        self, fake, aws_dir, ask, rc, pointer=None
    ):
        assert not rc
        assert not ask.called
        assert fake.calls == []
        config = read_config(aws_dir)
        assert f'login_session = {OLD_SESSION}' in config
        if pointer is None:
            assert 'credential_daemon' not in config
        else:
            assert f'credential_daemon = {pointer}' in config
        assert len(list((aws_dir / 'cache').iterdir())) == 1

    def test_new_profile_is_not_asked(self, fake, aws_dir, capsys):
        ask, _, rc = self.signup(fake)
        self.assert_signed_in_with_files(fake, aws_dir, ask, rc)
        assert 'credential_storage' not in read_config(aws_dir)
        assert capsys.readouterr().err == ''

    @pytest.mark.parametrize(
        'saved, environ',
        [
            ('credential_storage = file\n', {}),
            ('', {'AWS_CREDENTIAL_STORAGE': 'file'}),
            # The variable wins over the profile's answer.
            (
                'credential_storage = daemon\n',
                {'AWS_CREDENTIAL_STORAGE': 'file'},
            ),
        ],
    )
    def test_files_chosen_signs_in_with_files(
        self, fake, aws_dir, capsys, saved, environ
    ):
        write_config(aws_dir, f'[profile dev]\n{saved}')
        ask, _, rc = self.signup(fake, environ=environ)
        self.assert_signed_in_with_files(fake, aws_dir, ask, rc)
        out, err = capsys.readouterr()
        assert 'Updated profile dev to use' in out
        assert err == ''

    @pytest.mark.parametrize(
        'saved, environ',
        [
            ('credential_storage = daemon\n', {}),
            ('', {'AWS_CREDENTIAL_STORAGE': 'daemon'}),
            (
                'credential_storage = file\n',
                {'AWS_CREDENTIAL_STORAGE': 'daemon'},
            ),
        ],
    )
    def test_daemon_storage_signs_in_with_files(
        self, fake, aws_dir, capsys, saved, environ
    ):
        # The profile or the variable chose the credential daemon, which
        # can't create an account: signup signs in with files, says
        # nothing about it, and leaves credential_storage as it was.
        write_config(aws_dir, f'[profile dev]\n{saved}')
        ask, _, rc = self.signup(fake, environ=environ)
        self.assert_signed_in_with_files(fake, aws_dir, ask, rc)
        assert read_config(aws_dir).startswith(f'[profile dev]\n{saved}')
        out, err = capsys.readouterr()
        assert 'Updated profile dev to use' in out
        assert 'credential daemon' not in out
        assert err == ''

    @pytest.mark.parametrize(
        'source',
        [
            KIND_LOGIN,
            KIND_SSO,
            KIND_IAM_USER,
            'aws_roles_anywhere',
            'static_secret',
            'unsupported',
            None,
        ],
    )
    @pytest.mark.parametrize('storage', ['daemon', 'file'])
    def test_a_daemon_profile_keeps_its_credential_daemon(
        self, fake, aws_dir, capsys, source, storage
    ):
        # Whatever the credential holds (None: the daemon doesn't have it)
        # and whatever credential_storage says, signup adds login_session
        # and leaves credential_daemon, which still takes precedence, and
        # the credential daemon's credential alone.
        if source is not None:
            fake.seed('custom', kind=source)
        write_config(
            aws_dir,
            f'[profile dev]\ncredential_storage = {storage}\n'
            'credential_daemon = custom\n',
        )
        ask, _, rc = self.signup(fake)
        self.assert_signed_in_with_files(
            fake, aws_dir, ask, rc, pointer='custom'
        )
        assert f'credential_storage = {storage}' in read_config(aws_dir)
        if source is not None:
            assert fake.credential('custom').status != NO_SESSION
        out, err = capsys.readouterr()
        assert 'credential daemon' not in out
        assert err == ''

    def test_the_workaround_line_stays(self, fake, aws_dir):
        # Nothing moves out of the credential daemon, so the line for older
        # tools stays with credential_daemon.
        fake.seed(BOB_NAME, principal=BOB)
        workaround = (
            'credential_process = aws configure export-credentials '
            '--profile dev --format process'
        )
        write_config(
            aws_dir,
            '[profile dev]\ncredential_storage = daemon\n'
            f'credential_daemon = {BOB_NAME}\n{workaround}\n',
        )
        ask, _, rc = self.signup(fake)
        self.assert_signed_in_with_files(
            fake, aws_dir, ask, rc, pointer=BOB_NAME
        )
        assert workaround in read_config(aws_dir)
        assert fake.credential(BOB_NAME).status != NO_SESSION

    def test_access_keys_in_the_credential_daemon_sign_in_with_files(
        self, fake, aws_dir
    ):
        # aws login refuses a credential_daemon that holds access keys;
        # signup asks the credential daemon nothing, so it signs in.
        fake.seed(
            'keys.ci',
            kind=KIND_IAM_USER,
            principal='arn:aws:iam::123456789012:user/ci',
        )
        write_config(
            aws_dir,
            '[profile ci]\ncredential_storage = file\n'
            'credential_daemon = keys.ci\n',
        )
        ask, _, rc = self.signup(fake, profile='ci')
        self.assert_signed_in_with_files(
            fake, aws_dir, ask, rc, pointer='keys.ci'
        )

    def test_access_keys_in_the_profile_are_still_refused(self, fake, aws_dir):
        # As on any profile, keys in it would win over login_session, so
        # signup refuses them before the browser opens, credential_daemon
        # or not, and asks the credential daemon nothing.
        fake.seed('custom', kind=KIND_LOGIN)
        config = (
            '[profile dev]\ncredential_storage = daemon\n'
            'credential_daemon = custom\naws_access_key_id = AKIAX\n'
        )
        write_config(aws_dir, config)
        fetch, uri, auth = files_sign_in()
        with (
            fetch as fetched,
            uri,
            auth,
            mock.patch(LOGIN_TTY, return_value=True),
            pytest.raises(ConfigurationError) as e,
        ):
            login(fake, command_class=SignupCommand)
        assert "already configured with Access Key credentials" in str(e.value)
        assert "aws signup --profile new-profile-name" in str(e.value)
        assert not fetched.called
        assert fake.calls == []
        assert read_config(aws_dir) == config

    def test_a_failing_credential_daemon_is_not_asked(self, fake, aws_dir):
        # Nothing is sent, so a list that would fail doesn't matter.
        fake.seed('custom', kind=KIND_IAM_USER)
        fake.fail_next('credential/list', 'INTERNAL', 'busy')
        write_config(
            aws_dir,
            '[profile dev]\ncredential_storage = daemon\n'
            'credential_daemon = custom\n',
        )
        ask, _, rc = self.signup(fake)
        self.assert_signed_in_with_files(
            fake, aws_dir, ask, rc, pointer='custom'
        )

    def test_no_credential_daemon_signs_in_with_files(
        self, aws_dir, sock_dir, capsys
    ):
        # Nothing at the socket: signup doesn't need the credential daemon.
        write_config(
            aws_dir,
            '[profile dev]\ncredential_storage = daemon\n'
            'credential_daemon = keys.dev\n',
        )
        session = Session(profile='dev')
        client = CredentialDaemonClient(socket_path=str(sock_dir / 'gone'))
        command = SignupCommand(
            session,
            chooser=CredentialStorageChooser(
                session, credential_daemon_client=client, environ={}
            ),
            credential_daemon_client=client,
        )
        fetch, uri, auth = files_sign_in()
        with fetch, uri, auth, mock.patch(LOGIN_TTY, return_value=True):
            rc = command([], GLOBALS)
        assert not rc
        config = read_config(aws_dir)
        assert f'login_session = {OLD_SESSION}' in config
        assert 'credential_daemon = keys.dev' in config
        assert capsys.readouterr().err == ''


class TestRegionThroughTheDaemon:
    # As with files, a profile with no region gets v2's region prompt. The
    # credential daemon keeps the ID token, so there's no home region.
    def sign_in(self, fake, tty, answer='eu-west-1', parsed_globals=GLOBALS):
        with (
            mock.patch(LOGIN_TTY, return_value=tty),
            mock.patch(f'{HANDLER}.open_browser_with_original_ld_path'),
            mock.patch(
                'awscli.customizations.configure.sso.PTKPrompt'
            ) as prompt,
        ):
            prompt.return_value.get_value.return_value = answer
            _, _, rc = login(
                fake,
                tty=tty,
                storage_answer=True,
                parsed_globals=parsed_globals,
                return_rc=True,
            )
        return prompt, rc

    def test_no_region_in_a_terminal_asks_and_saves(
        self, fake, aws_dir, capsys
    ):
        prompt, rc = self.sign_in(fake, tty=True)
        assert not rc
        assert prompt.return_value.get_value.call_args[0][0] == 'us-west-2'
        assert 'No region is set for profile dev.' in capsys.readouterr().out
        assert read_config(aws_dir) == (
            '[profile dev]\n'
            'credential_storage = daemon\n'
            f'credential_daemon = {ALICE}\n'
            'region = eu-west-1\n'
        )

    def test_no_region_without_a_terminal_saves_none(
        self, fake, aws_dir, capsys
    ):
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        prompt, rc = self.sign_in(fake, tty=False)
        assert not rc
        assert not prompt.called
        assert 'No region is set' not in capsys.readouterr().out
        assert read_config(aws_dir) == (
            '[profile dev]\n'
            'credential_storage = daemon\n'
            f'credential_daemon = {ALICE}\n'
        )

    def test_region_already_set_is_kept(self, fake, aws_dir):
        write_config(
            aws_dir,
            '[profile dev]\ncredential_storage = daemon\nregion = ca-central-1\n',
        )
        prompt, rc = self.sign_in(fake, tty=True)
        assert not rc
        assert not prompt.called
        config = read_config(aws_dir)
        assert 'region = ca-central-1' in config
        assert f'credential_daemon = {ALICE}' in config

    def test_no_region_anywhere_saves_the_one_picked(self, fake, aws_dir):
        # The "No AWS region has been configured" prompt before the sign-in
        # picks the region, and it's saved without a second prompt.
        write_config(aws_dir, '[profile dev]\ncredential_storage = daemon\n')
        no_region = Namespace(region=None, endpoint_url=None, verify_ssl=None)
        prompt, rc = self.sign_in(
            fake, tty=True, answer='eu-west-1', parsed_globals=no_region
        )
        assert not rc
        assert prompt.return_value.get_value.call_count == 1
        assert 'region = eu-west-1' in read_config(aws_dir)


class TestHelp:
    def test_describes_the_credential_daemon(self):
        text = rendered_help('login')
        # The file path keeps the wording it had before the credential
        # daemon.
        assert 'AWS_LOGIN_CACHE_DIRECTORY' in text
        assert 'Updated profile default to use' in text
        assert (
            'the credential daemon keeps the session and refreshes its '
            'credentials instead, and nothing is cached on disk'
        ) in text
        assert (
            'Signed in as arn:aws:sts::123456789012:assumed-role/my-role/'
            'my-session-name Credentials are stored in the credential daemon.'
        ) in text


class TestPreviewNotice:
    def test_said_once_before_the_storage_question(
        self, fake, aws_dir, browser, capsys
    ):
        ask, _ = login(fake, storage_answer=True)
        assert ask.call_count == 1
        err = capsys.readouterr().err
        assert err.count(PREVIEW_LINE) == 1
        assert err.startswith(PREVIEW_LINE)

    def test_no_terminal_says_nothing(self, fake, aws_dir, capsys):
        fetch, uri, auth = files_sign_in()
        with fetch, uri, auth:
            ask, _ = login(fake, tty=False)
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_the_env_var_says_nothing(self, fake, aws_dir, capsys):
        fetch, uri, auth = files_sign_in()
        with fetch, uri, auth:
            ask, _ = login(fake, environ={'AWS_CREDENTIAL_STORAGE': 'file'})
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err
