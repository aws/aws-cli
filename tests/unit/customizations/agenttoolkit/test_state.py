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
import json
import os
import threading
from unittest.mock import patch

import pytest

from awscli.customizations.agenttoolkit import filelock, state


@pytest.fixture
def state_file(tmp_path):
    path = tmp_path / 'agent-toolkit' / 'state.json'
    with patch.object(state, 'STATE_PATH', str(path)):
        yield path


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data))


def _read(path):
    return json.loads(path.read_text())


def test_load_state_missing_file(state_file):
    assert state.load_state() == {}


@pytest.mark.parametrize('contents', ['{ not valid json', '[]', '"x"'])
def test_load_state_unreadable_file(state_file, contents):
    _write(state_file, contents)
    assert state.load_state() == {}


def test_update_state_creates_directory_and_file(state_file):
    state.update_state(lambda s: s.update({'a': 1}))
    assert _read(state_file) == {'a': 1}
    assert (state_file.parent / state.LOCK_FILENAME).exists()


def test_update_state_preserves_other_keys(state_file):
    _write(state_file, {'other': 'value'})
    state.update_state(lambda s: s.update({'a': 1}))
    assert _read(state_file) == {'other': 'value', 'a': 1}


@pytest.mark.parametrize('contents', ['{ not valid json', '[1, 2]'])
def test_update_state_does_not_overwrite_unparseable_file(
    state_file, contents
):
    _write(state_file, contents)
    with pytest.raises(state.StateFileError):
        state.update_state(lambda s: s.update({'a': 1}))
    assert state_file.read_text() == contents


def test_update_state_leaves_no_temp_file(state_file):
    state.update_state(lambda s: s.update({'a': 1}))
    assert not list(state_file.parent.glob('*.tmp'))


def test_update_state_failed_write_keeps_old_file(state_file):
    _write(state_file, {'a': 1})
    with patch.object(state.os, 'replace', side_effect=OSError('boom')):
        with pytest.raises(state.StateFileError):
            state.update_state(lambda s: s.update({'a': 2}))
    assert _read(state_file) == {'a': 1}
    assert not list(state_file.parent.glob('*.tmp'))


def test_update_state_error_message_names_the_file(state_file):
    _write(state_file, '{ not valid json')
    with pytest.raises(state.StateFileError) as e:
        state.update_state(lambda s: s.update({'a': 1}))
    assert str(e.value).startswith(f'{state_file}: ')
    assert 'Could not' not in str(e.value)


def test_update_state_times_out_when_lock_is_held(state_file):
    state_file.parent.mkdir(parents=True)
    with patch.object(filelock, 'DEFAULT_TIMEOUT', 0.2):
        with state._state_lock(str(state_file.parent)):
            with pytest.raises(state.StateFileError, match='timed out'):
                state.update_state(lambda s: s.update({'a': 1}))
    assert not state_file.exists()
    state.update_state(lambda s: s.update({'a': 1}))
    assert _read(state_file) == {'a': 1}


def test_update_state_unserializable_value_keeps_old_file(state_file):
    _write(state_file, {'a': 1})
    with pytest.raises(state.StateFileError, match='not JSON serializable'):
        state.update_state(lambda s: s.update({'a': object()}))
    assert _read(state_file) == {'a': 1}
    assert not list(state_file.parent.glob('*.tmp'))


def test_update_state_serializes_concurrent_writers(state_file):
    keys = [f'k{i}' for i in range(8)]
    errors = []

    def write(key):
        try:
            state.update_state(lambda s: s.update({key: 1}))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=write, args=(k,)) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(_read(state_file)) == sorted(keys)


@pytest.mark.parametrize(
    'contents, expected',
    [
        ({}, False),
        ({'agent_toolkit_auto_update': True}, True),
        ({'agent_toolkit_auto_update': False}, False),
        ({'agent_toolkit_auto_update': 'true'}, False),
        ('{ not valid json', False),
    ],
)
def test_is_auto_update_enabled(state_file, contents, expected):
    _write(state_file, contents)
    assert state.is_auto_update_enabled() is expected


def test_auto_update_absent_when_file_missing(state_file):
    assert state.is_auto_update_enabled() is False


@pytest.mark.parametrize('enabled', [True, False])
def test_set_auto_update(state_file, enabled):
    _write(state_file, {'hint_dismissed': True})
    state.set_auto_update(enabled)
    assert _read(state_file) == {
        'hint_dismissed': True,
        'agent_toolkit_auto_update': enabled,
    }
    assert state.is_auto_update_enabled() is enabled


def test_dismiss_hint(state_file):
    assert not state.is_hint_dismissed()
    state.dismiss_hint()
    assert state.is_hint_dismissed()
    assert _read(state_file) == {'hint_dismissed': True}


def test_record_hook_run(state_file, tmp_path):
    hook_path = str(tmp_path / '.claude' / 'settings.json')
    ts = datetime.datetime(2026, 10, 20, 12, 0, 5, 123, datetime.timezone.utc)
    state.record_hook_run(hook_path, True, '2 updated, 0 failed', ts)
    assert _read(state_file) == {
        'last_hook_run': {
            hook_path: {
                'timestamp': '2026-10-20T12:00:05Z',
                'is_successful': True,
                'summary': '2 updated, 0 failed',
            }
        }
    }


