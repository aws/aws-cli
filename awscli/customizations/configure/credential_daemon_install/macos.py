# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Installing and uninstalling aws-credential-daemon's per-user package on
macOS."""

import os
import plistlib
import shlex
import tempfile
import xml.parsers.expat

from awscli.customizations.configure.credential_daemon_install.host import (
    MACOS_ARCHITECTURES,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    CREDENTIAL_DAEMON_PRODUCT,
    MACOS_ASSET,
    check_package_version,
    parse_version,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print

# Where aws-credential-daemon's installers put things (its docs/install.md),
# relative to the root of the file system or the user's home. Read from its
# source and checked against the v0.1.0 release:
# - macOS: the signed release .pkg installs only for one user, never as a
#   system service (that exists only for builds from source), and `credsd`
#   refuses `--user` under sudo. Installed with -target
#   CurrentUserHomeDirectory, it puts Credsd.app in ~/Applications, links
#   credsd and creds into ~/.local/bin and registers the user's LaunchAgent.
#   Its ProgramArguments[0] is the in-bundle path, never a link. `credsd
#   uninstall --user` removes only that agent. Nothing in
#   aws-credential-daemon removes the bundle, the links or the package
#   receipt. Uninstall matches that: it leaves them, and says how to remove
#   them.
# - macOS: the LaunchAgent's Label is com.amazon.aws.credsd.daemon, the package
#   ID, like its file name. With no agent plist, `credsd uninstall --user` has
#   nothing to remove and exits 0.
_MACOS_BUNDLE = 'Applications/Credsd.app'


_MACOS_BUNDLE_CREDENTIAL_DAEMON = 'Contents/MacOS/credsd'


_MACOS_BUNDLE_INFO = 'Contents/Info.plist'


# What `credsd uninstall --user` removes, so what says it's installed for
# this user: the bundle stays after an uninstall.
_MACOS_LAUNCH_AGENT = 'Library/LaunchAgents/com.amazon.aws.credsd.daemon.plist'


_MAX_INFO_BYTES = 1024 * 1024


_MACOS_USER_BIN = '.local/bin'


# The links the package adds to ~/.local/bin, into the bundle.
_MACOS_USER_LINKS = ('credsd', 'creds')


# aws-credential-daemon's per-user macOS install adds a PATH block, marked
# with this line, to one of these when ~/.local/bin isn't on PATH. Uninstall
# leaves it and says where it is.
_PATH_BLOCK_MARKER = '# Added by credsd'


_PATH_BLOCK_FILES = ('.zprofile', '.bash_profile')


_MAX_PROFILE_BYTES = 1024 * 1024


_INSTALLER = '/usr/sbin/installer'


# Downloads are saved under these names, not the release's asset names, so
# no text from the release reaches a path, pkgutil's output, installer or gpg.
_LOCAL_PACKAGE = 'aws-credential-daemon.pkg'


def _has_path_block(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return _PATH_BLOCK_MARKER in f.read(_MAX_PROFILE_BYTES)
    except OSError:
        return False


def _shell_home(shown):
    """A ~/ path quoted for the shell, with ~ left to expand."""
    if shown.startswith('~/'):
        return '~/' + shlex.quote(shown[2:])
    return shlex.quote(shown)


class MacOSInstall:
    """The current user's install: ~/Applications/Credsd.app, its links and
    its LaunchAgent.

    Like aws-credential-daemon's own uninstall --user, this removes only
    the LaunchAgent.
    The app, its links and the package receipt stay. Running it again runs
    aws-credential-daemon's uninstaller again, which has nothing left to do.
    """

    whose = ' for this user'

    def __init__(self, host):
        self.host = host
        self._bundle = host.home_path(_MACOS_BUNDLE)
        self._credential_daemon = os.path.join(
            self._bundle, _MACOS_BUNDLE_CREDENTIAL_DAEMON
        )

    def is_installed(self):
        return os.path.lexists(self.host.home_path(_MACOS_LAUNCH_AGENT))

    def installed_version(self):
        """The bundle's version from its Info.plist, or None. Only while
        it's installed: the app stays after an uninstall."""
        if not self.is_installed():
            return None
        try:
            with open(
                os.path.join(self._bundle, _MACOS_BUNDLE_INFO), 'rb'
            ) as f:
                info = plistlib.loads(f.read(_MAX_INFO_BYTES))
        except (
            OSError,
            ValueError,
            plistlib.InvalidFileException,
            # A truncated XML plist, which isn't a ValueError.
            xml.parsers.expat.ExpatError,
        ):
            return None
        version = (
            info.get('CFBundleShortVersionString')
            if isinstance(info, dict)
            else None
        )
        return parse_version(version) if isinstance(version, str) else None

    def check_uninstaller(self):
        if os.path.islink(self._bundle) or not os.path.isdir(self._bundle):
            raise ConfigurationError(
                f'{self._bundle} isn\'t '
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s app bundle, so '
                f'nothing was uninstalled.'
            )
        if not os.path.lexists(self._credential_daemon):
            raise ConfigurationError(
                f'{self._credential_daemon} is missing, so '
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s uninstaller '
                f'can\'t run. Nothing was uninstalled.'
            )

    def run_uninstaller(self):
        self.host.run_uninstaller(
            [self._credential_daemon, 'uninstall', '--user'], self._bundle
        )

    def notes(self):
        """What uninstall left: the app and its links, which
        aws-credential-daemon's own uninstall leaves too, and a per-user
        PATH block."""
        notes = []
        left = [
            path
            for path in [self._bundle]
            + [
                self.host.home_path(os.path.join(_MACOS_USER_BIN, name))
                for name in _MACOS_USER_LINKS
            ]
            if os.path.lexists(path)
        ]
        if left:
            shown = [self._shown_home(path) for path in left]
            quoted = ' '.join(_shell_home(path) for path in shown)
            notes.append(
                f'Left {", ".join(shown)}, as '
                f'{CREDENTIAL_DAEMON_PRODUCT}\'s own uninstall does. To '
                f'remove them: rm -r {quoted}\n'
            )
        for name in _PATH_BLOCK_FILES:
            if _has_path_block(self.host.home_path(name)):
                notes.append(
                    f'Left the lines marked "{_PATH_BLOCK_MARKER}" in '
                    f'~/{name}. Remove them if you no longer need '
                    f'~/{_MACOS_USER_BIN} on PATH.\n'
                )
        return notes

    def _shown_home(self, path):
        home = self.host.home_path('')
        if path.startswith(home):
            return '~/' + path[len(home) :]
        return path

    def before_download(self):
        if self.host.machine not in MACOS_ARCHITECTURES:
            # The .pkg's credsd is arm64 only, so it can't run here (Rosetta
            # runs x86_64 on Apple silicon, not the other way round).
            raise ConfigurationError(
                f'{CREDENTIAL_DAEMON_PRODUCT} has no macOS release for '
                f'{self.host.machine}. Its macOS release is for Apple silicon '
                'only.'
            )

    def reinstall_note(self):
        """What install says about an install that's already here."""
        if not self.is_installed():
            return ''
        return (
            f'{CREDENTIAL_DAEMON_PRODUCT} is already installed for this '
            'user, so this reinstalls it.\n'
        )

    def install(self, source, release):
        """Install the per-user package. Returns the exit code."""
        with tempfile.TemporaryDirectory() as tmp:
            self._install_macos(source, release, tmp)
        # Only what the installer's exit code backs up. aws-credential-daemon
        # doesn't report where it seals secrets, so don't name a keystore.
        uni_print(f'Installed {CREDENTIAL_DAEMON_PRODUCT} for this user.\n')
        return 0

    def _install_macos(self, source, release, tmp):
        package = os.path.join(tmp, _LOCAL_PACKAGE)
        source.download(release, MACOS_ASSET, package)
        source.verify_package_signature(package)
        components = source.verify_package_identifier(package, tmp)
        check_package_version(components, release.version)
        self.host.run_installer(
            [
                _INSTALLER,
                '-pkg',
                package,
                '-target',
                'CurrentUserHomeDirectory',
            ]
        )
