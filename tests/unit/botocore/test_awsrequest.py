#!/usr/bin/env
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
import os
import tempfile
import shutil
import io
import socket
import sys

from mock import Mock, patch
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

from botocore.exceptions import UnseekableStreamError
from botocore.awsrequest import AWSRequest, AWSPreparedRequest, AWSResponse
from botocore.awsrequest import AWSHTTPConnection, AWSHTTPSConnection, HeadersDict
from botocore.awsrequest import prepare_request_dict, create_request_object
from botocore.compat import file_type, six


class IgnoreCloseBytesIO(io.BytesIO):
    def close(self):
        pass


class FakeSocket(object):
    def __init__(self, read_data, fileclass=IgnoreCloseBytesIO):
        self.sent_data = b''
        self.read_data = read_data
        self.fileclass = fileclass
        self._fp_object = None

    def sendall(self, data):
        self.sent_data += data

    def makefile(self, mode, bufsize=None):
        if self._fp_object is None:
            self._fp_object = self.fileclass(self.read_data)
        return self._fp_object

    def close(self):
        pass


class BytesIOWithLen(six.BytesIO):
    def __len__(self):
        return len(self.getvalue())


class Unseekable(file_type):
    def __init__(self, stream):
        self._stream = stream

    def read(self):
        return self._stream.read()

    def seek(self, offset, whence):
        # This is a case where seek() exists as part of the object's interface,
        # but it doesn't actually work (for example socket.makefile(), which
        # will raise an io.* error on python3).
        raise ValueError("Underlying stream does not support seeking.")


class Seekable(object):
    """This class represents a bare-bones,seekable file-like object

    Note it does not include some of the other attributes of other
    file-like objects such as StringIO's getvalue() and file object's fileno
    property. If the file-like object does not have either of these attributes
    requests will not calculate the content length even though it is still
    possible to calculate it.
    """
    def __init__(self, stream):
        self._stream = stream

    def __iter__(self):
        return iter(self._stream)

    def read(self):
        return self._stream.read()

    def seek(self, offset, whence=0):
        self._stream.seek(offset, whence)

    def tell(self):
        return self._stream.tell()


