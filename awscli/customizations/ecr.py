# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import create_client_from_parsed_globals

from base64 import b64decode
import sys


def register_ecr_commands(cli):
    cli.register('building-command-table.ecr', _inject_commands)


def _inject_commands(command_table, session, **kwargs):
    command_table['get-login'] = ECRLogin(session)
    command_table['get-login-password'] = ECRGetLoginPassword(session)


class ECRLogin(BasicCommand):
    """Log in with 'docker login'"""
    NAME = 'get-login'

    DESCRIPTION = BasicCommand.FROM_FILE('ecr/get-login_description.rst')

    ARG_TABLE = [
        {
            'name': 'registry-ids',
            'help_text': 'A list of AWS account IDs that correspond to the '
                         'Amazon ECR registries that you want to log in to.',
            'required': False,
            'nargs': '+'
        },
        {
            'name': 'include-email',
            'action': 'store_true',
            'group_name': 'include-email',
            'dest': 'include_email',
            'default': True,
            'required': False,
            'help_text': (
                "Specify if the '-e' flag should be included in the "
                "'docker login' command.  The '-e' option has been deprecated "
                "and is removed in Docker version 17.06 and later.  You must "
                "specify --no-include-email if you're using Docker version "
                "17.06 or later.  The default behavior is to include the "
                "'-e' flag in the 'docker login' output."),
        },
        {
            'name': 'no-include-email',
            'help_text': 'Include email arg',
            'action': 'store_false',
            'default': True,
            'group_name': 'include-email',
            'dest': 'include_email',
            'required': False,
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        ecr_client = create_client_from_parsed_globals(
            self._session, 'ecr', parsed_globals)
        if not parsed_args.registry_ids:
            result = ecr_client.get_authorization_token()
        else:
            result = ecr_client.get_authorization_token(
                registryIds=parsed_args.registry_ids)
        for auth in result['authorizationData']:
            auth_token = b64decode(auth['authorizationToken']).decode()
            username, password = auth_token.split(':')
            command = ['docker', 'login', '-u', username, '-p', password]
            if parsed_args.include_email:
                command.extend(['-e', 'none'])
            command.append(auth['proxyEndpoint'])
            sys.stdout.write(' '.join(command))
            sys.stdout.write('\n')
        return 0


class ECRGetLoginPassword(BasicCommand):
    """Get a password to be used with container clients such as Docker"""
    NAME = 'get-login-password'

    DESCRIPTION = BasicCommand.FROM_FILE(
            'ecr/get-login-password_description.rst')

    def _run_main(self, parsed_args, parsed_globals):
        ecr_client = create_client_from_parsed_globals(
                self._session,
                'ecr',
                parsed_globals)
        result = ecr_client.get_authorization_token()
        auth = result['authorizationData'][0]
        auth_token = b64decode(auth['authorizationToken']).decode()
        _, password = auth_token.split(':')
        sys.stdout.write(password)
        sys.stdout.write('\n')
        return 0
