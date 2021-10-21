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
import json
import datetime
import dateutil.tz
from tests import unittest

from botocore.model import ServiceModel
from botocore import serialize
from botocore.compat import six
from botocore.exceptions import ParamValidationError
from botocore.serialize import SERIALIZERS


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
                    }
                },
                'BlobType': {
                    'type': 'blob',
                }
            }
        }

    def serialize_to_request(self, input_params):
        service_model = ServiceModel(self.model)
        request_serializer = serialize.create_serializer(
            service_model.metadata['protocol'])
        return request_serializer.serialize_to_request(
            input_params, service_model.operation_model('TestOperation'))

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
        self.assert_serialized_blob_equals(
            request, blob_bytes=body)

    def test_blob_accepts_str_type(self):
        body = u'ascii text'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assert_serialized_blob_equals(
            request, blob_bytes=body.encode('ascii'))

    def test_blob_handles_unicode_chars(self):
        body = u'\u2713'
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assert_serialized_blob_equals(
            request, blob_bytes=body.encode('utf-8'))


class TestBinaryTypesJSON(BaseModelWithBlob):

    def setUp(self):
        super(TestBinaryTypesJSON, self).setUp()
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
            base64.b64encode(body).decode('ascii'),
            serialized_blob)


class TestBinaryTypesWithRestXML(BaseModelWithBlob):

    def setUp(self):
        super(TestBinaryTypesWithRestXML, self).setUp()
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
        body = six.BytesIO(b'foobar')
        request = self.serialize_to_request(input_params={'Blob': body})
        self.assertEqual(request['body'], body)

    def test_blob_serialization_when_payload_is_unicode(self):
        # When the body is a text type, we should encode the
        # text to bytes.
        body = u'\u2713'
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
                            'locationName': 'x-timestamp'
                        },
                    }
                },
                'TimestampType': {
                    'type': 'timestamp',
                }
            }
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'])
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation'))

    def test_accepts_datetime_object(self):
        request = self.serialize_to_request(
            {'TimestampHeader': datetime.datetime(2014, 1, 1, 12, 12, 12,
                                                  tzinfo=dateutil.tz.tzutc())})
        self.assertEqual(request['headers']['x-timestamp'],
                         'Wed, 01 Jan 2014 12:12:12 GMT')

    def test_accepts_iso_8601_format(self):
        request = self.serialize_to_request(
            {'TimestampHeader': '2014-01-01T12:12:12+00:00'})
        self.assertEqual(request['headers']['x-timestamp'],
                         'Wed, 01 Jan 2014 12:12:12 GMT')

    def test_accepts_iso_8601_format_non_utc(self):
        request = self.serialize_to_request(
            {'TimestampHeader': '2014-01-01T07:12:12-05:00'})
        self.assertEqual(request['headers']['x-timestamp'],
                         'Wed, 01 Jan 2014 12:12:12 GMT')

    def test_accepts_rfc_822_format(self):
        request = self.serialize_to_request(
            {'TimestampHeader': 'Wed, 01 Jan 2014 12:12:12 GMT'})
        self.assertEqual(request['headers']['x-timestamp'],
                         'Wed, 01 Jan 2014 12:12:12 GMT')

    def test_accepts_unix_timestamp_integer(self):
        request = self.serialize_to_request(
            {'TimestampHeader': 1388578332})
        self.assertEqual(request['headers']['x-timestamp'],
                         'Wed, 01 Jan 2014 12:12:12 GMT')


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
                    }
                },
                'TimestampType': {
                    'type': 'timestamp',
                }
            }
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'])
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation'))

    def test_accepts_datetime_object(self):
        request = self.serialize_to_request(
            {'Timestamp': datetime.datetime(2014, 1, 1, 12, 12, 12,
                                            tzinfo=dateutil.tz.tzutc())})
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_naive_datetime_object(self):
        request = self.serialize_to_request(
            {'Timestamp': datetime.datetime(2014, 1, 1, 12, 12, 12)})
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_iso_8601_format(self):
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12Z'})
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_accepts_timestamp_without_tz_info(self):
        # If a timezone/utc is not specified, assume they meant
        # UTC.  This is also the previous behavior from older versions
        # of botocore so we want to make sure we preserve this behavior.
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12'})
        self.assertEqual(request['body']['Timestamp'], '2014-01-01T12:12:12Z')

    def test_microsecond_timestamp_without_tz_info(self):
        request = self.serialize_to_request(
            {'Timestamp': '2014-01-01T12:12:12.123456'})
        self.assertEqual(request['body']['Timestamp'],
                         '2014-01-01T12:12:12.123456Z')


