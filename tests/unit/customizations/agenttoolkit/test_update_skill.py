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
import io
import json
import os
import zipfile
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import NoCredentialsError

from awscli.customizations.agenttoolkit import atomic, utils
from awscli.customizations.agenttoolkit.add_skill import AddSkillCommand
from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.update_skill import UpdateSkillCommand
from awscli.customizations.agenttoolkit.utils import AgentToolkitServiceError
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


def _make_skill_client(bad_checksum_skill=None):
    # Only the service responses are faked; the real download and install
    # code runs, and install_skill rejects the bad checksum.
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    client = Mock()
    client.get_latest_skill_version.return_value = {'body': 'v2'}
    client.get_skill_file.side_effect = lambda **kwargs: {
        'body': io.BytesIO(zip_bytes)
    }
    client.get_skill_file_checksum.side_effect = lambda name, **kwargs: {
        'body': '0' * 64 if name == bad_checksum_skill else checksum
    }
    return client


def _make_update_command(tmp_path, client):
    stream = StringIO()
    error_stream = StringIO()
    cmd = UpdateSkillCommand(
        make_session(),
        stream=stream,
        error_stream=error_stream,
        client=client,
        agent_configs=[make_config(tmp_path)],
    )
    return cmd, stream, error_stream


def test_update_all_continues_after_skill_failure(tmp_path):
    for name in ('aws-cdk', 'aws-lambda', 'aws-s3'):
        _install_skill_at_version(tmp_path, '.test-agent', name, 'v1')
    client = _make_skill_client(bad_checksum_skill='aws-lambda')
    cmd, stream, error_stream = _make_update_command(tmp_path, client)

    rc = cmd(args=['--all'], parsed_globals=Mock())

    assert rc == 1
    assert 'Updated aws-cdk (v2)' in stream.getvalue()
    assert 'Updated aws-s3 (v2)' in stream.getvalue()
    assert (
        'Failed to update aws-lambda: Checksum verification failed'
        in error_stream.getvalue()
    )
    lambda_marker = (
        tmp_path
        / '.test-agent'
        / 'skills'
        / 'aws-lambda'
        / SKILL_METADATA_FILENAME
    )
    assert json.loads(lambda_marker.read_text()) == {'version': 'v1'}


def test_update_all_failure_with_rest_up_to_date(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-cdk', 'v2')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-lambda', 'v1')
    client = _make_skill_client(bad_checksum_skill='aws-lambda')
    cmd, stream, error_stream = _make_update_command(tmp_path, client)

    rc = cmd(args=['--all'], parsed_globals=Mock())

    assert rc == 1
    assert 'already up to date' not in stream.getvalue()
    assert 'Failed to update aws-lambda' in error_stream.getvalue()


def test_update_all_stops_on_uncaught_error(tmp_path):
    for name in ('aws-cdk', 'aws-lambda'):
        _install_skill_at_version(tmp_path, '.test-agent', name, 'v1')
    client = _make_skill_client()
    client.get_latest_skill_version.side_effect = NoCredentialsError()
    cmd, _, error_stream = _make_update_command(tmp_path, client)

    with pytest.raises(NoCredentialsError):
        cmd(args=['--all'], parsed_globals=Mock())

    assert client.get_latest_skill_version.call_count == 1
    assert not client.get_skill_file.called
    assert error_stream.getvalue() == ''


def _skill_dir(tmp_path, name='aws-s3'):
    return tmp_path / '.test-agent' / 'skills' / name


def _hidden_entries(path):
    return sorted(p.name for p in path.iterdir() if p.name.startswith('.'))


def _corrupt_zip(files):
    # Flip a byte of the stored data so the CRC check fails on extraction.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    data = bytearray(buf.getvalue())
    offset = data.index(b'corrupt-me')
    data[offset] ^= 0xFF
    return bytes(data)


