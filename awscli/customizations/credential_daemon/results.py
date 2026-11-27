# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What the commands' shared credential daemon steps return."""

from collections import namedtuple
from enum import Enum


class ClearOutcome(Enum):
    """How clearing a credential's old copy from the credential daemon
    went (``CredentialDaemonCommandSupport.clear_old_copy``)."""

    CLEARED = 'cleared'
    # The credential daemon has no credential of that name.
    NOT_FOUND = 'not-found'
    # It doesn't run on this platform, such as Windows. Nothing is sent.
    UNSUPPORTED_PLATFORM = 'unsupported-platform'
    # Nothing is at its socket, such as after an uninstall. Nothing is
    # sent.
    ABSENT = 'absent'
    # The call failed with ``error``.
    FAILED = 'failed'


# ``result`` is what the call returned, for CLEARED. ``socket_path`` is the
# socket that has nothing at it, for ABSENT.
Cleared = namedtuple(
    'Cleared',
    ['outcome', 'error', 'result', 'socket_path'],
    defaults=(None, None, None),
)


# What ``CredentialDaemonCommandSupport.sign_out_tagged`` did. ``ok`` is
# whether nothing was left signed in. ``cleared`` is how many sessions it
# signed out, or None if the credential daemon couldn't be checked: it may
# hold sessions. ``left`` names the sessions a failed call left signed in.
SweepResult = namedtuple('SweepResult', ['ok', 'cleared', 'left'])
