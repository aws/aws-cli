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

from botocore.config import Config
from botocore.exceptions import EndpointResolutionError
from tests import ClientHTTPStubber, patch_load_service_model
from tests.functional.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)

FAKE_RULESET = {
    "version": "1.0",
    "parameters": {
        "AccountId": {
            "type": "String",
            "builtIn": "AWS::Auth::AccountId",
            "documentation": "The AWS account ID used for the request, eg. `123456789012`.",
        },
        "AccountIdEndpointMode": {
            "type": "String",
            "builtIn": "AWS::Auth::AccountIdEndpointMode",
            "documentation": "The behavior for account ID based endpoint routing, eg. `preferred`.",
        },
    },
    "rules": [
        {
            "documentation": "Template account ID into the URI when account ID is set and AccountIdEndpointMode is "
            "set to preferred.",
            "conditions": [
                {"fn": "isSet", "argv": [{"ref": "AccountId"}]},
                {"fn": "isSet", "argv": [{"ref": "AccountIdEndpointMode"}]},
                {
                    "fn": "stringEquals",
                    "argv": [{"ref": "AccountIdEndpointMode"}, "preferred"],
                },
            ],
            "endpoint": {
                "url": "https://{AccountId}.otherservice.us-west-2.amazonaws.com"
            },
            "type": "endpoint",
        },
        {
            "documentation": "Do not template account ID into the URI when AccountIdEndpointMode is set to disabled.",
            "conditions": [
                {"fn": "isSet", "argv": [{"ref": "AccountId"}]},
                {"fn": "isSet", "argv": [{"ref": "AccountIdEndpointMode"}]},
                {
                    "fn": "stringEquals",
                    "argv": [{"ref": "AccountIdEndpointMode"}, "disabled"],
                },
            ],
            "endpoint": {
                "url": "https://otherservice.us-west-2.amazonaws.com/"
            },
            "type": "endpoint",
        },
        {
            "documentation": "Raise an error when account ID is unset but AccountIdEndpointMode is set to required.",
            "conditions": [
                {
                    "fn": "not",
                    "argv": [{"fn": "isSet", "argv": [{"ref": "AccountId"}]}],
                },
                {"fn": "isSet", "argv": [{"ref": "AccountIdEndpointMode"}]},
                {
                    "fn": "stringEquals",
                    "argv": [{"ref": "AccountIdEndpointMode"}, "required"],
                },
            ],
            "error": "AccountIdEndpointMode is required but no AccountID was provided",
            "type": "error",
        },
        {
            "documentation": "Template account ID into the URI when account ID is set and AccountIdEndpointMode is "
            "set to required.",
            "conditions": [
                {"fn": "isSet", "argv": [{"ref": "AccountId"}]},
                {"fn": "isSet", "argv": [{"ref": "AccountIdEndpointMode"}]},
                {
                    "fn": "stringEquals",
                    "argv": [{"ref": "AccountIdEndpointMode"}, "required"],
                },
            ],
            "endpoint": {
                "url": "https://{AccountId}.otherservice.us-west-2.amazonaws.com"
            },
            "type": "endpoint",
        },
        {
            "documentation": "Fallback when AccountID is unset but AccountIdEndpointMode is set to preferred.",
            "conditions": [
                {
                    "fn": "not",
                    "argv": [{"fn": "isSet", "argv": [{"ref": "AccountId"}]}],
                },
                {"fn": "isSet", "argv": [{"ref": "AccountIdEndpointMode"}]},
                {
                    "fn": "stringEquals",
                    "argv": [{"ref": "AccountIdEndpointMode"}, "preferred"],
                },
            ],
            "endpoint": {
                "url": "https://otherservice.us-west-2.amazonaws.com/"
            },
            "type": "endpoint",
        },
    ],
}

