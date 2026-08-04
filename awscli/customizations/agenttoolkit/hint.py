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
"""End-of-command hint pointing at the Agent Toolkit wizard.

After a successful ``aws configure``, ``aws configure sso``, or first-time
``aws login``, print a one-line tip suggesting ``aws configure agent-toolkit``
when a supported AI coding agent is present and no AWS skills are installed
yet. The tip only shows on a TTY and can be suppressed with an environment
variable.
"""

import logging
import os

from botocore.utils import ensure_boolean

from awscli.customizations.agenttoolkit.agents import (
    get_detected_real_agents,
)
from awscli.customizations.utils import uni_print
from awscli.utils import is_a_tty

LOG = logging.getLogger(__name__)

HINT_DISABLED_ENV_VAR = 'AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED'

# The Agent Toolkit skill APIs are only available in us-east-1 today, so the
# tip pins the region explicitly rather than routing the caller's configured
# region through a hidden cross-region call.
HINT_TEXT = (
    "\nTip: run 'aws configure agent-toolkit --region us-east-1' to set up "
    'AWS skills and the AWS MCP server for your AI coding agent(s).\n'
)


def hint_disabled():
    return ensure_boolean(os.environ.get(HINT_DISABLED_ENV_VAR, ''))


def _has_installed_skills(detected_agents):
    return any(agent.get_installed_skills() for agent in detected_agents)


def _is_eligible():
    if not is_a_tty():
        return False
    if hint_disabled():
        return False
    detected_agents = get_detected_real_agents()
    if not detected_agents:
        return False
    if _has_installed_skills(detected_agents):
        return False
    return True


def maybe_print_agent_toolkit_hint():
    try:
        if _is_eligible():
            uni_print(HINT_TEXT)
    except Exception as e:
        LOG.debug('Agent toolkit hint failed: %s', e, exc_info=True)
