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
import argparse
import json
import logging
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


_UNSET = object()


def _parsed_globals(region='us-east-1'):
    return argparse.Namespace(
        region=region, endpoint_url=None, verify_ssl=None
    )


def _run(
    choice='yes',
    agents=None,
    tty=True,
    region='us-east-1',
    globals_region=_UNSET,
):
    """Run the hint.

    :param region: The region the calling command resolved.
    :param globals_region: ``--region`` as passed to the calling command.
        Defaults to matching ``region``; pass ``None`` to model a command that
        resolved a region without an explicit ``--region``.
    """
    if agents is None:
        agents = [_agent()]
    if globals_region is _UNSET:
        globals_region = region
    parsed_globals = _parsed_globals(globals_region)
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=tty),
        patch.object(hint, 'get_detected_real_agents', return_value=agents),
        patch.object(hint, 'yes_no_never_choice', return_value=choice),
    ):
        hint.maybe_prompt_agent_toolkit(
            MagicMock(), parsed_globals, region=region
        )
    return parsed_globals


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


@pytest.mark.parametrize('region', ['us-east-1', 'us-west-2', None])
def test_wizard_is_pinned_to_agent_toolkit_region(
    state_file, wizard_cls, region
):
    # Any commercial region prompts, and the wizard always runs against the
    # one region the Agent Toolkit is available in. A region of None means
    # nothing was configured anywhere, which is also safe to prompt on.
    _run(choice='yes', region=region)
    wizard_cls.return_value.assert_called_once()
    wizard_globals = wizard_cls.return_value.call_args[0][1]
    assert wizard_globals.region == 'us-east-1'


def test_swapping_the_region_is_logged(state_file, wizard_cls, caplog):
    # The resolved region drives the message, not ``--region``: a plain
    # "aws configure" that sets us-west-2 passes no --region at all.
    with caplog.at_level(logging.DEBUG, logger=hint.LOG.name):
        _run(choice='yes', region='us-west-2', globals_region=None)
    assert (
        'Running "aws configure agent-toolkit" in us-east-1 instead of '
        'us-west-2, the only region the Agent Toolkit for AWS is available in.'
    ) in caplog.text


def test_pinning_the_region_does_not_mutate_parsed_globals(
    state_file, wizard_cls
):
    parsed_globals = _run(choice='yes', region='us-west-2')
    assert parsed_globals.region == 'us-west-2'


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
        hint.maybe_prompt_agent_toolkit(
            MagicMock(), _parsed_globals(region), region=region
        )

    assert not prompt.called
    assert not wizard_cls.called
    assert capsys.readouterr().out == (
        "\nTip: run 'aws configure agent-toolkit' to set up AWS skills and "
        'the AWS MCP server for your AI coding agent(s).\n'
    )


def test_region_comes_from_the_caller_not_the_session(state_file, wizard_cls):
    session = MagicMock()
    session.get_config_variable.return_value = 'us-east-1'
    with (
        patch.object(hint, 'is_stdin_a_tty', return_value=True),
        patch.object(
            hint, 'get_detected_real_agents', return_value=[_agent()]
        ),
        patch.object(hint, 'yes_no_never_choice') as prompt,
    ):
        hint.maybe_prompt_agent_toolkit(
            session, _parsed_globals(None), region='us-gov-east-1'
        )
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
        hint.maybe_prompt_agent_toolkit(
            MagicMock(), _parsed_globals(), region='us-east-1'
        )
    assert not wizard_cls.called


def test_wizard_errors_are_not_swallowed(state_file, wizard_cls):
    wizard_cls.return_value.side_effect = RuntimeError('wizard boom')
    with pytest.raises(RuntimeError, match='wizard boom'):
        _run(choice='yes')
