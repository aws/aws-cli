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
import datetime
import hashlib
import io
import json
import os
import zipfile
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)

from awscli.clidriver import AWSCLIEntryPoint
from awscli.customizations.agenttoolkit import (
    atomic,
    filelock,
    hooks,
    state,
    update_skill,
    utils,
)
from awscli.customizations.agenttoolkit.add_skill import AddSkillCommand
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.remove_skill import RemoveCommand
from awscli.customizations.agenttoolkit.update_skill import (
    HOOK_CLIENT_CONFIG,
    UpdateSkillCommand,
)
from awscli.customizations.agenttoolkit.utils import AgentToolkitServiceError
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_session,
    make_skill_zip,
    requires_symlinks,
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


@requires_symlinks
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


def _make_skill_client(bad_checksum_skill=None, core_skills=()):
    # Only the service responses are faked; the real download and install
    # code runs, and install_skill rejects the bad checksum.
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    client = Mock()
    client.get_paginator.return_value.paginate.return_value = [
        {
            'skills': [
                {
                    'name': name,
                    'skillVersion': 'v2',
                    'categories': ['aws-core'],
                }
                for name in core_skills
            ]
        }
    ]
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


def _not_found(operation_name):
    return ClientError(
        {
            'Error': {'Code': '404', 'Message': 'Not Found'},
            'ResponseMetadata': {'HTTPStatusCode': 404},
        },
        operation_name,
    )


def _drop_from_catalog(client, dropped):
    def get_latest_skill_version(name, **kwargs):
        if name == dropped:
            raise _not_found('GetLatestSkillVersion')
        return {'body': 'v2'}

    client.get_latest_skill_version.side_effect = get_latest_skill_version


def test_update_all_leaves_skill_dropped_from_catalog(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-gone', 'v1')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    _drop_from_catalog(client, 'aws-gone')
    cmd, stream, error_stream = _make_update_command(tmp_path, client)
    assert cmd(args=['--all'], parsed_globals=Mock()) == 0
    assert 'aws-gone' not in stream.getvalue() + error_stream.getvalue()
    assert stream.getvalue().endswith(
        '1 updated, 0 skipped, 0 failed, 0 already up to date.\n'
    )
    marker = _skill_dir(tmp_path, 'aws-gone') / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v1'}


def test_update_all_fails_skill_missing_after_version_lookup(tmp_path):
    # Only a missing latest version means the skill left the catalog.
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    client.get_skill_file.side_effect = _not_found('GetSkillFile')
    cmd, _, error_stream = _make_update_command(tmp_path, client)
    assert cmd(args=['--all'], parsed_globals=Mock()) == 1
    assert 'Failed to update aws-s3' in error_stream.getvalue()


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
    assert 'All installed AWS skills' not in stream.getvalue()
    assert (
        '0 updated, 0 skipped, 1 failed, 1 already up to date.'
        in stream.getvalue()
    )
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
        p.relative_to(skill_dir).as_posix() for p in skill_dir.rglob('*')
    ) == sorted(['SKILL.md', SKILL_METADATA_FILENAME, 'ref', 'ref/a.md'])
    assert _hidden_entries(skill_dir.parent) == []


