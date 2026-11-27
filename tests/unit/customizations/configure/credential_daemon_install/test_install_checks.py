# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What install checks about the release and the machine before it says
Installed, and what uninstall recognises as this install's."""

import os
import plistlib

import pytest

from awscli.customizations.exceptions import ConfigurationError
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    NO_TSS_STDERR,
    STAGED,
    Runner,
    UninstallRunner,
    archive,
    credential_daemon_package,
    install,
    install_cli,
    linux_http,
    macos_http,
    macos_install,
    uninstall,
    write,
)

VERSION_1_0_0 = 'credsd 1.0.0\nstorage backends: tpm, file\n'


def staged_install(root):
    """An installed staged copy and its service under root."""
    write(root / STAGED.lstrip('/'), '#!/bin/sh\n').chmod(0o755)
    unit = write(
        root / 'etc/systemd/system/credsd.service',
        f'[Service]\nExecStart={STAGED} serve\n',
    )
    unit.chmod(0o644)
    write(root / 'etc/systemd/system/credsd.socket', '[Socket]\n').chmod(0o644)


class VersionRunner(Runner):
    """A Runner whose installed staged copy reports ``installed``, and
    whose downloaded copy reports ``downloaded``."""

    def __init__(self, installed, downloaded=VERSION_1_0_0, **kwargs):
        super().__init__(version=downloaded, **kwargs)
        self._installed = installed

    def __call__(self, command, check=True, timeout=None):
        if command[1:] == ['--version'] and command[0].endswith(
            'libexec/credsd/credsd'
        ):
            self.commands.append(command)
            return self._completed(command, self._installed)
        return super().__call__(command, check, timeout)

    def _completed(self, command, out):
        import subprocess

        return subprocess.CompletedProcess(command, 0, out, '')


