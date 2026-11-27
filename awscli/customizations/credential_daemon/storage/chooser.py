# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Asks once per profile where its credentials go, and saves the answer."""

import os
import sys

from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    CredentialDaemonClient,
    default_socket_path,
    socket_discovery_notes,
    socket_override,
    strip_control_characters,
)
from botocore.credential_daemon.config import DAEMON_SOCKET_ENV_VAR

from awscli.compat import compat_shell_quote
from awscli.customizations.configure import profile_to_section
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.credential_daemon.messages import (
    CREDENTIAL_DAEMON,
    print_preview_notice,
)
from awscli.customizations.credential_daemon.storage.kinds import (
    CredentialKind,
)
from awscli.customizations.credential_daemon.storage.policy import (
    CREDENTIAL_STORAGE,
    DAEMON,
    FILE,
    DecisionSource,
    Storage,
    StorageDecision,
    decide_storage,
    sso_without_role_reason,
)
from awscli.customizations.credential_daemon.storage.presence import (
    credential_daemon_runs_here,
    detect_presence,
    socket_path_present,
    unavailable_error,
)
from awscli.customizations.credential_daemon.storage.profiles import (
    expanded_path,
    profile_config,
    profile_or_default,
    resolve_own_storage,
)
from awscli.customizations.prompts import yes_no_choice
from awscli.customizations.utils import uni_print
from awscli.utils import is_a_tty, is_stdin_a_tty


class StorageChoice:
    """Where a sign-in's or store's credentials go (``decision``), for
    what ``kind`` of credentials and which profile (``profile_name``), as
    ``choose*()`` decided them. Nothing in it is written or shown as it is:
    config files and messages use the storage's value."""

    def __init__(
        self, storage, source, unsaved=False, kind=None, profile_name=None
    ):
        self.decision = StorageDecision(storage, source)
        self.kind = kind
        self.profile_name = profile_name
        # A new answer, not saved yet.
        self.unsaved = unsaved
        # The "Saved credential_storage = file" line, once a no is saved.
        # The command prints it last, after the sign-in succeeds.
        self.saved_line = None

    @property
    def storage(self):
        return self.decision.storage

    @property
    def source(self):
        return self.decision.source

    @property
    def uses_credential_daemon(self):
        return self.storage is Storage.DAEMON

    def __repr__(self):
        # The values, which is what config files and messages hold.
        return f'StorageChoice({self.storage.value!r}, {self.source.value!r})'


def known_decision(session, profile_name, environ=None):
    """The ``StorageDecision`` a profile already has, without asking:
    ``AWS_CREDENTIAL_STORAGE``, a saved answer, or ``credential_daemon``
    in the profile. Undecided for a profile with none of them. An SSO
    profile with no account and no role always gets files
    (``resolve_own_storage``).
    """
    decision = resolve_own_storage(session, profile_name, environ)
    if decision.storage is not None:
        return decision
    return decide_storage(
        None,
        None,
        None,
        CREDENTIAL_DAEMON_KEY in profile_config(session, profile_name),
    )


def stores_in_credential_daemon(session, profile_name, environ=None):
    """Whether a profile's new credentials go to the credential daemon
    without asking: ``AWS_CREDENTIAL_STORAGE`` or a saved answer says
    ``daemon``, or the profile has ``credential_daemon`` and no answer.

    A profile with no answer yet isn't one: the storage question checks
    the credential daemon itself, and files are used if it can't be.
    """
    profile_name = profile_or_default(profile_name)
    decision = known_decision(session, profile_name, environ)
    return decision.storage is Storage.DAEMON


_QUESTIONS = {
    CredentialKind.SESSION: (
        f'The {CREDENTIAL_DAEMON} is installed on this machine. Store this '
        f'profile\'s session there instead of in ~/.aws?\n'
        f'Tools built on older AWS SDKs won\'t be able to use this profile '
        f'(see docs for a workaround). [Y/n] '
    ),
    CredentialKind.STATIC_KEYS: (
        f'Store these keys in the {CREDENTIAL_DAEMON} instead of '
        '{credentials_file}?\n'
        f'Programs will get temporary credentials, so some things stop '
        f'working (IAM calls without MFA, long presigned URLs).\n'
        '{mfa_line}'
        f'Older AWS SDKs can\'t use this profile (see docs for a '
        f'workaround). [Y/n] '
    ),
}


def _in_a_terminal():
    """Whether a person can see the question and answer it: it's written
    to stdout and read from stdin, so both are terminals, as for aws
    configure's region prompt."""
    # For example, for a profile with nothing set,
    #   aws login --profile dev > out.txt
    # asks nothing and uses the files. Checking stdin alone would print the
    # question into out.txt and wait for an answer nobody sees.
    return is_stdin_a_tty() and is_a_tty()


