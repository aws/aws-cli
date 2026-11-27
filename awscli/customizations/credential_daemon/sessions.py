# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What aws login (and later commands) share about a profile's credential
daemon lines and the credential daemon's sessions.

It sits below both packages, which import each other's modules.
"""

import os

from botocore.compat import compat_shell_split
from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    profiles_with_config_file_keys,
    strip_control_characters,
)

from awscli.customizations.credential_daemon.messages import (
    warn_ignored_next_to_daemon,
)


def is_credential_daemon_workaround(credential_process, profile_name):
    """Whether credential_process is the documented line for older tools.

    That is ``<path to aws> configure export-credentials --profile
    <profile_name>``, with or without ``--format process``.
    """
    if not credential_process:
        return False
    try:
        args = compat_shell_split(credential_process)
    except ValueError:
        return False
    if len(args) < 3 or args[1:3] != ['configure', 'export-credentials']:
        return False
    executable = os.path.basename(args[0].replace('\\', '/')).lower()
    if executable not in ('aws', 'aws.exe', 'aws.cmd'):
        return False
    options = _parse_options(args[3:])
    if options is None or options.get('--profile') != profile_name:
        return False
    return set(options) <= {'--profile', '--format'} and (
        options.get('--format', 'process') == 'process'
    )


def leftover_credential_process(profile, profile_name):
    """The credential_process next to credential_daemon, if not the
    documented line for older tools."""
    credential_process = profile.get('credential_process')
    if CREDENTIAL_DAEMON_KEY not in profile or not credential_process:
        return None
    if is_credential_daemon_workaround(credential_process, profile_name):
        return None
    return credential_process


def warn_leftover_credential_process(profile_name, credential_process):
    # credential_daemon wins, so this CLI ignores the line, but older
    # tools still run it.
    warn_ignored_next_to_daemon(
        profile_name,
        f'credential_process = {strip_control_characters(credential_process)}',
        'it',
        'that line',
    )


def _parse_options(args):
    """Parse ``--name value`` and ``--name=value`` pairs, or return None."""
    options = {}
    args = list(args)
    while args:
        arg = args.pop(0)
        if not arg.startswith('--'):
            return None
        name, sep, value = arg.partition('=')
        if not sep:
            if not args:
                return None
            value = args.pop(0)
        if name in options:
            return None
        options[name] = value
    return options


def profiles_using_session_file(session, session_id, profile_name):
    """The other profiles whose ``login_session`` is ``session_id``, sorted:
    they share its aws login session file.

    A profile in the credential daemon counts too: an older CLI ignores
    its credential_daemon and still reads the file. Like
    ``profiles_naming``, this sees only the config file the CLI loaded.
    """
    return sorted(
        other
        for other, config in session.full_config.get('profiles', {}).items()
        if other != profile_name and config.get('login_session') == session_id
    )


def profiles_naming(session, name, profile_name):
    """The other profiles whose ``credential_daemon`` is ``name``, sorted.

    Accepted limit: this sees only the config file the CLI loaded. A
    profile in another config file (``AWS_CONFIG_FILE``) that names the
    same credential isn't seen or named in the question, and switches
    identity with the profiles that are; nor does it keep the credential
    on a move of keys back to files.
    """
    return sorted(
        other
        for other, config in profiles_with_config_file_keys(session).items()
        if other != profile_name and config.get(CREDENTIAL_DAEMON_KEY) == name
    )


def has_session(row):
    # Anything not already signed out is cleared: an expired session may
    # still hold a refresh token. The credential daemon refuses access
    # keys, which have no sign-in. Skip rows this CLI can't read rather
    # than fail the whole sign-out.
    return isinstance(row.name, str) and not row.signed_out


def profiles_using_credential_daemon(session):
    """The profiles with ``credential_daemon``, sorted."""
    return sorted(
        name
        for name, profile in profiles_with_config_file_keys(session).items()
        if CREDENTIAL_DAEMON_KEY in profile
    )