class TestJSONTimestampSerialization(unittest.TestCase):

    def setUp(self):
        self.model = {
            'metadata': {'protocol': 'json', 'apiVersion': '2014-01-01',
                         'jsonVersion': '1.1', 'targetPrefix': 'foo'},
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
                    }
                },
                'TimestampType': {
                    'type': 'timestamp',
                }
            }
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'])
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation'))

    def test_accepts_iso_8601_format(self):
        body = json.loads(self.serialize_to_request(
            {'Timestamp': '1970-01-01T00:00:00'})['body'].decode('utf-8'))
        self.assertEqual(body['Timestamp'], 0)

    def test_accepts_epoch(self):
        body = json.loads(self.serialize_to_request(
            {'Timestamp': '0'})['body'].decode('utf-8'))
        self.assertEqual(body['Timestamp'], 0)
        # Can also be an integer 0.
        body = json.loads(self.serialize_to_request(
            {'Timestamp': 0})['body'].decode('utf-8'))
        self.assertEqual(body['Timestamp'], 0)

    def test_accepts_partial_iso_format(self):
        body = json.loads(self.serialize_to_request(
            {'Timestamp': '1970-01-01'})['body'].decode('utf-8'))
        self.assertEqual(body['Timestamp'], 0)


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
                    }
                },
                'StringTestType': {
                    'type': 'string',
                    'min': 15
                }
            }
        }
        self.service_model = ServiceModel(self.model)

    def assert_serialize_valid_parameter(self, request_serializer):
        valid_string = 'valid_string_with_min_15_chars'
        request = request_serializer.serialize_to_request(
            {'Timestamp': valid_string},
            self.service_model.operation_model('TestOperation'))

        self.assertEqual(request['body']['Timestamp'], valid_string)

    def assert_serialize_invalid_parameter(self, request_serializer):
        invalid_string = 'short string'
        request = request_serializer.serialize_to_request(
            {'Timestamp': invalid_string},
            self.service_model.operation_model('TestOperation'))

        self.assertEqual(request['body']['Timestamp'], invalid_string)

    def test_instantiate_without_validation(self):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'], False)

        try:
            self.assert_serialize_valid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing valid parameter without validation".format(e))

        try:
            self.assert_serialize_invalid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing invalid parameter without validation".format(e))

    def test_instantiate_with_validation(self):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'], True)
        try:
            self.assert_serialize_valid_parameter(request_serializer)
        except ParamValidationError as e:
            self.fail(
                "Shouldn't fail serializing valid parameter with validation".format(e))

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
                            'locationName': 'Content-Length'
                        },
                    }
                },
                'Integer': {
                    'type': 'integer'
                },
            }
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
                        'Foo': {
                            'shape': 'FooShape',
                            'locationName': 'Foo'
                        },
                    },
                    'payload': 'Foo'
                },
                'FooShape': {
                    'type': 'list',
                    'member': {'shape': 'StringShape'}
                },
                'StringShape': {
                    'type': 'string',
                }
            }
        }
        self.service_model = ServiceModel(self.model)

    def serialize_to_request(self, input_params):
        request_serializer = serialize.create_serializer(
            self.service_model.metadata['protocol'])
        return request_serializer.serialize_to_request(
            input_params, self.service_model.operation_model('TestOperation'))

    def test_restxml_serializes_unicode(self):
        params = {
            'Foo': [u'\u65e5\u672c\u8a9e\u3067\u304a\uff4b']
        }
        try:
            self.serialize_to_request(params)
        except UnicodeEncodeError:
            self.fail("RestXML serializer failed to serialize unicode text.")
