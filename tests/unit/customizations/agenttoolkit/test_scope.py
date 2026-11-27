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
"""Tests for project-level (``--project``) and global (``--global``) scope."""

import json
import os
import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.agenttoolkit import atomic, utils
from awscli.customizations.agenttoolkit.add_skill import AddSkillCommand
from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
    DetectedAgent,
    Scope,
)
from awscli.customizations.agenttoolkit.check_skill_updates import (
    CheckSkillUpdatesCommand,
)
from awscli.customizations.agenttoolkit.list_installed_skills import (
    ListInstalledSkillsCommand,
)
from awscli.customizations.agenttoolkit.remove_skill import RemoveCommand
from awscli.customizations.agenttoolkit.update_skill import (
    UpdateSkillCommand,
)
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agenttoolkit.utils import (
    make_config,
    make_junction,
    make_parsed_globals,
    make_session,
    make_skill_zip,
    requires_junctions,
    requires_symlinks,
)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A project directory that is the current directory, with the agent
    installed in the home directory (``tmp_path``)."""
    (tmp_path / '.test-agent').mkdir()
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.chdir(repo)
    return repo


def _write_skill(skills_dir, name, version='v1'):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(f'{name} {version}')
    (skill_dir / SKILL_METADATA_FILENAME).write_text(
        json.dumps({'version': version})
    )
    return skill_dir


def _version(skill_dir):
    return json.loads((skill_dir / SKILL_METADATA_FILENAME).read_text())[
        'version'
    ]


def _run_add(configs, args, version='v2'):
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    stream = StringIO()
    with (
        patch(
            'awscli.customizations.agenttoolkit.add_skill.get_skill_download',
            return_value=(zip_bytes, checksum, version),
        ),
        patch('awscli.customizations.agenttoolkit.add_skill.create_client'),
    ):
        cmd = AddSkillCommand(
            make_session(), stream=stream, agent_configs=configs
        )
        rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def _run_remove(configs, args):
    stream = StringIO()
    cmd = RemoveCommand(make_session(), stream=stream, agent_configs=configs)
    rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def _run_update(configs, args, version='v2'):
    zip_bytes, checksum = make_skill_zip({'SKILL.md': 'new'})
    stream = StringIO()
    module = 'awscli.customizations.agenttoolkit.update_skill'
    with (
        patch(f'{module}.resolve_latest_version', return_value=version),
        patch(
            f'{module}.get_skill_download',
            return_value=(zip_bytes, checksum, version),
        ),
        patch(f'{module}.create_client'),
    ):
        cmd = UpdateSkillCommand(
            make_session(), stream=stream, agent_configs=configs
        )
        rc = cmd(args=args, parsed_globals=Mock())
    return rc, stream.getvalue()


def _run_list(monkeypatch, configs, args):
    stream = StringIO()
    monkeypatch.setattr('sys.stdout', stream)
    cmd = ListInstalledSkillsCommand(make_session(), agent_configs=configs)
    cmd(args=args, parsed_globals=make_parsed_globals())
    return json.loads(stream.getvalue())


# Scope resolution


def _args(**kwargs):
    return SimpleNamespace(**kwargs)


def test_resolve_scopes_defaults_to_global(tmp_path):
    assert utils.resolve_scopes(_args(), cwd=str(tmp_path / 'repo')) == [
        (Scope.GLOBAL, None)
    ]


def test_resolve_scopes_global_flag(tmp_path):
    args = _args(**{'global': True})
    assert utils.resolve_scopes(args, cwd=str(tmp_path)) == [
        (Scope.GLOBAL, None)
    ]


def test_resolve_scopes_project_uses_current_directory(tmp_path):
    repo = str(tmp_path / 'repo')
    assert utils.resolve_scopes(_args(project=True), cwd=repo) == [
        (Scope.PROJECT, repo)
    ]


def test_resolve_scopes_rejects_both_flags(tmp_path):
    args = _args(project=True, **{'global': True})
    with pytest.raises(ParamValidationError, match='--project together'):
        utils.resolve_scopes(args, cwd=str(tmp_path))


def test_resolve_scopes_both_by_default(tmp_path):
    repo = str(tmp_path / 'repo')
    assert utils.resolve_scopes(_args(), cwd=repo, both_by_default=True) == [
        (Scope.GLOBAL, None),
        (Scope.PROJECT, repo),
    ]


@pytest.mark.parametrize(
    'flags, expected',
    [
        ({'global': True}, [(Scope.GLOBAL, None)]),
        ({'project': True}, [(Scope.PROJECT, 'REPO')]),
    ],
)
def test_resolve_scopes_flag_picks_one(tmp_path, flags, expected):
    repo = str(tmp_path / 'repo')
    expected = [(s, repo if d == 'REPO' else d) for s, d in expected]
    result = utils.resolve_scopes(
        _args(**flags), cwd=repo, both_by_default=True
    )
    assert result == expected


def test_resolve_agents_in_home_lists_agent_once(tmp_path):
    # Without an override, both scopes name the same directories.
    (tmp_path / '.test-agent').mkdir()
    agents = utils.resolve_agents_in_scopes(
        None,
        [make_config(tmp_path)],
        utils.resolve_scopes(_args(), cwd=str(tmp_path), both_by_default=True),
    )
    assert [a.scope for a in agents] == [Scope.GLOBAL]


def test_resolve_agents_in_home_keeps_project_when_override_moves_global(
    tmp_path, monkeypatch
):
    (tmp_path / '.test-agent').mkdir()
    moved = tmp_path / 'moved'
    moved.mkdir()
    monkeypatch.setenv('TEST_AGENT_DIR', str(moved))
    config = make_config(
        tmp_path, detection_path_env_override='TEST_AGENT_DIR'
    )
    agents = utils.resolve_agents_in_scopes(
        None,
        [config],
        utils.resolve_scopes(_args(), cwd=str(tmp_path), both_by_default=True),
    )
    assert [(a.scope, a.skills_path) for a in agents] == [
        (Scope.GLOBAL, str(moved / 'skills')),
        (Scope.PROJECT, str(tmp_path / '.test-agent' / 'skills')),
    ]


def test_add_skill_project_in_home_ignores_global_override(
    tmp_path, monkeypatch
):
    (tmp_path / '.test-agent').mkdir()
    moved = tmp_path / 'moved'
    moved.mkdir()
    monkeypatch.setenv('TEST_AGENT_DIR', str(moved))
    config = make_config(
        tmp_path, detection_path_env_override='TEST_AGENT_DIR'
    )
    rc, _ = _run_add([config], ['--skill-name', 'aws-s3', '--project'])
    assert rc == 0
    assert (tmp_path / '.test-agent' / 'skills' / 'aws-s3').is_dir()
    assert not (moved / 'skills' / 'aws-s3').exists()


@pytest.fixture
def cwd_deleted(monkeypatch):
    # os.getcwd() fails when the current directory has been deleted.
    def fail():
        raise FileNotFoundError('current directory was deleted')

    monkeypatch.setattr(os, 'getcwd', fail)


@pytest.mark.parametrize(
    'args, both_by_default',
    [({}, False), ({'global': True}, False), ({'global': True}, True)],
)
def test_resolve_scopes_global_does_not_need_cwd(
    cwd_deleted, args, both_by_default
):
    assert utils.resolve_scopes(
        _args(**args), both_by_default=both_by_default
    ) == [(Scope.GLOBAL, None)]


def test_resolve_scopes_default_falls_back_to_global_without_cwd(
    cwd_deleted,
):
    assert utils.resolve_scopes(_args(), both_by_default=True) == [
        (Scope.GLOBAL, None)
    ]


def test_resolve_scopes_project_without_cwd_fails_clearly(cwd_deleted):
    with pytest.raises(ParamValidationError, match='current directory'):
        utils.resolve_scopes(_args(project=True))


# Windows does not let a process's current directory be deleted, and its
# os.path.realpath calls os.getcwd, so the fixture would break more than
# the current directory lookup.
requires_deletable_cwd = pytest.mark.skipif(
    sys.platform == 'win32',
    reason='The current directory cannot be deleted on Windows.',
)


@requires_deletable_cwd
def test_add_skill_global_works_when_cwd_deleted(tmp_path, cwd_deleted):
    (tmp_path / '.test-agent').mkdir()
    rc, _ = _run_add([make_config(tmp_path)], ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert (tmp_path / '.test-agent' / 'skills' / 'aws-s3').is_dir()


@requires_deletable_cwd
def test_update_hook_works_when_cwd_deleted(tmp_path, cwd_deleted):
    # Without a current directory the hook still updates global skills.
    (tmp_path / '.test-agent').mkdir()
    rc, _ = _run_update([make_config(tmp_path)], ['--hook'])
    assert rc == 0


def test_resolve_scopes_project_in_home_is_project(tmp_path):
    # The conftest points the home directory at tmp_path.
    assert utils.resolve_scopes(_args(project=True), cwd=str(tmp_path)) == [
        (Scope.PROJECT, str(tmp_path))
    ]


# Agent model


def test_project_skills_paths_resolve_against_project_dir(tmp_path, repo):
    config = make_config(
        tmp_path, skills_paths=['.agents/skills', '.test-agent/skills']
    )
    agent = config.detect(Scope.PROJECT, str(repo))
    assert agent.scope is Scope.PROJECT
    assert agent.skills_paths == [
        str(repo / '.agents' / 'skills'),
        str(repo / '.test-agent' / 'skills'),
    ]
    assert agent.skills_path == str(repo / '.agents' / 'skills')


def test_global_skills_paths_unchanged_by_default(tmp_path, repo):
    agent = make_config(tmp_path).detect()
    assert agent.scope is Scope.GLOBAL
    assert agent.skills_paths == [str(tmp_path / '.test-agent' / 'skills')]


def test_project_scope_ignores_detection_env_override(
    tmp_path, repo, monkeypatch
):
    override = tmp_path / 'override'
    override.mkdir()
    monkeypatch.setenv('TEST_CONFIG_DIR', str(override))
    config = make_config(
        tmp_path, detection_path_env_override='TEST_CONFIG_DIR'
    )
    assert config.detect().skills_paths == [str(override / 'skills')]
    assert config.detect(Scope.PROJECT, str(repo)).skills_paths == [
        str(repo / '.test-agent' / 'skills')
    ]


def test_project_scope_requires_project_dir(tmp_path):
    with pytest.raises(ValueError, match='project directory'):
        DetectedAgent(make_config(tmp_path), str(tmp_path), Scope.PROJECT)


def test_project_scope_detects_agents_from_home(tmp_path, repo):
    missing = make_config(
        tmp_path, id='missing', detection_path=str(tmp_path / '.missing')
    )
    assert missing.detect(Scope.PROJECT, str(repo)) is None


# Commands


def test_add_skill_project_installs_into_current_directory(tmp_path, repo):
    rc, output = _run_add(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    project_skill = repo / '.test-agent' / 'skills' / 'aws-s3'
    assert _version(project_skill) == 'v2'
    assert os.path.join('~', 'repo', '.test-agent', 'skills') in output
    assert not (tmp_path / '.test-agent' / 'skills').exists()


def test_add_skill_global_flag_installs_globally(tmp_path, repo):
    rc, _ = _run_add(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--global']
    )
    assert rc == 0
    assert (tmp_path / '.test-agent' / 'skills' / 'aws-s3').is_dir()
    assert not (repo / '.test-agent').exists()


def test_add_skill_project_writes_shared_directory_once(tmp_path, repo):
    (tmp_path / '.agent-b').mkdir()
    configs = [
        make_config(tmp_path, skills_paths=['.agents/skills']),
        make_config(
            tmp_path,
            id='b',
            display_name='Agent B',
            detection_path=str(tmp_path / '.agent-b'),
            skills_paths=['.agents/skills'],
        ),
    ]
    rc, output = _run_add(configs, ['--skill-name', 'aws-s3', '--project'])
    assert rc == 0
    assert output.count('Installed aws-s3') == 1
    assert (repo / '.agents' / 'skills' / 'aws-s3' / 'SKILL.md').exists()


def test_add_skill_project_does_not_touch_global_copy(tmp_path, repo):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_add(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    assert _version(global_skill) == 'v1'
    assert _version(repo / '.test-agent' / 'skills' / 'aws-s3') == 'v2'


def test_add_skill_rejects_both_scope_flags(tmp_path, repo):
    with pytest.raises(ParamValidationError, match='--project together'):
        _run_add(
            [make_config(tmp_path)],
            ['--skill-name', 'aws-s3', '--project', '--global'],
        )


def test_remove_skill_project_keeps_global_copy(tmp_path, repo):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, output = _run_remove(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    assert output.count('Removed aws-s3') == 1
    assert not project_skill.exists()
    assert global_skill.is_dir()


def test_remove_skill_default_keeps_project_copy(tmp_path, repo):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_remove([make_config(tmp_path)], ['--skill-name', 'aws-s3'])
    assert rc == 0
    assert not global_skill.exists()
    assert project_skill.is_dir()


def test_update_skill_project_updates_only_project_copy(tmp_path, repo):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_update(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    assert _version(project_skill) == 'v2'
    assert _version(global_skill) == 'v1'


@pytest.mark.parametrize(
    'args', [['--all'], ['--skill-name', 'aws-s3']], ids=['all', 'one']
)
def test_update_skill_default_updates_both_scopes(tmp_path, repo, args):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_update([make_config(tmp_path)], args)
    assert rc == 0
    assert _version(global_skill) == 'v2'
    assert _version(project_skill) == 'v2'


def test_update_skill_global_updates_only_global_copy(tmp_path, repo):
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_update([make_config(tmp_path)], ['--all', '--global'])
    assert rc == 0
    assert _version(global_skill) == 'v2'
    assert _version(project_skill) == 'v1'


def test_update_skill_default_finds_project_only_skill(tmp_path, repo):
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, output = _run_update(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3']
    )
    assert rc == 0
    assert _version(project_skill) == 'v2'
    assert output.count('Updated aws-s3') == 1


def test_update_skill_in_home_updates_once(tmp_path, monkeypatch):
    # In the home directory both scopes are the same directory.
    (tmp_path / '.test-agent').mkdir()
    monkeypatch.chdir(tmp_path)
    global_skill = _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    rc, output = _run_update([make_config(tmp_path)], ['--all'])
    assert rc == 0
    assert _version(global_skill) == 'v2'
    assert output.count('Updated aws-s3') == 1


@pytest.mark.parametrize('flag', ['--project', '--global'])
def test_update_skill_rejects_scope_flag_with_hook(tmp_path, repo, flag):
    with pytest.raises(ParamValidationError, match='together with --hook'):
        _run_update([make_config(tmp_path)], ['--hook', flag])


def test_list_installed_skills_by_scope(tmp_path, repo, monkeypatch):
    _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-global')
    _write_skill(repo / '.test-agent' / 'skills', 'aws-project')
    configs = [make_config(tmp_path)]

    def names(args):
        result = _run_list(monkeypatch, configs, args)
        return [(s['scope'], s['name']) for s in result['skills']]

    assert names([]) == [('global', 'aws-global'), ('project', 'aws-project')]
    assert names(['--global']) == [('global', 'aws-global')]
    assert names(['--project']) == [('project', 'aws-project')]


def test_list_installed_skills_in_home_lists_once(tmp_path, monkeypatch):
    (tmp_path / '.test-agent').mkdir()
    _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-s3')
    result = _run_list(monkeypatch, [make_config(tmp_path)], [])
    assert [(s['scope'], s['name']) for s in result['skills']] == [
        ('global', 'aws-s3')
    ]


def test_check_skill_updates_by_scope(tmp_path, repo, monkeypatch):
    _write_skill(tmp_path / '.test-agent' / 'skills', 'aws-global')
    _write_skill(repo / '.test-agent' / 'skills', 'aws-project')
    stream = StringIO()
    monkeypatch.setattr('sys.stdout', stream)
    module = 'awscli.customizations.agenttoolkit.check_skill_updates'
    with patch(f'{module}.resolve_latest_version', return_value='v2'):
        cmd = CheckSkillUpdatesCommand(
            make_session(),
            agent_configs=[make_config(tmp_path)],
            client=Mock(),
        )
        cmd(args=[], parsed_globals=make_parsed_globals())
    rows = json.loads(stream.getvalue())['skills']
    assert [(r['scope'], r['name']) for r in rows] == [
        ('global', 'aws-global'),
        ('project', 'aws-project'),
    ]


def test_skill_metadata_has_no_paths(tmp_path, repo):
    # Project skills may be committed, so the metadata must be portable.
    _run_add([make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project'])
    skill_dir = repo / '.test-agent' / 'skills' / 'aws-s3'
    content = (skill_dir / SKILL_METADATA_FILENAME).read_text()
    assert json.loads(content) == {'version': 'v2'}
    assert str(tmp_path) not in content


# Symbolic links


def _link_project_skills_to(repo, target):
    (repo / '.test-agent').mkdir()
    (repo / '.test-agent' / 'skills').symlink_to(
        target, target_is_directory=True
    )


@requires_symlinks
def test_can_write_follows_symlinks_by_default(tmp_path, repo):
    outside = tmp_path / 'outside'
    outside.mkdir()
    _link_project_skills_to(repo, outside)
    agent = make_config(tmp_path).detect(Scope.PROJECT, str(repo))
    assert agent.can_write(str(repo / '.test-agent' / 'skills' / 'aws-s3'))


@requires_symlinks
def test_can_write_refuses_path_under_symlink_when_not_following(
    tmp_path, repo
):
    outside = tmp_path / 'outside'
    outside.mkdir()
    _link_project_skills_to(repo, outside)
    (repo / '.other' / 'skills').mkdir(parents=True)
    agent = make_config(tmp_path).detect(
        Scope.PROJECT, str(repo), follow_symlinks=False
    )
    assert not agent.can_write(str(repo / '.test-agent' / 'skills' / 'aws-s3'))
    assert agent.can_write(str(repo / '.other' / 'skills' / 'aws-s3'))


@requires_junctions
def test_can_write_refuses_path_under_junction_when_not_following(
    tmp_path, repo
):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (repo / '.test-agent').mkdir()
    make_junction(repo / '.test-agent' / 'skills', outside)
    skill_dir = str(repo / '.test-agent' / 'skills' / 'aws-s3')
    agent = make_config(tmp_path).detect(Scope.PROJECT, str(repo))
    assert agent.can_write(skill_dir)
    agent = make_config(tmp_path).detect(
        Scope.PROJECT, str(repo), follow_symlinks=False
    )
    assert not agent.can_write(skill_dir)


@requires_symlinks
def test_can_write_follows_symlinks_above_project_dir(tmp_path, monkeypatch):
    # Links leading up to the project directory are followed, like aws s3.
    (tmp_path / '.test-agent').mkdir()
    real_repo = tmp_path / 'real-repo'
    real_repo.mkdir()
    linked_repo = tmp_path / 'linked-repo'
    linked_repo.symlink_to(real_repo, target_is_directory=True)
    agent = make_config(tmp_path).detect(
        Scope.PROJECT, str(linked_repo), follow_symlinks=False
    )
    assert agent.can_write(
        str(linked_repo / '.test-agent' / 'skills' / 'aws-s3')
    )


@requires_symlinks
def test_add_skill_project_follows_symlinked_skills_dir(tmp_path, repo):
    outside = tmp_path / 'outside'
    outside.mkdir()
    _link_project_skills_to(repo, outside)
    rc, _ = _run_add(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    assert _version(outside / 'aws-s3') == 'v2'


@requires_symlinks
def test_add_skill_no_follow_symlinks_skips_symlinked_skills_dir(
    tmp_path, repo
):
    outside = tmp_path / 'outside'
    outside.mkdir()
    _link_project_skills_to(repo, outside)
    rc, output = _run_add(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--project', '--no-follow-symlinks'],
    )
    assert rc == 0
    assert 'symbolic link' in output
    assert os.listdir(outside) == []


@requires_symlinks
def test_add_skill_no_follow_symlinks_applies_to_global(tmp_path, repo):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / '.test-agent' / 'skills').symlink_to(
        outside, target_is_directory=True
    )
    rc, output = _run_add(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--no-follow-symlinks'],
    )
    assert rc == 0
    assert 'symbolic link' in output
    assert os.listdir(outside) == []


@requires_symlinks
def test_remove_skill_no_follow_symlinks_skips_symlinked_skills_dir(
    tmp_path, repo
):
    outside_skill = _write_skill(tmp_path / 'outside', 'aws-s3')
    _link_project_skills_to(repo, outside_skill.parent)
    rc, output = _run_remove(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--project', '--no-follow-symlinks'],
    )
    assert rc == 0
    assert 'symbolic link' in output
    assert outside_skill.is_dir()


def _shared_through_link(tmp_path):
    """Two agents whose skills directories are one directory: the first,
    listed before the other, reaches it through a symbolic link."""
    (tmp_path / '.linked').mkdir()
    (tmp_path / '.real').mkdir()
    real_skills = tmp_path / '.real' / 'skills'
    real_skills.mkdir()
    (tmp_path / '.linked' / 'skills').symlink_to(
        real_skills, target_is_directory=True
    )
    return real_skills, [
        make_config(
            tmp_path,
            id='linked',
            detection_path='~/.linked',
            skills_paths=['.linked/skills'],
        ),
        make_config(
            tmp_path,
            id='real',
            detection_path='~/.real',
            skills_paths=['.real/skills'],
        ),
    ]


@requires_symlinks
def test_add_skill_no_follow_symlinks_installs_through_real_path(tmp_path):
    real_skills, configs = _shared_through_link(tmp_path)
    rc, output = _run_add(
        configs, ['--skill-name', 'aws-s3', '--no-follow-symlinks']
    )
    assert rc == 0
    assert (real_skills / 'aws-s3' / 'SKILL.md').is_file()
    assert 'symbolic link' not in output


@requires_symlinks
def test_remove_skill_no_follow_symlinks_removes_through_real_path(tmp_path):
    real_skills, configs = _shared_through_link(tmp_path)
    _write_skill(real_skills, 'aws-s3')
    rc, output = _run_remove(
        configs, ['--skill-name', 'aws-s3', '--no-follow-symlinks']
    )
    assert rc == 0
    assert not (real_skills / 'aws-s3').exists()
    assert 'symbolic link' not in output


def _two_agents(tmp_path):
    for name in ('.a', '.b'):
        (tmp_path / name / 'skills').mkdir(parents=True)
    return [
        make_config(
            tmp_path,
            id=name,
            detection_path=f'~/.{name}',
            skills_paths=[f'.{name}/skills'],
        )
        for name in ('a', 'b')
    ]


@requires_symlinks
def test_remove_skill_no_follow_symlinks_removes_linked_skill(tmp_path):
    configs = _two_agents(tmp_path)
    real_skill = _write_skill(tmp_path / '.b' / 'skills', 'aws-s3')
    link = tmp_path / '.a' / 'skills' / 'aws-s3'
    link.symlink_to(real_skill, target_is_directory=True)
    rc, output = _run_remove(
        configs, ['--skill-name', 'aws-s3', '--no-follow-symlinks']
    )
    assert rc == 0
    assert not os.path.lexists(link)
    assert not real_skill.exists()
    assert 'Skipped' not in output


@requires_symlinks
def test_remove_skill_no_follow_symlinks_unlinks_outside_target(tmp_path):
    configs = _two_agents(tmp_path)
    outside_skill = _write_skill(tmp_path / 'outside', 'aws-s3')
    link = tmp_path / '.a' / 'skills' / 'aws-s3'
    link.symlink_to(outside_skill, target_is_directory=True)
    rc, output = _run_remove(
        configs, ['--skill-name', 'aws-s3', '--no-follow-symlinks']
    )
    assert rc == 0
    assert not os.path.lexists(link)
    # Only the link is removed, never what it points to.
    assert outside_skill.is_dir()
    assert 'Skipped' not in output


@requires_symlinks
def test_remove_skill_project_follows_symlinked_skills_dir(tmp_path, repo):
    outside_skill = _write_skill(tmp_path / 'outside', 'aws-s3')
    _link_project_skills_to(repo, outside_skill.parent)
    rc, _ = _run_remove(
        [make_config(tmp_path)], ['--skill-name', 'aws-s3', '--project']
    )
    assert rc == 0
    assert not outside_skill.exists()


def test_update_skill_accepts_no_follow_symlinks(tmp_path, repo):
    project_skill = _write_skill(repo / '.test-agent' / 'skills', 'aws-s3')
    rc, _ = _run_update(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--project', '--no-follow-symlinks'],
    )
    assert rc == 0
    assert _version(project_skill) == 'v2'


@requires_symlinks
def test_update_skill_no_follow_symlinks_suggests_following(tmp_path, repo):
    outside_skill = _write_skill(tmp_path / 'outside', 'aws-s3')
    _link_project_skills_to(repo, outside_skill.parent)
    rc, output = _run_update(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--project', '--no-follow-symlinks'],
    )
    assert rc == 0
    assert 'without --no-follow-symlinks' in output
    assert 'move the existing path aside' not in output


@requires_symlinks
def test_add_skill_no_follow_symlinks_reports_link_path(tmp_path, repo):
    outside = tmp_path / 'outside'
    outside.mkdir()
    _link_project_skills_to(repo, outside)
    _, output = _run_add(
        [make_config(tmp_path)],
        ['--skill-name', 'aws-s3', '--project', '--no-follow-symlinks'],
    )
    # The path the customer knows, not the link's target.
    assert os.path.join('.test-agent', 'skills', 'aws-s3') in output
    assert str(outside) not in output


@requires_symlinks
def test_recovery_skips_symlinked_skills_when_not_following(tmp_path, repo):
    target = tmp_path / 'outside' / 'aws-s3'
    target.mkdir(parents=True)
    staging = atomic.make_staging_dir(str(target))
    skills = repo / '.test-agent' / 'skills'
    skills.mkdir(parents=True)
    (skills / 'aws-s3').symlink_to(target, target_is_directory=True)
    agent = make_config(tmp_path).detect(
        Scope.PROJECT, str(repo), follow_symlinks=False
    )
    utils._recover_interrupted_changes([agent])
    assert os.path.exists(staging)

    agent.follow_symlinks = True
    utils._recover_interrupted_changes([agent])
    assert not os.path.exists(staging)


@requires_symlinks
def test_no_follow_symlinks_refuses_symlinked_agent_dir(tmp_path):
    real_agent_dir = tmp_path / 'dotfiles' / 'test-agent'
    real_agent_dir.mkdir(parents=True)
    (tmp_path / '.test-agent').symlink_to(
        real_agent_dir, target_is_directory=True
    )
    agent = make_config(tmp_path).detect(follow_symlinks=False)
    assert not agent.can_write(
        str(tmp_path / '.test-agent' / 'skills' / 'aws-s3')
    )


@requires_symlinks
def test_no_follow_symlinks_checks_override_dir_like_agent_dir(
    tmp_path, monkeypatch
):
    # A CLAUDE_CONFIG_DIR-style override outside the home directory is
    # checked like the agent's directory in it.
    (tmp_path / '.test-agent').mkdir()
    elsewhere = tmp_path.parent / f'{tmp_path.name}-elsewhere'
    real_override = elsewhere / 'real'
    real_override.mkdir(parents=True)
    linked_override = elsewhere / 'linked'
    linked_override.symlink_to(real_override, target_is_directory=True)
    plain_override = elsewhere / 'plain'
    plain_override.mkdir()
    config = make_config(tmp_path, detection_path_env_override='TEST_DIR')

    monkeypatch.setenv('TEST_DIR', str(linked_override))
    agent = config.detect(follow_symlinks=False)
    assert not agent.can_write(str(linked_override / 'skills' / 'aws-s3'))

    monkeypatch.setenv('TEST_DIR', str(plain_override))
    agent = config.detect(follow_symlinks=False)
    assert agent.can_write(str(plain_override / 'skills' / 'aws-s3'))
