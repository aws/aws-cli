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
from awscli.customizations.codedeploy.deregister import Deregister
from awscli.errorhandler import ClientError
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
        self.args.delete_iam_user = True
        self.args.no_delete_iam_user = False

        self.globals = Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = False

        self.session = MagicMock()

        self.deregister = Deregister(self.session)
        self.deregister.codedeploy = MagicMock()
        self.deregister.iam = MagicMock()

    @patch.object(
        awscli.customizations.codedeploy.deregister,
        'validate_region'
    )
    def test_run_main_throws_on_invalid_region(self, validate_region):
        validate_region.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.deregister._run_main(self.args, self.globals)
        validate_region.assert_called_with(self.globals, self.session)

    @patch.object(
        awscli.customizations.codedeploy.deregister,
        'validate_instance_name'
    )
    def test_run_main_throws_on_invalid_instance_name(
        self, validate_instance_name
    ):
        validate_instance_name.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.deregister._run_main(self.args, self.globals)
        validate_instance_name.assert_called_with(self.args)

    def test_run_main_throws_on_invalid_delete_iam_user(self):
        self.deregister._validate_delete_iam_user = MagicMock()
        self.deregister._validate_delete_iam_user.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError) as error:
            self.deregister._run_main(self.args, self.globals)
        self.deregister._validate_delete_iam_user.assert_called_with(self.args)

    def test_run_main_creates_clients(self):
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

    def test_run_main_with_tags(self):
        self.args.tags = self.tags
        self.deregister._get_instance_info = MagicMock()
        self.deregister._remove_tags = MagicMock()
        self.deregister._deregister_instance = MagicMock()
        self.deregister._delete_user_policy = MagicMock()
        self.deregister._delete_access_key = MagicMock()
        self.deregister._delete_iam_user = MagicMock()
        self.deregister._run_main(self.args, self.globals)
        self.deregister._get_instance_info.assert_called_with(self.args)
        self.deregister._remove_tags.assert_called_with(self.args)
        self.deregister._deregister_instance.assert_called_with(self.args)

    def test_run_main_with_no_tags(self):
        self.args.tags = []
        self.deregister._get_instance_info = MagicMock()
        self.deregister._remove_tags = MagicMock()
        self.deregister._deregister_instance = MagicMock()
        self.deregister._delete_user_policy = MagicMock()
        self.deregister._delete_access_key = MagicMock()
        self.deregister._delete_iam_user = MagicMock()
        self.deregister._run_main(self.args, self.globals)
        self.deregister._get_instance_info.assert_called_with(self.args)
        self.assertFalse(self.deregister._remove_tags.called)
        self.deregister._deregister_instance.assert_called_with(self.args)

    def test_run_main_with_delete_iam_user(self):
        self.args.tags = []
        self.args.delete_iam_user = True
        self.args.no_delete_iam_user = False
        self.deregister._get_instance_info = MagicMock()
        self.deregister._remove_tags = MagicMock()
        self.deregister._deregister_instance = MagicMock()
        self.deregister._delete_user_policy = MagicMock()
        self.deregister._delete_access_key = MagicMock()
        self.deregister._delete_iam_user = MagicMock()
        self.deregister._run_main(self.args, self.globals)
        self.deregister._get_instance_info.assert_called_with(self.args)
        self.deregister._deregister_instance.assert_called_with(self.args)
        self.deregister._delete_user_policy.assert_called_with(self.args)
        self.deregister._delete_access_key.assert_called_with(self.args)
        self.deregister._delete_iam_user.assert_called_with(self.args)

    def test_run_main_with_no_delete_iam_user(self):
        self.args.tags = []
        self.args.delete_iam_user = False
        self.args.no_delete_iam_user = True
        self.deregister._get_instance_info = MagicMock()
        self.deregister._remove_tags = MagicMock()
        self.deregister._deregister_instance = MagicMock()
        self.deregister._delete_user_policy = MagicMock()
        self.deregister._delete_access_key = MagicMock()
        self.deregister._delete_iam_user = MagicMock()
        self.deregister._run_main(self.args, self.globals)
        self.deregister._get_instance_info.assert_called_with(self.args)
        self.deregister._deregister_instance.assert_called_with(self.args)
        self.assertFalse(self.deregister._delete_user_policy.called)
        self.assertFalse(self.deregister._delete_access_key.called)
        self.assertFalse(self.deregister._delete_iam_user.called)

    def test_validate_delete_iam_user(self):
        self.args.delete_iam_user = False
        self.args.no_delete_iam_user = False
        self.deregister._validate_delete_iam_user(self.args)
        self.assertTrue(self.args.delete_iam_user)

    def test_validate_delete_iam_user_and_no_delete_iam_user(self):
        self.args.delete_iam_user = True
        self.args.no_delete_iam_user = True
        with self.assertRaises(RuntimeError) as error:
            self.deregister._validate_delete_iam_user(self.args)

    def test_get_instance_info_with_tags(self):
        self.deregister.codedeploy.get_on_premises_instance.return_value = {
            'instanceInfo': {
                'iamUserArn': self.iam_user_arn,
                'tags': self.tags
            }
        }
        self.deregister._get_instance_info(self.args)
        self.deregister.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.assertIn('iam_user_arn', self.args)
        self.assertIn('user_name', self.args)
        self.assertIn('tags', self.args)
        self.assertEquals(self.tags, self.args.tags)

    def test_get_instance_info_with_no_tags(self):
        self.deregister.codedeploy.get_on_premises_instance.return_value = {
            'instanceInfo': {
                'iamUserArn': self.iam_user_arn,
                'tags': None
            }
        }
        self.deregister._get_instance_info(self.args)
        self.deregister.codedeploy.get_on_premises_instance.assert_called_with(
            instanceName=self.instance_name
        )
        self.assertIn('iam_user_arn', self.args)
        self.assertIn('user_name', self.args)
        self.assertIn('tags', self.args)
        self.assertEquals(None, self.args.tags)

    def test_user_name(self):
        self.assertTrue(
            self.instance_name,
            self.deregister._user_name(self.iam_user_arn)
        )

    def test_remove_tags(self):
        self.args.tags = self.tags
        self.deregister._remove_tags(self.args)
        self.deregister.codedeploy.remove_tags_from_on_premises_instances.\
            assert_called_with(
                tags=self.tags,
                instanceNames=[self.instance_name]
            )

    def test_deregister_instance(self):
        self.deregister._deregister_instance(self.args)
        self.deregister.codedeploy.deregister_on_premises_instance.\
            assert_called_with(
                instanceName=self.instance_name
            )

    def test_delete_user_policy(self):
        self.args.user_name = self.instance_name
        list_user_policies = MagicMock()
        list_user_policies.paginate.return_value = [
            {'PolicyNames': [self.policy_name]}
        ]
        self.deregister.iam.get_paginator.return_value = list_user_policies
        self.deregister._delete_user_policy(self.args)
        self.deregister.iam.get_paginator.assert_called_with(
            'list_user_policies'
        )
        list_user_policies.paginate.assert_called_with(
            UserName=self.args.user_name
        )
        self.deregister.iam.delete_user_policy.assert_called_with(
            UserName=self.args.user_name,
            PolicyName=self.policy_name
        )

    def test_delete_user_policy_with_no_such_entity(self):
        self.args.user_name = self.instance_name
        list_user_policies = MagicMock()
        list_user_policies.paginate.return_value = [
            {'PolicyNames': [self.policy_name]}
        ]
        self.deregister.iam.get_paginator.return_value = list_user_policies
        self.deregister.iam.delete_user_policy.side_effect = ClientError(
            error_code='NoSuchEntity',
            error_message='NoSuchEntity',
            error_type='NoSuchEntity',
            operation_name='DeleteUser',
            http_status_code=400
        )
        self.deregister._delete_user_policy(self.args)
        self.deregister.iam.get_paginator.assert_called_with(
            'list_user_policies'
        )
        list_user_policies.paginate.assert_called_with(
            UserName=self.args.user_name
        )
        self.deregister.iam.delete_user_policy.assert_called_with(
            UserName=self.args.user_name,
            PolicyName=self.policy_name
        )

    def test_delete_access_key(self):
        self.args.user_name = self.instance_name
        list_access_keys = MagicMock()
        list_access_keys.paginate.return_value = [
            {'AccessKeyMetadata': [{'AccessKeyId': self.access_key_id}]}
        ]
        self.deregister.iam.get_paginator.return_value = list_access_keys
        self.deregister._delete_access_key(self.args)
        self.deregister.iam.get_paginator.assert_called_with(
            'list_access_keys'
        )
        list_access_keys.paginate.assert_called_with(
            UserName=self.args.user_name
        )
        self.deregister.iam.delete_access_key.assert_called_with(
            UserName=self.args.user_name,
            AccessKeyId=self.access_key_id
        )

    def test_delete_access_key_with_no_such_entity(self):
        self.args.user_name = self.instance_name
        list_access_keys = MagicMock()
        list_access_keys.paginate.return_value = [
            {'AccessKeyMetadata': [{'AccessKeyId': self.access_key_id}]}
        ]
        self.deregister.iam.get_paginator.return_value = list_access_keys
        self.deregister.iam.delete_access_key.side_effect = ClientError(
            error_code='NoSuchEntity',
            error_message='NoSuchEntity',
            error_type='NoSuchEntity',
            operation_name='DeleteAccessKey',
            http_status_code=400
        )
        self.deregister._delete_access_key(self.args)
        self.deregister.iam.get_paginator.assert_called_with(
            'list_access_keys'
        )
        list_access_keys.paginate.assert_called_with(
            UserName=self.args.user_name
        )
        self.deregister.iam.delete_access_key.assert_called_with(
            UserName=self.args.user_name,
            AccessKeyId=self.access_key_id
        )

    def test_delete_iam_user(self):
        self.args.user_name = self.instance_name
        self.deregister._delete_iam_user(self.args)
        self.deregister.iam.delete_user.assert_called_with(
            UserName=self.args.user_name
        )

    def test_delete_iam_user_with_no_such_entity(self):
        self.args.user_name = self.instance_name
        self.deregister.iam.delete_user.side_effect = ClientError(
            error_code='NoSuchEntity',
            error_message='NoSuchEntity',
            error_type='NoSuchEntity',
            operation_name='DeleteUser',
            http_status_code=400
        )
        self.deregister._delete_iam_user(self.args)
        self.deregister.iam.delete_user.assert_called_with(
            UserName=self.args.user_name
        )


if __name__ == "__main__":
    unittest.main()