@skip_if_windows
class TestLinuxArchiveIsTheRelease:
    """The signature binds bytes only, so the archive's
    own folder and credsd --version must say it's this release's TPM
    build."""

    def test_another_builds_folder_is_refused(self, pinned_key):
        # v0.1.0's al2023 build, relabelled as the portable one.
        data = archive(('credsd-al2023-x64-tpm/credsd', b'#!/bin/sh\n'))
        runner = Runner()
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(data=data), runner=runner)
        assert str(e.value) == (
            'The archive isn\'t the credsd-linux-x64-tpm release (it has no '
            'credsd-linux-x64-tpm/credsd), so aws-credential-daemon wasn\'t '
            'installed.'
        )
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_the_first_credsd_found_isnt_enough(self, pinned_key):
        data = archive(
            ('a/credsd', b'#!/bin/sh\n'),
            ('credsd-linux-x64/credsd', b'#!/bin/sh\n'),
        )
        with pytest.raises(ConfigurationError, match='isn\'t the credsd'):
            install(http=linux_http(data=data), runner=Runner())

    @pytest.mark.parametrize(
        'version, shown',
        [
            ('credsd 0.1.0\nstorage backends: tpm, file\n', '0.1.0'),
            ('credsd 9.9.9\nstorage backends: tpm\n', '9.9.9'),
        ],
    )
    def test_another_version_is_refused(self, pinned_key, version, shown):
        runner = Runner(version=version)
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value).startswith(
            f'The archive is aws-credential-daemon {shown} '
        )
        assert str(e.value).endswith(
            'but its release says 1.0.0 with the tpm backend, so it wasn\'t '
            'installed.'
        )
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_output_that_isnt_a_version_isnt_called_another_version(
        self, pinned_key
    ):
        runner = Runner(version='garbage\n')
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value) == (
            'The downloaded aws-credential-daemon didn\'t report its '
            'version (it printed: garbage), so it wasn\'t installed.'
        )
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_a_failed_version_check_reports_its_exit_code_and_error(
        self, pinned_key
    ):
        runner = Runner(version_rc=3, version_stderr='boom\x1b[2J\n')
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value) == (
            'Couldn\'t run the downloaded aws-credential-daemon (exit 3): '
            'boom[2J'
        )
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_a_failed_version_check_without_output_says_the_code_once(
        self, pinned_key
    ):
        runner = Runner(version_rc=3)
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert str(e.value) == (
            'Couldn\'t run the downloaded aws-credential-daemon (exit 3)'
        )

    def test_a_missing_tpm2_tss_is_named(self, pinned_key):
        # amazonlinux:2023 without tpm2-tss: the loader fails, exit 127.
        runner = Runner(version_rc=127, version_stderr=NO_TSS_STDERR)
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        message = str(e.value)
        assert message.startswith(
            'Couldn\'t run the downloaded aws-credential-daemon (exit 127): '
        )
        assert 'libtss2-esys.so.0' in message
        # The package names differ: apt has no tpm2-tss package.
        assert message.endswith(
            'Its TPM build needs the tpm2-tss libraries: the tpm2-tss '
            'package on Amazon Linux, Fedora and RHEL, or the libtss2-esys '
            'packages on Debian and Ubuntu. Install them, then run:\n'
            '  sudo aws configure credential-daemon install'
        )
        # Not read as a release that says another version.
        assert 'release says' not in message
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_a_build_without_the_tpm_backend_is_refused(self, pinned_key):
        # v0.2.0's non-TPM build passes the signature check too.
        runner = Runner(version='credsd 1.0.0\nstorage backends: file\n')
        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=runner)
        assert '(storage backends: file)' in str(e.value)
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_a_version_check_that_cant_run_is_refused(self, pinned_key):
        class Fails(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[1:] == ['--version']:
                    raise OSError(8, 'Exec format error')
                return super().__call__(command, check, timeout)

        with pytest.raises(ConfigurationError) as e:
            install(http=linux_http(), runner=Fails())
        assert str(e.value) == (
            'Couldn\'t run the downloaded aws-credential-daemon (Exec format '
            'error), so it wasn\'t installed.'
        )

    def test_the_version_check_has_a_timeout(self, pinned_key):
        seen = []

        class Records(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[1:] == ['--version']:
                    seen.append(timeout)
                return super().__call__(command, check, timeout)

        assert install(http=linux_http(), runner=Records()) == 0
        assert seen == [10]


@skip_if_windows
class TestMinimumAndDowngrade:
    """A release older than 0.2.0, or
    than the installed one, is refused before anything is downloaded."""

    def test_below_the_minimum_is_refused_before_the_download(
        self, pinned_key
    ):
        http = linux_http(tag='v0.1.0')
        runner = Runner(version='credsd 0.1.0\nstorage backends: tpm\n')
        with pytest.raises(ConfigurationError) as e:
            install(http=http, runner=runner)
        assert 'older than 0.2.0' in str(e.value)
        assert len(http.urls) == 1
        assert runner.commands == []

    def test_a_linux_downgrade_is_refused(self, pinned_key, tmp_path):
        runner = VersionRunner('credsd 1.1.0\nstorage backends: tpm\n')
        runner.root = str(tmp_path)
        staged_install(tmp_path)
        http = linux_http()
        with pytest.raises(ConfigurationError) as e:
            install(http=http, runner=runner, trusted_uid=os.getuid())
        assert str(e.value) == (
            'aws-credential-daemon\'s latest release is 1.0.0, older than '
            'the installed 1.1.0, so nothing was changed.'
        )
        assert len(http.urls) == 1
        # Only the installed copy ran; nothing was installed.
        assert [c for c in runner.commands if c[1:] == ['--version']] == [
            [str(tmp_path / STAGED.lstrip('/')), '--version']
        ]
        assert not any(c[1:] == ['install'] for c in runner.commands)

    def test_the_same_linux_version_reinstalls(
        self, pinned_key, tmp_path, capsys
    ):
        runner = VersionRunner(VERSION_1_0_0)
        runner.root = str(tmp_path)
        staged_install(tmp_path)
        assert (
            install(http=linux_http(), runner=runner, trusted_uid=os.getuid())
            == 0
        )
        assert 'already installed, so this reinstalls it' in (
            capsys.readouterr().out
        )

    def test_an_installed_copy_others_can_change_isnt_run(
        self, pinned_key, tmp_path
    ):
        # Root only runs it once only root could have written it.
        runner = VersionRunner('credsd 9.0.0\nstorage backends: tpm\n')
        runner.root = str(tmp_path)
        staged_install(tmp_path)
        (tmp_path / STAGED.lstrip('/')).chmod(0o777)
        assert (
            install(http=linux_http(), runner=runner, trusted_uid=os.getuid())
            == 0
        )
        assert not any(c[0].endswith(STAGED) for c in runner.commands)

    def info_plist(self, home, version):
        path = home / 'Applications/Credsd.app/Contents/Info.plist'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            plistlib.dumps({'CFBundleShortVersionString': version})
        )

    def run_macos(self, tmp_path, tag='v1.0.0'):
        http = macos_http(tag)
        runner = Runner(package=credential_daemon_package(tag.lstrip('v')))
        return (
            http,
            runner,
            install(
                system='darwin', http=http, runner=runner, home=str(tmp_path)
            ),
        )

    def test_a_truncated_info_plist_is_no_version(self, tmp_path):
        # A truncated XML plist raises ExpatError, which isn't a
        # ValueError: install goes on rather than failing on a traceback.
        macos_install(tmp_path, tmp_path / '.local/bin')
        path = tmp_path / 'Applications/Credsd.app/Contents/Info.plist'
        path.write_bytes(
            plistlib.dumps({'CFBundleShortVersionString': '9.0.0'})[:60]
        )
        _, _, rc = self.run_macos(tmp_path)
        assert rc == 0

    def test_a_macos_downgrade_is_refused(self, tmp_path):
        macos_install(tmp_path, tmp_path / '.local/bin')
        self.info_plist(tmp_path, '1.1.0')
        with pytest.raises(ConfigurationError) as e:
            self.run_macos(tmp_path)
        assert str(e.value) == (
            'aws-credential-daemon\'s latest release is 1.0.0, older than '
            'the installed 1.1.0, so nothing was changed.'
        )

    @pytest.mark.parametrize('version', ['1.0.0', '0.9.0', 'garbage'])
    def test_a_macos_upgrade_or_reinstall_goes_on(self, tmp_path, version):
        macos_install(tmp_path, tmp_path / '.local/bin')
        self.info_plist(tmp_path, version)
        _, runner, rc = self.run_macos(tmp_path)
        assert rc == 0
        assert runner.commands[-1][0] == '/usr/sbin/installer'


@skip_if_windows
class TestMacOSReinstall:
    def test_says_it_reinstalls(self, tmp_path, capsys):
        macos_install(tmp_path, tmp_path / '.local/bin')
        http = macos_http()
        runner = Runner(package=credential_daemon_package('1.0.0'))
        install(system='darwin', http=http, runner=runner, home=str(tmp_path))
        assert capsys.readouterr().out.startswith(
            'aws-credential-daemon is already installed for this user, so '
            'this reinstalls it.\n'
        )

    def test_says_nothing_on_a_first_install(self, tmp_path, capsys):
        http = macos_http()
        runner = Runner(package=credential_daemon_package('1.0.0'))
        install(system='darwin', http=http, runner=runner, home=str(tmp_path))
        assert 'reinstalls' not in capsys.readouterr().out


def shown_service(root, exec_start=None, drop_ins='', fragment=None):
    """systemctl show's answer for credsd.service under root."""
    exec_start = exec_start or os.path.join(root, STAGED.lstrip('/'))
    fragment = fragment or os.path.join(
        root, 'etc/systemd/system/credsd.service'
    )
    return (
        f'ExecStart={{ path={exec_start} ; argv[]={exec_start} serve '
        '--system ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; '
        'pid=0 ; code=(null) ; status=0/0 }\n'
        'ExecStartPre=\nExecStartPost=\nExecReload=\nExecStop=\n'
        'ExecStopPost=\n'
        f'DropInPaths={drop_ins}\n'
        f'FragmentPath={fragment}\n'
    )


@skip_if_windows
class TestServiceCheckAsksSystemd:
    """What systemd will run, not the unit file's text."""

    def run(self, service_properties):
        runner = Runner(service_properties=service_properties)
        return runner, install_cli(http=linux_http(), runner=runner)

    def test_the_staged_copy_passes(self, pinned_key):
        _, rc = self.run(lambda root: shown_service(root))
        assert rc == 0

    def test_a_drop_in_that_runs_another_program_is_rolled_back(
        self, pinned_key, capsys
    ):
        # override.conf with ExecStart=/bin/true: the unit file still says
        # the staged copy.
        runner, rc = self.run(
            lambda root: shown_service(root, exec_start='/bin/true')
        )
        assert rc == 253
        assert 'credsd.service runs /bin/true, not ' in capsys.readouterr().err
        assert runner.uninstaller_existed == [True]

    def test_a_drop_in_with_an_exec_line_is_rolled_back(
        self, pinned_key, tmp_path, capsys
    ):
        drop_in = write(
            tmp_path / 'credsd.service.d/override.conf',
            '[Service]\nExecStartPre=/bin/sh -c id\n',
        )
        drop_in.chmod(0o644)
        runner = Runner(
            service_properties=lambda root: shown_service(
                root, drop_ins=str(drop_in)
            )
        )
        with pytest.MonkeyPatch.context() as patch:
            # The drop-in's folders are the test user's, standing in for
            # root's.
            patch.setattr(
                'awscli.customizations.configure.credential_daemon_install.'
                'linux.LinuxInstall._root_only_problem',
                lambda self, path, root=None: None,
            )
            rc = install_cli(http=linux_http(), runner=runner)
        assert rc == 253
        assert 'that sets what it runs' in capsys.readouterr().err

    def test_a_drop_in_others_can_change_is_rolled_back(
        self, pinned_key, tmp_path, capsys
    ):
        drop_in = write(tmp_path / 'override.conf', '[Service]\n')
        drop_in.chmod(0o666)
        _, rc = self.run(
            lambda root: shown_service(root, drop_ins=str(drop_in))
        )
        assert rc == 253
        assert 'users other than root can change' in capsys.readouterr().err

    def test_another_unit_file_is_rolled_back(self, pinned_key, capsys):
        _, rc = self.run(
            lambda root: shown_service(
                root, fragment='/run/systemd/system/credsd.service'
            )
        )
        assert rc == 253
        assert (
            'systemd loads credsd.service from '
            '/run/systemd/system/credsd.service'
        ) in capsys.readouterr().err

    def test_an_unreadable_answer_falls_back_to_the_unit_file(
        self, pinned_key
    ):
        # The fake writes a unit that runs the staged copy.
        _, rc = self.run(None)
        assert rc == 0


@skip_if_windows
class TestTakingOverAnotherService:
    """Install says it replaces a service that runs
    another program."""

    def test_names_the_program_that_stays(self, pinned_key, tmp_path, capsys):
        runner = Runner()
        runner.root = str(tmp_path)
        write(
            tmp_path / 'etc/systemd/system/credsd.service',
            '[Service]\nExecStart=/usr/local/bin/credsd serve\n',
        )
        install(http=linux_http(), runner=runner)
        assert capsys.readouterr().out.startswith(
            'aws-credential-daemon\'s service runs /usr/local/bin/credsd, '
            'not the release this command installs. Installing replaces the '
            'service with the GitHub release; /usr/local/bin/credsd stays.\n'
        )


KEPT = 'tmpab12cd34/release/credsd-linux-x64-tpm/credsd'


@skip_if_windows
class TestRefusalNamesOnlyARootOnlyProgram:
    def test_a_root_only_credsd_is_named(self, tmp_path, linux_install):
        linux_install.credential_daemon.unlink()
        service, _ = linux_install.units
        service.write_text(
            '[Service]\nExecStart=/opt/credsd/bin/credsd serve\n'
        )
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                'awscli.customizations.configure.credential_daemon_install.'
                'linux.LinuxInstall._root_only_problem',
                lambda self, path, root=None: None,
            )
            with pytest.raises(ConfigurationError) as e:
                uninstall(tmp_path, ['--yes'], runner=UninstallRunner())
        assert str(e.value).endswith(
            'Uninstall it with: sudo /opt/credsd/bin/credsd uninstall'
        )


