# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""``aws configure credential-daemon install``, ``uninstall`` and ``link``."""

import os
import sys

from botocore.credential_daemon import (
    DAEMON_SOCKET_ENV_VAR,
    HOME_SOCKET_DIR_NAME,
    HOME_SOCKET_FILE_NAME,
    LINK_COMMAND,
    LINK_REMOVE_COMMAND,
    NO_SOCKET_TO_LINK_HINT,
    SHOWN_HOME_SOCKET,
    home_socket_path,
    own_socket_path,
    socket_override,
)
from botocore.exceptions import CredentialDaemonError

from awscli.botocore.credential_daemon import strip_control_characters
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
    refuse_platform_or_user,
    root_passwd_home,
    wait_until_running,
)
from awscli.customizations.configure.credential_daemon_install.links import (
    create_home_link,
    left_elsewhere,
    left_not_link,
    link_error,
    link_problem,
    remove_home_link,
    remove_own_link,
    replaced_entry,
    replaced_line,
    shown_link,
)
from awscli.customizations.configure.credential_daemon_install.linux import (
    LinuxInstall,
)
from awscli.customizations.configure.credential_daemon_install.macos import (
    MacOSInstall,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    CREDENTIAL_DAEMON_PRODUCT,
    RELEASE_REPO,
    ReleaseSource,
    check_release_version,
)
from awscli.customizations.credential_daemon.messages import (
    print_preview_notice,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CREDENTIAL_DAEMON,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.customizations.prompts import yes_no_choice
from awscli.customizations.utils import uni_print

_NEXT_STEPS = 'Your next sign-in will ask whether to store its session here.\n'

# Profiles should move back before the uninstall: moving back after
# uninstalling can't check the identity or clear aws-credential-daemon's
# copy. Only aws login sessions move at the next sign-in. A keys profile
# doesn't: for example, credential_daemon = keys.ci with credential_storage
# = file makes aws login refuse, and aws configure on that profile writes
# files while credential_daemon still wins. So the warning says to remove
# credential_daemon first.
_UNINSTALL_WARNING = (
    f'Profiles that use the {CREDENTIAL_DAEMON} stop working until they '
    'move back to files.\n'
    'To move them back before uninstalling, answer no and set '
    'credential_storage = file in each profile. Each profile moves at its '
    "next sign-in. A profile with access keys there doesn't move: remove "
    'its credential_daemon and enter the keys again with aws configure.\n'
)

_UNINSTALL_QUESTION = 'Continue? [y/N] '

_UNINSTALL_SYSTEM_QUESTION = (
    f'This removes it for every user on this machine. {_UNINSTALL_QUESTION}'
)


class InstallCredentialDaemonCommand(BasicCommand):
    NAME = 'install'
    # The last sentence names only what this release moves: an aws login
    # session at its next sign-in, and new profiles' keys. A profile whose
    # keys are in ~/.aws/credentials, such as [ci], stays there (aws
    # configure writes files for a profile that exists).
    DESCRIPTION = (
        'Downloads aws-credential-daemon from its GitHub '
        'releases, checks its signature, and installs it. Then it waits for '
        'it to answer, and links ``~/.aws/credential-daemon.sock``, where the '
        'AWS CLI and SDKs look for the credential daemon, to '
        'aws-credential-daemon\'s socket. On macOS it installs for the '
        'current user only; run it without sudo. On Linux it installs a '
        'system service for every user on this machine; run it with sudo: '
        '``sudo aws configure credential-daemon install``. It links for root '
        'and for the user who ran sudo. Other users run ``aws configure '
        'credential-daemon link``. '
        'Behind a proxy, keep its settings: ``sudo '
        '--preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,'
        'AWS_CA_BUNDLE aws configure credential-daemon install``, and pass '
        '``--ca-bundle`` with its CA file if it inspects TLS. TLS is always '
        'checked, so ``--no-verify-ssl`` is refused. '
        'Installing changes no profile: a profile\'s aws login session moves '
        'at its next sign-in, after asking, and aws configure asks for a new '
        'profile\'s access keys.'
    )
    SYNOPSIS = 'aws configure credential-daemon install'
    EXAMPLES = BasicCommand.FROM_FILE(
        'configure', 'credential-daemon', 'install', '_examples.rst'
    )
    ARG_TABLE = []

    def __init__(self, session, host=None):
        super().__init__(session)
        self.host = host or InstallHost()

    def _run_main(self, parsed_args, parsed_globals):
        # Before anything is downloaded or asked.
        refuse_platform_or_user('install', self.host)
        if getattr(parsed_globals, 'verify_ssl', None) is False:
            # Not ignored silently: behind a TLS-inspecting proxy the
            # download would fail with a certificate error, and the user
            # wouldn't learn the flag did nothing. A usage error (252).
            raise ParamValidationError(
                'install always checks TLS, so --no-verify-ssl isn\'t '
                'supported. Pass --ca-bundle for a proxy\'s CA. Nothing was '
                'downloaded.'
            )
        rc, install, version = self._install_system(parsed_globals)
        if rc:
            return rc
        if self.host.system == 'linux':
            return self._install_as_root(install, version)
        # macOS: the per-user install, then the user's link.
        target = self.host.own_socket or own_socket_path(
            self.host.environ, 'darwin'
        )
        if target is None:
            uni_print(
                f'HOME isn\'t an absolute path, so {SHOWN_HOME_SOCKET} '
                'wasn\'t created.\n',
                sys.stderr,
            )
            return 1
        wait_until_running(self.host, target, install, version)
        if not self._link(self.host.environ, target):
            return 1
        uni_print(_NEXT_STEPS)
        return 0

    def _install_as_root(self, install, version):
        """Linux as root, such as ``sudo aws configure credential-daemon
        install``: once the service answers, a link in root's own ~/.aws,
        and, under sudo, the link of the user who ran sudo, made as that
        user. A link the caller needs that couldn't be made exits 1, as on
        macOS."""
        target = self._linux_socket()
        wait_until_running(self.host, target, install, version)
        # Root's home from the passwd entry: under sudo, HOME can still be
        # the user's, and a link root makes there would be root's, not
        # theirs.
        environ = dict(self.host.environ)
        environ['HOME'] = self.host.root_home or root_passwd_home()
        sudo_user = self.host.environ.get('SUDO_USER')
        if not sudo_user or sudo_user == 'root':
            # Root is the caller, so its link is the one it asked for.
            if not self._link(environ, target):
                return 1
            uni_print(
                'Each user who uses the credential daemon runs, without '
                f'sudo: {LINK_COMMAND}\n'
            )
        else:
            # Under sudo, root's own link is a note: the link the caller
            # needs is their own, so a failure of root's doesn't change the
            # exit code. link refuses to run under sudo, so there's no
            # command to suggest for root's.
            self._link(environ, target, suggest_link=False)
            if not self._link_sudo_user(sudo_user):
                uni_print(
                    f'Once that\'s fixed, run, without sudo: {LINK_COMMAND}\n',
                    sys.stderr,
                )
                return 1
        uni_print(_NEXT_STEPS)
        return 0

    def _link_sudo_user(self, name):
        """Link the ~/.aws/credential-daemon.sock of the user who ran sudo,
        as that user, from their passwd entry, as link does. Returns whether
        it's linked; prints why not."""
        try:
            entry = self.host.user_entry(name)
        except KeyError:
            uni_print(
                f'No passwd entry for {strip_control_characters(name)}, so '
                f'their {SHOWN_HOME_SOCKET} wasn\'t created.\n',
                sys.stderr,
            )
            return False
        home = entry.pw_dir or ''
        shown = strip_control_characters(
            os.path.join(home, HOME_SOCKET_DIR_NAME, HOME_SOCKET_FILE_NAME)
        )
        if not os.path.isabs(home):
            uni_print(
                f'{shown} wasn\'t created: the home folder isn\'t an '
                'absolute path.\n',
                sys.stderr,
            )
            return False
        target = self._linux_socket()
        try:
            link, replaced = self.host.link_as(entry, target)
        except (CredentialDaemonError, ConfigurationError, OSError) as e:
            uni_print(
                f'{shown} wasn\'t created: {link_error(e)}\n', sys.stderr
            )
            return False
        uni_print(f'Linked {link} to {strip_control_characters(target)}.\n')
        uni_print(replaced_line(link, replaced))
        return True

    def _linux_socket(self):
        return self.host.own_socket or own_socket_path({}, 'linux')

    def _link(self, environ, target, suggest_link=True):
        """Link ``~/.aws/credential-daemon.sock`` under ``environ``'s HOME
        to ``target``, as link does, and say so. Prints why not, and how to
        do it later with ``suggest_link``, and returns False, if it
        can't."""
        replaced = replaced_entry(environ, target)
        try:
            link = create_home_link(target, environ, remedy=None)
        except (CredentialDaemonError, ConfigurationError, OSError) as e:
            later = ''
            if suggest_link:
                later = f'Once that\'s fixed, run: {LINK_COMMAND}\n'
            uni_print(
                f'{self._shown_link(environ)} wasn\'t created: '
                f'{link_error(e)}\n{later}',
                sys.stderr,
            )
            return False
        uni_print(f'Linked {link} to {strip_control_characters(target)}.\n')
        uni_print(replaced_line(link, replaced))
        if not _under_sudo(self.host):
            # Under sudo the variable here is what sudo kept, not
            # necessarily what the caller's shell uses, so no note.
            uni_print(_socket_override_note(self.host.environ), sys.stderr)
        return True

    def _shown_link(self, environ=None):
        return shown_link(self.host.environ if environ is None else environ)

    def _install_system(self, parsed_globals):
        """Install aws-credential-daemon: the system service on Linux (as
        root), the per-user package on macOS. Returns the exit code, the
        install and the release's version."""
        host = self.host
        if host.system == 'darwin':
            install = MacOSInstall(host)
        else:
            install = LinuxInstall(host)
        install.before_download()
        source = ReleaseSource(host, verify=self._ca_bundle(parsed_globals))
        release = source.latest_release()
        # Before the download: no older release than the minimum, and no
        # downgrade of the installed one.
        check_release_version(release.version, install.installed_version())
        # After the refusals of this machine and this release (such as no
        # gpg, or a downgrade), so a refused install doesn't print it. A
        # download or signature check that fails can still follow.
        print_preview_notice()
        uni_print(install.reinstall_note())
        uni_print(
            f'Downloading {CREDENTIAL_DAEMON_PRODUCT} from '
            f'github.com/{RELEASE_REPO}...\n'
        )
        return install.install(source, release), install, release.version

    def _ca_bundle(self, parsed_globals):
        """The CA bundle to download with: --ca-bundle, else AWS_CA_BUNDLE
        or the profile's ca_bundle.

        --no-verify-ssl is refused before this (see _run_main): install
        runs as root and installs a program that holds secrets, so TLS is
        always checked, as with a proxy that inspects TLS and whose CA is
        given with --ca-bundle.
        """
        verify = getattr(parsed_globals, 'verify_ssl', None)
        if isinstance(verify, str):
            return verify
        bundle = self._session.get_config_variable('ca_bundle')
        return bundle if isinstance(bundle, str) else None


def _under_sudo(host):
    """Whether this runs as root under sudo for another user."""
    return host.runs_as_root() and host.environ.get('SUDO_USER') not in (
        None,
        '',
        'root',
    )


def _socket_override_note(environ):
    """A note when AWS_CREDENTIAL_DAEMON_SOCKET is set, since the CLI
    then dials that socket, not the link, or ''."""
    if not socket_override(environ):
        return ''
    return (
        f'Note: {DAEMON_SOCKET_ENV_VAR} is set, so the AWS CLI uses that '
        'socket, not this link.\n'
    )


class UninstallCredentialDaemonCommand(BasicCommand):
    NAME = 'uninstall'
    # As in _UNINSTALL_WARNING: a keys profile doesn't move at a sign-in.
    DESCRIPTION = (
        'Uninstalls the aws-credential-daemon that ``aws configure '
        'credential-daemon install`` installed: runs its own uninstaller. '
        'On macOS it removes the current user\'s install; run it without '
        'sudo. The app stays, as with aws-credential-daemon\'s own '
        'uninstall. On Linux it removes the system service and the files '
        'the install added, for every user on this machine; run it with '
        'sudo: ``sudo aws configure credential-daemon uninstall``. It '
        'removes any aws-credential-daemon system service that runs its '
        'staged copy, however it was installed. It also removes the '
        '``~/.aws/credential-daemon.sock`` link to aws-credential-daemon\'s '
        'socket: yours on macOS; on Linux, root\'s and that of the user who '
        'ran sudo. Other users remove theirs with ``aws configure '
        'credential-daemon link --remove``. '
        'The credential daemon\'s saved sign-ins and keys stay on this '
        'machine, so reinstalling brings them back, and nothing else in '
        '~/.aws changes. Profiles that use the credential daemon stop '
        'working until they move back to files, so it asks first. '
        'A profile with access keys there doesn\'t move: remove its '
        'credential_daemon and enter the keys again with aws configure.'
    )
    SYNOPSIS = 'aws configure credential-daemon uninstall [--yes]'
    EXAMPLES = BasicCommand.FROM_FILE(
        'configure', 'credential-daemon', 'uninstall', '_examples.rst'
    )
    ARG_TABLE = [
        {
            'name': 'yes',
            'action': 'store_true',
            'default': False,
            'help_text': 'Uninstalls without asking for confirmation.',
        },
    ]

    def __init__(self, session, host=None, ask=None):
        super().__init__(session)
        self.host = host or InstallHost()
        self._ask = ask or yes_no_choice

    def _run_main(self, parsed_args, parsed_globals):
        # Before anything is read, asked or changed.
        refuse_platform_or_user('uninstall', self.host)
        if self.host.system == 'darwin':
            install = MacOSInstall(self.host)
        else:
            install = LinuxInstall(self.host)
        if not install.is_installed():
            uni_print(
                f'{CREDENTIAL_DAEMON_PRODUCT} isn\'t installed{install.whose}.\n'
            )
            # A link left by another uninstaller, or by hand.
            for _, line in self._remove_links():
                uni_print(line)
            return 0
        # Check what will run before asking, so a refusal changes nothing.
        install.check_uninstaller()
        if not self._confirm(parsed_args.yes):
            uni_print('Nothing was uninstalled.\n')
            return 1
        install.run_uninstaller()
        # On macOS aws-credential-daemon's uninstaller is all that runs; only
        # Linux removes files itself and can leave some.
        left = install.remove_files() if self.host.system == 'linux' else []
        notes = install.notes()
        links = self._remove_links()
        if left:
            lines = ''.join(
                f'  {strip_control_characters(path)}: '
                f'{strip_control_characters(reason)}\n'
                for path, reason in left
            )
            uni_print(
                f'{CREDENTIAL_DAEMON_PRODUCT} wasn\'t fully '
                'uninstalled. These are still on '
                f'this machine:\n{lines}Remove them by hand.\n',
                sys.stderr,
            )
            for _, line in links:
                uni_print(line)
            return 1
        if any(removed for removed, _ in links):
            in_aws = ' Nothing else in ~/.aws was changed.'
        else:
            in_aws = ' Nothing in ~/.aws was changed.'
        uni_print(
            f'Removed {CREDENTIAL_DAEMON_PRODUCT}{install.whose}. '
            'The credential daemon\'s saved sign-ins and keys stay on this '
            f'machine, so reinstalling brings them back.{in_aws}\n'
        )
        for _, line in links:
            uni_print(line)
        for note in notes:
            uni_print(note)
        return 0

    def _remove_links(self):
        """Remove the ~/.aws/credential-daemon.sock links to
        aws-credential-daemon's socket that this uninstall can: the
        caller's on macOS; root's and, under sudo, the invoking user's on
        Linux. Returns ``(removed, line)`` for each one found."""
        if self.host.system == 'darwin':
            environ = self.host.environ
            if self.host.home is not None:
                environ = dict(environ, HOME=self.host.home)
            target = self.host.own_socket or own_socket_path(environ, 'darwin')
            link = home_socket_path(environ)
            if link is None or target is None:
                return []
            # The caller's own link, removed as link --remove does. Only
            # root, removing it in its own process, checks the folder.
            uid = os.geteuid()
            result = remove_own_link(link, target, uid, check_folder=uid == 0)
            return [] if result is None else [result]
        target = self.host.own_socket or own_socket_path({}, 'linux')
        root_home = self.host.root_home or root_passwd_home()
        results = [
            remove_own_link(
                os.path.join(
                    root_home, HOME_SOCKET_DIR_NAME, HOME_SOCKET_FILE_NAME
                ),
                target,
                0,
                check_folder=True,
                # Root's link: under sudo, link refuses to run, so there's
                # no command to give; as root itself, link --remove works.
                remedy=None if _under_sudo(self.host) else LINK_REMOVE_COMMAND,
            )
        ]
        sudo_user = self.host.environ.get('SUDO_USER')
        if sudo_user and sudo_user != 'root':
            results.append(self._remove_sudo_users_link(sudo_user, target))
        return [result for result in results if result is not None]

    def _remove_sudo_users_link(self, name, target):
        """Remove the link of the user who ran sudo, as that user, only if
        it's their link to ``target``. The unlink runs as that user, so
        root never removes anything they couldn't."""
        later = (
            False,
            f'To remove your link, run without sudo: {LINK_REMOVE_COMMAND}\n',
        )
        try:
            entry = self.host.user_entry(name)
        except KeyError:
            return later
        if not os.path.isabs(entry.pw_dir or ''):
            return later
        link = os.path.join(
            entry.pw_dir, HOME_SOCKET_DIR_NAME, HOME_SOCKET_FILE_NAME
        )
        problem = link_problem(link, target, entry.pw_uid)
        if problem == 'missing':
            return None
        if problem == 'elsewhere':
            return left_elsewhere(link)
        if problem == 'not_link':
            return left_not_link(link)
        if problem is not None:
            return later
        try:
            self.host.unlink_as(link, entry.pw_uid, entry.pw_gid)
        except OSError:
            return later
        return True, f'Removed {strip_control_characters(link)}.\n'

    def _confirm(self, yes):
        if yes:
            return True
        if not self.host.is_tty():
            raise ParamValidationError(
                f'Uninstalling {CREDENTIAL_DAEMON_PRODUCT} stops '
                'profiles that use it from '
                f'working. Run with --yes to uninstall without a terminal.'
            )
        uni_print(_UNINSTALL_WARNING, sys.stderr)
        if self.host.system == 'darwin':
            question = _UNINSTALL_QUESTION
        else:
            question = _UNINSTALL_SYSTEM_QUESTION
        return self._ask(question, default=False)


class LinkCredentialDaemonCommand(BasicCommand):
    NAME = 'link'
    DESCRIPTION = (
        'Links ``~/.aws/credential-daemon.sock``, where the AWS CLI and SDKs '
        'look for the credential daemon, to aws-credential-daemon\'s own '
        'socket: the per-user one on macOS, the system one on Linux. '
        '``aws configure credential-daemon install`` links for the user who '
        'installs; other users on the machine run this, without sudo. It '
        'checks the socket before linking, as commands that send the '
        'credential daemon secrets do, and sends nothing. With '
        '``--remove``, it removes the link. To use another credential '
        'daemon, link its socket yourself, or set '
        '``AWS_CREDENTIAL_DAEMON_SOCKET``.'
    )
    SYNOPSIS = 'aws configure credential-daemon link [--remove]'
    EXAMPLES = BasicCommand.FROM_FILE(
        'configure', 'credential-daemon', 'link', '_examples.rst'
    )
    ARG_TABLE = [
        {
            'name': 'remove',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Removes ``~/.aws/credential-daemon.sock`` if it\'s a link.'
            ),
        },
    ]

    def __init__(self, session, host=None):
        super().__init__(session)
        self.host = host or InstallHost()

    def _run_main(self, parsed_args, parsed_globals):
        if self.host.system not in ('linux', 'darwin'):
            raise ConfigurationError(
                f'{CREDENTIAL_DAEMON_PRODUCT} doesn\'t run on this platform.'
            )
        is_root = self.host.is_root
        if is_root is None:
            is_root = os.geteuid() == 0
        if is_root and self.host.environ.get('SUDO_USER', 'root') != 'root':
            # The link is the user's, and must be owned by them.
            command = (
                LINK_REMOVE_COMMAND if parsed_args.remove else LINK_COMMAND
            )
            raise ConfigurationError(
                'The link must be owned by you, not root, so nothing was '
                f'changed. Run this without sudo: {command}'
            )
        environ = self.host.environ
        if is_root:
            # Root links its own ~/.aws only, from its passwd entry: after
            # su, HOME can still be another user's, and a link root makes
            # there would be root's, not theirs.
            environ = dict(
                environ, HOME=self.host.root_home or root_passwd_home()
            )
        if parsed_args.remove:
            try:
                removed = remove_home_link(environ)
            except OSError as e:
                raise ConfigurationError(
                    f'{shown_link(environ)} wasn\'t removed: '
                    f'{link_error(e)}'
                ) from e
            if removed is None:
                uni_print(f'There\'s no {shown_link(environ)} to remove.\n')
            else:
                uni_print(f'Removed {removed}.\n')
            return 0
        target = self.host.own_socket or own_socket_path(
            environ, self.host.system
        )
        if target is None:
            raise ConfigurationError(
                f'HOME isn\'t an absolute path, so there\'s no '
                f'{SHOWN_HOME_SOCKET} to link.'
            )
        if not os.path.exists(target):
            raise ConfigurationError(
                f'No {CREDENTIAL_DAEMON_PRODUCT} socket is at '
                f'{strip_control_characters(target)}, so nothing was linked. '
                f'{NO_SOCKET_TO_LINK_HINT}'
            )
        replaced = replaced_entry(environ, target)
        try:
            link = create_home_link(target, environ)
        except (CredentialDaemonError, OSError) as e:
            raise ConfigurationError(
                f'{shown_link(environ)} wasn\'t linked: {link_error(e)}'
            ) from e
        uni_print(f'Linked {link} to {strip_control_characters(target)}.\n')
        uni_print(replaced_line(link, replaced))
        uni_print(_socket_override_note(self.host.environ), sys.stderr)
        return 0


class ConfigureCredentialDaemonCommand(BasicCommand):
    NAME = 'credential-daemon'
    DESCRIPTION = (
        'Manages aws-credential-daemon, which keeps aws login sessions '
        'sealed on this machine instead of in plaintext files.'
    )
    SYNOPSIS = 'aws configure credential-daemon <Command> [<Arg> ...]'
    SUBCOMMANDS = [
        {'name': 'install', 'command_class': InstallCredentialDaemonCommand},
        {
            'name': 'uninstall',
            'command_class': UninstallCredentialDaemonCommand,
        },
        {'name': 'link', 'command_class': LinkCredentialDaemonCommand},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            self._raise_usage_error()
