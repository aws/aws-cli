# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What this machine is: its platform, environment and user."""

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from botocore.exceptions import CredentialDaemonUnsupportedPlatformError


@dataclass(frozen=True)
class Host:
    """The platform and environment the credential daemon checks see.

    Made with ``Host.current()`` each time a check runs, never at import,
    so a caller's ``environ`` or ``platform`` is used where it passes one.
    """

    platform: str
    environ: Mapping

    @classmethod
    def current(cls, environ=None, platform=None):
        return cls(
            sys.platform if platform is None else platform,
            os.environ if environ is None else environ,
        )

    def runs_credential_daemon(self):
        return self.platform == 'darwin' or self.platform.startswith('linux')

    @property
    def home(self):
        # HOME comes from the environment, as the daemon reads it, not from
        # the passwd entry (which expanduser falls back to). An
        # unset, empty ("" + "/x" is absolute) or relative HOME skips
        # ~/.aws/credential-daemon.sock, so the path never resolves against /
        # or the cwd.
        home = self.environ.get('HOME')
        if home and os.path.isabs(home):
            return home
        return None

    def sun_path_size(self):
        # sun_path's size, including the terminating NUL.
        if self.platform == 'darwin' or 'bsd' in self.platform:
            return 104
        return 108

    def effective_uid(self):
        """The caller's effective uid. Raises the unsupported-platform
        ``CredentialDaemonConnectionError`` if there's none to get, so the
        daemon checks never pass by default."""
        geteuid = getattr(os, 'geteuid', None)
        try:
            euid = geteuid() if geteuid is not None else None
        except OSError:
            euid = None
        if not isinstance(euid, int) or isinstance(euid, bool) or euid < 0:
            raise _unsupported_platform(
                'the CLI can\'t get its effective user'
            )
        return euid


def _unsupported_platform(reason):
    # The error for a platform without Unix sockets, with the reason.
    return CredentialDaemonUnsupportedPlatformError(
        error_msg=(
            'The credential daemon isn\'t available on this platform: '
            f'{reason}, so the CLI can\'t check its socket. Nothing was sent '
            'to it.'
        )
    )
