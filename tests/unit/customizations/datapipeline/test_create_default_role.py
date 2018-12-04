import mock
import awscli.customizations.datapipeline.createdefaultroles \
    as createdefaultroles
from awscli.customizations.datapipeline.constants\
    import DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME,\
    DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME,\
    DATAPIPELINE_DEFAULT_SERVICE_ROLE_ASSUME_POLICY,\
    DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ASSUME_POLICY

from awscli.testutils import BaseAWSCommandParamsTest,\
    unittest
from awscli.customizations.datapipeline.translator import dict_to_string
from botocore.compat import json


class TestCreateDefaultRole(BaseAWSCommandParamsTest):
    prefix = 'datapipeline create-default-roles'

    DATAPIPELINE_ROLE_POLICY = {
        "Statement": [
            {
                "Action": [
                    "cloudwatch:*",
                    "dynamodb:*",
                    "ec2:Describe*",
                    "elasticmapreduce:Describe*",
                    "rds:Describe*",
                    "s3:*",
                    "sdb:*",
                    "sns:*",
                    "sqs:*"
                    ],
                "Effect": "Allow",
                "Resource": ["*"]
                }
            ]
    }

    CREATE_DATAPIPELINE_ROLE_RESULT = {
        "Role":  {
            "AssumeRolePolicyDocument": {
                "Version": "2008-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ec2.amazonaws.com"
                        }
                    }
                ]
            },
            "RoleId": "AROAJG7O4RNNSRINMF6DI",
            "CreateDate": "2014-05-01T23:47:14.552Z",
            "RoleName": DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME,
            "Path": "/",
            "Arn": "arn:aws:iam::176430881729:role/" +
                    DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME
        }
    }

    CONSTRUCTED_RESULT_OUTPUT = [
        {
            "Role": CREATE_DATAPIPELINE_ROLE_RESULT['Role'],
            "RolePolicy": DATAPIPELINE_ROLE_POLICY
        }
    ]

    # Use case: Default roles exists
    # Expected results: No Operation performed for creation, except calls made
    # for verifying existence of roles
    def test_default_roles_exist(self):
        cmdline = self.prefix

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 3)

        self.assertEqual(self.operations_called[0][0].name, 'GetRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME)

    # Use case: Default roles do not exist
    # Expected results: Operations are performed by the client to verify
    # existence of roles and then creation of roles (Service role,
    # resource role and instance profile)
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._check_if_role_exists')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._get_role_policy')
    def test_default_roles_not_exist(self, get_rp_patch,
                                     role_exists_patch,
                                     instance_profile_exists_patch,
                                     construct_result_patch):
        get_rp_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        role_exists_patch.return_value = False
        construct_result_patch.return_value = []

        self.run_cmd(self.prefix, expected_rc=0)
        self.assertEqual(len(self.operations_called), 6)

        self.assertEqual(self.operations_called[0][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME)
        self.assertEqual(
            self.operations_called[0][1]['AssumeRolePolicyDocument'],
            dict_to_string(DATAPIPELINE_DEFAULT_SERVICE_ROLE_ASSUME_POLICY))

        self.assertEqual(self.operations_called[1][0].name,
                         'AttachRolePolicy')
        self.assertEqual(self.operations_called[1][1]['PolicyArn'],
                         (createdefaultroles.
                          DATAPIPELINE_DEFAULT_SERVICE_ROLE_ARN))
        self.assertEqual(self.operations_called[1][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME)

        self.assertEqual(self.operations_called[2][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[2][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME)
        self.assertEqual(
            self.operations_called[2][1]['AssumeRolePolicyDocument'],
            dict_to_string(DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ASSUME_POLICY))

        self.assertEqual(self.operations_called[3][0].name, 'AttachRolePolicy')
        self.assertEqual(self.operations_called[3][1]['PolicyArn'],
                         (createdefaultroles.
                          DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ARN))
        self.assertEqual(self.operations_called[3][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME)

        self.assertEqual(self.operations_called[4][0].name,
                         'CreateInstanceProfile')
        self.assertEqual(self.operations_called[4][1]['InstanceProfileName'],
                         DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME)

        self.assertEqual(self.operations_called[5][0].name,
                         'AddRoleToInstanceProfile')
        self.assertEqual(self.operations_called[5][1]['InstanceProfileName'],
                         DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME)
        self.assertEqual(self.operations_called[5][1]['RoleName'],
                         DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME)

    # Use case: Creating only DataPipeline service role
    # Expected output: The service role is created displaying a message
    # to the customer that a particular role with a policy has been created
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._get_role_policy')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._create_role_with_role_policy')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.datapipeline.'
                'CreateDefaultRoles._check_if_role_exists')
    def test_constructed_result(self, role_exists_patch,
                                instance_profile_exists_patch,
                                create_role_patch,
                                get_role_policy_patch):
        role_exists_patch.side_effect = self.toggle_for_check_if_exists
        instance_profile_exists_patch.return_value = True
        create_role_patch.return_value = self.CREATE_DATAPIPELINE_ROLE_RESULT
        get_role_policy_patch.return_value = self.DATAPIPELINE_ROLE_POLICY

        result = self.run_cmd(self.prefix, 0)
        expected_output = json.dumps(self.CONSTRUCTED_RESULT_OUTPUT,
                                     indent=4) + '\n'
        self.assertEquals(result[0], expected_output)

    def toggle_for_check_if_exists(self, *args):
        if args[0] == DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME:
            return False
        else:
            return True


if __name__ == "__main__":
    unittest.main()
