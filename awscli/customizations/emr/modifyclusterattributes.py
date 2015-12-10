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
            'help_text': 'Set termination protection on or off'},
        {'name': 'no-termination-protected', 'required': False, 'action':
            'store_true', 'group_name': 'terminate',
            'help_text': 'Set termination protection on or off'},
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
        if not(args.termination_protected or args.no_termination_protected or
               args.visible_to_all_users or args.no_visible_to_all_users):
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
        return 0
