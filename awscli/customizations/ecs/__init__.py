# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.customizations.ecs.deploy import ECSDeploy
from awscli.customizations.ecs.executecommand import ECSExecuteCommand
from awscli.customizations.ecs.executecommand import ExecuteCommandCaller


def initialize(cli):
    """
    The entry point for ECS high level commands.
    """
    cli.register('building-command-table.ecs', inject_commands)


def inject_commands(command_table, session, **kwargs):
    """
    Called when the ECS command table is being built. Used to inject new
    high level commands into the command list.
    """
    command_table['deploy'] = ECSDeploy(session)
    command_table['execute-command'] = ECSExecuteCommand(
        name='execute-command',
        parent_name='ecs',
        session=session,
        operation_model=session.get_service_model('ecs')
                    .operation_model('ExecuteCommand'),
        operation_caller=ExecuteCommandCaller(session),
    )
