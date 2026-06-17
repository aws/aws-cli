# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest

import botocore
from botocore.config import Config
from tests import ClientHTTPStubber, patch_load_service_model
from tests.functional.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)

MOCK_SERVICE_MODEL = {
    "version": "2.0",
    "metadata": {
        "apiVersion": "2020-02-02",
        "endpointPrefix": "mock-bearer-service",
        "jsonVersion": "1.1",
        "protocol": "rest-json",
        "protocols": ["rest-json"],
        "serviceFullName": "Mock Bearer Service",
        "serviceId": "Bearer Service",
        "signatureVersion": "v4",
        "signingName": "bearer-service",
        "uid": "bearer-service-2020-02-02",
        "auth": ["aws.auth#sigv4", "smithy.api#httpBearerAuth"],
    },
    "operations": {
        "MockOperation": {
            "name": "MockOperation",
            "http": {"method": "GET", "requestUri": "/"},
            "input": {"shape": "MockOperationRequest"},
            "documentation": "",
        },
    },
    "shapes": {
        "MockOpParam": {
            "type": "string",
        },
        "MockOperationRequest": {
            "type": "structure",
            "required": ["MockOpParam"],
            "members": {
                "MockOpParam": {
                    "shape": "MockOpParam",
                    "documentation": "",
                    "location": "uri",
                    "locationName": "param",
                },
            },
        },
    },
}

MOCK_RULESET = {
    "version": "1.0",
    "parameters": {},
    "rules": [
        {
            "conditions": [],
            "endpoint": {
                "url": "https://bearer-service.us-west-2.amazonaws.com/"
            },
            "type": "endpoint",
        },
    ],
}


def mocked_supported_services():
    return {"bearer-service"}


@pytest.fixture(autouse=True)
def patch_supported_services(monkeypatch):
    monkeypatch.setattr(
        "botocore.handlers.get_bearer_auth_supported_services",
        mocked_supported_services,
    )


@pytest.mark.parametrize(
    "env_vars",
    [
        {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
        {
            "AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token",
            "AWS_AUTH_SCHEME_PREFERENCE": "sigv4,httpBearerAuth",
        },
    ],
    ids=["valid_token", "token_overrides_auth_scheme_preference"],
)
def test_service_uses_bearer_auth(monkeypatch, patched_session, env_vars):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    patch_load_service_model(
        patched_session, monkeypatch, MOCK_SERVICE_MODEL, MOCK_RULESET
    )

    client = patched_session.create_client(
        "bearer-service",
        region_name="us-west-2",
    )
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.mock_operation(MockOpParam="mock-op-param-value")
        request = http_stubber.requests[0]
        auth_header = request.headers.get("Authorization")
        assert auth_header == b"Bearer bearer-service-token"


@pytest.mark.parametrize(
    "env_vars, config",
    [
        ({}, None),
        ({"AWS_BEARER_TOKEN_FOO_SERVICE": "foo-service-token"}, None),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(signature_version="v4"),
        ),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(auth_scheme_preference="sigv4"),
        ),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(signature_version=botocore.UNSIGNED),
        ),
    ],
    ids=[
        "no_token_configured",
        "invalid_token",
        "signature_version_config_override",
        "auth_scheme_preference_config_override",
        "botocore_unsigned_config_override",
    ],
)
def test_service_does_not_use_bearer_auth(
    monkeypatch, patched_session, env_vars, config
):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    patch_load_service_model(
        patched_session, monkeypatch, MOCK_SERVICE_MODEL, MOCK_RULESET
    )
    client = patched_session.create_client(
        "bearer-service",
        region_name="us-west-2",
        config=config,
    )
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.mock_operation(MockOpParam="mock-op-param-value")
        request = http_stubber.requests[0]
        auth_header = request.headers.get("Authorization")
        assert not (auth_header and auth_header.startswith(b"Bearer"))


@pytest.mark.parametrize(
    "env_vars",
    [
        {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
        {
            "AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token",
            "AWS_AUTH_SCHEME_PREFERENCE": "sigv4,httpBearerAuth",
        },
    ],
    ids=["valid_token", "token_overrides_auth_scheme_preference"],
)
def test_user_agent_has_bearer_service_env_vars_feature_id(
    monkeypatch, patched_session, env_vars
):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    patch_load_service_model(
        patched_session, monkeypatch, MOCK_SERVICE_MODEL, MOCK_RULESET
    )

    client = patched_session.create_client(
        "bearer-service",
        region_name="us-west-2",
    )

    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.mock_operation(MockOpParam="mock-op-param-value")

    ua_string = get_captured_ua_strings(http_stubber)[0]
    feature_ids = parse_registered_feature_ids(ua_string)

    assert "3" in feature_ids


@pytest.mark.parametrize(
    "env_vars, config",
    [
        ({"AWS_BEARER_TOKEN_FOO_SERVICE": "foo-service-token"}, None),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(signature_version="v4"),
        ),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(auth_scheme_preference="sigv4"),
        ),
        (
            {"AWS_BEARER_TOKEN_BEARER_SERVICE": "bearer-service-token"},
            Config(signature_version=botocore.UNSIGNED),
        ),
    ],
    ids=[
        "invalid_token",
        "signature_version_config_override",
        "auth_scheme_preference_config_override",
        "botocore_unsigned_config_override",
    ],
)
def test_user_agent_does_not_have_bearer_service_env_vars_feature_id(
    monkeypatch, patched_session, env_vars, config
):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    patch_load_service_model(
        patched_session, monkeypatch, MOCK_SERVICE_MODEL, MOCK_RULESET
    )

    client = patched_session.create_client(
        "bearer-service",
        region_name="us-west-2",
        config=config,
    )

    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response()
        client.mock_operation(MockOpParam="mock-op-param-value")

    ua_string = get_captured_ua_strings(http_stubber)[0]
    feature_ids = parse_registered_feature_ids(ua_string)

    assert "3" not in feature_ids
