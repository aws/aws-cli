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
from awscli.customizations.codedeploy.systems import Ubuntu, Windows, RHEL, System
from awscli.customizations.codedeploy.uninstall import Uninstall
from awscli.customizations.exceptions import ConfigurationError
from awscli.testutils import mock, unittest
from socket import timeout


class TestUninstall(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'

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

        self.remove_patcher = mock.patch('os.remove')
        self.remove = self.remove_patcher.start()

        self.args = Namespace()
        self.globals = Namespace()
        self.globals.region = self.region
        self.session = mock.MagicMock()
        self.uninstall = Uninstall(self.session)

    def tearDown(self):
        self.system_patcher.stop()
        self.linux_distribution_patcher.stop()
        self.urlopen_patcher.stop()
        self.geteuid_patcher.stop()
        self.remove_patcher.stop()

    def test_uninstall_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        error_msg = 'Region not specified.'
        with self.assertRaisesRegex(ConfigurationError, error_msg):
            self.uninstall._run_main(self.args, self.globals)

    def test_uninstall_throws_on_unsupported_system(self):
        self.system.return_value = 'Unsupported'
        with self.assertRaisesRegex(
                RuntimeError, System.UNSUPPORTED_SYSTEM_MSG):
            self.uninstall._run_main(self.args, self.globals)

    def test_uninstall_throws_on_ec2_instance(self):
        self.urlopen.side_effect = None
        with self.assertRaisesRegex(
                RuntimeError, 'Amazon EC2 instances are not supported.'):
            self.uninstall._run_main(self.args, self.globals)
        self.assertIn('system', self.args)
        self.assertTrue(isinstance(self.args.system, Ubuntu))

    def test_uninstall_throws_on_non_administrator(self):
        self.geteuid.return_value = 1
        with self.assertRaisesRegex(
                RuntimeError, 'You must run this command as sudo.'):
            self.uninstall._run_main(self.args, self.globals)

    @mock.patch.object(Ubuntu, 'uninstall')
    def test_uninstall_for_ubuntu(self, uninstall):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', '', '')
        self.uninstall._run_main(self.args, self.globals)
        uninstall.assert_called_with(self.args)
        self.remove.assert_called_with(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml'
        )

    @mock.patch.object(RHEL, 'uninstall')
    def test_uninstall_for_RHEL(self, uninstall):
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Red Hat Enterprise Linux Server', '', '')
        self.uninstall._run_main(self.args, self.globals)
        uninstall.assert_called_with(self.args)
        self.remove.assert_called_with(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml'
        )

    @mock.patch.object(Windows, 'uninstall')
    @mock.patch.object(Windows, 'validate_administrator')
    def test_uninstall_for_windows(self, validate_administrator, uninstall):
        self.system.return_value = 'Windows'
        self.uninstall._run_main(self.args, self.globals)
        validate_administrator.assert_called_with()
        uninstall.assert_called_with(self.args)
        self.remove.assert_called_with(
            r'C:\ProgramData\Amazon\CodeDeploy\conf.onpremises.yml'
        )


if __name__ == "__main__":
    unittest.main()
