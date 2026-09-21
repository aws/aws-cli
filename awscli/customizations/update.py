# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile

from awscli.botocore.awsrequest import AWSRequest
from awscli.botocore.httpsession import URLLib3Session
from awscli.clidriver import (
    INSTALL_FILENAME,
    get_distribution_source,
)
from awscli.compat import is_windows
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print

_DOWNLOAD_BASE_URL = 'https://awscli.amazonaws.com'

_SUPPORTED_SOURCES = ('exe', 'script-exe', 'update-exe')

# AWS CLI public signing key, used to verify the detached signature of the
# downloaded Unix install script. This MUST stay in sync with AWS_CLI_PGP_KEY
# in scripts/install-v2/install.sh (a unit test asserts they match).
AWS_CLI_PGP_KEY = '''-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBF2Cr7UBEADJZHcgusOJl7ENSyumXh85z0TRV0xJorM2B/JL0kHOyigQluUG
ZMLhENaG0bYatdrKP+3H91lvK050pXwnO/R7fB/FSTouki4ciIx5OuLlnJZIxSzx
PqGl0mkxImLNbGWoi6Lto0LYxqHN2iQtzlwTVmq9733zd3XfcXrZ3+LblHAgEt5G
TfNxEKJ8soPLyWmwDH6HWCnjZ/aIQRBTIQ05uVeEoYxSh6wOai7ss/KveoSNBbYz
gbdzoqI2Y8cgH2nbfgp3DSasaLZEdCSsIsK1u05CinE7k2qZ7KgKAUIcT/cR/grk
C6VwsnDU0OUCideXcQ8WeHutqvgZH1JgKDbznoIzeQHJD238GEu+eKhRHcz8/jeG
94zkcgJOz3KbZGYMiTh277Fvj9zzvZsbMBCedV1BTg3TqgvdX4bdkhf5cH+7NtWO
lrFj6UwAsGukBTAOxC0l/dnSmZhJ7Z1KmEWilro/gOrjtOxqRQutlIqG22TaqoPG
fYVN+en3Zwbt97kcgZDwqbuykNt64oZWc4XKCa3mprEGC3IbJTBFqglXmZ7l9ywG
EEUJYOlb2XrSuPWml39beWdKM8kzr1OjnlOm6+lpTRCBfo0wa9F8YZRhHPAkwKkX
XDeOGpWRj4ohOx0d2GWkyV5xyN14p2tQOCdOODmz80yUTgRpPVQUtOEhXQARAQAB
tCFBV1MgQ0xJIFRlYW0gPGF3cy1jbGlAYW1hem9uLmNvbT6JAlQEEwEIAD4CGwMF
CwkIBwIGFQoJCAsCBBYCAwECHgECF4AWIQT7Xbd/1cEYuAURraimMQrMRnJHXAUC
akV0ygUJDqP4lQAKCRCmMQrMRnJHXFHjD/9eyZLYcKuQOlLvtqSDtUBiEZf6ZZjM
i3ygYH8rJNtuToUH+HvSpe819urJCquXhDrlK6N+aqW0hCLtNABJG/vsafIgvIYJ
hSGgpgtNnQyMV1jViRWqPjbouw8OkYKBThUfT1i2Y+wn58ifs6ODBCmTexWtXspA
Si+Gt49xDOW0APmbOPnI+a4HJW6tVEo6MWS0WjzpiBayR3d1A4pt4YrPfSdDgpLo
h2SLQqlRqvvVZJaWBjhkErNFpfsBA06sDcPEOb0G8LBUbR4WOcdvhe5LubJbZuxC
AG9kNPCVeQP1ixwjgjXKysaxeQ6rv0VzIQgRp6tLVLWhy6AKDNvLjFSsmXZ1Wl08
Y/RlOHXlzLuQMRE6sR1wOdRxc9TsrNWTGiBK65cvSWOy03JeBkQQ8pesqltiyxI9
U21kkgiXtTSKNGfKK8pO27D81YANhRqPK7iTp6kuFiY2WtOg90KTMNlIT+Ff85Y2
b1rHj6Z0SrCkJujhWk3IBPic/wJgz01LEc/OAdUPlby90RJZcIBhSlWhT7mXnXIO
c0HWlNQrns2s3CTyYwZSiSlYe9ApeLwhjDo8NhbFuCAy61l6O5UsR4AfZxx/rGKv
2wFb1/RN/P4gNe6vmxZAPjR0AQcwD3tc2McimOLr/22kmPz8IH3I0X7WoSFr0Biz
E91G7bb0hOb/cA==
=knv7
-----END PGP PUBLIC KEY BLOCK-----'''

