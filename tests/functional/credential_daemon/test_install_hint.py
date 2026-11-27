# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the hint to install the credential daemon, shown when aws login
writes a session to a file and the credential daemon isn't installed."""

import os
import socket
import textwrap
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.session import Session

import awscli
from awscli.customizations.configure import credentialdaemon
from awscli.customizations.configure.configure import ConfigureCommand
from awscli.customizations.configure.importer import ConfigureImportCommand
from awscli.customizations.configure.set import ConfigureSetCommand
from awscli.customizations.credential_daemon import hint
from awscli.customizations.credential_daemon.hint import (
    print_session_install_hint,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    StorageChoice,
)
from awscli.customizations.credential_daemon.storage.policy import (
    DecisionSource,
    Storage,
)
from awscli.customizations.login.login import LoginCommand
from awscli.customizations.login.signup import SignupCommand
from tests import CLIRunner, HTTPResponse, mock
from tests.functional.credential_daemon.login_helpers import (
    files_sign_in,
    login,
)

ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
GLOBALS = Namespace(region=None, endpoint_url=None, verify_ssl=None)
LOGIN_NOTE = (
    'note: this session is stored unencrypted in ~/.aws/login/cache. A '
    'developer preview of the AWS credential daemon is available (not for '
    'production use): aws configure credential-daemon install\n'
)


@pytest.fixture
def home(home_aws_dir):
    # Not readable by others, so there's no permissions warning.
    (home_aws_dir / 'credentials').chmod(0o600)
    return home_aws_dir.parent


@pytest.fixture
def terminal():
    with mock.patch.object(hint, '_in_terminal', return_value=True):
        yield


@pytest.fixture
def supported():
    with mock.patch.object(
        credentialdaemon, 'install_supported', return_value=True
    ) as install_supported:
        yield install_supported


def write_config(home, text):
    (home / '.aws' / 'config').write_text(textwrap.dedent(text))


class Prompter:
    def __init__(self, **values):
        self._values = values

    def get_value(self, current_value, config_name, prompt_text=''):
        return self._values.get(config_name)


def configure(profile='ci', **values):
    command = ConfigureCommand(
        Session(profile=profile), prompter=Prompter(**values)
    )
    with mock.patch(
        'awscli.customizations.configure.configure.maybe_prompt_agent_toolkit'
    ):
        return command([], GLOBALS)


def configure_set(*args, profile='ci'):
    return ConfigureSetCommand(Session(profile=profile))(list(args), GLOBALS)


def configure_import(rows, *args):
    csv = 'User Name,Access key ID,Secret access key\n' + ''.join(
        f'{name},{ACCESS_KEY},{SECRET_KEY}\n' for name in rows
    )
    command = ConfigureImportCommand(Session())
    return command(['--csv', csv, *args], GLOBALS)


def file_login(fake, environ=None, command_class=LoginCommand):
    fetch, uri, auth = files_sign_in()
    with fetch, uri, auth:
        # No terminal for the storage question, which a machine without
        # the credential daemon never asks anyway.
        login(fake, tty=False, environ=environ, command_class=command_class)


class TestShown:
    def test_aws_login(self, fake, home, terminal, supported, capsys):
        file_login(fake)
        assert capsys.readouterr().err == LOGIN_NOTE

    def test_a_link_to_nothing_is_not_installed(
        self, fake, home, terminal, supported, capsys
    ):
        # What an uninstall leaves for other users.
        (home / '.aws' / 'credential-daemon.sock').symlink_to(home / 'nothing')
        file_login(fake)
        assert capsys.readouterr().err == LOGIN_NOTE

    def test_a_relative_socket_variable_counts_as_unset(
        self, fake, home, monkeypatch, terminal, supported, capsys
    ):
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', 'credsd.sock')
        file_login(fake)
        assert capsys.readouterr().err == LOGIN_NOTE


KEYS_NOTE = (
    "note: the IAM access keys for 'ci' are stored unencrypted in "
    '~/.aws/credentials. A developer preview of the AWS credential daemon '
    'is available for new profiles (not for production use): aws configure '
    'credential-daemon install\n'
)


class TestShownForAccessKeys:
    def test_aws_configure(self, home, terminal, supported, capsys):
        configure(
            aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY
        )
        assert capsys.readouterr().err == KEYS_NOTE

    def test_aws_configure_on_an_existing_profile(
        self, home, terminal, supported, capsys
    ):
        write_config(home, '[profile ci]\nregion = us-west-2\n')
        configure(aws_secret_access_key=SECRET_KEY)
        assert capsys.readouterr().err == KEYS_NOTE


