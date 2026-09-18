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


def _run_update_all(agent_configs, args, remote_versions, call_counts=None):
    """Run update-skill with per-skill remote versions."""
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    mock_client = Mock()
    mock_client.meta.endpoint_url = 'https://example.com'
    stream = StringIO()

    resolve_latest = Mock(
        side_effect=lambda _client, name: remote_versions[name]
    )
    download = Mock(
        side_effect=lambda _client, name, version=None: (
            zip_bytes,
            checksum,
            version,
        )
    )
    with (
        patch(
            'awscli.customizations.agenttoolkit.update_skill.resolve_latest_version',
            resolve_latest,
        ),
        patch(
            'awscli.customizations.agenttoolkit.update_skill.get_skill_download',
            download,
        ),
        patch(
            'awscli.customizations.agenttoolkit.update_skill.create_client',
            return_value=mock_client,
        ),
    ):
        cmd = UpdateSkillCommand(
            make_session(), stream=stream, agent_configs=agent_configs
        )
        rc = cmd(args=args, parsed_globals=Mock())
    if call_counts is not None:
        call_counts['resolve_latest_version'] = resolve_latest.call_count
        call_counts['get_skill_download'] = download.call_count
    return rc, stream.getvalue()


def test_update_all_fetches_each_skill_once_for_all_agents(tmp_path):
    # Two skills installed for three agents is six installs, but each skill
    # should only be looked up and downloaded once and then written to every
    # outdated agent.
    agent_names = ['.agent-a', '.agent-b', '.agent-c']
    for agent_dir in agent_names:
        for skill in ['aws-s3', 'aws-lambda']:
            _install_skill_at_version(tmp_path, agent_dir, skill, 'v1')
    configs = [
        make_config(
            tmp_path,
            id=agent_dir.lstrip('.'),
            display_name=f'Agent {agent_dir}',
            detection_path=str(tmp_path / agent_dir),
        )
        for agent_dir in agent_names
    ]
    counts = {}
    rc, _ = _run_update_all(
        configs,
        ['--all'],
        remote_versions={'aws-s3': 'v2', 'aws-lambda': 'v2'},
        call_counts=counts,
    )
    assert rc == 0
    assert counts == {
        'resolve_latest_version': 2,
        'get_skill_download': 2,
    }
    # All six installs were written from those two downloads.
    for agent_dir in agent_names:
        for skill in ['aws-s3', 'aws-lambda']:
            marker = (
                tmp_path
                / agent_dir
                / 'skills'
                / skill
                / SKILL_METADATA_FILENAME
            )
            assert json.loads(marker.read_text()) == {'version': 'v2'}


def test_update_skill_requires_skill_name_or_all(tmp_path):
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='Either --skill-name'):
        _run_update(configs, [])


def test_update_skill_rejects_skill_name_with_all(tmp_path):
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='Cannot use --skill-name'):
        _run_update(configs, ['--all', '--skill-name', 'aws-s3'])


def test_update_all_no_client_when_nothing_installed(tmp_path):
    # Creating a client can fail on its own (no region, bad credentials), so
    # local state must be checked first.
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.create_client'
    ) as create:
        cmd = UpdateSkillCommand(
            make_session(),
            stream=StringIO(),
            agent_configs=[make_config(tmp_path)],
        )
        rc = cmd(args=['--all'], parsed_globals=Mock())
    assert rc == 0
    assert create.call_count == 0


def test_update_one_no_client_when_skill_not_installed(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.create_client'
    ) as create:
        cmd = UpdateSkillCommand(
            make_session(),
            stream=StringIO(),
            agent_configs=[make_config(tmp_path)],
        )
        with pytest.raises(ParamValidationError, match='not installed'):
            cmd(args=['--skill-name', 'aws-s3'], parsed_globals=Mock())
    assert create.call_count == 0


def test_update_all_updates_only_outdated_skills(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-lambda', 'v3')
    configs = [make_config(tmp_path)]
    rc, output = _run_update_all(
        configs,
        ['--all'],
        remote_versions={'aws-s3': 'v2', 'aws-lambda': 'v3'},
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output
    assert 'aws-lambda' not in output
    s3_marker = (
        tmp_path
        / '.test-agent'
        / 'skills'
        / 'aws-s3'
        / SKILL_METADATA_FILENAME
    )
    assert json.loads(s3_marker.read_text()) == {'version': 'v2'}


def test_update_all_when_everything_current(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    configs = [make_config(tmp_path)]
    rc, output = _run_update_all(
        configs, ['--all'], remote_versions={'aws-s3': 'v1'}
    )
    assert rc == 0
    assert output == 'All installed AWS skills are already up to date.\n'


def test_update_all_with_no_skills_installed(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    rc, output = _run_update_all(configs, ['--all'], remote_versions={})
    assert rc == 0
    assert output == 'No installed AWS skills found.\n'


def test_update_all_skips_agents_without_the_skill(tmp_path):
    # aws-s3 is only installed for Agent A. Updating everything must not
    # create the skill for Agent B, which never had it.
    _install_skill_at_version(tmp_path, '.agent-a', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.agent-b', 'aws-lambda', 'v1')
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
    rc, output = _run_update_all(
        configs,
        ['--all'],
        remote_versions={'aws-s3': 'v2', 'aws-lambda': 'v2'},
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2) to Agent A' in output
    assert 'Updated aws-lambda (v2) to Agent B' in output
    assert not (tmp_path / '.agent-b' / 'skills' / 'aws-s3').exists()
    assert not (tmp_path / '.agent-a' / 'skills' / 'aws-lambda').exists()


def test_update_all_with_agent_filter(tmp_path):
    _install_skill_at_version(tmp_path, '.agent-a', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.agent-b', 'aws-s3', 'v1')
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
    rc, output = _run_update_all(
        configs,
        ['--all', '--agent', 'agent-a'],
        remote_versions={'aws-s3': 'v2'},
    )
    assert rc == 0
    assert 'Agent A' in output
    assert 'Agent B' not in output
    b_marker = (
        tmp_path / '.agent-b' / 'skills' / 'aws-s3' / SKILL_METADATA_FILENAME
    )
    assert json.loads(b_marker.read_text()) == {'version': 'v1'}


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


def test_update_skill_through_symlinked_dir(tmp_path):
    # A user symlinks the per-skill dir into a shared location. update-skill
    # must follow the link and overwrite the target in place (shutil.rmtree
    # refuses to operate on the symlink itself), leaving the link intact.
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    target = tmp_path / 'shared' / 'aws-s3'
    target.mkdir(parents=True)
    (target / 'SKILL.md').write_text('old')
    (target / 'old.md').write_text('removed in v2')
    (target / SKILL_METADATA_FILENAME).write_text(
        json.dumps({'version': 'v1'})
    )
    link = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    link.symlink_to(target, target_is_directory=True)

    configs = [make_config(tmp_path)]
    new_zip = make_skill_zip({'SKILL.md': 'new'})[0]
    rc, output = _run_update(
        configs,
        ['--skill-name', 'aws-s3'],
        remote_version='v2',
        zip_bytes=new_zip,
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output
    assert link.is_symlink()
    assert (target / 'SKILL.md').read_text() == 'new'
    assert not (target / 'old.md').exists()
    assert json.loads((target / SKILL_METADATA_FILENAME).read_text()) == {
        'version': 'v2'
    }


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
