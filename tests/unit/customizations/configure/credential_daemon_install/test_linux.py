# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
from argparse import Namespace

import pytest

from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
)
from awscli.customizations.configure.credential_daemon_install.linux import (
    LinuxInstall,
    _unit_exec_lines,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    extract_safely,
)
from awscli.customizations.configure.credentialdaemon import (
    InstallCredentialDaemonCommand,
    UninstallCredentialDaemonCommand,
)
from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.exceptions import (
    ConfigurationError,
)
from awscli.errorhandler import construct_cli_error_handlers_chain
from tests import mock
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    DOWNLOAD,
    GLOBALS,
    STAGED,
    Runner,
    UninstallRunner,
    archive,
    install,
    install_cli,
    linux_http,
    uninstall,
    validsig,
    write,
)

# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'

pytestmark = skip_if_windows

SUBKEY = 'FEDCBA9876543210FEDCBA9876543210FEDCBA98'


def temp_dir(runner, temp_root=None):
    """The folder install downloaded into, from the installer's path."""
    temp_root = temp_root or runner.root
    credential_daemon = next(
        c[0] for c in runner.commands if c[1:] == ['install']
    )
    relative = os.path.relpath(credential_daemon, temp_root)
    return os.path.join(temp_root, relative.split(os.sep)[0])


def kept_report(tmp, root=None, runs_from=True):
    """What install prints when it keeps tmp, with root's units in it if
    they don't run the staged copy, and the warning if they run from tmp."""
    if root is None:
        return (
            f'Kept on this machine:\n  {tmp}\nRemove it with:\n'
            f'  sudo rm -r {tmp}\n'
        )
    socket = os.path.join(root, 'etc/systemd/system/credsd.socket')
    service = os.path.join(root, 'etc/systemd/system/credsd.service')
    if runs_from:
        warning = (
            f'A reboot or /tmp cleanup deletes {tmp}, and then anyone can '
            'put a program at the path credsd.service runs. Remove them '
            'now:\n'
        )
    else:
        warning = 'Remove them with:\n'
    return (
        f'Kept on this machine:\n  {tmp}\n  {socket}\n  {service}\n'
        + warning
        + '  sudo systemctl disable --now credsd.socket credsd.service\n'
        f'  sudo rm {socket} {service}\n'
        '  sudo systemctl daemon-reload\n'
        f'  sudo rm -r {tmp}\n'
    )


def ran_version(runner):
    """Whether any `<program> --version` ran."""
    return any(c[1:] == ['--version'] for c in runner.commands)


def lasting_runner(tmp_path, cls=None, **kwargs):
    """A runner whose root and temp root outlive install(), so a test
    can check what the rollback removed."""
    runner = (cls or Runner)(**kwargs)
    runner.root = str(tmp_path / 'root')
    runner.temp_root = str(tmp_path / 'tmp')
    os.makedirs(runner.root)
    os.makedirs(runner.temp_root)
    return runner


# systemctl show's arguments for the staging check.
SERVICE_SHOW = [
    'show',
    '-p',
    'ExecStartPre,ExecStart,ExecStartPost,ExecReload,ExecStop,'
    'ExecStopPost,DropInPaths,FragmentPath,NeedDaemonReload',
    'credsd.service',
]


