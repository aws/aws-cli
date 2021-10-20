# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
from tests.unit import BaseResponseTest
import datetime

from dateutil.tz import tzutc
from urllib3.exceptions import ReadTimeoutError as URLLib3ReadTimeoutError

import botocore
from botocore import response
from botocore.compat import six
from botocore.exceptions import IncompleteReadError, ReadTimeoutError
from botocore.awsrequest import AWSRequest, AWSResponse

XMLBODY1 = (b'<?xml version="1.0" encoding="UTF-8"?><Error>'
            b'<Code>AccessDenied</Code>'
            b'<Message>Access Denied</Message>'
            b'<RequestId>XXXXXXXXXXXXXXXX</RequestId>'
            b'<HostId>AAAAAAAAAAAAAAAAAAA</HostId>'
            b'</Error>')

XMLBODY2 = (b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            b'<Name>mybucket</Name><Prefix></Prefix><Marker></Marker>'
            b'<MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated>'
            b'<Contents><Key>test.png</Key><LastModified>2014-03-01T17:06:40.000Z</LastModified>'
            b'<ETag>&quot;00000000000000000000000000000000&quot;</ETag><Size>6702</Size>'
            b'<Owner><ID>AAAAAAAAAAAAAAAAAAA</ID>'
            b'<DisplayName>dummy</DisplayName></Owner>'
            b'<StorageClass>STANDARD</StorageClass></Contents></ListBucketResult>')


