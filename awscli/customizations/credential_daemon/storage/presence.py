# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Whether the credential daemon runs here, and why it can't be used."""

import logging
import os
import socket
from enum import Enum

from botocore.credential_daemon import HomeSocketPath, default_socket_path
from botocore.exceptions import (
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonTimeoutError,
    CredentialDaemonUntrustedSocketError,
)

# One logger name for the package, as before the split, so --debug
# output is the same.
LOG = logging.getLogger('awscli.customizations.credential_daemon.storage')


def unavailable_error(client):
    """None if the credential daemon answers a credential/list on
    ``client``, else the error."""
    try:
        client.list_credentials()
    except CredentialDaemonError as e:
        LOG.debug('The credential daemon isn\'t available: %s', e)
        return e
    return None


class Presence(Enum):
    """Whether a credential daemon is here (``detect_presence``)."""

    RUNNING = 'running'
    # Something is at the socket but didn't answer, or failed: a stopped,
    # hung or broken credential daemon.
    STOPPED = 'stopped'
    # Nothing is at the socket (``credential_daemon_absent``).
    ABSENT = 'absent'
    # It doesn't run on this platform, such as Windows.
    UNSUPPORTED_PLATFORM = 'unsupported-platform'
    # The CLI didn't trust what's at the socket, and sent nothing.
    UNTRUSTED = 'untrusted'

    @property
    def absent(self):
        """Whether this machine has no credential daemon to use."""
        return self in (Presence.ABSENT, Presence.UNSUPPORTED_PLATFORM)


def detect_presence(error, socket_path):
    """The ``Presence`` that what's already known shows: ``error`` is what
    the last call to the credential daemon at ``socket_path`` raised, or
    None if it answered. Nothing is sent; only the socket path is looked
    at."""
    if not credential_daemon_runs_here():
        return Presence.UNSUPPORTED_PLATFORM
    if error is None:
        return Presence.RUNNING
    if isinstance(error, CredentialDaemonUntrustedSocketError):
        return Presence.UNTRUSTED
    if not isinstance(error, CredentialDaemonNotRunningError) or isinstance(
        error, CredentialDaemonTimeoutError
    ):
        return Presence.STOPPED
    if socket_path_present(socket_path):
        return Presence.STOPPED
    return Presence.ABSENT


def credential_daemon_absent(error, socket_path):
    """Whether ``error`` means this machine has no credential daemon:
    nothing answered and the socket path isn't there at all, or it's
    ``~/.aws/credential-daemon.sock`` and links to nothing.

    A link to nothing is what's left for other users after an uninstall,
    or in a container that mounts ``~/.aws`` but not the socket. Any other
    failure means something is at the socket: a timeout means something
    is listening, and a refused connection on a socket that's still there
    is a credential daemon that's stopped.

    No socket path at all, or a platform the credential daemon doesn't run
    on, means it's absent too, even with AWS_CREDENTIAL_DAEMON_SOCKET set.
    """
    return detect_presence(error, socket_path).absent


def socket_path_present(socket_path):
    """Whether anything is at ``socket_path``.

    ``~/.aws/credential-daemon.sock`` counts only if its target is there.
    A target the CLI can't reach, such as one in a folder it can't search,
    counts: something is there that the CLI can't use.
    """
    if not socket_path:
        return False
    # The home link is followed, so a link to nothing counts as no
    # daemon. Counting it would make every move back on such a machine
    # report the old copy as not cleared, and logout --all warn on every
    # run, for a daemon that isn't there. Any other path counts if
    # anything is there, a link to nothing too.
    check = os.stat if isinstance(socket_path, HomeSocketPath) else os.lstat
    try:
        check(socket_path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return True
    return True


def credential_daemon_runs_here():
    """Whether the credential daemon runs on this platform (macOS or Linux,
    with Unix sockets). Where it doesn't, such as Windows, commands behave
    as an AWS CLI without credential daemon support, whatever
    AWS_CREDENTIAL_DAEMON_SOCKET says, and a profile that uses it is
    refused."""
    return hasattr(socket, 'AF_UNIX') and (
        default_socket_path(environ={}) is not None
    )
