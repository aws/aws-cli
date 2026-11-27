# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Installing and uninstalling aws-credential-daemon's system service on
Linux."""

import errno
import fnmatch
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from awscli.botocore.credential_daemon import strip_control_characters
from awscli.customizations.configure.credential_daemon_install.host import (
    LINUX_ARCHITECTURES,
    LINUX_TEMP_ROOTS,
    error_detail,
    root_only_problem,
    sudo_command,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    CREDENTIAL_DAEMON_PRODUCT,
    LINUX_SIGNATURE_SUFFIX,
    credential_daemon_version,
    extract_safely,
    find_gpg,
    format_version,
    linux_asset_name,
    printable_lines,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print

# Where aws-credential-daemon's installers put things (its docs/install.md),
# relative to the root of the file system or the user's home. Read from its
# source and checked against the v0.1.0 release:
# - Linux: aws-credential-daemon stages a root-owned copy at its libexec path,
#   and the service runs that, only when the program it's run from could be
#   replaced by someone other than root. Install runs it from a new directory
#   under /tmp (/var/tmp if /tmp is noexec) and checks the service runs the
#   staged copy. `credsd uninstall` removes the units, the staged copy and its
#   .credsd.staging file, and keeps aws-credential-daemon's data, logs and
#   account.
# - Linux: aws-credential-daemon's units are credsd.service, with one
#   ExecStart line that runs the staged copy, and credsd.socket, which starts
#   credsd.service by name. With no units left, `credsd uninstall` still
#   removes the staged copy; the CLI removes it itself.
_LINUX_STAGED_CREDENTIAL_DAEMON = 'usr/local/libexec/credsd/credsd'


# aws-credential-daemon's temporary file while it stages its copy.
_LINUX_STAGING = '.credsd.staging'


_LINUX_SERVICE = 'credsd.service'


_LINUX_SOCKET = 'credsd.socket'


_LINUX_UNIT_DIR = 'etc/systemd/system'


_LINUX_UNITS = (
    f'{_LINUX_UNIT_DIR}/{_LINUX_SERVICE}',
    f'{_LINUX_UNIT_DIR}/{_LINUX_SOCKET}',
)


_SYSTEMCTL_PATHS = ('/usr/bin/systemctl', '/bin/systemctl')


_UNIT_PROPERTIES = 'LoadState,UnitFileState,ActiveState'


# What systemd itself will run for credsd.service, drop-ins included.
_SERVICE_EXEC_PROPERTIES = (
    'ExecStartPre',
    'ExecStart',
    'ExecStartPost',
    'ExecReload',
    'ExecStop',
    'ExecStopPost',
)


_SERVICE_PROPERTIES = ','.join(
    _SERVICE_EXEC_PROPERTIES
    + ('DropInPaths', 'FragmentPath', 'NeedDaemonReload')
)


# One command in systemctl show's Exec* value: "{ path=/x ; argv[]=... }".
_SHOWN_EXEC_PATH = re.compile(r'(?:^|[{;]\s*)path=([^ ;]*)')


# The program a unit runs when a rollback that kept our temp folder was cut
# short (a second SIGINT, a kill): the copy extracted under the temp root.
_KEPT_COPY_PATTERN = 'tmp*/release/credsd-linux-*/credsd'


# How long `credsd --version` may take.
_VERSION_TIMEOUT_SECONDS = 10


# The TPM build's library a host without tpm2-tss lacks, as the loader names
# it: "error while loading shared libraries: libtss2-esys.so.0".
_TPM_LIBRARY = 'libtss2'


# The folders on the way to the staged copy that credsd's installer
# resolves. See _linked_folder_refusal.
_STAGED_FOLDERS = ('usr', 'usr/local', 'usr/local/libexec')


# UnitFileStates that can't start a unit. Anything else (enabled, linked,
# alias, indirect, static, generated, bad, ...) counts as still there.
_UNIT_FILE_STATES_OFF = ('', 'disabled', 'masked', 'masked-runtime')


_ACTIVE_STATES_RUNNING = (
    'active',
    'activating',
    'reloading',
    'deactivating',
    'refreshing',
)


_MAX_UNIT_BYTES = 64 * 1024


# Downloads are saved under this name, not the release's asset name, so no
# text from the release reaches a path, gpg or tar.
_LOCAL_ARCHIVE = 'aws-credential-daemon.tar.gz'


# The most of a program's output an error message shows.
_SHOWN_OUTPUT_CHARACTERS = 200


def _first_line(output):
    """The first printable line of a program's output, shortened, or
    'nothing'."""
    lines = printable_lines(output).split('\n')
    line = lines[0] if lines else ''
    if len(line) > _SHOWN_OUTPUT_CHARACTERS:
        line = line[:_SHOWN_OUTPUT_CHARACTERS] + '...'
    return line or 'nothing'


def _systemctl():
    for path in _SYSTEMCTL_PATHS:
        if os.path.isfile(path):
            return path
    return _SYSTEMCTL_PATHS[0]


def _service_staging_problem(service):
    """Why the unit file service doesn't run the staged copy, or None."""
    staged = '/' + _LINUX_STAGED_CREDENTIAL_DAEMON
    try:
        with open(service, 'rb') as f:
            data = f.read(_MAX_UNIT_BYTES + 1)
    except OSError as e:
        return f'{service} couldn\'t be read ({e.strerror})'
    # A later Exec* line past the limit would go unchecked.
    if len(data) > _MAX_UNIT_BYTES:
        return f'{service} is too large to check'
    programs = _unit_exec_programs(data.decode('utf-8', 'replace'))
    if not programs:
        return f'{service} has no ExecStart line'
    for program in programs:
        if program != staged:
            program = strip_control_characters(program)
            return f'{service} runs {program}, not {staged}'
    return None


