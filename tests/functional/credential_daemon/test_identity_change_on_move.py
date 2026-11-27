# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Moving a profile between files and the credential daemon must ask before it
changes who the profile signs in as.

aws login credentials are named after the account and role that sign in, so
another identity gets its own credential and the CLI asks the question it
asks for session files. A name the profile has that aws login didn't make
(``work`` here, as creds would make) is signed in to in place, so a different
account or role there needs the credential daemon's approval.
"""

import json
import socket
import textwrap
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import CredentialDaemonClient
from botocore.exceptions import (
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
)
from botocore.session import Session
from botocore.utils import generate_login_cache_key

from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.login.credential_daemon import (
    confirm_shared_sign_in,
)
from awscli.customizations.login.login import LoginCommand
from tests import mock
from tests.functional.credential_daemon.login_helpers import SAMPLE_ID_TOKEN
from tests.functional.credential_daemon.sso_helpers import (
    START_HINT_TEXT,
)
from tests.utils.credential_daemon import (
    DEFAULT_PRINCIPAL,
)

# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'

PROD_ADMIN = 'arn:aws:sts::111111111111:assumed-role/Admin/alice'
OTHER_DEV = 'arn:aws:sts::222222222222:assumed-role/Dev/alice'
THIRD_OPS = 'arn:aws:sts::333333333333:assumed-role/Ops/alice'
# The names the credential daemon gives their aws login credentials.
PROD_NAME = 'login.111111111111-role-Admin'
OTHER_NAME = 'login.222222222222-role-Dev'
THIRD_NAME = 'login.333333333333-role-Ops'
GLOBALS = Namespace(region='us-west-2', endpoint_url=None, verify_ssl=None)
HANDLER = 'awscli.customizations.login.credential_daemon'
MESSAGES = 'awscli.customizations.credential_daemon.messages'
LOGIN = 'awscli.customizations.login.login'
UTILS = 'awscli.customizations.login.utils'


@pytest.fixture
def browser():
    with mock.patch(f'{HANDLER}.open_browser_with_original_ld_path') as open_:
        yield open_


def write_config(aws_dir, config):
    (aws_dir / 'config').write_text(textwrap.dedent(config))


def read_config(aws_dir):
    return (aws_dir / 'config').read_text()


def write_session_file(aws_dir, session_id):
    cache = aws_dir / 'cache'
    cache.mkdir(exist_ok=True)
    path = cache / f'{generate_login_cache_key(session_id)}.json'
    path.write_text(json.dumps({'accessToken': {}}))
    return path


def login(
    fake,
    profile='prod',
    tty=True,
    storage_answer=None,
    replace=None,
    environ=None,
    answers=None,
):
    """Run aws login; one mock answers every yes/no question, with
    ``replace`` or, in turn, with each of ``answers``.

    The mock's exit_code is what the command returned.
    """
    session = Session(profile=profile)
    client = CredentialDaemonClient(socket_path=fake.socket_path, timeout=5)
    chooser = CredentialStorageChooser(
        session,
        credential_daemon_client=client,
        environ=environ if environ is not None else {},
        is_tty=lambda: tty,
        ask=mock.Mock(return_value=storage_answer),
    )
    command = LoginCommand(
        session, chooser=chooser, credential_daemon_client=client
    )
    if answers is not None:
        ask_replace = mock.Mock(side_effect=answers)
    else:
        ask_replace = mock.Mock(return_value=replace)
    with (
        mock.patch(f'{HANDLER}.is_stdin_a_tty', return_value=tty),
        mock.patch(f'{HANDLER}.yes_no_choice', ask_replace),
        mock.patch(f'{MESSAGES}.is_stdin_a_tty', return_value=tty),
        mock.patch(f'{MESSAGES}.yes_no_choice', ask_replace),
        mock.patch(f'{LOGIN}.yes_no_choice', ask_replace),
    ):
        ask_replace.exit_code = command([], GLOBALS)
    return ask_replace


def file_sign_in_returns(session_id):
    """Patch the file flow so the browser sign-in returns session_id."""
    return (
        mock.patch(
            f'{UTILS}.SameDeviceLoginTokenFetcher.fetch_token',
            return_value=(
                {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                session_id,
            ),
        ),
        mock.patch(f'{UTILS}.get_base_sign_in_uri'),
        mock.patch(f'{LOGIN}.AuthCodeFetcher'),
    )


def credential_daemon_list_fails():
    return mock.patch.object(
        CredentialDaemonClient,
        'list_credentials',
        # No final period: the question still ends the sentence.
        side_effect=CredentialDaemonNotRunningError(
            error_msg='The credential daemon is not running'
        ),
    )


def assert_declined_exit_code(ask):
    # Keeping the old identity isn't an error.
    assert ask.exit_code in (0, None)


class TestFirstMoveIntoCredentialDaemon:
    """prod is on files as Admin in 111…; the sign-in returns Dev in 222…."""

    QUESTION = (
        f'\nProfile prod is already configured to use session {PROD_ADMIN}. '
        f'Do you want to overwrite it to use {OTHER_DEV} instead? (y/n): '
    )

    def setup_prod(self, fake, aws_dir):
        write_config(
            aws_dir,
            f'''
            [profile prod]
            login_session = {PROD_ADMIN}
            region = us-west-2
            ''',
        )
        fake.next_principal = OTHER_DEV
        return write_session_file(aws_dir, PROD_ADMIN)

    def test_same_identity_moves_without_asking(self, fake, aws_dir, browser):
        session_file = self.setup_prod(fake, aws_dir)
        fake.next_principal = PROD_ADMIN
        ask = login(fake, storage_answer=True)
        assert not ask.called
        assert f'credential_daemon = {PROD_NAME}' in read_config(aws_dir)
        assert not session_file.exists()

    def test_asks_todays_question(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir)
        ask = login(fake, storage_answer=True, replace=True)
        assert ask.call_args_list == [mock.call(self.QUESTION)]

    def test_no_keeps_the_profile_and_its_file(self, fake, aws_dir, browser):
        session_file = self.setup_prod(fake, aws_dir)
        ask = login(fake, storage_answer=True, replace=False)
        assert_declined_exit_code(ask)
        config = read_config(aws_dir)
        assert f'login_session = {PROD_ADMIN}' in config
        assert 'credential_daemon' not in config
        assert session_file.exists()
        # credential/logout keeps the entry and its principal, so
        # the new session is signed out rather than gone.
        assert fake.credential(OTHER_NAME).status == 'no_session'

    def test_without_a_terminal_the_answer_is_no(self, fake, aws_dir, browser):
        # A script with AWS_CREDENTIAL_STORAGE=daemon moves without the
        # storage question; it still must not swap the identity.
        session_file = self.setup_prod(fake, aws_dir)
        # As for session files, the identity changing is an error for it.
        with pytest.raises(ConfigurationError) as e:
            login(
                fake, tty=False, environ={'AWS_CREDENTIAL_STORAGE': 'daemon'}
            )
        assert 'in a terminal to overwrite it' in str(e.value)
        config = read_config(aws_dir)
        assert f'login_session = {PROD_ADMIN}' in config
        assert 'credential_daemon' not in config
        assert session_file.exists()
        assert fake.credential(OTHER_NAME).status == 'no_session'

    def test_yes_moves_the_new_identity(self, fake, aws_dir, browser):
        session_file = self.setup_prod(fake, aws_dir)
        login(fake, storage_answer=True, replace=True)
        assert f'credential_daemon = {OTHER_NAME}' in read_config(aws_dir)
        assert not session_file.exists()
        assert fake.credential(OTHER_NAME).principal == OTHER_DEV

    def test_no_says_what_was_kept(self, fake, aws_dir, browser, capsys):
        self.setup_prod(fake, aws_dir)
        login(fake, storage_answer=True, replace=False)
        out = capsys.readouterr().out
        assert f'Kept \'prod\' signed in as {PROD_ADMIN}.' in out
        assert 'Signed in as' not in out

    def test_a_leftover_of_the_same_identity_isnt_asked_about(
        self, fake, aws_dir, browser
    ):
        # Left signed out by an earlier no or move back.
        session_file = self.setup_prod(fake, aws_dir)
        fake.seed(PROD_NAME, principal=PROD_ADMIN, status='no_session')
        fake.next_principal = PROD_ADMIN
        ask = login(fake, storage_answer=True)
        assert not ask.called
        assert f'credential_daemon = {PROD_NAME}' in read_config(aws_dir)
        assert fake.credential(PROD_NAME).status == 'active'
        assert not session_file.exists()

    def test_interrupted_question_signs_the_new_session_out(
        self, fake, aws_dir, browser
    ):
        session_file = self.setup_prod(fake, aws_dir)
        with pytest.raises(KeyboardInterrupt):
            login(fake, storage_answer=True, answers=[KeyboardInterrupt])
        assert fake.credential(OTHER_NAME).status == 'no_session'
        assert 'credential_daemon' not in read_config(aws_dir)
        assert session_file.exists()

    def test_no_sticks_on_a_re_run(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir)
        login(fake, storage_answer=True, replace=False)
        ask = login(fake, storage_answer=True, replace=False)
        assert ask.call_args_list == [mock.call(self.QUESTION)]
        assert fake.credential(OTHER_NAME).status == 'no_session'
        assert 'credential_daemon' not in read_config(aws_dir)

    def test_failed_sign_out_names_logout_all(
        self, fake, aws_dir, browser, capsys
    ):
        # The hint is a CLI command.
        self.setup_prod(fake, aws_dir)
        with mock.patch.object(
            CredentialDaemonClient,
            'logout',
            side_effect=CredentialDaemonNotRunningError(
                error_msg='The credential daemon stopped.'
            ),
        ):
            ask = login(fake, storage_answer=True, replace=False)
        # The declined session is left in the credential daemon, so this
        # isn't a clean no.
        assert ask.exit_code == 1
        err = capsys.readouterr().err
        assert (
            f'The new session for \'prod\' is still in the credential '
            f"daemon as '{OTHER_NAME}'"
        ) in err
        assert (
            f'{START_HINT_TEXT} Then run \'aws logout --all\' to sign it out.'
            in err
        )


class TestFirstMoveOntoAnotherProfilesCredential:
    """prod is on files as Admin. alias is already in the credential daemon as
    Dev, on Dev's credential. Profiles signed in as one identity share it."""

    def setup_prod(self, fake, aws_dir, alias_name, alias_principal):
        write_config(
            aws_dir,
            f'''
            [profile prod]
            login_session = {PROD_ADMIN}
            region = us-west-2
            [profile alias]
            credential_storage = daemon
            credential_daemon = {alias_name}
            ''',
        )
        fake.seed(alias_name, principal=alias_principal)
        return write_session_file(aws_dir, PROD_ADMIN)

    def alias_name(self, aws_dir):
        return (
            Session(profile='alias')
            .get_scoped_config()
            .get('credential_daemon')
        )

    def test_no_keeps_alias_signed_in(self, fake, aws_dir, browser, capsys):
        # The question is about prod's session file only; alias's
        # credential is in use, so a no never signs it out.
        session_file = self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.next_principal = OTHER_DEV
        ask = login(fake, storage_answer=True, replace=False)
        assert ask.call_args_list == [
            mock.call(TestFirstMoveIntoCredentialDaemon.QUESTION)
        ]
        assert_declined_exit_code(ask)
        assert fake.credential(OTHER_NAME).status == 'active'
        assert 'credential/logout' not in [m for m, _ in fake.calls]
        assert f'login_session = {PROD_ADMIN}' in read_config(aws_dir)
        assert session_file.exists()
        captured = capsys.readouterr()
        assert f'Kept \'prod\' signed in as {PROD_ADMIN}.' in captured.out
        assert captured.err == PREVIEW_LINE

    @pytest.mark.parametrize('status', ['no_session', 'expired'])
    def test_no_doesnt_sign_a_signed_out_credential_back_in(
        self, fake, aws_dir, browser, status
    ):
        # alias was signed out (aws logout --profile alias), or its session
        # ended. A config name alone isn't in use, so the declined session
        # is signed out again.
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        if status == 'expired':
            fake.expire(OTHER_NAME)
        else:
            fake.credential(OTHER_NAME).status = 'no_session'
            fake.credential(OTHER_NAME).secrets.clear()
        fake.next_principal = OTHER_DEV
        ask = login(fake, storage_answer=True, replace=False)
        assert ask.call_count == 1
        assert_declined_exit_code(ask)
        assert fake.credential(OTHER_NAME).status == 'no_session'
        assert self.alias_name(aws_dir) == OTHER_NAME

    def test_without_a_terminal_doesnt_sign_alias_back_in(
        self, fake, aws_dir, browser
    ):
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.credential(OTHER_NAME).status = 'no_session'
        fake.next_principal = OTHER_DEV
        with pytest.raises(ConfigurationError):
            login(
                fake, tty=False, environ={'AWS_CREDENTIAL_STORAGE': 'daemon'}
            )
        assert fake.credential(OTHER_NAME).status == 'no_session'
        assert (
            'credential_daemon'
            not in read_config(aws_dir).split('[profile alias]')[0]
        )

    def test_interrupt_doesnt_sign_alias_back_in(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.credential(OTHER_NAME).status = 'no_session'
        fake.next_principal = OTHER_DEV
        with pytest.raises(KeyboardInterrupt):
            login(fake, storage_answer=True, answers=[KeyboardInterrupt])
        assert fake.credential(OTHER_NAME).status == 'no_session'

    def test_failed_sign_out_names_alias(self, fake, aws_dir, browser, capsys):
        # What was left behind, and that alias names it.
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.credential(OTHER_NAME).status = 'no_session'
        fake.next_principal = OTHER_DEV
        with mock.patch.object(
            CredentialDaemonClient,
            'logout',
            side_effect=CredentialDaemonNotRunningError(
                error_msg='The credential daemon stopped.'
            ),
        ):
            ask = login(fake, storage_answer=True, replace=False)
        assert ask.exit_code == 1
        assert (
            f'The new session for \'prod\' is still in the credential '
            f"daemon as '{OTHER_NAME}', and 'alias' uses it: "
        ) in capsys.readouterr().err

    def test_yes_shares_alias_credential(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.next_principal = OTHER_DEV
        login(fake, storage_answer=True, replace=True)
        config = read_config(aws_dir)
        assert config.count(f'credential_daemon = {OTHER_NAME}\n') == 2
        assert self.alias_name(aws_dir) == OTHER_NAME
        assert fake.credential(OTHER_NAME).principal == OTHER_DEV

    def test_yes_to_a_third_identity_leaves_alias_alone(
        self, fake, aws_dir, browser
    ):
        self.setup_prod(fake, aws_dir, OTHER_NAME, OTHER_DEV)
        fake.next_principal = THIRD_OPS
        login(fake, storage_answer=True, replace=True)
        assert f'credential_daemon = {THIRD_NAME}' in read_config(aws_dir)
        assert self.alias_name(aws_dir) == OTHER_NAME
        assert fake.credential(OTHER_NAME).principal == OTHER_DEV
        assert fake.credential(OTHER_NAME).status == 'active'

    def test_same_identity_shares_it_without_asking(
        self, fake, aws_dir, browser
    ):
        session_file = self.setup_prod(fake, aws_dir, PROD_NAME, PROD_ADMIN)
        fake.next_principal = PROD_ADMIN
        ask = login(fake, storage_answer=True)
        assert not ask.called
        config = read_config(aws_dir)
        assert config.count(f'credential_daemon = {PROD_NAME}\n') == 2
        assert not session_file.exists()

    @pytest.mark.parametrize('status', ['no_session', 'expired'])
    def test_same_identity_signs_alias_back_in(
        self, fake, aws_dir, browser, status
    ):
        # As signing in again refreshes a shared session file.
        self.setup_prod(fake, aws_dir, PROD_NAME, PROD_ADMIN)
        if status == 'expired':
            fake.expire(PROD_NAME)
        else:
            fake.credential(PROD_NAME).status = 'no_session'
        fake.next_principal = PROD_ADMIN
        ask = login(fake, storage_answer=True)
        assert not ask.called
        assert fake.credential(PROD_NAME).status == 'active'


class TestSignedOutSharedCredential:
    """prod and alias are on work, which aws logout --profile alias
    signed out. Its row still holds Dev."""

    def setup_prod(self, fake, aws_dir):
        write_config(
            aws_dir,
            '''
            [profile prod]
            credential_storage = daemon
            credential_daemon = work
            region = us-west-2
            [profile alias]
            credential_storage = daemon
            credential_daemon = work
            ''',
        )
        fake.seed('work', principal=OTHER_DEV, status='no_session')
        fake.next_principal = OTHER_DEV

    def test_same_identity_asks_before_signing_alias_back_in(
        self, fake, aws_dir, browser, capsys
    ):
        # The credential daemon sees the same principal and doesn't ask, so
        # the CLI does.
        self.setup_prod(fake, aws_dir)
        before = read_config(aws_dir)
        ask = login(fake, replace=False)
        assert ask.call_args_list == [
            mock.call(
                f'\nCredential \'work\' is also used by \'alias\'. Sign in '
                f'as {OTHER_DEV} for both? [y/N] ',
                default=False,
            )
        ]
        assert_declined_exit_code(ask)
        assert fake.credential('work').status == 'no_session'
        assert read_config(aws_dir) == before
        assert "Profile 'prod' wasn't changed." in capsys.readouterr().out

    def test_yes_signs_both_back_in(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir)
        ask = login(fake, replace=True)
        assert ask.call_count == 1
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', OTHER_DEV)

    def test_without_a_terminal_signs_in_as_today(
        self, fake, aws_dir, browser
    ):
        self.setup_prod(fake, aws_dir)
        ask = login(fake, tty=False)
        assert not ask.called
        assert fake.credential('work').status == 'active'

    def test_a_different_identity_needs_approval(self, fake, aws_dir, browser):
        # The credential daemon records Dev for work, signed out or not.
        self.setup_prod(fake, aws_dir)
        before = read_config(aws_dir)
        fake.next_principal = THIRD_OPS
        with pytest.raises(ConfigurationError) as e:
            login(fake, replace=True)
        [request_id] = fake.approval_requests()
        assert f'sudo creds request approve {request_id}' in str(e.value)
        assert read_config(aws_dir) == before
        assert fake.credential('work').principal == OTHER_DEV

    def test_after_approval_the_cli_still_asks_about_alias(
        self, fake, aws_dir, browser, capsys
    ):
        # Nobody was signed in, so the CLI asks before alias gets an
        # identity, and a no signs the new session out.
        self.setup_prod(fake, aws_dir)
        before = read_config(aws_dir)
        fake.next_principal = THIRD_OPS
        with pytest.raises(ConfigurationError):
            login(fake)
        fake.approve()
        ask = login(fake, replace=False)
        assert ask.call_args_list == [
            mock.call(
                f'\nCredential \'work\' is also used by \'alias\'. Sign in '
                f'as {THIRD_OPS} for both? [y/N] ',
                default=False,
            )
        ]
        assert read_config(aws_dir) == before
        assert fake.credential('work').status == 'no_session'
        assert "Profile 'prod' wasn't changed." in capsys.readouterr().out


def test_the_shared_credential_name_is_printed_without_control_characters():
    ask = mock.Mock(return_value=False)
    notice = mock.Mock()
    for tty in (True, False):
        confirm_shared_sign_in(
            'work\x1b[2J',
            OTHER_DEV,
            ['alias'],
            is_tty=lambda: tty,
            ask=ask,
            yes_without_terminal=False,
            notice=notice,
        )
    [question] = ask.call_args.args
    [message] = notice.call_args.args
    for text in (question, message):
        assert "Credential 'work[2J' is also used by 'alias'." in text
        assert '\x1b' not in text


class TestExpiredSharedCredential:
    """prod and alias are on work, signed in as Dev, now expired. An
    expired credential still has an identity."""

    def setup_prod(self, fake, aws_dir):
        write_config(
            aws_dir,
            """
            [profile prod]
            credential_storage = daemon
            credential_daemon = work
            region = us-west-2
            [profile alias]
            credential_storage = daemon
            credential_daemon = work
            """,
        )
        fake.seed('work', principal=OTHER_DEV)
        fake.expire('work')
        return read_config(aws_dir)

    def test_same_identity_signs_in_without_asking(
        self, fake, aws_dir, browser
    ):
        before = self.setup_prod(fake, aws_dir)
        fake.next_principal = OTHER_DEV
        ask = login(fake, replace=False)
        assert not ask.called
        assert ask.exit_code in (0, None)
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', OTHER_DEV)

    def test_a_different_identity_needs_approval(self, fake, aws_dir, browser):
        before = self.setup_prod(fake, aws_dir)
        fake.next_principal = THIRD_OPS
        with pytest.raises(ConfigurationError):
            login(fake, replace=True)
        assert read_config(aws_dir) == before
        assert fake.credential('work').principal == OTHER_DEV
        [row] = fake.list_rows()
        assert row['status'] == 'expired'

    def test_an_approved_re_run_replaces_it_for_both(
        self, fake, aws_dir, browser
    ):
        # The approval was for exactly this; the CLI doesn't ask again.
        before = self.setup_prod(fake, aws_dir)
        fake.next_principal = THIRD_OPS
        with pytest.raises(ConfigurationError):
            login(fake)
        fake.approve()
        ask = login(fake, replace=False)
        assert not ask.called
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', THIRD_OPS)


def test_no_keeps_a_credential_no_profile_names(
    fake, aws_dir, browser, capsys
):
    # It was signed in to the credential daemon before this sign-in, so
    # something else (a toolkit, another config file) may use it. A no keeps
    # it.
    write_config(
        aws_dir,
        f'''
        [profile prod]
        login_session = {PROD_ADMIN}
        region = us-west-2
        ''',
    )
    write_session_file(aws_dir, PROD_ADMIN)
    fake.seed(OTHER_NAME, principal=OTHER_DEV)
    fake.next_principal = OTHER_DEV
    ask = login(fake, storage_answer=True, replace=False)
    assert ask.call_count == 1
    assert PROD_ADMIN in ask.call_args[0][0]
    assert_declined_exit_code(ask)
    assert fake.credential(OTHER_NAME).status == 'active'
    assert 'credential_daemon' not in read_config(aws_dir)
    out = capsys.readouterr().out
    assert f'Kept \'prod\' signed in as {PROD_ADMIN}.' in out


def test_a_profile_without_a_session_isnt_asked_about(
    fake, aws_dir, browser, capsys
):
    # prod has no identity to keep, as for login_session.
    write_config(aws_dir, '[profile prod]\nregion = us-west-2\n')
    fake.seed(THIRD_NAME, principal=THIRD_OPS)
    fake.next_principal = OTHER_DEV
    ask = login(fake, storage_answer=True)
    assert not ask.called
    assert f'credential_daemon = {OTHER_NAME}' in read_config(aws_dir)
    assert fake.credential(THIRD_NAME).principal == THIRD_OPS


class TestSignInAgainInCredentialDaemon:
    """prod is already in the credential daemon as Dev. An older CLI left
    login_session."""

    def setup_prod(self, fake, aws_dir):
        fake.seed(OTHER_NAME, principal=OTHER_DEV)
        write_config(
            aws_dir,
            f'''
            [profile prod]
            credential_storage = daemon
            credential_daemon = {OTHER_NAME}
            login_session = {PROD_ADMIN}
            region = us-west-2
            ''',
        )

    def test_leftover_login_session_isnt_compared(
        self, fake, aws_dir, browser, capsys
    ):
        # The credential daemon wins over the leftover key.
        self.setup_prod(fake, aws_dir)
        fake.next_principal = OTHER_DEV
        ask = login(fake, replace=False)
        assert not ask.called
        assert fake.credential(OTHER_NAME).status == 'active'
        assert f'credential_daemon = {OTHER_NAME}' in read_config(aws_dir)
        assert 'Kept prod' not in capsys.readouterr().out

    def test_the_question_names_the_credential(self, fake, aws_dir, browser):
        # The leftover login_session adds no second question. The credential
        # daemon's rows don't say who a credential is signed in as, so its
        # name stands for it.
        self.setup_prod(fake, aws_dir)
        fake.next_principal = THIRD_OPS
        ask = login(fake, replace=True)
        assert ask.call_count == 1
        question = ask.call_args[0][0]
        assert f'session {OTHER_NAME}.' in question
        assert THIRD_OPS in question
        assert PROD_ADMIN not in question
        assert f'credential_daemon = {THIRD_NAME}' in read_config(aws_dir)
        assert fake.credential(OTHER_NAME).principal == OTHER_DEV


class TestSignInAgainOntoASignedOutCredential:
    """prod is in the credential daemon as Admin. alias names Dev's
    credential, which aws logout --profile alias signed out. prod signs in as
    Dev."""

    def setup_prod(self, fake, aws_dir):
        fake.seed(PROD_NAME, principal=PROD_ADMIN)
        fake.seed(OTHER_NAME, principal=OTHER_DEV, status='no_session')
        write_config(
            aws_dir,
            f'''
            [profile prod]
            credential_storage = daemon
            credential_daemon = {PROD_NAME}
            region = us-west-2
            [profile alias]
            credential_storage = daemon
            credential_daemon = {OTHER_NAME}
            ''',
        )
        fake.next_principal = OTHER_DEV

    def test_no_leaves_alias_signed_out(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir)
        ask = login(fake, replace=False)
        assert ask.call_count == 1
        assert f'credential_daemon = {PROD_NAME}' in read_config(aws_dir)
        assert fake.credential(OTHER_NAME).status == 'no_session'
        assert fake.credential(PROD_NAME).status == 'active'

    def test_yes_signs_prod_in_as_dev(self, fake, aws_dir, browser):
        # As with session files: the session for Dev serves both.
        self.setup_prod(fake, aws_dir)
        login(fake, replace=True)
        config = read_config(aws_dir)
        assert config.count(f'credential_daemon = {OTHER_NAME}\n') == 2
        assert fake.credential(OTHER_NAME).status == 'active'


class TestDifferentIdentityOnSignIn:
    """prod is in the credential daemon as Admin; the sign-in returns Dev.
    When alias uses the credential too, the CLI's question names it and a yes
    replaces the credential for both. Otherwise it asks the question for
    session files about prod only. Nothing is ever auto-named."""

    def setup_prod(self, fake, aws_dir, shared=True, extra=''):
        config = """
            [profile prod]
            credential_storage = daemon
            credential_daemon = work
            region = us-west-2
            """
        if shared:
            config += """
            [profile alias]
            credential_storage = daemon
            credential_daemon = work
            """
        write_config(aws_dir, config + extra)
        fake.seed('work', principal=PROD_ADMIN)
        fake.next_principal = OTHER_DEV

    @pytest.mark.parametrize('shared', [True, False])
    @pytest.mark.parametrize('tty', [True, False])
    def test_needs_the_credential_daemons_approval(
        self, fake, aws_dir, browser, shared, tty
    ):
        # As in credsd, the sign-in finished, nothing was saved, and the
        # CLI shows the credential daemon's message and instructions. The
        # CLI asks nothing.
        self.setup_prod(fake, aws_dir, shared=shared)
        before = read_config(aws_dir)
        with pytest.raises(ConfigurationError) as e:
            login(fake, tty=tty, replace=True)
        [request_id] = fake.approval_requests()
        assert str(e.value) == (
            'Replacing work needs approval.\n'
            '  this sign-in is for a different '
            'account or role than the credential records, so nothing was '
            f'saved. sudo creds request approve {request_id}, then re-run '
            'the same bootstrap and sign in as the same account and role '
            "again\nOnce it's approved, run this command again. Profile "
            "'prod' wasn't changed."
        )
        assert browser.call_count == 1
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', PROD_ADMIN)
        assert 'credential/bootstrap/respond' not in [m for m, _ in fake.calls]

    @pytest.mark.parametrize('shared', [True, False])
    def test_an_approved_re_run_replaces_it_in_place(
        self, fake, aws_dir, browser, capsys, shared
    ):
        self.setup_prod(fake, aws_dir, shared=shared)
        before = read_config(aws_dir)
        with pytest.raises(ConfigurationError):
            login(fake)
        fake.approve()
        ask = login(fake, replace=False)
        assert not ask.called
        assert ask.exit_code in (0, None)
        # One credential, in place: the profiles still name work.
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', OTHER_DEV)
        assert f'Signed in as {OTHER_DEV}' in capsys.readouterr().out

    def test_an_approval_doesnt_cover_another_identity(
        self, fake, aws_dir, browser
    ):
        self.setup_prod(fake, aws_dir)
        with pytest.raises(ConfigurationError):
            login(fake)
        fake.approve()
        fake.next_principal = THIRD_OPS
        with pytest.raises(ConfigurationError):
            login(fake)
        assert fake.credential('work').principal == PROD_ADMIN
        assert len(fake.approval_requests()) == 1

    def test_same_identity_on_a_shared_credential_signs_in_in_place(
        self, fake, aws_dir, browser
    ):
        # Both profiles keep sharing it, as two profiles share one session
        # file.
        self.setup_prod(fake, aws_dir)
        fake.next_principal = PROD_ADMIN
        ask = login(fake)
        assert not ask.called
        assert 'credential_daemon = work\n' in read_config(aws_dir)
        assert fake.credential('work-2') is None

    NO_ROW_QUESTION = (
        f'\nCredential \'work\' is also used by \'alias\'. Sign in as '
        f'{OTHER_DEV} for both? [y/N] '
    )

    def setup_no_row(self, fake, aws_dir, extra=''):
        # The credential daemon has no work (its store was wiped, or the
        # config came from another machine), so it has no identity to ask
        # about.
        self.setup_prod(fake, aws_dir, extra=extra)
        fake.reset()
        fake.next_principal = OTHER_DEV
        return read_config(aws_dir)

    def test_shared_with_no_row_asks_before_alias_gets_an_identity(
        self, fake, aws_dir, browser, capsys
    ):
        # A yes gives alias prod's new identity, so the question names it.
        before = self.setup_no_row(fake, aws_dir)
        ask = login(fake, replace=True)
        assert ask.call_args_list == [
            mock.call(self.NO_ROW_QUESTION, default=False)
        ]
        assert ask.exit_code in (0, None)
        assert browser.call_count == 1
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.principal) == ('active', OTHER_DEV)
        assert fake.credential('work-2') is None
        assert f'Signed in as {OTHER_DEV}' in capsys.readouterr().out

    def test_shared_with_no_row_no_changes_nothing(
        self, fake, aws_dir, browser, capsys
    ):
        before = self.setup_no_row(fake, aws_dir)
        ask = login(fake, replace=False)
        assert ask.call_args_list == [
            mock.call(self.NO_ROW_QUESTION, default=False)
        ]
        assert_declined_exit_code(ask)
        assert read_config(aws_dir) == before
        cred = fake.credential('work')
        assert (cred.status, cred.secrets) == ('no_session', {})
        assert fake.credential('work-2') is None
        captured = capsys.readouterr()
        assert "Profile 'prod' wasn't changed." in captured.out
        assert captured.err == ''

    def test_shared_with_no_row_names_every_other_profile(
        self, fake, aws_dir, browser
    ):
        self.setup_no_row(
            fake,
            aws_dir,
            extra="""
            [profile ci]
            credential_daemon = work
            """,
        )
        ask = login(fake, replace=False)
        assert ask.call_args_list == [
            mock.call(
                f'\nCredential \'work\' is also used by \'alias\' and \'ci\'. '
                f'Sign in as {OTHER_DEV} for all of them? [y/N] ',
                default=False,
            )
        ]

    def test_shared_with_no_row_interrupted_question_signs_it_out(
        self, fake, aws_dir, browser
    ):
        # An interrupt is not a yes.
        before = self.setup_no_row(fake, aws_dir)
        with pytest.raises(KeyboardInterrupt):
            login(fake, answers=[KeyboardInterrupt])
        cred = fake.credential('work')
        assert (cred.status, cred.secrets) == ('no_session', {})
        assert read_config(aws_dir) == before

    def test_shared_with_no_row_without_a_terminal_signs_in_in_place(
        self, fake, aws_dir, browser, capsys
    ):
        # No identity is replaced, so a script signs in without a
        # question. "Nothing changes" without a terminal is for a replaced
        # identity.
        before = self.setup_no_row(fake, aws_dir)
        ask = login(fake, tty=False)
        assert not ask.called
        assert ask.exit_code == 0
        assert browser.call_count == 1
        assert read_config(aws_dir) == before
        assert fake.credential('work').principal == OTHER_DEV
        assert fake.credential('work-2') is None

    def test_unshared_with_no_row_asks_nothing(self, fake, aws_dir, browser):
        self.setup_prod(fake, aws_dir, shared=False)
        fake.reset()
        fake.next_principal = OTHER_DEV
        ask = login(fake)
        assert not ask.called
        assert fake.credential('work').principal == OTHER_DEV


class TestMoveBackToFiles:
    """prod is in the credential daemon; files sign-in returns Dev.

    Nothing is asked: the profile has no login_session, and the credential
    daemon's rows don't say who a credential is signed in as, so, as for a
    file profile with no login_session, there's nothing to compare with.
    """

    def setup_prod(self, fake, aws_dir, seed=True):
        if seed:
            fake.seed('login.prod')
        write_config(
            aws_dir,
            '''
            [profile prod]
            credential_storage = file
            credential_daemon = login.prod
            region = us-west-2
            ''',
        )

    @pytest.mark.parametrize('session_id', [OTHER_DEV, DEFAULT_PRINCIPAL])
    @pytest.mark.parametrize('tty', [True, False])
    def test_moves_back_without_asking(self, fake, aws_dir, session_id, tty):
        self.setup_prod(fake, aws_dir)
        patches = file_sign_in_returns(session_id)
        with patches[0], patches[1], patches[2]:
            ask = login(fake, tty=tty)
        assert not ask.called
        config = read_config(aws_dir)
        assert f'login_session = {session_id}' in config
        assert 'credential_daemon' not in config
        assert fake.credential('login.prod').status == 'no_session'

    def test_daemon_down_reports_the_session_left_in_it(
        self, fake, aws_dir, capsys
    ):
        # The sign-in worked, but the old session couldn't be cleared.
        self.setup_prod(fake, aws_dir)
        patches = file_sign_in_returns(OTHER_DEV)
        down = CredentialDaemonNotRunningError(
            error_msg='The credential daemon is not running.'
        )
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch.object(
                CredentialDaemonClient, 'logout', side_effect=down
            ),
        ):
            ask = login(fake)
        assert ask.exit_code == 1
        assert 'credential_daemon' not in read_config(aws_dir)
        assert fake.credential('login.prod').status == 'active'
        err = capsys.readouterr().err
        assert "It's still there as credential 'login.prod'." in err
        assert (
            f'{START_HINT_TEXT} Then run \'aws logout --all\' to sign it out.'
            in err
        )

    def test_failed_clear_names_logout_all(self, fake, aws_dir, capsys):
        self.setup_prod(fake, aws_dir)
        patches = file_sign_in_returns(OTHER_DEV)
        # A message without a final period still ends its sentence.
        failed = CredentialDaemonError(error_msg='clear failed')
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch.object(
                CredentialDaemonClient, 'logout', side_effect=failed
            ),
        ):
            ask = login(fake)
        assert ask.exit_code == 1
        err = capsys.readouterr().err
        assert (
            "wasn't cleared: clear failed. It's still there as credential "
            "'login.prod'."
        ) in err
        assert 'Run \'aws logout --all\' to sign it out.' in err