class TestLinux:
    def test_installs_after_the_signature_verifies(self, pinned_key, capsys):
        runner = Runner()
        assert install(http=linux_http(), runner=runner) == 0
        (
            gpg_import,
            gpg_verify,
            version,
            credential_daemon_install,
            show,
        ) = runner.commands
        assert '--import' in gpg_import
        assert gpg_verify[-5:-2] == ['--status-fd', '1', '--verify']
        # Saved under fixed names, not the release's asset names.
        assert os.path.basename(gpg_verify[-2]) == (
            'aws-credential-daemon.tar.gz.sig'
        )
        assert os.path.basename(gpg_verify[-1]) == (
            'aws-credential-daemon.tar.gz'
        )
        # Only the release's own folder's credsd, checked before it
        # installs.
        assert version[0].endswith('/release/credsd-linux-x64-tpm/credsd')
        assert version[1:] == ['--version']
        assert credential_daemon_install == [version[0], 'install']
        # What systemd will run, drop-ins included.
        assert show[1:] == SERVICE_SHOW
        out = capsys.readouterr().out
        assert (
            'Downloading aws-credential-daemon from '
            'github.com/aws/credential-daemon...\n'
        ) in out
        assert 'Installed aws-credential-daemon as a system service.' in out
        assert 'Your next sign-in will ask' in out

    def test_runs_the_installer_from_a_new_private_dir_under_tmp(
        self, pinned_key, tmp_path
    ):
        seen = {}

        class Recording(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[1:] == ['install']:
                    top = os.path.relpath(command[0], str(tmp_path))
                    folder = tmp_path / top.split(os.sep)[0]
                    seen['mode'] = stat.S_IMODE(folder.stat().st_mode)
                    seen['owner'] = folder.stat().st_uid
                    seen['folder'] = folder
                return super().__call__(command, check)

        runner = Recording()
        rc = install(
            http=linux_http(),
            runner=runner,
            temp_root=str(tmp_path),
        )
        assert rc == 0
        assert runner.commands[-2][0].startswith(f'{tmp_path}{os.sep}')
        assert seen['mode'] == 0o700
        assert seen['owner'] == os.getuid()
        # Removed once the install is done.
        assert not seen['folder'].exists()

    def test_the_temp_dir_is_under_tmp_whatever_tmpdir_says(self):
        command = InstallCredentialDaemonCommand(mock.Mock())
        shared = os.stat_result((0o41777, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        with (
            mock.patch.dict(os.environ, {'TMPDIR': '/root/private'}),
            mock.patch.object(os, 'statvfs', return_value=mock.Mock(f_flag=0)),
            mock.patch.object(os, 'stat', return_value=shared),
        ):
            assert command.host.linux_temp_root() == '/tmp'

    def test_a_service_that_runs_our_temp_copy_is_rolled_back(
        self, pinned_key, capsys
    ):
        # aws-credential-daemon didn't stage, so its service runs the copy in
        # our temp directory, whose path anyone can recreate once it's removed.
        runner = Runner(exec_start='self')
        rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        credential_daemon = runner.commands[2][0]
        service = os.path.join(
            runner.root, 'etc/systemd/system/credsd.service'
        )
        captured = capsys.readouterr()
        assert captured.err == PREVIEW_LINE + (
            'aws-credential-daemon\'s installer didn\'t set up its '
            f'service as expected: {service} runs {credential_daemon}, not '
            '/usr/local/libexec/credsd/credsd.\n'
            'The CLI stopped and removed aws-credential-daemon\'s '
            'service and socket (credsd.socket and credsd.service). Its '
            'uninstaller keeps its system account, /var/lib/credsd and '
            '/var/log/credsd.\n'
        )
        assert 'Installed aws-credential-daemon' not in captured.out

    def test_rollback_disables_then_uninstalls_before_cleanup(
        self, pinned_key, tmp_path
    ):
        runner = lasting_runner(tmp_path, exec_start='self')
        assert (
            install_cli(
                http=linux_http(),
                runner=runner,
                temp_root=runner.temp_root,
            )
            == 253
        )
        credential_daemon = runner.commands[3][0]
        # The unit file's own text fails the staging check, so systemd
        # isn't asked; the rollback comes next.
        after_install = runner.commands[4:]
        disable, uninstall = after_install[:2]
        assert os.path.basename(disable[0]) == 'systemctl'
        # The socket first, so it can't start the service again.
        assert disable[1:] == [
            'disable',
            '--now',
            'credsd.socket',
            'credsd.service',
        ]
        assert uninstall == [credential_daemon, 'uninstall']
        # Our temp copy still existed when it ran, and is gone after.
        assert runner.uninstaller_existed == [True]
        assert not os.path.exists(credential_daemon)
        units = os.path.join(runner.root, 'etc/systemd/system')
        assert not os.path.exists(f'{units}/credsd.service')
        assert not os.path.exists(f'{units}/credsd.socket')
        assert [c[1:] for c in after_install[2:]] == [
            [
                'show',
                '-p',
                'LoadState,UnitFileState,ActiveState',
                'credsd.socket',
                'credsd.service',
            ],
        ]

    def test_failed_rollback_says_what_is_left_and_exits_253(
        self, pinned_key, capsys
    ):
        runner = Runner(
            exec_start='self',
            disable_error='Access denied\x1b[2J',
            uninstall_error='boom',
            unit_states={
                'show': (
                    'LoadState=loaded\nActiveState=active\n'
                    'UnitFileState=enabled\n\n'
                    'LoadState=loaded\nActiveState=inactive\n'
                    'UnitFileState=static\n'
                ),
            },
        )
        rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        credential_daemon = runner.commands[2][0]
        units = os.path.join(runner.root, 'etc/systemd/system')
        captured = capsys.readouterr()
        assert captured.err == PREVIEW_LINE + (
            'aws-credential-daemon\'s installer didn\'t set up its '
            f'service as expected: {units}/credsd.service runs '
            f'{credential_daemon}, '
            'not /usr/local/libexec/credsd/credsd.\n'
            'The CLI couldn\'t undo the install. Still there:\n'
            '  credsd.socket: enabled\n'
            '  credsd.socket: active\n'
            '  credsd.service: static\n'
            f'  {units}/credsd.socket\n'
            f'  {units}/credsd.service\n'
            '  (systemctl disable --now failed: Access denied[2J)\n'
            '  (aws-credential-daemon\'s uninstaller failed: boom)\n'
            + kept_report(temp_dir(runner), runner.root)
        )
        assert 'Installed aws-credential-daemon' not in captured.out

    def test_failed_rollback_keeps_the_folder_the_units_run_from(
        self, pinned_key, tmp_path
    ):
        # Otherwise anyone could recreate the path the unit left behind
        # runs.
        runner = Runner(
            exec_start='self', disable_error='denied', uninstall_error='boom'
        )
        temp_root = tmp_path / 'tmp'
        temp_root.mkdir()
        rc = install_cli(
            http=linux_http(),
            runner=runner,
            temp_root=str(temp_root),
        )
        assert rc == 253
        credential_daemon = runner.commands[2][0]
        assert os.path.exists(credential_daemon)
        kept = temp_dir(runner, str(temp_root))
        assert stat.S_IMODE(os.stat(kept).st_mode) == 0o700

    def test_an_interrupted_rollback_keeps_the_folder_the_units_run_from(
        self, pinned_key, tmp_path
    ):
        # Ctrl-C while `systemctl disable --now` runs: credsd.service is
        # still enabled and runs our copy, so its folder must stay.
        runner = InterruptedRollbackRunner(exec_start='self')
        temp_root = tmp_path / 'tmp'
        temp_root.mkdir()
        with pytest.raises(KeyboardInterrupt):
            install(
                http=linux_http(),
                runner=runner,
                temp_root=str(temp_root),
            )
        credential_daemon = runner.commands[2][0]
        assert (
            f'ExecStart="{credential_daemon}"' in runner.service_at_interrupt
        )
        assert os.path.exists(credential_daemon)

    def test_an_interrupted_staging_check_keeps_the_folder(
        self, pinned_key, tmp_path
    ):
        # Between a successful install and the check, nothing has shown
        # that no unit runs our copy.
        runner = Runner(exec_start='self')
        temp_root = tmp_path / 'tmp'
        temp_root.mkdir()
        with mock.patch.object(
            LinuxInstall,
            '_staging_problem',
            side_effect=KeyboardInterrupt,
        ):
            with pytest.raises(KeyboardInterrupt):
                install(
                    http=linux_http(),
                    runner=runner,
                    temp_root=str(temp_root),
                )
        assert os.path.exists(runner.commands[2][0])

    def test_a_staged_install_removes_the_folder(self, pinned_key, tmp_path):
        runner = Runner()
        temp_root = tmp_path / 'tmp'
        temp_root.mkdir()
        rc = install(
            http=linux_http(),
            runner=runner,
            temp_root=str(temp_root),
        )
        assert rc == 0
        assert os.listdir(temp_root) == []

    def test_a_rollback_that_removes_the_units_removes_the_folder(
        self, pinned_key, tmp_path
    ):
        runner = Runner(exec_start='self')
        temp_root = tmp_path / 'tmp'
        temp_root.mkdir()
        rc = install_cli(
            http=linux_http(),
            runner=runner,
            temp_root=str(temp_root),
        )
        assert rc == 253
        assert os.listdir(temp_root) == []

    def test_rollback_still_uninstalls_when_disable_fails(
        self, pinned_key, capsys
    ):
        runner = Runner(exec_start='self', disable_error='Access denied')
        assert install_cli(http=linux_http(), runner=runner) == 253
        assert runner.uninstaller_existed == [True]
        assert '/var/log/credsd.\n' in capsys.readouterr().err

    def test_uninstaller_success_with_units_left_is_a_failed_rollback(
        self, pinned_key, capsys
    ):
        class KeepsUnits(Runner):
            def _uninstall(self, command):
                self.uninstaller_existed.append(True)
                return subprocess.CompletedProcess(command, 0, '', '')

        runner = KeepsUnits(exec_start='self')
        assert install_cli(http=linux_http(), runner=runner) == 253
        units = os.path.join(runner.root, 'etc/systemd/system')
        err = capsys.readouterr().err
        assert 'The CLI couldn\'t undo the install. Still there:\n' in err
        assert f'  {units}/credsd.service\n' in err
        assert err.endswith(kept_report(temp_dir(runner), runner.root))
        # Uninstalling wouldn't remove units that don't run the staged
        # copy, so it isn't suggested.
        assert 'credential-daemon uninstall' not in err
        assert err.count('Kept on this machine') == 1

    @pytest.mark.parametrize(
        'show',
        [
            OSError(2, 'No such file'),
            '',
            # One block for two units.
            'LoadState=not-found\nActiveState=inactive\nUnitFileState=\n',
            # No LoadState.
            'ActiveState=inactive\n\nActiveState=inactive\n',
        ],
    )
    def test_unreadable_unit_states_are_reported_as_maybe(
        self, pinned_key, capsys, show
    ):
        runner = Runner(exec_start='self', unit_states={'show': show})
        assert install_cli(http=linux_http(), runner=runner) == 253
        err = capsys.readouterr().err
        assert '  credsd.socket: may still be enabled\n' in err
        assert '  credsd.service: may still be enabled\n' in err
        assert '  credsd.socket: may still be active\n' in err
        assert '  credsd.service: may still be active\n' in err

    def test_units_systemd_reports_missing_are_rolled_back(
        self, pinned_key, capsys
    ):
        # systemd 252: once aws-credential-daemon's uninstaller deletes both
        # units, systemctl show reports them not-found, which counts as
        # rolled back, not as units left enabled or active.
        runner = Runner(exec_start='self')
        rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        err = capsys.readouterr().err
        assert 'couldn\'t undo' not in err
        assert 'may still be' not in err
        assert err.endswith('/var/lib/credsd and /var/log/credsd.\n')

    @pytest.mark.parametrize(
        'state',
        [
            'enabled',
            'enabled-runtime',
            'linked',
            'linked-runtime',
            'alias',
            'indirect',
            'static',
            'generated',
            'transient',
            'bad',
        ],
    )
    def test_a_unit_enabled_in_any_form_is_left(
        self, pinned_key, capsys, state
    ):
        show = (
            f'LoadState=loaded\nActiveState=inactive\nUnitFileState={state}\n'
            '\nLoadState=not-found\nActiveState=inactive\nUnitFileState=\n'
        )
        runner = Runner(exec_start='self', unit_states={'show': show})
        assert install_cli(http=linux_http(), runner=runner) == 253
        err = capsys.readouterr().err
        assert 'The CLI couldn\'t undo the install. Still there:\n' in err
        assert f'  credsd.socket: {state}\n' in err
        assert 'credsd.service:' not in err

    @pytest.mark.parametrize(
        'state', ['', 'disabled', 'masked', 'masked-runtime']
    )
    def test_a_unit_that_cannot_start_is_not_left(
        self, pinned_key, capsys, state
    ):
        show = (
            f'LoadState=loaded\nActiveState=inactive\nUnitFileState={state}\n'
            '\nLoadState=loaded\nActiveState=failed\nUnitFileState=disabled\n'
        )
        runner = Runner(exec_start='self', unit_states={'show': show})
        install_cli(http=linux_http(), runner=runner)
        err = capsys.readouterr().err
        assert 'couldn\'t undo' not in err
        assert err.endswith('/var/log/credsd.\n')

    @pytest.mark.parametrize(
        'active', ['active', 'activating', 'reloading', 'deactivating']
    )
    def test_a_running_unit_is_left_even_if_not_found(
        self, pinned_key, capsys, active
    ):
        show = (
            f'LoadState=not-found\nActiveState={active}\nUnitFileState=\n'
            '\nLoadState=not-found\nActiveState=inactive\nUnitFileState=\n'
        )
        runner = Runner(exec_start='self', unit_states={'show': show})
        install_cli(http=linux_http(), runner=runner)
        err = capsys.readouterr().err
        assert 'Still there:\n' in err
        assert f'  credsd.socket: {active}\n' in err
        assert 'credsd.socket: \n' not in err

    def test_a_failed_systemctl_show_is_reported_as_maybe(
        self, pinned_key, capsys
    ):
        class ShowFails(Runner):
            def _systemctl(self, command):
                if command[1] == 'show':
                    return subprocess.CompletedProcess(
                        command, 1, '', 'Failed to connect to bus'
                    )
                return super()._systemctl(command)

        runner = ShowFails(exec_start='self')
        install_cli(http=linux_http(), runner=runner)
        err = capsys.readouterr().err
        assert '  credsd.socket: may still be enabled\n' in err
        assert '  credsd.service: may still be active\n' in err

    def test_a_missing_service_is_rolled_back(self, pinned_key, capsys):
        runner = Runner()
        with mock.patch.object(Runner, '_write_service'):
            rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        err = capsys.readouterr().err
        assert 'credsd.service couldn\'t be read (' in err
        assert '/var/log/credsd.\n' in err
        assert runner.uninstaller_existed == [True]

    def test_a_service_with_no_exec_line_is_rolled_back(
        self, pinned_key, capsys
    ):
        runner = Runner()

        def write_service(self, credential_daemon):
            unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
            os.makedirs(os.path.dirname(unit))
            with open(unit, 'w') as f:
                f.write('[Service]\nType=simple\n')

        with mock.patch.object(Runner, '_write_service', write_service):
            rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        assert 'credsd.service has no ExecStart line.\n' in (
            capsys.readouterr().err
        )
        assert runner.uninstaller_existed == [True]

    def test_a_later_exec_line_that_runs_another_program_is_caught(
        self, pinned_key, capsys
    ):
        runner = Runner()

        def write_service(self, credential_daemon):
            unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
            os.makedirs(os.path.dirname(unit))
            with open(unit, 'w') as f:
                f.write(
                    f'[Service]\nExecStart="{STAGED}" "serve" "--system"\n'
                    'ExecStartPre=/tmp/x\n'
                )

        with mock.patch.object(Runner, '_write_service', write_service):
            rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        assert 'credsd.service runs /tmp/x, not ' in capsys.readouterr().err
        assert runner.uninstaller_existed == [True]

    @pytest.mark.parametrize('directive', ['ExecSearchPath', 'ExecPaths'])
    def test_exec_path_lists_arent_read_as_commands(
        self, pinned_key, directive
    ):
        # Their values are directories, not a program to run.
        runner = Runner()

        def write_service(self, credential_daemon):
            unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
            os.makedirs(os.path.dirname(unit))
            with open(unit, 'w') as f:
                f.write(
                    f'[Service]\n{directive}=/usr/bin:/bin\n'
                    f'ExecStart="{STAGED}" "serve" "--system"\n'
                )

        with mock.patch.object(Runner, '_write_service', write_service):
            rc = install(http=linux_http(), runner=runner)
        assert rc == 0

    def test_an_oversized_service_is_rolled_back(self, pinned_key, capsys):
        # Padding mustn't push a later Exec* line past what's checked.
        runner = Runner()

        def write_service(self, credential_daemon):
            unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
            os.makedirs(os.path.dirname(unit))
            with open(unit, 'w') as f:
                f.write(
                    f'[Service]\nExecStart="{STAGED}" "serve" "--system"\n'
                    + '#' * (64 * 1024)
                    + '\nExecStartPre=/tmp/x\n'
                )

        with mock.patch.object(Runner, '_write_service', write_service):
            rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        assert 'credsd.service is too large to check.\n' in (
            capsys.readouterr().err
        )
        assert runner.uninstaller_existed == [True]

    def test_the_staged_service_is_not_rolled_back(self, pinned_key):
        runner = Runner()
        assert install(http=linux_http(), runner=runner) == 0
        assert runner.uninstaller_existed == []
        # Only the staging check asked systemd anything.
        assert [
            c[1:]
            for c in runner.commands
            if os.path.basename(c[0]) == 'systemctl'
        ] == [SERVICE_SHOW]

    def test_gpg_comes_from_system_paths(self, pinned_key):
        runner = Runner()
        install(http=linux_http(), runner=runner)
        # Not PATH, which under sudo can still be the user's.
        shutil.which.assert_called_with(
            'gpg', path=os.pathsep.join(['/usr/bin', '/bin'])
        )
        assert runner.commands[0][0] == '/usr/bin/gpg'

    def test_gpg_not_found(self, pinned_key):
        shutil.which.return_value = None
        http = linux_http()
        with pytest.raises(ConfigurationError) as e:
            install(
                http=http,
                runner=Runner(),
            )
        assert "gpg wasn't found in /usr/bin or /bin" in str(e.value)
        # Before anything is downloaded.
        assert http.urls == []

    @pytest.mark.parametrize(
        'machine, name',
        [
            ('x86_64', 'credsd-linux-x64-tpm.tar.gz'),
            ('amd64', 'credsd-linux-x64-tpm.tar.gz'),
            ('aarch64', 'credsd-linux-aarch64-tpm.tar.gz'),
        ],
    )
    def test_picks_the_tpm_asset_for_this_machine(
        self, pinned_key, machine, name
    ):
        folder = name[: -len('.tar.gz')]
        http = linux_http(
            name, data=archive((f'{folder}/credsd', b'#!/bin/sh\n'))
        )
        assert install(machine=machine, http=http, runner=Runner()) == 0
        assert http.urls[1:] == [
            f'{DOWNLOAD}/{name}',
            f'{DOWNLOAD}/{name}.sig',
        ]

    def test_installs_on_any_distribution(self, pinned_key):
        # One release for every distribution, so the install never reads
        # /etc/os-release to pick one or to refuse.
        opened = []
        real_open = open

        def spy(file, *args, **kwargs):
            opened.append(os.fspath(file) if not isinstance(file, int) else '')
            return real_open(file, *args, **kwargs)

        with mock.patch('builtins.open', spy):
            assert install(http=linux_http(), runner=Runner()) == 0
        assert opened
        assert not [path for path in opened if 'os-release' in path]

    def test_signed_by_a_subkey_of_the_pinned_key(self, pinned_key):
        runner = Runner(gpg_status=validsig(signer=SUBKEY))
        assert install(http=linux_http(), runner=runner) == 0

    @pytest.mark.parametrize(
        'gpg_status',
        [
            # Verified, but by another key.
            validsig(signer=SUBKEY, primary=SUBKEY),
            # No VALIDSIG line at all.
            '[GNUPG:] GOODSIG 89ABCDEF01234567 credsd\n',
            f'[GNUPG:] EXPKEYSIG 89ABCDEF01234567 credsd\n{validsig()}',
            f'[GNUPG:] REVKEYSIG 89ABCDEF01234567 credsd\n{validsig()}',
            f'{validsig()}[GNUPG:] BADSIG 89ABCDEF01234567 credsd\n',
        ],
    )
    def test_exit_code_zero_without_a_good_pinned_signature_installs_nothing(
        self, pinned_key, gpg_status
    ):
        runner = Runner(gpg_status=gpg_status)
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
            )
        assert 'didn\'t verify' in str(e.value)
        assert not any(c[-1] == 'install' for c in runner.commands)
        # The downloaded program never ran before its signature checked out.
        assert not ran_version(runner)

    def test_failed_key_import_installs_nothing(self, pinned_key):
        # gpg's IMPORT_OK line decides, not its exit code.
        runner = Runner(import_rc=2, import_status='')
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
            )
        assert 'no valid OpenPGP data' in str(e.value)
        assert len(runner.commands) == 1
        assert not ran_version(runner)

    @pytest.mark.parametrize(
        'import_rc, status, installs',
        [
            # A warning can make gpg exit 2 though the key imported.
            (2, None, True),
            (0, '', False),
            # IMPORT_OK for another key isn't the pinned one.
            (
                0,
                '[GNUPG:] IMPORT_OK 1 FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\n',
                False,
            ),
        ],
    )
    def test_the_import_is_judged_by_import_ok(
        self, pinned_key, import_rc, status, installs
    ):
        kwargs = {'import_rc': import_rc}
        if status is not None:
            kwargs['import_status'] = status
        runner = Runner(**kwargs)
        if installs:
            assert install(http=linux_http(), runner=runner) == 0
        else:
            with pytest.raises(ConfigurationError, match='signing key'):
                install(http=linux_http(), runner=runner)
            assert not ran_version(runner)
        gpg_import = runner.commands[0]
        assert gpg_import[-4:-1] == ['--status-fd', '1', '--import']

    def test_bad_signature_installs_nothing(self, pinned_key):
        runner = Runner(verify_rc=1)
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
            )
        assert 'BAD signature' in str(e.value)
        assert not any(c[-1] == 'install' for c in runner.commands)
        assert not ran_version(runner)

    @pytest.mark.parametrize(
        'runner_kwargs, step',
        [
            ({'import_rc': 2, 'import_status': ''}, '--import'),
            ({'verify_rc': 1}, '--verify'),
        ],
    )
    def test_gpg_errors_are_shown_without_escape_sequences(
        self, pinned_key, runner_kwargs, step
    ):
        class Escapes(Runner):
            def __call__(self, command, check=True, timeout=None):
                result = super().__call__(command, check)
                if step in command:
                    result.stderr = (
                        '\x1bgpg:\x07 first line\r\ngpg: second\x9b line\x1b\n'
                    )
                return result

        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=Escapes(**runner_kwargs),
            )
        message = str(e.value)
        assert message.endswith('\ngpg: first line\ngpg: second line')
        assert not any(c in message for c in '\x1b\x07\x9b\r')

    def test_unsafe_archive_is_refused(self, pinned_key):
        runner = Runner()
        data = archive(('../evil', b'x'), ('credsd', b'#!/bin/sh\n'))
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(data=data),
                runner=runner,
            )
        assert 'unexpected entry' in str(e.value)
        assert not any(c[-1] == 'install' for c in runner.commands)

    @pytest.mark.parametrize(
        'entry',
        [
            'symlink',
            'hardlink',
            'char_device',
            'fifo',
            'absolute',
            'parent',
            'nested_parent',
        ],
    )
    def test_each_unsafe_entry_is_refused(self, tmp_path, entry):
        # extract_safely takes only regular files and folders inside the
        # target, and checks every entry before it extracts any.
        info = tarfile.TarInfo('credsd-linux-x64-tpm/evil')
        if entry == 'symlink':
            info.type = tarfile.SYMTYPE
            info.linkname = '/etc/passwd'
        elif entry == 'hardlink':
            info.type = tarfile.LNKTYPE
            info.linkname = 'credsd-linux-x64-tpm/credsd'
        elif entry == 'char_device':
            info.type = tarfile.CHRTYPE
            info.devmajor, info.devminor = 1, 3
        elif entry == 'fifo':
            info.type = tarfile.FIFOTYPE
        elif entry == 'absolute':
            info.name = str(tmp_path / 'abs')
        elif entry == 'parent':
            info.name = '../evil'
        else:
            info.name = 'a/../../b'
        safe = tarfile.TarInfo('credsd-linux-x64-tpm/credsd')
        safe.size = 3
        path = tmp_path / 'release.tar.gz'
        with tarfile.open(path, 'w:gz') as tar:
            tar.addfile(safe, io.BytesIO(b'#!x'))
            tar.addfile(info, io.BytesIO(b''))
        target = tmp_path / 'out' / 'release'
        target.mkdir(parents=True)
        with pytest.raises(ConfigurationError) as e:
            extract_safely(str(path), str(target))
        assert 'unexpected entry' in str(e.value)
        # Nothing was extracted, inside the target or next to it.
        assert os.listdir(target) == []
        assert sorted(os.listdir(tmp_path)) == ['out', 'release.tar.gz']
        assert os.listdir(tmp_path / 'out') == ['release']

    def test_installer_failure(self, pinned_key):
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=Runner(install_error='no systemd'),
            )
        assert 'no systemd' in str(e.value)