# systemd Exec* directives whose value is a list of paths, not a command line
# (systemd.exec(5)). Any other Exec* key is read as a command, so one systemd
# adds later is still checked.
_NON_COMMAND_EXEC_DIRECTIVES = frozenset({'ExecPaths', 'ExecSearchPath'})


def _unit_exec_lines(text):
    """The value of each Exec*= command line of a systemd unit."""
    values = []
    for line in text.splitlines():
        key, sep, value = line.strip().partition('=')
        key = key.strip()
        if (
            sep
            and key.startswith('Exec')
            and key not in _NON_COMMAND_EXEC_DIRECTIVES
        ):
            values.append(value)
    return values


def _unit_exec_programs(text):
    """The program of each Exec*= line of a systemd unit."""
    programs = []
    for value in _unit_exec_lines(text):
        # systemd's prefixes on the program: @ - : + !
        value = value.strip().lstrip('@-:+!')
        try:
            words = shlex.split(value)
        except ValueError:
            words = [value]
        programs.append(words[0] if words else '')
    return programs


def _unit_values(text, name):
    values = []
    for line in text.splitlines():
        key, sep, value = line.strip().partition('=')
        if sep and key.strip() == name:
            values.extend(value.split())
    return values


def _remove_empty_dir(path, left):
    try:
        os.rmdir(path)
    except FileNotFoundError:
        pass
    except OSError as e:
        if e.errno not in (errno.ENOTEMPTY, errno.EEXIST):
            left.append((path, e.strerror))


