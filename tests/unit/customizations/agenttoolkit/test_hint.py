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


def _run(choice='yes', agents=None, tty=True, region='us-east-1'):
    if agents is None:
        agents = [_agent()]
    parsed_globals = MagicMock()
    parsed_globals.region = region
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=tty),
        patch.object(hint, 'get_detected_real_agents', return_value=agents),
        patch.object(hint, 'yes_no_never_choice', return_value=choice),
    ):
        hint.maybe_prompt_agent_toolkit(MagicMock(), parsed_globals)


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


def test_skipped_when_env_var_true(state_file, wizard_cls, monkeypatch):
    monkeypatch.setenv(hint.HINT_DISABLED_ENV_VAR, 'true')
    _run(choice='yes')
    assert not wizard_cls.called


def test_not_skipped_when_env_var_false(state_file, wizard_cls, monkeypatch):
    monkeypatch.setenv(hint.HINT_DISABLED_ENV_VAR, 'false')
    _run(choice='yes')
    assert wizard_cls.called


def test_env_var_also_suppresses_the_tip(
    state_file, wizard_cls, capsys, monkeypatch
):
    monkeypatch.setenv(hint.HINT_DISABLED_ENV_VAR, 'true')
    _run(choice='yes', region='cn-north-1')
    assert not wizard_cls.called
    assert capsys.readouterr().out == ''


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


def test_prompts_when_region_in_commercial_partition(state_file, wizard_cls):
    # A non-us-east-1 commercial region still prompts: the wizard defaults to
    # the control-plane region on its own, so "yes" works.
    _run(choice='yes', region='us-west-2')
    assert wizard_cls.called


@pytest.mark.parametrize('region', ['us-gov-west-1', 'cn-north-1'])
def test_non_commercial_partition_prints_tip_and_does_not_prompt(
    state_file, wizard_cls, capsys, region
):
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', return_value=[_agent()]
        ),
        patch.object(hint, 'yes_no_never_choice') as prompt,
    ):
        parsed_globals = MagicMock()
        parsed_globals.region = region
        hint.maybe_prompt_agent_toolkit(MagicMock(), parsed_globals)

    assert not prompt.called
    assert not wizard_cls.called
    assert 'aws configure agent-toolkit' in capsys.readouterr().out


def test_prompts_when_no_region_configured(state_file, wizard_cls):
    # No region anywhere: the wizard defaults to the control-plane region, so
    # prompting is safe.
    session = MagicMock()
    session.get_config_variable.return_value = None
    parsed_globals = MagicMock()
    parsed_globals.region = None
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', return_value=[_agent()]
        ),
        patch.object(hint, 'yes_no_never_choice', return_value='yes'),
    ):
        hint.maybe_prompt_agent_toolkit(session, parsed_globals)
    assert wizard_cls.called


def test_region_falls_back_to_session_config(state_file, wizard_cls):
    session = MagicMock()
    session.get_config_variable.return_value = 'cn-north-1'
    parsed_globals = MagicMock()
    parsed_globals.region = None
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', return_value=[_agent()]
        ),
        patch.object(hint, 'yes_no_never_choice') as prompt,
    ):
        hint.maybe_prompt_agent_toolkit(session, parsed_globals)
    # Configured region is in the China partition, so we tip, not prompt.
    assert not prompt.called
    assert not wizard_cls.called


def test_corrupt_state_file_is_ignored(state_file, wizard_cls):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text('{ not valid json')
    _run(choice='yes')
    assert wizard_cls.called


def test_detection_failure_does_not_raise(state_file, wizard_cls):
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', side_effect=OSError('boom')
        ),
    ):
        hint.maybe_prompt_agent_toolkit(MagicMock(), MagicMock())
    assert not wizard_cls.called


def test_wizard_errors_are_not_swallowed(state_file, wizard_cls):
    wizard_cls.return_value.side_effect = RuntimeError('wizard boom')
    with pytest.raises(RuntimeError, match='wizard boom'):
        _run(choice='yes')
