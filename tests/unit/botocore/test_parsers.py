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
from tests import unittest, RawResponse
import datetime
import itertools

from dateutil.tz import tzutc
import pytest

from botocore import parsers
from botocore import model
from botocore.compat import json, MutableMapping


# HTTP responses will typically return a custom HTTP
# dict.  We want to ensure we're able to work with any
# kind of mutable mapping implementation.
class CustomHeaderDict(MutableMapping):
    def __init__(self, original_dict):
        self._d = original_dict

    def __getitem__(self, item):
        return self._d[item]

    def __setitem__(self, item, value):
        self._d[item] = value

    def __delitem__(self, item):
        del self._d[item]

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)


# These tests contain botocore specific tests that either
# don't make sense in the protocol tests or haven't been added
# yet.
class TestResponseMetadataParsed(unittest.TestCase):
    def test_response_metadata_parsed_for_query_service(self):
        parser = parsers.QueryParser()
        response = (
            '<OperationNameResponse>'
            '  <OperationNameResult><Str>myname</Str></OperationNameResult>'
            '  <ResponseMetadata>'
            '    <RequestId>request-id</RequestId>'
            '  </ResponseMetadata>'
            '</OperationNameResponse>').encode('utf-8')
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'resultWrapper': 'OperationNameResult',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    },
                    'Num': {
                        'shape': 'IntegerType',
                    }
                }
            },
            model.ShapeResolver({
                'StringType': {
                    'type': 'string',
                },
                'IntegerType': {
                    'type': 'integer',
                }
            })
        )
        parsed = parser.parse(
            {'body': response,
             'headers': {},
             'status_code': 200}, output_shape)
        self.assertEqual(
            parsed, {'Str': 'myname',
                     'ResponseMetadata': {'RequestId': 'request-id',
                                          'HTTPStatusCode': 200,
                                          'HTTPHeaders': {}}})

    def test_metadata_always_exists_for_query(self):
        # ResponseMetadata is used for more than just the request id. It
        # should always get populated, even if the request doesn't seem to
        # have an id.
        parser = parsers.QueryParser()
        response = (
            '<OperationNameResponse>'
            '  <OperationNameResult><Str>myname</Str></OperationNameResult>'
            '</OperationNameResponse>').encode('utf-8')
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'resultWrapper': 'OperationNameResult',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    },
                    'Num': {
                        'shape': 'IntegerType',
                    }
                }
            },
            model.ShapeResolver({
                'StringType': {
                    'type': 'string',
                },
                'IntegerType': {
                    'type': 'integer',
                }
            })
        )
        parsed = parser.parse(
            {'body': response, 'headers': {}, 'status_code': 200},
            output_shape)
        expected = {
            'Str': 'myname',
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': {}
            }
        }
        self.assertEqual(parsed, expected)

    def test_response_metadata_parsed_for_ec2(self):
        parser = parsers.EC2QueryParser()
        response = (
            '<OperationNameResponse>'
            '  <Str>myname</Str>'
            '  <requestId>request-id</requestId>'
            '</OperationNameResponse>').encode('utf-8')
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse({'headers': {},
                               'body': response,
                               'status_code': 200}, output_shape)
        # Note that the response metadata is normalized to match the query
        # protocol, even though this is not how it appears in the output.
        self.assertEqual(
            parsed, {'Str': 'myname',
                     'ResponseMetadata': {'RequestId': 'request-id',
                                          'HTTPStatusCode': 200,
                                          'HTTPHeaders': {}}})

    def test_metadata_always_exists_for_ec2(self):
        # ResponseMetadata is used for more than just the request id. It
        # should always get populated, even if the request doesn't seem to
        # have an id.
        parser = parsers.EC2QueryParser()
        response = (
            '<OperationNameResponse>'
            '  <Str>myname</Str>'
            '</OperationNameResponse>').encode('utf-8')
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse(
            {'headers': {}, 'body': response, 'status_code': 200},
            output_shape)
        expected = {
            'Str': 'myname',
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': {}
            }
        }
        self.assertEqual(
            parsed, expected)

    def test_response_metadata_on_json_request(self):
        parser = parsers.JSONParser()
        response = b'{"Str": "mystring"}'
        headers = {'x-amzn-requestid': 'request-id'}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse({'body': response, 'headers': headers,
                               'status_code': 200}, output_shape)
        # Note that the response metadata is normalized to match the query
        # protocol, even though this is not how it appears in the output.
        self.assertEqual(
            parsed, {'Str': 'mystring',
                     'ResponseMetadata': {'RequestId': 'request-id',
                                          'HTTPStatusCode': 200,
                                          'HTTPHeaders': headers}})

    def test_response_no_initial_event_stream(self):
        parser = parsers.JSONParser()
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Payload': {'shape': 'Payload'}
                }
            },
            model.ShapeResolver({
                'Payload': {
                    'type': 'structure',
                    'members': [],
                    'eventstream': True
                }
            })
        )
        with self.assertRaises(parsers.ResponseParserError):
            response_dict = {
                'status_code': 200,
                'headers': {},
                'body': RawResponse(b''),
                'context': {
                    'operation_name': 'TestOperation'
                }
            }
            parser.parse(response_dict, output_shape)

    def test_metadata_always_exists_for_json(self):
        # ResponseMetadata is used for more than just the request id. It
        # should always get populated, even if the request doesn't seem to
        # have an id.
        parser = parsers.JSONParser()
        response = b'{"Str": "mystring"}'
        headers = {}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse(
            {'body': response, 'headers': headers, 'status_code': 200},
            output_shape)
        expected = {
            'Str': 'mystring',
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': headers
            }
        }
        self.assertEqual(parsed, expected)

    def test_response_metadata_on_rest_json_response(self):
        parser = parsers.RestJSONParser()
        response = b'{"Str": "mystring"}'
        headers = {'x-amzn-requestid': 'request-id'}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse({'body': response, 'headers': headers,
                               'status_code': 200}, output_shape)
        # Note that the response metadata is normalized to match the query
        # protocol, even though this is not how it appears in the output.
        self.assertEqual(
            parsed, {'Str': 'mystring',
                     'ResponseMetadata': {'RequestId': 'request-id',
                                          'HTTPStatusCode': 200,
                                          'HTTPHeaders': headers}})

    def test_metadata_always_exists_on_rest_json_response(self):
        # ResponseMetadata is used for more than just the request id. It
        # should always get populated, even if the request doesn't seem to
        # have an id.
        parser = parsers.RestJSONParser()
        response = b'{"Str": "mystring"}'
        headers = {}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        parsed = parser.parse(
            {'body': response, 'headers': headers, 'status_code': 200},
            output_shape)
        expected = {
            'Str': 'mystring',
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': headers
            }
        }
        self.assertEqual(parsed, expected)

    def test_response_metadata_from_s3_response(self):
        # Even though s3 is a rest-xml service, it's response metadata
        # is slightly different.  It has two request ids, both come from
        # the response headers, are both are named differently from other
        # rest-xml responses.
        headers = {
            'x-amz-id-2': 'second-id',
            'x-amz-request-id': 'request-id'
        }
        parser = parsers.RestXMLParser()
        parsed = parser.parse(
            {'body': '', 'headers': headers, 'status_code': 200}, None)
        self.assertEqual(
            parsed,
            {'ResponseMetadata': {'RequestId': 'request-id',
                                  'HostId': 'second-id',
                                  'HTTPStatusCode': 200,
                                  'HTTPHeaders': headers}})

    def test_metadata_always_exists_on_rest_xml_response(self):
        # ResponseMetadata is used for more than just the request id. It
        # should always get populated, even if the request doesn't seem to
        # have an id.
        headers = {}
        parser = parsers.RestXMLParser()
        parsed = parser.parse(
            {'body': '', 'headers': headers, 'status_code': 200}, None)
        expected = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': headers
            }
        }
        self.assertEqual(parsed, expected)


