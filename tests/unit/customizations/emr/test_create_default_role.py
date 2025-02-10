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
from botocore.compat import json
from botocore.awsrequest import AWSResponse
from botocore.exceptions import ClientError

import awscli.customizations.emr.emrutils as emrutils
import awscli.customizations.emr.createdefaultroles as createdefaultroles
from awscli.testutils import mock, unittest
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


EC2_ROLE_NAME = "EMR_EC2_DefaultRole"
EMR_ROLE_NAME = "EMR_DefaultRole"
EMR_AUTOSCALING_ROLE_NAME = "EMR_AutoScaling_DefaultRole"

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

http_response = AWSResponse(None, 200, {}, None)

CN_EC2_ROLE_ARN = ('arn:aws-cn:iam::aws:policy/service-role/'
                   'AmazonElasticMapReduceforEC2Role')
US_GOV_EC2_ROLE_ARN = ('arn:aws-us-gov:iam::aws:policy/service-role/'
                       'AmazonElasticMapReduceforEC2Role')

EC2_ROLE_ARN = ('arn:aws:iam::aws:policy/service-role/'
                'AmazonElasticMapReduceforEC2Role')

CN_EMR_ROLE_ARN = ('arn:aws-cn:iam::aws:policy/service-role/'
                   'AmazonElasticMapReduceRole')

US_GOV_EMR_ROLE_ARN = ('arn:aws-us-gov:iam::aws:policy/'
                       'service-role/AmazonElasticMapReduceRole')

EMR_ROLE_ARN = ('arn:aws:iam::aws:policy/service-role/'
                'AmazonElasticMapReduceRole')

CN_EMR_AUTOSCALING_ROLE_ARN = 'arn:aws-cn:iam::aws:policy/service-role/AmazonElasticMapReduceforAutoScalingRole'

US_GOV_EMR_AUTOSCALING_ROLE_ARN = 'arn:aws-us-gov:iam::aws:policy/service-role/' \
                                  'AmazonElasticMapReduceforAutoScalingRole'

EMR_AUTOSCALING_ROLE_ARN = 'arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforAutoScalingRole'

