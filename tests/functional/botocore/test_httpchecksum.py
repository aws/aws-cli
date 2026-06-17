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

from botocore.compat import HAS_CRT
from botocore.config import Config
from botocore.exceptions import FlexibleChecksumError
from tests import ClientHTTPStubber, patch_load_service_model
from tests.functional.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)

TEST_CHECKSUM_SERVICE_MODEL = {
    "version": "2.0",
    "documentation": "This is a test service.",
    "metadata": {
        "apiVersion": "2023-01-01",
        "endpointPrefix": "test",
        "protocol": "rest-json",
        "jsonVersion": "1.1",
        "serviceFullName": "Test Service",
        "serviceId": "Test Service",
        "signatureVersion": "v4",
        "signingName": "testservice",
        "uid": "testservice-2023-01-01",
    },
    "operations": {
        "HttpChecksumOperation": {
            "name": "HttpChecksumOperation",
            "http": {"method": "POST", "requestUri": "/HttpChecksumOperation"},
            "input": {"shape": "SomeInput"},
            "output": {"shape": "SomeOutput"},
            "httpChecksum": {
                "requestChecksumRequired": True,
                "requestAlgorithmMember": "checksumAlgorithm",
                "requestValidationModeMember": "validationMode",
                "responseAlgorithms": [
                    "CRC32",
                    "CRC32C",
                    "CRC64NVME",
                    "SHA1",
                    "SHA256",
                    "SHA512",
                    "MD5",
                    "XXHASH64",
                    "XXHASH3",
                    "XXHASH128",
                ],
            },
        },
        "HttpChecksumStreamingOperation": {
            "name": "HttpChecksumStreamingOperation",
            "http": {
                "method": "POST",
                "requestUri": "/HttpChecksumStreamingOperation",
            },
            "input": {"shape": "SomeStreamingInput"},
            "output": {"shape": "SomeStreamingOutput"},
            "httpChecksum": {
                "requestChecksumRequired": True,
                "requestAlgorithmMember": "checksumAlgorithm",
                "requestValidationModeMember": "validationMode",
                "responseAlgorithms": [
                    "CRC32",
                    "CRC32C",
                    "CRC64NVME",
                    "SHA1",
                    "SHA256",
                    "SHA512",
                    "MD5",
                    "XXHASH64",
                    "XXHASH3",
                    "XXHASH128",
                ],
            },
        },
    },
    "shapes": {
        "ChecksumAlgorithm": {
            "type": "string",
            "enum": {
                "CRC32",
                "CRC32C",
                "CRC64NVME",
                "SHA1",
                "SHA256",
                "SHA512",
                "MD5",
                "XXHASH64",
                "XXHASH3",
                "XXHASH128",
            },
            "member": {"shape": "MockOpParam"},
        },
        "ValidationMode": {"type": "string", "enum": {"ENABLE"}},
        "String": {"type": "string"},
        "Blob": {"type": "blob"},
        "SomeStreamingOutput": {
            "type": "structure",
            "members": {"body": {"shape": "Blob", "streaming": True}},
            "payload": "body",
        },
        "SomeStreamingInput": {
            "type": "structure",
            "required": ["body"],
            "members": {
                "body": {
                    "shape": "Blob",
                    "streaming": True,
                },
                "validationMode": {
                    "shape": "ValidationMode",
                    "location": "header",
                    "locationName": "x-amz-response-validation-mode",
                },
                "checksumAlgorithm": {
                    "shape": "ChecksumAlgorithm",
                    "location": "header",
                    "locationName": "x-amz-request-algorithm",
                },
            },
            "payload": "body",
        },
        "SomeInput": {
            "type": "structure",
            "required": ["body"],
            "members": {
                "body": {"shape": "String"},
                "validationMode": {
                    "shape": "ValidationMode",
                    "location": "header",
                    "locationName": "x-amz-response-validation-mode",
                },
                "checksumAlgorithm": {
                    "shape": "ChecksumAlgorithm",
                    "location": "header",
                    "locationName": "x-amz-request-algorithm",
                },
                "ChecksumMD5": {
                    "shape": "ChecksumMD5",
                    "location": "header",
                    "locationName": "x-amz-checksum-md5",
                },
            },
            "payload": "body",
        },
        "SomeOutput": {
            "type": "structure",
        },
        "ChecksumMD5": {
            "type": "string",
        },
    },
}

