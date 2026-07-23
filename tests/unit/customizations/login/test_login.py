# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from argparse import Namespace
from unittest import mock

import pytest

from awscli.customizations.login import login as login_module
from awscli.customizations.login.login import LoginCommand


@pytest.fixture
def session():
    sess = mock.Mock()
    sess.profile = None
    sess.available_profiles = []
    sess._profile_map = {}
    sess.full_config = {'profiles': {}}
    sess.get_config_variable.return_value = 'us-east-1'
    return sess


@pytest.fixture
def parsed_globals():
    return Namespace(
        region='us-east-1',
        endpoint_url=None,
        verify_ssl=None,
    )


def _run_login(session, parsed_globals):
    command = LoginCommand(
        session,
        token_loader=mock.Mock(),
        config_file_writer=mock.Mock(),
    )
    fetcher = mock.Mock()
    fetcher.fetch_token.return_value = ('access.token', 'session-id')
    with (
        mock.patch.object(
            login_module, 'SameDeviceLoginTokenFetcher', return_value=fetcher
        ),
        mock.patch.object(login_module, 'AuthCodeFetcher'),
        mock.patch.object(login_module, 'OpenBrowserHandler'),
        mock.patch.object(login_module.EC, 'new_generate'),
        mock.patch.object(
            login_module, 'maybe_prompt_agent_toolkit'
        ) as prompt,
    ):
        command._run_main(Namespace(remote=False), parsed_globals)
    return prompt


def test_prompts_agent_toolkit_for_new_profile(session, parsed_globals):
    session.available_profiles = []
    prompt = _run_login(session, parsed_globals)
    prompt.assert_called_once()


def test_no_prompt_when_reauthenticating_existing_profile(
    session, parsed_globals
):
    session.available_profiles = ['default']
    prompt = _run_login(session, parsed_globals)
    prompt.assert_not_called()
