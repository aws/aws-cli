# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import pytest
from botocore.credential_daemon import USE_FILES_HERE_HINT
from botocore.exceptions import (
    CredentialDaemonNotRunningError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonUnsupportedPlatformError,
)

from awscli.customizations.credential_daemon.messages import (
    PREVIEW_NOTICE,
    WITHOUT_DAEMON_FLAG_HINT,
    approval_message,
    confirm_delete_leftover,
    confirm_session_overwrite,
    copy_not_cleared_message,
    daemon_down_is_configuration_error,
    daemon_down_message,
    moved_out_message,
    profile_subject,
    quoted_names,
    signed_out_count_message,
    unavailable_here_error,
    use_files_hint,
)
from awscli.customizations.exceptions import ConfigurationError
from tests import mock


def test_quoted_names_quotes_and_joins():
    assert quoted_names(['a', 'b']) == "'a', 'b'"


def test_quoted_names_strips_control_characters():
    # Names come from config files and the credential daemon's
    # credential/list, so an escape sequence could rewrite the terminal.
    assert quoted_names(['dev\x1b[2J', 'ops\x07']) == "'dev[2J', 'ops'"


def test_moved_out_message():
    assert moved_out_message("the keys for 'ci'", '~/.aws/credentials') == (
        "Moved the keys for 'ci' out of the credential daemon and into "
        '~/.aws/credentials.'
    )


@pytest.mark.parametrize(
    'hint', ['', " Run 'aws logout --all' to sign it out."]
)
def test_copy_not_cleared_message(hint):
    # The error's message ends its sentence, then the credential's name,
    # then what to run.
    error = CredentialDaemonRequestRejectedError(error_msg='busy')
    assert copy_not_cleared_message(
        "this profile's session", '~/.aws/login/cache', error, 'login.ci', hint
    ) == (
        "Moved this profile's session to ~/.aws/login/cache, but the copy in "
        "the credential daemon wasn't cleared: busy. It's still there as "
        f"credential 'login.ci'.{hint}"
    )


def test_confirm_session_overwrite_strips_the_profile_name():
    # The name comes from --profile or the config file.
    ask = mock.Mock(return_value=True)
    assert confirm_session_overwrite(
        'dev\x1b[2J', 'alice', 'bob', is_tty=lambda: True, ask=ask
    )
    ask.assert_called_once_with(
        '\nProfile dev[2J is already configured to use session alice. Do '
        'you want to overwrite it to use bob instead? (y/n): '
    )


def test_confirm_session_overwrite_without_a_terminal_strips_it_too():
    notices = []
    assert not confirm_session_overwrite(
        'dev\x07', 'alice', 'bob', is_tty=lambda: False, notice=notices.append
    )
    assert notices == [
        '\nProfile dev is already configured to use session alice. Run '
        '\'aws login\' in a terminal to overwrite it to use bob.\n'
    ]


def test_confirm_delete_leftover_strips_the_profile_name(capsys):
    assert not confirm_delete_leftover(
        'dev\x1b[2J', '/home/u/.aws/login/cache/x.json', is_tty=lambda: False
    )
    assert capsys.readouterr().err == (
        'Run \'aws login\' in a terminal to delete it, or '
        '\'aws logout --profile dev[2J\'.\n'
    )


def test_profile_subject_strips_control_characters():
    assert profile_subject('dev\x1b[2J') == "profile 'dev[2J'"


@pytest.mark.parametrize(
    'kwargs, hint',
    [
        ({}, 'set credential_storage = file in the profile.'),
        (
            {'from_env': True},
            'run the command again with AWS_CREDENTIAL_STORAGE=file.',
        ),
        (
            # The option wins over the variable, so it's enough.
            {'flag': True, 'from_env': True},
            'run the command again with --credential-storage file.',
        ),
    ],
)
def test_use_files_hint_names_only_what_works(kwargs, hint):
    assert use_files_hint(**kwargs) == f'To use files for it, {hint}'


def test_daemon_down_message_where_it_doesnt_run():
    # Starting or installing the credential daemon can't help there.
    error = CredentialDaemonUnsupportedPlatformError(error_msg='x')
    assert daemon_down_message(error) == (
        "The credential daemon isn't available on this platform."
    )