class TestCreateDefaultRole(BaseAWSCommandParamsTest):
    prefix = 'emr create-default-roles'

    ec2_role_policy_document = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
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

    emr_autoscaling_role_policy_document_cn = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "elasticmapreduce.amazonaws.com.cn",
                        "application-autoscaling.amazonaws.com.cn"
                    ]
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    emr_autoscaling_role_policy_document = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "elasticmapreduce.amazonaws.com",
                        "application-autoscaling.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    def test_default_roles_exist(self):
        cmdline = self.prefix

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 4)

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

        self.assertEqual(self.operations_called[3][0].name, 'GetRole')
        self.assertEqual(self.operations_called[3][1]['RoleName'],
                         EMR_AUTOSCALING_ROLE_NAME)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_role_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._get_role_policy')
    def test_default_autoscaling_role_commercial(self, get_rp_patch,
                                                 role_exists_patch,
                                                 instance_profile_exists_patch,
                                                 construct_result_patch):
        get_rp_patch.return_value = False
        role_exists_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        construct_result_patch.return_value = []

        cmdline = self.prefix + ' --region us-east-1'

        self.run_cmd(cmdline, expected_rc=0)

        # Only 8 operations will be called as we are mocking
        # check_if_role_exists and check_if_instance_profile_exists methods.
        self.assertEqual(len(self.operations_called), 8)
        self.assertEqual(
            self.operations_called[6][1]['AssumeRolePolicyDocument'],
            emrutils.dict_to_string(self.emr_autoscaling_role_policy_document))

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_role_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._get_role_policy')
    def test_default_roles_not_exist(self, get_rp_patch,
                                     role_exists_patch,
                                     instance_profile_exists_patch,
                                     construct_result_patch):
        get_rp_patch.return_value = False
        role_exists_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        construct_result_patch.return_value = []

        cmdline = self.prefix + ' --region cn-north-1'

        self.run_cmd(cmdline, expected_rc=0)

        # Only 8 operations will be called as we are mocking
        # check_if_role_exists and check_if_instance_profile_exists methods.
        self.assertEqual(len(self.operations_called), 8)

        self.assertEqual(self.operations_called[0][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         EC2_ROLE_NAME)
        self.assertEqual(
            self.operations_called[0][1]['AssumeRolePolicyDocument'],
            emrutils.dict_to_string(self.ec2_role_policy_document))

        self.assertEqual(self.operations_called[1][0].name,
                         'AttachRolePolicy')
        self.assertEqual(self.operations_called[1][1]['PolicyArn'],
                         CN_EC2_ROLE_ARN)
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

        self.assertEqual(self.operations_called[5][0].name, 'AttachRolePolicy')
        self.assertEqual(self.operations_called[5][1]['PolicyArn'],
                         CN_EMR_ROLE_ARN)
        self.assertEqual(self.operations_called[5][1]['RoleName'],
                         EMR_ROLE_NAME)

        self.assertEqual(self.operations_called[6][0].name, 'CreateRole')
        self.assertEqual(self.operations_called[6][1]['RoleName'],
                         EMR_AUTOSCALING_ROLE_NAME)
        self.assertEqual(
            self.operations_called[6][1]['AssumeRolePolicyDocument'],
            emrutils.dict_to_string(self.emr_autoscaling_role_policy_document_cn))

        self.assertEqual(self.operations_called[7][0].name, 'AttachRolePolicy')
        self.assertEqual(self.operations_called[7][1]['PolicyArn'],
                         CN_EMR_AUTOSCALING_ROLE_ARN)
        self.assertEqual(self.operations_called[7][1]['RoleName'],
                         EMR_AUTOSCALING_ROLE_NAME)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._construct_result')
    @mock.patch('awscli.customizations.emr.createdefaultroles'
                '.get_service_principal')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_role_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._get_role_policy')
    def test_get_service_principal_parameters(self, get_rp_patch,
                                              role_exists_patch,
                                              instance_profile_exists_patch,
                                              get_sp_patch,
                                              construct_result_patch):
        get_rp_patch.return_value = "blah"
        get_sp_patch.return_value = 'elasticmapreduce.amazonaws.abc'
        role_exists_patch.return_value = False
        instance_profile_exists_patch.return_value = False
        construct_result_patch.return_value = []

        endpoint_url = 'https://elasticmapreduce.abc'
        cmdline = self.prefix + ' --endpoint ' + endpoint_url
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(get_sp_patch.call_args[0][1], endpoint_url)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters(self, call_patch):
        cmdline = self.prefix + ' --region eu-west-1' + ' --no-verify-ssl'
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(call_patch.call_args[1]['region_name'], 'eu-west-1')
        self.assertEqual(call_patch.call_args[1]['verify'], False)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters_only_endpoint(self, call_patch):
        endpoint_arg = 'https://elasticmapreduce.us-unknown-1.amazonaws.com'
        cmdline = self.prefix + ' --endpoint ' + endpoint_arg
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(call_patch.call_args[1]['endpoint_url'], None)

    @mock.patch('botocore.session.Session.create_client')
    def test_call_parameters_only_iam_endpoint(self, call_patch):
        endpoint_arg = 'https://elasticmapreduce.us-unknown-1.amazonaws.com'
        cmdline = self.prefix + ' --iam-endpoint ' + endpoint_arg
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(call_patch.call_args[1]['endpoint_url'],
                          endpoint_arg)

    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._get_role_policy')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles._create_role_with_role_policy')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_instance_profile_exists')
    @mock.patch('awscli.customizations.emr.emr.'
                'CreateDefaultRoles.check_if_role_exists')
    def test_constructed_result(self, role_exists_patch,
                                instance_profile_exists_patch,
                                create_role_patch,
                                get_role_policy_patch):
        role_exists_patch.side_effect = side_effect_ofcheck_if_role_exists
        instance_profile_exists_patch.return_value = False
        create_role_patch.return_value = CREATE_EC2_ROLE_RESULT
        get_role_policy_patch.return_value = EC2_ROLE_POLICY

        cmdline = self.prefix + ' --region cn-north-1'
        result = self.run_cmd(cmdline, 0)
        expected_output = json.dumps(CONSTRUCTED_RESULT_OUTPUT, indent=4) +\
            '\n'
        self.assertEqual(result[0], expected_output)

    def test_policy_arn_construction(self):
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("cn-north-1", createdefaultroles.EC2_ROLE_POLICY_NAME),
            CN_EC2_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("us-gov-west-1", createdefaultroles.EC2_ROLE_POLICY_NAME),
            US_GOV_EC2_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("eu-west-1", createdefaultroles.EC2_ROLE_POLICY_NAME),
            EC2_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("cn-north-1", createdefaultroles.EMR_ROLE_POLICY_NAME),
            CN_EMR_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("us-gov-west-1", createdefaultroles.EMR_ROLE_POLICY_NAME),
            US_GOV_EMR_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("eu-west-1", createdefaultroles.EMR_ROLE_POLICY_NAME),
            EMR_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("cn-north-1", createdefaultroles.EMR_AUTOSCALING_ROLE_POLICY_NAME),
            CN_EMR_AUTOSCALING_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("us-gov-west-1",
                                                   createdefaultroles.EMR_AUTOSCALING_ROLE_POLICY_NAME),
            US_GOV_EMR_AUTOSCALING_ROLE_ARN)
        self.assertEqual(
            createdefaultroles.get_role_policy_arn("eu-west-1", createdefaultroles.EMR_AUTOSCALING_ROLE_POLICY_NAME),
            EMR_AUTOSCALING_ROLE_ARN)


