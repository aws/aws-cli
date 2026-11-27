# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""scripts/credential-daemon-check-peer: runs the checks commands make
before they send secrets, prints each result, and sends nothing."""

import importlib.machinery
import importlib.util
import os
import socket
import subprocess
import sys

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.exceptions import CredentialDaemonUntrustedSocketError

from tests import mock
from tests.utils.credential_daemon import FakeCredentialDaemon

SCRIPT = os.path.join(
    os.path.dirname(__file__),
    '..',
    '..',
    '..',
    'scripts',
    'credential-daemon-check-peer',
)


# The script's own process imports awscli from here, not from whatever
# checkout the interpreter's install points at.
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), *['..'] * 3)
)


def child_env():
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(
        filter(None, [REPO_ROOT, os.environ.get('PYTHONPATH')])
    )
    return env


def load_script():
    loader = importlib.machinery.SourceFileLoader('check_peer_script', SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def check_peer(path):
    return subprocess.run(
        [sys.executable, SCRIPT, path],
        capture_output=True,
        text=True,
        timeout=60,
        env=child_env(),
    )


def test_own_daemon_and_nothing_is_sent(private_dir):
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'f' / 'daemon.sock')
    ) as fake:
        run = check_peer(fake.socket_path)
        assert fake.calls == []
    lines = run.stdout.splitlines()
    assert 'path: pass' in lines
    assert 'peer uid: pass' in lines
    if sys.platform == 'darwin':
        # The fake is this Python, not the signed credential daemon.
        assert run.returncode == 1
        assert any(
            line.startswith('code signature: refused')
            and 'isn\'t the signed credential daemon' in line
            for line in lines
        ), run.stdout
        assert lines[-1] == 'result: refused'
    else:
        assert run.returncode == 0, run.stdout + run.stderr
        assert 'code signature: not checked (macOS only)' in lines
        assert lines[-1] == 'result: pass'


def test_loose_folder_is_refused_and_later_checks_still_run(private_dir):
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'f' / 'daemon.sock')
    ) as fake:
        os.chmod(private_dir, 0o777)
        try:
            run = check_peer(fake.socket_path)
        finally:
            os.chmod(private_dir, 0o700)
        assert fake.calls == []
    assert run.returncode == 1
    assert 'is writable by other users (mode 0777)' in run.stdout
    assert 'peer uid: pass' in run.stdout.splitlines()
    assert run.stdout.splitlines()[-1] == 'result: refused'


def test_missing_socket(private_dir):
    run = check_peer(str(private_dir / 'missing.sock'))
    assert run.returncode == 1
    assert 'path: refused: The credential daemon isn\'t running' in run.stdout
    assert 'connect: refused' in run.stdout


def test_control_characters_never_reach_the_terminal(private_dir):
    # The OS's error text names the path as given.
    missing = private_dir / 'x\x1b[2J.sock'
    run = check_peer(str(missing))
    assert run.returncode == 1
    assert 'connect: refused: No such file or directory' in run.stdout
    assert '\x1b' not in run.stdout


def test_a_socket_nothing_listens_on(private_dir):
    path = private_dir / 'x\x1b[2J.sock'
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.close()
    run = check_peer(str(path))
    assert run.returncode == 1
    assert 'connect: refused: Connection refused' in run.stdout
    assert '\x1b' not in run.stdout


def test_another_users_socket_never_passes_the_peer_check(private_dir, capsys):
    # The socket and the process serving it belong to another user, so the
    # path check refuses it. The peer check must then allow only this user
    # and root, as commands do, not the socket's owner.
    script = load_script()
    other = os.geteuid() + 4242
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'daemon.sock')
    ) as fake:
        refused = CredentialDaemonUntrustedSocketError(
            error_msg='the socket is owned by another user'
        )
        lstat = os.lstat

        def owned_by_other(path, *args, **kwargs):
            st = lstat(path, *args, **kwargs)
            if os.fspath(path) == fake.socket_path:
                fields = list(st)
                fields[4] = other
                return os.stat_result(fields)
            return st

        with (
            mock.patch.object(script.cd, 'check_socket', side_effect=refused),
            # check_peer, through the script's module, is in the trust module.
            mock.patch(
                'botocore.credential_daemon.trust._peer_uid',
                return_value=other,
            ),
            mock.patch.object(
                script.cd, 'checks_code_signature', return_value=False
            ),
            mock.patch('os.lstat', owned_by_other),
        ):
            rc = script.main([fake.socket_path])
        assert fake.calls == []
    lines = capsys.readouterr().out.splitlines()
    assert rc == 1
    assert 'path: refused: the socket is owned by another user' in lines
    assert any(line.startswith('peer uid: refused') for line in lines), lines
    assert lines[-1] == 'result: refused'


def run_at_macos_system_socket(script, fake, owners, peer=0, signature=None):
    # The fake's socket as the macOS system socket, with the owners given
    # (path to uid) and served as peer (root, as launchd does), on a host
    # that checks code signatures. signature is what check_code_signature
    # raises (None: the signed daemon). Returns the exit status and the
    # check_code_signature mock.
    lstat = os.lstat

    def owned(path, *args, **kwargs):
        st = lstat(path, *args, **kwargs)
        uid = owners.get(os.fspath(path))
        if uid is None:
            return st
        fields = list(st)
        fields[4] = uid
        return os.stat_result(fields)

    system = {fake.socket_path}
    with (
        mock.patch(
            'botocore.credential_daemon.trust.system_socket_paths',
            return_value=system,
        ),
        mock.patch(
            'botocore.credential_daemon.trust._system_socket_root_only',
            return_value=True,
        ),
        mock.patch.object(
            script.cd, 'checks_code_signature', return_value=True
        ),
        mock.patch.object(
            script.cd, 'check_code_signature', side_effect=signature
        ) as sig,
        mock.patch(
            'botocore.credential_daemon.trust._peer_uid', return_value=peer
        ),
        mock.patch('os.lstat', owned),
    ):
        rc = script.main([fake.socket_path])
    return rc, sig


def test_macos_system_socket_checks_the_code_signature(private_dir, capsys):
    # As commands that send secrets do: the system socket gets the path,
    # peer and code signature checks.
    script = load_script()
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'credsd' / 'credsd.sock')
    ) as fake:
        folder = os.path.dirname(fake.socket_path)
        rc, sig = run_at_macos_system_socket(
            script, fake, {fake.socket_path: 0, folder: 0}
        )
        assert fake.calls == []
    lines = capsys.readouterr().out.splitlines()
    assert rc == 0, lines
    sig.assert_called_once()
    assert sig.call_args.args[1] == fake.socket_path
    assert 'path: pass' in lines
    assert 'code signature: pass' in lines
    assert lines[-1] == 'result: pass'


def test_macos_system_socket_refuses_an_unsigned_daemon(private_dir, capsys):
    # A source-built daemon installed as a system service isn't signed:
    # refused, with the install-the-signed-release hint.
    script = load_script()
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'credsd' / 'credsd.sock')
    ) as fake:
        folder = os.path.dirname(fake.socket_path)
        unsigned = CredentialDaemonUntrustedSocketError(
            error_msg=(
                'The CLI didn\'t trust the credential daemon socket '
                f'{fake.socket_path}, so it sent nothing to it: the process '
                'serving it isn\'t the signed credential daemon (OSStatus '
                '-67062). Install the signed release with "aws configure '
                'credential-daemon install".'
            )
        )
        rc, _ = run_at_macos_system_socket(
            script, fake, {fake.socket_path: 0, folder: 0}, signature=unsigned
        )
        assert fake.calls == []
    lines = capsys.readouterr().out.splitlines()
    assert rc == 1
    assert 'path: pass' in lines
    assert 'peer uid: pass' in lines
    assert any(
        line.startswith('code signature: refused: ')
        and 'isn\'t the signed credential daemon (OSStatus -67062).' in line
        and line.endswith(
            'Install the signed release with '
            '"aws configure credential-daemon install".'
        )
        for line in lines
    ), lines
    assert lines[-1] == 'result: refused'


def test_macos_system_socket_needs_a_root_folder(private_dir, capsys):
    script = load_script()
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'credsd' / 'credsd.sock')
    ) as fake:
        folder = os.path.dirname(fake.socket_path)
        rc, _ = run_at_macos_system_socket(
            script, fake, {fake.socket_path: 0, folder: 1}
        )
        assert fake.calls == []
    lines = capsys.readouterr().out.splitlines()
    assert rc == 1
    assert any(
        line.startswith('path: refused: ')
        and line.endswith(
            f'its folder {folder} is owned by uid 1, not by root.'
        )
        for line in lines
    ), lines
    assert lines[-1] == 'result: refused'


def test_macos_system_socket_needs_a_root_peer(private_dir, capsys):
    # The path checks pass, as for a socket swapped in after them; the
    # process serving it isn't root (uid 501, mocked so the test holds
    # when it runs as root).
    script = load_script()
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'credsd' / 'credsd.sock')
    ) as fake:
        folder = os.path.dirname(fake.socket_path)
        rc, _ = run_at_macos_system_socket(
            script, fake, {fake.socket_path: 0, folder: 0}, peer=501
        )
        assert fake.calls == []
    lines = capsys.readouterr().out.splitlines()
    assert rc == 1
    assert 'path: pass' in lines
    assert any(
        line.startswith('peer uid: refused: ')
        and line.endswith('runs as uid 501, not as root.')
        for line in lines
    ), lines
    assert lines[-1] == 'result: refused'


def check_default(home, *args):
    # No SOCKET_PATH (unless given): the socket the CLI would dial, under
    # this HOME.
    env = child_env()
    env.pop('AWS_CREDENTIAL_DAEMON_SOCKET', None)
    env['HOME'] = str(home)
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def test_the_link_is_checked_first(private_dir):
    home = private_dir / 'h'
    (home / '.aws').mkdir(parents=True, mode=0o700)
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'f' / 'daemon.sock')
    ) as fake:
        (home / '.aws' / 'credential-daemon.sock').symlink_to(fake.socket_path)
        run = check_default(home)
        assert fake.calls == []
    lines = run.stdout.splitlines()
    assert f'link: -> {fake.socket_path}' in lines
    assert lines.index('link: pass') < lines.index('path: pass')


def test_the_link_given_by_hand_is_checked_too(private_dir):
    home = private_dir / 'h'
    (home / '.aws').mkdir(parents=True, mode=0o700)
    link = home / '.aws' / 'credential-daemon.sock'
    link.symlink_to(private_dir / 'gone' / 'daemon.sock')
    run = check_default(home, str(link))
    assert run.returncode == 1
    assert any(
        line.startswith('link: refused: ') and 'which isn\'t there' in line
        for line in run.stdout.splitlines()
    )


def test_no_home_says_so(private_dir):
    run = check_default('relative')
    assert run.returncode == 1
    assert run.stdout == (
        "No socket: HOME isn't an absolute path, so there's no "
        "~/.aws/credential-daemon.sock, and AWS_CREDENTIAL_DAEMON_SOCKET "
        "isn't set to an absolute path.\n"
    )


def test_a_loose_aws_folder_passes_the_link_check(private_dir):
    # ~/.aws has the same trust as the config file next to it: no owner
    # or mode check. The daemon behind the link is still checked.
    home = private_dir / 'h'
    (home / '.aws').mkdir(parents=True, mode=0o700)
    with FakeCredentialDaemon(
        socket_path=str(private_dir / 'f' / 'daemon.sock')
    ) as fake:
        (home / '.aws' / 'credential-daemon.sock').symlink_to(fake.socket_path)
        (home / '.aws').chmod(0o777)
        try:
            run = check_default(home)
        finally:
            (home / '.aws').chmod(0o700)
    lines = run.stdout.splitlines()
    assert 'link: pass' in lines
    assert 'path: pass' in lines
    assert 'peer uid: pass' in lines


def test_no_link_says_so(private_dir):
    home = private_dir / 'h'
    home.mkdir()
    run = check_default(home)
    assert run.returncode == 1
    assert run.stdout == (
        f'No socket: nothing is at {home}/.aws/credential-daemon.sock, and '
        "AWS_CREDENTIAL_DAEMON_SOCKET isn't set to an absolute path.\n"
    )