# The Windows install script is Authenticode-signed by AWS Signer using a
# DigiCert-issued EV code-signing certificate. We verify the signer *identity*
# (organization + issuing CA) rather than a specific certificate thumbprint:
# the certificate is renewed (~yearly) and pinning its thumbprint would break
# `aws update` on every rotation, whereas the organization and issuing CA are
# stable across renewals. The organization must be one of AWS's approved
# code-signing org names.
_WINDOWS_SIGNER_ORGS = (
    'Amazon.com Services LLC',
    'Amazon Web Services, Inc.',
    'Amazon.com, Inc.',
)
_WINDOWS_SIGNER_ISSUER = 'DigiCert'


def download_with_retry(url, dest, retries=1, session=None):
    session = session or URLLib3Session()
    uni_print(f"Downloading {url}\n")
    request = AWSRequest(method='GET', url=url).prepare()
    for attempt in range(retries + 1):
        try:
            response = session.send(request)
            if response.status_code != 200:
                raise UpdateError(
                    f"unexpected HTTP status {response.status_code}"
                )
            with open(dest, 'wb') as out:
                out.write(response.content)
            return
        except Exception as exc:
            if attempt == retries:
                raise UpdateError(f"failed to download {url}: {exc}")
            uni_print(f"download failed ({exc}); retrying...\n", sys.stderr)