class TestAWSRequest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'foo')
        self.request = AWSRequest(method='GET', url='http://example.com')
        self.prepared_request = self.request.prepare()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_prepared_request_repr(self):
        expected_repr = (
            '<AWSPreparedRequest stream_output=False, method=GET, '
            'url=http://example.com, headers={}>'
        )
        request_repr = repr(self.prepared_request)
        self.assertEqual(request_repr, expected_repr)

    def test_can_prepare_url_params(self):
        request = AWSRequest(url='http://example.com/', params={'foo': 'bar'})
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.url, 'http://example.com/?foo=bar')

    def test_can_prepare_dict_body(self):
        body = {'dead': 'beef'}
        request = AWSRequest(url='http://example.com/', data=body)
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.body, 'dead=beef')

    def test_can_prepare_dict_body_unicode_values(self):
        body = {'Text': u'\u30c6\u30b9\u30c8 string'}
        expected_body = 'Text=%E3%83%86%E3%82%B9%E3%83%88+string'
        request = AWSRequest(url='http://example.com/', data=body)
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.body, expected_body)

    def test_can_prepare_dict_body_unicode_keys(self):
        body = {u'\u30c6\u30b9\u30c8': 'string'}
        expected_body = '%E3%83%86%E3%82%B9%E3%83%88=string'
        request = AWSRequest(url='http://example.com/', data=body)
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.body, expected_body)

    def test_can_prepare_empty_body(self):
        request = AWSRequest(url='http://example.com/', data=b'')
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.body, None)
        content_length = prepared_request.headers.get('content-length')
        self.assertEqual(content_length, '0')

    def test_request_body_is_prepared(self):
        request = AWSRequest(url='http://example.com/', data='body')
        self.assertEqual(request.body, b'body')

    def test_prepare_body_content_adds_content_length(self):
        content = b'foobarbaz'
        expected_len = str(len(content))
        with open(self.filename, 'wb') as f:
            f.write(content)
        with open(self.filename, 'rb') as f:
            data = Seekable(f)
            self.request.data = data
            self.request.method = 'POST'
            prepared_request = self.request.prepare()
            calculated_len = prepared_request.headers['Content-Length']
            self.assertEqual(calculated_len, expected_len)

    def test_prepare_body_doesnt_override_content_length(self):
        self.request.method = 'PUT'
        self.request.headers['Content-Length'] = '20'
        self.request.data = b'asdf'
        prepared_request = self.request.prepare()
        self.assertEqual(prepared_request.headers['Content-Length'], '20')

    def test_prepare_body_doesnt_set_content_length_head(self):
        self.request.method = 'HEAD'
        self.request.data = b'thisshouldntbehere'
        prepared_request = self.request.prepare()
        self.assertEqual(prepared_request.headers.get('Content-Length'), None)

    def test_prepare_body_doesnt_set_content_length_get(self):
        self.request.method = 'GET'
        self.request.data = b'thisshouldntbehere'
        prepared_request = self.request.prepare()
        self.assertEqual(prepared_request.headers.get('Content-Length'), None)

    def test_prepare_body_doesnt_set_content_length_options(self):
        self.request.method = 'OPTIONS'
        self.request.data = b'thisshouldntbehere'
        prepared_request = self.request.prepare()
        self.assertEqual(prepared_request.headers.get('Content-Length'), None)

    def test_can_reset_stream_handles_binary(self):
        contents = b'notastream'
        self.prepared_request.body = contents
        self.prepared_request.reset_stream()
        # assert the request body doesn't change after reset_stream is called
        self.assertEqual(self.prepared_request.body, contents)

    def test_can_reset_stream_handles_bytearray(self):
        contents = bytearray(b'notastream')
        self.prepared_request.body = contents
        self.prepared_request.reset_stream()
        # assert the request body doesn't change after reset_stream is called
        self.assertEqual(self.prepared_request.body, contents)

    def test_can_reset_stream(self):
        contents = b'foobarbaz'
        with open(self.filename, 'wb') as f:
            f.write(contents)
        with open(self.filename, 'rb') as body:
            self.prepared_request.body = body
            # pretend the request body was partially sent
            body.read()
            self.assertNotEqual(body.tell(), 0)
            # have the prepared request reset its stream
            self.prepared_request.reset_stream()
            # the stream should be reset
            self.assertEqual(body.tell(), 0)

    def test_cannot_reset_stream_raises_error(self):
        contents = b'foobarbaz'
        with open(self.filename, 'wb') as f:
            f.write(contents)
        with open(self.filename, 'rb') as body:
            self.prepared_request.body = Unseekable(body)
            # pretend the request body was partially sent
            body.read()
            self.assertNotEqual(body.tell(), 0)
            # reset stream should fail
            with self.assertRaises(UnseekableStreamError):
                self.prepared_request.reset_stream()

    def test_duck_type_for_file_check(self):
        # As part of determining whether or not we can rewind a stream
        # we first need to determine if the thing is a file like object.
        # We should not be using an isinstance check.  Instead, we should
        # be using duck type checks.
        class LooksLikeFile(object):
            def __init__(self):
                self.seek_called = False
            def read(self, amount=None):
                pass
            def seek(self, where):
                self.seek_called = True
        looks_like_file = LooksLikeFile()
        self.prepared_request.body = looks_like_file
        self.prepared_request.reset_stream()
        # The stream should now be reset.
        self.assertTrue(looks_like_file.seek_called)


class TestAWSResponse(unittest.TestCase):
    def setUp(self):
        self.response = AWSResponse('http://url.com', 200, HeadersDict(), None)
        self.response.raw = Mock()

    def set_raw_stream(self, blobs):
        def stream(*args, **kwargs):
            for blob in blobs:
                yield blob
        self.response.raw.stream.return_value = stream()

    def test_content_property(self):
        self.set_raw_stream([b'some', b'data'])
        self.assertEqual(self.response.content, b'somedata')
        self.assertEqual(self.response.content, b'somedata')
        # assert that stream was not called more than once
        self.assertEqual(self.response.raw.stream.call_count, 1)

    def test_text_property(self):
        self.set_raw_stream([b'\xe3\x82\xb8\xe3\x83\xa7\xe3\x82\xb0'])
        self.response.headers['content-type'] = 'text/plain; charset=utf-8'
        self.assertEqual(self.response.text, u'\u30b8\u30e7\u30b0')

    def test_text_property_defaults_utf8(self):
        self.set_raw_stream([b'\xe3\x82\xb8\xe3\x83\xa7\xe3\x82\xb0'])
        self.assertEqual(self.response.text, u'\u30b8\u30e7\u30b0')


