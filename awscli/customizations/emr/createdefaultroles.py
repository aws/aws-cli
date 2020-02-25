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
import botocore.session
from botocore import xform_name

from awscli.customizations.utils import get_policy_arn_suffix
from awscli.customizations.emr import configutils
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions
from awscli.customizations.emr.command import Command
from awscli.customizations.emr.constants import EC2
from awscli.customizations.emr.constants import EC2_ROLE_NAME
from awscli.customizations.emr.constants import ROLE_ARN_PATTERN
from awscli.customizations.emr.constants import EMR
from awscli.customizations.emr.constants import EMR_ROLE_NAME
from awscli.customizations.emr.constants import EMR_AUTOSCALING_ROLE_NAME
from awscli.customizations.emr.constants import APPLICATION_AUTOSCALING
from awscli.customizations.emr.constants import EC2_ROLE_POLICY_NAME
from awscli.customizations.emr.constants import EMR_ROLE_POLICY_NAME
from awscli.customizations.emr.constants \
    import EMR_AUTOSCALING_ROLE_POLICY_NAME
from awscli.customizations.emr.constants import EMR_AUTOSCALING_SERVICE_NAME
from awscli.customizations.emr.constants \
    import EMR_AUTOSCALING_SERVICE_PRINCIPAL
from awscli.customizations.emr.exceptions import ResolveServicePrincipalError


LOG = logging.getLogger(__name__)


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


def get_role_policy_arn(region, policy_name):
    region_suffix = get_policy_arn_suffix(region)
    role_arn = ROLE_ARN_PATTERN.replace("{{region_suffix}}", region_suffix)
    role_arn = role_arn.replace("{{policy_name}}", policy_name)
    return role_arn


def get_service_principal(service, endpoint_host, session=None):
    suffix, region = _get_suffix_and_region_from_endpoint_host(endpoint_host)
    if session is None:
        session = botocore.session.Session()

    if service == EMR_AUTOSCALING_SERVICE_NAME:
        if region not in session.get_available_regions('emr', 'aws-cn'):
            return EMR_AUTOSCALING_SERVICE_PRINCIPAL

    return service + '.' + suffix


def _get_suffix_and_region_from_endpoint_host(endpoint_host):
    suffix_match = _get_regex_match_from_endpoint_host(endpoint_host)

    if suffix_match is not None and suffix_match.lastindex >= 3:
        suffix = suffix_match.group(3)
        region = suffix_match.group(2)
    else:
        raise ResolveServicePrincipalError

    return suffix, region


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


