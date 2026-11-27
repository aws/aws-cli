# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
from argparse import Namespace

import pytest

from awscli.customizations.configure.credential_daemon_install import (
    commands,
    links,
)
from awscli.customizations.configure.credential_daemon_install import (
    host as install_host,
)
from awscli.customizations.configure.credential_daemon_install import (
    linux as install_linux,
)
from awscli.customizations.configure.credential_daemon_install import (
    macos as install_macos,
)
from awscli.customizations.configure.credential_daemon_install import (
    release as install_release,
)
from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
)
from awscli.customizations.configure.credentialdaemon import (
    ConfigureCredentialDaemonCommand,
    InstallCredentialDaemonCommand,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from tests import mock
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    FakeHttp,
    Runner,
    UninstallRunner,
    home_with_link,
    install,
    linux_http,
    macos_http,
    macos_install,
    uninstall,
)


class TestNoDocPlaceholder:
    def test_no_user_facing_string_has_the_doc_placeholder(self):
        # Until credsd's install doc exists, nothing may print a
        # placeholder for it. Every string the module could print is a
        # literal in its source.
        import ast
        import inspect

        modules = [
            commands,
            install_host,
            install_release,
            links,
            install_linux,
            install_macos,
        ]
        strings = [
            node.value
            for module in modules
            for node in ast.walk(ast.parse(inspect.getsource(module)))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        assert strings
        assert not [s for s in strings if '<CREDENTIAL_DAEMON_DOC>' in s]
        assert not any(
            hasattr(module, 'CREDENTIAL_DAEMON_DOC') for module in modules
        )


# After the installer exits 0, say only that aws-credential-daemon was
# installed. aws-credential-daemon doesn't report where it seals secrets, so
# the CLI doesn't name a keystore.
class TestNoKeystoreClaim:
    def assert_no_claim(self, out):
        assert 'Secrets are sealed' not in out
        for keystore in ('TPM', 'Secure Enclave', 'keychain'):
            assert keystore not in out

    def test_linux(self, pinned_key, capsys):
        rc = install(
            http=linux_http(),
            runner=Runner(),
        )
        out = capsys.readouterr().out
        assert rc == 0
        assert 'Installed aws-credential-daemon as a system service.\n' in out
        self.assert_no_claim(out)

    def test_macos(self, capsys):
        rc = install(system='darwin', http=macos_http(), runner=Runner())
        out = capsys.readouterr().out
        assert rc == 0
        assert 'Installed aws-credential-daemon for this user.\n' in out
        self.assert_no_claim(out)


@skip_if_windows
class TestUninstallConfirmation:
    def test_no_terminal_and_no_yes_changes_nothing(
        self, tmp_path, linux_install
    ):
        runner = UninstallRunner()
        with pytest.raises(ParamValidationError, match='--yes'):
            uninstall(tmp_path, runner=runner, is_tty=False)
        assert runner.commands == []
        assert linux_install.credential_daemon.exists()

    def test_terminal_warns_and_asks(self, tmp_path, linux_install, capsys):
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, command = uninstall(tmp_path, runner=runner, is_tty=True)
        assert rc == 0
        assert capsys.readouterr().err == (
            'Profiles that use the credential daemon stop working until '
            'they move back to files.\n'
            'To move them back before uninstalling, answer no and set '
            'credential_storage = file in each profile. Each profile moves '
            "at its next sign-in. A profile with access keys there doesn't "
            'move: remove its credential_daemon and enter the keys again '
            'with aws configure.\n'
        )
        command._ask.assert_called_once_with(
            'This removes it for every user on this machine. Continue? '
            '[y/N] ',
            default=False,
        )

    def test_per_user_question(self, tmp_path, capsys):
        home = tmp_path / 'home'
        macos_install(home, home / '.local/bin')
        _, command = uninstall(
            tmp_path,
            system='darwin',
            is_root=False,
            is_tty=True,
        )
        command._ask.assert_called_once_with('Continue? [y/N] ', default=False)
        assert 'move them back before uninstalling, answer no' in (
            capsys.readouterr().err
        )

    def test_no_answer_changes_nothing(self, tmp_path, linux_install, capsys):
        runner = UninstallRunner()
        rc, _ = uninstall(tmp_path, runner=runner, is_tty=True, answer=False)
        assert rc == 1
        assert runner.commands == []
        assert linux_install.credential_daemon.exists()
        assert 'Nothing was uninstalled.' in capsys.readouterr().out

    def test_yes_skips_the_question(self, tmp_path, linux_install):
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, command = uninstall(tmp_path, ['--yes'], runner=runner)
        assert rc == 0
        command._ask.assert_not_called()

    def test_yes_in_a_terminal_prints_no_warning(
        self, tmp_path, linux_install, capsys
    ):
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, command = uninstall(
            tmp_path, ['--yes'], runner=runner, is_tty=True
        )
        assert rc == 0
        command._ask.assert_not_called()
        assert capsys.readouterr().err == ''


class TestCredentialDaemonSubcommands:
    def test_uninstall_is_a_subcommand(self):
        names = [
            sub['name'] for sub in ConfigureCredentialDaemonCommand.SUBCOMMANDS
        ]
        assert names == ['install', 'uninstall', 'link']


class TestHelpNamesNoInternalName:
    @pytest.mark.parametrize(
        'command',
        [
            ('configure', 'credential-daemon'),
            ('configure', 'credential-daemon', 'install'),
            ('configure', 'credential-daemon', 'uninstall'),
            ('configure', 'credential-daemon', 'link'),
        ],
    )
    def test_help_says_aws_credential_daemon_not_credsd(self, command):
        from awscli.testutils import CapturedRenderer, create_clidriver

        renderer = CapturedRenderer()
        with mock.patch('awscli.help.get_renderer', return_value=renderer):
            create_clidriver().main([*command, 'help'])
        text = renderer.rendered_contents
        assert 'aws-credential-daemon' in text
        # The AWS CLI User Guide page's own name has it.
        text = text.replace('/cli-authentication-credsd.html', '')
        assert 'credsd' not in text.lower()


class TestHelpNamesOnlyWhatMoves:
    # This release moves aws login sessions at their next sign-in, and
    # stores only a new profile's access keys in the credential daemon.
    KEYS_DONT_MOVE = (
        "A profile with access keys there doesn't move: remove its "
        'credential_daemon and enter the keys again with aws configure.'
    )

    def help_text(self, subcommand):
        from awscli.testutils import CapturedRenderer, create_clidriver

        renderer = CapturedRenderer()
        with mock.patch('awscli.help.get_renderer', return_value=renderer):
            create_clidriver().main(
                ['configure', 'credential-daemon', subcommand, 'help']
            )
        # The example's prose wraps and quotes names; compare plain words.
        text = renderer.rendered_contents.replace('``', '')
        return ' '.join(text.split())

    def test_install_help_says_only_sessions_and_new_keys_move(self):
        text = self.help_text('install')
        assert (
            "Installing changes no profile: a profile's aws login session "
            'moves at its next sign-in, after asking, and aws configure asks '
            "for a new profile's access keys."
        ) in text
        assert 'each profile moves' not in text

    def test_install_help_names_the_proxy_settings_and_tls(self):
        text = self.help_text('install')
        assert (
            'sudo --preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,'
            'AWS_CA_BUNDLE aws configure credential-daemon install'
        ) in text
        assert '--no-verify-ssl is refused' in text

    def test_uninstall_help_says_keys_profiles_dont_move(self):
        # The description, the example's prose and its output.
        assert self.help_text('uninstall').count(self.KEYS_DONT_MOVE) == 3


class TestCommandName:
    def test_configure_has_the_credential_daemon_command(self):
        from awscli.customizations.configure.configure import (
            ConfigureCommand,
        )

        names = [sub['name'] for sub in ConfigureCommand.SUBCOMMANDS]
        assert 'credential-daemon' in names

    def test_help_shows_the_command_name(self):
        from awscli.testutils import CapturedRenderer, create_clidriver

        renderer = CapturedRenderer()
        with mock.patch('awscli.help.get_renderer', return_value=renderer):
            create_clidriver().main(
                ['configure', 'credential-daemon', 'install', 'help']
            )
        text = renderer.rendered_contents
        assert 'aws configure credential-daemon install' in text

    def test_the_old_name_isnt_a_command(self, capsys):
        from awscli.testutils import create_clidriver

        rc = create_clidriver().main(
            ['configure', 'credentials-daemon', 'install']
        )
        assert rc == 252
        assert "invalid choice 'credentials-daemon'" in capsys.readouterr().err


class TestNoUserOption:
    @pytest.mark.parametrize('subcommand', ['install', 'uninstall'])
    def test_user_is_not_an_option(self, subcommand, capsys):
        from awscli.testutils import create_clidriver

        rc = create_clidriver().main(
            ['configure', 'credential-daemon', subcommand, '--user']
        )
        assert rc == 252
        assert 'Unknown options: --user' in capsys.readouterr().err

    @pytest.mark.parametrize(
        'subcommand, synopsis',
        [
            ('install', 'aws configure credential-daemon install\n'),
            ('uninstall', 'aws configure credential-daemon uninstall [--yes]'),
        ],
    )
    def test_help_says_macos_is_per_user_and_linux_needs_root(
        self, subcommand, synopsis
    ):
        from awscli.testutils import CapturedRenderer, create_clidriver

        renderer = CapturedRenderer()
        with mock.patch('awscli.help.get_renderer', return_value=renderer):
            create_clidriver().main(
                ['configure', 'credential-daemon', subcommand, 'help']
            )
        text = renderer.rendered_contents
        assert synopsis in text
        assert '--user' not in text
        assert 'without sudo' in text
        assert f'sudo aws configure credential-daemon {subcommand}' in text
        assert 'root' in text


@skip_if_windows
class TestUninstallOnLinuxWithoutRoot:
    """The CLI never runs sudo itself. Without root,
    uninstall prints the sudo command and exits 253 before it reads,
    asks or changes anything."""

    @pytest.mark.parametrize('is_tty', [True, False])
    def test_refuses_before_anything(self, tmp_path, linux_install, is_tty):
        runner = UninstallRunner()
        link = home_with_link(tmp_path / 'home')
        with mock.patch.object(
            install_linux.LinuxInstall, 'is_installed'
        ) as is_installed:
            with pytest.raises(ConfigurationError) as e:
                uninstall(
                    tmp_path,
                    ['--yes'],
                    is_root=False,
                    runner=runner,
                    is_tty=is_tty,
                    environ={'HOME': str(tmp_path / 'home')},
                )
        assert str(e.value) == (
            'Uninstalling aws-credential-daemon\'s system service requires '
            'root, so nothing was changed. Run:\n'
            '  sudo aws configure credential-daemon uninstall'
        )
        is_installed.assert_not_called()
        assert runner.commands == []
        assert linux_install.credential_daemon.exists()
        assert os.path.islink(link)


class TestNoSystemOption:
    # --system existed only for the sudo re-run.
    @pytest.mark.parametrize('subcommand', ['install', 'uninstall'])
    def test_system_is_not_an_option(self, subcommand, capsys):
        from awscli.testutils import create_clidriver

        rc = create_clidriver().main(
            ['configure', 'credential-daemon', subcommand, '--system']
        )
        assert rc == 252
        assert 'Unknown options: --system' in capsys.readouterr().err


class TestNoVerifySsl:
    def test_install_refuses_it_before_anything_runs(self):
        # Not ignored silently: TLS is always checked.
        http = FakeHttp({})
        runner = mock.Mock()
        command = InstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system='linux',
                machine='x86_64',
                is_root=True,
                http_session=http,
                run=runner,
            ),
        )
        # A usage error (252), like uninstall without --yes or a terminal.
        with pytest.raises(ParamValidationError) as e:
            command._run_main(Namespace(), Namespace(verify_ssl=False))
        assert str(e.value) == (
            'install always checks TLS, so --no-verify-ssl isn\'t supported. '
            'Pass --ca-bundle for a proxy\'s CA. Nothing was downloaded.'
        )
        assert http.urls == []
        runner.assert_not_called()
