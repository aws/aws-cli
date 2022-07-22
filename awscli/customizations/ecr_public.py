# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def register_ecr_public_commands(cli):
    cli.register('building-command-table.ecr-public', _inject_commands)


def _inject_commands(command_table, session, **kwargs):
    command_table['get-login-password'] = ECRPublicGetLoginPassword(session)


class ECRPublicGetLoginPassword(BasicCommand):
    """Get a password to be used with container clients such as Docker"""
    NAME = 'get-login-password'

    DESCRIPTION = BasicCommand.FROM_FILE(
            'ecr-public/get-login-password_description.rst')

    def _run_main(self, parsed_args, parsed_globals):
        ecr_public_client = create_client_from_parsed_globals(
                self._session,
                'ecr-public',
                parsed_globals)
        result = ecr_public_client.get_authorization_token()
        auth = result['authorizationData']
        auth_token = b64decode(auth['authorizationToken']).decode()
        _, password = auth_token.split(':')
        sys.stdout.write(password)
        sys.stdout.write('\n')
        return 0
