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
"""uninstall-skill: only an installed skill is deleted, only when confirmed."""

import argparse
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from awscli.customizations.agentregistry import install_skill, uninstall_skill
from awscli.customizations.agentregistry.uninstall_skill import (
    UninstallSkillCommand,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.exceptions import ParamValidationError
from tests.unit.customizations.agentregistry.utils import make_agents


def _with_marker(skill, **source):
    marker = {
        'registryId': 'abcDEF123456',
        'recordId': 'rec',
        'endpoint': 'https://agent-registry.us-west-2.api.aws',
        'sha256': '0' * 64,
    }
    marker.update(source)
    with open(os.path.join(skill, install_skill.PROVENANCE_MARKER), 'w') as f:
        json.dump(marker, f)


@pytest.fixture
def skills(tmp_path):
    target = tmp_path / 'skills'
    skill = target / 'pdf-extract'
    (skill / 'lib').mkdir(parents=True)
    (skill / 'SKILL.md').write_text('skill')
    (skill / 'lib' / 'a.py').write_text('code')
    _with_marker(str(skill))
    return target


@pytest.fixture
def terminal():
    with patch.object(uninstall_skill, 'stdin_is_terminal', return_value=True):
        yield


def _command(agent_configs=None):
    session = Mock()
    command = UninstallSkillCommand(
        session, agent_configs=[] if agent_configs is None else agent_configs
    )
    return command, session


def _run(target, name='pdf-extract', yes=False, agent=None, configs=None):
    command, session = _command(configs)
    args = argparse.Namespace(
        name=name,
        target_directory=None if target is None else str(target),
        agent=agent,
        yes=yes,
    )
    globals_ = argparse.Namespace(region=None, endpoint_url=None)
    return command._run_main(args, globals_), session


def _installed(folder, name='pdf-extract', marker=True, **source):
    skill = os.path.join(folder, name)
    os.makedirs(skill)
    with open(os.path.join(skill, 'SKILL.md'), 'w') as f:
        f.write('skill')
    if marker:
        _with_marker(skill, **source)
    return skill


def test_confirmed_removal_deletes_the_skill(skills, terminal, capsys):
    with patch.object(uninstall_skill, 'prompt', return_value='y') as asked:
        rc, session = _run(skills)
    assert rc == 0
    assert not (skills / 'pdf-extract').exists()
    assert skills.exists()
    # The prompt shows the full path being deleted.
    assert (
        str(os.path.realpath(skills / 'pdf-extract')) in asked.call_args[0][0]
    )
    assert '[y/N]' in asked.call_args[0][0]
    # Purely local: no client, no credentials.
    session.create_client.assert_not_called()
    session.get_credentials.assert_not_called()
    assert 'Uninstalled pdf-extract from' in capsys.readouterr().err


def test_yes_skips_the_prompt(skills):
    with (
        patch.object(uninstall_skill, 'prompt') as asked,
        patch.object(uninstall_skill, 'stdin_is_terminal', return_value=False),
    ):
        rc, _ = _run(skills, yes=True)
    assert rc == 0
    asked.assert_not_called()
    assert not (skills / 'pdf-extract').exists()


@pytest.mark.parametrize('answer', ['', 'n', 'no', 'N', 'maybe'])
def test_declining_keeps_the_skill(skills, terminal, answer):
    with patch.object(uninstall_skill, 'prompt', return_value=answer):
        rc, _ = _run(skills)
    assert rc == 1
    assert (skills / 'pdf-extract' / 'SKILL.md').read_text() == 'skill'


def test_non_terminal_without_yes_refuses_without_prompting(skills):
    with (
        patch.object(uninstall_skill, 'prompt') as asked,
        patch.object(uninstall_skill, 'stdin_is_terminal', return_value=False),
    ):
        with pytest.raises(AgentRegistryJWTError, match='--yes'):
            _run(skills)
    asked.assert_not_called()
    assert (skills / 'pdf-extract' / 'SKILL.md').exists()


@pytest.mark.parametrize(
    'name',
    [
        '../victim',
        '..',
        '.',
        'a/b',
        '/abs',
        '',
        'x\n',
        '.hidden',
        'CON',
        'con',
        'nul.md',
        'victim.',
    ],
)
def test_unsafe_names_are_refused(monkeypatch, tmp_path, name):
    # Windows' names included.
    monkeypatch.setattr(install_skill, '_ON_WINDOWS', True)
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'SKILL.md').write_text('keep')
    target = tmp_path / 'skills'
    target.mkdir()
    with pytest.raises(AgentRegistryJWTError, match='Agent Skills'):
        _run(target, name=name, yes=True)
    assert (victim / 'SKILL.md').read_text() == 'keep'


