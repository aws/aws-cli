# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""``~/.aws/credential-daemon.sock``: how ``aws configure credential-daemon
install`` links it as the user, and ``aws configure credential-daemon link``."""

import os
import socket
import stat
from argparse import Namespace

import pytest
from botocore.exceptions import CredentialDaemonError

from awscli.compat import is_windows
from awscli.customizations.configure.credential_daemon_install import (
    commands,
    links,
)
from awscli.customizations.configure.credential_daemon_install import (
    host as install_host,
)
from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
)
from awscli.customizations.configure.credential_daemon_install.links import (
    _create_users_link,
    create_home_link,
    link_as_user,
    remove_home_link,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    ReleaseSource,
)
from awscli.customizations.configure.credentialdaemon import (
    InstallCredentialDaemonCommand,
    LinkCredentialDaemonCommand,
)
from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.exceptions import (
    ConfigurationError,
)
from tests import mock

pytestmark = pytest.mark.skipif(
    is_windows, reason='The link is for Linux and macOS.'
)

GLOBALS = Namespace(debug=False)

# The release the install stand-in installs, and the system/health reply of
# its daemon.
RELEASE_VERSION = (1, 0, 0)
HEALTHY = {'protocol': 1, 'version': '1.0.0'}
NEXT_STEPS = 'Your next sign-in will ask whether to store its session here.\n'


def install(
    system='linux',
    is_root=False,
    environ=None,
    link=None,
    installed=0,
    socket_wait=0,
    health=None,
    **kwargs,
):
    if system == 'linux':
        # A machine the Linux release is built for.
        kwargs.setdefault('machine', 'x86_64')
    link = link or mock.Mock(
        side_effect=lambda target, environ, **kwargs: (
            f'{environ["HOME"]}/.aws/credential-daemon.sock'
        )
    )
    command = InstallCredentialDaemonCommand(
        mock.Mock(),
        InstallHost(
            system=system,
            is_root=is_root,
            environ={'HOME': '/home/alice'} if environ is None else environ,
            is_tty=lambda: True,
            root_home='/root',
            socket_wait=socket_wait,
            health=health or mock.Mock(return_value=HEALTHY),
            **kwargs,
        ),
    )
    with (
        mock.patch.object(
            InstallCredentialDaemonCommand,
            '_install_system',
            return_value=(installed, mock.Mock(), RELEASE_VERSION),
        ) as system_step,
        mock.patch.object(commands, 'create_home_link', link),
    ):
        rc = command._run_main(Namespace(), GLOBALS)
    return rc, link, system_step


class TestInstallOnLinuxWithoutRoot:
    """The CLI never runs sudo itself. Without root, install
    prints the sudo command and exits 253 before anything else."""

    def test_refuses_before_anything_runs(self):
        with pytest.raises(ConfigurationError) as e:
            install(is_root=False)
        assert str(e.value) == (
            'Installing aws-credential-daemon as a system service requires '
            'root, so nothing was downloaded or changed. Run:\n'
            '  sudo aws configure credential-daemon install'
        )


def alice(home='/home/alice'):
    return Namespace(pw_name='alice', pw_uid=1000, pw_gid=1000, pw_dir=home)


class TestInstallAsRootOnLinux:
    def test_under_sudo_links_roots_and_the_users_as_the_user(self, capsys):
        link_as = mock.Mock(
            return_value=('/home/alice/.aws/credential-daemon.sock', None)
        )
        user_entry = mock.Mock(return_value=alice())
        health = mock.Mock(return_value=HEALTHY)
        rc, link, system_step = install(
            is_root=True,
            environ={'HOME': '/home/alice', 'SUDO_USER': 'alice'},
            user_entry=user_entry,
            link_as=link_as,
            health=health,
        )
        assert rc == 0
        system_step.assert_called_once_with(GLOBALS)
        # The service answered before anything was linked.
        health.assert_called_once_with('/run/credsd/credsd.sock', timeout=1)
        # Root's home from the passwd entry, not sudo's HOME.
        # Install prints the remedy itself, so the link's error has none.
        link.assert_called_once_with(
            '/run/credsd/credsd.sock',
            {'HOME': '/root', 'SUDO_USER': 'alice'},
            remedy=None,
        )
        # The user's from their passwd entry, made as them.
        user_entry.assert_called_once_with('alice')
        link_as.assert_called_once_with(alice(), '/run/credsd/credsd.sock')
        assert capsys.readouterr().out == (
            'Linked /root/.aws/credential-daemon.sock to '
            '/run/credsd/credsd.sock.\n'
            'Linked /home/alice/.aws/credential-daemon.sock to '
            '/run/credsd/credsd.sock.\n' + NEXT_STEPS
        )

    def test_a_replaced_link_is_named(self, capsys):
        link_as = mock.Mock(
            return_value=(
                '/home/alice/.aws/credential-daemon.sock',
                'it pointed to /other/daemon.sock',
            )
        )
        install(
            is_root=True,
            environ={'SUDO_USER': 'alice'},
            user_entry=mock.Mock(return_value=alice()),
            link_as=link_as,
        )
        assert (
            'Replaced /home/alice/.aws/credential-daemon.sock (it pointed to '
            '/other/daemon.sock).\n'
        ) in capsys.readouterr().out

    def test_a_users_link_that_cant_be_made_exits_1(self, capsys):
        # As on macOS, the link the caller needs failing exits 1, with
        # the command that finishes it.
        link_as = mock.Mock(
            side_effect=ConfigurationError(
                '/home/alice/.aws/credential-daemon.sock is there and isn\'t '
                'a link or a socket, so it was left.'
            )
        )
        rc, _, _ = install(
            is_root=True,
            environ={'SUDO_USER': 'alice'},
            user_entry=mock.Mock(return_value=alice()),
            link_as=link_as,
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert captured.err == (
            '/home/alice/.aws/credential-daemon.sock wasn\'t created: '
            '/home/alice/.aws/credential-daemon.sock is there and isn\'t a '
            'link or a socket, so it was left.\n'
            'Once that\'s fixed, run, without sudo: aws configure '
            'credential-daemon link\n'
        )
        assert NEXT_STEPS not in captured.out

    @pytest.mark.parametrize(
        'entry, why',
        [
            (KeyError('alice'), 'No passwd entry for alice'),
            (alice(home=''), 'the home folder isn\'t an absolute path'),
            (alice(home='home/alice'), 'the home folder isn\'t an absolute'),
        ],
        ids=['unknown-user', 'no-home', 'relative-home'],
    )
    def test_no_usable_passwd_entry_exits_1(self, entry, why, capsys):
        link_as = mock.Mock()
        user_entry = mock.Mock(
            side_effect=entry if isinstance(entry, KeyError) else None,
            return_value=entry,
        )
        rc, _, _ = install(
            is_root=True,
            environ={'SUDO_USER': 'alice'},
            user_entry=user_entry,
            link_as=link_as,
        )
        assert rc == 1
        link_as.assert_not_called()
        err = capsys.readouterr().err
        assert why in err
        assert err.endswith(
            'Once that\'s fixed, run, without sudo: aws configure '
            'credential-daemon link\n'
        )

    @pytest.mark.parametrize('environ', [{}, {'SUDO_USER': 'root'}])
    def test_no_sudo_user_links_no_one_else(self, environ, capsys):
        link_as = mock.Mock()
        rc, _, _ = install(is_root=True, environ=environ, link_as=link_as)
        assert rc == 0
        link_as.assert_not_called()
        out = capsys.readouterr().out
        assert (
            'Each user who uses the credential daemon runs, without sudo: '
            'aws configure credential-daemon link\n'
        ) in out

    def test_as_root_itself_tells_each_user_to_link(self, capsys):
        rc, _, _ = install(is_root=True, environ={'HOME': '/root'})
        assert rc == 0
        out = capsys.readouterr().out
        assert out == (
            'Linked /root/.aws/credential-daemon.sock to '
            '/run/credsd/credsd.sock.\n'
            'Each user who uses the credential daemon runs, without sudo: '
            'aws configure credential-daemon link\n' + NEXT_STEPS
        )

    def test_as_root_itself_a_failed_link_exits_1(self, capsys):
        # Root's own link is the one root asked for, so, as on macOS, it
        # failing exits 1 with the command that finishes it.
        link = mock.Mock(side_effect=OSError(13, 'Permission denied'))
        rc, _, _ = install(is_root=True, environ={}, link=link)
        assert rc == 1
        err = capsys.readouterr().err
        assert err == (
            '/root/.aws/credential-daemon.sock wasn\'t created: [Errno 13] '
            'Permission denied.\n'
            'Once that\'s fixed, run: aws configure credential-daemon link\n'
        )

    def test_under_sudo_roots_link_failing_is_only_a_note(self, capsys):
        link = mock.Mock(side_effect=OSError(13, 'Permission denied'))
        rc, _, _ = install(
            is_root=True,
            environ={'SUDO_USER': 'alice'},
            link=link,
            user_entry=mock.Mock(return_value=alice()),
            link_as=mock.Mock(return_value=('/home/alice/x', None)),
        )
        assert rc == 0
        err = capsys.readouterr().err
        assert '/root/.aws/credential-daemon.sock wasn\'t created' in err
        # link refuses under sudo, so it isn't suggested.
        assert 'Once that' not in err

    def test_a_failed_system_step_stops(self):
        health = mock.Mock(return_value=HEALTHY)
        rc, link, _ = install(is_root=True, installed=1, health=health)
        assert rc == 1
        health.assert_not_called()
        link.assert_not_called()

    def test_the_socket_override_is_noted(self, capsys):
        # Discovery won't use the link then.
        install(
            is_root=True,
            environ={'AWS_CREDENTIAL_DAEMON_SOCKET': '/tmp/other.sock'},
        )
        assert capsys.readouterr().err == (
            'Note: AWS_CREDENTIAL_DAEMON_SOCKET is set, so the AWS CLI uses '
            'that socket, not this link.\n'
        )

    def test_under_sudo_the_socket_override_isnt_noted(self, capsys):
        # sudo resets the environment, so the variable seen here isn't the
        # caller's.
        install(
            is_root=True,
            environ={
                'AWS_CREDENTIAL_DAEMON_SOCKET': '/tmp/other.sock',
                'SUDO_USER': 'alice',
            },
            user_entry=mock.Mock(return_value=alice()),
            link_as=mock.Mock(
                return_value=('/home/alice/.aws/credential-daemon.sock', None)
            ),
        )
        assert 'AWS_CREDENTIAL_DAEMON_SOCKET' not in capsys.readouterr().err

    def test_under_sudo_a_failure_of_roots_link_suggests_no_command(
        self, capsys
    ):
        # link refuses under sudo, so no command is printed for root's.
        link = mock.Mock(
            side_effect=ConfigurationError(
                '/root/.aws/credential-daemon.sock is there and isn\'t a link '
                'or a socket, so it was left. Remove it first.'
            )
        )
        rc, _, _ = install(
            is_root=True,
            environ={'SUDO_USER': 'alice'},
            link=link,
            user_entry=mock.Mock(return_value=alice()),
            link_as=mock.Mock(
                return_value=('/home/alice/.aws/credential-daemon.sock', None)
            ),
        )
        assert rc == 0
        err = capsys.readouterr().err
        assert err == (
            '/root/.aws/credential-daemon.sock wasn\'t created: '
            '/root/.aws/credential-daemon.sock is there and isn\'t a link or '
            'a socket, so it was left. Remove it first.\n'
        )


class FakeClock:
    """time.monotonic for the wait: each sleep moves it on."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def not_running():
    from botocore.exceptions import CredentialDaemonNotRunningError

    return CredentialDaemonNotRunningError(error_msg='refused.')


