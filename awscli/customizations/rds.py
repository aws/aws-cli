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
"""
This customization splits the modify-option-group into two separate commands:

* ``add-option-group``
* ``remove-option-group``

In both commands the ``--options-to-remove`` and ``--options-to-add`` args will
be renamed to just ``--options``.

All the remaining args will be available in both commands (which proxy
modify-option-group).

"""

from awscli.clidriver import ServiceOperation
from awscli.clidriver import CLIOperationCaller
from awscli.customizations import utils


def register_rds_modify_split(cli):
    cli.register('building-command-table.rds', _building_command_table)
    cli.register('building-argument-table.rds.add-option-to-option-group',
                 _rename_add_option)
    cli.register('building-argument-table.rds.remove-option-from-option-group',
                 _rename_remove_option)


def _rename_add_option(argument_table, **kwargs):
    utils.rename_argument(argument_table, 'options-to-include',
                          new_name='options')
    del argument_table['options-to-remove']


def _rename_remove_option(argument_table, **kwargs):
    utils.rename_argument(argument_table, 'options-to-remove',
                          new_name='options')
    del argument_table['options-to-include']


def _building_command_table(command_table, session, **kwargs):
    # Hooked up to building-command-table.rds
    # We don't need the modify-option-group operation.
    del command_table['modify-option-group']
    # We're going to replace modify-option-group with two commands:
    # add-option-group and remove-option-group
    rds_model = session.get_service_model('rds')
    modify_operation_model = rds_model.operation_model('ModifyOptionGroup')
    command_table['add-option-to-option-group'] = ServiceOperation(
        parent_name='rds', name='add-option-to-option-group',
        operation_caller=CLIOperationCaller(session),
        session=session,
        operation_model=modify_operation_model)
    command_table['remove-option-from-option-group'] = ServiceOperation(
        parent_name='rds', name='remove-option-from-option-group',
        session=session,
        operation_model=modify_operation_model,
        operation_caller=CLIOperationCaller(session))
