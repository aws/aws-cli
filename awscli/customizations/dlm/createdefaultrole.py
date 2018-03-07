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

# Class to create default roles for lifecycle
import logging
from awscli.clidriver import CLIOperationCaller
from awscli.customizations.utils import get_policy_arn_suffix
from awscli.customizations.commands import BasicCommand
from awscli.customizations.dlm.iam import IAM
from awscli.customizations.dlm.constants \
    import LIFECYCLE_DEFAULT_ROLE_NAME, \
    LIFECYCLE_DEFAULT_ROLE_ASSUME_POLICY, \
    LIFECYCLE_DEFAULT_MANAGED_POLICY_NAME, \
    POLICY_ARN_PATTERN

LOG = logging.getLogger(__name__)


def _construct_result(create_role_response, get_policy_response):
    get_policy_response.pop('ResponseMetadata', None)
    create_role_response.pop('ResponseMetadata', None)
    result = {'RolePolicy': get_policy_response}
    result.update(create_role_response)
    return result


# Display the result as formatted json
def display_response(session, operation_name, result, parsed_globals):
    if result is not None:
        cli_operation_caller = CLIOperationCaller(session)
        # Calling a private method. Should be changed after the functionality
        # is moved outside CliOperationCaller.
        cli_operation_caller._display_response(
            operation_name, result, parsed_globals)


# Get policy arn from region and policy name
def get_policy_arn(region, policy_name):
    region_suffix = get_policy_arn_suffix(region)
    role_arn = POLICY_ARN_PATTERN.format(region_suffix, policy_name)
    return role_arn


# Method to parse the arguments to get the region value
def get_region(session, parsed_globals):
    region = parsed_globals.region
    if region is None:
        region = session.get_config_variable('region')
    return region


class CreateDefaultRole(BasicCommand):
    NAME = "create-default-role"
    DESCRIPTION = ('Creates the default IAM role ' +
                   LIFECYCLE_DEFAULT_ROLE_NAME +
                   ' which will be used by Lifecycle service.\n'
                   'If the role does not exist, create-default-role '
                   'will automatically create it and set its policy.'
                   ' If the role has been already '
                   'created, create-default-role'
                   ' will not update its policy.'
                   '\n')
    ARG_TABLE = [
        {'name': 'iam-endpoint',
         'no_paramfile': True,
         'help_text': '<p>The IAM endpoint to call for creating the roles.'
                      ' This is optional and should only be specified when a'
                      ' custom endpoint should be called for IAM operations'
                      '.</p>'}
    ]

    def __init__(self, session):
        super(CreateDefaultRole, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        """Call to run the commands"""

        self._region = get_region(self._session, parsed_globals)
        self._endpoint_url = parsed_args.iam_endpoint
        self._iam_client = IAM(self._session.create_client(
            'iam',
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            verify=parsed_globals.verify_ssl
        ))

        result = self._create_default_role_if_not_exists(parsed_globals)

        display_response(
            self._session,
            'create_role',
            result,
            parsed_globals
        )

        return 0

    def _create_default_role_if_not_exists(self, parsed_globals):
        """Method to create default lifecycle role
            if it doesn't exist already
        """
        role_name = LIFECYCLE_DEFAULT_ROLE_NAME
        assume_role_policy = LIFECYCLE_DEFAULT_ROLE_ASSUME_POLICY

        if self._iam_client.check_if_role_exists(role_name):
            LOG.debug('Role %s exists', role_name)
            return None

        LOG.debug('Role %s does not exist. '
                  'Creating default role for Lifecycle', role_name)

        # Get Region
        region = get_region(self._session, parsed_globals)

        if region is None:
            raise ValueError('You must specify a region. '
                             'You can also configure your region '
                             'by running "aws configure".')

        managed_policy_arn = get_policy_arn(
            region,
            LIFECYCLE_DEFAULT_MANAGED_POLICY_NAME
        )

        # Don't proceed if managed policy does not exist
        if not self._iam_client.check_if_policy_exists(managed_policy_arn):
            LOG.debug('Managed Policy %s does not exist.', managed_policy_arn)
            return None

        LOG.debug('Managed Policy %s exists.', managed_policy_arn)
        # Create default role
        create_role_response = \
            self._iam_client.create_role_with_trust_policy(
                role_name,
                assume_role_policy
            )
        # Attach policy to role
        self._iam_client.attach_policy_to_role(
            managed_policy_arn,
            role_name
        )

        # Construct result
        get_policy_response = self._iam_client.get_policy(managed_policy_arn)
        return _construct_result(create_role_response, get_policy_response)
