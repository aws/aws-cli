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
from unittest.mock import MagicMock, patch

from awscli.customizations.agenttoolkit import hint


def _agent(installed_skills=None):
    agent = MagicMock()
    agent.get_installed_skills.return_value = installed_skills or []
    return agent


def _run(agents=None, tty=True):
    if agents is None:
        agents = [_agent()]
    with (
        patch.object(hint, 'is_a_tty', return_value=tty),
        patch.object(hint, 'get_detected_real_agents', return_value=agents),
    ):
        hint.maybe_print_agent_toolkit_hint()


def test_prints_tip_when_eligible(capsys):
    _run()
    assert '--region us-east-1' in capsys.readouterr().out


def test_no_tip_when_not_a_tty(capsys):
    _run(tty=False)
    assert capsys.readouterr().out == ''


def test_no_tip_when_env_var_true(capsys, monkeypatch):
    monkeypatch.setenv(hint.HINT_DISABLED_ENV_VAR, 'true')
    _run()
    assert capsys.readouterr().out == ''


def test_tip_shown_when_env_var_false(capsys, monkeypatch):
    monkeypatch.setenv(hint.HINT_DISABLED_ENV_VAR, 'false')
    _run()
    assert '--region us-east-1' in capsys.readouterr().out


def test_no_tip_when_no_agents(capsys):
    _run(agents=[])
    assert capsys.readouterr().out == ''


def test_no_tip_when_skills_already_installed(capsys):
    _run(agents=[_agent(installed_skills=['s'])])
    assert capsys.readouterr().out == ''


def test_detection_failure_does_not_raise(capsys):
    with (
        patch.object(hint, 'is_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', side_effect=OSError('boom')
        ),
    ):
        hint.maybe_print_agent_toolkit_hint()
    assert capsys.readouterr().out == ''