class TestStreamWrapper(unittest.TestCase):

    def assert_lines(self, line_iterator, expected_lines):
        for expected_line in expected_lines:
            self.assertEqual(
                next(line_iterator),
                expected_line,
            )
        # We should have exhausted the iterator.
        with self.assertRaises(StopIteration):
            next(line_iterator)

    def test_streaming_wrapper_validates_content_length(self):
        body = six.BytesIO(b'1234567890')
        stream = response.StreamingBody(body, content_length=10)
        self.assertEqual(stream.read(), b'1234567890')

    def test_streaming_body_with_invalid_length(self):
        body = six.BytesIO(b'123456789')
        stream = response.StreamingBody(body, content_length=10)
        with self.assertRaises(IncompleteReadError):
            self.assertEqual(stream.read(9), b'123456789')
            # The next read will have nothing returned and raise
            # an IncompleteReadError because we were expectd 10 bytes, not 9.
            stream.read()

    def test_streaming_body_with_zero_read(self):
        body = six.BytesIO(b'1234567890')
        stream = response.StreamingBody(body, content_length=10)
        chunk = stream.read(0)
        self.assertEqual(chunk, b'')
        self.assertEqual(stream.read(), b'1234567890')

    def test_streaming_body_with_single_read(self):
        body = six.BytesIO(b'123456789')
        stream = response.StreamingBody(body, content_length=10)
        with self.assertRaises(IncompleteReadError):
            stream.read()

    def test_streaming_body_closes(self):
        body = six.BytesIO(b'1234567890')
        stream = response.StreamingBody(body, content_length=10)
        self.assertFalse(body.closed)
        stream.close()
        self.assertTrue(body.closed)

    def test_default_iter_behavior(self):
        body = six.BytesIO(b'a' * 2048)
        stream = response.StreamingBody(body, content_length=2048)
        chunks = list(stream)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks, [b'a' * 1024, b'a' * 1024])

    def test_streaming_body_is_an_iterator(self):
        body = six.BytesIO(b'a' * 1024 + b'b' * 1024 + b'c' * 2)
        stream = response.StreamingBody(body, content_length=2050)
        self.assertEqual(b'a' * 1024, next(stream))
        self.assertEqual(b'b' * 1024, next(stream))
        self.assertEqual(b'c' * 2, next(stream))
        with self.assertRaises(StopIteration):
            next(stream)

    def test_iter_chunks_single_byte(self):
        body = six.BytesIO(b'abcde')
        stream = response.StreamingBody(body, content_length=5)
        chunks = list(stream.iter_chunks(chunk_size=1))
        self.assertEqual(chunks, [b'a', b'b', b'c', b'd', b'e'])

    def test_iter_chunks_with_leftover(self):
        body = six.BytesIO(b'abcde')
        stream = response.StreamingBody(body, content_length=5)
        chunks = list(stream.iter_chunks(chunk_size=2))
        self.assertEqual(chunks, [b'ab', b'cd', b'e'])

    def test_iter_chunks_single_chunk(self):
        body = six.BytesIO(b'abcde')
        stream = response.StreamingBody(body, content_length=5)
        chunks = list(stream.iter_chunks(chunk_size=1024))
        self.assertEqual(chunks, [b'abcde'])

    def test_streaming_line_iterator(self):
        body = six.BytesIO(b'1234567890\n1234567890\n12345')
        stream = response.StreamingBody(body, content_length=27)
        self.assert_lines(
            stream.iter_lines(),
            [b'1234567890', b'1234567890', b'12345'],
        )

    def test_streaming_line_iterator_ends_newline(self):
        body = six.BytesIO(b'1234567890\n1234567890\n12345\n')
        stream = response.StreamingBody(body, content_length=28)
        self.assert_lines(
            stream.iter_lines(),
            [b'1234567890', b'1234567890', b'12345'],
        )

    def test_streaming_line_iter_chunk_sizes(self):
        for chunk_size in range(1, 30):
            body = six.BytesIO(b'1234567890\n1234567890\n12345')
            stream = response.StreamingBody(body, content_length=27)
            self.assert_lines(
                stream.iter_lines(chunk_size),
                [b'1234567890', b'1234567890', b'12345'],
            )

    def test_streaming_line_iterator_keepends(self):
        body = six.BytesIO(b'1234567890\n1234567890\n12345')
        stream = response.StreamingBody(body, content_length=27)
        self.assert_lines(
            stream.iter_lines(keepends=True),
            [b'1234567890\n', b'1234567890\n', b'12345'],
        )

    def test_catches_urllib3_read_timeout(self):
        class TimeoutBody(object):
            def read(*args, **kwargs):
                raise URLLib3ReadTimeoutError(None, None, None)

            def geturl(*args, **kwargs):
                return 'http://example.com'

        stream = response.StreamingBody(TimeoutBody(), content_length=None)
        with self.assertRaises(ReadTimeoutError):
            stream.read()

    def test_streaming_line_abstruse_newline_standard(self):
        for chunk_size in range(1, 30):
            body = six.BytesIO(b'1234567890\r\n1234567890\r\n12345\r\n')
            stream = response.StreamingBody(body, content_length=31)
            self.assert_lines(
                stream.iter_lines(chunk_size),
                [b'1234567890', b'1234567890', b'12345'],
            )

    def test_streaming_line_empty_body(self):
        stream = response.StreamingBody(
            six.BytesIO(b''), content_length=0,
        )
        self.assert_lines(stream.iter_lines(), [])


class FakeRawResponse(six.BytesIO):
    def stream(self, amt=1024, decode_content=None):
        while True:
            chunk = self.read(amt)
            if not chunk:
                break
            yield chunk