class TestLinuxHostCheck:
    """Only the architecture is checked before anything is downloaded.
    aws-credential-daemon's own installer checks the rest of what it
    needs, such as a TPM, and its error is the command's."""

    def test_installs_without_checking_for_systemd_tpm_or_libraries(
        self, pinned_key
    ):
        # The machine under root has no /run/systemd/system, no
        # /dev/tpmrm0, and nothing runs ldconfig.
        runner = Runner()
        with mock.patch.object(subprocess, 'run') as run:
            assert install(http=linux_http(), runner=runner) == 0
        run.assert_not_called()
        assert runner.commands[-2][-1] == 'install'

    def test_an_installer_that_finds_no_tpm_is_a_clean_error(
        self, pinned_key, capsys
    ):
        reason = 'Error: no TPM 2.0 device found at /dev/tpmrm0'
        runner = Runner(install_error=reason)
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value) == (
            f'aws-credential-daemon\'s installer failed:\n{reason}'
        )
        assert 'Installed' not in capsys.readouterr().out
        # The CLI's error handler shows it as an error, not a traceback.
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = construct_cli_error_handlers_chain().handle_exception(
            e.value, stdout=stdout, stderr=stderr
        )
        assert rc == 253
        assert reason in stderr.getvalue()
        assert 'Traceback' not in stderr.getvalue()

    def test_an_unsupported_architecture_is_refused_first(self, pinned_key):
        http = linux_http()
        runner = Runner()
        with pytest.raises(ConfigurationError) as e:
            install(machine='armv7l', http=http, runner=runner)
        assert str(e.value) == (
            'aws-credential-daemon has no release for armv7l.'
        )
        assert http.urls == []
        assert runner.commands == []

    def test_without_root_the_architecture_isnt_checked_first(self):
        # Root comes first now: without it nothing else runs at all.
        command = InstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system='linux',
                machine='armv7l',
                is_root=False,
                environ={'HOME': '/home/u'},
            ),
        )
        with pytest.raises(ConfigurationError) as e:
            command._run_main(Namespace(), GLOBALS)
        assert 'requires root' in str(e.value)


