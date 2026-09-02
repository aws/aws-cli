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
    agents_with_skill,
    collect_installed_skills,
    create_client,
    get_skill_download,
    install_skill,
    read_installed_version,
    resolve_agents,
    resolve_latest_version,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError

UPDATE_SKILL_NAME_ARG = {**SKILL_NAME_ARG, 'required': False}

ALL_SKILLS_ARG = {
    'name': 'all',
    'help_text': (
        'Update every installed AWS skill that is out of date. Cannot be '
        'combined with ``--skill-name``.'
    ),
    'action': 'store_true',
    'required': False,
}


class UpdateSkillCommand(BasicCommand):
    NAME = 'update-skill'
    DESCRIPTION = (
        'Update installed AWS skills to the latest version. '
        'Compares the locally installed version against the available skills '
        'and downloads the newer version if available. Pass ``--skill-name`` '
        'to update a single skill or ``--all`` to update every installed '
        'skill that is out of date. By default skills are '
        'updated for all detected agents, use ``--agent`` to update '
        'for only a specific tool.'
    )
    ARG_TABLE = [
        UPDATE_SKILL_NAME_ARG,
        ALL_SKILLS_ARG,
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
        update_all = getattr(parsed_args, 'all', False)
        agent_filter = getattr(parsed_args, 'agent', None)

        if update_all and skill_name:
            raise ParamValidationError(
                'Cannot use --skill-name together with --all.'
            )
        if not update_all and not skill_name:
            raise ParamValidationError(
                'Either --skill-name or --all is required.'
            )

        agents = resolve_agents(agent_filter, self._agent_configs)
        if not agents:
            raise ParamValidationError('No supported AI coding agents found.')

        if update_all:
            return self._update_all_skills(agents, parsed_globals)
        return self._update_one_skill(agents, parsed_globals, skill_name)

    def _create_client(self, parsed_globals):
        return self._client or create_client(self._session, parsed_globals)

    def _update_one_skill(self, agents, parsed_globals, skill_name):
        installed_agents = agents_with_skill(agents, skill_name)
        if not installed_agents:
            raise ParamValidationError(
                f'Skill "{skill_name}" is not installed.'
            )

        # Build the client only once we know there is something to update, so
        # local failures are not masked by endpoint or credential errors.
        client = self._create_client(parsed_globals)
        remote_version, outdated = self._find_outdated(
            installed_agents, client, skill_name
        )
        if not outdated:
            self._stream.write(
                f'{skill_name} is already up to date ({remote_version}).\n'
            )
            return 0

        self._install_version(client, skill_name, remote_version, outdated)
        return 0

    def _update_all_skills(self, agents, parsed_globals):
        installed_skills = collect_installed_skills(agents)
        if not installed_skills:
            self._stream.write('No installed AWS skills found.\n')
            return 0

        # Group by name from the scan above. Asking each agent which skills it
        # has once per skill name would rescan every skills directory for every
        # skill.
        agents_by_skill = {}
        for skill in installed_skills:
            agents_by_skill.setdefault(skill.name, []).append(skill.agent)

        client = self._create_client(parsed_globals)
        updated_any = False
        for skill_name in sorted(agents_by_skill):
            remote_version, outdated = self._find_outdated(
                agents_by_skill[skill_name], client, skill_name
            )
            if not outdated:
                continue
            self._install_version(client, skill_name, remote_version, outdated)
            updated_any = True

        if not updated_any:
            self._stream.write(
                'All installed AWS skills are already up to date.\n'
            )
        return 0

    def _find_outdated(self, installed_agents, client, skill_name):
        remote_version = resolve_latest_version(client, skill_name)
        outdated = []
        for agent in installed_agents:
            skill_dir = os.path.join(agent.skills_path, skill_name)
            local_version = read_installed_version(skill_dir)
            if local_version != remote_version:
                outdated.append(agent)
        return remote_version, outdated

    def _install_version(self, client, skill_name, remote_version, agents):
        zip_bytes, checksum, version = get_skill_download(
            client, skill_name, version=remote_version
        )
        install_skill(
            skill_name,
            version,
            zip_bytes,
            checksum,
            agents,
            self._stream,
            action='Updated',
            overwrite_existing=True,
        )
