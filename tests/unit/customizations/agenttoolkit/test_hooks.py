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

from awscli.customizations.agenttoolkit import hooks
from awscli.customizations.agenttoolkit.hooks import (
    HookAction,
    format_hook_message,
    format_hook_output,
    format_kiro_agent_manual_entry,
    format_manual_entry,
    hook_command,
    hook_config_path,
    hook_shell_command,
    install_hook,
    install_kiro_agent_hook,
    kiro_default_agent_path,
    remove_hook,
    remove_kiro_agent_hooks,
)
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    requires_symlinks,
)

_ENV_VARS = ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'GEMINI_CLI_HOME')

_HOOK_FILES = {
    'claude-code': 'settings.json',
    'gemini-cli': 'settings.json',
    'codex': 'hooks.json',
    'cursor': 'hooks.json',
}

_GROUP_EVENTS = {
    'claude-code': 'SessionStart',
    'gemini-cli': 'SessionStart',
    'codex': 'SessionStart',
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


def _expected_entry(agent_id):
    command = hook_shell_command(agent_id)
    if agent_id == 'claude-code':
        return {
            'hooks': {
                'SessionStart': [
                    {
                        'matcher': 'startup',
                        'hooks': [
                            {
                                'type': 'command',
                                'command': command,
                                'timeout': 60,
                            }
                        ],
                    }
                ]
            }
        }
    if agent_id == 'gemini-cli':
        return {
            'hooks': {
                'SessionStart': [
                    {
                        'matcher': '*',
                        'hooks': [
                            {
                                'name': 'aws-agent-toolkit',
                                'type': 'command',
                                'command': command,
                                'timeout': 60000,
                            }
                        ],
                    }
                ]
            }
        }
    if agent_id == 'codex':
        return {
            'hooks': {
                'SessionStart': [
                    {
                        'matcher': 'startup',
                        'hooks': [
                            {
                                'type': 'command',
                                'command': command,
                                'timeout': 60,
                            }
                        ],
                    }
                ]
            }
        }
    return {
        'version': 1,
        'hooks': {'sessionStart': [{'command': command, 'timeout': 60}]},
    }


def _our_group(agent_id):
    return _expected_entry(agent_id)['hooks'][_GROUP_EVENTS[agent_id]][0]


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES))
def test_install_creates_exact_entry(tmp_path, agent_id):
    agent = _agent(tmp_path, agent_id)
    action, path = install_hook(agent)
    expected_path = tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    assert (action, path) == (HookAction.INSTALLED, str(expected_path))
    text = expected_path.read_text()
    assert json.loads(text) == _expected_entry(agent_id)
    # New files use two spaces, LF and a trailing newline.
    assert text == json.dumps(_expected_entry(agent_id), indent=2) + '\n'
    if os.name != 'nt':
        assert expected_path.stat().st_mode & 0o777 == 0o600


def test_cursor_new_file_puts_version_first(tmp_path):
    agent = _agent(tmp_path, 'cursor')
    install_hook(agent)
    text = (tmp_path / '.cursor' / 'hooks.json').read_text()
    assert list(json.loads(text)) == ['version', 'hooks']


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES) + ['kiro'])
def test_install_twice_is_already_installed(tmp_path, agent_id):
    agent = _agent(tmp_path, agent_id)
    install_hook(agent)
    path = hook_config_path(agent.config, agent.base_dir)
    before = open(path, 'rb').read()
    mtime = os.stat(path).st_mtime_ns
    action, _ = install_hook(agent)
    assert action is HookAction.ALREADY_INSTALLED
    assert open(path, 'rb').read() == before
    assert os.stat(path).st_mtime_ns == mtime


