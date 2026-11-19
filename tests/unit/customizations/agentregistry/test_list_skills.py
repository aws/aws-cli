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
"""list-skills: the listing, its output and the installed check."""

import argparse
import contextlib
import io
import json
import os
from unittest.mock import Mock, patch

import botocore.loaders
import jmespath
import pytest
from botocore.awsrequest import AWSResponse
from botocore.endpoint import Endpoint
from botocore.exceptions import ClientError, EndpointConnectionError

from awscli.customizations.agentregistry import (
    cache,
    constants,
    dataplane,
    install_skill,
    list_skills,
    providers,
    utils,
)
from awscli.customizations.agentregistry.install_skill import (
    PROVENANCE_MARKER,
)
from awscli.customizations.agentregistry.list_skills import (
    ListSkillsCommand,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    UNIVERSAL_ROW_ID,
    AgentConfig,
)
from awscli.customizations.agenttoolkit.utils import AGENT_ARG
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agentregistry.utils import (
    make_agents,
    make_skill_md,
)

ENDPOINT = 'https://agent-registry.us-west-2.api.aws'
REGISTRY_ID = 'abcDEF123456'
REGISTRY_ARN = (
    f'arn:aws:agent-registry:us-west-2:123456789012:registry/{REGISTRY_ID}'
)


def _record(name, record_id, **fields):
    """A record summary as ListDiscoverableRegistryRecords returns it."""
    record = {
        'registryArn': REGISTRY_ARN,
        'recordArn': f'{REGISTRY_ARN}/record/{record_id}',
        'recordId': record_id,
        'name': name,
        'recordType': 'SKILL',
        'recordVersion': '1.0.0',
        'status': 'APPROVED',
        'descriptorTypes': ['SKILL'],
    }
    record.update(fields)
    return {key: value for key, value in record.items() if value is not None}


PDF = _record('pdf-extract', 'recPDF000001', description='Extract PDFs')
CSV = _record('csv-tools', 'recCSV000001', description='CSV helpers')


class _Output:
    """An OutputStreamFactory that writes into a buffer."""

    def __init__(self):
        self.buffer = io.StringIO()

    @contextlib.contextmanager
    def get_output_stream(self):
        yield self.buffer


@pytest.fixture
def auth_env(monkeypatch):
    # Set before deleting so monkeypatch restores the original absence even
    # though the command writes these variables itself.
    for name in (constants.TOKEN_ENV_VAR, 'AWS_AUTH_SCHEME_PREFERENCE'):
        monkeypatch.setenv(name, 'placeholder')
        monkeypatch.delenv(name)


@pytest.fixture(autouse=True)
def endpoint():
    """The data plane endpoint, without building a client from the mock."""
    with patch.object(
        dataplane, 'resolve_data_plane_endpoint', return_value=ENDPOINT
    ) as resolve:
        yield resolve


def _command(*pages, agent_configs=None):
    pages = pages or ([PDF, CSV],)
    client = Mock()
    paginator = client.get_paginator.return_value
    paginator.paginate.return_value = iter(
        [{'registryRecords': list(page)} for page in pages]
    )
    session = Mock()
    session.create_client.return_value = client
    session.get_config_variable.side_effect = {
        'region': 'us-west-2',
        'output': 'json',
    }.get
    output = _Output()
    command = ListSkillsCommand(
        session,
        agent_configs=[] if agent_configs is None else agent_configs,
        output_stream_factory=output,
    )
    command.output = output
    return command, client


def _run(
    command,
    registry_id=REGISTRY_ID,
    agent=None,
    authorizer=None,
    client_id=None,
    no_browser=False,
    output='json',
    query=None,
):
    args = argparse.Namespace(
        registry_id=registry_id,
        agent=agent,
        authorizer=authorizer,
        client_id=client_id,
        no_browser=no_browser,
    )
    globals_ = argparse.Namespace(
        region='us-west-2',
        endpoint_url=None,
        verify_ssl=None,
        ca_bundle=None,
        output=output,
        query=None if query is None else jmespath.compile(query),
        color='off',
    )
    return command._run_main(args, globals_)


def _skills(command, **kwargs):
    assert _run(command, **kwargs) == 0
    return json.loads(command.output.buffer.getvalue())['skills']


# --- The listing ------------------------------------------------------------


def test_every_page_of_skill_records_is_listed():
    command, client = _command([PDF], [CSV])
    skills = _skills(command, registry_id=REGISTRY_ARN)
    assert [skill['name'] for skill in skills] == ['pdf-extract', 'csv-tools']
    client.get_paginator.assert_called_once_with(
        'list_discoverable_registry_records'
    )
    # The registry as given, only skill records, and the most records the
    # service returns in a page.
    client.get_paginator.return_value.paginate.assert_called_once_with(
        registryId=REGISTRY_ARN,
        filters=[{'name': 'recordType', 'values': ['SKILL']}],
        PaginationConfig={'PageSize': 100},
    )


