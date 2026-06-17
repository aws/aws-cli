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

import pytest

from botocore.config import Config
from tests import ClientHTTPStubber, mock, patch_load_service_model

# fake rulesets compatible with all fake service models below
FAKE_RULESET_TEMPLATE = {
    "version": "1.0",
    "parameters": {},
    "rules": [
        {
            "conditions": [],
            "type": "endpoint",
            "endpoint": {
                "url": "https://foo.bar",
                "properties": {},
                "headers": {},
            },
        }
    ],
}

# The region param is unrelated to context parameters and used as control in
# all test cases to ascertain that ANY EndpointProvider paramaters get
# populated.
REGION_PARAM = {
    "builtIn": "AWS::Region",
    "required": False,
    "documentation": "",
    "type": "String",
}

FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS = {
    **FAKE_RULESET_TEMPLATE,
    "parameters": {
        "Region": REGION_PARAM,
    },
}

FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM = {
    **FAKE_RULESET_TEMPLATE,
    "parameters": {
        "Region": REGION_PARAM,
        "FooClientContextParamName": {
            "required": False,
            "documentation": "",
            "type": "String",
        },
        "BarClientContextParamName": {
            "required": False,
            "documentation": "",
            "type": "String",
        },
    },
}

FAKE_RULESET_WITH_STATIC_CONTEXT_PARAM = {
    **FAKE_RULESET_TEMPLATE,
    "parameters": {
        "Region": REGION_PARAM,
        "FooStaticContextParamName": {
            "required": False,
            "documentation": "",
            "type": "String",
        },
    },
}

FAKE_RULESET_WITH_DYNAMIC_CONTEXT_PARAM = {
    **FAKE_RULESET_TEMPLATE,
    "parameters": {
        "Region": REGION_PARAM,
        "FooDynamicContextParamName": {
            "required": False,
            "documentation": "",
            "type": "String",
        },
    },
}

# fake models for "otherservice"

FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS = {
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

FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM = {
    **FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
    "clientContextParams": {
        "FooClientContextParamName": {
            "documentation": "My mock client context parameter",
            "type": "string",
        },
        "BarClientContextParamName": {
            "documentation": "My mock client context parameter",
            "type": "string",
        },
    },
}

FAKE_MODEL_WITH_STATIC_CONTEXT_PARAM = {
    **FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
    "operations": {
        "MockOperation": {
            "name": "MockOperation",
            "http": {"method": "GET", "requestUri": "/"},
            "input": {"shape": "MockOperationRequest"},
            "documentation": "",
            "staticContextParams": {
                "FooStaticContextParamName": {
                    "value": "foo-static-context-param-value"
                }
            },
        },
    },
}

FAKE_MODEL_WITH_DYNAMIC_CONTEXT_PARAM = {
    **FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
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
                    "contextParam": {"name": "FooDynamicContextParamName"},
                },
            },
        },
    },
    #
}

# fake models for s3 and s3control, the only services botocore currently
# supports client context parameters for

S3_METADATA = {
    "apiVersion": "2006-03-01",
    "checksumFormat": "md5",
    "endpointPrefix": "s3",
    "globalEndpoint": "s3.amazonaws.com",
    "protocol": "rest-xml",
    "serviceAbbreviation": "Amazon S3",
    "serviceFullName": "Amazon Simple Storage Service",
    "serviceId": "S3",
    "signatureVersion": "s3",
    "uid": "s3-2006-03-01",
}

FAKE_S3_MODEL_WITHOUT_ANY_CONTEXT_PARAMS = {
    **FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
    "metadata": S3_METADATA,
}

FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM = {
    **FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
    "metadata": S3_METADATA,
}

S3CONTROL_METADATA = {
    "apiVersion": "2018-08-20",
    "endpointPrefix": "s3-control",
    "protocol": "rest-xml",
    "serviceFullName": "AWS S3 Control",
    "serviceId": "S3 Control",
    "signatureVersion": "s3v4",
    "signingName": "s3",
    "uid": "s3control-2018-08-20",
}

FAKE_S3CONTROL_MODEL_WITHOUT_ANY_CONTEXT_PARAMS = {
    **FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
    "metadata": S3CONTROL_METADATA,
}

FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM = {
    **FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
    "metadata": S3CONTROL_METADATA,
}
CLIENT_CONTEXT_PARAM_INPUT = {
    "foo_client_context_param_name": "foo_context_param_value"
}
OTHER_CLIENT_CONTEXT_PARAM_INPUT = {
    "bar_client_context_param_name": "bar_value"
}

CONFIG_WITH_S3 = Config(s3=CLIENT_CONTEXT_PARAM_INPUT)
CONFIG_WITH_CLIENT_CONTEXT_PARAMS = Config(
    client_context_params=CLIENT_CONTEXT_PARAM_INPUT
)
CONFIG_WITH_S3_AND_CLIENT_CONTEXT_PARAMS = Config(
    s3=CLIENT_CONTEXT_PARAM_INPUT,
    client_context_params=OTHER_CLIENT_CONTEXT_PARAM_INPUT,
)
CONFIG_WITH_CONFLICTING_S3_AND_CLIENT_CONTEXT_PARAMS = Config(
    s3=CLIENT_CONTEXT_PARAM_INPUT,
    client_context_params={"foo_client_context_param_name": "bar_value"},
)
NO_CTX_PARAM_EXPECTED_CALL_KWARGS = {"Region": "us-east-1"}
CTX_PARAM_EXPECTED_CALL_KWARGS = {
    **NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
    "FooClientContextParamName": "foo_context_param_value",
}
MULTIPLE_CONTEXT_PARAMS_EXPECTED_CALL_KWARGS = {
    **CTX_PARAM_EXPECTED_CALL_KWARGS,
    "BarClientContextParamName": "bar_value",
}


@pytest.mark.parametrize(
    'service_name,service_model,ruleset,config,expected_call_kwargs',
    [
        # s3
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_CLIENT_CONTEXT_PARAMS,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        # use both s3 and client_context_params when they don't overlap
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3_AND_CLIENT_CONTEXT_PARAMS,
            MULTIPLE_CONTEXT_PARAMS_EXPECTED_CALL_KWARGS,
        ),
        # use s3 over client_context_params when they overlap
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_CONFLICTING_S3_AND_CLIENT_CONTEXT_PARAMS,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        # s3control
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_CLIENT_CONTEXT_PARAMS,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        # use both s3 and client_context_params when they don't overlap
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3_AND_CLIENT_CONTEXT_PARAMS,
            MULTIPLE_CONTEXT_PARAMS_EXPECTED_CALL_KWARGS,
        ),
        # use s3 over client_context_params when they overlap
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_CONFLICTING_S3_AND_CLIENT_CONTEXT_PARAMS,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        # otherservice
        (
            'otherservice',
            FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            CONFIG_WITH_S3,
            NO_CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            CONFIG_WITH_CLIENT_CONTEXT_PARAMS,
            CTX_PARAM_EXPECTED_CALL_KWARGS,
        ),
    ],
)
def test_client_context_param_sent_to_endpoint_resolver(
    monkeypatch,
    patched_session,
    service_name,
    service_model,
    ruleset,
    config,
    expected_call_kwargs,
):
    # patch loader to return fake service model and fake endpoint ruleset
    patch_load_service_model(
        patched_session, monkeypatch, service_model, ruleset
    )

    # construct client using patched loader and a config object with an s3
    # or client_context_param section that sets the foo_context_param to a value
    client = patched_session.create_client(
        service_name,
        region_name='us-east-1',
        config=config,
    )

    # Stub client to prevent a request from getting sent and ascertain that
    # only a single request would get sent. Wrap the EndpointProvider's
    # resolve_endpoint method for inspecting the arguments it gets called with.
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200)
        with mock.patch.object(
            client._ruleset_resolver._provider,
            'resolve_endpoint',
            wraps=client._ruleset_resolver._provider.resolve_endpoint,
        ) as mock_resolve_endpoint:
            client.mock_operation(MockOpParam='mock-op-param-value')

        mock_resolve_endpoint.assert_called_once_with(**expected_call_kwargs)


