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

from argparse import Namespace
from mock import MagicMock, patch, call
from awscli.customizations.codedeploy.register import Register
from awscli.testutils import unittest


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.path = '/AWS/CodeDeploy/'
        self.instance_name = 'instance-name'
        self.tags = [{'Key': 'k1', 'Value': 'v1'}]
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/foo'
        self.access_key_id = 'ACCESSKEYID'
        self.secret_access_key = 'SECRETACCESSKEY'
        self.region = 'us-east-1'
        self.policy_name = 'codedeploy-agent'
        self.policy_document = (
            '{\n'
            '    "Version": "2012-10-17",\n'
            '    "Statement": [ {\n'
            '        "Action": [ "s3:Get*", "s3:List*" ],\n'
            '        "Effect": "Allow",\n'
            '        "Resource": "*"\n'
            '    } ]\n'
            '}'
        )
        self.config_file = 'codedeploy.onpremises.yml'
        self.endpoint_url = 'https://codedeploy.aws.amazon.com'

        self.args = Namespace()
        self.args.instance_name = self.instance_name
        self.args.tags = None
        self.args.iam_user_arn = None
        self.args.create_config = False

        self.globals = Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = False

        self.session = MagicMock()

        self.register = Register(self.session)
        self.register.codedeploy = MagicMock()
        self.register.iam = MagicMock()

    @patch.object(awscli.customizations.codedeploy.register, 'validate_region')
    def test_run_main_throws_on_invalid_region(self, validate_region):
        validate_region.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.register._run_main(self.args, self.globals)
        validate_region.assert_called_with(self.globals, self.session)

    @patch.object(
        awscli.customizations.codedeploy.register,
        'validate_instance_name'
    )
    def test_run_main_throws_on_invalid_instance_name(
        self, validate_instance_name
    ):
        validate_instance_name.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.register._run_main(self.args, self.globals)
        validate_instance_name.assert_called_with(self.args)

    def test_run_main_throws_on_invalid_tags(self):
        self.register._validate_tags = MagicMock()
        self.register._validate_tags.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.register._run_main(self.args, self.globals)
        self.register._validate_tags.assert_called_with(self.args)

    @patch.object(
        awscli.customizations.codedeploy.register,
        'validate_iam_user_arn'
    )
    def test_run_main_throws_on_invalid_iam_user_arn(
        self, validate_iam_user_arn
    ):
        validate_iam_user_arn.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.register._run_main(self.args, self.globals)
        validate_iam_user_arn.assert_called_with(self.args)

    def test_run_main_creates_clients(self):
        self.register._run_main(self.args, self.globals)
        self.session.create_client.assert_has_calls([
            call(
                'codedeploy',
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                verify=self.globals.verify_ssl
            ),
            call('iam', region_name=self.region)
        ])

    def test_run_main_with_no_iam_user_arn(self):
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.register._create_iam_user.assert_called_with(self.args)
        self.register._create_access_key.assert_called_with(self.args)
        self.register._create_user_policy.assert_called_with(self.args)
        self.register._register_instance.assert_called_with(self.args)

    def test_run_main_with_iam_user_arn(self):
        self.args.iam_user_arn = self.iam_user_arn
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.assertFalse(self.register._create_iam_user.called)
        self.assertFalse(self.register._create_access_key.called)
        self.assertFalse(self.register._create_user_policy.called)
        self.register._register_instance.assert_called_with(self.args)

    def test_run_main_with_no_tags(self):
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.register._register_instance.assert_called_with(self.args)
        self.assertFalse(self.register._add_tags.called)

    def test_run_main_with_tags(self):
        self.args.tags = self.tags
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.register._register_instance.assert_called_with(self.args)
        self.register._add_tags.assert_called_with(self.args)

    def test_run_main_with_no_create_config(self):
        self.args.create_config = False
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.register._register_instance.assert_called_with(self.args)
        self.assertFalse(self.register._create_config.called)

    def test_run_main_with_create_config(self):
        self.args.create_config = True
        self.register._create_iam_user = MagicMock()
        self.register._create_access_key = MagicMock()
        self.register._create_user_policy = MagicMock()
        self.register._register_instance = MagicMock()
        self.register._add_tags = MagicMock()
        self.register._create_config = MagicMock()
        self.register._run_main(self.args, self.globals)
        self.register._register_instance.assert_called_with(self.args)
        self.register._create_config.assert_called_with(self.args)

    def test_validate_tags_throws_on_too_many_tags(self):
        self.args.tags = [
            {'Key': 'k' + str(x), 'Value': 'v' + str(x)} for x in range(11)
        ]
        with self.assertRaises(RuntimeError) as error:
            self.register._validate_tags(self.args)

    def test_validate_tags_throws_on_long_key(self):
        key = 'k' * 129
        self.args.tags = [{'Key': key, 'Value': 'v1'}]
        with self.assertRaises(RuntimeError) as error:
            self.register._validate_tags(self.args)

    def test_validate_tags_throws_on_long_value(self):
        value = 'v' * 257
        self.args.tags = [{'Key': 'k1', 'Value': value}]
        with self.assertRaises(RuntimeError) as error:
            self.register._validate_tags(self.args)

    def test_create_iam_user_arn(self):
        self.register._create_iam_user(self.args)
        self.register.iam.create_user.return_value = {
            'User': {'Arn': self.iam_user_arn}
        }
        self.register.iam.create_user.assert_called_with(
            Path=self.path,
            UserName=self.args.instance_name
        )
        self.assertIn('iam_user_arn', self.args)

    def test_create_access_key(self):
        self.args.user_name = self.instance_name
        self.register.iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': self.access_key_id,
                'SecretAccessKey': self.secret_access_key
            }
        }
        self.register._create_access_key(self.args)
        self.register.iam.create_access_key.assert_called_with(
            UserName=self.args.user_name
        )
        self.assertIn('access_key_id', self.args)
        self.assertIn('secret_access_key', self.args)

    def test_create_user_policy(self):
        self.args.user_name = self.instance_name
        self.register._create_user_policy(self.args)
        self.register.iam.put_user_policy.assert_called_with(
            UserName=self.args.user_name,
            PolicyName=self.policy_name,
            PolicyDocument=self.policy_document
        )
        self.assertIn('policy_name', self.args)
        self.assertIn('policy_document', self.args)

    def test_register_instance(self):
        self.args.iam_user_arn = self.iam_user_arn
        self.register._register_instance(self.args)
        self.register.codedeploy.register_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name,
                iamUserArn=self.iam_user_arn
            )

    def test_add_tags(self):
        self.args.tags = self.tags
        self.register._add_tags(self.args)
        self.register.codedeploy.add_tags_to_on_premises_instances.\
            assert_called_with(
                tags=self.tags,
                instanceNames=[self.instance_name]
            )

    @patch.object(
        awscli.customizations.codedeploy.register,
        'create_config_file'
    )
    @patch.object(awscli.customizations.codedeploy.register, 'config_file')
    def test_create_config(self, config_file, create_config_file):
        config_file.return_value = self.config_file
        self.register._create_config(self.args)
        config_file.assert_called_with()
        create_config_file.assert_called_with(self.config_file, self.args)


if __name__ == "__main__":
    unittest.main()
