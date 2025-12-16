# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import webbrowser
from argparse import Namespace
from unittest import mock

import pytest

from awscli.customizations.login.login import LoginCommand

DEFAULT_ARGS = Namespace(remote=False)
DEFAULT_GLOBAL_ARGS = Namespace(
    region='us-east-1', endpoint_url=None, verify_ssl=None
)
SAMPLE_ID_TOKEN = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzM4NCJ9.eyJpc3MiOiJodHRwczovL3NpZ25pbi5hd'
    '3MuYW1hem9uLmNvbS9zaWduaW4iLCJpYXQiOjE3NjAxMTU3NjQsImV4cCI6MTc2MDExNjk'
    '2NSwiYXVkIjoiYXJuOmF3czpzaWduaW46OjpjbGkvc2FtZS1kZXZpY2UiLCJzdWIiOiJhc'
    'm46YXdzOmlhbTo6MDEyMzQ1Njc4OTAxMjp1c2VyL0FkbWluIiwic2Vzc2lvbl9hcm4iOiJ'
    'hcm46YXdzOmlhbTo6MDEyMzQ1Njc4OTAxMjp1c2VyL0FkbWluIn0.HcleGdakodn9ZbCsR'
    'nsF_F2n5TmQD-OW9zc9oMU7DtNrXQwxzg4jO40N2BMgiTyW'
)


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
    mock_session.profile = 'profile-name'
    mock_session.available_profiles = ['profile-name']
    mock_session.get_config_variable.side_effect = config_variables
    mock_session.full_config = {'profiles': {'profile-name': {}}}
    mock_session._profile_map = {'profile-name': {}}

    return mock_session


@pytest.fixture
def mock_login_command(
    mock_session, mock_token_loader, mock_config_file_writer
):
    return LoginCommand(
        mock_session,
        mock_token_loader,
        mock_config_file_writer,
    )


@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)
def test_run_main_same_device_flow(
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_login_command,
    mock_token_loader,
    mock_config_file_writer,
):
    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )

    mock_login_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    mock_token_fetcher.assert_called_once()

    mock_token_loader.save_token.assert_called_once_with(
        'arn:aws:iam::0123456789012:user/Admin',
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
    )

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': "profile profile-name",
            'login_session': 'arn:aws:iam::0123456789012:user/Admin',
        },
        'configfile',
    )


@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.CrossDeviceLoginTokenFetcher.fetch_token'
)
def test_run_main_cross_device_flow(
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_login_command,
    mock_token_loader,
    mock_config_file_writer,
):
    # Set the --remote argument
    args = Namespace(**vars(DEFAULT_ARGS))
    args.remote = True

    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )

    mock_login_command._run_main(args, DEFAULT_GLOBAL_ARGS)

    mock_token_fetcher.assert_called_once()

    mock_token_loader.save_token.assert_called_once_with(
        'arn:aws:iam::0123456789012:user/Admin',
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
    )

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': "profile profile-name",
            'login_session': 'arn:aws:iam::0123456789012:user/Admin',
        },
        'configfile',
    )


@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)
def test_no_verify_ssl_on_signin_client(
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_login_command,
    mock_token_loader,
    mock_config_file_writer,
):
    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )

    # Simulate setting --no-verify-ssl
    global_args = Namespace(**vars(DEFAULT_GLOBAL_ARGS))
    global_args.verify_ssl = False

    mock_login_command._run_main(DEFAULT_ARGS, global_args)

    # Assert that verify was set correctly on the custom signin client
    mock_login_command._session.create_client.assert_called_once_with(
        'signin',
        config=mock.ANY,
        endpoint_url=mock.ANY,
        verify=False,
    )


@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)
@mock.patch('awscli.customizations.configure.sso.PTKPrompt.get_value')
def test_new_profile_without_region(
    mock_prompt,
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_login_command,
    mock_token_loader,
    mock_config_file_writer,
    mock_session,
):
    # Use a different profile than mocked above,
    # simulating a new one via --profile
    mock_session.profile = 'new-profile'
    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )

    # Don't set a region via args, rather prompt the user for one
    global_args = Namespace(region=None, endpoint_url=None, verify_ssl=None)
    mock_prompt.return_value = 'us-west-2'

    mock_login_command._run_main(DEFAULT_ARGS, global_args)

    mock_prompt.assert_called_once()
    mock_token_fetcher.assert_called_once()

    mock_config_file_writer.update_config.assert_called_once_with(
        {
            '__section__': "profile new-profile",
            'login_session': 'arn:aws:iam::0123456789012:user/Admin',
            'region': 'us-west-2',
        },
        'configfile',
    )


@pytest.mark.parametrize(
    'profile_config,expect_prompt_to_be_called',
    [
        pytest.param({}, False, id="Empty profile"),
        pytest.param(
            {'login_session': 'arn:aws:iam::0123456789012:user/Admin'},
            False,
            id="Existing login profile",
        ),
        pytest.param(
            {'web_identity_token_file': '/path'},
            True,
            id="Web Identity Token profile",
        ),
        pytest.param({'sso_role_name': 'role'}, True, id="SSO profile"),
        pytest.param(
            {'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE'},
            True,
            id="IAM access key profile",
        ),
        pytest.param(
            {'role_arn': 'arn:aws:iam::123456789012:role/MyRole'},
            True,
            id="Assume role profile",
        ),
        pytest.param(
            {'credential_process': '/path/to/credential/process'},
            True,
            id="Credential process profile",
        ),
    ],
)
@mock.patch('awscli.customizations.login.login.compat_input', return_value='y')
@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)
def test_accept_change_to_existing_profile_if_needed(
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_input,
    mock_login_command,
    mock_session,
    profile_config,
    expect_prompt_to_be_called,
):
    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )
    mock_session.full_config = {'profiles': {'profile-name': profile_config}}

    mock_login_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)
    mock_token_fetcher.assert_called_once()

    assert mock_input.called == expect_prompt_to_be_called


@mock.patch('awscli.customizations.login.login.compat_input', return_value='n')
@mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri')
@mock.patch(
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)
def test_decline_change_to_existing_profile_does_not_update(
    mock_token_fetcher,
    mock_base_sign_in_uri,
    mock_input,
    mock_login_command,
    mock_session,
    mock_config_file_writer,
    mock_token_loader,
):
    mock_base_sign_in_uri.return_value = 'https://foo'
    mock_token_fetcher.return_value = (
        {
            'accessToken': 'access_token',
            'idToken': SAMPLE_ID_TOKEN,
            'expiresIn': 3600,
        },
        'arn:aws:iam::0123456789012:user/Admin',
    )
    mock_session.full_config = {
        'profiles': {
            'profile-name': {'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE'}
        }
    }

    mock_login_command._run_main(DEFAULT_ARGS, DEFAULT_GLOBAL_ARGS)

    # Because we mocked 'n' to compat_input above, we don't expect the command
    # to have finished when the user declines the existing credential prompt
    mock_input.assert_called_once()
    mock_token_loader.save_token.assert_not_called()
    mock_config_file_writer.update_config.assert_not_called()
