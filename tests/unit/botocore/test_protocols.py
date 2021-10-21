#!/usr/bin/env python
# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Test runner for the JSON models compliance tests

This is a test runner for all the JSON tests defined in
``tests/unit/protocols/``, including both the input/output tests.

You can use the normal ``python -m pytest tests/unit/test_protocols.py``
to run this test.  In addition, there are several env vars you can use during
development.

Tests are broken down by filename, test suite, testcase.  When a test fails
you'll see the protocol (filename), test suite, and test case number of the
failed test.

::

    Description           : Scalar members (0:0)  <--- (suite_id:test_id)
    Protocol:             : ec2                  <--- test file (ec2.json)
    Given                 : ...
    Response              : ...
    Expected serialization: ...
    Actual serialization  : ...
    Assertion message     : ...

To run tests from only a single file, you can set the
BOTOCORE_TEST env var::

    BOTOCORE_TEST=tests/unit/compliance/input/json.json pytest tests/unit/test_protocols.py

To run a single test suite you can set the BOTOCORE_TEST_ID env var:

    BOTOCORE_TEST=tests/unit/compliance/input/json.json BOTOCORE_TEST_ID=5 \
        pytest tests/unit/test_protocols.py

To run a single test case in a suite (useful when debugging a single test), you
can set the BOTOCORE_TEST_ID env var with the ``suite_id:test_id`` syntax.

    BOTOCORE_TEST_ID=5:1 pytest test/unit/test_protocols.py

