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


from awscli.arguments import CustomArgument
from awscli.customizations.emr import helptext
from awscli.customizations.emr import exceptions
from awscli.customizations.emr import constants


def modify_list_clusters_argument(argument_table, **kwargs):
    argument_table['cluster-states'] = \
        ClusterStatesArgument(
            name='cluster-states',
            help_text=helptext.LIST_CLUSTERS_CLUSTER_STATES,
            nargs='+')
    argument_table['active'] = \
        ActiveStateArgument(
            name='active', help_text=helptext.LIST_CLUSTERS_STATE_FILTERS,
            action='store_true', group_name='states_filter')
    argument_table['terminated'] = \
        TerminatedStateArgument(
            name='terminated',
            action='store_true', group_name='states_filter')
    argument_table['failed'] = \
        FailedStateArgument(
            name='failed', action='store_true', group_name='states_filter')
    argument_table['created-before'] = CreatedBefore(
        name='created-before', help_text=helptext.LIST_CLUSTERS_CREATED_BEFORE,
        cli_type_name='timestamp')
    argument_table['created-after'] = CreatedAfter(
        name='created-after', help_text=helptext.LIST_CLUSTERS_CREATED_AFTER,
        cli_type_name='timestamp')


class ClusterStatesArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is not None:
            if (parameters.get('ClusterStates') is not None and
                    len(parameters.get('ClusterStates')) > 0):
                raise exceptions.ClusterStatesFilterValidationError()
            parameters['ClusterStates'] = value


class ActiveStateArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is True:
            if (parameters.get('ClusterStates') is not None and
                    len(parameters.get('ClusterStates')) > 0):
                raise exceptions.ClusterStatesFilterValidationError()
            parameters['ClusterStates'] = constants.LIST_CLUSTERS_ACTIVE_STATES


class TerminatedStateArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is True:
            if (parameters.get('ClusterStates') is not None and
                    len(parameters.get('ClusterStates')) > 0):
                raise exceptions.ClusterStatesFilterValidationError()
            parameters['ClusterStates'] = \
                constants.LIST_CLUSTERS_TERMINATED_STATES


class FailedStateArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is True:
            if (parameters.get('ClusterStates') is not None and
                    len(parameters.get('ClusterStates')) > 0):
                raise exceptions.ClusterStatesFilterValidationError()
            parameters['ClusterStates'] = constants.LIST_CLUSTERS_FAILED_STATES


class CreatedBefore(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        parameters['CreatedBefore'] = value


class CreatedAfter(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        parameters['CreatedAfter'] = value
