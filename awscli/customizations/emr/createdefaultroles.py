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

import logging
import re

import botocore.exceptions

from awscli.customizations.emr.exceptions import ResolveServicePrincipalError
from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions


LOG = logging.getLogger(__name__)


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


EMR_ROLE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CancelSpotInstanceRequests",
                "ec2:CreateSecurityGroup",
                "ec2:CreateTags",
                "ec2:Describe*",
                "ec2:DeleteTags",
                "ec2:ModifyImageAttribute",
                "ec2:ModifyInstanceAttribute",
                "ec2:RequestSpotInstances",
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "iam:PassRole",
                "iam:ListRolePolicies",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:ListInstanceProfiles",
                "s3:Get*",
                "s3:List*",
                "s3:CreateBucket",
                "sdb:BatchPutAttributes",
                "sdb:Select"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}


def assume_role_policy(serviceprincipal):
    return {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": serviceprincipal},
                "Action": "sts:AssumeRole"
            }
        ]
    }


def get_service_principal(service, endpoint_host):
    return service+'.'+_get_suffix(endpoint_host)


def _get_suffix(endpoint_host):
        return _get_suffix_from_endpoint_host(endpoint_host)


def _get_suffix_from_endpoint_host(endpoint_host):
    suffix_match = _get_regex_match_from_endpoint_host(endpoint_host)

    if suffix_match is not None and suffix_match.lastindex >= 3:
        suffix = suffix_match.group(3)
    else:
        raise ResolveServicePrincipalError

    return suffix


def _get_regex_match_from_endpoint_host(endpoint_host):
    if endpoint_host is None:
        return None
    regex_match = re.match("(https?://)([^.]+).elasticmapreduce.([^/]*)",
                           endpoint_host)

    # Supports 'elasticmapreduce.{region}.' and '{region}.elasticmapreduce.'
    if regex_match is None:
        regex_match = re.match("(https?://elasticmapreduce).([^.]+).([^/]*)",
                               endpoint_host)
    return regex_match


