# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from argparse import Namespace

from awscli.customizations.configure.credential_daemon_install import (
    commands,
)
from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
)
from awscli.customizations.configure.credentialdaemon import (
    InstallCredentialDaemonCommand,
    UninstallCredentialDaemonCommand,
)
from awscli.customizations.exceptions import ConfigurationError
from tests import mock

RELEASE_URL = 'https://github.com/aws/credential-daemon/releases/latest'


def tag_page(tag='v1.0.0'):
    return f'https://github.com/aws/credential-daemon/releases/tag/{tag}'


def download(tag='v1.0.0'):
    return f'https://github.com/aws/credential-daemon/releases/download/{tag}'


DOWNLOAD = download()

GLOBALS = Namespace()

# pkgutil --check-signature's output for the v0.1.0 release package,
# verbatim (EC2 Mac run, 11/13). It ends with a blank line, and some
# fingerprint lines end with a space.
GOOD_PKGUTIL = (
    'Package "t872.pkg":\n'
    '   Status: signed by a developer certificate issued by Apple for '
    'distribution\n'
    '   Notarization: trusted by the Apple notary service\n'
    '   Signed with a trusted timestamp on: 2026-11-10 21:18:29 +0000\n'
    '   Certificate Chain:\n'
    '    1. Developer ID Installer: AMZN Mobile LLC (94KV3E626L)\n'
    '       Expires: 2030-09-26 00:18:06 +0000\n'
    '       SHA256 Fingerprint:\n'
    '           5C 45 BE 63 FD 52 10 07 2D 66 56 77 5C A9 FF 25 91 6D 3F 01 '
    'F7 0E \n'
    '           9A 8A 05 F6 2D 62 B2 88 8D A9\n'
    '       ------------------------------------------------------------'
    '------------\n'
    '    2. Developer ID Certification Authority\n'
    '       Expires: 2031-09-17 00:00:00 +0000\n'
    '       SHA256 Fingerprint:\n'
    '           F1 6C D3 C5 4C 7F 83 CE A4 BF 1A 3E 6A 08 19 C8 AA A8 E4 A1 '
    '52 8F \n'
    '           D1 44 71 5F 35 06 43 D2 DF 3A\n'
    '       ------------------------------------------------------------'
    '------------\n'
    '    3. Apple Root CA\n'
    '       Expires: 2035-02-09 21:40:36 +0000\n'
    '       SHA256 Fingerprint:\n'
    '           B0 B1 73 0E CB C7 FF 45 05 14 2C 49 F1 29 5E 6E DA 6B CA ED '
    '7E 2C \n'
    '           68 C5 BE 91 B5 A1 10 01 F0 24\n'
    '\n'
)


# The leaf certificate's line in GOOD_PKGUTIL.
GOOD_PKGUTIL_LEAF = (
    '    1. Developer ID Installer: AMZN Mobile LLC (94KV3E626L)\n'
)

FINGERPRINT = '0123456789ABCDEF0123456789ABCDEF01234567'


def validsig(signer=FINGERPRINT, primary=FINGERPRINT):
    return (
        f'[GNUPG:] VALIDSIG {signer} 2026-10-01 1790000000 0 4 0 1 10 00 '
        f'{primary}\n'
    )


# gpg --import --status-fd's lines for the pinned key (gpg 2.4).
GOOD_IMPORT_STATUS = (
    '[GNUPG:] KEY_CONSIDERED 0123456789ABCDEF0123456789ABCDEF01234567 0\n'
    '[GNUPG:] IMPORTED 89ABCDEF01234567 credsd\n'
    f'[GNUPG:] IMPORT_OK 1 {FINGERPRINT}\n'
    '[GNUPG:] IMPORT_RES 1 0 1 0 0 0 0 0 0 0 0 0 0 0 0\n'
)


# credsd's installer's stderr on a good install from a temp folder: its
# staging warning, verbatim from credsd's install.rs (two lines, the second
# indented by nine spaces).
STAGING_WARNING = (
    'warning: /tmp/tmpab12cd34/release/credsd-linux-x64-tpm/credsd can be '
    "modified by a non-root user, and the service runs as 'credsd', so "
    'install staged a root-owned copy of it at '
    '/usr/local/libexec/credsd/credsd.\n'
    '         The service runs that copy: rebuilding or upgrading '
    '/tmp/tmpab12cd34/release/credsd-linux-x64-tpm/credsd does NOT update '
    'the service. Re-run `sudo credsd install` to stage a new build, '
    '`credsd status` to see which file the service runs, and `sudo credsd '
    'uninstall` to remove the copy.\n'
)