class TestTaggedUnions(unittest.TestCase):
    def assert_tagged_union_response_with_unknown_member(self,
                                                         parser,
                                                         response,
                                                         output_shape,
                                                         expected_parsed_response,
                                                         expected_log):
        with self.assertLogs() as captured_log:
            parsed = parser.parse(response, output_shape)
            self.assertEqual(parsed, expected_parsed_response)
            self.assertEqual(len(captured_log.records), 1)
            self.assertIn(('Received a tagged union response with member '
                           'unknown to client'),
                          captured_log.records[0].getMessage())

    def test_base_json_parser_handles_unknown_member(self):
        parser = parsers.JSONParser()
        response = b'{"Foo": "mystring"}'
        headers = {'x-amzn-requestid': 'request-id'}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'union':True,
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        response = {'body': response, 'headers': headers, 'status_code': 200}
        # Parsed response omits data from service since it is not
        # modeled in the client
        expected_parsed_response = {
            'SDK_UNKNOWN_MEMBER': {
                'name': 'Foo'
            },
            'ResponseMetadata':
            {'RequestId': 'request-id',
             'HTTPStatusCode': 200,
             'HTTPHeaders': {
                 'x-amzn-requestid': 'request-id'}
             }
        }
        expected_log = "Received a response with an unknown member Foo set"
        self.assert_tagged_union_response_with_unknown_member(
            parser, response, output_shape, expected_parsed_response,
            expected_log
        )

    def test_base_xml_parser_handles_unknown_member(self):
        parser = parsers.QueryParser()
        response = (
            '<OperationNameResponse>'
            '  <OperationNameResult><Foo>mystring</Foo></OperationNameResult>'
            '  <ResponseMetadata>'
            '    <RequestId>request-id</RequestId>'
            '  </ResponseMetadata>'
            '</OperationNameResponse>').encode('utf-8')
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'union':True,
                'resultWrapper': 'OperationNameResult',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    },
                }
            },
            model.ShapeResolver({
                'StringType': {
                    'type': 'string',
                },
            })
        )
        response = {'body': response, 'headers': {}, 'status_code': 200}
        # Parsed response omits data from service since it is not
        # modeled in the client
        expected_parsed_response = {
            'SDK_UNKNOWN_MEMBER': {
                'name': 'Foo'
            },
            'ResponseMetadata':{
                'RequestId': 'request-id',
                'HTTPStatusCode': 200,
                'HTTPHeaders': {}
            }
        }
        expected_log = "Received a response with an unknown member Foo set"
        self.assert_tagged_union_response_with_unknown_member(
            parser, response, output_shape, expected_parsed_response,
            expected_log
        )

    def test_parser_errors_out_when_multiple_members_set(self):
        parser = parsers.JSONParser()
        response = b'{"Foo": "mystring", "Bar": "mystring2"}'
        headers = {'x-amzn-requestid': 'request-id'}
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'union':True,
                'members': {
                    'Foo': {
                        'shape': 'StringType',
                    },
                    'Bar': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )

        response = {'body': response, 'headers': headers, 'status_code': 200}
        with self.assertRaises(parsers.ResponseParserError):
            parser.parse(response, output_shape)


