# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

# Class to create default roles for datapipeline

import logging
from awscli.customizations.datapipeline.constants \
    import DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME, \
    DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME, \
    DATAPIPELINE_DEFAULT_SERVICE_ROLE_ARN, \
    DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ARN, \
    DATAPIPELINE_DEFAULT_SERVICE_ROLE_ASSUME_POLICY, \
    DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ASSUME_POLICY
from awscli.customizations.commands import BasicCommand
from awscli.customizations.datapipeline.translator \
    import display_response, dict_to_string, get_region, remove_cli_error_event
from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


class CreateDefaultRoles(BasicCommand):

    NAME = "create-default-roles"
    DESCRIPTION = ('Creates the default IAM role ' +
                   DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME + ' and ' +
                   DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME +
                   ' which are used while creating an EMR cluster.\n'
                   'If the roles do not exist, create-default-roles '
                   'will automatically create them and set their policies.'
                   ' If these roles are already '
                   'created create-default-roles'
                   ' will not update their policies.'
                   '\n')

    def __init__(self, session, formatter=None):
        super(CreateDefaultRoles, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals, **kwargs):
        """Call to run the commands"""
        self._region = get_region(self._session, parsed_globals)
        self._endpoint_url = parsed_globals.endpoint_url
        self._iam_client = self._session.create_client(
            'iam', 
            region_name=self._region, 
            endpoint_url=self._endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        remove_cli_error_event(self._iam_client)
        return self._create_default_roles(parsed_args, parsed_globals)

    def _create_role(self, role_name, role_arn, role_policy):
        """Method to create a role for a given role name and arn
        if it does not exist
        """

        role_result = None
        role_policy_result = None
        # Check if the role with the name exists
        if self._check_if_role_exists(role_name):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role for EC2: ' + role_name)
            # Create a create using the IAM Client with a particular triplet
            # (role_name, role_arn, assume_role_policy)
            role_result = self._create_role_with_role_policy(role_name,
                                                             role_policy,
                                                             role_arn)
            role_policy_result = self._get_role_policy(role_arn)
        return role_result, role_policy_result

    def _construct_result(self, dpl_default_result,
                          dpl_default_policy,
                          dpl_default_res_result,
                          dpl_default_res_policy):
        """Method to create a resultant list of responses for create roles
        for service and resource role
        """

        result = []
        self._construct_role_and_role_policy_structure(result,
                                                       dpl_default_result,
                                                       dpl_default_policy)
        self._construct_role_and_role_policy_structure(result,
                                                       dpl_default_res_result,
                                                       dpl_default_res_policy)
        return result

    def _create_default_roles(self, parsed_args, parsed_globals):

        # Setting the role name and arn value
        (datapipline_default_result,
            datapipline_default_policy) = self._create_role(
                DATAPIPELINE_DEFAULT_SERVICE_ROLE_NAME,
                DATAPIPELINE_DEFAULT_SERVICE_ROLE_ARN,
                DATAPIPELINE_DEFAULT_SERVICE_ROLE_ASSUME_POLICY)

        (datapipline_default_resource_result,
            datapipline_default_resource_policy) = self._create_role(
                DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME,
                DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ARN,
                DATAPIPELINE_DEFAULT_RESOURCE_ROLE_ASSUME_POLICY)

        # Check if the default EC2 Instance Profile for DataPipeline exists.
        instance_profile_name = DATAPIPELINE_DEFAULT_RESOURCE_ROLE_NAME
        if self._check_if_instance_profile_exists(instance_profile_name):
            LOG.debug('Instance Profile ' + instance_profile_name + ' exists.')
        else:
            LOG.debug('Instance Profile ' + instance_profile_name +
                      'does not exist. Creating default Instance Profile ' +
                      instance_profile_name)
            self._create_instance_profile_with_role(instance_profile_name,
                                                    instance_profile_name)

        result = self._construct_result(datapipline_default_result,
                                        datapipline_default_policy,
                                        datapipline_default_resource_result,
                                        datapipline_default_resource_policy)

        display_response(self._session, 'create_role', result, parsed_globals)

        return 0

    def _get_role_policy(self, arn):
        """Method to get the Policy for a particular ARN
        This is used to display the policy contents to the user
        """
        pol_det = self._iam_client.get_policy(PolicyArn=arn)
        policy_version_details = self._iam_client.get_policy_version(
            PolicyArn=arn, VersionId=pol_det["Policy"]["DefaultVersionId"])
        return policy_version_details["PolicyVersion"]["Document"]

    def _create_role_with_role_policy(
            self, role_name, assume_role_policy, role_arn):
        """Method to create role with a given rolename, assume_role_policy
        and role_arn
        """
        # Create a role using IAM client CreateRole API
        create_role_response = self._iam_client.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=dict_to_string(
                assume_role_policy))

        # Create a role using IAM client AttachRolePolicy API
        self._iam_client.attach_role_policy(PolicyArn=role_arn,
                                            RoleName=role_name)

        return create_role_response

    def _construct_role_and_role_policy_structure(
            self, list_val, response, policy):
        """Method to construct the message to be displayed to the user"""
        # If the response is not none they we get the role name
        # from the response and
        # append the policy information to the response
        if response is not None and response['Role'] is not None:
            list_val.append({'Role': response['Role'], 'RolePolicy': policy})
            return list_val

    def _check_if_instance_profile_exists(self, instance_profile_name):
        """Method to verify if a particular role exists"""
        try:
            # Client call to get the instance profile with that name
            self._iam_client.get_instance_profile(
                InstanceProfileName=instance_profile_name)

        except ClientError as e:
            # If the instance profile does not exist then the error message
            # would contain the required message
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # No instance profile error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def _check_if_role_exists(self, role_name):
        """Method to verify if a particular role exists"""
        try:
            # Client call to get the role
            self._iam_client.get_role(RoleName=role_name)
        except ClientError as e:
            # If the role does not exist then the error message
            # would contain the required message.
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # No role error.
                return False
            else:
                # Some other error. raise.
                raise e

        return True

    def _create_instance_profile_with_role(self, instance_profile_name,
                                           role_name):
        """Method to create the instance profile with the role"""
        # Setting the value for instance profile name
        # Client call to create an instance profile
        self._iam_client.create_instance_profile(
            InstanceProfileName=instance_profile_name)

        # Adding the role to the Instance Profile
        self._iam_client.add_role_to_instance_profile(
            InstanceProfileName=instance_profile_name, RoleName=role_name)