TEST_CHECKSUM_RULESET = {
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


def setup_test_client(patched_session, monkeypatch, config=None):
    patch_load_service_model(
        patched_session,
        monkeypatch,
        TEST_CHECKSUM_SERVICE_MODEL,
        TEST_CHECKSUM_RULESET,
    )
    return patched_session.create_client(
        "testservice", region_name="us-west-2", config=config
    )


def _request_checksum_calculation_cases():
    request_payload = "Hello world"
    cases = [
        (
            None,
            request_payload,
            {
                "x-amz-request-algorithm": "CRC32",
                "x-amz-checksum-crc32": "i9aeUg==",
            },
        ),
        (
            "CRC32",
            request_payload,
            {
                "x-amz-request-algorithm": "CRC32",
                "x-amz-checksum-crc32": "i9aeUg==",
            },
        ),
        (
            "SHA1",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA1",
                "x-amz-checksum-sha1": "e1AsOh9IyGCa4hLN+2Od7jlnP14=",
            },
        ),
        (
            "SHA256",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA256",
                "x-amz-checksum-sha256": "ZOyIygCyaOW6GjVnihtTFtIS9PNmskdyMlNKiuyjfzw=",
            },
        ),
        (
            "SHA512",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA512",
                "x-amz-checksum-sha512": "t/eDuu2Cl/DbkXRiGE/08I5pwtXl95qUJgD5cl9Yzh8pwYE5v4CwbA//K900c4RS7PQMSIwip+PYDN9vnBwNRw==",
            },
        ),
    ]
    if HAS_CRT:
        cases.extend(
            [
                (
                    "CRC32C",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "CRC32C",
                        "x-amz-checksum-crc32c": "crUfeA==",
                    },
                ),
                (
                    "CRC64NVME",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "CRC64NVME",
                        "x-amz-checksum-crc64nvme": "OOJZ0D8xKts=",
                    },
                ),
                (
                    "XXHASH64",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH64",
                        "x-amz-checksum-xxhash64": "xQCwyRKzdtg=",
                    },
                ),
                (
                    "XXHASH3",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH3",
                        "x-amz-checksum-xxhash3": "tqy52Eo4/3Q=",
                    },
                ),
                (
                    "XXHASH128",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH128",
                        "x-amz-checksum-xxhash128": "c1H4mBL5c4K5HQWzHgTdfw==",
                    },
                ),
            ]
        )
    return cases


@pytest.mark.parametrize(
    "checksum_algorithm, request_payload, expected_headers",
    _request_checksum_calculation_cases(),
)
def test_request_checksum_calculation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    request_payload,
    expected_headers,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200, body=b"<response/>")
        operation_kwargs = {"body": request_payload}
        if checksum_algorithm:
            operation_kwargs["checksumAlgorithm"] = checksum_algorithm
        client.http_checksum_operation(**operation_kwargs)
        actual_headers = http_stubber.requests[0].headers
        for key, val in expected_headers.items():
            assert key in actual_headers
            assert actual_headers[key].decode() == val


