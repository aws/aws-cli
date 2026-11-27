# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import importlib
import os
import platform
import subprocess

import pytest

from awscli.customizations.configure.credential_daemon_install import (
    host as install_host,
)
from awscli.customizations.configure.credential_daemon_install.host import (
    ST_NOEXEC,
    InstallHost,
)
from awscli.customizations.configure.credentialdaemon import (
    InstallCredentialDaemonCommand,
    install_supported,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
)
from tests import mock
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    STAGING_WARNING,
    TSS_WARNING,
    FakeHttp,
    Runner,
    UninstallRunner,
    install,
    linux_http,
    macos_http,
    macos_install,
    uninstall,
)


class TestChecksBeforeDownloading:
    def test_linux_install_needs_root_and_exits_253(self):
        # No self-escalation, and a refusal is 253.
        runner = Runner()
        http = FakeHttp({})
        with pytest.raises(ConfigurationError) as e:
            install(is_root=False, http=http, runner=runner)
        assert str(e.value) == (
            'Installing aws-credential-daemon as a system service requires '
            'root, so nothing was downloaded or changed. Run:\n'
            '  sudo aws configure credential-daemon install'
        )
        assert http.urls == []
        assert runner.commands == []

    def test_macos_install_as_root_is_refused_with_253(self):
        # The signed .pkg installs only for one user.
        runner = Runner()
        http = FakeHttp({})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', is_root=True, http=http, runner=runner)
        assert str(e.value) == (
            'On macOS aws-credential-daemon installs for one user. Run this '
            'without sudo: aws configure credential-daemon install'
        )
        assert http.urls == []
        assert runner.commands == []

    def test_unsupported_platform(self):
        with pytest.raises(ConfigurationError):
            install(system='win32')

    def test_intel_mac_install_is_refused(self):
        # The .pkg is for Apple silicon only, so its credsd can't run here.
        runner = Runner()
        http = FakeHttp({})
        with pytest.raises(ConfigurationError) as e:
            install(
                system='darwin', machine='x86_64', http=http, runner=runner
            )
        assert str(e.value) == (
            'aws-credential-daemon has no macOS release for x86_64. Its '
            'macOS release is for Apple silicon only.'
        )
        assert http.urls == []
        assert runner.commands == []


class TestInstallerOutput:
    def test_macos_installer_failure_shows_stdout_and_the_log(self):
        class Fails(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[0] == '/usr/sbin/installer':
                    self.commands.append(command)
                    raise subprocess.CalledProcessError(
                        1,
                        command,
                        output='installer: The install failed..\n',
                        stderr='',
                    )
                return super().__call__(command, check)

        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http(), runner=Fails())
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\n'
            'installer: The install failed..\n'
            'For details, see /var/log/install.log'
        )

    @pytest.mark.parametrize(
        'system, log',
        [('darwin', '\nFor details, see /var/log/install.log'), ('linux', '')],
    )
    def test_no_output_shows_the_exit_code(self, system, log, pinned_key):
        class Fails(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[-1] == 'install' or command[0].endswith(
                    'installer'
                ):
                    self.commands.append(command)
                    raise subprocess.CalledProcessError(
                        3, command, output='', stderr=''
                    )
                return super().__call__(command, check)

        if system == 'darwin':
            kwargs = {'http': macos_http()}
        else:
            kwargs = {
                'http': linux_http(),
            }
        with pytest.raises(ConfigurationError) as e:
            install(system=system, runner=Fails(), **kwargs)
        assert str(e.value) == (
            f'aws-credential-daemon\'s installer failed (exit 3).{log}'
        )

    def test_stderr_wins_over_stdout(self, pinned_key):
        class Fails(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[1:] == ['install']:
                    self.commands.append(command)
                    raise subprocess.CalledProcessError(
                        1, command, output='noise', stderr='no systemd'
                    )
                return super().__call__(command, check)

        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=Fails(),
            )
        # Linux has no install.log to point to.
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\nno systemd'
        )

    @pytest.mark.parametrize(
        'stdout, stderr',
        [
            ('', '\x1bno\x07 systemd\r\nline\x9b two\x1b'),
            ('\x1bno\x07 systemd\r\nline\x9b two\x1b', ''),
            # Control characters alone are no output, so stdout is shown.
            ('no systemd\nline two', '\x1b\x07'),
        ],
    )
    def test_control_characters_are_stripped(self, stdout, stderr, pinned_key):
        # Like the uninstaller's errors, the installer's output is shown
        # without control characters, so it can't rewrite the terminal.
        class Fails(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[1:] == ['install']:
                    self.commands.append(command)
                    raise subprocess.CalledProcessError(
                        1, command, output=stdout, stderr=stderr
                    )
                return super().__call__(command, check)

        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=Fails())
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\nno systemd\nline two'
        )

    @pytest.mark.parametrize(
        'stdout, stderr, detail',
        [
            (
                'Failed to stop credsd.socket',
                '',
                'Failed to stop credsd.socket',
            ),
            ('', '', 'exit 5'),
            (None, None, 'exit 5'),
        ],
    )
    def test_error_detail_falls_back_to_stdout_then_the_exit_code(
        self, stdout, stderr, detail
    ):
        error = subprocess.CalledProcessError(
            5, ['systemctl'], output=stdout, stderr=stderr
        )
        assert install_host.error_detail(error) == detail

    def test_error_detail_drops_lines_left_blank(self):
        # A line of control characters alone leaves no blank line at
        # either end of the uninstaller's error.
        error = subprocess.CalledProcessError(
            1, ['uninstall'], stderr='\x1b\nno systemd\n\x07'
        )
        assert install_host.error_detail(error) == 'no systemd'