def test_each_skill_has_the_records_own_fields():
    record = _record(
        'pdf-extract',
        'recPDF000001',
        description='Extract PDFs',
        recordVersion='2.1.0',
        displayName='PDF extract',
    )
    command, _ = _command([record])
    assert _skills(command) == [
        {
            'name': 'pdf-extract',
            'recordId': 'recPDF000001',
            'description': 'Extract PDFs',
            'recordVersion': '2.1.0',
            'installedFor': [],
        }
    ]


def test_a_field_the_record_lacks_is_left_out():
    command, _ = _command([_record('pdf-extract', 'recPDF000001')])
    [skill] = _skills(command)
    assert 'description' not in skill
    assert skill['recordVersion'] == '1.0.0'


def test_records_of_other_types_are_not_listed():
    mcp = _record('weather', 'recMCP000001', recordType='MCP')
    command, _ = _command([mcp, PDF, 'not a record'])
    assert [skill['name'] for skill in _skills(command)] == ['pdf-extract']


def test_a_registry_without_skills_lists_none():
    command, _ = _command([])
    assert _skills(command) == []


def test_unknown_agent_is_refused_before_any_call(tmp_path):
    configs, _ = make_agents(str(tmp_path / 'home'))
    command, client = _command(agent_configs=configs)
    with pytest.raises(ParamValidationError, match='Invalid agent "vim"'):
        _run(command, agent='vim')
    command._session.create_client.assert_not_called()


@pytest.mark.parametrize('registry_id', ['reg', '../../evil', 'a' * 17])
def test_malformed_registry_id_is_refused_before_any_call(registry_id):
    command, client = _command()
    with pytest.raises(AgentRegistryJWTError, match='registry identifier'):
        _run(command, registry_id=registry_id)
    command._session.create_client.assert_not_called()


# --- Output -----------------------------------------------------------------


def test_query_is_applied_by_the_cli_formatter():
    command, _ = _command()
    assert _run(command, query='skills[].name') == 0
    assert json.loads(command.output.buffer.getvalue()) == [
        'pdf-extract',
        'csv-tools',
    ]


def test_text_output_is_the_cli_formatters():
    command, _ = _command([PDF])
    assert _run(command, output='text') == 0
    assert command.output.buffer.getvalue() == (
        'SKILLS\tExtract PDFs\tpdf-extract\trecPDF000001\t1.0.0\n'
    )


def test_table_output_is_the_cli_formatters():
    command, _ = _command([PDF])
    assert _run(command, output='table') == 0
    table = command.output.buffer.getvalue()
    assert 'list-skills' in table
    assert 'pdf-extract' in table and 'Extract PDFs' in table


_HOSTILE = 'Extract\x1b[2J PDFs\nSKILLS\tfake\x07 \u202eevil'


@pytest.mark.parametrize('output', ['text', 'table'])
def test_displayed_output_replaces_control_characters(output):
    record = _record('pdf-extract', 'recPDF000001', description=_HOSTILE)
    command, _ = _command([record])
    assert _run(command, output=output) == 0
    shown = command.output.buffer.getvalue()
    for control in ('\x1b', '\x07', '\u202e'):
        assert control not in shown
    if output == 'text':
        # One line per skill: the description added no row or column.
        assert shown == (
            'SKILLS\tExtract [2J PDFs SKILLS fake   evil\tpdf-extract\t'
            'recPDF000001\t1.0.0\n'
        )


@pytest.mark.parametrize('output', ['json', 'yaml'])
def test_parsed_output_keeps_the_values_as_returned(output):
    record = _record('pdf-extract', 'recPDF000001', description=_HOSTILE)
    command, _ = _command([record])
    assert _run(command, output=output) == 0
    shown = command.output.buffer.getvalue()
    assert '\x1b' not in shown
    if output == 'json':
        assert json.loads(shown)['skills'][0]['description'] == _HOSTILE


# --- Installed for ----------------------------------------------------------


# Each agent as installedFor lists it: the id --agent takes, and its name.
CLAUDE = {'id': 'claude-code', 'name': 'Claude Code'}
CODEX = {'id': 'codex', 'name': 'Codex'}


def _install(folder, name='pdf-extract', skill_md=True, **source):
    """A skill as install-skill leaves it, from PDF unless told otherwise."""
    skill = os.path.join(folder, name)
    os.makedirs(skill)
    if skill_md:
        with open(os.path.join(skill, 'SKILL.md'), 'w') as f:
            f.write('skill')
    marker = {
        'registryId': REGISTRY_ID,
        'recordId': 'recPDF000001',
        'endpoint': ENDPOINT,
        'sha256': '0' * 64,
    }
    marker.update(source)
    if marker.get('registryId') is not None:
        with open(os.path.join(skill, PROVENANCE_MARKER), 'w') as f:
            json.dump(marker, f)
    return skill


