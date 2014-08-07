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
from awscli.customizations.emr import constants
from botocore.exceptions import NoCredentialsError


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
    EXAMPLES = BasicCommand.FROM_FILE('emr', 'describe-cluster.rst')

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        describe_cluster = emr.get_operation('DescribeCluster')
        parameters = {'ClusterId': parsed_args.cluster_id}

        describe_cluster_result = self._call(describe_cluster, parameters,
                                             parsed_globals)
        list_instance_groups_result = self._call(
            emr.get_operation('ListInstanceGroups'), parameters,
            parsed_globals)

        list_bootstrap_actions_result = self._call(
            emr.get_operation('ListBootstrapActions'),
            parameters, parsed_globals)

        master_public_dns = self._find_master_public_dns(
            cluster_id=parsed_args.cluster_id,
            parsed_globals=parsed_globals)

        constructed_result = self._construct_result(
            describe_cluster_result,
            list_instance_groups_result,
            list_bootstrap_actions_result,
            master_public_dns)

        emrutils.display_response(self._session, describe_cluster,
                                  constructed_result, parsed_globals)

        return 0

    def _find_master_public_dns(self, cluster_id, parsed_globals):
        return emrutils.find_master_public_dns(
            session=self._session, cluster_id=cluster_id,
            parsed_globals=parsed_globals)

    def _call(self, operation_object, parameters, parsed_globals):
        # We could get an error from get_endpoint() about not having
        # a region configured.  Before this happens we want to check
        # for credentials so we can give a good error message.
        result = []
        if not self._session.get_credentials():
            raise NoCredentialsError()
        endpoint = operation_object.service.get_endpoint(
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        if operation_object.can_paginate and parsed_globals.paginate:
            pages = operation_object.paginate(endpoint, **parameters)
            key = None
            for page in pages:
                http_response = page[0]
                if http_response.status_code == 200:
                    response_data = page[1]
                    keys = response_data.keys()
                    key = self._get_key_of_result(keys)
                    if key is not None:
                        result += response_data.get(key)

            if key is not None:
                return {key: result}
            else:
                return None
        else:
            http_response, response_data = operation_object.call(endpoint,
                                                                 **parameters)
            return response_data

    def _get_key_of_result(self, keys):
        # Return the first key that is not "Marker"
        for key in keys:
            if key != "Marker":
                return key

    def _construct_result(
            self, describe_cluster_result, list_instance_groups_result,
            list_bootstrap_actions_result, master_public_dns):
        result = describe_cluster_result
        result['Cluster']['MasterPublicDnsName'] = master_public_dns
        result['Cluster']['InstanceGroups'] = []
        result['Cluster']['BootstrapActions'] = []

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