class TestWaitForTheDaemon:
    """Install waits for the
    daemon to answer system/health, and fails if it doesn't."""

    def test_links_once_it_answers(self, tmp_path, capsys):
        # The LaunchAgent answers on the third try.
        health = mock.Mock(side_effect=[not_running(), not_running(), HEALTHY])
        clock = FakeClock()
        rc, link, _ = install(
            system='darwin',
            own_socket=str(tmp_path / 'credsd.sock'),
            socket_wait=30,
            sleep=clock.sleep,
            clock=clock,
            health=health,
        )
        assert rc == 0
        assert clock.sleeps == [0.5, 0.5]
        assert health.call_count == 3
        link.assert_called_once_with(
            str(tmp_path / 'credsd.sock'), {'HOME': '/home/alice'}, remedy=None
        )
        assert capsys.readouterr().out.endswith(NEXT_STEPS)

    @pytest.mark.parametrize(
        'error',
        [
            'CredentialDaemonNotRunningError',
            'CredentialDaemonTimeoutError',
            'CredentialDaemonConnectionError',
            'CredentialDaemonProtocolError',
        ],
    )
    def test_a_service_that_never_answers_fails_253(self, error, tmp_path):
        import botocore.exceptions

        # Such as credsd.service crash-looping on a missing tss group.
        health = mock.Mock(
            side_effect=getattr(botocore.exceptions, error)(error_msg='x.')
        )
        clock = FakeClock()
        with pytest.raises(ConfigurationError) as e:
            install(
                is_root=True,
                environ={},
                own_socket='/run/credsd/credsd.sock',
                socket_wait=30,
                sleep=clock.sleep,
                clock=clock,
                health=health,
            )
        assert clock.now >= 30
        # credsd.service's unit is written at install, so the remedy is to
        # fix the cause and install again, which links too.
        assert str(e.value) == (
            'aws-credential-daemon was installed but isn\'t running: '
            '/run/credsd/credsd.sock didn\'t answer as aws-credential-daemon '
            '1.0.0 within 30 seconds (last error: x.).\n'
            'Fix what journalctl -u credsd or sudo tail '
            '/var/log/credsd/credsd.log shows, then run again:\n'
            '  sudo aws configure credential-daemon install'
        )

    def test_the_wait_shows_whole_seconds(self):
        # Each try's call timeout is what's left of the wait, which the
        # tries themselves use up, and the client's error repeats it. A
        # fraction such as 2.474012944032438 would show in the message.
        from botocore.exceptions import CredentialDaemonTimeoutError

        clock = FakeClock()
        timeouts = []

        def health(target, timeout):
            timeouts.append(timeout)
            clock.now += 0.026
            raise CredentialDaemonTimeoutError(
                error_msg=f'no answer within the {timeout}-second call '
                'timeout.'
            )

        with pytest.raises(ConfigurationError) as e:
            install(
                is_root=True,
                environ={},
                own_socket='/run/credsd/credsd.sock',
                socket_wait=3,
                sleep=clock.sleep,
                clock=clock,
                health=health,
            )
        assert all(isinstance(timeout, int) for timeout in timeouts)
        assert timeouts[0] == 3
        assert timeouts[-1] == 1
        assert (
            'within 3 seconds (last error: no answer within the 1-second '
            'call timeout.).'
        ) in str(e.value)

    @pytest.mark.parametrize(
        'reply, message',
        [
            # The old daemon, still running after an upgrade.
            (
                {'protocol': 1, 'version': '0.9.0'},
                'aws-credential-daemon 1.0.0 was installed, but for 30 '
                'seconds /run/credsd/credsd.sock answered as '
                'aws-credential-daemon 0.9.0 (protocol 1).\n'
                'Restart it with: sudo systemctl restart credsd.service\n'
                'Then run again:\n'
                '  sudo aws configure credential-daemon install',
            ),
            (
                {'protocol': 2, 'version': '1.0.0'},
                'aws-credential-daemon 1.0.0 was installed, but for 30 '
                'seconds /run/credsd/credsd.sock answered as '
                'aws-credential-daemon 1.0.0 (protocol 2).\n'
                'This AWS CLI supports only protocol 1. Update the AWS CLI, '
                'then run: aws configure credential-daemon link',
            ),
            (
                {'protocol': 1},
                'aws-credential-daemon 1.0.0 was installed, but for 30 '
                'seconds /run/credsd/credsd.sock answered as an unknown '
                'version of aws-credential-daemon (protocol 1).\n'
                'Restart it with: sudo systemctl restart credsd.service\n'
                'Then run again:\n'
                '  sudo aws configure credential-daemon install',
            ),
            (
                None,
                'aws-credential-daemon 1.0.0 was installed, but for 30 '
                'seconds /run/credsd/credsd.sock answered as something that '
                'isn\'t a system/health reply.\n'
                'Restart it with: sudo systemctl restart credsd.service\n'
                'Then run again:\n'
                '  sudo aws configure credential-daemon install',
            ),
        ],
    )
    def test_only_the_release_just_installed_counts(self, reply, message):
        health = mock.Mock(return_value=reply)
        clock = FakeClock()
        with pytest.raises(ConfigurationError) as e:
            install(
                is_root=True,
                environ={},
                own_socket='/run/credsd/credsd.sock',
                socket_wait=30,
                sleep=clock.sleep,
                clock=clock,
                health=health,
            )
        # It kept waiting, and nothing was linked.
        assert health.call_count > 1
        assert str(e.value) == message

    def test_the_new_version_answering_later_links(self, tmp_path):
        health = mock.Mock(
            side_effect=[{'protocol': 1, 'version': '0.9.0'}, HEALTHY]
        )
        clock = FakeClock()
        rc, link, _ = install(
            system='darwin',
            own_socket=str(tmp_path / 'credsd.sock'),
            socket_wait=30,
            sleep=clock.sleep,
            clock=clock,
            health=health,
        )
        assert rc == 0
        assert health.call_count == 2
        link.assert_called_once()

    def test_a_missing_launch_agent_gives_credsds_remedy(self, tmp_path):
        # The package's postinstall logs this and exits 0.
        launch_agent = mock.Mock()
        launch_agent.is_installed.return_value = False
        command_rc = None
        with pytest.raises(ConfigurationError) as e:
            with mock.patch.object(
                InstallCredentialDaemonCommand,
                '_install_system',
                return_value=(0, launch_agent, RELEASE_VERSION),
            ):
                command = InstallCredentialDaemonCommand(
                    mock.Mock(),
                    InstallHost(
                        system='darwin',
                        is_root=False,
                        environ={'HOME': '/Users/alice'},
                        own_socket=str(tmp_path / 'credsd.sock'),
                        socket_wait=0,
                        health=mock.Mock(side_effect=not_running()),
                    ),
                )
                command_rc = command._run_main(Namespace(), GLOBALS)
        assert command_rc is None
        # Printed without quotes, so it runs as printed.
        assert str(e.value).endswith(
            'Its LaunchAgent wasn\'t registered. In a terminal, run: '
            '~/.local/bin/credsd install --user\n'
            'Then run: aws configure credential-daemon link'
        )

    def test_a_registered_launch_agent_that_doesnt_answer(self, tmp_path):
        launch_agent = mock.Mock()
        launch_agent.is_installed.return_value = True
        with pytest.raises(ConfigurationError) as e:
            with mock.patch.object(
                InstallCredentialDaemonCommand,
                '_install_system',
                return_value=(0, launch_agent, RELEASE_VERSION),
            ):
                InstallCredentialDaemonCommand(
                    mock.Mock(),
                    InstallHost(
                        system='darwin',
                        is_root=False,
                        environ={'HOME': '/Users/alice'},
                        own_socket=str(tmp_path / 'credsd.sock'),
                        socket_wait=0,
                        health=mock.Mock(side_effect=not_running()),
                    ),
                )._run_main(Namespace(), GLOBALS)
        assert (
            f'For details, run: launchctl print gui/{os.getuid()}/'
            'com.amazon.aws.credsd.daemon\n'
        ) in str(e.value)

    def test_another_error_stops_the_wait_and_the_link_reports_it(self):
        # Such as a socket that fails its checks.
        from botocore.exceptions import CredentialDaemonError

        health = mock.Mock(side_effect=CredentialDaemonError(error_msg='no.'))
        clock = FakeClock()
        rc, link, _ = install(
            system='darwin',
            socket_wait=30,
            sleep=clock.sleep,
            clock=clock,
            health=health,
        )
        assert rc == 0
        assert clock.sleeps == []
        link.assert_called_once()

    def test_an_untrusted_socket_stops_the_wait(self):
        # It's a connection error, but waiting won't fix it; the link's
        # check reports it.
        from botocore.exceptions import CredentialDaemonUntrustedSocketError

        health = mock.Mock(
            side_effect=CredentialDaemonUntrustedSocketError(error_msg='no.')
        )
        clock = FakeClock()
        rc, link, _ = install(
            system='darwin',
            socket_wait=30,
            sleep=clock.sleep,
            clock=clock,
            health=health,
        )
        assert rc == 0
        assert clock.sleeps == []
        link.assert_called_once()

    def test_links_the_per_user_socket(self):
        _, link, _ = install(system='darwin')
        assert link.call_args[0][0] == (
            '/home/alice/Library/Application Support/credsd/credsd.sock'
        )

    def test_the_health_call_sends_system_health(self):
        # Not a bare connect: credsd logs a NoPeerCred WARN for a peer that
        # closes before sending.
        with mock.patch.object(
            install_host.CredentialDaemonClient, '_call'
        ) as call:
            install_host.check_daemon_health('/run/credsd/credsd.sock', 5)
        call.assert_called_once_with('system/health')

    def test_the_health_call_returns_the_reply(self):
        # What the wait reads: credsd's HealthResult.
        reply = {'protocol': 1, 'version': '0.2.0'}
        with mock.patch.object(
            install_host.CredentialDaemonClient, '_call', return_value=reply
        ):
            assert (
                install_host.check_daemon_health('/run/credsd/credsd.sock', 5)
                == reply
            )

    def test_install_links_through_the_real_health_call(self, tmp_path):
        # The real check_daemon_health, with only the daemon's answer faked:
        # no health stand-in hides what the seam returns.
        with mock.patch.object(
            install_host.CredentialDaemonClient,
            '_call',
            return_value={'protocol': 1, 'version': '1.0.0'},
        ):
            rc, link, _ = install(
                system='darwin',
                own_socket=str(tmp_path / 'credsd.sock'),
                health=install_host.check_daemon_health,
            )
        assert rc == 0
        link.assert_called_once()