def test_skill_installed_from_this_registry_is_installed_for_its_agents(
    tmp_path,
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    _install(folders['codex'])
    command, _ = _command([PDF, CSV], agent_configs=configs)
    pdf, csv = _skills(command)
    # Codex and Gemini CLI share a folder, which is named for the first.
    assert pdf['installedFor'] == [CLAUDE, CODEX]
    assert csv['installedFor'] == []


def test_an_outdated_copy_still_counts_as_installed(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], sha256='f' * 64)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == [CLAUDE]


@pytest.mark.parametrize(
    'source',
    [
        {'registryId': 'xyzXYZ9876543210'},
        {'recordId': 'recOTHER0001'},
        {'endpoint': 'https://agent-registry.us-east-1.api.aws'},
    ],
    ids=['registry', 'record', 'endpoint'],
)
def test_a_copy_from_another_source_is_not_installed(tmp_path, source):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], **source)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


def test_the_endpoint_is_compared_as_install_skill_compares_it(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(
        folders['claude-code'],
        endpoint='https://AGENT-REGISTRY.us-west-2.api.aws:443/',
    )
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == [CLAUDE]


def test_a_registry_arn_matches_the_bare_id_in_the_marker(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    command, _ = _command([PDF], agent_configs=configs)
    skills = _skills(command, registry_id=REGISTRY_ARN)
    assert skills[0]['installedFor'] == [CLAUDE]


@pytest.mark.parametrize(
    'marker',
    ['missing', 'unreadable', 'no SKILL.md'],
)
def test_a_folder_install_skill_did_not_install_is_not_installed(
    tmp_path, marker
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    if marker == 'missing':
        _install(folders['claude-code'], registryId=None)
    elif marker == 'unreadable':
        skill = _install(folders['claude-code'])
        with open(os.path.join(skill, PROVENANCE_MARKER), 'w') as f:
            f.write('{not json')
    else:
        _install(folders['claude-code'], skill_md=False)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


@pytest.mark.parametrize('link', ['pdf-extract', 'alias'])
def test_installed_for_ignores_symlinked_folders(tmp_path, link):
    configs, folders = make_agents(str(tmp_path / 'home'))
    elsewhere = _install(str(tmp_path / 'elsewhere'))
    os.makedirs(folders['claude-code'])
    os.symlink(elsewhere, os.path.join(folders['claude-code'], link))
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


@pytest.mark.parametrize('content', ['skillMd', 'package', 'zipV2'])
def test_installed_for_counts_any_kind_of_content(tmp_path, content):
    # Also one a newer AWS CLI installed.
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], content=content)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == [CLAUDE]


@pytest.mark.parametrize('content', [7, None])
def test_installed_for_ignores_a_marker_with_non_text_content(
    tmp_path, content
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], content=content)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


def test_agent_limits_the_check_to_that_agent(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    _install(folders['codex'])
    command, _ = _command([PDF], agent_configs=configs)
    skills = _skills(command, agent='codex')
    assert skills[0]['installedFor'] == [CODEX]


@pytest.mark.parametrize('agent', [None, 'cursor'])
def test_no_detected_agent_lists_every_skill_as_installed_nowhere(
    tmp_path, agent
):
    configs, _ = make_agents(str(tmp_path / 'home'), detected=())
    command, _ = _command([PDF, CSV], agent_configs=configs)
    skills = _skills(command, agent=agent)
    assert [skill['installedFor'] for skill in skills] == [[], []]


@pytest.mark.parametrize(
    'name',
    [
        'a/../../x',
        'skills/pdf',
        '..',
        '.hidden',
        'x' * 256,
        'Pdf-extract',
        'pdf_extract',
        'csv-tools',
        '',
        7,
        None,
    ],
)
def test_record_name_does_not_decide_where_to_look(tmp_path, name):
    # The copy of recPDF000001 is found by its marker, whatever the
    # record's name, even one install-skill refuses or none at all.
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    record = _record(None, 'recPDF000001')
    if name is not None:
        record['name'] = name
    command, _ = _command([record, CSV], agent_configs=configs)
    pdf, csv = _skills(command)
    assert pdf.get('name') == name
    assert pdf['installedFor'] == [CLAUDE]
    assert csv['installedFor'] == []


def test_installed_for_finds_a_skill_under_its_skill_md_name(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], name='pdf-processing-skill')
    record = _record('pdf_processing_skill', 'recPDF000001')
    command, _ = _command([record], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == [CLAUDE]


@pytest.mark.parametrize(
    'name', ['.pdf-extract.staging-k2j4', '.pdf-extract.old-0a1b2c3d']
)
def test_installed_for_ignores_staging_and_backup_folders(tmp_path, name):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], name=name)
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