@skip_if_windows
class TestUninstallAfterACutShortRollback:
    """Units left running our kept temp copy are this
    install's."""

    def make(self, tmp_path, linux_install):
        temp_root = tmp_path / 'tmp'
        program = write(temp_root / KEPT, '#!/bin/sh\n')
        for folder in [temp_root / 'tmpab12cd34', *program.parents]:
            if folder == temp_root:
                break
            folder.chmod(0o700)
        linux_install.credential_daemon.unlink()
        service, socket = linux_install.units
        service.write_text(f'[Service]\nExecStart={program} serve --system\n')
        service.chmod(0o644)
        socket.write_text('[Socket]\nListenStream=/run/credsd/credsd.sock\n')
        socket.chmod(0o644)
        return temp_root, program

    def test_removes_the_units_and_the_kept_folder(
        self, tmp_path, linux_install, capsys
    ):
        temp_root, _ = self.make(tmp_path, linux_install)
        runner = UninstallRunner()
        rc, _ = uninstall(
            tmp_path, ['--yes'], runner=runner, temp_root=str(temp_root)
        )
        assert rc == 0
        assert [c[1:3] for c in runner.commands] == [
            ['disable', '--now'],
            ['daemon-reload'],
        ]
        assert not any(os.path.lexists(u) for u in linux_install.units)
        assert not (temp_root / 'tmpab12cd34').exists()
        assert 'Removed aws-credential-daemon.' in capsys.readouterr().out

    def test_a_kept_path_others_can_change_isnt_ours(
        self, tmp_path, linux_install
    ):
        temp_root, program = self.make(tmp_path, linux_install)
        # Recreated by someone else after a reboot cleared /tmp.
        (temp_root / 'tmpab12cd34').chmod(0o777)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError) as e:
            uninstall(
                tmp_path, ['--yes'], runner=runner, temp_root=str(temp_root)
            )
        # Another user could have put that program there, so it isn't
        # suggested to run as root; the unit commands are.
        assert str(program) not in str(e.value)
        assert str(e.value).endswith(
            'To remove its service, run:\n'
            '  sudo systemctl disable --now credsd.socket credsd.service\n'
            f'  sudo rm {linux_install.units[1]} {linux_install.units[0]}\n'
            '  sudo systemctl daemon-reload'
        )
        assert runner.commands == []
        assert all(os.path.lexists(u) for u in linux_install.units)