class TestInstallOnMacOS:
    def test_install_under_sudo_is_refused_with_253(self):
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', is_root=True)
        assert str(e.value) == (
            'On macOS aws-credential-daemon installs for one user. Run this '
            'without sudo: aws configure credential-daemon install'
        )

    def test_a_link_that_cant_be_made_exits_1(self, capsys):
        link = mock.Mock(side_effect=OSError(13, 'Permission denied'))
        rc, _, _ = install(system='darwin', link=link)
        assert rc == 1
        assert capsys.readouterr().err.endswith(
            'Once that\'s fixed, run: aws configure credential-daemon link\n'
        )


class _StopAtInstall(Exception):
    pass


class TestReinstall:
    def run(self, tmp_path):
        command = InstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system='linux',
                machine='x86_64',
                is_root=True,
                root=str(tmp_path),
                temp_root=str(tmp_path),
            ),
        )
        with (
            # before_download's gpg check looks only in /usr/bin and /bin,
            # and macOS runners have no gpg there.
            mock.patch.object(commands.LinuxInstall, 'before_download'),
            mock.patch.object(
                ReleaseSource,
                'latest_release',
                return_value=mock.Mock(version=(1, 0, 0)),
            ),
            mock.patch.object(commands.LinuxInstall, 'installed_version'),
            mock.patch.object(commands, 'check_release_version'),
            mock.patch.object(
                commands.LinuxInstall,
                'install',
                side_effect=_StopAtInstall,
            ),
        ):
            # Not ConfigurationError, so a refusal before the note fails the
            # test instead of passing as the stop.
            with pytest.raises(_StopAtInstall):
                command._install_system(GLOBALS)

    def test_says_it_reinstalls(self, tmp_path, capsys):
        # sudo aws ... install over an installed aws-credential-daemon.
        staged = tmp_path / 'usr/local/libexec/credsd/credsd'
        staged.parent.mkdir(parents=True)
        staged.write_text('')
        self.run(tmp_path)
        assert capsys.readouterr().out.startswith(
            'aws-credential-daemon is already installed, so this reinstalls '
            'it.\n'
        )

    def test_says_nothing_on_a_first_install(self, tmp_path, capsys):
        self.run(tmp_path)
        assert 'reinstalls' not in capsys.readouterr().out