class TestCreateDefaultRoles(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock()
        self.client = mock.Mock()
        self.session.create_client.return_value = self.client
        self.command = createdefaultroles.CreateDefaultRoles(self.session)
        setattr(self.command, 'iam_endpoint_url', 'https://www.amazonaws.com')
        self.parsed_globals = mock.Mock()
        self.parsed_globals.verify_ssl = True

    def testcheck_if_role_exists_raises_client_error(self):
        error_response = {
            'Error': {
                'Code': 'foo'
            }
        }
        error = ClientError(error_response, 'GetRole')
        self.client.get_role.side_effect = error

        with self.assertRaises(ClientError):
            self.command.check_if_role_exists('role', self.parsed_globals)

    def test_check_role_not_found(self):
        error_response = {
            'Error': {
                'Code': 'NoSuchEntity'
            }
        }
        error = ClientError(error_response, 'GetRole')
        self.client.get_role.side_effect = error
        self.assertFalse(self.command.check_if_role_exists('role', self.parsed_globals))

    def test_check_instance_profile_exists_raises_client_error(self):
        error_response = {
            'Error': {
                'Code': 'foo'
            }
        }
        error = ClientError(error_response, 'GetInstanceProfile')
        self.client.get_instance_profile.side_effect = error

        with self.assertRaises(ClientError):
            self.command.check_if_instance_profile_exists(
                'role', self.parsed_globals)

    def test_check_instance_profile_not_found(self):
        error_response = {
            'Error': {
                'Code': 'NoSuchEntity'
            }
        }
        error = ClientError(error_response, 'GetInstanceProfile')
        self.client.get_instance_profile.side_effect = error
        self.assertFalse(self.command.check_if_instance_profile_exists('role', self.parsed_globals))

def side_effect_ofcheck_if_role_exists(*args, **kwargs):
    if args[0] == EC2_ROLE_NAME:
        return False
    else:
        return True


if __name__ == "__main__":
    unittest.main()
