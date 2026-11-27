# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""``aws configure credential-daemon``: ``install``, ``uninstall`` and ``link``.

The commands and what they share live in ``credential_daemon_install/``:
``release`` (the GitHub release and its signatures), ``host`` (the platform
and its test seams), ``linux`` and ``macos`` (what each platform installs and
removes), ``links`` (the ``~/.aws/credential-daemon.sock`` link) and
``commands``. This module keeps the names ``configure`` registers and the
install hint reads.
"""

from awscli.customizations.configure.credential_daemon_install.commands import (  # noqa: F401
    ConfigureCredentialDaemonCommand,
    InstallCredentialDaemonCommand,
    LinkCredentialDaemonCommand,
    UninstallCredentialDaemonCommand,
)
from awscli.customizations.configure.credential_daemon_install.host import (  # noqa: F401
    install_supported,
)
