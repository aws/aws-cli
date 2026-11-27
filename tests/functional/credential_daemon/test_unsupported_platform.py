# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Where the credential daemon doesn't run, such as Windows, the commands
behave as an AWS CLI without credential daemon support: same output, same
exit code. A profile that uses the credential daemon only adds a warning
to aws logout --all.

Each command runs in a subprocess with stdin and stderr on a pty, as in a
terminal, and stdout on a pipe. The platform is patched in the child.
"""

import json
import os
import select
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

pty = pytest.importorskip('pty')

REPO_ROOT = Path(__file__).resolve().parents[3]

CHILD = textwrap.dedent(
    '''
    import sys
    from unittest import mock

    import awscli  # noqa: F401
    from awscli.clidriver import create_clidriver

    with (
        mock.patch(
            'botocore.credential_daemon.host.Host.runs_credential_daemon',
            return_value=False,
        ),
        # install has no release there either.
        mock.patch(
            'awscli.customizations.configure.credentialdaemon.'
            'install_supported',
            return_value=False,
        ),
    ):
        rc = create_clidriver().main(sys.argv[1:])
    sys.exit(rc)
    '''
)

CONFIG = '''\
[profile dev]
region = us-west-2

[profile sso]
sso_session = s
sso_account_id = 111111111111
sso_role_name = Admin

[sso-session s]
sso_start_url = https://d-123.awsapps.com/start
sso_region = us-east-1
'''

# A config copied from a Mac or Linux host, where cd uses the credential
# daemon.
LOGIN_DAEMON_CONFIG = (
    CONFIG
    + '''
[profile cd]
region = us-west-2
credential_daemon = login.cd
'''
)


def run_in_terminal(
    home, *args, typed='', socket_variable=False, config=CONFIG
):
    """``(stdout, terminal, exit code)``; ``terminal`` is stderr plus the
    echoed input."""
    aws_dir = home / '.aws'
    aws_dir.mkdir(mode=0o700)
    (aws_dir / 'config').write_text(config)
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': str(home),
        'LANG': 'C.UTF-8',
        'AWS_CONFIG_FILE': str(aws_dir / 'config'),
        'AWS_SHARED_CREDENTIALS_FILE': str(aws_dir / 'credentials'),
        'AWS_EC2_METADATA_DISABLED': 'true',
    }
    if socket_variable:
        # Something is at the path, so on Linux or macOS the daemon would
        # count as installed but stopped.
        stale = home / 'credential-daemon.sock'
        stale.write_text('')
        env['AWS_CREDENTIAL_DAEMON_SOCKET'] = str(stale)
    leader, follower = pty.openpty()
    try:
        proc = subprocess.Popen(
            [sys.executable, '-c', CHILD, *args],
            cwd=REPO_ROOT,
            stdin=follower,
            stderr=follower,
            stdout=subprocess.PIPE,
            env=env,
        )
    finally:
        os.close(follower)
    try:
        if typed:
            os.write(leader, typed.replace('\n', '\r').encode())
        terminal = b''
        # A command that waits for input fails the test instead of hanging.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ready, _, _ = select.select([leader], [], [], 0.2)
            if ready:
                try:
                    data = os.read(leader, 4096)
                except OSError:
                    break
                if not data:
                    break
                terminal += data
            elif proc.poll() is not None:
                break
        else:
            proc.kill()
        stdout = proc.stdout.read().decode()
        rc = proc.wait(timeout=60)
    finally:
        os.close(leader)
        proc.stdout.close()
    return stdout, terminal.decode().replace('\r\n', '\n'), rc


def test_logout_all_says_none_found(tmp_path):
    assert run_in_terminal(tmp_path, 'logout', '--all') == (
        'No cached login session tokens found.\n',
        '',
        0,
    )


def test_logout_all_warns_about_credential_daemon_profiles(tmp_path):
    # Their credentials can't be cleared here, so it's a warning and exit 0,
    # not the "isn't running" error, exit 1, that Linux or macOS gives.
    assert run_in_terminal(
        tmp_path, 'logout', '--all', config=LOGIN_DAEMON_CONFIG
    ) == (
        'No cached login session tokens found.\n',
        "warning: profile 'cd' uses the credential daemon, which isn't "
        "available on this platform; its credentials can't be cleared here.\n",
        0,
    )


def test_logout_of_one_profile_warns_as_today(tmp_path):
    assert run_in_terminal(tmp_path, 'logout', '--profile', 'dev') == (
        '',
        "warning: no login session found for profile 'dev'\n",
        0,
    )


def test_child_patches_the_platform(tmp_path):
    # Guards the tests above: the patch reaches the module the CLI uses.
    probe = (
        'import awscli, botocore.credential_daemon as cd, json, sys;'
        'from unittest import mock;'
        'p = mock.patch.object(cd.Host, "runs_credential_daemon",'
        ' return_value=False); p.start();'
        'print(json.dumps(cd.default_socket_path()))'
    )
    out = subprocess.run(
        [sys.executable, '-c', probe],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        env={'PATH': os.environ.get('PATH', ''), 'HOME': str(tmp_path)},
    ).stdout
    assert json.loads(out) is None


@pytest.mark.parametrize(
    'args, typed, expected_stdout_end, expected_terminal',
    [
        (
            ('logout', '--all'),
            '',
            'No cached login session tokens found.\n',
            '',
        ),
    ],
)
def test_the_socket_variable_is_ignored(
    tmp_path, args, typed, expected_stdout_end, expected_terminal
):
    # As an AWS CLI without credential daemon support, which never read it.
    stdout, terminal, rc = run_in_terminal(
        tmp_path, *args, typed=typed, socket_variable=True
    )
    assert (stdout.endswith(expected_stdout_end), terminal, rc) == (
        True,
        expected_terminal,
        0,
    )