@pytest.fixture
def short_dir(sock_dir):
    # sock_dir, closed to other users and resolved, as the socket checks
    # want it.
    os.chmod(sock_dir, 0o700)
    return sock_dir.resolve()


@pytest.fixture
def home(short_dir):
    home = short_dir / 'home'
    home.mkdir()
    return home


@pytest.fixture
def target(short_dir):
    folder = short_dir / 'daemon'
    folder.mkdir(mode=0o700)
    path = folder / 'd.sock'
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(4)
    with server:
        yield str(path)


def link_path(home):
    return home / '.aws' / 'credential-daemon.sock'


class TestCreateHomeLink:
    @pytest.mark.parametrize('umask', [0o000, 0o002, 0o022, 0o077])
    def test_a_new_aws_folder_follows_the_umask(self, home, target, umask):
        # As aws configure creates it.
        old = os.umask(umask)
        try:
            create_home_link(target, {'HOME': str(home)})
        finally:
            os.umask(old)
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o777 & ~umask
        assert os.readlink(link_path(home)) == target

    def test_returns_the_link_and_checks_the_target_first(self, home, target):
        with mock.patch.object(
            links,
            'probe_socket',
            wraps=links.probe_socket,
        ) as probe:
            link = create_home_link(target, {'HOME': str(home)})
        assert link == str(link_path(home))
        probe.assert_called_once_with(target)

    @pytest.mark.parametrize('existing', ['link', 'socket'])
    def test_replaces_a_link_or_a_socket(self, home, target, existing):
        (home / '.aws').mkdir(mode=0o700)
        if existing == 'link':
            link_path(home).symlink_to('/old/target.sock')
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(str(link_path(home)))
            sock.close()
        create_home_link(target, {'HOME': str(home)})
        assert os.readlink(link_path(home)) == target
        # No temporary names left.
        assert os.listdir(home / '.aws') == ['credential-daemon.sock']

    @pytest.mark.parametrize('existing', ['file', 'folder'])
    def test_refuses_anything_else(self, home, target, existing):
        (home / '.aws').mkdir(mode=0o700)
        if existing == 'file':
            link_path(home).write_text('keep')
        else:
            link_path(home).mkdir()
        with pytest.raises(ConfigurationError) as e:
            create_home_link(target, {'HOME': str(home)})
        assert 'isn\'t a link or a socket, so it was left' in str(e.value)
        assert not os.path.islink(link_path(home))

    def test_a_target_that_fails_its_checks_isnt_linked(self, home, tmp_path):
        from botocore.exceptions import CredentialDaemonNotRunningError

        (home / '.aws').mkdir(mode=0o700)
        link_path(home).symlink_to('/old/target.sock')
        with pytest.raises(CredentialDaemonNotRunningError):
            create_home_link(
                str(tmp_path / 'missing.sock'), {'HOME': str(home)}
            )
        # The old link is untouched.
        assert os.readlink(link_path(home)) == '/old/target.sock'

    def test_a_failed_rename_leaves_no_temporary_link(self, home, target):
        with mock.patch.object(os, 'replace', side_effect=OSError(28, 'full')):
            with pytest.raises(OSError):
                create_home_link(target, {'HOME': str(home)})
        assert os.listdir(home / '.aws') == []

    def test_a_link_that_fails_its_own_check_is_removed(self, home, target):
        from botocore.exceptions import CredentialDaemonNotRunningError

        error = CredentialDaemonNotRunningError(error_msg='no.')
        with mock.patch.object(links, 'check_home_socket', side_effect=error):
            with pytest.raises(CredentialDaemonNotRunningError):
                create_home_link(target, {'HOME': str(home)})
        assert not os.path.lexists(link_path(home))

    def test_without_the_check_a_missing_target_is_linked(
        self, home, tmp_path
    ):
        missing = str(tmp_path / 'later.sock')
        with mock.patch.object(links, 'probe_socket') as probe:
            create_home_link(missing, {'HOME': str(home)}, check_target=False)
        probe.assert_not_called()
        assert os.readlink(link_path(home)) == missing

    def test_the_link_is_made_0600_where_links_have_a_mode(self, home, target):
        lchmod = mock.Mock()
        with mock.patch.object(os, 'lchmod', lchmod, create=True):
            create_home_link(target, {'HOME': str(home)})
        (path, mode), _ = lchmod.call_args
        assert mode == 0o600
        assert os.path.basename(path).startswith('.credential-daemon.sock.')

    @pytest.mark.parametrize('environ', [{}, {'HOME': ''}, {'HOME': 'rel'}])
    def test_home_must_be_absolute(self, target, environ):
        with pytest.raises(
            ConfigurationError, match='HOME isn\'t an absolute'
        ):
            create_home_link(target, environ)


