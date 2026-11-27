# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Where the credential daemon's socket is."""

import logging
import os

from botocore.credential_daemon.config import DAEMON_SOCKET_ENV_VAR
from botocore.credential_daemon.host import Host
from botocore.credential_daemon.messages import (
    LINK_REMOVE_COMMAND,
    NO_SOCKET_HINT,
    START_HINT,
)
from botocore.credential_daemon.text import _os_error, strip_control_characters
from botocore.exceptions import (
    CredentialDaemonNotRunningError,
    CredentialDaemonUntrustedSocketError,
)

# One logger name for the package, as before the split, so --debug
# output is the same.
logger = logging.getLogger('botocore.credential_daemon')


# The one socket path the SDKs look at after the variable (SEP, Socket
# location): ~/.aws/credential-daemon.sock, usually a link to the daemon's own
# socket. `aws configure credential-daemon install`
# creates the link, and `aws configure credential-daemon link` creates it
# otherwise.
HOME_SOCKET_DIR_NAME = '.aws'
HOME_SOCKET_FILE_NAME = 'credential-daemon.sock'
# How messages show the path, with ~ and /. It's never opened.
SHOWN_HOME_SOCKET = f'~/{HOME_SOCKET_DIR_NAME}/{HOME_SOCKET_FILE_NAME}'


# The AWS credential daemon's own socket paths: its system socket on Linux
# and on macOS, and on macOS also its per-user socket, where its signed
# package installs per user. The link points at one of them; discovery
# never looks at them.
OWN_SOCKET_DIR_NAME = 'credsd'
OWN_SOCKET_FILE_NAME = 'credsd.sock'
LINUX_OWN_SOCKET_PATH = os.path.join(
    '/run', OWN_SOCKET_DIR_NAME, OWN_SOCKET_FILE_NAME
)
MACOS_OWN_SOCKET_PATH = os.path.join(
    '/var/run', OWN_SOCKET_DIR_NAME, OWN_SOCKET_FILE_NAME
)
# The per-user data folder on macOS, relative to HOME.
MACOS_USER_DATA_SUBPATH = os.path.join('Library', 'Application Support')


class HomeSocketPath(str):
    """``~/.aws/credential-daemon.sock`` as found by discovery (location 2).

    It's checked before it's dialed (``check_home_socket``), which a path
    from ``AWS_CREDENTIAL_DAEMON_SOCKET`` or a caller isn't.
    """


class NoSocketPath(str):
    """What discovery returns when no location applies. It's never dialed:
    a connect fails at once as not running, and says how to set the
    credential daemon up.

    Its value is the ``~/.aws/credential-daemon.sock`` path that wasn't
    there, or the empty string if ``HOME`` isn't an absolute path.
    """


def socket_override(environ=None):
    """The socket path ``AWS_CREDENTIAL_DAEMON_SOCKET`` names, or None if
    it's unset or empty. The one place that variable is read. It stays
    environment-only, not a session config variable: for example, nothing in
    ``~/.aws/config`` can point a program at another socket. Whether the
    path is absolute is for the caller: discovery ignores a relative one, and
    callers that explain why can say so.
    """
    return Host.current(environ).environ.get(DAEMON_SOCKET_ENV_VAR) or None


def default_socket_path(environ=None, platform=None):
    """Return the socket to dial, or None where the credential daemon doesn't
    run.

    The order matches the SDKs (SEP, Socket location), and nothing else is
    looked at:

    1. ``AWS_CREDENTIAL_DAEMON_SOCKET``, if it's an absolute path. An empty
       or relative value counts as unset.
    2. ``HOME/.aws/credential-daemon.sock``, if anything is there: a socket,
       a link, or a link whose target is missing. It's returned as a
       ``HomeSocketPath``, which the connection checks before dialing.
    3. Nothing: a ``NoSocketPath``, which fails as not running without a
       dial.

    ``HOME`` comes from ``environ``, never from the passwd entry, and an
    unset, empty or relative ``HOME`` skips step 2. If the dial fails, the
    caller doesn't try another location. Callers look the socket up on
    each fetch; nothing here caches it.
    """
    host = Host.current(environ, platform)
    environ = host.environ
    override = socket_override(environ)
    if override:
        # For example, AWS_CREDENTIAL_DAEMON_SOCKET=credsd.sock is ignored
        # as if unset, but =/run/x.sock with nothing there fails as not
        # running. A relative path would depend on the current folder, and
        # falling back after a set path fails would send names to a socket
        # the user didn't point at.
        if os.path.isabs(override):
            logger.debug(
                'Using the credential daemon socket from %s: %r',
                DAEMON_SOCKET_ENV_VAR,
                override,
            )
            return override
        logger.debug(
            'Ignored %s=%r: it isn\'t an absolute path, so it counts as '
            'unset.',
            DAEMON_SOCKET_ENV_VAR,
            override,
        )
    if not host.runs_credential_daemon():
        return None
    path = home_socket_path(environ)
    if path is None:
        logger.debug(
            'Skipped %s: HOME=%r isn\'t an absolute path.',
            SHOWN_HOME_SOCKET,
            environ.get('HOME'),
        )
        return NoSocketPath('')
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        logger.debug('Nothing is at %r, so no socket applies.', path)
        return NoSocketPath(path)
    except OSError:
        # Something may be there that the CLI can't see, such as in a
        # ~/.aws it can't search: the connection's check reports it.
        pass
    logger.debug('Using %r -> %r', path, os.path.realpath(path))
    return HomeSocketPath(path)