# credsd's warning without a tss group, verbatim from install.rs.
TSS_WARNING = (
    'warning: TPM backend selected but the `tss` group does not exist; '
    'install tpm2-tss and re-run `credsd install`\n'
)


# What the TPM build's `--version` prints without tpm2-tss (amazonlinux:2023).
NO_TSS_STDERR = (
    '/tmp/tmpab12cd34/release/credsd-linux-x64-tpm/credsd: error while '
    'loading shared libraries: libtss2-esys.so.0: cannot open shared object '
    'file: No such file or directory\n'
)


GOOD_GPG_STATUS = (
    f'[GNUPG:] NEWSIG\n[GNUPG:] GOODSIG 89ABCDEF01234567 credsd\n'
    f'{validsig()}'
)


def package_info(identifier, version='1.0.0'):
    return f'<pkg-info identifier="{identifier}" version="{version}"/>'


def credential_daemon_package(version='1.0.0'):
    """What pkgutil --expand writes: {relative path: contents}."""
    return {
        'PackageInfo': package_info('com.amazon.aws.credsd.daemon', version)
    }


CREDENTIAL_DAEMON_PACKAGE = credential_daemon_package()


class RawBody:
    """A urllib3 response body: streamed in chunks, then closed."""

    def __init__(self, content, chunks=None):
        self._chunks = chunks
        self._content = content
        self.read = 0
        self.closed = False

    def stream(self, amt):
        if self._chunks is not None:
            chunks = self._chunks
        else:
            chunks = (
                self._content[i : i + amt]
                for i in range(0, len(self._content), amt)
            )
        for chunk in chunks:
            self.read += len(chunk)
            yield chunk

    def close(self):
        self.closed = True


