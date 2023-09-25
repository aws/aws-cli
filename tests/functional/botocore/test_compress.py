# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import gzip

import pytest

from botocore.compress import COMPRESSION_MAPPING
from botocore.config import Config
from tests import ALL_SERVICES, ClientHTTPStubber, patch_load_service_model

FAKE_MODEL = {
    "version": "2.0",
    "documentation": "",
    "metadata": {
        "apiVersion": "2020-02-02",
        "endpointPrefix": "otherservice",
        "protocol": "query",
        "serviceFullName": "Other Service",
        "serviceId": "Other Service",
        "signatureVersion": "v4",
        "signingName": "otherservice",
        "uid": "otherservice-2020-02-02",
    },
    "operations": {
        "MockOperation": {
            "name": "MockOperation",
            "http": {"method": "POST", "requestUri": "/"},
            "input": {"shape": "MockOperationRequest"},
            "documentation": "",
            "requestcompression": {
                "encodings": ["gzip"],
            },
        },
    },
    "shapes": {
        "MockOpParamList": {
            "type": "list",
            "member": {"shape": "MockOpParam"},
        },
        "MockOpParam": {
            "type": "structure",
            "members": {"MockOpParam": {"shape": "MockOpParamValue"}},
        },
        "MockOpParamValue": {
            "type": "string",
        },
        "MockOperationRequest": {
            "type": "structure",
            "required": ["MockOpParamList"],
            "members": {
                "MockOpParamList": {
                    "shape": "MockOpParamList",
                    "documentation": "",
                },
            },
        },
    },
}

FAKE_RULESET = {
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


def _all_compression_operations():
    for service_model in ALL_SERVICES:
        for operation_name in service_model.operation_names:
            operation_model = service_model.operation_model(operation_name)
            if operation_model.request_compression is not None:
                yield operation_model


@pytest.mark.parametrize("operation_model", _all_compression_operations())
def test_no_unknown_compression_encodings(operation_model):
    for encoding in operation_model.request_compression["encodings"]:
        assert encoding in COMPRESSION_MAPPING.keys(), (
            f"Found unknown compression encoding '{encoding}' "
            f"in operation {operation_model.name}."
        )


def test_compression(patched_session, monkeypatch):
    patch_load_service_model(
        patched_session, monkeypatch, FAKE_MODEL, FAKE_RULESET
    )
    client = patched_session.create_client(
        "otherservice",
        region_name="us-west-2",
        config=Config(request_min_compression_size_bytes=100),
    )
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200, body=b"<response/>")
        params_list = [
            {"MockOpParam": f"MockOpParamValue{i}"} for i in range(1, 21)
        ]
        client.mock_operation(MockOpParamList=params_list)
        param_template = (
            "MockOpParamList.member.{i}.MockOpParam=MockOpParamValue{i}"
        )
        serialized_params = "&".join(
            param_template.format(i=i) for i in range(1, 21)
        )
        additional_params = "Action=MockOperation&Version=2020-02-02"
        serialized_body = f"{additional_params}&{serialized_params}"
        actual_body = gzip.decompress(http_stubber.requests[0].body)
        assert serialized_body.encode('utf-8') == actual_body
