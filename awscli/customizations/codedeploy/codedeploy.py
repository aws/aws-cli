# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations import utils
from awscli.customizations.codedeploy.locationargs import \
    modify_revision_arguments
from awscli.customizations.codedeploy.push import Push
from awscli.customizations.codedeploy.register import Register
from awscli.customizations.codedeploy.deregister import Deregister
from awscli.customizations.codedeploy.install import Install
from awscli.customizations.codedeploy.uninstall import Uninstall


def initialize(cli):
    """
    The entry point for CodeDeploy high level commands.
    """
    cli.register(
        'building-command-table.main',
        change_name
    )
    cli.register(
        'building-command-table.deploy',
        inject_commands
    )
    cli.register(
        'building-argument-table.deploy.get-application-revision',
        modify_revision_arguments
    )
    cli.register(
        'building-argument-table.deploy.register-application-revision',
        modify_revision_arguments
    )
    cli.register(
        'building-argument-table.deploy.create-deployment',
        modify_revision_arguments
    )
    cli.register(
        'building-command-table.deploy',
        alias_commands
    )


def change_name(command_table, session, **kwargs):
    """
    Change all existing 'aws codedeploy' commands to 'aws deploy' commands.
    """
    utils.rename_command(command_table, 'codedeploy', 'deploy')


def alias_commands(command_table, **kwargs):
    utils.make_hidden_command_alias(
        command_table,
        existing_name='list-github-account-token-names',
        alias_name='list-git-hub-account-token-names',
    )
    utils.make_hidden_command_alias(
        command_table,
        existing_name='delete-github-account-token',
        alias_name='delete-git-hub-account-token',
    )


def inject_commands(command_table, session, **kwargs):
    """
    Inject custom 'aws deploy' commands.
    """
    command_table['push'] = Push(session)
    command_table['register'] = Register(session)
    command_table['deregister'] = Deregister(session)
    command_table['install'] = Install(session)
    command_table['uninstall'] = Uninstall(session)
