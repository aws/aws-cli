# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What ``install``, ``uninstall`` and ``link`` share: the host they run on,
and its test seams."""

import math
import os
import platform
import re
import stat
import subprocess
import sys
import time

from botocore.credential_daemon.client import CredentialDaemonClient
from botocore.exceptions import (
    CredentialDaemonConnectionError,
    CredentialDaemonError,
    CredentialDaemonProtocolError,
    CredentialDaemonUntrustedSocketError,
)
from botocore.utils import original_ld_library_path

from awscli.botocore.credential_daemon import strip_control_characters
from awscli.customizations.configure.credential_daemon_install.links import (
    LINK_COMMAND,
    link_as_user,
    unlink_as_user,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    CREDENTIAL_DAEMON_PRODUCT,
    format_version,
    parse_version,
    printable_lines,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty

# Linux's ST_NOEXEC (mount flag "noexec"). Python defines os.ST_NOEXEC only
# on Linux, so reading it directly raises AttributeError on macOS. 8 is the
# value in <sys/statvfs.h> on Linux; only the Linux install path reads it.
ST_NOEXEC = getattr(os, 'ST_NOEXEC', 8)

# How long install waits for the installed daemon to answer system/health.
_SOCKET_WAIT_SECONDS = 30


_HEALTH_POLL_SECONDS = 0.5


# The longest one system/health call may take while install waits.
_HEALTH_CALL_SECONDS = 5


# Where the Linux install downloads and runs aws-credential-daemon's installer
# from: the first of these that isn't mounted noexec. aws-credential-daemon
# stages its own root-owned copy only when the program it's run from could be
# replaced by someone other than root, so the folder must be sticky and
# writable by everyone, as /tmp and /var/tmp are.
LINUX_TEMP_ROOTS = ('/tmp', '/var/tmp')


LINUX_ARCHITECTURES = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'aarch64'}


# The macOS release is built for Apple silicon only.
MACOS_ARCHITECTURES = ('arm64',)


_SYSCTL = '/usr/sbin/sysctl'


def _macos_root_refusal(subcommand):
    return (
        f'On macOS {CREDENTIAL_DAEMON_PRODUCT} installs for one user. Run this '
        f'without sudo: aws configure credential-daemon {subcommand}'
    )


class _HealthClient(CredentialDaemonClient):
    def health(self):
        return self._call('system/health')


def check_daemon_health(path, timeout):
    """Send ``system/health``, which needs no authorization, to the socket
    at ``path``, with the checks a command that sends secrets runs.

    Unlike a bare connect, it shows the daemon itself answers, not only
    that systemd or launchd holds its socket, and the daemon doesn't log
    a peer that closed before it could be read. Returns the reply, such
    as ``{'protocol': 1, 'version': '0.2.0'}``; raises what a call would.
    """
    return _HealthClient(socket_path=path, timeout=timeout).health()


def _not_answering(error):
    """Whether a system/health error means the daemon isn't answering yet,
    so install waits on: nothing listens, the call timed out, or the
    connection closed or sent something unreadable (a service that's
    starting, or crashing). A socket that fails its checks is answering:
    waiting won't fix it."""
    if isinstance(error, CredentialDaemonUntrustedSocketError):
        return False
    return isinstance(
        error, (CredentialDaemonConnectionError, CredentialDaemonProtocolError)
    )