class TestLinuxKeptTempDir:
    """Every path that keeps the temp folder says what's left, and how
    to remove it."""

    def test_an_interrupted_rollback_names_the_folder_and_units(
        self, pinned_key, capsys
    ):
        runner = InterruptedRollbackRunner(exec_start='self')
        with pytest.raises(KeyboardInterrupt):
            install(http=linux_http(), runner=runner)
        units = os.path.join(runner.root, 'etc/systemd/system')
        # Why it rolled back is printed before the rollback starts, and
        # the interrupt report names the units and how to remove them.
        assert capsys.readouterr().err == (
            PREVIEW_LINE
            + 'aws-credential-daemon\'s installer didn\'t set up its '
            f'service as expected: {units}/credsd.service runs '
            f'{runner.commands[3][0]}, '
            'not /usr/local/libexec/credsd/credsd.\n'
            'The rollback was interrupted. credsd.socket and credsd.service '
            'may be stopped and disabled, but are still there. To remove '
            'them, run:\n'
            '  sudo aws configure credential-daemon uninstall\n'
            f'Kept on this machine: {temp_dir(runner)}\n'
            'If it\'s still there after that, remove it with:\n'
            f'  sudo rm -r {temp_dir(runner)}\n'
        )

    def test_an_interrupted_staging_check_names_the_folder_and_units(
        self, pinned_key, capsys
    ):
        runner = Runner(exec_start='self')
        with mock.patch.object(
            LinuxInstall,
            '_staging_problem',
            side_effect=KeyboardInterrupt,
        ):
            with pytest.raises(KeyboardInterrupt):
                install(http=linux_http(), runner=runner)
        assert capsys.readouterr().err == PREVIEW_LINE + kept_report(
            temp_dir(runner), runner.root
        )

    def test_an_interrupted_staged_install_names_only_the_folder(
        self, pinned_key, capsys
    ):
        # credsd.service runs the staged copy, so no unit names the
        # folder.
        runner = Runner()
        with mock.patch.object(
            LinuxInstall,
            '_staging_problem',
            side_effect=KeyboardInterrupt,
        ):
            with pytest.raises(KeyboardInterrupt):
                install(http=linux_http(), runner=runner)
        assert capsys.readouterr().err == PREVIEW_LINE + kept_report(
            temp_dir(runner)
        )

    def test_an_unreadable_service_counts_as_naming_the_folder(
        self, pinned_key, capsys
    ):
        runner = Runner(exec_start='self')

        def interrupt():
            service = os.path.join(
                runner.root, 'etc/systemd/system/credsd.service'
            )
            os.chmod(service, 0)
            raise KeyboardInterrupt

        if os.geteuid() == 0:
            pytest.skip('root reads any file')
        with mock.patch.object(
            LinuxInstall,
            '_staging_problem',
            side_effect=interrupt,
        ):
            with pytest.raises(KeyboardInterrupt):
                install(http=linux_http(), runner=runner)
        assert capsys.readouterr().err == PREVIEW_LINE + kept_report(
            temp_dir(runner), runner.root
        )

    def test_an_interrupted_install_with_a_failed_rollback_says_it_once(
        self, pinned_key, capsys
    ):
        runner = FailsAfterWritingService(
            exec_start='self',
            error=KeyboardInterrupt(),
            uninstall_error='boom',
        )
        with pytest.raises(KeyboardInterrupt):
            install(http=linux_http(), runner=runner)
        err = capsys.readouterr().err
        assert err.endswith(kept_report(temp_dir(runner), runner.root))
        assert err.count('Kept on this machine') == 1

    def test_a_good_install_and_a_clean_rollback_say_nothing(
        self, pinned_key, capsys
    ):
        assert install_cli(http=linux_http()) == 0
        runner = Runner(exec_start='self')
        assert install_cli(http=linux_http(), runner=runner) == 253
        assert 'Kept on this machine' not in capsys.readouterr().err

    def test_a_path_with_a_space_is_quoted_in_the_commands(self, tmp_path):
        command = InstallCredentialDaemonCommand(
            mock.Mock(), InstallHost(root=str(tmp_path))
        )
        report = LinuxInstall(command.host)._kept_temp_dir_report('/tmp/a b')
        assert report.endswith("  sudo rm -r '/tmp/a b'\n")

    @pytest.mark.parametrize(
        'service, runs_from',
        [
            # The folder's path, spelled another way.
            ('ExecStart=/tmp//tmpab12cd/release/credsd serve\n', True),
            ('ExecStart=/tmp/./tmpab12cd/release/credsd serve\n', True),
            # A shell that runs the copy in the folder.
            (
                'ExecStart=/bin/sh -c "/tmp/tmpab12cd/release/credsd '
                'serve"\n',
                True,
            ),
            # Not from the folder, but not the staged copy either.
            ('', False),
            ('ExecStart=/usr/local/bin/x serve\n', False),
        ],
    )
    def test_units_that_dont_run_the_staged_copy_are_named(
        self, tmp_path, service, runs_from
    ):
        units = tmp_path / 'etc/systemd/system'
        units.mkdir(parents=True)
        (units / 'credsd.service').write_text(f'[Service]\n{service}')
        (units / 'credsd.socket').write_text('[Socket]\n')
        command = InstallCredentialDaemonCommand(
            mock.Mock(), InstallHost(root=str(tmp_path))
        )
        tmp = '/tmp/tmpab12cd'
        assert LinuxInstall(command.host)._kept_temp_dir_report(
            tmp
        ) == kept_report(tmp, str(tmp_path), runs_from=runs_from)

    def test_units_that_run_the_staged_copy_arent_named(self, tmp_path):
        units = tmp_path / 'etc/systemd/system'
        units.mkdir(parents=True)
        (units / 'credsd.service').write_text(
            '[Service]\nExecStart=/usr/local/libexec/credsd/credsd serve\n'
        )
        (units / 'credsd.socket').write_text('[Socket]\n')
        command = InstallCredentialDaemonCommand(
            mock.Mock(), InstallHost(root=str(tmp_path))
        )
        tmp = '/tmp/tmpab12cd'
        assert LinuxInstall(command.host)._kept_temp_dir_report(
            tmp
        ) == kept_report(tmp)

    def test_a_failed_rollback_of_a_service_running_another_program(
        self, pinned_key, capsys
    ):
        # The units don't run from the folder, but they're still enabled,
        # so the report still says how to remove them.
        runner = Runner(
            exec_start='/usr/local/bin/x',
            disable_error='denied',
            uninstall_error='boom',
        )
        rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        assert capsys.readouterr().err.endswith(
            '  (aws-credential-daemon\'s uninstaller failed: boom)\n'
            + kept_report(temp_dir(runner), runner.root, runs_from=False)
        )


