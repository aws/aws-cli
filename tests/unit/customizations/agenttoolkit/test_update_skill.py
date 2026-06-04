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
import hashlib
import json
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.update_skill import UpdateSkillCommand
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_session,
    make_skill_zip,
)


def _install_skill_at_version(tmp_path, agent_dir, skill_name, version):
    skill_dir = tmp_path / agent_dir / 'skills' / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(f'name: {skill_name}\n')
    (skill_dir / SKILL_METADATA_FILENAME).write_text(
        json.dumps({'version': version})
    )


def _run_update(agent_configs, args, remote_version='v2', zip_bytes=None):
    if zip_bytes is not None:
        checksum = hashlib.sha256(zip_bytes).hexdigest()
    else:
        zip_bytes, checksum = make_skill_zip({'SKILL.md': 'test'})

    mock_client = Mock()
    mock_client.meta.endpoint_url = 'https://example.com'

    stream = StringIO()
    session = make_session()

    with (
        patch(
            'awscli.customizations.agenttoolkit.update_skill.resolve_latest_version',
            return_value=remote_version,
        ),
        patch(
            'awscli.customizations.agenttoolkit.update_skill.get_skill_download',
            return_value=(zip_bytes, checksum, remote_version),
        ),
        patch(
            'awscli.customizations.agenttoolkit.update_skill.create_client',
            return_value=mock_client,
        ),
    ):
        cmd = UpdateSkillCommand(
            session, stream=stream, agent_configs=agent_configs
        )
        rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def test_update_skill_outdated(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    configs = [make_config(tmp_path)]
    rc, output = _run_update(
        configs, ['--skill-name', 'aws-s3'], remote_version='v2'
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output
    marker = (
        tmp_path
        / '.test-agent'
        / 'skills'
        / 'aws-s3'
        / SKILL_METADATA_FILENAME
    )
    assert json.loads(marker.read_text()) == {'version': 'v2'}


def test_update_skill_already_up_to_date(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    configs = [make_config(tmp_path)]
    rc, output = _run_update(
        configs, ['--skill-name', 'aws-s3'], remote_version='v1'
    )
    assert rc == 0
    assert 'already up to date' in output


def test_update_skill_not_installed(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='not installed'):
        _run_update(configs, ['--skill-name', 'aws-s3'])


def test_update_skill_only_outdated_agents_updated(tmp_path):
    _install_skill_at_version(tmp_path, '.agent-a', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.agent-b', 'aws-s3', 'v2')
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
    rc, output = _run_update(
        configs, ['--skill-name', 'aws-s3'], remote_version='v2'
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2) to Agent A' in output
    assert 'Agent B' not in output


def test_update_skill_missing_marker_skipped(tmp_path):
    skill_dir = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='not installed'):
        _run_update(configs, ['--skill-name', 'aws-s3'], remote_version='v2')


def test_update_skill_removes_orphaned_files(tmp_path):
    skill_dir = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('old')
    (skill_dir / 'old.md').write_text('removed in v2')
    (skill_dir / SKILL_METADATA_FILENAME).write_text(
        json.dumps({'version': 'v1'})
    )
    configs = [make_config(tmp_path)]
    new_zip = make_skill_zip({'SKILL.md': 'new'})[0]
    rc, _ = _run_update(
        configs,
        ['--skill-name', 'aws-s3'],
        remote_version='v2',
        zip_bytes=new_zip,
    )
    assert rc == 0
    assert (skill_dir / 'SKILL.md').read_text() == 'new'
    assert not (skill_dir / 'old.md').exists()
