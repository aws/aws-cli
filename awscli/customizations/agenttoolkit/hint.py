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
``aws configure agent-toolkit`` when a supported AI coding agent is present
and no AWS skills are installed yet. The Agent Toolkit API only exists in
one commercial region, so callers whose region resolves to the commercial
partition get an interactive prompt and the wizard is pinned to that region.
In other partitions we fall back to a non-interactive tip rather than
silently taking the user across a partition boundary. Either way the hint
only shows on a TTY and can be suppressed.
"""

import copy
import json
import logging
import os
import re

from botocore.loaders import Loader
from botocore.utils import ensure_boolean

from awscli.customizations.agenttoolkit.agents import (
    get_detected_real_agents,
)
from awscli.customizations.agenttoolkit.configure import (
    ConfigureAgentToolkitCommand,
)
from awscli.customizations.agenttoolkit.utils import AGENT_TOOLKIT_REGION
from awscli.customizations.prompts import yes_no_never_choice
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty

LOG = logging.getLogger(__name__)

STATE_PATH = '~/.aws/cli/agent-toolkit/state.json'

HINT_DISABLED_ENV_VAR = 'AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED'

# AGENT_TOOLKIT_REGION only exists in the commercial partition. Elsewhere we
# cannot run the wizard inline, so we only offer the interactive prompt to
# callers in this partition.
COMMERCIAL_PARTITION = 'aws'

PROMPT_TEXT = (
    '\nConfigure AWS skills and the AWS MCP server for your AI coding '
    'agent(s)? [y/n/never]: '
)

HINT_TEXT = (
    "\nTip: run 'aws configure agent-toolkit' to set up AWS skills and the "
    'AWS MCP server for your AI coding agent(s).\n'
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


def hint_disabled():
    return ensure_boolean(os.environ.get(HINT_DISABLED_ENV_VAR, ''))


def _is_eligible():
    if not is_stdin_a_tty():
        return False
    if hint_disabled():
        return False
    if _load_state().get('hint_dismissed'):
        return False
    detected_agents = get_detected_real_agents()
    if not detected_agents:
        return False
    if _has_installed_skills(detected_agents):
        return False
    return True


def _region_partition(region):
    for partition in Loader().load_data('partitions')['partitions']:
        if region in partition.get('regions', {}):
            return partition['id']
        regex = partition.get('regionRegex')
        if regex and re.match(regex, region):
            return partition['id']
    return None


def _can_run_wizard(region):
    if not region:
        # With no region resolved anywhere the wizard falls back to
        # AGENT_TOOLKIT_REGION
        return True
    return _region_partition(region) == COMMERCIAL_PARTITION


def _wizard_globals(parsed_globals, region):
    if region and region != AGENT_TOOLKIT_REGION:
        LOG.debug(
            'Running "aws configure agent-toolkit" in %s instead of %s, the '
            'only region the Agent Toolkit for AWS is available in.',
            AGENT_TOOLKIT_REGION,
            region,
        )
    wizard_globals = copy.copy(parsed_globals)
    wizard_globals.region = AGENT_TOOLKIT_REGION
    return wizard_globals


def maybe_prompt_agent_toolkit(session, parsed_globals, region):
    """Offer to run the Agent Toolkit wizard.

    :param region: The region the calling command just resolved for the
        profile, or ``None`` if it did not resolve one.
    """
    try:
        if not _is_eligible():
            return
        # Outside the commercial partition, running the wizard would mean
        # calling AGENT_TOOLKIT_REGION across a partition boundary on the
        # user's behalf. Print a tip and let them decide instead.
        if not _can_run_wizard(region):
            uni_print(HINT_TEXT)
            return
        choice = yes_no_never_choice(PROMPT_TEXT)
        if choice == 'never':
            _dismiss_forever()
        run_wizard = choice == 'yes'
    except Exception as e:
        LOG.debug('Agent toolkit hint failed: %s', e, exc_info=True)
        return

    if run_wizard:
        command = ConfigureAgentToolkitCommand(session)
        command([], _wizard_globals(parsed_globals, region))