# uninstall() needs os.getuid, which Windows doesn't have. The Windows refusal
# is tested in tests/functional/test_credential_daemon_windows_import.py.
@skip_if_windows
class TestUninstallChecks:
    def test_linux_uninstall_needs_root_and_exits_253(self, tmp_path):
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError) as e:
            uninstall(tmp_path, ['--yes'], is_root=False, runner=runner)
        assert str(e.value).startswith(
            'Uninstalling aws-credential-daemon\'s system service requires '
            'root, so nothing was changed. Run:\n'
        )
        assert runner.commands == []

    def test_macos_uninstall_as_root_is_refused(self, tmp_path, capsys):
        home = tmp_path / 'home'
        installed = macos_install(home, home / '.local/bin')
        # A per-user aws-credential-daemon the user can change must never
        # run as root.
        installed.credential_daemon.chmod(0o777)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError) as e:
            uninstall(
                tmp_path,
                ['--yes'],
                system='darwin',
                is_root=True,
                runner=runner,
            )
        assert str(e.value) == (
            'On macOS aws-credential-daemon installs for one user. Run this '
            'without sudo: aws configure credential-daemon uninstall'
        )
        assert runner.commands == []
        assert installed.bundle.exists()

    def test_macos_as_root_is_refused_even_with_nothing_installed(
        self, tmp_path, capsys
    ):
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError, match='Run this without sudo'):
            uninstall(
                tmp_path,
                ['--yes'],
                system='darwin',
                is_root=True,
                runner=runner,
            )
        assert runner.commands == []

    def test_unsupported_platform(self, tmp_path):
        with pytest.raises(ConfigurationError):
            uninstall(tmp_path, system='win32')

    def test_nothing_installed(self, tmp_path, capsys):
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert capsys.readouterr().out == (
            'aws-credential-daemon isn\'t installed.\n'
        )
        assert runner.commands == []


@skip_if_windows  # uninstall() needs os.getuid.
def test_uninstall_trusts_only_gid_0_by_default(tmp_path):
    _, command = uninstall(tmp_path, ['--yes'])
    assert command.host.trusted_gids == frozenset({0})


class TestInstallSupported:
    @pytest.mark.parametrize('machine', ['x86_64', 'amd64', 'aarch64'])
    def test_linux(self, machine):
        # Without a check for systemd or a TPM: install leaves that to
        # aws-credential-daemon's installer.
        with mock.patch.object(os.path, 'exists') as exists:
            assert install_supported('linux', machine)
        exists.assert_not_called()

    def test_linux_without_a_release(self):
        assert not install_supported('linux', 'armv7l')

    def test_macos_on_apple_silicon(self):
        assert install_supported('darwin', 'arm64')

    def test_macos_on_intel(self):
        assert not install_supported('darwin', 'x86_64')

    @pytest.mark.parametrize('system', ['win32', 'cygwin', 'freebsd14'])
    def test_other_platforms(self, system):
        assert not install_supported(system, 'x86_64')