def wait_until_running(host, target, install, version):
    """Wait, up to ``host.socket_wait`` seconds, for the installed daemon,
    the release at ``version``, to answer system/health on ``target``.
    Raises a ConfigurationError (253), with the remedy, if it doesn't.

    The installers can exit 0 for a daemon that never runs: for example,
    without a tss group credsd.service crash-loops on the TPM, and a macOS
    package whose LaunchAgent couldn't be registered only logs it. An
    answer counts only from protocol 1 and the release's version: credsd's
    installer restarts the service only on a best-effort basis, so after an
    upgrade the old daemon can be the one that answers. An error that isn't
    "not answering" (such as a socket that fails its checks) ends the wait,
    and the link's check reports it.
    """
    deadline = host.clock() + host.socket_wait
    error = None
    # The last reply that wasn't the release, if the last try got one.
    answered = _NO_REPLY
    while True:
        remaining = max(deadline - host.clock(), 0)
        try:
            # Whole seconds, rounded up: the client's timeout error repeats
            # this number in the "isn't running" message, so a fraction
            # would print as 2.474012944032438. The last try still gets a
            # second: a timeout of 0 would fail before connecting.
            timeout = min(_HEALTH_CALL_SECONDS, math.ceil(remaining)) or 1
            reply = host.health(target, timeout=timeout)
        except CredentialDaemonError as e:
            if not _not_answering(e):
                return
            error, answered = strip_control_characters(str(e)), _NO_REPLY
        else:
            if _is_release(reply, version):
                return
            error, answered = None, reply
        if host.clock() >= deadline:
            break
        host.sleep(_HEALTH_POLL_SECONDS)
    shown = strip_control_characters(target)
    expected = f'{CREDENTIAL_DAEMON_PRODUCT} {format_version(version)}'
    if answered is not _NO_REPLY:
        # A daemon runs, but not the release just installed.
        raise ConfigurationError(
            f'{expected} was installed, but for {host.socket_wait} seconds '
            f'{shown} answered as {_shown_reply(answered)}.\n'
            f'{_wrong_daemon_remedy(host, answered)}'
        )
    raise ConfigurationError(
        f'{CREDENTIAL_DAEMON_PRODUCT} was installed but isn\'t running: '
        f'{shown} didn\'t answer as {expected} within {host.socket_wait} '
        f'seconds (last error: {error}).\n{_not_running_remedy(host, install)}'
    )


_NO_REPLY = object()


def _is_release(reply, version):
    """Whether a system/health reply is from the release just installed:
    protocol 1 and ``version``."""
    if not isinstance(reply, dict):
        return False
    answered = reply.get('version')
    return (
        reply.get('protocol') == 1
        and isinstance(answered, str)
        and parse_version(answered) == version
    )


def _shown_reply(reply):
    """A system/health reply that isn't the release, as words."""
    if not isinstance(reply, dict):
        return 'something that isn\'t a system/health reply'
    answered = reply.get('version')
    if isinstance(answered, str):
        who = (
            f'{CREDENTIAL_DAEMON_PRODUCT} {strip_control_characters(answered)}'
        )
    else:
        who = f'an unknown version of {CREDENTIAL_DAEMON_PRODUCT}'
    protocol = strip_control_characters(str(reply.get('protocol')))
    return f'{who} (protocol {protocol})'


def _wrong_daemon_remedy(host, reply):
    """What to do when a daemon answers, but not the release installed."""
    if isinstance(reply, dict) and reply.get('protocol') not in (1, None):
        return (
            'This AWS CLI supports only protocol 1. Update the AWS CLI, then '
            f'run: {LINK_COMMAND}'
        )
    if host.system == 'darwin':
        # The earlier daemon may still be running after an upgrade.
        return (
            'Restart it with: launchctl kickstart -k '
            f'gui/{os.getuid()}/com.amazon.aws.credsd.daemon\n'
            f'Then run: {LINK_COMMAND}'
        )
    # credsd's installer restarts the service only on a best-effort basis,
    # so after an upgrade the earlier daemon can still be the one running.
    return (
        'Restart it with: sudo systemctl restart credsd.service\n'
        'Then run again:\n'
        f'  {sudo_command("install")}'
    )


