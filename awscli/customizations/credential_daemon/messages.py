# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What the CLI says when the credential daemon isn't running or doesn't
answer, or holds a request for the customer's approval, and the questions it
asks before a move changes what a profile signs in as."""

import contextlib
import os
import sys

from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    SHOWN_HOME_SOCKET,
    approval_instructions,
    end_sentence,
    start_hint,
    strip_control_characters,
    unavailable_here_message,
)
from botocore.exceptions import (
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonUnsupportedPlatformError,
    CredentialDaemonUntrustedSocketError,
)

from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.prompts import yes_no_choice
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty

# What messages call it.
CREDENTIAL_DAEMON = 'credential daemon'

# The errors a command reports as the credential daemon being unavailable:
# nothing answers on the socket (NOT_RUNNING, a timeout included), the
# CLI didn't trust what's there (UNTRUSTED_SOCKET) and sent nothing, or it
# doesn't run on this platform, such as Windows.
DAEMON_UNAVAILABLE_ERRORS = (
    CredentialDaemonNotRunningError,
    CredentialDaemonUntrustedSocketError,
    CredentialDaemonUnsupportedPlatformError,
)
# How to use files where the credential daemon doesn't run, for a command
# run with --credential-storage daemon.
WITHOUT_DAEMON_FLAG_HINT = (
    'To use files on this machine, run the command again without '
    '--credential-storage daemon.'
)


def daemon_down_message(error):
    """What to say when the credential daemon is unavailable. For
    NOT_RUNNING, a timeout included: the reason, how to start the
    credential daemon, and to try again.

    The client's message names the socket and the OS error or the timeout
    that fired, with control characters removed, as the credential
    provider shows it. For UNTRUSTED_SOCKET it's only the client's
    message, which says which check failed: starting the credential daemon
    wouldn't help.
    """
    if isinstance(error, CredentialDaemonUntrustedSocketError):
        return str(error)
    if isinstance(error, CredentialDaemonUnsupportedPlatformError):
        # Starting or installing it can't help here.
        return unavailable_here_message()
    hint = start_hint(error)
    if not hint:
        return f'{error} Then try again.'
    return f'{error} {hint} Then try again.'


def check_credential_daemon_ready(client):
    """Check that the credential daemon is there for ``client``'s next
    call, before a command asks for input or changes anything. Nothing is
    sent. An unavailable credential daemon is a ``ConfigurationError`` with
    ``daemon_down_message``, as the command's own call would raise it, so
    the command fails before its first prompt rather than after it."""
    with daemon_down_is_configuration_error():
        client.probe()


@contextlib.contextmanager
def daemon_down_is_configuration_error(other_errors=False):
    """Turn an unavailable credential daemon (``DAEMON_UNAVAILABLE_ERRORS``)
    into a ``ConfigurationError`` with ``daemon_down_message``, caused by
    the client's error. With ``other_errors``, any other credential daemon
    error is one too, with the error's own message. Anything else passes
    through."""
    try:
        yield
    except DAEMON_UNAVAILABLE_ERRORS as e:
        raise ConfigurationError(daemon_down_message(e)) from e
    except CredentialDaemonError as e:
        if not other_errors:
            raise
        raise ConfigurationError(str(e)) from e


def required_progress_text(progress, key, error_msg):
    """The text a credential daemon progress message sent under ``key``,
    with control characters removed. It fails the sign-in with
    ``error_msg`` if that's missing, not text, or empty once stripped."""
    value = progress.get(key)
    if not isinstance(value, str) or not strip_control_characters(value):
        raise CredentialDaemonProtocolError(error_msg=error_msg)
    return strip_control_characters(value)


def unavailable_here_error(subject=None, way_out=None):
    """The refusal where the credential daemon doesn't run, such as
    Windows, for ``subject`` (such as ``profile_subject``), which uses it.

    ``way_out`` says how to use files instead: ``USE_FILES_HERE_HINT`` for
    a profile with credential_daemon, ``WITHOUT_DAEMON_FLAG_HINT`` for
    --credential-storage daemon, or ``use_files_hint`` for
    credential_storage = daemon. The command stops before anything
    changes: nothing goes to files instead.
    """
    return ConfigurationError(unavailable_here_message(subject, way_out))


def removal_approval_message(error, why, until):
    """What to say when the credential daemon holds a ``credential/remove``
    for the customer's approval (``APPROVAL_REQUIRED``).

    ``why`` is one line saying why to approve it, and ``until`` says what
    stays in the credential daemon until then. Between them are the
    credential daemon's own instructions for approving
    (``data.remediation``). Without them, the credential daemon's error
    message takes their place and ``why``'s. It isn't a failure of the
    command's own work: the customer approves the removal later, or never.
    """
    return approval_message(error, until, why)


