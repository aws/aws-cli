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
import dataclasses
import enum
import glob
import json
import os
import shutil
import subprocess
from typing import Optional

SKILL_FILENAME = 'SKILL.md'
SKILL_METADATA_FILENAME = '.aws-skill-metadata'
AWS_MCP_SERVER_KEY = 'aws-mcp'
UNIVERSAL_ROW_ID = 'universal'


def collapse_home(path):
    home = os.path.expanduser('~').rstrip(os.sep)
    if path == home:
        return '~'
    if path.startswith(home + os.sep):
        return '~' + path[len(home) :]
    return path


class McpConfigureAction(enum.Enum):
    CONFIGURED = 'configured'
    ALREADY_CONFIGURED = 'already_configured'
    SKIPPED = 'skipped'


_AWS_MCP_PROXY_ARGS = [
    'mcp-proxy-for-aws@latest',
    'https://aws-mcp.us-east-1.api.aws/mcp',
    '--metadata',
    'INSTALL_SOURCE=aws-cli',
]


DEFAULT_MCP_SERVER_CONFIG = {
    'command': 'uvx',
    'args': _AWS_MCP_PROXY_ARGS,
}


@dataclasses.dataclass
class AgentConfig:
    """Definition of a supported AI coding agent.

    To add a new agent, append an instance to ``AGENT_CONFIGS`` in this
    module. Most agents only need ``id``, ``display_name``, and
    ``detection_path``; the remaining fields cover variations across
    different agents' filesystem layouts and MCP config formats.
    """

    id: str
    """Stable identifier. Used as the value for ``--agent`` filters."""

    display_name: str
    """Human-readable name shown in wizard output and command results."""

    detection_path: str
    """Filesystem path probed to decide whether the agent is installed.
    Tilde expansion is supported. The agent is considered detected when
    this path resolves to an existing directory."""

    detection_path_env_override: Optional[str] = None
    """Environment variable name that overrides ``detection_path`` when
    set (e.g. ``CLAUDE_CONFIG_DIR``)."""

    skills_dir: str = 'skills'
    """Subdirectory of the resolved base directory where skills live.
    Ignored when ``skills_path_override`` is set."""

    skills_path_override: Optional[str] = None
    """Absolute path to the skills directory when it is not under the
    detection directory (e.g. Codex stores skills at ``~/.agents/skills/``).
    Tilde expansion is supported."""

    mcp_config_path: Optional[str] = None
    """Path to the MCP config file. Relative paths are resolved against
    the detection directory; tilde-prefixed paths are absolute. Leave
    ``None`` for agents that don't have JSON-based MCP config."""

    mcp_servers_key: str = 'mcpServers'
    """Top-level JSON key under which MCP servers are stored. Most
    agents use ``mcpServers``; OpenCode uses ``mcp``."""

    mcp_extra_config: Optional[dict] = None
    """Extra fields merged into the default MCP server entry (e.g.
    Kiro requires ``timeout`` and ``transport``). Used only when
    ``mcp_server_entry`` is not set."""

    mcp_server_entry: Optional[dict] = None
    """Complete MCP server entry, replacing the default schema. Use
    when an agent expects a different shape than ``{command, args}``
    (e.g. OpenCode expects ``{type, command: [...]}``)."""

    mcp_shell_command: Optional[list] = None
    """Argv for a CLI invocation that registers the AWS MCP server
    (e.g. ``codex mcp add ...``). Used for agents whose MCP config is
    not JSON. The wizard skips MCP setup if the executable is not on
    PATH."""

    def __post_init__(self):
        if self.mcp_extra_config is None:
            self.mcp_extra_config = {}

    @property
    def _display_skills_path(self):
        if self.skills_path_override:
            return self.skills_path_override.rstrip('/')
        base = self.detection_path.rstrip('/')
        if self.skills_dir:
            return f'{base}/{self.skills_dir}'
        return base

    @property
    def display_label(self):
        return f'{self.display_name} — {self._display_skills_path}'

    def resolved_override_dir(self):
        if not self.detection_path_env_override:
            return None
        env_value = os.environ.get(self.detection_path_env_override)
        if not env_value:
            return None
        expanded = os.path.expanduser(env_value).rstrip(os.sep)
        if not os.path.isdir(expanded):
            return None
        return expanded

    def resolve_base_dir(self):
        override = self.resolved_override_dir()
        if override is not None:
            return override
        expanded = os.path.expanduser(self.detection_path).rstrip(os.sep)
        if os.path.isdir(expanded):
            return expanded
        return None

    def detect(self):
        base_dir = self.resolve_base_dir()
        if base_dir is None:
            return None
        return DetectedAgent(self, base_dir)