def _streaming_request_checksum_calculation_cases():
    request_payload = "Hello world"
    cases = [
        (
            None,
            request_payload,
            {
                "x-amz-request-algorithm": "CRC32",
                "content-encoding": "aws-chunked",
                "x-amz-trailer": "x-amz-checksum-crc32",
            },
            {"x-amz-checksum-crc32": "i9aeUg=="},
        ),
        (
            "CRC32",
            request_payload,
            {
                "x-amz-request-algorithm": "CRC32",
                "content-encoding": "aws-chunked",
                "x-amz-trailer": "x-amz-checksum-crc32",
            },
            {"x-amz-checksum-crc32": "i9aeUg=="},
        ),
        (
            "SHA1",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA1",
                "content-encoding": "aws-chunked",
                "x-amz-trailer": "x-amz-checksum-sha1",
            },
            {"x-amz-checksum-sha1": "e1AsOh9IyGCa4hLN+2Od7jlnP14="},
        ),
        (
            "SHA256",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA256",
                "content-encoding": "aws-chunked",
                "x-amz-trailer": "x-amz-checksum-sha256",
            },
            {
                "x-amz-checksum-sha256": "ZOyIygCyaOW6GjVnihtTFtIS9PNmskdyMlNKiuyjfzw="
            },
        ),
        (
            "SHA512",
            request_payload,
            {
                "x-amz-request-algorithm": "SHA512",
                "content-encoding": "aws-chunked",
                "x-amz-trailer": "x-amz-checksum-sha512",
            },
            {
                "x-amz-checksum-sha512": "t/eDuu2Cl/DbkXRiGE/08I5pwtXl95qUJgD5cl9Yzh8pwYE5v4CwbA//K900c4RS7PQMSIwip+PYDN9vnBwNRw=="
            },
        ),
    ]
    if HAS_CRT:
        cases.extend(
            [
                (
                    "CRC32C",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "CRC32C",
                        "content-encoding": "aws-chunked",
                        "x-amz-trailer": "x-amz-checksum-crc32c",
                    },
                    {"x-amz-checksum-crc32c": "crUfeA=="},
                ),
                (
                    "CRC64NVME",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "CRC64NVME",
                        "content-encoding": "aws-chunked",
                        "x-amz-trailer": "x-amz-checksum-crc64nvme",
                    },
                    {"x-amz-checksum-crc64nvme": "OOJZ0D8xKts="},
                ),
                (
                    "XXHASH64",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH64",
                        "content-encoding": "aws-chunked",
                        "x-amz-trailer": "x-amz-checksum-xxhash64",
                    },
                    {"x-amz-checksum-xxhash64": "xQCwyRKzdtg="},
                ),
                (
                    "XXHASH3",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH3",
                        "content-encoding": "aws-chunked",
                        "x-amz-trailer": "x-amz-checksum-xxhash3",
                    },
                    {"x-amz-checksum-xxhash3": "tqy52Eo4/3Q="},
                ),
                (
                    "XXHASH128",
                    request_payload,
                    {
                        "x-amz-request-algorithm": "XXHASH128",
                        "content-encoding": "aws-chunked",
                        "x-amz-trailer": "x-amz-checksum-xxhash128",
                    },
                    {"x-amz-checksum-xxhash128": "c1H4mBL5c4K5HQWzHgTdfw=="},
                ),
            ]
        )
    return cases


@pytest.mark.parametrize(
    "checksum_algorithm, request_payload, expected_headers, expected_trailers",
    _streaming_request_checksum_calculation_cases(),
)
def test_streaming_request_checksum_calculation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    request_payload,
    expected_headers,
    expected_trailers,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=200, body=b"<response/>")
        operation_kwargs = {"body": request_payload}
        if checksum_algorithm:
            operation_kwargs["checksumAlgorithm"] = checksum_algorithm
        client.http_checksum_streaming_operation(**operation_kwargs)
        request = http_stubber.requests[0]
        actual_headers = request.headers
        for key, val in expected_headers.items():
            assert key in actual_headers
            assert actual_headers[key].decode() == val
        read_body = request.body.read()
        for key, val in expected_trailers.items():
            assert f"{key}:{val}".encode() in read_body


def _successful_response_checksum_validation_cases():
    response_payload = "Hello world"
    cases = [
        (
            "CRC32",
            response_payload,
            {"x-amz-checksum-crc32": "i9aeUg=="},
        ),
        (
            "SHA1",
            response_payload,
            {"x-amz-checksum-sha1": "e1AsOh9IyGCa4hLN+2Od7jlnP14="},
        ),
        (
            "SHA256",
            response_payload,
            {
                "x-amz-checksum-sha256": "ZOyIygCyaOW6GjVnihtTFtIS9PNmskdyMlNKiuyjfzw="
            },
        ),
        (
            "SHA512",
            response_payload,
            {
                "x-amz-checksum-sha512": "t/eDuu2Cl/DbkXRiGE/08I5pwtXl95qUJgD5cl9Yzh8pwYE5v4CwbA//K900c4RS7PQMSIwip+PYDN9vnBwNRw=="
            },
        ),
    ]
    if HAS_CRT:
        cases.extend(
            [
                (
                    "CRC32C",
                    response_payload,
                    {"x-amz-checksum-crc32c": "crUfeA=="},
                ),
                (
                    "CRC64NVME",
                    response_payload,
                    {"x-amz-checksum-crc64nvme": "OOJZ0D8xKts="},
                ),
                (
                    "XXHASH64",
                    response_payload,
                    {"x-amz-checksum-xxhash64": "xQCwyRKzdtg="},
                ),
                (
                    "XXHASH3",
                    response_payload,
                    {"x-amz-checksum-xxhash3": "tqy52Eo4/3Q="},
                ),
                (
                    "XXHASH128",
                    response_payload,
                    {"x-amz-checksum-xxhash128": "c1H4mBL5c4K5HQWzHgTdfw=="},
                ),
            ]
        )
    return cases


