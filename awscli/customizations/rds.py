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
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print
from awscli.utils import create_nested_client


def register_rds_modify_split(cli):
    cli.register('building-command-table.rds', _building_command_table)
    cli.register('building-argument-table.rds.add-option-to-option-group',
                 _rename_add_option)
    cli.register('building-argument-table.rds.remove-option-from-option-group',
                 _rename_remove_option)


def register_add_generate_db_auth_token(cli):
    cli.register('building-command-table.rds', _add_generate_db_auth_token)


def _add_generate_db_auth_token(command_table, session, **kwargs):
    command = GenerateDBAuthTokenCommand(session)
    command_table['generate-db-auth-token'] = command


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


class GenerateDBAuthTokenCommand(BasicCommand):
    NAME = 'generate-db-auth-token'
    DESCRIPTION = (
        'Generates an auth token used to connect to a db with IAM credentials.'
    )
    ARG_TABLE = [
        {'name': 'hostname', 'required': True,
         'help_text': 'The hostname of the database to connect to.'},
        {'name': 'port', 'cli_type_name': 'integer', 'required': True,
         'help_text': 'The port number the database is listening on.'},
        {'name': 'username', 'required': True,
         'help_text': 'The username to log in as.'}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        rds = create_nested_client(
            self._session,
            'rds',
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        token = rds.generate_db_auth_token(
            DBHostname=parsed_args.hostname,
            Port=parsed_args.port,
            DBUsername=parsed_args.username
        )
        uni_print(token)
        uni_print('\n')
        return 0