class TestAWSHTTPConnection(unittest.TestCase):
    def create_tunneled_connection(self, url, port, response):
        s = FakeSocket(response)
        conn = AWSHTTPConnection(url, port)
        conn.sock = s
        conn._tunnel_host = url
        conn._tunnel_port = port
        conn._tunnel_headers = {'key': 'value'}

        # Create a mock response.
        self.mock_response = Mock()
        self.mock_response.fp = Mock()

        # Imitate readline function by creating a list to be sent as
        # a side effect of the mocked readline to be able to track how the
        # response is processed in ``_tunnel()``.
        delimeter = b'\r\n'
        side_effect = []
        response_components = response.split(delimeter)
        for i in range(len(response_components)):
            new_component = response_components[i]
            # Only add the delimeter on if it is not the last component
            # which should be an empty string.
            if i != len(response_components) - 1:
                new_component += delimeter
            side_effect.append(new_component)

        self.mock_response.fp.readline.side_effect = side_effect

        response_components = response.split(b' ')
        self.mock_response._read_status.return_value = (
            response_components[0], int(response_components[1]),
            response_components[2]
        )
        conn.response_class = Mock()
        conn.response_class.return_value = self.mock_response
        return conn

    def test_expect_100_continue_returned(self):
        with patch('urllib3.util.wait_for_read') as wait_mock:
            # Shows the server first sending a 100 continue response
            # then a 200 ok response.
            s = FakeSocket(b'HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 200 OK\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            wait_mock.return_value = True
            conn.request('GET', '/bucket/foo', b'body',
                         {'Expect': b'100-continue'})
            response = conn.getresponse()
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 1)
            # Now we should verify that our final response is the 200 OK
            self.assertEqual(response.status, 200)

    def test_handles_expect_100_with_different_reason_phrase(self):
        with patch('urllib3.util.wait_for_read') as wait_mock:
            # Shows the server first sending a 100 continue response
            # then a 200 ok response.
            s = FakeSocket(b'HTTP/1.1 100 (Continue)\r\n\r\nHTTP/1.1 200 OK\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            wait_mock.return_value = True
            conn.request('GET', '/bucket/foo', six.BytesIO(b'body'),
                         {'Expect': b'100-continue', 'Content-Length': b'4'})
            response = conn.getresponse()
            # Now we should verify that our final response is the 200 OK.
            self.assertEqual(response.status, 200)
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 1)
            # Verify that we went the request body because we got a 100
            # continue.
            self.assertIn(b'body', s.sent_data)

    def test_expect_100_sends_connection_header(self):
        # When using squid as an HTTP proxy, it will also send
        # a Connection: keep-alive header back with the 100 continue
        # response.  We need to ensure we handle this case.
        with patch('urllib3.util.wait_for_read') as wait_mock:
            # Shows the server first sending a 100 continue response
            # then a 500 response.  We're picking 500 to confirm we
            # actually parse the response instead of getting the
            # default status of 200 which happens when we can't parse
            # the response.
            s = FakeSocket(b'HTTP/1.1 100 Continue\r\n'
                           b'Connection: keep-alive\r\n'
                           b'\r\n'
                           b'HTTP/1.1 500 Internal Service Error\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            wait_mock.return_value = True
            conn.request('GET', '/bucket/foo', b'body',
                         {'Expect': b'100-continue'})
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 1)
            response = conn.getresponse()
            self.assertEqual(response.status, 500)

    def test_expect_100_continue_sends_307(self):
        # This is the case where we send a 100 continue and the server
        # immediately sends a 307
        with patch('urllib3.util.wait_for_read') as wait_mock:
            # Shows the server first sending a 100 continue response
            # then a 200 ok response.
            s = FakeSocket(
                b'HTTP/1.1 307 Temporary Redirect\r\n'
                b'Location: http://example.org\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            wait_mock.return_value = True
            conn.request('GET', '/bucket/foo', b'body',
                         {'Expect': b'100-continue'})
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 1)
            response = conn.getresponse()
            # Now we should verify that our final response is the 307.
            self.assertEqual(response.status, 307)

    def test_expect_100_continue_no_response_from_server(self):
        with patch('urllib3.util.wait_for_read') as wait_mock:
            # Shows the server first sending a 100 continue response
            # then a 200 ok response.
            s = FakeSocket(
                b'HTTP/1.1 307 Temporary Redirect\r\n'
                b'Location: http://example.org\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            # By settings wait_mock to return False, this indicates
            # that the server did not send any response.  In this situation
            # we should just send the request anyways.
            wait_mock.return_value = False
            conn.request('GET', '/bucket/foo', b'body',
                         {'Expect': b'100-continue'})
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 1)
            response = conn.getresponse()
            self.assertEqual(response.status, 307)

    def test_message_body_is_file_like_object(self):
        # Shows the server first sending a 100 continue response
        # then a 200 ok response.
        body = BytesIOWithLen(b'body contents')
        s = FakeSocket(b'HTTP/1.1 200 OK\r\n')
        conn = AWSHTTPConnection('s3.amazonaws.com', 443)
        conn.sock = s
        conn.request('GET', '/bucket/foo', body)
        response = conn.getresponse()
        self.assertEqual(response.status, 200)

    def test_no_expect_header_set(self):
        # Shows the server first sending a 100 continue response
        # then a 200 ok response.
        s = FakeSocket(b'HTTP/1.1 200 OK\r\n')
        conn = AWSHTTPConnection('s3.amazonaws.com', 443)
        conn.sock = s
        conn.request('GET', '/bucket/foo', b'body')
        response = conn.getresponse()
        self.assertEqual(response.status, 200)

    def test_tunnel_readline_none_bugfix(self):
        # Tests whether ``_tunnel`` function is able to work around the
        # py26 bug of avoiding infinite while loop if nothing is returned.
        conn = self.create_tunneled_connection(
            url='s3.amazonaws.com',
            port=443,
            response=b'HTTP/1.1 200 OK\r\n',
        )
        conn._tunnel()
        # Ensure proper amount of readline calls were made.
        self.assertEqual(self.mock_response.fp.readline.call_count, 2)

    def test_tunnel_readline_normal(self):
        # Tests that ``_tunnel`` function behaves normally when it comes
        # across the usual http ending.
        conn = self.create_tunneled_connection(
            url='s3.amazonaws.com',
            port=443,
            response=b'HTTP/1.1 200 OK\r\n\r\n',
        )
        conn._tunnel()
        # Ensure proper amount of readline calls were made.
        self.assertEqual(self.mock_response.fp.readline.call_count, 2)

    def test_tunnel_raises_socket_error(self):
        # Tests that ``_tunnel`` function throws appropriate error when
        # not 200 status.
        conn = self.create_tunneled_connection(
            url='s3.amazonaws.com',
            port=443,
            response=b'HTTP/1.1 404 Not Found\r\n\r\n',
        )
        with self.assertRaises(socket.error):
            conn._tunnel()

    def test_tunnel_uses_std_lib(self):
        s = FakeSocket(b'HTTP/1.1 200 OK\r\n')
        conn = AWSHTTPConnection('s3.amazonaws.com', 443)
        conn.sock = s
        # Test that the standard library method was used by patching out
        # the ``_tunnel`` method and seeing if the std lib method was called.
        with patch('urllib3.connection.HTTPConnection._tunnel') as mock_tunnel:
            conn._tunnel()
            self.assertTrue(mock_tunnel.called)

    def test_encodes_unicode_method_line(self):
        s = FakeSocket(b'HTTP/1.1 200 OK\r\n')
        conn = AWSHTTPConnection('s3.amazonaws.com', 443)
        conn.sock = s
        # Note the combination of unicode 'GET' and
        # bytes 'Utf8-Header' value.
        conn.request(u'GET', '/bucket/foo', b'body',
                     headers={"Utf8-Header": b"\xe5\xb0\x8f"})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)

    def test_state_reset_on_connection_close(self):
        # This simulates what urllib3 does with connections
        # in its connection pool logic.
        with patch('urllib3.util.wait_for_read') as wait_mock:

            # First fast fail with a 500 response when we first
            # send the expect header.
            s = FakeSocket(b'HTTP/1.1 500 Internal Server Error\r\n')
            conn = AWSHTTPConnection('s3.amazonaws.com', 443)
            conn.sock = s
            wait_mock.return_value = True

            conn.request('GET', '/bucket/foo', b'body',
                        {'Expect': b'100-continue'})
            self.assertEqual(wait_mock.call_count, 1)
            response = conn.getresponse()
            self.assertEqual(response.status, 500)

            # Now what happens in urllib3 is that when the next
            # request comes along and this conection gets checked
            # out.  We see that the connection needs to be
            # reset.  So first the connection is closed.
            conn.close()

            # And then a new connection is established.
            new_conn = FakeSocket(
                b'HTTP/1.1 100 (Continue)\r\n\r\nHTTP/1.1 200 OK\r\n')
            conn.sock = new_conn

            # And we make a request, we should see the 200 response
            # that was sent back.
            wait_mock.return_value = True

            conn.request('GET', '/bucket/foo', b'body',
                        {'Expect': b'100-continue'})
            # Assert that we waited for the 100-continue response
            self.assertEqual(wait_mock.call_count, 2)
            response = conn.getresponse()
            # This should be 200.  If it's a 500 then
            # the prior response was leaking into our
            # current response.,
            self.assertEqual(response.status, 200)


