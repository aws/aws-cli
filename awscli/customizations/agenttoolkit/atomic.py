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
import tempfile
import time

from awscli.compat import is_windows

# Windows can't rename or replace a path while it, or a file in it, is open
# (agent, editor, antivirus, an unlocked reader), which is usually brief.
_WINDOWS_RETRY_TIMEOUT = 1
_WINDOWS_RETRY_INTERVAL = 0.05


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
