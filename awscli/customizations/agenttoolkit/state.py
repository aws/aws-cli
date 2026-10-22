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
import logging
import os

from awscli.customizations.agenttoolkit.atomic import write_file_atomic
from awscli.customizations.agenttoolkit.filelock import file_lock

LOG = logging.getLogger(__name__)

STATE_PATH = '~/.aws/cli/agent-toolkit/state.json'
LOCK_FILENAME = 'state.lock'

HINT_DISMISSED_KEY = 'hint_dismissed'
AUTO_UPDATE_KEY = 'agent_toolkit_auto_update'
LAST_HOOK_RUN_KEY = 'last_hook_run'


class StateFileError(Exception):
    pass


def _state_file():
    return os.path.expanduser(STATE_PATH)


def _read_state(path):
    with open(path, encoding='utf-8') as f:
        state = json.load(f)
    if not isinstance(state, dict):
        raise ValueError(f'expected a JSON object, got {type(state).__name__}')
    return state


def load_state():
    """Return the state, or an empty dict if it is missing or unreadable."""
    try:
        return _read_state(_state_file())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        LOG.debug('Could not read agent toolkit state: %s', e)
        return {}


def _state_lock(directory):
    return file_lock(os.path.join(directory, LOCK_FILENAME))


def _write_state(path, state):
    try:
        content = json.dumps(state, indent=2, sort_keys=True) + '\n'
    except TypeError as e:
        raise ValueError(f'state is not JSON serializable: {e}') from e
    write_file_atomic(path, content, prefix='.state-')


def toolkit_dir():
    """Directory holding the state file and other agent toolkit files."""
    return os.path.dirname(_state_file())


def update_state(mutate):
    """Apply ``mutate`` to the state and save it.

    :param mutate: Called with the current state dict, which it changes in
        place.
    :raises StateFileError: if the state can't be read, locked or written.
        An existing file that can't be parsed is left untouched.
    """
    path = _state_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with _state_lock(os.path.dirname(path)):
            try:
                state = _read_state(path)
            except FileNotFoundError:
                state = {}
            mutate(state)
            _write_state(path, state)
    except (OSError, ValueError) as e:
        raise StateFileError(f'{path}: {e}') from e


def dismiss_hint():
    update_state(lambda state: state.update({HINT_DISMISSED_KEY: True}))


def is_hint_dismissed(state=None):
    if state is None:
        state = load_state()
    return state.get(HINT_DISMISSED_KEY) is True


def is_auto_update_enabled(state=None):
    """Whether automatic skill updates are enabled. Absent means disabled."""
    if state is None:
        state = load_state()
    return state.get(AUTO_UPDATE_KEY) is True


def set_auto_update(enabled):
    """Enable or disable automatic skill updates."""
    update_state(lambda state: state.update({AUTO_UPDATE_KEY: bool(enabled)}))


def get_last_hook_runs(state=None):
    """Return ``{agent_id: {timestamp, is_successful, summary}}``."""
    if state is None:
        state = load_state()
    runs = state.get(LAST_HOOK_RUN_KEY)
    if not isinstance(runs, dict):
        return {}
    return {
        agent_id: run
        for agent_id, run in runs.items()
        if _is_valid_hook_run(run)
    }


def _is_valid_hook_run(run):
    if not (
        isinstance(run, dict)
        and isinstance(run.get('timestamp'), str)
        and isinstance(run.get('is_successful'), bool)
        and isinstance(run.get('summary'), str)
    ):
        return False
    try:
        parse_timestamp(run['timestamp'])
    except ValueError:
        return False
    return True


def get_last_hook_run(agent_id, state=None):
    """Return the last hook run recorded for ``agent_id``, or ``None``."""
    return get_last_hook_runs(state).get(agent_id)


def record_hook_run(agent_id, is_successful, summary, timestamp=None):
    """Record the outcome of an automatic update run by an agent's hook.

    :param agent_id: The agent whose session start hook ran.
    :param timestamp: Aware ``datetime`` of the run. Defaults to now.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)
    run = {
        'timestamp': _format_timestamp(timestamp),
        'is_successful': bool(is_successful),
        'summary': str(summary),
    }

    def mutate(state):
        runs = state.get(LAST_HOOK_RUN_KEY)
        if not isinstance(runs, dict):
            runs = {}
            state[LAST_HOOK_RUN_KEY] = runs
        runs[agent_id] = run

    update_state(mutate)


def _format_timestamp(timestamp):
    return (
        timestamp.astimezone(datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime('%Y-%m-%dT%H:%M:%SZ')
    )


def parse_timestamp(value):
    """Parse a ``last_hook_run`` timestamp into an aware UTC ``datetime``."""
    return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(
        tzinfo=datetime.timezone.utc
    )
