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

from awscli.clidriver import CLIOperationCaller
from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import defaultroles
from awscli.customizations.emr import exceptions
from awscli.customizations.emr import helptext
from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import applicationutils
from awscli.customizations.emr import hbase
from awscli.customizations.emr import ssh
from awscli.customizations.emr.emrconfig import REGION_MAP
from awscli.customizations.emr.addsteps import AddSteps
from awscli.customizations.emr.createcluster import CreateCluster
from awscli.customizations.emr.emrconfig import get_service_principal
from awscli.customizations.emr.defaultroles import assume_role_policy
from awscli.customizations.emr.addinstancegroups import AddInstanceGroups


LOG = logging.getLogger(__name__)


def emr_initialize(cli):
    """
    The entry point for EMR high level commands.
    """
    cli.register('building-command-table.emr', register_commands)


def register_commands(command_table, session, **kwargs):
    """
    Called when the EMR command table is being built. Used to inject new
    high level commands into the command list. These high level commands
    must not collide with existing low-level API call names.
    """
    command_table['terminate-clusters'] = TerminateClusters(session)
    command_table['add-tags'] = AddTags(session)
    command_table['describe-cluster'] = DescribeCluster(session)
    command_table['modify-cluster-attributes'] = ModifyClusterAttr(session)
    command_table['install-applications'] = InstallApplications(session)
    command_table['create-cluster'] = CreateCluster(session)
    command_table['add-steps'] = AddSteps(session)
    command_table['restore-from-hbase-backup'] = \
        hbase.RestoreFromHBaseBackup(session)
    command_table['create-hbase-backup'] = hbase.CreateHBaseBackup(session)
    command_table['schedule-hbase-backup'] = hbase.ScheduleHBaseBackup(session)
    command_table['disable-hbase-backups'] = \
        hbase.DisableHBaseBackups(session)
    command_table['create-default-roles'] = CreateDefaultRoles(session)
    command_table['add-instance-groups'] = AddInstanceGroups(session)
    command_table['ssh'] = ssh.SSH(session)
    command_table['socks'] = ssh.Socks(session)
    command_table['get'] = ssh.Get(session)
    command_table['put'] = ssh.Put(session)


class TerminateClusters(BasicCommand):
    NAME = 'terminate-clusters'
    DESCRIPTION = helptext.TERMINATE_CLUSTERS
    ARG_TABLE = [
        {'name': 'cluster-ids', 'nargs': '+', 'required': True,
         'help_text': '<p>A list of clusters to terminate.</p>'}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        parameters = {'JobFlowIds': parsed_args.cluster_ids}
        cli_operation_caller = CLIOperationCaller(self._session)
        cli_operation_caller.invoke(
            emr.get_operation('TerminateJobFlows'),
            parameters, parsed_globals)
        return 0


class InstallApplications(BasicCommand):
    NAME = 'install-applications'
    DESCRIPTION = ('Installs applications on a running cluster. Currently only'
                   ' Hive and Pig can be installed using this command.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'apps', 'required': True,
         'help_text': helptext.INSTALL_APPLICATIONS,
         'schema': argumentschema.APPLICATIONS_SCHEMA},
    ]
    # Applications supported by the install-applications command.
    supported_apps = ['HIVE', 'PIG']

    def _run_main(self, parsed_args, parsed_globals):

        emr = self._session.get_service('emr')
        cli_operation_caller = CLIOperationCaller(self._session)
        parameters = {'JobFlowId': parsed_args.cluster_id}

        self.check_for_supported_apps(parsed_args.apps)
        parameters['Steps'] = applicationutils.build_applications(
            parsed_args.apps, parsed_globals)[2]

        cli_operation_caller.invoke(emr.get_operation('AddJobFlowSteps'),
                                    parameters, parsed_globals)
        return 0

    def check_for_supported_apps(self, parsed_applications):
        for app_config in parsed_applications:
            app_name = app_config['Name'].upper()

            if app_name in constants.APPLICATIONS:
                if app_name not in self.supported_apps:
                    raise ValueError(
                        "aws: error: " + app_config['Name'] + " cannot be"
                        " installed on a running cluster. 'Name' should be one"
                        " of the following: " +
                        ', '.join(self.supported_apps))
            else:
                raise ValueError(
                    "aws: error: Unknown application: " + app_config['Name'] +
                    ". 'Name' should be one of the following: " +
                    ', '.join(constants.APPLICATIONS))