class TestCreateHomeLinkLeavesTheFolder:
    """~/.aws gets no special treatment: a missing one is created as
    ``aws configure`` creates it, with the umask, and an existing one is
    never changed or checked."""

    @pytest.mark.parametrize('mode', [0o775, 0o777, 0o1775, 0o755, 0o700])
    def test_an_existing_folder_is_left_as_it_is(
        self, home, target, mode, capsys
    ):
        (home / '.aws').mkdir()
        (home / '.aws').chmod(mode)
        create_home_link(target, {'HOME': str(home)})
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == mode
        assert os.readlink(link_path(home)) == target
        assert capsys.readouterr().out == ''

    def test_link_leaves_a_0775_aws_folder_unchanged(
        self, home, target, capsys
    ):
        # Ubuntu's private user groups: a umask of 002 leaves a new ~/.aws
        # 0775. Every client dials the link in it, before and after link.
        from botocore.credential_daemon import check_home_socket

        old = os.umask(0o002)
        try:
            (home / '.aws').mkdir()
            link_path(home).symlink_to(target)
        finally:
            os.umask(old)
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o775
        check_home_socket(str(link_path(home)))
        assert link(environ={'HOME': str(home)}, own_socket=target) == 0
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o775
        check_home_socket(str(link_path(home)))
        assert capsys.readouterr().out == (
            f'Linked {link_path(home)} to {target}.\n'
        )

    def test_through_a_link_to_the_folder(self, home, short_dir, target):
        real = short_dir / 'real-aws'
        real.mkdir()
        real.chmod(0o775)
        (home / '.aws').symlink_to(real)
        create_home_link(target, {'HOME': str(home)})
        assert stat.S_IMODE(os.stat(real).st_mode) == 0o775
        assert os.readlink(real / 'credential-daemon.sock') == target

    def test_even_without_the_target_check(self, home, tmp_path):
        (home / '.aws').mkdir()
        (home / '.aws').chmod(0o770)
        create_home_link(
            str(tmp_path / 'later.sock'),
            {'HOME': str(home)},
            check_target=False,
        )
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o770

    def test_aws_linked_to_a_missing_folder_isnt_created(
        self, home, short_dir, target
    ):
        # Such as a dotfile manager's link before its checkout.
        missing = short_dir / 'dotfiles' / 'aws'
        (home / '.aws').symlink_to(missing)
        with pytest.raises(ConfigurationError) as e:
            link(environ={'HOME': str(home)}, own_socket=target)
        assert str(e.value).startswith(f'{link_path(home)} wasn\'t linked: ')
        assert not os.path.lexists(missing.parent)

    def test_without_the_target_check_its_folders_are_still_checked(
        self, home, short_dir
    ):
        # The macOS install links before the daemon answers: a socket in
        # a folder other users can write is still refused.
        from botocore.exceptions import CredentialDaemonUntrustedSocketError

        loose = short_dir / 'open'
        loose.mkdir()
        loose.chmod(0o777)
        target = loose / 's.sock'
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(target))
        with server:
            with pytest.raises(CredentialDaemonUntrustedSocketError) as e:
                create_home_link(
                    str(target), {'HOME': str(home)}, check_target=False
                )
        assert f'the folder {loose} is writable by other users' in str(e.value)
        assert not os.path.lexists(link_path(home))

    def test_without_the_target_check_a_missing_target_folder_is_linked(
        self, home, short_dir
    ):
        # The macOS install, before the LaunchAgent has made its folder.
        target = str(short_dir / 'later' / 'd.sock')
        create_home_link(target, {'HOME': str(home)}, check_target=False)
        assert os.readlink(link_path(home)) == target

    def test_a_folder_someone_else_owns_isnt_checked_or_changed(
        self, home, target, capsys
    ):
        (home / '.aws').mkdir()
        (home / '.aws').chmod(0o775)
        with (
            mock.patch('os.geteuid', return_value=os.geteuid() + 4242),
            mock.patch.object(links, 'probe_socket') as probe,
        ):
            create_home_link(target, {'HOME': str(home)})
        probe.assert_called_once_with(target)
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o775
        assert os.readlink(link_path(home)) == target
        assert capsys.readouterr().out == ''

    def test_the_target_gets_the_peer_check(self, home, target):
        with mock.patch(
            'botocore.credential_daemon.transport.check_peer'
        ) as check_peer:
            create_home_link(target, {'HOME': str(home)})
        assert check_peer.called


