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
import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from awscli.customizations.agenttoolkit import state
from awscli.customizations.agenttoolkit.agents import (
    AgentConfig,
    collapse_home,
)
from awscli.customizations.agenttoolkit.configure import (
    AUTO_UPDATE_KEEP_PROMPT,
    AUTO_UPDATE_PROMPT,
    PROJECT_SCOPE_PROMPT,
    ConfigureAgentToolkitCommand,
)
from awscli.customizations.agenttoolkit.hooks import (
    CODEX_TRUST_NOTE,
    KIRO_AGENT_NOTE,
    KIRO_NO_AGENT_NOTE,
    KIRO_VERSION_NOTE,
    format_kiro_agent_manual_entry,
    format_manual_entry,
    hook_command,
    hook_shell_command,
)
from awscli.customizations.agenttoolkit.utils import AgentToolkitServiceError
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from tests.unit.customizations.agenttoolkit.utils import (
    home_relative,
    make_config,
    make_session,
    make_skill,
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


def _parsed_args(yes=False, no_auto_update=False, project=False, **kwargs):
    # ``global`` is a keyword, so it is passed as ``**{'global': True}``.
    return SimpleNamespace(
        yes=yes,
        no_auto_update=no_auto_update,
        project=project,
        **{'global': kwargs.pop('global', False)},
        **kwargs,
    )


def _run(
    agent_configs,
    yes_no_return=True,
    client=None,
    yes=False,
    prompts=None,
    no_auto_update=False,
    **scope_args,
):
    stream = StringIO()
    session = make_session()
    if client is None:
        client = _make_client()
    cmd = ConfigureAgentToolkitCommand(
        session, stream=stream, agent_configs=agent_configs, client=client
    )
    parsed_args = _parsed_args(
        yes=yes, no_auto_update=no_auto_update, **scope_args
    )
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
            skills_paths=[
                home_relative(tmp_path, tmp_path / 'nonexistent', 'skills')
            ],
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
            skills_paths=[
                home_relative(tmp_path, tmp_path / 'nope', 'skills')
            ],
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
            skills_paths=[home_relative(tmp_path, universal_dir)],
            mcp_config_path='mcp.json',
        ),
        AgentConfig(
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(tmp_path / '.agents'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.agents', 'skills')
            ],
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
            skills_paths=[home_relative(tmp_path, universal_dir)],
            mcp_config_path='mcp.json',
        ),
        AgentConfig(
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(tmp_path / '.agents'),
            skills_paths=[
                home_relative(tmp_path, tmp_path / '.agents', 'skills')
            ],
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
        parsed_args = _parsed_args(yes=True, no_auto_update=False)
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
    return [
        p
        for p in prompts
        if p in (AUTO_UPDATE_PROMPT, AUTO_UPDATE_KEEP_PROMPT)
    ]


def _write_state(state_file, data):
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps(data))


def _make_agent_with_skill(tmp_path):
    configs = _make_agent_configs(tmp_path, count=1)
    make_skill(tmp_path, '.agent-0', 'aws-serverless')
    return configs


def test_auto_update_prompt_mentions_core_skills():
    assert (
        'new core AWS skills are added wherever AWS skills are already '
        'installed'
    ) in AUTO_UPDATE_PROMPT


def test_auto_update_enabled_on_yes(tmp_path, state_file):
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes_no_return=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_PROMPT]
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True
    }
    assert 'Automatic skill updates enabled.' in stream.getvalue()


def test_auto_update_declined_writes_nothing(tmp_path, state_file):
    configs = _make_agent_with_skill(tmp_path)
    _, stream = _run(configs, yes_no_return=False)
    assert not state_file.exists()
    assert 'Automatic skill updates' not in stream.getvalue()


def test_auto_update_enabled_without_prompt_on_yes_flag(tmp_path, state_file):
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _run(configs, yes=True, prompts=prompts)
    assert prompts == []
    assert state.is_auto_update_enabled()


def test_auto_update_asks_to_keep_when_enabled(tmp_path, state_file):
    _write_state(
        state_file, {'agent_toolkit_auto_update': True, 'hint_dismissed': True}
    )
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes_no_return=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_KEEP_PROMPT]
    assert 'Automatic skill updates' not in stream.getvalue()
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True,
        'hint_dismissed': True,
    }


