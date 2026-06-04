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
from awscli.customizations.agenttoolkit.agents import universal_first
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    resolve_agents,
)
from awscli.customizations.commands import BasicCommand
from awscli.formatter import get_formatter
from awscli.utils import OutputStreamFactory


class ListInstalledSkillsCommand(BasicCommand):
    NAME = 'list-installed-skills'
    DESCRIPTION = (
        'List AWS skills that were previously installed by the '
        '``aws agent-toolkit`` commands. Shows the skill name, agent, and file '
        'path for each installation. By default it lists skills from all '
        'detected agents, use ``--agent`` to filter results to a specific tool.'
    )
    ARG_TABLE = [AGENT_ARG]

    def __init__(
        self, session, agent_configs=None, output_stream_factory=None
    ):
        super().__init__(session)
        self._agent_configs = agent_configs
        if output_stream_factory is None:
            output_stream_factory = OutputStreamFactory(session)
        self._output_stream_factory = output_stream_factory

    def _run_main(self, parsed_args, parsed_globals):
        agent_filter = getattr(parsed_args, 'agent', None)
        agents = resolve_agents(agent_filter, self._agent_configs)

        seen_paths = set()
        all_skills = []
        for agent in universal_first(agents):
            for skill in agent.get_installed_skills():
                if skill.path in seen_paths:
                    continue
                seen_paths.add(skill.path)
                all_skills.append(skill)

        result = {
            'skills': [
                {
                    'agent': skill.agent.display_name,
                    'name': skill.name,
                    'path': skill.path,
                }
                for skill in all_skills
            ]
        }

        output = parsed_globals.output
        if output is None:
            output = self._session.get_config_variable('output')
        formatter = get_formatter(output, parsed_globals)
        with self._output_stream_factory.get_output_stream() as stream:
            formatter(self.NAME, result, stream=stream)
            stream.write('\n')
        return 0
