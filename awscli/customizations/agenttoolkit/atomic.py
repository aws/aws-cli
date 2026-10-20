# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import contextlib
import ctypes
import errno
import functools
import logging
import os
import re
import secrets
import shutil
import tempfile
import time

from awscli.compat import is_macos, is_windows

LOG = logging.getLogger(__name__)

_STAGING = 'staging'
_BACKUP = 'backup'
_TRASH = 'trash'
_LEFTOVER_RE = re.compile(
    r'^\.(?P<name>.+)\.aws-cli-(?P<kind>staging|backup|trash)-[0-9a-f]{16}$'
)

# Windows can't rename or replace a path while it, or a file in it, is open
# (agent, editor, antivirus, an unlocked reader), which is usually brief.
_WINDOWS_RETRY_TIMEOUT = 1
_WINDOWS_RETRY_INTERVAL = 0.05

# errno values meaning the atomic exchange isn't available here, so the
# two-rename fallback should be used instead.
_EXCHANGE_UNSUPPORTED = {
    errno.EINVAL,
    errno.ENOSYS,
    errno.ENOTSUP,
    errno.EOPNOTSUPP,
}

_AT_FDCWD = -100
_RENAME_EXCHANGE = 2  # Linux
_RENAME_SWAP = 0x2  # macOS


@functools.cache
def _load_exchange():
    if is_windows:
        return None
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except OSError:
        return None
    if is_macos:
        func = getattr(libc, 'renamex_np', None)
        if func is None:
            return None
        func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        func.restype = ctypes.c_int
        return lambda a, b: func(a, b, _RENAME_SWAP)
    func = getattr(libc, 'renameat2', None)
    if func is None:
        return None
    func.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    func.restype = ctypes.c_int
    return lambda a, b: func(_AT_FDCWD, a, _AT_FDCWD, b, _RENAME_EXCHANGE)


def _exchange(a, b):
    """Atomically swap two paths.

    :returns: ``False`` if the OS or filesystem doesn't support it.
    """
    exchange = _load_exchange()
    if exchange is None:
        return False
    if exchange(os.fsencode(a), os.fsencode(b)) == 0:
        return True
    err = ctypes.get_errno()
    if err in _EXCHANGE_UNSUPPORTED:
        return False
    raise OSError(err, os.strerror(err), a, None, b)


def _call_with_windows_retry(func, *args):
    """Call ``func``, retrying briefly on ``PermissionError`` on Windows."""
    deadline = time.monotonic() + _WINDOWS_RETRY_TIMEOUT
    while True:
        try:
            return func(*args)
        except PermissionError:
            if not is_windows or time.monotonic() >= deadline:
                raise
        time.sleep(_WINDOWS_RETRY_INTERVAL)


def _rename(src, dst):
    _call_with_windows_retry(os.rename, src, dst)


def write_file_atomic(path, content, prefix):
    """Replace ``path`` with ``content`` without ever leaving it partial.

    The temporary file is created as ``<prefix>*.tmp`` next to ``path``
    with owner-only permissions, and removed if anything fails.
    """
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(path), prefix=prefix, suffix='.tmp'
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        _call_with_windows_retry(os.replace, tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise


def _remove_tree(path):
    # Best effort. Anything left behind is removed by the next recover().
    shutil.rmtree(path, ignore_errors=True)


def _sibling(live_dir, kind):
    parent, name = os.path.split(live_dir)
    return os.path.join(
        parent, f'.{name}.aws-cli-{kind}-{secrets.token_hex(8)}'
    )


def make_staging_dir(live_dir):
    """Create an empty staging directory next to ``live_dir``."""
    path = _sibling(live_dir, _STAGING)
    os.mkdir(path)
    return path


def swap_into_place(staging_dir, live_dir):
    """Make ``staging_dir`` the new ``live_dir`` and delete the old one.

    ``staging_dir`` must be a sibling of ``live_dir`` (see
    :func:`make_staging_dir`). If this raises, ``live_dir`` still holds its
    previous contents, or is restored by the next :func:`recover`.
    """
    if not os.path.lexists(live_dir):
        _rename(staging_dir, live_dir)
        return
    if _exchange(staging_dir, live_dir):
        # staging_dir now holds the previous version.
        _remove_tree(staging_dir)
        return
    backup_dir = _sibling(live_dir, _BACKUP)
    _rename(live_dir, backup_dir)
    try:
        _rename(staging_dir, live_dir)
    except BaseException:
        try:
            _rename(backup_dir, live_dir)
        except OSError as e:
            LOG.debug(
                'Could not restore %s from %s: %s', live_dir, backup_dir, e
            )
        raise
    _remove_tree(backup_dir)


def remove_dir(live_dir):
    """Delete ``live_dir`` so an interruption never leaves part of it."""
    trash_dir = _sibling(live_dir, _TRASH)
    _rename(live_dir, trash_dir)
    _remove_tree(trash_dir)


def _find_leftovers(parent):
    """Return ``{name: (to_delete, backup_dirs)}`` found in ``parent``."""
    try:
        entries = os.listdir(parent)
    except (FileNotFoundError, NotADirectoryError):
        return {}
    leftovers = {}
    for entry in entries:
        match = _LEFTOVER_RE.match(entry)
        if not match:
            continue
        path = os.path.join(parent, entry)
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        to_delete, backups = leftovers.setdefault(
            match.group('name'), ([], [])
        )
        if match.group('kind') == _BACKUP:
            backups.append(path)
        else:
            to_delete.append(path)
    return leftovers


def recover(live_dir):
    """Clean up after an interrupted :func:`swap_into_place` of ``live_dir``.

    If ``live_dir`` is missing and a backup exists, the backup is restored.
    All other staging, backup and trash directories for it are deleted.
    """
    parent, name = os.path.split(live_dir)
    to_delete, backups = _find_leftovers(parent).get(name, ([], []))
    _recover(live_dir, to_delete, backups)


def recover_all(parent):
    """:func:`recover` every skill directory with leftovers in ``parent``."""
    for name, (to_delete, backups) in _find_leftovers(parent).items():
        _recover(os.path.join(parent, name), to_delete, backups)


def _recover(live_dir, to_delete, backups):
    # Swaps run one at a time after recovery, so there is at most one backup.
    if backups and not os.path.lexists(live_dir):
        _rename(backups.pop(), live_dir)
    for path in backups + to_delete:
        _remove_tree(path)
