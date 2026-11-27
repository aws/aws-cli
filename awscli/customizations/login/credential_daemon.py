# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Signing in with ``aws login`` through the credential daemon.

The credential daemon runs the whole sign-in in one ``credential/bootstrap``
call. The CLI only handles what the customer sees: it opens or prints the
sign-in URL and reads the code for ``--remote``. Replacing a credential with
a different identity is the credential daemon's to approve: it asks for
approval before it saves one over another.
"""

import logging
import os
import sys
from collections import namedtuple

from botocore.configloader import load_config
from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    LOGIN_TAG,
    Source,
    Status,
    credential_daemon_value,
    end_sentence,
    find_credential_row,
    is_logout_unsupported,
    is_valid_credential_name,
    strip_control_characters,
)
from botocore.credential_daemon.config import is_sso_profile_without_role
from botocore.exceptions import (
    BotoCoreError,
    CredentialDaemonApprovalRequiredError,
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonError,
    CredentialDaemonProtocolError,
    LoginAuthorizationCodeError,
)
from botocore.utils import get_login_token_cache_directory

from awscli.compat import compat_input
from awscli.customizations.configure import profile_to_section
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.credential_daemon.command import (
    CredentialDaemonCommandSupport,
)
from awscli.customizations.credential_daemon.messages import (
    DAEMON_UNAVAILABLE_ERRORS,
    approval_message,
    confirm_delete_leftover,
    confirm_session_overwrite,
    copy_not_cleared_message,
    daemon_down_is_configuration_error,
    daemon_down_message,
    display_path,
    join_names,
    mark_created_by_cli,
    moved_out_message,
    note_copy_left_uninstalled,
    print_notice,
    profile_subject,
    required_progress_text,
    uses_phrase,
    warn_copy_left_on_unsupported_platform,
    warn_ignored_next_to_daemon,
)
from awscli.customizations.credential_daemon.results import ClearOutcome
from awscli.customizations.credential_daemon.sessions import (
    is_credential_daemon_workaround,
    leftover_credential_process,
    profiles_naming,
    profiles_using_session_file,
    warn_leftover_credential_process,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CREDENTIAL_DAEMON,
)
from awscli.customizations.credential_daemon.storage.presence import (
    credential_daemon_absent,
)
from awscli.customizations.credential_daemon.storage.profiles import (
    expanded_path,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.customizations.login import utils as login_utils
from awscli.customizations.login.backends import (
    Leaving,
    SignInBackend,
    SignInResult,
)
from awscli.customizations.login.utils import (
    LoginType,
)
from awscli.customizations.prompts import yes_no_choice
from awscli.customizations.sso.utils import (
    OpenBrowserHandler,
    PrintOnlyHandler,
    open_browser_with_original_ld_path,
)
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty

LOG = logging.getLogger(__name__)

# What a move back to files calls the session it moves.
_SESSION_SUBJECT = "this profile's session"


class CredentialDaemonSignInHandler:
    """Answers the credential daemon's progress messages during a sign-in."""

    def __init__(
        self,
        remote,
        open_browser=None,
        read_input=None,
    ):
        self._remote = remote
        self._open_browser = open_browser or open_browser_with_original_ld_path
        self._read_input = read_input or compat_input

    def __call__(self, progress):
        kind = progress.get('type')
        if kind == 'authorize_url':
            if self._remote:
                # A credential daemon without --remote ignores it and sends a
                # URL that redirects to this host, so no code would come.
                raise CredentialDaemonProtocolError(
                    error_msg='This version of the credential daemon '
                    'doesn\'t support \'aws login --remote\'. Update it, or '
                    'run \'aws login\' without --remote.'
                )
            self._show_url(progress)
        elif kind == 'authorize_code':
            if not self._remote:
                # Only a --remote sign-in has a code to enter. Raising
                # cancels the sign-in.
                raise CredentialDaemonProtocolError(
                    error_msg=(
                        'The credential daemon asked for an '
                        'authorization code, but '
                        'this sign-in isn\'t --remote.'
                    )
                )
            self._show_url(progress)
            return self._read_code()
        return None

    def _show_url(self, progress):
        # Without one, the customer would be told to open no page, and the
        # sign-in would wait until the credential daemon gives up.
        url = required_progress_text(
            progress,
            'url',
            'The credential daemon sent a URL sign-in without a URL.',
        )
        if self._remote:
            handler = PrintOnlyHandler()
        else:
            handler = OpenBrowserHandler(open_browser=self._open_browser)
        handler(
            userCode=None,
            verificationUri=url,
            verificationUriComplete=url,
            cross_device_flag='--remote',
        )

    def _read_code(self):
        # One code, as with files: the credential daemon checks it, and a
        # wrong one ends the sign-in with the credential daemon's error.
        code = self._read_input(
            '\nEnter the authorization code displayed in your browser: '
        ).strip()
        if not code:
            # Raising closes the connection, which cancels the sign-in.
            raise LoginAuthorizationCodeError(
                error_msg='Failed to retrieve an authorization code.'
            )
        return {'selection': code}