class TestRemoveHomeLink:
    def test_removes_a_link(self, home):
        (home / '.aws').mkdir()
        link_path(home).symlink_to('/run/credsd/credsd.sock')
        assert remove_home_link({'HOME': str(home)}) == str(link_path(home))
        assert not os.path.lexists(link_path(home))

    def test_nothing_there(self, home):
        assert remove_home_link({'HOME': str(home)}) is None

    def test_refuses_what_isnt_a_link(self, home):
        (home / '.aws').mkdir()
        link_path(home).write_text('keep')
        with pytest.raises(ConfigurationError, match='isn\'t a link'):
            remove_home_link({'HOME': str(home)})
        assert link_path(home).read_text() == 'keep'


def link(args=(), system='linux', environ=None, is_root=False, **kwargs):
    command = LinkCredentialDaemonCommand(
        mock.Mock(),
        InstallHost(system=system, environ=environ, is_root=is_root, **kwargs),
    )
    return command._run_main(Namespace(remove='--remove' in args), GLOBALS)


class TestLinkCommand:
    def test_links_credsds_own_socket(self, home, target, capsys):
        assert link(environ={'HOME': str(home)}, own_socket=target) == 0
        assert os.readlink(link_path(home)) == target
        assert capsys.readouterr().out == (
            f'Linked {link_path(home)} to {target}.\n'
        )

    def test_a_replaced_link_is_named(self, home, target, capsys):
        # Say so when the old link pointed elsewhere.
        (home / '.aws').mkdir()
        link_path(home).symlink_to('/other/daemon.sock')
        assert link(environ={'HOME': str(home)}, own_socket=target) == 0
        assert capsys.readouterr().out == (
            f'Linked {link_path(home)} to {target}.\n'
            f'Replaced {link_path(home)} (it pointed to /other/daemon.sock).\n'
        )

    def test_relinking_the_same_target_says_nothing_more(
        self, home, target, capsys
    ):
        (home / '.aws').mkdir()
        link_path(home).symlink_to(target)
        link(environ={'HOME': str(home)}, own_socket=target)
        assert 'Replaced' not in capsys.readouterr().out

    def test_the_socket_override_is_noted(self, home, target, capsys):
        # Discovery uses the variable, not the link.
        environ = {
            'HOME': str(home),
            'AWS_CREDENTIAL_DAEMON_SOCKET': '/tmp/other.sock',
        }
        link(environ=environ, own_socket=target)
        assert capsys.readouterr().err.endswith(
            'Note: AWS_CREDENTIAL_DAEMON_SOCKET is set, so the AWS CLI uses '
            'that socket, not this link.\n'
        )

    def test_no_socket_says_to_install(self, home, tmp_path):
        missing = str(tmp_path / 'credsd.sock')
        with pytest.raises(ConfigurationError) as e:
            link(environ={'HOME': str(home)}, own_socket=missing)
        # Not "link its socket": that's this command, which just failed.
        assert str(e.value) == (
            f'No aws-credential-daemon socket is at {missing}, so nothing was '
            'linked. Start the credential daemon, or install it with \'aws '
            'configure credential-daemon install\', or set '
            'AWS_CREDENTIAL_DAEMON_SOCKET.'
        )
        assert 'credential-daemon link' not in str(e.value)
        assert not os.path.lexists(home / '.aws')

    def test_a_socket_that_fails_its_checks_is_reported(self, home, short_dir):
        # A socket file nothing listens on.
        stale = short_dir / 's.sock'
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(stale))
        sock.close()
        with pytest.raises(ConfigurationError) as e:
            link(environ={'HOME': str(home)}, own_socket=str(stale))
        assert str(e.value).startswith(
            f'{link_path(home)} wasn\'t linked: The credential daemon isn\'t '
            'running'
        )

    def test_remove(self, home, capsys):
        (home / '.aws').mkdir()
        link_path(home).symlink_to('/run/credsd/credsd.sock')
        assert link(['--remove'], environ={'HOME': str(home)}) == 0
        assert not os.path.lexists(link_path(home))
        assert capsys.readouterr().out == f'Removed {link_path(home)}.\n'

    def test_remove_with_nothing_there(self, home, capsys):
        assert link(['--remove'], environ={'HOME': str(home)}) == 0
        assert capsys.readouterr().out == (
            f'There\'s no {link_path(home)} to remove.\n'
        )

    @pytest.mark.parametrize('args', [(), ('--remove',)])
    def test_under_sudo_is_refused(self, home, args, capsys):
        # A refusal exits 253.
        environ = {'HOME': str(home), 'SUDO_USER': 'alice'}
        with pytest.raises(ConfigurationError) as e:
            link(args, environ=environ, is_root=True)
        assert str(e.value).startswith(
            'The link must be owned by you, not root, so nothing was '
            'changed. Run this without sudo: aws configure credential-daemon '
            'link'
        )
        assert not os.path.lexists(home / '.aws')

    def test_root_itself_links_its_own(self, home, target):
        assert (
            link(
                environ={'HOME': '/home/alice'},
                is_root=True,
                own_socket=target,
                root_home=str(home),
            )
            == 0
        )
        assert os.readlink(link_path(home)) == target

    def test_root_never_links_in_another_users_home(
        self, home, short_dir, target
    ):
        # After su without -, HOME is still the user's: root links in its
        # own home from the passwd entry, never there.
        alice = short_dir / 'alice'
        alice.mkdir()
        environ = {'HOME': str(alice)}
        assert (
            link(
                environ=environ,
                is_root=True,
                own_socket=target,
                root_home=str(home),
            )
            == 0
        )
        assert os.listdir(alice) == []
        assert os.readlink(link_path(home)) == target
        assert environ == {'HOME': str(alice)}

    def test_macos_links_the_per_user_socket(self, home):
        environ = {'HOME': str(home)}
        with pytest.raises(ConfigurationError) as e:
            link(system='darwin', environ=environ)
        assert f'{home}/Library/Application Support/credsd/credsd.sock' in str(
            e.value
        )

    def test_a_folder_it_cant_create_is_reported(self, short_dir, target):
        # HOME is a file, so ~/.aws can't be made.
        (short_dir / 'file').write_text('')
        environ = {'HOME': str(short_dir / 'file')}
        with pytest.raises(ConfigurationError) as e:
            link(environ=environ, own_socket=target)
        assert str(e.value).startswith(
            f'{short_dir}/file/.aws/credential-daemon.sock wasn\'t linked: '
        )

    def test_other_platforms(self):
        with pytest.raises(ConfigurationError, match='doesn\'t run'):
            link(system='win32', environ={})


