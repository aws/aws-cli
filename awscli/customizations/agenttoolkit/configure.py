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
import io
import sys

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    UNIVERSAL_ROW_ID,
    McpConfigureAction,
    collapse_home,
    universal_first,
)
from awscli.customizations.agenttoolkit.utils import (
    AgentToolkitServiceError,
    create_client,
    get_skill_download,
    install_skill,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.prompts import multiselect_choice, yes_no_choice
from awscli.customizations.utils import uni_print


class ConfigureAgentToolkitCommand(BasicCommand):
    NAME = 'agent-toolkit'
    DESCRIPTION = (
        'Set up AI coding agents with AWS skills and the AWS MCP Server.\n\n'
        'Supported agents are determined by the presence of configuration '
        'directories, such as ``~/.kiro``. Skills are installed globally in '
        'those configuration directories, not per project.'
    )
    SYNOPSIS = 'aws configure agent-toolkit'

    def __init__(self, session, stream=None, agent_configs=None, client=None):
        super().__init__(session)
        self._stream = stream or sys.stdout
        self._agent_configs = (
            agent_configs if agent_configs is not None else AGENT_CONFIGS
        )
        self._client = client

    def _run_main(self, parsed_args, parsed_globals):
        uni_print('\nDetecting installed AI coding agents...\n', self._stream)
        wizard_configs = [
            c for c in self._agent_configs if c.id != UNIVERSAL_ROW_ID
        ]
        universal_agent = next(
            (
                c.detect()
                for c in self._agent_configs
                if c.id == UNIVERSAL_ROW_ID
            ),
            None,
        )

        detected = []
        for config in wizard_configs:
            agent = config.detect()
            if agent:
                # Use the DetectedAgent's label so any env-overridden
                # paths (e.g. CLAUDE_CONFIG_DIR) display the resolved
                # location instead of the config-time literal.
                uni_print(f'  \u2713 {agent.display_label}\n', self._stream)
                detected.append(agent)
            else:
                uni_print(
                    f'  \u2717 {config.display_label} (not found)\n',
                    self._stream,
                )

        if not detected:
            raise ConfigurationError(
                'No supported AI coding agents found. '
                'Supported agents: '
                f'{", ".join(c.display_name for c in wizard_configs)}. '
                'Install one and re-run \'aws configure agent-toolkit\'.'
            )

        selected_agents = multiselect_choice(
            '\nSelect agents to configure',
            detected,
            display_format=lambda a: a.display_label,
        )

        if not selected_agents:
            uni_print('No agents selected.\n', self._stream)
            return 0

        install_targets = list(selected_agents)
        if universal_agent and any(
            a.skills_path == universal_agent.skills_path
            for a in selected_agents
        ):
            install_targets.append(universal_agent)

        client = self._client or create_client(self._session, parsed_globals)
        self._install_default_skills(install_targets, client)
        self._configure_mcp(selected_agents)

        uni_print(
            '\nYou can discover additional skills with '
            '\'aws agent-toolkit search-skills --search-query <text>\'\n',
            self._stream,
        )
        return 0

    def _install_default_skills(self, selected_agents, client):
        uni_print('\nFetching default AWS skills...\n', self._stream)
        paginator = client.get_paginator('list_skills')
        default_skills = []
        for page in paginator.paginate(categoryFilter='aws-core'):
            default_skills.extend(page.get('skills', []))

        if not default_skills:
            return

        names = ', '.join(s['name'] for s in default_skills)
        uni_print(f'  Found: {names}\n', self._stream)

        if not yes_no_choice(
            f'\nInstall {len(default_skills)} default AWS skills? [Y/n]: '
        ):
            return

        uni_print(
            f'\nInstalling {len(default_skills)} default AWS skills...\n',
            self._stream,
        )

        installed_count = 0
        for i, skill in enumerate(default_skills, 1):
            name = skill['name']
            try:
                zip_bytes, checksum, version = get_skill_download(client, name)
                install_skill(
                    name,
                    version,
                    zip_bytes,
                    checksum,
                    selected_agents,
                )
                installed_count += 1
                uni_print(
                    f'  [{i}/{len(default_skills)}] {name}\n',
                    self._stream,
                )
            except AgentToolkitServiceError as e:
                uni_print(
                    f'  [{i}/{len(default_skills)}] {name}: {e}\n',
                    self._stream,
                )

        if installed_count:
            uni_print('\nSkills installed to:\n', self._stream)
            seen_paths = set()
            for agent in universal_first(selected_agents):
                if agent.skills_path in seen_paths:
                    continue
                seen_paths.add(agent.skills_path)
                uni_print(
                    f'  {agent.display_label}\n',
                    self._stream,
                )
        else:
            uni_print(
                '\nNo skills were installed successfully.\n', self._stream
            )

    def _configure_mcp(self, agents):
        if not yes_no_choice('\nConfigure AWS MCP server connection? [Y/n]: '):
            return

        uni_print('\nAWS MCP server configured for:\n', self._stream)
        skipped = []
        for agent in agents:
            action, detail = agent.configure_mcp_server()
            if action is McpConfigureAction.SKIPPED:
                skipped.append((agent, detail))
            elif action is McpConfigureAction.ALREADY_CONFIGURED:
                uni_print(
                    f'  \u2713 {agent.display_name} \u2014 '
                    f'{collapse_home(detail)}: already configured\n',
                    self._stream,
                )
            else:
                uni_print(
                    f'  \u2713 {agent.display_name} \u2014 '
                    f'{collapse_home(detail)}: updated\n',
                    self._stream,
                )

        if skipped:
            uni_print(
                '\nMCP setup not available for the following agents. '
                'See https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html '
                'for manual setup instructions.\n',
                self._stream,
            )
            for agent, detail in skipped:
                reason = (
                    f'requires {detail!r} on PATH'
                    if detail
                    else 'no automated setup'
                )
                uni_print(
                    f'  \u2717 {agent.display_name} ({reason})\n',
                    self._stream,
                )
