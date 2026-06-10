# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from awscli.customizations.agenttoolkit.add_skill import AddSkillCommand
from awscli.customizations.agenttoolkit.get_skill_file import (
    GetSkillFileCommand,
)
from awscli.customizations.agenttoolkit.list_installed_skills import (
    ListInstalledSkillsCommand,
)
from awscli.customizations.agenttoolkit.remove_skill import RemoveCommand
from awscli.customizations.agenttoolkit.update_skill import UpdateSkillCommand
from awscli.customizations.agenttoolkit.utils import (
    NONPROD_ACCESS_TOKEN_ENV_VAR,
    NONPROD_ACCESS_TOKEN_HEADER,
)

MODELED_COMMAND_ALLOWLIST = {
    'get-skill',
    'list-skills',
    'search-skills',
}

MODELED_COMMAND_RENAMES = {
    'get-skill': 'get-skill-metadata',
    'list-skills': 'list-available-skills',
}


def register_agent_toolkit_commands(event_handlers):
    event_handlers.register(
        'building-command-table.agent-toolkit', _inject_commands
    )
    event_handlers.register(
        'before-sign.agenttoolkit.*', _inject_nonprod_header
    )


def _inject_nonprod_header(request, **kwargs):
    # Only attach the token when testing internally against the gamma endpoint
    if '.gamma.agent-toolkit' not in request.url:
        return
    token = os.environ.get(NONPROD_ACCESS_TOKEN_ENV_VAR)
    if token:
        request.headers[NONPROD_ACCESS_TOKEN_HEADER] = token


def _rename_service(command_table, session, **kwargs):
    service_cmd = command_table.pop('agenttoolkit', None)
    if service_cmd is not None:
        service_cmd._name = 'agent-toolkit'
        command_table['agent-toolkit'] = service_cmd


def _inject_commands(command_table, session, **kwargs):
    # Remove any modeled commands not in our allowlist, then rename the rest
    for name in list(command_table):
        if name not in MODELED_COMMAND_ALLOWLIST:
            del command_table[name]

    for old_name, new_name in MODELED_COMMAND_RENAMES.items():
        cmd = command_table.pop(old_name, None)
        if cmd is not None:
            cmd._name = new_name
            command_table[new_name] = cmd

    # Add custom commands
    command_table['get-skill-file'] = GetSkillFileCommand(session)
    command_table['add-skill'] = AddSkillCommand(session)
    command_table['list-installed-skills'] = ListInstalledSkillsCommand(
        session
    )
    command_table['remove-skill'] = RemoveCommand(session)
    command_table['update-skill'] = UpdateSkillCommand(session)