class TestGetResponse(BaseResponseTest):
    maxDiff = None

    def test_get_response_streaming_ok(self):
        headers = {
            'content-type': 'image/png',
            'server': 'AmazonS3',
            'AcceptRanges': 'bytes',
            'transfer-encoding': 'chunked',
            'ETag': '"00000000000000000000000000000000"',
        }
        raw = FakeRawResponse(b'\x89PNG\r\n\x1a\n\x00\x00')

        http_response = AWSResponse(None, 200, headers, raw)

        session = botocore.session.get_session()
        service_model = session.get_service_model('s3')
        operation_model = service_model.operation_model('GetObject')

        res = response.get_response(operation_model, http_response)
        self.assertTrue(isinstance(res[1]['Body'], response.StreamingBody))
        self.assertEqual(res[1]['ETag'],
                         '"00000000000000000000000000000000"')

    def test_get_response_streaming_ng(self):
        headers = {
            'content-type': 'application/xml',
            'date': 'Sat, 08 Mar 2014 12:05:44 GMT',
            'server': 'AmazonS3',
            'transfer-encoding': 'chunked',
            'x-amz-id-2': 'AAAAAAAAAAAAAAAAAAA',
            'x-amz-request-id': 'XXXXXXXXXXXXXXXX'}
        raw = FakeRawResponse(XMLBODY1)
        http_response = AWSResponse(None, 403, headers, raw)

        session = botocore.session.get_session()
        service_model = session.get_service_model('s3')
        operation_model = service_model.operation_model('GetObject')

        self.assert_response_with_subset_metadata(
            response.get_response(operation_model, http_response)[1],
            {'Error': {'Message': 'Access Denied',
                       'Code': 'AccessDenied'},
             'ResponseMetadata': {'HostId': 'AAAAAAAAAAAAAAAAAAA',
                                  'RequestId': 'XXXXXXXXXXXXXXXX',
                                  'HTTPStatusCode': 403},
             }
        )

    def test_get_response_nonstreaming_ok(self):
        headers = {
            'content-type': 'application/xml',
            'date': 'Sun, 09 Mar 2014 02:55:43 GMT',
            'server': 'AmazonS3',
            'transfer-encoding': 'chunked',
            'x-amz-id-2': 'AAAAAAAAAAAAAAAAAAA',
            'x-amz-request-id': 'XXXXXXXXXXXXXXXX'}
        raw = FakeRawResponse(XMLBODY1)
        http_response = AWSResponse(None, 403, headers, raw)

        session = botocore.session.get_session()
        service_model = session.get_service_model('s3')
        operation_model = service_model.operation_model('ListObjects')

        self.assert_response_with_subset_metadata(
            response.get_response(operation_model, http_response)[1],
            {
                'ResponseMetadata': {
                    'RequestId': 'XXXXXXXXXXXXXXXX',
                    'HostId': 'AAAAAAAAAAAAAAAAAAA',
                    'HTTPStatusCode': 403
                },
                'Error': {
                    'Message': 'Access Denied',
                    'Code': 'AccessDenied'
                }
            })

    def test_get_response_nonstreaming_ng(self):
        headers = {
            'content-type': 'application/xml',
            'date': 'Sat, 08 Mar 2014 12:05:44 GMT',
            'server': 'AmazonS3',
            'transfer-encoding': 'chunked',
            'x-amz-id-2': 'AAAAAAAAAAAAAAAAAAA',
            'x-amz-request-id': 'XXXXXXXXXXXXXXXX'}
        raw = FakeRawResponse(XMLBODY2)
        http_response = AWSResponse(None, 200, headers, raw)

        session = botocore.session.get_session()
        service_model = session.get_service_model('s3')
        operation_model = service_model.operation_model('ListObjects')

        self.assert_response_with_subset_metadata(
            response.get_response(operation_model, http_response)[1],
            {u'Contents': [{u'ETag': '"00000000000000000000000000000000"',
                            u'Key': 'test.png',
                            u'LastModified': datetime.datetime(2014, 3, 1, 17, 6, 40, tzinfo=tzutc()),
                            u'Owner': {u'DisplayName': 'dummy',
                                       u'ID': 'AAAAAAAAAAAAAAAAAAA'},
                            u'Size': 6702,
                            u'StorageClass': 'STANDARD'}],
             u'IsTruncated': False,
             u'Marker': "",
             u'MaxKeys': 1000,
             u'Name': 'mybucket',
             u'Prefix': "",
             'ResponseMetadata': {
                 'RequestId': 'XXXXXXXXXXXXXXXX',
                 'HostId': 'AAAAAAAAAAAAAAAAAAA',
                 'HTTPStatusCode': 200,
             }}
        )
