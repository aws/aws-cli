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
from awscli.customizations.emr import helptext
from awscli.customizations.emr.command import Command


class TerminateClusters(Command):
    NAME = 'terminate-clusters'
    DESCRIPTION = helptext.TERMINATE_CLUSTERS
    ARG_TABLE = [{
        'name': 'cluster-ids', 'nargs': '+', 'required': True,
        'help_text': '<p>A list of clusters to terminate.</p>',
        'schema': {'type': 'array', 'items': {'type': 'string'}},
    }]

    def _run_main_command(self, parsed_args, parsed_globals):
        parameters = {'JobFlowIds': parsed_args.cluster_ids}
        emrutils.call_and_display_response(self._session,
                                           'TerminateJobFlows', parameters,
                                           parsed_globals)
        return 0
