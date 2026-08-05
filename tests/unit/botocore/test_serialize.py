"""Additional tests for request serialization.

While there are compliance tests in tests/unit/protocols where
the majority of the request serialization/response parsing is tested,
this test module contains additional tests that go above and beyond the
spec.  This can happen for a number of reasons:

* We are testing python specific behavior that doesn't make sense as a
  compliance test.
* We are testing behavior that is not strictly part of the spec.  These
  may result in a a coverage gap that would otherwise be untested.

"""

import base64
import datetime
import decimal
import io
import json

import dateutil.tz

from botocore import serialize
from botocore.exceptions import ParamValidationError
from botocore.model import ServiceModel
from botocore.serialize import (
    TIMESTAMP_PRECISION_DEFAULT,
    TIMESTAMP_PRECISION_MILLISECOND,
)
from tests import unittest


class BaseModelWithBlob(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'query', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Blob': {'shape': 'BlobType'},
                    },
                },
                'BlobType': {
                    'type': 'blob',
                },
            },
        }

    def serialize_to_request(self, input_params):
        service_model = ServiceModel(self.model)
        request_serializer = serialize.create_serializer(
            service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, service_model.operation_model('TestOperation')
        )

    def assert_serialized_blob_equals(self, request, blob_bytes):
        # This method handles all the details of the base64 decoding.
        encoded = base64.b64encode(blob_bytes)
        # Now the serializers actually have the base64 encoded contents
        # as str types so we need to decode back.  We know that this is
        # ascii so it's safe to use the ascii encoding.
        expected = encoded.decode('ascii')
        self.assertEqual(request['body']['Blob'], expected)


class TestBinaryTypes(BaseModelWithBlob):
    def test_blob_accepts_bytes_type(self):
        body = b'bytes body'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assert_serialized_blob_equals(request, blob_bytes=body)

    def test_blob_accepts_str_type(self):
        body = 'ascii text'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assert_serialized_blob_equals(
            request, blob_bytes=body.encode('ascii')
        )

    def test_blob_handles_unicode_chars(self):
        body = '\u2713'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assert_serialized_blob_equals(
            request, blob_bytes=body.encode('utf-8')
        )


class TestBinaryTypesJSON(BaseModelWithBlob):
    def setUp(self):
        super().setUp()
        self.model['metadata'] = {
            'protocol': 'json',
            'apiVersion': '2014-01-01',
            'jsonVersion': '1.1',
            'targetPrefix': 'foo',
        }

    def test_blob_accepts_bytes_type(self):
        body = b'bytes body'
        request = self.serialize_to_request(input_params={'Blob': body})
        serialized_blob = json.loads(request['body'].decode('utf-8'))['Blob']
        self.assertEqual(
            base64.b64encode(body).decode('ascii'), serialized_blob
        )


class TestBinaryTypesWithRestXML(BaseModelWithBlob):
    def setUp(self):
        super().setUp()
        self.model['metadata'] = {
            'protocol': 'rest-xml',
            'apiVersion': '2014-01-01',
        }
        self.model['operations']['TestOperation']['input'] = {
            'shape': 'InputShape',
            'locationName': 'OperationRequest',
            'payload': 'Blob',
        }

    def test_blob_serialization_with_file_like_object(self):
        body = io.BytesIO(b'foobar')
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assertEqual(request['body'], body)

    def test_blob_serialization_when_payload_is_unicode(self):
        # When the body is a text type, we should encode the
        # text to bytes.
        body = '\u2713'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assertEqual(request['body'], body.encode('utf-8'))

    def test_blob_serialization_when_payload_is_bytes(self):
        body = b'bytes body'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assertEqual(request['body'], body)