@skip_if_windows
class TestServiceCheckNeedsBothViews:
    """systemd's view is out of date until a daemon-reload, so the unit
    file on disk is checked too."""

    def test_a_unit_file_running_our_copy_is_rolled_back(
        self, pinned_key, capsys
    ):
        # The installer rewrote the unit to run our temp copy and stopped
        # before its daemon-reload: systemd still shows the staged copy.
        runner = Runner(
            exec_start='self', service_properties=lambda r: shown_service(r)
        )
        assert install_cli(http=linux_http(), runner=runner) == 253
        assert 'credsd.service runs ' in capsys.readouterr().err
        assert runner.uninstaller_existed == [True]

    def test_a_unit_systemd_hasnt_reloaded_is_rolled_back(
        self, pinned_key, capsys
    ):
        runner = Runner(
            service_properties=lambda r: shown_service(r)
            + 'NeedDaemonReload=yes\n'
        )
        assert install_cli(http=linux_http(), runner=runner) == 253
        assert 'systemd hasn\'t loaded the current' in capsys.readouterr().err

    def test_every_exec_line_is_checked(self, pinned_key, capsys):
        # systemctl show prints one line per command, with the same key.
        def shown(root):
            staged = os.path.join(root, STAGED.lstrip('/'))
            return (
                'ExecStart={ path=/bin/true ; argv[]=/bin/true }\n'
                + shown_service(root, exec_start=staged)
            )

        runner = Runner(service_properties=shown)
        assert install_cli(http=linux_http(), runner=runner) == 253
        assert 'runs /bin/true' in capsys.readouterr().err


