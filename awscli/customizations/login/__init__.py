# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from awscli.customizations.login.login import LoginCommand
from awscli.customizations.login.logout import LogoutCommand


def register_login_cmds(cli):
    cli.register('building-command-table.main', LoginCommand.add_command)
    cli.register('building-command-table.main', LogoutCommand.add_command)
