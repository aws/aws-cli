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
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from awscli.customizations.agenttoolkit import state
from awscli.customizations.agenttoolkit.agents import AgentConfig
from awscli.customizations.agenttoolkit.configure import (
    AUTO_UPDATE_PROMPT,
    ConfigureAgentToolkitCommand,
)
from awscli.customizations.exceptions import ConfigurationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_session,
    make_skill_zip,
)


@pytest.fixture(autouse=True)
def state_file(tmp_path):
    path = tmp_path / 'agent-toolkit-state' / 'state.json'
    with patch.object(state, 'STATE_PATH', str(path)):
        yield path


def _make_agent_configs(tmp_path, count=2):
    configs = []
    for i in range(count):
        agent_dir = tmp_path / f'.agent-{i}'
        agent_dir.mkdir()
        configs.append(
            make_config(
                tmp_path,
                id=f'agent-{i}',
                display_name=f'Agent {i}',
                detection_path=str(agent_dir),
                mcp_config_path='mcp.json',
            )
        )
    return configs


def _make_client(skills=None):
    """Create a mock client that returns the given default skills."""
    if skills is None:
        skills = []
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [{'skills': skills}]
    client.get_paginator.return_value = paginator
    return client


def _run(
    agent_configs, yes_no_return=True, client=None, yes=False, prompts=None
):
    stream = StringIO()
    session = make_session()
    if client is None:
        client = _make_client()
    cmd = ConfigureAgentToolkitCommand(
        session, stream=stream, agent_configs=agent_configs, client=client
    )
    parsed_args = MagicMock()
    parsed_args.yes = yes
    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
            side_effect=lambda msg, items, **kw: items,
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice',
            return_value=yes_no_return,
        ) as yes_no,
    ):
        rc = cmd._run_main(parsed_args, None)
    if prompts is not None:
        prompts.extend(c.args[0] for c in yes_no.call_args_list)
    return rc, stream


def test_no_agents_detected_raises_error(tmp_path):
    configs = [
        AgentConfig(
            id='missing',
            display_name='Missing',
            detection_path=str(tmp_path / 'nonexistent'),
        )
    ]
    with pytest.raises(ConfigurationError):
        _run(configs)


