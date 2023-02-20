# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import dateutil.parser
import pytest

from botocore.exceptions import (
    InvalidConfigError,
    SSOTokenLoadError,
    TokenRetrievalError,
)
from botocore.session import Session
from botocore.tokens import SSOTokenProvider
from tests import mock


def parametrize(cases):
    return pytest.mark.parametrize(
        "test_case",
        cases,
        ids=[c["documentation"] for c in cases],
    )


sso_provider_resolution_cases = [
    {
        "documentation": "Full valid profile",
        "config": {
            "profiles": {"test": {"sso_session": "admin"}},
            "sso_sessions": {
                "admin": {
                    "sso_region": "us-east-1",
                    "sso_start_url": "https://d-abc123.awsapps.com/start",
                }
            },
        },
        "resolves": True,
    },
    {
        "documentation": "Non-SSO profiles are skipped",
        "config": {"profiles": {"test": {"region": "us-west-2"}}},
        "resolves": False,
    },
    {
        "documentation": "Only start URL is invalid",
        "config": {
            "profiles": {"test": {"sso_session": "admin"}},
            "sso_sessions": {
                "admin": {
                    "sso_start_url": "https://d-abc123.awsapps.com/start"
                }
            },
        },
        "resolves": False,
        "expectedException": InvalidConfigError,
    },
    {
        "documentation": "Only sso_region is invalid",
        "config": {
            "profiles": {"test": {"sso_session": "admin"}},
            "sso_sessions": {"admin": {"sso_region": "us-east-1"}},
        },
        "resolves": False,
        "expectedException": InvalidConfigError,
    },
    {
        "documentation": "Specified sso-session must exist",
        "config": {
            "profiles": {"test": {"sso_session": "dev"}},
            "sso_sessions": {"admin": {"sso_region": "us-east-1"}},
        },
        "resolves": False,
        "expectedException": InvalidConfigError,
    },
    {
        "documentation": "The sso_session must be specified",
        "config": {
            "profiles": {"test": {"region": "us-west-2"}},
            "sso_sessions": {
                "admin": {
                    "sso_region": "us-east-1",
                    "sso_start_url": "https://d-abc123.awsapps.com/start",
                }
            },
        },
        "resolves": False,
    },
]


def _create_mock_session(config):
    mock_session = mock.Mock(spec=Session)
    mock_session.get_config_variable.return_value = "test"
    mock_session.full_config = config
    return mock_session


def _run_token_provider_test_case(provider, test_case):
    expected_exception = test_case.get("expectedException")
    if expected_exception is not None:
        with pytest.raises(expected_exception):
            auth_token = provider.load_token()
        return

    auth_token = provider.load_token()
    if test_case["resolves"]:
        assert auth_token is not None
    else:
        assert auth_token is None


@parametrize(sso_provider_resolution_cases)
def test_sso_token_provider_resolution(test_case):
    mock_session = _create_mock_session(test_case["config"])
    resolver = SSOTokenProvider(mock_session)

    _run_token_provider_test_case(resolver, test_case)


@parametrize(sso_provider_resolution_cases)
def test_sso_token_provider_profile_name_overrides_session_profile(test_case):
    mock_session = _create_mock_session(test_case["config"])
    mock_session.get_config_variable.return_value = "default"
    resolver = SSOTokenProvider(mock_session, profile_name='test')

    _run_token_provider_test_case(resolver, test_case)


