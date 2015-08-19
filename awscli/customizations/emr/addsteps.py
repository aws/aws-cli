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
from awscli.customizations.emr import steputils
from awscli.customizations.emr.command import Command


class AddSteps(Command):
    NAME = 'add-steps'
    DESCRIPTION = ('Add a list of steps to a cluster.')
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID
         },
        {'name': 'steps',
         'required': True,
         'nargs': '+',
         'schema': argumentschema.STEPS_SCHEMA,
         'help_text': helptext.STEPS
         }
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        parsed_steps = parsed_args.steps

        release_label = emrutils.get_release_label(
            parsed_args.cluster_id, self._session, self.region,
            parsed_globals.endpoint_url, parsed_globals.verify_ssl)

        step_list = steputils.build_step_config_list(
            parsed_step_list=parsed_steps, region=self.region,
            release_label=release_label)
        parameters = {
            'JobFlowId': parsed_args.cluster_id,
            'Steps': step_list
        }

        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0
