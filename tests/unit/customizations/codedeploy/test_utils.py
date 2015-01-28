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

import awscli.compat
import sys

from socket import timeout
from argparse import Namespace
from mock import MagicMock, patch, mock_open
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_instance_name, validate_s3_location, \
    validate_iam_user_arn, validate_instance, config_file, config_path, \
    create_config_file
from awscli.testutils import unittest


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.saved_sys_platform = sys.platform
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/foo'
        self.access_key_id = 'ACCESSKEYID'
        self.secret_access_key = 'SECRETACCESSKEY'
        self.region = 'us-east-1'
        self.arg_name = 's3-location'
        self.bucket = 'bucket'
        self.key = 'key'

        self.globals = MagicMock()
        self.session = MagicMock()
        self.args = Namespace()

    def tearDown(self):
        sys.platform = self.saved_sys_platform

    def test_validate_region_returns_global_region(self):
        self.globals.region = self.region
        self.session.get_config_variable.return_value = None
        region = validate_region(self.globals, self.session)
        self.assertEquals(self.region, region)

    def test_validate_region_returns_session_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = self.region
        region = validate_region(self.globals, self.session)
        self.assertEquals(self.region, region)

    def test_validate_region_throws_on_no_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        with self.assertRaises(RuntimeError) as error:
            validate_region(self.globals, self.session)

    def test_validate_instance_name(self):
        instance_name = 'instance-name'
        self.args.instance_name = instance_name
        validate_instance_name(self.args)

    def test_validate_instance_name_throws_on_invalid_characters(self):
        self.args.instance_name = '!#$%^&*()<>/?;:[{]}'
        with self.assertRaises(RuntimeError) as error:
            validate_instance_name(self.args)

    def test_validate_instance_name_throws_on_i_dash(self):
        self.args.instance_name = 'i-instance'
        with self.assertRaises(RuntimeError) as error:
            validate_instance_name(self.args)

    def test_validate_instance_name_throws_on_long_name(self):
        self.args.instance_name = (
            '01234567890123456789012345678901234567890123456789'
            '012345678901234567890123456789012345678901234567891'
        )
        with self.assertRaises(RuntimeError) as error:
            validate_instance_name(self.args)

    def test_s3_location_returns_bucket_key(self):
        self.args.s3_location = 's3://{0}/{1}'.format(self.bucket, self.key)
        validate_s3_location(self.args, self.arg_name)
        self.assertIn('bucket', self.args)
        self.assertIn('key', self.args)
        self.assertEquals(self.bucket, self.args.bucket)
        self.assertEquals(self.key, self.args.key)

    def test_validate_s3_location_not_present(self):
        validate_s3_location(self.args, 'unknown')
        self.assertNotIn('bucket', self.args)
        self.assertNotIn('key', self.args)

    def test_validate_s3_location_throws_on_invalid_location(self):
        self.args.s3_location = 'invalid-s3-location'
        with self.assertRaises(RuntimeError) as error:
            validate_s3_location(self.args, self.arg_name)

    def test_validate_iam_user_arn(self):
        self.args.iam_user_arn = self.iam_user_arn
        validate_iam_user_arn(self.args)

    def test_validate_iam_user_arn_throws_on_invalid_characters(self):
        self.args.iam_user_arn = '!#$%^&*()<>/?;:[{]}'
        with self.assertRaises(RuntimeError) as error:
            validate_iam_user_arn(self.args)

    def test_validate_iam_user_arn_throws_on_invalid_arn_pattern(self):
        self.args.iam_user_arn = 'invalid-arn-pattern'
        with self.assertRaises(RuntimeError) as error:
            validate_iam_user_arn(self.args)

    @patch('platform.linux_distribution')
    @patch.object(awscli.customizations.codedeploy.utils, 'urlopen')
    def test_validate_instance_ubuntu(self, urlopen, distribution):
        urlopen.side_effect = timeout('Not EC2 instance')
        sys.platform = 'linux2'
        distribution.return_value = ('Ubuntu', None, None)
        validate_instance(self.args)
        self.assertIn('system', self.args)
        self.assertEquals('ubuntu', self.args.system)

    @patch('platform.linux_distribution')
    @patch.object(awscli.customizations.codedeploy.utils, 'urlopen')
    def test_validate_instance_redhat(self, urlopen, distribution):
        urlopen.side_effect = timeout('Not EC2 instance')
        sys.platform = 'linux2'
        distribution.return_value = ('Red Hat', None, None)
        validate_instance(self.args)
        self.assertIn('system', self.args)
        self.assertEquals('redhat', self.args.system)

    @patch.object(awscli.customizations.codedeploy.utils, 'urlopen')
    def test_validate_instance_windows(self, urlopen):
        urlopen.side_effect = timeout('Not EC2 instance')
        sys.platform = 'win32'
        validate_instance(self.args)
        self.assertIn('system', self.args)
        self.assertEquals('windows', self.args.system)

    def test_validate_instance_unknown(self):
        sys.platform = 'unknown'
        with self.assertRaises(RuntimeError) as error:
            validate_instance(self.args)

    @patch.object(awscli.customizations.codedeploy.utils, 'urlopen')
    def test_validate_instance_ec2(self, urlopen):
        urlopen.return_value = MagicMock()
        with self.assertRaises(RuntimeError) as error:
            validate_instance(self.args)

    def test_config_file_linux(self):
        sys.platform = 'linux2'
        self.assertEqual('codedeploy.onpremises.yml', config_file())

    def test_config_file_windows(self):
        sys.platform = 'win32'
        self.assertEqual('conf.onpremises.yml', config_file())

    def test_config_path_linux(self):
        sys.platform = 'linux2'
        self.assertEqual(
            '/etc/codedeploy-agent/conf/codedeploy.onpremises.yml',
            config_path()
        )

    def test_config_path_windows(self):
        sys.platform = 'win32'
        self.assertEqual(
            'C:\ProgramData\Amazon\CodeDeploy\conf.onpremises.yml',
            config_path()
        )

    def test_create_config(self):
        with patch(
            'awscli.customizations.codedeploy.utils.open',
            mock_open(),
            create=True
        ) as open_mock:
            path = 'configfile'
            self.args.region = self.region
            self.args.iam_user_arn = self.iam_user_arn
            self.args.access_key_id = self.access_key_id
            self.args.secret_access_key = self.secret_access_key
            create_config_file(path, self.args)
            open_mock.assert_called_once_with(path, 'w')
            open_mock().write.assert_called_with(
                '---\n'
                'region: {0}\n'
                'iam_user_arn: {1}\n'
                'aws_access_key_id: {2}\n'
                'aws_secret_access_key: {3}\n'.format(
                    self.region,
                    self.iam_user_arn,
                    self.access_key_id,
                    self.secret_access_key
                )
            )


if __name__ == "__main__":
    unittest.main()
