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
from awscli.customizations.agenttoolkit.hint import (
    maybe_prompt_agent_toolkit,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print

_DOWNLOAD_BASE_URL = 'https://awscli.amazonaws.com'

_SUPPORTED_SOURCES = ('exe', 'script-exe', 'update-exe')


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
    ARG_TABLE = []

    _no_color = False

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
        self._do_update()
        self._maybe_prompt_agent_toolkit(parsed_globals)
        return 0

    def _maybe_prompt_agent_toolkit(self, parsed_globals):
        maybe_prompt_agent_toolkit(self._session, parsed_globals)

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
            f.write('ping -n 3 127.0.0.1 >nul 2>&1\n')
            f.write(f'"{ps_exe}" {ps_args}\n')

        self._run_update(['cmd', '/c', wrapper_path])
        uni_print(
            'Update started. This process will exit and the '
            'update will complete shortly.\n'
        )

    def _maybe_prompt_agent_toolkit(self, parsed_globals):
        # No-op on Windows: the update runs in a detached subprocess and the
        # actual CLI update happens after this process exits, so there is no
        # safe point to prompt (blocking here would hold the exe lock the
        # detached-process workaround exists to avoid).
        pass

    def _run_install(self, cmd):
        subprocess.Popen(
            cmd,
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def _find_powershell(self):
        path = shutil.which('powershell')
        if not path:
            raise UpdateError('powershell.exe not found on PATH.')
        return path

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