class FailsAfterWritingService(Runner):
    """credsd install that writes credsd.service, then fails.

    Like aws-credential-daemon on a reinstall, where it doesn't undo what it
    did when a later step (daemon-reload, enable --now) fails.
    """

    def __init__(self, error=None, **kwargs):
        super().__init__(**kwargs)
        self._error = error

    def __call__(self, command, check=True, timeout=None):
        if command[1:] == ['install']:
            self.commands.append(command)
            self._write_service(command[0])
            if self._error is not None:
                raise self._error
            raise subprocess.CalledProcessError(
                1, command, stderr='Failed to enable credsd.socket'
            )
        return super().__call__(command, check)


class InterruptedRollbackRunner(Runner):
    """Ctrl-C while the rollback's `systemctl disable --now` runs."""

    def _systemctl(self, command):
        if command[1] == 'disable':
            unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
            with open(unit) as f:
                self.service_at_interrupt = f.read()
            raise KeyboardInterrupt
        return super()._systemctl(command)


class TestLinuxInstallerFails:
    def test_a_unit_rewritten_to_our_copy_is_rolled_back(
        self, pinned_key, tmp_path, capsys
    ):
        runner = lasting_runner(
            tmp_path, FailsAfterWritingService, exec_start='self'
        )
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
                temp_root=runner.temp_root,
            )
        credential_daemon = runner.commands[3][0]
        units = os.path.join(runner.root, 'etc/systemd/system')
        # Why, before the rollback ran; then what it did.
        assert capsys.readouterr().err.endswith(
            'aws-credential-daemon\'s installer didn\'t set up its '
            f'service as expected: {units}/credsd.service runs '
            f'{credential_daemon}, '
            'not /usr/local/libexec/credsd/credsd.\n'
        )
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\n'
            'Failed to enable credsd.socket\n'
            'The CLI stopped and removed aws-credential-daemon\'s '
            'service and socket (credsd.socket and credsd.service). Its '
            'uninstaller keeps its system account, /var/lib/credsd and '
            '/var/log/credsd.'
        )
        disable, uninstall = runner.commands[4:6]
        assert disable[1:3] == ['disable', '--now']
        assert uninstall == [credential_daemon, 'uninstall']
        # While our copy still existed; it's gone after.
        assert runner.uninstaller_existed == [True]
        assert not os.path.exists(credential_daemon)
        # No unit is left pointing into the removed directory.
        assert not os.path.exists(f'{units}/credsd.service')
        assert not os.path.exists(f'{units}/credsd.socket')

    def test_a_failed_rollback_is_in_the_error(self, pinned_key):
        runner = FailsAfterWritingService(
            exec_start='self', uninstall_error='boom'
        )
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        message = str(e.value)
        assert message.startswith(
            'aws-credential-daemon\'s installer failed:\n'
        )
        assert 'The CLI couldn\'t undo the install. Still there:\n' in message
        assert '(aws-credential-daemon\'s uninstaller failed: boom)' in (
            message
        )
        assert message.endswith(
            kept_report(temp_dir(runner), runner.root).rstrip()
        )

    def test_another_error_is_re_raised_after_the_rollback(
        self, pinned_key, capsys
    ):
        runner = FailsAfterWritingService(
            exec_start='self', error=KeyboardInterrupt()
        )
        with pytest.raises(KeyboardInterrupt):
            install(http=linux_http(), runner=runner)
        assert runner.uninstaller_existed == [True]
        assert capsys.readouterr().err.endswith('/var/log/credsd.\n')

    def test_a_unit_that_runs_the_staged_copy_is_kept(self, pinned_key):
        # A reinstall that failed before touching the old, staged unit.
        runner = FailsAfterWritingService()
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        # What's left is named, with the command that removes it.
        units = os.path.join(runner.root, 'etc/systemd/system')
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\n'
            'Failed to enable credsd.socket\n'
            'aws-credential-daemon may be partly installed. Still there:\n'
            f'  {units}/credsd.service\n'
            f'  {units}/credsd.socket\n'
            # As printed: install runs as root.
            'To remove it, run: sudo aws configure credential-daemon '
            'uninstall'
        )
        assert runner.uninstaller_existed == []
        # Nothing but the staging check asked systemd anything.
        assert [
            c[1:]
            for c in runner.commands
            if os.path.basename(c[0]) == 'systemctl'
        ] == [SERVICE_SHOW]

    def test_a_failed_reinstall_over_a_staged_install_says_it_is_kept(
        self, pinned_key, tmp_path
    ):
        # The earlier install still works, so the CLI doesn't suggest
        # uninstalling it.
        runner = lasting_runner(tmp_path, FailsAfterWritingService)
        runner._write_service('unused')
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
                temp_root=runner.temp_root,
            )
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\n'
            'Failed to enable credsd.socket\n'
            'The earlier install of aws-credential-daemon is still there: '
            'its service runs /usr/local/libexec/credsd/credsd.\n'
            'To try again, run: sudo aws configure credential-daemon install'
        )
        assert 'uninstall' not in str(e.value)
        assert runner.uninstaller_existed == []
        assert os.listdir(runner.temp_root) == []

    def test_a_failed_reinstall_over_an_unstaged_unit_is_partly_installed(
        self, pinned_key, tmp_path
    ):
        # Before the run, the service ran something else, so the earlier
        # install wasn't one the CLI supports.
        runner = lasting_runner(
            tmp_path, FailsAfterWritingService, exec_start='/opt/other/credsd'
        )
        runner._write_service('unused')
        # The failed reinstall wrote the staged copy's unit.
        runner.exec_start = None
        with pytest.raises(ConfigurationError) as e:
            install(
                http=linux_http(),
                runner=runner,
                temp_root=runner.temp_root,
            )
        assert 'may be partly installed' in str(e.value)
        assert str(e.value).endswith(
            'To remove it, run: sudo aws configure credential-daemon '
            'uninstall'
        )

    def test_no_unit_means_nothing_to_roll_back(self, pinned_key):
        runner = Runner(install_error='no space left')
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value) == (
            'aws-credential-daemon\'s installer failed:\nno space left'
        )
        assert runner.uninstaller_existed == []


