# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from botocore.exceptions import (
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonUnsupportedPlatformError,
    CredentialDaemonUntrustedSocketError,
)

from awscli.customizations.credential_daemon.command import (
    CredentialDaemonCommandSupport,
)
from awscli.customizations.credential_daemon.results import (
    Cleared,
    ClearOutcome,
)
from awscli.customizations.exceptions import ConfigurationError
from tests import mock


def test_client_is_made_once_and_shared():
    with mock.patch(
        'awscli.customizations.credential_daemon.command.command_client'
    ) as make:
        support = CredentialDaemonCommandSupport(mock.Mock())
        assert support.client() is support.client()
    make.assert_called_once_with()


def test_client_passed_in_is_used():
    client = mock.Mock()
    assert (
        CredentialDaemonCommandSupport(mock.Mock(), client).client() is client
    )


def test_check_ready_checks_the_client():
    client = mock.Mock()
    with (
        mock.patch(
            'awscli.customizations.credential_daemon.command.'
            'check_credential_daemon_ready'
        ) as check,
        # As where the credential daemon runs, Windows too.
        mock.patch(
            'awscli.customizations.credential_daemon.command.'
            'credential_daemon_runs_here',
            return_value=True,
        ),
    ):
        CredentialDaemonCommandSupport(mock.Mock(), client).check_ready()
    check.assert_called_once_with(client)


def test_run_again_hint_runs_the_command():
    support = CredentialDaemonCommandSupport(mock.Mock())
    hint = support.run_again_hint(ValueError('x'), 'aws logout')
    assert hint == " Run 'aws logout' again."


def test_run_again_hint_has_a_tail():
    support = CredentialDaemonCommandSupport(mock.Mock())
    hint = support.run_again_hint(
        ValueError('x'), 'aws logout --all', 'to sign it out.'
    )
    assert hint == " Run 'aws logout --all' to sign it out."


class TestClearOldCopy:
    def support(self, tmp_path, runs_here=True, present=True):
        socket_path = tmp_path / 'daemon.sock'
        if present:
            socket_path.touch()
        client = mock.Mock(socket_path=str(socket_path))
        support = CredentialDaemonCommandSupport(mock.Mock(), client)
        support.runs_here = mock.Mock(return_value=runs_here)
        return support, client

    def test_cleared_has_the_calls_result(self, tmp_path):
        support, client = self.support(tmp_path)
        cleared = support.clear_old_copy(lambda c: c.logout('login.x'))
        assert cleared == Cleared(
            ClearOutcome.CLEARED, result=client.logout.return_value
        )
        client.logout.assert_called_once_with('login.x')

    def test_not_found(self, tmp_path):
        support, client = self.support(tmp_path)
        client.logout.side_effect = CredentialDaemonCredentialNotFoundError(
            error_msg='gone'
        )
        cleared = support.clear_old_copy(lambda c: c.logout('login.x'))
        assert cleared == Cleared(ClearOutcome.NOT_FOUND)

    def test_failed_has_the_error(self, tmp_path):
        support, client = self.support(tmp_path)
        error = CredentialDaemonRequestRejectedError(error_msg='no')
        client.logout.side_effect = error
        cleared = support.clear_old_copy(lambda c: c.logout('login.x'))
        assert cleared == Cleared(ClearOutcome.FAILED, error=error)

    def test_where_it_doesnt_run_nothing_is_sent(self, tmp_path):
        support, client = self.support(tmp_path, runs_here=False)
        cleared = support.clear_old_copy(lambda c: c.logout('login.x'))
        assert cleared == Cleared(ClearOutcome.UNSUPPORTED_PLATFORM)
        assert client.mock_calls == []

    def test_with_nothing_at_the_socket_nothing_is_sent(self, tmp_path):
        support, client = self.support(tmp_path, present=False)
        cleared = support.clear_old_copy(lambda c: c.logout('login.x'))
        assert cleared == Cleared(
            ClearOutcome.ABSENT, socket_path=client.socket_path
        )
        assert client.mock_calls == []


