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
from unittest.mock import Mock

import pytest

from awscli.customizations.agenttoolkit.agents import SKILL_METADATA_FILENAME
from awscli.customizations.agenttoolkit.remove_skill import RemoveCommand
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_skill,
)


def _run_remove(agent_configs, args):
    stream = StringIO()
    session = Mock()
    session.user_agent_extra = ''
    session.emit_first_non_none_response.return_value = None
    cmd = RemoveCommand(session, stream=stream, agent_configs=agent_configs)
    rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def test_remove_skill_not_installed(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='not installed'):
        _run_remove(configs, ['--skill-name', 'aws-foo'])


def test_remove_skill_success(tmp_path):
    make_skill(tmp_path, '.test-agent', 'aws-serverless')
    configs = [make_config(tmp_path)]
    rc, output = _run_remove(configs, ['--skill-name', 'aws-serverless'])
    assert rc == 0
    assert 'Removed aws-serverless from Test Agent' in output
    assert not (
        tmp_path / '.test-agent' / 'skills' / 'aws-serverless'
    ).exists()


def test_remove_from_multiple_agents(tmp_path):
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
    rc, output = _run_remove(configs, ['--skill-name', 'aws-serverless'])
    assert rc == 0
    assert 'Agent A' in output
    assert 'Agent B' in output
    assert not (tmp_path / '.agent-a' / 'skills' / 'aws-serverless').exists()
    assert not (tmp_path / '.agent-b' / 'skills' / 'aws-serverless').exists()


def test_remove_with_client_filter(tmp_path):
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
    rc, output = _run_remove(
        configs,
        ['--skill-name', 'aws-serverless', '--agent', 'agent-a'],
    )
    assert rc == 0
    assert 'Agent A' in output
    assert 'Agent B' not in output
    assert not (tmp_path / '.agent-a' / 'skills' / 'aws-serverless').exists()
    assert (tmp_path / '.agent-b' / 'skills' / 'aws-serverless').exists()


def test_remove_skill_dedupes_shared_skills_path(tmp_path):
    (tmp_path / '.agent-a').mkdir()
    (tmp_path / '.agent-b').mkdir()
    shared = tmp_path / 'shared' / 'skills'
    skill_dir = shared / 'aws-s3'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    (skill_dir / SKILL_METADATA_FILENAME).write_text(
        json.dumps({'version': 'v1'})
    )
    configs = [
        make_config(
            tmp_path,
            id='a',
            display_name='Agent A',
            detection_path=str(tmp_path / '.agent-a'),
            skills_path_override=str(shared),
        ),
        make_config(
            tmp_path,
            id='b',
            display_name='Agent B',
            detection_path=str(tmp_path / '.agent-b'),
            skills_path_override=str(shared),
        ),
    ]
    rc, output = _run_remove(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert output.count('Removed aws-s3') == 1
    assert not (shared / 'aws-s3').exists()


def test_remove_skill_universal_row_coexists_with_override_agent(tmp_path):
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
    rc, output = _run_remove(configs, ['--skill-name', 'aws-cdk'])
    assert rc == 0
    assert 'Removed aws-cdk from Universal (Codex)' in output
    # Codex shares the skills path; the universal row owns the print line.
    assert output.count('Removed aws-cdk') == 1
    assert not (shared / 'aws-cdk').exists()


def test_remove_skill_without_marker_refused(tmp_path):
    make_skill(tmp_path, '.test-agent', 'hand-rolled', with_marker=False)
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='not installed'):
        _run_remove(configs, ['--skill-name', 'hand-rolled'])
    assert (tmp_path / '.test-agent' / 'skills' / 'hand-rolled').exists()


def test_remove_invalid_client_rejected(tmp_path):
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='Invalid agent'):
        _run_remove(
            configs,
            ['--skill-name', 'aws-serverless', '--agent', 'nonexistent'],
        )