class TestSudoInstallLinksTheUsersAsTheUser:
    """``sudo aws configure credential-daemon install`` on Linux, with the
    real links: root's in root's own ~/.aws, and the user's made as the
    user. Here the test's own uid stands in for the user's."""

    def run(self, short_dir, target, entry, rc=0):
        root_home = short_dir / 'root'
        root_home.mkdir()
        command = InstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system='linux',
                is_root=True,
                environ={'HOME': entry.pw_dir, 'SUDO_USER': 'alice'},
                root_home=str(root_home),
                own_socket=target,
                user_entry=mock.Mock(return_value=entry),
                health=mock.Mock(return_value=HEALTHY),
            ),
        )
        with mock.patch.object(
            InstallCredentialDaemonCommand,
            '_install_system',
            return_value=(0, mock.Mock(), RELEASE_VERSION),
        ):
            assert command._run_main(Namespace(), GLOBALS) == rc
        return root_home

    def test_links_both_and_the_users_is_theirs(
        self, short_dir, target, capsys
    ):
        home = short_dir / 'alice'
        home.mkdir()
        root_home = self.run(short_dir, target, me(home))
        assert os.readlink(link_path(root_home)) == target
        assert os.readlink(link_path(home)) == target
        assert os.lstat(link_path(home)).st_uid == os.getuid()
        out = capsys.readouterr().out
        assert f'Linked {link_path(home)} to {target}.\n' in out

    def test_a_link_to_something_else_is_replaced_and_named(
        self, short_dir, target, capsys
    ):
        # The same rule as link.
        home = short_dir / 'alice'
        (home / '.aws').mkdir(parents=True, mode=0o700)
        link_path(home).symlink_to('/elsewhere.sock')
        self.run(short_dir, target, me(home))
        assert os.readlink(link_path(home)) == target
        assert (
            f'Replaced {link_path(home)} (it pointed to /elsewhere.sock).\n'
        ) in capsys.readouterr().out

    def test_a_file_at_the_path_is_left_and_exits_1(
        self, short_dir, target, capsys
    ):
        home = short_dir / 'alice'
        (home / '.aws').mkdir(parents=True, mode=0o700)
        link_path(home).write_text('keep')
        self.run(short_dir, target, me(home), rc=1)
        assert link_path(home).read_text() == 'keep'
        err = capsys.readouterr().err
        assert 'isn\'t a link or a socket, so it was left' in err
        # The remedy, once.
        assert err.count('credential-daemon link') == 1
        assert err.endswith(
            'Once that\'s fixed, run, without sudo: aws configure '
            'credential-daemon link\n'
        )


