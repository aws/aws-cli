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

from socket import timeout
from argparse import Namespace
from mock import MagicMock, patch
from awscli.customizations.codedeploy.systems import Ubuntu, Windows, RHEL, System
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_instance_name, validate_tags, \
    validate_iam_user_arn, validate_instance, validate_s3_location, \
    MAX_INSTANCE_NAME_LENGTH, MAX_TAGS_PER_INSTANCE, MAX_TAG_KEY_LENGTH, \
    MAX_TAG_VALUE_LENGTH
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import unittest


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/AWS/CodeDeploy/foo'
        self.region = 'us-east-1'
        self.arg_name = 's3-location'
        self.bucket = 'bucket'
        self.key = 'key'

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

        self.globals = MagicMock()
        self.session = MagicMock()
        self.params = Namespace()
        self.params.session = self.session

    def tearDown(self):
        self.system_patcher.stop()
        self.linux_distribution_patcher.stop()
        self.urlopen_patcher.stop()

    def test_validate_region_returns_global_region(self):
        self.globals.region = self.region
        self.session.get_config_variable.return_value = None
        validate_region(self.params, self.globals)
        self.assertIn('region', self.params)
        self.assertEquals(self.region, self.params.region)

    def test_validate_region_returns_session_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = self.region
        validate_region(self.params, self.globals)
        self.assertIn('region', self.params)
        self.assertEquals(self.region, self.params.region)

    def test_validate_region_throws_on_no_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        error_msg = 'Region not specified.'
        with self.assertRaisesRegexp(ConfigurationError, error_msg):
            validate_region(self.params, self.globals)

    def test_validate_instance_name(self):
        instance_name = 'instance-name'
        self.params.instance_name = instance_name
        validate_instance_name(self.params)

    def test_validate_instance_name_throws_on_invalid_characters(self):
        self.params.instance_name = '!#$%^&*()<>/?;:[{]}'
        error_msg = 'Instance name contains invalid characters.'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_instance_name(self.params)

    def test_validate_instance_name_throws_on_i_dash(self):
        self.params.instance_name = 'i-instance'
        error_msg = "Instance name cannot start with 'i-'."
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_instance_name(self.params)

    def test_validate_instance_name_throws_on_long_name(self):
        self.params.instance_name = (
            '01234567890123456789012345678901234567890123456789'
            '012345678901234567890123456789012345678901234567891'
        )
        error_msg = (
            'Instance name cannot be longer than {0} characters.'
        ).format(MAX_INSTANCE_NAME_LENGTH)
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_instance_name(self.params)

    def test_validate_tags_throws_on_too_many_tags(self):
        self.params.tags = [
            {'Key': 'k' + str(x), 'Value': 'v' + str(x)} for x in range(11)
        ]
        error_msg = (
            'Instances can only have a maximum of {0} tags.'
        ).format(MAX_TAGS_PER_INSTANCE)
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_tags(self.params)

    def test_validate_tags_throws_on_max_key_not_accepted(self):
        key = 'k' * 128
        self.params.tags = [{'Key': key, 'Value': 'v1'}]
        validate_tags(self.params)

    def test_validate_tags_throws_on_long_key(self):
        key = 'k' * 129
        self.params.tags = [{'Key': key, 'Value': 'v1'}]
        error_msg = (
            'Tag Key cannot be longer than {0} characters.'
        ).format(MAX_TAG_KEY_LENGTH)
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_tags(self.params)

    def test_validate_tags_throws_on_max_value_not_accepted(self):
        value = 'v' * 256
        self.params.tags = [{'Key': 'k1', 'Value': value}]
        validate_tags(self.params)

    def test_validate_tags_throws_on_long_value(self):
        value = 'v' * 257
        self.params.tags = [{'Key': 'k1', 'Value': value}]
        error_msg = (
            'Tag Value cannot be longer than {0} characters.'
        ).format(MAX_TAG_VALUE_LENGTH)
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_tags(self.params)

    def test_validate_iam_user_arn(self):
        self.params.iam_user_arn = self.iam_user_arn
        validate_iam_user_arn(self.params)

    def test_validate_iam_user_arn_throws_on_invalid_arn_pattern(self):
        self.params.iam_user_arn = 'invalid-arn-pattern'
        error_msg = 'Invalid IAM user ARN.'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_iam_user_arn(self.params)

    def test_validate_instance_ubuntu(self):
        self.urlopen.side_effect = timeout('Not EC2 instance')
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Ubuntu', None, None)
        self.params.session = self.session
        self.params.region = self.region
        validate_instance(self.params)
        self.assertIn('system', self.params)
        self.assertTrue(isinstance(self.params.system, Ubuntu))

    def test_validate_instance_rhel(self):
        self.urlopen.side_effect = timeout('Not EC2 instance')
        self.system.return_value = 'Linux'
        self.linux_distribution.return_value = ('Red Hat Enterprise Linux Server', None, None)
        self.params.session = self.session
        self.params.region = self.region
        validate_instance(self.params)
        self.assertIn('system', self.params)
        self.assertTrue(isinstance(self.params.system, RHEL))

    def test_validate_instance_windows(self):
        self.urlopen.side_effect = timeout('Not EC2 instance')
        self.system.return_value = 'Windows'
        self.params.session = self.session
        self.params.region = self.region
        validate_instance(self.params)
        self.assertIn('system', self.params)
        self.assertTrue(isinstance(self.params.system, Windows))

    def test_validate_instance_throws_on_unsupported_system(self):
        self.system.return_value = 'Unsupported'
        with self.assertRaisesRegexp(
                RuntimeError, System.UNSUPPORTED_SYSTEM_MSG):
            validate_instance(self.params)

    def test_validate_instance_throws_on_ec2_instance(self):
        self.params.session = self.session
        self.params.region = self.region
        self.urlopen.side_effect = None
        with self.assertRaisesRegexp(
                RuntimeError, 'Amazon EC2 instances are not supported.'):
            validate_instance(self.params)

    def test_validate_s3_location_returns_bucket_key(self):
        self.params.s3_location = 's3://{0}/{1}'.format(self.bucket, self.key)
        validate_s3_location(self.params, self.arg_name)
        self.assertIn('bucket', self.params)
        self.assertEquals(self.bucket, self.params.bucket)
        self.assertIn('key', self.params)
        self.assertEquals(self.key, self.params.key)

    def test_validate_s3_location_not_present(self):
        validate_s3_location(self.params, 'unknown')
        self.assertNotIn('bucket', self.params)
        self.assertNotIn('key', self.params)

    def test_validate_s3_location_throws_on_invalid_location(self):
        self.params.s3_location = 'invalid-s3-location'
        error_msg = (
            '--{0} must specify the Amazon S3 URL format as '
            's3://<bucket>/<key>.'
        ).format(self.arg_name)
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            validate_s3_location(self.params, self.arg_name)


if __name__ == "__main__":
    unittest.main()
