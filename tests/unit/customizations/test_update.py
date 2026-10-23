# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import ntpath
import os
import re
import subprocess
from argparse import Namespace
from types import SimpleNamespace
from unittest import mock

import pytest

from awscli.customizations import update as update_module
from awscli.customizations.update import (
    UnixUpdateCommand,
    UpdateError,
    WindowsUpdateCommand,
)
from tests.markers import skip_if_windows

USER_INSTALL = {
    'install_dir': '/home/user/.local/share/aws-cli',
    'bin_dir': '/home/user/.local/bin',
    'script_install': {'system': False},
}
SYSTEM_INSTALL = {
    'install_dir': '/usr/local/aws-cli',
    'bin_dir': '/usr/local/bin',
    'script_install': {'system': True},
}


WINDOWS_SYSTEM_DIR = 'C:\\Windows\\System32'


def global_args(color='auto'):
    return Namespace(color=color)


def mock_session():
    session = mock.Mock()
    session.user_agent_extra = 'aws-cli'
    # A real session returns None when no plugin overrides an arg value.
    session.emit_first_non_none_response.return_value = None
    return session


class TestUnixUpdateCommand:
    def _command(
        self,
        install,
        source='exe',
        elevated=True,
        runner=None,
        downloader=None,
        verifier=None,
    ):
        command = UnixUpdateCommand(
            mock_session(),
            source=source,
            install_metadata=install,
            downloader=downloader or mock.Mock(),
            is_elevated=elevated,
            runner=runner or mock.Mock(),
        )
        # Signature verification is exercised by TestUnixVerifyScript; here we
        # replace it so the behavioral tests don't shell out to gpg.
        command._verify_script = verifier or mock.Mock()
        return command

    def _run(self, install, color='auto', **kwargs):
        runner = mock.Mock()
        command = self._command(install, runner=runner, **kwargs)
        command([], global_args(color=color))
        return runner.call_args.args

    @pytest.mark.parametrize('source', ['exe', 'script-exe', 'update-exe'])
    def test_supported_distribution_source_runs_installer(self, source):
        runner = mock.Mock()
        command = self._command(USER_INSTALL, source=source, runner=runner)

        assert command([], global_args()) == 0
        runner.assert_called_once()

    def test_prints_agent_toolkit_tip_after_successful_update(self, capsys):
        command = self._command(USER_INSTALL)
        command([], global_args())
        assert 'aws configure agent-toolkit' in capsys.readouterr().out

    def test_install_script_tip_is_suppressed(self):
        # The install script prints the same tip, so we silence its copy and
        # print our own, otherwise the user sees it twice.
        _, env = self._run(USER_INSTALL)

        assert env['AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED'] == 'true'

    def test_no_agent_toolkit_tip_when_hint_disabled(
        self, capsys, monkeypatch
    ):
        monkeypatch.setenv('AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED', 'true')
        command = self._command(USER_INSTALL)
        command([], global_args())
        assert 'aws configure agent-toolkit' not in capsys.readouterr().out

    def test_no_agent_toolkit_tip_when_update_fails(self, capsys):
        runner = mock.Mock(side_effect=subprocess.CalledProcessError(1, 'x'))
        command = self._command(USER_INSTALL, runner=runner)
        with pytest.raises(UpdateError):
            command([], global_args())
        assert 'aws configure agent-toolkit' not in capsys.readouterr().out

    @pytest.mark.parametrize('source', ['source', 'other', 'pip', ''])
    def test_unsupported_distribution_source_raises(self, source):
        runner = mock.Mock()
        command = self._command(USER_INSTALL, source=source, runner=runner)

        with pytest.raises(UpdateError, match='Detected distribution source'):
            command([], global_args())
        runner.assert_not_called()

    def test_missing_install_dir_raises(self):
        runner = mock.Mock()
        command = self._command({}, runner=runner)

        with pytest.raises(
            UpdateError, match='Install-time metadata could not be found'
        ):
            command([], global_args())
        runner.assert_not_called()

    def test_user_install_runs_bash_script_without_system(self):
        cmd, _ = self._run(USER_INSTALL)

        assert cmd[0] == 'bash'
        assert cmd[1].endswith('install.sh')
        assert len(cmd) == 2

    def test_downloads_install_script_to_path_that_is_run(self):
        downloader = mock.Mock()
        runner = mock.Mock()
        command = self._command(
            USER_INSTALL, downloader=downloader, runner=runner
        )

        command([], global_args())

        url, dest = downloader.call_args.args
        assert url == UnixUpdateCommand.SCRIPT_URL
        assert runner.call_args.args[0] == ['bash', dest]

    def test_color_off_sets_no_color_env(self):
        _, env = self._run(USER_INSTALL, color='off')

        assert env['NO_COLOR'] == '1'

    @pytest.mark.parametrize('color', ['auto', 'on'])
    def test_color_not_off_omits_no_color_env(self, color):
        _, env = self._run(USER_INSTALL, color=color)

        assert 'NO_COLOR' not in env

    def test_user_install_sets_xdg_from_install_dir(self):
        _, env = self._run(USER_INSTALL)

        assert env['XDG_DATA_HOME'] == '/home/user/.local/share'
        assert env['XDG_BIN_HOME'] == '/home/user/.local/bin'
        assert env['AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE'] == 'update-exe'
        assert 'AWS_CLI_NO_BIN_DIR' not in env

    def test_missing_bin_dir_uses_throwaway_dir_and_flag(self):
        install = {
            'install_dir': '/home/user/.local/share/aws-cli',
            'script_install': {'system': False},
        }

        _, env = self._run(install)

        assert env['AWS_CLI_NO_BIN_DIR'] == '1'
        assert env['XDG_BIN_HOME'].endswith('bin')
        assert '.local/bin' not in env['XDG_BIN_HOME']

    def test_system_install_passes_system_flag(self):
        cmd, env = self._run(SYSTEM_INSTALL, elevated=True)

        assert cmd[0] == 'bash'
        assert cmd[1].endswith('install.sh')
        assert cmd[2] == '--system'
        assert len(cmd) == 3
        assert 'XDG_DATA_HOME' not in env
        assert 'XDG_BIN_HOME' not in env

    def test_forwards_skip_signature_verification_to_install_script(self):
        # --skip-signature-verification must be passed through to install.sh,
        # otherwise install.sh re-verifies and hard-fails when gpg is missing,
        # defeating the opt-out.
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command(['--skip-signature-verification'], global_args())
        cmd = runner.call_args.args[0]
        assert '--skip-signature-verification' in cmd

    def test_system_install_also_forwards_skip_flag(self):
        runner = mock.Mock()
        command = self._command(SYSTEM_INSTALL, elevated=True, runner=runner)
        command(['--skip-signature-verification'], global_args())
        cmd = runner.call_args.args[0]
        assert '--system' in cmd
        assert '--skip-signature-verification' in cmd

    def test_no_skip_flag_passed_by_default(self):
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command([], global_args())
        cmd = runner.call_args.args[0]
        assert '--skip-signature-verification' not in cmd

    def test_env_var_true_honored_as_skip(self, monkeypatch):
        # AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION=true is honored as a
        # version-independent opt-out, equivalent to the flag, and is forwarded
        # to the install script.
        monkeypatch.setenv(
            'AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION', 'true'
        )
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command([], global_args())
        assert '--skip-signature-verification' in runner.call_args.args[0]

    def test_env_var_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv(
            'AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION', 'TRUE'
        )
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command([], global_args())
        assert '--skip-signature-verification' in runner.call_args.args[0]

    def test_env_var_non_true_value_does_not_skip(self, monkeypatch):
        # Follows the ensure_boolean convention: only "true" enables it, so a
        # value like "1" must NOT disable verification.
        monkeypatch.setenv('AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION', '1')
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command([], global_args())
        assert '--skip-signature-verification' not in runner.call_args.args[0]

    def test_system_install_requires_elevation(self):
        runner = mock.Mock()
        command = self._command(SYSTEM_INSTALL, elevated=False, runner=runner)

        with pytest.raises(UpdateError, match='requires root'):
            command([], global_args())
        runner.assert_not_called()

    def test_install_script_failure_raises_update_error(self):
        runner = mock.Mock(
            side_effect=subprocess.CalledProcessError(8, ['bash'])
        )
        command = self._command(USER_INSTALL, runner=runner)

        with pytest.raises(UpdateError, match='exit code 8'):
            command([], global_args())

    @skip_if_windows
    def test_system_detected_from_binary_path_when_no_metadata(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            update_module.sys,
            'executable',
            '/usr/local/aws-cli/v2/current/bin/aws',
        )

        cmd, _ = self._run({'install_dir': '/usr/local/aws-cli'})

        assert '--system' in cmd

    @skip_if_windows
    def test_user_detected_from_binary_path_when_no_metadata(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            update_module.sys,
            'executable',
            '/home/user/.local/share/aws-cli/v2/current/bin/aws',
        )
        install = {
            'install_dir': '/home/user/.local/share/aws-cli',
            'bin_dir': '/home/user/.local/bin',
        }

        cmd, _ = self._run(install)

        assert '--system' not in cmd

    @skip_if_windows
    def test_resolves_symlink_before_checking_install_dir(
        self, monkeypatch, tmp_path
    ):
        root = tmp_path.resolve()
        install_dir = root / 'aws-cli'
        real_bin = install_dir / 'v2' / 'current' / 'bin' / 'aws'
        real_bin.parent.mkdir(parents=True)
        real_bin.touch()
        link = root / 'bin' / 'aws'
        link.parent.mkdir()
        link.symlink_to(real_bin)

        monkeypatch.setattr(
            UnixUpdateCommand, 'SYSTEM_INSTALL_DIR', str(install_dir)
        )
        monkeypatch.setattr(update_module.sys, 'executable', str(link))

        cmd, _ = self._run({'install_dir': str(install_dir)})

        assert '--system' in cmd


