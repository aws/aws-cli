# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
import shutil

import pytest

from awscli.customizations.exceptions import (
    ConfigurationError,
)
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    CREDENTIAL_DAEMON_PACKAGE,
    GOOD_PKGUTIL,
    GOOD_PKGUTIL_LEAF,
    Runner,
    UninstallRunner,
    install,
    macos_http,
    macos_install,
    package_info,
    uninstall,
    write,
)

pytestmark = skip_if_windows


class TestMacOS:
    def http(self):
        return macos_http()

    def test_installs_a_signed_notarized_package_for_this_user(self, capsys):
        runner = Runner()
        assert (
            install(
                system='darwin',
                is_root=False,
                http=self.http(),
                runner=runner,
            )
            == 0
        )
        # Tools come from fixed paths, not PATH.
        assert runner.commands[0][:2] == [
            '/usr/sbin/pkgutil',
            '--check-signature',
        ]
        assert runner.commands[1][:2] == ['/usr/sbin/pkgutil', '--expand']
        assert runner.commands[2][0] == '/usr/sbin/installer'
        assert runner.commands[2][-2:] == [
            '-target',
            'CurrentUserHomeDirectory',
        ]
        out = capsys.readouterr().out
        assert 'Installed aws-credential-daemon for this user.\n' in out
        assert 'system service' not in out

    @pytest.mark.parametrize(
        'program, ran',
        [('/usr/sbin/pkgutil', 1), ('/usr/sbin/installer', 3)],
    )
    def test_a_tool_that_cant_run_is_a_clean_error(self, program, ran):
        class Missing(Runner):
            def __call__(self, command, check=True, timeout=None):
                if command[0] == program:
                    self.commands.append(command)
                    raise FileNotFoundError(2, 'No such file or directory')
                return super().__call__(command, check)

        runner = Missing()
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=self.http(), runner=runner)
        assert str(e.value) == (
            f'Couldn\'t run {program} (No such file or directory), so '
            'aws-credential-daemon wasn\'t installed.'
        )
        assert len(runner.commands) == ran

    @pytest.mark.parametrize(
        'pkgutil',
        [
            GOOD_PKGUTIL.replace(
                'trusted by the Apple notary service', 'none'
            ),
            GOOD_PKGUTIL.replace('94KV3E626L', 'ABCDE12345'),
            'Status: no signature\n',
            # The Team ID only in lines the path's newlines made.
            'Package "/tmp/x\n'
            '    1. Developer ID Installer: AMZN Mobile LLC (94KV3E626L)\n'
            '.pkg":\n'
            '   Status: signed by a developer certificate issued by Apple '
            'for distribution\n'
            '   Notarization: trusted by the Apple notary service\n'
            '   Certificate Chain:\n'
            '    1. Developer ID Installer: Someone Else (ABCDE12345)\n',
            # The status and notarization only in the path line.
            'Package "/tmp/signed by a developer certificate issued by '
            'Apple, trusted by the Apple notary service.pkg":\n'
            '   Status: no signature\n'
            '   Certificate Chain:\n'
            '    1. Developer ID Installer: AMZN Mobile LLC (94KV3E626L)\n',
            # Our certificate, but not as the leaf.
            GOOD_PKGUTIL.replace(
                GOOD_PKGUTIL_LEAF,
                '    1. Developer ID Installer: Someone Else (ABCDE12345)\n'
                + GOOD_PKGUTIL_LEAF.replace('1. ', '2. '),
            )
            .replace(
                '    2. Developer ID Certification Authority',
                '    3. Developer ID Certification Authority',
            )
            .replace('    3. Apple Root CA', '    4. Apple Root CA'),
            # Our Team ID, but not a Developer ID Installer certificate.
            GOOD_PKGUTIL.replace(
                'Developer ID Installer: AMZN Mobile LLC',
                'Developer ID Application: AMZN Mobile LLC',
            ),
            # Entries out of order.
            GOOD_PKGUTIL.replace('    1. ', '    2. ', 1),
            # A status given twice.
            GOOD_PKGUTIL.replace(
                '   Notarization:', '   Status: no signature\n   Notarization:'
            ),
            # Blank lines are skipped, but what follows them still counts.
            GOOD_PKGUTIL + '\nPackage "other.pkg":\n',
            GOOD_PKGUTIL.replace(
                '   Notarization:',
                '\n   Status: no signature\n   Notarization:',
            ),
        ],
    )
    def test_unsigned_or_foreign_packages_are_refused(self, pkgutil):
        runner = Runner(pkgutil=pkgutil)
        with pytest.raises(ConfigurationError):
            install(system='darwin', http=self.http(), runner=runner)
        assert len(runner.commands) == 1

    def test_reads_pkgutils_full_output(self):
        pkgutil = (
            'Package "credsd-1.0.0.pkg":\n'
            '   Status: signed by a developer certificate issued by Apple '
            'for distribution\n'
            '   Notarization: trusted by the Apple notary service\n'
            '   Signed with a trusted timestamp on: 2026-11-11 18:02:11 '
            '+0000\n'
            '   Certificate Chain:\n'
            '    1. Developer ID Installer: AMZN Mobile LLC (94KV3E626L)\n'
            '       Expires: 2031-02-01 22:12:15 +0000\n'
            '       SHA256 Fingerprint:\n'
            '           6A 2E 9F 01 3C 7B 44 D2 8E 0A 51 19 C3 6F 82 B4 1D\n'
            '       ------------------------------------------------------\n'
            '    2. Developer ID Certification Authority\n'
            '       Expires: 2031-09-17 00:00:00 +0000\n'
            '    3. Apple Root CA\n'
            '       Expires: 2035-02-09 21:40:36 +0000\n'
        )
        runner = Runner(pkgutil=pkgutil)
        assert install(system='darwin', http=self.http(), runner=runner) == 0

    @pytest.mark.parametrize(
        'pkgutil',
        [
            GOOD_PKGUTIL,
            GOOD_PKGUTIL + '\n',
            GOOD_PKGUTIL + '   \n',
            GOOD_PKGUTIL.replace(
                '   Certificate Chain:\n', '\n   Certificate Chain:\n'
            ),
        ],
    )
    def test_blank_lines_in_pkgutils_output_are_skipped(self, pkgutil):
        runner = Runner(pkgutil=pkgutil)
        assert install(system='darwin', http=self.http(), runner=runner) == 0

    def test_installs_a_product_archive_of_credential_daemon_components(self):
        package = {
            'Distribution': '<installer-gui-script/>',
            'credsd.pkg/PackageInfo': CREDENTIAL_DAEMON_PACKAGE['PackageInfo'],
        }
        runner = Runner(package=package)
        assert install(system='darwin', http=self.http(), runner=runner) == 0

    @pytest.mark.parametrize(
        'package',
        [
            {'PackageInfo': package_info('com.amazon.aws.cli2')},
            {
                'Distribution': '<installer-gui-script/>',
                'credsd.pkg/PackageInfo': CREDENTIAL_DAEMON_PACKAGE[
                    'PackageInfo'
                ],
                'other.pkg/PackageInfo': package_info('com.amazon.other'),
            },
            {'Distribution': '<installer-gui-script/>'},
            {'PackageInfo': 'not xml'},
        ],
    )
    def test_other_amazon_packages_are_refused(self, package):
        runner = Runner(package=package)
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=self.http(), runner=runner)
        assert 'isn\'t com.amazon.aws.credsd.daemon' in str(e.value)
        assert len(runner.commands) == 2

    def test_a_package_that_wont_expand_is_refused(self):
        runner = Runner(expand_rc=1)
        with pytest.raises(ConfigurationError):
            install(system='darwin', http=self.http(), runner=runner)
        assert len(runner.commands) == 2


