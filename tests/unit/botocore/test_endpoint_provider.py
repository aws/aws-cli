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
import logging
import os

import pytest

from botocore.endpoint_provider import (
    EndpointProvider,
    EndpointRule,
    ErrorRule,
    RuleCreator,
    RuleSet,
    RuleSetStandardLibary,
    TreeRule,
)
from botocore.exceptions import (
    EndpointResolutionError,
    UnknownSignatureVersionError,
)
from botocore.loaders import Loader
from botocore.regions import EndpointRulesetResolver

REGION_TEMPLATE = "{Region}"
REGION_REF = {"ref": "Region"}
BUCKET_ARN_REF = {"ref": "bucketArn"}
PARSE_ARN_FUNC = {
    "fn": "aws.parseArn",
    "argv": [{"ref": "Bucket"}],
    "assign": "bucketArn",
}
STRING_EQUALS_FUNC = {
    "fn": "stringEquals",
    "argv": [
        {
            "fn": "getAttr",
            "argv": [BUCKET_ARN_REF, "region"],
            "assign": "bucketRegion",
        },
        "",
    ],
}
DNS_SUFFIX_TEMPLATE = "{PartitionResults#dnsSuffix}"
URL_TEMPLATE = (
    f"https://{REGION_TEMPLATE}.myGreatService.{DNS_SUFFIX_TEMPLATE}"
)
ENDPOINT_DICT = {
    "url": URL_TEMPLATE,
    "properties": {
        "authSchemes": [
            {
                "signingName": "s3",
                "signingScope": REGION_TEMPLATE,
                "name": "s3v4",
            }
        ],
    },
    "headers": {
        "x-amz-region-set": [
            REGION_REF,
            {
                "fn": "getAttr",
                "argv": [BUCKET_ARN_REF, "region"],
            },
            "us-east-2",
        ],
    },
}


@pytest.fixture(scope="module")
def loader():
    return Loader()


@pytest.fixture(scope="module")
def partitions(loader):
    return loader.load_data("partitions")


@pytest.fixture(scope="module")
def rule_lib(partitions):
    return RuleSetStandardLibary(partitions)


@pytest.fixture(scope="module")
def ruleset_dict():
    path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "endpoints",
        "valid-rules",
        "deprecated-param.json",
    )
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def endpoint_provider(ruleset_dict, partitions):
    return EndpointProvider(ruleset_dict, partitions)


@pytest.fixture(scope="module")
def endpoint_rule():
    return EndpointRule(
        endpoint=ENDPOINT_DICT,
        conditions=[
            PARSE_ARN_FUNC,
            {
                "fn": "not",
                "argv": [STRING_EQUALS_FUNC],
            },
            {
                "fn": "aws.partition",
                "argv": [REGION_REF],
                "assign": "PartitionResults",
            },
        ],
    )


def ruleset_testcases():
    filenames = [
        "account-id",
        "array-index",
        "aws-region",
        "default-values",
        "eventbridge",
        "fns",
        "headers",
        "is-virtual-hostable-s3-bucket",
        "local-region-override",
        "parse-arn",
        "parse-url",
        "substring",
        "uri-encode",
        "valid-hostlabel",
    ]
    error_cases = []
    endpoint_cases = []
    base_path = os.path.join(os.path.dirname(__file__), "data", "endpoints")
    for name in filenames:

        with open(os.path.join(base_path, "valid-rules", f"{name}.json")) as f:
            ruleset = json.load(f)
        with open(os.path.join(base_path, "test-cases", f"{name}.json")) as f:
            tests = json.load(f)

        for test in tests["testCases"]:
            input_params = test["params"]
            expected_object = test["expect"]
            if "error" in expected_object:
                error_cases.append(
                    (ruleset, input_params, expected_object["error"])
                )
            elif "endpoint" in expected_object:
                endpoint_cases.append(
                    (ruleset, input_params, expected_object["endpoint"])
                )
            else:
                raise ValueError("Expected `error` or `endpoint` in test case")
    return error_cases, endpoint_cases


ERROR_TEST_CASES, ENDPOINT_TEST_CASES = ruleset_testcases()


@pytest.mark.parametrize(
    "ruleset,input_params,expected_error",
    ERROR_TEST_CASES,
)
def test_endpoint_resolution_raises(
    partitions, ruleset, input_params, expected_error
):
    endpoint_provider = EndpointProvider(ruleset, partitions)
    with pytest.raises(EndpointResolutionError) as exc_info:
        endpoint_provider.resolve_endpoint(**input_params)
    assert str(exc_info.value) == expected_error


