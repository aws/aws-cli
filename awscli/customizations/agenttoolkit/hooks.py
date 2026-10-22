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

HOOK_ERROR_MESSAGE = (
    'AWS agent skills could not be checked for updates; run '
    '"aws agent-toolkit update-skill --all" for details.'
)

# Agents ``update-skill --hook`` can run as the session start hook of.
HOOK_AGENT_IDS = ('claude-code', 'gemini-cli', 'codex', 'cursor', 'kiro')


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