class CredentialStorageChooser:
    """Decides whether a profile's new credentials go to the credential daemon
    or files.

    ``AWS_CREDENTIAL_STORAGE`` or the profile's saved answer decides. With
    neither, a terminal gets asked once, if the credential daemon is running.
    Otherwise the credentials go to files as before, and nothing is saved.

    ``choose()`` never saves the answer. Once the sign-in has worked or the
    keys are stored, the caller writes ``unsaved_values()`` with the rest of
    the profile in one update and calls ``mark_saved()``, or calls ``save()``.
    So a cancelled or failed sign-in, or a failed write, saves nothing. The
    caller prints a saved no with ``print_saved_line()`` at the end of a
    sign-in that succeeded.
    """

    def __init__(
        self,
        session,
        credential_daemon_client=None,
        config_writer=None,
        environ=None,
        is_tty=_in_a_terminal,
        ask=yes_no_choice,
    ):
        self._session = session
        self._credential_daemon_client = credential_daemon_client
        self._config_writer = config_writer or ConfigFileWriter()
        self._environ = environ
        self._is_tty = is_tty
        self._ask = ask
        self._credential_daemon_available = None
        # Why the last availability check failed, and the socket it dialed.
        self._unavailable = None
        self._notes_printed = False
        self._sso_without_role_printed = False

    def choose(self, profile_name, kind=CredentialKind.SESSION):
        # None is the default profile, as for the session with no profile
        # selected.
        profile_name = profile_or_default(profile_name)
        choice = self._known_choice(profile_name, kind)
        if choice is not None:
            return self._noted(choice)
        return self._ask_once(
            lambda: _question(self._session, profile_name, kind),
            kind,
            profile_name,
        )

    def _ask_once(self, question, kind, profile_name):
        """Ask ``question()`` in a terminal, if the credential daemon is
        there to answer for, or choose files without asking. A new answer
        isn't saved."""
        if not self._is_tty() or not self._answers_for_question():
            return StorageChoice(
                Storage.FILE,
                DecisionSource.DEFAULT,
                kind=kind,
                profile_name=profile_name,
            )
        # Each time the question is asked, not once per command: for
        # example, a chooser asked about profiles dev and ci says it before
        # each question.
        print_preview_notice()
        try:
            answer = self._ask(question(), default=True)
        except EOFError:
            # Ctrl-D stops the command as Ctrl-C does (exit 130), before
            # anything is signed in or saved. from None: the EOFError has
            # nothing to add.
            raise KeyboardInterrupt from None
        storage = Storage.DAEMON if answer else Storage.FILE
        return StorageChoice(
            storage,
            DecisionSource.NEW_ANSWER,
            unsaved=True,
            kind=kind,
            profile_name=profile_name,
        )

    def choose_without_asking(self, profile_name, kind=CredentialKind.SESSION):
        """The choice for a profile that has one, or files without asking.

        For a sign-in the credential daemon can't do, such as one on a port
        the credential daemon refuses. Nothing is saved and the credential
        daemon isn't called.
        """
        profile_name = profile_or_default(profile_name)
        choice = self._known_choice(profile_name, kind)
        if choice is not None:
            return choice
        return StorageChoice(
            Storage.FILE,
            DecisionSource.DEFAULT,
            kind=kind,
            profile_name=profile_name,
        )

    def _known_choice(self, profile_name, kind):
        decision = known_decision(self._session, profile_name, self._environ)
        if decision.storage is None:
            return None
        if decision.source is DecisionSource.SSO_WITHOUT_ROLE:
            self._print_sso_without_role(profile_name)
        return StorageChoice(*decision, kind=kind, profile_name=profile_name)

    def _print_sso_without_role(self, profile_name):
        # Once per command, where the question would otherwise be asked:
        # in a terminal with a credential daemon socket here. Scripts and
        # machines without the credential daemon see what they did before.
        if (
            self._sso_without_role_printed
            or not self._is_tty()
            or not self._socket_present()
        ):
            return
        self._sso_without_role_printed = True
        reason = sso_without_role_reason(
            profile_name, profile_config(self._session, profile_name)
        )
        uni_print(f'Note: {reason} They\'re stored in ~/.aws.\n', sys.stderr)

    def save(self, choice):
        """Save a new answer for a profile that hasn't been saved yet."""
        if not choice.unsaved:
            return
        self._save(choice.profile_name, choice.storage)
        self.mark_saved(choice)

    def unsaved_values(self, choice):
        """A new answer that hasn't been saved yet, as config values.

        A caller that creates the profile writes these in the same update
        as the rest of the profile, so a failed write leaves no profile
        with only the answer, then calls ``mark_saved()``.
        """
        if not choice.unsaved:
            return {}
        return {CREDENTIAL_STORAGE: choice.storage.value}

    def mark_saved(self, choice):
        """Record that the caller wrote ``unsaved_values()`` with the
        profile the choice is for."""
        if not choice.unsaved:
            return
        choice.unsaved = False
        if choice.storage is not Storage.FILE:
            return
        profile_name = choice.profile_name
        choice.saved_line = (
            f'Saved {CREDENTIAL_STORAGE} = {FILE} for '
            f"'{_shown(profile_name)}'. "
            f'{_later_hint(self._session, profile_name, choice.kind)}'
        )

    def print_saved_line(self, choice):
        """Print the line for a saved no, if there is one."""
        if choice.saved_line is not None:
            uni_print(f'{choice.saved_line}\n')
            choice.saved_line = None

    def is_credential_daemon_available(self):
        """Whether the credential daemon answers a credential/list."""
        if self._credential_daemon_available is None and (
            self._credential_daemon_client is None
            and not credential_daemon_runs_here()
        ):
            # As an AWS CLI without credential daemon support: nothing to
            # ask about, and nothing to say.
            self._credential_daemon_available = False
        if self._credential_daemon_available is None:
            client = self._credential_daemon_client
            if client is None:
                # The call timeout every other command's call has.
                client = CredentialDaemonClient()
            error = unavailable_error(client)
            self._credential_daemon_available = error is None
            if error is not None:
                self._unavailable = (
                    error,
                    getattr(client, "socket_path", None),
                )
        return self._credential_daemon_available

    def _answers_for_question(self):
        """is_credential_daemon_available(), for the opt-in question, in a
        terminal. Says so when the answer moves the profile to files
        quietly: an installed credential daemon that can't be used. A
        machine without the credential daemon gets no note, unless
        AWS_CREDENTIAL_DAEMON_SOCKET is set: the customer chose a socket,
        so they're told why it isn't used."""
        available = self.is_credential_daemon_available()
        variable = self._socket_variable()
        silent = not available and self._installed_but_silent()
        installed = available or silent or self._named_socket_failed(variable)
        if installed or variable is not None:
            self._print_notes()
        # A daemon that's here but can't be used, such as one stopped or
        # with an untrusted socket, keeps this profile's credentials in
        # files with a note instead of failing. No profile chose the daemon
        # yet and nothing was sent to it, so the command can still work as
        # it did before the daemon was installed.
        if not available and installed:
            error, _ = self._unavailable
            # Once per command.
            self._unavailable = None
            if not silent:
                # Nothing answers at the socket the customer set, such as
                # AWS_CREDENTIAL_DAEMON_SOCKET=/x/missing.sock: name it
                # rather than say the credential daemon isn't running.
                where = (
                    f'{DAEMON_SOCKET_ENV_VAR} is '
                    f'{strip_control_characters(variable)}, and the '
                    f'{CREDENTIAL_DAEMON} can\'t be used there'
                )
            else:
                where = f'The {CREDENTIAL_DAEMON} can\'t be used'
            # The error may quote the daemon's own text.
            uni_print(
                f'Note: {where}, so this command keeps credentials in '
                f'files, in plaintext: '
                f'{strip_control_characters(str(error))}\n',
                sys.stderr,
            )
        return available

    def _socket_variable(self):
        """AWS_CREDENTIAL_DAEMON_SOCKET, or None if it's unset or empty, or
        the credential daemon doesn't run here."""
        if not credential_daemon_runs_here():
            return None
        return socket_override()

    def _named_socket_failed(self, variable):
        # An absolute AWS_CREDENTIAL_DAEMON_SOCKET is the socket dialed,
        # so the failure names it, even with nothing there. A relative one
        # is ignored, and its discovery note says so.
        return (
            variable is not None
            and os.path.isabs(variable)
            and self._unavailable is not None
        )

    def _installed_but_silent(self):
        # A machine without the credential daemon sees the same output as
        # an AWS CLI without credential daemon support.
        if self._unavailable is None:
            return False
        return not detect_presence(*self._unavailable).absent

    def _noted(self, choice):
        """``choice``, after the discovery notes, for a profile that uses
        the credential daemon, in a terminal."""
        if choice.uses_credential_daemon and self._is_tty():
            self._print_notes()
        return choice

    def _print_notes(self):
        # Once per command. Only the CLI's sign-in commands say this; the
        # credential provider's lookup logs it at debug. Discovery reads
        # os.environ, so the notes do too.
        # A chooser given a client (tests) doesn't look the socket up.
        if self._notes_printed or self._credential_daemon_client is not None:
            return
        self._notes_printed = True
        for note in socket_discovery_notes():
            uni_print(f'Note: {note}\n', sys.stderr)

    def storage_line(self, choice):
        """The lines for a sign-in's summary that say where the
        credentials are stored, or None.

        For files there's a line only in a terminal with a credential daemon
        socket here, running or not, so scripts and machines without the
        credential daemon see the output of an AWS CLI without credential
        daemon support. After a
        saved no it reminds the customer how to switch;
        under ``AWS_CREDENTIAL_STORAGE`` it doesn't, because an admin chose.
        """
        if choice.uses_credential_daemon:
            return f'Credentials are stored in the {CREDENTIAL_DAEMON}.'
        if not self._is_tty() or choice.source in (
            DecisionSource.DEFAULT,
            # The note from choose() already said where and why.
            DecisionSource.SSO_WITHOUT_ROLE,
        ):
            return None
        plaintext = 'Credentials are stored in ~/.aws, in plaintext.'
        if choice.source is DecisionSource.NEW_ANSWER:
            return plaintext
        if not self._socket_present():
            return None
        if choice.source is DecisionSource.SAVED:
            switch_command = _switch_command(choice.profile_name)
            return (
                'Credentials are stored in ~/.aws, in plaintext '
                f'({CREDENTIAL_STORAGE} = {FILE}).\n'
                f'To use the {CREDENTIAL_DAEMON} from the next sign-in: '
                f'{switch_command}'
            )
        return plaintext

    def _socket_present(self):
        """Whether a credential daemon's socket is here, from the file
        system: a reminder to switch doesn't call the credential daemon,
        which could wait for the call timeout. A stopped credential
        daemon counts."""
        if self._credential_daemon_available:
            return True
        client = self._credential_daemon_client
        if client is not None:
            return socket_path_present(getattr(client, 'socket_path', None))
        if not credential_daemon_runs_here():
            return False
        return socket_path_present(default_socket_path())

    def _save(self, profile_name, storage):
        writer = self._config_writer or ConfigFileWriter()
        config_file = expanded_path(self._session, 'config_file')
        # The setting's value, never the Storage member.
        writer.update_config(
            {
                '__section__': profile_to_section(profile_name),
                CREDENTIAL_STORAGE: storage.value,
            },
            config_file,
        )

    def stores_in_credential_daemon(self, profile_name):
        """``stores_in_credential_daemon`` with this chooser's environment:
        whether the profile chose the credential daemon, so what the daemon
        can't take is refused rather than written to files."""
        return stores_in_credential_daemon(
            self._session, profile_name, self._environ
        )