@pytest.mark.parametrize(
    "checksum_algorithm, response_payload, response_headers",
    _successful_response_checksum_validation_cases(),
)
def test_successful_response_checksum_validation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    response_payload,
    response_headers,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=response_payload.encode(),
            headers=response_headers,
        )
        operation_kwargs = {
            "body": response_payload,
            "checksumAlgorithm": checksum_algorithm,
        }

        client.http_checksum_operation(**operation_kwargs)


@pytest.mark.parametrize(
    "checksum_algorithm, response_payload, response_headers",
    _successful_response_checksum_validation_cases(),
)
def test_successful_streaming_response_checksum_validation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    response_payload,
    response_headers,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=response_payload.encode(),
            headers=response_headers,
        )
        response = client.http_checksum_streaming_operation(
            body=response_payload,
            checksumAlgorithm=checksum_algorithm,
        )
        response["body"].read()


def _unsuccessful_response_checksum_validation_cases():
    response_payload = "Hello world"
    cases = [
        (
            "CRC32",
            response_payload,
            {"x-amz-checksum-crc32": "bm90LWEtY2hlY2tzdW0="},
            "i9aeUg==",
        ),
        (
            "SHA1",
            response_payload,
            {"x-amz-checksum-sha1": "bm90LWEtY2hlY2tzdW0="},
            "e1AsOh9IyGCa4hLN+2Od7jlnP14=",
        ),
        (
            "SHA256",
            response_payload,
            {"x-amz-checksum-sha256": "bm90LWEtY2hlY2tzdW0="},
            "ZOyIygCyaOW6GjVnihtTFtIS9PNmskdyMlNKiuyjfzw=",
        ),
        (
            "SHA512",
            response_payload,
            {"x-amz-checksum-sha512": "bm90LWEtY2hlY2tzdW0="},
            "t/eDuu2Cl/DbkXRiGE/08I5pwtXl95qUJgD5cl9Yzh8pwYE5v4CwbA//K900c4RS7PQMSIwip+PYDN9vnBwNRw==",
        ),
    ]
    if HAS_CRT:
        cases.extend(
            [
                (
                    "CRC32C",
                    response_payload,
                    {"x-amz-checksum-crc32c": "bm90LWEtY2hlY2tzdW0="},
                    "crUfeA==",
                ),
                (
                    "CRC64NVME",
                    response_payload,
                    {"x-amz-checksum-crc64nvme": "bm90LWEtY2hlY2tzdW0="},
                    "OOJZ0D8xKts=",
                ),
                (
                    "XXHASH64",
                    response_payload,
                    {"x-amz-checksum-xxhash64": "bm90LWEtY2hlY2tzdW0="},
                    "xQCwyRKzdtg=",
                ),
                (
                    "XXHASH3",
                    response_payload,
                    {"x-amz-checksum-xxhash3": "bm90LWEtY2hlY2tzdW0="},
                    "tqy52Eo4/3Q=",
                ),
                (
                    "XXHASH128",
                    response_payload,
                    {"x-amz-checksum-xxhash128": "bm90LWEtY2hlY2tzdW0="},
                    "c1H4mBL5c4K5HQWzHgTdfw==",
                ),
            ]
        )
    return cases


@pytest.mark.parametrize(
    "checksum_algorithm, response_payload, response_headers, expected_checksum",
    _unsuccessful_response_checksum_validation_cases(),
)
def test_unsuccessful_response_checksum_validation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    response_payload,
    response_headers,
    expected_checksum,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=response_payload.encode(),
            headers=response_headers,
        )
        operation_kwargs = {
            "body": response_payload,
            "checksumAlgorithm": checksum_algorithm,
        }
        with pytest.raises(FlexibleChecksumError) as expected_error:
            client.http_checksum_operation(**operation_kwargs)
        error_msg = "Expected checksum {} did not match calculated checksum: {}".format(
            response_headers[f'x-amz-checksum-{checksum_algorithm.lower()}'],
            expected_checksum,
        )
        assert str(expected_error.value) == error_msg


