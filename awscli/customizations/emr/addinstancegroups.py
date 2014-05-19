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
from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import helptext
from awscli.customizations.emr import instancegroupsutils


class AddInstanceGroups(BasicCommand):
    NAME = 'add-instance-groups'
    DESCRIPTION = 'Adds an instance group to a running cluster.'
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'instance-groups', 'required': True,
         'help_text': helptext.INSTANCE_GROUPS,
         'schema': argumentschema.INSTANCE_GROUPS_SCHEMA}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        parameters = {'JobFlowId': parsed_args.cluster_id}
        parameters['InstanceGroups'] = \
            instancegroupsutils.build_instance_groups(
            parsed_args.instance_groups)

        emrutils.call_and_display_response(self._session, 'AddInstanceGroups',
                                           parameters, parsed_globals)
        return 0