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


def register_rename_config(cli):
    cli.register('building-command-table.main', change_name)


def change_name(command_table, session, **kwargs):
    """
    Change all existing ``aws config`` commands to ``aws configservice``
    commands.
    """
    utils.rename_command(command_table, 'config', 'configservice')