class TestTimestampHeadersWithRestXML(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'rest-xml', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'TimestampHeader': {
                            'shape': 'TimestampType',
                            'location': 'header',
                            'locationName': 'x-timestamp',
                        },
                    },
                },
                'TimestampType': {
                    'type': 'timestamp',
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_accepts_datetime_object(self):
        request = self.serialize_to_request(
            {
                'TimestampHeader': datetime.datetime(
                    2014, 1, 1, 12, 12, 12, tzinfo=dateutil.tz.tzutc()
                )
            }
        )
        self.assertEqual(
            request['headers']['x-timestamp'], 'Wed, 01 Jan 2014 12:12:12 GMT'
        )

    def test_accepts_iso_8601_format(self):
        request = self.serialize_to_request(
            {'TimestampHeader': '2014-01-01T12:12:12+00:00'}
        )
        self.assertEqual(
            request['headers']['x-timestamp'], 'Wed, 01 Jan 2014 12:12:12 GMT'
        )

    def test_accepts_iso_8601_format_non_utc(self):
        request = self.serialize_to_request(
            {'TimestampHeader': '2014-01-01T07:12:12-05:00'}
        )
        self.assertEqual(
            request['headers']['x-timestamp'], 'Wed, 01 Jan 2014 12:12:12 GMT'
        )

    def test_accepts_rfc_822_format(self):
        request = self.serialize_to_request(
            {'TimestampHeader': 'Wed, 01 Jan 2014 12:12:12 GMT'}
        )
        self.assertEqual(
            request['headers']['x-timestamp'], 'Wed, 01 Jan 2014 12:12:12 GMT'
        )

    def test_accepts_unix_timestamp_integer(self):
        request = self.serialize_to_request({'TimestampHeader': 1388578332})
        self.assertEqual(
            request['headers']['x-timestamp'], 'Wed, 01 Jan 2014 12:12:12 GMT'
        )


class TestTimestamps(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'query', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Timestamp': {'shape': 'TimestampType'},
                    },
                },
                'TimestampType': {
                    'type': 'timestamp',
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_accepts_datetime_object(self):
        request = self.serialize_to_request(
            {
                'Timestamp': datetime.datetime(
                    2014, 1, 1, 12, 12, 12, tzinfo=dateutil.tz.tzutc()
                )
            }
        )
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_naive_datetime_object(self):
        request = self.serialize_to_request(
            {'Timestamp': datetime.datetime(2014, 1, 1, 12, 12, 12)}
        )
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_iso_8601_format(self):
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12Z'}
        )
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_timestamp_without_tz_info(self):
        # If a timezone/utc is not specified, assume they meant
        # UTC.  This is also the previous behavior from older versions
        # of botocore so we want to make sure we preserve this behavior.
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12'}
        )
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_microsecond_timestamp_without_tz_info(self):
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12.123456'}
        )
        self.assertEqual(
            request['body']['Timestamp'], '2014-01-01T12:12:12.123456Z'
        )


class TestJSONTimestampSerialization(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {
                'protocol': 'json',
                'apiVersion': '2014-01-01',
                'jsonVersion': '1.1',
                'targetPrefix': 'foo',
            },
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Timestamp': {'shape': 'TimestampType'},
                    },
                },
                'TimestampType': {
                    'type': 'timestamp',
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_accepts_iso_8601_format(self):
        body = json.loads(
            self.serialize_to_request({'Timestamp': '1970-01-01T00:00:00'})[
                'body'
            ].decode('utf-8')
        )
        self.assertEqual(body['Timestamp'], 0)

    def test_accepts_epoch(self):
        body = json.loads(
            self.serialize_to_request({'Timestamp': '0'})['body'].decode(
                'utf-8'
            )
        )
        self.assertEqual(body['Timestamp'], 0)
        # Can also be an integer 0.
        body = json.loads(
            self.serialize_to_request({'Timestamp': 0})['body'].decode('utf-8')
        )
        self.assertEqual(body['Timestamp'], 0)

    def test_accepts_partial_iso_format(self):
        body = json.loads(
            self.serialize_to_request({'Timestamp': '1970-01-01'})[
                'body'
            ].decode('utf-8')
        )
        self.assertEqual(body['Timestamp'], 0)


class TestJSONFloatSerialization(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {
                'protocol': 'json',
                'apiVersion': '2014-01-01',
                'jsonVersion': '1.1',
                'targetPrefix': 'foo',
            },
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Double': {'shape': 'DoubleType'},
                        'Float': {'shape': 'FloatType'},
                    },
                },
                'DoubleType': {
                    'type': 'double',
                },
                'FloatType': {
                    'type': 'float',
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_accepts_decimal_with_precision_above_floats(self):
        float_string = '0.12345678901234567890'
        float_as_float = float(
            float_string
        )  # This has less precision; it will be lost on serialization
        float_as_decimal = decimal.Decimal(float_string)
        body = json.loads(
            self.serialize_to_request({'Float': float_as_decimal})[
                'body'
            ].decode('utf-8')
        )
        self.assertEqual(decimal.Decimal(body['Float']), float_as_float)

    def test_accepts_decimal_with_precision_above_doubles(self):
        double_string = '0.12345678901234567890'
        double_as_float = float(
            double_string
        )  # This has less precision; it will be lost on serialization
        double_as_decimal = decimal.Decimal(double_string)
        body = json.loads(
            self.serialize_to_request({'Double': double_as_decimal})[
                'body'
            ].decode('utf-8')
        )
        self.assertEqual(decimal.Decimal(body['Double']), double_as_float)


class TestInstanceCreation(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'query', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Timestamp': {'shape': 'StringTestType'},
                    },
                },
                'StringTestType': {'type': 'string', 'min': 15},
            },
        }
        self.service_model = ServiceModel(self.model)

    def assert_serialize_valid_parameter(self, request_serializer):
        valid_string = 'valid_string_with_min_15_chars'
        request = request_serializer.serialize_to_request(
            {'Timestamp': valid_string},
            self.service_model.operation_model('TestOperation'),
        )

        self.assertEqual(request['body']['Timestamp'], valid_string)

    def assert_serialize_invalid_parameter(self, request_serializer):
        invalid_string = 'short string'
        request = request_serializer.serialize_to_request(
            {'Timestamp': invalid_string},
            self.service_model.operation_model('TestOperation'),
        )

        self.assertEqual(request['body']['Timestamp'], invalid_string)

    def test_instantiate_without_validation(self):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'], False
        )

        try:
            self.assert_serialize_valid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing valid parameter without "
                f"validation: {e}"
            )

        try:
            self.assert_serialize_invalid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing invalid parameter without "
                f"validation: {e}"
            )

    def test_instantiate_with_validation(self):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'], True
        )
        try:
            self.assert_serialize_valid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing invalid parameter without "
                f"validation: {e}"
            )

        with self.assertRaises(ParamValidationError):
            self.assert_serialize_invalid_parameter(request_serializer)


