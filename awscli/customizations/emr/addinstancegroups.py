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


from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import helptext
from awscli.customizations.emr import instancegroupsutils
from awscli.customizations.emr.command import Command


class AddInstanceGroups(Command):
    NAME = 'add-instance-groups'
    DESCRIPTION = 'Adds an instance group to a running cluster.'
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'instance-groups', 'required': True,
         'help_text': helptext.INSTANCE_GROUPS,
         'schema': argumentschema.INSTANCE_GROUPS_SCHEMA}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        parameters = {'JobFlowId': parsed_args.cluster_id}
        parameters['InstanceGroups'] = \
            instancegroupsutils.build_instance_groups(
            parsed_args.instance_groups)

        add_instance_groups_response = emrutils.call(
            self._session, 'add_instance_groups', parameters,
            self.region, parsed_globals.endpoint_url,
            parsed_globals.verify_ssl)

        constructed_result = self._construct_result(
            add_instance_groups_response)

        emrutils.display_response(self._session, 'add_instance_groups',
                                  constructed_result, parsed_globals)
        return 0

    def _construct_result(self, add_instance_groups_result):
        jobFlowId = None
        instanceGroupIds = None
        if add_instance_groups_result is not None:
            jobFlowId = add_instance_groups_result.get('JobFlowId')
            instanceGroupIds = add_instance_groups_result.get(
                'InstanceGroupIds')

        if jobFlowId is not None and instanceGroupIds is not None:
            return {'ClusterId': jobFlowId,
                    'InstanceGroupIds': instanceGroupIds}
        else:
            return {}
