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
import json
from unittest.mock import MagicMock, patch

import pytest

from awscli.customizations.agenttoolkit import hint


@pytest.fixture
def state_file(tmp_path):
    path = tmp_path / 'agent-toolkit' / 'state.json'
    with patch.object(hint, 'STATE_PATH', str(path)):
        yield path


def _agent(installed_skills=None):
    agent = MagicMock()
    agent.get_installed_skills.return_value = installed_skills or []
    return agent


@pytest.fixture
def wizard_cls():
    with patch.object(hint, 'ConfigureAgentToolkitCommand') as cls:
        yield cls


def _run(choice='yes', agents=None, tty=True):
    if agents is None:
        agents = [_agent()]
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=tty),
        patch.object(hint, 'get_detected_real_agents', return_value=agents),
        patch.object(hint, 'yes_no_never_choice', return_value=choice),
    ):
        hint.maybe_prompt_agent_toolkit(MagicMock(), MagicMock())


def test_launches_wizard_on_yes(state_file, wizard_cls):
    _run(choice='yes')
    assert wizard_cls.called
    wizard_cls.return_value.assert_called_once()


def test_no_launch_on_no(state_file, wizard_cls):
    _run(choice='no')
    assert not wizard_cls.called
    assert not state_file.exists()


def test_never_persists_dismissal(state_file, wizard_cls):
    _run(choice='never')
    assert not wizard_cls.called
    assert json.loads(state_file.read_text())['hint_dismissed'] is True
    # The atomic write must not leave its temp file behind.
    assert not (state_file.parent / f'{state_file.name}.tmp').exists()


def test_skipped_when_not_a_tty(state_file, wizard_cls):
    _run(choice='yes', tty=False)
    assert not wizard_cls.called


def test_skipped_when_already_dismissed(state_file, wizard_cls):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({'hint_dismissed': True}))
    _run(choice='yes')
    assert not wizard_cls.called


def test_skipped_when_no_agents(state_file, wizard_cls):
    _run(choice='yes', agents=[])
    assert not wizard_cls.called


def test_skipped_when_skills_already_installed(state_file, wizard_cls):
    _run(choice='yes', agents=[_agent(installed_skills=['s'])])
    assert not wizard_cls.called


def test_corrupt_state_file_is_ignored(state_file, wizard_cls):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text('{ not valid json')
    # Corrupt state must not suppress or crash; hint stays eligible.
    _run(choice='yes')
    assert wizard_cls.called


def test_detection_failure_does_not_raise(state_file, wizard_cls):
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', side_effect=OSError('boom')
        ),
    ):
        # Must swallow errors so `aws configure` never fails because of it.
        hint.maybe_prompt_agent_toolkit(MagicMock(), MagicMock())
    assert not wizard_cls.called
