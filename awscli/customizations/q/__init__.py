# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.q.chat import ChatCommand
from awscli.customizations.q.uninstall import UninstallCommand
from awscli.customizations.q.update import UpdateCommand
from awscli.customizations.q.version import VersionCommand


def register_q_commands(event_handlers):
    event_handlers.register('building-command-table.main', inject_commands)


def inject_commands(command_table, session, **kwargs):
    command_table['q'] = QCommand(session)


class QCommand(BasicCommand):
    # 'TODO help prints "System Message: WARNING/2 (<string>:, line 7)"
    # but not figuring out yet since naming may still change
    NAME = 'q'
    SYNOPSIS = 'q <command> [<args>]'
    DESCRIPTION = (
        'You can use Amazon Q Developer to translate natural language to '
        'AWS CLI commands. Run ``aws q chat`` to launch the Q CLI. You can '
        'update to the latest version of the Q plugin with ``aws q update``.'
    )
    SUBCOMMANDS = [
        {'name': 'chat', 'command_class': ChatCommand},
        {'name': 'version', 'command_class': VersionCommand},
        {'name': 'update', 'command_class': UpdateCommand},
        {'name': 'uninstall', 'command_class': UninstallCommand},
    ]
