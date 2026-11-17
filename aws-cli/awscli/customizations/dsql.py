# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import uni_print


def register_dsql_customizations(cli):
    cli.register(
        'building-command-table.dsql', _add_generate_dsql_db_connect_auth_token
    )
    cli.register(
        'building-command-table.dsql',
        _add_generate_dsql_db_connect_admin_auth_token,
    )


def _add_generate_dsql_db_connect_auth_token(command_table, session, **kwargs):
    command = GenerateDBConnectAuthTokenCommand(session)
    command_table['generate-db-connect-auth-token'] = command


def _add_generate_dsql_db_connect_admin_auth_token(
    command_table, session, **kwargs
):
    command = GenerateDBConnectAdminAuthTokenCommand(session)
    command_table['generate-db-connect-admin-auth-token'] = command


class GenerateDBConnectAuthTokenCommand(BasicCommand):
    NAME = 'generate-db-connect-auth-token'
    DESCRIPTION = 'Generates an authorization token used to connect to a DSQL database with IAM credentials.'
    ARG_TABLE = [
        {
            'name': 'hostname',
            'required': True,
            'help_text': 'Cluster endpoint e.g. http://test.example.com',
        },
        {
            'name': 'expires-in',
            'cli_type_name': 'integer',
            'default': 900,
            'required': False,
            'help_text': 'Token expiry duration in seconds e.g. 3600. Default is 900 seconds.',
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        dsql = self._session.create_client(
            'dsql',
            parsed_globals.region,
            parsed_globals.endpoint_url,
            parsed_globals.verify_ssl,
        )

        token = dsql.generate_db_connect_auth_token(
            parsed_args.hostname, parsed_globals.region, parsed_args.expires_in
        )
        uni_print(token)
        uni_print('\n')
        return 0


class GenerateDBConnectAdminAuthTokenCommand(BasicCommand):
    NAME = 'generate-db-connect-admin-auth-token'
    DESCRIPTION = 'Generates an Admin authorization token used to connect to a DSQL database with IAM credentials.'
    ARG_TABLE = [
        {
            'name': 'hostname',
            'required': True,
            'help_text': 'Cluster endpoint e.g. http://test.example.com',
        },
        {
            'name': 'expires-in',
            'cli_type_name': 'integer',
            'default': 900,
            'required': False,
            'help_text': 'Token expiry duration in seconds e.g. 3600. Default is 900 seconds.',
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        dsql = self._session.create_client(
            'dsql',
            parsed_globals.region,
            parsed_globals.endpoint_url,
            parsed_globals.verify_ssl,
        )

        token = dsql.generate_db_connect_admin_auth_token(
            parsed_args.hostname, parsed_globals.region, parsed_args.expires_in
        )
        uni_print(token)
        uni_print('\n')
        return 0