@pytest.mark.parametrize(
    'name',
    [
        '-pdf',
        '_pdf',
        'x' * 65,
        'pdf extract',
        'pdf+extract',
        'p\u00e9f',
    ],
)
def test_names_outside_the_spec_are_refused_before_touching_anything(
    tmp_path, monkeypatch, name
):
    # The Windows-only rules add a clause to the message
    monkeypatch.setattr(install_skill, '_ON_WINDOWS', False)
    # Even a folder of that name with install-skill's marker stays.
    skills = tmp_path / 'skills'
    skill = _installed(skills, name=name)
    with (
        patch.object(uninstall_skill, 'resolve_skill_folders') as resolve,
        pytest.raises(AgentRegistryJWTError) as e,
    ):
        _run(skills, name=name, yes=True)
    resolve.assert_not_called()
    assert os.path.isdir(skill)
    assert str(e.value) == (
        f"Refusing a skill named {name!r}: a skill's folder name must be a "
        'skill name under the Agent Skills specification (at most 64 '
        'lowercase letters, digits and hyphens, with no hyphen at the start '
        'or end and no two hyphens in a row) or, for an older skill, at most '
        '64 letters, digits, dots, underscores and hyphens, beginning with a '
        'letter or digit.'
    )


@pytest.mark.parametrize(
    'name',
    ['pdf_extract', 'Pdf-Extract', 'pdf.extract', 'pdf--extract', 'x' * 64],
)
def test_uninstall_accepts_a_legacy_folder_name(tmp_path, capsys, name):
    skills = tmp_path / 'skills'
    _installed(skills, name=name)
    rc, _ = _run(skills, name=name, yes=True)
    assert rc == 0
    assert not os.path.lexists(skills / name)
    assert f'Uninstalled {name} from' in capsys.readouterr().err


def _case_insensitive(folder):
    probe = os.path.join(folder, 'Case-Probe')
    os.makedirs(probe)
    try:
        return os.path.exists(os.path.join(folder, 'case-probe'))
    finally:
        os.rmdir(probe)


def test_result_line_names_the_folder_as_it_is_on_disk(tmp_path, capsys):
    skills = tmp_path / 'skills'
    _installed(skills)
    if not _case_insensitive(str(skills)):
        pytest.skip('needs a file system that ignores case')
    rc, _ = _run(skills, name='PDF-Extract', yes=True)
    assert rc == 0
    assert not os.path.lexists(skills / 'pdf-extract')
    err = capsys.readouterr().err
    assert 'Uninstalled pdf-extract from' in err
    assert 'PDF-Extract' not in err


def test_on_disk_path_is_the_entry_that_is_the_same_file(tmp_path):
    # Simulates a file system that ignores case, whatever this one does.
    info = os.lstat(tmp_path)
    other = Mock(path=str(tmp_path / 'other'))
    other.name = 'other'
    entry = Mock(path=str(tmp_path / 'pdf-extract'))
    entry.name = 'pdf-extract'
    scandir = MagicMock()
    scandir.return_value.__enter__.return_value = [other, entry]
    typed = str(tmp_path / 'PDF-Extract')
    with (
        patch.object(uninstall_skill.os, 'scandir', scandir),
        patch.object(uninstall_skill.os, 'lstat', return_value=info) as lstat,
    ):
        on_disk = uninstall_skill._on_disk_path(typed)
    assert on_disk == str(tmp_path / 'pdf-extract')
    # Only an entry whose name matches but for case is examined, with
    # os.lstat: on Windows a directory entry's own stat has no file id.
    assert [c.args[0] for c in lstat.call_args_list] == [typed, entry.path]
    other.stat.assert_not_called()
    entry.stat.assert_not_called()


def test_on_disk_path_prefers_the_exact_name(tmp_path):
    (tmp_path / 'pdf-extract').mkdir()
    path = str(tmp_path / 'pdf-extract')
    assert uninstall_skill._on_disk_path(path) == path


def test_on_disk_path_of_a_missing_folder_is_the_path(tmp_path):
    path = str(tmp_path / 'missing')
    assert uninstall_skill._on_disk_path(path) == path


def test_uninstall_removes_a_skill_md_only_install(tmp_path, capsys):
    skills = tmp_path / 'skills'
    skill = _installed(skills, content='skillMd')
    assert sorted(os.listdir(skill)) == [
        install_skill.PROVENANCE_MARKER,
        'SKILL.md',
    ]
    rc, _ = _run(skills, yes=True)
    assert rc == 0
    assert not os.path.lexists(skill)
    assert 'Uninstalled pdf-extract from' in capsys.readouterr().err