@pytest.mark.parametrize(
    "ruleset,input_params,expected_endpoint",
    ENDPOINT_TEST_CASES,
)
def test_endpoint_resolution(
    partitions, ruleset, input_params, expected_endpoint
):
    endpoint_provider = EndpointProvider(ruleset, partitions)
    endpoint = endpoint_provider.resolve_endpoint(**input_params)
    assert endpoint.url == expected_endpoint["url"]
    assert endpoint.properties == expected_endpoint.get("properties", {})
    assert endpoint.headers == expected_endpoint.get("headers", {})


def test_none_returns_default_partition(rule_lib):
    partition_dict = rule_lib.aws_partition(None)
    assert partition_dict['name'] == "aws"


def test_no_match_region_returns_default_partition(rule_lib):
    partition_dict = rule_lib.aws_partition("invalid-region-42")
    assert partition_dict['name'] == "aws"


def test_invalid_arn_returns_none(rule_lib):
    assert rule_lib.aws_parse_arn("arn:aws:this-is-not-an-arn:foo") is None


@pytest.mark.parametrize(
    "arn, expected_resource_id",
    [
        (
            "arn:aws:s3:::myBucket/key",
            {
                "partition": "aws",
                "service": "s3",
                "region": "",
                "accountId": "",
                "resourceId": ["myBucket", "key"],
            },
        ),
        (
            "arn:aws:kinesis:us-east-1:1234567890:stream/mystream:foo",
            {
                "partition": "aws",
                "service": "kinesis",
                "region": "us-east-1",
                "accountId": "1234567890",
                "resourceId": ["stream", "mystream", "foo"],
            },
        ),
        (
            "arn:aws:s3:::myBucket",
            {
                "partition": "aws",
                "service": "s3",
                "region": "",
                "accountId": "",
                "region": "",
                "resourceId": ["myBucket"],
            },
        ),
    ],
)
def test_parse_arn_delimiters(rule_lib, arn, expected_resource_id):
    parsed_arn = rule_lib.aws_parse_arn(arn)
    assert parsed_arn == expected_resource_id


def test_uri_encode_none_returns_none(rule_lib):
    assert rule_lib.uri_encode(None) is None


def test_parse_url_none_return_none(rule_lib):
    assert rule_lib.parse_url(None) is None


def test_string_equals_wrong_type_raises(rule_lib):
    with pytest.raises(EndpointResolutionError) as exc_info:
        rule_lib.string_equals(1, 2)
    assert "Both values must be strings" in str(exc_info.value)


def test_boolean_equals_wrong_type_raises(rule_lib):
    with pytest.raises(EndpointResolutionError) as exc_info:
        rule_lib.boolean_equals(1, 2)
    assert "Both arguments must be bools" in str(exc_info.value)


def test_substring_wrong_type_raises(rule_lib):
    with pytest.raises(EndpointResolutionError) as exc_info:
        rule_lib.substring(["h", "e", "l", "l", "o"], 0, 5, False)
    assert "Input must be a string" in str(exc_info.value)


def test_creator_unknown_type_raises():
    with pytest.raises(EndpointResolutionError) as exc_info:
        RuleCreator.create(type="foo")
    assert "Unknown rule type: foo." in str(exc_info.value)


def test_parameter_wrong_type_raises(endpoint_provider):
    param = endpoint_provider.ruleset.parameters["Region"]
    with pytest.raises(EndpointResolutionError) as exc_info:
        param.validate_input(1)
    assert "Value (Region) is the wrong type" in str(exc_info.value)


def test_deprecated_parameter_logs(endpoint_provider, caplog):
    caplog.set_level(logging.INFO)
    param = endpoint_provider.ruleset.parameters["Region"]
    param.validate_input("foo")
    assert "Region has been deprecated." in caplog.text


def test_no_endpoint_found_error(endpoint_provider):
    with pytest.raises(EndpointResolutionError) as exc_info:
        endpoint_provider.resolve_endpoint(
            **{"Endpoint": "mygreatendpoint.com", "Bucket": "mybucket"}
        )
    assert "No endpoint found for parameters" in str(exc_info.value)


@pytest.mark.parametrize(
    "rule_dict,expected_rule_type",
    [
        (
            {
                "type": "endpoint",
                "conditions": [],
                "endpoint": {
                    "url": (
                        "https://{Region}.myGreatService."
                        "{PartitionResult#dualStackDnsSuffix}"
                    ),
                    "properties": {},
                    "headers": {},
                },
            },
            EndpointRule,
        ),
        (
            {
                "type": "error",
                "conditions": [],
                "error": (
                    "Dualstack is enabled but this partition "
                    "does not support DualStack"
                ),
            },
            ErrorRule,
        ),
        ({"type": "tree", "conditions": [], "rules": []}, TreeRule),
    ],
)
def test_rule_creation(rule_dict, expected_rule_type):
    rule = RuleCreator.create(**rule_dict)
    assert isinstance(rule, expected_rule_type)