class TestNotShown:
    def test_not_in_a_terminal(self, fake, home, supported, capsys):
        file_login(fake)
        assert capsys.readouterr().err == ''

    @pytest.mark.parametrize(
        'config, environ',
        [
            ('', None),
            ('[profile dev]\ncredential_storage = file\n', None),
            ('', {'AWS_CREDENTIAL_STORAGE': 'file'}),
        ],
    )
    def test_aws_signup(
        self, fake, home, terminal, supported, capsys, config, environ
    ):
        # aws signup never uses the credential daemon, so it prints what
        # an AWS CLI without the credential daemon prints.
        write_config(home, config)
        file_login(fake, environ=environ, command_class=SignupCommand)
        assert 'login_session' in (home / '.aws' / 'config').read_text()
        assert capsys.readouterr().err == ''

    def test_profile_chose_files(
        self, fake, home, terminal, supported, capsys
    ):
        write_config(
            home,
            '''
            [profile ci]
            credential_storage = file
            [profile dev]
            credential_storage = file
            ''',
        )
        file_login(fake)
        assert capsys.readouterr().err == ''

    def test_environment_chose_files(
        self, fake, home, monkeypatch, terminal, supported, capsys
    ):
        monkeypatch.setenv('AWS_CREDENTIAL_STORAGE', 'file')
        file_login(fake, environ={'AWS_CREDENTIAL_STORAGE': 'file'})
        assert capsys.readouterr().err == ''

    def test_unsupported_platform(
        self, fake, home, terminal, supported, capsys
    ):
        supported.return_value = False
        file_login(fake)
        assert capsys.readouterr().err == ''

    def test_home_socket_present(
        self, fake, home, terminal, supported, capsys
    ):
        (home / '.aws' / 'credential-daemon.sock').symlink_to(fake.socket_path)
        file_login(fake)
        assert capsys.readouterr().err == ''

    def test_socket_variable_present(
        self, fake, home, monkeypatch, terminal, supported, capsys
    ):
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', fake.socket_path)
        file_login(
            fake, environ={'AWS_CREDENTIAL_DAEMON_SOCKET': fake.socket_path}
        )
        assert capsys.readouterr().err == ''

    def test_socket_present_but_not_running(
        self, home, terminal, supported, capsys
    ):
        # Something is there: the messages that dial it cover it.
        (home / '.aws' / 'credential-daemon.sock').write_text('')
        assert hint._credential_daemon_is_installed() is True

    # aws configure set and import write access keys to files as before
    # the credential daemon, so they print no note.
    def test_access_keys_set_or_imported(
        self, home, terminal, supported, capsys
    ):
        configure_set('aws_secret_access_key', SECRET_KEY)
        configure_import(['ci'])
        assert capsys.readouterr().err == ''

    def test_temporary_access_keys(self, home, terminal, supported, capsys):
        configure(
            aws_access_key_id='ASIAIOSFODNN7EXAMPLE',
            aws_secret_access_key=SECRET_KEY,
            aws_session_token='token',
        )
        assert capsys.readouterr().err == ''

    def test_access_keys_on_files_by_choice(
        self, home, terminal, supported, capsys
    ):
        write_config(home, '[profile ci]\ncredential_storage = file\n')
        configure(
            aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY
        )
        assert capsys.readouterr().err == ''

    def test_region_only(self, home, terminal, supported, capsys):
        configure(region='us-west-2')
        configure_set('region', 'us-west-2')
        assert capsys.readouterr().err == ''

    @pytest.mark.parametrize(
        'source', [DecisionSource.ENV.value, DecisionSource.SAVED.value]
    )
    def test_session_on_files_by_choice(
        self, home, terminal, supported, capsys, source
    ):
        print_session_install_hint(
            StorageChoice(Storage.FILE, DecisionSource(source)), str(home)
        )
        assert capsys.readouterr().err == ''

    def test_never_breaks_the_command(self, home, terminal, supported, capsys):
        supported.side_effect = RuntimeError('boom')
        print_session_install_hint(
            StorageChoice(Storage.FILE, DecisionSource.DEFAULT), 'x'
        )
        assert capsys.readouterr().err == ''

    def test_api_calls(self, home, terminal, supported):
        # Only commands that write a secret show it: an API call in a
        # terminal, with the credential daemon not installed, says nothing.
        result = api_call_with_plaintext_keys(home, terminal=True)
        assert result.rc == 0, result.stderr
        assert result.stderr == ''

    def test_api_calls_with_the_credential_daemon_running(
        self, fake, home, supported
    ):
        # Nothing says the keys are in plaintext, even with the credential
        # daemon installed and running.
        result = api_call_with_plaintext_keys(
            home, terminal=True, AWS_CREDENTIAL_DAEMON_SOCKET=fake.socket_path
        )
        assert result.rc == 0, result.stderr
        assert result.stderr == ''
        assert fake.calls == []


def api_call_with_plaintext_keys(home, terminal=False, **environ):
    (home / '.aws' / 'credentials').write_text(
        f'[ci]\naws_access_key_id = {ACCESS_KEY}\n'
        f'aws_secret_access_key = {SECRET_KEY}\n'
    )
    runner = CLIRunner(
        env={
            'AWS_DATA_PATH': os.path.join(
                os.path.dirname(awscli.__file__), 'data'
            ),
            'AWS_DEFAULT_REGION': 'us-west-2',
            'HOME': str(home),
            'AWS_CONFIG_FILE': str(home / '.aws' / 'config'),
            'AWS_SHARED_CREDENTIALS_FILE': str(home / '.aws' / 'credentials'),
            **environ,
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
    # CLIRunner swaps in streams without a file descriptor, so a terminal
    # is patched where each check reads it.
    with (
        mock.patch('awscli.utils.os.isatty', return_value=terminal),
        mock.patch.object(hint, '_in_terminal', return_value=terminal),
    ):
        return runner.run(['sts', 'get-caller-identity', '--profile', 'ci'])


class StreamWithoutFileno:
    """A stream a host program swapped in, with no fileno or isatty."""

    def write(self, text):
        pass

    def flush(self):
        pass


def test_a_stderr_without_fileno_isnt_a_terminal(monkeypatch):
    with mock.patch('awscli.utils.os.isatty', return_value=True):
        monkeypatch.setattr('sys.stdin', mock.Mock(fileno=lambda: 0))
        monkeypatch.setattr('sys.stderr', StreamWithoutFileno())
        assert hint._in_terminal() is False


def test_both_streams_on_a_terminal_is_a_terminal(monkeypatch):
    with mock.patch('awscli.utils.os.isatty', return_value=True):
        monkeypatch.setattr('sys.stdin', mock.Mock(fileno=lambda: 0))
        monkeypatch.setattr('sys.stderr', mock.Mock(fileno=lambda: 2))
        assert hint._in_terminal() is True
