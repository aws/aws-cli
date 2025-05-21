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

import argparse

from awscli.argparser import CLIArgParser
from awscli.customizations.q.chat import ChatCommand


class AgentModeDriver(CLIArgParser):
    """
    Driver for the CLI to enable the Q plugin when the --agent-mode argument
    is passed. This behaves more like a custom command, but is implemented
    as a driver similar to autoprompt so we don't need to expose it as an
    actual command via the command table.
    """

    _AGENT_MODE_ARG = '--agent-mode'

    def __init__(self, driver):
        super().__init__()
        self._driver = driver
        self._session = driver.session
        self._parser = self._create_parser()

    def _create_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--region',
            help='AWS region to use for agent inference.',
            default=None,
        )
        parser.add_argument(
            '--profile',
            help='Use a specific profile from your credential file.',
            default=None,
        )
        parser.add_argument(
            self._AGENT_MODE_ARG,
            action='store_true',
            help='Enable agentic mode.',
        )
        return parser

    def should_enter_agent_mode(self, args):
        return self._AGENT_MODE_ARG in args

    def enter_agent_mode(self, args):
        parsed_args = self._parser.parse_args(args)

        # TODO - handle the agent-mode-specific region and profile
        return ChatCommand(self._session)('', parsed_args)
