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
import os
import time

from awscli.compat import is_windows

DEFAULT_TIMEOUT = 10
_RETRY_INTERVAL = 0.05

if is_windows:
    import msvcrt

    def _try_lock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _lock(f, timeout, path):
    # Poll a non-blocking lock so a stuck holder can't block us forever.
    deadline = time.monotonic() + timeout
    while True:
        try:
            _try_lock(f)
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f'timed out after {timeout} seconds waiting for {path}'
                )
        time.sleep(_RETRY_INTERVAL)


@contextlib.contextmanager
def file_lock(path, timeout=None):
    """Hold an exclusive lock on ``path``, creating it if needed.

    The lock isn't reentrant: taking it again in the same process, even
    from the same thread, waits for ``timeout`` and raises.

    :param timeout: Seconds to wait. Defaults to ``DEFAULT_TIMEOUT``.
    :raises TimeoutError: if the lock isn't acquired in time.
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'r+') as f:
        _lock(f, timeout, path)
        try:
            yield
        finally:
            _unlock(f)
