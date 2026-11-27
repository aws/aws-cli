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
import json
import os
from unittest.mock import patch

import pytest

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    DEFAULT_MCP_SERVER_CONFIG,
    UNIVERSAL_ROW_ID,
    AgentConfig,
    DetectedAgent,
    McpConfigureAction,
    get_detected_agents,
    get_detected_real_agents,
)
from awscli.testutils import skip_if_windows
from tests.unit.customizations.agenttoolkit.utils import (
    home_relative,
    make_config,
    make_skill,
)


def test_detect_when_installed(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(tmp_path)
    agent = config.detect()
    assert isinstance(agent, DetectedAgent)
    assert agent.display_name == 'Test Agent'
    assert agent.base_dir == str(tmp_path / '.test-agent')


def test_detect_when_not_installed(tmp_path):
    config = make_config(tmp_path)
    assert config.detect() is None


def test_detect_env_override(tmp_path, monkeypatch):
    (tmp_path / '.test-agent').mkdir()
    override_dir = tmp_path / '.custom-location'
    override_dir.mkdir()
    config = make_config(
        tmp_path,
        detection_path_env_override='TEST_CONFIG_DIR',
    )
    monkeypatch.setenv('TEST_CONFIG_DIR', str(override_dir))
    agent = config.detect()
    assert agent.base_dir == str(override_dir)


def test_detect_env_override_falls_back(tmp_path, monkeypatch):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(
        tmp_path,
        detection_path_env_override='TEST_CONFIG_DIR',
    )
    monkeypatch.setenv('TEST_CONFIG_DIR', str(tmp_path / 'nonexistent'))
    agent = config.detect()
    assert agent.base_dir == str(tmp_path / '.test-agent')


def test_get_installed_skills_finds_aws_skills(tmp_path):
    make_skill(tmp_path, '.test-agent', 'aws-serverless')
    make_skill(tmp_path, '.test-agent', 'aws-databases')
    config = make_config(tmp_path)
    agent = config.detect()
    skills = agent.get_installed_skills()
    assert len(skills) == 2
    assert skills[0].name == 'aws-databases'
    assert skills[0].agent.display_name == 'Test Agent'
    assert skills[1].name == 'aws-serverless'
    assert skills[1].path.endswith(os.path.join('aws-serverless', 'SKILL.md'))


def test_skills_path_outside_detection_dir(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    override_dir = tmp_path / 'shared' / 'skills'
    config = make_config(
        tmp_path,
        skills_paths=[home_relative(tmp_path, override_dir)],
    )
    agent = config.detect()
    assert agent.skills_path == str(override_dir)


def test_universal_row_display_name_lists_consumers():
    from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS

    universal = next(c for c in AGENT_CONFIGS if c.id == 'universal')
    assert universal.detection_path == '~/.agents'
    for config in AGENT_CONFIGS:
        if any(
            p.rstrip('/').endswith('.agents/skills')
            for p in config.skills_paths
        ):
            assert config.display_name in universal.display_name


def test_get_installed_skills_excludes_unmarked(tmp_path):
    make_skill(tmp_path, '.test-agent', 'aws-installed', with_marker=True)
    make_skill(tmp_path, '.test-agent', 'hand-rolled', with_marker=False)
    config = make_config(tmp_path)
    skills = config.detect().get_installed_skills()
    names = [s.name for s in skills]
    assert names == ['aws-installed']


def test_get_installed_skills_empty(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    config = make_config(tmp_path)
    assert config.detect().get_installed_skills() == []


def test_get_detected_agents(tmp_path):
    (tmp_path / '.kiro').mkdir()
    test_configs = [
        AgentConfig(
            id='kiro',
            display_name='Kiro',
            detection_path=str(tmp_path / '.kiro'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.kiro', 'skills')
            ],
        ),
        AgentConfig(
            id='cursor',
            display_name='Cursor',
            detection_path=str(tmp_path / '.cursor'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.cursor', 'skills')
            ],
        ),
    ]
    detected = get_detected_agents(agent_configs=test_configs)
    assert len(detected) == 1
    assert detected[0].display_name == 'Kiro'


def test_get_detected_real_agents_excludes_universal_row(tmp_path):
    # Only the universal row detects (``~/.agents`` exists) but no real
    # per-agent directory does. The wizard would find nothing here, so the
    # hint must not treat this as an eligible detection.
    (tmp_path / '.agents').mkdir()
    test_configs = [
        AgentConfig(
            id='cursor',
            display_name='Cursor',
            detection_path=str(tmp_path / '.cursor'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.cursor', 'skills')
            ],
        ),
        AgentConfig(
            id=UNIVERSAL_ROW_ID,
            display_name='Universal',
            detection_path=str(tmp_path / '.agents'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.agents', 'skills')
            ],
        ),
    ]
    assert get_detected_agents(agent_configs=test_configs)
    assert get_detected_real_agents(agent_configs=test_configs) == []


def test_mcp_config_path_honors_detection_env_override(tmp_path, monkeypatch):
    (tmp_path / '.test-agent').mkdir()
    override_dir = tmp_path / '.custom-location'
    override_dir.mkdir()
    config = make_config(
        tmp_path,
        detection_path_env_override='TEST_CONFIG_DIR',
        mcp_config_path='~/.test-agent.json',
    )
    monkeypatch.setenv('TEST_CONFIG_DIR', str(override_dir))
    agent = config.detect()
    assert agent.mcp_config_file == str(override_dir / '.test-agent.json')


def test_mcp_config_path_falls_back_when_env_override_dir_missing(
    tmp_path, monkeypatch
):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(
        tmp_path,
        detection_path_env_override='TEST_CONFIG_DIR',
        mcp_config_path='~/.test-agent.json',
    )
    monkeypatch.setenv('TEST_CONFIG_DIR', str(tmp_path / 'nonexistent'))
    agent = config.detect()
    assert agent.mcp_config_file == os.path.expanduser('~/.test-agent.json')


def _home_override_config(tmp_path, monkeypatch, **kwargs):
    home = tmp_path / 'agent-home'
    (home / '.test-agent').mkdir(parents=True)
    monkeypatch.setenv('TEST_AGENT_HOME', str(home))
    config = AgentConfig(
        id='test-agent',
        display_name='Test Agent',
        detection_path='~/.test-agent/',
        home_env_override='TEST_AGENT_HOME',
        **{'skills_paths': ['.test-agent/skills'], **kwargs},
    )
    return home, config


def test_home_env_override_moves_every_tilde_path(tmp_path, monkeypatch):
    home, config = _home_override_config(
        tmp_path,
        monkeypatch,
        skills_paths=['.agents/skills'],
        mcp_config_path='settings.json',
    )
    agent = config.detect()
    assert agent.base_dir == str(home / '.test-agent')
    assert agent.skills_path == str(home / '.agents' / 'skills')
    assert agent.mcp_config_file == str(home / '.test-agent' / 'settings.json')


def test_home_env_override_applies_to_tilde_mcp_path(tmp_path, monkeypatch):
    home, config = _home_override_config(
        tmp_path, monkeypatch, mcp_config_path='~/.test-agent.json'
    )
    assert config.detect().mcp_config_file == str(home / '.test-agent.json')


def test_home_env_override_not_detected_without_agent_dir(
    tmp_path, monkeypatch
):
    monkeypatch.setenv('TEST_AGENT_HOME', str(tmp_path / 'empty-home'))
    config = AgentConfig(
        id='test-agent',
        display_name='Test Agent',
        detection_path='~/.test-agent/',
        skills_paths=['.test-agent/skills'],
        home_env_override='TEST_AGENT_HOME',
    )
    assert config.detect() is None


def test_expand_path_without_home_env_override(monkeypatch):
    monkeypatch.delenv('TEST_AGENT_HOME', raising=False)
    config = AgentConfig(
        id='test-agent',
        display_name='Test Agent',
        detection_path='~/.test-agent/',
        skills_paths=['.test-agent/skills'],
        home_env_override='TEST_AGENT_HOME',
    )
    assert config.expand_path('~/.x') == os.path.expanduser('~/.x')
    assert config.expand_path('/abs/path') == '/abs/path'


def test_gemini_uses_gemini_cli_home():
    gemini = next(c for c in AGENT_CONFIGS if c.id == 'gemini-cli')
    assert gemini.home_env_override == 'GEMINI_CLI_HOME'


def test_mcp_config_path_falls_back_to_home_without_env_override(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(tmp_path, mcp_config_path='~/.test-agent.json')
    agent = config.detect()
    assert agent.mcp_config_file == os.path.expanduser('~/.test-agent.json')


def test_configure_mcp_new_file(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    action, path = agent.configure_mcp_server()
    assert action is McpConfigureAction.CONFIGURED
    data = json.loads(open(path).read())
    assert data['mcpServers']['aws-mcp']['command'] == 'uvx'
    assert 'mcp-proxy-for-aws@latest' in data['mcpServers']['aws-mcp']['args']


def test_configure_mcp_already_configured(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    mcp_path.write_text(
        json.dumps({'mcpServers': {'aws-mcp': {'command': 'custom'}}})
    )
    action, _ = agent.configure_mcp_server()
    assert action is McpConfigureAction.ALREADY_CONFIGURED
    data = json.loads(mcp_path.read_text())
    assert data['mcpServers']['aws-mcp']['command'] == 'custom'


def test_configure_mcp_preserves_other_servers(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    mcp_path.write_text(
        json.dumps({'mcpServers': {'other': {'command': 'foo'}}})
    )
    agent.configure_mcp_server()
    data = json.loads(mcp_path.read_text())
    assert data['mcpServers']['other']['command'] == 'foo'
    assert 'aws-mcp' in data['mcpServers']


def test_configure_mcp_extra_config_merged(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(
        tmp_path,
        mcp_config_path='mcp.json',
        mcp_extra_config={'timeout': 100000},
    ).detect()
    agent.configure_mcp_server()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    data = json.loads(mcp_path.read_text())
    entry = data['mcpServers']['aws-mcp']
    assert entry['timeout'] == 100000
    assert entry['command'] == 'uvx'


def test_configure_mcp_server_entry_overrides_default(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    custom_entry = {
        'type': 'local',
        'command': ['uvx', 'something@latest'],
    }
    agent = make_config(
        tmp_path,
        mcp_config_path='mcp.json',
        mcp_servers_key='mcp',
        mcp_server_entry=custom_entry,
    ).detect()
    agent.configure_mcp_server()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    data = json.loads(mcp_path.read_text())
    entry = data['mcp']['aws-mcp']
    assert entry == custom_entry
    assert 'args' not in entry


def test_configure_mcp_shell_command_runs_when_executable_present(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(
        tmp_path,
        mcp_shell_command=['some-cli', 'mcp', 'add', 'aws-mcp'],
    )
    agent = config.detect()
    with (
        patch(
            'awscli.customizations.agenttoolkit.agents.shutil.which',
            return_value='/usr/local/bin/some-cli',
        ),
        patch(
            'awscli.customizations.agenttoolkit.agents.subprocess.run'
        ) as run_mock,
    ):
        action, detail = agent.configure_mcp_server()
    assert action is McpConfigureAction.CONFIGURED
    assert detail == 'some-cli'
    run_mock.assert_called_once_with(
        ['some-cli', 'mcp', 'add', 'aws-mcp'], check=True
    )


def test_configure_mcp_shell_command_skipped_when_executable_missing(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    config = make_config(
        tmp_path,
        mcp_shell_command=['missing-cli', 'mcp', 'add', 'aws-mcp'],
    )
    agent = config.detect()
    with (
        patch(
            'awscli.customizations.agenttoolkit.agents.shutil.which',
            return_value=None,
        ),
        patch(
            'awscli.customizations.agenttoolkit.agents.subprocess.run'
        ) as run_mock,
    ):
        action, detail = agent.configure_mcp_server()
    assert action is McpConfigureAction.SKIPPED
    assert detail == 'missing-cli'
    run_mock.assert_not_called()


def test_configure_mcp_creates_parent_directories(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(
        tmp_path, mcp_config_path='nested/dir/mcp.json'
    ).detect()
    agent.configure_mcp_server()
    assert (tmp_path / '.test-agent' / 'nested' / 'dir' / 'mcp.json').exists()


@skip_if_windows("POSIX file permissions are not enforced on Windows.")
def test_configure_mcp_new_file_gets_0600_permissions(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    agent.configure_mcp_server()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    assert oct(mcp_path.stat().st_mode & 0o777) == oct(0o600)


@skip_if_windows("POSIX file permissions are not enforced on Windows.")
def test_configure_mcp_preserves_existing_permissions(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    mcp_path.write_text(json.dumps({'mcpServers': {}}))
    os.chmod(mcp_path, 0o644)
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    agent.configure_mcp_server()
    assert oct(mcp_path.stat().st_mode & 0o777) == oct(0o644)


def test_agent_configs_sorted_alphabetically():
    ids = [c.id for c in AGENT_CONFIGS if c.id != 'universal']
    assert ids == sorted(ids)


def _get_agent_config(agent_id):
    return next(c for c in AGENT_CONFIGS if c.id == agent_id)


def test_devin_config():
    devin = _get_agent_config('devin')
    assert devin.display_name == 'Devin'
    assert devin.detection_path == '~/.config/devin/'
    assert devin.detection_path_env_override is None
    assert devin.skills_paths == ['.agents/skills']
    assert devin.mcp_config_path == 'mcp_config.json'
    assert devin.mcp_servers_key == 'mcpServers'
    assert devin.mcp_extra_config == {}
    assert devin.mcp_server_entry is None
    assert devin.mcp_shell_command is None
    assert 'Devin' in _get_agent_config(UNIVERSAL_ROW_ID).display_name


def test_devin_configure_mcp_writes_default_entry(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    devin_dir = tmp_path / '.config' / 'devin'
    devin_dir.mkdir(parents=True)
    agent = _get_agent_config('devin').detect()
    assert os.path.normpath(agent.skills_path) == os.path.normpath(
        str(tmp_path / '.agents' / 'skills')
    )
    action, path = agent.configure_mcp_server()
    assert action is McpConfigureAction.CONFIGURED
    assert os.path.normpath(path) == os.path.normpath(
        str(devin_dir / 'mcp_config.json')
    )
    data = json.loads((devin_dir / 'mcp_config.json').read_text())
    assert data == {'mcpServers': {'aws-mcp': DEFAULT_MCP_SERVER_CONFIG}}


def _multi_path_config(tmp_path):
    (tmp_path / '.test-agent').mkdir(exist_ok=True)
    secondary = tmp_path / 'secondary'
    return make_config(
        tmp_path,
        skills_paths=[
            home_relative(tmp_path, tmp_path / '.test-agent' / 'skills'),
            home_relative(tmp_path, secondary),
        ],
    )


def test_skills_paths_resolved_in_priority_order(tmp_path):
    agent = _multi_path_config(tmp_path).detect()
    assert agent.skills_paths == [
        os.path.join(str(tmp_path / '.test-agent'), 'skills'),
        str(tmp_path / 'secondary'),
    ]
    assert agent.skills_path == agent.skills_paths[0]


def test_undetected_label_matches_detected_label(tmp_path):
    config = make_config(tmp_path, skills_paths=['.test-agent/skills'])
    undetected_label = config.display_label
    (tmp_path / '.test-agent').mkdir()
    detected_label = config.detect().display_label
    assert undetected_label == detected_label
    assert undetected_label == (
        f'Test Agent — ~{os.sep}{os.path.join(".test-agent", "skills")}'
    )


def test_skills_paths_must_not_be_empty(tmp_path):
    with pytest.raises(ValueError, match='at least one skills path'):
        make_config(tmp_path, skills_paths=[])


def test_get_installed_skills_checks_every_skills_path(tmp_path):
    agent = _multi_path_config(tmp_path).detect()
    make_skill(tmp_path, 'secondary', 'aws-iam')
    (tmp_path / 'secondary' / 'skills' / 'aws-iam').rename(
        tmp_path / 'secondary' / 'aws-iam'
    )
    make_skill(tmp_path, '.test-agent', 'aws-s3')
    skills = agent.get_installed_skills()
    assert [s.name for s in skills] == ['aws-s3', 'aws-iam']


def test_get_installed_skills_reads_shared_root_once(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    shared = os.path.join('.test-agent', 'skills')
    config = make_config(tmp_path, skills_paths=[shared, shared + '/'])
    make_skill(tmp_path, '.test-agent', 'aws-s3')
    assert [s.name for s in config.detect().get_installed_skills()] == [
        'aws-s3'
    ]


def test_skill_dirs_defaults_to_primary_path(tmp_path):
    agent = _multi_path_config(tmp_path).detect()
    assert agent.skill_dirs('aws-s3') == [
        os.path.join(agent.skills_paths[0], 'aws-s3')
    ]


def test_skill_dirs_returns_existing_locations(tmp_path):
    agent = _multi_path_config(tmp_path).detect()
    existing = tmp_path / 'secondary' / 'aws-s3'
    existing.mkdir(parents=True)
    assert agent.skill_dirs('aws-s3') == [str(existing)]


@pytest.mark.parametrize(
    'agent_id, skills_paths',
    [
        ('claude-code', ['.claude/skills']),
        ('cline', ['.cline/skills']),
        ('codex', ['.agents/skills']),
        ('cursor', ['.agents/skills', '.cursor/skills']),
        ('devin', ['.agents/skills']),
        ('gemini-cli', ['.agents/skills']),
        ('kiro', ['.kiro/skills']),
        ('openclaw', ['.agents/skills', '.openclaw/skills']),
        ('opencode', ['.agents/skills']),
        ('pi', ['.agents/skills', '.pi/agent/skills']),
        ('windsurf', ['.agents/skills']),
    ],
)
def test_agent_skills_paths(agent_id, skills_paths):
    assert _get_agent_config(agent_id).skills_paths == skills_paths


def test_shared_skills_path_matches_universal_row(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    (tmp_path / '.codex').mkdir()
    (tmp_path / '.agents').mkdir()
    codex = _get_agent_config('codex').detect()
    universal = _get_agent_config(UNIVERSAL_ROW_ID).detect()
    assert codex.skills_path == universal.skills_path


@pytest.mark.parametrize(
    'path', ['~/.test-agent/skills', '/abs/skills', '\\abs\\skills']
)
def test_skills_paths_must_be_relative_to_home(tmp_path, path):
    with pytest.raises(ValueError, match='relative to the home directory'):
        make_config(tmp_path, skills_paths=[path])


def test_skills_path_under_detection_dir_follows_env_override(
    tmp_path, monkeypatch
):
    (tmp_path / '.test-agent').mkdir()
    override_dir = tmp_path / '.custom-location'
    override_dir.mkdir()
    shared = str(tmp_path / 'shared' / 'skills')
    config = make_config(
        tmp_path,
        detection_path_env_override='TEST_CONFIG_DIR',
        skills_paths=[
            home_relative(tmp_path, tmp_path / '.test-agent' / 'skills'),
            home_relative(tmp_path, shared),
        ],
    )
    monkeypatch.setenv('TEST_CONFIG_DIR', str(override_dir))
    assert config.detect().skills_paths == [
        str(override_dir / 'skills'),
        shared,
    ]
