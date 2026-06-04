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
import sys

from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    SKILL_NAME_ARG,
    create_client,
    get_skill_download,
    install_skill,
    read_installed_version,
    resolve_agents,
    resolve_latest_version,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError


class UpdateSkillCommand(BasicCommand):
    NAME = 'update-skill'
    DESCRIPTION = (
        'Update an installed AWS skill to the latest version. '
        'Compares the locally installed version against the available skills '
        'and downloads the newer version if available. By default the skill is '
        'updated for all detected agents, use ``--agent`` to update the skill '
        'for only a specific tool.'
    )
    ARG_TABLE = [
        SKILL_NAME_ARG,
        AGENT_ARG,
    ]

    def __init__(self, session, stream=None, client=None, agent_configs=None):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        self._client = client
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        skill_name = parsed_args.skill_name
        agent_filter = getattr(parsed_args, 'agent', None)

        agents = resolve_agents(agent_filter, self._agent_configs)
        if not agents:
            raise ParamValidationError('No supported AI coding agents found.')

        installed_agents = [
            agent
            for agent in agents
            if any(
                skill.name == skill_name
                for skill in agent.get_installed_skills()
            )
        ]
        if not installed_agents:
            raise ParamValidationError(
                f'Skill "{skill_name}" is not installed.'
            )

        client = self._client or create_client(self._session, parsed_globals)
        remote_version = resolve_latest_version(client, skill_name)

        outdated = []
        for agent in installed_agents:
            skill_dir = os.path.join(agent.skills_path, skill_name)
            local_version = read_installed_version(skill_dir)
            if local_version != remote_version:
                outdated.append(agent)

        if not outdated:
            self._stream.write(
                f'{skill_name} is already up to date ({remote_version}).\n'
            )
            return 0

        zip_bytes, checksum, version = get_skill_download(
            client, skill_name, version=remote_version
        )
        install_skill(
            skill_name,
            version,
            zip_bytes,
            checksum,
            outdated,
            self._stream,
            action='Updated',
        )
        return 0
