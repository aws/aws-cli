# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What the commands that use the credential daemon share.

Each command keeps its own flow for files and puts the credential daemon's
part in a class of its own that builds on ``CredentialDaemonCommandSupport``.
"""

import sys

from botocore.credential_daemon import (
    CLI_TAGS,
    CREDENTIAL_DAEMON_KEY,
    USE_FILES_HERE_ENV_HINT,
    USE_FILES_HERE_HINT,
    end_sentence,
    is_logout_unsupported,
    profiles_with_config_file_keys,
    strip_control_characters,
)
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonError,
    CredentialDaemonUnsupportedPlatformError,
    CredentialDaemonUntrustedSocketError,
)

from awscli.customizations.credential_daemon.client import command_client
from awscli.customizations.credential_daemon.messages import (
    WITHOUT_DAEMON_FLAG_HINT,
    check_credential_daemon_ready,
    profile_subject,
    quoted_names,
    run_hint_start,
    signed_out_count_message,
    unavailable_here_error,
    use_files_hint,
    warn_unsupported_platform,
)
from awscli.customizations.credential_daemon.results import (
    Cleared,
    ClearOutcome,
    SweepResult,
)
from awscli.customizations.credential_daemon.sessions import has_session
from awscli.customizations.credential_daemon.storage.chooser import (
    CREDENTIAL_DAEMON,
    stores_in_credential_daemon,
)
from awscli.customizations.credential_daemon.storage.policy import (
    DecisionSource,
    Storage,
)
from awscli.customizations.credential_daemon.storage.presence import (
    credential_daemon_absent,
    credential_daemon_runs_here,
    socket_path_present,
)
from awscli.customizations.credential_daemon.storage.profiles import (
    profile_or_default,
    resolve_storage,
)
from awscli.customizations.utils import uni_print


class CredentialDaemonCommandSupport:
    def __init__(self, session, client=None):
        self._session = session
        self._client = client

    def client(self):
        """The command's client, made on first use and shared by its calls."""
        if self._client is None:
            self._client = command_client()
        return self._client

    def profile_config(self, profile_name):
        """The profile's config, with credential_daemon and
        credential_storage read from the config file alone."""
        return profiles_with_config_file_keys(self._session).get(
            profile_name, {}
        )

    def check_ready_if_stored(self, profile_name):
        """Fail now, before the command asks anything, if the profile's
        credentials go to the credential daemon without asking and it isn't
        there."""
        if stores_in_credential_daemon(self._session, profile_name):
            self.check_ready(profile_or_default(profile_name))

    def check_ready(self, profile_name=None, flag=False):
        """Fail now, before the command asks anything or holds anything, if
        the credential daemon isn't there (``check_credential_daemon_ready``).

        Where it doesn't run, such as Windows, the refusal names
        ``profile_name``, the profile that uses it, and how to use files
        for it: without --credential-storage daemon if ``flag`` chose it.
        """
        if not credential_daemon_runs_here():
            raise self.unavailable_here(profile_name, flag)
        check_credential_daemon_ready(self.client())

    def unavailable_here(self, profile_name=None, flag=False):
        """The ``ConfigurationError`` for a command that would use the
        credential daemon where it doesn't run, such as Windows.

        The hint names every setting that would refuse the next run too:
        credential_daemon if the profile names a credential, even when
        --credential-storage daemon (``flag``) chose it, and
        credential_storage or AWS_CREDENTIAL_STORAGE if it says daemon.
        Else ``flag`` says to run without the option.
        """
        if profile_name is None:
            if flag:
                return unavailable_here_error(None, WITHOUT_DAEMON_FLAG_HINT)
            return unavailable_here_error()
        subject = profile_subject(profile_name)
        config = self.profile_config(profile_name)
        storage, source = resolve_storage(
            self._session, profile_or_default(profile_name)
        )
        if CREDENTIAL_DAEMON_KEY in config:
            if source is DecisionSource.ENV and storage is Storage.DAEMON:
                # The variable wins over the profile, so editing the
                # profile alone would be refused again.
                return unavailable_here_error(subject, USE_FILES_HERE_ENV_HINT)
            return unavailable_here_error(subject, USE_FILES_HERE_HINT)
        if flag:
            return unavailable_here_error(subject, WITHOUT_DAEMON_FLAG_HINT)
        return unavailable_here_error(
            subject, use_files_hint(from_env=source is DecisionSource.ENV)
        )

    def runs_here(self):
        """Whether the credential daemon runs on this platform. Where it
        doesn't, such as Windows, commands behave as an AWS CLI without
        credential daemon support, and a profile that uses it is refused
        (``unavailable_here``)."""
        return credential_daemon_runs_here()

    def clear_old_copy(self, call):
        """Clear a credential's old copy from the credential daemon, after
        a move back to files, with ``call(client)``, such as a
        ``credential/logout``. Returns a ``Cleared``; each caller says what
        each outcome means for it.

        Nothing is sent where the credential daemon doesn't run, such as
        Windows (UNSUPPORTED_PLATFORM), or when nothing is at its socket,
        such as after an uninstall (ABSENT): there's nothing to clear it
        with.
        """
        client = self.client()
        if not self.runs_here():
            return Cleared(ClearOutcome.UNSUPPORTED_PLATFORM)
        socket_path = getattr(client, 'socket_path', None)
        if not socket_path_present(socket_path):
            return Cleared(ClearOutcome.ABSENT, socket_path=socket_path)
        try:
            result = call(client)
        except CredentialDaemonCredentialNotFoundError:
            return Cleared(ClearOutcome.NOT_FOUND)
        except CredentialDaemonError as e:
            return Cleared(ClearOutcome.FAILED, error=e)
        return Cleared(ClearOutcome.CLEARED, result=result)

    def sign_out_tagged(
        self,
        select,
        what,
        command,
        profiles_using,
        log,
        log_message,
        name_left=False,
        on_signed_out=None,
    ):
        """Sign out of the sessions the CLI made or signed in, whatever
        they're named and whether or not the config still names them: they
        carry the CLI's tags. Other tools' sessions are theirs to sign out.
        Returns a ``SweepResult``.

        ``select(row)`` picks the command's sessions from the listed rows
        that have one, and ``what`` names one, such as ``session``.
        ``command`` is the command to run again. ``profiles_using()`` lists
        the profiles that use them: a listing that fails is an error only
        when there's one. With none, a credential daemon that's absent is
        silent (``log_message`` goes to ``log`` at debug), and one that's
        stopped, hung or broken gets a warning, so scripts on machines that
        use it only for other tools don't fail.

        One failed sign-out doesn't keep the others signed in, unless the
        credential daemon is gone, since the rest fail too. ``name_left``
        names the sessions left in the error. ``on_signed_out(name,
        result)`` sees each sign-out's ``LogoutResult``.
        """
        if not self.runs_here():
            # Such as Windows: as an AWS CLI without credential daemon
            # support, whatever AWS_CREDENTIAL_DAEMON_SOCKET says. Profiles
            # that name a credential, such as a config copied from a Mac,
            # get a warning: signing out can't succeed here, so it isn't an
            # error.
            profiles = profiles_using()
            if profiles:
                warn_unsupported_platform(profiles)
            return SweepResult(True, 0, [])
        label = f'{what[0].upper()}{what[1:]}s'
        client = None
        try:
            client = self.client()
            rows = client.list_credentials(tags=CLI_TAGS)
            names = [
                row.name for row in rows if has_session(row) and select(row)
            ]
        except CredentialDaemonError as e:
            # For example, aws logout --all with a stopped daemon and no
            # profile with credential_daemon warns and exits 0.
            if profiles_using():
                self.report_uncleared(label, e, "weren't", command)
                return SweepResult(False, 0, [])
            path = getattr(client, 'socket_path', None)
            if credential_daemon_absent(e, path):
                log.debug(log_message, e)
                return SweepResult(True, 0, [])
            self.warn_unchecked(f'{what}s', e, command)
            return SweepResult(True, None, [])
        cleared = 0
        left = []
        error = None
        for i, name in enumerate(names):
            try:
                result = client.logout(name)
            except CredentialDaemonCredentialNotFoundError:
                # Removed since the listing: not counted, as this command
                # didn't sign it out.
                continue
            except CredentialDaemonError as e:
                if is_logout_unsupported(e):
                    # No sign-in to clear, as for access keys.
                    continue
                error = e
                if isinstance(e, CredentialDaemonConnectionError):
                    left.extend(names[i:])
                    break
                left.append(name)
                continue
            if on_signed_out is not None:
                on_signed_out(name, result)
            if result.signed_out:
                cleared += 1
        if cleared:
            uni_print(signed_out_count_message(cleared, what))
        if error is not None:
            verb = "weren't"
            if name_left:
                quoted = quoted_names(
                    strip_control_characters(n) for n in left
                )
                if len(left) == 1:
                    label, verb = f'{what} {quoted}', "wasn't"
                else:
                    label = f'{what}s {quoted}'
            self.report_uncleared(label, error, verb, command)
            return SweepResult(False, cleared, left)
        return SweepResult(True, cleared, left)

    def report_uncleared(self, what, error, verb, command):
        """Say that ``what`` (in the credential daemon) ``verb`` (wasn't or
        weren't) cleared, and how to run ``command`` again."""
        uni_print(
            f"{what} in the {CREDENTIAL_DAEMON} {verb} cleared: "
            f"{end_sentence(strip_control_characters(str(error)))}"
            f"{self.run_again_hint(error, command)}\n",
            sys.stderr,
        )

    def run_again_hint(self, error, command, tail='again.'):
        """How to say to run ``command``, after a space, or nothing for an
        untrusted socket: running a command can't help until the socket is
        fixed, which the trust error says how. Nor where the credential
        daemon doesn't run, such as Windows. It starts with how to start
        the credential daemon when ``error`` says it isn't running."""
        if isinstance(
            error,
            (
                CredentialDaemonUntrustedSocketError,
                CredentialDaemonUnsupportedPlatformError,
            ),
        ):
            return ''
        return f" {run_hint_start(error)} '{command}' {tail}"

    def logout_all_hint(self, error):
        """How to sign out a session left in the credential daemon after
        ``error``."""
        return self.run_again_hint(
            error, 'aws logout --all', 'to sign it out.'
        )

    def warn_unchecked(self, what, error, command):
        """Warn that ``what`` in the credential daemon weren't checked
        because of ``error``. For when no profile uses the credential
        daemon, so ``command`` doesn't fail on a daemon it doesn't need."""
        hint = self.run_again_hint(error, command, 'again to clear them.')
        uni_print(
            f"warning: {what} in the {CREDENTIAL_DAEMON} weren't checked: "
            f"{end_sentence(strip_control_characters(str(error)))} "
            f"No profile uses it.{hint}\n",
            sys.stderr,
        )