AGENT = 'Library/LaunchAgents/com.amazon.aws.credsd.daemon.plist'


LEFT = (
    'Left ~/Applications/Credsd.app, ~/.local/bin/credsd, '
    '~/.local/bin/creds, as aws-credential-daemon\'s own uninstall does. '
    'To remove them: rm -r ~/Applications/Credsd.app ~/.local/bin/credsd '
    '~/.local/bin/creds\n'
)


class TestUninstallMacOSUser:
    def install(self, tmp_path):
        home = tmp_path / 'home'
        installed = macos_install(home, home / '.local/bin')
        installed.agent = installed.launch_agent
        installed.data = write(
            home / 'Library/Application Support/credsd/credentials'
        )
        return installed

    def run(self, tmp_path, runner=None, **kwargs):
        return uninstall(
            tmp_path,
            ['--yes'],
            system='darwin',
            is_root=False,
            runner=runner,
            **kwargs,
        )

    def test_runs_credential_daemon_uninstall_user_and_keeps_the_app(
        self, tmp_path, capsys
    ):
        installed = self.install(tmp_path)
        runner = UninstallRunner(removes=[installed.agent])
        rc, _ = self.run(tmp_path, runner)
        assert rc == 0
        # Only aws-credential-daemon's uninstaller: no receipt is forgotten.
        assert runner.commands == [
            [str(installed.credential_daemon), 'uninstall', '--user']
        ]
        assert installed.bundle.exists()
        assert os.path.lexists(installed.bin / 'credsd')
        assert os.path.lexists(installed.bin / 'creds')
        assert installed.data.exists()
        assert capsys.readouterr().out == (
            'Removed aws-credential-daemon for this user. '
            'The credential daemon\'s saved sign-ins and keys stay on this '
            'machine, so reinstalling brings them back. Nothing in ~/.aws '
            'was changed.\n' + LEFT
        )

    @pytest.mark.parametrize('name', ['.zprofile', '.bash_profile'])
    def test_names_the_file_with_the_path_block(self, tmp_path, capsys, name):
        installed = self.install(tmp_path)
        profile = write(
            tmp_path / 'home' / name,
            'export A=1\n# Added by credsd\nexport PATH="$HOME/.local/bin:'
            '$PATH"\n',
        )
        rc, _ = self.run(tmp_path, UninstallRunner(removes=[installed.agent]))
        assert rc == 0
        assert capsys.readouterr().out.endswith(
            f'Left the lines marked "# Added by credsd" in ~/{name}. Remove '
            f'them if you no longer need ~/.local/bin on PATH.\n'
        )
        # The block stays.
        assert '# Added by credsd' in profile.read_text()

    def test_no_path_block_no_line(self, tmp_path, capsys):
        installed = self.install(tmp_path)
        write(tmp_path / 'home/.zprofile', 'export A=1\n')
        self.run(tmp_path, UninstallRunner(removes=[installed.agent]))
        assert 'Added by credsd' not in capsys.readouterr().out

    def test_a_second_uninstall_says_it_isnt_installed(self, tmp_path, capsys):
        # The app stays after an uninstall, so it isn't what
        # says it's installed; the LaunchAgent uninstall removes is.
        installed = self.install(tmp_path)
        installed.agent.unlink()
        runner = UninstallRunner()
        rc, command = self.run(tmp_path, runner)
        assert rc == 0
        assert runner.commands == []
        command._ask.assert_not_called()
        assert capsys.readouterr().out == (
            'aws-credential-daemon isn\'t installed for this user.\n'
        )
        assert installed.bundle.exists()

    def test_not_installed_for_this_user(self, tmp_path, capsys):
        runner = UninstallRunner()
        rc, _ = self.run(tmp_path, runner)
        assert rc == 0
        assert 'isn\'t installed for this user' in capsys.readouterr().out
        assert runner.commands == []

    def test_only_links_left_is_not_an_install(self, tmp_path, capsys):
        installed = self.install(tmp_path)
        shutil.rmtree(installed.bundle)
        installed.agent.unlink()
        runner = UninstallRunner()
        rc, _ = self.run(tmp_path, runner)
        assert rc == 0
        # The links dangle now; they stay, and nothing is said about them.
        assert capsys.readouterr().out == (
            'aws-credential-daemon isn\'t installed for this user.\n'
        )
        assert runner.commands == []
        assert os.path.lexists(installed.bin / 'credsd')

    def test_nothing_left_says_only_not_installed(self, tmp_path, capsys):
        installed = self.install(tmp_path)
        shutil.rmtree(installed.bundle)
        installed.agent.unlink()
        for name in ('credsd', 'creds'):
            (installed.bin / name).unlink()
        rc, _ = self.run(tmp_path, UninstallRunner())
        assert rc == 0
        # The aws link points elsewhere, so it isn't named.
        assert capsys.readouterr().out == (
            'aws-credential-daemon isn\'t installed for this user.\n'
        )

    def test_names_the_app_and_links_that_stay(self, tmp_path, capsys):
        # credsd stays on PATH with no service behind it.
        installed = self.install(tmp_path)
        rc, _ = self.run(tmp_path, UninstallRunner(removes=[installed.agent]))
        assert rc == 0
        assert capsys.readouterr().out.endswith(LEFT)

    def test_names_only_what_is_still_there(self, tmp_path, capsys):
        installed = self.install(tmp_path)
        (installed.bin / 'creds').unlink()
        self.run(tmp_path, UninstallRunner(removes=[installed.agent]))
        assert capsys.readouterr().out.endswith(
            'Left ~/Applications/Credsd.app, ~/.local/bin/credsd, as '
            'aws-credential-daemon\'s own uninstall does. To remove them: '
            'rm -r ~/Applications/Credsd.app ~/.local/bin/credsd\n'
        )

    def test_an_app_without_credential_daemon_is_refused(self, tmp_path):
        installed = self.install(tmp_path)
        installed.credential_daemon.unlink()
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError, match='is missing'):
            self.run(tmp_path, runner)
        assert runner.commands == []
        assert installed.bundle.exists()

    def test_a_symlinked_bundle_is_refused(self, tmp_path):
        elsewhere = tmp_path / 'elsewhere.app'
        elsewhere.mkdir()
        bundle = tmp_path / 'home/Applications/Credsd.app'
        bundle.parent.mkdir(parents=True)
        bundle.symlink_to(elsewhere)
        write(tmp_path / 'home' / AGENT)
        runner = UninstallRunner()
        with pytest.raises(ConfigurationError):
            self.run(tmp_path, runner)
        assert runner.commands == []
        assert elsewhere.exists()

    def test_uninstaller_failure_exits_with_an_error(self, tmp_path):
        installed = self.install(tmp_path)
        runner = UninstallRunner(error='launchctl unload failed')
        with pytest.raises(ConfigurationError) as e:
            self.run(tmp_path, runner)
        assert 'launchctl unload failed' in str(e.value)
        assert f'still installed at {installed.bundle}' in str(e.value)
        assert installed.bundle.exists()
        assert os.path.lexists(installed.bin / 'credsd')