def _not_running_remedy(host, install):
    """What to do when the installed daemon doesn't answer."""
    if host.system == 'darwin' and not install.is_installed():
        # The package's postinstall logs this and exits 0.
        return (
            'Its LaunchAgent wasn\'t registered. In a terminal, run: '
            f'~/.local/bin/credsd install --user\nThen run: {LINK_COMMAND}'
        )
    if host.system == 'darwin':
        return (
            'For details, run: launchctl print '
            f'gui/{os.getuid()}/com.amazon.aws.credsd.daemon\n'
            f'Once it answers, run: {LINK_COMMAND}'
        )
    # credsd.service's unit is written at install, so a fix (such as
    # adding the tss group) takes effect only when install runs again,
    # which links too.
    return (
        'Fix what journalctl -u credsd or sudo tail '
        '/var/log/credsd/credsd.log shows, then run again:\n'
        f'  {sudo_command("install")}'
    )


# The environment of every program install, uninstall and link run on Linux,
# where they run as root. Nothing comes from the caller's environment: under
# sudo -E, for example, CREDSD_DATA_DIR would point credsd's installer at the
# user's folder, LD_LIBRARY_PATH (set by the official installer's bundled
# Python) would load the CLI's own copies of libz into gpg and systemctl, and
# a PATH of the user's could put another program first.
_LINUX_CHILD_PATH = '/usr/sbin:/usr/bin:/sbin:/bin'


def _run(command, check=True, timeout=None, env=None):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
        env=env,
    )


def _user_child_environ(environ):
    """``environ`` for a program the CLI runs as the user (macOS): as
    botocore runs credential_process and the pager, without the bundled
    Python's LD_LIBRARY_PATH."""
    environ = dict(environ)
    with original_ld_library_path(environ):
        return dict(environ)


def _not_run(command, error):
    """The error for a program the install couldn't start."""
    program = strip_control_characters(command[0])
    reason = strip_control_characters(error.strerror or str(error))
    return ConfigurationError(
        f'Couldn\'t run {program} ({reason}), so '
        f'{CREDENTIAL_DAEMON_PRODUCT} wasn\'t installed.'
    )


def error_detail(e):
    """A failed command's error output, without escape sequences: its
    stderr, else its stdout, else its exit code."""
    for detail in (
        getattr(e, 'stderr', None),
        getattr(e, 'stdout', None),
        getattr(e, 'strerror', None),
    ):
        shown = printable_lines(detail if isinstance(detail, str) else '')
        if shown:
            return shown
    returncode = getattr(e, 'returncode', None)
    if returncode is not None:
        return f'exit {returncode}'
    return strip_control_characters(str(e))


def _passwd_entry(name):
    """``pwd.getpwnam(name)``. ``pwd`` is imported here, not at the top,
    because it doesn't exist on Windows, and the CLI imports this module
    for every ``aws configure`` command."""
    import pwd

    return pwd.getpwnam(name)


def root_passwd_home():
    """Root's home folder from its passwd entry. See ``_passwd_entry``."""
    import pwd

    return pwd.getpwuid(0).pw_dir


