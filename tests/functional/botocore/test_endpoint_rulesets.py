# Copyright 2012-2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
from functools import lru_cache
from pathlib import Path

import pytest

from botocore import xform_name
from botocore.compat import HAS_CRT
from botocore.config import Config
from botocore.endpoint_provider import EndpointProvider
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointResolutionError,
)
from botocore.loaders import Loader
from botocore.parsers import ResponseParserError
from tests import ClientHTTPStubber

ENDPOINT_TESTDATA_DIR = Path(__file__).parent / 'endpoint-rules'
LOADER = Loader()

# For the purpose of the tests in this file, only services for which an
# endpoint ruleset file exists matter. The existence of required endpoint
# ruleset files is asserted for in tests/functional/test_model_completeness.py
ALL_SERVICES = [
    service_name
    for service_name in LOADER.list_available_services(
        type_name='endpoint-rule-set-1'
    )
]


@pytest.fixture(scope='module')
def partitions():
    return LOADER.load_data('partitions')


@lru_cache()
def get_endpoint_tests_for_service(service_name):
    file_path = ENDPOINT_TESTDATA_DIR / service_name / 'endpoint-tests-1.json'
    if not file_path.is_file():
        raise FileNotFoundError(
            f'Cannot find endpoint tests file for "{service_name}" at '
            'path {file_path}'
        )
    with file_path.open('r') as f:
        return json.load(f)


@pytest.mark.parametrize("service_name", ALL_SERVICES)
def test_all_endpoint_tests_exist(service_name):
    """Tests the existence of endpoint-tests-1.json for each service that has
    a ruleset and verifies that content is present."""
    data = get_endpoint_tests_for_service(service_name)
    assert len(data['testCases']) > 0


def assert_all_signing_region_sets_have_length_one(rule):
    """Helper function for test_all_signing_region_sets_have_length_one()"""
    if 'endpoint' in rule:
        authSchemes = (
            rule['endpoint'].get('properties', {}).get('authSchemes', [])
        )
        for authScheme in authSchemes:
            if 'signingRegionSet' in authScheme:
                assert len(authScheme['signingRegionSet']) == 1
    for sub_rule in rule.get('rules', []):
        assert_all_signing_region_sets_have_length_one(sub_rule)


@pytest.mark.parametrize("service_name", ALL_SERVICES)
def test_all_signing_region_sets_have_length_one(service_name):
    """Checks all endpoint rulesets for endpoints that contain an authSchemes
    property with a `signingRegionSet` and asserts that it is a list of
    length 1.

    In theory, `signingRegionSet` could have >1 entries. As of writing this
    test, no service uses >1 entry, the meaning of >1 entry is poorly defined,
    and botocore cannot handle >1 entry. This test exists specifically to
    fail if a ruleset ever uses >1 entry.

    The test also fails for empty lists. While botocore would handle these
    gracefully, the expected behavior for empty `signingRegionSet` lists is
    not defined.
    """
    ruleset = LOADER.load_service_model(service_name, 'endpoint-rule-set-1')
    assert_all_signing_region_sets_have_length_one(ruleset)


def test_assert_all_signing_region_sets_have_length_one():
    """Negative test for to confirm that
    assert_all_signing_region_sets_have_length_one() actually fails when two
    sigingRegionSet entries are present."""
    with pytest.raises(AssertionError):
        assert_all_signing_region_sets_have_length_one(
            {
                "version": "1.0",
                "parameters": {},
                "rules": [
                    {
                        "conditions": [],
                        "endpoint": {
                            "url": "https://foo",
                            "properties": {
                                "authSchemes": [
                                    {
                                        "name": "sigv4a",
                                        "disableDoubleEncoding": True,
                                        "signingRegionSet": ["*", "abc"],
                                        "signingName": "myservice",
                                    }
                                ]
                            },
                            "headers": {},
                        },
                        "type": "endpoint",
                    }
                ],
            }
        )


def iter_all_test_cases():
    for service_name in ALL_SERVICES:
        test_data = get_endpoint_tests_for_service(service_name)
        for test_case in test_data['testCases']:
            yield service_name, test_case


def iter_provider_test_cases_that_produce(endpoints=False, errors=False):
    for service_name, test in iter_all_test_cases():
        input_params = test.get('params', {})
        expected_object = test['expect']
        if endpoints and 'endpoint' in expected_object:
            yield service_name, input_params, expected_object['endpoint']
        if errors and 'error' in expected_object:
            yield service_name, input_params, expected_object['error']


