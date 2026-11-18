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


def _relative_path_within(path, directory):
    """Return ``path`` relative to ``directory``, or ``None`` if outside."""
    try:
        relative = os.path.relpath(path, directory)
    except ValueError:
        # On Windows, the paths are on different drives.
        return None
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return None
    return relative


def _has_symlink_below(root, relative):
    """Whether a path component of ``relative``, joined to ``root`` one at
    a time, is a symbolic link. ``root`` itself is not checked."""
    if relative == os.curdir:
        return False
    current = root
    for part in relative.split(os.sep):
        current = os.path.join(current, part)
        if os.path.islink(current):
            return True
    return False


class Scope(enum.Enum):
    """Where skills are installed: the home or the current directory."""

    GLOBAL = 'global'
    PROJECT = 'project'


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
    module. Most agents only need ``id``, ``display_name``,
    ``detection_path``, and ``skills_paths``; the remaining fields cover
    variations across different agents' filesystem layouts and MCP config
    formats.
    """

    id: str
    """Stable identifier. Used as the value for ``--agent`` filters."""

    display_name: str
    """Human-readable name shown in wizard output and command results."""

    detection_path: str
    """Filesystem path probed to decide whether the agent is installed.
    Tilde expansion is supported. The agent is considered detected when
    this path resolves to an existing directory."""

    skills_paths: list[str]
    """Skills directories the agent loads skills from, in priority order,
    relative to the home directory (e.g. ``.claude/skills``).

    The first entry is where new skills are installed; every entry is
    checked when looking for installed skills. The home directory follows
    ``home_env_override``, and entries under ``detection_path`` move with
    ``detection_path_env_override`` when it is set. List ``.agents/skills``
    first when the agent reads it, so one copy of a skill serves every
    agent that shares it.

    For project-level skills, the same entries are resolved against the
    project directory instead of the home directory."""

    detection_path_env_override: Optional[str] = None
    """Environment variable name that overrides ``detection_path`` when
    set (e.g. ``CLAUDE_CONFIG_DIR``)."""

    home_env_override: Optional[str] = None
    """Environment variable naming the home directory the agent uses in
    place of ``~`` (e.g. ``GEMINI_CLI_HOME``). When set, every
    tilde-prefixed path of this agent is resolved against it."""

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
        if not self.skills_paths:
            raise ValueError(
                f'Agent {self.id!r} must have at least one skills path.'
            )
        for path in self.skills_paths:
            drive, rest = os.path.splitdrive(path)
            # Checks drives and leading separators itself, as isabs() is
            # False for "/x" and "C:x" on Windows, though join() then
            # drops the home directory.
            if path.startswith('~') or drive or rest.startswith(('/', '\\')):
                raise ValueError(
                    f'Skills path {path!r} of agent {self.id!r} must be '
                    'relative to the home directory.'
                )

    @property
    def _display_skills_path(self):
        return f'~/{self.skills_paths[0]}'.rstrip('/')

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

    def expand_path(self, path):
        """Expand a leading ``~`` to the home directory the agent uses."""
        home = os.environ.get(self.home_env_override or '')
        if home and (path == '~' or path.startswith('~/')):
            return os.path.join(
                os.path.expanduser(home), path[2:].replace('/', os.sep)
            )
        return os.path.expanduser(path)

    def resolve_base_dir(self):
        override = self.resolved_override_dir()
        if override is not None:
            return override
        expanded = self.expand_path(self.detection_path).rstrip(os.sep)
        if os.path.isdir(expanded):
            return expanded
        return None

    def detect(
        self, scope=Scope.GLOBAL, project_dir=None, follow_symlinks=True
    ):
        """Return the agent if installed, with skills paths for ``scope``."""
        base_dir = self.resolve_base_dir()
        if base_dir is None:
            return None
        return DetectedAgent(
            self, base_dir, scope, project_dir, follow_symlinks
        )


class DetectedAgent:
    """An agent that was found installed on this machine."""

    def __init__(
        self,
        config,
        base_dir,
        scope=Scope.GLOBAL,
        project_dir=None,
        follow_symlinks=True,
    ):
        if scope is Scope.PROJECT and project_dir is None:
            raise ValueError('A project directory is required.')
        self.config = config
        self.base_dir = base_dir
        self.scope = scope
        self.project_dir = project_dir
        self.follow_symlinks = follow_symlinks

    @property
    def display_name(self):
        return self.config.display_name

    @property
    def display_label(self):
        return self.label_for(self.skills_path)

    def label_for(self, skills_path):
        """Return a label naming this agent and one of its skills paths."""
        return f'{self.display_name} — {collapse_home(skills_path)}'

    @property
    def skills_paths(self):
        """Every skills directory of this agent in its scope, in priority
        order."""
        if self.scope is Scope.PROJECT:
            return [
                os.path.normpath(os.path.join(self.project_dir, path))
                for path in self.config.skills_paths
            ]
        detection_dir = os.path.normpath(
            self.config.expand_path(self.config.detection_path)
        )
        paths = []
        home = self.config.expand_path('~')
        for path in self.config.skills_paths:
            path = os.path.normpath(os.path.join(home, path))
            relative = _relative_path_within(path, detection_dir)
            if relative is not None:
                # Under the detection directory, so it moves with an
                # override of that directory.
                path = os.path.normpath(os.path.join(self.base_dir, relative))
            paths.append(path)
        return paths

    @property
    def skills_path(self):
        """The skills directory new skills are installed into."""
        return self.skills_paths[0]

    def can_write(self, path):
        """Whether the CLI may change ``path``.

        Symbolic links are followed unless ``follow_symlinks`` is off. Then
        a path that is a symbolic link, or is under one, is refused,
        starting below the scope's root: the project directory, or the home
        directory for global skills. Links above the root are still
        followed.
        """
        if self.follow_symlinks:
            return True
        path = os.path.normpath(path)
        for root in self._symlink_check_roots():
            relative = _relative_path_within(path, root)
            if relative is not None:
                return not _has_symlink_below(root, relative)
        return not os.path.islink(path)

    def _symlink_check_roots(self):
        """Roots that symbolic links are checked below. The first root
        that contains a path is used.

        An agent directory moved out of the home directory by
        ``detection_path_env_override`` is checked like one in it, so the
        moved directory itself counts as below the root.
        """
        if self.scope is Scope.PROJECT:
            return [os.path.normpath(self.project_dir)]
        return [
            os.path.normpath(self.config.expand_path('~')),
            os.path.dirname(os.path.normpath(self.base_dir)),
        ]

    def skill_dirs(self, skill_name):
        """Return the directories to install ``skill_name`` into.

        These are the existing entries named ``skill_name`` in any skills
        directory, so an installed skill is changed where it is. When there
        are none, it is the directory under :attr:`skills_path`.
        """
        dirs = []
        seen = set()
        for root in self.skills_paths:
            skill_dir = os.path.join(root, skill_name)
            real_dir = os.path.realpath(skill_dir)
            if real_dir in seen or not os.path.lexists(skill_dir):
                continue
            seen.add(real_dir)
            dirs.append(skill_dir)
        return dirs or [os.path.join(self.skills_path, skill_name)]

    @property
    def mcp_config_file(self):
        if self.config.mcp_config_path is None:
            return None
        if self.config.mcp_config_path.startswith('~'):
            override = self.config.resolved_override_dir()
            if override is not None:
                relative = self.config.mcp_config_path.removeprefix('~/')
                return os.path.join(override, relative)
            return self.config.expand_path(self.config.mcp_config_path)
        return os.path.join(self.base_dir, self.config.mcp_config_path)

    def _skill_files(self):
        seen_roots = set()
        for root in self.skills_paths:
            real_root = os.path.realpath(root)
            if real_root in seen_roots:
                continue
            seen_roots.add(real_root)
            pattern = os.path.join(root, '*', SKILL_FILENAME)
            yield from sorted(glob.glob(pattern))

    def get_installed_skills(self):
        """Return the AWS skills in every skills directory of this agent.

        Skills are ordered by skills directory priority, then by name.
        """
        results = []
        for skill_path in self._skill_files():
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
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _write_mcp_config(path, config):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        is_new = not os.path.exists(path)
        with open(path, 'w', encoding='utf-8') as f:
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


AGENT_CONFIGS = [
    # https://docs.anthropic.com/en/docs/claude-code/mcp
    AgentConfig(
        id='claude-code',
        display_name='Claude Code',
        detection_path='~/.claude/',
        skills_paths=['.claude/skills'],
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
        skills_paths=['.cline/skills'],
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
        skills_paths=['.agents/skills'],
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
        skills_paths=['.agents/skills', '.cursor/skills'],
        mcp_config_path='mcp.json',
        mcp_servers_key='mcpServers',
    ),
    # https://docs.devin.ai/cli/extensibility/mcp/configuration
    # https://docs.devin.ai/cli/extensibility/skills/overview
    # Covers Devin CLI and the Devin Local agent in Devin Desktop, which
    # share ~/.config/devin/.
    # Windows (%APPDATA%\devin) and a non-default $XDG_CONFIG_HOME are not
    # detected.
    AgentConfig(
        id='devin',
        display_name='Devin',
        detection_path='~/.config/devin/',
        skills_paths=['.agents/skills'],
        mcp_config_path='mcp_config.json',
        mcp_servers_key='mcpServers',
    ),
    # https://geminicli.com/docs/cli/tutorials/mcp-setup/
    # https://geminicli.com/docs/cli/skills/
    AgentConfig(
        id='gemini-cli',
        display_name='Gemini CLI',
        detection_path='~/.gemini/',
        home_env_override='GEMINI_CLI_HOME',
        skills_paths=['.agents/skills'],
        mcp_config_path='settings.json',
        mcp_servers_key='mcpServers',
    ),
    # https://kiro.dev/docs/mcp/configuration/
    AgentConfig(
        id='kiro',
        display_name='Kiro',
        detection_path='~/.kiro/',
        skills_paths=['.kiro/skills'],
        mcp_config_path='settings/mcp.json',
        mcp_servers_key='mcpServers',
        mcp_extra_config={'timeout': 100000, 'transport': 'stdio'},
    ),
    # https://openclaw-openclaw.mintlify.app/configuration
    # https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md
    # OpenClaw does not document MCP support — install skills only.
    AgentConfig(
        id='openclaw',
        display_name='OpenClaw',
        detection_path='~/.openclaw/',
        skills_paths=['.agents/skills', '.openclaw/skills'],
    ),
    # https://docs.opencode.ai/docs/mcp-servers
    # https://docs.opencode.ai/docs/skills
    AgentConfig(
        id='opencode',
        display_name='OpenCode',
        detection_path='~/.config/opencode/',
        skills_paths=['.agents/skills'],
        mcp_config_path='opencode.json',
        mcp_servers_key='mcp',
        mcp_server_entry={
            'type': 'local',
            'command': ['uvx', *_AWS_MCP_PROXY_ARGS],
        },
    ),
    # https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md
    # https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md
    # Pi does not document MCP support — install skills only.
    AgentConfig(
        id='pi',
        display_name='Pi',
        detection_path='~/.pi/agent/',
        skills_paths=['.agents/skills', '.pi/agent/skills'],
    ),
    # https://docs.windsurf.com/plugins/cascade/mcp
    # https://docs.windsurf.com/windsurf/cascade/skills
    AgentConfig(
        id='windsurf',
        display_name='Windsurf',
        detection_path='~/.codeium/windsurf/',
        skills_paths=['.agents/skills'],
        mcp_config_path='~/.codeium/mcp_config.json',
        mcp_servers_key='mcpServers',
    ),
]


def _build_universal_row(configs):
    universal_path = os.path.normpath('.agents/skills')
    consumers = [
        c.display_name
        for c in configs
        if any(
            os.path.normpath(path) == universal_path for path in c.skills_paths
        )
    ]
    return AgentConfig(
        id=UNIVERSAL_ROW_ID,
        display_name=f'Universal ({", ".join(consumers)})',
        detection_path='~/.agents',
        skills_paths=['.agents/skills'],
    )


AGENT_CONFIGS.append(_build_universal_row(AGENT_CONFIGS))


def universal_first(items, get_id=lambda a: a.config.id):
    return sorted(
        items,
        key=lambda i: 0 if get_id(i) == UNIVERSAL_ROW_ID else 1,
    )


def get_detected_agents(
    agent_configs=None,
    scope=Scope.GLOBAL,
    project_dir=None,
    follow_symlinks=True,
):
    if agent_configs is None:
        agent_configs = AGENT_CONFIGS
    detected = []
    for config in agent_configs:
        agent = config.detect(scope, project_dir, follow_symlinks)
        if agent is not None:
            detected.append(agent)
    return detected


def get_detected_real_agents(agent_configs=None):
    return [
        agent
        for agent in get_detected_agents(agent_configs)
        if agent.config.id != UNIVERSAL_ROW_ID
    ]