class BaseUpdateCommand(BasicCommand):
    NAME = 'update'
    DESCRIPTION = (
        'Update the AWS CLI to the latest version.\n\n'
        'Note that ``update`` is only supported if the '
        'current CLI instance was installed using an official '
        'installer, install script, or the ``update`` command. '
        'Other distribution mechanisms such as source or container '
        'images are not supported.'
    )
    SYNOPSIS = 'aws update'
    ARG_TABLE = [
        {
            'name': 'skip-signature-verification',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Skip signature verification of the downloaded install '
                'script. NOT RECOMMENDED: this disables a security control '
                'that confirms the install script is authentic before it is '
                'run. Only use it if you understand and accept the risk '
                '(for example, when gpg is unavailable on Linux and cannot '
                'be installed).'
            ),
        },
    ]

    _no_color = False
    _skip_verification = False

    def __init__(
        self, session, source=None, install_metadata=None, downloader=None
    ):
        super().__init__(session)
        self._source = get_distribution_source() if source is None else source
        self._install_metadata = (
            self._read_install_json()
            if install_metadata is None
            else install_metadata
        )
        self._download = downloader or download_with_retry

    def _read_install_json(self):
        import awscli

        path = os.path.join(
            os.path.dirname(os.path.abspath(awscli.__file__)),
            'data',
            INSTALL_FILENAME,
        )
        if not os.path.isfile(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _run_main(self, parsed_args, parsed_globals):
        source = self._source
        if source not in _SUPPORTED_SOURCES:
            raise UpdateError(
                f"Detected distribution source: {source}. "
                f"`aws update` is only supported on AWS CLI instances "
                f"installed using an official installer, install script, "
                f"or the `aws update` command."
            )
        uni_print(f"Updating AWS CLI (source: {source})\n")
        self._no_color = parsed_globals.color == 'off'
        self._skip_verification = parsed_args.skip_signature_verification
        self._do_update()
        return 0

    def _warn_skipping_verification(self):
        uni_print(
            "WARNING: skipping install script signature verification "
            "(--skip-signature-verification); the downloaded script will be "
            "run without confirming it is authentic.\n",
            sys.stderr,
        )

    def _do_update(self):
        raise NotImplementedError


class UnixUpdateCommand(BaseUpdateCommand):
    SCRIPT_URL = f'{_DOWNLOAD_BASE_URL}/v2/install.sh'
    SYSTEM_INSTALL_DIR = '/usr/local/aws-cli'

    def __init__(self, session, is_elevated=None, runner=None, **kwargs):
        super().__init__(session, **kwargs)
        self._is_elevated = is_elevated
        self._run_update = runner or self._run_install

    def _do_update(self):
        install_dir = self._install_metadata.get('install_dir')
        if not install_dir:
            raise UpdateError(
                'Install-time metadata could not be found. Reinstall '
                'using the install script or an official installer '
                'and try again.'
            )
        bin_dir = self._install_metadata.get('bin_dir')
        is_system = self._is_system_install(self._install_metadata)
        if is_system:
            self._assert_elevated()
        with tempfile.TemporaryDirectory() as tmp:
            script_path = os.path.join(tmp, 'install.sh')
            self._download(self.SCRIPT_URL, script_path)
            self._verify_script(script_path, tmp)
            env = os.environ.copy()
            env['AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE'] = 'update-exe'
            if self._no_color:
                env['NO_COLOR'] = '1'
            cmd = ['bash', script_path]
            if is_system:
                cmd.append('--system')
            else:
                env['XDG_DATA_HOME'] = os.path.dirname(install_dir)
                if bin_dir:
                    env['XDG_BIN_HOME'] = bin_dir
                else:
                    env['XDG_BIN_HOME'] = os.path.join(tmp, 'bin')
                    env['AWS_CLI_NO_BIN_DIR'] = '1'
            uni_print('Running install script...\n')
            try:
                self._run_update(cmd, env)
            except subprocess.CalledProcessError as exc:
                raise UpdateError(
                    f"install script failed with exit code {exc.returncode}"
                )

    def _run_install(self, cmd, env):
        subprocess.run(cmd, env=env, check=True)

    def _verify_script(self, script_path, tmp):
        # Verify the downloaded install script with a detached PGP signature
        # before executing it. `aws update` runs unattended, so a missing gpg
        # is a hard failure by default; the explicit --skip-signature-verification
        # opt-out is the only way to bypass it.
        if self._skip_verification:
            self._warn_skipping_verification()
            return
        gpg = shutil.which('gpg')
        if gpg is None:
            raise UpdateError(
                'gpg was not found, so the downloaded install script cannot '
                'be verified. Install gnupg and try again, or re-run with '
                '--skip-signature-verification to update without verification '
                '(not recommended).'
            )
        sig_path = script_path + '.sig'
        self._download(self.SCRIPT_URL + '.sig', sig_path)
        gpghome = os.path.join(tmp, 'gpghome')
        os.makedirs(gpghome, mode=0o700, exist_ok=True)
        keyfile = os.path.join(tmp, 'aws-cli.key')
        with open(keyfile, 'w') as f:
            f.write(AWS_CLI_PGP_KEY)
        gpg_opts = [gpg, '--homedir', gpghome, '--batch', '--no-autostart']
        # Import can exit non-zero on minimal systems even when it succeeds
        # (key-preference warnings, missing agent), so judge success by
        # --verify rather than the import's return code.
        subprocess.run(
            gpg_opts + ['--import', keyfile],
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            gpg_opts + ['--verify', sig_path, script_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise UpdateError(
                'install script signature verification failed:\n'
                f'{result.stderr.strip()}'
            )
        uni_print('Install script signature verified.\n')

    def _is_system_install(self, install_metadata):
        if 'script_install' in install_metadata:
            return install_metadata['script_install'].get('system', False)
        if not sys.executable:
            return False
        aws_bin = os.path.realpath(sys.executable)
        return aws_bin.startswith(self.SYSTEM_INSTALL_DIR + os.sep)

    def _assert_elevated(self):
        elevated = (
            os.geteuid() == 0
            if self._is_elevated is None
            else self._is_elevated
        )
        if not elevated:
            raise UpdateError(
                'Updating a system-wide AWS CLI installation requires root.'
            )


class WindowsUpdateCommand(BaseUpdateCommand):
    SCRIPT_URL = f'{_DOWNLOAD_BASE_URL}/v2/install.ps1'

    def __init__(
        self,
        session,
        is_elevated=None,
        runner=None,
        powershell_path=None,
        **kwargs,
    ):
        super().__init__(session, **kwargs)
        self._is_elevated = is_elevated
        self._run_update = runner or self._run_install
        self._powershell_path = powershell_path

    def _do_update(self):
        is_system = self._is_system_install(self._install_metadata)
        if is_system:
            self._assert_elevated()

        tmp = tempfile.mkdtemp()
        script_path = os.path.join(tmp, 'install.ps1')
        self._download(self.SCRIPT_URL, script_path)

        wrapper_path = os.path.join(tmp, 'aws-update.cmd')
        ps_exe = self._powershell_path or self._find_powershell()
        self._verify_script(script_path, ps_exe)
        ps_args = f'-NoProfile -File "{script_path}"'
        if is_system:
            ps_args += ' -System'

        with open(wrapper_path, 'w') as f:
            # Windows acquires a lock when running an exe process, preventing
            # an update in-place. The workaround is to launch a detached CMD
            # subprocess and exit the parent early. Use ping to wait before
            # running the installation to ensure the parent isn't holding onto
            # the lock.
            f.write('@echo off\n')
            f.write('set AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE=update-exe\n')
            if self._no_color:
                f.write('set NO_COLOR=1\n')
            # Clear the inherited PSModulePath so the launched PowerShell
            # rebuilds its own default.
            # https://github.com/aws/aws-cli/issues/10532
            f.write('set PSModulePath=\n')
            f.write('ping -n 3 127.0.0.1 >nul 2>&1\n')
            f.write(f'"{ps_exe}" {ps_args}\n')

        self._run_update(['cmd', '/c', wrapper_path])
        uni_print(
            'Update started. This process will exit and the '
            'update will complete shortly.\n'
        )

    def _run_install(self, cmd):
        subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def _verify_script(self, script_path, ps_exe):
        # Verify the downloaded install script's Authenticode signature before
        # executing it: the signature must be valid AND signed by AWS (signer
        # organization) AND issued by our CA. The script path is passed via an
        # environment variable to avoid any quoting issues.
        if self._skip_verification:
            self._warn_skipping_verification()
            return
        orgs = ','.join(
            "'" + org.replace("'", "''") + "'" for org in _WINDOWS_SIGNER_ORGS
        )
        ps_command = (
            "$ErrorActionPreference = 'Stop'; "
            "$path = $env:AWS_CLI_VERIFY_PATH; "
            "$sig = Get-AuthenticodeSignature -FilePath $path; "
            "if ($sig.Status -ne 'Valid') { "
            "Write-Error \"signature status is '$($sig.Status)'\"; exit 1 }; "
            "$cert = $sig.SignerCertificate; "
            "if (-not $cert) { Write-Error 'no signer certificate'; exit 1 }; "
            f"$orgs = @({orgs}); $ok = $false; "
            "foreach ($o in $orgs) { "
            "if ($cert.Subject -like \"*$o*\") { $ok = $true; break } }; "
            "if (-not $ok) { "
            "Write-Error \"not signed by AWS: $($cert.Subject)\"; exit 1 }; "
            f"if ($cert.Issuer -notlike '*{_WINDOWS_SIGNER_ISSUER}*') {{ "
            "Write-Error \"unexpected issuer: $($cert.Issuer)\"; exit 1 }; "
            "exit 0"
        )
        env = os.environ.copy()
        env['AWS_CLI_VERIFY_PATH'] = script_path
        result = subprocess.run(
            [ps_exe, '-NoProfile', '-Command', ps_command],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise UpdateError(
                f'install script signature verification failed: {detail}'
            )
        uni_print('Install script signature verified.\n')

    def _find_powershell(self):
        for name in ('powershell', 'pwsh'):
            path = shutil.which(name)
            if path:
                return path
        raise UpdateError(
            'Neither powershell.exe nor pwsh.exe was found on PATH.'
        )

    def _is_system_install(self, install_metadata):
        if 'script_install' in install_metadata:
            return install_metadata['script_install'].get('system', False)
        # AWS CLI is always installed to 'C:\Program Files\Amazon\AWSCLIV2'
        # for all users. 'ProgramW6432' always points to 'C:\Program Files'
        # while 'ProgramFiles' dynamically points to 'C:\Program Files' or
        # 'C:\Program Files (x86)', depending on the architecture.
        # Prefer 'ProgramW6432' and only read 'ProgramFiles' as a fallback.
        program_files = os.environ.get('ProgramW6432') or os.environ.get(
            'ProgramFiles'
        )
        if not program_files:
            return False
        canonical = os.path.join(
            program_files, 'Amazon', 'AWSCLIV2', 'aws.exe'
        )
        buf = ctypes.create_unicode_buffer(32768)
        ctypes.windll.kernel32.GetModuleFileNameW(None, buf, len(buf))
        return os.path.normcase(buf.value) == os.path.normcase(canonical)

    def _assert_elevated(self):
        elevated = (
            bool(ctypes.windll.shell32.IsUserAnAdmin())
            if self._is_elevated is None
            else self._is_elevated
        )
        if not elevated:
            raise UpdateError(
                'Updating a system-wide AWS CLI install requires an '
                'elevated shell. Re-run from an Administrator prompt.'
            )


UpdateCommand = WindowsUpdateCommand if is_windows else UnixUpdateCommand


def register_update_command(event_handlers):
    event_handlers.register(
        'building-command-table.main', UpdateCommand.add_command
    )


class UpdateError(Exception):
    pass
