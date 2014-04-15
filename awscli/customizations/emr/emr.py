# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
import logging
import sys
import constants

from awscli.customizations.commands import BasicCommand
from awscli.customizations.service import Service
from awscli.formatter import get_formatter
from awscli.clidriver import CLIOperationCaller

LOG = logging.getLogger(__name__)

HIVE_BASE_PATH = '/libs/hive'
HIVE_SCRIPT_PATH = '/libs/hive/hive-script'

PIG_BASE_PATH = '/libs/pig'
PIG_SCRIPT_PATH = '/libs/pig/pig-script'

SCRIPT_RUNNER_PATH = '/libs/script-runner/script-runner.jar'
DEFAULT_FAILURE_ACTION = 'CANCEL_AND_WAIT'


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
    command_table['modify-cluster-attributes'] = ModifyClusterAttr(session)


def _build_s3_link(relative_path='', region=None):
    if region and region != 'us-east-1':
        return 's3://{0}.elasticmapreduce{1}'.format(region, relative_path)
    else:
        return 's3://elasticmapreduce{}'.format(relative_path)


def _build_step(name, region, action_on_failure, jar, args):
    step = {}
    step['Name'] = name
    step['ActionOnFailure'] = action_on_failure
    step['HadoopJarStep'] = {'Jar': jar}
    step['HadoopJarStep']['Args'] = args
    return step


def build_pig_install_step(region, version,
                           action_on_failure=DEFAULT_FAILURE_ACTION):
    step_args = [_build_s3_link(PIG_SCRIPT_PATH, region), '--install-pig',
                 '--base-path', _build_s3_link(PIG_BASE_PATH, region),
                 '--pig-versions', version]
    step = _build_step('Install Pig', region, action_on_failure,
                       _build_s3_link(SCRIPT_RUNNER_PATH, region), step_args)
    return step


def build_hive_install_step(region, version,
                            action_on_failure=DEFAULT_FAILURE_ACTION):
    step_args = [_build_s3_link(HIVE_SCRIPT_PATH, region), '--install-hive',
                 '--base-path', _build_s3_link(HIVE_BASE_PATH),
                 '--hive-versions', version]
    step = _build_step('Install Hive', region, action_on_failure,
                       _build_s3_link(SCRIPT_RUNNER_PATH, region), step_args)
    return step


class TerminateClusters(BasicCommand):
    NAME = 'terminate-clusters'
    DESCRIPTION = ('terminate-clusters shuts down a list of clusters.')
    ARG_TABLE = [
        {'name': 'cluster-ids', 'nargs': '+', 'required': True,
         'help_text': 'A list of clusters to be shutdown\n'}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        parameters = {'JobFlowIds': parsed_args.cluster_ids}
        cliOperationCaller = CLIOperationCaller(self._session)
        cliOperationCaller.invoke(emr.get_operation('TerminateJobFlows'),
                                  parameters, parsed_globals)
        return 0


class InstallApplications(BasicCommand):
    Name = 'install-applications'
    DESCRIPTION = ('Install applications on a cluster.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True, 'help_text':
            'Cluster id of the cluster to install applications on'},
        {'name': 'hive', 'required': False, 'help_text': 'Install hive'},
        {'name': 'pig', 'required': False,  'help_text': 'Install pig'},
    ]

    def _get_version(self, arg):
        if arg.find('=') == -1:
            raise ValueError('aws: error: Invalid format.')
        key, value = arg.strip().split('=', 1)
        if key.lower() != 'version':
            raise ValueError('aws: error: Application version missing.')
        return value

    def _run_main(self, parsed_args, parsed_globals):
        if not (parsed_args.hive or parsed_args.pig):
            raise ValueError('aws: error: You need to specify atleast one '
                             'application.')

        emr = self._session.get_service('emr')
        cli_operation_caller = CLIOperationCaller(self._session)
        parameters = {'JobFlowId': parsed_args.cluster_id, 'Steps': []}

        if parsed_args.hive:
            version = self._get_version(parsed_args.hive)
            parameters['Steps'].append(build_hive_install_step(
                                       parsed_globals.region, version))

        if parsed_args.pig:
            version = self._get_version(parsed_args.pig)
            parameters['Steps'].append(build_pig_install_step(
                                       parsed_globals.region, version))

        cli_operation_caller.invoke(emr.get_operation('AddJobFlowSteps'),
                                    parameters, parsed_globals)
        return 0


class AddTags(BasicCommand):
    NAME = 'add-tags'
    DESCRIPTION = ('Add tags to the cluster.')
    ARG_TABLE = [
        {'name': 'resource-id', 'required': True,
            'help_text': 'The Amazon EMR resource identifier to which '
            'tags will be added. This value must be a cluster identifier.'},
        {'name': 'tags', 'required': True, 'nargs': '+',
            'help_text': ' A  list  of tags to associate with a cluster and '
            'propagate to Amazon EC2 instances. They are user-defined '
            'key/value pairs that  consist of  a  required  key string with '
            'a maximum of 128 characters, and an optional value string with '
            'a maximum of 256 characters. You can specify tags in key1=val1 '
            'format or to add a tag without value just write key name, key2.'
            ' For example: aws emr add-tags --resource-id j-XXXXXXYY --tags '
            'name="John Doe" age=29 male address="123 East NW Seattle" '},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        tags_list = parsed_args.tags

        tags_dictionary_list = []
        for tag in tags_list:
            if tag.find('=') == -1:
                key, value = tag, ''
            else:
                key, value = tag.split('=', 1)
            tags_dictionary_list.append({'Key': key, 'Value': value})

        emr = self._session.get_service('emr')
        parameters = {'ResourceId': parsed_args.resource_id,
                      'Tags': tags_dictionary_list}
        cli_operation_caller = CLIOperationCaller(self._session)
        cli_operation_caller.invoke(emr.get_operation('AddTags'), parameters,
                                    parsed_globals)
        return 0


class DescribeCluster(BasicCommand):
    NAME = 'describe-cluster'
    DESCRIPTION = ('Displays information'
                   ' about the specified cluster.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': 'The cluster-id of the cluster whose'
                      ' details are to be displayed.'}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        parameters = {}
        cluster_id = parsed_args.cluster_id
        parameters['ClusterId'] = cluster_id
        cliOperationCaller = CLIOperationCaller(self._session)

        LOG.debug("Calling DescribeCluster API with ClusterId: "+cluster_id)
        describe_cluster_result = cliOperationCaller.invoke(
            emr.get_operation('DescribeCluster'),
            parameters, parsed_globals)
        LOG.debug("Calling ListInstanceGroups with ClusterId: "+cluster_id)
        list_instance_groups_result = cliOperationCaller.invoke(
            emr.get_operation('ListInstanceGroups'),
            parameters, parsed_globals)
        LOG.debug("Calling ListBootstrapActions with ClusterId: "+cluster_id)
        list_bootstrap_actions_result = cliOperationCaller.invoke(
            emr.get_operation('ListBootstrapActions'),
            parameters, parsed_globals)

        if (describe_cluster_result == 0 and list_instance_groups_result == 0
                and list_bootstrap_actions_result == 0):
            return 0
        else:
            return 255


class ModifyClusterAttr(BasicCommand):
    NAME = 'modify-cluster-attributes'
    DESCRIPTION = ('Modify various cluster attributes')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
            'help_text': 'Cluster Id of cluster to modify attributes'},
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
