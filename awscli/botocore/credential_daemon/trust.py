# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Checks on who put the credential daemon's socket there, and which user
set it up, before anything is sent."""

import os
import socket
import stat
import struct
import sys

from botocore.credential_daemon.discovery import (
    LINUX_OWN_SOCKET_PATH,
    MACOS_OWN_SOCKET_PATH,
    _not_running,
    _untrusted,
)
from botocore.credential_daemon.host import Host
from botocore.credential_daemon.text import _os_error, strip_control_characters

# A user namespace shows every uid it doesn't map, the caller's own
# included, as this one (the overflow uid). It never counts as the
# caller, root or the socket's owner, so an unmapped socket can't pass for
# the caller's own.
OVERFLOW_UID = 65534
_OVERFLOW_EUID_REASON = (
    f'the CLI is running as uid {OVERFLOW_UID}, which a user namespace also '
    'shows for users it doesn\'t map, so it can\'t tell who owns the socket'
)
# macOS: SOL_LOCAL and LOCAL_PEERCRED from <sys/un.h>, and the size of
# struct xucred (cr_version, cr_uid, cr_ngroups, cr_groups[16]).
_SOL_LOCAL = 0
_LOCAL_PEERCRED = 1
_XUCRED_SIZE = 76
# The struct xucred cr_version this layout is for (XUCRED_VERSION in
# <sys/ucred.h>).
_XUCRED_VERSION = 0


def shown_socket(given, resolved):
    """The socket path for a message: the path as given, then the resolved
    path in parentheses when a link makes it differ, both with control
    characters removed.

    For example, ``/tmp/d.sock`` on macOS, where /tmp links to
    /private/tmp, shows as ``/tmp/d.sock (/private/tmp/d.sock)``. Why: the
    customer recognizes the path they set, and the resolved one says which
    socket was checked. Folders in a message stay resolved, since that's
    where a ``chmod`` goes.
    """
    shown = strip_control_characters(given)
    if resolved == given:
        return shown
    return f'{shown} ({strip_control_characters(resolved)})'


def system_socket_paths(platform=None):
    """The AWS credential daemon's resolved system socket paths, trusted by
    where they are.

    init (systemd or launchd) binds them as root. On macOS /var/run
    resolves to /private/var/run. Only that folder is resolved there, not
    the credsd folder in it: /private/var/run is writable by the daemon
    group, so a link put in place of the credsd folder never makes another
    path the system socket. Discovery never looks at them; a link at
    ``~/.aws/credential-daemon.sock`` can point at one.
    """
    if platform is None:
        platform = sys.platform
    if platform == 'darwin':
        folder, name = os.path.split(MACOS_OWN_SOCKET_PATH)
        run, credsd = os.path.split(folder)
        return frozenset((os.path.join(os.path.realpath(run), credsd, name),))
    if platform.startswith('linux'):
        return frozenset((os.path.realpath(LINUX_OWN_SOCKET_PATH),))
    return frozenset()


def check_socket(path):
    """Check who can have put the socket at ``path`` there, before dialing.

    Returns the resolved path, which is the one to dial, and the socket
    file's owner. Raises ``CredentialDaemonUntrustedSocketError`` if
    another user could own or replace the socket or the CLI can't check a
    folder on the way, and ``CredentialDaemonNotRunningError`` if no
    socket is there, as a failed connect would.

    1. Every symbolic link in the path is resolved.
    2. At a system location (``system_socket_paths``), the socket's own
       folder must be a folder, not a link or a file, and not be writable
       by group or others. On Linux it must be owned by root or the
       socket's owner. On macOS the folder and the socket must both be
       owned by root: /private/var/run is writable by the daemon group,
       so another owner could have put them there. ``check_peer`` then
       requires root to serve it.
    3. Anywhere else, without following links, every folder from ``/``
       down must be a folder, not a link or a file, be owned by root or
       the caller's effective uid and not be writable by group or others
       unless it's sticky, and the socket must be owned by root or the
       caller.

    A caller running as the overflow uid (65534) always fails: in a user
    namespace that doesn't map it, every unmapped owner looks like the
    caller.
    """
    shown = strip_control_characters(path)
    # No socket is NOT_RUNNING whoever runs the CLI, so a machine without
    # the credential daemon gets the not-running error, not a trust error.
    try:
        canon = os.path.realpath(path)
        sock_st = os.lstat(canon)
    except (OSError, ValueError) as e:
        reason = _os_error(e) if isinstance(e, OSError) else str(e)
        raise _not_running(shown, reason) from e
    shown = shown_socket(path, canon)
    if not stat.S_ISSOCK(sock_st.st_mode):
        raise _not_running(shown, 'it isn\'t a socket')
    if not (sys.platform.startswith('linux') or sys.platform == 'darwin'):
        raise _untrusted(shown, 'the CLI can\'t check it on this platform')
    euid = Host.current().effective_uid()
    if euid == OVERFLOW_UID:
        raise _untrusted(shown, _OVERFLOW_EUID_REASON)
    owner = sock_st.st_uid
    if canon in system_socket_paths():
        if owner == OVERFLOW_UID:
            raise _untrusted(
                shown,
                f'the socket is owned by uid {OVERFLOW_UID}, which a user '
                'namespace also shows for users it doesn\'t map',
            )
        root_only = _system_socket_root_only()
        if root_only and owner != 0:
            raise _untrusted(
                shown, f'the socket is owned by uid {owner}, not by root'
            )
        folder = os.path.dirname(canon)
        folder_st = _lstat_folder(shown, folder)
        allowed = (0,) if root_only else (0, owner)
        if folder_st.st_uid == OVERFLOW_UID or folder_st.st_uid not in allowed:
            by = 'root' if root_only else 'root or the socket\'s owner'
            raise _untrusted(
                shown,
                f'its folder {strip_control_characters(folder)} is owned '
                f'by uid {folder_st.st_uid}, not by {by}',
            )
        if folder_st.st_mode & 0o022:
            raise _untrusted(
                shown,
                f'its folder {strip_control_characters(folder)} is '
                'writable by other users (mode '
                f'{stat.S_IMODE(folder_st.st_mode):04o}). Run \'chmod go-w '
                f'{strip_control_characters(folder)}\' as root',
            )
        return canon, owner
    _check_folders(shown, os.path.dirname(canon), euid)
    if owner not in (0, euid):
        raise _untrusted(
            shown,
            f'the socket is owned by uid {owner}, not by you or root',
        )
    return canon, owner


def _system_socket_root_only():
    # On macOS /private/var/run is writable by the daemon group, so only
    # root (launchd creates both) may own the system socket and its
    # folder. On Linux /run is root's alone, and systemd gives the folder
    # and socket to the daemon's account.
    return sys.platform == 'darwin'


def check_socket_folders(path):
    """Check the folders on the way to the socket at ``path``, as
    ``check_socket`` step 3 does, for a socket that isn't there yet or
    doesn't answer: the socket file and the peer aren't checked.

    Every symbolic link in the path is resolved. Then, without following
    links, every folder from ``/`` down that's there must be a folder, not
    a link or a file, be owned by root or the caller's effective uid and
    not be writable by group or others unless it's sticky. The walk stops
    at the first folder that isn't there yet, such as the folder of a
    daemon that hasn't started: a client checks the rest when it uses the
    socket. Raises ``CredentialDaemonUntrustedSocketError`` if a folder
    fails.
    """
    shown = strip_control_characters(path)
    if not (sys.platform.startswith('linux') or sys.platform == 'darwin'):
        raise _untrusted(shown, 'the CLI can\'t check it on this platform')
    euid = Host.current().effective_uid()
    if euid == OVERFLOW_UID:
        raise _untrusted(shown, _OVERFLOW_EUID_REASON)
    try:
        canon = os.path.realpath(path)
    except (OSError, ValueError) as e:
        reason = _os_error(e) if isinstance(e, OSError) else str(e)
        raise _not_running(shown, reason) from e
    shown = shown_socket(path, canon)
    _check_folders(shown, os.path.dirname(canon), euid, missing_ok=True)


def _check_folders(shown, canon_dir, euid, missing_ok=False):
    # Every folder from / down to the resolved canon_dir, not following
    # links (check_socket step 3). With missing_ok, the walk stops at the
    # first folder that isn't there.
    folder = '/'
    for name in [''] + [part for part in canon_dir.split('/') if part]:
        folder = os.path.join(folder, name)
        if missing_ok and not os.path.lexists(folder):
            return
        _check_folder(shown, folder, _lstat_folder(shown, folder), euid)


def _lstat_folder(shown, folder):
    # A folder that's gone means no socket, as for the socket itself; one
    # the CLI can't stat (no search permission on its parent), or that
    # isn't a folder, can't be checked, so it isn't trusted.
    try:
        st = os.lstat(folder)
    except (FileNotFoundError, NotADirectoryError) as e:
        raise _not_running(shown, _os_error(e)) from e
    except OSError as e:
        raise _untrusted(
            shown,
            f'the CLI can\'t check the folder '
            f'{strip_control_characters(folder)}: {_os_error(e)}',
        ) from e
    # The path was resolved first, so a link here is one realpath left
    # (a link to itself) or one swapped in after it, e.g. ~/.aws replaced
    # by a link to /tmp/x between realpath and lstat. A link's owner and
    # mode say nothing about where it leads; a file in place of a folder
    # means the path isn't what it was checked as. Neither is trusted.
    if not stat.S_ISDIR(st.st_mode):
        raise _untrusted(
            shown, f'{strip_control_characters(folder)} isn\'t a folder'
        )
    return st


def _check_folder(shown, folder, st, euid):
    folder_shown = strip_control_characters(folder)
    if st.st_uid not in (0, euid):
        raise _untrusted(
            shown,
            f'the folder {folder_shown} is owned by uid {st.st_uid}, not by '
            'you or root',
        )
    if st.st_mode & 0o022 and not st.st_mode & stat.S_ISVTX:
        # The fix ends the message. go-w, not g-w: the check refuses a
        # folder others can write to as well, e.g. mode 0777. The folder is
        # the resolved one, where the chmod goes. A folder root owns, such
        # as a 0777 bind mount, only root can change, so the hint says so.
        as_root = ' as root' if st.st_uid == 0 and euid != 0 else ''
        raise _untrusted(
            shown,
            f'the folder {folder_shown} is writable by other users (mode '
            f'{stat.S_IMODE(st.st_mode):04o}). Run \'chmod go-w '
            f'{folder_shown}\'{as_root}, or move the socket to a folder only '
            'you can write to',
        )


def check_peer(sock, path, owner, given=None):
    """Check which user set up the connected socket ``sock``.

    The peer credentials name the process that bound the socket and
    called ``listen()``, not always the one that answers. Under the
    systemd system manager or launchd that's init, which reports uid 0,
    and launchd does even for a socket it makes for a user's own
    LaunchAgent. So the check shows who
    set up the socket, not which program serves it; on macOS the code
    signature check does that.

    It must be the caller's effective uid, root, or ``owner``, the socket
    file's owner from ``check_socket``; never the overflow uid. At the
    macOS system socket (``path`` is the resolved path ``check_socket``
    returns) it must be root. Checked on the connection that will carry
    the request. ``given`` is the path before links were resolved, for the
    message (see ``shown_socket``). Raises
    ``CredentialDaemonUntrustedSocketError``.
    """
    shown = shown_socket(path if given is None else given, path)
    try:
        uid = _peer_uid(sock)
    except (OSError, ValueError, struct.error) as e:
        reason = _os_error(e) if isinstance(e, OSError) else str(e)
        raise _untrusted(
            shown, f'the CLI couldn\'t read which user serves it: {reason}'
        ) from e
    # check_socket's root-only rule (the macOS system socket), applied to
    # the peer. /private/var/run is writable by the daemon group, so
    # between check_socket and connect a process in that group can swap
    # the folder: e.g. the daemon user (uid 1) renames
    # /private/var/run/credsd away, makes its own credsd folder there and
    # binds credsd.sock in it. The path checks passed on the old folder;
    # the new socket's peer is uid 1. launchd makes the real socket, and
    # its peer is always uid 0 (idle, after a restart, with many clients),
    # so only root passes here, not the caller or the socket's owner.
    # uid 0 doesn't prove it's the system daemon, though: launchd also
    # reports uid 0 for a socket it makes for a user's own LaunchAgent.
    # For calls that send secrets or start sign-ins, the code signature
    # check does that.
    if _system_socket_root_only() and path in system_socket_paths():
        if uid != 0:
            raise _untrusted(
                shown, f'the process serving it runs as uid {uid}, not as root'
            )
        return
    allowed = {Host.current().effective_uid(), 0, owner} - {OVERFLOW_UID}
    if uid not in allowed:
        raise _untrusted(
            shown,
            f'the process serving it runs as uid {uid}, not as you, root or '
            'the socket\'s owner',
        )


def _peer_uid(sock):
    """The uid of the process on the other end of the connected ``sock``."""
    if sys.platform.startswith('linux'):
        # struct ucred: pid_t, then uid_t and gid_t, which are unsigned.
        raw = sock.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('iII')
        )
        _pid, uid, _gid = struct.unpack('iII', raw)
        return uid
    if sys.platform == 'darwin':
        raw = sock.getsockopt(_SOL_LOCAL, _LOCAL_PEERCRED, _XUCRED_SIZE)
        version, uid = struct.unpack_from('=II', raw)
        # Another layout could put something else where cr_uid is.
        if version != _XUCRED_VERSION:
            raise ValueError(f'unknown xucred version {version}')
        return uid
    raise OSError('no peer credentials on this platform')
