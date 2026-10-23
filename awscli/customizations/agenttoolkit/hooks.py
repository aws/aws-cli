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
import errno
import glob
import json
import os
import stat
from typing import Callable, Optional

from awscli.compat import is_windows
from awscli.customizations.agenttoolkit.atomic import write_file_atomic

HOOK_NAME = 'aws-agent-toolkit'
_COMMAND_MARKERS = ('agent-toolkit update-skill', '--hook')
_TEMP_PREFIX = '.aws-agent-toolkit-'


CODEX_TRUST_NOTE = (
    'Open Codex and run /hooks to trust the hook. It does not run until '
    'you do.'
)
KIRO_VERSION_NOTE = 'Used by Kiro IDE 1.0.182 or later and kiro-cli --v3.'
KIRO_AGENT_NOTE = (
    'kiro-cli 2.x runs it in interactive sessions of this agent only.'
)
KIRO_NO_AGENT_NOTE = (
    'kiro-cli 2.x only runs hooks from agent configs and no default agent '
    'is set.'
)

HOOK_ERROR_MESSAGE = (
    'AWS agent skills could not be checked for updates; run '
    '"aws agent-toolkit update-skill --all" for details.'
)


class HookAction(enum.Enum):
    INSTALLED = 'installed'
    ALREADY_INSTALLED = 'already_installed'
    REMOVED = 'removed'
    NOT_INSTALLED = 'not_installed'
    UNREADABLE = 'unreadable'
    NOT_SUPPORTED = 'not_supported'
    NOT_NEEDED = 'not_needed'


@dataclasses.dataclass(frozen=True)
class _HookFormat:
    filename: str
    """Hook file, relative to the agent's base directory."""

    event: str
    """Key under ``hooks`` holding the session start entries."""

    matcher: Optional[str]
    """Matcher of the group our handler is in. ``None`` for agents whose
    event list holds handlers directly."""

    handler: Callable[[str], dict]
    """Builds our handler from the hook command."""

    version: Optional[int] = None
    """Top-level ``version`` the file needs, if any."""


_HOOK_FORMATS = {
    # https://code.claude.com/docs/en/hooks
    'claude-code': _HookFormat(
        filename='settings.json',
        event='SessionStart',
        matcher='startup',
        handler=lambda command: {
            'type': 'command',
            'command': command,
            'timeout': 60,
        },
    ),
    # https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md
    # Timeouts are in milliseconds.
    'gemini-cli': _HookFormat(
        filename='settings.json',
        event='SessionStart',
        matcher='*',
        handler=lambda command: {
            'name': HOOK_NAME,
            'type': 'command',
            'command': command,
            'timeout': 60000,
        },
    ),
    # https://developers.openai.com/codex/hooks
    'codex': _HookFormat(
        filename='hooks.json',
        event='SessionStart',
        matcher='startup',
        handler=lambda command: {
            'type': 'command',
            'command': command,
            'timeout': 60,
        },
    ),
    # https://cursor.com/docs/agent/hooks
    'cursor': _HookFormat(
        filename='hooks.json',
        event='sessionStart',
        matcher=None,
        handler=lambda command: {'command': command, 'timeout': 60},
        version=1,
    ),
}

# https://kiro.dev/docs/hooks/
_KIRO_ID = 'kiro'
_KIRO_FILENAME = os.path.join('hooks', f'{HOOK_NAME}.json')

# kiro-cli 2.x ignores the standalone hook file and only runs hooks from the
# active agent's config, so the hook is also added to the default agent.
# https://kiro.dev/docs/cli/2x-reference/
_KIRO_AGENTS_DIR = 'agents'
_KIRO_CLI_SETTINGS = os.path.join('settings', 'cli.json')
_KIRO_DEFAULT_AGENT_KEY = 'chat.defaultAgent'
_KIRO_AGENT_FORMAT = _HookFormat(
    filename='',
    event='agentSpawn',
    matcher=None,
    handler=lambda command: {'command': command, 'timeout_ms': 60000},
)

HOOK_AGENT_IDS = ('claude-code', 'gemini-cli', 'codex', 'cursor', _KIRO_ID)


class _UnreadableError(Exception):
    pass


def is_hook_supported(agent_id):
    return agent_id in HOOK_AGENT_IDS


def hook_command(agent_id):
    # Agents run hooks without a terminal, where auto-prompt turned on in
    # the user's config would fail before the command runs.
    return (
        f'aws agent-toolkit update-skill --hook --agent {agent_id} '
        '--no-cli-auto-prompt'
    )


