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

import subprocess

from argparse import Namespace
from mock import MagicMock, patch, call, mock_open
from awscli.customizations.codedeploy.systems import Windows, Ubuntu, RHEL
from awscli.testutils import unittest


class TestWindows(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = patch('subprocess.Popen')
        self.popen = self.popen_patcher.start()

        self.check_call_patcher = patch('subprocess.check_call')
        self.check_call = self.check_call_patcher.start()

        self.open_patcher = patch(
            'awscli.customizations.codedeploy.systems.open',
            mock_open(), create=True
        )
        self.open = self.open_patcher.start()

        self.config_dir = r'C:\ProgramData\Amazon\CodeDeploy'
        self.config_file = 'conf.onpremises.yml'
        self.config_path = r'{0}\{1}'.format(self.config_dir, self.config_file)
        self.installer = 'codedeploy-agent.msi'
        self.bucket = 'bucket'
        self.key = 'key'
        self.region = 'us-east-1'

        self.body = 'install-script'
        self.reader = MagicMock()
        self.reader.read.return_value = self.body
        self.s3 = MagicMock()
        self.s3.get_object.return_value = {'Body': self.reader}

        self.session = MagicMock()
        self.session.create_client.return_value = self.s3

        self.params = Namespace()
        self.params.session = self.session
        self.params.region = self.region
        self.params.bucket = self.bucket
        self.params.key = self.key

        self.windows = Windows(self.params)

    def tearDown(self):
        self.popen_patcher.stop()
        self.check_call_patcher.stop()
        self.open_patcher.stop()

    def test_config_dir(self):
        self.assertEqual(self.config_dir, self.windows.CONFIG_DIR)

    def test_config_file(self):
        self.assertEquals(self.config_file, self.windows.CONFIG_FILE)

    def test_config_path(self):
        self.assertEquals(self.config_path, self.windows.CONFIG_PATH)

    def test_installer(self):
        self.assertEquals(self.installer, self.windows.INSTALLER)

    def test_install(self):
        process = MagicMock()
        process.communicate.side_effect = [('', ''), ('Running', '')]
        process.returncode = 0
        self.popen.return_value = process
        self.windows.install(self.params)
        self.popen.assert_has_calls([
            call(
                [
                    'powershell.exe',
                    '-Command', 'Stop-Service',
                    '-Name', 'codedeployagent'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate(),
            call(
                [
                    'powershell.exe',
                    '-Command', 'Get-Service',
                    '-Name', 'codedeployagent'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])
        self.check_call.assert_has_calls([
            call(
                [
                    r'.\{0}'.format(self.installer),
                    '/quiet',
                    '/l', r'.\codedeploy-agent-install-log.txt'
                ],
                shell=True
            ),
            call([
                'powershell.exe',
                '-Command', 'Restart-Service',
                '-Name', 'codedeployagent'
            ])
        ])
        self.open.assert_called_with(self.installer, 'wb')
        self.open().write.assert_called_with(self.body)

    def test_uninstall(self):
        process = MagicMock()
        process.communicate.side_effect = [('', ''), ('', '')]
        process.returncode = 0
        self.popen.return_value = process
        self.windows.uninstall(self.params)
        self.popen.assert_has_calls([
            call(
                [
                    'powershell.exe',
                    '-Command', 'Stop-Service',
                    '-Name', 'codedeployagent'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate(),
            call(
                [
                    'wmic',
                    'product', 'where', 'name="CodeDeploy Host Agent"',
                    'call', 'uninstall', '/nointeractive'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])


class TestLinux(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = patch('subprocess.Popen')
        self.popen = self.popen_patcher.start()

        self.check_call_patcher = patch('subprocess.check_call')
        self.check_call = self.check_call_patcher.start()

        self.open_patcher = patch(
            'awscli.customizations.codedeploy.systems.open',
            mock_open(), create=True
        )
        self.open = self.open_patcher.start()

        self.environ_patcher = patch('os.environ')
        self.environ = self.environ_patcher.start()
        self.environ.copy.return_value = dict()

        self.config_dir = '/etc/codedeploy-agent/conf'
        self.config_file = 'codedeploy.onpremises.yml'
        self.config_path = '{0}/{1}'.format(self.config_dir, self.config_file)
        self.installer = 'install'
        self.bucket = 'bucket'
        self.key = 'key'
        self.region = 'us-east-1'

        self.access_key_id = 'ACCESSKEYID'
        self.secret_access_key = 'SECRETACCESSKEY'
        self.session_token = 'SESSION_TOKEN'
        self.credentials = MagicMock()
        self.credentials.access_key = self.access_key_id
        self.credentials.secret_key = self.secret_access_key
        self.credentials.token = self.session_token

        self.environment = dict({
            'AWS_REGION': self.region,
            'AWS_ACCESS_KEY_ID': self.access_key_id,
            'AWS_SECRET_ACCESS_KEY': self.secret_access_key,
            'AWS_SESSION_TOKEN': self.session_token
        })

        self.body = 'install-script'
        self.reader = MagicMock()
        self.reader.read.return_value = self.body
        self.s3 = MagicMock()
        self.s3.get_object.return_value = {'Body': self.reader}

        self.session = MagicMock()
        self.session.create_client.return_value = self.s3
        self.session.get_credentials.return_value = self.credentials

        self.params = Namespace()
        self.params.session = self.session
        self.params.region = self.region
        self.params.bucket = self.bucket
        self.params.key = self.key

    def tearDown(self):
        self.popen_patcher.stop()
        self.check_call_patcher.stop()
        self.open_patcher.stop()
        self.environ_patcher.stop()


class TestUbuntu(TestLinux):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.ubuntu = Ubuntu(self.params)

    def test_config_dir(self):
        self.assertEquals(self.config_dir, self.ubuntu.CONFIG_DIR)

    def test_config_file(self):
        self.assertEquals(self.config_file, self.ubuntu.CONFIG_FILE)

    def test_config_path(self):
        self.assertEquals(self.config_path, self.ubuntu.CONFIG_PATH)

    def test_installer(self):
        self.assertEquals(self.installer, self.ubuntu.INSTALLER)

    @patch('os.geteuid', create=True)
    def test_validate_administrator_throws(self, geteuid):
        geteuid.return_value = 1
        with self.assertRaisesRegexp(
                RuntimeError, 'You must run this command as sudo.'):
            self.ubuntu.validate_administrator()

    def test_install(self):
        process = MagicMock()
        process.communicate.return_value = ('', '')
        process.returncode = 0
        self.popen.return_value = process
        self.ubuntu.install(self.params)
        self.popen.assert_has_calls([
            call(
                ['service', 'codedeploy-agent', 'stop'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])
        self.check_call.assert_has_calls([
            call(['apt-get', '-y', 'update']),
            call(['apt-get', '-y', 'install', 'ruby2.0']),
            call(['chmod', '+x', './{0}'.format(self.installer)]),
            call(
                ['./{0}'.format(self.installer), 'auto'],
                env=self.environment
            )
        ])
        self.open.assert_called_with(self.installer, 'wb')
        self.open().write.assert_called_with(self.body)

    def test_uninstall(self):
        process = MagicMock()
        process.communicate.return_value = ('', '')
        process.returncode = 0
        self.popen.return_value = process
        self.ubuntu.uninstall(self.params)
        self.popen.assert_has_calls([
            call(
                ['service', 'codedeploy-agent', 'stop'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])
        self.check_call.assert_has_calls([
            call(['dpkg', '-r', 'codedeploy-agent'])
        ])

class TestRHEL(TestLinux):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.rhel = RHEL(self.params)

    def test_config_dir(self):
        self.assertEquals(self.config_dir, self.rhel.CONFIG_DIR)

    def test_config_file(self):
        self.assertEquals(self.config_file, self.rhel.CONFIG_FILE)

    def test_config_path(self):
        self.assertEquals(self.config_path, self.rhel.CONFIG_PATH)

    def test_installer(self):
        self.assertEquals(self.installer, self.rhel.INSTALLER)

    @patch('os.geteuid', create=True)
    def test_validate_administrator_throws(self, geteuid):
        geteuid.return_value = 1
        with self.assertRaisesRegexp(
                RuntimeError, 'You must run this command as sudo.'):
            self.rhel.validate_administrator()

    def test_install(self):
        process = MagicMock()
        process.communicate.return_value = ('', '')
        process.returncode = 0
        self.popen.return_value = process
        self.rhel.install(self.params)
        self.popen.assert_has_calls([
            call(
                ['service', 'codedeploy-agent', 'stop'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])
        self.check_call.assert_has_calls([
            call(['yum', '-y', 'install', 'ruby']),
            call(['chmod', '+x', './{0}'.format(self.installer)]),
            call(
                ['./{0}'.format(self.installer), 'auto'],
                env=self.environment
            )
        ])
        self.open.assert_called_with(self.installer, 'wb')
        self.open().write.assert_called_with(self.body)

    def test_uninstall(self):
        process = MagicMock()
        process.communicate.return_value = ('', '')
        process.returncode = 0
        self.popen.return_value = process
        self.rhel.uninstall(self.params)
        self.popen.assert_has_calls([
            call(
                ['service', 'codedeploy-agent', 'stop'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ),
            call().communicate()
        ])
        self.check_call.assert_has_calls([
            call(['yum', '-y', 'erase', 'codedeploy-agent'])
        ])

if __name__ == "__main__":
    unittest.main()