class TestWindowsUpdateCommand:
    def _command(
        self,
        install,
        elevated=True,
        runner=None,
        downloader=None,
        powershell_path='powershell.exe',
        verifier=None,
        system_directory=WINDOWS_SYSTEM_DIR,
    ):
        command = WindowsUpdateCommand(
            mock_session(),
            source='exe',
            install_metadata=install,
            downloader=downloader or mock.Mock(),
            is_elevated=elevated,
            runner=runner or mock.Mock(),
            powershell_path=powershell_path,
            system_directory=system_directory,
        )
        # Signature verification is exercised by TestWindowsVerifyScript; here
        # we replace it so the behavioral tests don't shell out to PowerShell.
        command._verify_script = verifier or mock.Mock()
        return command

    def _run(self, install, color='auto', **kwargs):
        cmd, _, wrapper = self._run_with_cwd(install, color=color, **kwargs)
        return cmd, wrapper

    def _run_with_cwd(self, install, color='auto', **kwargs):
        runner = mock.Mock()
        command = self._command(install, runner=runner, **kwargs)
        command([], global_args(color=color))
        cmd, cwd = runner.call_args.args
        with open(cmd[-1]) as f:
            return cmd, cwd, f.read()

    def test_spawns_detached_cmd_wrapper(self):
        cmd, _ = self._run(USER_INSTALL)

        assert cmd[0] == os.path.join(WINDOWS_SYSTEM_DIR, 'cmd.exe')
        assert cmd[1] == '/c'
        assert cmd[2].endswith('.cmd')
        assert len(cmd) == 3

    def test_runs_wrapper_from_its_temp_directory(self):
        cmd, cwd, _ = self._run_with_cwd(USER_INSTALL)

        assert cwd == os.path.dirname(cmd[-1])

    def test_wrapper_disables_current_directory_lookup(self):
        _, wrapper = self._run(USER_INSTALL)

        assert wrapper.startswith(
            '@echo off\nset NoDefaultCurrentDirectoryInExePath=1\n'
        )

    def test_wrapper_runs_ping_by_absolute_path(self):
        _, wrapper = self._run(USER_INSTALL)

        ping_exe = os.path.join(WINDOWS_SYSTEM_DIR, 'PING.EXE')
        assert f'"{ping_exe}" -n 3 127.0.0.1' in wrapper

    def test_prints_agent_toolkit_tip(self, capsys):
        command = self._command(USER_INSTALL)
        command([], global_args())
        assert 'aws configure agent-toolkit' in capsys.readouterr().out

    def test_downloads_install_script_referenced_by_wrapper(self):
        downloader = mock.Mock()
        _, wrapper = self._run(USER_INSTALL, downloader=downloader)

        url, dest = downloader.call_args.args
        assert url == WindowsUpdateCommand.SCRIPT_URL
        assert f'-File "{dest}"' in wrapper

    def test_wrapper_runs_powershell_without_system(self):
        _, wrapper = self._run(USER_INSTALL)

        assert 'set AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE=update-exe' in wrapper
        assert '"powershell.exe" -NoProfile -File "' in wrapper
        assert '-System' not in wrapper
        assert 'set NO_COLOR=1' not in wrapper

    def test_wrapper_passes_system_flag(self):
        _, wrapper = self._run(SYSTEM_INSTALL, elevated=True)

        assert wrapper.rstrip().endswith('-System')

    def test_wrapper_forwards_skip_signature_verification(self):
        runner = mock.Mock()
        command = self._command(USER_INSTALL, runner=runner)
        command(['--skip-signature-verification'], global_args())
        cmd, _ = runner.call_args.args
        with open(cmd[-1]) as f:
            wrapper = f.read()
        assert '-SkipSignatureVerification' in wrapper

    def test_wrapper_omits_skip_flag_by_default(self):
        _, wrapper = self._run(USER_INSTALL)

        assert '-SkipSignatureVerification' not in wrapper

    def test_wrapper_sets_no_color_when_color_off(self):
        _, wrapper = self._run(USER_INSTALL, color='off')

        assert 'set NO_COLOR=1' in wrapper

    def test_wrapper_clears_psmodulepath(self):
        _, wrapper = self._run(USER_INSTALL)

        assert 'set PSModulePath=\n' in wrapper

    @pytest.fixture
    def path_dirs(self, tmp_path, monkeypatch):
        windows_ps = tmp_path / 'WindowsPowerShell'
        pwsh_dir = tmp_path / 'PowerShell7'
        planted = tmp_path / 'planted'
        for d in (windows_ps, pwsh_dir, planted):
            d.mkdir()
        self.system_dir = tmp_path / 'System32'
        self.system_dir.mkdir()
        monkeypatch.chdir(planted)
        monkeypatch.setenv(
            'PATH', os.pathsep.join([str(windows_ps), str(pwsh_dir)])
        )
        return windows_ps, pwsh_dir, planted

    def _find(self, **kwargs):
        kwargs.setdefault('system_directory', str(self.system_dir))
        _, wrapper = self._run(USER_INSTALL, powershell_path=None, **kwargs)
        return wrapper

    def _install_system_powershell(self):
        return _touch(
            self.system_dir / 'WindowsPowerShell' / 'v1.0', 'powershell.exe'
        )

    def test_falls_back_to_system_directory_when_not_on_path(
        self, path_dirs, monkeypatch
    ):
        monkeypatch.setenv('PATH', '')
        powershell = self._install_system_powershell()

        assert f'"{powershell}" -NoProfile' in self._find()

    def test_prefers_pwsh_on_path_over_system_directory(self, path_dirs):
        _, pwsh_dir, _ = path_dirs
        pwsh = _touch(pwsh_dir, 'pwsh.exe')
        self._install_system_powershell()

        assert f'"{pwsh}" -NoProfile' in self._find()

    def test_prefers_windows_powershell_over_earlier_pwsh(
        self, path_dirs, monkeypatch
    ):
        windows_ps, pwsh_dir, _ = path_dirs
        powershell = _touch(windows_ps, 'powershell.exe')
        _touch(pwsh_dir, 'pwsh.exe')
        monkeypatch.setenv(
            'PATH', os.pathsep.join([str(pwsh_dir), str(windows_ps)])
        )

        assert f'"{powershell}" -NoProfile' in self._find()

    def test_falls_back_to_pwsh_when_windows_powershell_missing(
        self, path_dirs
    ):
        _, pwsh_dir, _ = path_dirs
        pwsh = _touch(pwsh_dir, 'pwsh.exe')

        assert f'"{pwsh}" -NoProfile' in self._find()

    def test_finds_powershell_in_quoted_path_entry(
        self, path_dirs, monkeypatch
    ):
        windows_ps, _, _ = path_dirs
        powershell = _touch(windows_ps, 'powershell.exe')
        monkeypatch.setenv('PATH', f'"{windows_ps}"')

        assert f'"{powershell}" -NoProfile' in self._find()

    def test_raises_when_no_powershell_found(self, path_dirs):
        command = self._command(
            USER_INSTALL,
            powershell_path=None,
            system_directory=str(self.system_dir),
        )

        with pytest.raises(UpdateError, match='Neither powershell'):
            command([], global_args())

    def test_ignores_executables_planted_in_cwd(self, path_dirs):
        # Guards against reintroducing shutil.which(), which searches the cwd
        # on Windows.
        windows_ps, _, planted = path_dirs
        powershell = _touch(windows_ps, 'powershell.exe')
        for name in (
            'powershell.cmd',
            'powershell.exe',
            'pwsh.cmd',
            'pwsh.exe',
        ):
            _touch(planted, name)

        wrapper = self._find()

        assert f'"{powershell}" -NoProfile' in wrapper
        assert str(planted) not in wrapper

    @pytest.mark.parametrize('entry', ['', '.', 'planted'])
    def test_ignores_relative_path_entries(
        self, entry, path_dirs, monkeypatch
    ):
        # Empty and relative PATH entries resolve against the cwd.
        windows_ps, _, planted = path_dirs
        _touch(planted, 'powershell.exe')
        _touch(planted / 'planted', 'powershell.exe')
        pwsh = _touch(windows_ps, 'pwsh.exe')
        monkeypatch.setenv('PATH', os.pathsep.join([entry, str(windows_ps)]))

        assert f'"{pwsh}" -NoProfile' in self._find()

    @pytest.mark.parametrize(
        'entry, expected',
        [
            ('C:\\Tools', True),
            ('C:/Tools', True),
            ('\\\\server\\share\\Tools', True),
            ('\\Tools', False),
            ('/Tools', False),
            ('C:Tools', False),
            ('Tools', False),
            ('', False),
        ],
    )
    def test_windows_path_entry_requires_drive_or_share(
        self, entry, expected, monkeypatch
    ):
        # Simulate ntpath.isabs() before Python 3.13, which also accepts
        # root-relative paths such as "\Tools".
        def isabs(path):
            return path[:1] in ('\\', '/') or ntpath.isabs(path)

        fake_os = SimpleNamespace(
            name='nt',
            path=SimpleNamespace(isabs=isabs, splitdrive=ntpath.splitdrive),
        )
        monkeypatch.setattr(update_module, 'os', fake_os)
        command = self._command(USER_INSTALL)

        assert command._is_absolute_path(entry) is expected

    def test_only_accepts_exe_on_path(self, path_dirs):
        windows_ps, pwsh_dir, _ = path_dirs
        _touch(windows_ps, 'powershell.cmd')
        pwsh = _touch(pwsh_dir, 'pwsh.exe')

        assert f'"{pwsh}" -NoProfile' in self._find()

    def test_run_install_uses_cwd_and_disables_current_directory_lookup(
        self, monkeypatch
    ):
        popen = mock.Mock()
        monkeypatch.setattr(update_module.subprocess, 'Popen', popen)
        # DETACHED_PROCESS and CREATE_NEW_PROCESS_GROUP only exist on Windows.
        monkeypatch.setattr(
            update_module.subprocess, 'DETACHED_PROCESS', 0x8, raising=False
        )
        monkeypatch.setattr(
            update_module.subprocess,
            'CREATE_NEW_PROCESS_GROUP',
            0x200,
            raising=False,
        )
        command = self._command(USER_INSTALL)

        command._run_install(['cmd.exe', '/c', 'wrapper.cmd'], 'C:\\tmp')

        kwargs = popen.call_args.kwargs
        assert kwargs['cwd'] == 'C:\\tmp'
        assert kwargs['env']['NoDefaultCurrentDirectoryInExePath'] == '1'

    def test_raises_when_system_directory_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            update_module, 'ctypes', _fake_system_directory_ctypes('', 0)
        )
        command = self._command(USER_INSTALL, system_directory=None)

        with pytest.raises(UpdateError, match='system directory'):
            command._get_system_directory()

    def test_system_install_requires_elevation(self):
        runner = mock.Mock()
        command = self._command(SYSTEM_INSTALL, elevated=False, runner=runner)

        with pytest.raises(UpdateError, match='elevated shell'):
            command([], global_args())
        runner.assert_not_called()

    def test_system_detected_from_program_files_when_no_metadata(
        self, monkeypatch
    ):
        program_files = 'C:\\Program Files'
        monkeypatch.setattr(
            update_module.os, 'environ', {'ProgramW6432': program_files}
        )
        running_exe = update_module.os.path.join(
            program_files, 'Amazon', 'AWSCLIV2', 'aws.exe'
        )
        monkeypatch.setattr(update_module, 'ctypes', _fake_ctypes(running_exe))

        _, wrapper = self._run(
            {'install_dir': 'C:\\Program Files\\Amazon\\AWSCLIV2'}
        )

        assert wrapper.rstrip().endswith('-System')

    def test_user_detected_from_program_files_when_no_metadata(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            update_module.os, 'environ', {'ProgramW6432': 'C:\\Program Files'}
        )
        running_exe = update_module.os.path.join(
            'C:\\Users\\me\\AppData\\Local\\Programs',
            'Amazon',
            'AWSCLIV2',
            'aws.exe',
        )
        monkeypatch.setattr(update_module, 'ctypes', _fake_ctypes(running_exe))

        _, wrapper = self._run({'install_dir': 'C:\\Users\\me\\AWSCLIV2'})

        assert '-System' not in wrapper


