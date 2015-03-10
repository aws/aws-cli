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
from mock import MagicMock, call
from awscli.customizations.codedeploy.deregister import Deregister
from awscli.testutils import unittest


class TestDeregister(unittest.TestCase):
    def setUp(self):
        self.instance_name = 'instance-name'
        self.tags = [{'Key': 'k1', 'Value': 'v1'}]
        self.iam_user_arn = 'arn:aws:iam::012345678912:user/{0}'.format(
            self.instance_name
        )
        self.access_key_id = 'ACCESSKEYID'
        self.region = 'us-east-1'
        self.policy_name = 'codedeploy-agent'
        self.endpoint_url = 'https://codedeploy.aws.amazon.com'

        self.args = Namespace()
        self.args.instance_name = self.instance_name
        self.args.no_delete_iam_user = False

        self.globals = Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = False

        self.codedeploy = MagicMock()
        self.codedeploy.get_on_premises_instance.return_value = {
            'instanceInfo': {
                'iamUserArn': self.iam_user_arn,
                'tags': None
            }
        }

        self.iam = MagicMock()
        self.list_user_policies = MagicMock()
        self.list_user_policies.paginate.return_value = [
            {'PolicyNames': [self.policy_name]}
        ]
        self.list_access_keys = MagicMock()
        self.list_access_keys.paginate.return_value = [
            {'AccessKeyMetadata': [{'AccessKeyId': self.access_key_id}]}
        ]
        self.iam.get_paginator.side_effect = [
            self.list_user_policies, self.list_access_keys
        ]

        self.session = MagicMock()
        self.session.create_client.side_effect = [self.codedeploy, self.iam]
        self.deregister = Deregister(self.session)

    def test_deregister_throws_on_invalid_region(self):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        with self.assertRaisesRegexp(RuntimeError, 'Region not specified.'):
            self.deregister._run_main(self.args, self.globals)

    def test_deregister_throws_on_invalid_instance_name(self):
        self.args.instance_name = 'invalid%@^&%#&'
        with self.assertRaisesRegexp(
                ValueError, 'Instance name contains invalid characters.'):
            self.deregister._run_main(self.args, self.globals)

    def test_deregister_creates_clients(self):
        self.deregister._run_main(self.args, self.globals)
        self.session.create_client.assert_has_calls([
            call(
                'codedeploy',
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                verify=self.globals.verify_ssl
            ),
            call('iam', region_name=self.region)
        ])

    def test_deregister_with_tags(self):
        self.codedeploy.get_on_premises_instance.return_value = {
            'instanceInfo': {
                'iamUserArn': self.iam_user_arn,
                'tags': self.tags
            }
        }
        self.deregister._run_main(self.args, self.globals)
        self.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.assertIn('iam_user_arn', self.args)
        self.assertEquals(self.iam_user_arn, self.args.iam_user_arn)
        self.assertIn('user_name', self.args)
        self.assertEquals(self.instance_name, self.args.user_name)
        self.assertIn('tags', self.args)
        self.assertEquals(self.tags, self.args.tags)
        self.codedeploy.remove_tags_from_on_premises_instances.\
            assert_called_with(
                tags=self.tags,
                instanceNames=[self.instance_name]
            )
        self.codedeploy.deregister_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name
            )

    def test_deregister_with_no_tags(self):
        self.codedeploy.get_on_premises_instance.return_value = {
            'instanceInfo': {
                'iamUserArn': self.iam_user_arn,
                'tags': None
            }
        }
        self.deregister._run_main(self.args, self.globals)
        self.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.assertIn('iam_user_arn', self.args)
        self.assertEquals(self.iam_user_arn, self.args.iam_user_arn)
        self.assertIn('user_name', self.args)
        self.assertEquals(self.instance_name, self.args.user_name)
        self.assertIn('tags', self.args)
        self.assertEquals(None, self.args.tags)
        self.assertFalse(
            self.codedeploy.remove_tags_from_on_premises_instances.called
        )
        self.codedeploy.deregister_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name
            )

    def test_deregister_with_delete_iam_user(self):
        self.args.no_delete_iam_user = False
        self.deregister._run_main(self.args, self.globals)
        self.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.codedeploy.deregister_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name
            )
        self.iam.get_paginator.assert_has_calls([
            call('list_user_policies'),
            call('list_access_keys')
        ])
        self.list_user_policies.paginate.assert_called_with(
            UserName=self.instance_name
        )
        self.iam.delete_user_policy.assert_called_with(
            UserName=self.instance_name,
            PolicyName=self.policy_name
        )
        self.list_access_keys.paginate.assert_called_with(
            UserName=self.instance_name
        )
        self.iam.delete_access_key.assert_called_with(
            UserName=self.instance_name,
            AccessKeyId=self.access_key_id
        )
        self.iam.delete_user.assert_called_with(
            UserName=self.instance_name
        )

    def test_deregister_with_no_delete_iam_user(self):
        self.args.no_delete_iam_user = True
        self.deregister._run_main(self.args, self.globals)
        self.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.codedeploy.deregister_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name
            )
        self.assertFalse(self.iam.get_paginator.called)
        self.assertFalse(self.list_user_policies.paginate.called)
        self.assertFalse(self.iam.delete_user_policy.called)
        self.assertFalse(self.list_access_keys.paginate.called)
        self.assertFalse(self.iam.delete_access_key.called)
        self.assertFalse(self.iam.delete_user.called)


if __name__ == "__main__":
    unittest.main()