class TestHeaderResponseInclusion(unittest.TestCase):
    def create_parser(self):
        return parsers.JSONParser()

    def create_arbitary_output_shape(self):
        output_shape = model.StructureShape(
            'OutputShape',
            {
                'type': 'structure',
                'members': {
                    'Str': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )
        return output_shape

    def test_can_add_errors_into_response(self):
        parser = self.create_parser()
        headers = {
            'x-amzn-requestid': 'request-id',
            'Header1': 'foo',
            'Header2': 'bar',
        }
        output_shape = self.create_arbitary_output_shape()
        parsed = parser.parse(
            {'body': b'{}', 'headers': headers,
             'status_code': 200}, output_shape)
        # The mapped header's keys should all be lower cased
        parsed_headers = {
            'x-amzn-requestid': 'request-id',
            'header1': 'foo',
            'header2': 'bar',
        }
        # Response headers should be mapped as HTTPHeaders.
        self.assertEqual(
            parsed['ResponseMetadata']['HTTPHeaders'], parsed_headers)

    def test_can_always_json_serialize_headers(self):
        parser = self.create_parser()
        original_headers = {
            'x-amzn-requestid': 'request-id',
            'Header1': 'foo',
        }
        headers = CustomHeaderDict(original_headers)
        output_shape = self.create_arbitary_output_shape()
        parsed = parser.parse(
            {'body': b'{}', 'headers': headers,
             'status_code': 200}, output_shape)
        metadata = parsed['ResponseMetadata']
        # We've had the contract that you can json serialize a
        # response.  So we want to ensure that despite using a CustomHeaderDict
        # we can always JSON dumps the response metadata.
        self.assertEqual(
            json.loads(json.dumps(metadata))['HTTPHeaders']['header1'], 'foo')


class TestResponseParsingDatetimes(unittest.TestCase):
    def test_can_parse_float_timestamps(self):
        # The type "timestamp" can come back as both an integer or as a float.
        # We need to make sure we handle the case where the timestamp comes
        # back as a float.  It might make sense to move this to protocol tests.
        output_shape = model.Shape(shape_name='datetime',
                                   shape_model={'type': 'timestamp'})
        parser = parsers.JSONParser()
        timestamp_as_float = b'1407538750.49'
        expected_parsed = datetime.datetime(
            2014, 8, 8, 22, 59, 10, 490000, tzinfo=tzutc())
        parsed = parser.parse(
            {'body': timestamp_as_float,
             'headers': [],
             'status_code': 200}, output_shape)
        self.assertEqual(parsed, expected_parsed)


class TestResponseParserFactory(unittest.TestCase):
    def setUp(self):
        self.factory = parsers.ResponseParserFactory()

    def test_rest_parser(self):
        parser = self.factory.create_parser('rest-xml')
        self.assertTrue(isinstance(parser, parsers.BaseRestParser))
        self.assertTrue(isinstance(parser, parsers.BaseXMLResponseParser))

    def test_json_parser(self):
        parser = self.factory.create_parser('json')
        self.assertTrue(isinstance(parser, parsers.BaseJSONParser))


class TestCanDecorateResponseParsing(unittest.TestCase):
    def setUp(self):
        self.factory = parsers.ResponseParserFactory()

    def create_request_dict(self, with_body):
        return {
            'body': with_body, 'headers': [], 'status_code': 200
        }

    def test_normal_blob_parsing(self):
        output_shape = model.Shape(shape_name='BlobType',
                                   shape_model={'type': 'blob'})
        parser = self.factory.create_parser('json')

        hello_world_b64 = b'"aGVsbG8gd29ybGQ="'
        expected_parsed = b'hello world'
        parsed = parser.parse(
            self.create_request_dict(with_body=hello_world_b64),
            output_shape)
        self.assertEqual(parsed, expected_parsed)

    def test_can_decorate_scalar_parsing(self):
        output_shape = model.Shape(shape_name='BlobType',
                                   shape_model={'type': 'blob'})
        # Here we're overriding the blob parser so that
        # we can change it to a noop parser.
        self.factory.set_parser_defaults(
            blob_parser=lambda x: x)
        parser = self.factory.create_parser('json')

        hello_world_b64 = b'"aGVsbG8gd29ybGQ="'
        expected_parsed = "aGVsbG8gd29ybGQ="
        parsed = parser.parse(
            self.create_request_dict(with_body=hello_world_b64),
            output_shape)
        self.assertEqual(parsed, expected_parsed)

    def test_can_decorate_timestamp_parser(self):
        output_shape = model.Shape(shape_name='datetime',
                                   shape_model={'type': 'timestamp'})
        # Here we're overriding the timestamp parser so that
        # we can change it to just convert a string to an integer
        # instead of converting to a datetime.
        self.factory.set_parser_defaults(
            timestamp_parser=lambda x: int(x))
        parser = self.factory.create_parser('json')

        timestamp_as_int = b'1407538750'
        expected_parsed = int(timestamp_as_int)
        parsed = parser.parse(
            self.create_request_dict(with_body=timestamp_as_int),
            output_shape)
        self.assertEqual(parsed, expected_parsed)


class TestHandlesNoOutputShape(unittest.TestCase):
    """Verify that each protocol handles no output shape properly."""

    def test_empty_rest_json_response(self):
        headers = {'x-amzn-requestid': 'request-id'}
        parser = parsers.RestJSONParser()
        output_shape = None
        parsed = parser.parse(
            {'body': b'', 'headers': headers, 'status_code': 200},
            output_shape)
        self.assertEqual(
            parsed,
            {'ResponseMetadata': {'RequestId': 'request-id',
                                  'HTTPStatusCode': 200,
                                  'HTTPHeaders': headers}})

    def test_empty_rest_xml_response(self):
        # This is the format used by cloudfront, route53.
        headers = {'x-amzn-requestid': 'request-id'}
        parser = parsers.RestXMLParser()
        output_shape = None
        parsed = parser.parse(
            {'body': b'', 'headers': headers, 'status_code': 200},
            output_shape)
        self.assertEqual(
            parsed,
            {'ResponseMetadata': {'RequestId': 'request-id',
                                  'HTTPStatusCode': 200,
                                  'HTTPHeaders': headers}})

    def test_empty_query_response(self):
        body = (
            b'<DeleteTagsResponse xmlns="http://autoscaling.amazonaws.com/">'
            b'  <ResponseMetadata>'
            b'    <RequestId>request-id</RequestId>'
            b'  </ResponseMetadata>'
            b'</DeleteTagsResponse>'
        )
        parser = parsers.QueryParser()
        output_shape = None
        parsed = parser.parse(
            {'body': body, 'headers': {}, 'status_code': 200},
            output_shape)
        self.assertEqual(
            parsed,
            {'ResponseMetadata': {'RequestId': 'request-id',
                                  'HTTPStatusCode': 200,
                                  'HTTPHeaders': {}}})

    def test_empty_json_response(self):
        headers = {'x-amzn-requestid': 'request-id'}
        # Output shape of None represents no output shape in the model.
        output_shape = None
        parser = parsers.JSONParser()
        parsed = parser.parse(
            {'body': b'', 'headers': headers, 'status_code': 200},
            output_shape)
        self.assertEqual(
            parsed,
            {'ResponseMetadata': {'RequestId': 'request-id',
                                  'HTTPStatusCode': 200,
                                  'HTTPHeaders': headers}})


class TestHandlesInvalidXMLResponses(unittest.TestCase):
    def test_invalid_xml_shown_in_error_message(self):
        # Missing the closing XML tags.
        invalid_xml = (
            b'<DeleteTagsResponse xmlns="http://autoscaling.amazonaws.com/">'
            b'  <ResponseMetadata>'
        )
        parser = parsers.QueryParser()
        output_shape = None
        # The XML body should be in the error message.
        with self.assertRaisesRegex(parsers.ResponseParserError,
                                    '<DeleteTagsResponse'):
            parser.parse(
                {'body': invalid_xml, 'headers': {}, 'status_code': 200},
                output_shape)


class TestRESTXMLResponses(unittest.TestCase):
    def test_multiple_structures_list_returns_struture(self):
        # This is to handle the scenario when something is modeled
        # as a structure and instead a list of structures is returned.
        # For this case, a single element from the list should be parsed
        # For botocore, this will be the first element.
        # Currently, this logic may happen in s3's GetBucketLifecycle
        # operation.
        headers = {}
        parser = parsers.RestXMLParser()
        body = (
            '<?xml version="1.0" ?>'
            '<OperationName xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            '	<Foo><Bar>first_value</Bar></Foo>'
            '	<Foo><Bar>middle_value</Bar></Foo>'
            '	<Foo><Bar>last_value</Bar></Foo>'
            '</OperationName>'
        )
        builder = model.DenormalizedStructureBuilder()
        output_shape = builder.with_members({
            'Foo': {
                'type': 'structure',
                'members': {
                    'Bar': {
                        'type': 'string',
                    }
                }
            }
        }).build_model()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 200},
            output_shape)
        # Ensure the first element is used out of the list.
        self.assertEqual(parsed['Foo'], {'Bar': 'first_value'})