class TestUnixVerifyScript:
    def _command(self, runner=None, downloader=None):
        # Note: does NOT mock _verify_script -- these tests exercise it.
        return UnixUpdateCommand(
            mock_session(),
            source='exe',
            install_metadata=USER_INSTALL,
            downloader=downloader or mock.Mock(),
            is_elevated=True,
            runner=runner or mock.Mock(),
        )

    def test_skips_verification_with_flag(self, monkeypatch):
        which = mock.Mock()
        run = mock.Mock()
        monkeypatch.setattr(update_module.shutil, 'which', which)
        monkeypatch.setattr(update_module.subprocess, 'run', run)
        runner = mock.Mock()
        command = self._command(runner=runner)

        command(['--skip-signature-verification'], global_args())

        which.assert_not_called()
        run.assert_not_called()
        runner.assert_called_once()

    def test_missing_gpg_raises(self, monkeypatch):
        monkeypatch.setattr(update_module.shutil, 'which', lambda name: None)
        runner = mock.Mock()
        command = self._command(runner=runner)

        with pytest.raises(UpdateError, match='gpg was not found'):
            command([], global_args())
        runner.assert_not_called()

    def test_verifies_and_runs_on_success(self, monkeypatch):
        monkeypatch.setattr(
            update_module.shutil, 'which', lambda name: '/usr/bin/gpg'
        )
        run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=''))
        monkeypatch.setattr(update_module.subprocess, 'run', run)
        downloader = mock.Mock()
        runner = mock.Mock()
        command = self._command(runner=runner, downloader=downloader)

        command([], global_args())

        downloaded = [c.args[0] for c in downloader.call_args_list]
        assert UnixUpdateCommand.SCRIPT_URL + '.sig' in downloaded
        assert any('--verify' in c.args[0] for c in run.call_args_list)
        runner.assert_called_once()

    def test_verification_failure_raises(self, monkeypatch):
        monkeypatch.setattr(
            update_module.shutil, 'which', lambda name: '/usr/bin/gpg'
        )

        def fake_run(cmd, **kwargs):
            returncode = 1 if '--verify' in cmd else 0
            return mock.Mock(returncode=returncode, stderr='bad signature')

        monkeypatch.setattr(update_module.subprocess, 'run', fake_run)
        runner = mock.Mock()
        command = self._command(runner=runner)

        with pytest.raises(UpdateError, match='signature verification failed'):
            command([], global_args())
        runner.assert_not_called()