def hook_shell_command(agent_id):
    """Return the hook command wrapped so the hook always exits zero.

    ``aws`` exits non-zero with ``--hook`` when a skill could not be updated,
    and it can also be missing, fail to start, or crash. The agent would
    report any of these as a failed hook. The wrapper depends on the shell
    the agent runs hooks with.
    """
    return hook_command(agent_id) + _exit_zero_suffix(agent_id)


def _exit_zero_suffix(agent_id):
    if not is_windows:
        return ' || true'
    if agent_id == _KIRO_ID:
        # Kiro runs hooks with cmd.exe, where ``verify`` resets the error
        # level.
        return ' || verify > nul'
    # The others run hooks with PowerShell, except Claude Code which uses
    # Git Bash when it is installed. This works in both.
    return '; exit 0'


def hook_config_path(agent_config, base_dir=None):
    """Return the file the agent's hook lives in, or ``None`` if unsupported.

    :param base_dir: The detected agent's base directory. Resolved from the
        config when not given, even if the agent is not installed.
    """
    if not is_hook_supported(agent_config.id):
        return None
    if base_dir is None:
        base_dir = agent_config.resolve_base_dir() or (
            agent_config.expand_path(agent_config.detection_path).rstrip(
                os.sep
            )
        )
    if agent_config.id == _KIRO_ID:
        return os.path.join(base_dir, _KIRO_FILENAME)
    return os.path.join(base_dir, _HOOK_FORMATS[agent_config.id].filename)


def install_hook(agent):
    """Install the session start hook for a detected agent."""
    agent_id = agent.config.id
    path = hook_config_path(agent.config, agent.base_dir)
    if path is None:
        return HookAction.NOT_SUPPORTED, None
    if agent_id == _KIRO_ID:
        return _install_kiro_hook(agent, path), path
    hook_format = _HOOK_FORMATS[agent_id]
    try:
        text, data = _read_json(path)
        action = _add_entry(data, hook_format, _handler(agent_id))
    except _UnreadableError:
        return HookAction.UNREADABLE, path
    if action is not HookAction.INSTALLED:
        return action, path
    if text is None:
        _make_parent_dir(agent, path)
    _write(path, _dump_json(data))
    return HookAction.INSTALLED, path


def remove_hook(agent):
    """Remove the session start hook from a detected agent."""
    agent_id = agent.config.id
    path = hook_config_path(agent.config, agent.base_dir)
    if path is None:
        return HookAction.NOT_SUPPORTED, None
    if agent_id == _KIRO_ID:
        return _remove_kiro_hook(path), path
    try:
        text, data = _read_json(path)
        removed = _remove_entries(data, _HOOK_FORMATS[agent_id])
    except _UnreadableError:
        # Most files we can't edit never had our hook, such as a Gemini
        # settings file with comments, so only those that do are reported.
        if _mentions_hook(path):
            return HookAction.UNREADABLE, path
        return HookAction.NOT_INSTALLED, path
    if not removed:
        return HookAction.NOT_INSTALLED, path
    _write(path, _dump_json(data))
    return HookAction.REMOVED, path


def kiro_default_agent_path(agent):
    """Return the config file of Kiro's default agent, or ``None``."""
    name = _kiro_default_agent_name(agent.base_dir)
    if name is None:
        return None
    paths = _kiro_agent_paths(agent)
    # Agents are found by the name in the file, which tools that install
    # agents often make different from the file name.
    for path in paths:
        if _agent_name(path) == name:
            return path
    for path in paths:
        if os.path.splitext(os.path.basename(path))[0] == name:
            return path
    return None


def install_kiro_agent_hook(agent):
    """Add the hook to Kiro's default agent, for kiro-cli 2.x."""
    path = kiro_default_agent_path(agent)
    if path is None:
        return HookAction.NOT_SUPPORTED, None
    try:
        text, data = _read_json(path)
        if isinstance(data.get('hooks'), list):
            return HookAction.NOT_NEEDED, path
        action = _add_entry(data, _KIRO_AGENT_FORMAT, _kiro_agent_handler())
    except _UnreadableError:
        return HookAction.UNREADABLE, path
    if text is None or not text.strip():
        # Removed since it was found, or empty. Adding only our hook would
        # not make it an agent.
        return HookAction.NOT_SUPPORTED, None
    if action is not HookAction.INSTALLED:
        return action, path
    _write(path, _dump_json(data))
    return HookAction.INSTALLED, path