class TestHostMachine:
    def sysctl(self, stdout='', returncode=0, error=None):
        if error is not None:
            return mock.Mock(side_effect=error)
        return mock.Mock(
            return_value=subprocess.CompletedProcess(
                [], returncode, stdout=stdout, stderr=''
            )
        )

    def host_machine(self, system, machine, run):
        with (
            mock.patch.object(platform, 'machine', return_value=machine),
            mock.patch.object(subprocess, 'run', run),
        ):
            return install_host._host_machine(system)

    @pytest.mark.parametrize(
        'system, machine', [('linux', 'x86_64'), ('darwin', 'arm64')]
    )
    def test_platform_machine_without_sysctl(self, system, machine):
        run = self.sysctl('1\n')
        assert self.host_machine(system, machine, run) == machine
        run.assert_not_called()

    def test_apple_silicon_under_rosetta_is_arm64(self):
        run = self.sysctl('1\n')
        assert self.host_machine('darwin', 'x86_64', run) == 'arm64'
        assert run.call_args.args[0] == [
            '/usr/sbin/sysctl',
            '-n',
            'hw.optional.arm64',
        ]

    @pytest.mark.parametrize(
        'run_kwargs',
        [
            # Intel Macs don't have the key.
            {'returncode': 1},
            {'stdout': '0\n'},
            {'error': OSError(2, 'No such file or directory')},
            {'error': subprocess.TimeoutExpired('sysctl', 5)},
        ],
    )
    def test_intel_mac_stays_x86_64(self, run_kwargs):
        run = self.sysctl(**run_kwargs)
        assert self.host_machine('darwin', 'x86_64', run) == 'x86_64'

    def test_install_looks_once_and_only_when_asked(self):
        command = InstallCredentialDaemonCommand(
            mock.Mock(), InstallHost(system='darwin')
        )
        with mock.patch.object(
            install_host, '_host_machine', return_value='arm64'
        ) as host_machine:
            assert command.host.machine == 'arm64'
            assert command.host.machine == 'arm64'
        host_machine.assert_called_once_with('darwin')

    def test_install_supported_on_apple_silicon_under_rosetta(self):
        with mock.patch.object(
            install_host, '_host_machine', return_value='arm64'
        ):
            assert install_supported('darwin')


@skip_if_windows  # os.getuid.
class TestRootOnlyProblem:
    def test_a_folder_that_cant_be_checked_is_a_problem(self, tmp_path):
        # A folder above credsd's program that lstat can't read counts as
        # not root-only, so the program isn't run as root.
        program = tmp_path / 'bin' / 'credsd'
        program.parent.mkdir()
        program.write_text('')
        program.chmod(0o755)
        real_lstat = os.lstat

        def lstat(path):
            if str(path) == str(program.parent):
                raise PermissionError(13, 'Permission denied')
            return real_lstat(path)

        with mock.patch.object(os, 'lstat', lstat):
            problem = install_host.root_only_problem(
                str(program), root=str(tmp_path), trusted_uid=os.getuid()
            )
        assert problem == ('error', str(program.parent), 'Permission denied')


@skip_if_windows
class TestSudoCommand:
    """Every Linux "needs root" message prints the plain command, whichever
    aws runs: the CLI doesn't work out which aws sudo would run."""

    @pytest.fixture(autouse=True)
    def user_venv_aws(self, tmp_path):
        # This aws is in a folder of the user's, such as a venv, so no
        # message may name its path.
        aws = tmp_path / 'home' / 'alice' / '.venv' / 'bin' / 'aws'
        aws.parent.mkdir(parents=True)
        aws.write_text('#!/bin/sh\n')
        aws.chmod(0o755)
        with mock.patch.object(install_host.sys, 'argv', [str(aws)]):
            yield

    @pytest.mark.parametrize('subcommand', ['install', 'uninstall'])
    def test_sudo_command_is_the_plain_command(self, subcommand):
        assert install_host.sudo_command(subcommand) == (
            f'sudo aws configure credential-daemon {subcommand}'
        )

    @pytest.mark.parametrize(
        'subcommand, needs_root',
        [
            (
                'install',
                'Installing aws-credential-daemon as a system service '
                'requires root, so nothing was downloaded or changed.',
            ),
            (
                'uninstall',
                "Uninstalling aws-credential-daemon's system service "
                'requires root, so nothing was changed.',
            ),
        ],
    )
    def test_the_refusal_prints_the_plain_command(
        self, subcommand, needs_root
    ):
        host = InstallHost(system='linux', is_root=False)
        with pytest.raises(ConfigurationError) as e:
            install_host.refuse_platform_or_user(subcommand, host)
        assert str(e.value) == (
            f'{needs_root} Run:\n'
            f'  sudo aws configure credential-daemon {subcommand}'
        )

    def test_the_proxy_hint_prints_the_plain_command(self):
        assert InstallHost(system='linux').proxy_hint() == (
            'Behind a proxy, keep its settings under sudo:\n'
            '  sudo --preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,'
            'AWS_CA_BUNDLE aws configure credential-daemon install\n'
            'If the proxy inspects TLS, also pass --ca-bundle with its CA '
            'file.'
        )