class TestWindowsVerifyScript:
    def _command(self, runner=None, downloader=None):
        # Note: does NOT mock _verify_script -- these tests exercise it.
        return WindowsUpdateCommand(
            mock_session(),
            source='exe',
            install_metadata=USER_INSTALL,
            downloader=downloader or mock.Mock(),
            is_elevated=True,
            runner=runner or mock.Mock(),
            powershell_path='powershell.exe',
            system_directory=WINDOWS_SYSTEM_DIR,
        )

    def test_skips_verification_with_flag(self, monkeypatch):
        run = mock.Mock()
        monkeypatch.setattr(update_module.subprocess, 'run', run)
        runner = mock.Mock()
        command = self._command(runner=runner)

        command(['--skip-signature-verification'], global_args())

        run.assert_not_called()
        runner.assert_called_once()

    def test_verifies_and_runs_on_success(self, monkeypatch):
        run = mock.Mock(
            return_value=mock.Mock(returncode=0, stdout='', stderr='')
        )
        monkeypatch.setattr(update_module.subprocess, 'run', run)
        runner = mock.Mock()
        command = self._command(runner=runner)

        command([], global_args())

        ps_cmd = ' '.join(run.call_args.args[0])
        assert 'Get-AuthenticodeSignature' in ps_cmd
        runner.assert_called_once()

    def test_verification_failure_raises(self, monkeypatch):
        run = mock.Mock(
            return_value=mock.Mock(
                returncode=1, stdout='', stderr='not signed by AWS'
            )
        )
        monkeypatch.setattr(update_module.subprocess, 'run', run)
        runner = mock.Mock()
        command = self._command(runner=runner)

        with pytest.raises(UpdateError, match='signature verification failed'):
            command([], global_args())
        runner.assert_not_called()

    def test_verify_subprocess_clears_psmodulepath(self, monkeypatch):
        # The verification PowerShell invocation must not inherit PSModulePath;
        # inheriting it can break module resolution across PS5/PS7.
        # https://github.com/aws/aws-cli/issues/10532
        monkeypatch.setenv('PSModulePath', 'C:\\inherited\\modules')
        captured = {}

        def fake_run(cmd, **kwargs):
            captured['env'] = kwargs.get('env')
            return mock.Mock(returncode=0, stdout='', stderr='')

        monkeypatch.setattr(update_module.subprocess, 'run', fake_run)
        command = self._command(runner=mock.Mock())

        command([], global_args())

        assert 'PSModulePath' not in captured['env']

    def test_verification_matches_org_exactly(self, monkeypatch):
        # The signer check must gate on an exact match of the certificate's
        # Organization (O) RDN, not a substring of the whole subject DN: a
        # substring match would also accept a DigiCert-issued cert whose CN/OU
        # merely contained one of the allowlisted org strings. The PowerShell
        # logic itself is exercised out-of-band (it needs a real
        # Get-AuthenticodeSignature); here we lock in the shape of the emitted
        # command so the fragile substring form cannot silently return.
        captured = {}

        def fake_run(cmd, **kwargs):
            captured['ps'] = cmd[cmd.index('-Command') + 1]
            return mock.Mock(returncode=0, stdout='', stderr='')

        monkeypatch.setattr(update_module.subprocess, 'run', fake_run)
        command = self._command(runner=mock.Mock())

        command([], global_args())

        ps = captured['ps']
        # Exact O-RDN match against the allowlist.
        assert '-notcontains $subjectOrg' in ps
        assert 'Get-Org' in ps
        # Format($true) quotes comma-bearing O values (e.g. "Amazon Web
        # Services, Inc."); the surrounding quote pair must be stripped so the
        # value matches the plain allowlist entry.
        assert '-replace' in ps
        # The previous whole-subject substring check must be gone.
        assert '$cert.Subject -like' not in ps


