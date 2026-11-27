# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from argparse import Namespace

import pytest

from awscli.customizations.login.backends import (
    ALL_SESSIONS,
    SignInBackend,
    SignInResult,
    SignOutBackend,
    SignOutResult,
)
from awscli.customizations.login.login import LoginCommand
from awscli.customizations.login.logout import LogoutCommand
from tests import mock

ARGS = Namespace(remote=False, redirect_port=None)
GLOBAL_ARGS = Namespace(region='us-west-2', endpoint_url=None, verify_ssl=None)


class FakeSignIn(SignInBackend):
    def __init__(self, result):
        self.result = result
        self.calls = []

    def sign_in(self, request):
        self.calls.append('sign_in')
        return self.result

    def write_failed(self, request):
        self.calls.append('write_failed')

    def after_write(self, request, result):
        self.calls.append('after_write')


class FakeSignOut(SignOutBackend):
    def __init__(self, targets, result):
        self.targets = targets
        self.result = result
        self.signed_out = []

    def sessions(self, profile):
        return self.targets

    def sign_out(self, target):
        self.signed_out.append(target)
        return self.result


@pytest.fixture
def session():
    session = mock.Mock()
    session.profile = 'dev'
    session.available_profiles = ['dev']
    session.full_config = {'profiles': {'dev': {'region': 'us-west-2'}}}
    session.get_config_variable.side_effect = lambda key: (
        'configfile' if key == 'config_file' else None
    )
    return session


@pytest.fixture
def config_file_writer():
    return mock.Mock()


def login_with(session, config_file_writer, backend):
    command = LoginCommand(session, mock.Mock(), config_file_writer)
    command._sign_in_backend = lambda request: backend
    # The region rules have their own tests.
    command._resolve_profile_region = mock.Mock(return_value=None)
    return command


class TestLoginBackends:
    def test_writes_backend_values_once(self, session, config_file_writer):
        backend = FakeSignIn(
            SignInResult(
                ok=True, exit_code=None, profile_values={'key': 'value'}
            )
        )
        command = login_with(session, config_file_writer, backend)

        assert command._run_main(ARGS, GLOBAL_ARGS) is None

        config_file_writer.update_config.assert_called_once_with(
            {'__section__': 'profile dev', 'key': 'value'}, 'configfile'
        )
        assert backend.calls == ['sign_in', 'after_write']

    def test_stopped_sign_in_writes_nothing(self, session, config_file_writer):
        backend = FakeSignIn(SignInResult(ok=False, exit_code=2))
        command = login_with(session, config_file_writer, backend)

        assert command._run_main(ARGS, GLOBAL_ARGS) == 2

        config_file_writer.update_config.assert_not_called()
        assert backend.calls == ['sign_in']

    def test_failed_write_tells_backend(self, session, config_file_writer):
        config_file_writer.update_config.side_effect = OSError('read-only')
        backend = FakeSignIn(
            SignInResult(
                ok=True, exit_code=None, profile_values={'key': 'value'}
            )
        )
        command = login_with(session, config_file_writer, backend)

        with pytest.raises(OSError):
            command._run_main(ARGS, GLOBAL_ARGS)

        assert backend.calls == ['sign_in', 'write_failed']


class TestLogoutBackends:
    def logout_with(self, session, backends):
        command = LogoutCommand(session, cache_dir='unused')
        command._backends = backends
        return command

    def test_all_reports_nothing_found_only_when_every_backend_is_empty(
        self, session, capsys
    ):
        empty = FakeSignOut([ALL_SESSIONS], SignOutResult(True, True))
        found = FakeSignOut([ALL_SESSIONS], SignOutResult(True, False))
        command = self.logout_with(session, [empty, found])

        assert command._run_main(Namespace(all=True), None) == 0

        assert 'No cached login session tokens found' not in (
            capsys.readouterr().out
        )
        assert empty.signed_out == [ALL_SESSIONS]
        assert found.signed_out == [ALL_SESSIONS]

    def test_exits_1_when_any_backend_leaves_something(self, session):
        failed = FakeSignOut(['dev'], SignOutResult(False, None))
        ok = FakeSignOut(['dev'], SignOutResult(True, None))
        command = self.logout_with(session, [failed, ok])

        assert command._run_main(Namespace(all=False), None) == 1

        assert ok.signed_out == ['dev']

    def test_backend_with_nothing_for_profile_is_skipped(self, session):
        nothing = FakeSignOut([], SignOutResult(False, None))
        command = self.logout_with(session, [nothing])

        assert command._run_main(Namespace(all=False), None) == 0