def _host_machine(system):
    """The machine to pick a release for. On a Mac with Apple silicon it's
    arm64 even when Python runs under Rosetta, where platform.machine()
    says x86_64."""
    machine = platform.machine()
    if system != 'darwin' or machine in MACOS_ARCHITECTURES:
        return machine
    try:
        reply = subprocess.run(
            [_SYSCTL, '-n', 'hw.optional.arm64'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            env=_user_child_environ(os.environ),
        )
    except (OSError, subprocess.SubprocessError):
        return machine
    # Intel Macs don't have the key, so sysctl fails there.
    if reply.returncode == 0 and reply.stdout.strip() == '1':
        return 'arm64'
    return machine


def install_supported(system=None, machine=None):
    """Whether ``install`` has a release for this machine: macOS on arm64,
    or Linux on x86_64 or arm64.

    It doesn't check what else the release needs from the machine, such
    as a TPM on Linux: aws-credential-daemon's installer does, and its
    failure is reported as it says. A check of its own here would have
    to follow every release's needs, and could refuse a host the
    installer accepts. Runs at most
    sysctl (macOS when platform.machine() isn't arm64), and never the
    network.
    """
    system = system or sys.platform
    machine = machine or _host_machine(system)
    if system == 'darwin':
        return machine in MACOS_ARCHITECTURES
    return system == 'linux' and machine in LINUX_ARCHITECTURES


def refuse_platform_or_user(command, host):
    """Install and uninstall run only on Linux and macOS: as root on Linux,
    and never as root on macOS. Raises the refusal before anything is
    downloaded, asked or changed."""
    if host.system not in ('linux', 'darwin'):
        raise ConfigurationError(
            f'{CREDENTIAL_DAEMON_PRODUCT} doesn\'t run on this platform.'
        )
    is_root = host.runs_as_root()
    if host.system == 'darwin' and is_root:
        # aws-credential-daemon's signed .pkg installs only for one user (its
        # system service exists only for builds from source). Under sudo, ~
        # can still be the user's home, so the per-user `credsd`, a file the
        # user can change, would run as root.
        raise ConfigurationError(_macos_root_refusal(command))
    if host.system == 'linux' and not is_root:
        # The CLI never runs itself as root: the customer runs sudo, as
        # with aws update on a system install. A self-run sudo would run
        # an aws, and a Python, that the user may be able to change.
        if command == 'install':
            needs_root = (
                f'Installing {CREDENTIAL_DAEMON_PRODUCT} as a system service '
                'requires root, so nothing was downloaded or changed.'
            )
        else:
            needs_root = (
                f'Uninstalling {CREDENTIAL_DAEMON_PRODUCT}\'s system service '
                'requires root, so nothing was changed.'
            )
        raise ConfigurationError(
            f'{needs_root} Run:\n  {sudo_command(command)}'
        )


def sudo_command(subcommand):
    """The command a Linux "needs root" message prints, such as ``sudo aws
    configure credential-daemon install``. It's always plain ``aws``: the
    CLI doesn't work out which aws sudo would run (root's PATH, a venv,
    the official installer's versioned path)."""
    return f'sudo aws configure credential-daemon {subcommand}'


# The proxy hint's command: sudo drops the proxy's settings and the CA
# bundle (env_reset) unless they're kept.
_PROXY_SUDO_INSTALL = (
    'sudo --preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,'
    'AWS_CA_BUNDLE aws configure credential-daemon install'
)


def root_only_problem(path, root='/', trusted_uid=0, trusted_gids=(0,)):
    """(kind, checked path, detail) if users other than root could
    have written path, or None. kind is 'error', 'writable',
    'symlink' or 'not-regular'.

    Every folder from path's up to ``root`` is checked, not only its
    own: a user who can rename any of them can swap in another program.
    None may be a symbolic link, and none may be writable by others, or
    by a group other than one in ``trusted_gids``.
    """
    try:
        st = os.lstat(path)
    except OSError as e:
        return 'error', path, e.strerror
    if not stat.S_ISREG(st.st_mode):
        return 'not-regular', path, None
    if st.st_uid != trusted_uid or st.st_mode & 0o022:
        return 'writable', path, None
    root = os.path.normpath(root)
    folder = os.path.dirname(os.path.normpath(path))
    while True:
        try:
            st = os.lstat(folder)
        except OSError as e:
            return 'error', folder, e.strerror
        if stat.S_ISLNK(st.st_mode):
            return 'symlink', folder, None
        if (
            st.st_uid != trusted_uid
            or st.st_mode & 0o002
            or (st.st_mode & 0o020 and st.st_gid not in trusted_gids)
        ):
            return 'writable', folder, None
        parent = os.path.dirname(folder)
        if folder == root or parent == folder:
            return None
        folder = parent


def _temp_root_problem(path):
    """Why the installer can't run from a folder under path, or None."""
    try:
        if os.statvfs(path).f_flag & ST_NOEXEC:
            return 'noexec'
        st = os.stat(path)
    except OSError:
        return 'missing'
    # Sticky and writable by everyone, so aws-credential-daemon stages
    # its root-owned copy (see LINUX_TEMP_ROOTS).
    if not (
        stat.S_ISDIR(st.st_mode)
        and st.st_mode & stat.S_ISVTX
        and st.st_mode & 0o002
    ):
        return 'not-shared'
    return None


# credsd's installer's warning that it staged a root-owned copy of the
# program it was run from. Install always runs it from a temp folder others
# can write, so it always stages: the warning would print on every install,
# though staging is what install wants.
_STAGING_WARNING = re.compile(
    r'warning: .* can be modified by a non-root user\b', re.IGNORECASE
)


# A warning that tells the user to run credsd's own installer again.
_NAMES_CREDSD_INSTALL = '`credsd install`'


def installer_warnings(stderr):
    """The installer's ``warning:`` lines, each with its indented
    continuation lines, without escape sequences and without the staging
    warning (see _STAGING_WARNING)."""
    kept = []
    keep = False
    for raw in (stderr or '').split('\n'):
        line = strip_control_characters(raw).rstrip()
        if line.lower().startswith('warning:'):
            keep = not _STAGING_WARNING.match(line)
            if keep:
                kept.append(line)
        elif keep and line[:1].isspace() and line.strip():
            kept.append(line)
        else:
            keep = False
    return kept


class InstallHost:
    """The platform, environment and test seams that ``install``,
    ``uninstall`` and ``link`` share.

    Made with ``InstallHost()`` for a real run. Tests pass the seams they
    replace: the platform, root, the program runner, the terminal
    and the clock, the passwd lookup and the linking helpers.
    """

    def __init__(
        self,
        system=None,
        machine=None,
        is_root=None,
        http_session=None,
        run=None,
        root='/',
        temp_root=None,
        home=None,
        trusted_uid=0,
        trusted_gids=None,
        environ=None,
        is_tty=None,
        root_home=None,
        own_socket=None,
        socket_wait=_SOCKET_WAIT_SECONDS,
        sleep=None,
        clock=None,
        health=None,
        user_entry=None,
        link_as=None,
        unlink_as=None,
    ):
        self.system = system or sys.platform
        self._given_machine = machine
        self._found_machine = None
        self.is_root = is_root
        self.http_session = http_session
        self.run = run or self._run
        self.root = root
        # The folder to run the installer from, instead of the first of
        # LINUX_TEMP_ROOTS that works (tests).
        self.temp_root = temp_root
        self.home = home
        self.trusted_uid = trusted_uid
        # Groups that may write a folder on the way to a program run as
        # root: gid 0 only.
        if trusted_gids is None:
            trusted_gids = (0,)
        self.trusted_gids = frozenset(trusted_gids)
        self.environ = os.environ if environ is None else environ
        self.is_tty = is_tty or is_stdin_a_tty
        self.root_home = root_home
        # The socket to link to, instead of aws-credential-daemon's own
        # (tests).
        self.own_socket = own_socket
        self.socket_wait = socket_wait
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
        # How to ask the daemon for system/health (tests).
        self.health = health or check_daemon_health
        # pwd.getpwnam, and how to link or unlink as another user (tests).
        self.user_entry = user_entry or _passwd_entry
        self.link_as = link_as or link_as_user
        self.unlink_as = unlink_as or unlink_as_user

    def _run(self, command, check=True, timeout=None):
        return _run(
            command, check=check, timeout=timeout, env=self.child_environ()
        )

    def child_environ(self):
        """The environment of the programs install, uninstall and link run.

        On Linux they run as root, so it's fixed: a PATH of system folders
        only, the C locale, and root's home from its passwd entry, and
        nothing from the caller. For example, sudo -E would otherwise pass
        on the user's CREDSD_DATA_DIR, RUST_LOG, proxies and the official
        installer's LD_LIBRARY_PATH. On macOS they run as the user, with
        the user's environment, less the bundled Python's library path.
        """
        if self.system == 'linux':
            return {
                'PATH': _LINUX_CHILD_PATH,
                'LC_ALL': 'C',
                'HOME': self.root_home or root_passwd_home(),
            }
        return _user_child_environ(self.environ)

    def proxy_hint(self):
        """How to keep a proxy's settings and CA bundle under sudo, which
        drops them (env_reset), for a download that couldn't connect."""
        command = _PROXY_SUDO_INSTALL
        return (
            f'Behind a proxy, keep its settings under sudo:\n  {command}\n'
            'If the proxy inspects TLS, also pass --ca-bundle with its CA '
            'file.'
        )

    @property
    def machine(self):
        if self._given_machine:
            return self._given_machine
        if self._found_machine is None:
            self._found_machine = _host_machine(self.system)
        return self._found_machine

    def runs_as_root(self):
        if self.is_root is None:
            return os.geteuid() == 0
        return self.is_root

    def path(self, relative):
        return os.path.join(self.root, relative)

    def home_path(self, relative, home=None):
        home = home or self.home or os.path.expanduser('~')
        return os.path.join(home, relative)

    def linux_temp_root(self):
        """The folder the Linux install runs the installer from. Refuses,
        before anything is downloaded, if none of them can run programs."""
        if self.temp_root is not None:
            return self.temp_root
        for path in LINUX_TEMP_ROOTS:
            if _temp_root_problem(path) is None:
                return path
        # A noexec /tmp is a common hardening control (CIS). The installer
        # must run from a folder everyone can write to, so a root-only one
        # isn't a fallback.
        roots = ' and '.join(LINUX_TEMP_ROOTS)
        raise ConfigurationError(
            f'{roots} are mounted noexec or aren\'t shared temporary folders, '
            f'so {CREDENTIAL_DAEMON_PRODUCT}\'s installer can\'t run from '
            'them. Nothing was downloaded.'
        )

    def run_installer(self, command):
        """Run aws-credential-daemon's installer, and print the warnings it
        gave on success, such as a missing tss group."""
        try:
            result = self.run(command)
        except subprocess.CalledProcessError as e:
            # macOS's installer writes its failure to stdout.
            detail = printable_lines(e.stderr) or printable_lines(e.stdout)
            if detail:
                message = f'{CREDENTIAL_DAEMON_PRODUCT}\'s installer failed:\n{detail}'
            else:
                message = (
                    f'{CREDENTIAL_DAEMON_PRODUCT}\'s installer failed '
                    f'(exit {e.returncode}).'
                )
            if self.system == 'darwin':
                message += '\nFor details, see /var/log/install.log'
            raise ConfigurationError(message) from e
        except OSError as e:
            raise _not_run(command, e) from e
        warnings = installer_warnings(getattr(result, 'stderr', ''))
        if warnings:
            uni_print(''.join(f'{line}\n' for line in warnings), sys.stderr)
            if self.system == 'linux' and any(
                _NAMES_CREDSD_INSTALL in line for line in warnings
            ):
                # credsd's own `credsd install` isn't on PATH; this
                # command runs it, and links too.
                uni_print(f'Then run: {sudo_command("install")}\n', sys.stderr)

    def run_tool(self, command):
        """Run a checking tool, whose exit code the caller reads."""
        try:
            return self.run(command, check=False)
        except OSError as e:
            raise _not_run(command, e) from e

    def run_uninstaller(self, command, still_there):
        """Run aws-credential-daemon's uninstaller."""
        try:
            self.run(command)
        except (OSError, subprocess.CalledProcessError) as e:
            raise ConfigurationError(
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s uninstaller failed:\n'
                f'{error_detail(e)}\nNothing else was removed; '
                f'{CREDENTIAL_DAEMON_PRODUCT} is still installed at '
                f'{still_there}.'
            ) from e
