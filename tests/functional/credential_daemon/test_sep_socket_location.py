# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The SEP's Socket location test cases, run against the CLI's credential
provider.

``socket-location-cases.json`` holds the SEP's cases that set up where the
socket is (``$HOME/.aws/credential-daemon.sock``,
``AWS_CREDENTIAL_DAEMON_SOCKET`` and ``HOME``), copied unchanged from
the SEP's ``credential-daemon-provider-test-cases.json``. The SEP's
other cases are covered by ``test_provider.py``.

Each case gets its own short temporary root (sun_path is short): ``HOME``,
the link's targets, and an ``env`` socket. Every socket is a scripted
daemon that records whether it was dialed and answers the case's one
exchange.
"""

import contextlib
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

import botocore.credential_daemon
from botocore.configloader import load_config
from botocore.credentials import CredentialDaemonProvider
from botocore.exceptions import CredentialDaemonError

from awscli.testutils import skip_if_windows
from tests import mock

CASES = json.loads(
    (Path(__file__).parent / 'socket-location-cases.json').read_text()
)
ERROR_CODES = {
    'NOT_RUNNING': botocore.exceptions.CredentialDaemonNotRunningError,
}
PLATFORMS = {'linux': 'linux', 'macos': 'darwin'}


class ScriptedDaemon:
    """Listens on ``path``, notes each connection, and answers one request
    with the case's reply lines."""

    def __init__(self, path, exchanges=()):
        self.path = str(path)
        self.dialed = threading.Event()
        self.requests = []
        self._exchanges = list(exchanges)
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.path)
        self._server.listen(4)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while True:
            try:
                connection, _ = self._server.accept()
            except OSError:
                return
            self.dialed.set()
            with connection, connection.makefile('rb') as reader:
                line = reader.readline()
                if not line:
                    continue
                request = json.loads(line)
                self.requests.append(request)
                if not self._exchanges:
                    continue
                exchange = self._exchanges.pop(0)
                for reply in exchange['replyLines']:
                    if isinstance(reply, dict):
                        if reply.get('id') == '$id':
                            reply = dict(reply, id=request['id'])
                        reply = json.dumps(reply)
                    connection.sendall(reply.encode('utf-8') + b'\n')

    def was_dialed(self):
        # A connect lands in the backlog before accept() runs, so wait a
        # little for the thread, and look at the backlog too.
        if self.dialed.wait(0.2):
            return True
        self._server.setblocking(False)
        try:
            self._server.accept()[0].close()
        except (BlockingIOError, OSError):
            return False
        return True

    def close(self):
        try:
            self._server.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._server.close()
        self._thread.join(5)


def stale_socket(path):
    # A socket file nothing listens on.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(path))
    sock.close()


class Case:
    def __init__(self, case, root, monkeypatch):
        self.case = case
        self.root = root
        self.daemons = {}
        self._monkeypatch = monkeypatch
        try:
            self._set_up()
        except BaseException:
            # Close the daemons already started.
            self.close()
            raise

    def _set_up(self):
        case = self.case
        root = self.root
        monkeypatch = self._monkeypatch
        daemon = case['daemon']
        exchanges = daemon.get('exchanges', [])
        environment = case.get('environment', {})
        unset = case.get('unsetEnvironment', [])
        home = root / 'home'
        cwd = root / 'cwd'
        cwd.mkdir(mode=0o700)
        monkeypatch.chdir(cwd)
        if 'HOME' in unset:
            monkeypatch.delenv('HOME', raising=False)
            # The link would be here if HOME counted.
            home = cwd
        elif environment.get('HOME') == 'relative':
            monkeypatch.setenv('HOME', 'relative')
            home = cwd / 'relative'
        else:
            monkeypatch.setenv('HOME', str(home))
        home.mkdir(exist_ok=True)
        self.aws = home / '.aws'
        self.aws.mkdir(mode=0o700)
        self.link = self.aws / 'credential-daemon.sock'
        if 'HOME' in unset or environment.get('HOME') == 'relative':
            # Under the cwd too, for a lookup that resolves against it.
            (cwd / '.aws').mkdir(mode=0o700, exist_ok=True)
        targets = root / 'daemon'
        targets.mkdir(mode=0o700)
        env_dir = root / 'env'
        env_dir.mkdir(mode=0o700)
        env_path = env_dir / 'env.sock'
        sockets = daemon['sockets']
        for name in sockets:
            if name == 'link':
                target = targets / 'link.sock'
                self._listen('link', target, exchanges)
                self.link.symlink_to(target)
                if 'HOME' in unset or environment.get('HOME') == 'relative':
                    other = cwd / '.aws' / 'credential-daemon.sock'
                    if not os.path.lexists(other):
                        other.symlink_to(target)
            elif name == 'link-stale':
                target = targets / 'stale.sock'
                stale_socket(target)
                self.link.symlink_to(target)
            elif name == 'link-dangling':
                self.link.symlink_to(root / 'gone' / 'missing-daemon.sock')
            elif name == 'home-socket':
                self._listen('home-socket', self.link, exchanges)
            elif name == 'env':
                if (
                    environment.get('AWS_CREDENTIAL_DAEMON_SOCKET')
                    == 'relative'
                ):
                    # Created at the relative path under the cwd, below.
                    continue
                self._listen('env', env_path, exchanges)
            elif name == 'env-stale':
                stale_socket(env_path)
            elif name == 'env-file':
                env_path.touch()
            else:
                raise AssertionError(f'unknown socket {name}')
        monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
        for key, value in environment.items():
            if key == 'HOME':
                continue
            if key == 'AWS_CREDENTIAL_DAEMON_SOCKET':
                if value == 'env':
                    value = str(env_path)
                elif value == 'relative':
                    # The env socket at that path under the cwd.
                    relative = Path('env.sock')
                    self._listen('env', cwd / relative, exchanges)
                    value = str(relative)
            monkeypatch.setenv(key, value)

    def _listen(self, role, path, exchanges):
        self.daemons[role] = ScriptedDaemon(path, exchanges)

    def close(self):
        for daemon in self.daemons.values():
            daemon.close()


