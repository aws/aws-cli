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


from awscli.customizations.commands import BasicCommand
from awscli.customizations.service import Service
from awscli.formatter import get_formatter
from awscli.clidriver import CLIOperationCaller

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


class AddTags(BasicCommand):
    NAME = 'add-tags'
    DESCRIPTION = ('Add tags to the cluster')
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
            'name="John Doe" age=29 male address="123 East NW, Seattle" '},
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
