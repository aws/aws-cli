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

import sys

from argparse import Namespace
from awscli.customizations.codedeploy.install import Install
from awscli.customizations.codedeploy.systems import Ubuntu, Windows, RHEL, System
from awscli.testutils import unittest
from mock import MagicMock, patch, mock_open
from socket import timeout


class TestInstall(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'
        self.config_file = 'config-file'
        self.installer = 'install'
        self.bucket = 'aws-codedeploy-{0}'.format(self.region)
        self.key = 'latest/{0}'.format(self.installer)
        self.agent_installer = 's3://{0}/{1}'.format(self.bucket, self.key)

        self.system_patcher = patch('platform.system')
        self.system = self.system_patcher.start()
        self.system.return_value = 'Linux'

        self.linux_distribution_patcher = patch('awscli.compat.linux_distribution')
        self.linux_distribution = self.linux_distribution_patcher.start()
        self.linux_distribution.return_value = ('Ubuntu', '', '')

        self.urlopen_patcher = patch(
            'awscli.customizations.codedeploy.utils.urlopen'
        )
        self.urlopen = self.urlopen_patcher.start()
        self.urlopen.side_effect = timeout('Not EC2 instance')

        self.geteuid_patcher = patch('os.geteuid', create=True)
        self.geteuid = self.geteuid_patcher.start()
        self.geteuid.return_value = 0

        self.isfile_patcher = patch('os.path.isfile')
        self.isfile = self.isfile_patcher.start()
        self.isfile.return_value = False

        self.makedirs_patcher = patch('os.makedirs')
        self.makedirs = self.makedirs_patcher.start()

        self.copyfile_patcher = patch('shutil.copyfile')
        self.copyfile = self.copyfile_patcher.start()

        self.open_patcher = patch(
            'awscli.customizations.codedeploy.systems.open',
            mock_open(), create=True
        )
        self.open = self.open_patcher.start()

        self.args = Namespace()
        self.args.override_config = False
        self.args.config_file = self.config_file
        self.args.agent_installer = None

        self.globals = Namespace()
        self.globals.region = self.region

        self.body = 'install-script'
        self.reader = MagicMock()
        self.reader.read.return_value = self.body
        self.s3 = MagicMock()
        self.s3.get_object.return_value = {'Body': self.reader}

        self.session = MagicMock()
        self.session.create_client.return_value = self.s3
        self.install = Install(self.session)

    def tearDown(self):
        self.system_patcher.stop()
        self.linux_distribution_patcher.stop()
        self.urlopen_patcher.stop()
        self.geteuid_patcher.stop()
        self.isfile_patcher.stop()
        self.makedirs_patcher.stop()
        self.copyfile_patcher.stop()
        self.open_patcher.stop()

    def test_install_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        with self.assertRaisesRegexp(RuntimeError, 'Region not specified.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_unsupported_system(self):
        self.system.return_value = 'Unsupported'
        with self.assertRaisesRegexp(
                RuntimeError, System.UNSUPPORTED_SYSTEM_MSG):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_ec2_instance(self):
        self.urlopen.side_effect = None
        with self.assertRaisesRegexp(
                RuntimeError, 'Amazon EC2 instances are not supported.'):
            self.install._run_main(self.args, self.globals)
        self.assertIn('system', self.args)
        self.assertTrue(isinstance(self.args.system, Ubuntu))

    def test_install_throws_on_non_administrator(self):
        self.geteuid.return_value = 1
        with self.assertRaisesRegexp(
                RuntimeError, 'You must run this command as sudo.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_no_override_config(self):
        self.isfile.return_value = True
        self.args.override_config = False
        with self.assertRaisesRegexp(
                RuntimeError,
                'The on-premises instance configuration file already exists. '
                'Specify --override-config to update the existing on-premises '
                'instance configuration file.'):
            self.install._run_main(self.args, self.globals)

    def test_install_throws_on_invalid_agent_installer(self):
        self.args.agent_installer = 'invalid-s3-location'
        with self.assertRaisesRegexp(
                ValueError,
                '--agent-installer must specify the Amazon S3 URL format as '
                's3://<bucket>/<key>.'):
            self.install._run_main(self.args, self.globals)

    @patch.object(Ubuntu, 'install')
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

    @patch.object(Ubuntu, 'install')
    def test_install_for_ubuntu(self, install):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.install._run_main(self.args, self.globals)
        self.assertIn('bucket', self.args)
        self.assertEquals(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEquals('latest/install', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEquals('install', self.args.installer)
        self.makedirs.assert_called_with('/etc/codedeploy-agent/conf')
        self.copyfile.assset_called_with(
            'codedeploy.onpremises.yml',
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml'
        )
        install.assert_called_with(self.args)

    @patch.object(Windows, 'install')
    @patch.object(Windows, 'validate_administrator')
    def test_install_for_windows(self, validate_administrator, install):
        self.system.return_value = 'Windows'
        self.install._run_main(self.args, self.globals)
        self.assertIn('bucket', self.args)
        self.assertEquals(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEquals('latest/codedeploy-agent.msi', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEquals('codedeploy-agent.msi', self.args.installer)
        self.makedirs.assert_called_with(r'C:\ProgramData\Amazon\CodeDeploy')
        self.copyfile.assset_called_with(
            'conf.onpremises.yml',
            r'C:\ProgramData\Amazon\CodeDeploy\conf.onpremises.yml'
        )
        validate_administrator.assert_called_with()
        install.assert_called_with(self.args)


if __name__ == "__main__":
    unittest.main()