@pytest.fixture
def short_root():
    # sun_path is 104 bytes on macOS and 108 on Linux; pytest's tmp_path
    # can pass it.
    with tempfile.TemporaryDirectory(dir='/tmp', prefix='sl') as root:
        os.chmod(root, 0o700)
        yield Path(os.path.realpath(root))


def load(case, root):
    config = root / 'config'
    config.write_text(case['configContents'])
    profiles = load_config(str(config))
    provider = CredentialDaemonProvider(
        load_config=lambda: profiles, profile_name=case['profile']
    )
    platform = PLATFORMS[case['platform']]
    emulated = not sys.platform.startswith(platform)
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch('sys.platform', platform))
        if emulated:
            # The emulated platform can't read this one's peer uid; the
            # scripted daemon runs in this process, as the caller.
            stack.enter_context(
                mock.patch(
                    'botocore.credential_daemon.trust._peer_uid',
                    return_value=os.geteuid(),
                )
            )
        return provider.load()


@skip_if_windows('The credential daemon socket is for Linux and macOS.')
@pytest.mark.parametrize('case', CASES, ids=[c['id'] for c in CASES])
def test_socket_location_case(case, short_root, monkeypatch):
    setup = Case(case, short_root, monkeypatch)
    outcome = case['outcome']
    try:
        if outcome['result'] == 'credentials':
            credentials = load(case, short_root)
            # Read without a refresh: the case's expiry is before today.
            assert credentials._access_key == outcome['accessKeyId']
            assert credentials._secret_key == outcome['secretAccessKey']
            assert credentials._token == outcome['sessionToken']
            assert (
                credentials._expiry_time.isoformat().replace('+00:00', 'Z')
                == (outcome['expiresAt'])
            )
            expected = case['daemon']['exchanges'][0]['expectedRequest']
            requests = setup.daemons[outcome['dialed']].requests
            assert [(r['method'], r.get('params')) for r in requests[:1]] == [
                (expected['method'], expected.get('params'))
            ]
        else:
            with pytest.raises(CredentialDaemonError) as e:
                load(case, short_root)
            assert isinstance(e.value, ERROR_CODES[outcome['errorCode']])
            for text in outcome.get('messageContains', []):
                assert text in str(e.value)
        dialed = sorted(
            role
            for role, daemon in setup.daemons.items()
            if daemon.was_dialed()
        )
        if outcome['dialed'] == 'none':
            assert dialed == []
        elif outcome['dialed'] in setup.daemons:
            # Only that socket: no other location is tried.
            assert dialed == [outcome['dialed']]
        else:
            # A stale or missing target: nothing else was dialed.
            assert dialed == []
    finally:
        setup.close()


def test_the_cases_are_the_seps_socket_location_cases():
    # The ids the SEP's Socket location section lists, so a case dropped
    # from this copy shows up.
    assert [c['id'] for c in CASES] == [
        'success-basic',
        'not-running',
        'linux-env-socket-wins',
        'env-socket-not-listening',
        'env-socket-regular-file',
        'env-socket-relative',
        'env-socket-empty',
        'no-link',
        'no-link-home-unset',
        'no-link-home-relative',
        'link-dangling',
        'link-is-a-socket',
    ]