def identity_principal(identity):
    """The principal to show for an identity the credential daemon sent
    (its ``arn``), or None."""
    if not isinstance(identity, dict):
        return None
    arn = identity.get('arn')
    if not isinstance(arn, str):
        return None
    return strip_control_characters(arn) or None


def result_principal(result):
    """Who an aws login ``credential/bootstrap`` result says signed in,
    or None."""
    if not isinstance(result, dict):
        return None
    return identity_principal(result.get('identity'))


def confirm_shared_sign_in(
    name,
    new,
    others,
    is_tty=None,
    ask=None,
    yes_without_terminal=True,
    notice=print_notice,
):
    """Ask before a sign-in gives an identity to a credential that other
    profiles name but no profile has an identity on.

    A yes keeps the sign-in, so every profile on the credential gets the
    new identity. No identity is replaced, so with no terminal the answer
    is yes, as with no other profile on it, unless
    ``yes_without_terminal`` is False.
    """
    used_by = (
        f"\nCredential '{strip_control_characters(name)}' is also used by "
        f"{join_names(others)}."
    )
    every = _every(others)
    if (is_tty or is_stdin_a_tty)():
        return (ask or yes_no_choice)(
            f'{used_by} Sign in as {new} for {every}? [y/N] ',
            default=False,
        )
    if yes_without_terminal:
        return True
    notice(
        f'{used_by} Run \'aws login\' in a terminal to sign in as {new} for '
        f'{every}.\n'
    )
    return False


def _every(others):
    return 'both' if len(others) == 1 else 'all of them'


