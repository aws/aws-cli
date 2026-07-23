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
"""End-of-``aws configure`` hint suggesting the Agent Toolkit wizard.

After a successful ``aws configure`` that writes profile values, offer to run
``aws configure agent-toolkit`` when a supported AI coding agent is present and
the toolkit is not already installed. The hint is interactive-only and can be
permanently suppressed.
"""

import json
import logging
import os

from awscli.customizations.agenttoolkit.agents import (
    get_detected_real_agents,
)
from awscli.customizations.agenttoolkit.configure import (
    ConfigureAgentToolkitCommand,
)
from awscli.customizations.prompts import yes_no_never_choice
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty

LOG = logging.getLogger(__name__)

STATE_PATH = '~/.aws/cli/agent-toolkit/state.json'

PROMPT_TEXT = (
    'Configure AWS skills and the AWS MCP server for your AI coding '
    'agent(s)? [Y/n/never]: '
)


def _state_file():
    return os.path.expanduser(STATE_PATH)


def _load_state():
    try:
        with open(_state_file()) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as e:
        LOG.debug('Could not read agent toolkit hint state: %s', e)
        return {}


def _save_state(state):
    path = _state_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f'{path}.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(state, f)
            f.write('\n')
        os.replace(tmp_path, path)
    except OSError as e:
        LOG.debug('Could not write agent toolkit hint state: %s', e)


def _dismiss_forever():
    state = _load_state()
    state['hint_dismissed'] = True
    _save_state(state)


def _has_installed_skills(detected_agents):
    return any(agent.get_installed_skills() for agent in detected_agents)


def _is_eligible(detected_agents):
    if not is_stdin_a_tty():
        return False
    if _load_state().get('hint_dismissed'):
        return False
    if not detected_agents:
        return False
    if _has_installed_skills(detected_agents):
        return False
    return True


def maybe_prompt_agent_toolkit(session, parsed_globals, stream=None):
    try:
        detected_agents = get_detected_real_agents()
        if not _is_eligible(detected_agents):
            return
        choice = yes_no_never_choice(PROMPT_TEXT)
        if choice == 'never':
            _dismiss_forever()
            return
        if choice == 'no':
            return
        command = ConfigureAgentToolkitCommand(session)
        command([], parsed_globals)
    except Exception as e:
        LOG.debug('Agent toolkit hint failed: %s', e, exc_info=True)
