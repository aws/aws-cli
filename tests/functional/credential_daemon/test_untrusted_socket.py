# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Every command that sends the credential daemon a secret, or starts a
sign-in, checks the daemon first: the socket behind any link, the folders
on the way to it, and the process serving it. ~/.aws and the link itself
aren't checked, by these commands or the credential provider: ~/.aws has
the same trust as the config file next to it. With a peer the CLI doesn't
trust (another user's process, or on macOS a process that isn't the signed
credential daemon), each fails as if the daemon were unavailable, without
the start-the-daemon hint: the daemon gets no request, no file changes and
no browser opens.
"""

import os
import socket
import stat
import textwrap
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import START_HINT
from botocore.session import Session

from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.testutils import create_clidriver
from tests import mock
from tests.utils.credential_daemon import (
    KIND_IAM_USER,
    KIND_LOGIN,
)

UNTRUSTED = "The CLI didn't trust the credential daemon socket"
GLOBALS = Namespace(region=None, endpoint_url=None, verify_ssl=None)
# Access keys, mfa-login and SSO don't use the credential daemon in this
# version, so only aws login and aws logout are here.
CONFIG = '''
[profile dev]
region = us-west-2
credential_storage = daemon

[profile signed-in]
region = us-west-2
credential_daemon = login.dev

[profile moving]
region = us-west-2
credential_daemon = keys.moving
credential_storage = file
'''


@pytest.fixture
def fake(fake):
    fake.seed('login.dev', kind=KIND_LOGIN)
    # Its own credential: a move back to files keeps one another profile
    # names without asking the credential daemon.
    fake.seed('keys.moving', kind=KIND_IAM_USER)
    fake.calls.clear()
    return fake


@pytest.fixture
def aws_dir(tmp_path, monkeypatch, daemon_env):
    monkeypatch.setenv('HOME', str(tmp_path))
    aws_dir = tmp_path / '.aws'
    aws_dir.mkdir()
    monkeypatch.setenv('AWS_CONFIG_FILE', str(aws_dir / 'config'))
    monkeypatch.setenv(
        'AWS_SHARED_CREDENTIALS_FILE', str(aws_dir / 'credentials')
    )
    monkeypatch.setenv('AWS_LOGIN_CACHE_DIRECTORY', str(tmp_path / 'login'))
    (aws_dir / 'config').write_text(textwrap.dedent(CONFIG))
    (aws_dir / 'credentials').write_text('')
    return aws_dir


@pytest.fixture
def browser():
    with (
        mock.patch(
            'awscli.customizations.login.credential_daemon.'
            'open_browser_with_original_ld_path'
        ) as login_open,
        mock.patch('webbrowser.open') as web_open,
    ):
        yield [login_open, web_open]


# Why the peer isn't trusted, and what the error says.
PEER_RUNS_AS_ANOTHER_USER = 'the process serving it runs as uid'
PEER_ISNT_THE_SIGNED_DAEMON = (
    "the process serving it isn't the signed credential daemon"
)


@pytest.fixture(params=['another-user', 'unsigned'])
def untrusted_peer(request):
    """A peer the CLI doesn't trust; yields the reason the error gives.

    another-user: the process on the socket runs as another user.
    unsigned: on macOS, it runs as the caller but isn't the signed
    credential daemon (its code doesn't meet the requirement).
    """
    if request.param == 'another-user':
        with mock.patch(
            'botocore.credential_daemon.trust._peer_uid',
            return_value=os.geteuid() + 4242,
        ):
            yield PEER_RUNS_AS_ANOTHER_USER
        return
    with (
        mock.patch(
            'botocore.credential_daemon.transport.checks_code_signature',
            return_value=True,
        ),
        mock.patch(
            'botocore.credential_daemon.codesign._peer_audit_token',
            return_value=bytes(32),
        ),
        mock.patch(
            'botocore.credential_daemon.codesign._code_signature_status',
            return_value=-67050,
        ),
    ):
        yield PEER_ISNT_THE_SIGNED_DAEMON


def snapshot(aws_dir):
    return {
        path.relative_to(aws_dir.parent): path.read_bytes()
        for path in aws_dir.parent.rglob('*')
        if path.is_file()
    }


def aws(*args):
    return create_clidriver().main(list(args))


COMMANDS = {
    'login': (253, ['login', '--profile', 'dev']),
    'login --remote': (253, ['login', '--profile', 'dev', '--remote']),
    # Moving back to files reads what the credential holds first.
    'login to files': (253, ['login', '--profile', 'moving']),
    'logout': (1, ['logout', '--profile', 'signed-in']),
    'logout --all': (1, ['logout', '--all']),
}


@pytest.mark.parametrize('command', COMMANDS)
def test_untrusted_peer_gets_nothing(
    command, fake, aws_dir, browser, untrusted_peer, capsys
):
    rc, args = COMMANDS[command]
    before = snapshot(aws_dir)
    assert aws(*args) == rc
    err = capsys.readouterr().err
    assert UNTRUSTED in err
    assert untrusted_peer in err
    assert START_HINT not in err
    if 'logout' in command:
        # Running it again can't help until the socket is fixed.
        assert 'again' not in err
    # The credential daemon got no request: nothing was sent.
    assert fake.calls == []
    # No file was written or deleted, keys included.
    assert snapshot(aws_dir) == before
    for opened in browser:
        opened.assert_not_called()


@pytest.fixture(params=['writable-folder', 'link-owned-by-another-user'])
def loose_link(request, aws_dir, fake, monkeypatch, sock_dir):
    """~/.aws/credential-daemon.sock links to the fake, found by discovery,
    in a ~/.aws anyone can write (0777), or as a link another uid owns.
    Neither is checked. HOME is short, for sun_path; the config files stay
    where AWS_CONFIG_FILE and AWS_SHARED_CREDENTIALS_FILE name them."""
    monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET')
    monkeypatch.setenv('HOME', str(sock_dir))
    home_aws = sock_dir / '.aws'
    home_aws.mkdir()
    link = home_aws / 'credential-daemon.sock'
    link.symlink_to(fake.socket_path)
    if request.param == 'writable-folder':
        home_aws.chmod(0o777)
        yield
        assert stat.S_IMODE(home_aws.stat().st_mode) == 0o777
        home_aws.chmod(0o700)
        return
    real_lstat = os.lstat

    def lstat_(path, *args, **kwargs):
        st = real_lstat(path, *args, **kwargs)
        if str(path) == str(link):
            fields = list(st)
            fields[4] = os.geteuid() + 4242
            return os.stat_result(fields)
        return st

    with mock.patch('botocore.credential_daemon.trust.os.lstat', lstat_):
        yield


@pytest.mark.parametrize('command', COMMANDS)
def test_link_in_a_loose_aws_folder_reaches_the_daemon(
    command, fake, aws_dir, browser, loose_link, capsys
):
    # The daemon behind the link is checked, and trusted.
    _, args = COMMANDS[command]
    with mock.patch(
        'awscli.customizations.login.credential_daemon.compat_input',
        return_value='code',
    ):
        aws(*args)
    assert UNTRUSTED not in capsys.readouterr().err
    assert fake.calls != []


def test_the_provider_dials_a_link_in_a_loose_aws_folder(
    fake, aws_dir, loose_link, capsys, monkeypatch
):
    # export-credentials notes the profile in this variable; put it back
    # afterwards, so the next case isn't a loop.
    monkeypatch.delenv('_AWS_CLI_PROFILE_CHAIN', raising=False)
    assert (
        aws('configure', 'export-credentials', '--profile', 'signed-in') == 0
    )
    assert UNTRUSTED not in capsys.readouterr().err
    assert fake.calls
    assert {call[0] for call in fake.calls} == {'credential/get'}


def test_logout_all_without_daemon_profiles_warns(
    fake, aws_dir, untrusted_peer, capsys
):
    # Only file-based profiles, so nothing names the daemon, but the
    # socket is there. The CLI's sessions may be in the daemon, so
    # aws logout --all says it couldn't check them, as a warning: no
    # profile uses the daemon.
    (aws_dir / 'config').write_text('[profile files]\nregion = us-west-2\n')
    assert aws('logout', '--all') == 0
    err = capsys.readouterr().err
    assert err.startswith(
        "warning: sessions in the credential daemon weren't checked: "
        f'{UNTRUSTED}'
    )
    assert err.endswith('No profile uses it.\n')
    assert untrusted_peer in err
    assert fake.calls == []
    assert 'again' not in err


@pytest.fixture(params=['unchecked-signature', 'signed'])
def trusted_peer(request):
    # The real peer. signed: the code signature check runs too, as on
    # macOS, and the peer meets the requirement.
    if request.param == 'unchecked-signature':
        yield
        return
    with (
        mock.patch(
            'botocore.credential_daemon.transport.checks_code_signature',
            return_value=True,
        ),
        mock.patch(
            'botocore.credential_daemon.codesign._peer_audit_token',
            return_value=bytes(32),
        ),
        mock.patch(
            'botocore.credential_daemon.codesign._code_signature_status',
            return_value=0,
        ) as status,
    ):
        yield
        status.assert_called()


@pytest.mark.parametrize('command', COMMANDS)
def test_trusted_peer_gets_the_request(
    command, fake, aws_dir, browser, trusted_peer, capsys
):
    # The same commands, with the real peer: each reaches the daemon, so
    # the test above shows the check is what stopped them.
    _, args = COMMANDS[command]
    with mock.patch(
        'awscli.customizations.login.credential_daemon.compat_input',
        return_value='code',
    ):
        aws(*args)
    assert UNTRUSTED not in capsys.readouterr().err
    assert fake.calls != []


@pytest.mark.parametrize('args', [[], ['--remote']], ids=['login', 'remote'])
def test_login_asks_no_region(fake, aws_dir, browser, untrusted_peer, args):
    from awscli.customizations.login.login import LoginCommand

    config = aws_dir / 'config'
    # No region, so the region prompt would come first.
    config.write_text(config.read_text().replace('region = us-west-2\n', ''))
    before = snapshot(aws_dir)
    with (
        mock.patch.object(
            LoginCommand,
            '_prompt_for_region',
            side_effect=AssertionError('prompted'),
        ),
        pytest.raises(ConfigurationError) as e,
    ):
        LoginCommand(Session(profile='dev'))(args, GLOBALS)
    assert UNTRUSTED in str(e.value)
    assert fake.calls == []
    assert snapshot(aws_dir) == before
    for opened in browser:
        opened.assert_not_called()


@pytest.mark.parametrize(
    'clear, start',
    [
        (
            lambda command: command._credential_daemon._clear_declined(
                'dev', 'login.dev'
            ),
            "The new session for 'dev' is still in the credential daemon as "
            "'login.dev': ",
        ),
    ],
    ids=['declined'],
)
def test_login_leaving_a_session_gives_only_the_trust_error(
    fake, aws_dir, untrusted_peer, capsys, clear, start
):
    # As for aws logout, aws logout --all wouldn't help until the socket
    # is fixed, so there's no hint to run it.
    from awscli.customizations.login.login import LoginCommand

    clear(LoginCommand(Session(profile='dev')))
    err = capsys.readouterr().err
    assert err.startswith(start)
    assert f': {UNTRUSTED}' in err
    assert 'aws logout --all' not in err
    assert START_HINT not in err
    assert err.endswith('.\n')
    assert ' \n' not in err
    assert fake.calls == []


def test_storage_question_treats_it_as_unavailable(
    fake, aws_dir, untrusted_peer, capsys
):
    # A profile with no saved choice, in a terminal: the probe's
    # credential/list isn't sent, there's no question, and one line says
    # why. The session goes to files, as when no credential daemon is
    # running.
    from botocore.session import Session

    ask = mock.Mock()
    chooser = CredentialStorageChooser(
        Session(), is_tty=lambda: True, ask=ask, environ={}
    )
    choice = chooser.choose('new-profile')
    assert not choice.uses_credential_daemon
    ask.assert_not_called()
    assert fake.calls == []
    err = capsys.readouterr().err
    assert err.count('\n') == 1
    assert err.startswith(
        'Note: The credential daemon can\'t be used, so this command keeps '
        'credentials in files, in plaintext: ' + UNTRUSTED
    )
