# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the CLI's credential daemon client, run against the fake
credential daemon."""

import contextlib
import errno
import json
import logging
import os
import pickle
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore import credential_daemon
from botocore.credential_daemon import (
    AWS_LOGIN_SOURCE,
    CLI_TAGS,
    CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    LOGOUT_TIMEOUT,
    MAX_MESSAGE_BYTES,
    MAX_REPLY_LINE_BYTES,
    SIGN_IN_TIMEOUT,
    CredentialDaemonClient,
    LogoutResult,
    SocketChecks,
    approval_instructions,
    credential_source,
)
from botocore.credential_daemon.transport import _Connection
from botocore.exceptions import (
    CredentialDaemonApprovalRequiredError,
    CredentialDaemonConnectionError,
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonCredentialUnusableError,
    CredentialDaemonError,
    CredentialDaemonIdentityMismatchError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonProviderUnavailableError,
    CredentialDaemonReauthRequiredError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonTimeoutError,
)

from awscli.testutils import skip_if_windows
from tests import mock
from tests.functional.credential_daemon.login_helpers import socket_checks_pass
from tests.utils.credential_daemon import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_PRINCIPAL,
    DEFAULT_START_URL,
    KIND_IAM_USER,
    KIND_SSO,
    NO_SESSION,
    FakeCredentialDaemon,
)
from tests.utils.credential_daemon.skips import skip_unless_linux

BOB = f'arn:aws:sts::{DEFAULT_ACCOUNT_ID}:assumed-role/ReadOnly/bob'
ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
REGION = 'us-west-2'


@pytest.fixture
def client(fake):
    return CredentialDaemonClient(socket_path=fake.socket_path, timeout=5)


@pytest.fixture
def short_home(monkeypatch):
    # A short HOME with a private ~/.aws, for discovery through
    # ~/.aws/credential-daemon.sock: pytest's tmp_path would pass
    # sun_path's limit.
    monkeypatch.delenv('AWS_CREDENTIAL_DAEMON_SOCKET', raising=False)
    with tempfile.TemporaryDirectory(dir='/tmp', prefix='h') as home:
        (Path(home) / '.aws').mkdir(mode=0o700)
        monkeypatch.setenv('HOME', home)
        yield Path(home)


def aws_login(**provider):
    return dict({'type': 'aws_login', 'region': 'us-west-2'}, **provider)


def eventually(condition, timeout=2):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, 'condition never became true'
        time.sleep(0.01)


def scripted_daemon(path, *replies, hang_up=False, received=None):
    """A daemon that answers each request with the next reply, then hangs
    up. With ``hang_up``, it hangs up right after the last reply, without
    waiting for another request. Each line it reads is added to the
    ``received`` list, if given."""
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(path)
    server.listen(1)

    def run():
        connection, _ = server.accept()
        with connection, connection.makefile('rb') as reader:
            # Read every request before replying or hanging up, so the
            # client sees a clean close rather than a reset.
            line = reader.readline()
            if received is not None:
                received.append(line)
            for i, reply in enumerate(replies):
                connection.sendall(reply)
                if hang_up and i == len(replies) - 1:
                    break
                line = reader.readline()
                if received is not None and line:
                    received.append(line)
        server.close()

    threading.Thread(target=run, daemon=True).start()


LIST = b'{"jsonrpc":"2.0","id":1,"result":{"credentials":[]}}\n'
PROGRESS = (
    b'{"jsonrpc":"2.0","method":"notifications/progress",'
    b'"params":{"step":"waiting"}}\n'
)


def client_frame_locals(error):
    """The locals of the client's frames in ``error``'s traceback."""
    tb = error.__traceback__
    while tb is not None:
        if os.path.dirname(tb.tb_frame.f_code.co_filename) == os.path.dirname(
            credential_daemon.__file__
        ):
            yield from tb.tb_frame.f_locals.values()
        tb = tb.tb_next


def finishes_within(limit, call):
    """Run ``call`` in a thread and return what it raised (or None).

    Fails, rather than hanging the run, if it's still going after
    ``limit`` seconds.
    """
    raised = []

    def run():
        try:
            call()
        except BaseException as e:
            raised.append(e)
        else:
            raised.append(None)

    thread = threading.Thread(target=run, daemon=True)
    start = time.monotonic()
    thread.start()
    thread.join(limit)
    assert not thread.is_alive(), f'the call was still running after {limit}s'
    return raised[0], time.monotonic() - start


_FLOOD = """
import socket, sys
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(sys.argv[1])
server.listen(1)
connection, _ = server.accept()
connection.makefile('rb').readline()
burst = sys.argv[2].encode() * 64
try:
    while True:
        connection.sendall(burst)
except OSError:
    pass
"""


@contextlib.contextmanager
def flooding_daemon(path):
    """A daemon that reads one request, then floods progress
    notifications and never replies. It runs in its own process, so
    there's always a notification waiting, whatever the GIL does."""
    daemon = subprocess.Popen(
        [sys.executable, '-I', '-c', _FLOOD, path, PROGRESS.decode()]
    )
    try:
        eventually(lambda: os.path.exists(path), timeout=10)
        yield
    finally:
        daemon.kill()
        daemon.wait(5)