def test_uninstall_removes_a_newer_clis_install(tmp_path, capsys):
    skills = tmp_path / 'skills'
    skill = _installed(skills, content='something-new')
    rc, _ = _run(skills, yes=True)
    assert rc == 0
    assert not os.path.lexists(skill)
    assert 'Uninstalled pdf-extract from' in capsys.readouterr().err


@pytest.mark.parametrize('content', [7, None, ['x']])
def test_uninstall_skips_a_marker_with_non_text_content(
    tmp_path, capsys, content
):
    skills = tmp_path / 'skills'
    skill = _installed(skills, content=content)
    rc, _ = _run(skills, yes=True)
    assert rc == 1
    assert os.path.isdir(skill)
    assert 'no readable' in capsys.readouterr().err


def test_symlink_to_a_folder_outside_the_target_is_refused(tmp_path, capsys):
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / 'SKILL.md').write_text('keep')
    target = tmp_path / 'skills'
    target.mkdir()
    os.symlink(elsewhere, target / 'pdf-extract')
    rc, _ = _run(target, yes=True)
    assert rc == 1
    assert 'outside' in capsys.readouterr().err
    assert (elsewhere / 'SKILL.md').read_text() == 'keep'
    assert os.path.islink(target / 'pdf-extract')


def test_symlink_to_another_skill_in_the_target_is_refused(skills, capsys):
    os.symlink(skills / 'pdf-extract', skills / 'alias')
    rc, _ = _run(skills, name='alias', yes=True)
    assert rc == 1
    assert 'symbolic link' in capsys.readouterr().err
    assert (skills / 'pdf-extract' / 'SKILL.md').exists()
    assert os.path.islink(skills / 'alias')


def test_symlinks_inside_the_skill_are_removed_not_followed(tmp_path, skills):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'keep.txt').write_text('important')
    os.symlink(outside, skills / 'pdf-extract' / 'link')
    rc, _ = _run(skills, yes=True)
    assert rc == 0
    assert not (skills / 'pdf-extract').exists()
    assert (outside / 'keep.txt').read_text() == 'important'


def test_folder_replaced_by_a_link_after_the_prompt_is_refused(
    tmp_path, skills, terminal, capsys
):
    elsewhere = tmp_path / 'skills' / 'decoy'
    elsewhere.mkdir()
    (elsewhere / 'keep.txt').write_text('important')
    skill = skills / 'pdf-extract'

    def swap(_message):
        # Stand in for another process acting while the prompt is open.
        os.rename(skill, skills / 'moved')
        os.symlink(elsewhere, skill)
        return 'y'

    with (
        patch.object(uninstall_skill, 'prompt', side_effect=swap),
        patch.object(uninstall_skill.shutil, 'rmtree') as rmtree,
    ):
        rc, _ = _run(skills)
    assert rc == 1
    assert 'symbolic link' in capsys.readouterr().err
    rmtree.assert_not_called()
    assert (elsewhere / 'keep.txt').read_text() == 'important'


def test_folder_without_skill_md_is_refused(skills, capsys):
    (skills / 'notes').mkdir()
    (skills / 'notes' / 'README').write_text('x')
    rc, _ = _run(skills, name='notes', yes=True)
    assert rc == 1
    assert 'SKILL.md' in capsys.readouterr().err
    assert (skills / 'notes' / 'README').exists()


def test_missing_folder_is_reported(skills):
    with pytest.raises(
        AgentRegistryJWTError, match='No skill named absent is installed in'
    ) as e:
        _run(skills, name='absent', yes=True)
    assert str(skills) in str(e.value)


def test_missing_target_directory_is_reported(tmp_path):
    with pytest.raises(AgentRegistryJWTError, match='No skill named'):
        _run(tmp_path / 'nowhere', yes=True)


def test_regular_file_is_refused(skills, capsys):
    (skills / 'file').write_text('x')
    rc, _ = _run(skills, name='file', yes=True)
    assert rc == 1
    assert 'not a directory' in capsys.readouterr().err
    assert (skills / 'file').exists()


def test_failed_delete_is_reported(skills, capsys):
    with patch.object(
        uninstall_skill.shutil, 'rmtree', side_effect=PermissionError('denied')
    ):
        rc, _ = _run(skills, yes=True)
    assert rc == 1
    err = capsys.readouterr().err
    assert 'Could not remove' in err
    assert 'denied' in err