class DaemonSignIn(CredentialDaemonCommandSupport, SignInBackend):
    """aws login with the credential daemon.

    As the new backend, it signs in and returns ``credential_daemon`` for
    the command's profile write. As the old one, when a profile moves back
    to files, ``leave`` says what goes with the write and clears the
    credential after it (``DaemonLeave``).
    """

    def __init__(self, session, chooser, client=None):
        super().__init__(session, client=client)
        self._chooser = chooser
        # The command's name, for the access-key refusal's message.
        self._command = 'login'
        self._left_in_credential_daemon = False
        # The sign-in this run made, for write_failed() and after_write().
        self._signed_in = None
        # credential/list's rows from refuse_access_keys, for sign_in.
        self._listed = None

    @property
    def exit_code(self):
        """1 if the sign-in worked but left the new session in the
        credential daemon, else None."""
        if self._left_in_credential_daemon:
            return 1
        return None

    def check(self, profile_name, command):
        """Nothing to refuse here: access keys were refused before any
        prompt (``refuse_access_keys``). Only records the command's name."""
        self._command = command

    def holds(self, profile_name, before):
        """Whether the profile's credentials are in the credential daemon.

        Not for an SSO profile with no account and no role: tools skip its
        credential_daemon, such as sso.acme that aws sso login wrote on
        [profile ci] with only sso_session = acme. That credential is the
        session's, so a sign-in with files leaves it alone.
        """
        if is_sso_profile_without_role(before):
            return False
        return credential_daemon_value(profile_name, before) is not None

    def leave(self, profile_name, before=None):
        """A sign-in with files for a profile that was in the credential
        daemon: what goes with the write, and the clear after it, as a
        ``DaemonLeave``. The config file's credential_daemon is read here,
        so ``before`` isn't needed.

        A credential that holds access keys was refused before any prompt
        (``refuse_access_keys``), unless the credential daemon is absent.

        Nothing is asked. The profile has no login_session, and the
        credential daemon's rows don't say who a credential is signed in
        as, so, as for a file profile with no login_session, there's no
        identity to compare with.
        """
        name = credential_daemon_value(
            profile_name, self.profile_config(profile_name)
        )
        # The documented line for older tools only reaches the credential
        # daemon, so it goes with credential_daemon. Any other
        # credential_process is the customer's own and stays. Only
        # ~/.aws/config is rewritten, so a line in ~/.aws/credentials stays
        # too.
        remove_workaround = name is not None and (
            is_credential_daemon_workaround(
                _config_file_profile(self._session, profile_name).get(
                    'credential_process'
                ),
                profile_name,
            )
        )
        return DaemonLeave(
            self._session,
            profile_name,
            name,
            remove_workaround,
            client=self.client(),
        )

    def refuse_access_keys(self, profile_name, command, daemon_path=True):
        """Refuse, before any prompt, a profile whose credential_daemon
        credential holds access keys, wherever the sign-in goes.

        A sign-in to the credential daemon is refused as aws login refuses
        keys in files; it's checked only if ``daemon_path``, since a
        refused --redirect-port gets its own error first. A sign-in with
        files is refused because credential_storage only says where new
        credentials go: keys move back to files only when they're entered
        again with aws configure. So the credential daemon is asked even
        with ``credential_storage = file``, unless it's absent, such as
        after an uninstall: then nothing there can be dropped, and the
        profile moves to files as before.

        The credential's source decides, never its name. Where the
        credential daemon doesn't run, there's nothing to ask.
        """
        self._command = command
        self._listed = None
        if not self.runs_here():
            return
        config = self.profile_config(profile_name)
        if is_sso_profile_without_role(config):
            # Its sign-in goes to files and leaves its credential_daemon
            # alone (holds()), so the credential daemon isn't asked.
            return
        name = credential_daemon_value(profile_name, config)
        if name is None:
            return
        to_credential_daemon = self._chooser.stores_in_credential_daemon(
            profile_name
        )
        if to_credential_daemon and not daemon_path:
            return
        client = self.client()
        try:
            rows = client.list_credentials()
        except DAEMON_UNAVAILABLE_ERRORS as e:
            if not to_credential_daemon and credential_daemon_absent(
                e, getattr(client, 'socket_path', None)
            ):
                LOG.debug('Not checking credential %s: %s', name, e)
                return
            raise ConfigurationError(daemon_down_message(e)) from e
        if to_credential_daemon:
            # The sign-in uses these rows, so it doesn't list again.
            self._listed = rows
            self._refuse_access_keys(rows, profile_name, name)
        elif _holds_access_keys(rows, name):
            # A move back to files is refused too (exit 253), for example:
            #   [profile dev]
            #   credential_daemon = keys.dev
            #   credential_storage = file
            # `aws login --profile dev` fails before the region prompt and
            # nothing changes. Signing in would drop credential_daemon and
            # leave the keys in the daemon with no profile pointing at them.
            raise login_utils.move_back_keys_error(command, profile_name)

    def sign_in(self, request):
        """Sign in to the credential daemon. Returns a ``SignInResult``
        whose values point the profile at the credential."""
        profile_name = request.profile_name
        region = request.region
        sign_in_type = request.sign_in_type
        redirect_port = request.parsed_args.redirect_port
        remote = sign_in_type is LoginType.CROSS_DEVICE
        if refuses_redirect_port(redirect_port, sign_in_type):
            raise redirect_port_refused_error()
        profile = self.profile_config(profile_name)
        stored = credential_daemon_value(profile_name, profile)
        provider = {'type': 'aws_login', 'region': region}
        if remote:
            provider['remote'] = True
        elif redirect_port is not None:
            # The credential daemon listens for the browser's redirect.
            provider['callback_port'] = redirect_port
        client = self.client()
        old_session = profile.get('login_session')
        # aws login names its credential after who signs in, as it names
        # session files, so profiles signed in as one identity share it. The
        # credential daemon picks the name after the sign-in. A name the CLI
        # didn't make, such as one made with creds, is kept.
        by_identity = stored is None or stored.startswith(LOGIN_TAG)
        with daemon_down_is_configuration_error():
            rows = self._listed
            self._listed = None
            if rows is None:
                rows = client.list_credentials()
            self._refuse_access_keys(rows, profile_name, stored)
            if by_identity:
                signed_in = self._sign_in_by_identity(
                    client, provider, rows, profile_name, stored, old_session
                )
            else:
                signed_in = self._sign_in_to_stored_name(
                    client, provider, rows, profile_name, stored
                )
        name = signed_in.name
        pending = signed_in.pending
        principal = result_principal(signed_in.result) or (
            strip_control_characters(name)
        )
        try:
            if not pending.accept():
                return SignInResult(ok=False, exit_code=self.exit_code)
            self._check_new_credential(
                client, profile_name, signed_in, old_session
            )
            leftover = leftover_credential_process(profile, profile_name)
            leftover_keys = stored is not None and (
                'aws_access_key_id' in profile
            )
            values = self._profile_values(request.choice, name)
        except BaseException:
            self._clear_if_pending(
                pending, profile_name, name, signed_in.others
            )
            raise

        self._signed_in = _SignedIn(
            pending, name, signed_in.others, principal, leftover, leftover_keys
        )
        return SignInResult(ok=True, exit_code=None, profile_values=values)

    def _check_new_credential(
        self, client, profile_name, signed_in, old_session
    ):
        """Check that the credential daemon can hand out the new credential
        before the profile points at it and any session file from before
        goes. A failure signs out a credential that wasn't in use."""
        name = signed_in.name
        try:
            client.get_credentials(name)
        except CredentialDaemonError as e:
            kept = f'Profile \'{profile_name}\' wasn\'t changed'
            if old_session is not None:
                kept += ' and its session file was kept'
            message = (
                f'Signed in, but the {CREDENTIAL_DAEMON} couldn\'t return '
                f"credentials for '{name}': {end_sentence(str(e))} "
                f'{kept}.'
            )
            pending = signed_in.pending
            if pending.clear_on_failure:
                pending.clear_on_failure = False
                message += self._clear_unused(client, name, signed_in.others)
            raise ConfigurationError(message) from e

    def _refuse_access_keys(self, rows, profile_name, stored):
        """Refuse, before any sign-in, a profile whose credential holds
        access keys, as aws login refuses one with keys in files."""
        if stored is not None and _holds_access_keys(rows, stored):
            raise login_utils.existing_credentials_error(
                self._command, profile_name, 'Access Key'
            )

    def write_failed(self, request):
        """The profile write failed: sign out a credential that wasn't in
        use before."""
        signed_in = self._signed_in
        self._clear_if_pending(
            signed_in.pending,
            request.profile_name,
            signed_in.name,
            signed_in.others,
        )

    def after_write(self, request, result):
        signed_in = self._signed_in
        # The profile now uses the credential, so a later failure
        # mustn't sign it out.
        signed_in.pending.clear_on_failure = False
        profile_name = request.profile_name
        leaving = request.leaving
        leftover = signed_in.leftover
        storage_line = self._chooser.storage_line(request.choice)
        if leftover is not None:
            warn_leftover_credential_process(profile_name, leftover)
        if signed_in.leftover_keys:
            # credential_daemon wins over static keys too. The key values
            # aren't printed.
            warn_ignored_next_to_daemon(
                profile_name,
                'access keys (aws_access_key_id)',
                'them',
                'the keys',
            )
        # The credential daemon doesn't say when the session ends, so there's
        # no session line.
        lines = [f'\nSigned in as {signed_in.principal}', f'{storage_line}']
        if leaving is not None:
            leaving.note()
            # The session file moves before the summary prints, so a
            # warning about a file that couldn't be deleted comes first.
            lines.extend(leaving.release())
        uni_print('\n'.join(lines) + '\n')
        if leaving is not None:
            leaving.after_summary()
        self._chooser.mark_saved(request.choice)

    def _clear_if_pending(self, pending, profile_name, name, others):
        if pending.clear_on_failure:
            try:
                self._clear_declined(profile_name, name, others)
            except BaseException as e:
                # A failed sign-out, or a second Ctrl-C, mustn't hide
                # the error that stopped the sign-in.
                LOG.debug(
                    'Failed to sign out %s after a failed sign-in: %r',
                    name,
                    e,
                )

    def _profile_values(self, choice, name):
        """credential_daemon, and the storage answer for a new profile:
        it goes in the same write, so a failed write leaves no profile with
        only credential_storage, which would fall through to the host's
        role. What the profile leaves (login_session) is the old
        backend's ``values_to_clear``."""
        return {
            **self._chooser.unsaved_values(choice),
            CREDENTIAL_DAEMON_KEY: name,
        }

    def _sign_in_by_identity(
        self, client, provider, rows, profile_name, stored, old_session
    ):
        """Sign in to the credential the credential daemon names after who
        signs in.

        Returns a ``_Bootstrapped``.
        """
        result = self._bootstrap(
            profile_name, client, provider, name_prefix=LOGIN_TAG
        )
        name = result.get('credential')
        principal = result_principal(result)
        if (
            not is_valid_credential_name(name)
            or not name.startswith(LOGIN_TAG)
            or principal is None
        ):
            raise CredentialDaemonProtocolError(
                error_msg=(
                    f'The {CREDENTIAL_DAEMON} didn\'t '
                    'return a valid aws login '
                    f'credential name and identity. Update it. Profile '
                    f'\'{profile_name}\' wasn\'t changed.'
                    f'{self._clear_unexpected_name(client, rows, name)}'
                )
            )
        # The bootstrap kept the credential's tags; add the CLI's.
        mark_created_by_cli(client, name)
        # Who the profile is signed in as. On the first move that's its session
        # file; in the credential daemon it's its credential's identity. A
        # login_session next to credential_daemon is ignored.
        if stored is None:
            own = old_session
        elif stored == name:
            # The credential daemon named it after this identity, so it's the
            # same one, and nothing is asked. The name has the account and
            # role but not the role session name: with
            # login.111122223333-role-Admin, a sign-in as bob after alice on
            # Admin renews it without the overwrite question files ask. The
            # daemon's own identity check compares the same way, so asking
            # would question a change it treats as the same identity.
            own = None
        else:
            # The credential daemon's rows don't say who a credential is
            # signed in as, so its name stands for who the profile was, and
            # the change is asked about. The credential daemon names an aws
            # login credential after its account and role, so another name
            # is another identity.
            own = stored
        # Only a credential signed in as this identity before the sign-in
        # is in use. A profile that names a signed-out one isn't using it,
        # so a no signs the new session out again.
        others = profiles_naming(self._session, name, profile_name)
        before = find_credential_row(rows, name)
        # The credential daemon names it after the account and role that
        # sign in, and saves another one over it only with approval, so a
        # credential of that name signed in before is in use.
        in_use = before is not None and before.signed_in
        pending = _ByIdentity(
            self, profile_name, name, others, own, principal, in_use
        )
        return _Bootstrapped(name, result, others, pending)

    def _clear_unexpected_name(self, client, rows, name):
        """Sign out the session the credential daemon stored under a name aws
        login doesn't use, and say what's left.

        A name that isn't valid can't be cleared or printed. A credential
        that was signed in before the sign-in is in use, so it's left
        alone.
        """
        if not is_valid_credential_name(name):
            return (
                ' Remove the new session in the '
                f'{CREDENTIAL_DAEMON} if it\'s still there.'
            )
        before = find_credential_row(rows, name)
        if before is not None and before.signed_in:
            return (
                f" '{name}' was signed in to the "
                f'{CREDENTIAL_DAEMON} before, so it '
                f'wasn\'t signed out.'
            )
        try:
            client.logout(name)
        except CredentialDaemonCredentialNotFoundError:
            return (
                f" The {CREDENTIAL_DAEMON} has no credential named '{name}'."
            )
        except CredentialDaemonError as e:
            return (
                ' The new session is still signed in to the '
                f'{CREDENTIAL_DAEMON} as '
                f"'{name}', because it couldn't be signed out: "
                f'{end_sentence(str(e))} Remove '
                f'it in the {CREDENTIAL_DAEMON}.'
            )
        return (
            f" The new session ('{name}') was signed out of "
            f'the {CREDENTIAL_DAEMON}.'
        )

    def _sign_in_to_stored_name(
        self, client, provider, rows, profile_name, name
    ):
        """Sign in to a credential named in the profile that aws login
        didn't name, such as one made with creds (stored names win).

        Profiles that name it share it, and a sign-in replaces it in place
        for all of them. Returns a ``_Bootstrapped``.
        """
        # Access keys were refused in sign_in. Whatever else the credential
        # holds, the credential daemon's approval guards replacing it, a
        # different account or role included.
        row = find_credential_row(rows, name)
        # Only a credential signed in before this sign-in is in use, so
        # only it is kept on a "no" below.
        was_signed_in = row is not None and row.signed_in
        # An expired credential, or one that needs a new sign-in, still
        # has the identity the profiles on it use. A no clears only what
        # wasn't in use.
        had_identity = row is not None and (
            row.signed_in
            or row.status in (Status.EXPIRED, Status.SIGN_IN_REQUIRED)
        )
        others = profiles_naming(self._session, name, profile_name)
        result = self._bootstrap(profile_name, client, provider, name=name)
        # The bootstrap kept the credential's tags; add the CLI's.
        mark_created_by_cli(client, name)
        shown = result_principal(result) or strip_control_characters(name)
        # The sign-in already stored the new identity, and the others on
        # the credential use it. Until the profile is updated, a no, an
        # interrupt or a failure signs out a credential that wasn't in use
        # before.
        pending = _ToStoredName(
            self,
            profile_name,
            name,
            others,
            shown,
            had_identity,
            was_signed_in,
        )
        return _Bootstrapped(name, result, others, pending)

    def _bootstrap(self, profile_name, client, provider, **naming):
        """Sign in to the credential daemon, naming the credential with
        ``naming`` (``name`` or ``name_prefix``).

        A replace the credential daemon holds for approval, such as a sign-in
        as another account or role than the credential records, saved
        nothing, so it fails with the credential daemon's
        message and instructions, and the profile isn't changed.
        """
        handler = CredentialDaemonSignInHandler(
            remote=provider.get('remote', False),
        )
        try:
            return client.bootstrap(provider, on_progress=handler, **naming)
        except CredentialDaemonApprovalRequiredError as e:
            # The same text as aws sso login's: the credential daemon's
            # message, its instructions for approving, then what to do.
            raise ConfigurationError(
                approval_message(
                    e,
                    "Once it's approved, run this command again. Profile "
                    f"'{profile_name}' wasn't changed.",
                )
            ) from e

    def _clear_declined(self, profile_name, name, others=()):
        """Sign out the credential a declined or interrupted sign-in left
        in the credential daemon."""
        try:
            self.client().logout(name)
        except CredentialDaemonError as e:
            self._left_in_credential_daemon = True
            uni_print(
                f'The new session for \'{profile_name}\' is still in the '
                f"{CREDENTIAL_DAEMON} as '{name}'{_used_by(others)}: "
                f'{end_sentence(str(e))}'
                f'{self.logout_all_hint(e)}\n',
                sys.stderr,
            )

    def _clear_unused(self, client, name, others=()):
        """Sign out a new credential that wasn't signed in before.

        Returns a sentence for the error message. A credential that was
        signed in before the sign-in is in use, so it's left alone.
        """
        try:
            client.logout(name)
        except CredentialDaemonCredentialNotFoundError:
            return ''
        except CredentialDaemonError as e:
            return (
                ' The new session is still in the '
                f'{CREDENTIAL_DAEMON}{_used_by(others)}'
                ', because it couldn\'t be signed out: '
                f'{end_sentence(str(e))}'
                f'{self.logout_all_hint(e)}'
            )
        return f' The new session was signed out of the {CREDENTIAL_DAEMON}.'


