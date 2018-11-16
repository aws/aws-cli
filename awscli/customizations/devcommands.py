# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def register_dev_commands(event_handlers):
    event_handlers.register('building-command-table.main',
                            CLIDevCommand.add_command)


# This is adding a top level placeholder command to add dev commands.
# Each specific customization can add to this command via the
# building-command-table event name.
class CLIDevCommand(BasicCommand):
    NAME = 'cli-dev'
    DESCRIPTION = (
        'Internal commands for AWS CLI development.\n'
        'These commands are not intended for normal end usage. These '
        'commands are used to help develop and debug the AWS CLI.\n'
        'Do not rely on these commands, backwards compatibility '
        'is not guaranteed.  Any of these commands under "aws cli-dev" '
        'may be removed in future versions.\n'
    )
    SYNOPSIS = 'aws cli-dev [dev-command]'
