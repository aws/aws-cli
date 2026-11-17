# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import base64
import datetime
from unittest import mock

import pytest
from botocore.utils import LoginCredentialsLoader
from dateutil.tz import tzutc

from awscli.botocore.exceptions import (
    ClientError,
    LoginAuthorizationCodeError,
)
from awscli.customizations.login.utils import (
    CrossDeviceLoginTokenFetcher,
    SameDeviceLoginTokenFetcher,
)

ID_TOKEN = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhcm46YXdzOnN0czo6MDEyMzQ1'
    'Njc4OTAxOmFzc3VtZWQtcm9sZS9BZG1pbi9hZG1pbiIsImF1ZCI6ImFybjphd3M6c2lnbmluO'
    'jo6Y2xpL3NhbWUtZGV2aWNlIiwiaXNzIjoiaHR0cHM6Ly9zaWduaW4uYXdzLmFtYXpvbi5jb2'
    '0vc2lnbmluIiwic2Vzc2lvbl9hcm4iOiJhcm46YXdzOnN0czo6MDEyMzQ1Njc4OTAxOmFzc3V'
    'tZWQtcm9sZS9BZG1pbi9hZG1pbiIsImV4cCI6MTc2MTA5OTMxMCwiaWF0IjoxNzYxMDk4NDEw'
    'fQ.kiIJ6sOFm_keeapxWtB6u5oV-sCEoNsA4vortcNW6U4'
)

EXPECTED_DPOP_KEY = (
    '-----BEGIN EC PRIVATE KEY-----\n'
    'MHcCAQEEIHjt7c+VnkIkN6RW7QgZPFNLb/9AZEhqSYYMtwrlLb3WoAoGCCqGSM49\n'
    'AwEHoUQDQgAEv2FjRpMtADMZ4zoZxshV9chEkembgzZnXSUNe+DA8dKqXN/7qTcZ\n'
    'jYJHKIi+Rn88zUGqCJo3DWF/X+ufVfdU2g==\n'
    '-----END EC PRIVATE KEY-----\n'
)

TOKEN_RESPONSE = {
    'tokenOutput': {
        'accessToken': {
            'accessKeyId': 'access_key',
            'secretAccessKey': 'secret_access_key',
            'sessionToken': 'session_token',
        },
        'tokenType': 'aws_sigv4',
        'idToken': ID_TOKEN,
        'refreshToken': 'refresh_token',
        'expiresIn': 3600,
    }
}
UTC_NOW = datetime.datetime(2025, 9, 1, 17, 39, 33, tzinfo=tzutc())

EXPECTED_TOKEN = {
    'accessToken': {
        'accessKeyId': 'access_key',
        'secretAccessKey': 'secret_access_key',
        'sessionToken': 'session_token',
        'expiresAt': '2025-09-01T18:39:33Z',
        'accountId': '012345678901',
    },
    'tokenType': 'aws_sigv4',
    'idToken': ID_TOKEN,
    'clientId': 'arn:aws:signin:::devtools/same-device',
    'refreshToken': 'refresh_token',
    'dpopKey': EXPECTED_DPOP_KEY,
}


def fake_get_base_sign_in_uri(client):
    return 'https://foobar'


@pytest.fixture
def mock_client():
    mock_client = mock.Mock()
    mock_client.create_o_auth2_token.return_value = TOKEN_RESPONSE
    return mock_client


@pytest.fixture
def mock_auth_code_fetcher():
    return mock.Mock()


@pytest.fixture
def mock_on_pending_auth():
    return mock.Mock()


@pytest.fixture
def mock_same_device_fetcher(
    mock_client, mock_auth_code_fetcher, mock_on_pending_auth, private_key
):
    with mock.patch(
        'awscli.customizations.login.utils.secrets.choice', return_value='a'
    ):
        fetcher = SameDeviceLoginTokenFetcher(
            mock_client,
            mock_auth_code_fetcher,
            mock_on_pending_auth,
            private_key,
            base_uri_builder=fake_get_base_sign_in_uri,
        )

    return fetcher


@pytest.fixture
def mock_cross_device_fetcher(mock_client, mock_on_pending_auth, private_key):
    with mock.patch(
        'awscli.customizations.login.utils.secrets.choice', return_value='a'
    ):
        fetcher = CrossDeviceLoginTokenFetcher(
            mock_client,
            mock_on_pending_auth,
            private_key,
            base_uri_builder=fake_get_base_sign_in_uri,
        )

    return fetcher


def test_same_device_fetch_token_success(
    mock_auth_code_fetcher,
    mock_same_device_fetcher,
    mock_on_pending_auth,
    mock_client,
    fake_build_dpop_header,
):
    mock_auth_code_fetcher.redirect_uri_with_port.return_value = (
        'http://localhost:8080'
    )
    mock_auth_code_fetcher.get_auth_code_and_state.return_value = (
        'auth_code',
        str(mock_same_device_fetcher._expected_state),
    )

    with mock.patch(
        'awscli.botocore.utils.build_dpop_header',
        side_effect=fake_build_dpop_header,
    ):
        with mock.patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = UTC_NOW
            token, session_id = mock_same_device_fetcher.fetch_token()

    assert token == EXPECTED_TOKEN
    assert session_id == 'arn:aws:sts::012345678901:assumed-role/Admin/admin'
    mock_on_pending_auth.assert_called_once()
    mock_client.create_o_auth2_token.assert_called_with(
        tokenInput={
            'clientId': 'arn:aws:signin:::devtools/same-device',
            'grantType': 'authorization_code',
            'code': 'auth_code',
            'codeVerifier': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'redirectUri': 'http://localhost:8080',
        },
    )