class TestConnecting:
    def test_list(self, client):
        assert client.list_credentials() == []

    @skip_if_windows('The link is for Linux and macOS.')
    def test_the_link_in_aws_is_dialed(self, fake, short_home):
        # A daemon serves ~/.aws/credential-daemon.sock through a link to
        # its own socket elsewhere (SEP Socket location).
        link = short_home / '.aws' / 'credential-daemon.sock'
        link.symlink_to(fake.socket_path)
        client = CredentialDaemonClient(timeout=5)
        assert client.socket_path == str(link)
        assert client.list_credentials() == []
        assert [method for method, _ in fake.calls] == ['credential/list']

    @skip_if_windows('The link is for Linux and macOS.')
    def test_no_link_dials_nothing(self, short_home):
        client = CredentialDaemonClient(timeout=5)
        with mock.patch.object(socket.socket, 'connect') as connect:
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                client.list_credentials()
        assert 'there\'s no socket at' in str(e.value)
        connect.assert_not_called()

    def test_a_fetch_sends_only_credential_get(self, fake, client):
        # Each fetch is one credential/get on its own connection.
        fake.seed('dev')
        client.get_credentials('dev')
        client.get_credentials('dev')
        assert [method for method, _ in fake.calls] == [
            'credential/get',
            'credential/get',
        ]

    @pytest.mark.parametrize(
        'method,call',
        [
            ('credential/list', lambda c: c.list_credentials()),
            (
                'credential/bootstrap',
                lambda c: c.store_keys('dev', 'AKIDEXAMPLE', 'secret', REGION),
            ),
            (
                'credential/bootstrap',
                lambda c: c.bootstrap(aws_login(), name='dev'),
            ),
            ('credential/logout', lambda c: c.logout('dev')),
        ],
        ids=['list', 'store_keys', 'bootstrap', 'logout'],
    )
    def test_every_call_sends_only_its_request(
        self, fake, client, method, call
    ):
        # The daemon's protocol version doesn't stop a call.
        fake.protocol_version = 2
        if method == 'credential/logout':
            fake.seed('dev')
        call(client)
        assert [m for m, _ in fake.calls] == [method]

    def test_probe_sends_nothing(self, fake, client):
        client.probe()
        assert fake.calls == []
        assert client.list_credentials() == []

    def test_probe_raises_what_a_call_would(self, sock_dir):
        client = CredentialDaemonClient(
            socket_path=str(sock_dir / 'credsd.sock')
        )
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            client.probe()
        with pytest.raises(CredentialDaemonNotRunningError) as call:
            client.list_credentials()
        assert str(e.value) == str(call.value)

    def test_probe_connects_within_the_connect_timeout(self, fake):
        # As a call does, so a full listen queue holds the check only for
        # the connect timeout.
        client = CredentialDaemonClient(socket_path=fake.socket_path)
        with mock.patch.object(
            _Connection, 'open', wraps=_Connection.open
        ) as opened:
            client.probe()
        assert opened.call_args[0][1] == min(CONNECT_TIMEOUT, DEFAULT_TIMEOUT)

    @skip_if_windows('The link is for Linux and macOS.')
    def test_probe_pins_the_socket_it_found(self, fake, short_home):
        link = short_home / '.aws' / 'credential-daemon.sock'
        link.symlink_to(fake.socket_path)
        client = CredentialDaemonClient(pin_socket=True, timeout=5)
        client.probe()
        os.unlink(link)
        # The later call dials the socket the check found.
        assert client.socket_path == str(link)

    def test_not_running(self, sock_dir):
        client = CredentialDaemonClient(
            socket_path=str(sock_dir / 'credsd.sock')
        )
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            client.list_credentials()
        assert 'isn\'t running' in str(e.value)

    @pytest.mark.parametrize(
        'platform,size', [('linux', 108), ('darwin', 104)]
    )
    def test_socket_path_too_long(self, platform, size):
        # A NotRunning error naming the path, not a connection error.
        path = '/' + 'a' * (size - 1)
        with mock.patch('sys.platform', platform):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                CredentialDaemonClient(socket_path=path).list_credentials()
        assert str(e.value) == (
            'The credential daemon isn\'t running: the socket '
            f'path {path} is too long.'
        )

    def test_control_characters_are_stripped_from_the_socket_path(
        self, sock_dir
    ):
        # The path comes from the customer's environment (HOME or
        # AWS_CREDENTIAL_DAEMON_SOCKET).
        path = str(sock_dir / 'credsd\x1b[2K.sock')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert '\x1b' not in str(e.value)
        assert 'credsd[2K.sock' in str(e.value)

    def test_control_characters_are_stripped_from_a_connect_error(
        self, sock_dir
    ):
        # A file in the middle of the path: NotADirectoryError.
        (sock_dir / 'file\x1b[2K').touch()
        path = str(sock_dir / 'file\x1b[2K' / 'credsd.sock')
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert 'can\'t connect to' in str(e.value)
        assert '\x1b' not in str(e.value)

    def test_every_connect_failure_is_not_running(self, sock_dir):
        # Refused, no access, no such file or not a directory: each is
        # NOT_RUNNING, naming the path and the OS error.
        stale = str(sock_dir / 'stale.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(stale)
        server.close()
        (sock_dir / 'file').touch()
        locked = sock_dir / 'locked'
        locked.mkdir()
        cases = [
            (str(sock_dir / 'missing.sock'), 'No such file or directory'),
            (stale, 'Connection refused'),
            (str(sock_dir / 'file' / 'x.sock'), 'Not a directory'),
        ]
        for path, os_error in cases:
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                CredentialDaemonClient(socket_path=path).list_credentials()
            assert str(e.value) == (
                'The credential daemon isn\'t running: can\'t connect to '
                f'{path}: {os_error}.'
            )
        path = str(locked / 'x.sock')
        with mock.patch.object(
            socket.socket,
            'connect',
            side_effect=PermissionError(13, 'Permission denied'),
        ):
            with (
                pytest.raises(CredentialDaemonNotRunningError) as e,
                socket_checks_pass(path),
            ):
                CredentialDaemonClient(socket_path=path).list_credentials()
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{path}: Permission denied.'
        )

    def test_longest_socket_path_is_dialed(self):
        size = 104 if sys.platform == 'darwin' else 108
        path = '/' + 'a' * (size - 2)
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert 'No such file or directory' in str(e.value)

    def test_stale_socket(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(path)
        stale.close()
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert 'isn\'t running' in str(e.value)

    def test_no_credential_daemon_on_this_platform(self):
        client = CredentialDaemonClient()
        with mock.patch(
            'botocore.credential_daemon.client.default_socket_path',
            return_value=None,
        ):
            with pytest.raises(CredentialDaemonConnectionError) as e:
                client.list_credentials()
        assert 'isn\'t available' in str(e.value)

    def test_uses_the_default_socket(self):
        with mock.patch(
            'botocore.credential_daemon.client.default_socket_path',
            return_value='/a.sock',
        ):
            assert CredentialDaemonClient().socket_path == '/a.sock'

    def test_timeout(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.bind(path)
        silent.listen(1)
        try:
            with pytest.raises(CredentialDaemonTimeoutError) as e:
                CredentialDaemonClient(
                    socket_path=path, timeout=0.2
                ).list_credentials()
            assert str(e.value) == (
                f'The credential daemon on {path} didn\'t respond within '
                'the 0.2-second call timeout.'
            )
        finally:
            silent.close()

    def test_a_fetch_times_out(self, sock_dir):
        # The SEP's defaults: 1 second to connect and 5 seconds for the
        # whole call. A timeout counts as NOT_RUNNING.
        client = CredentialDaemonClient(socket_path='/x')
        assert client._connect_timeout == CONNECT_TIMEOUT == 1
        assert client._timeout == DEFAULT_TIMEOUT == 5
        path = str(sock_dir / 'credsd.sock')
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.bind(path)
        silent.listen(1)
        start = time.monotonic()
        try:
            with pytest.raises(CredentialDaemonTimeoutError) as e:
                CredentialDaemonClient(
                    socket_path=path, timeout=0.2
                ).get_credentials('dev')
            assert isinstance(e.value, CredentialDaemonNotRunningError)
            assert '0.2-second call timeout' in str(e.value)
            assert time.monotonic() - start < 1
        finally:
            silent.close()

    def test_a_timeout_closes_the_connection(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        try:
            with pytest.raises(CredentialDaemonTimeoutError):
                CredentialDaemonClient(
                    socket_path=path, timeout=0.2
                ).get_credentials('dev')
            connection, _ = server.accept()
            connection.settimeout(2)
            with connection:
                received = b''
                while True:
                    data = connection.recv(65536)
                    if not data:
                        break
                    received += data
            # The request came, then the CLI hung up.
            assert b'credential/get' in received
        finally:
            server.close()

    def test_sending_times_out(self, sock_dir):
        # A daemon that never reads can't hold a send past the timeout.
        path = str(sock_dir / 'credsd.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        try:
            client = CredentialDaemonClient(socket_path=path, timeout=0.3)
            # In a thread, so a send with no timeout fails the test
            # rather than hanging the run.
            error, elapsed = finishes_within(
                5,
                lambda: client._call(
                    'credential/get',
                    {'credential': 'x' * (MAX_MESSAGE_BYTES - 100)},
                ),
            )
            assert isinstance(error, CredentialDaemonTimeoutError)
            assert '0.3-second call timeout' in str(error)
            assert elapsed < 2
        finally:
            server.close()

    def test_notifications_dont_hold_the_call_past_the_timeout(self, sock_dir):
        # The timeout covers the whole call. A daemon that keeps
        # sending notifications and never replies can't hold it open.
        path = str(sock_dir / 'credsd.sock')
        client = CredentialDaemonClient(socket_path=path, timeout=1)
        with flooding_daemon(path):
            error, elapsed = finishes_within(
                5, lambda: client.get_credentials('dev')
            )
        assert isinstance(error, CredentialDaemonTimeoutError)
        assert elapsed < 1.5, f'took {elapsed:.2f}s with a 1s timeout'

    def test_an_answer_after_the_timeout_doesnt_hold_the_call(self, sock_dir):
        # The customer answers a sign-in step after the deadline while the
        # credential daemon keeps sending notifications. The CLI sends nothing
        # more and gives up, rather than answering each one.
        path = str(sock_dir / 'credsd.sock')
        client = CredentialDaemonClient(socket_path=path, timeout=1)
        answers = []

        def answer(progress):
            answers.append(progress)
            time.sleep(max(0, deadline - time.monotonic()) + 0.05)
            return {'selection': 'x'}

        with flooding_daemon(path):
            deadline = time.monotonic() + 0.3
            error, elapsed = finishes_within(
                5,
                lambda: client._call(
                    'credential/bootstrap',
                    {'name': 'dev'},
                    on_progress=answer,
                    timeout=0.3,
                ),
            )
        assert isinstance(error, CredentialDaemonTimeoutError)
        assert elapsed < 1.5, f'took {elapsed:.2f}s with a 0.3s timeout'
        assert len(answers) == 1

    @skip_if_windows('The link is for Linux and macOS.')
    def test_socket_is_looked_up_on_each_call(self, short_home):
        # Look for the socket on each fetch, never cache it.
        link = short_home / '.aws' / 'credential-daemon.sock'
        client = CredentialDaemonClient(timeout=2)
        with FakeCredentialDaemon() as first, FakeCredentialDaemon() as second:
            first.seed('dev')
            second.seed('dev')
            link.symlink_to(first.socket_path)
            client.get_credentials('dev')
            assert client.socket_path == str(link)
            # The link now points at another daemon: the next call
            # dials it.
            link.unlink()
            link.symlink_to(second.socket_path)
            client.get_credentials('dev')
            assert len(first.calls) == len(second.calls) == 1
            # And when it goes, the next call dials nothing.
            link.unlink()
            with pytest.raises(CredentialDaemonNotRunningError):
                client.get_credentials('dev')
            assert len(first.calls) == len(second.calls) == 1

    @skip_if_windows('The link is for Linux and macOS.')
    def test_a_pinned_socket_stays_put(self, short_home, monkeypatch):
        # A command's calls all go to the socket its first call found,
        # even if AWS_CREDENTIAL_DAEMON_SOCKET changes between them.
        link = short_home / '.aws' / 'credential-daemon.sock'
        with FakeCredentialDaemon() as linked, FakeCredentialDaemon() as other:
            linked.seed('dev')
            link.symlink_to(linked.socket_path)
            client = CredentialDaemonClient(timeout=2, pin_socket=True)
            # Before any call, socket_path is the one the call dials.
            assert client.socket_path == str(link)
            client.list_credentials()
            monkeypatch.setenv(
                'AWS_CREDENTIAL_DAEMON_SOCKET', other.socket_path
            )
            client.logout('dev')
            assert client.socket_path == str(link)
            assert other.calls == []
            assert [m for m, _ in linked.calls] == [
                'credential/list',
                'credential/logout',
            ]

    def test_each_thread_reports_the_socket_it_dialed(
        self, sock_dir, monkeypatch
    ):
        # Unpinned, each call looks the socket up again, and socket_path
        # is the one this thread's last call dialed, even when another
        # thread dialed elsewhere since.
        client = CredentialDaemonClient(timeout=2)
        first_called = threading.Event()
        second_called = threading.Event()
        seen = {}

        def first():
            with pytest.raises(CredentialDaemonNotRunningError):
                client.list_credentials()
            first_called.set()
            second_called.wait(5)
            seen['first'] = client.socket_path

        def second():
            with pytest.raises(CredentialDaemonNotRunningError):
                client.list_credentials()
            seen['second'] = client.socket_path
            second_called.set()

        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', str(sock_dir / 'a'))
        thread = threading.Thread(target=first)
        thread.start()
        assert first_called.wait(5)
        monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', str(sock_dir / 'b'))
        other = threading.Thread(target=second)
        other.start()
        other.join(5)
        thread.join(5)
        assert not thread.is_alive() and not other.is_alive()
        assert seen == {
            'first': str(sock_dir / 'a'),
            'second': str(sock_dir / 'b'),
        }

    def test_threads_racing_on_a_pinned_client_share_one_lookup(
        self, sock_dir, monkeypatch
    ):
        # Two threads make the first calls at once: the first lookup wins,
        # and both threads, and every later call, use it.
        both_looking = threading.Barrier(2)
        paths = iter([str(sock_dir / 'a'), str(sock_dir / 'b')])

        def look_up():
            # Without the lock, both threads get here and take a path each.
            try:
                both_looking.wait(0.5)
            except threading.BrokenBarrierError:
                pass
            return next(paths)

        lookup = mock.Mock(side_effect=look_up)
        monkeypatch.setattr(
            'botocore.credential_daemon.client.default_socket_path', lookup
        )
        client = CredentialDaemonClient(timeout=2, pin_socket=True)
        seen = []

        def call():
            with pytest.raises(CredentialDaemonNotRunningError):
                client.list_credentials()
            seen.append(client.socket_path)

        threads = [threading.Thread(target=call) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
        assert not any(thread.is_alive() for thread in threads)
        assert seen == [str(sock_dir / 'a')] * 2
        assert client.socket_path == str(sock_dir / 'a')
        assert lookup.call_count == 1

    def test_explicit_socket_path_is_kept(self, sock_dir, monkeypatch):
        lookup = mock.Mock(return_value='/elsewhere')
        monkeypatch.setattr(
            'botocore.credential_daemon.client.default_socket_path', lookup
        )
        client = CredentialDaemonClient(socket_path=str(sock_dir / 's'))
        with pytest.raises(CredentialDaemonNotRunningError):
            client.list_credentials()
        assert client.socket_path == str(sock_dir / 's')
        lookup.assert_not_called()

    @skip_unless_linux(
        'Linux returns EAGAIN for a full Unix socket listen queue.'
    )
    def test_a_full_listen_queue_is_not_running_at_once(self, sock_dir):
        # The SEP: a connect that fails because the daemon's listen queue
        # is full (EAGAIN) is NOT_RUNNING at once, not a timeout, and
        # isn't retried.
        path = str(sock_dir / 's')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(0)
        waiting = []
        try:
            # Fill the queue: Linux takes one more connection than the
            # backlog.
            while True:
                waiting.append(socket.socket(socket.AF_UNIX))
                waiting[-1].setblocking(False)
                try:
                    waiting[-1].connect(path)
                except BlockingIOError:
                    break
            client = CredentialDaemonClient(socket_path=path)
            start = time.monotonic()
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                client.get_credentials('dev')
            elapsed = time.monotonic() - start
        finally:
            for sock in waiting:
                sock.close()
            server.close()
        assert not isinstance(e.value, CredentialDaemonTimeoutError)
        assert elapsed < CONNECT_TIMEOUT / 2
        assert path in str(e.value)

    def test_eagain_on_connect_is_not_retried(self, sock_dir):
        path = str(sock_dir / 's')
        eagain = BlockingIOError(
            errno.EAGAIN, 'Resource temporarily unavailable'
        )
        with (
            mock.patch.object(
                socket.socket, 'connect', side_effect=eagain
            ) as connect,
            socket_checks_pass(path),
        ):
            with pytest.raises(CredentialDaemonNotRunningError) as e:
                CredentialDaemonClient(
                    socket_path=path, checks=SocketChecks.PEER
                ).get_credentials('dev')
        assert connect.call_count == 1
        assert not isinstance(e.value, CredentialDaemonTimeoutError)
        assert str(e.value) == (
            'The credential daemon isn\'t running: can\'t connect to '
            f'{path}: Resource temporarily unavailable.'
        )

    def test_connecting_times_out(self, sock_dir):
        path = str(sock_dir / 's')
        with (
            mock.patch.object(
                socket.socket, 'connect', side_effect=socket.timeout
            ),
            socket_checks_pass(path),
        ):
            with pytest.raises(CredentialDaemonTimeoutError) as e:
                CredentialDaemonClient(socket_path=path).list_credentials()
        assert isinstance(e.value, CredentialDaemonNotRunningError)
        assert str(e.value) == (
            f'The credential daemon didn\'t accept the connection on {path} '
            'within the 1-second connect timeout.'
        )

    @pytest.mark.parametrize(
        'kwargs, connect_timeout',
        [
            ({}, 1),
            ({'connect_timeout': 0.25}, 0.25),
            # The connect timeout never outlasts the call timeout.
            ({'timeout': 0.5}, 0.5),
        ],
    )
    def test_connecting_has_its_own_timeout(
        self, sock_dir, kwargs, connect_timeout
    ):
        path = str(sock_dir / 's')
        client = CredentialDaemonClient(
            socket_path=path, checks=SocketChecks.PEER, **kwargs
        )
        with (
            socket_checks_pass(path),
            mock.patch.object(socket.socket, 'settimeout') as settimeout,
            mock.patch.object(
                socket.socket, 'connect', side_effect=socket.timeout
            ),
        ):
            with pytest.raises(CredentialDaemonTimeoutError) as e:
                client.get_credentials('dev')
        settimeout.assert_called_once_with(connect_timeout)
        assert f'{connect_timeout}-second connect timeout' in str(e.value)

    def test_sign_in_keeps_its_own_call_timeout(self):
        # Sign-in waits on the customer, so only connecting gets the
        # short timeout.
        connection = mock.MagicMock()
        connection.__enter__.return_value = connection
        connection.call.return_value = {}
        with mock.patch.object(
            _Connection, 'open', return_value=connection
        ) as open_:
            CredentialDaemonClient(socket_path='/x').bootstrap(
                aws_login(), name='dev'
            )
        open_.assert_called_once_with(
            '/x', CONNECT_TIMEOUT, checks=SocketChecks.FULL
        )
        assert connection.call.call_args.args[4] == SIGN_IN_TIMEOUT == 330

    def test_logout_waits_as_long_as_the_daemon_does(self):
        # The credential daemon may wait 10 seconds for the user's write
        # lock and hold it 60, up to 30 of them on the SSO refresh and
        # Logout calls.
        connection = mock.MagicMock()
        connection.__enter__.return_value = connection
        connection.call.return_value = {'signed_out': True}
        with mock.patch.object(
            _Connection, 'open', return_value=connection
        ) as open_:
            CredentialDaemonClient(socket_path='/x').logout('dev')
        open_.assert_called_once_with(
            '/x', CONNECT_TIMEOUT, checks=SocketChecks.FULL
        )
        assert connection.call.call_args.args[4] == LOGOUT_TIMEOUT == 75

    def test_timeout_covers_the_whole_reply(self, sock_dir):
        # A daemon that sends one byte at a time mustn't hold the call open
        # past the timeout.
        path = str(sock_dir / 'credsd.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        stop = threading.Event()

        def drip():
            connection, _ = server.accept()
            with connection:
                for byte in LIST:
                    if stop.wait(0.05):
                        return
                    connection.sendall(bytes([byte]))

        thread = threading.Thread(target=drip, daemon=True)
        thread.start()
        start = time.monotonic()
        try:
            with pytest.raises(CredentialDaemonConnectionError) as e:
                CredentialDaemonClient(
                    socket_path=path, timeout=0.3
                ).list_credentials()
            assert '0.3-second call timeout' in str(e.value)
            assert time.monotonic() - start < 1
        finally:
            stop.set()
            thread.join()
            server.close()

    @pytest.mark.parametrize(
        'replies',
        [(), (LIST.rstrip(b'\n'),)],
        ids=['no-line', 'partial-line'],
    )
    def test_daemon_hangs_up(self, sock_dir, replies):
        # Closing before a whole line is a protocol error, even when what
        # came is valid JSON.
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, *replies, hang_up=True)
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert str(e.value) == (
            'The credential daemon closed the connection before it sent a '
            'whole line.'
        )

    @pytest.mark.parametrize(
        'reply, message',
        [
            (b'not json\n', 'isn\'t valid JSON'),
            (b'[1]\n', 'isn\'t a JSON object'),
            (b'x' * (MAX_MESSAGE_BYTES + 1), 'over 1,048,576 bytes'),
            (b'{"jsonrpc":"2.0","id":1}\n', 'neither result nor error'),
            (b'{"jsonrpc":"2.0","id":1,"error":"x"}\n', 'can\'t read'),
            (
                b'{"jsonrpc":"2.0","method":"notifications/progress",'
                b'"params":[]}\n',
                'progress message',
            ),
        ],
    )
    def test_unreadable_replies(self, sock_dir, reply, message):
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, reply)
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert message in str(e.value)

    @pytest.mark.parametrize('opener', [b'[', b'{"a":'])
    def test_a_deeply_nested_reply_isnt_valid_json(self, sock_dir, opener):
        # json.loads raises RecursionError, not ValueError, for a line
        # nested too deep, even one within credential/get's line limit.
        reply = opener * (MAX_REPLY_LINE_BYTES // len(opener)) + b'\n'
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, reply)
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(socket_path=path).get_credentials('dev')
        assert str(e.value) == (
            'The credential daemon sent a message that isn\'t valid JSON.'
        )

    @pytest.mark.parametrize(
        'head, tail',
        [(b'', b'x'), (b'[' * 60_000, b'')],
        ids=['extra-data', 'nested'],
    )
    def test_a_reply_that_isnt_json_isnt_kept(
        self, sock_dir, caplog, head, tail
    ):
        # The decode error holds the whole line, here a credential/get
        # reply's secrets. Nothing the raised error reaches keeps it: no
        # __cause__ or __context__, and no local in the client's frames of
        # its traceback.
        caplog.set_level(logging.DEBUG)
        reply = (
            head
            + b'{"jsonrpc":"2.0","id":1,"result":{"material":'
            + b'{"type":"session_credentials","access_key_id":"'
            + ACCESS_KEY.encode()
            + b'","secret_access_key":"'
            + SECRET_KEY.encode()
            + b'"},"expires_at":"2099-01-01T00:00:00Z"}}'
            + tail
            + b'\n'
        )
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, reply)
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(socket_path=path).get_credentials('dev')
        assert 'isn\'t valid JSON' in str(e.value)
        assert e.value.__cause__ is None
        assert e.value.__context__ is None
        assert not any(
            SECRET_KEY.encode() in value
            for value in client_frame_locals(e.value)
            if isinstance(value, (bytes, bytearray))
        )
        # What --debug prints: the debug log and the traceback.
        shown = caplog.text + ''.join(
            traceback.format_exception(
                type(e.value), e.value, e.value.__traceback__
            )
        )
        assert SECRET_KEY not in shown
        assert ACCESS_KEY not in shown

    @pytest.mark.parametrize('reply_id', [b'7', b'null', b'"1"'])
    def test_an_error_reply_with_another_id_is_still_the_error(
        self, sock_dir, reply_id
    ):
        # The SEP: the reply's id isn't compared with the request's, since
        # the reply on a connection is for its one request.
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(
            path,
            b'{"jsonrpc":"2.0","id":' + reply_id + b',"error":{"code":-32000,'
            b'"message":"No credential named x.","data":{"code":'
            b'"CREDENTIAL_NOT_FOUND"}}}\n',
        )
        with pytest.raises(CredentialDaemonCredentialNotFoundError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert e.value.code == 'CREDENTIAL_NOT_FOUND'

    def test_replies_that_arrive_together(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(
            path,
            b'{"jsonrpc":"2.0","method":"notifications/other"}\n'
            + b'{"jsonrpc":"2.0","id":1,"result":{"credentials":[]}}\n',
        )
        client = CredentialDaemonClient(socket_path=path)
        assert client.list_credentials() == []

    def test_other_notifications_are_ignored(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(
            path,
            b'{"jsonrpc":"2.0","method":"notifications/other"}\n' + LIST,
        )
        assert (
            CredentialDaemonClient(socket_path=path).list_credentials() == []
        )


SECRET_REPLY = {
    'credential': 'dev',
    'material': {
        'type': 'session_credentials',
        'access_key_id': 'ASIADAEMON',
        'secret_access_key': 'topsecret',
        'session_token': 'token',
    },
    'expires_at': '2099-01-01T00:00:00Z',
}


def reply_line(size=None, **reply):
    """A credential/get reply line, padded with a ``padding`` field in
    ``result`` so it's ``size`` bytes without the newline."""
    reply = dict({'jsonrpc': '2.0', 'id': 1}, **reply)
    line = json.dumps(reply, separators=(',', ':')).encode()
    if size is not None:
        reply['result'] = dict(reply['result'], padding='')
        line = json.dumps(reply, separators=(',', ':')).encode()
        reply['result']['padding'] = 'x' * (size - len(line))
        line = json.dumps(reply, separators=(',', ':')).encode()
        assert len(line) == size
    return line + b'\n'


class TestReplies:
    # The SEP's rules for a credential/get reply. None of the errors
    # quotes the reply.
    def get(self, sock_dir, *replies, hang_up=False):
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, *replies, hang_up=hang_up)
        return CredentialDaemonClient(socket_path=path).get_credentials('dev')

    def test_a_reply_line_at_the_limit_is_read(self, sock_dir):
        assert MAX_REPLY_LINE_BYTES == 64000
        line = reply_line(MAX_REPLY_LINE_BYTES, result=SECRET_REPLY)
        result = self.get(sock_dir, line)
        assert result['material']['access_key_id'] == 'ASIADAEMON'

    @pytest.mark.parametrize(
        'line',
        [
            reply_line(MAX_REPLY_LINE_BYTES + 1, result=SECRET_REPLY),
            b'x' * (MAX_REPLY_LINE_BYTES + 1),
        ],
        ids=['json', 'no-newline'],
    )
    def test_a_reply_line_over_the_limit_is_a_protocol_error(
        self, sock_dir, line
    ):
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.get(sock_dir, line)
        assert str(e.value) == (
            'The credential daemon sent a line over 64,000 bytes.'
        )

    def test_reading_stops_at_the_limit(self):
        # A daemon that never sends a newline: the CLI reads the limit
        # and one more byte, then gives up.
        class Endless:
            requested = 0

            def settimeout(self, timeout):
                pass

            def sendall(self, data):
                pass

            def recv(self, size):
                self.requested += size
                return b'x' * size

            def close(self):
                pass

        sock = Endless()
        connection = _Connection(sock)
        with pytest.raises(CredentialDaemonProtocolError):
            connection.call(
                'credential/get',
                {'credential': 'dev'},
                None,
                time.monotonic() + 5,
                max_line_bytes=MAX_REPLY_LINE_BYTES,
            )
        assert sock.requested == MAX_REPLY_LINE_BYTES + 1

    def test_other_calls_keep_the_larger_limit(self, sock_dir):
        rows = [{'name': f'c{i}', 'source': 'aws_login'} for i in range(3000)]
        line = reply_line(result={'credentials': rows})
        assert len(line) > MAX_REPLY_LINE_BYTES
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(path, line)
        client = CredentialDaemonClient(socket_path=path)
        assert len(client.list_credentials()) == 3000

    @pytest.mark.parametrize(
        'reply, message',
        [
            (
                {'jsonrpc': '1.0', 'result': SECRET_REPLY},
                'a reply whose jsonrpc isn\'t "2.0"',
            ),
            (
                {'jsonrpc': None, 'result': SECRET_REPLY},
                'a reply whose jsonrpc isn\'t "2.0"',
            ),
            (
                {
                    'result': SECRET_REPLY,
                    'error': {
                        'code': -32000,
                        'message': 'denied',
                        'data': {'code': 'REAUTH_REQUIRED'},
                    },
                },
                'a reply with both result and error',
            ),
            ({}, 'a reply with neither result nor error'),
        ],
        ids=[
            'jsonrpc-1.0',
            'jsonrpc-null',
            'result-and-error',
            'neither',
        ],
    )
    def test_malformed_replies(self, sock_dir, reply, message):
        line = reply_line(**reply)
        if 'jsonrpc' in reply and reply['jsonrpc'] is None:
            line = line.replace(b'"jsonrpc":null,', b'')
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.get(sock_dir, line)
        assert str(e.value) == f'The credential daemon sent {message}.'
        assert 'topsecret' not in str(e.value)
        assert 'denied' not in str(e.value)

    @pytest.mark.parametrize(
        'reply',
        [{'result': None}, {'error': None}, {'result': None, 'error': None}],
        ids=['result-null', 'error-null', 'both-null'],
    )
    def test_a_null_result_or_error_counts_as_absent(self, sock_dir, reply):
        # The SEP: a null result or error counts as absent.
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.get(sock_dir, reply_line(**reply))
        assert str(e.value) == (
            'The credential daemon sent a reply with neither result nor '
            'error.'
        )

    def test_a_null_error_next_to_a_result_is_ignored(self, sock_dir):
        line = reply_line(result=SECRET_REPLY, error=None)
        assert self.get(sock_dir, line) == SECRET_REPLY

    def test_a_null_result_next_to_an_error_is_the_error(self, sock_dir):
        line = reply_line(
            result=None,
            error={
                'code': -32000,
                'message': 'Sign in again.',
                'data': {'code': 'REAUTH_REQUIRED'},
            },
        )
        with pytest.raises(CredentialDaemonReauthRequiredError):
            self.get(sock_dir, line)

    @pytest.mark.parametrize(
        'reply_id',
        ['not-the-request-id', 999, True, None],
        ids=['id-string', 'id-other', 'id-true', 'id-null'],
    )
    def test_the_reply_id_and_credential_arent_checked(
        self, sock_dir, reply_id
    ):
        # The SEP's reply-id-and-name-not-checked: the reply on a connection
        # is for its one request, so neither is compared with the request's.
        result = dict(SECRET_REPLY, credential='other')
        line = reply_line(id=reply_id, result=result)
        assert self.get(sock_dir, line) == result

    def test_a_reply_without_an_id_isnt_a_notification(self, sock_dir):
        line = reply_line(result=SECRET_REPLY).replace(b'"id":1,', b'')
        assert b'"id"' not in line
        assert self.get(sock_dir, line) == SECRET_REPLY

    @pytest.mark.parametrize(
        'kwargs, params',
        [
            ({}, {'credential': 'dev'}),
            (
                {'account_id': '111111111111', 'role_name': 'Admin'},
                {
                    'credential': 'dev',
                    'account_id': '111111111111',
                    'role_name': 'Admin',
                },
            ),
        ],
        ids=['credential', 'sso-role'],
    )
    def test_the_request_has_an_id_and_only_the_seps_params(
        self, sock_dir, kwargs, params
    ):
        # The SEP: the request has an id, and no params beyond its own,
        # since the daemon rejects params it doesn't know.
        path = str(sock_dir / 'credsd.sock')
        received = []
        scripted_daemon(
            path, reply_line(result=SECRET_REPLY), received=received
        )
        CredentialDaemonClient(socket_path=path).get_credentials(
            'dev', **kwargs
        )
        request = json.loads(received[0])
        assert set(request) == {'jsonrpc', 'id', 'method', 'params'}
        assert request['jsonrpc'] == '2.0'
        assert isinstance(request['id'], int)
        assert not isinstance(request['id'], bool)
        assert request['method'] == 'credential/get'
        assert request['params'] == params

    def test_eof_mid_reply_doesnt_quote_it(self, sock_dir):
        line = reply_line(result=SECRET_REPLY).rstrip(b'\n')
        with pytest.raises(CredentialDaemonProtocolError) as e:
            self.get(sock_dir, line, hang_up=True)
        assert 'topsecret' not in str(e.value)
        assert 'closed the connection before' in str(e.value)

    def test_the_reply_credential_isnt_compared(self, sock_dir):
        # The reply on a connection is for its one request.
        line = reply_line(result=dict(SECRET_REPLY, credential='other'))
        assert self.get(sock_dir, line)['credential'] == 'other'


class TestCalls:
    def test_list_credentials(self, fake, client):
        fake.seed('dev')
        [row] = client.list_credentials()
        assert row.name == 'dev'
        assert row.status == 'active'
        # As credsd's rows with credential tags: a source and tags, and no
        # creator.
        assert row.source == AWS_LOGIN_SOURCE
        assert row.tags == {}
        assert 'creator' not in row.raw
        assert dict(fake.calls)['credential/list'] == {}

    def test_list_credentials_by_tag(self, fake, client):
        fake.seed('dev', tags=CLI_TAGS)
        fake.seed('other', tags={'created-by': 'another-tool'})
        fake.seed('untagged')
        rows = client.list_credentials(tags=CLI_TAGS)
        assert [row.name for row in rows] == ['dev']
        assert dict(fake.calls)['credential/list'] == {'tags': CLI_TAGS}

    @pytest.mark.parametrize(
        'row', [{}, {'source': None}, {'source': 1}, None, 'aws_login']
    )
    def test_credential_source_of_a_row_without_one(self, row):
        assert credential_source(row) is None

    @pytest.mark.parametrize(
        'result', [b'{}', b'{"credentials":null}', b'[]', b'"x"']
    )
    def test_unreadable_credential_list(self, sock_dir, result):
        path = str(sock_dir / 'credsd.sock')
        scripted_daemon(
            path,
            b'{"jsonrpc":"2.0","id":1,"result":' + result + b'}\n',
        )
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(socket_path=path).list_credentials()
        assert 'credential list' in str(e.value)

    def test_get_credentials(self, fake, client):
        fake.seed('dev')
        result = client.get_credentials('dev')
        assert dict(fake.calls)['credential/get'] == {'credential': 'dev'}
        assert result['material']['type'] == 'session_credentials'
        assert result['material']['account_id'] == DEFAULT_ACCOUNT_ID
        assert result['expires_at'].endswith('Z')
        # The credential daemon names the credential in credential and adds
        # provenance.
        assert result['credential'] == 'dev'
        assert 'provenance' in result

    def test_get_sso_role_credentials(self, fake, client):
        fake.seed('acme', kind=KIND_SSO, principal=None)
        result = client.get_credentials(
            'acme', account_id='111111111111', role_name='Admin'
        )
        assert dict(fake.calls)['credential/get'] == {
            'credential': 'acme',
            'account_id': '111111111111',
            'role_name': 'Admin',
        }
        assert result['material']['account_id'] == '111111111111'

    def test_store_keys_names_the_cli_as_creator(self, fake, client):
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        params = dict(fake.calls)['credential/bootstrap']
        assert params['credential'] == 'ci'
        assert params['creator'] == 'aws-cli'
        assert 'client' not in params

    def test_store_keys_sends_the_region(self, fake, client):
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, 'eu-west-1')
        params = dict(fake.calls)['credential/bootstrap']
        assert params['provider']['region'] == 'eu-west-1'

    def test_a_test_can_set_another_creator(self, fake):
        client = CredentialDaemonClient(
            socket_path=fake.socket_path, timeout=5, creator='other-tool'
        )
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        client.bootstrap(aws_login(), name='dev')
        creators = [p.get('creator') for _, p in fake.calls]
        assert creators == ['other-tool', 'other-tool']
        material = client.get_credentials('ci')['material']
        assert material['access_key_id'] != ACCESS_KEY

    def test_logout(self, fake, client):
        fake.seed('dev')
        assert client.logout('dev') == LogoutResult(
            signed_out=True, provider='local_only'
        )
        assert dict(fake.calls)['credential/logout'] == {'credential': 'dev'}
        assert fake.credential('dev').status == NO_SESSION
        # Nothing left to sign out.
        assert client.logout('dev') == LogoutResult(
            signed_out=False, provider='none'
        )

    @pytest.mark.parametrize('provider', ['ended', 'token_rejected'])
    def test_sso_logout_says_what_sso_did(self, fake, client, provider):
        fake.seed('acme', kind=KIND_SSO)
        if provider != 'ended':
            fake.set_sso_logout(provider)
        result = client.logout('acme')
        assert result == LogoutResult(signed_out=True, provider=provider)
        assert not result.provider_failed

    def test_failed_sso_logout_says_where_to_sign_out(self, fake, client):
        credential = fake.seed('acme', kind=KIND_SSO)
        fake.set_sso_logout(
            'failed', access_token_expires_at='2026-11-19T18:00:00Z'
        )
        result = client.logout('acme')
        assert result == LogoutResult(
            signed_out=True,
            provider='failed',
            start_url=DEFAULT_START_URL,
            access_token_expires_at='2026-11-19T18:00:00Z',
        )
        assert result.provider_failed
        # Signed out here all the same.
        assert credential.status == NO_SESSION

    def test_failed_sso_logout_without_an_expiry(self, fake, client):
        fake.seed('acme', kind=KIND_SSO)
        fake.set_sso_logout('failed', access_token_expires_at=None)
        result = client.logout('acme')
        assert result.start_url == DEFAULT_START_URL
        assert result.access_token_expires_at is None

    def test_logout_refuses_access_keys(self, fake, client):
        # credsd signs out only sign-in sources.
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        with pytest.raises(CredentialDaemonRequestRejectedError) as e:
            client.logout('ci')
        assert e.value.code == 'LOGOUT_UNSUPPORTED_SOURCE'
        assert credential_daemon.is_logout_unsupported(e.value)
        assert 'no sign-in to log out of' in str(e.value)
        assert fake.credential('ci') is not None

    def test_logout_of_an_unknown_name(self, client):
        with pytest.raises(CredentialDaemonCredentialNotFoundError):
            client.logout('nope')

    def test_remove(self, fake, client):
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        assert client.remove('ci') == {}
        assert dict(fake.calls)['credential/remove'] == {'credential': 'ci'}
        assert fake.credential('ci') is None
        with pytest.raises(CredentialDaemonCredentialNotFoundError):
            client.remove('ci')

    def test_secrets_are_never_logged(self, client, caplog):
        caplog.set_level(logging.DEBUG)
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        material = client.get_credentials('ci')['material']
        assert 'credential/bootstrap' in caplog.text
        for secret in (
            ACCESS_KEY,
            SECRET_KEY,
            material['secret_access_key'],
            material['session_token'],
        ):
            assert secret not in caplog.text


class TestErrors:
    def test_credential_not_found(self, client):
        with pytest.raises(CredentialDaemonCredentialNotFoundError) as e:
            client.get_credentials('nope')
        assert e.value.code == 'CREDENTIAL_NOT_FOUND'

    def test_reauth_required(self, fake, client):
        fake.seed('dev', status=NO_SESSION)
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            client.get_credentials('dev')
        assert e.value.data['remediation']

    def test_provider_unavailable(self, fake, client):
        fake.seed('dev')
        fake.fail_next('credential/get', 'PROVIDER_UNAVAILABLE')
        with pytest.raises(CredentialDaemonProviderUnavailableError):
            client.get_credentials('dev')

    @pytest.mark.parametrize(
        'call',
        [
            lambda client: client.get_credentials('dev'),
            lambda client: client.list_credentials(),
        ],
        ids=['get', 'list'],
    )
    def test_config_that_doesnt_validate_is_unusable(self, fake, client, call):
        fake.seed('dev')
        fake.set_config_invalid('tag key "Bad Key" is not valid')
        with pytest.raises(CredentialDaemonCredentialUnusableError) as e:
            call(client)
        assert e.value.code == 'CONFIG_INVALID'
        assert str(e.value) == (
            'caller configuration does not validate: tag key "Bad Key" is '
            'not valid; fix it, then run: creds revalidate (CONFIG_INVALID)'
        )

    @pytest.mark.parametrize(
        'code', ['CONFIG_DRIFTED', 'INTEGRITY_UNVERIFIABLE', 'CUSTODY_BROKEN']
    )
    def test_unusable_credential(self, fake, client, code):
        fake.seed('dev')
        fake.fail_next('credential/get', code, 'Sealed snapshot changed')
        with pytest.raises(CredentialDaemonCredentialUnusableError) as e:
            client.get_credentials('dev')
        assert e.value.code == code
        assert e.value.daemon_message == 'Sealed snapshot changed'
        assert str(e.value) == f'Sealed snapshot changed ({code})'

    def test_identity_mismatch(self, fake, client):
        # Only the code-to-error mapping: credsd sends IDENTITY_MISMATCH on
        # credential/login, which this release doesn't call, so any call
        # shows it.
        fake.seed('dev')
        fake.fail_next('credential/get', 'IDENTITY_MISMATCH', 'Not them')
        with pytest.raises(CredentialDaemonIdentityMismatchError) as e:
            client.get_credentials('dev')
        assert e.value.code == 'IDENTITY_MISMATCH'
        assert e.value.daemon_message == 'Not them'
        assert str(e.value) == 'Not them (IDENTITY_MISMATCH)'

    def test_approval_required(self, fake, client):
        fake.seed('ci', kind=KIND_IAM_USER)
        fake.need_approval_next('credential/remove', "remove credential 'ci'")
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.remove('ci')
        remediation = e.value.data['remediation']
        assert str(e.value) == (
            f"approval required: remove credential 'ci'. {remediation}"
        )

    def test_store_keys_over_a_name_that_exists_needs_approval(
        self, fake, client
    ):
        fake.seed('ci', kind=KIND_IAM_USER)
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        assert isinstance(e.value.data['challenge'], dict)
        assert fake.calls[-1] == (
            'credential/bootstrap',
            {
                'credential': 'ci',
                'provider': {
                    'type': 'aws_iam_user',
                    'access_key_id': '<redacted>',
                    'secret_access_key': '<redacted>',
                    'region': REGION,
                },
                'creator': 'aws-cli',
            },
        )
        fake.approve()
        assert client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION) == {}
        assert fake.credential('ci').secrets['secret_access_key'] == SECRET_KEY

    def test_remediation_is_stripped_of_control_characters(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'APPROVAL_REQUIRED',
            message='Needs approval.',
            challenge={'id': 'x'},
            remediation='\x1b[2Jsudo creds\trequest approve\x9b x\n',
        )
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.get_credentials('dev')
        assert str(e.value) == (
            'Needs approval. [2Jsudo creds request approve x'
        )

    @pytest.mark.parametrize(
        'remediation',
        [
            # Right-to-left override: would show "x evorppa".
            'sudo creds request approve \u202ex',
            # Isolates U+2066-2069.
            'sudo creds \u2066request\u2069 \u2067approve\u2069 \u2068x',
            # Zero-width space and joiner.
            'sudo cre\u200bds request approve\u200d x',
            # Line and paragraph separators become spaces.
            'sudo creds\u2028request\u2029approve x',
        ],
    )
    def test_remediation_is_stripped_of_format_characters(
        self, fake, client, remediation
    ):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'APPROVAL_REQUIRED',
            message='Needs \u202eapproval.',
            challenge={'id': 'x'},
            remediation=remediation,
        )
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.get_credentials('dev')
        assert str(e.value) == ('Needs approval. sudo creds request approve x')

    def test_other_non_ascii_text_is_kept(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'NEW',
            message='Zugriff verweigert f\u00fcr caf\u00e9',
        )
        with pytest.raises(CredentialDaemonError) as e:
            client.get_credentials('dev')
        assert str(e.value) == 'Zugriff verweigert f\u00fcr caf\u00e9 (NEW)'

    @pytest.mark.parametrize(
        'data',
        [
            {},
            {'challenge': {'id': 'req-1'}},
            {'challenge': {'id': 'req-1'}, 'remediation': ' \x1b\n'},
            {'challenge': {'id': 'req-1'}, 'remediation': 7},
            # The old string challenge isn't read.
            {'challenge': 'approve x'},
        ],
    )
    def test_approval_without_remediation_keeps_the_message(
        self, fake, client, data
    ):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'APPROVAL_REQUIRED',
            message='Needs approval',
            **data,
        )
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.get_credentials('dev')
        assert str(e.value) == 'Needs approval'
        assert approval_instructions(e.value.data) is None

    def test_approval_shows_the_daemons_remediation(self, fake, client):
        # The credential daemon sends the challenge as an object and its own
        # instructions in data.remediation.
        fake.seed('dev', kind=KIND_IAM_USER)
        request_id = fake.need_approval_next(
            'credential/remove', 'remove credential dev'
        )
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.remove('dev')
        remediation = e.value.data['remediation']
        assert request_id in remediation
        assert str(e.value) == (
            f'approval required: remove credential dev. {remediation}'
        )
        assert approval_instructions(e.value.data) == remediation
        assert e.value.data['challenge']['id'] == request_id
        # Nothing was removed.
        assert [row.name for row in client.list_credentials()] == ['dev']

    def test_only_approval_errors_show_a_challenge(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'PROVIDER_UNAVAILABLE',
            challenge={'id': 'req-1'},
            remediation='approve x',
        )
        with pytest.raises(CredentialDaemonProviderUnavailableError) as e:
            client.get_credentials('dev')
        assert 'approve x' not in str(e.value)

    def test_unknown_codes_are_failures(self, fake, client):
        fake.seed('dev')
        fake.fail_next('credential/get', 'SOMETHING_NEW')
        with pytest.raises(CredentialDaemonError) as e:
            client.get_credentials('dev')
        # The SEP's REQUEST_REJECTED, naming the credential daemon's code and
        # message.
        assert type(e.value) is CredentialDaemonRequestRejectedError
        assert e.value.code == 'SOMETHING_NEW'
        assert str(e.value) == 'Injected SOMETHING_NEW (SOMETHING_NEW)'
        assert e.value.daemon_message == 'Injected SOMETHING_NEW'

    @pytest.mark.parametrize('code', [['x'], {'a': 1}, 7])
    def test_a_code_that_isnt_a_string_is_a_protocol_error(
        self, sock_dir, code
    ):
        # A reply the SDK can't read is PROTOCOL_ERROR.
        path = str(sock_dir / 's')
        reply = {
            'jsonrpc': '2.0',
            'id': 1,
            'error': {'code': -32000, 'message': 'm', 'data': {'code': code}},
        }
        scripted_daemon(path, json.dumps(reply).encode() + b'\n')
        with pytest.raises(CredentialDaemonProtocolError) as e:
            CredentialDaemonClient(
                socket_path=path, timeout=5
            ).get_credentials('dev')
        assert 'error code' in str(e.value)

    @pytest.mark.parametrize('message', [{'a': '\x1b[31m'}, ['x'], 5, ''])
    def test_a_message_that_isnt_a_string_isnt_shown(self, sock_dir, message):
        path = str(sock_dir / 's')
        reply = {
            'jsonrpc': '2.0',
            'id': 1,
            'error': {
                'code': -32000,
                'message': message,
                'data': {'code': 'REAUTH_REQUIRED'},
            },
        }
        scripted_daemon(path, json.dumps(reply).encode() + b'\n')
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            CredentialDaemonClient(
                socket_path=path, timeout=5
            ).get_credentials('dev')
        assert str(e.value) == 'The credential daemon returned an error.'
        assert e.value.daemon_message is None

    @pytest.mark.parametrize('code', ['REAUTH_REQUIRED', 'SOMETHING_NEW'])
    def test_an_empty_message_is_no_daemon_message(self, sock_dir, code):
        path = str(sock_dir / 's')
        reply = {
            'jsonrpc': '2.0',
            'id': 1,
            'error': {
                'code': -32000,
                'message': ' \x07\n ',
                'data': {'code': code},
            },
        }
        scripted_daemon(path, json.dumps(reply).encode() + b'\n')
        with pytest.raises(CredentialDaemonError) as e:
            CredentialDaemonClient(
                socket_path=path, timeout=5
            ).get_credentials('dev')
        assert 'The credential daemon returned an error.' in str(e.value)
        assert e.value.daemon_message is None

    def test_a_rejected_request_without_a_message(self, sock_dir):
        path = str(sock_dir / 's')
        reply = {
            'jsonrpc': '2.0',
            'id': 1,
            'error': {'code': -32601, 'message': None},
        }
        scripted_daemon(path, json.dumps(reply).encode() + b'\n')
        with pytest.raises(CredentialDaemonRequestRejectedError) as e:
            CredentialDaemonClient(
                socket_path=path, timeout=5
            ).get_credentials('dev')
        assert str(e.value) == (
            'The credential daemon rejected the request: '
            'The credential daemon returned an error.'
        )
        assert e.value.daemon_message is None

    def test_a_message_is_stripped(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get', 'REAUTH_REQUIRED', message='  Revoked.\n'
        )
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            client.get_credentials('dev')
        assert str(e.value) == 'Revoked.'

    def test_a_timeout_is_not_running(self):
        assert issubclass(
            CredentialDaemonTimeoutError, CredentialDaemonNotRunningError
        )

    def test_error_without_a_code_is_rejected(self, fake, client):
        fake.seed('dev')
        fake.fail_next('credential/get', None, message='No.')
        with pytest.raises(CredentialDaemonRequestRejectedError) as e:
            client.get_credentials('dev')
        assert e.value.code is None
        assert str(e.value) == 'No.'

    def test_known_codes_keep_credential_daemons_message(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get', 'REAUTH_REQUIRED', message='Revoked\x1b[2K.'
        )
        with pytest.raises(CredentialDaemonReauthRequiredError) as e:
            client.get_credentials('dev')
        assert e.value.daemon_message == 'Revoked[2K.'

    def test_approval_daemon_message_has_no_challenge(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get',
            'APPROVAL_REQUIRED',
            message='Needs approval.',
            challenge={'id': '1'},
            remediation='creds approve 1',
        )
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.get_credentials('dev')
        assert e.value.daemon_message == 'Needs approval.'
        assert 'creds approve 1' in str(e.value)

    def test_connection_errors_have_no_daemon_message(self, sock_dir):
        with pytest.raises(CredentialDaemonNotRunningError) as e:
            CredentialDaemonClient(
                socket_path=str(sock_dir / 's')
            ).list_credentials()
        assert e.value.daemon_message is None

    def test_control_characters_are_stripped_from_messages(self, fake, client):
        fake.seed('dev')
        fake.fail_next(
            'credential/get', 'NEW\x1b[2K', message='Bad\x1b[2K\r\x9bnews'
        )
        with pytest.raises(CredentialDaemonError) as e:
            client.get_credentials('dev')
        assert str(e.value) == 'Bad[2K news (NEW[2K)'
        assert e.value.code == 'NEW\x1b[2K'

    def test_line_breaks_and_tabs_in_messages_become_spaces(
        self, fake, client
    ):
        fake.seed('dev')
        fake.fail_next('credential/get', 'NEW', message='one\ntwo\tthree')
        with pytest.raises(CredentialDaemonError) as e:
            client.get_credentials('dev')
        assert str(e.value) == 'one two three (NEW)'

    def test_refused_request_is_rejected(self, client):
        # A JSON-RPC error is an error reply too: REQUEST_REJECTED.
        with pytest.raises(CredentialDaemonRequestRejectedError) as e:
            client.get_credentials('me@corp')
        assert e.value.code == -32602
        assert str(e.value).startswith(
            'The credential daemon rejected the request: '
        )
        assert e.value.daemon_message in str(e.value)

    def test_errors_can_be_pickled(self, client):
        with pytest.raises(CredentialDaemonCredentialNotFoundError) as e:
            client.get_credentials('nope')
        copy = pickle.loads(pickle.dumps(e.value))
        assert type(copy) is CredentialDaemonCredentialNotFoundError
        assert copy.code == 'CREDENTIAL_NOT_FOUND'
        assert str(copy) == str(e.value)


class TestTag:
    def test_set_and_unset_keep_the_other_tags(self, fake, client):
        fake.seed('dev', tags={'team': 'pay', 'stage': 'dev'})
        client.tag('dev', set_tags={'team': 'ops'}, unset=['stage'])
        assert fake.calls[-1] == (
            'credential/tag',
            {'credential': 'dev', 'set': {'team': 'ops'}, 'unset': ['stage']},
        )
        assert fake.credential('dev').tags == {'team': 'ops'}

    def test_sends_only_what_is_given(self, fake, client):
        fake.seed('dev', tags={'team': 'pay'})
        client.tag('dev', unset=['team'])
        assert fake.calls[-1] == (
            'credential/tag',
            {'credential': 'dev', 'unset': ['team']},
        )
        assert fake.credential('dev').tags == {}

    def test_mark_created_by_cli_adds_the_clis_tags(self, fake, client):
        fake.seed('dev', tags={'team': 'x', 'created-by': 'someone'})
        assert client.mark_created_by_cli('dev') is True
        assert fake.calls[-1] == (
            'credential/tag',
            {'credential': 'dev', 'set': CLI_TAGS},
        )
        assert fake.credential('dev').tags == {'team': 'x', **CLI_TAGS}

    def test_a_new_credential_ends_with_only_the_clis_tags(self, fake, client):
        client.bootstrap(aws_login(), name='dev')
        assert client.mark_created_by_cli('dev') is True
        assert fake.credential('dev').tags == CLI_TAGS

    def test_mark_created_by_cli_returns_false_on_an_error(self, fake, client):
        # No such credential: the error isn't raised.
        assert client.mark_created_by_cli('nope') is False

    def test_mark_created_by_cli_returns_false_with_no_daemon(self, sock_dir):
        client = CredentialDaemonClient(
            socket_path=str(sock_dir / 'missing.sock')
        )
        assert client.mark_created_by_cli('dev') is False


class TestBootstrap:
    def test_local_sign_in(self, fake, client):
        seen = []
        result = client.bootstrap(
            aws_login(), name='dev', on_progress=lambda p: seen.append(p)
        )
        assert result['identity']['arn'] == DEFAULT_PRINCIPAL
        assert [p['type'] for p in seen] == ['authorize_url']
        assert fake.credential('dev').kind == 'aws_login'

    def test_sends_a_flat_creator_and_no_version(self, fake, client):
        client.bootstrap(aws_login(), name_prefix='login.')
        params = dict(fake.calls)['credential/bootstrap']
        assert params == {
            'name_prefix': 'login.',
            'provider': aws_login(),
            'creator': 'aws-cli',
        }

    @pytest.mark.parametrize('creator', ['aws-cli', None])
    def test_a_bootstrap_keeps_the_credentials_tags(self, fake, creator):
        # No tags are sent, so a replaced credential keeps the customer's.
        tags = {'team': 'pay', 'created-by': 'someone'}
        fake.seed('dev', tags=tags)
        client = CredentialDaemonClient(
            socket_path=fake.socket_path, creator=creator
        )
        client.bootstrap(aws_login(), name='dev')
        client.store_keys('ci', ACCESS_KEY, SECRET_KEY, REGION)
        bootstraps = [p for m, p in fake.calls if m == 'credential/bootstrap']
        assert len(bootstraps) == 2
        assert all('tags' not in params for params in bootstraps)
        assert fake.credential('dev').tags == tags
        assert fake.credential('ci').tags == {}

    def test_works_without_a_progress_handler(self, fake, client):
        result = client.bootstrap(aws_login(), name='dev')
        assert result['credential'] == 'dev'
        params = dict(fake.calls)['credential/bootstrap']
        assert params['credential'] == 'dev'

    def test_credential_daemon_names_it_from_a_prefix(self, fake, client):
        result = client.bootstrap(aws_login(), name_prefix='login.')
        assert result['credential'] == (
            f'login.{DEFAULT_ACCOUNT_ID}-role-Admin'
        )
        [params] = [p for m, p in fake.calls if m == 'credential/bootstrap']
        assert params['name_prefix'] == 'login.'
        assert 'credential' not in params

    def test_another_identity_needs_approval(self, fake, client):
        # As in credsd: no progress message to answer, and nothing saved.
        client.bootstrap(aws_login(), name='dev')
        fake.next_principal = BOB
        seen = []
        with pytest.raises(CredentialDaemonApprovalRequiredError) as e:
            client.bootstrap(aws_login(), name='dev', on_progress=seen.append)
        assert [p['type'] for p in seen] == ['authorize_url']
        request_id = e.value.data['challenge']['id']
        assert str(e.value).endswith(
            f'sudo creds request approve {request_id}, then re-run the same '
            'bootstrap and sign in as the same account and role again'
        )
        assert fake.credential('dev').principal == DEFAULT_PRINCIPAL

    def test_remote_sign_in(self, client):
        def paste(progress):
            if progress['type'] == 'authorize_code':
                return {'selection': 'abc123'}

        result = client.bootstrap(
            aws_login(remote=True), name='dev', on_progress=paste
        )
        assert result['credential'] == 'dev'

    def test_late_paste_shows_credential_daemons_timeout(self):
        # The credential daemon's AUTH_TIMEOUT arrives while the customer is
        # still pasting. Once the CLI's own deadline passes too, it shows
        # the credential daemon's error, not "didn't respond in time".
        def slow_paste(progress):
            if progress['type'] == 'authorize_code':
                time.sleep(0.6)
                return {'selection': 'abc123'}

        with FakeCredentialDaemon(auth_timeout=0.1) as fake:
            client = CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            )
            with mock.patch(
                'botocore.credential_daemon.client.SIGN_IN_TIMEOUT', 0.3
            ):
                with pytest.raises(CredentialDaemonError) as e:
                    client.bootstrap(
                        aws_login(remote=True),
                        name='dev',
                        on_progress=slow_paste,
                    )
            assert e.value.code == 'AUTH_TIMEOUT'
            assert fake.credential('dev') is None

    def test_multi_role(self, client):
        def pick(progress):
            if progress['type'] == 'select_role':
                return {
                    'roles': [
                        {'account_id': '123456789012', 'role_name': 'Admin'}
                    ]
                }

        result = client.bootstrap(aws_login(multi_role=True), on_progress=pick)
        names = [c['name'] for c in result['credentials']]
        assert names == ['Admin-123456789012']

    def test_answers_carry_only_the_answer(self, sock_dir):
        path = str(sock_dir / 'credsd.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        answers = []

        def run():
            connection, _ = server.accept()
            with connection, connection.makefile('rb') as reader:
                reader.readline()
                connection.sendall(
                    b'{"jsonrpc":"2.0","method":"notifications/progress",'
                    b'"params":{"type":"authorize_code"}}\n'
                )
                answers.append(json.loads(reader.readline()))
                connection.sendall(
                    b'{"jsonrpc":"2.0","id":1,"result":{"credential":"dev"}}\n'
                )
                reader.readline()
            server.close()

        threading.Thread(target=run, daemon=True).start()
        client = CredentialDaemonClient(socket_path=path, timeout=5)
        client.bootstrap(
            aws_login(),
            name='dev',
            on_progress=lambda p: {'selection': 'abc123'},
        )
        assert answers == [
            {
                'jsonrpc': '2.0',
                'method': 'credential/bootstrap/respond',
                'params': {'selection': 'abc123'},
            }
        ]

    def test_raising_in_the_handler_cancels_the_sign_in(self):
        with FakeCredentialDaemon(signin='manual') as fake:
            client = CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            )

            def cancel(progress):
                raise KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                client.bootstrap(aws_login(), name='dev', on_progress=cancel)
            eventually(lambda: fake.waiting_signins() == [])
            assert fake.credential('dev') is None

    def test_daemon_stopping_mid_sign_in(self):
        with FakeCredentialDaemon(signin='manual') as fake:
            client = CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            )
            # The daemon closes the connection before its reply.
            with pytest.raises(CredentialDaemonProtocolError):
                client.bootstrap(
                    aws_login(), name='dev', on_progress=lambda p: fake.stop()
                )