@pytest.mark.parametrize(
    'zip_bytes, match',
    [
        (make_skill_zip({'README.md': 'no skill file'})[0], 'has no SKILL.md'),
        (b'not a zip file', 'Could not read the archive'),
        (_corrupt_zip({'SKILL.md': 'corrupt-me'}), 'is corrupt'),
    ],
    # The zip bytes include a timestamp, so they can't be used as test IDs:
    # pytest-xdist workers would collect different tests.
    ids=['no-skill-md', 'not-a-zip', 'corrupt-zip'],
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


def _skip_aws_cdk_at(tmp_path):
    """Put a directory the CLI didn't create in aws-cdk's second location."""
    _install_skill_at_version(tmp_path, '.agent-a', 'aws-cdk', 'v1')
    other = tmp_path / '.agent-b' / 'skills' / 'aws-cdk'
    other.mkdir(parents=True)
    (other / 'SKILL.md').write_text('mine')
    (other / SKILL_METADATA_FILENAME).write_text('{"version": "v1"}')
    return other


def _two_agent_configs(tmp_path):
    return [
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


def test_update_all_reports_summary(tmp_path):
    for name, version in (
        ('aws-cdk', 'v1'),
        ('aws-iam', 'v2'),
        ('aws-s3', 'v1'),
    ):
        _install_skill_at_version(tmp_path, '.test-agent', name, version)
    real_swap = atomic.swap_into_place

    def swap(staging, live):
        if live.endswith('aws-s3'):
            raise PermissionError('in use')
        real_swap(staging, live)

    with patch.object(atomic, 'swap_into_place', side_effect=swap):
        rc, output, errors = _run_update_all_with_errors(
            [make_config(tmp_path)],
            {'aws-cdk': 'v2', 'aws-iam': 'v2', 'aws-s3': 'v2'},
        )
    assert rc == 1
    assert '1 updated, 0 skipped, 1 failed, 1 already up to date.' in output
    assert 'Skipped:' not in output
    assert '\nFailed:\n  Failed to update aws-s3: ' in errors
    assert 'To retry, run "aws agent-toolkit update-skill' in errors


def test_update_all_reports_skipped_with_reason(tmp_path):
    other = _skip_aws_cdk_at(tmp_path)
    # Agent B's copy has a marker so it is listed, but replace it with a
    # directory the CLI didn't create just before installing.
    real_install_dir = utils._install_skill_dir

    def install_dir(skill_name, version, zf, real_dir, *args):
        if real_dir == os.path.realpath(other):
            os.remove(other / SKILL_METADATA_FILENAME)
        return real_install_dir(skill_name, version, zf, real_dir, *args)

    with patch.object(utils, '_install_skill_dir', side_effect=install_dir):
        rc, output, errors = _run_update_all_with_errors(
            _two_agent_configs(tmp_path), {'aws-cdk': 'v2'}
        )
    assert rc == 0
    assert '0 updated, 1 skipped, 0 failed, 0 already up to date.' in output
    assert (
        f'Skipped:\n  aws-cdk at {os.path.realpath(other)}: directory was not '
        'installed by the AWS CLI.\n'
    ) in output
    assert 'add-skill --skill-name <name>' in output
    assert (other / 'SKILL.md').read_text() == 'mine'
    assert errors == ''


def test_update_one_skill_reports_skipped(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch.object(utils, '_install_skill_dir', return_value='a reason'):
        rc, output = _run_update(
            [make_config(tmp_path)], ['--skill-name', 'aws-s3']
        )
    assert rc == 0
    assert 'Skipped:\n  aws-s3 at ' in output
    assert ': a reason.\n' in output


def test_update_all_up_to_date_has_no_summary(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    rc, output, _ = _run_update_all_with_errors(
        [make_config(tmp_path)], {'aws-s3': 'v2'}
    )
    assert rc == 0
    assert output == 'All installed AWS skills are already up to date.\n'


def test_install_skill_returns_skipped_dirs(tmp_path):
    skills = tmp_path / '.test-agent' / 'skills'
    skills.mkdir(parents=True)
    (skills / 'aws-s3').write_text('not a skill')
    zip_bytes, checksum = make_skill_zip()
    agent = make_config(tmp_path).detect()
    skipped = utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent])
    assert skipped == [
        (
            os.path.realpath(skills / 'aws-s3'),
            'a file that is not a skill directory is in the way',
        )
    ]


def test_install_skill_returns_empty_when_installed(tmp_path):
    (tmp_path / '.test-agent').mkdir()
    zip_bytes, checksum = make_skill_zip()
    agent = make_config(tmp_path).detect()
    assert (
        utils.install_skill('aws-s3', 'v1', zip_bytes, checksum, [agent]) == []
    )


@pytest.fixture
def auto_update_on():
    state.set_auto_update(True)


def _hook_configs(tmp_path, agent_id='claude-code'):
    # The agent whose hook runs, and another agent with its own skills.
    return [
        make_config(tmp_path, id=agent_id),
        make_config(
            tmp_path,
            id='other-agent',
            display_name='Other Agent',
            detection_path=str(tmp_path / '.other'),
        ),
    ]


def _run_hook(tmp_path, agent_id, client, configs=None, extra_args=()):
    stream, error_stream = StringIO(), StringIO()
    cmd = UpdateSkillCommand(
        make_session(),
        stream=stream,
        error_stream=error_stream,
        client=client,
        agent_configs=configs or _hook_configs(tmp_path, agent_id or 'cline'),
    )
    args = ['--hook', *extra_args]
    if agent_id is not None:
        args += ['--agent', agent_id]
    rc = cmd(args=args, parsed_globals=Mock())
    assert error_stream.getvalue() == ''
    return rc, stream.getvalue()


def _last_run(tmp_path, agent_dir='.test-agent'):
    root = os.path.realpath(tmp_path / agent_dir / 'skills')
    return state.get_last_hook_run(root)


def test_hook_does_nothing_when_auto_update_off(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert (rc, output) == (0, '')
    assert not client.get_latest_skill_version.called
    assert state.get_last_hook_runs() == {}


def test_hook_claude_code_output(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-cdk', 'v2')
    rc, output = _run_hook(tmp_path, 'claude-code', _make_skill_client())
    assert rc == 0
    msg = 'AWS agent skills updated: aws-s3.'
    assert output == (
        '{"hookSpecificOutput":{"hookEventName":"SessionStart",'
        f'"additionalContext":"{msg}","reloadSkills":true}},'
        f'"systemMessage":"{msg}"}}\n'
    )
    marker = _skill_dir(tmp_path) / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v2'}
    run = _last_run(tmp_path)
    assert run['is_successful'] is True
    assert run['summary'] == (
        '1 updated, 0 skipped, 0 failed, 1 already up to date'
    )


@pytest.mark.parametrize(
    'agent_id,expected',
    [
        (
            'gemini-cli',
            {
                'systemMessage': 'AWS agent skills updated: aws-s3.',
                'hookSpecificOutput': {
                    'hookEventName': 'SessionStart',
                    'additionalContext': 'AWS agent skills updated: '
                    'aws-s3. Run /skills reload to use them.',
                },
            },
        ),
        (
            'cursor',
            {'additional_context': 'AWS agent skills updated: aws-s3.'},
        ),
        ('codex', 'AWS agent skills updated: aws-s3.\n'),
        ('kiro', 'AWS agent skills updated: aws-s3.\n'),
    ],
)
def test_hook_output_per_agent(tmp_path, auto_update_on, agent_id, expected):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    rc, output = _run_hook(tmp_path, agent_id, _make_skill_client())
    assert rc == 0
    assert output.endswith('\n') and output.count('\n') == 1
    if isinstance(expected, dict):
        assert json.loads(output) == expected
    else:
        assert output == expected
    # Recorded against the skills root, whichever agent's hook ran.
    assert _last_run(tmp_path)['is_successful'] is True


def test_hook_prints_nothing_when_up_to_date(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    rc, output = _run_hook(tmp_path, 'claude-code', _make_skill_client())
    assert (rc, output) == (0, '')
    assert _last_run(tmp_path)['summary'] == (
        '0 updated, 0 skipped, 0 failed, 1 already up to date'
    )


def test_hook_prints_nothing_without_skills_or_agents(
    tmp_path, auto_update_on
):
    client = _make_skill_client()
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert (rc, output) == (0, '')
    assert not client.get_latest_skill_version.called
    assert state.get_last_hook_runs() == {}


def test_hook_reports_failures(tmp_path, auto_update_on):
    for name in ('aws-cdk', 'aws-s3'):
        _install_skill_at_version(tmp_path, '.test-agent', name, 'v1')
    client = _make_skill_client(bad_checksum_skill='aws-s3')
    rc, output = _run_hook(tmp_path, 'codex', client)
    assert rc == 1
    assert output == (
        'AWS agent skills updated: aws-cdk. Could not update aws-s3; run '
        '"aws agent-toolkit update-skill --all" for details.\n'
    )
    run = _last_run(tmp_path)
    assert run['is_successful'] is False
    assert run['summary'] == (
        '1 updated, 0 skipped, 1 failed, 0 already up to date'
    )


def test_hook_failure_without_updates_does_not_reload(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client(bad_checksum_skill='aws-s3')
    _, output = _run_hook(tmp_path, 'claude-code', client)
    assert 'reloadSkills' not in output
    assert json.loads(output)['systemMessage'].startswith(
        'Could not update aws-s3;'
    )


def test_hook_reports_skipped(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-cdk', 'v1')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    real_install_dir = utils._install_skill_dir

    def install_dir(skill_name, *args):
        if skill_name == 'aws-s3':
            return 'a reason'
        return real_install_dir(skill_name, *args)

    with patch.object(utils, '_install_skill_dir', side_effect=install_dir):
        _, output = _run_hook(tmp_path, 'kiro', _make_skill_client())
    assert output == 'AWS agent skills updated: aws-cdk. Skipped aws-s3.\n'


@pytest.mark.parametrize(
    'error', [NoCredentialsError(), RuntimeError('boom'), OSError('nope')]
)
def test_hook_unexpected_error_exits_with_error(
    tmp_path, auto_update_on, error
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    client.get_latest_skill_version.side_effect = error
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert rc == 1
    assert json.loads(output)['systemMessage'] == hooks.HOOK_ERROR_MESSAGE
    assert _last_run(tmp_path)['is_successful'] is False


def test_hook_error_creating_client_exits_with_error(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.create_client',
        side_effect=NoCredentialsError(),
    ):
        rc, output = _run_hook(tmp_path, 'cursor', None)
    assert rc == 1
    assert json.loads(output) == {
        'additional_context': hooks.HOOK_ERROR_MESSAGE
    }


@pytest.mark.parametrize(
    'error',
    [
        ReadTimeoutError(endpoint_url='https://example.com'),
        EndpointConnectionError(endpoint_url='https://example.com'),
    ],
)
def test_hook_error_keeps_skills_already_updated(
    tmp_path, auto_update_on, error
):
    for name in ('aws-cdk', 'aws-s3'):
        _install_skill_at_version(tmp_path, '.test-agent', name, 'v1')
    client = _make_skill_client()
    client.get_latest_skill_version.side_effect = [{'body': 'v2'}, error]
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert rc == 1
    msg = f'AWS agent skills updated: aws-cdk. {hooks.HOOK_ERROR_MESSAGE}'
    assert json.loads(output) == {
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': msg,
            'reloadSkills': True,
        },
        'systemMessage': msg,
    }
    assert _last_run(tmp_path)['is_successful'] is False


def test_hook_client_fails_fast(tmp_path, auto_update_on):
    # Agents stop the hook after 60 seconds.
    assert HOOK_CLIENT_CONFIG.connect_timeout == 5
    assert HOOK_CLIENT_CONFIG.read_timeout == 10
    assert HOOK_CLIENT_CONFIG.retries == {'max_attempts': 1}
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.create_client',
        return_value=_make_skill_client(),
    ) as create_client:
        _run_hook(tmp_path, 'codex', None)
    assert create_client.call_args.kwargs == {'config': HOOK_CLIENT_CONFIG}


def test_update_all_uses_default_client_config(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    cmd, _, _ = _make_update_command(tmp_path, None)
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.create_client',
        return_value=_make_skill_client(),
    ) as create_client:
        cmd(args=['--all'], parsed_globals=Mock())
    assert create_client.call_args.kwargs == {'config': None}


def test_hook_command_ignores_auto_prompt_setting(
    tmp_path, monkeypatch, capsys
):
    # Agents run the hook without a terminal, so prompting would fail.
    config_file = tmp_path / 'config'
    config_file.write_text('[default]\ncli_auto_prompt = on\n')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(config_file))
    monkeypatch.setenv('AWS_CLI_AUTO_PROMPT', 'on')
    for name in ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE'):
        monkeypatch.delenv(name, raising=False)
    state.set_auto_update(False)
    args = hooks.hook_command('codex').split()[1:]
    assert AWSCLIEntryPoint().main(args) == 0
    assert capsys.readouterr() == ('', '')


def test_hook_error_resolving_agents_exits_with_error(
    tmp_path, auto_update_on
):
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.resolve_agents',
        side_effect=ValueError('bad'),
    ):
        rc, output = _run_hook(tmp_path, 'kiro', _make_skill_client())
    assert (rc, output) == (1, f'{hooks.HOOK_ERROR_MESSAGE}\n')


def test_hook_record_failure_is_ignored(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch(
        'awscli.customizations.agenttoolkit.update_skill.record_hook_run',
        side_effect=state.StateFileError('locked'),
    ) as record:
        rc, output = _run_hook(tmp_path, 'codex', _make_skill_client())
    assert rc == 0
    assert output == 'AWS agent skills updated: aws-s3.\n'
    assert record.call_args.args == (
        os.path.realpath(tmp_path / '.test-agent' / 'skills'),
    )
    assert record.call_args.kwargs['is_successful'] is True
    assert record.call_args.kwargs['summary'] == (
        '1 updated, 0 skipped, 0 failed, 0 already up to date'
    )


def test_hook_accepts_all(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    rc, output = _run_hook(
        tmp_path, 'codex', _make_skill_client(), extra_args=['--all']
    )
    assert rc == 0
    assert output == 'AWS agent skills updated: aws-s3.\n'


def test_hook_rejects_skill_name(tmp_path):
    with pytest.raises(ParamValidationError, match='--skill-name together'):
        _run_hook(
            tmp_path,
            'codex',
            Mock(),
            extra_args=['--skill-name', 'aws-s3'],
        )


def test_hook_without_agent_updates_every_agent(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.other', 'aws-cdk', 'v1')
    rc, output = _run_hook(tmp_path, None, _make_skill_client())
    assert rc == 0
    # Without an agent, the summary is plain text.
    assert output == 'AWS agent skills updated: aws-cdk, aws-s3.\n'
    assert _last_run(tmp_path)['is_successful'] is True
    assert _last_run(tmp_path, '.other')['is_successful'] is True


def test_hook_agent_without_hook_format_gets_plain_text(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    rc, output = _run_hook(tmp_path, 'cline', _make_skill_client())
    assert (rc, output) == (0, 'AWS agent skills updated: aws-s3.\n')


def test_hook_agent_is_case_insensitive(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    configs = _hook_configs(tmp_path, 'cursor')
    rc, output = _run_hook(
        tmp_path, 'Cursor', _make_skill_client(), configs=configs
    )
    assert rc == 0
    assert json.loads(output) == {
        'additional_context': 'AWS agent skills updated: aws-s3.'
    }


def test_hook_rejects_unknown_agent(tmp_path):
    client = Mock()
    with pytest.raises(ParamValidationError, match='Invalid agent "nope"'):
        _run_hook(tmp_path, 'nope', client, configs=_hook_configs(tmp_path))
    assert not client.mock_calls


def test_hook_installs_new_core_skills(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    # Another agent's skills are left alone.
    (tmp_path / '.other').mkdir()
    client = _make_skill_client(core_skills=['aws-s3', 'aws-iam'])
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert rc == 0
    msg = 'New AWS core skills installed: aws-iam.'
    assert json.loads(output) == {
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': msg,
            'reloadSkills': True,
        },
        'systemMessage': msg,
    }
    marker = _skill_dir(tmp_path, 'aws-iam') / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v2'}
    assert not (tmp_path / '.other' / 'skills').exists()
    client.get_paginator.assert_called_once_with('list_skills')
    client.get_paginator.return_value.paginate.assert_called_once_with(
        categoryFilter='aws-core'
    )
    # Only the new skill is downloaded.
    assert [
        c.kwargs['name'] for c in client.get_skill_file.call_args_list
    ] == ['aws-iam']
    assert _last_run(tmp_path)['summary'] == (
        '1 installed, 0 updated, 0 skipped, 0 failed, 1 already up to date'
    )


def test_hook_leaves_other_agents_alone(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.other', 'aws-s3', 'v1')
    client = _make_skill_client(core_skills=['aws-iam'])
    _, output = _run_hook(tmp_path, 'kiro', client)
    assert output == (
        'AWS agent skills updated: aws-s3. '
        'New AWS core skills installed: aws-iam.\n'
    )
    assert (_skill_dir(tmp_path, 'aws-iam') / 'SKILL.md').read_text() == 'new'
    other = tmp_path / '.other' / 'skills'
    marker = other / 'aws-s3' / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v1'}
    assert not (other / 'aws-iam').exists()
    assert _last_run(tmp_path, '.other') is None


def test_hook_reinstalls_removed_core_skill(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-iam', 'v2')
    remove = RemoveCommand(
        make_session(),
        stream=StringIO(),
        agent_configs=_hook_configs(tmp_path),
    )
    remove(args=['--skill-name', 'aws-iam'], parsed_globals=Mock())
    assert not _skill_dir(tmp_path, 'aws-iam').exists()
    client = _make_skill_client(core_skills=['aws-iam'])
    _, output = _run_hook(tmp_path, 'kiro', client)
    assert output == 'New AWS core skills installed: aws-iam.\n'
    assert (_skill_dir(tmp_path, 'aws-iam') / 'SKILL.md').read_text() == 'new'


def test_hook_leaves_skill_it_did_not_install(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    mine = _skill_dir(tmp_path, 'aws-iam')
    mine.mkdir()
    (mine / 'SKILL.md').write_text('mine')
    client = _make_skill_client(core_skills=['aws-iam'])
    rc, output = _run_hook(tmp_path, 'claude-code', client)
    assert (rc, output) == (0, '')
    assert (mine / 'SKILL.md').read_text() == 'mine'
    assert not client.get_skill_file.called
    assert _last_run(tmp_path)['summary'] == (
        '0 updated, 1 skipped, 0 failed, 1 already up to date'
    )


def test_hook_reports_core_skill_install_failure(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    client = _make_skill_client(
        bad_checksum_skill='aws-iam', core_skills=['aws-iam']
    )
    _, output = _run_hook(tmp_path, 'codex', client)
    assert output == (
        'Could not install aws-iam; run "aws agent-toolkit add-skill '
        '--skill-name aws-iam" for details.\n'
    )
    assert not _skill_dir(tmp_path, 'aws-iam').exists()
    run = _last_run(tmp_path)
    assert run['is_successful'] is False
    assert run['summary'] == (
        '0 updated, 0 skipped, 1 failed, 1 already up to date'
    )


def test_hook_core_skill_download_timeout_fails_only_that_skill(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    client = _make_skill_client(core_skills=['aws-cdk', 'aws-iam'])
    download = client.get_skill_file.side_effect

    def get_skill_file(name, **kwargs):
        if name == 'aws-cdk':
            raise ReadTimeoutError(endpoint_url='https://example.com')
        return download(name=name, **kwargs)

    client.get_skill_file.side_effect = get_skill_file
    _, output = _run_hook(tmp_path, 'kiro', client)
    assert output == (
        'New AWS core skills installed: aws-iam. Could not install aws-cdk; '
        'run "aws agent-toolkit add-skill --skill-name aws-cdk" for '
        'details.\n'
    )
    assert (_skill_dir(tmp_path, 'aws-iam') / 'SKILL.md').exists()


def test_hook_core_skill_connection_error_ends_run(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    client = _make_skill_client(core_skills=['aws-cdk', 'aws-iam'])
    client.get_skill_file.side_effect = EndpointConnectionError(
        endpoint_url='https://example.com'
    )
    _, output = _run_hook(tmp_path, 'kiro', client)
    assert output == f'{hooks.HOOK_ERROR_MESSAGE}\n'
    assert client.get_skill_file.call_count == 1


def test_hook_lists_core_skills_only_when_skills_installed(
    tmp_path, auto_update_on
):
    (tmp_path / '.test-agent').mkdir()
    client = _make_skill_client(core_skills=['aws-iam'])
    assert _run_hook(tmp_path, 'claude-code', client) == (0, '')
    assert not client.get_paginator.called


def test_update_all_does_not_install_core_skills(tmp_path):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    client = _make_skill_client(core_skills=['aws-iam'])
    cmd, _, _ = _make_update_command(tmp_path, client)
    assert cmd(args=['--all'], parsed_globals=Mock()) == 0
    assert not client.get_paginator.called
    assert not _skill_dir(tmp_path, 'aws-iam').exists()


def test_hook_run_right_after_another_does_nothing(tmp_path, auto_update_on):
    # Kiro V3 runs both its standalone hook and the agent's agentSpawn hook.
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _, output = _run_hook(tmp_path, 'kiro', _make_skill_client())
    assert output == 'AWS agent skills updated: aws-s3.\n'
    first = _last_run(tmp_path)
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    rc, output = _run_hook(tmp_path, 'kiro', client)
    assert (rc, output) == (0, '')
    assert not client.get_latest_skill_version.called
    assert _last_run(tmp_path) == first


def test_hook_run_for_another_agent_skips_checked_root(
    tmp_path, auto_update_on
):
    # The skills root was just checked through another agent's hook.
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _run_hook(tmp_path, 'kiro', _make_skill_client())
    client = _make_skill_client()
    assert _run_hook(tmp_path, 'codex', client) == (0, '')
    assert not client.get_latest_skill_version.called


def _record_check(tmp_path, age, is_successful=True, agent_dir='.test-agent'):
    state.record_hook_run(
        os.path.realpath(tmp_path / agent_dir / 'skills'),
        is_successful=is_successful,
        summary='old',
        timestamp=datetime.datetime.now(datetime.timezone.utc) - age,
    )


@pytest.mark.parametrize(
    'age,is_successful,is_checked',
    [
        (update_skill.HOOK_CHECK_INTERVAL, True, True),
        (
            update_skill.HOOK_CHECK_INTERVAL - datetime.timedelta(minutes=1),
            True,
            False,
        ),
        (update_skill.HOOK_RETRY_INTERVAL, False, True),
        (
            update_skill.HOOK_RETRY_INTERVAL - datetime.timedelta(minutes=1),
            False,
            False,
        ),
        # A check recorded in the future means the clock moved back.
        (-datetime.timedelta(days=7), True, True),
    ],
)
def test_hook_checks_root_once_interval_passed(
    tmp_path, auto_update_on, age, is_successful, is_checked
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _record_check(tmp_path, age, is_successful)
    client = _make_skill_client()
    _, output = _run_hook(tmp_path, 'kiro', client)
    assert client.get_latest_skill_version.called is is_checked
    expected = 'AWS agent skills updated: aws-s3.\n' if is_checked else ''
    assert output == expected


def test_hook_checks_only_roots_that_are_due(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.other', 'aws-cdk', 'v1')
    _record_check(tmp_path, datetime.timedelta(minutes=1))
    _, output = _run_hook(tmp_path, None, _make_skill_client())
    assert output == 'AWS agent skills updated: aws-cdk.\n'
    # The root that wasn't due keeps its record and its old skill.
    assert _last_run(tmp_path)['summary'] == 'old'
    marker = _skill_dir(tmp_path) / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v1'}
    assert _last_run(tmp_path, '.other')['is_successful'] is True


def test_hook_records_failure_only_for_root_with_failed_skill(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.other', 'aws-cdk', 'v1')
    client = _make_skill_client(bad_checksum_skill='aws-s3')
    _run_hook(tmp_path, None, client)
    assert _last_run(tmp_path)['is_successful'] is False
    assert _last_run(tmp_path, '.other')['is_successful'] is True


def test_hook_records_failure_for_every_root_on_error(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    _install_skill_at_version(tmp_path, '.other', 'aws-cdk', 'v1')
    client = _make_skill_client()
    client.get_latest_skill_version.side_effect = EndpointConnectionError(
        endpoint_url='https://example.com'
    )
    _run_hook(tmp_path, None, client)
    assert _last_run(tmp_path)['is_successful'] is False
    assert _last_run(tmp_path, '.other')['is_successful'] is False


def test_hook_installs_core_skill_into_each_agent_missing_it(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    _install_skill_at_version(tmp_path, '.other', 'aws-s3', 'v2')
    _install_skill_at_version(tmp_path, '.other', 'aws-iam', 'v2')
    client = _make_skill_client(core_skills=['aws-iam'])
    _, output = _run_hook(tmp_path, None, client)
    assert output == 'New AWS core skills installed: aws-iam.\n'
    assert (_skill_dir(tmp_path, 'aws-iam') / 'SKILL.md').read_text() == 'new'
    other_skill = tmp_path / '.other' / 'skills' / 'aws-iam' / 'SKILL.md'
    assert other_skill.read_text() == 'name: aws-iam\n'


def test_hook_leaves_skill_dropped_from_catalog(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-gone', 'v1')
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v2')
    client = _make_skill_client()
    _drop_from_catalog(client, 'aws-gone')
    assert _run_hook(tmp_path, 'codex', client) == (0, '')
    run = _last_run(tmp_path)
    assert run['is_successful'] is True
    assert run['summary'] == (
        '0 updated, 0 skipped, 0 failed, 1 already up to date'
    )
    marker = _skill_dir(tmp_path, 'aws-gone') / SKILL_METADATA_FILENAME
    assert json.loads(marker.read_text()) == {'version': 'v1'}


def test_hook_does_nothing_while_another_run_holds_the_lock(
    tmp_path, auto_update_on
):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    client = _make_skill_client()
    lock_path = os.path.join(
        state.toolkit_dir(), update_skill.HOOK_LOCK_FILENAME
    )
    with (
        patch.object(update_skill, 'HOOK_LOCK_TIMEOUT', 0.1),
        filelock.file_lock(lock_path),
    ):
        rc, output = _run_hook(tmp_path, 'kiro', client)
    assert (rc, output) == (0, '')
    assert not client.get_latest_skill_version.called


def test_hook_runs_when_it_can_not_lock(tmp_path, auto_update_on):
    _install_skill_at_version(tmp_path, '.test-agent', 'aws-s3', 'v1')
    with patch.object(
        update_skill, 'file_lock', side_effect=PermissionError('denied')
    ):
        rc, output = _run_hook(tmp_path, 'kiro', _make_skill_client())
    assert (rc, output) == (0, 'AWS agent skills updated: aws-s3.\n')
