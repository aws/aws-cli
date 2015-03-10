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

from argparse import Namespace
from awscli.customizations.codedeploy.register import Register
from awscli.customizations.codedeploy.utils import MAX_TAGS_PER_INSTANCE
from awscli.testutils import unittest
from mock import MagicMock, patch, call, mock_open


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.path = '/AWS/CodeDeploy/'
        self.instance_name = 'instance-name'
        self.tags = [{'Key': 'k1', 'Value': 'v1'}]
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/instance-name'
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

        self.globals = Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = False

        self.open_patcher = patch(
            'awscli.customizations.codedeploy.register.open',
            mock_open(), create=True
        )
        self.open = self.open_patcher.start()

        self.codedeploy = MagicMock()

        self.iam = MagicMock()
        self.iam.create_user.return_value = {
            'User': {'Arn': self.iam_user_arn}
        }
        self.iam.create_access_key.return_value = {
            'AccessKey': {
                'AccessKeyId': self.access_key_id,
                'SecretAccessKey': self.secret_access_key
            }
        }

        self.session = MagicMock()
        self.session.create_client.side_effect = [self.codedeploy, self.iam]
        self.register = Register(self.session)

    def tearDown(self):
        self.open_patcher.stop()

    def test_register_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        with self.assertRaisesRegexp(RuntimeError, 'Region not specified.'):
            self.register._run_main(self.args, self.globals)

    def test_register_throws_on_invalid_instance_name(self):
        self.args.instance_name = 'invalid%@^&%#&'
        with self.assertRaisesRegexp(
                ValueError, 'Instance name contains invalid characters.'):
            self.register._run_main(self.args, self.globals)

    def test_register_throws_on_invalid_tags(self):
        self.args.tags = [
            {'Key': 'k' + str(x), 'Value': 'v' + str(x)} for x in range(11)
        ]
        with self.assertRaisesRegexp(
                ValueError,
                'Instances can only have a maximum of {0} tags.'.format(
                    MAX_TAGS_PER_INSTANCE)):
            self.register._run_main(self.args, self.globals)

    def test_register_throws_on_invalid_iam_user_arn(self):
        self.args.iam_user_arn = 'invalid%@^&%#&'
        with self.assertRaisesRegexp(ValueError, 'Invalid IAM user ARN.'):
            self.register._run_main(self.args, self.globals)

    def test_register_creates_clients(self):
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

    def test_register_with_no_iam_user_arn(self):
        self.args.iam_user_arn = None
        self.register._run_main(self.args, self.globals)
        self.register.iam.create_user.assert_called_with(
            Path=self.path,
            UserName=self.instance_name
        )
        self.assertIn('iam_user_arn', self.args)
        self.assertEqual(self.iam_user_arn, self.args.iam_user_arn)
        self.register.iam.create_access_key.assert_called_with(
            UserName=self.instance_name
        )
        self.assertIn('access_key_id', self.args)
        self.assertEqual(self.access_key_id, self.args.access_key_id)
        self.assertIn('secret_access_key', self.args)
        self.assertEqual(self.secret_access_key, self.args.secret_access_key)
        self.register.iam.put_user_policy.assert_called_with(
            UserName=self.instance_name,
            PolicyName=self.policy_name,
            PolicyDocument=self.policy_document
        )
        self.assertIn('policy_name', self.args)
        self.assertEqual(self.policy_name, self.args.policy_name)
        self.assertIn('policy_document', self.args)
        self.assertEqual(self.policy_document, self.args.policy_document)
        self.open.assert_called_with(self.config_file, 'w')
        self.open().write.assert_called_with(
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
        self.register.codedeploy.register_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name,
                iamUserArn=self.iam_user_arn
            )

    def test_register_with_iam_user_arn(self):
        self.args.iam_user_arn = self.iam_user_arn
        self.register._run_main(self.args, self.globals)
        self.assertFalse(self.register.iam.create_user.called)
        self.assertFalse(self.register.iam.create_access_key.called)
        self.assertFalse(self.register.iam.put_user_policy.called)
        self.assertFalse(self.open.called)
        self.register.codedeploy.register_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name,
                iamUserArn=self.iam_user_arn
            )

    def test_register_with_no_tags(self):
        self.args.tags = None
        self.register._run_main(self.args, self.globals)
        self.register.codedeploy.register_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name,
                iamUserArn=self.iam_user_arn
            )
        self.assertFalse(
            self.register.codedeploy.add_tags_to_on_premises_instances.called
        )

    def test_register_with_tags(self):
        self.args.tags = self.tags
        self.register._run_main(self.args, self.globals)
        self.register.codedeploy.register_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name,
                iamUserArn=self.iam_user_arn
            )
        self.register.codedeploy.add_tags_to_on_premises_instances.\
            assert_called_with(
                tags=self.tags,
                instanceNames=[self.instance_name]
            )


if __name__ == "__main__":
    unittest.main()