_Bootstrapped = namedtuple(
    '_Bootstrapped', ['name', 'result', 'others', 'pending']
)
_Bootstrapped.__doc__ = """A credential daemon sign-in the profile doesn't
point at yet: the credential's ``name``, the bootstrap ``result``, the
``others`` profiles that name it, and what's ``pending`` (``_ByIdentity``
or ``_ToStoredName``)."""


class _ByIdentity:
    """What's left of a sign-in to the credential named after who signed
    in: asking before the profile changes identity.

    ``accept()`` asks and returns whether to keep the sign-in. While
    ``clear_on_failure`` is set, a no, an interrupt or a failure signs the
    new credential out.
    """

    def __init__(
        self, sign_in, profile_name, name, others, own, principal, in_use
    ):
        self._sign_in = sign_in
        self._profile_name = profile_name
        self._name = name
        self._others = others
        # Who the profile was signed in as, or None.
        self._own = own
        self._principal = principal
        self._in_use = in_use
        self.clear_on_failure = not in_use

    def accept(self):
        own = self._own
        principal = self._principal
        profile_name = self._profile_name
        if own is None or own == principal:
            return True
        shown = strip_control_characters(own)
        refused = []
        # A yes changes only this profile; the others keep theirs.
        if confirm_session_overwrite(
            profile_name, shown, principal, notice=refused.append
        ):
            return True
        if refused:
            # With no terminal, a script never changes who a profile
            # signs in as, and the identity changing is an error for it,
            # as with session files. The caller signs out the new
            # session if nothing used it before.
            raise ConfigurationError(
                f'{refused[0].strip()} Profile '
                f'\'{strip_control_characters(profile_name)}\' '
                'wasn\'t changed.'
            )
        if not self._in_use:
            self.clear_on_failure = False
            self._sign_in._clear_declined(
                profile_name, self._name, self._others
            )
        uni_print(
            f'\nKept \'{strip_control_characters(profile_name)}\' '
            f'signed in as {shown}.\n'
        )
        return False


