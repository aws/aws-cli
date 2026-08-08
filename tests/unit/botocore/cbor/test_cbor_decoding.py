import json
import os
import struct

import pytest

from botocore.parsers import ResponseParserError, RpcV2CBORParser

IGNORE_CASES = [
    # We ignore all the tag tests since none of them are supported tags in AWS.
    # The majority of these aren't even defined tags in CBOR and just test that we
    # can properly parse the number
    'tag - 0/min',
    'tag - 1/min',
    'tag - 2/min',
    'tag - 4/min',
    'tag - 8/min',
    'tag - 0/max',
    'tag - 1/max',
    'tag - 2/max',
    'tag - 4/max',
    'tag - 8/max',
    # We are expected to drop keys with null values, which is the opposite of the
    # assertion in these two map tests
    'map - {_ null}',
    'map - {null}',
]

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def parser():
    return RpcV2CBORParser()


def _get_cbor_decoding_success_tests():
    success_test_file_name = os.path.join(
        TEST_DIR, 'decode-success-tests.json'
    )
    success_test_data = json.load(open(success_test_file_name))
    for case in success_test_data:
        if case['description'] in IGNORE_CASES:
            continue
        yield case['description'], case['input'], case['expect']


def _get_cbor_decoding_error_tests():
    error_test_file_name = os.path.join(TEST_DIR, 'decode-error-tests.json')
    error_test_data = json.load(open(error_test_file_name))
    for case in error_test_data:
        yield case['description'], case['input'], case['error']


@pytest.mark.parametrize(
    "json_description, input, expect", _get_cbor_decoding_success_tests()
)
def test_cbor_decoding_success(json_description, input, expect, parser):
    stream = parser.get_peekable_stream_from_bytes(bytearray.fromhex(input))
    parsed = parser.parse_data_item(stream)
    _assert_expected_value(parsed, expect)


@pytest.mark.parametrize(
    "json_description, input, error", _get_cbor_decoding_error_tests()
)
def test_cbor_decoding_error(json_description, input, error, parser):
    stream = parser.get_peekable_stream_from_bytes(bytearray.fromhex(input))
    with pytest.raises(ResponseParserError):
        parser.parse_data_item(stream)


def assert_null(actual):
    assert actual is None


def assert_bytestring(actual, value):
    assert actual == bytes(value)


def assert_list(actual, value):
    assert isinstance(actual, list)
    for act_val, exp_val in zip(actual, value):
        _assert_expected_value(act_val, exp_val)


def assert_map(actual, value):
    assert isinstance(actual, dict)
    for key, val in value.items():
        assert key in actual
        _assert_expected_value(actual[key], val)


def assert_tag(actual, value):
    assert actual.tag == value['id']
    assert actual.value == value['value']['uint']


def assert_float(actual, expected_key, value):
    struct_format = '<f' if expected_key == 'float32' else '<d'
    packed_value = struct.pack(
        '<I' if expected_key == 'float32' else '<Q', value
    )
    unpacked_value = struct.unpack(struct_format, packed_value)[0]
    assert actual == unpacked_value


def assert_default(actual, value):
    assert actual == value


ASSERTION_MAP = {
    'null': assert_null,
    'undefined': assert_null,
    'bytestring': assert_bytestring,
    'list': assert_list,
    'map': assert_map,
    'tag': assert_tag,
    'float32': assert_float,
    'float64': assert_float,
}


def _assert_expected_value(actual, expected):
    for expected_key, value in expected.items():
        assertion_func = ASSERTION_MAP.get(expected_key, assert_default)
        if expected_key in ['null']:
            assertion_func(actual)
        elif expected_key in ['float32', 'float64']:
            assertion_func(actual, expected_key, value)
        else:
            assertion_func(actual, value)
