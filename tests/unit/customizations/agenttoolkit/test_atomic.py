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
import errno
import os
from unittest.mock import patch

import pytest

from awscli.customizations.agenttoolkit import atomic


def _make_dir(path, files):
    path.mkdir(parents=True)
    for name, content in files.items():
        (path / name).write_text(content)
    return path


def _contents(path):
    return {
        p.name: p.read_text() for p in sorted(path.iterdir()) if p.is_file()
    }


def _leftovers(parent):
    return [p.name for p in parent.iterdir() if p.name.startswith('.')]


@pytest.fixture
def live(tmp_path):
    return _make_dir(tmp_path / 'aws-s3', {'SKILL.md': 'old', 'old.md': 'x'})


@pytest.fixture(params=['exchange', 'two-renames'])
def swap_mode(request):
    if request.param == 'exchange':
        if atomic._load_exchange() is None:
            pytest.skip('atomic exchange is not available on this platform')
        yield
    else:
        with patch.object(atomic, '_load_exchange', return_value=None):
            yield


def _staging_for(live_dir, files):
    staging = atomic.make_staging_dir(str(live_dir))
    for name, content in files.items():
        with open(os.path.join(staging, name), 'w') as f:
            f.write(content)
    return staging


def test_make_staging_dir_is_hidden_sibling(live):
    staging = atomic.make_staging_dir(str(live))
    assert os.path.dirname(staging) == str(live.parent)
    assert os.path.basename(staging).startswith('.aws-s3.aws-cli-staging-')
    assert os.path.isdir(staging)


def test_swap_replaces_live_dir(live, swap_mode):
    staging = _staging_for(live, {'SKILL.md': 'new'})
    atomic.swap_into_place(staging, str(live))
    assert _contents(live) == {'SKILL.md': 'new'}
    assert _leftovers(live.parent) == []


def test_swap_when_live_dir_missing(tmp_path, swap_mode):
    live = tmp_path / 'aws-s3'
    staging = _staging_for(live, {'SKILL.md': 'new'})
    atomic.swap_into_place(staging, str(live))
    assert _contents(live) == {'SKILL.md': 'new'}
    assert _leftovers(tmp_path) == []


def test_exchange_is_used_when_available(live):
    if atomic._load_exchange() is None:
        pytest.skip('atomic exchange is not available on this platform')
    staging = _staging_for(live, {'SKILL.md': 'new'})
    with patch.object(atomic, '_rename') as rename:
        atomic.swap_into_place(staging, str(live))
    assert not rename.called
    assert _contents(live) == {'SKILL.md': 'new'}


@pytest.mark.parametrize('err', [errno.EINVAL, errno.ENOSYS, errno.ENOTSUP])
def test_unsupported_exchange_falls_back_to_renames(live, err):
    staging = _staging_for(live, {'SKILL.md': 'new'})
    with (
        patch.object(atomic, '_load_exchange', return_value=lambda a, b: -1),
        patch.object(atomic.ctypes, 'get_errno', return_value=err),
    ):
        atomic.swap_into_place(staging, str(live))
    assert _contents(live) == {'SKILL.md': 'new'}
    assert _leftovers(live.parent) == []


def test_other_exchange_error_is_raised_and_live_untouched(live):
    staging = _staging_for(live, {'SKILL.md': 'new'})
    with (
        patch.object(atomic, '_load_exchange', return_value=lambda a, b: -1),
        patch.object(atomic.ctypes, 'get_errno', return_value=errno.EACCES),
    ):
        with pytest.raises(PermissionError):
            atomic.swap_into_place(staging, str(live))
    assert _contents(live) == {'SKILL.md': 'old', 'old.md': 'x'}


@pytest.mark.parametrize('error', [OSError('boom'), KeyboardInterrupt()])
def test_failed_second_rename_restores_live_dir(live, error):
    staging = _staging_for(live, {'SKILL.md': 'new'})
    real_rename = os.rename

    def rename(src, dst):
        if src == staging:
            raise error
        real_rename(src, dst)

    with (
        patch.object(atomic, '_load_exchange', return_value=None),
        patch.object(atomic.os, 'rename', side_effect=rename),
    ):
        with pytest.raises(type(error)):
            atomic.swap_into_place(staging, str(live))
    assert _contents(live) == {'SKILL.md': 'old', 'old.md': 'x'}
    # Only the staging dir is left; the caller removes it.
    assert _leftovers(live.parent) == [os.path.basename(staging)]


def test_interrupted_two_rename_swap_is_recovered(live):
    # Simulate a crash after the live dir was moved to its backup name.
    staging = _staging_for(live, {'SKILL.md': 'new'})
    backup = atomic._sibling(str(live), atomic._BACKUP)
    os.rename(str(live), backup)
    atomic.recover(str(live))
    assert _contents(live) == {'SKILL.md': 'old', 'old.md': 'x'}
    assert _leftovers(live.parent) == []
    assert not os.path.exists(staging)


def test_recover_deletes_backup_when_live_dir_exists(live):
    backup = _make_dir(
        live.parent / f'.aws-s3.aws-cli-backup-{"0" * 16}', {'SKILL.md': 'x'}
    )
    atomic.recover(str(live))
    assert not backup.exists()
    assert _contents(live) == {'SKILL.md': 'old', 'old.md': 'x'}