def tree(path):
    """(path, mode, mtime, size) of everything under path, links unfollowed."""
    entries = set()
    for dirpath, dirnames, filenames in os.walk(path):
        for name in [''] + dirnames + filenames:
            full = os.path.join(dirpath, name)
            st = os.lstat(full)
            entries.add((full, st.st_mode, st.st_mtime_ns, st.st_size))
    return entries


OUR_SERVICE = (
    '[Unit]\nDescription=AWS credential daemon\n\n[Service]\n'
    f'ExecStart={STAGED} serve\n\n[Install]\nWantedBy=multi-user.target\n'
)

OUR_SOCKET = (
    '[Socket]\nListenStream=/run/credsd/credsd.sock\n\n'
    '[Install]\nWantedBy=sockets.target\n'
)


def write_unit(path, text):
    path = write(path, text)
    path.chmod(0o644)
    return path


def systemctl_calls(runner):
    return [
        command[1:]
        for command in runner.commands
        if os.path.basename(command[0]) == 'systemctl'
    ]


class TestUninstallLinux:
    def test_runs_credential_daemons_uninstaller_and_keeps_credentials(
        self, tmp_path, linux_install, capsys
    ):
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert runner.commands == [
            [str(linux_install.credential_daemon), 'uninstall']
        ]
        # The staged copy's empty directory goes too; nothing else does.
        assert not linux_install.credential_daemon.parent.exists()
        assert linux_install.data.exists()
        assert linux_install.other.exists()
        assert capsys.readouterr().out == (
            'Removed aws-credential-daemon. '
            'The credential daemon\'s saved sign-ins and keys stay on this '
            'machine, so reinstalling brings them back. Nothing in ~/.aws '
            'was changed.\n'
        )

    def test_a_staged_directory_with_other_files_stays(
        self, tmp_path, linux_install
    ):
        extra = write(linux_install.credential_daemon.parent / 'notes')
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert extra.exists()

    def test_files_the_uninstaller_left_are_reported(
        self, tmp_path, linux_install, capsys
    ):
        runner = UninstallRunner(removes=[linux_install.credential_daemon])
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        err = capsys.readouterr().err
        for unit in linux_install.units:
            assert f'  {unit}: not removed by the uninstaller\n' in err
        assert 'Remove them by hand.' in err

    def test_uninstaller_failure_says_what_is_left(
        self, tmp_path, linux_install
    ):
        runner = UninstallRunner(error='systemctl failed')
        with pytest.raises(ConfigurationError) as e:
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert 'systemctl failed' in str(e.value)
        assert f'still installed at {linux_install.credential_daemon}' in str(
            e.value
        )
        assert linux_install.credential_daemon.parent.exists()

    def test_uninstaller_errors_are_printed_without_control_characters(
        self, tmp_path, linux_install
    ):
        runner = UninstallRunner(
            error='\x1b]0;pwned\x07failed\x1b[2K\r\nsecond\x9b line\n'
        )
        with pytest.raises(ConfigurationError) as e:
            uninstall(tmp_path, ['--yes'], runner=runner)
        message = str(e.value)
        assert not re.search(r'[\x00-\x09\x0b-\x1f\x7f-\x9f]', message)
        assert '0;pwnedfailed[2K\nsecond line\n' in message

    def test_units_without_the_staged_copy_are_not_ours(
        self, tmp_path, linux_install
    ):
        linux_install.credential_daemon.unlink()
        runner = UninstallRunner()
        with pytest.raises(
            ConfigurationError,
            match='To remove its service, run:',
        ):
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert runner.commands == []
        assert all(unit.exists() for unit in linux_install.units)

    def test_units_that_run_another_program_are_not_ours(
        self, tmp_path, linux_install
    ):
        linux_install.credential_daemon.unlink()
        service, socket = linux_install.units
        write_unit(service, OUR_SERVICE.replace(STAGED, '/usr/bin/credsd'))
        write_unit(socket, OUR_SOCKET)
        before = tree(tmp_path / 'root')
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError) as e:
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert str(e.value) == (
            'aws-credential-daemon wasn\'t installed by aws configure '
            f'credential-daemon install ({linux_install.credential_daemon} is '
            'missing), so nothing was uninstalled. To remove its service, '
            'run:\n'
            '  sudo systemctl disable --now credsd.socket credsd.service\n'
            f'  sudo rm {socket} {service}\n'
            '  sudo systemctl daemon-reload'
        )
        assert runner.commands == []
        assert tree(tmp_path / 'root') == before

    def test_a_staged_copy_others_can_change_is_not_run(
        self, tmp_path, linux_install
    ):
        linux_install.credential_daemon.chmod(0o777)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError, match='other than root'):
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert runner.commands == []

    def test_a_staged_copy_owned_by_someone_else_is_not_run(
        self, tmp_path, linux_install
    ):
        runner = UninstallRunner()
        command = UninstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system='linux',
                is_root=True,
                run=runner,
                root=str(tmp_path / 'root'),
                trusted_uid=os.getuid() + 1,
                is_tty=lambda: False,
            ),
        )
        with pytest.raises(ConfigurationError, match='other than root'):
            command._run_main(Namespace(user=False, yes=True), GLOBALS)
        assert runner.commands == []

    def test_a_symlinked_staged_copy_is_not_run(self, tmp_path, linux_install):
        target = write(tmp_path / 'root/usr/local/libexec/credsd/real')
        linux_install.credential_daemon.unlink()
        linux_install.credential_daemon.symlink_to(target)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError, match='isn\'t a regular file'):
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert runner.commands == []