def approval_message(error, until, why=None):
    """What to say when the credential daemon holds a request for the
    customer's approval (``APPROVAL_REQUIRED``): ``why``, then the
    credential daemon's own instructions for approving, then ``until``.

    Without ``why``, the credential daemon's message says it, as it names
    each change. Without the instructions, or that message, the credential
    daemon's error message takes their place and ``why``'s.
    """
    instructions = approval_instructions(error.data)
    if why is None:
        if not error.daemon_message:
            instructions = None
        else:
            why = end_sentence(error.daemon_message)
    if instructions is None:
        return f'{error}\n{until}'
    return f'{why}\n  {instructions}\n{until}'


def profile_subject(profile_name):
    """``profile '<name>'``, for a message about a profile."""
    return f"profile '{strip_control_characters(profile_name)}'"


def warn_copy_left_on_unsupported_platform(subject, where, name):
    """Warn that ``subject``, such as ``profile 'ci'``, moved to ``where``,
    but its copy in the credential daemon, credential ``name``, can't be
    cleared because the credential daemon doesn't run on this platform. A
    warning, not an error, as in ``warn_unsupported_platform``: running the
    command again can never help."""
    uni_print(
        f'warning: {strip_control_characters(subject)} moved to {where}. '
        f'Its copy in the {CREDENTIAL_DAEMON} '
        f'(credential {quoted_names([name])}) can\'t be cleared on this '
        f'platform; clear it on the machine where the {CREDENTIAL_DAEMON} '
        'runs.\n',
        sys.stderr,
    )


def note_copy_left_uninstalled(
    socket_path, name, what="this profile's credential"
):
    """Say that the copy of ``what``, credential ``name``, wasn't cleared
    on a move back to files, because nothing is at ``socket_path``. A
    note, not an error: there's nothing here to clear it with.

    The credential daemon may run elsewhere, such as on the host of a
    container that mounts ``~/.aws``. The move back already took
    credential_daemon out of that shared config, so a command run there
    for this profile wouldn't reach the copy. The note names the
    credential instead.
    """
    shown = strip_control_characters(socket_path or SHOWN_HOME_SOCKET)
    uni_print(
        f'note: no {CREDENTIAL_DAEMON} is running at {shown}, so its old '
        f'copy of {strip_control_characters(what)} wasn\'t cleared. If the '
        f'{CREDENTIAL_DAEMON} runs elsewhere (for example, on the host of '
        f'this container), clear credential {quoted_names([name])} there.\n',
        sys.stderr,
    )


def moved_out_message(subject, where):
    """What to say when ``subject``, such as ``the keys for 'ci'``, moved
    back to files at ``where`` and its copy in the credential daemon was
    cleared. aws login says it this way when it moves a session back to
    files."""
    return f'Moved {subject} out of the {CREDENTIAL_DAEMON} and into {where}.'


def copy_not_cleared_message(subject, where, error, name, hint=''):
    """What to say when ``subject`` moved back to files at ``where``, but
    clearing its copy, credential ``name``, failed with ``error``. aws
    login says it this way when it moves a session back to files.
    ``hint``, starting with a space, says what to run to clear it."""
    return (
        f'Moved {subject} to {where}, but the copy in the '
        f"{CREDENTIAL_DAEMON} wasn't cleared: {end_sentence(str(error))} "
        f"It's still there as credential '{name}'.{hint}"
    )


def use_files_hint(flag=False, from_env=False):
    """How to use files instead, naming only what works for the command.

    ``--credential-storage file`` if the command has it (``flag``).
    ``AWS_CREDENTIAL_STORAGE=file`` when that variable chose the credential
    daemon (``from_env``), since it wins over the profile; else
    ``credential_storage = file`` in the profile.
    """
    ways = []
    if flag:
        ways.append('run the command again with --credential-storage file')
    if not from_env:
        ways.append('set credential_storage = file in the profile')
    elif not flag:
        ways.append('run the command again with AWS_CREDENTIAL_STORAGE=file')
    return f'To use files for it, {", or ".join(ways)}.'


def run_hint_start(error):
    """How a hint to run a command starts: with how to start the credential
    daemon first when ``error`` says it isn't running."""
    if isinstance(error, CredentialDaemonNotRunningError):
        hint = start_hint(error)
        if hint:
            return f'{hint} Then run'
    return 'Run'


def quoted_names(names):
    """Names, each in single quotes, joined with commas, with control
    characters removed: they come from config files and the credential
    daemon's credential/list."""
    return ', '.join(f"'{strip_control_characters(name)}'" for name in names)


def display_path(path):
    """``path`` as messages show it, with ``~`` for the home folder."""
    home = os.path.expanduser('~')
    if path.startswith(home + os.sep):
        return '~' + path[len(home) :]
    return path


def mark_created_by_cli(
    client, name, done='Signed in', clears='aws logout --all'
):
    """Tag credential ``name`` created-by=aws-cli after a bootstrap.

    The bootstrap sends no tags, so the credential keeps any it had, and
    this adds the CLI's. If the credential daemon doesn't tag it, the
    sign-in or store still worked, so this only warns: ``done`` says what
    worked, and ``clears`` names the command that signs out only tagged
    credentials, or is None when none does. Returns whether it was tagged.
    """
    if client.mark_created_by_cli(name):
        return True
    shown = strip_control_characters(name)
    message = (
        f"{done}, but the {CREDENTIAL_DAEMON} didn't tag '{shown}' "
        'created-by=aws-cli'
    )
    if clears is not None:
        message += f", so {clears} won't sign it out"
    message += (
        f'. To tag it: creds tag set --credential {shown} created-by=aws-cli'
    )
    uni_print(f'{message}\n', sys.stderr)
    return False


