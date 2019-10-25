# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.exceptions import ProfileNotFound
from botocore.exceptions import UnknownCredentialError
from botocore.credentials import JSONFileCache

from awscli.customizations.sso.login import LoginCommand
from awscli.customizations.sso.logout import LogoutCommand
from awscli.customizations.sso.utils import AWS_CREDS_CACHE_DIR


def register_sso_commands(event_emitter):
    event_emitter.register(
        'building-command-table.sso', add_sso_commands,
    )
    event_emitter.register(
        'session-initialized', inject_json_file_cache,
        unique_id='inject_sso_json_file_cache'
    )


def add_sso_commands(command_table, session, **kwargs):
    command_table['login'] = LoginCommand(session)
    command_table['logout'] = LogoutCommand(session)


def inject_json_file_cache(session, **kwargs):
    try:
        cred_chain = session.get_component('credential_provider')
        sso_provider = cred_chain.get_provider('sso')
        sso_provider.cache = JSONFileCache(AWS_CREDS_CACHE_DIR)
    except (ProfileNotFound, UnknownCredentialError):
        return