class TestUninstallLinuxAncestors:
    """Every folder on the way to a program run as root is checked."""

    @pytest.mark.parametrize('folder', ['usr/local', 'usr', ''])
    def test_a_folder_above_the_staged_copy_others_can_change(
        self, tmp_path, linux_install, folder
    ):
        # A user who can write usr/local can rename libexec and put another
        # program at the staged copy's path.
        ancestor = tmp_path / 'root' / folder
        ancestor.chmod(0o777)
        runner = UninstallRunner()
        try:
            with pytest.raises(ConfigurationError) as e:
                uninstall(tmp_path, ['--yes'], runner=runner)
        finally:
            ancestor.chmod(0o755)
        assert str(e.value) == (
            f'{os.path.normpath(ancestor)} can be changed by users other '
            'than root, so aws-credential-daemon\'s uninstaller wasn\'t '
            'run. Nothing was uninstalled.'
        )
        assert runner.commands == []

    def test_a_folder_an_untrusted_group_can_change(
        self, tmp_path, linux_install
    ):
        ancestor = tmp_path / 'root/usr/local'
        ancestor.chmod(0o775)
        runner = UninstallRunner()
        try:
            with pytest.raises(ConfigurationError, match='other than root'):
                uninstall(tmp_path, ['--yes'], runner=runner, trusted_gids=())
        finally:
            ancestor.chmod(0o755)
        assert runner.commands == []

    def test_a_folder_a_trusted_group_can_change(
        self, tmp_path, linux_install
    ):
        ancestor = tmp_path / 'root/usr/local'
        ancestor.chmod(0o775)
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=runner,
            trusted_gids=(os.lstat(ancestor).st_gid,),
        )
        assert rc == 0
        assert runner.commands == [
            [str(linux_install.credential_daemon), 'uninstall']
        ]

    def test_others_can_never_write_a_folder(self, tmp_path, linux_install):
        # Not even with a trusted group.
        ancestor = tmp_path / 'root/usr/local'
        ancestor.chmod(0o777)
        runner = UninstallRunner()
        try:
            with pytest.raises(ConfigurationError, match='other than root'):
                uninstall(
                    tmp_path,
                    ['--yes'],
                    runner=runner,
                    trusted_gids=(os.lstat(ancestor).st_gid,),
                )
        finally:
            ancestor.chmod(0o755)
        assert runner.commands == []

    @pytest.mark.parametrize(
        'folder', ['usr/local/libexec/credsd', 'usr/local/libexec']
    )
    def test_a_symlinked_folder_is_not_run(
        self, tmp_path, linux_install, folder
    ):
        # The link itself can pass an owner check while the exec follows
        # it somewhere else.
        link = tmp_path / 'root' / folder
        real = tmp_path / 'root/real'
        link.rename(real)
        link.symlink_to(real)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError) as e:
            uninstall(tmp_path, ['--yes'], runner=runner)
        if folder == 'usr/local/libexec':
            # A folder credsd's installer resolves: refused up front.
            # Its own uninstaller still works there.
            staged = real / 'credsd/credsd'
            assert str(e.value) == (
                '/usr/local/libexec is a symbolic link (as on rpm-ostree '
                'systems), which this command doesn\'t support, so nothing '
                f'was uninstalled. Uninstall it with: sudo {staged} uninstall'
            )
        else:
            assert str(e.value) == (
                f'{link} is a symbolic link, so aws-credential-daemon\'s '
                'uninstaller wasn\'t run. Nothing was uninstalled.'
            )
        assert runner.commands == []

    def test_a_unit_in_a_symlinked_folder_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, socket = linux_install.units
        write_unit(service, OUR_SERVICE)
        write_unit(socket, OUR_SOCKET)
        link = tmp_path / 'root/etc/systemd'
        real = tmp_path / 'root/etc/real-systemd'
        link.rename(real)
        link.symlink_to(real)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert runner.commands == []
        assert (real / 'system/credsd.service').exists()
        assert (
            f'  {service}: {link} is a symbolic link, so it wasn\'t '
            'removed\n'
        ) in capsys.readouterr().err

    def test_folders_above_the_install_root_arent_checked(
        self, tmp_path, linux_install
    ):
        # Only from the program up to the install root, which is / outside
        # tests.
        tmp_path.chmod(0o777)
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        try:
            rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        finally:
            tmp_path.chmod(0o700)
        assert rc == 0


