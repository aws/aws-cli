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
from awscli.customizations import utils
from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3.subcommands import ListCommand, WebsiteCommand, \
    CpCommand, MvCommand, RmCommand, SyncCommand, MbCommand, RbCommand
from awscli.customizations.s3.syncstrategy.register import \
    register_sync_strategies


def awscli_initialize(cli):
    """
    This function is require to use the plugin.  It calls the functions
    required to add all neccessary commands and parameters to the CLI.
    This function is necessary to install the plugin using a configuration
    file
    """
    cli.register("building-command-table.main", add_s3)
    cli.register('building-command-table.sync', register_sync_strategies)


def s3_plugin_initialize(event_handlers):
    """
    This is a wrapper to make the plugin built-in to the cli as opposed
    to specifiying it in the configuration file.
    """
    awscli_initialize(event_handlers)


def add_s3(command_table, session, **kwargs):
    """
    This creates a new service object for the s3 plugin.  It sends the
    old s3 commands to the namespace ``s3api``.
    """
    utils.rename_command(command_table, 's3', 's3api')
    command_table['s3'] = S3(session)


class S3(BasicCommand):
    NAME = 's3'
    DESCRIPTION = BasicCommand.FROM_FILE('s3/_concepts.rst')
    SYNOPSIS = "aws s3 <Command> [<Arg> ...]"
    SUBCOMMANDS = [
        {'name': 'ls', 'command_class': ListCommand},
        {'name': 'website', 'command_class': WebsiteCommand},
        {'name': 'cp', 'command_class': CpCommand},
        {'name': 'mv', 'command_class': MvCommand},
        {'name': 'rm', 'command_class': RmCommand},
        {'name': 'sync', 'command_class': SyncCommand},
        {'name': 'mb', 'command_class': MbCommand},
        {'name': 'rb', 'command_class': RbCommand}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            raise ValueError("usage: aws [options] <command> <subcommand> "
                             "[parameters]\naws: error: too few arguments")