class DetectedAgent:
    """An agent that was found installed on this machine."""

    def __init__(self, config, base_dir):
        self.config = config
        self.base_dir = base_dir

    @property
    def display_name(self):
        return self.config.display_name

    @property
    def display_label(self):
        return f'{self.display_name} — {collapse_home(self.skills_path)}'

    @property
    def skills_path(self):
        if self.config.skills_path_override:
            return os.path.expanduser(self.config.skills_path_override)
        return os.path.join(self.base_dir, self.config.skills_dir)

    @property
    def mcp_config_file(self):
        if self.config.mcp_config_path is None:
            return None
        if self.config.mcp_config_path.startswith('~'):
            override = self.config.resolved_override_dir()
            if override is not None:
                relative = self.config.mcp_config_path.removeprefix('~/')
                return os.path.join(override, relative)
            return os.path.expanduser(self.config.mcp_config_path)
        return os.path.join(self.base_dir, self.config.mcp_config_path)

    def get_installed_skills(self):
        pattern = os.path.join(
            self.skills_path,
            '*',
            SKILL_FILENAME,
        )
        results = []
        for skill_path in sorted(glob.glob(pattern)):
            skill_dir_path = os.path.dirname(skill_path)
            if not os.path.exists(
                os.path.join(skill_dir_path, SKILL_METADATA_FILENAME)
            ):
                continue
            skill_dir = os.path.basename(skill_dir_path)
            results.append(InstalledSkill(self, skill_dir, skill_path))
        return results

    def configure_mcp_server(self):
        """Configure the AWS MCP server entry for this agent.

        Returns a tuple of (action, detail) where action is a member of
        McpConfigureAction. detail is the config file path for JSON-based
        agents, the executable name for shell-based agents, or None when
        no MCP setup is wired up.
        """
        if self.config.mcp_shell_command is not None:
            return self._configure_via_shell()

        config_path = self.mcp_config_file
        if config_path is None:
            return McpConfigureAction.SKIPPED, None

        existing_config = self._read_mcp_config(config_path)
        servers = existing_config.setdefault(self.config.mcp_servers_key, {})

        if AWS_MCP_SERVER_KEY in servers:
            return McpConfigureAction.ALREADY_CONFIGURED, config_path

        if self.config.mcp_server_entry is not None:
            server_entry = self.config.mcp_server_entry
        else:
            server_entry = {
                **DEFAULT_MCP_SERVER_CONFIG,
                **self.config.mcp_extra_config,
            }
        servers[AWS_MCP_SERVER_KEY] = server_entry
        self._write_mcp_config(config_path, existing_config)
        return McpConfigureAction.CONFIGURED, config_path

    def _configure_via_shell(self):
        argv = list(self.config.mcp_shell_command)
        executable = argv[0]
        if shutil.which(executable) is None:
            return McpConfigureAction.SKIPPED, executable
        subprocess.run(argv, check=True)
        return McpConfigureAction.CONFIGURED, executable

    @staticmethod
    def _read_mcp_config(path):
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def _write_mcp_config(path, config):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        is_new = not os.path.exists(path)
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
            f.write('\n')
        # If we created the MCP config file, set permissions to 600, otherwise
        # the open call above preserves permissions for existing files
        if is_new:
            os.chmod(path, 0o600)


class InstalledSkill:
    """A skill found in an agent's skills directory."""

    def __init__(self, agent, name, path):
        self.agent = agent
        self.name = name
        self.path = path


