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
from awscli.customizations.codedeploy.install import Install
from awscli.testutils import unittest


class TestInstall(unittest.TestCase):
    def setUp(self):
        self.saved_sys_platform = sys.platform
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/foo'
        self.region = 'us-east-1'
        self.config_dir = '/etc/codedeploy-agent/conf'
        self.config_file = 'codedeploy.onpremises.yml'
        self.config_path = '{0}/{1}'.format(self.config_dir, self.config_file)
        self.installer = 'install'
        self.bucket = 'aws-codedeploy-{0}'.format(self.region)
        self.key = 'latest/{0}'.format(self.installer)
        self.agent_installer = 's3://{0}/{1}'.format(self.bucket, self.key)

        self.args = Namespace()
        self.args.override_config = False
        self.args.config_file = None
        self.args.iam_user_arn = None
        self.args.agent_installer = None

        self.globals = Namespace()
        self.globals.region = self.region

        self.session = MagicMock()

        self.install = Install(self.session)

    def tearDown(self):
        sys.platform = self.saved_sys_platform

    @patch.object(awscli.customizations.codedeploy.install, 'validate_region')
    def test_run_main_throws_on_invalid_region(self, validate_region):
        validate_region.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._run_main(self.args, self.globals)
        validate_region.assert_called_with(self.globals, self.session)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_instance'
    )
    def test_run_main_throws_on_invalid_instance(self, validate_instance):
        validate_instance.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._run_main(self.args, self.globals)
        validate_instance.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_instance'
    )
    def test_run_main_throws_on_invalid_config(self, validate_instance):
        self.install._validate_config = MagicMock()
        self.install._validate_config.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._run_main(self.args, self.globals)
        self.install._validate_config.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_instance'
    )
    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_iam_user_arn'
    )
    def test_run_main_throws_on_invalid_iam_user_arn(
        self, validate_iam_user_arn, validate_instance
    ):
        validate_iam_user_arn.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._run_main(self.args, self.globals)
        validate_iam_user_arn.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_instance'
    )
    def test_run_main_throws_on_invalid_agent_installer(
        self, validate_instance
    ):
        self.install._validate_agent_installer = MagicMock()
        self.install._validate_agent_installer.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._run_main(self.args, self.globals)
        self.install._validate_agent_installer.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_instance'
    )
    def test_run_main(
        self, validate_instance
    ):
        self.install._validate_agent_installer = MagicMock()
        self.install._create_config = MagicMock()
        self.install._install_agent = MagicMock()
        self.install._run_main(self.args, self.globals)
        self.install._create_config.assert_called_with(self.args)
        self.install._install_agent.assert_called_with(self.args)

    def test_validate_config_with_installer_and_iam_user_arn(self):
        self.args.config_file = self.config_file
        self.args.iam_user_arn = self.iam_user_arn
        with self.assertRaises(RuntimeError) as error:
            self.install._validate_config(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_s3_location'
    )
    def test_validate_agent_installer_throws_on_invalid_s3_location(
        self, validate_s3_location
    ):
        validate_s3_location.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.install._validate_agent_installer(self.args)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_s3_location'
    )
    def test_validate_agent_installer_with_s3_location(
        self, validate_s3_location
    ):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.install._validate_agent_installer(self.args)
        self.assertIn('installer', self.args)
        self.assertEquals(self.installer, self.args.installer)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_s3_location'
    )
    def test_validate_agent_installer_for_linux(
        self, validate_s3_location
    ):
        sys.platform = 'linux2'
        self.args.region = self.region
        self.install._validate_agent_installer(self.args)
        self.assertIn('bucket', self.args)
        self.assertEquals(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEquals('latest/install', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEquals('install', self.args.installer)

    @patch.object(
        awscli.customizations.codedeploy.install,
        'validate_s3_location'
    )
    def test_validate_agent_installer_for_windows(
        self, validate_s3_location
    ):
        sys.platform = 'win32'
        self.args.region = self.region
        self.install._validate_agent_installer(self.args)
        self.assertIn('bucket', self.args)
        self.assertEquals(self.bucket, self.args.bucket)
        self.assertIn('key', self.args)
        self.assertEquals('latest/codedeploy-agent.msi', self.args.key)
        self.assertIn('installer', self.args)
        self.assertEquals('codedeploy-agent.msi', self.args.installer)

    @patch('os.path')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    def test_create_config_throws_on_existing_config_file(
        self, config_path, path
    ):
        config_path.return_value = self.config_file
        path.isfile.return_value = True
        with self.assertRaises(RuntimeError) as error:
            self.install._create_config(self.args)

    @patch('os.makedirs')
    @patch('os.path')
    @patch('__builtin__.raw_input')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    @patch.object(
        awscli.customizations.codedeploy.install,
        'create_config_file'
    )
    def test_create_config_with_override_existing_config_file(
        self, create_config_file, config_path, raw_input, path, makedirs
    ):
        self.args.override_config = True
        config_path.return_value = self.config_path
        path.isfile.return_value = True
        path.dirname.return_value = self
        self.install._create_config(self.args)
        create_config_file.assert_called_with(self.config_path, self.args)

    @patch('shutil.copyfile')
    @patch('os.makedirs')
    @patch('os.path')
    @patch('__builtin__.raw_input')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    @patch.object(
        awscli.customizations.codedeploy.install,
        'create_config_file'
    )
    def test_create_config_with_new_config_file(
        self, create_config_file, config_path, raw_input, path, makedirs,
        copyfile
    ):
        self.args.config_file = self.config_file
        config_path.return_value = self.config_path
        path.isfile.return_value = False
        self.install._create_config(self.args)
        copyfile.assert_called_with(self.config_file, self.config_path)

    @patch('shutil.copyfile')
    @patch('os.makedirs')
    @patch('os.path')
    @patch('__builtin__.raw_input')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    @patch.object(
        awscli.customizations.codedeploy.install,
        'create_config_file'
    )
    def test_create_config_with_same_config_file(
        self, create_config_file, config_path, raw_input, path, makedirs,
        copyfile
    ):
        self.args.config_file = self.config_path
        config_path.return_value = self.config_path
        path.isfile.return_value = False
        self.install._create_config(self.args)
        self.assertFalse(copyfile.called)

    @patch('os.makedirs')
    @patch('os.path')
    @patch('__builtin__.raw_input')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    @patch.object(
        awscli.customizations.codedeploy.install,
        'create_config_file'
    )
    def test_create_config_with_iam_user_arn(
        self, create_config_file, config_path, raw_input, path, makedirs,
    ):
        self.args.iam_user_arn = self.iam_user_arn
        config_path.return_value = self.config_path
        path.isfile.return_value = False
        self.install._create_config(self.args)
        raw_input.assert_has_calls([
            call('Enter Access Key ID: '),
            call('Enter Secret Access Key: ')
        ])
        create_config_file.assert_called_with(self.config_path, self.args)
        self.assertIn('access_key_id', self.args)
        self.assertIn('secret_access_key', self.args)

    @patch('os.makedirs')
    @patch('os.path')
    @patch('__builtin__.raw_input')
    @patch.object(awscli.customizations.codedeploy.install, 'config_path')
    @patch.object(
        awscli.customizations.codedeploy.install,
        'create_config_file'
    )
    def test_create_config_with_no_iam_user_arn(
        self, create_config_file, config_path, raw_input, path, makedirs,
    ):
        config_path.return_value = self.config_path
        path.isfile.return_value = False
        self.install._create_config(self.args)
        raw_input.assert_has_calls([
            call('Enter IAM User ARN: '),
            call('Enter Access Key ID: '),
            call('Enter Secret Access Key: ')
        ])
        create_config_file.assert_called_with(self.config_path, self.args)
        self.assertIn('access_key_id', self.args)
        self.assertIn('secret_access_key', self.args)

    @patch('subprocess.check_call')
    def test_install_agent_ubuntu(self, check_call):
        sys.platform = 'linux2'
        self.args.system = 'ubuntu'
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.args.installer = self.installer
        self.args.region = self.region
        self.install._install_agent(self.args)
        check_call.assert_has_calls([
            call('sudo apt-get -y update', shell=True),
            call('sudo apt-get -y install ruby2.0', shell=True),
            call(
                'sudo service codedeploy-agent stop',
                stdout=-1,
                stderr=-1,
                shell=True
            ),
            call(
                'aws s3 cp s3://{0}/{1} ./{2} --region {3}'.format(
                    self.bucket,
                    self.key,
                    self.installer,
                    self.region
                ),
                shell=True
            ),
            call('sudo chmod +x ./{0}'.format(self.installer), shell=True),
            call('sudo ./{0} auto'.format(self.installer), shell=True)
        ])

    @patch('subprocess.check_call')
    def test_install_agent_redhat(self, check_call):
        sys.platform = 'linux2'
        self.args.system = 'redhat'
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.args.installer = self.installer
        self.args.region = self.region
        self.install._install_agent(self.args)
        check_call.assert_has_calls([
            call('sudo yum -y update', shell=True),
            call(
                'sudo service codedeploy-agent stop',
                stdout=-1,
                stderr=-1,
                shell=True
            ),
            call(
                'aws s3 cp s3://{0}/{1} ./{2} --region {3}'.format(
                    self.bucket,
                    self.key,
                    self.installer,
                    self.region
                ),
                shell=True
            ),
            call('sudo chmod +x ./{0}'.format(self.installer), shell=True),
            call('sudo ./{0} auto'.format(self.installer), shell=True)
        ])

    @patch('subprocess.check_call')
    @patch('subprocess.Popen')
    def test_install_agent_windows(self, popen, check_call):
        sys.platform = 'win32'
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.args.installer = self.installer
        self.args.region = self.region

        check_call.return_value.returncode = 0
        popen.return_value.returncode = 0
        popen.return_value.communicate.return_value = ["Running", None]

        self.install._install_agent(self.args)

        check_call.assert_has_calls([
            call(
                r'powershell.exe -Command New-Item'
                r' -Path "c:\temp"'
                r' -ItemType Directory'
                r' -Force',
                shell=True
            ),
            call(
                r'powershell.exe -Command Read-S3Object'
                r' -BucketName {0} -Key {1}'
                r' -File c:\temp\{2}'.format(
                    self.bucket,
                    self.key,
                    self.installer
                ),
                shell=True
            ),
            call(
                r'c:\temp\{0}'
                r' /quiet'
                r' /l c:\temp\codedeploy-agent-install-log.txt'.format(
                    self.installer
                ),
                shell=True
            ),
            call(
                'powershell.exe -Command Restart-Service'
                ' -Name codedeployagent',
                shell=True
            )
        ])

        stop_args = ["powershell.exe", "-Command", "Stop-Service", "-Name", "codedeployagent"]
        get_args = ["powershell.exe", "-Command", "Get-Service", "-Name", "codedeployagent"]
        popen.assert_has_calls([
            call(stop_args, stdout=-1, stderr=-1, shell=True),
            call(get_args, stdout=-1, stderr=-1, shell=True),
            call().communicate()
        ])


if __name__ == "__main__":
    unittest.main()
