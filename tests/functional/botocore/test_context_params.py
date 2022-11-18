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
from tests import ClientHTTPStubber, mock

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
        }
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


def patch_load_service_model(
    session, monkeypatch, service_model_json, ruleset_json
):
    def mock_load_service_model(service_name, type_name, api_version=None):
        if type_name == 'service-2':
            return service_model_json
        if type_name == 'endpoint-rule-set-1':
            return ruleset_json

    loader = session.get_component('data_loader')
    monkeypatch.setattr(loader, 'load_service_model', mock_load_service_model)


@pytest.mark.parametrize(
    'service_name,service_model,ruleset,call_should_include_ctx_param',
    [
        # s3
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            True,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            False,
        ),
        (
            's3',
            FAKE_S3_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        # s3control
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            True,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            False,
        ),
        (
            's3control',
            FAKE_S3CONTROL_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,
        ),
        # botocore does not currently support client context params for
        # services other than s3 and s3-control.
        (
            'otherservice',
            FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            False,  # would be True for s3 and s3control
        ),
        (
            'otherservice',
            FAKE_MODEL_WITH_CLIENT_CONTEXT_PARAM,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,  # same as for s3 and s3control
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITH_CLIENT_CONTEXT_PARAM,
            False,  # same as for s3 and s3control
        ),
        (
            'otherservice',
            FAKE_MODEL_WITHOUT_ANY_CONTEXT_PARAMS,
            FAKE_RULESET_WITHOUT_ANY_CONTEXT_PARAMS,
            False,  # same as for s3 and s3control
        ),
    ],
)
def test_client_context_param_sent_to_endpoint_resolver(
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

    # construct client using patched loader and a config object with an s3
    # section that sets the foo_context_param to a value
    client = patched_session.create_client(
        service_name,
        region_name='us-east-1',
        config=Config(
            s3={'foo_client_context_param_name': 'foo_context_param_value'}
        ),
    )

    # Stub client to prevent a request from getting sent and asceertain that
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

    if call_should_include_ctx_param:
        mock_resolve_endpoint.assert_called_once_with(
            Region='us-east-1',
            FooClientContextParamName='foo_context_param_value',
        )
    else:
        mock_resolve_endpoint.assert_called_once_with(Region='us-east-1')


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