def test_update_skill_replaces_whole_directory(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    skill_dir = _skill_dir(tmp_path)
    (skill_dir / 'removed-in-v2.md').write_text('old')
    new_zip = make_skill_zip({'SKILL.md': 'new', 'ref/a.md': 'a'})[0]
    rc, _ = _run_update(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3'], zip_bytes=new_zip
    )
    assert rc == 0
    assert sorted(
        str(p.relative_to(skill_dir)) for p in skill_dir.rglob('*')
    ) == sorted(['SKILL.md', SKILL_METADATA_FILENAME, 'ref', 'ref/a.md'])
    assert _hidden_entries(skill_dir.parent) == []


@pytest.mark.parametrize(
    'zip_bytes, match',
    [
        (make_skill_zip({'README.md': 'no skill file'})[0], 'has no SKILL.md'),
        (b'not a zip file', 'Could not read the archive'),
        (_corrupt_zip({'SKILL.md': 'corrupt-me'}), 'is corrupt'),
    ],
)
def test_update_skill_bad_archive_leaves_installed_version(
    tmp_path, zip_bytes, match
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    skill_dir = _skill_dir(tmp_path)
    with pytest.raises(AgentToolkitServiceError, match=match):
        _run_update(
            [make_config(tmp_path)],
            ['--skill-name', 'aws-s3'],
            zip_bytes=zip_bytes,
        )
    assert (skill_dir / 'SKILL.md').read_text() == 'name: aws-s3\n'
    assert json.loads((skill_dir / SKILL_METADATA_FILENAME).read_text()) == {
        'version': 'v1'
    }
    assert _hidden_entries(skill_dir.parent) == []


@pytest.mark.parametrize('error', [OSError('disk full'), KeyboardInterrupt()])
def test_update_skill_interrupted_swap_leaves_installed_version(
    tmp_path, error
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    skill_dir = _skill_dir(tmp_path)
    with patch.object(atomic, 'swap_into_place', side_effect=error):
        with pytest.raises((AgentToolkitServiceError, KeyboardInterrupt)):
            _run_update([make_config(tmp_path)], ['--skill-name', 'aws-s3'])
    assert (skill_dir / 'SKILL.md').read_text() == 'name: aws-s3\n'
    assert _hidden_entries(skill_dir.parent) == []


def test_update_skill_recovers_from_previous_interrupted_swap(tmp_path):
    # A previous run died after moving the live dir to its backup name.
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    skill_dir = _skill_dir(tmp_path)
    staging = atomic.make_staging_dir(str(skill_dir))
    os.rename(skill_dir, atomic._sibling(str(skill_dir), atomic._BACKUP))
    # The leftover dirs are hidden, so until recovery the skill looks
    # uninstalled; recovery happens when it's installed again.
    configs = [make_config(tmp_path)]
    with patch(
        'awscli.customizations.agenttoolkit.add_skill.get_skill_download',
        return_value=(*make_skill_zip({'SKILL.md': 'new'}), 'v2'),
    ):
        stream = StringIO()
        cmd = AddSkillCommand(
            make_session(), stream=stream, agent_configs=configs
        )
        with patch(
            'awscli.customizations.agenttoolkit.add_skill.create_client'
        ):
            rc = cmd(args=['--skill-name', 'aws-s3'], parsed_globals=Mock())
    assert rc == 0
    # The backup was restored, so add-skill finds v1 already installed.
    assert 'already installed (v1)' in stream.getvalue()
    assert (skill_dir / 'SKILL.md').read_text() == 'name: aws-s3\n'
    assert not os.path.exists(staging)
    assert _hidden_entries(skill_dir.parent) == []


def test_update_skill_lock_timeout_is_reported(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch.object(
        utils, 'file_lock', side_effect=TimeoutError('timed out')
    ):
        with pytest.raises(AgentToolkitServiceError, match='timed out'):
            _run_update([make_config(tmp_path)], ['--skill-name', 'aws-s3'])
    skill_dir = _skill_dir(tmp_path)
    assert (skill_dir / 'SKILL.md').read_text() == 'name: aws-s3\n'


def test_update_all_continues_after_filesystem_error(tmp_path):
    for name in ('aws-cdk', 'aws-s3'):
        _install_skill_at_version(tmp_path, '.test-agent', name, 'v1')
    real_swap = atomic.swap_into_place

    def swap(staging, live):
        if live.endswith('aws-cdk'):
            raise PermissionError('in use')
        real_swap(staging, live)

    with patch.object(atomic, 'swap_into_place', side_effect=swap):
        rc, output, errors = _run_update_all_with_errors(
            [make_config(tmp_path)], {'aws-cdk': 'v2', 'aws-s3': 'v2'}
        )
    assert rc == 1
    assert 'Failed to update aws-cdk' in errors
    assert 'Updated aws-s3 (v2)' in output
    assert json.loads(
        (_skill_dir(tmp_path, 'aws-cdk') / SKILL_METADATA_FILENAME).read_text()
    ) == {'version': 'v1'}


def _run_update_all_with_errors(agent_configs, remote_versions):
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    stream, error_stream = StringIO(), StringIO()
    with (
        patch(
            'awscli.customizations.agenttoolkit.update_skill.resolve_latest_version',
            side_effect=lambda _client, name: remote_versions[name],
        ),
        patch(
            'awscli.customizations.agenttoolkit.update_skill.get_skill_download',
            side_effect=lambda _client, name, version=None: (
                zip_bytes,
                checksum,
                version,
            ),
        ),
        patch('awscli.customizations.agenttoolkit.update_skill.create_client'),
    ):
        cmd = UpdateSkillCommand(
            make_session(),
            stream=stream,
            agent_configs=agent_configs,
            error_stream=error_stream,
        )
        rc = cmd(args=['--all'], parsed_globals=Mock())
    return rc, stream.getvalue(), error_stream.getvalue()


def _crash_mid_swap(skill_dir):
    """Leave ``skill_dir`` as a crash after its first rename would."""
    staging = atomic.make_staging_dir(str(skill_dir))
    os.rename(skill_dir, atomic._sibling(str(skill_dir), atomic._BACKUP))
    return staging


def test_update_skill_recovers_hidden_skill_then_updates_it(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    skill_dir = _skill_dir(tmp_path)
    _crash_mid_swap(skill_dir)
    rc, output = _run_update(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3'],
        remote_version='v2',
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output
    assert json.loads((skill_dir / SKILL_METADATA_FILENAME).read_text()) == {
        'version': 'v2'
    }
    assert _hidden_entries(skill_dir.parent) == []


def test_update_all_recovers_hidden_skill(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _crash_mid_swap(_skill_dir(tmp_path))
    rc, output, _ = _run_update_all_with_errors(
        [make_config(tmp_path)], {'aws-s3': 'v2'}
    )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output


def test_update_skill_recovery_failure_does_not_block_update(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch.object(atomic, 'recover_all', side_effect=OSError('boom')):
        rc, output = _run_update(
            [make_config(tmp_path)], ['--skill-name', 'aws-s3']
        )
    assert rc == 0
    assert 'Updated aws-s3 (v2)' in output


def test_install_skips_file_in_place_of_skill_dir(tmp_path):
    skills = tmp_path / '.test-agent' / 'skills'
    skills.mkdir(parents=True)
    (skills / 'aws-s3').write_text('not a skill')
    zip_bytes, checksum = make_skill_zip()
    stream = StringIO()
    agent = make_config(tmp_path).detect()
    utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent], stream)
    assert 'is in the way' in stream.getvalue()
    assert (skills / 'aws-s3').read_text() == 'not a skill'
    assert _hidden_entries(skills) == []


def test_install_accepts_dot_slash_skill_file(tmp_path):
    zip_bytes, checksum = make_skill_zip({'./SKILL.md': 'x'})
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path).detect()
    utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent])
    assert (_skill_dir(tmp_path) / 'SKILL.md').read_text() == 'x'


def test_install_rejects_skill_file_that_is_a_directory(tmp_path):
    zip_bytes, checksum = make_skill_zip({'SKILL.md/': '', 'README.md': 'x'})
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path).detect()
    with pytest.raises(AgentToolkitServiceError, match='has no SKILL.md'):
        utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent])


def test_install_rejects_encrypted_member(tmp_path):
    zip_bytes = bytearray(make_skill_zip()[0])
    # Set the "encrypted" flag on the local and central directory headers.
    zip_bytes[zip_bytes.index(b'PK\x03\x04') + 6] |= 1
    zip_bytes[zip_bytes.index(b'PK\x01\x02') + 8] |= 1
    zip_bytes = bytes(zip_bytes)
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    (tmp_path / '.test-agent').mkdir()
    agent = make_config(tmp_path).detect()
    with pytest.raises(
        AgentToolkitServiceError, match='corrupt or unsupported'
    ):
        utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent])
    assert not _skill_dir(tmp_path).exists()
