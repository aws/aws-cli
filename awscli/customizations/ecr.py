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
    cli.register('building-command-table.ecr', _inject_get_login)


def _inject_get_login(command_table, session, **kwargs):
    command_table['get-login'] = ECRLogin(session)


class ECRLogin(BasicCommand):
    """Log in with docker login"""
    NAME = 'get-login'

    DESCRIPTION = BasicCommand.FROM_FILE('ecr/get-login_description.rst')

    ARG_TABLE = [
        {
            'name': 'registry-ids',
            'help_text': 'A list of AWS account IDs that correspond to the '
                         'Amazon ECR registries that you want to log in to.',
            'required': False,
            'nargs': '+'
        }
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
            sys.stdout.write('docker login -u %s -p %s -e none %s\n'
                             % (username, password, auth['proxyEndpoint']))
        return 0
