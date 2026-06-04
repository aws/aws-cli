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

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    AgentConfig,
    DetectedAgent,
    McpConfigureAction,
    get_detected_agents,
)
from tests.unit.customizations.agenttoolkit.utils import (
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
    assert skills[1].path.endswith('aws-serverless/SKILL.md')


def test_skills_path_override(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    override_dir = tmp_path / 'shared' / 'skills'
    config = make_config(
        tmp_path,
        skills_path_override=str(override_dir),
    )
    agent = config.detect()
    assert agent.skills_path == str(override_dir)


def test_universal_row_display_name_lists_consumers():
    from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS

    universal = next(c for c in AGENT_CONFIGS if c.id == 'universal')
    assert universal.detection_path == '~/.agents'
    for config in AGENT_CONFIGS:
        if config.skills_path_override and config.skills_path_override.rstrip(
            '/'
        ).endswith('.agents/skills'):
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
        ),
        AgentConfig(
            id='cursor',
            display_name='Cursor',
            detection_path=str(tmp_path / '.cursor'),
        ),
    ]
    detected = get_detected_agents(agent_configs=test_configs)
    assert len(detected) == 1
    assert detected[0].display_name == 'Kiro'


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


def test_configure_mcp_new_file_gets_0600_permissions(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path, mcp_config_path='mcp.json').detect()
    agent.configure_mcp_server()
    mcp_path = tmp_path / '.test-agent' / 'mcp.json'
    assert oct(mcp_path.stat().st_mode & 0o777) == oct(0o600)


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
