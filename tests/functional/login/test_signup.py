# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import base64
import json
from argparse import Namespace
from unittest import mock

import pytest

from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.login.signup import SignupCommand

DEFAULT_ARGS = Namespace(remote=False, redirect_port=None)
DEFAULT_GLOBAL_ARGS = Namespace(
    region=None, endpoint_url=None, verify_ssl=None
)
LOGIN_SESSION = 'arn:aws:sts::123456789012:assumed-role/Admin/new-user'


def _id_token(**claims):
    payload = base64.urlsafe_b64encode(
        json.dumps({'sub': LOGIN_SESSION, **claims}).encode()
    ).decode()
    return f'header.{payload.rstrip("=")}.signature'


@pytest.fixture
def mock_token_loader():
    return mock.Mock()


@pytest.fixture
def mock_config_file_writer():
    return mock.Mock()


@pytest.fixture
def mock_session():
    def config_variables(key):
        if key == 'config_file':
            return 'configfile'
        return None

    mock_session = mock.Mock()
    mock_session.profile = 'new-profile'
    mock_session.available_profiles = []
    mock_session.get_config_variable.side_effect = config_variables
    mock_session.full_config = {'profiles': {}}
    mock_session.get_scoped_config.return_value = {}
    mock_session._profile_map = {}
    return mock_session


@pytest.fixture
def signup_command(mock_session, mock_token_loader, mock_config_file_writer):
    return SignupCommand(
        mock_session, mock_token_loader, mock_config_file_writer
    )


@pytest.fixture
def mock_fetch_token():
    with mock.patch(
        'awscli.customizations.login.utils.get_base_sign_in_uri',
        return_value='https://foo',
    ):
        with mock.patch(
            'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher'
            '.fetch_token'
        ) as fetch_token:
            yield fetch_token


@pytest.fixture(autouse=True)
def mock_stdin_a_tty():
    # The prompts below only run on a terminal, which tests don't have
    with mock.patch(
        'awscli.customizations.login.login.is_stdin_a_tty', return_value=True
    ) as is_a_tty:
        yield is_a_tty


@pytest.fixture(autouse=True)
def no_agent_toolkit_prompt():
    with mock.patch(
        'awscli.customizations.login.login.maybe_prompt_agent_toolkit'
    ) as agent_toolkit_prompt:
        yield agent_toolkit_prompt


def _token(id_token):
    return {'accessToken': 'access_token', 'idToken': id_token}


@pytest.mark.parametrize(
    'remote,fetcher',
    [
        (False, 'SameDeviceLoginTokenFetcher'),
        (True, 'CrossDeviceLoginTokenFetcher'),
    ],
)
def test_signup_sends_prompt_create(signup_command, remote, fetcher):
    with mock.patch(
        f'awscli.customizations.login.login.{fetcher}'
    ) as fetcher_cls:
        fetcher_cls.return_value.fetch_token.return_value = (
            _token(_id_token(aws_home_region='us-east-2')),
            LOGIN_SESSION,
        )
        signup_command._run_main(
            Namespace(remote=remote, redirect_port=None), DEFAULT_GLOBAL_ARGS
        )

    assert fetcher_cls.call_args.kwargs['prompt'] == 'create'


@pytest.mark.parametrize(
    'requested_region,configured_region,expected',
    [
        (None, None, 'us-east-1'),
        ('eu-west-1', None, 'eu-west-1'),
        # A configured region is ignored, since signup happens in us-east-1
        (None, 'ap-southeast-2', 'us-east-1'),
        ('eu-west-1', 'ap-southeast-2', 'eu-west-1'),
    ],
)
def test_signup_region_needs_no_prompt(
    signup_command,
    mock_session,
    requested_region,
    configured_region,
    expected,
):
    mock_session.get_config_variable.side_effect = (
        lambda key: configured_region if key == 'region' else None
    )

    with mock.patch.object(signup_command, '_prompt_for_region') as prompt:
        region = signup_command._resolve_region(
            Namespace(region=requested_region)
        )

    assert region == expected
    prompt.assert_not_called()


def test_signup_writes_home_region(
    signup_command,
    mock_session,
    mock_fetch_token,
    mock_token_loader,
    mock_config_file_writer,
    no_agent_toolkit_prompt,
    capsys,
):
    mock_fetch_token.return_value = (
        _token(_id_token(aws_home_region='us-east-2')),
        LOGIN_SESSION,
    )

    signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': 'profile new-profile',
            'login_session': LOGIN_SESSION,
            'region': 'us-east-2',
        },
        'configfile',
    )
    assert 'Set region to us-east-2, the home region for this account.\n' in (
        capsys.readouterr().out
    )
    # Refresh still goes to where we signed in, not the new profile region
    saved_token = mock_token_loader.save_token.call_args[0][1]
    assert saved_token['signInRegion'] == 'us-east-1'
    no_agent_toolkit_prompt.assert_called_once_with(
        mock_session, DEFAULT_GLOBAL_ARGS, region='us-east-1'
    )


