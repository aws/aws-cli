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

from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions
from awscli.customizations.emr import helptext
from awscli.customizations.emr.command import Command


class ModifyClusterAttr(Command):
    NAME = 'modify-cluster-attributes'
    DESCRIPTION = ("Modifies the cluster attributes 'visible-to-all-users', "
                   " 'termination-protected' and 'unhealthy-node-replacement'.")
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
            'help_text': helptext.CLUSTER_ID},
        {'name': 'visible-to-all-users', 'required': False, 'action':
            'store_true', 'group_name': 'visible',
            'help_text': helptext.VISIBILITY},
        {'name': 'no-visible-to-all-users', 'required': False, 'action':
            'store_true', 'group_name': 'visible',
            'help_text': helptext.VISIBILITY},
        {'name': 'termination-protected', 'required': False, 'action':
            'store_true', 'group_name': 'terminate',
            'help_text': 'Set termination protection on or off'},
        {'name': 'no-termination-protected', 'required': False, 'action':
            'store_true', 'group_name': 'terminate',
            'help_text': 'Set termination protection on or off'},
        {'name': 'auto-terminate', 'required': False, 'action':
            'store_true', 'group_name': 'auto_terminate',
            'help_text': 'Set cluster auto terminate after completing all the steps on or off'},
        {'name': 'no-auto-terminate', 'required': False, 'action':
            'store_true', 'group_name': 'auto_terminate',
            'help_text': 'Set cluster auto terminate after completing all the steps on or off'},
        {'name': 'unhealthy-node-replacement', 'required': False, 'action':
            'store_true', 'group_name': 'UnhealthyReplacement',
            'help_text': 'Set Unhealthy Node Replacement on or off'},
        {'name': 'no-unhealthy-node-replacement', 'required': False, 'action':
            'store_true', 'group_name': 'UnhealthyReplacement',
            'help_text': 'Set Unhealthy Node Replacement on or off'},
    ]

    def _run_main_command(self, args, parsed_globals):

        if (args.visible_to_all_users and args.no_visible_to_all_users):
            raise exceptions.MutualExclusiveOptionError(
                option1='--visible-to-all-users',
                option2='--no-visible-to-all-users')
        if (args.termination_protected and args.no_termination_protected):
            raise exceptions.MutualExclusiveOptionError(
                option1='--termination-protected',
                option2='--no-termination-protected')
        if (args.auto_terminate and args.no_auto_terminate):
            raise exceptions.MutualExclusiveOptionError(
                option1='--auto-terminate',
                option2='--no-auto-terminate')
        if (args.unhealthy_node_replacement and args.no_unhealthy_node_replacement):
            raise exceptions.MutualExclusiveOptionError(
                option1='--unhealthy-node-replacement',
                option2='--no-unhealthy-node-replacement')
        if not(args.termination_protected or args.no_termination_protected or
               args.visible_to_all_users or args.no_visible_to_all_users or
               args.auto_terminate or args.no_auto_terminate or
               args.unhealthy_node_replacement or args.no_unhealthy_node_replacement):
            raise exceptions.MissingClusterAttributesError()

        if (args.visible_to_all_users or args.no_visible_to_all_users):
            visible = (args.visible_to_all_users and
                       not args.no_visible_to_all_users)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'VisibleToAllUsers': visible}
            emrutils.call_and_display_response(self._session,
                                               'SetVisibleToAllUsers',
                                               parameters, parsed_globals)

        if (args.termination_protected or args.no_termination_protected):
            protected = (args.termination_protected and
                         not args.no_termination_protected)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'TerminationProtected': protected}
            emrutils.call_and_display_response(self._session,
                                               'SetTerminationProtection',
                                               parameters, parsed_globals)

        if (args.auto_terminate or args.no_auto_terminate):
            auto_terminate = (args.auto_terminate and
                         not args.no_auto_terminate)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'KeepJobFlowAliveWhenNoSteps': not auto_terminate}
            emrutils.call_and_display_response(self._session,
                                               'SetKeepJobFlowAliveWhenNoSteps',
                                               parameters, parsed_globals)
            
        if (args.unhealthy_node_replacement or args.no_unhealthy_node_replacement):
            protected = (args.unhealthy_node_replacement and
                         not args.no_unhealthy_node_replacement)
            parameters = {'JobFlowIds': [args.cluster_id],
                          'UnhealthyNodeReplacement': protected}
            emrutils.call_and_display_response(self._session,
                                               'SetUnhealthyNodeReplacement',
                                               parameters, parsed_globals)

        return 0