class _ToStoredName:
    """What's left of a sign-in to a name the profile stored: asking before
    other profiles on a credential with no identity get this one.

    ``accept()`` and ``clear_on_failure`` work as for ``_ByIdentity``.
    ``in_use`` says the credential was signed in before this sign-in.
    """

    def __init__(
        self, sign_in, profile_name, name, others, shown, had_identity, in_use
    ):
        self._sign_in = sign_in
        self._profile_name = profile_name
        self._name = name
        self._others = others
        self._shown = shown
        self._had_identity = had_identity
        self.clear_on_failure = not in_use

    def accept(self):
        if self._others and not self._had_identity:
            # Others name a credential with no identity: it has no row,
            # or a signed-out one, for example one aws logout left. A
            # yes gives them this one.
            accepted = confirm_shared_sign_in(
                self._name, self._shown, self._others
            )
        else:
            accepted = True
        if accepted:
            return True
        # Only a credential with no identity is asked about, so it
        # wasn't in use.
        self.clear_on_failure = False
        self._sign_in._clear_declined(
            self._profile_name, self._name, self._others
        )
        uni_print(f'\nProfile \'{self._profile_name}\' wasn\'t changed.\n')
        return False


def refuses_redirect_port(redirect_port, sign_in_type):
    # The credential daemon refuses ports below 1024 with an error that names
    # its own callback_port field, so the CLI says it in the customer's terms
    # first. A remote sign-in doesn't listen on a port.
    return (
        redirect_port is not None
        and sign_in_type is not LoginType.CROSS_DEVICE
        and not 1024 <= redirect_port <= 65535
    )