sso_provider_refresh_cases = [
    {
        "documentation": "Valid token with all fields",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "cachedtoken",
            "expiresAt": "2021-12-25T21:30:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2022-12-25T13:30:00Z",
            "refreshToken": "cachedrefreshtoken",
        },
        "expectedToken": {
            "token": "cachedtoken",
            "expiration": "2021-12-25T21:30:00Z",
        },
    },
    {
        "documentation": "Minimal valid cached token",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "accessToken": "cachedtoken",
            "expiresAt": "2021-12-25T21:30:00Z",
        },
        "expectedToken": {
            "token": "cachedtoken",
            "expiration": "2021-12-25T21:30:00Z",
        },
    },
    {
        "documentation": "Minimal expired cached token",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "accessToken": "cachedtoken",
            "expiresAt": "2021-12-25T13:00:00Z",
        },
        "expectedException": TokenRetrievalError,
    },
    {
        "documentation": "Token missing the expiresAt field",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {"accessToken": "cachedtoken"},
        "expectedException": SSOTokenLoadError,
    },
    {
        "documentation": "Token missing the accessToken field",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {"expiresAt": "2021-12-25T13:00:00Z"},
        "expectedException": SSOTokenLoadError,
    },
    {
        "documentation": "Expired token refresh with refresh token",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "cachedtoken",
            "expiresAt": "2021-12-25T13:00:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2022-12-25T13:30:00Z",
            "refreshToken": "cachedrefreshtoken",
        },
        "refreshResponse": {
            "tokenType": "Bearer",
            "accessToken": "newtoken",
            "expiresIn": 28800,
            "refreshToken": "newrefreshtoken",
        },
        "expectedTokenWriteback": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "newtoken",
            "expiresAt": "2021-12-25T21:30:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2022-12-25T13:30:00Z",
            "refreshToken": "newrefreshtoken",
        },
        "expectedToken": {
            "token": "newtoken",
            "expiration": "2021-12-25T21:30:00Z",
        },
    },
    {
        "documentation": "Expired token refresh without new refresh token",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "cachedtoken",
            "expiresAt": "2021-12-25T13:00:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2022-12-25T13:30:00Z",
            "refreshToken": "cachedrefreshtoken",
        },
        "refreshResponse": {
            "tokenType": "Bearer",
            "accessToken": "newtoken",
            "expiresIn": 28800,
        },
        "expectedTokenWriteback": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "newtoken",
            "expiresAt": "2021-12-25T21:30:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2022-12-25T13:30:00Z",
        },
        "expectedToken": {
            "token": "newtoken",
            "expiration": "2021-12-25T21:30:00Z",
        },
    },
    {
        "documentation": "Expired token and expired client registration",
        "currentTime": "2021-12-25T13:30:00Z",
        "cachedToken": {
            "startUrl": "https://d-123.awsapps.com/start",
            "region": "us-west-2",
            "accessToken": "cachedtoken",
            "expiresAt": "2021-10-25T13:00:00Z",
            "clientId": "clientid",
            "clientSecret": "YSBzZWNyZXQ=",
            "registrationExpiresAt": "2021-11-25T13:30:00Z",
            "refreshToken": "cachedrefreshtoken",
        },
        "expectedException": TokenRetrievalError,
    },
]


@parametrize(sso_provider_refresh_cases)
def test_sso_token_provider_refresh(test_case):
    config = {
        "profiles": {"test": {"sso_session": "admin"}},
        "sso_sessions": {
            "admin": {
                "sso_region": "us-west-2",
                "sso_start_url": "https://d-123.awsapps.com/start",
            }
        },
    }
    cache_key = "d033e22ae348aeb5660fc2140aec35850c4da997"
    token_cache = {}

    # Prepopulate the token cache
    cached_token = test_case.pop("cachedToken", None)
    if cached_token:
        token_cache[cache_key] = cached_token

    mock_session = _create_mock_session(config)
    mock_sso_oidc = mock.Mock()
    mock_session.create_client.return_value = mock_sso_oidc

    refresh_response = test_case.pop("refreshResponse", None)
    mock_sso_oidc.create_token.return_value = refresh_response

    current_time = dateutil.parser.parse(test_case.pop("currentTime"))

    def _time_fetcher():
        return current_time

    resolver = SSOTokenProvider(
        mock_session,
        token_cache,
        time_fetcher=_time_fetcher,
    )

    auth_token = resolver.load_token()

    actual_exception = None
    try:
        actual_token = auth_token.get_frozen_token()
    except Exception as e:
        actual_exception = e

    expected_exception = test_case.pop("expectedException", None)
    if expected_exception is not None:
        assert isinstance(actual_exception, expected_exception)
    elif actual_exception is not None:
        raise actual_exception

    expected_token = test_case.pop("expectedToken", {})
    raw_token = expected_token.get("token")
    if raw_token is not None:
        assert actual_token.token == raw_token

    raw_expiration = expected_token.get("expiration")
    if raw_expiration is not None:
        expected_expiration = dateutil.parser.parse(raw_expiration)
        assert actual_token.expiration == expected_expiration

    expected_token_write_back = test_case.pop("expectedTokenWriteback", None)
    if expected_token_write_back:
        mock_sso_oidc.create_token.assert_called_with(
            grantType="refresh_token",
            clientId=cached_token["clientId"],
            clientSecret=cached_token["clientSecret"],
            refreshToken=cached_token["refreshToken"],
        )
        raw_expiration = expected_token_write_back["expiresAt"]
        # The in-memory cache doesn't serialize to JSON so expect a datetime
        expected_expiration = dateutil.parser.parse(raw_expiration)
        expected_token_write_back["expiresAt"] = expected_expiration
        assert expected_token_write_back == token_cache[cache_key]

    # Pop the documentation to ensure all test fields are handled
    test_case.pop("documentation")
    assert not test_case.keys(), "All fields of test case should be handled"
