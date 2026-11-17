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
from io import StringIO

import pytest

from awscli.customizations.agenttoolkit.list_installed_skills import (
    ListInstalledSkillsCommand,
)
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_parsed_globals,
    make_session,
    make_skill,
)


def _run_installed(monkeypatch, agent_configs, args=None):
    stream = StringIO()
    monkeypatch.setattr('sys.stdout', stream)
    cmd = ListInstalledSkillsCommand(
        make_session(), agent_configs=agent_configs
    )
    cmd(args=args or [], parsed_globals=make_parsed_globals())
    return json.loads(stream.getvalue())


def test_list_installed_no_agents(monkeypatch):
    result = _run_installed(monkeypatch, [])
    assert result['skills'] == []


def test_list_installed_no_skills(tmp_path, monkeypatch):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    result = _run_installed(monkeypatch, configs)
    assert result['skills'] == []


def test_list_installed_shows_skills(tmp_path, monkeypatch):
    make_skill(tmp_path, '.test-agent', 'aws-serverless')
    make_skill(tmp_path, '.test-agent', 'aws-databases')
    configs = [make_config(tmp_path)]
    result = _run_installed(monkeypatch, configs)
    skills = result['skills']
    assert len(skills) == 2
    assert skills[0]['agent'] == 'Test Agent'
    assert skills[0]['name'] == 'aws-databases'
    assert skills[1]['name'] == 'aws-serverless'


def test_list_installed_multiple_agents(tmp_path, monkeypatch):
    make_skill(tmp_path, '.agent-a', 'aws-serverless')
    make_skill(tmp_path, '.agent-b', 'aws-serverless')
    configs = [
        make_config(
            tmp_path,
            id='a',
            display_name='Agent A',
            detection_path=str(tmp_path / '.agent-a'),
        ),
        make_config(
            tmp_path,
            id='b',
            display_name='Agent B',
            detection_path=str(tmp_path / '.agent-b'),
        ),
    ]
    result = _run_installed(monkeypatch, configs)
    clients = [s['agent'] for s in result['skills']]
    assert 'Agent A' in clients
    assert 'Agent B' in clients


def test_list_installed_with_client_filter(tmp_path, monkeypatch):
    make_skill(tmp_path, '.agent-a', 'aws-serverless')
    make_skill(tmp_path, '.agent-b', 'aws-serverless')
    configs = [
        make_config(
            tmp_path,
            id='agent-a',
            display_name='Agent A',
            detection_path=str(tmp_path / '.agent-a'),
        ),
        make_config(
            tmp_path,
            id='agent-b',
            display_name='Agent B',
            detection_path=str(tmp_path / '.agent-b'),
        ),
    ]
    result = _run_installed(monkeypatch, configs, args=['--agent', 'agent-a'])
    clients = [s['agent'] for s in result['skills']]
    assert clients == ['Agent A']


def test_list_installed_invalid_agent(tmp_path, monkeypatch):
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='Invalid agent'):
        _run_installed(monkeypatch, configs, args=['--agent', 'nonexistent'])


def test_list_installed_universal_row_only_detected(tmp_path, monkeypatch):
    universal_base = tmp_path / '.agents'
    shared = universal_base / 'skills'
    skill_dir = shared / 'aws-cdk'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    (skill_dir / '.aws-skill-metadata').write_text(
        json.dumps({'version': 'v1'})
    )
    configs = [
        make_config(
            tmp_path,
            id='codex',
            display_name='Codex',
            detection_path=str(tmp_path / '.codex'),
            skills_path_override=str(shared),
        ),
        make_config(
            tmp_path,
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(universal_base),
        ),
    ]
    result = _run_installed(monkeypatch, configs)
    skills = result['skills']
    assert len(skills) == 1
    assert skills[0]['agent'] == 'Universal (Codex)'


def test_list_installed_universal_row_lists_alongside_override_agent(
    tmp_path, monkeypatch
):
    (tmp_path / '.codex').mkdir()
    universal_base = tmp_path / '.agents'
    shared = universal_base / 'skills'
    skill_dir = shared / 'aws-cdk'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    (skill_dir / '.aws-skill-metadata').write_text(
        json.dumps({'version': 'v1'})
    )
    configs = [
        make_config(
            tmp_path,
            id='codex',
            display_name='Codex',
            detection_path=str(tmp_path / '.codex'),
            skills_path_override=str(shared),
        ),
        make_config(
            tmp_path,
            id='universal',
            display_name='Universal (Codex)',
            detection_path=str(universal_base),
        ),
    ]
    result = _run_installed(monkeypatch, configs)
    skills = result['skills']
    assert len(skills) == 1
    assert skills[0]['agent'] == 'Universal (Codex)'