FAKE_SERVICE_MODEL = {
    "version": "2.0",
    "documentation": "",
    "metadata": {
        "apiVersion": "2020-02-02",
        "endpointPrefix": "otherservice",
        "protocol": "rest-xml",
        "serviceFullName": "Other Service",
        "serviceId": "Other Service",
        "signatureVersion": "v4",
        "signingName": "otherservice",
        "uid": "otherservice-2020-02-02",
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


@pytest.mark.parametrize(
    "account_id_endpoint_mode, expected_endpoint, expected_error, account_id_in_url",
    [
        # Test case for 'preferred' mode: Account ID is in the URL
        (
            'preferred',
            'https://123456789012.otherservice.us-west-2.amazonaws.com/',
            None,
            True,
        ),
        # Test case for 'disabled' mode: Account ID is not in the URL
        (
            'disabled',
            'https://otherservice.us-west-2.amazonaws.com/',
            None,
            False,
        ),
        # Test case for 'required' mode: Error is raised due to missing Account ID
        (
            'required',
            None,
            'AccountIdEndpointMode is required but no AccountID was provided',
            False,
        ),
    ],
)
def test_account_id_endpoint_resolution(
    account_id_endpoint_mode,
    expected_endpoint,
    expected_error,
    account_id_in_url,
    patched_session,
    monkeypatch,
):
    account_id = '123456789012'
    patch_load_service_model(
        patched_session, monkeypatch, FAKE_SERVICE_MODEL, FAKE_RULESET
    )

    if account_id_endpoint_mode != 'required':
        monkeypatch.setenv('AWS_ACCOUNT_ID', account_id)

    client = patched_session.create_client(
        'otherservice',
        region_name='us-west-2',
        config=Config(account_id_endpoint_mode=account_id_endpoint_mode),
    )

    # If we expect an error, assert that the error is raised
    if expected_error:
        with pytest.raises(EndpointResolutionError) as exc_info:
            with ClientHTTPStubber(client, strict=True) as http_stubber:
                http_stubber.add_response()
                client.mock_operation(MockOpParam='mock-op-param-value')
        assert str(exc_info.value) == expected_error
    else:
        # If no error is expected, verify the endpoint resolution
        with ClientHTTPStubber(client, strict=True) as http_stubber:
            http_stubber.add_response(status=200, body=b'{}')
            client.mock_operation(MockOpParam='mock-op-param-value')
            request = http_stubber.requests[0]

            if account_id_in_url:
                assert account_id in request.url, (
                    f"Account ID should be in the URL, but it's not: {request.url}"
                )
            else:
                assert account_id not in request.url, (
                    f"Account ID should not be in the URL, but it is: {request.url}"
                )
            assert request.url == expected_endpoint, (
                f"Expected endpoint '{expected_endpoint}', but got: {request.url}"
            )


@pytest.mark.parametrize(
    "account_id, account_id_endpoint_mode, expected_feature_ids",
    [
        # Feature IDs:
        #   ACCOUNT_ID_MODE_PREFERRED -> P
        #   ACCOUNT_ID_MODE_DISABLED  -> Q
        #   ACCOUNT_ID_MODE_REQUIRED  -> R
        #   RESOLVED_ACCOUNT_ID       -> T
        ('123456789012', 'preferred', ['P', 'T']),
        ('123456789012', 'disabled', ['Q', 'T']),
        ('123456789012', 'required', ['R', 'T']),
        (None, 'preferred', ['P']),
        ('', 'preferred', ['P']),
    ],
)
def test_user_agent_has_account_id_endpoint_feature_ids(
    patched_session,
    monkeypatch,
    account_id,
    account_id_endpoint_mode,
    expected_feature_ids,
):
    if account_id is not None:
        monkeypatch.setenv('AWS_ACCOUNT_ID', account_id)
    else:
        monkeypatch.delenv('AWS_ACCOUNT_ID', raising=False)

    patch_load_service_model(
        patched_session, monkeypatch, FAKE_SERVICE_MODEL, FAKE_RULESET
    )

    client = patched_session.create_client(
        'otherservice',
        region_name='us-west-2',
        config=Config(account_id_endpoint_mode=account_id_endpoint_mode),
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response()
        client.mock_operation(MockOpParam='mock-op-param-value')
    ua_string = get_captured_ua_strings(http_stubber)[0]
    feature_list = parse_registered_feature_ids(ua_string)
    assert all(item in feature_list for item in expected_feature_ids)