@skip_if_windows
class TestOrderAndOptions:
    def test_the_downgrade_refusal_says_nothing_about_reinstalling(
        self, pinned_key, tmp_path, capsys
    ):
        runner = VersionRunner('credsd 1.1.0\nstorage backends: tpm\n')
        runner.root = str(tmp_path)
        staged_install(tmp_path)
        with pytest.raises(ConfigurationError):
            install(http=linux_http(), runner=runner, trusted_uid=os.getuid())
        assert 'reinstalls' not in capsys.readouterr().out

    @pytest.mark.parametrize('linked', ['usr/local', 'usr'])
    def test_a_linked_usr_local_is_refused_before_the_download(
        self, pinned_key, tmp_path, linked
    ):
        # rpm-ostree: /usr/local links to /var/usrlocal. credsd's unit then
        # runs /var/usrlocal/libexec/credsd/credsd, which the service check
        # would roll back after a good install.
        real = tmp_path / 'var' / linked.replace('/', '')
        real.mkdir(parents=True)
        if linked == 'usr/local':
            (tmp_path / 'usr').mkdir()
        (tmp_path / linked).symlink_to(real)
        runner = Runner()
        runner.root = str(tmp_path)
        http = linux_http()
        with pytest.raises(ConfigurationError) as e:
            install(http=http, runner=runner)
        assert str(e.value) == (
            f'/{linked} is a symbolic link (as on rpm-ostree systems), which '
            'this command doesn\'t support, so nothing was downloaded.'
        )
        assert http.urls == []
        assert runner.commands == []

    def test_after_a_macos_uninstall_the_kept_app_isnt_installed(
        self, tmp_path
    ):
        # The app stays after an uninstall; it doesn't block an older
        # release.
        macos_install(tmp_path, tmp_path / '.local/bin', launch_agent=False)
        info = tmp_path / 'Applications/Credsd.app/Contents/Info.plist'
        info.write_bytes(
            plistlib.dumps({'CFBundleShortVersionString': '9.0.0'})
        )
        runner = Runner(package=credential_daemon_package('1.0.0'))
        rc = install(
            system='darwin',
            http=macos_http(),
            runner=runner,
            home=str(tmp_path),
        )
        assert rc == 0