def test_same_device_fetch_token_no_auth_code(
    mock_auth_code_fetcher, mock_same_device_fetcher
):
    mock_auth_code_fetcher.get_auth_code_and_state.return_value = (
        None,
        'state',
    )

    with pytest.raises(LoginAuthorizationCodeError):
        mock_same_device_fetcher.fetch_token()


def test_same_device_fetch_token_state_mismatch(
    mock_auth_code_fetcher, mock_same_device_fetcher
):
    mock_auth_code_fetcher.get_auth_code_and_state.return_value = (
        'auth_code',
        'wrong_state',
    )

    with pytest.raises(LoginAuthorizationCodeError):
        mock_same_device_fetcher.fetch_token()


@mock.patch(
    'awscli.customizations.login.utils.CrossDeviceLoginTokenFetcher._prompt'
)
def test_cross_device_fetch_token_success(
    mock_prompt,
    mock_cross_device_fetcher,
    mock_on_pending_auth,
    mock_client,
    fake_build_dpop_header,
):
    unencoded_verification_code = (
        f'state={mock_cross_device_fetcher._expected_state}&code=auth_code'
    )
    mock_prompt.return_value = base64.b64encode(
        unencoded_verification_code.encode('utf-8')
    )

    with mock.patch(
        'awscli.botocore.utils.build_dpop_header',
        side_effect=fake_build_dpop_header,
    ):
        with mock.patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = UTC_NOW
            token, session_id = mock_cross_device_fetcher.fetch_token()

    expected_token = EXPECTED_TOKEN.copy()
    expected_token['clientId'] = 'arn:aws:signin:::devtools/cross-device'

    assert token == expected_token
    assert session_id == 'arn:aws:sts::012345678901:assumed-role/Admin/admin'
    mock_on_pending_auth.assert_called_once()
    mock_client.create_o_auth2_token.assert_called_with(
        tokenInput={
            'clientId': 'arn:aws:signin:::devtools/cross-device',
            'grantType': 'authorization_code',
            'code': 'auth_code',
            'codeVerifier': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'redirectUri': 'https://foobar/v1/sessions/confirmation',
        },
    )


@mock.patch(
    'awscli.customizations.login.utils.CrossDeviceLoginTokenFetcher._prompt'
)
def test_cross_device_fetch_token_state_mismatch(
    mock_prompt,
    mock_cross_device_fetcher,
    fake_build_dpop_header,
):
    unencoded_verification_code = 'state=wrong_state&code=auth_code'
    mock_prompt.return_value = base64.b64encode(
        unencoded_verification_code.encode('utf-8')
    )

    with mock.patch(
        'awscli.botocore.utils.build_dpop_header',
        side_effect=fake_build_dpop_header,
    ):
        with mock.patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = UTC_NOW
            with pytest.raises(LoginAuthorizationCodeError):
                mock_cross_device_fetcher.fetch_token()


class TestLoginCredentialsLoader:
    def test_save_and_load_token(self):
        loader = LoginCredentialsLoader()
        token = {'access_token': 'token_123'}
        session_name = 'login_test'

        loader.save_token(session_name, token)

        loaded = loader.load_token(session_name)
        assert loaded == token

    def test_load_token_not_exists(self):
        loader = LoginCredentialsLoader()
        assert loader.load_token('nonexistant_session') is None


@mock.patch('awscli.customizations.login.utils.register_feature_id')
def test_same_device_fetcher_registers_login_same_device(
    mock_register, mock_auth_code_fetcher, mock_same_device_fetcher
):
    mock_auth_code_fetcher.redirect_uri_with_port.return_value = (
        'http://localhost:8080'
    )
    mock_auth_code_fetcher.get_auth_code_and_state.return_value = (
        'auth_code',
        str(mock_same_device_fetcher._expected_state),
    )

    with mock.patch.object(
        mock_same_device_fetcher, '_exchange_auth_code_for_access_token'
    ):
        mock_same_device_fetcher.fetch_token()

    mock_register.assert_called_with('LOGIN_SAME_DEVICE')


@mock.patch('awscli.customizations.login.utils.register_feature_id')
@mock.patch(
    'awscli.customizations.login.utils.CrossDeviceLoginTokenFetcher._prompt'
)
def test_cross_device_fetcher_registers_login_cross_device(
    mock_prompt, mock_register, mock_cross_device_fetcher
):
    import base64

    unencoded = (
        f'state={mock_cross_device_fetcher._expected_state}&code=auth_code'
    )
    mock_prompt.return_value = base64.b64encode(unencoded.encode('utf-8'))

    with mock.patch.object(
        mock_cross_device_fetcher, '_exchange_auth_code_for_access_token'
    ):
        mock_cross_device_fetcher.fetch_token()

    mock_register.assert_called_with('LOGIN_CROSS_DEVICE')


def test_same_device_fetch_token_expired_auth_code(
    mock_auth_code_fetcher, mock_same_device_fetcher
):
    mock_auth_code_fetcher.redirect_uri_with_port.return_value = (
        'http://localhost:8080'
    )
    mock_auth_code_fetcher.get_auth_code_and_state.return_value = (
        'expired_code',
        str(mock_same_device_fetcher._expected_state),
    )

    error_response = {
        'Error': {'Code': 'AccessDeniedException'},
        'error': 'AUTHCODE_EXPIRED',
    }
    mock_same_device_fetcher._client.create_o_auth2_token.side_effect = (
        ClientError(error_response, 'CreateOAuth2Token')
    )
    mock_same_device_fetcher._client.exceptions.AccessDeniedException = (
        ClientError
    )

    with pytest.raises(
        LoginAuthorizationCodeError, match="expired authorization code"
    ):
        mock_same_device_fetcher.fetch_token()
