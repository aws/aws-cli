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

from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    collect_installed_skills,
    create_client,
    read_installed_version,
    resolve_agents,
    resolve_latest_version,
)
from awscli.customizations.commands import BasicCommand
from awscli.formatter import get_formatter
from awscli.utils import OutputStreamFactory


class CheckUpdatesCommand(BasicCommand):
    NAME = 'check-updates'
    DESCRIPTION = (
        'Check installed AWS skills for available updates. For each installed '
        'skill this reports the version currently on disk, the latest version '
        'available, and whether an update is available. Nothing is downloaded '
        'or modified, run ``aws agent-toolkit update-skill`` to apply an '
        'update. By default it checks skills for all detected agents, use '
        '``--agent`` to check only a specific tool.'
    )
    ARG_TABLE = [AGENT_ARG]

    def __init__(
        self,
        session,
        agent_configs=None,
        client=None,
        output_stream_factory=None,
    ):
        super().__init__(session)
        self._agent_configs = agent_configs
        self._client = client
        if output_stream_factory is None:
            output_stream_factory = OutputStreamFactory(session)
        self._output_stream_factory = output_stream_factory

    def _run_main(self, parsed_args, parsed_globals):
        agent_filter = getattr(parsed_args, 'agent', None)
        agents = resolve_agents(agent_filter, self._agent_configs)
        installed_skills = collect_installed_skills(agents)

        result = {'skills': []}
        if installed_skills:
            client = self._client or create_client(
                self._session, parsed_globals
            )
            result['skills'] = self._build_rows(client, installed_skills)

        output = parsed_globals.output
        if output is None:
            output = self._session.get_config_variable('output')
        formatter = get_formatter(output, parsed_globals)
        with self._output_stream_factory.get_output_stream() as stream:
            formatter(self.NAME, result, stream=stream)
        return 0

    def _build_rows(self, client, installed_skills):
        # The same skill is often installed for several agents. Look up each
        # name once so the number of API calls tracks distinct skills rather
        # than installs.
        latest_versions = {}
        rows = []
        for skill in installed_skills:
            if skill.name not in latest_versions:
                latest_versions[skill.name] = resolve_latest_version(
                    client, skill.name
                )
            latest_version = latest_versions[skill.name]
            installed_version = read_installed_version(
                os.path.dirname(skill.path)
            )
            rows.append(
                {
                    'agent': skill.agent.display_name,
                    'name': skill.name,
                    'path': skill.path,
                    'installedVersion': installed_version,
                    'latestVersion': latest_version,
                    'updateAvailable': installed_version != latest_version,
                }
            )
        return rows