# TODO: Verify detection, skills, and MCP config paths against actual
# installations before release. Currently only tested with Kiro and
# simulated agent directories.
AGENT_CONFIGS = [
    # https://docs.anthropic.com/en/docs/claude-code/mcp
    AgentConfig(
        id='claude-code',
        display_name='Claude Code',
        detection_path='~/.claude/',
        mcp_config_path='~/.claude.json',
        mcp_servers_key='mcpServers',
        detection_path_env_override='CLAUDE_CONFIG_DIR',
    ),
    # https://docs.cline.bot/mcp/mcp-overview
    # https://docs.cline.bot/customization/skills
    AgentConfig(
        id='cline',
        display_name='Cline',
        detection_path='~/.cline/',
        mcp_config_path='mcp.json',
        mcp_servers_key='mcpServers',
    ),
    # https://developers.openai.com/codex/skills
    # https://github.com/openai/codex/blob/main/codex-rs/cli/src/mcp_cmd.rs
    # Codex stores MCP config in TOML, not JSON. We shell out to its CLI
    # rather than add a TOML dependency.
    AgentConfig(
        id='codex',
        display_name='Codex',
        detection_path='~/.codex/',
        skills_path_override='~/.agents/skills/',
        detection_path_env_override='CODEX_HOME',
        mcp_shell_command=[
            'codex',
            'mcp',
            'add',
            AWS_MCP_SERVER_KEY,
            '--',
            'uvx',
            *_AWS_MCP_PROXY_ARGS,
        ],
    ),
    # https://docs.cursor.com/context/model-context-protocol
    # https://cursor.com/docs/skills
    AgentConfig(
        id='cursor',
        display_name='Cursor',
        detection_path='~/.cursor/',
        mcp_config_path='mcp.json',
        mcp_servers_key='mcpServers',
    ),
    # https://geminicli.com/docs/cli/tutorials/mcp-setup/
    # https://geminicli.com/docs/cli/skills/
    AgentConfig(
        id='gemini-cli',
        display_name='Gemini CLI',
        detection_path='~/.gemini/',
        skills_path_override='~/.agents/skills/',
        mcp_config_path='settings.json',
        mcp_servers_key='mcpServers',
    ),
    # https://kiro.dev/docs/mcp/configuration/
    AgentConfig(
        id='kiro',
        display_name='Kiro',
        detection_path='~/.kiro/',
        mcp_config_path='settings/mcp.json',
        mcp_servers_key='mcpServers',
        mcp_extra_config={'timeout': 100000, 'transport': 'stdio'},
    ),
    # https://openclaw-openclaw.mintlify.app/configuration
    # OpenClaw does not document MCP support — install skills only.
    AgentConfig(
        id='openclaw',
        display_name='OpenClaw',
        detection_path='~/.openclaw/',
    ),
    # https://docs.opencode.ai/docs/mcp-servers
    # https://docs.opencode.ai/docs/skills
    AgentConfig(
        id='opencode',
        display_name='OpenCode',
        detection_path='~/.config/opencode/',
        skills_path_override='~/.agents/skills/',
        mcp_config_path='opencode.json',
        mcp_servers_key='mcp',
        mcp_server_entry={
            'type': 'local',
            'command': ['uvx', *_AWS_MCP_PROXY_ARGS],
        },
    ),
    # https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md
    # Pi does not document MCP support — install skills only.
    AgentConfig(
        id='pi',
        display_name='Pi',
        detection_path='~/.pi/agent/',
    ),
    # https://docs.windsurf.com/plugins/cascade/mcp
    # https://docs.windsurf.com/windsurf/cascade/skills
    AgentConfig(
        id='windsurf',
        display_name='Windsurf',
        detection_path='~/.codeium/windsurf/',
        skills_path_override='~/.agents/skills/',
        mcp_config_path='~/.codeium/mcp_config.json',
        mcp_servers_key='mcpServers',
    ),
]


def _build_universal_row(configs):
    universal_path = os.path.expanduser('~/.agents/skills/').rstrip(os.sep)
    consumers = [
        c.display_name
        for c in configs
        if c.skills_path_override
        and os.path.expanduser(c.skills_path_override).rstrip(os.sep)
        == universal_path
    ]
    return AgentConfig(
        id=UNIVERSAL_ROW_ID,
        display_name=f'Universal ({", ".join(consumers)})',
        detection_path='~/.agents',
    )


AGENT_CONFIGS.append(_build_universal_row(AGENT_CONFIGS))


def universal_first(items, get_id=lambda a: a.config.id):
    return sorted(
        items,
        key=lambda i: 0 if get_id(i) == UNIVERSAL_ROW_ID else 1,
    )


def get_detected_agents(agent_configs=None):
    if agent_configs is None:
        agent_configs = AGENT_CONFIGS
    detected = []
    for config in agent_configs:
        agent = config.detect()
        if agent is not None:
            detected.append(agent)
    return detected