def test_daemon_down_is_configuration_error():
    error = CredentialDaemonNotRunningError(error_msg='x')
    with pytest.raises(ConfigurationError) as raised:
        with daemon_down_is_configuration_error():
            raise error
    assert str(raised.value) == daemon_down_message(error)
    assert raised.value.__cause__ is error


def test_daemon_down_is_configuration_error_leaves_other_errors():
    error = CredentialDaemonRequestRejectedError(error_msg='refused')
    with pytest.raises(CredentialDaemonRequestRejectedError):
        with daemon_down_is_configuration_error():
            raise error


def test_daemon_down_is_configuration_error_with_other_errors():
    error = CredentialDaemonRequestRejectedError(error_msg='refused')
    with pytest.raises(ConfigurationError) as raised:
        with daemon_down_is_configuration_error(other_errors=True):
            raise error
    assert str(raised.value) == str(error)
    assert raised.value.__cause__ is error
    down = CredentialDaemonNotRunningError(error_msg='down')
    with pytest.raises(ConfigurationError) as raised:
        with daemon_down_is_configuration_error(other_errors=True):
            raise down
    assert str(raised.value) == daemon_down_message(down)


@pytest.mark.parametrize(
    'count, what, message',
    [
        (1, 'session', 'Signed out of 1 session in the credential daemon.\n'),
        (
            2,
            'SSO session',
            'Signed out of 2 SSO sessions in the credential daemon.\n',
        ),
    ],
)
def test_signed_out_count_message(count, what, message):
    assert signed_out_count_message(count, what) == message


@pytest.mark.parametrize(
    'subject, way_out, message',
    [
        (
            None,
            None,
            "The credential daemon isn't available on this platform.",
        ),
        (
            "profile 'dev'",
            USE_FILES_HERE_HINT,
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile and '
            'any credential_storage = daemon (or set it to file), then sign in '
            "again or enter its keys with 'aws configure'.",
        ),
        (
            None,
            WITHOUT_DAEMON_FLAG_HINT,
            "The credential daemon isn't available on this platform. To use "
            'files on this machine, run the command again without '
            '--credential-storage daemon.',
        ),
    ],
)
def test_unavailable_here_error(subject, way_out, message):
    error = unavailable_here_error(subject, way_out)
    assert isinstance(error, ConfigurationError)
    assert str(error) == message


class TestApprovalMessage:
    def error(self, daemon_message='Replace it?', remediation='creds approve'):
        error = mock.Mock(daemon_message=daemon_message)
        error.__str__ = mock.Mock(return_value='held for approval')
        error.data = {'remediation': remediation}
        return error

    def test_the_daemon_message_says_why(self):
        with mock.patch(
            'awscli.customizations.credential_daemon.messages.'
            'approval_instructions',
            return_value='Run: creds approve',
        ):
            message = approval_message(self.error(), 'Then run it again.')
        assert message == (
            'Replace it?\n  Run: creds approve\nThen run it again.'
        )

    def test_without_a_daemon_message_the_error_says_it(self):
        with mock.patch(
            'awscli.customizations.credential_daemon.messages.'
            'approval_instructions',
            return_value='Run: creds approve',
        ):
            message = approval_message(self.error(''), 'Then run it again.')
        assert message == 'held for approval\nThen run it again.'

    def test_why_given(self):
        with mock.patch(
            'awscli.customizations.credential_daemon.messages.'
            'approval_instructions',
            return_value='Run: creds approve',
        ):
            message = approval_message(self.error(''), 'Until.', why='Why:')
        assert message == 'Why:\n  Run: creds approve\nUntil.'


class TestPreviewNotice:
    def test_the_notice_text(self):
        # As the credential daemon docs word it.
        assert PREVIEW_NOTICE == (
            'note: The credential daemon support in this build is a '
            'developer preview under active development. Don\'t use it in '
            'production environments. For more information, see '
            'https://docs.aws.amazon.com/cli/latest/userguide/'
            'cli-authentication-credsd.html'
        )