def iter_e2e_test_cases_that_produce(endpoints=False, errors=False):
    for service_name, test in iter_all_test_cases():
        # Not all test cases contain operation inputs for end-to-end tests.
        if 'operationInputs' not in test:
            continue
        # Each test case can contain a list of input sets for the same
        # expected result.
        for op_inputs in test['operationInputs']:
            op_params = op_inputs.get('operationParams', {})
            # Test cases that use invalid bucket names as inputs fail in
            # botocore because botocore validated bucket names before running
            # endpoint resolution.
            if op_params.get('Bucket') in ['bucket name', 'example.com#']:
                continue
            op_name = op_inputs['operationName']
            builtins = op_inputs.get('builtInParams', {})

            expected_object = test['expect']
            if endpoints and 'endpoint' in expected_object:
                expected_endpoint = expected_object['endpoint']
                expected_props = expected_endpoint.get('properties', {})
                expected_authschemes = [
                    auth_scheme['name']
                    for auth_scheme in expected_props.get('authSchemes', [])
                ]
                yield pytest.param(
                    service_name,
                    op_name,
                    op_params,
                    builtins,
                    expected_endpoint,
                    marks=pytest.mark.skipif(
                        'sigv4a' in expected_authschemes and not HAS_CRT,
                        reason="Test case expects sigv4a which requires CRT",
                    ),
                )
            if errors and 'error' in expected_object:
                yield pytest.param(
                    service_name,
                    op_name,
                    op_params,
                    builtins,
                    expected_object['error'],
                )


@pytest.mark.parametrize(
    'service_name, input_params, expected_endpoint',
    iter_provider_test_cases_that_produce(endpoints=True),
)
def test_endpoint_provider_test_cases_yielding_endpoints(
    partitions, service_name, input_params, expected_endpoint
):
    ruleset = LOADER.load_service_model(service_name, 'endpoint-rule-set-1')
    endpoint_provider = EndpointProvider(ruleset, partitions)
    endpoint = endpoint_provider.resolve_endpoint(**input_params)
    assert endpoint.url == expected_endpoint['url']
    assert endpoint.properties == expected_endpoint.get('properties', {})
    assert endpoint.headers == expected_endpoint.get('headers', {})


@pytest.mark.parametrize(
    'service_name, input_params, expected_error',
    iter_provider_test_cases_that_produce(errors=True),
)
def test_endpoint_provider_test_cases_yielding_errors(
    partitions, service_name, input_params, expected_error
):
    ruleset = LOADER.load_service_model(service_name, 'endpoint-rule-set-1')
    endpoint_provider = EndpointProvider(ruleset, partitions)
    with pytest.raises(EndpointResolutionError) as exc_info:
        endpoint_provider.resolve_endpoint(**input_params)
    assert str(exc_info.value) == expected_error


@pytest.mark.parametrize(
    'service_name, op_name, op_params, builtin_params, expected_endpoint',
    iter_e2e_test_cases_that_produce(endpoints=True),
)
def test_end_to_end_test_cases_yielding_endpoints(
    patched_session,
    service_name,
    op_name,
    op_params,
    builtin_params,
    expected_endpoint,
):
    def builtin_overwriter_handler(builtins, **kwargs):
        # must edit builtins dict in place but need to erase all existing
        # entries
        for key in list(builtins.keys()):
            del builtins[key]
        for key, val in builtin_params.items():
            builtins[key] = val

    region = builtin_params.get('AWS::Region', 'us-east-1')
    client = patched_session.create_client(
        service_name,
        region_name=region,
        # endpoint ruleset test cases do not account for host prefixes from the
        # operation model
        config=Config(inject_host_prefix=False),
    )
    client.meta.events.register_last(
        'before-endpoint-resolution', builtin_overwriter_handler
    )
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=418)
        op_fn = getattr(client, xform_name(op_name))
        try:
            op_fn(**op_params)
        except (ClientError, ResponseParserError):
            pass
        assert len(http_stubber.requests) > 0
        actual_url = http_stubber.requests[0].url
        assert actual_url.startswith(
            expected_endpoint['url']
        ), f"{actual_url} does not start with {expected_endpoint['url']}"


@pytest.mark.parametrize(
    'service_name, op_name, op_params, builtin_params, expected_error',
    iter_e2e_test_cases_that_produce(errors=True),
)
def test_end_to_end_test_cases_yielding_errors(
    patched_session,
    service_name,
    op_name,
    op_params,
    builtin_params,
    expected_error,
):
    def builtin_overwriter_handler(builtins, **kwargs):
        # must edit builtins dict in place but need to erase all existing
        # entries
        for key in list(builtins.keys()):
            del builtins[key]
        for key, val in builtin_params.items():
            builtins[key] = val

    region = builtin_params.get('AWS::Region', 'us-east-1')
    client = patched_session.create_client(service_name, region_name=region)
    client.meta.events.register_last(
        'before-endpoint-resolution', builtin_overwriter_handler
    )
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(status=418)
        op_fn = getattr(client, xform_name(op_name))
        with pytest.raises(BotoCoreError):
            try:
                op_fn(**op_params)
            except (ClientError, ResponseParserError):
                pass
        assert len(http_stubber.requests) == 0
