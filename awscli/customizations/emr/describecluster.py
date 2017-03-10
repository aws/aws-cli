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

from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import helptext
from awscli.customizations.emr.command import Command
from botocore.exceptions import NoCredentialsError


class DescribeCluster(Command):
    NAME = 'describe-cluster'
    DESCRIPTION = ('Provides  cluster-level details including status, hardware'
                   ' and software configuration, VPC settings, bootstrap'
                   ' actions, instance groups and so on. For information about'
                   ' the cluster steps, see <code>list-steps</code>.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        parameters = {'ClusterId': parsed_args.cluster_id}
        list_instance_fleets_result = None
        list_instance_groups_result = None
        is_fleet_based_cluster = False

        describe_cluster_result = self._call(
            self._session, 'describe_cluster', parameters, parsed_globals)


        if 'Cluster' in describe_cluster_result:
            describe_cluster = describe_cluster_result['Cluster']
            if describe_cluster.get('InstanceCollectionType') == constants.INSTANCE_FLEET_TYPE:
                is_fleet_based_cluster = True

            if 'Ec2InstanceAttributes' in describe_cluster:
                ec2_instance_attr_keys = \
                    describe_cluster['Ec2InstanceAttributes'].keys()
                ec2_instance_attr = \
                    describe_cluster['Ec2InstanceAttributes']
        else:
            ec2_instance_attr_keys = {}

        if is_fleet_based_cluster:
            list_instance_fleets_result = self._call(
                self._session, 'list_instance_fleets', parameters,
                parsed_globals)
        else:
            list_instance_groups_result = self._call(
                self._session, 'list_instance_groups', parameters,
                parsed_globals)

        list_bootstrap_actions_result = self._call(
            self._session, 'list_bootstrap_actions',
            parameters, parsed_globals)

        constructed_result = self._construct_result(
            describe_cluster_result,
            list_instance_fleets_result,
            list_instance_groups_result,
            list_bootstrap_actions_result)

        emrutils.display_response(self._session, 'describe_cluster',
                                  constructed_result, parsed_globals)

        return 0

    def _call(self, session, operation_name, parameters, parsed_globals):
        return emrutils.call(
            session, operation_name, parameters,
            region_name=self.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)

    def _get_key_of_result(self, keys):
        # Return the first key that is not "Marker"
        for key in keys:
            if key != "Marker":
                return key

    def _construct_result(
            self, describe_cluster_result, list_instance_fleets_result,
            list_instance_groups_result, list_bootstrap_actions_result):
        result = describe_cluster_result
        result['Cluster']['BootstrapActions'] = []

        if (list_instance_fleets_result is not None and
                list_instance_fleets_result.get('InstanceFleets') is not None):
            result['Cluster']['InstanceFleets'] = \
                list_instance_fleets_result.get('InstanceFleets')
        if (list_instance_groups_result is not None and
                list_instance_groups_result.get('InstanceGroups') is not None):
            result['Cluster']['InstanceGroups'] = \
                list_instance_groups_result.get('InstanceGroups')
        if (list_bootstrap_actions_result is not None and
                list_bootstrap_actions_result.get('BootstrapActions')
                is not None):
            result['Cluster']['BootstrapActions'] = \
                list_bootstrap_actions_result['BootstrapActions']

        return result
