# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import ctypes
import os
import re
import shutil
import stat
import sys
import tempfile
from argparse import Namespace
from socket import timeout

from awscli.customizations.codedeploy.install import Install
from awscli.customizations.codedeploy.systems import (
    RHEL,
    System,
    Ubuntu,
    Windows,
    _create_windows_file,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.testutils import mock, unittest


class TestInstall(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'
        self.config_file = 'config-file'
        self.installer = 'install'
        self.bucket = f'aws-codedeploy-{self.region}'
        self.key = f'latest/{self.installer}'
        self.agent_installer = f's3://{self.bucket}/{self.key}'

        self.system_patcher = mock.patch('platform.system')
        self.system = self.system_patcher.start()
        self.system.return_value = 'Linux'

        self.linux_distribution_patcher = mock.patch(
            'awscli.compat.linux_distribution'
        )
        self.linux_distribution = self.linux_distribution_patcher.start()
        self.linux_distribution.return_value = ('Ubuntu', '', '')

        self.urlopen_patcher = mock.patch(
            'awscli.customizations.codedeploy.utils.urlopen'
        )
        self.urlopen = self.urlopen_patcher.start()
        self.urlopen.side_effect = timeout('Not EC2 instance')

        self.geteuid_patcher = mock.patch('os.geteuid', create=True)
        self.geteuid = self.geteuid_patcher.start()
        self.geteuid.return_value = 0

        self.isfile_patcher = mock.patch('os.path.isfile')
        self.isfile = self.isfile_patcher.start()
        self.isfile.return_value = False

        self.makedirs_patcher = mock.patch('os.makedirs')
        self.makedirs = self.makedirs_patcher.start()

        self.config_open_patcher = mock.patch(
            'awscli.customizations.codedeploy.install.open',
            mock.mock_open(read_data=b'config-contents'),
            create=True,
        )
        self.config_open = self.config_open_patcher.start()

        self.os_open_patcher = mock.patch(
            'awscli.customizations.codedeploy.install.os.open',
            return_value=3,
        )
        self.os_open = self.os_open_patcher.start()

        self.os_fdopen_patcher = mock.patch(
            'awscli.customizations.codedeploy.install.os.fdopen',
            mock.mock_open(),
        )
        self.os_fdopen = self.os_fdopen_patcher.start()

        self.os_chmod_patcher = mock.patch(
            'awscli.customizations.codedeploy.install.os.chmod'
        )
        self.os_chmod = self.os_chmod_patcher.start()

        self.create_config_file_patcher = mock.patch.object(
            Windows, 'create_config_file', return_value=4
        )
        self.create_config_file = self.create_config_file_patcher.start()

        self.open_patcher = mock.patch(
            'awscli.customizations.codedeploy.systems.open',
            mock.mock_open(),
            create=True,
        )
        self.open = self.open_patcher.start()

        self.args = Namespace()
        self.args.override_config = False
        self.args.config_file = self.config_file
        self.args.agent_installer = None

        self.globals = Namespace()
        self.globals.region = self.region

        self.body = 'install-script'
        self.reader = mock.MagicMock()
        self.reader.read.return_value = self.body
        self.s3 = mock.MagicMock()
        self.s3.get_object.return_value = {'Body': self.reader}

        self.session = mock.MagicMock()
        self.session.create_client.return_value = self.s3
        self.install = Install(self.session)

    def tearDown(self):
        self.system_patcher.stop()
        self.linux_distribution_patcher.stop()
        self.urlopen_patcher.stop()
        self.geteuid_patcher.stop()
        self.isfile_patcher.stop()
        self.makedirs_patcher.stop()
        self.config_open_patcher.stop()
        self.os_open_patcher.stop()
        self.os_fdopen_patcher.stop()
        self.os_chmod_patcher.stop()
        self.create_config_file_patcher.stop()
        self.open_patcher.stop()

    def test_install_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        error_msg = 'Region not specified.'
        with self.assertRaisesRegex(ConfigurationError, error_msg):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_unsupported_system(self):
        self.system.return_value = 'Unsupported'
        with self.assertRaisesRegex(
            RuntimeError, System.UNSUPPORTED_SYSTEM_MSG
        ):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_ec2_instance(self):
        self.urlopen.side_effect = None
        with self.assertRaisesRegex(
            RuntimeError, 'Amazon EC2 instances are not supported.'
        ):
            self.install._run_main(self.args, self.globals)
        self.assertIn('system', self.args)
        self.assertTrue(isinstance(self.args.system, Ubuntu))

    def test_install_throws_on_non_administrator(self):
        self.geteuid.return_value = 1
        with self.assertRaisesRegex(
            RuntimeError, 'You must run this command as sudo.'
        ):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_no_override_config(self):
        self.isfile.return_value = True
        self.args.override_config = False
        with self.assertRaisesRegex(
            RuntimeError,
            'The on-premises instance configuration file already exists. '
            'Specify --override-config to update the existing on-premises '
            'instance configuration file.',
        ):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_invalid_agent_installer(self):
        self.args.agent_installer = 'invalid-s3-location'
        with self.assertRaisesRegex(
            ParamValidationError,
            '--agent-installer must specify the Amazon S3 URL format as '
            's3://<bucket>/<key>.',
        ):
            self.install._run_main(self.args, self.globals)

    @mock.patch.object(Ubuntu, 'install')
    def test_install_with_agent_installer(self, install):
        self.args.agent_installer = self.agent_installer
        self.install._run_main(self.args, self.globals)
        self.assertIn('bucket', self.args)
        self.assertEqual(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEqual(self.key, self.args.key)
        self.assertIn('installer', self.args)
        self.assertEqual(self.installer, self.args.installer)
        install.assert_called_with(self.args)

    @mock.patch.object(Ubuntu, 'install')
    def test_install_for_ubuntu(self, install):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.install._run_main(self.args, self.globals)
        self.assertIn('bucket', self.args)
        self.assertEqual(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEqual('latest/install', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEqual('install', self.args.installer)
        self.makedirs.assert_called_with('/etc/codedeploy-agent/conf')
        self.config_open.assert_called_with(self.config_file, 'rb')
        self.os_open.assert_called_with(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml',
            mock.ANY,
            0o600,
        )
        self.os_fdopen().write.assert_called_with(b'config-contents')
        install.assert_called_with(self.args)

    @mock.patch.object(Windows, 'install')
    @mock.patch.object(Windows, 'validate_administrator')
    def test_install_for_windows(self, validate_administrator, install):
        self.system.return_value = 'Windows'
        self.install._run_main(self.args, self.globals)
        self.assertIn('bucket', self.args)
        self.assertEqual(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEqual('latest/codedeploy-agent.msi', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEqual('codedeploy-agent.msi', self.args.installer)
        self.makedirs.assert_called_with(r'C:\ProgramData\Amazon\CodeDeploy')
        self.config_open.assert_called_with(self.config_file, 'rb')
        self.create_config_file.assert_called_with()
        self.assertFalse(self.os_open.called)
        self.assertFalse(self.os_chmod.called)
        self.os_fdopen.assert_called_with(4, 'wb')
        self.os_fdopen().write.assert_called_with(b'config-contents')
        validate_administrator.assert_called_with()
        install.assert_called_with(self.args)

    @mock.patch.object(Windows, 'install')
    @mock.patch.object(Windows, 'validate_administrator')
    def test_create_config_on_windows_replaces_when_source_is_destination(
        self, validate_administrator, install
    ):
        self.system.return_value = 'Windows'
        config_path = r'C:\ProgramData\Amazon\CodeDeploy\conf.onpremises.yml'
        self.args.config_file = config_path
        self.isfile.return_value = True
        self.args.override_config = True
        calls = mock.Mock()
        calls.attach_mock(self.config_open, 'read')
        calls.attach_mock(self.create_config_file, 'create_config_file')
        self.install._run_main(self.args, self.globals)
        self.assertEqual(
            [name for name, _, _ in calls.mock_calls if '.' not in name],
            ['read', 'create_config_file'],
        )
        self.config_open.assert_called_with(config_path, 'rb')
        self.os_fdopen().write.assert_called_with(b'config-contents')
        install.assert_called_with(self.args)

    @mock.patch.object(Windows, 'install')
    @mock.patch.object(Windows, 'validate_administrator')
    def test_create_config_on_windows_stops_if_file_cannot_be_replaced(
        self, validate_administrator, install
    ):
        self.system.return_value = 'Windows'
        self.create_config_file.side_effect = RuntimeError('in use')
        with mock.patch('sys.stderr', new_callable=mock.MagicMock):
            self.assertEqual(
                self.install._run_main(self.args, self.globals), 255
            )
        self.assertFalse(self.os_fdopen().write.called)
        self.assertFalse(install.called)

    @mock.patch.object(Ubuntu, 'install')
    def test_create_config_uses_restricted_permissions(self, install):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.install._run_main(self.args, self.globals)
        self.os_open.assert_called_with(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml',
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_BINARY', 0),
            0o600,
        )

    @mock.patch.object(Ubuntu, 'install')
    def test_create_config_chmods_existing_file(self, install):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.install._run_main(self.args, self.globals)
        self.os_chmod.assert_called_with(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml', 0o600
        )

    @mock.patch.object(Ubuntu, 'install')
    def test_create_config_skips_copy_when_source_is_destination(
        self, install
    ):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.args.config_file = (
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml'
        )
        self.isfile.return_value = True
        self.args.override_config = True
        self.install._run_main(self.args, self.globals)
        self.assertFalse(self.config_open.called)
        self.assertFalse(self.os_open.called)


@unittest.skipIf(os.name != 'posix', 'POSIX file modes only')
class TestInstallConfigFileMode(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tempdir, 'conf')
        self.config_path = os.path.join(
            self.config_dir, 'codedeploy.onpremises.yml'
        )
        self.source = os.path.join(self.tempdir, 'codedeploy.onpremises.yml')
        with open(self.source, 'w') as f:
            f.write('aws_secret_access_key: secret\n')
        os.chmod(self.source, 0o600)
        self.old_umask = os.umask(0o022)
        self.params = Namespace(
            config_file=self.source,
            system=Namespace(
                CONFIG_DIR=self.config_dir,
                CONFIG_PATH=self.config_path,
                RECREATE_CONFIG_FILE=False,
            ),
        )
        self.install = Install(mock.MagicMock())

    def tearDown(self):
        os.umask(self.old_umask)
        for root, dirs, files in os.walk(self.tempdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.tempdir)

    def _mode(self):
        return stat.S_IMODE(os.stat(self.config_path).st_mode)

    def test_new_config_file_is_owner_only(self):
        self.install._create_config(self.params)
        self.assertEqual(self._mode(), 0o600)
        with open(self.config_path) as f:
            self.assertEqual(f.read(), 'aws_secret_access_key: secret\n')

    def test_existing_config_file_is_tightened(self):
        os.makedirs(self.config_dir)
        with open(self.config_path, 'w') as f:
            f.write('old\n')
        os.chmod(self.config_path, 0o644)
        self.install._create_config(self.params)
        self.assertEqual(self._mode(), 0o600)
        with open(self.config_path) as f:
            self.assertEqual(f.read(), 'aws_secret_access_key: secret\n')


def _is_windows_admin():
    return os.name == 'nt' and bool(ctypes.windll.shell32.IsUserAnAdmin())


def _get_windows_dacl(path):
    """Return the DACL of ``path`` as an SDDL string, such as 'D:P(...)'."""
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    get_info = advapi32.GetNamedSecurityInfoW
    get_info.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    get_info.restype = wintypes.DWORD
    to_string = advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW
    to_string.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    to_string.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    se_file_object = 1
    dacl_security_information = 0x4
    descriptor = ctypes.c_void_p()
    result = get_info(
        path,
        se_file_object,
        dacl_security_information,
        None,
        None,
        None,
        None,
        ctypes.byref(descriptor),
    )
    if result != 0:
        raise ctypes.WinError(result)
    try:
        sddl = ctypes.c_void_p()
        if not to_string(
            descriptor, 1, dacl_security_information, ctypes.byref(sddl), None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.wstring_at(sddl.value)
        finally:
            kernel32.LocalFree(sddl)
    finally:
        kernel32.LocalFree(descriptor)


def _dacl_trustees(dacl):
    return {ace.split(';')[5] for ace in re.findall(r'\(([^)]*)\)', dacl)}


@unittest.skipIf(
    not _is_windows_admin(), 'Windows ACLs; requires an elevated session'
)
class TestInstallConfigFileWindowsAcl(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.tempdir, 'CodeDeploy')
        self.config_path = os.path.join(self.config_dir, 'conf.onpremises.yml')
        self.source = os.path.join(self.tempdir, 'codedeploy.onpremises.yml')
        with open(self.source, 'w') as f:
            f.write('aws_secret_access_key: secret\n')
        system = Windows(Namespace(session=mock.MagicMock(), region=None))
        system.CONFIG_DIR = self.config_dir
        system.CONFIG_PATH = self.config_path
        self.params = Namespace(config_file=self.source, system=system)
        self.install = Install(mock.MagicMock())

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def create_world_readable_config(self, contents):
        # An explicit Everyone-read entry, which a change to the directory
        # ACL or truncating the file would not remove.
        os.makedirs(self.config_dir)
        fd = _create_windows_file(
            self.config_path, 'D:(A;;FA;;;BA)(A;;FR;;;WD)'
        )
        with os.fdopen(fd, 'w') as f:
            f.write(contents)
        self.assertIn(
            'WD', _dacl_trustees(_get_windows_dacl(self.config_path))
        )

    def assert_admin_only_config(self):
        dacl = _get_windows_dacl(self.config_path)
        # Protected, so nothing is inherited from the directory.
        self.assertTrue(dacl.startswith('D:P'), dacl)
        self.assertEqual(_dacl_trustees(dacl), {'SY', 'BA'})
        with open(self.config_path) as f:
            self.assertEqual(f.read(), 'aws_secret_access_key: secret\n')

    def test_new_config_file_is_admin_only(self):
        self.install._create_config(self.params)
        self.assert_admin_only_config()

    def test_existing_config_file_with_explicit_access_is_replaced(self):
        self.create_world_readable_config('old\n')
        self.install._create_config(self.params)
        self.assert_admin_only_config()

    def test_installed_config_as_source_is_replaced(self):
        self.create_world_readable_config('aws_secret_access_key: secret\n')
        self.params.config_file = self.config_path
        self.install._create_config(self.params)
        self.assert_admin_only_config()


if __name__ == "__main__":
    unittest.main()
