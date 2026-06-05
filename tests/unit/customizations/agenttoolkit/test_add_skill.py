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
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.agenttoolkit.add_skill import AddSkillCommand
from awscli.customizations.agenttoolkit.agents import SKILL_METADATA_FILENAME
from awscli.customizations.agenttoolkit.utils import AgentToolkitServiceError
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_skill_zip,
)


def _run_add(agent_configs, args, zip_bytes=None, version='v1', checksum=None):
    default_bytes, default_checksum = make_skill_zip({'SKILL.md': 'test'})
    if zip_bytes is None:
        zip_bytes = default_bytes
    if checksum is None:
        checksum = hashlib.sha256(zip_bytes).hexdigest()

    def mock_download(client, skill_name, version=None):
        v = version if version is not None else fallback_version
        return zip_bytes, checksum, v

    fallback_version = version

    stream = StringIO()
    session = Mock()
    session.user_agent_extra = ''
    session.emit_first_non_none_response.return_value = None

    with (
        patch(
            'awscli.customizations.agenttoolkit.add_skill.get_skill_download',
            side_effect=mock_download,
        ),
        patch('awscli.customizations.agenttoolkit.add_skill.create_client'),
    ):
        cmd = AddSkillCommand(
            session, stream=stream, agent_configs=agent_configs
        )
        rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def test_add_skill_success(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'Installed aws-s3 (v1) to Test Agent' in output
    assert (
        tmp_path / '.test-agent' / 'skills' / 'aws-s3' / 'SKILL.md'
    ).exists()


def test_add_skill_with_version(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    rc, output = _run_add(
        configs,
        ['--skill-name', 'aws-s3', '--skill-version', 'v2'],
        version='v999',
    )
    assert rc == 0
    assert 'v2' in output
    assert 'v999' not in output


def test_add_skill_checksum_failure(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    with pytest.raises(
        AgentToolkitServiceError, match='Checksum verification failed'
    ):
        _run_add(configs, ['--skill-name', 'aws-s3'], checksum='bad_checksum')


def test_add_skill_multiple_agents(tmp_path):
    (tmp_path / '.agent-a' / 'skills').mkdir(parents=True)
    (tmp_path / '.agent-b' / 'skills').mkdir(parents=True)
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
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'Agent A' in output
    assert 'Agent B' in output
    assert (tmp_path / '.agent-a' / 'skills' / 'aws-s3' / 'SKILL.md').exists()
    assert (tmp_path / '.agent-b' / 'skills' / 'aws-s3' / 'SKILL.md').exists()


def test_add_skill_dedupes_shared_skills_path(tmp_path):
    (tmp_path / '.agent-a').mkdir()
    (tmp_path / '.agent-b').mkdir()
    shared = str(tmp_path / 'shared' / 'skills')
    configs = [
        make_config(
            tmp_path,
            id='a',
            display_name='Agent A',
            detection_path=str(tmp_path / '.agent-a'),
            skills_path_override=shared,
        ),
        make_config(
            tmp_path,
            id='b',
            display_name='Agent B',
            detection_path=str(tmp_path / '.agent-b'),
            skills_path_override=shared,
        ),
    ]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert output.count('Installed aws-s3') == 1
    assert (tmp_path / 'shared' / 'skills' / 'aws-s3' / 'SKILL.md').exists()


def test_add_skill_with_client_filter(tmp_path):
    (tmp_path / '.agent-a' / 'skills').mkdir(parents=True)
    (tmp_path / '.agent-b' / 'skills').mkdir(parents=True)
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
    rc, output = _run_add(
        configs, ['--skill-name', 'aws-s3', '--agent', 'agent-a']
    )
    assert rc == 0
    assert 'Agent A' in output
    assert 'Agent B' not in output
    assert (tmp_path / '.agent-a' / 'skills' / 'aws-s3' / 'SKILL.md').exists()
    assert not (tmp_path / '.agent-b' / 'skills' / 'aws-s3').exists()


def test_add_skill_agent_filter_is_case_insensitive(tmp_path):
    (tmp_path / '.agent-a' / 'skills').mkdir(parents=True)
    configs = [
        make_config(
            tmp_path,
            id='agent-a',
            display_name='Agent A',
            detection_path=str(tmp_path / '.agent-a'),
        ),
    ]
    rc, output = _run_add(
        configs, ['--skill-name', 'aws-s3', '--agent', 'AGENT-A']
    )
    assert rc == 0
    assert 'Agent A' in output
    assert (tmp_path / '.agent-a' / 'skills' / 'aws-s3' / 'SKILL.md').exists()


def test_add_skill_invalid_client(tmp_path):
    configs = [make_config(tmp_path)]
    with pytest.raises(ParamValidationError, match='Invalid agent'):
        _run_add(configs, ['--skill-name', 'aws-s3', '--agent', 'nonexistent'])


def test_add_skill_no_agents(tmp_path):
    configs = [make_config(tmp_path)]  # dir doesn't exist
    with pytest.raises(
        ParamValidationError, match='No supported AI coding agents'
    ):
        _run_add(configs, ['--skill-name', 'aws-s3'])


def test_add_skill_universal_row_coexists_with_override_agent(tmp_path):
    (tmp_path / '.codex').mkdir()
    universal_base = tmp_path / '.agents'
    shared = universal_base / 'skills'
    shared.mkdir(parents=True)
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
    rc, output = _run_add(configs, ['--skill-name', 'aws-cdk'])
    assert rc == 0
    assert 'Universal (Codex)' in output
    # Codex shares the skills path; the universal row owns the print line.
    assert output.count('Installed aws-cdk') == 1
    assert (shared / 'aws-cdk' / 'SKILL.md').exists()


def test_add_skill_already_installed_message_not_duplicated(tmp_path):
    (tmp_path / '.codex').mkdir()
    universal_base = tmp_path / '.agents'
    shared = universal_base / 'skills'
    skill_dir = shared / 'aws-cdk'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('old')
    (skill_dir / SKILL_METADATA_FILENAME).write_text('{"version": "v1"}')
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
    rc, output = _run_add(configs, ['--skill-name', 'aws-cdk'])
    assert rc == 0
    assert output.count('already installed') == 1


def test_add_skill_into_symlinked_skills_dir(tmp_path):
    # User symlinks an agent's skills dir into a shared location so every
    # agent reads one source of truth. We follow the link and write into
    # its target, preserving the link (shutil.rmtree would otherwise refuse
    # to operate on the symlink).
    shared = tmp_path / 'shared-skills'
    shared.mkdir()
    agent_dir = tmp_path / '.test-agent'
    agent_dir.mkdir()
    skills_link = agent_dir / 'skills'
    skills_link.symlink_to(shared, target_is_directory=True)

    configs = [make_config(tmp_path)]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'Installed aws-s3 (v1) to Test Agent' in output
    # The symlink is preserved and the skill landed in its target.
    assert skills_link.is_symlink()
    assert (shared / 'aws-s3' / 'SKILL.md').exists()


def test_add_skill_already_installed_recommends_update(tmp_path):
    # add-skill leaves an existing AWS-CLI install alone and points the
    # user at the version-aware update-skill command rather than silently
    # overwriting it.
    skill_dir = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('old')
    (skill_dir / SKILL_METADATA_FILENAME).write_text('{"version": "v1"}')

    configs = [make_config(tmp_path)]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'aws-s3 is already installed (v1)' in output
    assert 'update-skill --skill-name aws-s3' in output
    assert 'Installed aws-s3' not in output
    # Existing content is untouched.
    assert (skill_dir / 'SKILL.md').read_text() == 'old'


def test_add_skill_skips_symlinked_existing_install(tmp_path):
    # The per-skill dir is a symlink to a previously-installed location.
    # We resolve it, see our marker, and skip (recommend update) without
    # touching the link or its target.
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    target = tmp_path / 'real-aws-s3'
    target.mkdir()
    (target / 'SKILL.md').write_text('old')
    (target / SKILL_METADATA_FILENAME).write_text('{"version": "v1"}')
    link = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    link.symlink_to(target, target_is_directory=True)

    configs = [make_config(tmp_path)]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'aws-s3 is already installed (v1)' in output
    assert link.is_symlink()
    assert (target / 'SKILL.md').read_text() == 'old'


def test_add_skill_skips_unmarked_existing_dir(tmp_path):
    # User has a hand-written skill (no AWS CLI metadata marker). Install
    # must skip it rather than destroy the user's content.
    skill_dir = tmp_path / '.test-agent' / 'skills' / 'aws-s3'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('hand-written content')

    configs = [make_config(tmp_path)]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert 'was not installed by the AWS CLI' in output
    assert 'Installed aws-s3' not in output
    assert (skill_dir / 'SKILL.md').read_text() == 'hand-written content'
    # No marker written, so we did not adopt the directory.
    assert not (skill_dir / SKILL_METADATA_FILENAME).exists()


def test_add_skill_zip_slip_rejected(tmp_path):
    (tmp_path / '.test-agent' / 'skills').mkdir(parents=True)
    configs = [make_config(tmp_path)]
    zip_bytes = make_skill_zip({'../../../evil.txt': 'pwned'})[0]
    with pytest.raises(
        AgentToolkitServiceError, match='path escapes skill directory'
    ):
        _run_add(configs, ['--skill-name', 'aws-s3'], zip_bytes=zip_bytes)
