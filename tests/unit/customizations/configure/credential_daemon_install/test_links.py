# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
import socket

import pytest

from awscli.customizations.configure.credential_daemon_install import (
    commands,
    links,
)
from tests import mock
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    REMOVED,
    UninstallRunner,
    home_with_link,
    linux_runner,
    macos_install,
    uninstall,
    user,
    write,
)
from tests.utils.credential_daemon.skips import skip_if_root

pytestmark = skip_if_windows


class TestUninstallRemovesTheLink:
    """Uninstall removes the ~/.aws/credential-daemon.sock links it can show
    point to aws-credential-daemon's socket, and says so."""

    def test_roots_own_link(self, tmp_path, linux_install, capsys):
        # As root without sudo, root's link: root owns /root/.aws. Here
        # the test's own uid stands in for root's.
        link = home_with_link(tmp_path / 'roothome')
        check = links.link_problem
        own = lambda path, target, uid, **kw: check(  # noqa: E731
            path, target, os.geteuid(), **kw
        )
        with (
            mock.patch.object(links, 'link_problem', own),
            mock.patch.object(commands, 'link_problem', own),
        ):
            rc, _ = uninstall(
                tmp_path, ['--yes'], runner=linux_runner(linux_install)
            )
        assert rc == 0
        assert not os.path.lexists(link)
        assert capsys.readouterr().out == (
            f'{REMOVED}Nothing else in ~/.aws was changed.\n'
            f'Removed {link}.\n'
        )

    def test_under_sudo_roots_own_link_left_gets_no_command(
        self, tmp_path, linux_install, capsys
    ):
        # link refuses to run under sudo, so nothing is suggested for
        # root's own link.
        link = home_with_link(tmp_path / 'roothome', mode=0o775)
        check = links.link_problem
        own = lambda path, target, uid, **kw: check(  # noqa: E731
            path, target, os.geteuid(), **kw
        )
        with (
            mock.patch.object(links, 'link_problem', own),
            mock.patch.object(commands, 'link_problem', own),
        ):
            rc, _ = uninstall(
                tmp_path,
                ['--yes'],
                runner=linux_runner(linux_install),
                environ={'SUDO_USER': 'alice'},
                user_entry=mock.Mock(side_effect=KeyError('alice')),
            )
        assert rc == 0
        out = capsys.readouterr().out
        assert (
            f'Left {link}: another user can change its folder, so it '
            "wasn't removed as root.\n"
        ) in out
        # Nothing on any line about root's link; the user's own link gets
        # its own "without sudo" line.
        roots = [line for line in out.splitlines() if str(link) in line]
        assert roots and not any('aws configure' in line for line in roots)

    def test_roots_own_link_in_a_folder_others_can_change_is_left(
        self, tmp_path, linux_install, capsys
    ):
        # Root unlinks its own link in its own process, so its folder
        # must be root's alone.
        link = home_with_link(tmp_path / 'roothome', mode=0o775)
        check = links.link_problem
        own = lambda path, target, uid, **kw: check(  # noqa: E731
            path, target, os.geteuid(), **kw
        )
        with (
            mock.patch.object(links, 'link_problem', own),
            mock.patch.object(commands, 'link_problem', own),
        ):
            rc, _ = uninstall(
                tmp_path, ['--yes'], runner=linux_runner(linux_install)
            )
        assert rc == 0
        assert os.path.lexists(link)
        assert capsys.readouterr().out == (
            f'{REMOVED}Nothing in ~/.aws was changed.\n'
            # Root itself (no sudo) can run link --remove.
            f'Left {link}: another user can change its folder, so it '
            "wasn't removed as root. To remove it, run: aws configure "
            'credential-daemon link --remove\n'
        )

    def test_sudo_users_link_is_removed_as_that_user(
        self, tmp_path, linux_install, capsys
    ):
        home = tmp_path / 'alice'
        link = home_with_link(home)
        unlink_as = mock.Mock(
            side_effect=lambda path, uid, gid: os.unlink(path)
        )
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=unlink_as,
        )
        assert rc == 0
        unlink_as.assert_called_once_with(
            str(link), os.geteuid(), os.getegid()
        )
        assert not os.path.lexists(link)
        assert capsys.readouterr().out.endswith(
            f'Nothing else in ~/.aws was changed.\nRemoved {link}.\n'
        )

    def test_not_installed_still_removes_the_link(self, tmp_path, capsys):
        # It was removed by its own uninstaller or by hand, and the
        # link was left pointing at nothing.
        home = tmp_path / 'alice'
        link = home_with_link(home)
        unlink_as = mock.Mock(
            side_effect=lambda path, uid, gid: os.unlink(path)
        )
        runner = UninstallRunner()
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=runner,
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=unlink_as,
        )
        assert rc == 0
        assert runner.commands == []
        assert not os.path.lexists(link)
        assert capsys.readouterr().out == (
            f'aws-credential-daemon isn\'t installed.\nRemoved {link}.\n'
        )

    def test_files_left_still_remove_the_link(
        self, tmp_path, linux_install, capsys
    ):
        home = tmp_path / 'alice'
        link = home_with_link(home)
        unlink_as = mock.Mock(
            side_effect=lambda path, uid, gid: os.unlink(path)
        )
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=UninstallRunner(removes=[linux_install.credential_daemon]),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=unlink_as,
        )
        assert rc == 1
        assert not os.path.lexists(link)
        captured = capsys.readouterr()
        assert 'Remove them by hand.' in captured.err
        assert captured.out == f'Removed {link}.\n'

    @pytest.mark.parametrize('setup', ['aws is a link', 'aws group can write'])
    def test_a_sudo_users_link_in_any_aws_folder_is_removed(
        self, tmp_path, linux_install, capsys, setup
    ):
        # ~/.aws gets no checks of its own: the unlink runs as the user,
        # so root removes only what the user could.
        home = tmp_path / 'alice'
        if setup == 'aws is a link':
            # A dotfiles folder, as stow or chezmoi make.
            real = tmp_path / 'dotfiles'
            home_with_link(real)
            home.mkdir()
            (home / '.aws').symlink_to(real / '.aws')
            link = home / '.aws' / 'credential-daemon.sock'
        else:
            link = home_with_link(home, mode=0o775)
        unlink_as = mock.Mock(
            side_effect=lambda path, uid, gid: os.unlink(path)
        )
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=unlink_as,
        )
        assert rc == 0
        unlink_as.assert_called_once()
        assert not os.path.lexists(link)
        assert capsys.readouterr().out == (
            f'{REMOVED}Nothing else in ~/.aws was changed.\n'
            f'Removed {link}.\n'
        )

    @pytest.mark.parametrize(
        'setup',
        [
            'entry is a regular file',
            'entry is a socket',
            'entry is not theirs',
        ],
    )
    def test_a_sudo_users_link_that_isnt_plainly_theirs_is_left(
        self, tmp_path, linux_install, capsys, setup
    ):
        # Root never follows the link: anything odd, and the user removes
        # it without sudo.
        home = tmp_path / 'alice'
        if setup == 'entry is not theirs':
            link = home_with_link(home)
        elif setup == 'entry is a regular file':
            (home / '.aws').mkdir(parents=True, mode=0o700)
            link = home / '.aws' / 'credential-daemon.sock'
            link.write_text('')
        else:
            # A daemon listening there itself: not a link to remove.
            (home / '.aws').mkdir(parents=True, mode=0o700)
            link = home / '.aws' / 'credential-daemon.sock'
            cwd = os.getcwd()
            os.chdir(link.parent)
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.bind(link.name)
                sock.close()
            finally:
                os.chdir(cwd)
        entry = user(home)
        if setup == 'entry is not theirs':
            # Another uid than the link's owner.
            entry.return_value.pw_uid = os.geteuid() + 1
        unlink_as = mock.Mock()
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'alice'},
            user_entry=entry,
            unlink_as=unlink_as,
        )
        assert rc == 0
        unlink_as.assert_not_called()
        assert os.path.lexists(link)
        if setup in ('entry is a regular file', 'entry is a socket'):
            # Not a link, so link --remove would refuse it too.
            line = (
                f'Left {link}: it isn\'t a link to aws-credential-daemon\'s '
                'socket.\n'
            )
        else:
            line = (
                'To remove your link, run without sudo: '
                'aws configure credential-daemon link --remove\n'
            )
        assert capsys.readouterr().out == (
            f'{REMOVED}Nothing in ~/.aws was changed.\n' + line
        )

    def test_a_link_to_another_daemon_is_left(
        self, tmp_path, linux_install, capsys
    ):
        home = tmp_path / 'alice'
        link = home_with_link(home, target='/run/other/daemon.sock')
        unlink_as = mock.Mock()
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=unlink_as,
        )
        assert rc == 0
        unlink_as.assert_not_called()
        assert os.path.islink(link)
        assert capsys.readouterr().out.endswith(
            f'Left {link}: it doesn\'t point to aws-credential-daemon\'s '
            'socket.\n'
        )

    def test_no_link_changes_nothing_in_aws(
        self, tmp_path, linux_install, capsys
    ):
        unlink_as = mock.Mock()
        uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(tmp_path / 'alice'),
            unlink_as=unlink_as,
        )
        unlink_as.assert_not_called()
        assert capsys.readouterr().out == (
            f'{REMOVED}Nothing in ~/.aws was changed.\n'
        )

    def test_unknown_sudo_user_gets_the_command(
        self, tmp_path, linux_install, capsys
    ):
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=linux_runner(linux_install),
            environ={'SUDO_USER': 'ghost'},
            user_entry=mock.Mock(side_effect=KeyError('ghost')),
        )
        assert rc == 0
        assert capsys.readouterr().out.endswith(
            'To remove your link, run without sudo: '
            'aws configure credential-daemon link --remove\n'
        )

    def test_a_failed_uninstall_leaves_the_link(self, tmp_path, capsys):
        # Files are left, so the service may still be there: so is the
        # link.
        home = tmp_path / 'alice'
        link = home_with_link(home)
        root = tmp_path / 'root'
        write(root / 'usr/local/libexec/credsd/credsd')
        write(root / 'etc/systemd/system/credsd.service', 'x')
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            runner=UninstallRunner(),
            environ={'SUDO_USER': 'alice'},
            user_entry=user(home),
            unlink_as=mock.Mock(),
        )
        assert rc == 1
        assert os.path.islink(link)

    def test_macos_removes_the_users_link(self, tmp_path, capsys):
        home = tmp_path / 'home'
        bundle = macos_install(home, home / '.local/bin')
        target = str(home / 'Library/Application Support/credsd/credsd.sock')
        link = home_with_link(home, target=target)
        runner = UninstallRunner()
        rc, _ = uninstall(
            tmp_path, ['--yes'], system='darwin', runner=runner, home=str(home)
        )
        assert rc == 0
        assert runner.commands == [
            [str(bundle.credential_daemon), 'uninstall', '--user']
        ]
        # The socket file stays on macOS; the link goes.
        assert not os.path.lexists(link)
        assert f'Removed {link}.\n' in capsys.readouterr().out

    def test_macos_follows_a_linked_aws_folder(self, tmp_path, capsys):
        # A dotfiles ~/.aws: the user's own link, removed as link --remove
        # removes it.
        home = tmp_path / 'home'
        macos_install(home, home / '.local/bin')
        target = str(home / 'Library/Application Support/credsd/credsd.sock')
        link = home_with_link(tmp_path / 'dotfiles', target=target)
        (home / '.aws').symlink_to(link.parent)
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            system='darwin',
            runner=UninstallRunner(),
            home=str(home),
        )
        assert rc == 0
        assert not os.path.lexists(link)

    @skip_if_root('Root checks the folder of its own link.')
    def test_macos_removes_a_link_in_a_group_writable_aws(
        self, tmp_path, capsys
    ):
        # As link --remove does: the caller's own link, in its own
        # process, whatever ~/.aws's mode (umask 002).
        home = tmp_path / 'home'
        macos_install(home, home / '.local/bin')
        target = str(home / 'Library/Application Support/credsd/credsd.sock')
        link = home_with_link(home, target=target, mode=0o775)
        rc, _ = uninstall(
            tmp_path,
            ['--yes'],
            system='darwin',
            runner=UninstallRunner(),
            home=str(home),
        )
        assert rc == 0
        assert not os.path.lexists(link)
        assert f'Removed {link}.\n' in capsys.readouterr().out


@skip_if_root('Root can drop its groups.')
def test_unlink_as_fails_closed_without_root(tmp_path):
    # Dropping groups needs root, so as a user the child exits non-zero
    # and nothing is removed.
    path = tmp_path / 'x'
    path.symlink_to('/nowhere')
    with pytest.raises(OSError):
        links.unlink_as_user(str(path), os.geteuid(), os.getegid())
    assert os.path.islink(path)
