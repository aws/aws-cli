# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import alias_command, rename_command


def register_rename_signin_commands(event_emitter):
    event_emitter.register(
        'building-command-table.signin',
        rename_signin_commands,
    )


def rename_signin_commands(command_table, **kwargs):
    """Rename o-auth2 commands to oauth2.

    create-o-auth2-token was released without a rename, so we keep a
    hidden alias for backwards compatibility.
    """
    alias_command(
        command_table, 'create-o-auth2-token', 'create-oauth2-token'
    )
    for old_name in (
        'create-o-auth2-token-with-iam',
        'introspect-o-auth2-token-with-iam',
        'revoke-o-auth2-token-with-iam',
    ):
        new_name = old_name.replace('-o-auth2-', '-oauth2-')
        rename_command(command_table, old_name, new_name)
