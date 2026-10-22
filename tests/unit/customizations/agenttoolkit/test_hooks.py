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

import pytest

from awscli.customizations.agenttoolkit import hooks
from awscli.customizations.agenttoolkit.hooks import (
    format_hook_message,
    format_hook_output,
    hook_config_path,
    is_hook_supported,
)
from tests.unit.customizations.agenttoolkit.utils import make_config

_ENV_VARS = ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'GEMINI_CLI_HOME')

_HOOK_FILES = {
    'claude-code': 'settings.json',
    'gemini-cli': 'settings.json',
    'codex': 'hooks.json',
    'cursor': 'hooks.json',
    'kiro': os.path.join('hooks', 'aws-agent-toolkit.json'),
}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _agent(tmp_path, agent_id, create=True, **overrides):
    agent_dir = tmp_path / f'.{agent_id}'
    if create:
        agent_dir.mkdir(exist_ok=True)
    config = make_config(
        tmp_path,
        id=agent_id,
        display_name=agent_id,
        detection_path=str(agent_dir),
        **overrides,
    )
    return config.detect() if create else config


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES))
def test_hook_config_path_for_detected_agent(tmp_path, agent_id):
    agent = _agent(tmp_path, agent_id)
    assert hook_config_path(agent.config, agent.base_dir) == str(
        tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    )
    assert hook_config_path(agent.config) == str(
        tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    )


def test_claude_code_honours_config_dir(tmp_path, monkeypatch):
    override = tmp_path / 'claude-config'
    override.mkdir()
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(override))
    config = _agent(
        tmp_path,
        'claude-code',
        create=False,
        detection_path_env_override='CLAUDE_CONFIG_DIR',
    )
    assert hook_config_path(config) == str(override / 'settings.json')


def test_codex_honours_codex_home(tmp_path, monkeypatch):
    override = tmp_path / 'codex-home'
    override.mkdir()
    monkeypatch.setenv('CODEX_HOME', str(override))
    config = _agent(
        tmp_path,
        'codex',
        create=False,
        detection_path_env_override='CODEX_HOME',
    )
    assert hook_config_path(config) == str(override / 'hooks.json')


def _gemini_with_home(tmp_path, monkeypatch, create=True):
    home = tmp_path / 'gemini-home'
    if create:
        (home / '.gemini').mkdir(parents=True)
    monkeypatch.setenv('GEMINI_CLI_HOME', str(home))
    config = make_config(
        tmp_path,
        id='gemini-cli',
        display_name='Gemini CLI',
        detection_path='~/.gemini/',
        home_env_override='GEMINI_CLI_HOME',
    )
    return home, config


def test_gemini_honours_gemini_cli_home(tmp_path, monkeypatch):
    home, config = _gemini_with_home(tmp_path, monkeypatch)
    agent = config.detect()
    assert hook_config_path(agent.config, agent.base_dir) == str(
        home / '.gemini' / 'settings.json'
    )


def test_gemini_cli_home_path_for_undetected_agent(tmp_path, monkeypatch):
    home, config = _gemini_with_home(tmp_path, monkeypatch, create=False)
    assert config.detect() is None
    assert hook_config_path(config) == str(home / '.gemini' / 'settings.json')


def test_hook_config_path_for_undetected_agent(tmp_path):
    config = _agent(tmp_path, 'codex', create=False)
    assert hook_config_path(config) == str(tmp_path / '.codex' / 'hooks.json')


def test_unsupported_agent(tmp_path):
    agent = _agent(tmp_path, 'cline')
    assert not is_hook_supported('cline')
    assert hook_config_path(agent.config) is None


def test_hook_message():
    assert format_hook_message([], [], [], [], []) == ''
    assert format_hook_message([], [], ['aws-s3'], [], []) == ''
    assert format_hook_message(
        ['aws-cdk', 'aws-s3'], [], ['aws-iam'], [], []
    ) == ('AWS agent skills updated: aws-cdk, aws-s3. Skipped aws-iam.')
    assert format_hook_message(['aws-cdk'], [], [], ['aws-s3'], []) == (
        'AWS agent skills updated: aws-cdk. Could not update aws-s3; run '
        '"aws agent-toolkit update-skill --all" for details.'
    )
    assert format_hook_message([], ['aws-iam'], [], [], []) == (
        'New AWS core skills installed: aws-iam.'
    )
    assert format_hook_message(['aws-s3'], ['aws-iam'], [], [], []) == (
        'AWS agent skills updated: aws-s3. New AWS core skills installed: '
        'aws-iam.'
    )


def test_hook_message_failed_installs_point_at_add_skill():
    assert format_hook_message([], [], [], [], ['aws-iam']) == (
        'Could not install aws-iam; run "aws agent-toolkit add-skill '
        '--skill-name aws-iam" for details.'
    )
    assert format_hook_message([], [], [], [], ['aws-cdk', 'aws-iam']) == (
        'Could not install aws-cdk, aws-iam; run "aws agent-toolkit '
        'add-skill --skill-name <name>" for details.'
    )


def test_hook_output_formats():
    msg = 'AWS agent skills updated: aws-s3.'
    assert format_hook_output('claude-code', msg, True) == (
        json.dumps(
            {
                'hookSpecificOutput': {
                    'hookEventName': 'SessionStart',
                    'additionalContext': msg,
                    'reloadSkills': True,
                },
                'systemMessage': msg,
            },
            separators=(',', ':'),
        )
        + '\n'
    )
    assert json.loads(format_hook_output('claude-code', msg)) == {
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': msg,
        },
        'systemMessage': msg,
    }
    assert json.loads(format_hook_output('gemini-cli', msg, True)) == {
        'systemMessage': msg,
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': f'{msg} Run /skills reload to use them.',
        },
    }
    assert json.loads(format_hook_output('gemini-cli', msg)) == {
        'systemMessage': msg,
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': msg,
        },
    }
    assert format_hook_output('cursor', msg, True) == (
        '{"additional_context":"AWS agent skills updated: aws-s3."}\n'
    )
    assert format_hook_output('codex', msg, True) == f'{msg}\n'
    assert format_hook_output('kiro', msg, True) == f'{msg}\n'
    for agent_id in hooks.HOOK_AGENT_IDS:
        assert format_hook_output(agent_id, '', True) == ''