def _existing_settings(agent_id, indent, newline):
    if agent_id == 'cursor':
        data = {
            'version': 1,
            'hooks': {
                'sessionStart': [{'command': 'echo mine'}],
                'stop': [{'command': 'echo stop'}],
            },
        }
    else:
        data = {
            'model': 'some-model',
            'permissions': {'allow': ['Bash(ls)']},
            'hooks': {
                'SessionStart': [
                    {
                        'matcher': 'startup',
                        'hooks': [{'type': 'command', 'command': 'echo hi'}],
                    }
                ],
                'Stop': [
                    {'hooks': [{'type': 'command', 'command': 'echo bye'}]}
                ],
            },
        }
    return (json.dumps(data, indent=indent) + '\n').replace('\n', newline)


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES))
@pytest.mark.parametrize(
    'indent,newline',
    [(2, '\n'), (4, '\n'), ('\t', '\n'), (2, '\r\n')],
    ids=['2-spaces', '4-spaces', 'tab', 'crlf'],
)
def test_install_then_remove_restores_file(
    tmp_path, agent_id, indent, newline
):
    agent = _agent(tmp_path, agent_id)
    path = tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    original = _existing_settings(agent_id, indent, newline).encode()
    path.write_bytes(original)

    assert install_hook(agent)[0] is HookAction.INSTALLED
    installed = path.read_bytes()
    text = installed.decode()
    expected_text = json.dumps(json.loads(text), indent=indent) + '\n'
    assert text == expected_text.replace('\n', newline)
    data = json.loads(text)
    if agent_id == 'cursor':
        assert data['hooks']['sessionStart'] == [
            {'command': 'echo mine'},
            _expected_entry('cursor')['hooks']['sessionStart'][0],
        ]
        assert data['hooks']['stop'] == [{'command': 'echo stop'}]
    else:
        assert data['model'] == 'some-model'
        assert data['hooks']['SessionStart'] == [
            {
                'matcher': 'startup',
                'hooks': [{'type': 'command', 'command': 'echo hi'}],
            },
            _our_group(agent_id),
        ]
        assert data['hooks']['Stop'] == [
            {'hooks': [{'type': 'command', 'command': 'echo bye'}]}
        ]

    assert install_hook(agent)[0] is HookAction.ALREADY_INSTALLED
    assert path.read_bytes() == installed
    assert remove_hook(agent)[0] is HookAction.REMOVED
    assert path.read_bytes() == original


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES))
def test_remove_drops_empty_containers(tmp_path, agent_id):
    agent = _agent(tmp_path, agent_id)
    path = tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    path.write_text('{\n  "theme": "dark"\n}\n')
    install_hook(agent)
    assert remove_hook(agent)[0] is HookAction.REMOVED
    expected = {'theme': 'dark'}
    if agent_id == 'cursor':
        # The version is kept since we can't tell whether we added it.
        expected['version'] = 1
    assert json.loads(path.read_text()) == expected


def test_install_into_empty_object_uses_default_style(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    path.write_text('{}')
    install_hook(agent)
    assert path.read_text() == (
        json.dumps(_expected_entry('claude-code'), indent=2)
    )
    remove_hook(agent)
    assert path.read_text() == '{}'


def test_install_into_empty_file(tmp_path):
    agent = _agent(tmp_path, 'codex')
    path = tmp_path / '.codex' / 'hooks.json'
    path.write_text('')
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text()) == _expected_entry('codex')


def test_install_preserves_one_line_file(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    path.write_text('{"model": "x"}\n')
    install_hook(agent)
    assert '\n' not in path.read_text()[:-1]
    remove_hook(agent)
    assert path.read_text() == '{"model": "x"}\n'


def test_install_keeps_unicode_escapes(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    original = '{\n  "name": "caf\\u00e9"\n}\n'
    path.write_text(original)
    install_hook(agent)
    assert '"caf\\u00e9"' in path.read_text()
    remove_hook(agent)
    assert path.read_text() == original


def test_install_keeps_raw_unicode(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    original = '{\n  "name": "café"\n}\n'
    path.write_text(original, encoding='utf-8')
    install_hook(agent)
    remove_hook(agent)
    assert path.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('agent_id', ['claude-code', 'gemini-cli', 'codex'])
def test_install_replaces_outdated_entry_in_place(tmp_path, agent_id):
    agent = _agent(tmp_path, agent_id)
    path = tmp_path / f'.{agent_id}' / _HOOK_FILES[agent_id]
    other = {'hooks': [{'type': 'command', 'command': 'echo other'}]}
    outdated = {
        'matcher': 'resume',
        'hooks': [
            {
                'type': 'command',
                'command': f'{hook_command(agent_id)} || true',
                'timeout': 10,
            }
        ],
    }
    path.write_text(
        json.dumps({'hooks': {'SessionStart': [outdated, other]}}, indent=2)
        + '\n'
    )
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        _our_group(agent_id),
        other,
    ]


def test_install_replaces_our_handler_in_shared_group(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    mine = {'type': 'command', 'command': 'echo mine'}
    old = {'type': 'command', 'command': hook_command('claude-code')}
    group = {'matcher': 'startup|resume', 'hooks': [mine, old]}
    path.write_text(json.dumps({'hooks': {'SessionStart': [group]}}))
    install_hook(agent)
    handler = _our_group('claude-code')['hooks'][0]
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        {'matcher': 'startup|resume', 'hooks': [mine, handler]}
    ]
    # Ours is in a shared group, so it is rewritten each time, but to the
    # same bytes.
    before = path.read_bytes()
    install_hook(agent)
    assert path.read_bytes() == before
    remove_hook(agent)
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        {'matcher': 'startup|resume', 'hooks': [mine]}
    ]


def test_install_collapses_duplicates(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    ours = _our_group('claude-code')
    mine = {'hooks': [{'type': 'command', 'command': 'echo mine'}]}
    path.write_text(
        json.dumps({'hooks': {'SessionStart': [ours, mine, ours]}}, indent=2)
    )
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        ours,
        mine,
    ]


def test_cursor_install_collapses_duplicates_and_adds_version(tmp_path):
    agent = _agent(tmp_path, 'cursor')
    path = tmp_path / '.cursor' / 'hooks.json'
    ours = _expected_entry('cursor')['hooks']['sessionStart'][0]
    mine = {'command': 'echo mine'}
    path.write_text(
        json.dumps({'hooks': {'sessionStart': [mine, ours, ours]}})
    )
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text()) == {
        'hooks': {'sessionStart': [mine, ours]},
        'version': 1,
    }


