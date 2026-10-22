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
import os
import sys

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    UNIVERSAL_ROW_ID,
    McpConfigureAction,
    collapse_home,
    universal_first,
)
from awscli.customizations.agenttoolkit.hooks import (
    CODEX_TRUST_NOTE,
    KIRO_AGENT_NOTE,
    KIRO_NO_AGENT_NOTE,
    KIRO_VERSION_NOTE,
    HookAction,
    format_kiro_agent_manual_entry,
    format_manual_entry,
    hook_config_path,
    install_hook,
    install_kiro_agent_hook,
    is_hook_supported,
    kiro_default_agent_path,
    remove_hook,
    remove_kiro_agent_hooks,
)
from awscli.customizations.agenttoolkit.state import (
    StateFileError,
    is_auto_update_enabled,
    set_auto_update,
)
from awscli.customizations.agenttoolkit.utils import (
    AgentToolkitServiceError,
    create_client,
    get_skill_download,
    install_skill,
    list_core_skills,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.prompts import multiselect_choice, yes_no_choice
from awscli.customizations.utils import uni_print

AUTO_UPDATE_PROMPT = (
    '\nKeep AWS skills up to date automatically? When your agent starts, '
    'installed AWS skills are updated and new core AWS skills are '
    'installed. [Y/n]: '
)

AUTO_UPDATE_KEEP_PROMPT = (
    '\nAutomatic skill updates are on. Keep them on? [Y/n]: '
)


class ConfigureAgentToolkitCommand(BasicCommand):
    NAME = 'agent-toolkit'
    DESCRIPTION = (
        'Set up AI coding agents with AWS skills and the AWS MCP Server.\n\n'
        'Supported agents are determined by the presence of configuration '
        'directories, such as ``~/.kiro``. Skills are installed globally in '
        'those configuration directories, not per project.'
    )
    SYNOPSIS = 'aws configure agent-toolkit'
    ARG_TABLE = [
        {
            'name': 'yes',
            'help_text': (
                'Skip all interactive prompts and accept defaults: '
                'select all detected agents, install default skills, '
                'configure the AWS MCP server, and enable automatic skill '
                'updates.'
            ),
            'default': False,
            'action': 'store_true',
        },
    ]

    def __init__(self, session, stream=None, agent_configs=None, client=None):
        super().__init__(session)
        self._stream = stream or sys.stdout
        self._agent_configs = (
            agent_configs if agent_configs is not None else AGENT_CONFIGS
        )
        self._client = client

    def _run_main(self, parsed_args, parsed_globals):
        yes = getattr(parsed_args, 'yes', False)
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

        selected_agents = (
            detected
            if yes
            else multiselect_choice(
                '\nSelect agents to configure',
                detected,
                display_format=lambda a: a.display_label,
            )
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
        self._install_default_skills(install_targets, client, yes=yes)
        self._configure_mcp(selected_agents, yes=yes)
        self._configure_auto_update(selected_agents, yes=yes)

        uni_print(
            '\nYou can discover additional skills with '
            '\'aws agent-toolkit search-skills --search-query <text>\'\n',
            self._stream,
        )
        return 0

    def _install_default_skills(self, selected_agents, client, yes=False):
        uni_print('\nFetching default AWS skills...\n', self._stream)
        default_skills = list_core_skills(client)

        if not default_skills:
            return

        names = ', '.join(s['name'] for s in default_skills)
        uni_print(f'  Found: {names}\n', self._stream)

        if not yes and not yes_no_choice(
            f'\nInstall {len(default_skills)} default AWS skills? [Y/n]: ',
            default=True,
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

    def _configure_auto_update(self, agents, yes=False):
        # This wizard is the only place allowed to change the setting, so it
        # always asks, letting customers opt out as well as in.
        currently_enabled = is_auto_update_enabled()
        prompt = (
            AUTO_UPDATE_KEEP_PROMPT
            if currently_enabled
            else AUTO_UPDATE_PROMPT
        )
        enabled = yes or yes_no_choice(prompt, default=True)
        if enabled != currently_enabled:
            try:
                set_auto_update(enabled)
            except StateFileError as e:
                uni_print(
                    '\nCould not save the automatic skill update setting '
                    f'to {e}\n',
                    self._stream,
                )
                return
            if enabled:
                uni_print('\nAutomatic skill updates enabled.\n', self._stream)
            else:
                uni_print(
                    '\nAutomatic skill updates turned off.\n', self._stream
                )
        if enabled:
            self._install_hooks(agents)
        else:
            self._remove_hooks()

    def _install_hooks(self, agents):
        uni_print('\nAutomatic update hooks:\n', self._stream)
        unsupported = []
        for agent in agents:
            if not is_hook_supported(agent.config.id):
                unsupported.append(agent)
                continue
            try:
                action, path = install_hook(agent)
            except OSError as e:
                path = hook_config_path(agent.config, agent.base_dir)
                self._print_hook_line(
                    '\u2717', agent, path, f'could not install the hook ({e})'
                )
                continue
            if action is HookAction.UNREADABLE:
                self._print_hook_line(
                    '\u2717',
                    agent,
                    path,
                    'could not be updated because it is not plain JSON or '
                    'its formatting can not be kept',
                )
                uni_print(
                    format_manual_entry(agent.config.id, collapse_home(path)),
                    self._stream,
                )
                continue
            status = (
                'already installed'
                if action is HookAction.ALREADY_INSTALLED
                else 'hook installed'
            )
            self._print_hook_line('\u2713', agent, path, status)
            if agent.config.id == 'codex':
                uni_print(f'    {CODEX_TRUST_NOTE}\n', self._stream)
            elif agent.config.id == 'kiro':
                uni_print(f'    {KIRO_VERSION_NOTE}\n', self._stream)
                self._install_kiro_agent_hook(agent)
        for agent in unsupported:
            uni_print(
                f'  \u2717 {agent.display_name} '
                '(automatic updates not supported yet)\n',
                self._stream,
            )

    def _install_kiro_agent_hook(self, agent):
        try:
            action, path = install_kiro_agent_hook(agent)
        except OSError as e:
            path = kiro_default_agent_path(agent) or os.path.join(
                agent.base_dir, 'agents'
            )
            self._print_hook_line(
                '\u2717', agent, path, f'could not install the hook ({e})'
            )
            return
        if path is None:
            uni_print(
                f'  \u2717 {agent.display_name} \u2014 {KIRO_NO_AGENT_NOTE}\n'
                + format_kiro_agent_manual_entry(
                    collapse_home(
                        os.path.join(agent.base_dir, 'agents', '<agent>.json')
                    )
                ),
                self._stream,
            )
            return
        if action is HookAction.UNREADABLE:
            self._print_hook_line(
                '\u2717',
                agent,
                path,
                'could not be updated because it is not plain JSON or '
                'its formatting can not be kept',
            )
            uni_print(
                format_kiro_agent_manual_entry(collapse_home(path)),
                self._stream,
            )
        elif action is HookAction.NOT_NEEDED:
            self._print_hook_line(
                '\u2713', agent, path, 'not needed for V3 agents'
            )
            return
        else:
            status = (
                'already installed'
                if action is HookAction.ALREADY_INSTALLED
                else 'hook installed'
            )
            self._print_hook_line('\u2713', agent, path, status)
        uni_print(f'    {KIRO_AGENT_NOTE}\n', self._stream)

    def _remove_hooks(self):
        # Hooks may have been installed for agents that weren't selected this
        # time, so every detected agent is cleaned up.
        lines = []
        for config in self._agent_configs:
            if not is_hook_supported(config.id):
                continue
            agent = config.detect()
            if agent is None:
                continue
            try:
                results = [remove_hook(agent)]
            except OSError as e:
                path = hook_config_path(agent.config, agent.base_dir)
                lines.append(
                    ('\u2717', agent, path, f'could not remove the hook ({e})')
                )
                continue
            if config.id == 'kiro':
                try:
                    results.extend(remove_kiro_agent_hooks(agent))
                except OSError as e:
                    path = os.path.join(agent.base_dir, 'agents')
                    lines.append(
                        (
                            '\u2717',
                            agent,
                            path,
                            f'could not remove the hook ({e})',
                        )
                    )
            for action, path in results:
                if action is HookAction.REMOVED:
                    lines.append(('\u2713', agent, path, 'hook removed'))
                elif action is HookAction.UNREADABLE:
                    lines.append(
                        (
                            '\u2717',
                            agent,
                            path,
                            'could not be updated; remove the "aws '
                            'agent-toolkit update-skill" hook from it by hand',
                        )
                    )
        if not lines:
            return
        uni_print('\nAutomatic update hooks:\n', self._stream)
        for line in lines:
            self._print_hook_line(*line)

    def _print_hook_line(self, mark, agent, path, status):
        uni_print(
            f'  {mark} {agent.display_name} \u2014 '
            f'{collapse_home(path)}: {status}\n',
            self._stream,
        )

    def _configure_mcp(self, agents, yes=False):
        if not yes and not yes_no_choice(
            '\nConfigure AWS MCP server connection? [Y/n]: ', default=True
        ):
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