class TestEventStreamParsers(unittest.TestCase):

    def setUp(self):
        self.parser = parsers.EventStreamXMLParser()
        self.output_shape = model.StructureShape(
            'EventStream',
            {
                'eventstream': True,
                'type': 'structure',
                'members': {
                    'EventA': {'shape': 'EventAStructure'},
                    'EventB': {'shape': 'EventBStructure'},
                    'EventC': {'shape': 'EventCStructure'},
                    'EventD': {'shape': 'EventDStructure'},
                    'EventException': {'shape': 'ExceptionShape'},
                }
            },
            model.ShapeResolver({
                'EventAStructure': {
                    'event': True,
                    'type': 'structure',
                    'members': {
                        'Stats': {
                            'shape': 'StatsStructure',
                            'eventpayload': True
                        },
                        'Header': {
                            'shape': 'IntShape',
                            'eventheader': True
                        }
                    }
                },
                'EventBStructure': {
                    'event': True,
                    'type': 'structure',
                    'members': {
                        'Body': {
                            'shape': 'BlobShape',
                            'eventpayload': True
                        }
                    }
                },
                'EventCStructure': {
                    'event': True,
                    'type': 'structure',
                    'members': {
                        'Body': {
                            'shape': 'StringShape',
                            'eventpayload': True
                        }
                    }
                },
                'EventDStructure': {
                    'event': True,
                    'type': 'structure',
                    'members': {
                        'StringField': {'shape': 'StringShape'},
                        'IntField': {'shape': 'IntShape'},
                        'Header': {
                            'shape': 'IntShape',
                            'eventheader': True
                        }
                    }
                },
                'StatsStructure': {
                    'type': 'structure',
                    'members': {
                        'StringField': {'shape': 'StringShape'},
                        'IntField': {'shape': 'IntShape'}
                    }
                },
                'BlobShape': {'type': 'blob'},
                'StringShape': {'type': 'string'},
                'IntShape': {'type': 'integer'},
                'ExceptionShape': {
                    'exception': True,
                    'type': 'structure',
                    'members': {
                        'message': {'shape': 'StringShape'}
                    }
                },
            })
        )

    def parse_event(self, headers=None, body=None, status_code=200):
        response_dict = {
            'body': body,
            'headers': headers,
            'status_code': status_code
        }
        return self.parser.parse(response_dict, self.output_shape)

    def test_parses_event_xml(self):
        headers = {
            'Header': 123,
            ':event-type': 'EventA'
        }
        body = (
            b'<Stats xmlns="">'
            b'  <StringField>abcde</StringField>'
            b'  <IntField>1234</IntField>'
            b'</Stats>'
        )
        parsed = self.parse_event(headers, body)
        expected = {
            'EventA': {
                'Header': 123,
                'Stats': {
                    'StringField': 'abcde',
                    'IntField': 1234
                }
            }
        }
        self.assertEqual(parsed, expected)

    def test_parses_event_bad_xml(self):
        headers = {
            'Header': 123,
            ':event-type': 'EventA'
        }
        parsed = self.parse_event(headers, b'')
        expected = {
            'EventA': {
                'Header': 123,
                'Stats': {}
            }
        }
        self.assertEqual(parsed, expected)

    def test_parses_event_blob(self):
        headers = {':event-type': 'EventB'}
        parsed = self.parse_event(headers, b'blob')
        expected = {'EventB': {'Body': b'blob'}}
        self.assertEqual(parsed, expected)

    def test_parses_event_string(self):
        headers = {':event-type': 'EventC'}
        parsed = self.parse_event(headers, b'blob')
        expected = {'EventC': {'Body': u'blob'}}
        self.assertEqual(parsed, expected)

    def test_parses_payload_implicit(self):
        headers = {
            'Header': 123,
            ':event-type': 'EventD'
        }
        body = (
            b'<EventD xmlns="">'
            b'  <StringField>abcde</StringField>'
            b'  <IntField>1234</IntField>'
            b'</EventD>'
        )
        parsed = self.parse_event(headers, body)
        expected = {
            'EventD': {
                'Header': 123,
                'StringField': 'abcde',
                'IntField': 1234
            }
        }
        self.assertEqual(parsed, expected)

    def test_parses_error_event(self):
        error_code = 'client/SomeError'
        error_message = 'You did something wrong'
        headers = {
            ':message-type': 'error',
            ':error-code': error_code,
            ':error-message': error_message
        }
        body = b''
        parsed = self.parse_event(headers, body, status_code=400)
        expected = {
            'Error': {
                'Code': error_code,
                'Message': error_message
            }
        }
        self.assertEqual(parsed, expected)

    def test_parses_exception_event(self):
        self.parser = parsers.EventStreamJSONParser()
        error_code = 'EventException'
        headers = {
            ':message-type': 'exception',
            ':exception-type': error_code,
        }
        body = b'{"message": "You did something wrong"}'
        parsed = self.parse_event(headers, body, status_code=400)
        expected = {
            'Error': {
                'Code': error_code,
                'Message': 'You did something wrong'
            }
        }
        self.assertEqual(parsed, expected)

    def test_parses_event_json(self):
        self.parser = parsers.EventStreamJSONParser()
        headers = {':event-type': 'EventD'}
        body = (
            b'{'
            b'  "StringField": "abcde",'
            b'  "IntField": 1234'
            b'}'
        )
        parsed = self.parse_event(headers, body)
        expected = {
            'EventD': {
                'StringField': 'abcde',
                'IntField': 1234
            }
        }
        self.assertEqual(parsed, expected)