@pytest.mark.parametrize(
    "checksum_algorithm, response_payload, response_headers, expected_checksum",
    _unsuccessful_response_checksum_validation_cases(),
)
def test_unsuccessful_streaming_response_checksum_validation(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    response_payload,
    response_headers,
    expected_checksum,
):
    client = setup_test_client(patched_session, monkeypatch)

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=response_payload.encode(),
            headers=response_headers,
        )
        response = client.http_checksum_streaming_operation(
            body=response_payload,
            checksumAlgorithm=checksum_algorithm,
        )
        with pytest.raises(FlexibleChecksumError) as expected_error:
            response["body"].read()
        error_msg = "Expected checksum {} did not match calculated checksum: {}".format(
            response_headers[f'x-amz-checksum-{checksum_algorithm.lower()}'],
            expected_checksum,
        )
        assert str(expected_error.value) == error_msg


def _checksum_user_agent_feature_id_cases():
    request_payload = "Hello world"
    cases = [
        (None, None, None, request_payload, ["U", "b", "Z"]),
        (
            "CRC32",
            "when_required",
            "when_required",
            request_payload,
            ["U", "a", "c"],
        ),
        (
            "SHA1",
            "when_supported",
            "when_supported",
            request_payload,
            ["X", "Z", "b"],
        ),
        (
            "SHA256",
            "when_supported",
            "when_required",
            request_payload,
            ["Y", "Z", "c"],
        ),
        (
            "SHA1",
            "when_required",
            "when_supported",
            request_payload,
            ["X", "a", "b"],
        ),
        (
            "SHA512",
            None,
            None,
            request_payload,
            ["AF", "Z", "b"],
        ),
    ]
    if HAS_CRT:
        cases.extend(
            [("CRC32C", None, None, request_payload, ["V", "Z", 'b'])]
        )
        cases.extend(
            [
                (
                    "CRC64NVME",
                    None,
                    "when_required",
                    request_payload,
                    ["W", "Z", "c"],
                )
            ]
        )
        cases.extend(
            [
                (
                    "XXHASH3",
                    None,
                    None,
                    request_payload,
                    ["AG", "Z", "b"],
                )
            ]
        )
        cases.extend(
            [
                (
                    "XXHASH64",
                    None,
                    None,
                    request_payload,
                    ["AH", "Z", "b"],
                )
            ]
        )
        cases.extend(
            [
                (
                    "XXHASH128",
                    None,
                    None,
                    request_payload,
                    ["AI", "Z", "b"],
                )
            ]
        )
    return cases


@pytest.mark.parametrize(
    "checksum_algorithm, checksum_calculation, checksum_validation, request_payload, expected_feature_ids",
    _checksum_user_agent_feature_id_cases(),
)
def test_user_agent_has_checksum_request_feature_id(
    patched_session,
    monkeypatch,
    checksum_algorithm,
    checksum_calculation,
    checksum_validation,
    request_payload,
    expected_feature_ids,
):
    client = setup_test_client(
        patched_session,
        monkeypatch,
        config=Config(
            request_checksum_calculation=checksum_calculation,
            response_checksum_validation=checksum_validation,
        ),
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=b"<response/>",
        )
        operation_kwargs = {"body": request_payload}
        if checksum_algorithm:
            operation_kwargs["checksumAlgorithm"] = checksum_algorithm
        client.http_checksum_streaming_operation(**operation_kwargs)
    ua_string = get_captured_ua_strings(http_stubber)[0]
    feature_list = parse_registered_feature_ids(ua_string)
    for feature_id in expected_feature_ids:
        assert feature_id in feature_list


def test_user_agent_has_md5_feature_id(
    patched_session,
    monkeypatch,
):
    """Test that ChecksumMD5 parameter usage registers the AE feature ID in user agent.
    This test is not part of test_user_agent_has_checksum_request_feature_id since automatic
    MD5 calculation is not supported"""

    client = setup_test_client(
        patched_session,
        monkeypatch,
    )

    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=200,
            body=b"<response/>",
        )
        client.http_checksum_operation(
            body="test", ChecksumMD5="rL0Y20zC+Fzt72VPzMSk2A=="
        )

    ua_string = get_captured_ua_strings(http_stubber)[0]
    feature_list = parse_registered_feature_ids(ua_string)

    assert "AE" in feature_list