def test_record_hook_run_keeps_other_hooks(state_file, tmp_path):
    first = str(tmp_path / 'a.json')
    second = str(tmp_path / 'b.json')
    state.record_hook_run(first, True, 'ok')
    state.record_hook_run(second, False, 'network error')
    state.record_hook_run(first, False, 'failed')
    runs = state.get_last_hook_runs()
    assert set(runs) == {first, second}
    assert runs[first]['is_successful'] is False
    assert runs[first]['summary'] == 'failed'
    assert runs[second]['summary'] == 'network error'


def test_record_hook_run_normalizes_path(state_file, tmp_path):
    with patch.dict(
        os.environ, {'HOME': str(tmp_path), 'USERPROFILE': str(tmp_path)}
    ):
        state.record_hook_run('~/settings.json', True, 'ok')
        expected = os.path.abspath(
            os.path.join(str(tmp_path), 'settings.json')
        )
        assert list(state.get_last_hook_runs()) == [expected]
        assert state.get_last_hook_run('~/settings.json')['summary'] == 'ok'


def test_record_hook_run_default_timestamp_is_now(state_file, tmp_path):
    before = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    )
    state.record_hook_run(str(tmp_path / 'a.json'), True, 'ok')
    after = datetime.datetime.now(datetime.timezone.utc)
    run = state.get_last_hook_run(str(tmp_path / 'a.json'))
    assert before <= state.parse_timestamp(run['timestamp']) <= after


def test_record_hook_run_converts_timestamp_to_utc(state_file, tmp_path):
    tz = datetime.timezone(datetime.timedelta(hours=-4))
    ts = datetime.datetime(2026, 10, 20, 8, 0, 0, tzinfo=tz)
    state.record_hook_run(str(tmp_path / 'a.json'), True, 'ok', ts)
    run = state.get_last_hook_run(str(tmp_path / 'a.json'))
    assert run['timestamp'] == '2026-10-20T12:00:00Z'


def test_record_hook_run_replaces_malformed_last_hook_run(
    state_file, tmp_path
):
    _write(state_file, {'last_hook_run': 'garbage', 'hint_dismissed': True})
    state.record_hook_run(str(tmp_path / 'a.json'), True, 'ok')
    data = _read(state_file)
    assert data['hint_dismissed'] is True
    assert list(data['last_hook_run']) == [str(tmp_path / 'a.json')]


def test_get_last_hook_runs_skips_malformed_entries(state_file):
    _write(
        state_file,
        {
            'last_hook_run': {
                '/good': {
                    'timestamp': '2026-10-20T12:00:00Z',
                    'is_successful': True,
                    'summary': 'ok',
                },
                '/not-a-dict': 'x',
                '/missing-fields': {'timestamp': '2026-10-20T12:00:00Z'},
                '/wrong-type': {
                    'timestamp': '2026-10-20T12:00:00Z',
                    'is_successful': 'yes',
                    'summary': 'ok',
                },
            }
        },
    )
    assert list(state.get_last_hook_runs()) == ['/good']


@pytest.mark.parametrize(
    'summary, expected', [(None, 'None'), (3, '3'), (['x'], "['x']")]
)
def test_record_hook_run_stores_summary_as_str(
    state_file, tmp_path, summary, expected
):
    state.record_hook_run(str(tmp_path / 'a.json'), True, summary)
    run = state.get_last_hook_run(str(tmp_path / 'a.json'))
    assert run['summary'] == expected


@pytest.mark.parametrize(
    'timestamp', ['yesterday', '2026-10-20', '2026-10-20T12:00:00+00:00', '']
)
def test_get_last_hook_runs_skips_malformed_timestamp(state_file, timestamp):
    _write(
        state_file,
        {
            'last_hook_run': {
                '/bad': {
                    'timestamp': timestamp,
                    'is_successful': True,
                    'summary': 'ok',
                }
            }
        },
    )
    assert state.get_last_hook_runs() == {}


def test_get_last_hook_run_missing(state_file, tmp_path):
    assert state.get_last_hook_run(str(tmp_path / 'a.json')) is None


def test_parse_timestamp_round_trip():
    ts = datetime.datetime(
        2026, 10, 20, 12, 0, 0, tzinfo=datetime.timezone.utc
    )
    assert state.parse_timestamp(state._format_timestamp(ts)) == ts


def test_lock_file_is_owner_only(state_file):
    state.update_state(lambda s: s.update({'a': 1}))
    mode = os.stat(state_file.parent / state.LOCK_FILENAME).st_mode & 0o777
    assert mode == 0o600


def test_lock_timeout_message_names_lock_file(state_file):
    state_file.parent.mkdir(parents=True)
    with patch.object(filelock, 'DEFAULT_TIMEOUT', 0.1):
        with state._state_lock(str(state_file.parent)):
            with pytest.raises(state.StateFileError) as e:
                state.update_state(lambda s: s.update({'a': 1}))
    assert str(state_file.parent / state.LOCK_FILENAME) in str(e.value)