@skip_if_windows
class TestTempRoot:
    """/tmp, else /var/tmp, else 253, before
    anything is downloaded."""

    def host(self):
        return InstallHost(system='linux')

    def statvfs(self, noexec):
        def statvfs(path):
            flag = ST_NOEXEC if path in noexec else 0
            return mock.Mock(f_flag=flag)

        return statvfs

    def shared(self, path):
        return os.stat_result((0o41777, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    def test_tmp_when_it_can_run_programs(self):
        with (
            mock.patch.object(os, 'statvfs', self.statvfs(())),
            mock.patch.object(os, 'stat', self.shared),
        ):
            assert self.host().linux_temp_root() == '/tmp'

    def test_the_flag_is_defined_where_os_lacks_it(self):
        # macOS has no os.ST_NOEXEC; loading the module must not need it.
        saved = getattr(os, 'ST_NOEXEC', None)
        if saved is not None:
            del os.ST_NOEXEC
        try:
            reloaded = importlib.reload(install_host)
            assert reloaded.ST_NOEXEC == 8
        finally:
            if saved is not None:
                os.ST_NOEXEC = saved
            importlib.reload(install_host)

    def test_var_tmp_when_tmp_is_noexec(self):
        with (
            mock.patch.object(os, 'statvfs', self.statvfs(('/tmp',))),
            mock.patch.object(os, 'stat', self.shared),
        ):
            assert self.host().linux_temp_root() == '/var/tmp'

    def test_both_noexec_is_refused_before_the_download(self):
        runner = Runner()
        http = FakeHttp({})
        with (
            mock.patch.object(
                os, 'statvfs', self.statvfs(('/tmp', '/var/tmp'))
            ),
            mock.patch.object(os, 'stat', self.shared),
        ):
            with pytest.raises(ConfigurationError) as e:
                install(http=http, runner=runner, temp_root='auto')
        assert str(e.value) == (
            '/tmp and /var/tmp are mounted noexec or aren\'t shared temporary '
            'folders, so aws-credential-daemon\'s installer can\'t run from '
            'them. Nothing was downloaded.'
        )
        assert http.urls == []
        assert runner.commands == []

    def test_a_folder_only_root_can_write_isnt_used(self):
        # credsd wouldn't stage its own copy from there.
        def stat_(path):
            mode = 0o40755 if path == '/tmp' else 0o41777
            return os.stat_result((mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))

        with (
            mock.patch.object(os, 'statvfs', self.statvfs(())),
            mock.patch.object(os, 'stat', stat_),
        ):
            assert self.host().linux_temp_root() == '/var/tmp'


class TestInstallerWarnings:
    """On success, the installer's warning lines show."""

    def test_warnings_are_printed_on_success(self, capsys):
        def run(command, check=True):
            return subprocess.CompletedProcess(
                command,
                0,
                'installed\n',
                'info: staged\nwarning: TPM backend selected but the `tss` '
                'group does not exist; install tpm2-tss and re-run `credsd '
                'install`\n'
                'WARNING: \x1b[31mred\x1b[0m\n',
            )

        InstallHost(system='linux', run=run).run_installer(
            ['credsd', 'install']
        )
        assert capsys.readouterr().err == (
            'warning: TPM backend selected but the `tss` group does not '
            'exist; install tpm2-tss and re-run `credsd install`\n'
            'WARNING: [31mred[0m\n'
            'Then run: sudo aws configure credential-daemon install\n'
        )

    def test_the_staging_warning_is_left_out(self, capsys):
        # Install always runs the installer from a temp folder, so credsd
        # always stages: its warning would print on every install.
        def run(command, check=True):
            return subprocess.CompletedProcess(
                command, 0, '', STAGING_WARNING + 'info: done\n'
            )

        InstallHost(system='linux', run=run).run_installer(
            ['credsd', 'install']
        )
        assert capsys.readouterr().err == ''

    def test_a_warnings_continuation_lines_stay(self, capsys):
        def run(command, check=True):
            return subprocess.CompletedProcess(
                command,
                0,
                '',
                STAGING_WARNING + 'warning: first\n   second\n'
                'info: done\n   not a continuation\n',
            )

        InstallHost(system='linux', run=run).run_installer(
            ['credsd', 'install']
        )
        assert capsys.readouterr().err == 'warning: first\n   second\n'

    def test_a_warning_that_says_rerun_credsd_install_says_how(self, capsys):
        # credsd isn't on PATH; this command runs its installer and links.
        def run(command, check=True):
            return subprocess.CompletedProcess(
                command, 0, '', STAGING_WARNING + TSS_WARNING
            )

        InstallHost(system='linux', run=run).run_installer(
            ['credsd', 'install']
        )
        assert capsys.readouterr().err == (
            TSS_WARNING + 'Then run: sudo aws configure credential-daemon '
            'install\n'
        )

    def test_nothing_without_warnings(self, capsys):
        def run(command, check=True):
            return subprocess.CompletedProcess(command, 0, '', 'info: ok\n')

        InstallHost(run=run).run_installer(['credsd', 'install'])
        assert capsys.readouterr().err == ''


@skip_if_windows
class TestChildEnvironment:
    """What the programs install, uninstall and link run get."""

    CALLER = {
        'PATH': '/home/alice/bin:/usr/bin',
        'HOME': '/home/alice',
        'CREDSD_DATA_DIR': '/home/alice/credsd',
        'RUST_LOG': 'trace',
        'LD_LIBRARY_PATH': '/usr/local/aws-cli/v2/2.41.2/dist',
        'LD_PRELOAD': '/home/alice/x.so',
        'PYINSTALLER_RESET_ENVIRONMENT': '1',
        'https_proxy': 'http://proxy:3128',
        'LANG': 'de_DE.UTF-8',
    }

    def env(self, system):
        host = InstallHost(
            system=system, environ=dict(self.CALLER), root_home='/root'
        )
        with mock.patch.object(subprocess, 'run') as run:
            host.run(['/usr/bin/systemctl', 'daemon-reload'])
        return run.call_args.kwargs['env']

    def test_linux_children_get_a_fixed_environment(self):
        # They run as root: nothing comes from the caller (sudo -E).
        assert self.env('linux') == {
            'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
            'LC_ALL': 'C',
            'HOME': '/root',
        }

    def test_linux_roots_home_comes_from_its_passwd_entry(self):
        host = InstallHost(system='linux', environ={'HOME': '/home/alice'})
        with mock.patch.object(
            install_host, 'root_passwd_home', return_value='/var/root'
        ):
            assert host.child_environ()['HOME'] == '/var/root'

    def test_macos_children_get_the_users_environment_without_the_cli_libs(
        self,
    ):
        env = self.env('darwin')
        assert 'LD_LIBRARY_PATH' not in env
        assert env['CREDSD_DATA_DIR'] == '/home/alice/credsd'
        assert env['HOME'] == '/home/alice'

    def test_macos_children_get_the_users_own_library_path_back(self):
        caller = dict(self.CALLER, LD_LIBRARY_PATH_ORIG='/opt/lib')
        host = InstallHost(system='darwin', environ=caller)
        assert host.child_environ()['LD_LIBRARY_PATH'] == '/opt/lib'
        # The caller's environment itself is unchanged.
        assert caller['LD_LIBRARY_PATH'] == self.CALLER['LD_LIBRARY_PATH']

    def test_sysctl_runs_without_the_cli_libs(self):
        run = mock.Mock(
            return_value=subprocess.CompletedProcess([], 0, '1\n', '')
        )
        with (
            mock.patch.object(platform, 'machine', return_value='x86_64'),
            mock.patch.object(subprocess, 'run', run),
            mock.patch.dict(
                os.environ, {'LD_LIBRARY_PATH': '/usr/local/aws-cli/dist'}
            ),
        ):
            install_host._host_machine('darwin')
        assert 'LD_LIBRARY_PATH' not in run.call_args.kwargs['env']