def redirect_port_refused_error():
    return ParamValidationError(
        f'--redirect-port must be between 1024 and 65535 when the '
        f'{CREDENTIAL_DAEMON} signs you in.'
    )


def _holds_access_keys(rows, name):
    """Whether credential ``name`` holds access keys. Its source decides,
    never its name. A name the credential daemon doesn't have doesn't."""
    row = find_credential_row(rows, name)
    return row is not None and row.source == Source.IAM_USER


def _used_by(others):
    """Says which other profiles use a credential left in the credential
    daemon."""
    if not others:
        return ''
    return f', and {uses_phrase(others, still=False)}'


_SignedIn = namedtuple(
    '_SignedIn',
    ['pending', 'name', 'others', 'principal', 'leftover', 'leftover_keys'],
)
_SignedIn.__doc__ = """What a sign-in left for the profile write and
``after_write``."""


class DaemonLeave(Leaving, CredentialDaemonCommandSupport):
    """What a profile leaves in the credential daemon when it signs in with
    files: ``credential_daemon`` and the older-tools credential_process line
    go with the write (``values_to_clear``), and the credential is cleared
    after it (``release``). Made by ``DaemonSignIn.leave``, for one run.
    """

    def __init__(
        self, session, profile_name, name, remove_workaround, client=None
    ):
        super().__init__(session, client=client)
        self._profile_name = profile_name
        self._leaving = name
        self._remove_workaround = remove_workaround
        self._left_in_credential_daemon = False

    @property
    def exit_code(self):
        """1 if the clear left the old session in the credential daemon,
        else None."""
        if self._left_in_credential_daemon:
            return 1
        return None

    def values_to_clear(self):
        """The profile write's part: a failed write leaves the profile in
        the credential daemon, as before."""
        new_values = {}
        if self._leaving is not None:
            new_values[CREDENTIAL_DAEMON_KEY] = None
        if self._remove_workaround:
            new_values['credential_process'] = None
        return new_values

    def note(self):
        """Before the files sign-in's storage line: what the write
        removed."""
        if self._remove_workaround:
            uni_print(
                f'Removed the credential_process line that older tools used '
                f'to reach the {CREDENTIAL_DAEMON} from '
                f'profile \'{self._profile_name}\'.\n'
            )

    def release(self):
        """After the write: clear the credential the profile left. Prints
        what it did, so there are no summary lines."""
        if self._leaving is not None:
            self._clear_from_credential_daemon(
                self._profile_name, self._leaving
            )
        return []

    def _clear_from_credential_daemon(self, profile_name, name):
        cache_dir = display_path(get_login_token_cache_directory())
        # Clearing a credential another profile names would sign that
        # profile out.
        users = profiles_naming(self._session, name, profile_name)
        if users:
            uni_print(
                f'Signed in to profile \'{profile_name}\' with a session '
                f"file. Kept credential '{name}' in the {CREDENTIAL_DAEMON}, "
                f'because {uses_phrase(users)}.\n'
            )
            return
        # The credential daemon decides what it holds: it signs out a
        # session, and refuses anything that isn't a sign-in.
        # A move back signs out (credential/logout) and doesn't delete
        # (credential/clear). For example, `aws login --profile dev` with
        # credential_storage = file signs login.111122223333-role-Admin
        # out, and credential/list still shows it as signed out.
        cleared = self.clear_old_copy(lambda client: client.logout(name))
        if cleared.outcome is ClearOutcome.UNSUPPORTED_PLATFORM:
            # Such as Windows: clearing can never work from here, so it's
            # a warning, not a failure.
            warn_copy_left_on_unsupported_platform(
                profile_subject(profile_name), cache_dir, name
            )
            return
        if cleared.outcome is ClearOutcome.ABSENT:
            # No credential daemon, such as after an uninstall: nothing is
            # sent. The sign-in with files still counts (exit 0), and the
            # note names the credential, which may hold access keys, so it
            # isn't called a session. For example, with no socket at
            # ~/.aws/credential-daemon.sock, a move back of
            # login.111122223333-role-Admin signs in to files and says it may
            # be left in the daemon's storage. Failing would leave no way off
            # an uninstalled daemon; aws logout --all is quiet here too.
            note_copy_left_uninstalled(cleared.socket_path, name)
            return
        if cleared.outcome is ClearOutcome.NOT_FOUND:
            return
        if cleared.outcome is ClearOutcome.FAILED:
            e = cleared.error
            if is_logout_unsupported(e):
                self._keep_unmanaged(profile_name, name)
                return
            self._left_in_credential_daemon = True
            message = copy_not_cleared_message(
                _SESSION_SUBJECT,
                cache_dir,
                e,
                name,
                self.logout_all_hint(e),
            )
            uni_print(f'{message}\n', sys.stderr)
            return
        uni_print(f'{moved_out_message(_SESSION_SUBJECT, cache_dir)}\n')

    def _keep_unmanaged(self, profile_name, name):
        """Keep what the credential daemon refused to sign out: the CLI
        doesn't manage it."""
        uni_print(
            f'Signed in to profile \'{profile_name}\' with a session file. '
            f"Kept credential '{name}' in the {CREDENTIAL_DAEMON}; it isn't "
            "a sign-in and the CLI doesn't manage it.\n"
        )


