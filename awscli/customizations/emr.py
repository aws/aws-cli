# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
import logging
import sys


from awscli.customizations.commands import BasicCommand
from awscli.customizations.service import Service
from awscli.formatter import get_formatter
from awscli.clidriver import CLIOperationCaller

LOG = logging.getLogger(__name__)


def emr_initialize(cli):
    """
    The entry point for EMR high level commands.
    """
    cli.register('building-command-table.emr', register_commands)


def register_commands(command_table, session, **kwargs):
    """
    Called when the EMR command table is being built. Used to inject new
    high level commands into the command list. These high level commands
    must not collide with existing low-level API call names.
    """
    command_table['terminate-clusters'] = TerminateClusters(session)


class TerminateClusters(BasicCommand):
    NAME = 'terminate-clusters'
    DESCRIPTION = ('terminate-clusters shuts down a list of clusters.')
    ARG_TABLE = [
        {'name': 'cluster-ids', 'nargs': '+', 'required': True,
            'help_text': 'A list of clusters to be shutdown\n'}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        parameters = {'JobFlowIds': parsed_args.cluster_ids}
        cliOperationCaller = CLIOperationCaller(self._session)
        cliOperationCaller.invoke(emr.get_operation('TerminateJobFlows'),
                                  parameters, parsed_globals)
        return 0