class TestHeaderSerialization(BaseModelWithBlob):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'rest-xml', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'ContentLength': {
                            'shape': 'Integer',
                            'location': 'header',
                            'locationName': 'Content-Length',
                        },
                    },
                },
                'Integer': {'type': 'integer'},
            },
        }
        self.service_model = ServiceModel(self.model)

    def test_always_serialized_as_str(self):
        request = self.serialize_to_request({'ContentLength': 100})
        self.assertEqual(request['headers']['Content-Length'], '100')


class TestRestXMLUnicodeSerialization(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'rest-xml', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Foo': {'shape': 'FooShape', 'locationName': 'Foo'},
                    },
                    'payload': 'Foo',
                },
                'FooShape': {
                    'type': 'list',
                    'member': {'shape': 'StringShape'},
                },
                'StringShape': {
                    'type': 'string',
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol']
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_restxml_serializes_unicode(self):
        params = {'Foo': ['\u65e5\u672c\u8a9e\u3067\u304a\uff4b']}
        try:
            self.serialize_to_request(params)
        except UnicodeEncodeError:
            self.fail("RestXML serializer failed to serialize unicode text.")


class TestTimestampPrecisionParameter(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'query', 'apiVersion': '2014-01-01'},
            'documentation': '',
            'operations': {
                'TestOperation': {
                    'name': 'TestOperation',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/',
                    },
                    'input': {'shape': 'InputShape'},
                }
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'UnixTimestamp': {'shape': 'UnixTimestampType'},
                        'IsoTimestamp': {'shape': 'IsoTimestampType'},
                        'Rfc822Timestamp': {'shape': 'Rfc822TimestampType'},
                    },
                },
                'IsoTimestampType': {
                    'type': 'timestamp',
                    "timestampFormat": "iso8601",
                },
                'UnixTimestampType': {
                    'type': 'timestamp',
                    "timestampFormat": "unixTimestamp",
                },
                'Rfc822TimestampType': {
                    'type': 'timestamp',
                    "timestampFormat": "rfc822",
                },
            },
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(
        self, input_params, timestamp_precision=TIMESTAMP_PRECISION_DEFAULT
    ):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'],
            timestamp_precision=timestamp_precision,
        )
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation')
        )

    def test_second_precision_maintains_existing_behavior(self):
        test_datetime = datetime.datetime(2024, 1, 1, 12, 0, 0, 123456)
        request = self.serialize_to_request(
            {'UnixTimestamp': test_datetime, 'IsoTimestamp': test_datetime}
        )
        # To maintain backwards compatibility, unix should not include milliseconds by default
        self.assertEqual(1704110400, request['body']['UnixTimestamp'])

        # ISO always supported microseconds, so we need to continue supporting this
        self.assertEqual(
            '2024-01-01T12:00:00.123456Z',
            request['body']['IsoTimestamp'],
        )

    def test_millisecond_precision_serialization(self):
        test_datetime = datetime.datetime(2024, 1, 1, 12, 0, 0, 123456)

        # Check that millisecond precision is used when it is opted in to via the input param
        request = self.serialize_to_request(
            {'UnixTimestamp': test_datetime, 'IsoTimestamp': test_datetime},
            TIMESTAMP_PRECISION_MILLISECOND,
        )
        self.assertEqual(1704110400.123, request['body']['UnixTimestamp'])
        self.assertEqual(
            '2024-01-01T12:00:00.123Z',
            request['body']['IsoTimestamp'],
        )

    def test_millisecond_precision_with_zero_microseconds(self):
        test_datetime = datetime.datetime(2024, 1, 1, 12, 0, 0, 0)

        request = self.serialize_to_request(
            {'UnixTimestamp': test_datetime, 'IsoTimestamp': test_datetime},
            TIMESTAMP_PRECISION_MILLISECOND,
        )
        self.assertEqual(1704110400.0, request['body']['UnixTimestamp'])
        self.assertEqual(
            '2024-01-01T12:00:00.000Z',
            request['body']['IsoTimestamp'],
        )

    def test_rfc822_timestamp_always_uses_second_precision(self):
        # RFC822 format doesn't support sub-second precision.
        test_datetime = datetime.datetime(2024, 1, 1, 12, 0, 0, 123456)
        request_second = self.serialize_to_request(
            {'Rfc822Timestamp': test_datetime},
        )
        request_milli = self.serialize_to_request(
            {'Rfc822Timestamp': test_datetime}, TIMESTAMP_PRECISION_MILLISECOND
        )
        self.assertEqual(
            request_second['body']['Rfc822Timestamp'],
            request_milli['body']['Rfc822Timestamp'],
        )
        self.assertIn('2024', request_second['body']['Rfc822Timestamp'])
        self.assertIn('GMT', request_second['body']['Rfc822Timestamp'])

    def test_invalid_timestamp_precision_raises_error(self):
        with self.assertRaises(ValueError) as context:
            serialize.create_serializer(
                self.service_model.metadata['protocol'],
                timestamp_precision='invalid',
            )
        self.assertIn("Invalid timestamp precision", str(context.exception))


