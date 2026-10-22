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

from awscli.customizations.agenttoolkit import hooks
from awscli.customizations.agenttoolkit.hooks import (
    format_hook_message,
    format_hook_output,
)


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