def me(home):
    """A passwd entry for the test's own user, with ``home``."""
    return Namespace(
        pw_name='alice',
        pw_uid=os.getuid(),
        pw_gid=os.getgid(),
        pw_dir=str(home),
    )


class TestCreateUsersLink:
    """What the child that runs as the user does: link's own rule."""

    @pytest.mark.parametrize('umask', [0o000, 0o002, 0o022, 0o077])
    def test_a_missing_aws_folder_follows_the_umask(self, home, target, umask):
        # As aws configure creates it, and as link does.
        old = os.umask(umask)
        try:
            shown, previous = _create_users_link(str(home), target)
        finally:
            os.umask(old)
        assert shown == str(link_path(home))
        assert previous is None
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == 0o777 & ~umask
        assert os.readlink(link_path(home)) == target
        assert os.lstat(link_path(home)).st_uid == os.getuid()

    @pytest.mark.parametrize('mode', [0o775, 0o777, 0o700])
    def test_an_existing_folder_isnt_checked_or_changed(
        self, home, target, mode
    ):
        (home / '.aws').mkdir()
        (home / '.aws').chmod(mode)
        _create_users_link(str(home), target)
        assert stat.S_IMODE(os.stat(home / '.aws').st_mode) == mode
        assert os.readlink(link_path(home)) == target

    @pytest.mark.parametrize('existing', ['link', 'socket'])
    def test_a_link_or_a_socket_is_replaced(self, home, target, existing):
        (home / '.aws').mkdir(mode=0o700)
        if existing == 'link':
            link_path(home).symlink_to('/elsewhere.sock')
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(str(link_path(home)))
            sock.close()
        _, replaced = _create_users_link(str(home), target)
        assert replaced == (
            'it pointed to /elsewhere.sock'
            if existing == 'link'
            else 'it was a socket'
        )
        assert os.readlink(link_path(home)) == target

    @pytest.mark.parametrize('existing', ['file', 'folder'])
    def test_anything_else_is_left(self, home, target, existing):
        (home / '.aws').mkdir(mode=0o700)
        if existing == 'file':
            link_path(home).write_text('keep')
        else:
            link_path(home).mkdir()
        with pytest.raises(ConfigurationError, match='so it was left'):
            _create_users_link(str(home), target)
        assert not os.path.islink(link_path(home))

    def test_a_target_that_doesnt_answer_links_nothing(self, home, short_dir):
        with pytest.raises(CredentialDaemonError):
            _create_users_link(str(home), str(short_dir / 'missing.sock'))
        assert not os.path.lexists(link_path(home))


class TestLinkAs:
    """The child process: run as the test's own user, it needs no
    privilege to drop."""

    def test_links_in_a_child_as_the_user(self, home, target):
        assert link_as_user(me(home), target) == (str(link_path(home)), None)
        assert os.lstat(link_path(home)).st_uid == os.getuid()

    def test_a_replaced_target_comes_back(self, home, target):
        (home / '.aws').mkdir(mode=0o700)
        link_path(home).symlink_to('/elsewhere.sock')
        assert link_as_user(me(home), target) == (
            str(link_path(home)),
            'it pointed to /elsewhere.sock',
        )

    def test_a_refusal_comes_back_as_a_configuration_error(self, home, target):
        (home / '.aws').mkdir(mode=0o700)
        link_path(home).write_text('keep')
        with pytest.raises(ConfigurationError, match='so it was left'):
            link_as_user(me(home), target)
        assert link_path(home).read_text() == 'keep'

    def test_another_uid_fails_without_touching_the_home(self, home, target):
        if os.geteuid() == 0:
            pytest.skip('root can become another uid')
        entry = me(home)
        entry.pw_uid = os.getuid() + 1
        with pytest.raises(OSError):
            link_as_user(entry, target)
        assert os.listdir(home) == []


class TestInstallOrderAndOptions:
    def test_the_daemon_answers_before_anything_is_linked(self):
        calls = mock.Mock()
        calls.link.side_effect = lambda target, environ, **kwargs: '/root/x'
        calls.health.return_value = HEALTHY
        install(
            is_root=True,
            environ={},
            link=calls.link,
            health=calls.health,
        )
        assert [name for name, _, _ in calls.mock_calls] == ['health', 'link']

    @pytest.mark.parametrize(
        'verify, config, expected',
        [
            ('/etc/ca.pem', '/home/u/ca.pem', '/etc/ca.pem'),
            (None, '/home/u/ca.pem', '/home/u/ca.pem'),
            (None, None, None),
            # --no-verify-ssl: TLS is still checked.
            (False, '/home/u/ca.pem', '/home/u/ca.pem'),
            (False, None, None),
        ],
    )
    def test_the_ca_bundle_reaches_the_download(
        self, verify, config, expected
    ):
        session = mock.Mock()
        session.get_config_variable.return_value = config
        command = InstallCredentialDaemonCommand(
            session,
            InstallHost(system='linux', machine='x86_64', is_root=True),
        )
        with (
            mock.patch.object(commands, 'ReleaseSource') as source,
            mock.patch.object(commands.LinuxInstall, 'before_download'),
            mock.patch.object(commands.LinuxInstall, 'installed_version'),
            mock.patch.object(commands, 'check_release_version'),
            mock.patch.object(
                commands.LinuxInstall, 'reinstall_note', return_value=''
            ),
            mock.patch.object(
                commands.LinuxInstall, 'install', return_value=0
            ),
        ):
            command._install_system(Namespace(verify_ssl=verify))
        assert source.call_args.kwargs == {'verify': expected}


class TestPreviewNotice:
    def test_link_says_nothing(self, home, target, capsys):
        assert link(environ={'HOME': str(home)}, own_socket=target) == 0
        assert PREVIEW_NOTICE not in capsys.readouterr().err