class CreateDefaultRoles(Command):
    NAME = "create-default-roles"
    DESCRIPTION = ('Creates the default IAM role ' +
                   EC2_ROLE_NAME + ' and ' +
                   EMR_ROLE_NAME + ' which can be used when creating the'
                   ' cluster using the create-cluster command. The default'
                   ' roles for EMR use managed policies, which are updated'
                   ' automatically to support future EMR functionality.\n'
                   '\nIf you do not have a Service Role and Instance Profile '
                   'variable set for your create-cluster command in the AWS '
                   'CLI config file, create-default-roles will automatically '
                   'set the values for these variables with these default '
                   'roles. If you have already set a value for Service Role '
                   'or Instance Profile, create-default-roles will not '
                   'automatically set the defaults for these variables in the '
                   'AWS CLI config file. You can view settings for variables '
                   'in the config file using the "aws configure get" command.'
                   '\n')
    ARG_TABLE = [
        {'name': 'iam-endpoint',
         'no_paramfile': True,
         'help_text': '<p>The IAM endpoint to call for creating the roles.'
                      ' This is optional and should only be specified when a'
                      ' custom endpoint should be called for IAM operations'
                      '.</p>'}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):

        self.iam_endpoint_url = parsed_args.iam_endpoint

        self._check_for_iam_endpoint(self.region, self.iam_endpoint_url)
        self.emr_endpoint_url = \
            self._session.create_client(
                'emr',
                region_name=self.region,
                endpoint_url=parsed_globals.endpoint_url,
                verify=parsed_globals.verify_ssl).meta.endpoint_url

        LOG.debug('elasticmapreduce endpoint used for resolving'
                  ' service principal: ' + self.emr_endpoint_url)

        # Create default EC2 Role for EMR if it does not exist.
        ec2_result, ec2_policy = self._create_role_if_not_exists(parsed_globals, EC2_ROLE_NAME,
                                                                 EC2_ROLE_POLICY_NAME, [EC2])

        # Create default EC2 Instance Profile for EMR if it does not exist.
        instance_profile_name = EC2_ROLE_NAME
        if self.check_if_instance_profile_exists(instance_profile_name,
                                                 parsed_globals):
            LOG.debug('Instance Profile ' + instance_profile_name + ' exists.')
        else:
            LOG.debug('Instance Profile ' + instance_profile_name +
                      'does not exist. Creating default Instance Profile ' +
                      instance_profile_name)
            self._create_instance_profile_with_role(instance_profile_name,
                                                    instance_profile_name,
                                                    parsed_globals)

        # Create default EMR Role if it does not exist.
        emr_result, emr_policy = self._create_role_if_not_exists(parsed_globals, EMR_ROLE_NAME,
                                                                 EMR_ROLE_POLICY_NAME, [EMR])

        # Create default EMR AutoScaling Role if it does not exist.
        emr_autoscaling_result, emr_autoscaling_policy = \
            self._create_role_if_not_exists(parsed_globals, EMR_AUTOSCALING_ROLE_NAME,
                                            EMR_AUTOSCALING_ROLE_POLICY_NAME, [EMR, APPLICATION_AUTOSCALING])

        configutils.update_roles(self._session)
        emrutils.display_response(
            self._session,
            'create_role',
            self._construct_result(ec2_result, ec2_policy,
                                   emr_result, emr_policy,
                                   emr_autoscaling_result, emr_autoscaling_policy),
            parsed_globals)

        return 0

    def _create_role_if_not_exists(self, parsed_globals, role_name, policy_name, service_names):
        result = None
        policy = None

        if self.check_if_role_exists(role_name, parsed_globals):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role: ' + role_name)
            role_arn = get_role_policy_arn(self.region, policy_name)
            result = self._create_role_with_role_policy(
                    role_name, service_names, role_arn, parsed_globals)
            policy = self._get_role_policy(role_arn, parsed_globals)
        return result, policy

    def _check_for_iam_endpoint(self, region, iam_endpoint):
        try:
            self._session.create_client('emr', region)
        except botocore.exceptions.UnknownEndpointError:
            if iam_endpoint is None:
                raise exceptions.UnknownIamEndpointError(region=region)

    def _construct_result(self, ec2_response, ec2_policy,
                          emr_response, emr_policy,
                          emr_autoscaling_response, emr_autoscaling_policy):
        result = []
        self._construct_role_and_role_policy_structure(
            result, ec2_response, ec2_policy)
        self._construct_role_and_role_policy_structure(
            result, emr_response, emr_policy)
        self._construct_role_and_role_policy_structure(
            result, emr_autoscaling_response, emr_autoscaling_policy)
        return result

    def _construct_role_and_role_policy_structure(
            self, list, response, policy):
        if response is not None and response['Role'] is not None:
            list.append({'Role': response['Role'], 'RolePolicy': policy})
            return list

    def check_if_role_exists(self, role_name, parsed_globals):
        parameters = {'RoleName': role_name}

        try:
            self._call_iam_operation('GetRole', parameters, parsed_globals)
        except botocore.exceptions.ClientError as e:
            role_not_found_code = "NoSuchEntity"
            error_code = e.response.get('Error', {}).get('Code', '')
            if role_not_found_code == error_code:
                # No role error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def check_if_instance_profile_exists(self, instance_profile_name,
                                         parsed_globals):
        parameters = {'InstanceProfileName': instance_profile_name}
        try:
            self._call_iam_operation('GetInstanceProfile', parameters,
                                     parsed_globals)
        except botocore.exceptions.ClientError as e:
            profile_not_found_code = 'NoSuchEntity'
            error_code = e.response.get('Error', {}).get('Code')
            if profile_not_found_code == error_code:
                # No instance profile error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def _get_role_policy(self, arn, parsed_globals):
        parameters = {}
        parameters['PolicyArn'] = arn
        policy_details = self._call_iam_operation('GetPolicy', parameters,
                                                  parsed_globals)
        parameters["VersionId"] = policy_details["Policy"]["DefaultVersionId"]
        policy_version_details = self._call_iam_operation('GetPolicyVersion',
                                                          parameters,
                                                          parsed_globals)
        return policy_version_details["PolicyVersion"]["Document"]

    def _create_role_with_role_policy(
            self, role_name, service_names, role_arn, parsed_globals):

        if len(service_names) == 1:
            service_principal = get_service_principal(
                service_names[0], self.emr_endpoint_url, self._session)
        else:
            service_principal = []
            for service in service_names:
                service_principal.append(get_service_principal(
                    service, self.emr_endpoint_url, self._session))

        LOG.debug(service_principal)

        parameters = {'RoleName': role_name}
        _assume_role_policy = \
            emrutils.dict_to_string(assume_role_policy(service_principal))
        parameters['AssumeRolePolicyDocument'] = _assume_role_policy
        create_role_response = self._call_iam_operation('CreateRole',
                                                        parameters,
                                                        parsed_globals)

        parameters = {}
        parameters['PolicyArn'] = role_arn
        parameters['RoleName'] = role_name
        self._call_iam_operation('AttachRolePolicy',
                                 parameters, parsed_globals)

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
        client = self._session.create_client(
            'iam', region_name=self.region, endpoint_url=self.iam_endpoint_url,
            verify=parsed_globals.verify_ssl)
        return getattr(client, xform_name(operation_name))(**parameters)