class Response:
    def __init__(
        self, status_code=200, content=b'', headers=None, chunks=None
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.raw = RawBody(content, chunks)


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []
        self.user_agents = []

    def send(self, request):
        self.urls.append(request.url)
        self.user_agents.append(request.headers.get('User-Agent'))
        response = self.responses[request.url]
        return response() if callable(response) else response


def release(tag='v1.0.0', status=302):
    """github.com's releases/latest: a redirect to the tag's page."""
    return Response(status, headers={'Location': tag_page(tag)})


def archive(*members):
    """A .tar.gz with the given (name, data) members, as bytes."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class Runner:
    def __init__(
        self,
        verify_rc=0,
        install_error=None,
        pkgutil=GOOD_PKGUTIL,
        pkgutil_rc=0,
        gpg_status=GOOD_GPG_STATUS,
        import_rc=0,
        import_status=GOOD_IMPORT_STATUS,
        installer_stderr=STAGING_WARNING,
        version_rc=0,
        version_stderr='',
        package=CREDENTIAL_DAEMON_PACKAGE,
        expand_rc=0,
        exec_start=None,
        disable_error=None,
        uninstall_error=None,
        unit_states=None,
        version='credsd 1.0.0\nstorage backends: tpm, file\n',
        service_properties=None,
    ):
        self.commands = []
        # What `credsd --version` prints: credsd's own format.
        self._version = version
        # What `systemctl show -p Exec*,DropInPaths,FragmentPath
        # credsd.service` prints, or None for an output the install can't
        # read, so it checks the unit file's text.
        self._service_properties = service_properties
        # For each `credsd uninstall`, whether its program still existed.
        self.uninstaller_existed = []
        self._disable_error = disable_error
        self._uninstall_error = uninstall_error
        # systemctl output per verb, overriding the fake's model of
        # systemd 252 (see _systemctl). An Exception is raised instead.
        self._unit_states = unit_states or {}
        # Units `systemctl disable --now` stopped and disabled.
        self.disabled = set()
        # Where credsd install writes credsd.service (set by install()),
        # and the program its ExecStart runs (the staged copy by default).
        self.root = None
        self.exec_start = exec_start
        self._verify_rc = verify_rc
        self._install_error = install_error
        self._pkgutil = pkgutil
        self._pkgutil_rc = pkgutil_rc
        self._gpg_status = gpg_status
        self._import_rc = import_rc
        self._import_status = import_status
        # What credsd install prints on success: its staging warning, as
        # every install from a temp folder does.
        self._installer_stderr = installer_stderr
        self._version_rc = version_rc
        self._version_stderr = version_stderr
        self._package = package
        self._expand_rc = expand_rc

    def __call__(self, command, check=True, timeout=None):
        self.commands.append(command)
        if command[1:] == ['--version']:
            if self._version_rc:
                return subprocess.CompletedProcess(
                    command, self._version_rc, '', self._version_stderr
                )
            return subprocess.CompletedProcess(command, 0, self._version, '')
        if '--import' in command:
            return subprocess.CompletedProcess(
                command,
                self._import_rc,
                self._import_status,
                'no valid OpenPGP data',
            )
        if '--verify' in command:
            return subprocess.CompletedProcess(
                command, self._verify_rc, self._gpg_status, 'BAD signature'
            )
        if command[:2] == ['/usr/sbin/pkgutil', '--expand']:
            return self._expand(command)
        if command[0] == '/usr/sbin/pkgutil':
            return subprocess.CompletedProcess(
                command, self._pkgutil_rc, self._pkgutil, ''
            )
        if self._install_error and command[-1] in ('install', '/', 'x'):
            raise subprocess.CalledProcessError(
                1, command, stderr=self._install_error
            )
        if command[1:] == ['install'] and self.root is not None:
            self._write_service(command[0])
            return subprocess.CompletedProcess(
                command, 0, '', self._installer_stderr
            )
        if os.path.basename(command[0]) == 'systemctl':
            return self._systemctl(command)
        if command[1:] == ['uninstall']:
            return self._uninstall(command)
        return subprocess.CompletedProcess(command, 0, '', '')

    def _systemctl(self, command):
        """Like systemd 252 (AL2023), from the unit files on disk.

        A unit whose file exists is loaded, and enabled and active until
        `disable --now`. For a missing unit, show prints LoadState=not-found,
        an empty UnitFileState and ActiveState=inactive.
        """
        verb = command[1]
        if verb == 'disable' and self._disable_error:
            raise subprocess.CalledProcessError(
                1, command, stderr=self._disable_error
            )
        if verb == 'show' and 'FragmentPath' in ' '.join(command):
            out = self._service_properties
            if callable(out):
                out = out(self.root)
            return subprocess.CompletedProcess(
                command, 0 if out is not None else 1, out or '', ''
            )
        if verb in self._unit_states:
            out = self._unit_states[verb]
            if isinstance(out, Exception):
                raise out
            return subprocess.CompletedProcess(command, 0, out, '')
        names = [arg for arg in command[2:] if arg.startswith('credsd.')]
        if verb == 'disable':
            self.disabled.update(names)
            return subprocess.CompletedProcess(command, 0, '', '')
        states = [self._unit_state(name) for name in names]
        if verb == 'show':
            blocks = []
            for state in states:
                load, (enabled, active) = 'loaded', state or ('', 'inactive')
                if state is None:
                    load = 'not-found'
                blocks.append(
                    f'LoadState={load}\nActiveState={active}\n'
                    f'UnitFileState={enabled}\n'
                )
            return subprocess.CompletedProcess(
                command, 0, '\n'.join(blocks), ''
            )
        return subprocess.CompletedProcess(command, 0, '', '')

    def _unit_state(self, name):
        """(UnitFileState, ActiveState) of a unit, or None if missing."""
        unit = os.path.join(self.root, 'etc/systemd/system', name)
        if not os.path.exists(unit):
            return None
        if name in self.disabled:
            return ('disabled', 'inactive')
        return ('enabled', 'active')

    def _uninstall(self, command):
        self.uninstaller_existed.append(os.path.exists(command[0]))
        if self._uninstall_error:
            raise subprocess.CalledProcessError(
                1, command, stderr=self._uninstall_error
            )
        for name in ('credsd.socket', 'credsd.service'):
            unit = os.path.join(self.root, 'etc/systemd/system', name)
            if os.path.exists(unit):
                os.remove(unit)
        return subprocess.CompletedProcess(command, 0, '', '')

    def _write_service(self, credential_daemon):
        program = self.exec_start or STAGED
        if program == 'self':
            program = credential_daemon
        unit = os.path.join(self.root, 'etc/systemd/system/credsd.service')
        os.makedirs(os.path.dirname(unit), exist_ok=True)
        with open(unit, 'w') as f:
            f.write(f'[Service]\nExecStart="{program}" "serve" "--system"\n')
        socket = os.path.join(os.path.dirname(unit), 'credsd.socket')
        with open(socket, 'w') as f:
            f.write('[Socket]\nListenStream=/run/credsd/credsd.sock\n')

    def _expand(self, command):
        if self._expand_rc == 0:
            for path, contents in self._package.items():
                full = os.path.join(command[3], path)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, 'w', encoding='utf-8') as f:
                    f.write(contents)
        return subprocess.CompletedProcess(
            command, self._expand_rc, '', 'Error'
        )


def health_reply(version='1.0.0', protocol=1):
    """credsd's system/health result."""
    return {'protocol': protocol, 'version': version}


def installed_daemon(runner, system):
    """A system/health stand-in: the daemon just installed answers, with
    its version: on Linux what its `--version` gives, on macOS the
    package's."""
    version = '1.0.0'
    if system == 'darwin':
        found = re.search(
            r'version="([^"]*)"', ''.join(runner._package.values())
        )
        version = found.group(1) if found else version
    else:
        first = (runner._version or '').strip().splitlines()[:1]
        version = first[0].split()[-1] if first else version
    return mock.Mock(return_value=health_reply(version))


def install(
    system='linux',
    machine=None,
    is_root=None,
    http=None,
    runner=None,
    temp_root=None,
    link=None,
    health=None,
    environ=None,
    **host_options,
):
    """Run install. The link step goes to ``link``, a Mock standing in for
    _create_home_link, so these tests see only the install itself; the
    TestLink* classes cover the link. ``health`` stands in for the
    system/health wait; by default the installed daemon answers."""
    runner = runner or Runner()
    if machine is None:
        # A machine each platform has a release for.
        machine = 'arm64' if system == 'darwin' else 'x86_64'
    if is_root is None:
        # Each platform's supported way: root on Linux, the user on macOS.
        is_root = system == 'linux'
    if link is None:
        link = mock.Mock(return_value='/home/u/.aws/credential-daemon.sock')
    if health is None:
        health = installed_daemon(runner, system)
    with tempfile.TemporaryDirectory() as root:
        if runner.root is None:
            runner.root = root
        command = InstallCredentialDaemonCommand(
            mock.Mock(),
            InstallHost(
                system=system,
                machine=machine,
                is_root=is_root,
                http_session=http or FakeHttp({}),
                run=runner,
                root=runner.root,
                # 'auto': pick from /tmp and /var/tmp, as a real run does.
                temp_root=None if temp_root == 'auto' else temp_root or root,
                environ={'HOME': '/home/u'} if environ is None else environ,
                root_home='/root',
                own_socket=os.path.join(root, 'credsd.sock'),
                socket_wait=0,
                health=health,
                **host_options,
            ),
        )
        with mock.patch.object(commands, 'create_home_link', link):
            return command._run_main(Namespace(), GLOBALS)


def install_cli(**kwargs):
    """Run install as the CLI does: a ConfigurationError is printed to
    stderr and exits 253."""
    try:
        return install(**kwargs)
    except ConfigurationError as e:
        sys.stderr.write(f'{e}\n')
        return 253


# A release's files the install downloads, named as in v0.2.0: one TPM
# build per architecture with its detached signature, and the macOS package.
LINUX_ASSETS = (
    'credsd-linux-x64-tpm.tar.gz',
    'credsd-linux-x64-tpm.tar.gz.sig',
    'credsd-linux-aarch64-tpm.tar.gz',
    'credsd-linux-aarch64-tpm.tar.gz.sig',
)


MACOS_ASSET = 'credsd-macos-aarch64.pkg'


def linux_http(name='credsd-linux-x64-tpm.tar.gz', data=None, tag='v1.0.0'):
    if data is None:
        # Each archive unpacks into a folder named after itself.
        folder = name[: -len('.tar.gz')]
        data = archive((f'{folder}/credsd', b'#!/bin/sh\n'))
    return FakeHttp(
        {
            RELEASE_URL: release(tag),
            f'{download(tag)}/{name}': Response(content=data),
            f'{download(tag)}/{name}.sig': Response(content=b'signature'),
        }
    )


def macos_http(tag='v1.0.0'):
    return FakeHttp(
        {
            RELEASE_URL: release(tag),
            f'{download(tag)}/{MACOS_ASSET}': Response(content=b'pkg'),
        }
    )


class UninstallRunner:
    """Runs aws-credential-daemon's uninstaller by removing the given paths.

    systemctl succeeds unless systemctl_error names its subcommand. With
    error_if, only the commands it returns true for fail.
    """

    def __init__(
        self,
        removes=(),
        error=None,
        systemctl_error=None,
        error_if=None,
    ):
        self.commands = []
        self._removes = removes
        self._error = error
        self._error_if = error_if or (lambda command: True)
        self.systemctl_error = systemctl_error or {}

    def __call__(self, command, check=True, timeout=None):
        self.commands.append(command)
        if os.path.basename(command[0]) == 'systemctl':
            if command[1] in self.systemctl_error:
                raise subprocess.CalledProcessError(
                    1, command, stderr=self.systemctl_error[command[1]]
                )
            return subprocess.CompletedProcess(command, 0, '', '')
        if self._error is not None and self._error_if(command):
            raise subprocess.CalledProcessError(1, command, stderr=self._error)
        for path in self._removes:
            # Each call removes what's still there.
            if os.path.lexists(path):
                os.remove(path)
        return subprocess.CompletedProcess(command, 0, '', '')


def uninstall(
    tmp_path,
    args=(),
    system='linux',
    is_root=None,
    runner=None,
    is_tty=False,
    answer=True,
    home=None,
    trusted_gids=None,
    **link_options,
):
    if is_root is None:
        # Each platform's supported way: root on Linux, the user on macOS.
        is_root = system == 'linux'
    link_options.setdefault('environ', {})
    link_options.setdefault('root_home', str(tmp_path / 'roothome'))
    command = UninstallCredentialDaemonCommand(
        mock.Mock(),
        InstallHost(
            system=system,
            is_root=is_root,
            run=runner or UninstallRunner(),
            root=str(tmp_path / 'root'),
            home=home or str(tmp_path / 'home'),
            trusted_uid=os.getuid(),
            is_tty=lambda: is_tty,
            trusted_gids=trusted_gids,
            **link_options,
        ),
        ask=mock.Mock(return_value=answer),
    )
    parsed = Namespace(yes='--yes' in args)
    return command._run_main(parsed, GLOBALS), command


def write(path, text=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


STAGED = '/usr/local/libexec/credsd/credsd'


LAUNCH_AGENT = 'Library/LaunchAgents/com.amazon.aws.credsd.daemon.plist'


def macos_install(base, bin_dir, launch_agent=True):
    """A per-user install under ``base``: the bundle, its links and, with
    ``launch_agent``, the LaunchAgent that says it's installed."""
    bundle = base / 'Applications/Credsd.app'
    credential_daemon = write(bundle / 'Contents/MacOS/credsd')
    if launch_agent:
        write(base / LAUNCH_AGENT, '<plist/>')
    write(bundle / 'Contents/Resources/creds')
    (bin_dir).mkdir(parents=True, exist_ok=True)
    for name, target in (
        ('credsd', credential_daemon),
        ('creds', bundle / 'Contents/Resources/creds'),
    ):
        (bin_dir / name).symlink_to(target)
    # A link of the same kind that points elsewhere isn't the install's.
    write(base / 'elsewhere/aws')
    (bin_dir / 'aws').symlink_to(base / 'elsewhere/aws')
    return Namespace(
        bundle=bundle,
        credential_daemon=credential_daemon,
        bin=bin_dir,
        launch_agent=base / LAUNCH_AGENT,
    )


OWN_SOCKET = '/run/credsd/credsd.sock'

REMOVED = (
    'Removed aws-credential-daemon. The credential daemon\'s saved sign-ins '
    'and keys stay on this machine, so reinstalling brings them back. '
)


def home_with_link(home, target=OWN_SOCKET, mode=0o700):
    aws = home / '.aws'
    aws.mkdir(parents=True)
    aws.chmod(mode)
    link = aws / 'credential-daemon.sock'
    link.symlink_to(target)
    return link


def user(home):
    return mock.Mock(
        return_value=Namespace(
            pw_dir=str(home), pw_uid=os.geteuid(), pw_gid=os.getegid()
        )
    )


def linux_runner(linux_install):
    return UninstallRunner(
        removes=[linux_install.credential_daemon, *linux_install.units]
    )