def home_socket_path(environ=None):
    """``HOME/.aws/credential-daemon.sock``, or None if ``HOME`` isn't an
    absolute path."""
    home = Host.current(environ).home
    if home is None:
        return None
    return os.path.join(home, HOME_SOCKET_DIR_NAME, HOME_SOCKET_FILE_NAME)


def own_socket_path(environ=None, platform=None):
    """The AWS credential daemon's own socket, which the link points at.

    Its per-user socket on macOS, under ``HOME`` (None if ``HOME`` isn't
    an absolute path), and its system socket on Linux. None where it
    doesn't run.
    """
    host = Host.current(environ, platform)
    if host.platform == 'darwin':
        home = host.home
        if home is None:
            return None
        return os.path.join(
            home,
            MACOS_USER_DATA_SUBPATH,
            OWN_SOCKET_DIR_NAME,
            OWN_SOCKET_FILE_NAME,
        )
    if host.platform.startswith('linux'):
        return LINUX_OWN_SOCKET_PATH
    return None


def _too_long(path, platform):
    """``(size, limit)`` when ``path`` is too long to dial, else None."""
    size = len(os.fsencode(path))
    limit = Host.current(platform=platform).sun_path_size()
    if size >= limit:
        return size, limit
    return None


def socket_discovery_notes(environ=None, platform=None):
    """Why socket discovery passed over a location the customer may have
    meant, one line each, for a CLI command to show.

    ``~/.aws/credential-daemon.sock`` skipped because HOME isn't absolute,
    or with a path too long to dial, and an ``AWS_CREDENTIAL_DAEMON_SOCKET``
    that isn't absolute. Nothing at ``~/.aws/credential-daemon.sock`` gets
    no note: the error then says what to do. This changes nothing about
    discovery: ``default_socket_path`` logs the same at debug, and the
    credential provider shows nothing.
    """
    host = Host.current(environ, platform)
    environ = host.environ
    notes = []
    override = socket_override(environ)
    if override:
        if os.path.isabs(override):
            return notes
        notes.append(
            f'{DAEMON_SOCKET_ENV_VAR} isn\'t an absolute path, so it was '
            f'ignored: {strip_control_characters(override)}'
        )
    if not host.runs_credential_daemon():
        return notes
    path = home_socket_path(environ)
    if path is None:
        notes.append(
            f'HOME isn\'t an absolute path, so {SHOWN_HOME_SOCKET} was '
            'skipped.'
        )
        return notes
    too_long = _too_long(path, host.platform)
    if too_long is not None:
        size, limit = too_long
        notes.append(
            f'The credential daemon socket path is {size} bytes, over the '
            f'limit of {limit - 1}, so it can\'t be dialed: '
            f'{strip_control_characters(path)}'
        )
    return notes


def check_home_socket(path):
    """Check ``~/.aws/credential-daemon.sock`` before it's dialed
    (SEP, Socket location).

    Raises ``CredentialDaemonNotRunningError`` if nothing is there any more,
    or if it's a link whose target is missing; that error names the link
    and its target. A link to a socket that's there passes, and the dial
    then shows whether anything listens on it.
    """
    shown = strip_control_characters(path)
    try:
        os.lstat(path)
    except OSError as e:
        raise _not_running(shown, _os_error(e)) from e
    if os.path.islink(path):
        # A link whose target is gone is "not running". For example, with
        # ~/.aws/credential-daemon.sock pointing to /run/credsd/credsd.sock
        # and no daemon installed, commands say the link points to a socket
        # that isn't there. The later checks would also say not running,
        # but name only the missing target, not the link the customer set
        # up and can fix.
        try:
            os.stat(path)
        except (FileNotFoundError, NotADirectoryError) as e:
            raise _dangling_link(path) from e
        except OSError:
            # The dial reports it, such as a folder on the way the CLI
            # can't search.
            pass


def _dangling_link(path):
    try:
        target = os.readlink(path)
    except OSError:
        target = '?'
    return CredentialDaemonNotRunningError(
        error_msg=(
            'The credential daemon isn\'t running: '
            f'{strip_control_characters(path)} points to '
            f'{strip_control_characters(target)}, which isn\'t there. '
            f'{_uninstalled_link_hint()}'
        ),
        hint='',
    )


def _no_socket(path):
    # No location applies, so nothing is dialed (NoSocketPath).
    if path:
        where = f'there\'s no socket at {strip_control_characters(path)}'
    else:
        where = (
            f'HOME isn\'t an absolute path, so there\'s no '
            f'{SHOWN_HOME_SOCKET} to connect to'
        )
    return CredentialDaemonNotRunningError(
        error_msg=(
            f'The credential daemon isn\'t running: {where}. '
            f'{NO_SOCKET_HINT}'
        ),
        hint='',
    )


def _connect_failed_hint(path, via_home_socket):
    # A link to a socket nothing listens on: on macOS the per-user socket
    # file stays after an uninstall, so the link may be all that's left.
    if via_home_socket and os.path.islink(path):
        return _uninstalled_link_hint()
    return None


def _uninstalled_link_hint():
    # For a link whose daemon is gone or stopped.
    return (
        f'{START_HINT} If you uninstalled it, remove the link with '
        f"'{LINK_REMOVE_COMMAND}'."
    )


def _untrusted(shown, reason):
    return CredentialDaemonUntrustedSocketError(
        error_msg=(
            f'The CLI didn\'t trust the credential daemon socket {shown}, so '
            f'it sent nothing to it: {reason}.'
        )
    )


def _not_running(shown, reason):
    return CredentialDaemonNotRunningError(
        error_msg=(
            'The credential daemon isn\'t running: can\'t connect to '
            f'{shown}: {reason}.'
        )
    )
