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

import os
import stat
import sys
import tempfile

from argparse import Namespace
from awscli.customizations.codedeploy.install import Install
from awscli.customizations.codedeploy.systems import Ubuntu, Windows, RHEL, System
from awscli.testutils import mock, unittest
from socket import timeout


class TestInstall(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'
        self.config_file = 'config-file'
        self.installer = 'install'
        self.bucket = 'aws-codedeploy-{0}'.format(self.region)
        self.key = 'latest/{0}'.format(self.installer)
        self.agent_installer = 's3://{0}/{1}'.format(self.bucket, self.key)

        self.system_patcher = mock.patch('platform.system')
        self.system = self.system_patcher.start()
        self.system.return_value = 'Linux'

        self.linux_distribution_patcher = mock.patch('awscli.compat.linux_distribution')
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

        self.open_patcher = mock.patch(
            'awscli.customizations.codedeploy.systems.open',
            mock.mock_open(), create=True
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
        self.open_patcher.stop()

    def test_install_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        with self.assertRaisesRegex(RuntimeError, 'Region not specified.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_unsupported_system(self):
        self.system.return_value = 'Unsupported'
        with self.assertRaisesRegex(
                RuntimeError, System.UNSUPPORTED_SYSTEM_MSG):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_ec2_instance(self):
        self.urlopen.side_effect = None
        with self.assertRaisesRegex(
                RuntimeError, 'Amazon EC2 instances are not supported.'):
            self.install._run_main(self.args, self.globals)
        self.assertIn('system', self.args)
        self.assertTrue(isinstance(self.args.system, Ubuntu))

    def test_install_throws_on_non_administrator(self):
        self.geteuid.return_value = 1
        with self.assertRaisesRegex(
                RuntimeError, 'You must run this command as sudo.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_no_override_config(self):
        self.isfile.return_value = True
        self.args.override_config = False
        with self.assertRaisesRegex(
                RuntimeError,
                'The on-premises instance configuration file already exists. '
                'Specify --override-config to update the existing on-premises '
                'instance configuration file.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_invalid_agent_installer(self):
        self.args.agent_installer = 'invalid-s3-location'
        with self.assertRaisesRegex(
                ValueError,
                '--agent-installer must specify the Amazon S3 URL format as '
                's3://<bucket>/<key>.'):
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
        self.os_open.assert_called_with(
            r'C:\ProgramData\Amazon\CodeDeploy\conf.onpremises.yml',
            mock.ANY,
            0o600,
        )
        self.os_fdopen().write.assert_called_with(b'config-contents')
        validate_administrator.assert_called_with()
        install.assert_called_with(self.args)

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
                CONFIG_DIR=self.config_dir, CONFIG_PATH=self.config_path
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


if __name__ == "__main__":
    unittest.main()