def test_installed_for_ignores_other_registry_record_or_endpoint(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    folder = folders['claude-code']
    _install(folder, name='pdf-extract', registryId='xyzXYZ9876543210')
    _install(folder, name='pdf_extract', recordId='recOTHER0001')
    _install(
        folder,
        name='Pdf-Extract-2',
        endpoint='https://agent-registry.us-east-1.api.aws',
    )
    command, _ = _command([PDF], agent_configs=configs)
    assert _skills(command)[0]['installedFor'] == []


def test_installed_for_reads_each_marker_once(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    _install(folders['claude-code'], name='csv_tools', recordId='recCSV000001')
    _install(folders['codex'], name='other', recordId='recOTHER0001')
    records = [PDF, CSV] + [
        _record(f'skill-{n}', f'recSKILL{n:04}') for n in range(5)
    ]
    command, _ = _command(records, agent_configs=configs)
    with patch.object(
        install_skill, 'read_provenance', wraps=install_skill.read_provenance
    ) as read:
        skills = _skills(command)
    assert read.call_count == 3
    assert [skill['installedFor'] for skill in skills[:2]] == [
        [CLAUDE],
        [CLAUDE],
    ]
    assert all(skill['installedFor'] == [] for skill in skills[2:])


def test_installed_for_missing_skills_folder_is_empty(tmp_path):
    # Detected agents whose skills folders do not exist yet.
    configs, folders = make_agents(str(tmp_path / 'home'))
    assert not any(os.path.exists(folder) for folder in folders.values())
    command, _ = _command([PDF, CSV], agent_configs=configs)
    skills = _skills(command)
    assert [skill['installedFor'] for skill in skills] == [[], []]


def _installed_for_claude_and_codex(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    _install(folders['codex'])
    command, _ = _command([PDF], agent_configs=configs)
    return command


def test_text_output_lists_each_agent_on_its_own_line(tmp_path):
    command = _installed_for_claude_and_codex(tmp_path)
    assert _run(command, output='text') == 0
    assert command.output.buffer.getvalue() == (
        'SKILLS\tExtract PDFs\tpdf-extract\trecPDF000001\t1.0.0\n'
        'INSTALLEDFOR\tclaude-code\tClaude Code\n'
        'INSTALLEDFOR\tcodex\tCodex\n'
    )


def test_table_output_lists_each_agent_with_its_id(tmp_path):
    command = _installed_for_claude_and_codex(tmp_path)
    assert _run(command, output='table') == 0
    rows = [
        [cell.strip() for cell in line.strip('|').split('|')]
        for line in command.output.buffer.getvalue().splitlines()
    ]
    assert ['id', 'name'] in rows
    assert ['claude-code', 'Claude Code'] in rows
    assert ['codex', 'Codex'] in rows


def test_agent_ids_can_be_queried_for_agent(tmp_path):
    command = _installed_for_claude_and_codex(tmp_path)
    assert _run(command, query='skills[0].installedFor[].id') == 0
    assert json.loads(command.output.buffer.getvalue()) == [
        'claude-code',
        'codex',
    ]


@pytest.mark.parametrize('name', ['-pdf', '_pdf', 'pdf extract', 'x' * 65])
def test_a_folder_outside_the_folder_name_rule_is_not_looked_at(
    tmp_path, name
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'], name=name)
    command, _ = _command(
        [_record(name, 'recPDF000001')], agent_configs=configs
    )
    with patch.object(install_skill, 'read_provenance') as read:
        assert _skills(command)[0]['installedFor'] == []
    read.assert_not_called()


def _with_universal_row(home, configs):
    """``configs`` and agent-toolkit's row for the shared folder."""
    os.makedirs(os.path.join(home, '.agents'), exist_ok=True)
    universal = AgentConfig(
        id=UNIVERSAL_ROW_ID,
        display_name='Universal (Codex, Gemini CLI)',
        detection_path=os.path.join(home, '.agents'),
    )
    return [*configs, universal]


def test_the_shared_folder_is_listed_with_an_id_agent_accepts(tmp_path):
    home = str(tmp_path / 'home')
    configs, folders = make_agents(home)
    configs = _with_universal_row(home, configs)
    _install(folders['claude-code'])
    _install(folders['codex'])
    command, _ = _command([PDF], agent_configs=configs)
    universal = {
        'id': UNIVERSAL_ROW_ID,
        'name': 'Universal (Codex, Gemini CLI)',
    }
    # As agent-toolkit orders them: the shared folder first.
    assert _skills(command)[0]['installedFor'] == [universal, CLAUDE]
    # Each id is one --agent accepts, and names the same folder.
    for agent in (universal, CLAUDE):
        command, _ = _command([PDF], agent_configs=configs)
        skills = _skills(command, agent=agent['id'])
        assert skills[0]['installedFor'] == [agent]


def test_every_id_listed_is_a_valid_agent_value():
    ids = {config.id for config in AGENT_CONFIGS}
    assert UNIVERSAL_ROW_ID in ids
    for agent_id in ids:
        assert agent_id in AGENT_ARG['help_text']


def test_agent_argument_is_agent_toolkits():
    [argument] = [
        arg for arg in ListSkillsCommand.ARG_TABLE if arg['name'] == 'agent'
    ]
    assert argument == dict(AGENT_ARG, help_text=argument['help_text'])
    assert argument['help_text'].startswith(AGENT_ARG['help_text'])
    assert 'checked for installed skills' in argument['help_text']
    assert 'target-directory' not in argument['help_text']
    assert ListSkillsCommand(Mock())._agent_configs is AGENT_CONFIGS


# --- Authorization ----------------------------------------------------------


# --- SKILL.md names ---------------------------------------------------------


_PRESIGNED = (
    'https://bucket.s3.us-west-2.amazonaws.com/pkg.zip?X-Amz-Credential='
    'ASIAEXAMPLE&X-Amz-Signature=deadbeef'
)


def _with_text(record, text):
    """``record`` as BatchGet returns it, holding ``text`` as SKILL.md."""
    return dict(
        record,
        descriptors={
            'agentSkillsDefinition': {
                'additionalData': {'skillMd': {'data': text}}
            }
        },
    )


def _batch_get(client, *records, errors=()):
    client.batch_get_discoverable_registry_record.return_value = {
        'registryRecords': list(records),
        'errors': list(errors),
    }
    return client.batch_get_discoverable_registry_record


def test_skill_name_is_read_for_package_and_inline_records(capsys):
    command, client = _command([PDF, CSV])
    batch_get = _batch_get(
        client,
        # A package record carries its SKILL.md text too.
        dict(
            _with_text(PDF, make_skill_md('pdf-extract-skill')),
            artifact={'downloadUrl': _PRESIGNED, 'sha256': '0' * 64},
        ),
        _with_text(CSV, make_skill_md('CSV_Tools')),
    )
    pdf, csv = _skills(command, registry_id=REGISTRY_ARN)
    assert list(pdf) == [
        'name',
        'skillName',
        'recordId',
        'description',
        'recordVersion',
        'installedFor',
    ]
    assert (pdf['name'], pdf['skillName']) == (
        'pdf-extract',
        'pdf-extract-skill',
    )
    assert (csv['name'], csv['skillName']) == ('csv-tools', 'CSV_Tools')
    # The same registry as the listing, as it was given.
    batch_get.assert_called_once_with(
        entries=[
            {
                'registryId': REGISTRY_ARN,
                'recordIds': ['recPDF000001', 'recCSV000001'],
            }
        ]
    )
    assert capsys.readouterr().err == ''


@pytest.mark.parametrize(
    'returned',
    [
        PDF,
        dict(PDF, descriptors={}),
        _with_text(PDF, ''),
        _with_text(PDF, '  \n'),
        _with_text(PDF, None),
        _with_text(PDF, 7),
        _with_text(PDF, 'no frontmatter'),
        _with_text(PDF, '﻿' + make_skill_md()),
        _with_text(PDF, '\n' + make_skill_md()),
        _with_text(PDF, '---\nname: [x\n---\n'),
        _with_text(PDF, make_skill_md('../evil')),
        _with_text(PDF, make_skill_md('a b')),
        _with_text(PDF, make_skill_md(body='x' * 102_400)),
        _with_text(PDF, make_skill_md(body='\ud800')),
        _with_text(PDF, make_skill_md(body='\x00')),
        # Another record's text is not this one's.
        _with_text(CSV, make_skill_md()),
        'not a record',
    ],
)
def test_skill_name_is_left_out_without_usable_text(capsys, returned):
    command, client = _command([PDF])
    _batch_get(client, returned)
    [pdf] = _skills(command)
    assert 'skillName' not in pdf
    assert capsys.readouterr().err == ''


@pytest.mark.parametrize(
    'response', [None, 'text', {}, {'registryRecords': 'x'}, Mock()]
)
def test_an_odd_batch_get_response_gives_no_names(response):
    command, client = _command([PDF])
    client.batch_get_discoverable_registry_record.return_value = response
    [pdf] = _skills(command)
    assert 'skillName' not in pdf


def _many(count):
    return [_record(f'skill-{n}', f'rec{n:09}') for n in range(count)]


@pytest.mark.parametrize('count,calls', [(1, 1), (100, 1), (101, 2), (205, 3)])
def test_skill_names_are_read_100_records_a_call(count, calls):
    records = _many(count)
    command, client = _command(records[: count // 2], records[count // 2 :])

    def batch_get(entries):
        [entry] = entries
        assert entry['registryId'] == REGISTRY_ID
        assert 1 <= len(entry['recordIds']) <= 100
        return {
            'registryRecords': [
                _with_text(
                    _record(None, record_id),
                    make_skill_md(f'name-{record_id.lower()}'),
                )
                for record_id in entry['recordIds']
            ]
        }

    client.batch_get_discoverable_registry_record.side_effect = batch_get
    skills = _skills(command)
    assert client.batch_get_discoverable_registry_record.call_count == calls
    asked = [
        record_id
        for call in client.batch_get_discoverable_registry_record.mock_calls
        for record_id in call.kwargs['entries'][0]['recordIds']
    ]
    assert asked == [record['recordId'] for record in records]
    assert [skill['skillName'] for skill in skills] == [
        f'name-{record["recordId"].lower()}' for record in records
    ]


def test_no_skills_need_no_batch_get():
    command, client = _command([])
    assert _skills(command) == []
    client.batch_get_discoverable_registry_record.assert_not_called()


def test_each_record_is_asked_for_once():
    command, client = _command([PDF], [PDF, _record('x', None)])
    batch_get = _batch_get(client)
    _skills(command)
    assert batch_get.call_args.kwargs['entries'][0]['recordIds'] == [
        'recPDF000001'
    ]


def _client_error(code):
    return ClientError(
        {'Error': {'Code': code, 'Message': f'see {_PRESIGNED}'}},
        'BatchGetDiscoverableRegistryRecord',
    )


@pytest.mark.parametrize(
    'error,reason',
    [
        (_client_error('AccessDeniedException'), 'AccessDeniedException'),
        (_client_error('ThrottlingException'), 'ThrottlingException'),
        (
            EndpointConnectionError(endpoint_url=_PRESIGNED),
            'EndpointConnectionError',
        ),
        (
            AgentRegistryJWTError(f'failed at {_PRESIGNED}'),
            'AgentRegistryJWTError',
        ),
    ],
)
def test_batch_get_error_degrades_with_one_warning(capsys, error, reason):
    records = _many(205)
    command, client = _command(records)
    answers = iter([{'registryRecords': []}, error, error])

    def batch_get(entries):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    client.batch_get_discoverable_registry_record.side_effect = batch_get
    skills = _skills(command)
    assert len(skills) == 205
    assert all('skillName' not in skill for skill in skills)
    # No call after the first that fails, and the listing still goes out.
    assert client.batch_get_discoverable_registry_record.call_count == 2
    err = capsys.readouterr().err
    assert err == (
        'Warning: could not read the SKILL.md names of the skills '
        f'({reason}), so skillName is left out.\n'
    )


def test_names_read_before_a_failure_are_left_out_too():
    records = _many(150)
    command, client = _command(records)
    first = {
        'registryRecords': [
            _with_text(_record(None, record['recordId']), make_skill_md())
            for record in records[:100]
        ]
    }
    client.batch_get_discoverable_registry_record.side_effect = [
        first,
        _client_error('ThrottlingException'),
    ]
    assert all('skillName' not in skill for skill in _skills(command))


@pytest.mark.parametrize('output', ['json', 'yaml', 'text', 'table'])
def test_batch_get_package_details_and_text_are_never_output(output):
    secret = 'SECRET-SKILL-TEXT-1234'
    command, client = _command([PDF])
    _batch_get(
        client,
        dict(
            _with_text(
                PDF, f'---\nname: pdf-extract\ndescription: {secret}\n---\n'
            ),
            artifact={'downloadUrl': _PRESIGNED, 'sha256': 'f' * 64},
        ),
    )
    assert _run(command, output=output) == 0
    out = command.output.buffer.getvalue()
    for leaked in (secret, 'X-Amz', 'amazonaws', 'ASIAEXAMPLE', 'f' * 64):
        assert leaked not in out
    assert 'pdf-extract' in out


def test_query_on_name_is_unchanged():
    command, client = _command([PDF, CSV])
    _batch_get(client, _with_text(PDF, make_skill_md('other-name')))
    assert _run(command, query='skills[].name') == 0
    assert json.loads(command.output.buffer.getvalue()) == [
        'pdf-extract',
        'csv-tools',
    ]


def test_skill_name_can_be_queried():
    command, client = _command([PDF, CSV])
    _batch_get(client, _with_text(PDF, make_skill_md('other-name')))
    assert _run(command, query='skills[].[name, skillName]') == 0
    assert json.loads(command.output.buffer.getvalue()) == [
        ['pdf-extract', 'other-name'],
        ['csv-tools', None],
    ]


def test_text_output_adds_the_skill_name():
    command, client = _command([PDF])
    _batch_get(client, _with_text(PDF, make_skill_md('pdf-extract-skill')))
    assert _run(command, output='text') == 0
    assert command.output.buffer.getvalue() == (
        'SKILLS\tExtract PDFs\tpdf-extract\trecPDF000001\t1.0.0\t'
        'pdf-extract-skill\n'
    )


def test_displayed_skill_name_has_no_control_characters():
    # A folder name never holds one, so nothing is replaced in practice.
    command, client = _command([PDF])
    _batch_get(client, _with_text(PDF, make_skill_md('Pdf_Extract')))
    assert _run(command, output='table') == 0
    assert 'Pdf_Extract' in command.output.buffer.getvalue()


def _token_at_list_call(client):
    """Record the bearer token in the environment when the list starts."""
    seen = []
    paginator = client.get_paginator.return_value
    pages = paginator.paginate.return_value

    def paginate(**kwargs):
        seen.append(os.environ.get(constants.TOKEN_ENV_VAR))
        return pages

    paginator.paginate.side_effect = paginate
    return seen


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
def test_sigv4_is_the_default_and_never_signs_in(auth_env, authorizer):
    command, client = _command()
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
    ):
        _skills(command, authorizer=authorizer, client_id='ignored')
    load.assert_not_called()
    sign_in.assert_not_called()
    assert constants.TOKEN_ENV_VAR not in os.environ
    assert command._session.create_client.call_args.kwargs['verify'] is None


def test_jwt_uses_the_cached_sign_in(auth_env, endpoint):
    command, client = _command()
    seen = _token_at_list_call(client)

    def batch_get(entries):
        seen.append(os.environ.get(constants.TOKEN_ENV_VAR))
        return {'registryRecords': []}

    client.batch_get_discoverable_registry_record.side_effect = batch_get
    with (
        patch.object(cache, 'load_token', return_value='tok') as load,
        patch.object(providers, 'sign_in') as sign_in,
    ):
        _skills(command, authorizer='JWT', registry_id=REGISTRY_ARN)
    sign_in.assert_not_called()
    load.assert_called_once()
    assert load.call_args.args == (ENDPOINT, REGISTRY_ID)
    # The list, then the BatchGet, with one client and token.
    assert seen == ['tok', 'tok']
    command._session.create_client.assert_called_once()
    assert 'AWS_AUTH_SCHEME_PREFERENCE' not in os.environ
    config = command._session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'
    assert endpoint.call_args.kwargs == {'https_only': True}


@pytest.mark.parametrize('no_browser', [False, True])
def test_jwt_signs_in_on_a_cache_miss(auth_env, no_browser):
    command, client = _command()
    seen = _token_at_list_call(client)
    with (
        patch.object(cache, 'load_token', return_value=None),
        patch.object(
            providers, 'sign_in', return_value='signed-in-token'
        ) as sign_in,
    ):
        _skills(
            command,
            authorizer='JWT',
            client_id='my-client',
            no_browser=no_browser,
        )
    sign_in.assert_called_once_with(
        command._session,
        ENDPOINT,
        REGISTRY_ID,
        client_id='my-client',
        ca_bundle=None,
        open_browser=not no_browser,
    )
    assert seen == ['signed-in-token']


def test_jwt_sends_a_preset_token_as_is(auth_env, monkeypatch, capsys):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-elsewhere')
    command, client = _command()
    seen = _token_at_list_call(client)
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
    ):
        _skills(command, authorizer='JWT')
    load.assert_not_called()
    sign_in.assert_not_called()
    assert seen == ['minted-elsewhere']
    assert (
        'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
        'sign-in, --client-id and --no-browser are not used.'
    ) in capsys.readouterr().err


def test_jwt_refuses_no_verify_ssl_before_the_call(auth_env):
    command, client = _command()
    with patch.object(providers, 'sign_in') as sign_in:
        with pytest.raises(AgentRegistryJWTError, match='--ca-bundle'):
            command._run_main(
                argparse.Namespace(
                    registry_id=REGISTRY_ID,
                    agent=None,
                    authorizer='JWT',
                    client_id=None,
                    no_browser=False,
                ),
                argparse.Namespace(
                    region='us-west-2',
                    endpoint_url=None,
                    verify_ssl=False,
                    ca_bundle=None,
                    output='json',
                    query=None,
                ),
            )
    sign_in.assert_not_called()
    client.get_paginator.assert_not_called()


def test_jwt_remembers_the_sign_in_for_the_401_hint(
    auth_env, signed_in_registry
):
    command, _ = _command()
    with patch.object(cache, 'load_token', return_value='tok'):
        _skills(command, authorizer='JWT', registry_id=REGISTRY_ARN)
    assert signed_in_registry['registry_id'] == REGISTRY_ID


# --- Help -------------------------------------------------------------------


def test_arguments_and_description():
    names = [arg['name'] for arg in ListSkillsCommand.ARG_TABLE]
    assert names == [
        'registry-id',
        'agent',
        'authorizer',
        'client-id',
        'no-browser',
    ]
    shared = ListSkillsCommand.ARG_TABLE[2:]
    assert shared == dataplane.SIGN_IN_ARGUMENTS
    description = ListSkillsCommand.DESCRIPTION
    assert description.endswith(dataplane.SIGN_IN_DESCRIPTION)
    assert '``install-skill``' in description
    assert '``installedFor``' in description
    assert (
        'Each agent in ``installedFor`` has an ``id``, the value to pass as '
        '``--agent``, and a display ``name``.'
    ) in description
    assert '``~/.agents/skills`` as ``universal``' in description
    assert PROVENANCE_MARKER in description
    assert (
        "``skillName`` is the ``name`` in the frontmatter of the record's "
        "``SKILL.md``, which ``install-skill`` names the skill's folder "
        "after; ``name`` is the record's own name, which can differ."
    ) in description
    assert '``BatchGetDiscoverableRegistryRecord``, up to 100' in description
    assert (
        'The copy is found by that marker, whatever the name of its folder.'
    ) in description
    assert 'refuses' not in description


# --- On a real command line -------------------------------------------------


class _Body:
    def __init__(self, document):
        self._document = document

    def stream(self):
        yield json.dumps(self._document).encode()


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """An isolated environment with an empty config file and credentials."""
    path = tmp_path / 'config'
    path.write_text('')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(path))
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'creds'))
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDEXAMPLE')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-west-2')
    for name in list(os.environ):
        # AWS_REGION would win over AWS_DEFAULT_REGION.
        if name.startswith('AWS_ENDPOINT_URL') or name in (
            'AWS_REGION',
            'AWS_PROFILE',
            'AWS_DEFAULT_PROFILE',
            'AWS_CA_BUNDLE',
            'AWS_DEFAULT_OUTPUT',
            'AWS_PAGER',
        ):
            monkeypatch.delenv(name)
    return path


