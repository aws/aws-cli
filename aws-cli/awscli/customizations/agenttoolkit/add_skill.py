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
import sys

from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    SKILL_NAME_ARG,
    SKILL_VERSION_ARG,
    create_client,
    get_skill_download,
    install_skill,
    resolve_agents,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError


class AddSkillCommand(BasicCommand):
    NAME = 'add-skill'
    DESCRIPTION = (
        'Download and install an AWS skill to detected AI coding agents. '
        'By default the latest version is installed globally to all detected '
        'agents. Use ``--agent`` to target a specific tool, or '
        '``--skill-version`` to pin a specific version.'
    )
    ARG_TABLE = [
        SKILL_NAME_ARG,
        SKILL_VERSION_ARG,
        AGENT_ARG,
    ]

    def __init__(self, session, stream=None, client=None, agent_configs=None):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        self._client = client
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        skill_name = parsed_args.skill_name
        version = getattr(parsed_args, 'skill_version', None)
        agent_filter = getattr(parsed_args, 'agent', None)

        agents = resolve_agents(agent_filter, self._agent_configs)
        if not agents:
            raise ParamValidationError('No supported AI coding agents found.')

        client = self._client or create_client(self._session, parsed_globals)
        zip_bytes, checksum, version = get_skill_download(
            client, skill_name, version=version
        )

        install_skill(
            skill_name, version, zip_bytes, checksum, agents, self._stream
        )
        return 0