# --- Agents -----------------------------------------------------------------


def test_default_removes_from_every_detected_agent_after_one_prompt(
    tmp_path, terminal, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'])
    shared = _installed(folders['codex'])
    with patch.object(uninstall_skill, 'prompt', return_value='y') as asked:
        rc, _ = _run(None, configs=configs)
    assert rc == 0
    assert not os.path.exists(claude)
    assert not os.path.exists(shared)
    # One question, listing every folder; the shared folder once.
    asked.assert_called_once()
    question = asked.call_args.args[0]
    assert 'Remove these 2 folders?' in question
    assert os.path.realpath(claude) in question
    assert os.path.realpath(shared) in question
    err = capsys.readouterr().err
    assert 'Claude Code: Uninstalled pdf-extract' in err
    assert 'Codex: Uninstalled pdf-extract' in err
    assert 'Gemini CLI' not in err


def test_default_removes_only_where_the_skill_is_installed(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    shared = _installed(folders['codex'])
    rc, _ = _run(None, yes=True, configs=configs)
    assert rc == 0
    assert not os.path.exists(shared)


def test_agent_removes_from_that_agent_only(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'])
    shared = _installed(folders['codex'])
    rc, _ = _run(None, yes=True, agent='codex', configs=configs)
    assert rc == 0
    assert os.path.exists(claude)
    assert not os.path.exists(shared)


def test_refused_folder_is_skipped_and_the_others_removed(tmp_path, capsys):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'])
    os.remove(os.path.join(claude, 'SKILL.md'))
    shared = _installed(folders['codex'])
    rc, _ = _run(None, yes=True, configs=configs)
    assert rc == 1
    assert os.path.exists(claude)
    assert not os.path.exists(shared)
    err = capsys.readouterr().err
    assert 'Claude Code: Refusing to remove' in err
    assert 'Codex: Uninstalled pdf-extract' in err


def test_refused_folders_are_listed_before_the_prompt(
    tmp_path, terminal, capsys
):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'])
    os.remove(os.path.join(claude, 'SKILL.md'))
    shared = _installed(folders['codex'])
    with patch.object(uninstall_skill, 'prompt', return_value='y') as asked:
        _run(None, configs=configs)
    question = asked.call_args.args[0]
    assert os.path.realpath(shared) in question
    assert claude not in question


def test_not_installed_for_any_agent_is_reported(tmp_path):
    configs, folders = make_agents(str(tmp_path / 'home'))
    with pytest.raises(AgentRegistryJWTError, match='No skill named') as e:
        _run(None, yes=True, configs=configs)
    assert folders['claude-code'] in str(e.value)


def test_no_detected_agent_is_reported(tmp_path):
    configs, _ = make_agents(str(tmp_path / 'home'), detected=())
    with pytest.raises(
        AgentRegistryJWTError, match='no supported AI coding agents'
    ):
        _run(None, yes=True, configs=configs)


def test_agent_and_target_directory_cannot_be_combined(skills):
    with pytest.raises(ParamValidationError, match='--target-directory'):
        _run(skills, yes=True, agent='codex')
    assert (skills / 'pdf-extract').exists()


def test_unknown_agent_is_refused(tmp_path):
    configs, _ = make_agents(str(tmp_path / 'home'))
    with pytest.raises(ParamValidationError, match='Invalid agent'):
        _run(None, yes=True, agent='vim', configs=configs)


def test_defaults_to_agent_toolkits_agents():
    command = UninstallSkillCommand(Mock())
    assert command._agent_configs is AGENT_CONFIGS


def test_name_help_states_the_naming_rule():
    [name] = [
        arg for arg in UninstallSkillCommand.ARG_TABLE if arg['name'] == 'name'
    ]
    assert (
        'The name must be a valid skill name under the Agent Skills '
        'specification (at most 64 lowercase letters, digits and hyphens, '
        'with no hyphen at the start or end and no two hyphens in a row) or, '
        'for an older skill, at most 64 letters, digits, dots, underscores '
        'and hyphens, beginning with a letter or digit.'
    ) in name['help_text']


def test_help_text_matches_install_skill():
    names = [arg['name'] for arg in UninstallSkillCommand.ARG_TABLE]
    assert names == ['name', 'agent', 'target-directory', 'yes']
    agent = UninstallSkillCommand.ARG_TABLE[1]
    assert agent is install_skill.AGENT_ARGUMENT
    assert 'install-skill' in UninstallSkillCommand.DESCRIPTION
    assert 'uninstall-skill' in install_skill.InstallSkillCommand.DESCRIPTION


# --- Provenance -------------------------------------------------------------


def test_confirmation_shows_each_folders_source(tmp_path, terminal):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'])
    shared = _installed(folders['codex'], registryId='otherREG123456')
    with patch.object(uninstall_skill, 'prompt', return_value='n') as asked:
        rc, _ = _run(None, configs=configs)
    assert rc == 1
    question = asked.call_args.args[0]
    assert (
        f'  {os.path.realpath(claude)} (from registry abcDEF123456, record '
        'rec)\n'
    ) in question
    assert (
        f'  {os.path.realpath(shared)} (from registry otherREG123456, record '
        'rec)\n'
    ) in question
    # Declined, so both are still there.
    assert os.path.exists(claude) and os.path.exists(shared)


def test_single_folder_confirmation_shows_the_source(skills, terminal):
    _with_marker(str(skills / 'pdf-extract'), recordId='r\x1b[2J')
    with patch.object(uninstall_skill, 'prompt', return_value='y') as asked:
        _run(skills)
    question = asked.call_args.args[0]
    assert question == (
        f'Remove {os.path.realpath(skills / "pdf-extract")} (from registry '
        'abcDEF123456, record r [2J)? [y/N]: '
    )


def test_yes_prints_the_source_in_each_result_line(tmp_path, capsys):
    configs, folders = make_agents(str(tmp_path / 'home'))
    _installed(folders['claude-code'])
    _installed(folders['codex'], recordId='other')
    rc, _ = _run(None, yes=True, configs=configs)
    assert rc == 0
    err = capsys.readouterr().err
    assert (
        f'Claude Code: Uninstalled pdf-extract from {folders["claude-code"]} '
        '(installed from registry abcDEF123456, record rec)'
    ) in err
    assert (
        f'Codex: Uninstalled pdf-extract from {folders["codex"]} (installed '
        'from registry abcDEF123456, record other)'
    ) in err


def test_any_source_is_removed(skills):
    # uninstall-skill applies the same checks whatever the source.
    _with_marker(str(skills / 'pdf-extract'), registryId='otherREG123456')
    rc, _ = _run(skills, yes=True)
    assert rc == 0
    assert not (skills / 'pdf-extract').exists()


# --- Only skills install-skill put in place ---------------------------------

SKIP = (
    "it has no readable .agent-registry-skill.json, so it wasn't installed "
    'by aws agent-registry install-skill. Delete it yourself if you no '
    'longer need it.'
)


@pytest.mark.parametrize('yes', [True, False])
def test_skill_without_a_marker_is_skipped(tmp_path, terminal, capsys, yes):
    target = tmp_path / 'skills'
    skill = _installed(str(target), marker=False)
    with patch.object(uninstall_skill, 'prompt') as asked:
        rc, _ = _run(target, yes=yes)
    assert rc == 1
    asked.assert_not_called()
    assert os.path.exists(os.path.join(skill, 'SKILL.md'))
    assert capsys.readouterr().err.strip() == (
        f'Skipping {os.path.realpath(skill)}: {SKIP}'
    )


@pytest.mark.parametrize(
    'content', ['not json', '[]', json.dumps({'registryId': 'x'})]
)
def test_skill_with_an_unreadable_marker_is_skipped(tmp_path, capsys, content):
    target = tmp_path / 'skills'
    skill = _installed(str(target), marker=False)
    with open(os.path.join(skill, install_skill.PROVENANCE_MARKER), 'w') as f:
        f.write(content)
    rc, _ = _run(target, yes=True)
    assert rc == 1
    assert os.path.exists(skill)
    assert SKIP in capsys.readouterr().err


def test_marked_folders_are_removed_and_others_skipped(tmp_path, capsys):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'], marker=False)
    shared = _installed(folders['codex'])
    rc, _ = _run(None, yes=True, configs=configs)
    assert rc == 1
    assert os.path.exists(claude)
    assert not os.path.exists(shared)
    err = capsys.readouterr().err
    assert f'Claude Code: Skipping {os.path.realpath(claude)}: {SKIP}' in err
    assert 'Codex: Uninstalled pdf-extract' in err


def test_skipped_folders_are_not_in_the_confirmation(tmp_path, terminal):
    configs, folders = make_agents(str(tmp_path / 'home'))
    claude = _installed(folders['claude-code'], marker=False)
    shared = _installed(folders['codex'])
    with patch.object(uninstall_skill, 'prompt', return_value='y') as asked:
        _run(None, configs=configs)
    question = asked.call_args.args[0]
    assert os.path.realpath(shared) in question
    assert claude not in question
