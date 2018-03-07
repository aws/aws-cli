# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import mock

from awscli.testutils import BaseAWSCommandParamsTest, unittest
from botocore.compat import json
import botocore.session
from awscli.customizations.dlm.iam import IAM

from awscli.customizations.dlm.constants \
    import LIFECYCLE_DEFAULT_ROLE_NAME, \
    LIFECYCLE_DEFAULT_ROLE_ASSUME_POLICY


class TestCreateDefaultRole(BaseAWSCommandParamsTest):
    prefix = 'dlm create-default-role'
    LIFECYCLE_DEFAULT_MANAGED_POLICY_ARN = \
        "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"

    # Use case: Default role exists
    # Expected results: No Operation performed for creation,
    # only call made for verifying existence of role
    def test_default_role_exists(self):
        cmdline = self.prefix

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1)

        # Call to check if default lifecycle role exists
        self.assertEqual(self.operations_called[0][0].name, 'GetRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         LIFECYCLE_DEFAULT_ROLE_NAME)

    # Use case: Default role does not exist.
    # Managed Policy exists.
    # Expected results: Operations are performed by the client to verify
    # existence of policy, creation of role and then
    # attaching policy to role
    @mock.patch('awscli.customizations.dlm.'
                'iam.IAM.check_if_role_exists')
    def test_default_role_not_exist(self, role_exists_patch):

        role_exists_patch.return_value = False

        self.run_cmd(self.prefix, expected_rc=0)
        self.assertEqual(len(self.operations_called), 5)

        # Call to check if managed policy exists.
        self.assertEqual(self.operations_called[0][0].name, 'GetPolicy')
        self.assertEqual(self.operations_called[0][1]['PolicyArn'],
                         self.LIFECYCLE_DEFAULT_MANAGED_POLICY_ARN)

        # Call to create default role
        self.assertEqual(self.operations_called[1][0].name, 'CreateRole')
        self.assertEqual(
            self.operations_called[1][1]['RoleName'],
            LIFECYCLE_DEFAULT_ROLE_NAME
        )
        self.assertEqual(
            self.operations_called[1][1]['AssumeRolePolicyDocument'],
            json.dumps(LIFECYCLE_DEFAULT_ROLE_ASSUME_POLICY)
        )

        # Call to attach policy to role
        self.assertEqual(self.operations_called[2][0].name, 'AttachRolePolicy')
        self.assertEqual(self.operations_called[2][1]['PolicyArn'],
                         self.LIFECYCLE_DEFAULT_MANAGED_POLICY_ARN)
        self.assertEqual(self.operations_called[2][1]['RoleName'],
                         LIFECYCLE_DEFAULT_ROLE_NAME)

        # Call to get policy's default version id
        self.assertEqual(self.operations_called[3][0].name, 'GetPolicy')
        self.assertEqual(self.operations_called[3][1]['PolicyArn'],
                         self.LIFECYCLE_DEFAULT_MANAGED_POLICY_ARN)

        # Call to get detailed policy to
        # construct result with policy permissions
        self.assertEqual(self.operations_called[4][0].name, 'GetPolicyVersion')
        self.assertEqual(self.operations_called[4][1]['PolicyArn'],
                         self.LIFECYCLE_DEFAULT_MANAGED_POLICY_ARN)


class TestCreateDefaultRoleUnitTest(unittest.TestCase):

    def setUp(self):
        self.iam_client = mock.Mock()
        self.iam_client.exceptions.NoSuchEntityException = \
            botocore.session\
            .get_session()\
            .create_client('iam', region_name="us-east-1")\
            .exceptions.NoSuchEntityException
        self.iam = IAM(self.iam_client)

    def test_check_if_role_exists_raises_client_error(self):
        self.iam_client.get_role.side_effect = \
            self.iam_client.exceptions.NoSuchEntityException(
                error_response={'Error': {'Code': 'NoSuchEntityError'}},
                operation_name='GetRole',
            )

        self.assertFalse(self.iam.check_if_role_exists('role'))

    def test_check_if_policy_exists_raises_client_error(self):
        self.iam_client.get_policy.side_effect = \
            self.iam_client.exceptions.NoSuchEntityException(
                error_response={'Error': {'Code': 'NoSuchEntityError'}},
                operation_name='GetPolicy',
            )
        self.assertFalse(self.iam.check_if_policy_exists('policy'))


if __name__ == "__main__":
    unittest.main()