def test_recover_deletes_staging_dirs(live):
    _make_dir(live.parent / f'.aws-s3.aws-cli-staging-{"a" * 16}', {})
    _make_dir(live.parent / f'.aws-s3.aws-cli-staging-{"b" * 16}', {})
    atomic.recover(str(live))
    assert _leftovers(live.parent) == []


def test_recover_leaves_unrelated_entries_alone(live):
    keep = [
        f'.aws-lambda.aws-cli-backup-{"0" * 16}',  # another skill
        f'.aws-s3.aws-cli-backup-{"0" * 15}',  # wrong token length
        '.aws-s3.backup',  # not ours
        '.hidden',
    ]
    for name in keep:
        _make_dir(live.parent / name, {})
    atomic.recover(str(live))
    assert sorted(_leftovers(live.parent)) == sorted(keep)


def test_recover_does_not_follow_symlinks(tmp_path):
    target = _make_dir(tmp_path / 'elsewhere', {'SKILL.md': 'keep'})
    skills = tmp_path / 'skills'
    skills.mkdir()
    link = skills / f'.aws-s3.aws-cli-staging-{"0" * 16}'
    link.symlink_to(target, target_is_directory=True)
    atomic.recover(str(skills / 'aws-s3'))
    assert link.is_symlink()
    assert _contents(target) == {'SKILL.md': 'keep'}


def test_recover_missing_parent_is_noop(tmp_path):
    atomic.recover(str(tmp_path / 'missing' / 'aws-s3'))


def test_rename_retries_permission_error_on_windows():
    calls = []

    def rename(src, dst):
        calls.append(src)
        if len(calls) < 3:
            raise PermissionError('in use')

    with (
        patch.object(atomic, 'is_windows', True),
        patch.object(atomic.os, 'rename', side_effect=rename),
        patch.object(atomic.time, 'sleep'),
    ):
        atomic._rename('a', 'b')
    assert len(calls) == 3


def test_rename_gives_up_after_timeout_on_windows():
    with (
        patch.object(atomic, 'is_windows', True),
        patch.object(atomic, '_WINDOWS_RETRY_TIMEOUT', 0),
        patch.object(
            atomic.os, 'rename', side_effect=PermissionError('in use')
        ) as rename,
    ):
        with pytest.raises(PermissionError):
            atomic._rename('a', 'b')
    assert rename.call_count == 1


def test_rename_does_not_retry_on_posix():
    with (
        patch.object(atomic, 'is_windows', False),
        patch.object(
            atomic.os, 'rename', side_effect=PermissionError('denied')
        ) as rename,
    ):
        with pytest.raises(PermissionError):
            atomic._rename('a', 'b')
    assert rename.call_count == 1


def test_write_file_atomic(tmp_path):
    path = tmp_path / 'f.json'
    path.write_text('old')
    atomic.write_file_atomic(str(path), 'new', prefix='.f-')
    assert path.read_text() == 'new'
    assert [p.name for p in tmp_path.iterdir()] == ['f.json']


def test_write_file_atomic_failure_keeps_old_file(tmp_path):
    path = tmp_path / 'f.json'
    path.write_text('old')
    with patch.object(atomic.os, 'replace', side_effect=OSError('boom')):
        with pytest.raises(OSError):
            atomic.write_file_atomic(str(path), 'new', prefix='.f-')
    assert path.read_text() == 'old'
    assert [p.name for p in tmp_path.iterdir()] == ['f.json']


def test_write_file_atomic_retries_replace_on_windows(tmp_path):
    path = tmp_path / 'f.json'
    real_replace = os.replace
    calls = []

    def replace(src, dst):
        calls.append(src)
        if len(calls) == 1:
            raise PermissionError('reader has it open')
        real_replace(src, dst)

    with (
        patch.object(atomic, 'is_windows', True),
        patch.object(atomic.os, 'replace', side_effect=replace),
        patch.object(atomic.time, 'sleep'),
    ):
        atomic.write_file_atomic(str(path), 'new', prefix='.f-')
    assert path.read_text() == 'new'
    assert len(calls) == 2


def test_recover_all_handles_every_skill(tmp_path):
    _make_dir(tmp_path / 'aws-s3', {'SKILL.md': 'live'})
    _make_dir(
        tmp_path / f'.aws-s3.aws-cli-backup-{"0" * 16}', {'SKILL.md': 'b'}
    )
    _make_dir(
        tmp_path / f'.aws-cdk.aws-cli-backup-{"0" * 16}', {'SKILL.md': 'cdk'}
    )
    _make_dir(tmp_path / f'.aws-iam.aws-cli-staging-{"0" * 16}', {})
    atomic.recover_all(str(tmp_path))
    assert _contents(tmp_path / 'aws-s3') == {'SKILL.md': 'live'}
    assert _contents(tmp_path / 'aws-cdk') == {'SKILL.md': 'cdk'}
    assert not (tmp_path / 'aws-iam').exists()
    assert _leftovers(tmp_path) == []


def test_recover_all_missing_dir_is_noop(tmp_path):
    atomic.recover_all(str(tmp_path / 'missing'))


def test_remove_dir(live):
    atomic.remove_dir(str(live))
    assert not live.exists()
    assert _leftovers(live.parent) == []


def test_recover_finishes_interrupted_remove(live):
    trash = live.parent / f'.aws-s3.aws-cli-trash-{"0" * 16}'
    os.rename(live, trash)
    atomic.recover(str(live))
    assert not trash.exists()
    assert not live.exists()