class TestRpcV2CBORHostPrefix(unittest.TestCase):
    def setUp(self):
        self.model = {
            'metadata': {
                'protocol': 'smithy-rpc-v2-cbor',
                'apiVersion': '2014-01-01',
                'serviceId': 'MyService',
                'targetPrefix': 'sampleservice',
                'documentation': '',
            },
            'operations': {
                'TestHostPrefixOperation': {
                    'name': 'TestHostPrefixOperation',
                    'input': {'shape': 'InputShape'},
                    'endpoint': {'hostPrefix': '{Foo}'},
                },
                'TestNoHostPrefixOperation': {
                    'name': 'TestNoHostPrefixOperation',
                    'input': {'shape': 'InputShape'},
                },
            },
            'shapes': {
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'Foo': {'shape': 'StringType', 'hostLabel': True},
                    },
                },
                'StringType': {'type': 'string'},
            },
        }
        self.service_model = ServiceModel(self.model)

    def test_host_prefix_added_to_serialized_request(self):
        operation_model = self.service_model.operation_model(
            'TestHostPrefixOperation'
        )
        serializer = serialize.create_serializer('smithy-rpc-v2-cbor')

        params = {'Foo': 'bound'}
        serialized = serializer.serialize_to_request(params, operation_model)

        self.assertEqual(serialized['host_prefix'], 'bound')

    def test_no_host_prefix_when_not_configured(self):
        operation_model = self.service_model.operation_model(
            'TestNoHostPrefixOperation'
        )
        serializer = serialize.create_serializer('smithy-rpc-v2-cbor')

        params = {'Foo': 'bound'}
        serialized = serializer.serialize_to_request(params, operation_model)

        self.assertNotIn('host_prefix', serialized)