def remove_kiro_agent_hooks(agent):
    """Remove the hook from every Kiro agent config that has it."""
    results = []
    for path in _kiro_agent_paths(agent):
        if not _mentions_hook(path):
            continue
        try:
            _, data = _read_json(path)
            if isinstance(data.get('hooks'), list):
                # We never add the hook to V3 agents.
                continue
            removed = _remove_entries(data, _KIRO_AGENT_FORMAT)
        except _UnreadableError:
            results.append((HookAction.UNREADABLE, path))
            continue
        if removed:
            _write(path, _dump_json(data))
            results.append((HookAction.REMOVED, path))
    return results


def _kiro_default_agent_name(base_dir):
    try:
        with open(
            os.path.join(base_dir, _KIRO_CLI_SETTINGS), encoding='utf-8'
        ) as f:
            settings = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(settings, dict):
        return None
    name = settings.get(_KIRO_DEFAULT_AGENT_KEY)
    return name if isinstance(name, str) and name else None


def _kiro_agent_paths(agent):
    return sorted(
        glob.glob(os.path.join(agent.base_dir, _KIRO_AGENTS_DIR, '*.json'))
    )


def _agent_name(path):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data.get('name') if isinstance(data, dict) else None


def format_manual_entry(agent_id, path, indent='    '):
    """Return instructions for adding the hook to ``path`` by hand."""
    return _format_manual_entry(
        _HOOK_FORMATS[agent_id], _handler(agent_id), path, indent
    )


def format_kiro_agent_manual_entry(path, indent='    '):
    """Return instructions for adding the hook to a Kiro agent config."""
    return _format_manual_entry(
        _KIRO_AGENT_FORMAT, _kiro_agent_handler(), path, indent
    )


def _format_manual_entry(hook_format, handler, path, indent):
    if hook_format.matcher is None:
        snippet = {'hooks': {hook_format.event: [handler]}}
    else:
        snippet = {
            'hooks': {hook_format.event: [_group(hook_format, handler)]}
        }
    if hook_format.version is not None:
        snippet = {'version': hook_format.version, **snippet}
    lines = [f'Add this hook to {path}:']
    lines.extend(json.dumps(snippet, indent=2).splitlines())
    return ''.join(f'{indent}{line}\n' for line in lines)


def format_hook_message(
    updated, installed, skipped, failed_updates, failed_installs
):
    """Return the one line summary a hook reports, or ``''`` if nothing
    changed and nothing failed."""
    if not (updated or installed or failed_updates or failed_installs):
        return ''
    parts = []
    if updated:
        parts.append(f'AWS agent skills updated: {", ".join(updated)}.')
    if installed:
        parts.append(f'New AWS core skills installed: {", ".join(installed)}.')
    if failed_updates:
        parts.append(
            f'Could not update {", ".join(failed_updates)}; run '
            '"aws agent-toolkit update-skill --all" for details.'
        )
    if failed_installs:
        # update-skill only updates installed skills, so point at add-skill.
        skill_name = (
            failed_installs[0] if len(failed_installs) == 1 else '<name>'
        )
        parts.append(
            f'Could not install {", ".join(failed_installs)}; run '
            f'"aws agent-toolkit add-skill --skill-name {skill_name}" for '
            'details.'
        )
    if skipped:
        parts.append(f'Skipped {", ".join(skipped)}.')
    return ' '.join(parts)


def format_hook_output(agent_id, message, skills_updated=False):
    """Return what the hook prints for ``agent_id``, or ``''`` if nothing."""
    if not message:
        return ''
    if agent_id == 'claude-code':
        specific = {
            'hookEventName': 'SessionStart',
            'additionalContext': message,
        }
        if skills_updated:
            specific['reloadSkills'] = True
        output = {'hookSpecificOutput': specific, 'systemMessage': message}
    elif agent_id == 'gemini-cli':
        # Gemini only loads skills at startup.
        context = message
        if skills_updated:
            context += ' Run /skills reload to use them.'
        output = {
            'systemMessage': message,
            'hookSpecificOutput': {
                'hookEventName': 'SessionStart',
                'additionalContext': context,
            },
        }
    elif agent_id == 'cursor':
        output = {'additional_context': message}
    else:
        # Codex and Kiro add plain text output to the agent's context.
        return f'{message}\n'
    return json.dumps(output, separators=(',', ':')) + '\n'


def _handler(agent_id):
    return _HOOK_FORMATS[agent_id].handler(hook_shell_command(agent_id))


def _kiro_agent_handler():
    return _KIRO_AGENT_FORMAT.handler(hook_shell_command(_KIRO_ID))


def _group(hook_format, handler):
    return {'matcher': hook_format.matcher, 'hooks': [handler]}


def _is_ours(handler):
    if not isinstance(handler, dict):
        return False
    command = handler.get('command')
    return isinstance(command, str) and _has_markers(command)