def _driver():
    """A real CLI driver that loads only the models shipped with the CLI."""
    from awscli.clidriver import create_clidriver

    driver = create_clidriver()
    session = driver.session
    data_path = session.get_config_variable('data_path').split(os.pathsep)
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[
                *data_path,
                botocore.loaders.Loader.BUILTIN_DATA_PATH,
            ],
            include_default_search_paths=False,
        ),
    )
    return driver


def test_real_command_line_reads_every_page(
    config_file, auth_env, tmp_path, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _install(folders['claude-code'])
    pages = [
        {'registryRecords': [PDF], 'nextToken': 'page-2'},
        {'registryRecords': [CSV]},
    ]
    batch = {
        'registryRecords': [
            _with_text(PDF, make_skill_md('pdf-extract-skill')),
            dict(
                CSV,
                artifact={'downloadUrl': _PRESIGNED, 'sha256': '0' * 64},
            ),
        ],
        'errors': [],
    }
    sent = []

    def send(request):
        sent.append((request.url, json.loads(request.body)))
        if request.url.endswith('/discoverable-records-batch'):
            return AWSResponse(request.url, 200, {}, _Body(batch))
        return AWSResponse(request.url, 200, {}, _Body(pages[len(sent) - 1]))

    with (
        patch.object(list_skills, 'AGENT_CONFIGS', configs),
        patch.object(Endpoint, '_send', side_effect=send),
    ):
        rc = _driver().main(
            [
                'agent-registry',
                'list-skills',
                '--registry-id',
                REGISTRY_ID,
                '--query',
                "skills[].[name, join(',', installedFor[].id), skillName]",
                '--output',
                'text',
            ]
        )
    assert rc == 0
    url = f'{ENDPOINT}/registries/{REGISTRY_ID}/discoverable-records-list'
    skill_filter = [{'name': 'recordType', 'values': ['SKILL']}]
    # Each page asks for the model's maximum, 100 records.
    listing = {'filters': skill_filter, 'maxResults': 100}
    assert sent == [
        (url, listing),
        (url, {**listing, 'nextToken': 'page-2'}),
        (
            f'{ENDPOINT}/discoverable-records-batch',
            {
                'entries': [
                    {
                        'registryId': REGISTRY_ID,
                        'recordIds': ['recPDF000001', 'recCSV000001'],
                    }
                ]
            },
        ),
    ]
    out, err = capsys.readouterr()
    assert out == (
        'pdf-extract\tclaude-code\tpdf-extract-skill\ncsv-tools\t\tNone\n'
    )
    assert 'X-Amz' not in out + err


@pytest.mark.parametrize(
    'option,value',
    [
        ('--endpoint-url', 'https://registry.example/?x=1'),
        ('AWS_ENDPOINT_URL_AGENT_REGISTRY', 'https://registry.example?x=1'),
        ('endpoint_url', 'https://registry.example?x=1'),
    ],
)
def test_real_command_line_refuses_an_endpoint_with_a_query(
    config_file, auth_env, monkeypatch, capsys, endpoint, option, value
):
    # The real resolution.
    endpoint.side_effect = utils.resolve_data_plane_endpoint
    arguments = [
        'agent-registry',
        'list-skills',
        '--registry-id',
        REGISTRY_ID,
    ]
    if option == '--endpoint-url':
        arguments += [option, value]
    elif option == 'endpoint_url':
        config_file.write_text(f'[default]\nendpoint_url = {value}\n')
    else:
        monkeypatch.setenv(option, value)
    with patch.object(
        Endpoint, '_send', side_effect=AssertionError('sent')
    ) as send:
        rc = _driver().main(arguments)
    assert rc != 0
    send.assert_not_called()
    err = capsys.readouterr().err
    assert (
        'Refusing registry endpoint https://registry.example: it has a ' in err
    )
    setting = (
        '--endpoint-url'
        if option == '--endpoint-url'
        else (
            'AWS_ENDPOINT_URL_AGENT_REGISTRY, AWS_ENDPOINT_URL or endpoint_url'
        )
    )
    assert f'from {setting}' in err