def test_assign_existing_scope_var_raises(rule_lib):
    rule = EndpointRule(
        conditions=[
            {
                'fn': 'aws.parseArn',
                'argv': ['{Bucket}'],
                'assign': 'bucketArn',
            },
            {
                'fn': 'aws.parseArn',
                'argv': ['{Bucket}'],
                'assign': 'bucketArn',
            },
        ],
        endpoint={'url': 'foo.bar'},
    )
    with pytest.raises(EndpointResolutionError) as exc_info:
        rule.evaluate_conditions(
            scope_vars={
                'Bucket': 'arn:aws:s3:us-east-1:123456789012:mybucket'
            },
            rule_lib=rule_lib,
        )
    assert str(exc_info.value) == (
        "Assignment bucketArn already exists in "
        "scoped variables and cannot be overwritten"
    )


def test_ruleset_unknown_parameter_type_raises(partitions):
    with pytest.raises(EndpointResolutionError) as exc_info:
        RuleSet(
            version='1.0',
            parameters={
                'Bucket': {"type": "list"},
            },
            rules=[],
            partitions=partitions,
        )
    assert "Unknown parameter type: list." in str(exc_info.value)


@pytest.fixture()
def empty_resolver():
    return EndpointRulesetResolver(
        endpoint_ruleset_data={
            'version': '1.0',
            'parameters': {},
            'rules': [],
        },
        partition_data={},
        service_model=None,
        builtins={},
        client_context=None,
        event_emitter=None,
        use_ssl=True,
        requested_auth_scheme=None,
    )


def test_auth_schemes_conversion_sigv4(empty_resolver):
    auth_schemes = [
        {
            'name': 'sigv4',
            'signingName': 'dynamodb',
            'signingRegion': 'my-region-1',
            'disableDoubleEncoding': True,
            'otherParameter': 'otherValue',
        }
    ]
    at, sc = empty_resolver.auth_schemes_to_signing_ctx(auth_schemes)
    assert at == 'v4'
    assert sc == {
        'region': 'my-region-1',
        'signing_name': 'dynamodb',
        'disableDoubleEncoding': True,
    }


def test_auth_schemes_conversion_sigv4a_with_crt(empty_resolver):
    auth_schemes = [
        {'name': 'sigv4a', 'signingName': 's3', 'signingRegionSet': ['*']}
    ]
    at, sc = empty_resolver.auth_schemes_to_signing_ctx(auth_schemes)
    assert at == 'v4a'
    assert sc == {'region': '*', 'signing_name': 's3'}


def test_auth_schemes_conversion_no_known_auth_types(empty_resolver):
    auth_schemes = [
        {'name': 'foo', 'signingName': 's3', 'signingRegion': 'ap-south-2'},
        {'name': 'bar', 'otherParamKey': 'otherParamVal'},
    ]
    with pytest.raises(UnknownSignatureVersionError):
        empty_resolver.auth_schemes_to_signing_ctx(auth_schemes)


def test_auth_schemes_conversion_first_authtype_unknown(
    monkeypatch, empty_resolver
):
    monkeypatch.setattr('botocore.regions.AUTH_TYPE_MAPS', {'bar': None})
    auth_schemes = [
        {'name': 'foo', 'signingName': 's3', 'signingRegion': 'ap-south-1'},
        {'name': 'bar', 'signingName': 's3', 'signingRegion': 'ap-south-2'},
    ]
    at, sc = empty_resolver.auth_schemes_to_signing_ctx(auth_schemes)
    assert at == 'bar'
    assert sc == {'region': 'ap-south-2', 'signing_name': 's3'}


@pytest.mark.parametrize(
    "value, path, expected_value",
    [
        ({"foo": ['bar']}, 'baz[0]', None),  # Missing index
        ({"foo": ['bar']}, 'foo[1]', None),  # Out of range index
        ({"foo": ['bar']}, 'foo[0]', "bar"),  # Named index
        (("foo",), '[0]', "foo"),  # Bare index
        ({"foo": {}}, 'foo.bar[0]', None),  # Missing index from split path
        (
            {"foo": {'bar': []}},
            'foo.bar[0]',
            None,
        ),  # Out of range from split path
        (
            {"foo": {"bar": "baz"}},
            'foo.bar',
            "baz",
        ),  # Split path with named index
        (
            {"foo": {"bar": ["baz"]}},
            'foo.bar[0]',
            "baz",
        ),  # Split path with numeric index
    ],
)
def test_get_attr(rule_lib, value, path, expected_value):
    result = rule_lib.get_attr(value, path)
    assert result == expected_value