class TestAWSHTTPConnectionPool(unittest.TestCase):
    def test_global_urllib3_pool_is_unchanged(self):
        http_connection_class = HTTPConnectionPool.ConnectionCls
        self.assertIsNot(http_connection_class, AWSHTTPConnection)
        https_connection_class = HTTPSConnectionPool.ConnectionCls
        self.assertIsNot(https_connection_class, AWSHTTPSConnection)


class TestPrepareRequestDict(unittest.TestCase):
    def setUp(self):
        self.user_agent = 'botocore/1.0'
        self.endpoint_url = 'https://s3.amazonaws.com'
        self.base_request_dict = {
            'body': '',
            'headers': {},
            'method': u'GET',
            'query_string': '',
            'url_path': '/',
            'context': {}
        }

    def prepare_base_request_dict(self, request_dict, endpoint_url=None,
                                  user_agent=None, context=None):
        self.base_request_dict.update(request_dict)
        context = context or {}
        if user_agent is None:
            user_agent = self.user_agent
        if endpoint_url is None:
            endpoint_url = self.endpoint_url
        prepare_request_dict(self.base_request_dict, endpoint_url=endpoint_url,
                             user_agent=user_agent, context=context)

    def test_prepare_request_dict_for_get(self):
        request_dict = {
            'method': u'GET',
            'url_path': '/'
        }
        self.prepare_base_request_dict(
            request_dict, endpoint_url='https://s3.amazonaws.com')
        self.assertEqual(self.base_request_dict['method'], 'GET')
        self.assertEqual(self.base_request_dict['url'],
                         'https://s3.amazonaws.com/')
        self.assertEqual(self.base_request_dict['headers']['User-Agent'],
                         self.user_agent)

    def test_prepare_request_dict_for_get_no_user_agent(self):
        self.user_agent = None
        request_dict = {
            'method': u'GET',
            'url_path': '/'
        }
        self.prepare_base_request_dict(
            request_dict, endpoint_url='https://s3.amazonaws.com')
        self.assertNotIn('User-Agent', self.base_request_dict['headers'])

    def test_prepare_request_dict_with_context(self):
        context = {'foo': 'bar'}
        self.prepare_base_request_dict({}, context=context)
        self.assertEqual(self.base_request_dict['context'], context)

    def test_query_string_serialized_to_url(self):
        request_dict = {
            'method': u'GET',
            'query_string': {u'prefix': u'foo'},
            'url_path': u'/mybucket'
        }
        self.prepare_base_request_dict(request_dict)
        self.assertEqual(
            self.base_request_dict['url'],
            'https://s3.amazonaws.com/mybucket?prefix=foo')

    def test_url_path_combined_with_endpoint_url(self):
        # This checks the case where a user specifies and
        # endpoint_url that has a path component, and the
        # serializer gives us a request_dict that has a url
        # component as well (say from a rest-* service).
        request_dict = {
            'query_string': {u'prefix': u'foo'},
            'url_path': u'/mybucket'
        }
        endpoint_url = 'https://custom.endpoint/foo/bar'
        self.prepare_base_request_dict(request_dict, endpoint_url)
        self.assertEqual(
            self.base_request_dict['url'],
            'https://custom.endpoint/foo/bar/mybucket?prefix=foo')

    def test_url_path_with_trailing_slash(self):
        self.prepare_base_request_dict(
            {'url_path': u'/mybucket'},
            endpoint_url='https://custom.endpoint/foo/bar/')

        self.assertEqual(
            self.base_request_dict['url'],
            'https://custom.endpoint/foo/bar/mybucket')

    def test_url_path_is_slash(self):
        self.prepare_base_request_dict(
            {'url_path': u'/'},
            endpoint_url='https://custom.endpoint/foo/bar/')

        self.assertEqual(
            self.base_request_dict['url'],
            'https://custom.endpoint/foo/bar/')

    def test_url_path_is_slash_with_endpoint_url_no_slash(self):
        self.prepare_base_request_dict(
            {'url_path': u'/'},
            endpoint_url='https://custom.endpoint/foo/bar')

        self.assertEqual(
            self.base_request_dict['url'],
            'https://custom.endpoint/foo/bar')

    def test_custom_endpoint_with_query_string(self):
        self.prepare_base_request_dict(
            {'url_path': u'/baz', 'query_string': {'x': 'y'}},
            endpoint_url='https://custom.endpoint/foo/bar?foo=bar')

        self.assertEqual(
            self.base_request_dict['url'],
            'https://custom.endpoint/foo/bar/baz?foo=bar&x=y')


