# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""One connection to the credential daemon: connect, check, send and read."""

import json
import logging
import os
import socket
import time

from botocore.credential_daemon.codesign import (
    check_code_signature,
    checks_code_signature,
)
from botocore.credential_daemon.discovery import (
    HomeSocketPath,
    NoSocketPath,
    _connect_failed_hint,
    _no_socket,
    check_home_socket,
)
from botocore.credential_daemon.host import Host
from botocore.credential_daemon.messages import UNSUPPORTED_PLATFORM_MESSAGE
from botocore.credential_daemon.model import SocketChecks
from botocore.credential_daemon.protocol import _result_from_reply
from botocore.credential_daemon.text import (
    _os_error,
    _seconds,
    strip_control_characters,
)
from botocore.credential_daemon.trust import check_peer, check_socket
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonTimeoutError,
    CredentialDaemonUnsupportedPlatformError,
)

# One logger name for the package, as before the split, so --debug
# output is the same.
logger = logging.getLogger('botocore.credential_daemon')


MAX_MESSAGE_BYTES = 1024 * 1024
# The longest credential/get reply line the SEP allows, not counting the
# newline.
MAX_REPLY_LINE_BYTES = 64000
# The SEP's defaults: the connect timeout covers connecting, and the call
# timeout covers the whole call (connecting, sending and reading).
CONNECT_TIMEOUT = 1
DEFAULT_TIMEOUT = 5


_READ_SIZE = 64 * 1024
# What _Connection._receive decodes a line that isn't JSON to.
_NOT_JSON = object()


def probe_socket(path, timeout=CONNECT_TIMEOUT):
    """Connect to the socket at ``path`` with every check a command that
    sends secrets runs, and close the connection. Nothing is sent.

    Raises what a call would: ``CredentialDaemonNotRunningError`` if
    nothing answers, ``CredentialDaemonUntrustedSocketError`` if a check
    fails.
    """
    _Connection.open(path, timeout, checks=SocketChecks.FULL).close()