def test_detection_output(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    configs.append(
        AgentConfig(
            id='missing',
            display_name='Missing Agent',
            detection_path=str(tmp_path / 'nope'),
        )
    )
    _, stream = _run(configs)
    output = stream.getvalue()
    assert '\u2713 Agent 0' in output
    assert '\u2717 Missing Agent' in output
    assert '(not found)' in output


def test_mcp_configured_on_yes(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    _run(configs, yes_no_return=True)
    mcp_path = tmp_path / '.agent-0' / 'mcp.json'
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    assert 'aws-mcp' in data['mcpServers']
    assert data['mcpServers']['aws-mcp']['command'] == 'uvx'


def test_mcp_skipped_on_no(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    _run(configs, yes_no_return=False)
    mcp_path = tmp_path / '.agent-0' / 'mcp.json'
    assert not mcp_path.exists()


def test_mcp_already_configured_not_overwritten(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    mcp_path = tmp_path / '.agent-0' / 'mcp.json'
    mcp_path.write_text(
        json.dumps(
            {'mcpServers': {'aws-mcp': {'command': 'custom', 'args': []}}}
        )
    )
    _, stream = _run(configs, yes_no_return=True)
    data = json.loads(mcp_path.read_text())
    assert data['mcpServers']['aws-mcp']['command'] == 'custom'
    assert 'already configured' in stream.getvalue()


def test_default_skills_installed(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    zip_bytes, checksum = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        return_value=(zip_bytes, checksum, 'v1'),
    ):
        _, stream = _run(configs, yes_no_return=True, client=client)
    skill_path = (
        tmp_path / '.agent-0' / 'skills' / 'aws-serverless' / 'SKILL.md'
    )
    assert skill_path.exists()
    assert '[1/1] aws-serverless' in stream.getvalue()


def test_default_skills_skipped_on_no(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    _run(configs, yes_no_return=False, client=client)
    skill_path = tmp_path / '.agent-0' / 'skills' / 'aws-serverless'
    assert not skill_path.exists()


def test_wizard_hides_universal_row_from_detection(tmp_path):
    universal_dir = tmp_path / '.agents' / 'skills'
    universal_dir.mkdir(parents=True)
    real_dir = tmp_path / '.codex'
    real_dir.mkdir()
    configs = [
        AgentConfig(
            id='codex',
            display_name='Codex',
            detection_path=str(real_dir),
            skills_path_override=str(universal_dir),
            mcp_config_path='mcp.json',
        ),
        AgentConfig(
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(tmp_path / '.agents'),
        ),
    ]
    _, stream = _run(configs)
    output = stream.getvalue()
    assert '✓ Codex' in output
    assert 'Universal' not in output


def test_wizard_credits_universal_row_for_shared_path_install(tmp_path):
    universal_dir = tmp_path / '.agents' / 'skills'
    universal_dir.mkdir(parents=True)
    real_dir = tmp_path / '.codex'
    real_dir.mkdir()
    configs = [
        AgentConfig(
            id='codex',
            display_name='Codex',
            detection_path=str(real_dir),
            skills_path_override=str(universal_dir),
            mcp_config_path='mcp.json',
        ),
        AgentConfig(
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(tmp_path / '.agents'),
        ),
    ]
    zip_bytes, checksum = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-cdk'}])
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        return_value=(zip_bytes, checksum, 'v1'),
    ):
        _, stream = _run(configs, yes_no_return=True, client=client)
    output = stream.getvalue()
    assert 'Universal (Codex)' in output
    assert (universal_dir / 'aws-cdk' / 'SKILL.md').exists()


def test_yes_skips_all_prompts(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    zip_bytes, checksum = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.get_skill_download',
            return_value=(zip_bytes, checksum, 'v1'),
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
        ) as multiselect_mock,
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice',
        ) as yes_no_mock,
    ):
        stream = StringIO()
        cmd = ConfigureAgentToolkitCommand(
            make_session(),
            stream=stream,
            agent_configs=configs,
            client=client,
        )
        parsed_args = MagicMock()
        parsed_args.yes = True
        cmd._run_main(parsed_args, None)
    multiselect_mock.assert_not_called()
    yes_no_mock.assert_not_called()
    skill_path = (
        tmp_path / '.agent-0' / 'skills' / 'aws-serverless' / 'SKILL.md'
    )
    assert skill_path.exists()
    mcp_path = tmp_path / '.agent-0' / 'mcp.json'
    assert mcp_path.exists()


def test_skill_checksum_failure_reported(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    zip_bytes, _ = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-bad'}])
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        return_value=(zip_bytes, 'bad' * 21 + 'x', 'v1'),
    ):
        _, stream = _run(configs, yes_no_return=True, client=client)
    assert '[1/1] aws-bad' in stream.getvalue()
    skill_path = tmp_path / '.agent-0' / 'skills' / 'aws-bad'
    assert not skill_path.exists()


def _auto_update_prompts(prompts):
    return [p for p in prompts if p == AUTO_UPDATE_PROMPT]


def test_auto_update_prompt_mentions_core_skills():
    assert 'new core AWS skills' in AUTO_UPDATE_PROMPT


def test_auto_update_enabled_on_yes(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    prompts = []
    _, stream = _run(configs, yes_no_return=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_PROMPT]
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True
    }
    assert 'Automatic skill updates enabled.' in stream.getvalue()


def test_auto_update_disabled_on_no(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    _, stream = _run(configs, yes_no_return=False)
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': False
    }
    assert 'Automatic skill updates enabled' not in stream.getvalue()


def test_auto_update_enabled_without_prompt_on_yes_flag(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    prompts = []
    _run(configs, yes=True, prompts=prompts)
    assert prompts == []
    assert state.is_auto_update_enabled()


def test_auto_update_not_prompted_when_already_enabled(tmp_path, state_file):
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        json.dumps({'agent_toolkit_auto_update': True, 'hint_dismissed': True})
    )
    configs = _make_agent_configs(tmp_path, count=1)
    prompts = []
    _, stream = _run(configs, yes_no_return=False, prompts=prompts)
    assert _auto_update_prompts(prompts) == []
    assert 'Automatic skill updates are enabled.' in stream.getvalue()
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True,
        'hint_dismissed': True,
    }


def test_auto_update_prompted_again_when_previously_declined(
    tmp_path, state_file
):
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({'agent_toolkit_auto_update': False}))
    configs = _make_agent_configs(tmp_path, count=1)
    prompts = []
    _run(configs, yes_no_return=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_PROMPT]
    assert state.is_auto_update_enabled()


def test_auto_update_preserves_other_state_keys(tmp_path, state_file):
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({'hint_dismissed': True}))
    configs = _make_agent_configs(tmp_path, count=1)
    _run(configs, yes_no_return=True)
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True,
        'hint_dismissed': True,
    }


def test_auto_update_corrupt_state_file_is_reported_not_overwritten(
    tmp_path, state_file
):
    state_file.parent.mkdir(parents=True)
    state_file.write_text('{ not valid json')
    configs = _make_agent_configs(tmp_path, count=1)
    rc, stream = _run(configs, yes_no_return=True)
    assert rc == 0
    assert state_file.read_text() == '{ not valid json'
    assert (
        'Could not save the automatic skill update setting'
        in stream.getvalue()
    )


def test_auto_update_write_failure_is_reported(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    with patch(
        'awscli.customizations.agenttoolkit.configure.set_auto_update',
        side_effect=state.StateFileError('/x/state.json: disk full'),
    ):
        rc, stream = _run(configs, yes_no_return=True)
    assert rc == 0
    assert (
        'Could not save the automatic skill update setting to '
        '/x/state.json: disk full\n' in stream.getvalue()
    )
    assert 'Automatic skill updates enabled' not in stream.getvalue()


def test_auto_update_not_prompted_when_no_agents_selected(
    tmp_path, state_file
):
    configs = _make_agent_configs(tmp_path, count=1)
    stream = StringIO()
    cmd = ConfigureAgentToolkitCommand(
        make_session(),
        stream=stream,
        agent_configs=configs,
        client=MagicMock(),
    )
    parsed_args = MagicMock()
    parsed_args.yes = False
    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
            return_value=[],
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice'
        ) as yes_no,
    ):
        cmd._run_main(parsed_args, None)
    assert not yes_no.called
    assert not state_file.exists()