def join_names(names):
    """Names, each in single quotes, with "and" before the last."""
    if len(names) == 1:
        return quoted_names(names)
    return f'{quoted_names(names[:-1])} and {quoted_names(names[-1:])}'


def uses_phrase(names, still=True):
    """``'a' still uses it``, or ``'a' and 'b' still use it``, for the
    profiles that keep something the command left."""
    verb = 'uses' if len(names) == 1 else 'use'
    still = 'still ' if still else ''
    return f'{join_names(names)} {still}{verb} it'


def warn_ignored_next_to_daemon(profile_name, what, ignored, used):
    """Warn that profile ``profile_name`` also has ``what``, which the
    AWS CLI ignores (``ignored``, such as ``it``) because credential_daemon
    wins, but older tools use (``used``, such as ``that line``)."""
    uni_print(
        f"warning: profile '{profile_name}' also has {what}. The AWS CLI "
        f'ignores {ignored} and uses the {CREDENTIAL_DAEMON}, but older '
        f'SDKs and tools use {used} instead.\n',
        sys.stderr,
    )


def warn_unsupported_platform(profiles):
    """Warn that ``profiles`` use the credential daemon, which doesn't run on
    this platform (such as a config copied from a Mac to Windows), so their
    credentials can't be cleared here. A warning, not an error: running the
    command again can never help."""
    one = len(profiles) == 1
    uni_print(
        f"warning: {'profile' if one else 'profiles'} "
        f"{join_names(profiles)} {'uses' if one else 'use'} the "
        f"{CREDENTIAL_DAEMON}, which isn't available on this platform; "
        f"{'its' if one else 'their'} credentials can't be cleared "
        "here.\n",
        sys.stderr,
    )


def signed_out_count_message(count, what):
    """``Signed out of <count> <what>(s) in the credential daemon.``, for
    a sign-out of every session the CLI made, such as ``what`` session or
    SSO session."""
    plural = 's' if count != 1 else ''
    return (
        f'Signed out of {count} {what}{plural} in the {CREDENTIAL_DAEMON}.\n'
    )


def print_notice(text):
    uni_print(text, sys.stderr)


# The developer preview notice, as the credential daemon docs word it.
# The URL stays although the page isn't live yet: for example, before the
# docs launch it redirects to the AWS CLI user guide's start page. Kept so
# the text matches the docs word for word and needs no change at launch;
# the notice says what matters without the link.
PREVIEW_NOTICE = (
    'note: The credential daemon support in this build is a developer '
    'preview under active development. Don\'t use it in production '
    'environments. For more information, see '
    'https://docs.aws.amazon.com/cli/latest/userguide/'
    'cli-authentication-credsd.html'
)


def print_preview_notice():
    """Say on stderr, on its own line, that credential daemon support is a
    developer preview.

    The support may still change, so the customer hears it each time they
    choose to use the credential daemon:

    - when ``aws configure credential-daemon install`` starts, after its
      refusals and release checks;
    - before each question about where to store credentials (``aws
      login``, and ``aws configure`` entering a new profile's keys).

    Nothing else prints it. For example, ``aws login`` with no terminal
    asks nothing and stores in files as before, so it says nothing new.
    """
    print_notice(f'{PREVIEW_NOTICE}\n')


def confirm_session_overwrite(
    profile_name, old, new, is_tty=None, ask=None, notice=print_notice
):
    """Ask before a profile signs in as a different identity, in the words
    aws login uses for session files.

    With no terminal the answer is no, so a script never changes who a
    profile signs in as. ``notice`` gets the text that says so.
    """
    profile_name = strip_control_characters(profile_name)
    if (is_tty or is_stdin_a_tty)():
        return (ask or yes_no_choice)(
            f'\nProfile {profile_name} is already configured to use session '
            f'{old}. Do you want to overwrite it to use {new} instead? '
            f'(y/n): '
        )
    notice(
        f'\nProfile {profile_name} is already configured to use session '
        f'{old}. Run \'aws login\' in a terminal to overwrite it to use '
        f'{new}.\n'
    )
    return False


def confirm_delete_leftover(profile_name, path, is_tty=None, ask=None):
    """Offer to delete a session file an older CLI left next to a
    profile in the credential daemon.

    With no terminal the answer is no, so a script never deletes it.
    """
    profile_name = strip_control_characters(profile_name)
    if (is_tty or is_stdin_a_tty)():
        return (ask or yes_no_choice)(
            'Delete it? Older AWS CLIs then can\'t use this profile. [y/N] ',
            default=False,
        )
    uni_print(
        f'Run \'aws login\' in a terminal to delete it, or '
        f'\'aws logout --profile {profile_name}\'.\n',
        sys.stderr,
    )
    return False