@pytest.mark.parametrize(
    'service_name,service_model,ruleset,call_should_include_ctx_param',
    [
        (
            'otherservice',
            FAKE_MODEL_WITH_STATIC_CONTEXT_PARAM,
            FAKE_RULESET_WITH_STATIC_CONTEXT_PARAM,
            True,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITH_STATIC_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_STATIC_CONTEXT_PARAM,
            False,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
    ],
)
def test_static_context_param_sent_to_endpoint_resolver(
    monkeypatch,
    patched_session,
    service_name,
    service_model,
    ruleset,
    call_should_include_ctx_param,
):
    # patch loader to return fake service model and fake endpoint ruleset
    patch_load_service_model(
        patched_session, monkeypatch, service_model, ruleset
    )

    # construct client using patched loader, but no special config is required
    # for static context param to take effect
    client = patched_session.create_client(
        service_name, region_name='us-east-1'
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200)
        with mock.patch.object(
            client._ruleset_resolver._provider,
            'resolve_endpoint',
            wraps=client._ruleset_resolver._provider.resolve_endpoint,
        ) as mock_resolve_endpoint:
            client.mock_operation(MockOpParam='mock-op-param-value')

    if call_should_include_ctx_param:
        mock_resolve_endpoint.assert_called_once_with(
            Region='us-east-1',
            FooStaticContextParamName='foo-static-context-param-value',
        )
    else:
        mock_resolve_endpoint.assert_called_once_with(Region='us-east-1')


@pytest.mark.parametrize(
    'service_name,service_model,ruleset,call_should_include_ctx_param',
    [
        (
            'otherservice',
            FAKE_MODEL_WITH_DYNAMIC_CONTEXT_PARAM,
            FAKE_RULESET_WITH_DYNAMIC_CONTEXT_PARAM,
            True,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITH_DYNAMIC_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_DYNAMIC_CONTEXT_PARAM,
            False,
        ),
    ],
)
def test_dynamic_context_param_sent_to_endpoint_resolver(
    monkeypatch,
    patched_session,
    service_name,
    service_model,
    ruleset,
    call_should_include_ctx_param,
):
    # patch loader to return fake service model and fake endpoint ruleset
    patch_load_service_model(
        patched_session, monkeypatch, service_model, ruleset
    )

    # construct client using patched loader, but no special config is required
    # for static context param to take effect
    client = patched_session.create_client(
        service_name, region_name='us-east-1'
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200)
        with mock.patch.object(
            client._ruleset_resolver._provider,
            'resolve_endpoint',
            wraps=client._ruleset_resolver._provider.resolve_endpoint,
        ) as mock_resolve_endpoint:
            client.mock_operation(MockOpParam='mock-op-param-value')

    if call_should_include_ctx_param:
        mock_resolve_endpoint.assert_called_once_with(
            Region='us-east-1',
            FooDynamicContextParamName='mock-op-param-value',
        )
    else:
        mock_resolve_endpoint.assert_called_once_with(Region='us-east-1')


def test_dynamic_context_param_from_event_handler_sent_to_endpoint_resolver(
    monkeypatch,
    patched_session,
):
    # patch loader to return fake service model and fake endpoint ruleset
    patch_load_service_model(
        patched_session,
        monkeypatch,
        FAKE_MODEL_WITH_DYNAMIC_CONTEXT_PARAM,
        FAKE_RULESET_WITH_DYNAMIC_CONTEXT_PARAM,
    )

    # event handler for provide-client-params that modifies the value of the
    # MockOpParam parameter
    def change_param(params, **kwargs):
        params['MockOpParam'] = 'mock-op-param-value-2'

    client = patched_session.create_client(
        'otherservice', region_name='us-east-1'
    )
    client.meta.events.register_last(
        'provide-client-params.other-service.*', change_param
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200)
        with mock.patch.object(
            client._ruleset_resolver._provider,
            'resolve_endpoint',
            wraps=client._ruleset_resolver._provider.resolve_endpoint,
        ) as mock_resolve_endpoint:
            client.mock_operation(MockOpParam='mock-op-param-value-1')

    mock_resolve_endpoint.assert_called_once_with(
        Region='us-east-1',
        FooDynamicContextParamName='mock-op-param-value-2',
    )