class TestWhereTheCredentialDaemonDoesntRun:
    # Such as Windows: the refusal names the profile and how to use files
    # for it, and nothing is dialed.
    def support(self, profiles, environ=None):
        session = mock.Mock()
        session.full_config = {'profiles': profiles}
        session.get_config_variable.return_value = '/nonexistent/aws-file'
        support = CredentialDaemonCommandSupport(session, mock.Mock())
        patches = [
            mock.patch(
                'awscli.customizations.credential_daemon.command.'
                'credential_daemon_runs_here',
                return_value=False,
            ),
            mock.patch.dict('os.environ', environ or {}, clear=True),
        ]
        for patch in patches:
            patch.start()
        self._patches = patches
        return support

    def teardown_method(self):
        for patch in getattr(self, '_patches', []):
            patch.stop()

    def refusal(self, support, *args, **kwargs):
        with pytest.raises(ConfigurationError) as e:
            support.check_ready(*args, **kwargs)
        support.client().probe.assert_not_called()
        return str(e.value)

    @pytest.mark.parametrize(
        'profile',
        [
            {'credential_daemon': 'login.dev'},
            {'credential_daemon': 'login.dev', 'credential_storage': 'daemon'},
        ],
    )
    def test_a_profile_with_credential_daemon(self, profile):
        # credential_storage = daemon would refuse the next sign-in too, so
        # the hint names it.
        support = self.support({'dev': profile})
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile '
            'and any credential_storage = daemon (or set it to file), then '
            "sign in again or enter its keys with 'aws configure'."
        )

    def test_an_sso_profile_with_credential_daemon_names_the_profile(self):
        # The sso-session's credential_storage isn't read.
        support = self.support(
            {'dev': {'credential_daemon': 'sso.acme', 'sso_session': 'acme'}}
        )
        support._session.full_config['sso_sessions'] = {
            'acme': {'credential_storage': 'daemon'}
        }
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile '
            'and any credential_storage = daemon (or set it to file), then '
            "sign in again or enter its keys with 'aws configure'."
        )

    def test_a_profile_with_credential_daemon_and_the_storage_variable(self):
        # The variable wins over the profile.
        support = self.support(
            {'dev': {'credential_daemon': 'login.dev'}},
            environ={'AWS_CREDENTIAL_STORAGE': 'daemon'},
        )
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use it on this machine, "
            'use files for it: remove credential_daemon from the profile '
            'and run the command again with AWS_CREDENTIAL_STORAGE=file.'
        )

    def test_a_profile_whose_storage_says_daemon(self):
        support = self.support({'dev': {'credential_storage': 'daemon'}})
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use files for it, set "
            'credential_storage = file in the profile.'
        )

    def test_the_storage_variable_says_daemon(self):
        support = self.support(
            {'dev': {}}, environ={'AWS_CREDENTIAL_STORAGE': 'daemon'}
        )
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use files for it, run the "
            'command again with AWS_CREDENTIAL_STORAGE=file.'
        )

    def test_the_storage_option_says_daemon(self):
        support = self.support({'dev': {}})
        assert self.refusal(support, 'dev', flag=True) == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use files on this "
            'machine, run the command again without --credential-storage '
            'daemon.'
        )

    def test_an_sso_profile_whose_storage_says_daemon(self):
        # Read from the profile, not its sso-session.
        support = self.support(
            {'dev': {'sso_session': 'acme', 'credential_storage': 'daemon'}}
        )
        support._session.full_config['sso_sessions'] = {
            'acme': {'credential_storage': 'file'}
        }
        assert self.refusal(support, 'dev') == (
            "The credential daemon isn't available on this platform, so "
            "profile 'dev' can't be used here. To use files for it, set "
            'credential_storage = file in the profile.'
        )

    def test_the_storage_option_on_a_profile_with_credential_daemon(self):
        # Running without the option would be refused too.
        support = self.support({'dev': {'credential_daemon': 'keys.dev'}})
        assert 'remove credential_daemon from the profile' in self.refusal(
            support, 'dev', flag=True
        )

    def test_no_profile(self):
        support = self.support({})
        assert self.refusal(support) == (
            "The credential daemon isn't available on this platform."
        )

    def test_check_ready_if_stored_names_the_profile(self):
        support = self.support({'dev': {'credential_daemon': 'keys.dev'}})
        with pytest.raises(ConfigurationError) as e:
            support.check_ready_if_stored('dev')
        assert "so profile 'dev' can't be used here" in str(e.value)

    def test_check_ready_if_stored_skips_a_profile_moving_back(self):
        # credential_storage = file: the command uses files, which work.
        support = self.support(
            {
                'dev': {
                    'credential_daemon': 'keys.dev',
                    'credential_storage': 'file',
                }
            }
        )
        support.check_ready_if_stored('dev')


def test_runs_here_follows_the_platform_check():
    with mock.patch(
        'awscli.customizations.credential_daemon.command.'
        'credential_daemon_runs_here',
        return_value=False,
    ):
        assert not CredentialDaemonCommandSupport(mock.Mock()).runs_here()


def test_warn_unchecked_says_what_and_how_to_clear_it(capsys):
    support = CredentialDaemonCommandSupport(mock.Mock())
    support.warn_unchecked(
        'sessions', ValueError('go\x1bne'), 'aws logout --all'
    )
    assert capsys.readouterr().err == (
        "warning: sessions in the credential daemon weren't checked: gone. "
        "No profile uses it. Run 'aws logout --all' again to clear them.\n"
    )


def test_report_uncleared_says_what_and_how_to_run_it_again(capsys):
    support = CredentialDaemonCommandSupport(mock.Mock())
    support.report_uncleared(
        'Sessions', ValueError('go\x1bne'), "weren't", 'aws logout --all'
    )
    assert capsys.readouterr().err == (
        "Sessions in the credential daemon weren't cleared: gone. "
        "Run 'aws logout --all' again.\n"
    )


def test_run_again_hint_is_empty_for_an_untrusted_socket():
    support = CredentialDaemonCommandSupport(mock.Mock())
    error = CredentialDaemonUntrustedSocketError(error_msg='untrusted')
    assert support.run_again_hint(error, 'aws logout') == ''


def test_warn_unchecked_has_no_run_hint_for_an_untrusted_socket(capsys):
    support = CredentialDaemonCommandSupport(mock.Mock())
    error = CredentialDaemonUntrustedSocketError(error_msg='untrusted')
    support.warn_unchecked('sessions', error, 'aws logout --all')
    assert capsys.readouterr().err == (
        "warning: sessions in the credential daemon weren't checked: "
        'untrusted. No profile uses it.\n'
    )


def test_run_again_hint_is_empty_where_the_credential_daemon_doesnt_run():
    support = CredentialDaemonCommandSupport(mock.Mock())
    error = CredentialDaemonUnsupportedPlatformError(error_msg='x')
    assert support.run_again_hint(error, 'aws logout --all') == ''
