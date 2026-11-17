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
import shutil
import sys

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    universal_first,
)
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    SKILL_NAME_ARG,
    resolve_agents,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError


class RemoveCommand(BasicCommand):
    NAME = 'remove-skill'
    DESCRIPTION = (
        'Remove a previously installed AWS skill from detected agents. '
        'By default the skill is removed from all detected agents, use '
        '``--agent`` to remove from a specific tool only.'
    )
    ARG_TABLE = [
        SKILL_NAME_ARG,
        AGENT_ARG,
    ]

    def __init__(self, session, stream=None, agent_configs=None):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        skill_name = parsed_args.skill_name
        agent_filter = getattr(parsed_args, 'agent', None)

        agents = resolve_agents(agent_filter, self._agent_configs)

        matches = []
        for agent in agents:
            for skill in agent.get_installed_skills():
                if skill.name == skill_name:
                    matches.append(skill)

        if not matches:
            raise ParamValidationError(
                f'Skill "{skill_name}" is not installed.'
            )

        removed_paths = set()
        ordered = universal_first(matches, get_id=lambda s: s.agent.config.id)
        for skill in ordered:
            skill_dir = os.path.dirname(skill.path)
            if skill_dir in removed_paths:
                continue
            shutil.rmtree(skill_dir)
            removed_paths.add(skill_dir)
            self._stream.write(
                f'Removed {skill.name} from {skill.agent.display_label}.\n'
            )
        return 0