class TestMoveBackOfASharedCredential:
    """prod moves back to files; alias still names credential login.prod."""

    def setup_prod(self, fake, aws_dir, others=('alias',)):
        fake.seed('login.prod')
        config = '''
            [profile prod]
            credential_storage = file
            credential_daemon = login.prod
            region = us-west-2
            '''
        for other in others:
            config += f'''
            [profile {other}]
            credential_storage = daemon
            credential_daemon = login.prod
            '''
        write_config(aws_dir, config)

    def test_keeps_the_credential_and_names_the_profile(
        self, fake, aws_dir, capsys
    ):
        self.setup_prod(fake, aws_dir)
        patches = file_sign_in_returns(DEFAULT_PRINCIPAL)
        with patches[0], patches[1], patches[2]:
            ask = login(fake, replace=True)
        assert ask.exit_code in (0, None)
        config = read_config(aws_dir)
        assert (
            'credential_daemon = login.prod'
            in config.split('[profile alias]')[1]
        )
        assert 'credential_daemon' not in config.split('[profile alias]')[0]
        assert fake.credential('login.prod').status == 'active'
        captured = capsys.readouterr()
        assert (
            'Kept credential \'login.prod\' in the credential daemon, because '
            '\'alias\' still uses it.'
        ) in captured.out
        assert captured.err == ''

    def test_names_every_profile_that_uses_it(self, fake, aws_dir, capsys):
        self.setup_prod(fake, aws_dir, others=('beta', 'alias'))
        patches = file_sign_in_returns(DEFAULT_PRINCIPAL)
        with patches[0], patches[1], patches[2]:
            login(fake, replace=True)
        assert fake.credential('login.prod').status == 'active'
        assert (
            'because \'alias\' and \'beta\' still use it.'
            in capsys.readouterr().out
        )

    def test_a_different_identity_keeps_it_too(self, fake, aws_dir):
        self.setup_prod(fake, aws_dir)
        patches = file_sign_in_returns(OTHER_DEV)
        with patches[0], patches[1], patches[2]:
            ask = login(fake)
        assert not ask.called
        assert (
            'credential_daemon'
            not in read_config(aws_dir).split('[profile alias]')[0]
        )
        assert fake.credential('login.prod').status == 'active'
        assert fake.credential('login.prod').principal == DEFAULT_PRINCIPAL


def test_a_move_back_saves_the_session_file(fake, aws_dir):
    fake.seed('login.prod')
    write_config(
        aws_dir,
        '''
        [profile prod]
        credential_storage = file
        credential_daemon = login.prod
        ''',
    )
    patches = file_sign_in_returns(OTHER_DEV)
    with patches[0], patches[1], patches[2]:
        ask = login(fake)
    assert ask.exit_code in (0, None)
    assert list((aws_dir / 'cache').iterdir())
