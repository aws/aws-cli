# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import awscli.customizations.emr.emrutils as emrutils
from botocore.compat import json
from botocore.vendored import requests
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


EC2_ROLE_NAME = "EMR_EC2_DefaultRole"
EMR_ROLE_NAME = "EMR_DefaultRole"

EC2_ROLE_POLICY = {
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

CREATE_EC2_ROLE_RESULT = {
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
        "RoleName": EC2_ROLE_NAME,
        "Path": "/",
        "Arn": "arn:aws:iam::176430881729:role/"+EC2_ROLE_NAME
    }
}

CONSTRUCTED_RESULT_OUTPUT = [
    {
        "Role": CREATE_EC2_ROLE_RESULT['Role'],
        "RolePolicy": EC2_ROLE_POLICY
    }
]

http_response = requests.models.Response()
http_response.status_code = 200


class TestCreateDefaultRole(BaseAWSCommandParamsTest):
    prefix = 'emr create-default-roles'

    ec2_role_policy_document = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com.cn"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    emr_role_policy_document = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "elasticmapreduce.amazonaws.com.cn"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    def test_default_roles_exist(self):
        cmdline = self.prefix

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 3)

        self.assertEqual(self.operations_called[0][0].name, 'GetRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         EC2_ROLE_NAME)

        self.assertEqual(self.operations_called[1][0].name,
                         'GetInstanceProfile')
        self.assertEqual(self.operations_called[1][1]['InstanceProfileName'],
                         EC2_ROLE_NAME)
        self.assertEqual(self.operations_called[2][0].name, 'GetRole')
        self.assertEqual(self.operations_called[2][1]['RoleName'],
                         EMR_ROLE_NAME)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_role_exists')
    def test_default_roles_not_exist(self, role_exists_patch,
                                     instance_profile_exists_patch,
                                     construct_result_patch):
        role_exists_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        construct_result_patch.return_value = []

        cmdline = self.prefix + ' --region cn-north-1'
        self.run_cmd(cmdline, expected_rc=0)

        # Only 6 operations will be called as we are mocking
        # _check_if_role_exists and _check_if_instance_profile_exists methods.
        self.assertEqual(len(self.operations_called), 6)

        self.assertEqual(self.operations_called[0][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         EC2_ROLE_NAME)
        self.assertEqual(
            self.operations_called[0][1]['AssumeRolePolicyDocument'],
            emrutils.dict_to_string(self.ec2_role_policy_document))

        self.assertEqual(self.operations_called[1][0].name,
                         'PutRolePolicy')
        self.assertEqual(self.operations_called[1][1]['PolicyDocument'],
                         emrutils.dict_to_string(EC2_ROLE_POLICY))
        self.assertEqual(self.operations_called[1][1]['PolicyName'],
                         EC2_ROLE_NAME)
        self.assertEqual(self.operations_called[1][1]['RoleName'],
                         EC2_ROLE_NAME)

        self.assertEqual(self.operations_called[2][0].name,
                         'CreateInstanceProfile')
        self.assertEqual(self.operations_called[2][1]['InstanceProfileName'],
                         EC2_ROLE_NAME)

        self.assertEqual(self.operations_called[3][0].name,
                         'AddRoleToInstanceProfile')
        self.assertEqual(self.operations_called[3][1]['InstanceProfileName'],
                         EC2_ROLE_NAME)
        self.assertEqual(self.operations_called[3][1]['RoleName'],
                         EC2_ROLE_NAME)

        self.assertEqual(self.operations_called[4][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[4][1]['RoleName'],
                         EMR_ROLE_NAME)
        self.assertEqual(
            self.operations_called[4][1]['AssumeRolePolicyDocument'],
            emrutils.dict_to_string(self.emr_role_policy_document))

        self.assertEqual(self.operations_called[5][0].name, 'PutRolePolicy')
        self.assertEqual(self.operations_called[5][1]['PolicyName'],
                         EMR_ROLE_NAME)
        self.assertEqual(self.operations_called[5][1]['RoleName'],
                         EMR_ROLE_NAME)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.emr.createdefaultroles'
                '.get_service_principal')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_role_exists')
    def test_get_service_principal_parameters(self, role_exists_patch,
                                              instance_profile_exists_patch,
                                              get_sp_patch,
                                              construct_result_patch):
        get_sp_patch.return_value = 'elasticmapreduce.amazonaws.abc'
        role_exists_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        construct_result_patch.return_value = []

        endpoint_url = 'https://elasticmapreduce.abc'
        cmdline = self.prefix + ' --endpoint ' + endpoint_url
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEquals(get_sp_patch.call_args[0][1], endpoint_url)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters(self, call_patch):
        cmdline = self.prefix + ' --region eu-west-1' + ' --no-verify-ssl'
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEquals(call_patch.call_args[0][1], 'eu-west-1')
        self.assertEquals(call_patch.call_args[0][3], False)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters_only_endpoint(self, call_patch):
        endpoint_arg = 'https://elasticmapreduce.us-unknown-1.amazonaws.com'
        cmdline = self.prefix + ' --endpoint ' + endpoint_arg
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEquals(call_patch.call_args[0][2], None)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters_only_iam_endpoint(self, call_patch):
        endpoint_arg = 'https://elasticmapreduce.us-unknown-1.amazonaws.com'
        cmdline = self.prefix + ' --iam-endpoint ' + endpoint_arg
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEquals(call_patch.call_args[0][2], endpoint_arg)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._create_role_with_role_policy')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._check_if_role_exists')
    def test_constructed_result(self, role_exists_patch,
                                instance_profile_exists_patch,
                                create_role_patch):
        role_exists_patch.side_effect = side_effect_of_check_if_role_exists
        instance_profile_exists_patch.return_value = False
        create_role_patch.return_value = (http_response,
                                          CREATE_EC2_ROLE_RESULT)

        cmdline = self.prefix + ' --region cn-north-1'
        result = self.run_cmd(cmdline, 0)
        expected_output = json.dumps(CONSTRUCTED_RESULT_OUTPUT, indent=4) +\
            '\n'
        self.assertEquals(result[0], expected_output)


def side_effect_of_check_if_role_exists(*args, **kwargs):
    if args[0] == EC2_ROLE_NAME:
        return False
    else:
        return True


if __name__ == "__main__":
    unittest.main()