def _has_markers(text):
    return all(marker in text for marker in _COMMAND_MARKERS)


def _has_handlers(group):
    return isinstance(group, dict) and isinstance(group.get('hooks'), list)


def _entries(data, event):
    """Return the ``hooks`` object and its ``event`` list, or ``None`` for
    each one that is missing."""
    hooks = data.get('hooks')
    if hooks is None:
        return None, None
    if not isinstance(hooks, dict):
        raise _UnreadableError('"hooks" is not an object')
    entries = hooks.get(event)
    if entries is not None and not isinstance(entries, list):
        raise _UnreadableError(f'"hooks.{event}" is not a list')
    return hooks, entries


def _handlers(entries, hook_format):
    if hook_format.matcher is None:
        return entries
    return [h for g in entries if _has_handlers(g) for h in g['hooks']]


def _add_entry(data, hook_format, handler):
    """Add our handler to ``data`` unless one of ours is there."""
    _, entries = _entries(data, hook_format.event)
    installed = any(_is_ours(h) for h in _handlers(entries or [], hook_format))
    needs_version = hook_format.version is not None and 'version' not in data
    if installed and not needs_version:
        return HookAction.ALREADY_INSTALLED
    if needs_version:
        data['version'] = hook_format.version
    if not installed:
        hooks, entries = _entries(data, hook_format.event)
        if hooks is None:
            hooks = data['hooks'] = {}
        if entries is None:
            entries = hooks[hook_format.event] = []
        if hook_format.matcher is None:
            entries.append(handler)
        else:
            entries.append(_group(hook_format, handler))
    return HookAction.INSTALLED


def _remove_entries(data, hook_format):
    """Remove every handler of ours, and groups left empty. Returns whether
    any were removed."""
    hooks, entries = _entries(data, hook_format.event)
    if not entries:
        return False
    removed = False
    kept = []
    for entry in entries:
        if hook_format.matcher is None:
            if _is_ours(entry):
                removed = True
            else:
                kept.append(entry)
            continue
        if not _has_handlers(entry):
            kept.append(entry)
            continue
        others = [h for h in entry['hooks'] if not _is_ours(h)]
        if len(others) == len(entry['hooks']):
            kept.append(entry)
            continue
        removed = True
        if others:
            entry['hooks'] = others
            kept.append(entry)
    if not removed:
        return False
    if kept:
        hooks[hook_format.event] = kept
    else:
        del hooks[hook_format.event]
    if not hooks:
        del data['hooks']
    return True


def _mentions_hook(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return _has_markers(f.read())


def _read_json(path):
    """Return ``(text, data)`` for the JSON file at ``path``."""
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        return None, {}
    except UnicodeDecodeError as e:
        raise _UnreadableError(str(e)) from e
    if not text.strip():
        return text, {}
    try:
        data = json.loads(text)
    except ValueError as e:
        raise _UnreadableError(str(e)) from e
    if not isinstance(data, dict):
        raise _UnreadableError('not a JSON object')
    return text, data


def _dump_json(data):
    # Written like the MCP server config.
    return json.dumps(data, indent=2) + '\n'


def _kiro_hook_content():
    return _dump_json(
        {
            'version': 'v1',
            'hooks': [
                {
                    'name': HOOK_NAME,
                    'description': (
                        'Keeps AWS agent skills up to date '
                        '(managed by aws agent-toolkit)'
                    ),
                    'trigger': 'SessionStart',
                    'action': {
                        'type': 'command',
                        'command': hook_shell_command(_KIRO_ID),
                    },
                    'timeout': 60,
                }
            ],
        }
    )


def _install_kiro_hook(agent, path):
    # The file is named for us, so it is ours. It is left alone while it
    # runs our command.
    try:
        with open(path, encoding='utf-8', errors='replace', newline='') as f:
            if _has_markers(f.read()):
                return HookAction.ALREADY_INSTALLED
    except FileNotFoundError:
        _make_parent_dir(agent, path)
    _write(path, _kiro_hook_content())
    return HookAction.INSTALLED


def _remove_kiro_hook(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        return HookAction.NOT_INSTALLED
    return HookAction.REMOVED


def _make_parent_dir(agent, path):
    # Directories are only created inside the agent's own directory, never
    # in place of it.
    root = agent.base_dir
    if not os.path.isdir(root):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), root)
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _write(path, content):
    # Write through symlinks, such as a settings file kept in a dotfiles
    # repository, rather than replacing the link.
    path = os.path.realpath(path)
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        mode = None
    write_file_atomic(path, content, prefix=_TEMP_PREFIX, mode=mode)
