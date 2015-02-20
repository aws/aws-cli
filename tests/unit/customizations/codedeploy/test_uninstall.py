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

import awscli
import sys

from argparse import Namespace
from mock import MagicMock, patch, call
from awscli.customizations.codedeploy.uninstall import Uninstall
from awscli.testutils import unittest


class TestUninstall(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'
        self.config_dir = '/etc/codedeploy-agent/conf'
        self.config_file = 'codedeploy.onpremises.yml'
        self.config_path = '{0}/{1}'.format(self.config_dir, self.config_file)

        self.args = Namespace()
        self.globals = Namespace()

        self.session = MagicMock()

        self.uninstall = Uninstall(self.session)

    @patch.object(
        awscli.customizations.codedeploy.uninstall,
        'validate_instance'
    )
    def test_run_main_throws_on_invalid_instance(self, validate_instance):
        validate_instance.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.uninstall._run_main(self.args, self.globals)
        validate_instance.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.uninstall,
        'validate_instance'
    )
    def test_run_main(self, validate_instance):
        self.uninstall._uninstall_agent = MagicMock()
        self.uninstall._delete_config_file = MagicMock()
        self.uninstall._run_main(self.args, self.globals)
        self.uninstall._uninstall_agent.assert_called_with(self.args)
        self.uninstall._delete_config_file.assert_called_with()

    @patch('subprocess.check_call')
    def test_uninstall_agent_ubuntu(self, check_call):
        sys.platform = 'linux2'
        self.args.system = 'ubuntu'
        self.uninstall._uninstall_agent(self.args)
        check_call.assert_has_calls([
            call('sudo service codedeploy-agent stop', shell=True),
            call('sudo dpkg -r codedeploy-agent', shell=True)
        ])

    @patch('subprocess.check_call')
    def test_uninstall_agent_redhat(self, check_call):
        sys.platform = 'linux2'
        self.args.system = 'redhat'
        self.uninstall._uninstall_agent(self.args)
        check_call.assert_has_calls([
            call('sudo service codedeploy-agent stop', shell=True),
            call('sudo yum -y erase codedeploy-agent', shell=True)
        ])

    @patch('subprocess.check_call')
    def test_uninstall_agent_windows(self, check_call):
        sys.platform = 'win32'
        self.uninstall._uninstall_agent(self.args)
        check_call.assert_has_calls([
            call(
                r'wmic product where name="CodeDeploy Host Agent" call uninstall /nointeractive',
                stdout=-1,
                shell=True
            )
        ])

    @patch('os.remove')
    @patch.object(awscli.customizations.codedeploy.uninstall, 'config_path')
    def test_delete_config_file(self, config_path, remove):
        config_path.return_value = self.config_path
        self.uninstall._delete_config_file()
        remove.assert_called_with(self.config_path)


if __name__ == "__main__":
    unittest.main()
