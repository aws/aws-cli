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

HOOK_ERROR_MESSAGE = (
    'AWS agent skills could not be checked for updates; run '
    '"aws agent-toolkit update-skill --all" for details.'
)

# The file each agent's session start hook lives in, relative to the agent's
# base directory. Hook runs are recorded against it.
_HOOK_FILENAMES = {
    # https://code.claude.com/docs/en/hooks
    'claude-code': 'settings.json',
    # https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md
    'gemini-cli': 'settings.json',
    # https://developers.openai.com/codex/hooks
    'codex': 'hooks.json',
    # https://cursor.com/docs/agent/hooks
    'cursor': 'hooks.json',
    # https://kiro.dev/docs/hooks/
    'kiro': os.path.join('hooks', 'aws-agent-toolkit.json'),
}

HOOK_AGENT_IDS = tuple(_HOOK_FILENAMES)


def is_hook_supported(agent_id):
    return agent_id in HOOK_AGENT_IDS


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
    return os.path.join(base_dir, _HOOK_FILENAMES[agent_config.id])


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
    """Return what the hook prints for ``agent_id``, or ``''`` if nothing.

    :param skills_updated: Whether any skill changed on disk, so the agent
        should load them again.
    """
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