def test_cursor_keeps_existing_version(tmp_path):
    agent = _agent(tmp_path, 'cursor')
    path = tmp_path / '.cursor' / 'hooks.json'
    path.write_text(json.dumps({'version': 2}))
    install_hook(agent)
    assert json.loads(path.read_text())['version'] == 2


@pytest.mark.parametrize(
    'content',
    [
        '{\n  // comment\n  "a": 1\n}\n',
        '{ not json',
        '{\n  "a":1\n}\n',
        '{\n  "a": 1,\n    "b": 2\n}\n',
        '{\n  "a": 1\n}\n\n',
        '[]\n',
        '{\n  "hooks": []\n}\n',
        '{\n  "hooks": {\n    "SessionStart": {}\n  }\n}\n',
        '\ufeff{}',
    ],
    ids=[
        'comments',
        'invalid',
        'compact-separators',
        'mixed-indent',
        'extra-newline',
        'root-list',
        'hooks-list',
        'event-object',
        'bom',
    ],
)
def test_unreadable_file_is_left_untouched(tmp_path, content):
    agent = _agent(tmp_path, 'gemini-cli')
    path = tmp_path / '.gemini-cli' / 'settings.json'
    path.write_bytes(content.encode('utf-8'))
    assert install_hook(agent) == (HookAction.UNREADABLE, str(path))
    assert path.read_bytes() == content.encode('utf-8')
    # Nothing of ours is in there, so there is nothing to remove.
    assert remove_hook(agent)[0] is HookAction.NOT_INSTALLED
    assert path.read_bytes() == content.encode('utf-8')
    assert sorted(os.listdir(path.parent)) == ['settings.json']


def test_remove_reports_unreadable_file_with_our_hook(tmp_path):
    agent = _agent(tmp_path, 'gemini-cli')
    path = tmp_path / '.gemini-cli' / 'settings.json'
    content = (
        '{\n  // added by hand\n  "hooks": {"SessionStart": [{"hooks": '
        f'[{{"command": "{hook_command("gemini-cli")}"}}]}}]}}\n}}\n'
    )
    path.write_text(content)
    assert remove_hook(agent)[0] is HookAction.UNREADABLE
    assert path.read_text() == content