class AddTags(BasicCommand):
    NAME = 'add-tags'
    DESCRIPTION = ('Add tags to the cluster.')
    ARG_TABLE = [
        {'name': 'resource-id', 'required': True,
            'help_text': '<p>The Amazon EMR resource identifier to which '
            'tags will be added. This value must be a cluster identifier.'},
        {'name': 'tags', 'required': True, 'nargs': '+',
            'help_text': helptext.TAGS}
    ]
    EXAMPLES = emrutils.get_example_file(NAME).read()

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        parameters = {'ResourceId': parsed_args.resource_id,
                      'Tags': emrutils.parse_tags(parsed_args.tags)}
        cli_operation_caller = CLIOperationCaller(self._session)
        cli_operation_caller.invoke(emr.get_operation('AddTags'), parameters,
                                    parsed_globals)
        return 0


class DescribeCluster(BasicCommand):
    NAME = 'describe-cluster'
    DESCRIPTION = ('Provides  cluster-level details including status, hardware'
                   ' and software configuration, VPC settings, bootstrap'
                   ' actions, instance groups and so on. For information about'
                   ' the cluster steps, see <code>list-steps</code>.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID}
    ]
    EXAMPLES = emrutils.get_example_file(NAME).read()

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        describe_cluster = emr.get_operation('DescribeCluster')
        parameters = {'ClusterId': parsed_args.cluster_id}

        describe_cluster_response = self._call(describe_cluster, parameters,
                                               parsed_globals)

        list_instance_groups_response = self._call(
            emr.get_operation('ListInstanceGroups'), parameters,
            parsed_globals)

        list_bootstrap_actions_response = self._call(
            emr.get_operation('ListBootstrapActions'),
            parameters, parsed_globals)

        index = 1
        constructed_result = self.construct_result(
            describe_cluster_response[index],
            list_instance_groups_response[index],
            list_bootstrap_actions_response[index])

        cli_operation_caller = CLIOperationCaller(self._session)
        # Calling a private method. Should be changed after the functionality
        # is moved outside CliOperationCaller.
        cli_operation_caller._display_response(describe_cluster,
                                               constructed_result,
                                               parsed_globals)

        return 0

    def _call(self, operation, parameters, parsed_globals):
        return emrutils.call(
            self._session, operation, parameters, parsed_globals.region,
            parsed_globals.endpoint_url, parsed_globals.verify_ssl)

    def construct_result(
            self, describe_cluster_result, list_instance_groups_result,
            list_bootstrap_actions_result):
        result = describe_cluster_result

        result['Cluster']['InstanceGroups'] = \
            list_instance_groups_result['InstanceGroups']
        result['Cluster']['BootstrapActions'] = \
            list_bootstrap_actions_result['BootstrapActions']

        return result


class ModifyClusterAttr(BasicCommand):
    NAME = 'modify-cluster-attributes'
    DESCRIPTION = ("Modifies the cluster attributes 'visible-to-all-users' and"
                   " 'termination-protected'.")
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
            'help_text': helptext.CLUSTER_ID},
        {'name': 'visible-to-all-users', 'required': False, 'action':
            'store_true', 'group_name': 'visible',
            'help_text': 'Change cluster visibility for IAM users'},
        {'name': 'no-visible-to-all-users', 'required': False, 'action':
            'store_true', 'group_name': 'visible',
            'help_text': 'Change cluster visibility for IAM users'},
        {'name': 'termination-protected', 'required': False, 'action':
            'store_true', 'group_name': 'terminate',
            'help_text': 'Set termination protected on or off'},
        {'name': 'no-termination-protected', 'required': False, 'action':
            'store_true', 'group_name': 'terminate',
            'help_text': 'Set termination protected on or off'},
    ]

    def _run_main(self, args, parsed_globals):
        emr = self._session.get_service('emr')

        if (args.visible_to_all_users and args.no_visible_to_all_users):
            raise ValueError(
                'aws: error: Cannot use both options --visible-to-all-users '
                'and --no-visible-to-all-users together.')
        if (args.termination_protected and args.no_termination_protected):
            raise ValueError(
                'aws: error: Cannot use both options --termination-protected '
                'and --no-termination-protected together.')
        if not(args.termination_protected or args.no_termination_protected
               or args.visible_to_all_users or args.no_visible_to_all_users):
            raise ValueError('aws: error: You need to specify atleast one of '
                             'the options.')

        cli_operation_caller = CLIOperationCaller(self._session)

        if (args.visible_to_all_users or args.no_visible_to_all_users):
            visible = (args.visible_to_all_users and
                       not args.no_visible_to_all_users)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'VisibleToAllUsers': visible}
            cli_operation_caller.invoke(
                emr.get_operation('SetVisibleToAllUsers'),
                parameters, parsed_globals)

        if (args.termination_protected or args.no_termination_protected):
            protected = (args.termination_protected and
                         not args.no_termination_protected)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'TerminationProtected': protected}
            cli_operation_caller.invoke(
                emr.get_operation('SetTerminationProtection'),
                parameters, parsed_globals)

        return 0


