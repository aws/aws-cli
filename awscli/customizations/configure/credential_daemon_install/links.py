# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The ``~/.aws/credential-daemon.sock`` link: creating, checking and
removing it."""

import errno
import json
import os
import secrets
import stat

from botocore.credential_daemon import (
    HOME_SOCKET_DIR_NAME,
    HOME_SOCKET_FILE_NAME,
    LINK_COMMAND,
    LINK_REMOVE_COMMAND,
    SHOWN_HOME_SOCKET,
    check_home_socket,
    check_socket_folders,
    home_socket_path,
    probe_socket,
)
from botocore.exceptions import CredentialDaemonError

from awscli.botocore.credential_daemon import strip_control_characters
from awscli.customizations.configure.credential_daemon_install.release import (
    CREDENTIAL_DAEMON_PRODUCT,
)
from awscli.customizations.exceptions import ConfigurationError


def link_problem(link, target, uid, check_folder=False):
    """Why the link at ``link`` isn't one to remove, or None.

    'missing': nothing is there. 'elsewhere': a link to something other
    than ``target``. 'not_link': the entry isn't a link, so ``link
    --remove`` would refuse it too. 'unsafe': the entry isn't ``uid``'s,
    or can't be read. With ``check_folder``, for root's own link,
    'unsafe_folder': its folder isn't a folder only ``uid`` can change.
    The link itself is never followed.
    """
    if check_folder:
        try:
            folder = os.stat(os.path.dirname(link))
        except FileNotFoundError:
            return 'missing'
        except OSError:
            return 'unsafe'
        if (
            not stat.S_ISDIR(folder.st_mode)
            or folder.st_uid != uid
            or folder.st_mode & 0o022
        ):
            return 'unsafe_folder'
    try:
        entry = os.lstat(link)
    except FileNotFoundError:
        return 'missing'
    except OSError:
        return 'unsafe'
    if not stat.S_ISLNK(entry.st_mode):
        return 'not_link'
    if entry.st_uid != uid:
        return 'unsafe'
    try:
        if os.readlink(link) != target:
            return 'elsewhere'
    except OSError:
        return 'unsafe'
    return None


def remove_own_link(
    link, target, uid, check_folder=False, remedy=LINK_REMOVE_COMMAND
):
    """Remove ``link`` if it's ``uid``'s link to ``target``, in the caller's
    own process. With ``check_folder`` (root), only from a folder only
    ``uid`` can change. Returns ``(removed, line)``, or None if nothing is
    there. ``remedy`` is the command that removes it later, if any.
    """
    shown = strip_control_characters(link)
    later = f' To remove it, run: {remedy}' if remedy else ''
    problem = link_problem(link, target, uid, check_folder=check_folder)
    if problem == 'missing':
        return None
    if problem == 'elsewhere':
        return left_elsewhere(link)
    if problem == 'not_link':
        return left_not_link(link)
    if problem == 'unsafe_folder':
        return (
            False,
            f'Left {shown}: another user can change its folder, so it '
            f'wasn\'t removed as root.{later}\n',
        )
    if problem is not None:
        return (
            False,
            f'Left {shown}: the CLI couldn\'t check it, so it wasn\'t '
            f'removed.{later}\n',
        )
    try:
        os.unlink(link)
    except FileNotFoundError:
        return None
    except OSError as e:
        return False, f'Left {shown}: {strip_control_characters(str(e))}.\n'
    return True, f'Removed {shown}.\n'


def left_elsewhere(link):
    return (
        False,
        f'Left {strip_control_characters(link)}: it doesn\'t point to '
        f'{CREDENTIAL_DAEMON_PRODUCT}\'s socket.\n',
    )


def left_not_link(link):
    # A file or socket at the path: link --remove would refuse it too.
    return (
        False,
        f'Left {strip_control_characters(link)}: it isn\'t a link to '
        f'{CREDENTIAL_DAEMON_PRODUCT}\'s socket.\n',
    )


def unlink_as_user(path, uid, gid):
    """Unlink ``path`` as ``uid``, in a child process, so root never
    removes anything that user couldn't. Raises OSError if it fails."""
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
            os.unlink(path)
            code = 0
        except BaseException:
            pass
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    if os.waitstatus_to_exitcode(status) != 0:
        raise OSError(errno.EPERM, f'couldn\'t remove {path} as uid {uid}')