def test_install_preserves_permissions(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    path.write_text('{}\n')
    os.chmod(path, 0o640)
    mode = path.stat().st_mode
    install_hook(agent)
    assert path.stat().st_mode == mode
    remove_hook(agent)
    assert path.stat().st_mode == mode


@requires_symlinks
def test_install_writes_through_symlink(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    real = tmp_path / 'dotfiles' / 'settings.json'
    real.parent.mkdir()
    real.write_text('{}\n')
    link = tmp_path / '.claude-code' / 'settings.json'
    link.symlink_to(real)
    install_hook(agent)
    assert link.is_symlink()
    assert json.loads(real.read_text()) == _expected_entry('claude-code')


def test_other_users_hooks_untouched_on_remove(tmp_path):
    agent = _agent(tmp_path, 'codex')
    path = tmp_path / '.codex' / 'hooks.json'
    content = json.dumps(
        {
            'hooks': {
                'SessionStart': [
                    {
                        'hooks': [
                            {
                                'type': 'command',
                                'command': 'aws agent-toolkit update-skill',
                            }
                        ]
                    }
                ]
            }
        },
        indent=2,
    )
    path.write_text(content)
    assert remove_hook(agent)[0] is HookAction.NOT_INSTALLED
    assert path.read_text() == content


def test_remove_missing_file_is_not_installed(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    assert remove_hook(agent)[0] is HookAction.NOT_INSTALLED
    assert not (tmp_path / '.claude-code' / 'settings.json').exists()


def test_claude_code_honours_config_dir(tmp_path, monkeypatch):
    override = tmp_path / 'claude-config'
    override.mkdir()
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(override))
    agent = _agent(
        tmp_path,
        'claude-code',
        create=False,
        detection_path_env_override='CLAUDE_CONFIG_DIR',
    ).detect()
    action, path = install_hook(agent)
    assert (action, path) == (
        HookAction.INSTALLED,
        str(override / 'settings.json'),
    )


def test_codex_honours_codex_home(tmp_path, monkeypatch):
    override = tmp_path / 'codex-home'
    override.mkdir()
    monkeypatch.setenv('CODEX_HOME', str(override))
    agent = _agent(
        tmp_path,
        'codex',
        create=False,
        detection_path_env_override='CODEX_HOME',
    ).detect()
    assert install_hook(agent) == (
        HookAction.INSTALLED,
        str(override / 'hooks.json'),
    )


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
    expected = home / '.gemini' / 'settings.json'
    assert install_hook(agent) == (HookAction.INSTALLED, str(expected))
    assert json.loads(expected.read_text()) == _expected_entry('gemini-cli')
    assert remove_hook(agent) == (HookAction.REMOVED, str(expected))


def test_gemini_cli_home_path_for_undetected_agent(tmp_path, monkeypatch):
    home, config = _gemini_with_home(tmp_path, monkeypatch, create=False)
    assert config.detect() is None
    assert hook_config_path(config) == str(home / '.gemini' / 'settings.json')


def test_hook_config_path_for_undetected_agent(tmp_path):
    config = _agent(tmp_path, 'codex', create=False)
    assert hook_config_path(config) == str(tmp_path / '.codex' / 'hooks.json')


def test_kiro_owns_its_file(tmp_path):
    agent = _agent(tmp_path, 'kiro')
    path = tmp_path / '.kiro' / 'hooks' / 'aws-agent-toolkit.json'
    assert install_hook(agent) == (HookAction.INSTALLED, str(path))
    assert json.loads(path.read_text()) == {
        'version': 'v1',
        'hooks': [
            {
                'name': 'aws-agent-toolkit',
                'description': (
                    'Keeps AWS agent skills up to date '
                    '(managed by aws agent-toolkit)'
                ),
                'trigger': 'SessionStart',
                'action': {
                    'type': 'command',
                    'command': hook_shell_command('kiro'),
                },
                'timeout': 60,
            }
        ],
    }
    assert remove_hook(agent) == (HookAction.REMOVED, str(path))
    assert not path.exists()
    assert path.parent.is_dir()
    assert remove_hook(agent)[0] is HookAction.NOT_INSTALLED


def test_kiro_rewrites_changed_file(tmp_path):
    agent = _agent(tmp_path, 'kiro')
    path = tmp_path / '.kiro' / 'hooks' / 'aws-agent-toolkit.json'
    path.parent.mkdir()
    path.write_text('old')
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text())['version'] == 'v1'


def test_kiro_leaves_other_hooks_alone(tmp_path):
    agent = _agent(tmp_path, 'kiro')
    other = tmp_path / '.kiro' / 'hooks' / 'mine.json'
    other.parent.mkdir()
    other.write_text('{}')
    install_hook(agent)
    remove_hook(agent)
    assert os.listdir(other.parent) == ['mine.json']


def _kiro_with_agents(tmp_path, agents, default='my-agent'):
    """Return a detected Kiro with ``agents`` as ``{file name: content}``."""
    agent = _agent(tmp_path, 'kiro')
    if default is not None:
        settings = tmp_path / '.kiro' / 'settings' / 'cli.json'
        settings.parent.mkdir()
        settings.write_text(json.dumps({'chat.defaultAgent': default}))
    agents_dir = tmp_path / '.kiro' / 'agents'
    agents_dir.mkdir()
    for name, content in agents.items():
        if not isinstance(content, str):
            content = json.dumps(content, indent=2) + '\n'
        (agents_dir / name).write_text(content)
    return agent


def _kiro_agent_handler():
    return {'command': hook_shell_command('kiro'), 'timeout_ms': 60000}


def test_kiro_default_agent_found_by_name(tmp_path):
    agent = _kiro_with_agents(
        tmp_path,
        {
            'my-agent.json': {'name': 'other'},
            'Tool-my-agent.json': {'name': 'my-agent'},
        },
    )
    assert kiro_default_agent_path(agent) == str(
        tmp_path / '.kiro' / 'agents' / 'Tool-my-agent.json'
    )


def test_kiro_default_agent_found_by_file_name(tmp_path):
    agent = _kiro_with_agents(tmp_path, {'my-agent.json': {'tools': []}})
    assert kiro_default_agent_path(agent) == str(
        tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    )


@pytest.mark.parametrize(
    'settings', [None, '{}', '{"chat.defaultAgent": ""}', 'not json', '[]']
)
def test_kiro_without_default_agent_is_not_supported(tmp_path, settings):
    agent = _kiro_with_agents(
        tmp_path, {'my-agent.json': {'name': 'my-agent'}}, default=None
    )
    if settings is not None:
        path = tmp_path / '.kiro' / 'settings' / 'cli.json'
        path.parent.mkdir()
        path.write_text(settings)
    assert kiro_default_agent_path(agent) is None
    assert install_kiro_agent_hook(agent) == (HookAction.NOT_SUPPORTED, None)
    assert json.loads(
        (tmp_path / '.kiro' / 'agents' / 'my-agent.json').read_text()
    ) == {'name': 'my-agent'}


def test_kiro_missing_default_agent_file_is_not_supported(tmp_path):
    agent = _kiro_with_agents(tmp_path, {'other.json': {'name': 'other'}})
    assert install_kiro_agent_hook(agent) == (HookAction.NOT_SUPPORTED, None)
    assert os.listdir(tmp_path / '.kiro' / 'agents') == ['other.json']


def test_kiro_agent_hook_added_to_default_agent(tmp_path):
    spawn = {'command': 'git status'}
    other = {'matcher': 'fs_write', 'command': 'lint'}
    agent = _kiro_with_agents(
        tmp_path,
        {
            'my-agent.json': {
                'name': 'my-agent',
                'hooks': {'agentSpawn': [spawn], 'preToolUse': [other]},
            }
        },
    )
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    assert install_kiro_agent_hook(agent) == (HookAction.INSTALLED, str(path))
    assert json.loads(path.read_text()) == {
        'name': 'my-agent',
        'hooks': {
            'agentSpawn': [spawn, _kiro_agent_handler()],
            'preToolUse': [other],
        },
    }
    before = path.read_bytes()
    assert install_kiro_agent_hook(agent)[0] is HookAction.ALREADY_INSTALLED
    assert path.read_bytes() == before


def test_kiro_agent_hook_install_then_remove_restores_file(tmp_path):
    original = {'name': 'my-agent', 'prompt': 'Hi'}
    agent = _kiro_with_agents(tmp_path, {'my-agent.json': original})
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    before = path.read_text()
    install_kiro_agent_hook(agent)
    assert remove_kiro_agent_hooks(agent) == [(HookAction.REMOVED, str(path))]
    assert path.read_text() == before


def test_kiro_agent_hook_replaces_outdated_entry(tmp_path):
    outdated = {'command': hook_command('kiro'), 'timeout_ms': 10}
    agent = _kiro_with_agents(
        tmp_path,
        {
            'my-agent.json': {
                'name': 'my-agent',
                'hooks': {'agentSpawn': [outdated, outdated]},
            }
        },
    )
    install_kiro_agent_hook(agent)
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    assert json.loads(path.read_text())['hooks'] == {
        'agentSpawn': [_kiro_agent_handler()]
    }


def test_kiro_agent_keeps_formatting_it_can_not_preserve(tmp_path):
    # Formatting written by tools such as Jackson can't be reproduced.
    content = '{\n  "name" : "my-agent"\n}'
    agent = _kiro_with_agents(tmp_path, {'my-agent.json': content})
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    assert install_kiro_agent_hook(agent) == (HookAction.UNREADABLE, str(path))
    assert path.read_text() == content


def test_kiro_v3_agent_is_not_needed(tmp_path):
    content = {'name': 'my-agent', 'hooks': [{'trigger': 'SessionStart'}]}
    agent = _kiro_with_agents(tmp_path, {'my-agent.json': content})
    path = tmp_path / '.kiro' / 'agents' / 'my-agent.json'
    before = path.read_text()
    assert install_kiro_agent_hook(agent) == (HookAction.NOT_NEEDED, str(path))
    assert path.read_text() == before


def test_kiro_agent_hooks_removed_from_every_agent(tmp_path):
    ours = {'hooks': {'agentSpawn': [_kiro_agent_handler()]}}
    unreadable = (
        '{\n  "hooks" : {"agentSpawn" : [{"command" : '
        f'{json.dumps(hook_command("kiro"))}}}]}}\n}}'
    )
    agent = _kiro_with_agents(
        tmp_path,
        {
            'a.json': {'name': 'a', **ours},
            'b.json': {'name': 'b', **ours},
            'c.json': {'name': 'c'},
            'd.json': unreadable,
        },
        default='b',
    )
    agents_dir = tmp_path / '.kiro' / 'agents'
    assert remove_kiro_agent_hooks(agent) == [
        (HookAction.REMOVED, str(agents_dir / 'a.json')),
        (HookAction.REMOVED, str(agents_dir / 'b.json')),
        (HookAction.UNREADABLE, str(agents_dir / 'd.json')),
    ]
    assert json.loads((agents_dir / 'a.json').read_text()) == {'name': 'a'}
    assert (agents_dir / 'd.json').read_text() == unreadable
    assert remove_kiro_agent_hooks(agent) == [
        (HookAction.UNREADABLE, str(agents_dir / 'd.json'))
    ]


def test_kiro_agent_manual_entry_is_the_installed_entry():
    text = format_kiro_agent_manual_entry('~/x.json', indent='')
    first, rest = text.split('\n', 1)
    assert first == 'Add this hook to ~/x.json:'
    assert json.loads(rest) == {
        'hooks': {'agentSpawn': [_kiro_agent_handler()]}
    }


def test_unsupported_agent(tmp_path):
    agent = _agent(tmp_path, 'cline')
    assert install_hook(agent) == (HookAction.NOT_SUPPORTED, None)
    assert remove_hook(agent) == (HookAction.NOT_SUPPORTED, None)
    assert hook_config_path(agent.config) is None
    assert os.listdir(tmp_path / '.cline') == []


def test_write_failure_leaves_file(tmp_path, monkeypatch):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    path.write_text('{}\n')

    def fail(*args, **kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(hooks, 'write_file_atomic', fail)
    with pytest.raises(OSError):
        install_hook(agent)
    assert path.read_text() == '{}\n'


@pytest.mark.parametrize('agent_id', sorted(_HOOK_FILES))
def test_manual_entry_is_the_installed_entry(agent_id):
    text = format_manual_entry(agent_id, '~/x.json', indent='')
    first, rest = text.split('\n', 1)
    assert first == 'Add this hook to ~/x.json:'
    assert json.loads(rest) == _expected_entry(agent_id)


def test_hook_command_has_no_shell_syntax():
    for agent_id in hooks.HOOK_AGENT_IDS:
        assert hook_command(agent_id) == (
            f'aws agent-toolkit update-skill --hook --agent {agent_id} '
            '--no-cli-auto-prompt'
        )


@pytest.mark.parametrize(
    'agent_id, windows, suffix',
    [
        ('claude-code', False, ' || true'),
        ('kiro', False, ' || true'),
        ('claude-code', True, '; exit 0'),
        ('gemini-cli', True, '; exit 0'),
        ('codex', True, '; exit 0'),
        ('cursor', True, '; exit 0'),
        ('kiro', True, ' || verify > nul'),
    ],
)
def test_hook_shell_command_always_exits_zero(agent_id, windows, suffix):
    with patch.object(hooks, 'is_windows', windows):
        assert hook_shell_command(agent_id) == hook_command(agent_id) + suffix


def test_install_replaces_unwrapped_entry(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    previous = _our_group('claude-code')
    previous['hooks'][0]['command'] = hook_command('claude-code')
    path.write_text(json.dumps({'hooks': {'SessionStart': [previous]}}))
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        _our_group('claude-code')
    ]


def test_install_replaces_entry_without_auto_prompt_flag(tmp_path):
    agent = _agent(tmp_path, 'claude-code')
    path = tmp_path / '.claude-code' / 'settings.json'
    previous = _our_group('claude-code')
    previous['hooks'][0]['command'] = (
        'aws agent-toolkit update-skill --all --hook claude-code'
    )
    path.write_text(json.dumps({'hooks': {'SessionStart': [previous]}}))
    assert install_hook(agent)[0] is HookAction.INSTALLED
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [
        _our_group('claude-code')
    ]


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
