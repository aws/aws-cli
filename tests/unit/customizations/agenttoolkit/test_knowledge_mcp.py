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
import json
from io import StringIO
from unittest.mock import MagicMock, patch

from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.agenttoolkit.configure import (
    ConfigureAgentToolkitCommand,
)
from tests.unit.customizations.agenttoolkit.utils import make_session

KNOWLEDGE_SERVER_KEY = 'aws-knowledge-mcp-server'
KNOWLEDGE_SERVER_URL = 'https://knowledge-mcp.global.api.aws'

EXPECTED_JSON_ENTRIES = {
    'claude-code': {
        'url': KNOWLEDGE_SERVER_URL,
        'type': 'http',
    },
    'cline': {
        'url': KNOWLEDGE_SERVER_URL,
        'type': 'streamableHttp',
        'disabled': False,
    },
    'cursor': {
        'url': KNOWLEDGE_SERVER_URL,
    },
    'gemini-cli': {
        'httpUrl': KNOWLEDGE_SERVER_URL,
    },
    'kiro': {
        'url': KNOWLEDGE_SERVER_URL,
        'disabled': False,
    },
    'opencode': {
        'type': 'remote',
        'url': KNOWLEDGE_SERVER_URL,
        'enabled': True,
    },
    'windsurf': {
        'serverUrl': KNOWLEDGE_SERVER_URL,
    },
}


def _get_agent_config(agent_id):
    return next(config for config in AGENT_CONFIGS if config.id == agent_id)


def test_json_agents_use_their_remote_knowledge_server_schema(tmp_path):
    for agent_id, expected_entry in EXPECTED_JSON_ENTRIES.items():
        base_dir = tmp_path / agent_id
        base_dir.mkdir()
        source_config = _get_agent_config(agent_id)
        config = dataclasses.replace(
            source_config,
            detection_path=str(base_dir),
            detection_path_env_override=None,
            mcp_config_path='mcp.json',
        )

        agent = config.detect()
        agent.configure_mcp_server()

        data = json.loads((base_dir / 'mcp.json').read_text())
        assert data[config.mcp_servers_key][KNOWLEDGE_SERVER_KEY] == (
            expected_entry
        )


def test_codex_registers_remote_knowledge_server_by_url():
    config = _get_agent_config('codex')
    assert config.mcp_shell_command == [
        'codex',
        'mcp',
        'add',
        KNOWLEDGE_SERVER_KEY,
        '--url',
        KNOWLEDGE_SERVER_URL,
    ]


def test_configure_prompt_names_aws_knowledge_mcp_server(tmp_path):
    base_dir = tmp_path / '.test-agent'
    base_dir.mkdir()
    source_config = _get_agent_config('cursor')
    config = dataclasses.replace(
        source_config,
        detection_path=str(base_dir),
        mcp_config_path='mcp.json',
    )
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [{'skills': []}]
    client.get_paginator.return_value = paginator
    command = ConfigureAgentToolkitCommand(
        make_session(),
        stream=StringIO(),
        agent_configs=[config],
        client=client,
    )
    parsed_args = MagicMock()
    parsed_args.yes = False

    with (
        patch(
            'awscli.customizations.agenttoolkit.configure.multiselect_choice',
            side_effect=lambda message, items, **kwargs: items,
        ),
        patch(
            'awscli.customizations.agenttoolkit.configure.yes_no_choice',
            return_value=False,
        ) as yes_no_mock,
    ):
        command._run_main(parsed_args, None)

    yes_no_mock.assert_called_once_with(
        '\nConfigure AWS Knowledge MCP server connection? [Y/n]: '
    )
