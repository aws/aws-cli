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
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.check_updates import (
    CheckUpdatesCommand,
)
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_parsed_globals,
    make_session,
    make_skill,
)


def _run_check(monkeypatch, agent_configs, args=None, latest_versions=None):
    """Run check-updates and return (parsed output, latest version mock)."""
    if latest_versions is None:
        latest_versions = {}
    stream = StringIO()
    monkeypatch.setattr('sys.stdout', stream)

    mock_client = Mock()
    resolve_latest = Mock(
        side_effect=lambda _client, name: latest_versions[name]
    )
    with (
        patch(
            'awscli.customizations.agenttoolkit.check_updates.'
            'resolve_latest_version',
            resolve_latest,
        ),
        patch(
            'awscli.customizations.agenttoolkit.check_updates.create_client',
            return_value=mock_client,
        ) as create,
    ):
        cmd = CheckUpdatesCommand(make_session(), agent_configs=agent_configs)
        rc = cmd(args=args or [], parsed_globals=make_parsed_globals())
    assert rc == 0
    return json.loads(stream.getvalue()), resolve_latest, create


def test_check_updates_no_agents(monkeypatch):
    result, resolve_latest, create = _run_check(monkeypatch, [])
    assert result == {'skills': []}
    # Nothing installed means there is nothing to look up, so we should not
    # even build a client.
    assert create.call_count == 0
    assert resolve_latest.call_count == 0


def test_check_updates_no_skills_installed(tmp_path, monkeypatch):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    result, resolve_latest, create = _run_check(
        monkeypatch, [make_config(tmp_path)]
    )
    assert result == {'skills': []}
    assert create.call_count == 0
    assert resolve_latest.call_count == 0


def test_check_updates_reports_available_update(tmp_path, monkeypatch):
    make_skill(tmp_path, '.test-agent', 'aws-s3')
    skill_path = str(
        tmp_path / '.test-agent' / 'skills' / 'aws-s3' / 'SKILL.md'
    )
    result, _, _ = _run_check(
        monkeypatch,
        [make_config(tmp_path)],
        latest_versions={'aws-s3': 'v2'},
    )
    assert result == {
        'skills': [
            {
                'agent': 'Test Agent',
                'name': 'aws-s3',
                'path': skill_path,
                'installedVersion': 'v1',
                'latestVersion': 'v2',
                'updateAvailable': True,
            }
        ]
    }


def test_check_updates_reports_up_to_date(tmp_path, monkeypatch):
    make_skill(tmp_path, '.test-agent', 'aws-s3')
    result, _, _ = _run_check(
        monkeypatch,
        [make_config(tmp_path)],
        latest_versions={'aws-s3': 'v1'},
    )
    assert result['skills'][0]['updateAvailable'] is False
    assert result['skills'][0]['installedVersion'] == 'v1'
    assert result['skills'][0]['latestVersion'] == 'v1'


@pytest.mark.parametrize(
    'marker_contents',
    [
        '{ not valid json',
        '',
        'null',
        # Valid JSON, but not an object, so there is no version field to read.
        '[]',
        '["v1"]',
        '"v1"',
        '42',
    ],
)
def test_check_updates_unreadable_metadata_reports_null_version(
    tmp_path, monkeypatch, marker_contents
):
    make_skill(tmp_path, '.test-agent', 'aws-s3')
    marker = (
        tmp_path
        / '.test-agent'
        / 'skills'
        / 'aws-s3'
        / SKILL_METADATA_FILENAME
    )
    marker.write_text(marker_contents)
    result, _, _ = _run_check(
        monkeypatch,
        [make_config(tmp_path)],
        latest_versions={'aws-s3': 'v1'},
    )
    assert result['skills'][0]['installedVersion'] is None
    assert result['skills'][0]['updateAvailable'] is True


def test_check_updates_looks_up_each_skill_once(tmp_path, monkeypatch):
    # The same skill installed for two agents should still only cost one
    # lookup, and each distinct skill should cost exactly one.
    make_skill(tmp_path, '.agent-a', 'aws-s3')
    make_skill(tmp_path, '.agent-b', 'aws-s3')
    make_skill(tmp_path, '.agent-a', 'aws-lambda')
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
    result, resolve_latest, _ = _run_check(
        monkeypatch,
        configs,
        latest_versions={'aws-s3': 'v2', 'aws-lambda': 'v1'},
    )
    assert len(result['skills']) == 3
    assert resolve_latest.call_count == 2


def test_check_updates_with_agent_filter(tmp_path, monkeypatch):
    make_skill(tmp_path, '.agent-a', 'aws-s3')
    make_skill(tmp_path, '.agent-b', 'aws-s3')
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
    result, _, _ = _run_check(
        monkeypatch,
        configs,
        args=['--agent', 'agent-a'],
        latest_versions={'aws-s3': 'v1'},
    )
    assert [s['agent'] for s in result['skills']] == ['Agent A']


def test_check_updates_shared_skills_dir_reported_once(tmp_path, monkeypatch):
    # Agents that point at the shared universal skills directory must not
    # produce a duplicate row for the same install.
    (tmp_path / '.codex').mkdir()
    universal_base = tmp_path / '.agents'
    shared = universal_base / 'skills'
    skill_dir = shared / 'aws-cdk'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    (skill_dir / SKILL_METADATA_FILENAME).write_text(
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
    result, resolve_latest, _ = _run_check(
        monkeypatch, configs, latest_versions={'aws-cdk': 'v2'}
    )
    assert len(result['skills']) == 1
    assert result['skills'][0]['agent'] == 'Universal (Codex)'
    assert resolve_latest.call_count == 1


def test_check_updates_invalid_agent(tmp_path, monkeypatch):
    with pytest.raises(ParamValidationError, match='Invalid agent'):
        _run_check(
            monkeypatch,
            [make_config(tmp_path)],
            args=['--agent', 'nonexistent'],
        )