class TestCreateRequestObject(unittest.TestCase):
    def setUp(self):
        self.request_dict = {
            'method': u'GET',
            'query_string': {u'prefix': u'foo'},
            'url_path': u'/mybucket',
            'headers': {u'User-Agent': u'my-agent'},
            'body': u'my body',
            'url': u'https://s3.amazonaws.com/mybucket?prefix=foo',
            'context': {'signing': {'region': 'us-west-2'}}
        }

    def test_create_request_object(self):
        request = create_request_object(self.request_dict)
        self.assertEqual(request.method, self.request_dict['method'])
        self.assertEqual(request.url, self.request_dict['url'])
        self.assertEqual(request.data, self.request_dict['body'])
        self.assertEqual(request.context, self.request_dict['context'])
        self.assertIn('User-Agent', request.headers)


class TestHeadersDict(unittest.TestCase):
    def setUp(self):
        self.headers = HeadersDict()

    def test_get_insensitive(self):
        self.headers['foo'] = 'bar'
        self.assertEqual(self.headers['FOO'], 'bar')

    def test_set_insensitive(self):
        self.headers['foo'] = 'bar'
        self.headers['FOO'] = 'baz'
        self.assertEqual(self.headers['foo'], 'baz')

    def test_del_insensitive(self):
        self.headers['foo'] = 'bar'
        self.assertEqual(self.headers['FOO'], 'bar')
        del self.headers['FoO']
        with self.assertRaises(KeyError):
            self.headers['foo']

    def test_iteration(self):
        self.headers['FOO'] = 'bar'
        self.headers['dead'] = 'beef'
        self.assertIn('FOO', list(self.headers))
        self.assertIn('dead', list(self.headers))
        headers_items = list(self.headers.items())
        self.assertIn(('FOO', 'bar'), headers_items)
        self.assertIn(('dead', 'beef'), headers_items)


if __name__ == "__main__":
    unittest.main()