def link_as_user(entry, target):
    """Link ``~/.aws/credential-daemon.sock`` in the home of the passwd
    ``entry`` to ``target``, as that user, in a child process that drops to
    their uid, gid and groups before it touches their home, so root never
    creates or follows anything there. The child links as ``link`` does.
    Returns ``(link as shown, what it replaced or None)``. Raises
    ConfigurationError with why if it wasn't linked, or OSError if the
    child failed."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            os.close(read_fd)
            # Not caught below: if it can't run as the user, the child
            # exits 1 before it touches their home.
            if os.geteuid() == 0:
                os.initgroups(entry.pw_name, entry.pw_gid)
                os.setgid(entry.pw_gid)
                os.setuid(entry.pw_uid)
            if entry.pw_uid != os.getuid() or entry.pw_uid != os.geteuid():
                raise OSError(errno.EPERM, 'couldn\'t run as the user')
            try:
                link, replaced = _create_users_link(entry.pw_dir, target)
                result = {'link': link, 'replaced': replaced}
            except (CredentialDaemonError, ConfigurationError, OSError) as e:
                result = {'error': link_error(e)}
            data = json.dumps(result).encode('utf-8')
            while data:
                data = data[os.write(write_fd, data) :]
            code = 0
        except BaseException:
            pass
        finally:
            os._exit(code)
    os.close(write_fd)
    chunks = []
    try:
        with os.fdopen(read_fd, 'rb') as reply:
            chunks.append(reply.read(_LINK_AS_REPLY_BYTES))
    finally:
        _, status = os.waitpid(pid, 0)
    try:
        result = json.loads(b''.join(chunks).decode('utf-8'))
    except ValueError:
        result = None
    if os.waitstatus_to_exitcode(status) != 0 or not isinstance(result, dict):
        raise OSError(errno.EPERM, f'couldn\'t link as uid {entry.pw_uid}')
    if isinstance(result.get('link'), str):
        replaced = result.get('replaced')
        return result['link'], replaced if isinstance(replaced, str) else None
    raise ConfigurationError(str(result.get('error', 'unknown error')))


# The most link_as_user reads back from its child: a path or an error message.
_LINK_AS_REPLY_BYTES = 64 * 1024


def _create_users_link(home, target):
    """Link ``<home>/.aws/credential-daemon.sock`` to ``target`` as ``link``
    does, run as the user (``link_as_user``'s child). Returns ``(link as
    shown, what it replaced or None)``, as ``replaced_entry`` says it.

    The same rule as ``link``, so ``sudo aws configure credential-daemon
    install`` and ``link`` give one result: a missing ~/.aws is created
    with the umask, an existing one isn't checked or changed, and a link
    or socket at the path is replaced. The child already runs as the user,
    so a check on their folder would protect nothing root does.
    """
    environ = {'HOME': home}
    replaced = replaced_entry(environ, target)
    return create_home_link(target, environ, remedy=None), replaced


def create_home_link(
    target, environ=None, check_target=True, remedy=LINK_COMMAND
):
    """Point ``~/.aws/credential-daemon.sock`` at ``target``, the credential
    daemon's own socket, and return the link's path.

    HOME comes from ``environ``. ``~/.aws`` is created with the umask if
    it's missing, as ``aws configure`` creates it, and is never changed. With
    ``check_target``, the target first passes every check a command that
    sends secrets runs (nothing is sent), and the new link passes the
    checks every client runs before it's dialed. Without it (the target
    doesn't answer yet), only the folders on the way to the target are
    checked, and the link is checked when it's used. The link is
    written under a temporary name and renamed over the old one, so the
    path is never missing or half-written. A link or a socket at the path
    is replaced; anything else is refused, with ``remedy``, the command to
    run once it's removed, if any.
    """
    link = home_socket_path(environ)
    if link is None:
        raise ConfigurationError(
            f'HOME isn\'t an absolute path, so there\'s no '
            f'~/{HOME_SOCKET_DIR_NAME} to link in.'
        )
    shown = strip_control_characters(link)
    folder = os.path.dirname(link)
    if not os.path.lexists(folder):
        os.makedirs(folder)
    if os.path.lexists(link):
        mode = os.lstat(link).st_mode
        if not (stat.S_ISLNK(mode) or stat.S_ISSOCK(mode)):
            # Install prints its own remedy, once: who runs link, and how,
            # differs (as the user, or not at all for root's under sudo).
            then = f', then run: {remedy}' if remedy else ' first'
            raise ConfigurationError(
                f'{shown} is there and isn\'t a link or a socket, so it was '
                f'left. Remove it{then}.'
            )
    if check_target:
        probe_socket(target)
    else:
        # The socket and its peer are checked when the link is used; the
        # folders a socket could be replaced in are checked now.
        check_socket_folders(target)
    tmp = os.path.join(
        folder,
        f'.{HOME_SOCKET_FILE_NAME}.{os.getpid()}.{secrets.token_hex(4)}',
    )
    os.symlink(target, tmp)
    try:
        if hasattr(os, 'lchmod'):
            # macOS gives links 0755; the mode means nothing, but 0600
            # doesn't look writable by others.
            try:
                os.lchmod(tmp, 0o600)
            except (OSError, NotImplementedError):
                pass
        os.replace(tmp, link)
    except BaseException:
        os.unlink(tmp)
        raise
    if check_target:
        try:
            check_home_socket(link)
        except BaseException:
            if os.path.islink(link) and os.readlink(link) == target:
                os.unlink(link)
            raise
    return shown


def replaced_entry(environ, target):
    """What linking ``~/.aws/credential-daemon.sock`` to ``target`` would
    replace, as a phrase, or None: a link to another socket, or a socket."""
    link = home_socket_path(environ)
    if link is None:
        return None
    try:
        mode = os.lstat(link).st_mode
        if stat.S_ISSOCK(mode):
            return 'it was a socket'
        previous = os.readlink(link) if stat.S_ISLNK(mode) else None
    except OSError:
        return None
    if previous is None or previous == target:
        return None
    return f'it pointed to {strip_control_characters(previous)}'


def replaced_line(link, replaced):
    """The line saying what the link replaced, or ''."""
    if replaced is None:
        return ''
    return f'Replaced {strip_control_characters(link)} ({replaced}).\n'


def remove_home_link(environ=None):
    """Remove ``~/.aws/credential-daemon.sock`` if it's a link. Returns the
    path removed, or None if nothing was there. Anything else at the path
    is refused."""
    link = home_socket_path(environ)
    if link is None:
        raise ConfigurationError(
            f'HOME isn\'t an absolute path, so there\'s no '
            f'{SHOWN_HOME_SOCKET} to remove.'
        )
    if not os.path.lexists(link):
        return None
    shown = strip_control_characters(link)
    if not os.path.islink(link):
        raise ConfigurationError(f'{shown} isn\'t a link, so it was left.')
    os.unlink(link)
    return shown


def link_error(error):
    # The checks' errors end with a period; an OSError doesn't.
    if isinstance(error, OSError):
        return f'{strip_control_characters(str(error))}.'
    return str(error)


def shown_link(environ):
    path = home_socket_path(environ)
    if path is None:
        return SHOWN_HOME_SOCKET
    return strip_control_characters(path)