class SessionMove(Leaving):
    """What a sign-in into the credential daemon does with the profile's
    session file, for one run, so the sign-in can order it with its own
    output.

    ``values_to_clear`` is the sign-in write's part: login_session stays on
    a first move until the file goes, and a file an older CLI left stays
    until the customer deletes it. ``release`` moves the file on a first
    move and returns the lines for the sign-in's summary.
    ``after_summary`` asks about a file an older CLI left.
    """

    def __init__(self, session, config_writer, profile_name, before):
        self._session = session
        self._config_writer = config_writer
        self._profile_name = profile_name
        self._left_on_disk = False
        self._has_login_session = 'login_session' in before
        self._session_id = before.get('login_session')
        stored = credential_daemon_value(profile_name, before)
        # An older CLI signed in to a profile already in the credential
        # daemon and left a session file. Nothing moves, so it isn't a first
        # move.
        older_cli = stored is not None and self._session_id is not None
        self._leftover_file = older_cli and self.session_file_exists(
            self._session_id
        )
        self._first_move = self._session_id is not None and not older_cli

    @property
    def keeps_login_session(self):
        return self._leftover_file or self._first_move

    @property
    def exit_code(self):
        """1 if a session file couldn't be deleted, else None."""
        if self._left_on_disk:
            return 1
        return None

    def values_to_clear(self):
        """login_session goes in the sign-in's write, unless it stays until
        its session file is dealt with."""
        if self._has_login_session and not self.keeps_login_session:
            return {'login_session': None}
        return {}

    def release(self):
        if not self._first_move:
            return []
        return self.move_session_file(self._profile_name, self._session_id)

    def after_summary(self):
        if self._leftover_file:
            self.offer_to_delete_leftover(self._profile_name, self._session_id)

    def _drop_login_session(self, profile_name):
        writer = self._config_writer or ConfigFileWriter()
        writer.update_config(
            {
                '__section__': profile_to_section(profile_name),
                'login_session': None,
            },
            expanded_path(self._session, 'config_file'),
        )

    def offer_to_delete_leftover(self, profile_name, session_id):
        """Warn about a session file an older CLI left, and offer to
        delete it.

        The profile keeps login_session while the file stays, so the older
        CLI can still use it.
        """
        path = display_path(login_utils.session_file_path(session_id))
        uni_print(
            f'warning: an older AWS CLI left a plaintext session file for '
            f'\'{profile_name}\': {path}. Older CLIs use it for this '
            f'profile; this CLI uses the {CREDENTIAL_DAEMON}.\n',
            sys.stderr,
        )
        users = profiles_using_session_file(
            self._session, session_id, profile_name
        )
        if users:
            uni_print(
                f'Kept it, because {uses_phrase(users)}.\n',
                sys.stderr,
            )
            return
        if not confirm_delete_leftover(profile_name, path):
            return
        try:
            login_utils.delete_session_file(
                login_utils.session_file_path(session_id)
            )
        except OSError as e:
            # login_session stays, because the file is still there.
            self._left_on_disk = True
            uni_print(
                f'Couldn\'t delete {path}: {end_sentence(str(e))} The '
                'plaintext session file is still there. Delete it by hand.\n',
                sys.stderr,
            )
            return
        self._drop_login_session(profile_name)
        uni_print(f'Deleted {path}.\n')

    def move_session_file(self, profile_name, session_id):
        """Delete a session file that no other profile names, then drop
        the profile's login_session.

        Returns the summary lines to print.
        """
        cache_dir = display_path(get_login_token_cache_directory())
        users = profiles_using_session_file(
            self._session, session_id, profile_name
        )
        if users:
            self._drop_login_session(profile_name)
            return [
                'Moved this profile\'s session into the '
                f'{CREDENTIAL_DAEMON}. Kept its '
                f'file in {cache_dir}, because {uses_phrase(users)}.'
            ]
        try:
            deleted = login_utils.delete_session_file(
                login_utils.session_file_path(session_id)
            )
        except OSError as e:
            self._left_on_disk = True
            # The file is still there, so the profile keeps pointing at it,
            # as on the leftover path.
            path = display_path(login_utils.session_file_path(session_id))
            uni_print(
                f'warning: couldn\'t delete the session file for '
                f'\'{profile_name}\': {end_sentence(str(e))} The plaintext '
                f'session file is still at {path}. Delete it by hand.\n',
                sys.stderr,
            )
            return [
                'Moved this profile\'s session into the '
                f'{CREDENTIAL_DAEMON}. Its file '
                f'in {cache_dir} wasn\'t deleted.'
            ]
        self._drop_login_session(profile_name)
        if not deleted:
            return []
        return [
            'Moved this profile\'s session into the '
            f'{CREDENTIAL_DAEMON} and deleted '
            f'its file in {cache_dir}.'
        ]

    def session_file_exists(self, session_id):
        return os.path.isfile(login_utils.session_file_path(session_id))


def _config_file_profile(session, profile_name):
    """The profile's own section of the config file, without the values
    the credentials file adds."""
    config_filename = expanded_path(session, 'config_file')
    try:
        config = load_config(config_filename)
    except BotoCoreError:
        return {}
    return config['profiles'].get(profile_name, {})