def test_auto_update_kept_does_not_rewrite_state(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_with_skill(tmp_path)
    with patch(
        'awscli.customizations.agenttoolkit.configure.set_auto_update'
    ) as set_auto_update:
        _run(configs, yes_no_return=True)
    assert not set_auto_update.called


def test_auto_update_turned_off_on_no_when_enabled(tmp_path, state_file):
    _write_state(
        state_file, {'agent_toolkit_auto_update': True, 'hint_dismissed': True}
    )
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes_no_return=False, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_KEEP_PROMPT]
    assert 'Automatic skill updates turned off.' in stream.getvalue()
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': False,
        'hint_dismissed': True,
    }


def test_auto_update_yes_flag_keeps_it_enabled(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes=True, prompts=prompts)
    assert prompts == []
    assert state.is_auto_update_enabled()
    assert 'turned off' not in stream.getvalue()


def test_no_auto_update_flag_with_yes_leaves_it_off(tmp_path, state_file):
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes=True, no_auto_update=True, prompts=prompts)
    assert prompts == []
    assert not state_file.exists()
    assert not state.is_auto_update_enabled()
    assert 'Automatic skill updates' not in stream.getvalue()


def test_no_auto_update_flag_with_yes_turns_it_off(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _, stream = _run(configs, yes=True, no_auto_update=True, prompts=prompts)
    assert prompts == []
    assert not state.is_auto_update_enabled()
    assert 'Automatic skill updates turned off.' in stream.getvalue()


def test_no_auto_update_flag_skips_prompt_interactively(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _run(configs, yes_no_return=True, no_auto_update=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == []
    assert not state.is_auto_update_enabled()


def test_auto_update_prompted_again_when_previously_declined(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': False})
    configs = _make_agent_with_skill(tmp_path)
    prompts = []
    _run(configs, yes_no_return=True, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_PROMPT]
    assert state.is_auto_update_enabled()


def test_auto_update_preserves_other_state_keys(tmp_path, state_file):
    state_file.parent.mkdir(parents=True)
    state_file.write_text(json.dumps({'hint_dismissed': True}))
    configs = _make_agent_with_skill(tmp_path)
    _run(configs, yes_no_return=True)
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True,
        'hint_dismissed': True,
    }


def test_auto_update_corrupt_state_file_is_replaced(tmp_path, state_file):
    state_file.parent.mkdir(parents=True)
    state_file.write_text('{ not valid json')
    configs = _make_agent_with_skill(tmp_path)
    rc, stream = _run(configs, yes_no_return=True)
    assert rc == 0
    assert json.loads(state_file.read_text()) == {
        'agent_toolkit_auto_update': True
    }
    assert 'Automatic skill updates enabled.' in stream.getvalue()


def test_auto_update_write_failure_is_reported(tmp_path, state_file):
    configs = _make_agent_with_skill(tmp_path)
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
    configs = _make_agent_with_skill(tmp_path)
    stream = StringIO()
    cmd = ConfigureAgentToolkitCommand(
        make_session(),
        stream=stream,
        agent_configs=configs,
        client=MagicMock(),
    )
    parsed_args = _parsed_args(yes=False, no_auto_update=False)
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


def test_auto_update_not_prompted_when_skills_declined(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    prompts = []
    _run(configs, yes_no_return=False, client=client, prompts=prompts)
    assert _auto_update_prompts(prompts) == []
    assert not state_file.exists()


def test_auto_update_not_enabled_when_all_installs_fail(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    client = _make_client(skills=[{'name': 'aws-bad'}])
    prompts = []
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        side_effect=AgentToolkitServiceError('download failed'),
    ):
        _run(configs, yes=True, client=client, prompts=prompts)
    assert prompts == []
    assert not state_file.exists()


def test_auto_update_prompted_after_skills_installed(tmp_path, state_file):
    configs = _make_agent_configs(tmp_path, count=1)
    zip_bytes, checksum = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    prompts = []
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        return_value=(zip_bytes, checksum, 'v1'),
    ):
        _run(configs, yes_no_return=True, client=client, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_PROMPT]
    assert state.is_auto_update_enabled()


def test_auto_update_keep_prompt_shown_without_installed_skills(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_configs(tmp_path, count=1)
    prompts = []
    _run(configs, yes_no_return=False, prompts=prompts)
    assert _auto_update_prompts(prompts) == [AUTO_UPDATE_KEEP_PROMPT]
    assert not state.is_auto_update_enabled()


def test_no_auto_update_flag_applied_before_skill_fetch_fails(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _make_agent_with_skill(tmp_path)
    client = _make_client()
    client.get_paginator.return_value.paginate.side_effect = RuntimeError(
        'network down'
    )
    with pytest.raises(RuntimeError):
        _run(configs, yes=True, no_auto_update=True, client=client)
    assert not state.is_auto_update_enabled()


def _hook_agent_configs(tmp_path, agent_ids, detected=True):
    configs = []
    for agent_id in agent_ids:
        agent_dir = tmp_path / f'.{agent_id}'
        if detected:
            # An installed skill, so the wizard offers automatic updates.
            make_skill(tmp_path, f'.{agent_id}', 'aws-serverless')
        configs.append(
            make_config(
                tmp_path,
                id=agent_id,
                display_name=agent_id.title(),
                detection_path=str(agent_dir),
            )
        )
    return configs


def _hook_file(tmp_path, agent_id):
    return (
        tmp_path
        / f'.{agent_id}'
        / {
            'claude-code': 'settings.json',
            'codex': 'hooks.json',
            'cursor': 'hooks.json',
        }.get(agent_id, os.path.join('hooks', 'aws-agent-toolkit.json'))
    )


def _collapse(path):
    return collapse_home(str(path))


def _run_selecting(configs, selected_ids, yes_no_return=True):
    stream = StringIO()
    cmd = ConfigureAgentToolkitCommand(
        make_session(),
        stream=stream,
        agent_configs=configs,
        client=_make_client(),
    )
    parsed_args = _parsed_args(yes=False, no_auto_update=False)
    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
            side_effect=lambda msg, items, **kw: [
                a for a in items if a.config.id in selected_ids
            ],
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice',
            return_value=yes_no_return,
        ),
    ):
        cmd._run_main(parsed_args, None)
    return stream.getvalue()


def test_auto_update_installs_hooks_for_selected_agents(tmp_path):
    configs = _hook_agent_configs(
        tmp_path, ['claude-code', 'codex', 'kiro', 'cline']
    )
    _, stream = _run(configs, yes_no_return=True)
    output = stream.getvalue()
    for agent_id in ('claude-code', 'codex', 'kiro'):
        path = _hook_file(tmp_path, agent_id)
        assert hook_command(agent_id) in path.read_text()
        assert (
            f'  ✓ {agent_id.title()} — {_collapse(path)}: hook installed\n'
        ) in output
    assert '  ✗ Cline (automatic updates not supported yet)\n' in output
    assert f'    {CODEX_TRUST_NOTE}\n' in output
    assert f'    {KIRO_VERSION_NOTE}\n' in output
    assert os.listdir(tmp_path / '.cline') == ['skills']


def test_auto_update_kept_reports_already_installed(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    _run(configs, yes_no_return=True)
    path = _hook_file(tmp_path, 'claude-code')
    before = path.read_bytes()
    _, stream = _run(configs, yes_no_return=True)
    assert path.read_bytes() == before
    assert f'{_collapse(path)}: already installed\n' in stream.getvalue()


def _change_claude_hook(path):
    data = json.loads(path.read_text())
    data['hooks']['SessionStart'][0]['matcher'] = '*'
    path.write_text(json.dumps(data, indent=2) + '\n')
    return path.read_bytes()


def test_auto_update_keeps_our_hook_changed_by_customer(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    _run(configs, yes_no_return=True)
    path = _hook_file(tmp_path, 'claude-code')
    before = _change_claude_hook(path)
    _, stream = _run(configs, yes_no_return=True)
    assert path.read_bytes() == before
    assert f'{_collapse(path)}: already installed\n' in stream.getvalue()


def test_auto_update_off_removes_our_hook_changed_by_customer(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    _run(configs, yes_no_return=True)
    path = _hook_file(tmp_path, 'claude-code')
    _change_claude_hook(path)
    _, stream = _run(configs, yes_no_return=False)
    assert json.loads(path.read_text()) == {}
    assert (
        f'  ✓ Claude-Code — {_collapse(path)}: hook removed\n'
    ) in stream.getvalue()


def test_auto_update_yes_flag_installs_hooks(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['cursor'])
    _run(configs, yes=True)
    assert hook_command('cursor') in _hook_file(tmp_path, 'cursor').read_text()


def test_auto_update_installs_only_for_selected_agents(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['claude-code', 'cursor'])
    _run_selecting(configs, {'cursor'})
    assert _hook_file(tmp_path, 'cursor').exists()
    assert not _hook_file(tmp_path, 'claude-code').exists()


def test_auto_update_unreadable_file_prints_manual_entry(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    path = _hook_file(tmp_path, 'claude-code')
    path.write_text('{\n  // my settings\n}\n')
    _, stream = _run(configs, yes_no_return=True)
    output = stream.getvalue()
    assert path.read_text() == '{\n  // my settings\n}\n'
    assert f'  ✗ Claude-Code — {_collapse(path)}: could not' in (output)
    assert format_manual_entry('claude-code', _collapse(path)) in output


def test_auto_update_hook_error_is_reported(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['claude-code', 'codex'])
    with patch(
        'awscli.customizations.agenttoolkit.hooks.write_file_atomic',
        side_effect=[OSError('disk full'), None],
    ):
        rc, stream = _run(configs, yes_no_return=True)
    assert rc == 0
    path = _hook_file(tmp_path, 'claude-code')
    assert (
        f'  ✗ Claude-Code — {_collapse(path)}: could not install '
        'the hook (disk full)\n'
    ) in stream.getvalue()
    assert 'Codex —' in stream.getvalue()


def test_auto_update_off_removes_hooks_only_from_selected_agents(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['claude-code', 'kiro', 'cline'])
    _run(configs, yes_no_return=True)
    settings = _hook_file(tmp_path, 'claude-code')
    kiro_hook = _hook_file(tmp_path, 'kiro')
    kiro_before = kiro_hook.read_bytes()

    output = _run_selecting(
        configs, {'claude-code', 'cline'}, yes_no_return=False
    )

    assert not state.is_auto_update_enabled()
    assert json.loads(settings.read_text()) == {}
    assert kiro_hook.read_bytes() == kiro_before
    assert (
        f'  ✓ Claude-Code — {_collapse(settings)}: hook removed\n'
    ) in output
    after = output.split('Automatic skill updates turned off.')[1]
    assert 'Kiro —' not in after
    assert 'Cline' not in after


def test_auto_update_declined_prints_nothing_without_hooks(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    settings = _hook_file(tmp_path, 'claude-code')
    settings.write_text('{\n  // comments\n}\n')
    _, stream = _run(configs, yes_no_return=False)
    assert 'hook' not in stream.getvalue()
    assert settings.read_text() == '{\n  // comments\n}\n'


def test_auto_update_state_error_changes_no_hooks(tmp_path, state_file):
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    with patch(
        'awscli.customizations.agenttoolkit.configure.set_auto_update',
        side_effect=state.StateFileError('/x/state.json: disk full'),
    ):
        _, stream = _run(configs, yes_no_return=True)
    assert not _hook_file(tmp_path, 'claude-code').exists()
    assert 'hook' not in stream.getvalue()


def test_auto_update_state_error_keeps_hooks_when_disabling(
    tmp_path, state_file
):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    _run(configs, yes_no_return=True)
    with patch(
        'awscli.customizations.agenttoolkit.configure.set_auto_update',
        side_effect=state.StateFileError('/x/state.json: disk full'),
    ):
        _run(configs, yes_no_return=False)
    assert hook_command('claude-code') in (
        _hook_file(tmp_path, 'claude-code').read_text()
    )


def _kiro_default_agent(tmp_path, content=None):
    settings = tmp_path / '.kiro' / 'settings' / 'cli.json'
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({'chat.defaultAgent': 'my-agent'}))
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    path.parent.mkdir()
    if content is None:
        content = json.dumps({'name': 'my-agent'}, indent=2) + '\n'
    path.write_text(content)
    return path


def test_auto_update_adds_hook_to_kiro_default_agent(tmp_path):
    configs = _hook_agent_configs(tmp_path, ['kiro'])
    agent_file = _kiro_default_agent(tmp_path)
    _, stream = _run(configs, yes_no_return=True)
    output = stream.getvalue()
    assert json.loads(agent_file.read_text())['hooks'] == {
        'agentSpawn': [
            {'command': hook_shell_command('kiro'), 'timeout_ms': 60000}
        ]
    }
    assert (
        f'  ✓ Kiro — {_collapse(_hook_file(tmp_path, "kiro"))}: '
        'hook installed\n'
        f'    {KIRO_VERSION_NOTE}\n'
        f'  ✓ Kiro — {_collapse(agent_file)}: hook installed\n'
        f'    {KIRO_AGENT_NOTE}\n'
    ) in output


def test_auto_update_kiro_without_default_agent_prints_manual_entry(
    tmp_path,
):
    configs = _hook_agent_configs(tmp_path, ['kiro'])
    _, stream = _run(configs, yes_no_return=True)
    output = stream.getvalue()
    assert f'  ✗ Kiro — {KIRO_NO_AGENT_NOTE}\n' in output
    assert (
        format_kiro_agent_manual_entry(
            _collapse(tmp_path / '.kiro' / 'agents' / '<agent>.json')
        )
        in output
    )
    assert not (tmp_path / '.kiro' / 'agents').exists()


def test_auto_update_kiro_agent_with_comments_prints_manual_entry(
    tmp_path,
):
    configs = _hook_agent_configs(tmp_path, ['kiro'])
    content = '{\n  // mine\n  "name": "my-agent"\n}\n'
    agent_file = _kiro_default_agent(tmp_path, content)
    _, stream = _run(configs, yes_no_return=True)
    output = stream.getvalue()
    assert agent_file.read_text() == content
    assert f'  ✗ Kiro — {_collapse(agent_file)}: could not' in output
    assert format_kiro_agent_manual_entry(_collapse(agent_file)) in output


def test_auto_update_off_removes_hook_from_kiro_agents(tmp_path, state_file):
    _write_state(state_file, {'agent_toolkit_auto_update': True})
    configs = _hook_agent_configs(tmp_path, ['kiro'])
    agent_file = _kiro_default_agent(tmp_path)
    before = agent_file.read_text()
    _run(configs, yes_no_return=True)
    _, stream = _run(configs, yes_no_return=False)
    assert agent_file.read_text() == before
    assert f'  ✓ Kiro — {_collapse(agent_file)}: hook removed\n' in (
        stream.getvalue()
    )


@pytest.mark.parametrize('yes', [True, False])
def test_no_auto_update_flag_removes_hooks(tmp_path, state_file, yes):
    configs = _hook_agent_configs(tmp_path, ['claude-code', 'kiro'])
    agent_file = _kiro_default_agent(tmp_path)
    settings = _hook_file(tmp_path, 'claude-code')
    settings.write_text(json.dumps({'theme': 'dark'}))
    _run(configs, yes=True)
    assert hook_command('claude-code') in settings.read_text()
    assert hook_command('kiro') in agent_file.read_text()

    prompts = []
    _, stream = _run(
        configs,
        yes=yes,
        yes_no_return=True,
        no_auto_update=True,
        prompts=prompts,
    )
    output = stream.getvalue()
    assert _auto_update_prompts(prompts) == []
    assert not state.is_auto_update_enabled()
    assert json.loads(settings.read_text()) == {'theme': 'dark'}
    assert json.loads(agent_file.read_text()) == {'name': 'my-agent'}
    assert not _hook_file(tmp_path, 'kiro').exists()
    assert f'  ✓ Claude-Code — {_collapse(settings)}: hook removed\n' in output
    assert f'  ✓ Kiro — {_collapse(agent_file)}: hook removed\n' in output
    assert 'hook installed' not in output


def test_no_auto_update_flag_without_hooks_prints_nothing(
    tmp_path, state_file
):
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    _, stream = _run(configs, yes=True, no_auto_update=True)
    assert 'hook' not in stream.getvalue()
    assert not _hook_file(tmp_path, 'claude-code').exists()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A project directory, below the home directory, that is the current
    directory."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.chdir(repo)
    return repo


def _project_configs(tmp_path, **overrides):
    configs = _make_agent_configs(tmp_path, count=1)
    configs[0].project_mcp_config_path = overrides.pop(
        'project_mcp_config_path', '.agent-0-mcp.json'
    )
    return configs


def _run_answering(configs, answer, client=None, **scope_args):
    """Run the wizard, answering the project prompt with ``answer`` and
    every other prompt with yes."""
    stream = StringIO()
    cmd = ConfigureAgentToolkitCommand(
        make_session(),
        stream=stream,
        agent_configs=configs,
        client=client or _make_client(),
    )
    prompts = []

    def yes_no(prompt, default=None):
        prompts.append(prompt)
        if prompt.startswith(PROJECT_SCOPE_PROMPT.split('{}')[0]):
            assert default is False
            return answer
        return True

    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
            side_effect=lambda msg, items, **kw: items,
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice',
            side_effect=yes_no,
        ),
    ):
        cmd._run_main(_parsed_args(**scope_args), None)
    return stream.getvalue(), prompts


def _install_one_skill(configs, **kwargs):
    zip_bytes, checksum = make_skill_zip()
    client = _make_client(skills=[{'name': 'aws-serverless'}])
    with patch(
        'awscli.customizations.agenttoolkit.configure.get_skill_download',
        return_value=(zip_bytes, checksum, 'v1'),
    ):
        return _run_answering(configs, client=client, **kwargs)


def test_project_installs_skills_into_current_directory(tmp_path, repo):
    configs = _project_configs(tmp_path)
    output, _ = _install_one_skill(configs, answer=True, project=True)
    project_skill = repo / '.agent-0' / 'skills' / 'aws-serverless'
    assert (project_skill / 'SKILL.md').exists()
    assert not (tmp_path / '.agent-0' / 'skills' / 'aws-serverless').exists()
    assert f'Setting up the agent toolkit for {_collapse(repo)}.' in output
    assert '--project' in output


def test_project_configures_project_mcp_config(tmp_path, repo):
    configs = _project_configs(tmp_path)
    output, _ = _run_answering(configs, answer=True, project=True)
    data = json.loads((repo / '.agent-0-mcp.json').read_text())
    assert data['mcpServers']['aws-mcp']['command'] == 'uvx'
    assert not (tmp_path / '.agent-0' / 'mcp.json').exists()
    assert f'{_collapse(repo / ".agent-0-mcp.json")}: updated' in output


def test_project_skips_mcp_without_project_config(tmp_path, repo):
    configs = _project_configs(tmp_path, project_mcp_config_path=None)
    output, _ = _run_answering(configs, answer=True, project=True)
    assert (
        'MCP setup not available in the current directory for the '
        'following agents.\n'
        "  ✗ Agent 0 (no project-level MCP config; run 'aws configure "
        "agent-toolkit --global' to configure it globally)\n"
    ) in output
    assert 'manual setup instructions' not in output
    assert not (tmp_path / '.agent-0' / 'mcp.json').exists()


def test_project_does_not_run_global_mcp_shell_command(tmp_path, repo):
    configs = _project_configs(tmp_path, project_mcp_config_path=None)
    configs[0].mcp_shell_command = ['true']
    with patch('subprocess.run') as run:
        output, _ = _run_answering(configs, answer=True, project=True)
    run.assert_not_called()
    assert 'no project-level MCP config' in output


def test_project_installs_hooks_only_globally(tmp_path, repo):
    configs = _hook_agent_configs(tmp_path, ['claude-code'])
    configs[0].project_mcp_config_path = '.mcp.json'
    make_skill(repo, '.claude-code', 'aws-serverless')
    output, _ = _run_answering(configs, answer=True, project=True)
    hook_path = _hook_file(tmp_path, 'claude-code')
    assert hook_command('claude-code') in hook_path.read_text()
    assert f'{_collapse(hook_path)}: hook installed' in output
    # Only skills and MCP config are written to the project.
    assert sorted(os.listdir(repo)) == ['.claude-code', '.mcp.json']
    assert os.listdir(repo / '.claude-code') == ['skills']


def test_project_and_global_are_mutually_exclusive(tmp_path, repo):
    configs = _project_configs(tmp_path)
    with pytest.raises(ParamValidationError, match='--project together'):
        _run_answering(configs, answer=True, project=True, **{'global': True})


def test_project_fails_without_current_directory(tmp_path, repo):
    configs = _project_configs(tmp_path)
    with patch('os.getcwd', side_effect=FileNotFoundError('gone')):
        with pytest.raises(ParamValidationError, match='--project'):
            _run_answering(configs, answer=True, project=True)


@pytest.mark.parametrize('answer', [True, False])
def test_no_scope_flag_asks_for_scope(tmp_path, repo, answer):
    configs = _project_configs(tmp_path)
    output, prompts = _install_one_skill(configs, answer=answer)
    assert prompts[0] == PROJECT_SCOPE_PROMPT.format(_collapse(repo))
    project_skill = repo / '.agent-0' / 'skills' / 'aws-serverless'
    global_skill = tmp_path / '.agent-0' / 'skills' / 'aws-serverless'
    assert project_skill.exists() is answer
    assert global_skill.exists() is not answer


def test_global_flag_does_not_ask_for_scope(tmp_path, repo):
    configs = _project_configs(tmp_path)
    _, prompts = _install_one_skill(configs, answer=True, **{'global': True})
    assert PROJECT_SCOPE_PROMPT.format(_collapse(repo)) not in prompts
    assert (tmp_path / '.agent-0' / 'skills' / 'aws-serverless').exists()
    assert not (repo / '.agent-0').exists()


def test_yes_without_scope_flag_sets_up_globally(tmp_path, repo):
    configs = _project_configs(tmp_path)
    _, prompts = _install_one_skill(configs, answer=True, yes=True)
    assert prompts == []
    assert (tmp_path / '.agent-0' / 'skills' / 'aws-serverless').exists()
    assert not (repo / '.agent-0').exists()


def test_yes_with_project_sets_up_project(tmp_path, repo):
    configs = _project_configs(tmp_path)
    _, prompts = _install_one_skill(
        configs, answer=True, yes=True, project=True
    )
    assert prompts == []
    assert (repo / '.agent-0' / 'skills' / 'aws-serverless').exists()


def test_scope_not_asked_in_home_directory(tmp_path):
    # The current directory is the home directory, where project-level
    # skills are the global ones.
    configs = _project_configs(tmp_path)
    output, prompts = _install_one_skill(configs, answer=True)
    assert not any('current directory' in p for p in prompts)
    assert 'Setting up the agent toolkit for' not in output
    assert (tmp_path / '.agent-0' / 'mcp.json').exists()


def test_project_in_home_directory_is_global(tmp_path):
    configs = _project_configs(tmp_path)
    output, _ = _install_one_skill(configs, answer=True, project=True)
    assert 'Setting up the agent toolkit for' not in output
    assert (tmp_path / '.agent-0' / 'mcp.json').exists()
    assert not (tmp_path / '.agent-0-mcp.json').exists()


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='The current directory cannot be deleted on Windows.',
)
def test_no_scope_flag_without_current_directory_sets_up_globally(
    tmp_path, repo
):
    configs = _project_configs(tmp_path)
    with patch('os.getcwd', side_effect=FileNotFoundError('gone')):
        output, prompts = _install_one_skill(configs, answer=True)
    assert not any('current directory' in p for p in prompts)
    assert (tmp_path / '.agent-0' / 'skills' / 'aws-serverless').exists()
    assert not (repo / '.agent-0').exists()


def test_project_asks_same_auto_update_prompt(tmp_path, repo):
    configs = _project_configs(tmp_path)
    _, prompts = _install_one_skill(configs, answer=True, project=True)
    assert AUTO_UPDATE_PROMPT in prompts


def test_project_not_found_agent_shows_no_global_path(tmp_path, repo):
    configs = _project_configs(tmp_path)
    configs.append(
        make_config(
            tmp_path,
            id='missing',
            display_name='Missing Agent',
            detection_path=str(tmp_path / '.missing'),
        )
    )
    output, _ = _run_answering(configs, answer=True, project=True)
    assert '  ✗ Missing Agent (not found)\n' in output
    assert f'  ✓ Agent 0 — {_collapse(repo / ".agent-0" / "skills")}' in output


def test_project_reports_agent_without_mcp_support(tmp_path, repo):
    configs = _project_configs(tmp_path, project_mcp_config_path=None)
    configs[0].mcp_config_path = None
    output, _ = _run_answering(configs, answer=True, project=True)
    assert '  ✗ Agent 0 (MCP not supported)\n' in output


def test_global_skipped_mcp_message_unchanged(tmp_path, repo):
    configs = _project_configs(tmp_path)
    configs[0].mcp_config_path = None
    output, _ = _run_answering(configs, answer=True, **{'global': True})
    assert 'for manual setup instructions.\n' in output
    assert '  ✗ Agent 0 (no automated setup)\n' in output