def test_signup_region_arg_with_home_region(
    signup_command,
    mock_fetch_token,
    mock_token_loader,
    mock_config_file_writer,
):
    mock_fetch_token.return_value = (
        _token(_id_token(aws_home_region='us-east-2')),
        LOGIN_SESSION,
    )
    global_args = Namespace(
        region='eu-west-1', endpoint_url=None, verify_ssl=None
    )

    signup_command._run_main(DEFAULT_ARGS, global_args)

    # --region sets where we sign in, and the profile gets the home region
    saved_token = mock_token_loader.save_token.call_args[0][1]
    assert saved_token['signInRegion'] == 'eu-west-1'
    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': 'profile new-profile',
            'login_session': LOGIN_SESSION,
            'region': 'us-east-2',
        },
        'configfile',
    )


def test_signup_without_home_region_leaves_region_unset(
    signup_command, mock_fetch_token, mock_config_file_writer, capsys
):
    mock_fetch_token.return_value = (_token(_id_token()), LOGIN_SESSION)

    signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': 'profile new-profile',
            'login_session': LOGIN_SESSION,
        },
        'configfile',
    )
    assert (
        '\nCould not determine the home region for this account. To set the '
        'region for this profile, run "aws configure set region REGION '
        '--profile new-profile".\n'
    ) in capsys.readouterr().out


def test_signup_without_home_region_keeps_existing_region_quietly(
    signup_command,
    mock_session,
    mock_fetch_token,
    mock_config_file_writer,
    capsys,
):
    mock_session.full_config = {
        'profiles': {'new-profile': {'region': 'us-west-2'}}
    }
    mock_fetch_token.return_value = (_token(_id_token()), LOGIN_SESSION)

    signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': 'profile new-profile',
            'login_session': LOGIN_SESSION,
        },
        'configfile',
    )
    assert 'Could not determine the home region' not in (
        capsys.readouterr().out
    )


@pytest.mark.parametrize(
    'existing_region,accepts,expected_values',
    [
        ('us-east-2', None, {}),
        ('us-west-2', True, {'region': 'us-east-2'}),
        ('us-west-2', False, {}),
    ],
    ids=['matches', 'overwrite accepted', 'overwrite declined'],
)
def test_signup_existing_profile_region(
    signup_command,
    mock_session,
    mock_fetch_token,
    mock_config_file_writer,
    existing_region,
    accepts,
    expected_values,
):
    mock_session.full_config = {
        'profiles': {'new-profile': {'region': existing_region}}
    }
    mock_fetch_token.return_value = (
        _token(_id_token(aws_home_region='us-east-2')),
        LOGIN_SESSION,
    )

    with mock.patch(
        'awscli.customizations.login.login.yes_no_choice',
        return_value=accepts,
    ) as choice:
        signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    assert choice.called is (accepts is not None)
    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': 'profile new-profile',
            'login_session': LOGIN_SESSION,
            **expected_values,
        },
        'configfile',
    )


def test_signup_existing_credentials_error_names_signup(
    signup_command, mock_session
):
    mock_session.full_config = {
        'profiles': {'new-profile': {'aws_access_key_id': 'AKID'}}
    }

    with pytest.raises(ConfigurationError) as e:
        signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    assert str(e.value) == (
        "Profile 'new-profile' is already configured with Access Key "
        "credentials.\n\nYou may run 'aws signup --profile new-profile-name' "
        'to create a new profile with the specified name. Otherwise you must '
        "first manually remove the existing credentials from 'new-profile'.\n"
    )


def test_signup_declined_identity_change_writes_nothing(
    signup_command,
    mock_session,
    mock_fetch_token,
    mock_token_loader,
    mock_config_file_writer,
):
    mock_session.full_config = {
        'profiles': {
            'new-profile': {
                'login_session': 'arn:aws:iam::111122223333:user/Other',
                'region': 'us-west-2',
            }
        }
    }
    mock_fetch_token.return_value = (
        _token(_id_token(aws_home_region='us-east-2')),
        LOGIN_SESSION,
    )

    with mock.patch(
        'awscli.customizations.login.login.yes_no_choice', return_value=False
    ) as choice:
        signup_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    # Only the identity question is asked, not the region one
    assert choice.call_count == 1
    assert 'session' in choice.call_args[0][0]
    mock_token_loader.save_token.assert_not_called()
    mock_config_file_writer.update_config.assert_not_called()