class LinuxInstall:
    """A system install: aws-credential-daemon's staged copy and its systemd
    units.

    Each step skips what's already gone, so running uninstall again after a
    partial cleanup finishes the rest. With the staged copy there and a unit
    left, aws-credential-daemon's own uninstaller runs. Without it, the CLI
    finishes by itself, but only with what it can show is from this install: a
    root-only unit whose Exec lines run the staged copy, the socket next
    to such a service, and the staged copy. Anything else is reported.
    """

    whose = ''

    def __init__(self, host):
        self.host = host
        self._credential_daemon = host.path(_LINUX_STAGED_CREDENTIAL_DAEMON)
        self._service, self._socket = (
            host.path(unit) for unit in _LINUX_UNITS
        )
        # The socket first, so a run that stops halfway leaves the
        # service, which is what shows the socket is this install's.
        self._units = [self._socket, self._service]
        self._staging = os.path.join(
            os.path.dirname(self._credential_daemon), _LINUX_STAGING
        )
        self._runs_uninstaller = False
        # Our extracted copies under the temp root that units still run.
        self._kept_copies = set()
        self._temp_root = None
        self._source = None
        self._keep_temp_dir = False
        self._kept_temp_dir_reported = False
        # Whether credsd.service ran the staged copy before the installer.
        self._had_staged_install = False
        # Whether a rollback started, so a report after an interrupt names
        # the units it may have left.
        self._rolling_back = False

    def is_installed(self):
        # The staging file alone is what an interrupted install
        # leaves, and that counts too.
        return any(
            os.path.lexists(path)
            for path in [self._credential_daemon, self._staging] + self._units
        )

    def notes(self):
        return []

    def check_uninstaller(self):
        self._refuse_linked_folders('nothing was uninstalled')
        units_left = any(os.path.lexists(unit) for unit in self._units)
        if os.path.lexists(self._credential_daemon):
            # Without units, aws-credential-daemon's uninstaller has nothing
            # to do; the staged copy is removed below.
            self._runs_uninstaller = units_left
            if units_left:
                self._check_runs_as_root(self._credential_daemon)
            return
        ours, others = self._classify_units()
        if (
            not ours
            and others
            and all(kind == 'other' for _, kind, _ in others)
        ):
            # Units that run another program: aws-credential-daemon was
            # installed some other way, and its own uninstaller removes it.
            raise ConfigurationError(
                f'{CREDENTIAL_DAEMON_PRODUCT} wasn\'t installed by aws configure '
                'credential-daemon install ('
                f'{self._credential_daemon} is missing), so '
                f'nothing was uninstalled. {self._other_install_remedy()}'
            )

    def _other_install_remedy(self):
        """How to remove units another install left.

        Named as the unit runs it, since `credsd` may not be on PATH, but
        only when root alone can change that program: the CLI never
        suggests running as root what another user could have put there.
        For example, a unit left running /tmp/tmpab12cd34/release/.../credsd
        after a reboot cleared /tmp gets the systemctl commands instead.
        """
        program = self._service_program(exec_start_only=True)
        if (
            program is not None
            and os.path.isabs(program)
            and os.path.basename(program) == 'credsd'
            and self._root_only_problem(program) is None
        ):
            shown = shlex.quote(strip_control_characters(program))
            return f'Uninstall it with: sudo {shown} uninstall'
        units = ' '.join(
            shlex.quote(unit) for unit in self._units if os.path.lexists(unit)
        )
        return (
            'To remove its service, run:\n'
            '  sudo systemctl disable --now '
            f'{_LINUX_SOCKET} {_LINUX_SERVICE}\n'
            f'  sudo rm {units}\n'
            '  sudo systemctl daemon-reload'
        )

    def run_uninstaller(self):
        if self._runs_uninstaller:
            self.host.run_uninstaller(
                [self._credential_daemon, 'uninstall'], self._credential_daemon
            )

    def remove_files(self):
        left = []
        ours, others = self._classify_units()
        for path, _, reason in others:
            if self._runs_uninstaller:
                reason = 'not removed by the uninstaller'
            left.append((path, reason))
        left.extend(self._remove_units(ours))
        if not left:
            # Only once no unit is left: one still on disk may still run
            # that copy, so its folder stays until the unit is gone.
            left.extend(self._remove_kept_copies())
        if os.path.lexists(self._credential_daemon):
            left.extend(self._remove_staged_copy())
        if not left:
            left.extend(self._remove_staging_leftover())
        if not left:
            _remove_empty_dir(os.path.dirname(self._credential_daemon), left)
        return left

    def _classify_units(self):
        """([ours], [(path, kind, reason)]) for the units still there.

        kind 'other' means the unit runs another program, so it's from
        another install."""
        service = self._unit_problem(self._service)
        ours, others = [], []
        if os.path.lexists(self._socket):
            socket = self._unit_problem(self._socket)
            if socket is None and not os.path.lexists(self._service):
                socket = (
                    'unmatched',
                    f'can\'t be shown to be from this install without '
                    f'{_LINUX_SERVICE}, so it wasn\'t removed',
                )
            elif socket is None and service is not None:
                socket = (
                    service[0],
                    f'starts {_LINUX_SERVICE}, which isn\'t from this '
                    f'install, so it wasn\'t removed',
                )
            if socket is None:
                ours.append(self._socket)
            else:
                others.append((self._socket, *socket))
        if os.path.lexists(self._service):
            if service is None:
                ours.append(self._service)
            else:
                others.append((self._service, *service))
        return ours, others

    def _unit_problem(self, path):
        """(kind, reason) if path isn't provably this install's unit."""
        if not os.path.lexists(path):
            return None
        reason = self._not_removed_reason(path)
        if reason is not None:
            return 'unsafe', reason
        try:
            with open(path, 'rb') as f:
                data = f.read(_MAX_UNIT_BYTES + 1)
        except OSError as e:
            return 'unsafe', (
                f'couldn\'t be read ({e.strerror}), so it wasn\'t removed'
            )
        if len(data) > _MAX_UNIT_BYTES:
            return 'unsafe', 'is too large to check, so it wasn\'t removed'
        text = data.decode('utf-8', 'replace')
        staged = '/' + _LINUX_STAGED_CREDENTIAL_DAEMON
        programs = _unit_exec_programs(text)
        not_ours = (
            f'doesn\'t run {staged}, so it isn\'t from this install and '
            f'wasn\'t removed'
        )
        kept = [program for program in programs if self._is_kept_copy(program)]
        if any(
            program != staged and program not in kept for program in programs
        ):
            return 'other', not_ours
        self._kept_copies.update(kept)
        if path == self._service and not programs:
            return 'other', not_ours
        if path == self._socket and any(
            name != _LINUX_SERVICE for name in _unit_values(text, 'Service')
        ):
            return 'other', (
                f'starts a service other than {_LINUX_SERVICE}, so it isn\'t '
                f'from this install and wasn\'t removed'
            )
        return None

    def _is_kept_copy(self, program):
        """Whether program is the copy a cut-short install or rollback left
        under a temp root, in a folder only root can change.

        For example, after a second Ctrl-C during the rollback,
        credsd.service still runs
        /tmp/tmpab12cd34/release/credsd-linux-x64-tpm/credsd. That's this
        install's, so uninstall removes the units and the folder. A path
        someone else could have made there isn't, and is refused.
        """
        for temp_root in self._temp_roots():
            relative = os.path.relpath(os.path.normpath(program), temp_root)
            if relative.startswith('..') or not fnmatch.fnmatchcase(
                relative, _KEPT_COPY_PATTERN
            ):
                continue
            # From the program up to our tmpXXXX folder: /tmp itself is
            # writable by everyone, but sticky, so only its owner can
            # rename that folder.
            kept = os.path.join(temp_root, relative.split(os.sep)[0])
            return self._root_only_problem(program, root=kept) is None
        return False

    def _temp_roots(self):
        if self.host.temp_root is not None:
            return [self.host.temp_root]
        return [self.host.path(root.lstrip('/')) for root in LINUX_TEMP_ROOTS]

    def _remove_kept_copies(self):
        """Remove the temp folders whose copy units ran, now that they're
        gone."""
        left = []
        for program in sorted(self._kept_copies):
            for temp_root in self._temp_roots():
                relative = os.path.relpath(program, temp_root)
                if relative.startswith('..'):
                    continue
                folder = os.path.join(temp_root, relative.split(os.sep)[0])
                try:
                    shutil.rmtree(folder)
                except FileNotFoundError:
                    pass
                except OSError as e:
                    left.append((folder, e.strerror))
        return left

    def _remove_units(self, units):
        if not units:
            return []
        systemctl = _systemctl()
        names = [os.path.basename(unit) for unit in units]
        try:
            self.host.run([systemctl, 'disable', '--now', *names])
        except (OSError, subprocess.CalledProcessError) as e:
            reason = f'systemctl disable --now failed: {error_detail(e)}'
            return [(unit, reason) for unit in units]
        left = []
        for unit in units:
            try:
                os.remove(unit)
            except FileNotFoundError:
                pass
            except OSError as e:
                left.append((unit, e.strerror))
        try:
            self.host.run([systemctl, 'daemon-reload'])
        except (OSError, subprocess.CalledProcessError) as e:
            left.append(
                (
                    'systemd',
                    f'still has the removed units loaded '
                    f'({error_detail(e)})',
                )
            )
        return left

    def _remove_staged_copy(self):
        if any(os.path.lexists(unit) for unit in self._units):
            return [
                (self._credential_daemon, 'not removed by the uninstaller')
            ]
        reason = self._not_removed_reason(self._credential_daemon)
        if reason is not None:
            return [(self._credential_daemon, reason)]
        try:
            os.remove(self._credential_daemon)
        except FileNotFoundError:
            pass
        except OSError as e:
            return [(self._credential_daemon, e.strerror)]
        return []

    def _remove_staging_leftover(self):
        """Remove the temporary file an interrupted install left."""
        path = self._staging
        if not os.path.lexists(path):
            return []
        reason = self._not_removed_reason(path)
        if reason is not None:
            return [(path, reason)]
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            return [(path, e.strerror)]
        return []

    def before_download(self):
        # Before anything is downloaded. aws-credential-daemon's own
        # installer checks the rest of what it needs from the machine.
        self.linux_arch()
        self._refuse_linked_folders('nothing was downloaded')
        self._temp_root = self.host.linux_temp_root()
        # Its signature check needs gpg. Checked here, so a machine without
        # it is refused before the download and before install says it
        # starts: for example, a minimal container image with no gnupg.
        find_gpg()

    def _refuse_linked_folders(self, outcome):
        """Refuse a /usr/local (or /usr, or /usr/local/libexec) that's a
        symbolic link, before anything happens.

        For example, on rpm-ostree systems (Fedora Silverblue, CoreOS)
        /usr/local links to /var/usrlocal. credsd's installer writes the
        real path into its unit, ExecStart=/var/usrlocal/libexec/credsd/
        credsd, so the check that the service runs the staged copy at
        /usr/local/libexec/credsd/credsd would fail after a good install
        and roll it back. Refusing up front says why before the download.
        """
        for relative in _STAGED_FOLDERS:
            if os.path.islink(self.host.path(relative)):
                message = (
                    f'/{relative} is a symbolic link (as on rpm-ostree '
                    'systems), which this command doesn\'t support, so '
                    f'{outcome}.'
                )
                staged = os.path.realpath(self._credential_daemon)
                if (
                    outcome == 'nothing was uninstalled'
                    and os.path.isfile(staged)
                    and self._root_only_problem(staged) is None
                ):
                    # Its own uninstaller works there, and only root can
                    # have put it there.
                    shown = shlex.quote(strip_control_characters(staged))
                    message += f' Uninstall it with: sudo {shown} uninstall'
                raise ConfigurationError(message)

    def reinstall_note(self):
        """What install says about an install that's already here, once
        the release is known to install."""
        service = os.path.join(self.host.root, _LINUX_UNITS[0])
        other = None
        if os.path.lexists(service) and self._staging_problem() is not None:
            other = self._service_program()
        if other is not None:
            # A service set up some other way, such as from source. credsd's
            # installer rewrites the units, so say what changes.
            other = strip_control_characters(other)
            return (
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s service runs {other}, not the '
                'release this command installs. Installing replaces the '
                f'service with the GitHub release; {other} stays.\n'
            )
        if self._is_installed_linux():
            return (
                f'{CREDENTIAL_DAEMON_PRODUCT} is already installed, so this '
                'reinstalls it.\n'
            )
        return ''

    def installed_version(self):
        """The installed staged copy's version, or None if there's none, it
        can't be shown to be root's, or it doesn't say. It runs as root, so
        it runs only once only root could have written it."""
        if not os.path.lexists(self._credential_daemon):
            return None
        if self._root_only_problem(self._credential_daemon) is not None:
            return None
        try:
            result = self._run_version(self._credential_daemon)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        version, _ = credential_daemon_version(result.stdout)
        return version

    def _run_version(self, program):
        """Run ``program --version``. Raises what running it raises."""
        return self.host.run(
            [program, '--version'],
            check=False,
            timeout=_VERSION_TIMEOUT_SECONDS,
        )

    def _service_program(self, exec_start_only=False):
        """The first program credsd.service runs that isn't the staged
        copy, from its unit file (its ExecStart lines only, with
        ``exec_start_only``), or None."""
        service = os.path.join(self.host.root, _LINUX_UNITS[0])
        staged = '/' + _LINUX_STAGED_CREDENTIAL_DAEMON
        try:
            with open(service, 'rb') as f:
                data = f.read(_MAX_UNIT_BYTES)
        except OSError:
            return None
        text = data.decode('utf-8', 'replace')
        if exec_start_only:
            text = '\n'.join(
                line
                for line in text.splitlines()
                if line.strip().partition('=')[0].strip() == 'ExecStart'
            )
        for program in _unit_exec_programs(text):
            if program and program != staged:
                return program
        return None

    def install(self, source, release):
        """Install the system service as root: download, check the signature,
        run aws-credential-daemon's installer, and check the service runs its
        staged copy. Returns the exit code."""
        self._source = source
        # aws-credential-daemon stages its own copy only when the program
        # it's run from could be replaced by someone other than root, and
        # /tmp can be. Under a root-only TMPDIR it would skip staging and
        # its service would run our copy, which is deleted below. The
        # directory itself is new, 0700 and the caller's (root's).
        tmp = tempfile.mkdtemp(
            dir=self._temp_root or self.host.linux_temp_root()
        )
        # A unit the installer wrote may run our copy. Once the directory
        # is removed, anyone can recreate its path in /tmp, and that unit
        # would run their program. So from the install on, the directory
        # stays unless a check shows no unit runs from it: an interrupted
        # install or rollback keeps it.
        self._keep_temp_dir = False
        self._kept_temp_dir_reported = False
        self._rolling_back = False
        try:
            credential_daemon = self._download_linux(release, tmp)
            self._had_staged_install = self._runs_staged_copy()
            self._keep_temp_dir = True
            # aws-credential-daemon's own installer creates its
            # account, units and socket.
            try:
                self.host.run_installer([credential_daemon, 'install'])
            except (Exception, KeyboardInterrupt) as e:
                # On a reinstall aws-credential-daemon doesn't undo a
                # half-done install, so a rewritten credsd.service can be
                # left enabled and running our copy.
                self._roll_back_failed_install(credential_daemon, e, tmp)
                raise
            # Check while our copy still exists.
            problem = self._staging_problem()
            if problem is not None:
                # Nothing is installed after the rollback, so it exits
                # like any other install that fails (253).
                raise ConfigurationError(
                    self._roll_back_linux(
                        credential_daemon, problem, tmp
                    ).rstrip()
                )
            # The service runs the staged copy, not ours.
            self._keep_temp_dir = False
        finally:
            if not self._keep_temp_dir:
                shutil.rmtree(tmp, ignore_errors=True)
            elif not self._kept_temp_dir_reported:
                # An interrupt, or an error the rollback didn't report.
                uni_print(self._kept_temp_dir_report(tmp), sys.stderr)
        # Only what the installer's exit code backs up. aws-credential-daemon
        # doesn't report where it seals secrets, so don't name a keystore.
        uni_print(
            f'Installed {CREDENTIAL_DAEMON_PRODUCT} as a system service.\n'
        )
        return 0

    def _check_runs_as_root(self, path):
        """Refuse to run path as root unless only root can replace it."""
        problem = self._root_only_problem(path)
        if problem is None:
            return
        kind, checked, detail = problem
        if kind == 'error':
            raise ConfigurationError(f'Couldn\'t check {checked}: {detail}')
        if kind == 'writable':
            raise ConfigurationError(
                f'{checked} can be changed by users other than root, so '
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s uninstaller '
                'wasn\'t run. Nothing was '
                f'uninstalled.'
            )
        if kind == 'symlink':
            raise ConfigurationError(
                f'{checked} is a symbolic link, so {CREDENTIAL_DAEMON_PRODUCT}\'s '
                f'uninstaller wasn\'t run. Nothing was uninstalled.'
            )
        raise ConfigurationError(
            f'{path} isn\'t a regular file, so {CREDENTIAL_DAEMON_PRODUCT}\'s '
            f'uninstaller wasn\'t run. Nothing was uninstalled.'
        )

    def _root_only_problem(self, path, root=None):
        """host.root_only_problem with this host's install root and trusted
        owner and groups."""
        return root_only_problem(
            path,
            root=self.host.root if root is None else root,
            trusted_uid=self.host.trusted_uid,
            trusted_gids=self.host.trusted_gids,
        )

    def _not_removed_reason(self, path):
        """Why path can't be shown to be root's, or None if it can."""
        problem = self._root_only_problem(path)
        if problem is None:
            return None
        kind, checked, detail = problem
        if kind == 'error':
            return f'couldn\'t be checked ({detail}), so it wasn\'t removed'
        if kind == 'writable' and checked != path:
            return (
                f'{checked} can be changed by users other than root, so it '
                f'wasn\'t removed'
            )
        if kind == 'writable':
            return (
                'can be changed by users other than root, so it wasn\'t '
                'removed'
            )
        if kind == 'symlink':
            return f'{checked} is a symbolic link, so it wasn\'t removed'
        return 'isn\'t a regular file, so it wasn\'t removed'

    def _is_installed_linux(self):
        return any(
            os.path.lexists(os.path.join(self.host.root, path))
            for path in (_LINUX_STAGED_CREDENTIAL_DAEMON,) + _LINUX_UNITS
        )

    def _download_linux(self, release, tmp):
        name = linux_asset_name(self.linux_arch())
        archive = os.path.join(tmp, _LOCAL_ARCHIVE)
        self._source.download(release, name, archive)
        signature = archive + LINUX_SIGNATURE_SUFFIX
        self._source.download(
            release, name + LINUX_SIGNATURE_SUFFIX, signature
        )
        self._source.verify_pgp_signature(archive, signature, tmp)
        extracted = os.path.join(tmp, 'release')
        extract_safely(archive, extracted)
        return self._release_program(extracted, release)

    def _release_program(self, extracted, release):
        """The archive's credsd, checked to be the release it was
        downloaded as.

        The signature covers the archive's bytes only, not its name or
        tag, so any archive the key ever signed would pass. What the signed
        bytes say is checked instead: the folder they unpack to, and what
        credsd itself reports. For example, v0.1.0's al2023 build uploaded
        as credsd-linux-x64-tpm.tar.gz under v9.9.9 unpacks to
        credsd-al2023-x64-tpm/ and reports 0.1.0, so it's refused.
        """
        folder = linux_asset_name(self.linux_arch())[: -len('.tar.gz')]
        program = os.path.join(extracted, folder, 'credsd')
        try:
            st = os.lstat(program)
        except OSError:
            st = None
        if st is None or not stat.S_ISREG(st.st_mode):
            raise ConfigurationError(
                f'The archive isn\'t the {folder} release (it has no '
                f'{folder}/credsd), so {CREDENTIAL_DAEMON_PRODUCT} wasn\'t '
                'installed.'
            )
        os.chmod(program, 0o755)
        # A signature-checked program, run as root from our 0700 folder.
        output = self._release_version_output(program)
        version, backends = credential_daemon_version(output)
        if version is None:
            raise ConfigurationError(
                f'The downloaded {CREDENTIAL_DAEMON_PRODUCT} didn\'t report '
                f'its version (it printed: {_first_line(output)}), so it '
                'wasn\'t installed.'
            )
        if version != release.version or 'tpm' not in backends:
            shown_version = format_version(version)
            shown_backends = ', '.join(backends) or 'none'
            raise ConfigurationError(
                f'The archive is {CREDENTIAL_DAEMON_PRODUCT} {shown_version} '
                '(storage backends: '
                f'{strip_control_characters(shown_backends)}), '
                f'but its release says {format_version(release.version)} with '
                f'the tpm backend, so it wasn\'t installed.'
            )
        return program

    def _release_version_output(self, program):
        """What the downloaded program's ``--version`` printed. Raises, with its exit code and error
        output, if it couldn't run or failed: for example, without
        tpm2-tss the TPM build can't load libtss2-esys.so.0 and exits 127,
        which isn't a release that says another version."""
        not_run = f'Couldn\'t run the downloaded {CREDENTIAL_DAEMON_PRODUCT}'
        try:
            result = self._run_version(program)
        except subprocess.TimeoutExpired as e:
            raise ConfigurationError(
                f'{not_run} (it didn\'t finish within '
                f'{_VERSION_TIMEOUT_SECONDS} seconds), so it wasn\'t '
                'installed.'
            ) from e
        except (OSError, subprocess.SubprocessError) as e:
            raise ConfigurationError(
                f'{not_run} ({error_detail(e)}), so it wasn\'t installed.'
            ) from e
        if result.returncode != 0:
            detail = error_detail(result)
            message = f'{not_run} (exit {result.returncode})'
            if detail != f'exit {result.returncode}':
                message += f': {detail}'
            if _TPM_LIBRARY in detail:
                message += (
                    '\nIts TPM build needs the tpm2-tss libraries: the '
                    'tpm2-tss package on Amazon Linux, Fedora and RHEL, or '
                    'the libtss2-esys packages on Debian and Ubuntu. Install '
                    'them, then run:\n'
                    f'  {sudo_command("install")}'
                )
            raise ConfigurationError(message)
        return result.stdout

    def _roll_back_failed_install(self, credential_daemon, error, tmp):
        """Roll back a failed install if credsd.service runs our copy.

        Raises a ConfigurationError that adds the rollback's report to
        the installer's error. With no credsd.service, or one that runs
        the staged copy, there is nothing to roll back: the report lists
        what the installer left, if anything, and the caller re-raises a
        non-ConfigurationError.
        """
        service = os.path.join(self.host.root, _LINUX_UNITS[0])
        problem = None
        if os.path.lexists(service):
            problem = self._staging_problem()
        if problem is not None:
            report = self._roll_back_linux(credential_daemon, problem, tmp)
        else:
            # No service, or one that runs the staged copy: nothing runs
            # ours.
            self._keep_temp_dir = False
            report = self._installer_leftovers()
        if not report:
            return
        if isinstance(error, ConfigurationError):
            raise ConfigurationError(f'{error}\n{report.rstrip()}') from error
        uni_print(report, sys.stderr)

    def _installer_leftovers(self):
        """What a failed install left in place (its staged copy and
        units), with the command that removes it, or '' if nothing."""
        staged = os.path.join(self.host.root, _LINUX_STAGED_CREDENTIAL_DAEMON)
        staging = os.path.join(os.path.dirname(staged), _LINUX_STAGING)
        units = [os.path.join(self.host.root, unit) for unit in _LINUX_UNITS]
        left = [
            path for path in [staged, staging, *units] if os.path.lexists(path)
        ]
        if not left:
            return ''
        if self._had_staged_install and self._runs_staged_copy():
            # A failed reinstall over an earlier install, whose service still
            # runs the staged copy. Uninstalling would remove that install.
            return (
                f'The earlier install of {CREDENTIAL_DAEMON_PRODUCT} is still '
                f'there: its service runs /{_LINUX_STAGED_CREDENTIAL_DAEMON}.\n'
                f'To try again, run: {sudo_command("install")}\n'
            )
        lines = [
            f'{CREDENTIAL_DAEMON_PRODUCT} may be partly installed. Still there:\n'
        ]
        lines.extend(f'  {path}\n' for path in left)
        lines.append(f'To remove it, run: {sudo_command("uninstall")}\n')
        return ''.join(lines)

    def _runs_staged_copy(self):
        """Whether credsd.service is there and runs the staged copy."""
        service = os.path.join(self.host.root, _LINUX_UNITS[0])
        return os.path.lexists(service) and self._staging_problem() is None

    def _roll_back_linux(self, credential_daemon, problem, tmp):
        """Undo an install whose service doesn't run the staged copy.

        Runs before our temp directory, tmp, is removed. The units are
        disabled first, socket first, so nothing can start the service
        while aws-credential-daemon's own uninstaller (our temp copy)
        removes them.
        Prints why first, so an interrupted rollback still says it. Returns
        the rest of the message. If units are left, tmp is kept.
        """
        uni_print(
            f'{CREDENTIAL_DAEMON_PRODUCT}\'s installer didn\'t '
            'set up its service as '
            f'expected: {problem}.\n',
            sys.stderr,
        )
        self._rolling_back = True
        systemctl = _systemctl()
        names = [_LINUX_SOCKET, _LINUX_SERVICE]
        errors = []
        try:
            self.host.run([systemctl, 'disable', '--now', *names])
        except (OSError, subprocess.CalledProcessError) as e:
            errors.append(f'systemctl disable --now failed: {error_detail(e)}')
        try:
            self.host.run([credential_daemon, 'uninstall'])
        except (OSError, subprocess.CalledProcessError) as e:
            errors.append(
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s uninstaller '
                f'failed: {error_detail(e)}'
            )
        left = self._linux_units_left(systemctl, names)
        if not left:
            self._rolling_back = False
            self._keep_temp_dir = False
            return (
                'The CLI stopped and removed '
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s '
                f'service and socket ({_LINUX_SOCKET} and {_LINUX_SERVICE}). '
                f'Its uninstaller keeps its system account, /var/lib/credsd '
                f'and /var/log/credsd.\n'
            )
        # A unit left may still run our copy, so its folder stays (the
        # caller set _keep_temp_dir), owned by root, until the unit is gone.
        lines = ['The CLI couldn\'t undo the install. Still there:\n']
        lines.extend(f'  {what}\n' for what in left)
        lines.extend(f'  ({error})\n' for error in errors)
        # The rollback ran to its end, so it isn't reported as interrupted.
        self._rolling_back = False
        lines.append(self._kept_temp_dir_report(tmp))
        self._kept_temp_dir_reported = True
        return ''.join(lines)

    def _kept_temp_dir_report(self, tmp):
        """What's left, and the commands that remove it.

        The units are named whenever credsd.service doesn't run the staged
        copy, wherever it runs from. The warning about tmp is added when its
        Exec lines may run a program in tmp, or it can't be read.
        """
        service, socket = (
            os.path.join(self.host.root, unit) for unit in _LINUX_UNITS
        )
        units = []
        # Not self._staging_problem(), which the caller may be inside of.
        if (
            os.path.lexists(service)
            and _service_staging_problem(service) is not None
        ) or self._rolling_back:
            units = [
                path for path in (socket, service) if os.path.lexists(path)
            ]
        if self._rolling_back and units:
            # For example, a Ctrl-C after `systemctl disable --now`: the
            # units are stopped and disabled, but still on disk. Uninstall
            # removes them (and the folder, if they run our copy from it),
            # so it's the one command given.
            return (
                'The rollback was interrupted. '
                f'{_LINUX_SOCKET} and {_LINUX_SERVICE} may be stopped and '
                'disabled, but are still there. To remove them, run:\n'
                f'  {sudo_command("uninstall")}\n'
                f'Kept on this machine: {tmp}\n'
                'If it\'s still there after that, remove it with:\n'
                f'  sudo rm -r {shlex.quote(tmp)}\n'
            )
        lines = ['Kept on this machine:\n', f'  {tmp}\n']
        lines.extend(f'  {unit}\n' for unit in units)
        commands = []
        if units:
            if self._runs_from(service, tmp):
                lines.append(
                    f'A reboot or /tmp cleanup deletes {tmp}, and then anyone '
                    f'can put a program at the path {_LINUX_SERVICE} runs. '
                    'Remove them now:\n'
                )
            else:
                lines.append('Remove them with:\n')
            names = ' '.join(os.path.basename(unit) for unit in units)
            commands = [
                f'sudo systemctl disable --now {names}',
                'sudo rm ' + ' '.join(shlex.quote(unit) for unit in units),
                'sudo systemctl daemon-reload',
            ]
        else:
            lines.append('Remove it with:\n')
        commands.append(f'sudo rm -r {shlex.quote(tmp)}')
        lines.extend(f'  {command}\n' for command in commands)
        return ''.join(lines)

    def _runs_from(self, service, tmp):
        """Whether service's Exec lines may run a program in tmp.

        Any mention of tmp's own name counts, so that a path spelled another
        way (``/tmp//tmpX``) or a shell's command line (``sh -c "..."``)
        does too.
        """
        try:
            with open(service, 'rb') as f:
                data = f.read(_MAX_UNIT_BYTES + 1)
        except OSError:
            return True
        if len(data) > _MAX_UNIT_BYTES:
            return True
        name = os.path.basename(tmp.rstrip('/'))
        return any(
            name in line
            for line in _unit_exec_lines(data.decode('utf-8', 'replace'))
        )

    def _linux_units_left(self, systemctl, names):
        """What of aws-credential-daemon's units is still enabled, running or
        on disk."""
        left = []
        for name, state in zip(
            names, self._linux_unit_states(systemctl, names)
        ):
            if state is None:
                # Unknown, so assume the worst.
                left.append(f'{name}: may still be enabled')
                left.append(f'{name}: may still be active')
                continue
            enabled = state.get('UnitFileState', '')
            active = state.get('ActiveState', '')
            # LoadState=not-found is gone, unless it's still running.
            if (
                state['LoadState'] != 'not-found'
                and enabled not in _UNIT_FILE_STATES_OFF
            ):
                left.append(f'{name}: {enabled}')
            if active in _ACTIVE_STATES_RUNNING:
                left.append(f'{name}: {active}')
        for unit in (_LINUX_UNITS[1], _LINUX_UNITS[0]):
            path = os.path.join(self.host.root, unit)
            if os.path.lexists(path):
                left.append(path)
        return left

    def _linux_unit_states(self, systemctl, names):
        """systemctl show's properties for each unit, or None if unknown.

        Unlike is-enabled, which prints nothing for a missing unit and
        stops there, show prints one block per unit, in argument order,
        with LoadState=not-found for a missing one.
        """
        unknown = [None] * len(names)
        try:
            result = self.host.run(
                [systemctl, 'show', '-p', _UNIT_PROPERTIES, *names],
                check=False,
            )
        except OSError:
            return unknown
        if result.returncode != 0:
            return unknown
        blocks = re.split(r'\n\s*\n', result.stdout.strip())
        if len(blocks) != len(names):
            return unknown
        states = []
        for block in blocks:
            state = {}
            for line in block.splitlines():
                key, sep, value = line.strip().partition('=')
                if sep:
                    state[key] = value.strip()
            states.append(state if 'LoadState' in state else None)
        return states

    def _staging_problem(self):
        """Why credsd.service doesn't run the staged copy, or None.

        systemd is asked what it will run, so a drop-in's ExecStart counts:
        for example, an override.conf with ``ExecStart=/bin/true`` fails
        this check though the unit file itself runs the staged copy. Paths
        are compared by their real path, so a staged copy reached through
        another spelling of the same path passes (a /usr/local that's a
        link is refused before this runs). If systemctl's answer can't be
        read, the unit file's text is checked instead.
        """
        service = os.path.join(self.host.root, _LINUX_UNITS[0])
        # The unit file on disk too: systemd's view is out of date until a
        # daemon-reload, so a unit an interrupted installer rewrote to run
        # our temp copy would still show the staged copy, and our folder,
        # which anyone can recreate in /tmp, would be deleted.
        problem = _service_staging_problem(service)
        if problem is not None:
            return problem
        shown = self._shown_service_properties()
        if shown is None:
            return None
        if shown.get('NeedDaemonReload', [''])[-1] == 'yes':
            return f'systemd hasn\'t loaded the current {service}'
        fragment = shown.get('FragmentPath', [''])[-1]
        if fragment != service:
            fragment = strip_control_characters(fragment) or 'no unit file'
            return (
                f'systemd loads {_LINUX_SERVICE} from {fragment}, not '
                f'{service}'
            )
        for drop_in in ' '.join(shown.get('DropInPaths', [])).split():
            problem = self._drop_in_problem(drop_in)
            if problem is not None:
                return problem
        staged = os.path.realpath(
            os.path.join(self.host.root, _LINUX_STAGED_CREDENTIAL_DAEMON)
        )
        # One line per command: a key can repeat.
        programs = [
            program
            for name in _SERVICE_EXEC_PROPERTIES
            for value in shown.get(name, [])
            for program in _SHOWN_EXEC_PATH.findall(value)
        ]
        if not any(
            _SHOWN_EXEC_PATH.findall(value)
            for value in shown.get('ExecStart', [])
        ):
            return f'{service} has no ExecStart line'
        for program in programs:
            if os.path.realpath(program) != staged:
                program = strip_control_characters(program)
                return (
                    f'{_LINUX_SERVICE} runs {program}, not '
                    f'/{_LINUX_STAGED_CREDENTIAL_DAEMON}'
                )
        return None

    def _shown_service_properties(self):
        """systemctl show's Exec*, DropInPaths and FragmentPath for
        credsd.service, or None if they can't be read."""
        try:
            result = self.host.run(
                [
                    _systemctl(),
                    'show',
                    '-p',
                    _SERVICE_PROPERTIES,
                    _LINUX_SERVICE,
                ],
                check=False,
            )
        except OSError:
            return None
        if result.returncode != 0 or not isinstance(result.stdout, str):
            return None
        shown = {}
        for line in result.stdout.splitlines():
            key, sep, value = line.partition('=')
            if sep:
                shown.setdefault(key.strip(), []).append(value.strip())
        if 'FragmentPath' not in shown or 'ExecStart' not in shown:
            return None
        return shown

    def _drop_in_problem(self, drop_in):
        """Why a drop-in of credsd.service may change what it runs, or
        None: it must be root's alone and have no Exec line."""
        shown = strip_control_characters(drop_in)
        problem = self._root_only_problem(drop_in)
        if problem is not None:
            return (
                f'{_LINUX_SERVICE} has a drop-in, {shown}, that users other '
                'than root can change'
            )
        try:
            with open(drop_in, 'rb') as f:
                data = f.read(_MAX_UNIT_BYTES + 1)
        except OSError as e:
            return f'{shown} couldn\'t be read ({e.strerror})'
        if len(data) > _MAX_UNIT_BYTES or _unit_exec_lines(
            data.decode('utf-8', 'replace')
        ):
            return (
                f'{_LINUX_SERVICE} has a drop-in, {shown}, that sets what it '
                'runs'
            )
        return None

    def linux_arch(self):
        arch = LINUX_ARCHITECTURES.get(self.host.machine)
        if arch is None:
            raise ConfigurationError(
                f'{CREDENTIAL_DAEMON_PRODUCT} has no release for {self.host.machine}.'
            )
        return arch