class CreateDefaultRoles(BasicCommand):
    NAME = "create-default-roles"
    DESCRIPTION = ('Creates the default IAM role ' +
                   EC2_ROLE_NAME + ' and ' +
                   EMR_ROLE_NAME + ' which can be used when'
                   ' creating the cluster using the create-cluster command.')
    ARG_TABLE = [
        {'name': 'iam-endpoint',
         'no_paramfile': True,
         'help_text': '<p>The IAM endpoint to call for creating the roles.'
                      ' This is optional and should only be specified when a'
                      ' custom endpoint should be called for IAM operations'
                      '.</p>'}
    ]
    EXAMPLES = BasicCommand.FROM_FILE('emr', 'create-default-roles.rst')

    def _run_main(self, parsed_args, parsed_globals):
        ec2_result = None
        emr_result = None
        self.iam = self._session.get_service('iam')
        self.iam_endpoint_url = parsed_args.iam_endpoint
        region = self._get_region(parsed_globals)

        self._check_for_iam_endpoint(region, self.iam_endpoint_url)
        self.emr_endpoint_url = \
            self._session.get_service('emr').get_endpoint(
                region_name=parsed_globals.region,
                endpoint_url=parsed_globals.endpoint_url,
                verify=parsed_globals.verify_ssl).host

        LOG.debug('elasticmapreduce endpoint used for resolving'
                  ' service principal: ' + self.emr_endpoint_url)

        # Check if the default EC2 Role for EMR exists.
        role_name = EC2_ROLE_NAME
        if self._check_if_role_exists(role_name, parsed_globals):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role for EC2: ' + role_name)
            ec2_result = self._create_role_with_role_policy(
                role_name, role_name, constants.EC2,
                emrutils.dict_to_string(EC2_ROLE_POLICY),
                parsed_globals)

        # Check if the default EC2 Instance Profile for EMR exists.
        instance_profile_name = EC2_ROLE_NAME
        if self._check_if_instance_profile_exists(instance_profile_name,
                                                  parsed_globals):
            LOG.debug('Instance Profile ' + instance_profile_name + ' exists.')
        else:
            LOG.debug('Instance Profile ' + instance_profile_name +
                      'does not exist. Creating default Instance Profile ' +
                      instance_profile_name)
            self._create_instance_profile_with_role(instance_profile_name,
                                                    instance_profile_name,
                                                    parsed_globals)

        # Check if the default EMR Role exists.
        role_name = EMR_ROLE_NAME
        if self._check_if_role_exists(role_name, parsed_globals):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role for EMR: ' + role_name)
            emr_result = self._create_role_with_role_policy(
                role_name, role_name, constants.EMR,
                emrutils.dict_to_string(EMR_ROLE_POLICY),
                parsed_globals)

        emrutils.display_response(
            self._session,
            self._session.get_service('iam').get_operation('CreateRole'),
            self._construct_result(ec2_result, emr_result),
            parsed_globals)

        return 0

    def _check_for_iam_endpoint(self, region, iam_endpoint):
        try:
            self._session.get_service('emr').get_endpoint(region)
        except botocore.exceptions.UnknownEndpointError:
            if iam_endpoint is None:
                raise exceptions.UnknownIamEndpointError(region=region)

    def _construct_result(self, ec2_response, emr_response):
        result = []
        self._construct_role_and_role_policy_structure(
            result, ec2_response, EC2_ROLE_POLICY)
        self._construct_role_and_role_policy_structure(
            result, emr_response, EMR_ROLE_POLICY)
        return result

    def _construct_role_and_role_policy_structure(
            self, list, response, role_policy):
        if response is not None and response[1] is not None:
            list.append({'Role': response[1]['Role'],
                        'RolePolicy': role_policy})
            return list

    def _get_region(self, parsed_globals):
        region = self._session.get_config_variable('region')

        if parsed_globals.region is not None:
            region = parsed_globals.region

        return region

    def _check_if_role_exists(self, role_name, parsed_globals):
        parameters = {'RoleName': role_name}
        try:
            self._call_iam_operation('GetRole', parameters, parsed_globals)
        except Exception as e:
            role_not_found_msg = 'The role with name ' + role_name +\
                                 ' cannot be found'
            if role_not_found_msg in e.message:
                # No role error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def _check_if_instance_profile_exists(self, instance_profile_name,
                                          parsed_globals):
        parameters = {'InstanceProfileName': instance_profile_name}
        try:
            self._call_iam_operation('GetInstanceProfile', parameters,
                                     parsed_globals)
        except Exception as e:
            profile_not_found_msg = 'Instance Profile ' +\
                                    instance_profile_name +\
                                    ' cannot be found.'
            if profile_not_found_msg in e.message:
                # No instance profile error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def _create_role_with_role_policy(
            self, role_name, policy_name, service_name, policy_document,
            parsed_globals):
        service_principal = get_service_principal(service_name,
                                                  self.emr_endpoint_url)
        LOG.debug(service_principal)

        parameters = {'RoleName': role_name}
        _assume_role_policy = \
            emrutils.dict_to_string(assume_role_policy(service_principal))
        parameters['AssumeRolePolicyDocument'] = _assume_role_policy
        create_role_response = self._call_iam_operation('CreateRole',
                                                        parameters,
                                                        parsed_globals)

        parameters = {}
        parameters['PolicyDocument'] = policy_document
        parameters['PolicyName'] = policy_name
        parameters['RoleName'] = role_name
        self._call_iam_operation('PutRolePolicy', parameters, parsed_globals)

        return create_role_response

    def _create_instance_profile_with_role(self, instance_profile_name,
                                           role_name, parsed_globals):
        # Creating an Instance Profile
        parameters = {'InstanceProfileName': instance_profile_name}
        self._call_iam_operation('CreateInstanceProfile', parameters,
                                 parsed_globals)
        # Adding the role to the Instance Profile
        parameters = {}
        parameters['InstanceProfileName'] = instance_profile_name
        parameters['RoleName'] = role_name
        self._call_iam_operation('AddRoleToInstanceProfile', parameters,
                                 parsed_globals)

    def _call_iam_operation(self, operation_name, parameters, parsed_globals):
        operation_object = self.iam.get_operation(operation_name)
        return emrutils.call(
            self._session, operation_object, parameters, parsed_globals.region,
            self.iam_endpoint_url, parsed_globals.verify_ssl)
