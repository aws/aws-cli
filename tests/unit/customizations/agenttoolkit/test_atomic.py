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
import os
from unittest.mock import patch

import pytest

from awscli.customizations.agenttoolkit import atomic


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


def test_write_file_atomic_gives_up_after_timeout_on_windows(tmp_path):
    path = tmp_path / 'f.json'
    with (
        patch.object(atomic, 'is_windows', True),
        patch.object(atomic, '_WINDOWS_RETRY_TIMEOUT', 0),
        patch.object(
            atomic.os, 'replace', side_effect=PermissionError('in use')
        ) as replace,
    ):
        with pytest.raises(PermissionError):
            atomic.write_file_atomic(str(path), 'new', prefix='.f-')
    assert replace.call_count == 1
    assert list(tmp_path.iterdir()) == []


def test_write_file_atomic_does_not_retry_on_posix(tmp_path):
    path = tmp_path / 'f.json'
    with (
        patch.object(atomic, 'is_windows', False),
        patch.object(
            atomic.os, 'replace', side_effect=PermissionError('denied')
        ) as replace,
    ):
        with pytest.raises(PermissionError):
            atomic.write_file_atomic(str(path), 'new', prefix='.f-')
    assert replace.call_count == 1