def _question(session, profile_name, kind):
    if kind is CredentialKind.STATIC_KEYS:
        # Not expanded, so ~ shows as the customer wrote it.
        credentials_file = _shown(
            session.get_config_variable('credentials_file')
        )
        return _QUESTIONS[kind].format(
            credentials_file=credentials_file,
            mfa_line=_mfa_line(session, profile_name),
        )
    return _QUESTIONS[kind]


def _mfa_line(session, profile_name):
    # The credential daemon keeps the keys' MFA device and serves only MFA
    # sessions, so scripts using the profile stop working until a person signs
    # in.
    if not profile_config(session, profile_name).get('mfa_serial'):
        return ''
    return mfa_login_line('This profile has an MFA device', 'it')


def mfa_login_line(subject, them):
    """``subject`` (``mfa_serial``), such as ``'ci' has an MFA device``,
    gets no credentials until ``aws configure mfa-login``, said of
    ``them``: the credential daemon serves only MFA sessions for keys with
    a device."""
    return (
        f'{subject} (mfa_serial), so programs using {them} get no '
        f'credentials until you run \'aws configure mfa-login\', and '
        f'again after each MFA session ends.\n'
    )


def _later_hint(session, profile_name, kind):
    # Setting credential_storage moves nothing: a session moves at its
    # next sign-in, and keys already in ~/.aws/credentials stay there.
    if kind is CredentialKind.STATIC_KEYS:
        # Not expanded, so ~ shows as the customer wrote it.
        credentials_file = _shown(
            session.get_config_variable('credentials_file')
        )
        return f'The keys stay in {credentials_file}.'
    return (
        f'To use the {CREDENTIAL_DAEMON} from the next sign-in: '
        f'{_switch_command(profile_name)}'
    )


def _switch_command(profile_name):
    return (
        f'aws configure set {CREDENTIAL_STORAGE} {DAEMON} '
        f'--profile {_command_arg(profile_name)}'
    )


def _shown(name):
    """A name from a config file as messages show it, with its control
    characters removed."""
    return strip_control_characters(name)


def _command_arg(name):
    """A name from a config file in a command to paste: control
    characters removed, then quoted for the shell."""
    if not isinstance(name, str):
        return name
    return compat_shell_quote(strip_control_characters(name))