class _Connection:
    def __init__(self, sock, shown_path=None):
        self._sock = sock
        # The socket path, control characters removed, for error messages.
        self._shown_path = shown_path
        self._buffer = b''
        self._next_id = 0
        # Whether this call already read what was waiting after its
        # deadline. It does that at most once.
        self._drained = False
        # The current call's timeout, for the error message, and its
        # longest line.
        self._call_timeout = DEFAULT_TIMEOUT
        self._max_line_bytes = MAX_MESSAGE_BYTES

    @classmethod
    def open(cls, path, timeout, checks=SocketChecks.FULL):
        checks = SocketChecks(checks)
        if path is None or not hasattr(socket, 'AF_UNIX'):
            raise CredentialDaemonUnsupportedPlatformError(
                error_msg=UNSUPPORTED_PLATFORM_MESSAGE
            )
        if isinstance(path, NoSocketPath):
            raise _no_socket(path)
        # The path comes from the customer's environment, so it can hold
        # control characters; never send them to the terminal.
        shown = strip_control_characters(path)
        via_home_socket = isinstance(path, HomeSocketPath)
        if via_home_socket:
            check_home_socket(path)
        requested = path
        owner = None
        if len(os.fsencode(path)) < Host.current().sun_path_size():
            # The resolved path is the one checked and dialed, so its
            # length is checked below too.
            path, owner = check_socket(path)
        if len(os.fsencode(path)) >= Host.current().sun_path_size():
            # Not shortened, and no other socket is tried. A short link
            # can point at a long target, which is the path dialed.
            too_long = shown
            if path != requested:
                too_long = (
                    f'{strip_control_characters(path)}, where {shown} '
                    'points,'
                )
            raise CredentialDaemonNotRunningError(
                error_msg=(
                    'The credential daemon isn\'t running: '
                    f'the socket path {too_long} '
                    f'is too long.'
                )
            )
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(path)
        except socket.timeout as e:
            sock.close()
            raise CredentialDaemonTimeoutError(
                error_msg=(
                    'The credential daemon didn\'t accept the '
                    f'connection on {shown} within the '
                    f'{_seconds(timeout)} connect timeout.'
                )
            ) from e
        except OSError as e:
            # Refused, no access, no such file, or a full listen queue
            # (EAGAIN): whatever the reason, the SEP counts a failed
            # connect as the daemon not running, at once. Nothing retries
            # it; only the refresh backoff calls again.
            sock.close()
            raise CredentialDaemonNotRunningError(
                error_msg=(
                    'The credential daemon isn\'t running: can\'t connect '
                    f'to {shown}: {_os_error(e)}.'
                ),
                hint=_connect_failed_hint(requested, via_home_socket),
            ) from e
        # On macOS, FULL checks the code signature at every socket, the
        # system socket too. For example, a source-built daemon installed as
        # a system service (/private/var/run/credsd/credsd.sock) is refused,
        # as an unsigned daemon at a per-user socket is. Why: the signed
        # release doesn't install a system service, and the root-owned
        # folder doesn't prove the peer. launchd reports uid 0 for a socket
        # it makes for a user's own LaunchAgent too, and connecting through
        # the checked folder (connectat) isn't available on macOS. Source-
        # built system installs aren't supported for now. PEER never checks
        # the signature.
        #
        # The peer is checked right after connect, on this connection, not
        # after a system/health reply. While launchd still holds a socket
        # it's handing to the daemon, the peer is launchd and the
        # signature check fails; that refusal is kept (fail closed). Reading
        # the peer after a health reply would need several requests on one
        # connection.
        signature = checks is SocketChecks.FULL and checks_code_signature()
        try:
            check_peer(sock, path, owner, given=requested)
            if signature:
                check_code_signature(sock, path, given=requested)
        except BaseException:
            sock.close()
            raise
        also = ', and its code signature' if signature else ''
        logger.debug(
            'Checked %r: its folders, its owner and the user serving it%s.',
            path,
            also,
        )
        return cls(sock, shown)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        self._sock.close()

    def call(
        self,
        method,
        params,
        on_progress,
        deadline,
        call_timeout=DEFAULT_TIMEOUT,
        max_line_bytes=MAX_MESSAGE_BYTES,
    ):
        self._next_id += 1
        request_id = self._next_id
        request = {'jsonrpc': '2.0', 'id': request_id, 'method': method}
        if params is not None:
            request['params'] = params
        self._drained = False
        self._call_timeout = call_timeout
        self._max_line_bytes = max_line_bytes
        self._send(request, deadline)
        while True:
            message = self._receive(deadline)
            if 'id' not in message and 'method' in message:
                # Past the deadline, only a reply counts: a daemon that
                # keeps sending notifications can't hold the call open.
                if time.monotonic() < deadline:
                    self._handle_notification(message, on_progress, deadline)
                continue
            return _result_from_reply(message)

    def _handle_notification(self, message, on_progress, deadline):
        if message.get('method') != 'notifications/progress':
            return
        progress = message.get('params')
        if not isinstance(progress, dict):
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The credential daemon sent a progress '
                    'message the CLI can\'t read.'
                )
            )
        if on_progress is None:
            return
        answer = on_progress(progress)
        if answer is not None:
            self._send(
                {
                    'jsonrpc': '2.0',
                    'method': 'credential/bootstrap/respond',
                    'params': answer,
                },
                deadline,
            )

    def _send(self, message, deadline):
        data = json.dumps(message, separators=(',', ':')).encode('utf-8')
        if len(data) > MAX_MESSAGE_BYTES:
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The request is too large to send to '
                    'the credential daemon.'
                )
            )
        # Sending waits only for the time left too, so a daemon that
        # stops reading can't hold the call past the deadline.
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            if self._drain_once():
                # The credential daemon answered while the CLI waited on the
                # customer, such as with its own AUTH_TIMEOUT. Send nothing, so
                # the next read shows that answer.
                return
            raise self._call_timed_out()
        self._sock.settimeout(remaining)
        try:
            self._sock.sendall(data + b'\n')
        except socket.timeout as e:
            raise self._call_timed_out() from e
        except OSError as e:
            raise CredentialDaemonConnectionError(
                error_msg=(
                    'Lost the connection to the credential daemon: '
                    f'{_os_error(e)}'
                )
            ) from e

    def _call_timed_out(self):
        where = f' on {self._shown_path}' if self._shown_path else ''
        return CredentialDaemonTimeoutError(
            error_msg=(
                f'The credential daemon{where} didn\'t respond within the '
                f'{_seconds(self._call_timeout)} call timeout.'
            )
        )

    def _receive(self, deadline):
        line = self._read_line(deadline)
        try:
            message = json.loads(line)
        except (ValueError, RecursionError):
            # A deeply nested line raises RecursionError. The decode error
            # holds the whole line, which can carry secrets, so the protocol
            # error is raised after this block: it has no __cause__ or
            # __context__ that reaches the line.
            message = _NOT_JSON
        del line
        if message is _NOT_JSON:
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The credential daemon sent a message '
                    'that isn\'t valid JSON.'
                )
            )
        if not isinstance(message, dict):
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The credential daemon sent a message '
                    'that isn\'t a JSON object.'
                )
            )
        return message

    def _read_line(self, deadline):
        # Each read waits only for the time left, so a daemon that sends a
        # byte at a time can't keep the call open past the deadline.
        limit = self._max_line_bytes
        while True:
            end = self._buffer.find(b'\n', 0, limit + 1)
            if end != -1:
                line = self._buffer[: end + 1]
                self._buffer = self._buffer[end + 1 :]
                return line
            if len(self._buffer) > limit:
                raise CredentialDaemonProtocolError(
                    error_msg=(
                        'The credential daemon sent a line over '
                        f'{limit:,} bytes.'
                    )
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # The credential daemon may have answered while the CLI waited
                # on the customer, such as with its own AUTH_TIMEOUT. Show that
                # rather than saying the credential daemon didn't respond.
                # Only once, so a daemon that keeps sending can't hold the call
                # open.
                if self._drain_once():
                    continue
                raise self._call_timed_out()
            self._sock.settimeout(remaining)
            try:
                # Never reads past the limit, so a daemon that sends no
                # newline can't make the CLI buffer without end.
                data = self._sock.recv(self._read_size())
            except socket.timeout as e:
                raise self._call_timed_out() from e
            except OSError as e:
                raise CredentialDaemonConnectionError(
                    error_msg=(
                        'Lost the connection to the credential daemon: '
                        f'{_os_error(e)}'
                    )
                ) from e
            if not data:
                raise CredentialDaemonProtocolError(
                    error_msg=(
                        'The credential daemon closed the connection before '
                        'it sent a whole line.'
                    )
                )
            self._buffer += data

    def _read_size(self):
        return max(
            1, min(_READ_SIZE, self._max_line_bytes + 1 - len(self._buffer))
        )

    def _drain_once(self):
        # After the deadline, reads what the credential daemon already sent,
        # once.
        if self._drained:
            return False
        self._drained = True
        return self._read_waiting()

    def _read_waiting(self):
        # Reads what the credential daemon already sent, without waiting.
        self._sock.settimeout(0)
        try:
            data = self._sock.recv(self._read_size())
        except OSError:
            return False
        self._buffer += data
        return bool(data)
