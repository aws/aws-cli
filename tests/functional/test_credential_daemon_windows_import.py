# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The CLI must still start on Windows, where the credential daemon doesn't
run: no credential daemon module may import a POSIX-only module (``pwd``,
``grp``, ``fcntl``, ``termios``...) at import time.

Each test runs in a fresh interpreter that hides those modules and reports
Windows as the platform, so a module the CLI already imported can't hide
the failure.
"""

import os
import subprocess
import sys
import textwrap

import pytest

import awscli

# Every module the credential daemon work adds or changes, as of this
# commit. A commit that adds or renames one updates this list.
MODULES = [
    'awscli.botocore.credential_daemon',
    'awscli.botocore.credentials',
    'awscli.botocore.exceptions',
    'awscli.botocore.useragent',
    'awscli.clidriver',
    'awscli.customizations.configure.configure',
    'awscli.customizations.configure.credential_daemon_keys',
    'awscli.customizations.configure.credential_daemon_install.commands',
    'awscli.customizations.configure.credential_daemon_install.host',
    'awscli.customizations.configure.credential_daemon_install.links',
    'awscli.customizations.configure.credential_daemon_install.linux',
    'awscli.customizations.configure.credential_daemon_install.macos',
    'awscli.customizations.configure.credential_daemon_install.release',
    'awscli.customizations.configure.credentialdaemon',
    'awscli.customizations.configure.importer',
    'awscli.customizations.configure.mfalogin',
    'awscli.customizations.configure.set',
    'awscli.customizations.configure.sso_commands',
    'awscli.customizations.configure.writer',
    'awscli.customizations.credential_daemon.client',
    'awscli.customizations.credential_daemon.hint',
    'awscli.customizations.credential_daemon.messages',
    'awscli.customizations.credential_daemon.storage',
    'awscli.customizations.credential_daemon.storage.chooser',
    'awscli.customizations.credential_daemon.storage.kinds',
    'awscli.customizations.credential_daemon.storage.policy',
    'awscli.customizations.credential_daemon.storage.presence',
    'awscli.customizations.credential_daemon.storage.profiles',
    'awscli.customizations.gpg',
    'awscli.customizations.login.credential_daemon',
    'awscli.customizations.login.login',
    'awscli.customizations.login.logout',
    'awscli.customizations.sso.login',
    'awscli.customizations.sso.logout',
    'awscli.customizations.sso.utils',
    'awscli.customizations.update',
    'awscli.redaction',
    'awscli.utils',
]

# Runs before any awscli import. The standard library modules are imported
# first, on the real platform: on Windows they load their own nt-based
# variants, which this host doesn't have. For the same reason, Path() keeps
# building POSIX paths after os.name says Windows.
_PRELUDE = textwrap.dedent(
    """\
    import sys, os
    import asyncio, ctypes, getpass, importlib.abc, logging, pathlib
    import platform
    import selectors, shutil, signal, socket, ssl, subprocess, tarfile
    import tempfile, uuid
    for name in ('pwd', 'grp', 'fcntl', 'termios', 'resource', 'tty', 'pty'):
        sys.modules[name] = None
    if os.name != 'nt':
        pathlib.WindowsPath = pathlib.PosixPath
        # 3.13 picks the class in pathlib._local.
        if 'pathlib._local' in sys.modules:
            sys.modules['pathlib._local'].WindowsPath = pathlib.PosixPath
    import types
    # Windows has msvcrt, and agenttoolkit's file lock imports it.
    msvcrt = types.ModuleType('msvcrt')
    msvcrt.LK_NBLCK = 2
    msvcrt.LK_UNLCK = 0
    msvcrt.locking = lambda *args: None
    sys.modules['msvcrt'] = msvcrt
    sys.platform = 'win32'
    os.name = 'nt'
    """
)


_ROOT = os.path.dirname(os.path.dirname(awscli.__file__))

# Variables a Windows Python child expects. Without SYSTEMROOT it can't get
# random numbers for hash randomization and dies before running any code.
_WINDOWS_START_VARS = (
    'SYSTEMROOT',
    'WINDIR',
    'COMSPEC',
    'PATH',
    'PATHEXT',
    'TEMP',
    'TMP',
)


def _child_env():
    """This process's environment, plus what a Windows child needs to start.

    If os.environ was replaced by a plain dict without those variables,
    for example by a patch another test didn't stop, each missing one is
    taken from nt.environ, the environment this process started with.
    """
    env = dict(os.environ)
    if sys.platform == 'win32':
        import nt

        present = {name.upper() for name in env}
        started_with = {k.upper(): v for k, v in nt.environ.items()}
        for name in _WINDOWS_START_VARS:
            if name not in present and name in started_with:
                env[name] = started_with[name]
    return env


def _run_as_windows(code, tmp_path):
    env = _child_env()
    env['AWS_CONFIG_FILE'] = str(tmp_path / 'config')
    env['AWS_SHARED_CREDENTIALS_FILE'] = str(tmp_path / 'credentials')
    env['HOME'] = str(tmp_path)
    # Where Windows Python looks for the home folder.
    env['USERPROFILE'] = str(tmp_path)
    # Import this checkout's awscli, not an installed one.
    env['PYTHONPATH'] = os.pathsep.join(
        p for p in (_ROOT, env.get('PYTHONPATH')) if p
    )
    return subprocess.run(
        [sys.executable, '-c', _PRELUDE + textwrap.dedent(code)],
        env=env,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_prelude_blocks_posix_modules(tmp_path):
    result = _run_as_windows(
        """\
        try:
            import pwd
        except ImportError:
            print('blocked')
        """,
        tmp_path,
    )
    assert result.stdout.strip() == 'blocked', result.stderr


def _exists(module):
    path = os.path.join(_ROOT, *module.split('.'))
    return os.path.exists(path + '.py') or os.path.isdir(path)


@pytest.mark.parametrize('module', MODULES)
def test_module_imports_on_windows(module, tmp_path):
    # A missing module fails: a renamed one would otherwise drop out of
    # the check without anyone noticing.
    assert _exists(module), f'{module} is listed but not in this checkout'
    result = _run_as_windows(
        f"""\
        import importlib
        importlib.import_module({module!r})
        print('ok')
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok'


def test_command_tables_build_on_windows(tmp_path):
    result = _run_as_windows(
        """\
        from awscli.clidriver import create_clidriver

        def walk(table):
            for command in table.values():
                sub = getattr(command, 'subcommand_table', None)
                if sub:
                    walk(sub)

        driver = create_clidriver()
        table = driver._get_command_table()
        for name in ('configure', 'login', 'logout', 'sso'):
            walk({name: table[name]})
        daemon = table['configure'].subcommand_table['credential-daemon']
        print(sorted(daemon.subcommand_table))
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['install', 'link', 'uninstall']"


@pytest.mark.parametrize('subcommand', ['install', 'uninstall', 'link'])
def test_credential_daemon_commands_refuse_on_windows(subcommand, tmp_path):
    result = _run_as_windows(
        f"""\
        import sys
        from awscli.clidriver import create_clidriver

        sys.exit(
            create_clidriver().main(
                ['configure', 'credential-daemon', {subcommand!r}]
            )
        )
        """,
        tmp_path,
    )
    assert result.returncode == 253, result.stderr
    assert "doesn't run on this platform" in result.stderr
    assert 'Traceback' not in result.stderr