"""
import os
import copy
from enum import Enum

from base64 import b64decode
from dateutil.tz import tzutc

import pytest

from botocore.awsrequest import HeadersDict
from botocore.compat import json, OrderedDict, urlsplit
from botocore.eventstream import EventStream
from botocore.model import ServiceModel, OperationModel
from botocore.serialize import EC2Serializer, QuerySerializer, \
        JSONSerializer, RestJSONSerializer, RestXMLSerializer
from botocore.parsers import QueryParser, JSONParser, \
        RestJSONParser, RestXMLParser, EC2QueryParser
from botocore.utils import parse_timestamp, percent_encode_sequence
from botocore.awsrequest import prepare_request_dict
from calendar import timegm
from botocore.model import NoShapeFoundError

TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'protocols')
NOT_SPECIFIED = object()
PROTOCOL_SERIALIZERS = {
    'ec2': EC2Serializer,
    'query': QuerySerializer,
    'json': JSONSerializer,
    'rest-json': RestJSONSerializer,
    'rest-xml': RestXMLSerializer,
}
PROTOCOL_PARSERS = {
    'ec2': EC2QueryParser,
    'query': QueryParser,
    'json': JSONParser,
    'rest-json': RestJSONParser,
    'rest-xml': RestXMLParser,
}
PROTOCOL_TEST_BLACKLIST = [
    'Idempotency token auto fill'
]


class TestType(Enum):
    # Tell test runner to ignore this class
    __test__ = False

    INPUT = "input"
    OUTPUT = "output"


def _compliance_tests(test_type=None):
    inp = test_type is None or test_type is TestType.INPUT
    out = test_type is None or test_type is TestType.OUTPUT

    for full_path in _walk_files():
        if full_path.endswith('.json'):
            for model, case, basename in _load_cases(full_path):
                if model.get('description') in PROTOCOL_TEST_BLACKLIST:
                    continue
                if 'params' in case and inp:
                    yield model, case, basename
                elif 'response' in case and out:
                    yield model, case, basename


@pytest.mark.parametrize(
    "json_description, case, basename",
    _compliance_tests(TestType.INPUT)
)
def test_input_compliance(json_description, case, basename):
    service_description = copy.deepcopy(json_description)
    service_description['operations'] = {
        case.get('name', 'OperationName'): case,
    }
    model = ServiceModel(service_description)
    protocol_type = model.metadata['protocol']
    try:
        protocol_serializer = PROTOCOL_SERIALIZERS[protocol_type]
    except KeyError:
        raise RuntimeError("Unknown protocol: %s" % protocol_type)
    serializer = protocol_serializer()
    serializer.MAP_TYPE = OrderedDict
    operation_model = OperationModel(case['given'], model)
    request = serializer.serialize_to_request(case['params'], operation_model)
    _serialize_request_description(request)
    client_endpoint = service_description.get('clientEndpoint')
    try:
        _assert_request_body_is_bytes(request['body'])
        _assert_requests_equal(request, case['serialized'])
        _assert_endpoints_equal(request, case['serialized'], client_endpoint)
    except AssertionError as e:
        _input_failure_message(protocol_type, case, request, e)


def _assert_request_body_is_bytes(body):
    if not isinstance(body, bytes):
        raise AssertionError("Expected body to be serialized as type "
                             "bytes(), instead got: %s" % type(body))


def _assert_endpoints_equal(actual, expected, endpoint):
    if 'host' not in expected:
        return
    prepare_request_dict(actual, endpoint)
    actual_host = urlsplit(actual['url']).netloc
    assert_equal(actual_host, expected['host'], 'Host')


class MockRawResponse(object):
    def __init__(self, data):
        self._data = b64decode(data)

    def stream(self):
        yield self._data

@pytest.mark.parametrize(
    "json_description, case, basename",
    _compliance_tests(TestType.OUTPUT)
)
def test_output_compliance(json_description, case, basename):
    service_description = copy.deepcopy(json_description)
    operation_name = case.get('name', 'OperationName')
    service_description['operations'] = {
        operation_name: case,
    }
    case['response']['context'] = {'operation_name': operation_name}
    try:
        model = ServiceModel(service_description)
        operation_model = OperationModel(case['given'], model)
        parser = PROTOCOL_PARSERS[model.metadata['protocol']](
            timestamp_parser=_compliance_timestamp_parser)
        # We load the json as utf-8, but the response parser is at the
        # botocore boundary, so it expects to work with bytes.
        body_bytes = case['response']['body'].encode('utf-8')
        case['response']['body'] = body_bytes
        # We need the headers to be case insensitive
        headers = HeadersDict(case['response']['headers'])
        case['response']['headers'] = headers
        # If this is an event stream fake the raw streamed response
        if operation_model.has_event_stream_output:
            case['response']['body'] = MockRawResponse(body_bytes)
        if 'error' in case:
            output_shape = operation_model.output_shape
            parsed = parser.parse(case['response'], output_shape)
            try:
                error_shape = model.shape_for(parsed['Error']['Code'])
            except NoShapeFoundError:
                error_shape = None
            if error_shape is not None:
                error_parse = parser.parse(case['response'], error_shape)
                parsed.update(error_parse)
        else:
            output_shape = operation_model.output_shape
            parsed = parser.parse(case['response'], output_shape)
        parsed = _fixup_parsed_result(parsed)
    except Exception as e:
        msg = (
            "\nFailed to run test  : %s\n"
            "Protocol            : %s\n"
            "Description         : %s (%s:%s)\n" % (
                e, model.metadata['protocol'],
                case['description'], case['suite_id'], case['test_id']))
        raise AssertionError(msg)
    try:
        if 'error' in case:
            expected_result = {
                'Error': {
                    'Code': case.get('errorCode', ''),
                    'Message': case.get('errorMessage', ''),
                }
            }
            expected_result.update(case['error'])
        else:
            expected_result = case['result']
        assert_equal(parsed, expected_result, "Body")
    except Exception as e:
        _output_failure_message(model.metadata['protocol'],
                                case, parsed, expected_result, e)


def _fixup_parsed_result(parsed):
    # This function contains all the transformation we need
    # to do from the response _our_ response parsers give
    # vs. the expected responses in the protocol tests.
    # These are implementation specific changes, not any
    # "we're not following the spec"-type changes.

    # 1. RequestMetadata.  We parse this onto the returned dict, but compliance
    # tests don't have any specs for how to deal with request metadata.
    if 'ResponseMetadata' in parsed:
        del parsed['ResponseMetadata']
    # 2. Binary blob types.  In the protocol test, blob types, when base64
    # decoded, always decode to something that can be expressed via utf-8.
    # This is not always the case.  In python3, the blob type is designed to
    # return a bytes (not str) object.  However, for these tests we'll work for
    # any bytes type, and decode it as utf-8 because we know that's safe for
    # the compliance tests.
    parsed = _convert_bytes_to_str(parsed)
    # 3. We need to expand the event stream object into the list of events
    for key, value in parsed.items():
        if isinstance(value, EventStream):
            parsed[key] = _convert_bytes_to_str(list(value))
            break
    # 4. We parse the entire error body into the "Error" field for rest-xml
    # which causes some modeled fields in the response to be placed under the
    # error key. We don't have enough information in the test suite to assert
    # these properly, and they probably shouldn't be there in the first place.
    if 'Error' in parsed:
        error_keys = list(parsed['Error'].keys())
        for key in error_keys:
            if key not in ['Code', 'Message']:
                del parsed['Error'][key]
    return parsed


def _convert_bytes_to_str(parsed):
    if isinstance(parsed, dict):
        new_dict = {}
        for key, value in parsed.items():
            new_dict[key] = _convert_bytes_to_str(value)
        return new_dict
    elif isinstance(parsed, bytes):
        return parsed.decode('utf-8')
    elif isinstance(parsed, list):
        new_list = []
        for item in parsed:
            new_list.append(_convert_bytes_to_str(item))
        return new_list
    else:
        return parsed


def _compliance_timestamp_parser(value):
    datetime = parse_timestamp(value)
    # Convert from our time zone to UTC
    datetime = datetime.astimezone(tzutc())
    # Convert to epoch.
    return int(timegm(datetime.timetuple()))


def _output_failure_message(
    protocol_type, case, actual_parsed,
    expected_result, error
):
    j = _try_json_dump
    error_message = (
        "\nDescription           : %s (%s:%s)\n"
        "Protocol:             : %s\n"
        "Given                 : %s\n"
        "Response              : %s\n"
        "Expected serialization: %s\n"
        "Actual serialization  : %s\n"
        "Assertion message     : %s\n" % (
            case['description'], case['suite_id'],
            case['test_id'], protocol_type,
            j(case['given']), j(case['response']),
            j(expected_result), j(actual_parsed), error))
    raise AssertionError(error_message)


def _input_failure_message(protocol_type, case, actual_request, error):
    j = _try_json_dump
    error_message = (
        "\nDescription           : %s (%s:%s)\n"
        "Protocol:             : %s\n"
        "Given                 : %s\n"
        "Params                : %s\n"
        "Expected serialization: %s\n"
        "Actual serialization  : %s\n"
        "Assertion message     : %s\n" % (
            case['description'], case['suite_id'],
            case['test_id'], protocol_type,
            j(case['given']), j(case['params']),
            j(case['serialized']), j(actual_request), error))
    raise AssertionError(error_message)


def _try_json_dump(obj):
    try:
        return json.dumps(obj)
    except (ValueError, TypeError):
        return str(obj)


def assert_equal(first, second, prefix):
    # A better assert equals.  It allows you to just provide
    # prefix instead of the entire message.
    try:
        assert first == second
    except Exception:
        try:
            better = "%s (actual != expected)\n%s !=\n%s" % (
                prefix,
                json.dumps(first, indent=2),
                json.dumps(second, indent=2))
        except (ValueError, TypeError):
            better = "%s (actual != expected)\n%s !=\n%s" % (
                prefix, first, second)
        raise AssertionError(better)


def _serialize_request_description(request_dict):
    if isinstance(request_dict.get('body'), dict):
        # urlencode the request body.
        encoded = percent_encode_sequence(request_dict['body']).encode('utf-8')
        request_dict['body'] = encoded
    if isinstance(request_dict.get('query_string'), dict):
        encoded = percent_encode_sequence(request_dict.get('query_string'))
        if encoded:
            # 'requests' automatically handle this, but we in the
            # test runner we need to handle the case where the url_path
            # already has query params.
            if '?' not in request_dict['url_path']:
                request_dict['url_path'] += '?%s' % encoded
            else:
                request_dict['url_path'] += '&%s' % encoded


def _assert_requests_equal(actual, expected):
    assert_equal(actual['body'], expected.get('body', '').encode('utf-8'),
                 'Body value')
    actual_headers = HeadersDict(actual['headers'])
    expected_headers = HeadersDict(expected.get('headers', {}))
    excluded_headers = expected.get('forbidHeaders', [])
    _assert_expected_headers_in_request(
        actual_headers, expected_headers, excluded_headers
    )
    assert_equal(actual['url_path'], expected.get('uri', ''), "URI")
    if 'method' in expected:
        assert_equal(actual['method'], expected['method'], "Method")


def _assert_expected_headers_in_request(actual, expected, excluded_headers):
    for header, value in expected.items():
        assert header in actual
        assert actual[header] == value
    for header in excluded_headers:
        assert header not in actual


def _walk_files():
    # Check for a shortcut when running the tests interactively.
    # If a BOTOCORE_TEST env var is defined, that file is used as the
    # only test to run.  Useful when doing feature development.
    single_file = os.environ.get('BOTOCORE_TEST')
    if single_file is not None:
        yield os.path.abspath(single_file)
    else:
        for root, _, filenames in os.walk(TEST_DIR):
            for filename in filenames:
                yield os.path.join(root, filename)


def _load_cases(full_path):
    # During developement, you can set the BOTOCORE_TEST_ID
    # to run a specific test suite or even a specific test case.
    # The format is BOTOCORE_TEST_ID=suite_id:test_id or
    # BOTOCORE_TEST_ID=suite_id
    suite_id, test_id = _get_suite_test_id()
    all_test_data = json.load(open(full_path), object_pairs_hook=OrderedDict)
    basename = os.path.basename(full_path)
    for i, test_data in enumerate(all_test_data):
        if suite_id is not None and i != suite_id:
            continue
        cases = test_data.pop('cases')
        description = test_data['description']
        for j, case in enumerate(cases):
            if test_id is not None and j != test_id:
                continue
            case['description'] = description
            case['suite_id'] = i
            case['test_id'] = j
            yield (test_data, case, basename)


def _get_suite_test_id():
    if 'BOTOCORE_TEST_ID' not in os.environ:
        return None, None
    test_id = None
    suite_id = None
    split = os.environ['BOTOCORE_TEST_ID'].split(':')
    try:
        if len(split) == 2:
            suite_id, test_id = int(split[0]), int(split[1])
        else:
            suite_id = int(split([0]))
    except TypeError:
        # Same exception, just give a better error message.
        raise TypeError("Invalid format for BOTOCORE_TEST_ID, should be "
                        "suite_id[:test_id], and both values should be "
                        "integers.")
    return suite_id, test_id