class TestParseErrorResponses(unittest.TestCase):
    # This class consolidates all the error parsing tests
    # across all the protocols.  We may potentially pull
    # this into the shared protocol tests in the future,
    # so consolidating them into a single class will make
    # this easier.
    def setUp(self):
        self.error_shape = model.StructureShape(
            'ErrorShape',
            {
                'type': 'structure',
                'exception': True,
                'members': {
                    'ModeledField': {
                        'shape': 'StringType',
                    }
                }
            },
            model.ShapeResolver({'StringType': {'type': 'string'}})
        )

    def test_response_metadata_errors_for_json_protocol(self):
        parser = parsers.JSONParser()
        response = {
            "body": b"""
                {"__type":"amazon.foo.validate#ValidationException",
                 "message":"this is a message"}
                """,
            "status_code": 400,
            "headers": {
                "x-amzn-requestid": "request-id"
            }
        }
        parsed = parser.parse(response, None)
        # Even (especially) on an error condition, the
        # ResponseMetadata should be populated.
        self.assertIn('ResponseMetadata', parsed)
        self.assertEqual(parsed['ResponseMetadata']['RequestId'], 'request-id')

        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error']['Message'], 'this is a message')
        self.assertEqual(parsed['Error']['Code'], 'ValidationException')

    def test_response_metadata_errors_alternate_form_json_protocol(self):
        # Sometimes there is no '#' in the __type.  We need to be
        # able to parse this error message as well.
        parser = parsers.JSONParser()
        response = {
            "body": b"""
                {"__type":"ValidationException",
                 "message":"this is a message"}
                """,
            "status_code": 400,
            "headers": {
                "x-amzn-requestid": "request-id"
            }
        }
        parsed = parser.parse(response, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error']['Message'], 'this is a message')
        self.assertEqual(parsed['Error']['Code'], 'ValidationException')

    def test_parse_error_response_for_query_protocol(self):
        body = (
            '<ErrorResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">'
            '  <Error>'
            '    <Type>Sender</Type>'
            '    <Code>InvalidInput</Code>'
            '    <Message>ARN asdf is not valid.</Message>'
            '  </Error>'
            '  <RequestId>request-id</RequestId>'
            '</ErrorResponse>'
        ).encode('utf-8')
        parser = parsers.QueryParser()
        parsed = parser.parse({
            'body': body, 'headers': {}, 'status_code': 400}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': 'InvalidInput',
            'Message': 'ARN asdf is not valid.',
            'Type': 'Sender',
        })

    def test_can_parse_sdb_error_response_query_protocol(self):
        body = (
            '<OperationNameResponse>'
            '    <Errors>'
            '        <Error>'
            '            <Code>1</Code>'
            '            <Message>msg</Message>'
            '        </Error>'
            '    </Errors>'
            '    <RequestId>abc-123</RequestId>'
            '</OperationNameResponse>'
        ).encode('utf-8')
        parser = parsers.QueryParser()
        parsed = parser.parse({
            'body': body, 'headers': {}, 'status_code': 500}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': '1',
            'Message': 'msg'
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'RequestId': 'abc-123',
            'HTTPStatusCode': 500,
            'HTTPHeaders': {}
        })

    def test_can_parser_ec2_errors(self):
        body = (
            '<Response>'
            '  <Errors>'
            '    <Error>'
            '      <Code>InvalidInstanceID.NotFound</Code>'
            '      <Message>The instance ID i-12345 does not exist</Message>'
            '    </Error>'
            '  </Errors>'
            '  <RequestID>06f382b0-d521-4bb6-988c-ca49d5ae6070</RequestID>'
            '</Response>'
        ).encode('utf-8')
        parser = parsers.EC2QueryParser()
        parsed = parser.parse({
            'body': body, 'headers': {}, 'status_code': 400}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': 'InvalidInstanceID.NotFound',
            'Message': 'The instance ID i-12345 does not exist',
        })

    def test_can_parse_rest_xml_errors(self):
        body = (
            '<ErrorResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">'
            '  <Error>'
            '    <Type>Sender</Type>'
            '    <Code>NoSuchHostedZone</Code>'
            '    <Message>No hosted zone found with ID: foobar</Message>'
            '  </Error>'
            '  <RequestId>bc269cf3-d44f-11e5-8779-2d21c30eb3f1</RequestId>'
            '</ErrorResponse>'
        ).encode('utf-8')
        parser = parsers.RestXMLParser()
        parsed = parser.parse({
            'body': body, 'headers': {}, 'status_code': 400}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': 'NoSuchHostedZone',
            'Message': 'No hosted zone found with ID: foobar',
            'Type': 'Sender',
        })

    def test_can_parse_rest_json_errors(self):
        body = (
            '{"Message":"Function not found: foo","Type":"User"}'
        ).encode('utf-8')
        headers = {
            'x-amzn-requestid': 'request-id',
            'x-amzn-errortype': 'ResourceNotFoundException:http://url/',
        }
        parser = parsers.RestJSONParser()
        parsed = parser.parse({
            'body': body, 'headers': headers, 'status_code': 400}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': 'ResourceNotFoundException',
            'Message': 'Function not found: foo',
        })

    def test_error_response_with_no_body_rest_json(self):
        parser = parsers.RestJSONParser()
        response = b''
        headers = {'content-length': '0', 'connection': 'keep-alive'}
        output_shape = None
        parsed = parser.parse({'body': response, 'headers': headers,
                               'status_code': 504}, output_shape)

        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': '504',
            'Message': 'Gateway Timeout'
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'HTTPStatusCode': 504,
            'HTTPHeaders': headers
        })

    def test_error_response_with_string_body_rest_json(self):
        parser = parsers.RestJSONParser()
        response = b'HTTP content length exceeded 1049600 bytes.'
        headers = {'content-length': '0', 'connection': 'keep-alive'}
        output_shape = None
        parsed = parser.parse({'body': response, 'headers': headers,
                               'status_code': 413}, output_shape)

        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': '413',
            'Message': response.decode('utf-8')
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'HTTPStatusCode': 413,
            'HTTPHeaders': headers
        })

    def test_error_response_with_xml_body_rest_json(self):
        parser = parsers.RestJSONParser()
        response = (
            '<AccessDeniedException>'
            '   <Message>Unable to determine service/operation name to be authorized</Message>'
            '</AccessDeniedException>'
        ).encode('utf-8')
        headers = {'content-length': '0', 'connection': 'keep-alive'}
        output_shape = None
        parsed = parser.parse({'body': response, 'headers': headers,
                               'status_code': 403}, output_shape)

        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': '403',
            'Message': response.decode('utf-8')
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'HTTPStatusCode': 403,
            'HTTPHeaders': headers
        })

    def test_s3_error_response(self):
        body = (
            '<Error>'
            '  <Code>NoSuchBucket</Code>'
            '  <Message>error message</Message>'
            '  <BucketName>asdf</BucketName>'
            '  <RequestId>EF1EF43A74415102</RequestId>'
            '  <HostId>hostid</HostId>'
            '</Error>'
        ).encode('utf-8')
        headers = {
            'x-amz-id-2': 'second-id',
            'x-amz-request-id': 'request-id'
        }
        parser = parsers.RestXMLParser()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 400}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': 'NoSuchBucket',
            'Message': 'error message',
            'BucketName': 'asdf',
            # We don't want the RequestId/HostId because they're already
            # present in the ResponseMetadata key.
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'RequestId': 'request-id',
            'HostId': 'second-id',
            'HTTPStatusCode': 400,
            'HTTPHeaders': headers
        })

    def test_s3_error_response_with_no_body(self):
        # If you try to HeadObject a key that does not exist,
        # you will get an empty body.  When this happens
        # we expect that we will use Code/Message from the
        # HTTP status code.
        body = ''
        headers = {
            'x-amz-id-2': 'second-id',
            'x-amz-request-id': 'request-id'
        }
        parser = parsers.RestXMLParser()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 404}, None)
        self.assertIn('Error', parsed)
        self.assertEqual(parsed['Error'], {
            'Code': '404',
            'Message': 'Not Found',
        })
        self.assertEqual(parsed['ResponseMetadata'], {
            'RequestId': 'request-id',
            'HostId': 'second-id',
            'HTTPStatusCode': 404,
            'HTTPHeaders': headers
        })

    def test_can_parse_glacier_error_response(self):
        body = (b'{"code":"AccessDeniedException","type":"Client","message":'
                b'"Access denied"}')
        headers = {
             'x-amzn-requestid': 'request-id'
        }
        parser = parsers.RestJSONParser()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 400}, None)
        self.assertEqual(parsed['Error'], {'Message': 'Access denied',
                                           'Code': 'AccessDeniedException'})

    def test_can_parse_restjson_error_code(self):
        body = b'''{
            "status": "error",
            "errors": [{"message": "[*Deprecated*: blah"}],
            "adds": 0,
            "__type": "#WasUnableToParseThis",
            "message": "blah",
            "deletes": 0}'''
        headers = {
             'x-amzn-requestid': 'request-id'
        }
        parser = parsers.RestJSONParser()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 400}, None)
        self.assertEqual(parsed['Error'], {'Message': 'blah',
                                           'Code': 'WasUnableToParseThis'})

    def test_can_parse_with_case_insensitive_keys(self):
        body = (b'{"Code":"AccessDeniedException","type":"Client","Message":'
                b'"Access denied"}')
        headers = {
             'x-amzn-requestid': 'request-id'
        }
        parser = parsers.RestJSONParser()
        parsed = parser.parse(
            {'body': body, 'headers': headers, 'status_code': 400}, None)
        self.assertEqual(parsed['Error'], {'Message': 'Access denied',
                                           'Code': 'AccessDeniedException'})

    def test_can_parse_rest_json_modeled_fields(self):
        body = (
            b'{"ModeledField":"Some modeled field",'
            b'"Message":"Some message"}'
        )
        parser = parsers.RestJSONParser()
        response_dict = {
            'status_code': 400,
            'headers': {},
            'body': body,
        }
        parsed = parser.parse(response_dict, self.error_shape)
        expected_parsed = {
            'ModeledField': 'Some modeled field',
        }
        self.assertEqual(parsed, expected_parsed)

    def test_can_parse_rest_xml_modeled_fields(self):
        parser = parsers.RestXMLParser()
        body = (
            b'<?xml version="1.0"?>\n<ErrorResponse xmlns="http://foo.bar">'
            b'<Error><Type>Sender</Type><Code>NoSuchDistribution</Code>'
            b'<Message>The specified distribution does not exist.</Message>'
            b'<ModeledField>Some modeled field</ModeledField>'
            b'</Error>'
            b'</ErrorResponse>'
        )
        response_dict = {
            'status_code': 400,
            'headers': {},
            'body': body,
        }
        parsed = parser.parse(response_dict, self.error_shape)
        expected_parsed = {
            'ModeledField': 'Some modeled field',
        }
        self.assertEqual(parsed, expected_parsed)

    def test_can_parse_ec2_modeled_fields(self):
        body = (
            b'<Response><Errors><Error>'
            b'<Code>ExceptionShape</Code>'
            b'<Message>Foo message</Message>'
            b'<ModeledField>Some modeled field</ModeledField>'
            b'</Error></Errors></Response>'
        )
        parser = parsers.EC2QueryParser()
        response_dict = {
            'status_code': 400,
            'headers': {},
            'body': body,
        }
        parsed = parser.parse(response_dict, self.error_shape)
        expected_parsed = {
            'ModeledField': 'Some modeled field',
        }
        self.assertEqual(parsed, expected_parsed)

    def test_can_parse_query_modeled_fields(self):
        parser = parsers.QueryParser()
        body = (
            b'<?xml version="1.0"?>\n<ErrorResponse xmlns="http://foo.bar">'
            b'<Error><Type>Sender</Type><Code>SomeCode</Code>'
            b'<Message>A message</Message>'
            b'<ModeledField>Some modeled field</ModeledField>'
            b'</Error>'
            b'</ErrorResponse>'
        )
        response_dict = {
            'status_code': 400,
            'headers': {},
            'body': body,
        }
        parsed = parser.parse(response_dict, self.error_shape)
        expected_parsed = {
            'ModeledField': 'Some modeled field',
        }
        self.assertEqual(parsed, expected_parsed)

    def test_can_parse_json_modeled_fields(self):
        body = (
            b'{"ModeledField":"Some modeled field",'
            b'"Message":"Some message",'
            b'"__type": "Prefix#SomeError"}'
        )
        parser = parsers.JSONParser()
        response_dict = {
            'status_code': 400,
            'headers': {},
            'body': body,
        }
        parsed = parser.parse(response_dict, self.error_shape)
        expected_parsed = {
            'ModeledField': 'Some modeled field',
        }
        self.assertEqual(parsed, expected_parsed)

    def test_can_parse_route53_with_missing_message(self):
        # The message isn't always in the XML response (or even the headers).
        # We should be able to handle this gracefully and still at least
        # populate a "Message" key so that consumers don't have to
        # conditionally check for this.
        body =  (
            '<ErrorResponse>'
            '  <Error>'
            '    <Type>Sender</Type>'
            '    <Code>InvalidInput</Code>'
            '  </Error>'
            '  <RequestId>id</RequestId>'
            '</ErrorResponse>'
        ).encode('utf-8')
        parser = parsers.RestXMLParser()
        parsed = parser.parse({
            'body': body, 'headers': {}, 'status_code': 400}, None)
        error = parsed['Error']
        self.assertEqual(error['Code'], 'InvalidInput')
        # Even though there's no <Message /> we should
        # still populate an empty string.
        self.assertEqual(error['Message'], '')

def _generic_test_bodies():
    generic_html_body = (
        '<html><body><b>Http/1.1 Service Unavailable</b></body></html>'
    ).encode('utf-8')
    empty_body = b''
    none_body = None

    return [generic_html_body, empty_body, none_body]

@pytest.mark.parametrize("parser, body",
    itertools.product(
        parsers.PROTOCOL_PARSERS.values(),
        _generic_test_bodies()
    ),
)
def test_can_handle_generic_error_message(parser, body):
    # There are times when you can get a service to respond with a generic
    # html error page.  We should be able to handle this case.
    parsed = parser().parse(
        {'body': body, 'headers': {}, 'status_code': 503}, None
    )
    assert parsed['Error'] == {'Code': '503', 'Message': 'Service Unavailable'}
    assert parsed['ResponseMetadata']['HTTPStatusCode'] == 503
