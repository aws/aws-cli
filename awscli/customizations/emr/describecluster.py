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
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import helptext


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

        emrutils.display_response(self._session, describe_cluster,
                                  constructed_result, parsed_globals)

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
