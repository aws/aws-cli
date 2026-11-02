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
from awscli.botocore.utils import ensure_boolean
from awscli.clidriver import (
    INSTALL_FILENAME,
    get_distribution_source,
)
from awscli.compat import is_windows
from awscli.customizations.agenttoolkit.hint import (
    HINT_DISABLED_ENV_VAR,
    HINT_TEXT,
    hint_disabled,
)
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
                'be installed). Setting the '
                'AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION environment '
                'variable to "true" does the same.'
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
        self._skip_verification = parsed_args.skip_signature_verification or (
            ensure_boolean(
                os.environ.get(
                    'AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION', ''
                )
            )
        )
        self._do_update()
        if not hint_disabled():
            uni_print(HINT_TEXT)
        return 0

    def _warn_skipping_verification(self):
        uni_print(
            "WARNING: skipping install script signature verification "
            "(--skip-signature-verification or "
            "AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION); the downloaded "
            "script will be run without confirming it is authentic.\n",
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
            # The install script prints the Agent Toolkit tip too. Silence its
            # copy so we own the decision and print at most one.
            env[HINT_DISABLED_ENV_VAR] = 'true'
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
            if self._skip_verification:
                # Forward the opt-out so the install script also skips its own
                # installer-signature check. Without this it would hard-fail
                # when gpg is unavailable, defeating --skip-signature-verification.
                cmd.append('--skip-signature-verification')
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
                'be verified. Install gnupg and try again, re-run with '
                '--skip-signature-verification, or set '
                'AWS_CLI_INSTALL_SKIP_SIGNATURE_VERIFICATION=true, to update '
                'without verification (not recommended).'
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
        system_directory=None,
        **kwargs,
    ):
        super().__init__(session, **kwargs)
        self._is_elevated = is_elevated
        self._run_update = runner or self._run_install
        self._powershell_path = powershell_path
        self._system_directory = system_directory

    def _do_update(self):
        is_system = self._is_system_install(self._install_metadata)
        if is_system:
            self._assert_elevated()

        # The update may run elevated, so every executable is launched by an
        # absolute path and never resolved from the current working
        # directory, which may contain a planted executable.
        system_dir = self._get_system_directory()
        tmp = tempfile.mkdtemp()
        script_path = os.path.join(tmp, 'install.ps1')
        self._download(self.SCRIPT_URL, script_path)

        wrapper_path = os.path.join(tmp, 'aws-update.cmd')
        ps_exe = self._powershell_path or self._find_powershell(system_dir)
        self._verify_script(script_path, ps_exe)
        ps_args = f'-NoProfile -File "{script_path}"'
        if is_system:
            ps_args += ' -System'
        if self._skip_verification:
            # Forward the opt-out so install.ps1 also skips its own installer
            # verification, matching the user's --skip-signature-verification.
            ps_args += ' -SkipSignatureVerification'

        with open(wrapper_path, 'w') as f:
            # Windows acquires a lock when running an exe process, preventing
            # an update in-place. The workaround is to launch a detached CMD
            # subprocess and exit the parent early. Use ping to wait before
            # running the installation to ensure the parent isn't holding onto
            # the lock.
            f.write('@echo off\n')
            f.write('set NoDefaultCurrentDirectoryInExePath=1\n')
            f.write('set AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE=update-exe\n')
            if self._no_color:
                f.write('set NO_COLOR=1\n')
            # Clear the inherited PSModulePath so the launched PowerShell
            # rebuilds its own default.
            # https://github.com/aws/aws-cli/issues/10532
            f.write('set PSModulePath=\n')
            ping_exe = os.path.join(system_dir, 'PING.EXE')
            f.write(f'"{ping_exe}" -n 3 127.0.0.1 >nul 2>&1\n')
            f.write(f'"{ps_exe}" {ps_args}\n')

        cmd_exe = os.path.join(system_dir, 'cmd.exe')
        self._run_update([cmd_exe, '/c', wrapper_path], tmp)
        uni_print(
            'Update started. This process will exit and the '
            'update will complete shortly.\n'
        )

    def _run_install(self, cmd, cwd):
        # Run from the private temp directory with the current directory
        # excluded from executable lookups, so nothing launched by name can
        # be picked up from the caller's working directory.
        env = os.environ.copy()
        env['NoDefaultCurrentDirectoryInExePath'] = '1'
        subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
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
        # Match the certificate's Organization (O) relative distinguished name
        # *exactly* against the allowlist, rather than substring-matching the
        # whole subject DN: a substring match on the DN would also accept a
        # DigiCert-issued cert whose CN/OU merely contained one of these
        # strings. X500DistinguishedName.Format($true) emits one RDN per line,
        # so an O value that itself contains commas (e.g. "Amazon Web Services,
        # Inc.") is parsed correctly. Format wraps such values in double
        # quotes, so Get-Org strips a surrounding quote pair before matching.
        ps_command = "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                "function Get-Org("
                "[System.Security.Cryptography.X509Certificates."
                "X500DistinguishedName]$name) {",
                '  foreach ($line in ($name.Format($true) '
                '-split "\\r?\\n")) {',
                "    if ($line -match '^O=(.*)$') {",
                "      $v = $matches[1].Trim();",
                "      if ($v.Length -ge 2 -and $v.StartsWith('\"') "
                "-and $v.EndsWith('\"')) "
                "{ $v = $v.Substring(1, $v.Length - 2) "
                "-replace '\"\"', '\"' };",
                "      return $v",
                "    }",
                "  }",
                "  return $null",
                "}",
                "$path = $env:AWS_CLI_VERIFY_PATH",
                "$sig = Get-AuthenticodeSignature -FilePath $path",
                "if ($sig.Status -ne 'Valid') "
                "{ Write-Error \"signature status is '$($sig.Status)'\"; "
                "exit 1 }",
                "$cert = $sig.SignerCertificate",
                "if (-not $cert) "
                "{ Write-Error 'no signer certificate'; exit 1 }",
                f"$orgs = @({orgs})",
                "$subjectOrg = Get-Org $cert.SubjectName",
                "if ($orgs -notcontains $subjectOrg) "
                '{ Write-Error "not signed by AWS (O=$subjectOrg): '
                '$($cert.Subject)"; exit 1 }',
                "$issuerOrg = Get-Org $cert.IssuerName",
                f"if ($issuerOrg -notlike '*{_WINDOWS_SIGNER_ISSUER}*') "
                '{ Write-Error "unexpected issuer (O=$issuerOrg): '
                '$($cert.Issuer)"; exit 1 }',
                "exit 0",
            ]
        )
        env = os.environ.copy()
        # Clear any inherited PSModulePath so this PowerShell invocation
        # rebuilds its own default; inheriting it can break module resolution
        # across PS5/PS7. https://github.com/aws/aws-cli/issues/10532
        env.pop('PSModulePath', None)
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

    def _get_system_directory(self):
        if self._system_directory is not None:
            return self._system_directory
        # Ask the OS rather than trusting %SystemRoot% from the environment.
        buf = ctypes.create_unicode_buffer(260)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(buf, len(buf))
        if not length or length > len(buf):
            raise UpdateError('Unable to locate the Windows system directory.')
        return buf.value

    def _is_absolute_path(self, path):
        # Before Python 3.13, isabs() on Windows also accepts root-relative
        # paths such as "\tools", which resolve against the current drive, so
        # a drive letter or UNC share is required as well.
        if not os.path.isabs(path):
            return False
        return os.name != 'nt' or bool(os.path.splitdrive(path)[0])

    def _find_powershell(self, system_dir):
        # Search PATH ourselves instead of using shutil.which(), which on
        # Windows also checks the current working directory. Only absolute
        # PATH entries are considered, since empty or relative entries resolve
        # against the cwd, and only real .exe files are accepted so a planted
        # .cmd or .bat cannot be picked up through PATHEXT.
        directories = [
            d.strip('"') for d in os.environ.get('PATH', '').split(os.pathsep)
        ]
        for name in ('powershell.exe', 'pwsh.exe'):
            for directory in directories:
                if not self._is_absolute_path(directory):
                    continue
                path = os.path.join(directory, name)
                if os.path.isfile(path):
                    return path
        # PATH may be empty, trimmed, or contain unexpanded entries, so fall
        # back to the Windows PowerShell that ships in the system directory.
        path = os.path.join(
            system_dir, 'WindowsPowerShell', 'v1.0', 'powershell.exe'
        )
        if os.path.isfile(path):
            return path
        raise UpdateError(
            'Neither powershell.exe nor pwsh.exe was found on PATH or in the '
            'Windows system directory.'
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