def _touch(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text('')
    return str(path)


def _fake_system_directory_ctypes(value, length):
    fake_ctypes = mock.Mock()
    buf = mock.MagicMock(value=value)
    buf.__len__.return_value = 260
    fake_ctypes.create_unicode_buffer.return_value = buf
    fake_ctypes.windll.kernel32.GetSystemDirectoryW.return_value = length
    return fake_ctypes


def _response(status_code, content=b''):
    return mock.Mock(status_code=status_code, content=content)


class TestDownloadWithRetry:
    def test_sends_get_request_for_url(self, tmp_path):
        session = mock.Mock()
        session.send.return_value = _response(200, b'data')

        update_module.download_with_retry(
            'https://foo.bar/install.sh',
            str(tmp_path / 'install.sh'),
            session=session,
        )

        request = session.send.call_args.args[0]
        assert request.method == 'GET'
        assert request.url == 'https://foo.bar/install.sh'

    def test_writes_response_content_to_dest(self, tmp_path):
        session = mock.Mock()
        session.send.return_value = _response(200, b'#!/bin/sh\n')
        dest = tmp_path / 'install.sh'

        update_module.download_with_retry(
            'https://foo.bar/install.sh', str(dest), session=session
        )

        assert dest.read_bytes() == b'#!/bin/sh\n'

    def test_retries_once_then_succeeds(self, tmp_path):
        session = mock.Mock()
        session.send.side_effect = [
            ConnectionError('boom'),
            _response(200, b'ok'),
        ]
        dest = tmp_path / 'install.sh'

        update_module.download_with_retry(
            'https://foo.bar/install.sh', str(dest), session=session
        )

        assert dest.read_bytes() == b'ok'
        assert session.send.call_count == 2

    def test_non_200_status_raises(self, tmp_path):
        session = mock.Mock()
        session.send.return_value = _response(404)

        with pytest.raises(UpdateError, match='unexpected HTTP status 404'):
            update_module.download_with_retry(
                'https://foo.bar/install.sh',
                str(tmp_path / 'install.sh'),
                session=session,
            )

    def test_raises_after_retries_exhausted(self, tmp_path):
        session = mock.Mock()
        session.send.side_effect = ConnectionError('boom')

        with pytest.raises(UpdateError, match='failed to download'):
            update_module.download_with_retry(
                'https://foo.bar/install.sh',
                str(tmp_path / 'install.sh'),
                retries=1,
                session=session,
            )
        assert session.send.call_count == 2

    def test_honors_retry_count(self, tmp_path):
        session = mock.Mock()
        session.send.side_effect = ConnectionError('boom')

        with pytest.raises(UpdateError):
            update_module.download_with_retry(
                'https://foo.bar/install.sh',
                str(tmp_path / 'install.sh'),
                retries=3,
                session=session,
            )
        assert session.send.call_count == 4


_INSTALL_SH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        '..',
        'scripts',
        'install-v2',
        'install.sh',
    )
)
_PGP_BLOCK_RE = re.compile(
    r'-----BEGIN PGP PUBLIC KEY BLOCK-----'
    r'.*?'
    r'-----END PGP PUBLIC KEY BLOCK-----',
    re.DOTALL,
)


def test_embedded_pgp_key_matches_install_script():
    # update.py embeds its own copy of the AWS CLI signing key because it
    # cannot read install.sh at runtime (the script is standalone and scripts/
    # is not shipped in the package). This test guards against the two copies
    # drifting apart.
    with open(_INSTALL_SH, encoding='utf-8') as f:
        install_sh = f.read()
    match = _PGP_BLOCK_RE.search(install_sh)
    assert match is not None, 'no PGP key block found in install.sh'
    assert (
        match.group(0) == update_module.AWS_CLI_PGP_KEY
    ), 'AWS_CLI_PGP_KEY in update.py does not match install.sh; update both.'


def _fake_ctypes(module_filename):
    buf = mock.MagicMock()
    buf.value = module_filename
    buf.__len__.return_value = 32768
    fake = mock.Mock()
    fake.create_unicode_buffer.return_value = buf
    return fake