class CreateDefaultRoles(BasicCommand):
    NAME = "create-default-roles"
    DESCRIPTION = ('Creates the default IAM roles ' +
                   defaultroles.EC2_ROLE_NAME + ' and ' +
                   defaultroles.EMR_ROLE_NAME + ' which can be used when'
                   ' creating the cluster using the create-cluster command.')
    ARG_TABLE = [
        {'name': 'iam-endpoint',
         'no_paramfile': True,
         'help_text': '<p>The IAM endpoint to call for creating the roles.'
                      ' This is optional and should only be specified when a'
                      ' custom endpoint should be called for IAM operations'
                      '.</p>'}
    ]
    EXAMPLES = emrutils.get_example_file(NAME).read()

    def _run_main(self, parsed_args, parsed_globals):
        ec2_result = None
        emr_result = None
        self.iam = self._session.get_service('iam')
        self.iam_endpoint_url = parsed_args.iam_endpoint
        self.emr_endpoint_url = self._session.get_service('emr').get_endpoint(
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl).host
        LOG.debug('elasticmapreduce endpoint used for resolving'
                  ' service principal: ' + self.emr_endpoint_url)

        region = self._get_region(parsed_globals)
        if self._is_known_region(region) is False:
            if parsed_args.iam_endpoint is None:
                raise exceptions.UnkownIamEndpointError(region=region)

        # Check if the default EC2 Role for EMR exists.
        role_name = defaultroles.EC2_ROLE_NAME
        if self._check_if_role_exists(role_name, parsed_globals):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role ' + role_name)
            ec2_result = self._create_role_with_role_policy(
                role_name, role_name, constants.EC2,
                emrutils.dict_to_string(defaultroles.EC2_ROLE_POLICY),
                parsed_globals)

        # Check if the default EC2 Instance Profile for EMR exists.
        instance_profile_name = defaultroles.EC2_ROLE_NAME
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
        role_name = defaultroles.EMR_ROLE_NAME
        if self._check_if_role_exists(role_name, parsed_globals):
            LOG.debug('Role ' + role_name + ' exists.')
        else:
            LOG.debug('Role ' + role_name + ' does not exist.'
                      ' Creating default role ' + role_name)
            emr_result = self._create_role_with_role_policy(
                role_name, role_name, constants.EMR,
                emrutils.dict_to_string(defaultroles.EMR_ROLE_POLICY),
                parsed_globals)

        cli_operation_caller = CLIOperationCaller(self._session)
        # Calling a private method. Should be changed after the functionality
        # is moved outside CliOperationCaller.
        cli_operation_caller._display_response(
            self._session.get_service('iam').get_operation('CreateRole'),
            self._construct_result(ec2_result, emr_result),
            parsed_globals)

        return 0

    def _construct_result(self, ec2_response, emr_response):
        result = []
        self._construct_role_and_role_policy_structure(
            result, ec2_response, defaultroles.EC2_ROLE_POLICY)
        self._construct_role_and_role_policy_structure(
            result, emr_response, defaultroles.EMR_ROLE_POLICY)

        return result

    def _construct_role_and_role_policy_structure(
            self, list, response, role_policy):
        if response is not None and response[1] is not None:
            list.append({'Role': response[1]['Role'],
                        'RolePolicy': role_policy})
            return list

    def _get_region(self, parsed_globals):
        if self._session.get_config_variable('region') is not None:
            region = self._session.get_config_variable('region')
        if parsed_globals.region is not None:
            region = parsed_globals.region

        return region

    def _is_known_region(self, region):
        if region is not None and region in REGION_MAP:
            return True

        return False

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
        service_principal = get_service_principal(
            service_name, self._get_region(parsed_globals),
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
