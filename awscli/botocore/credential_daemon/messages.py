# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Advice the CLI gives about the credential daemon."""

from botocore.credential_daemon.config import (
    CREDENTIAL_DAEMON_KEY,
    DAEMON_SOCKET_ENV_VAR,
)
from botocore.credential_daemon.text import (
    end_sentence,
    strip_control_characters,
)

INSTALL_COMMAND = 'aws configure credential-daemon install'
LINK_COMMAND = 'aws configure credential-daemon link'
LINK_REMOVE_COMMAND = f'{LINK_COMMAND} --remove'
# The one remedy every not-running message gives, as the SEP's NOT_RUNNING
# remedy does: install the credential daemon, link its socket, or point the
# variable at it. Messages build on it through START_HINT and NO_SOCKET_HINT,
# or on its parts; don't word it anywhere else.
INSTALL_REMEDY = f"install it with '{INSTALL_COMMAND}'"
LINK_REMEDY = f"link its socket with '{LINK_COMMAND}'"
SOCKET_ENV_VAR_REMEDY = f'set {DAEMON_SOCKET_ENV_VAR}'
NOT_RUNNING_REMEDY = (
    f'{INSTALL_REMEDY}, {LINK_REMEDY}, or {SOCKET_ENV_VAR_REMEDY}'
)
# What to do when the credential daemon isn't running or doesn't answer. It
# may be installed but stopped, not installed, or not linked.
START_HINT = f'Start the credential daemon, or {NOT_RUNNING_REMEDY}.'
# What link says when no socket is there to link: the remedy without
# linking.
NO_SOCKET_TO_LINK_HINT = (
    f'Start the credential daemon, or {INSTALL_REMEDY}, or '
    f'{SOCKET_ENV_VAR_REMEDY}.'
)


# What to do when no location applies: nothing is at
# ~/.aws/credential-daemon.sock and the variable isn't set, so there's
# nothing to start.
NO_SOCKET_HINT = f'To use the credential daemon, {NOT_RUNNING_REMEDY}.'
# What every command and the credential provider say where the credential
# daemon doesn't run, such as Windows (unavailable_here_message). Nothing
# that can't work there, such as starting or installing it.
UNSUPPORTED_PLATFORM_MESSAGE = (
    'The credential daemon isn\'t available on this platform.'
)
# credential_storage = daemon would refuse the next sign-in too, so the hint
# names it.
USE_FILES_HERE_HINT = (
    'To use it on this machine, use files for it: remove '
    f'{CREDENTIAL_DAEMON_KEY} from the profile and any credential_storage = '
    'daemon (or set it to file), then sign in again or enter its keys with '
    "'aws configure'."
)
# USE_FILES_HERE_HINT, for when AWS_CREDENTIAL_STORAGE=daemon chose the
# credential daemon: it wins over the profile.
USE_FILES_HERE_ENV_HINT = (
    'To use it on this machine, use files for it: remove '
    f'{CREDENTIAL_DAEMON_KEY} from the profile and run the command again '
    'with AWS_CREDENTIAL_STORAGE=file.'
)


def unavailable_here_message(subject=None, way_out=None):
    """What to say when ``subject``, such as ``profile 'dev'``, uses the
    credential daemon on a platform it doesn't run on, such as Windows.

    ``way_out`` says how to use files instead, such as
    ``USE_FILES_HERE_HINT`` for a profile with credential_daemon. With
    neither, only that the credential daemon isn't available.
    """
    if subject is None:
        message = UNSUPPORTED_PLATFORM_MESSAGE
    else:
        message = (
            'The credential daemon isn\'t available on this platform, so '
            f'{subject} can\'t be used here.'
        )
    if way_out:
        message = f'{message} {way_out}'
    return message


def start_hint(error):
    """What to tell the customer to do about ``error``, a not-running
    error, or the empty string when its message already says it.

    Most not-running errors get ``START_HINT``. Discovery's own errors,
    such as no socket at all or a link to nothing, carry their own.
    """
    hint = getattr(error, 'hint', None)
    return START_HINT if hint is None else hint


def approval_instructions(data):
    """The credential daemon's own instructions for approving what an
    ``APPROVAL_REQUIRED`` error holds, from ``data.remediation``, or None.

    The CLI shows them as sent, with control characters removed, rather than
    making its own. ``data.challenge`` is an object the CLI doesn't read.
    """
    if not isinstance(data, dict):
        return None
    remediation = data.get('remediation')
    if not isinstance(remediation, str):
        return None
    return strip_control_characters(remediation).strip() or None


def _with_approval_instructions(message, data):
    """Add the credential daemon's instructions for approving to
    ``message``. Without them, the message stays as the credential daemon
    sent it.
    """
    instructions = approval_instructions(data)
    if instructions is None:
        return message
    return f'{end_sentence(message)} {instructions}'