class TestUninstallLinuxRerun:
    """A re-run after a partial cleanup finishes what's provably ours."""

    def our_units(self, linux_install, service=True, socket=True):
        unit_service, unit_socket = linux_install.units
        unit_service.unlink()
        unit_socket.unlink()
        if service:
            write_unit(unit_service, OUR_SERVICE)
        if socket:
            write_unit(unit_socket, OUR_SOCKET)
        return unit_service, unit_socket

    def test_staged_copy_gone_and_both_units_left(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, socket = self.our_units(linux_install)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert systemctl_calls(runner) == [
            ['disable', '--now', 'credsd.socket', 'credsd.service'],
            ['daemon-reload'],
        ]
        # aws-credential-daemon itself is gone, so its uninstaller isn't run.
        assert all(
            os.path.basename(c[0]) == 'systemctl' for c in runner.commands
        )
        assert not service.exists()
        assert not socket.exists()
        assert not linux_install.credential_daemon.parent.exists()
        assert linux_install.data.exists()
        assert linux_install.other.exists()
        assert capsys.readouterr().out == (
            'Removed aws-credential-daemon. '
            'The credential daemon\'s saved sign-ins and keys stay on this '
            'machine, so reinstalling brings them back. Nothing in ~/.aws '
            'was changed.\n'
        )

    def test_only_the_service_left(self, tmp_path, linux_install):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install, socket=False)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert systemctl_calls(runner)[0] == [
            'disable',
            '--now',
            'credsd.service',
        ]
        assert not service.exists()

    def test_only_the_staged_copy_left(self, tmp_path, linux_install):
        self.our_units(linux_install, service=False, socket=False)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        # No units: nothing for aws-credential-daemon's uninstaller to do.
        assert runner.commands == []
        assert not linux_install.credential_daemon.parent.exists()
        assert linux_install.other.exists()

    def test_a_leftover_staging_file_is_removed_with_the_staged_copy(
        self, tmp_path, linux_install
    ):
        # From an interrupted credsd install.
        self.our_units(linux_install, service=False, socket=False)
        staging = write(
            linux_install.credential_daemon.parent / '.credsd.staging'
        )
        rc, _ = uninstall(tmp_path, ['--yes'])
        assert rc == 0
        assert not staging.exists()
        assert not linux_install.credential_daemon.parent.exists()

    def test_a_lone_staging_file_is_removed(
        self, tmp_path, linux_install, capsys
    ):
        # An interrupted credsd install that got no further.
        self.our_units(linux_install, service=False, socket=False)
        linux_install.credential_daemon.unlink()
        staging = write(
            linux_install.credential_daemon.parent / '.credsd.staging'
        )
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert runner.commands == []
        assert not staging.exists()
        assert not linux_install.credential_daemon.parent.exists()
        assert 'Removed aws-credential-daemon.' in capsys.readouterr().out

    def test_a_staging_file_others_can_change_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        self.our_units(linux_install, service=False, socket=False)
        staging = write(
            linux_install.credential_daemon.parent / '.credsd.staging'
        )
        staging.chmod(0o666)
        rc, _ = uninstall(tmp_path, ['--yes'])
        assert rc == 1
        assert staging.exists()
        assert (
            f'  {staging}: can be changed by users other than root, so it '
            f'wasn\'t removed\n'
        ) in capsys.readouterr().err

    def test_a_staged_copy_others_can_change_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        self.our_units(linux_install, service=False, socket=False)
        linux_install.credential_daemon.chmod(0o777)
        before = tree(tmp_path / 'root')
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert runner.commands == []
        assert tree(tmp_path / 'root') == before
        assert capsys.readouterr().err == (
            'aws-credential-daemon wasn\'t fully uninstalled. These are '
            'still on this machine:\n'
            f'  {linux_install.credential_daemon}: can be '
            'changed by users other than '
            'root, so it wasn\'t removed\n'
            'Remove them by hand.\n'
        )

    def test_a_socket_alone_is_reported_not_removed(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        _, socket = self.our_units(linux_install, service=False)
        before = tree(tmp_path / 'root')
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert runner.commands == []
        assert tree(tmp_path / 'root') == before
        assert capsys.readouterr().err == (
            'aws-credential-daemon wasn\'t fully uninstalled. These are '
            'still on this machine:\n'
            f'  {socket}: can\'t be shown to be from this install without '
            'credsd.service, so it wasn\'t removed\n'
            'Remove them by hand.\n'
        )

    def test_a_socket_for_another_service_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, socket = self.our_units(linux_install)
        write_unit(socket, OUR_SOCKET + 'Service=other.service\n')
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert systemctl_calls(runner)[0] == [
            'disable',
            '--now',
            'credsd.service',
        ]
        assert not service.exists()
        assert socket.exists()
        assert (
            f'  {socket}: starts a service other than credsd.service, so it '
            'isn\'t from this install and wasn\'t removed\n'
        ) in capsys.readouterr().err

    @pytest.mark.parametrize(
        'line',
        [
            'ExecStartPre=/bin/sh -c id\n',
            'ExecStart=\n',
            f'ExecStopPost=-{STAGED}x stop\n',
        ],
    )
    def test_a_service_with_another_exec_line_is_not_ours(
        self, tmp_path, linux_install, line
    ):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        write_unit(service, OUR_SERVICE + line)
        before = tree(tmp_path / 'root')
        runner = UninstallRunner()
        with pytest.raises(
            ConfigurationError,
            match='To remove its service, run:',
        ):
            uninstall(tmp_path, ['--yes'], runner=runner)
        assert runner.commands == []
        assert tree(tmp_path / 'root') == before

    def test_systemd_prefixes_on_our_program_are_ours(
        self, tmp_path, linux_install
    ):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        write_unit(
            service,
            OUR_SERVICE + f'ExecStopPost=-{STAGED} stop\n'
            f'ExecReload=@{STAGED} aws-credential-daemon reload\n',
        )
        rc, _ = uninstall(tmp_path, ['--yes'])
        assert rc == 0
        assert not service.exists()

    @pytest.mark.parametrize('which', ['file', 'folder'])
    def test_a_unit_others_can_change_is_reported(
        self, tmp_path, linux_install, capsys, which
    ):
        linux_install.credential_daemon.unlink()
        service, socket = self.our_units(linux_install)
        target = service if which == 'file' else service.parent
        target.chmod(0o777 if which == 'folder' else 0o666)
        before = tree(tmp_path / 'root')
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert runner.commands == []
        assert tree(tmp_path / 'root') == before
        err = capsys.readouterr().err
        if which == 'file':
            reason = 'can be changed by users other than root'
        else:
            reason = (
                f'{service.parent} can be changed by users other than root'
            )
        assert f'  {service}: {reason}, so it wasn\'t removed\n' in err
        assert f'  {socket}: ' in err
        service.parent.chmod(0o755)

    def test_a_symlinked_unit_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        real = write_unit(tmp_path / 'root/etc/real.service', OUR_SERVICE)
        service.unlink()
        service.symlink_to(real)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert runner.commands == []
        assert real.exists()
        assert (
            f'  {service}: isn\'t a regular file, so it wasn\'t removed\n'
        ) in capsys.readouterr().err

    def test_a_huge_unit_is_reported(self, tmp_path, linux_install, capsys):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        write_unit(service, OUR_SERVICE + '#' * (64 * 1024))
        rc, _ = uninstall(tmp_path, ['--yes'])
        assert rc == 1
        assert service.exists()
        assert (
            f'  {service}: is too large to check, so it wasn\'t removed\n'
        ) in capsys.readouterr().err

    def test_uninstaller_leaves_units_and_the_cli_finishes(
        self, tmp_path, linux_install, capsys
    ):
        # The uninstaller removes its staged copy but leaves our units.
        service, socket = self.our_units(linux_install)
        runner = UninstallRunner(removes=[linux_install.credential_daemon])
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert runner.commands[0] == [
            str(linux_install.credential_daemon),
            'uninstall',
        ]
        assert systemctl_calls(runner) == [
            ['disable', '--now', 'credsd.socket', 'credsd.service'],
            ['daemon-reload'],
        ]
        assert not service.exists()
        assert not socket.exists()
        assert not linux_install.credential_daemon.parent.exists()

    def test_uninstaller_leaves_its_staged_copy(self, tmp_path, linux_install):
        runner = UninstallRunner(removes=linux_install.units)
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert not linux_install.credential_daemon.parent.exists()

    def test_systemctl_failure_is_reported_and_a_rerun_finishes(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, socket = self.our_units(linux_install)
        runner = UninstallRunner(
            systemctl_error={'disable': '\x1b[31mFailed to disable\n'}
        )
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert service.exists()
        assert socket.exists()
        assert capsys.readouterr().err == (
            'aws-credential-daemon wasn\'t fully uninstalled. These are '
            'still on this machine:\n'
            f'  {socket}: systemctl disable --now failed: [31mFailed to '
            'disable\n'
            f'  {service}: systemctl disable --now failed: [31mFailed to '
            'disable\n'
            'Remove them by hand.\n'
        )
        runner.systemctl_error = {}
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        assert not service.exists()
        assert not linux_install.credential_daemon.parent.exists()

    def test_daemon_reload_failure_is_reported(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        runner = UninstallRunner(systemctl_error={'daemon-reload': 'busy'})
        rc, _ = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 1
        assert not service.exists()
        assert (
            '  systemd: still has the removed units loaded (busy)\n'
            'Remove them by hand.\n'
        ) in capsys.readouterr().err

    def test_rerun_after_reporting_unproven_units_reports_them_again(
        self, tmp_path, linux_install, capsys
    ):
        linux_install.credential_daemon.unlink()
        _, socket = self.our_units(linux_install, service=False)
        for _ in range(2):
            rc, _ = uninstall(tmp_path, ['--yes'])
            assert rc == 1
            assert f'  {socket}: ' in capsys.readouterr().err
        socket.unlink()
        rc, _ = uninstall(tmp_path, ['--yes'])
        assert rc == 0
        assert capsys.readouterr().out == (
            'aws-credential-daemon isn\'t installed.\n'
        )

    def test_rerun_asks_first(self, tmp_path, linux_install):
        linux_install.credential_daemon.unlink()
        service, _ = self.our_units(linux_install)
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, runner=runner, is_tty=True, answer=False)
        assert rc == 1
        assert runner.commands == []
        assert service.exists()


class TestUnitExecLines:
    def test_only_command_lines(self):
        # ExecSearchPath= and ExecPaths= list directories; every other
        # Exec* key, ExecCondition= included, is a command line.
        unit = (
            '[Service]\n'
            'ExecSearchPath=/usr/bin:/bin\n'
            'ExecPaths=/usr/local\n'
            'ExecCondition=/bin/true\n'
            'ExecStartPre=/bin/a\n'
            'ExecStart=/bin/b serve\n'
            'ExecReload = /bin/c\n'
        )
        assert _unit_exec_lines(unit) == [
            '/bin/true',
            '/bin/a',
            '/bin/b serve',
            ' /bin/c',
        ]
