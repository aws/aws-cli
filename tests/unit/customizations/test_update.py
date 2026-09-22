# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
import re
import subprocess
from argparse import Namespace
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
    ):
        command = WindowsUpdateCommand(
            mock_session(),
            source='exe',
            install_metadata=install,
            downloader=downloader or mock.Mock(),
            is_elevated=elevated,
            runner=runner or mock.Mock(),
            powershell_path=powershell_path,
        )
        # Signature verification is exercised by TestWindowsVerifyScript; here
        # we replace it so the behavioral tests don't shell out to PowerShell.
        command._verify_script = verifier or mock.Mock()
        return command

    def _run(self, install, color='auto', **kwargs):
        runner = mock.Mock()
        command = self._command(install, runner=runner, **kwargs)
        command([], global_args(color=color))
        (cmd,) = runner.call_args.args
        with open(cmd[-1]) as f:
            return cmd, f.read()

    def test_spawns_detached_cmd_wrapper(self):
        cmd, _ = self._run(USER_INSTALL)

        assert cmd[0] == 'cmd'
        assert cmd[1] == '/c'
        assert cmd[2].endswith('.cmd')
        assert len(cmd) == 3

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

    def test_wrapper_sets_no_color_when_color_off(self):
        _, wrapper = self._run(USER_INSTALL, color='off')

        assert 'set NO_COLOR=1' in wrapper

    def test_wrapper_clears_psmodulepath(self):
        _, wrapper = self._run(USER_INSTALL)

        assert 'set PSModulePath=\n' in wrapper

    def test_prefers_windows_powershell_when_available(self, monkeypatch):
        def which(name):
            return {
                'powershell': 'C:\\powershell.exe',
                'pwsh': 'C:\\pwsh.exe',
            }.get(name)

        monkeypatch.setattr(update_module.shutil, 'which', which)

        _, wrapper = self._run(USER_INSTALL, powershell_path=None)

        assert '"C:\\powershell.exe" -NoProfile' in wrapper

    def test_falls_back_to_pwsh_when_windows_powershell_missing(
        self, monkeypatch
    ):
        def which(name):
            return 'C:\\pwsh.exe' if name == 'pwsh' else None

        monkeypatch.setattr(update_module.shutil, 'which', which)

        _, wrapper = self._run(USER_INSTALL, powershell_path=None)

        assert '"C:\\pwsh.exe" -NoProfile' in wrapper

    def test_raises_when_no_powershell_found(self, monkeypatch):
        def which(name):
            return None

        monkeypatch.setattr(update_module.shutil, 'which', which)
        command = self._command(USER_INSTALL, powershell_path=None)

        with pytest.raises(UpdateError, match='Neither powershell'):
            command([], global_args())

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
