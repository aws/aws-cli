#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
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
import datetime
import time
import base64
import json

import mock

import botocore.auth
import botocore.credentials
from botocore.compat import HTTPHeaders, urlsplit, parse_qs, six
from botocore.awsrequest import AWSRequest


class BaseTestWithFixedDate(unittest.TestCase):
    def setUp(self):
        self.fixed_date = datetime.datetime(2014, 3, 10, 17, 2, 55, 0)
        self.datetime_patch = mock.patch('botocore.auth.datetime.datetime')
        self.datetime_mock = self.datetime_patch.start()
        self.datetime_mock.utcnow.return_value = self.fixed_date
        self.datetime_mock.strptime.return_value = self.fixed_date

    def tearDown(self):
        self.datetime_patch.stop()


class TestSigV2(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        access_key = 'foo'
        secret_key = 'bar'
        self.credentials = botocore.credentials.Credentials(access_key,
                                                            secret_key)
        self.signer = botocore.auth.SigV2Auth(self.credentials)
        self.time_patcher = mock.patch.object(
            botocore.auth.time, 'gmtime',
            mock.Mock(wraps=time.gmtime)
        )
        mocked_time = self.time_patcher.start()
        mocked_time.return_value = time.struct_time(
            [2014, 6, 20, 8, 40, 23, 4, 171, 0])

    def tearDown(self):
        self.time_patcher.stop()

    def test_put(self):
        request = mock.Mock()
        request.url = '/'
        request.method = 'POST'
        params = {'Foo': u'\u2713'}
        result = self.signer.calc_signature(request, params)
        self.assertEqual(
            result, ('Foo=%E2%9C%93',
                     u'VCtWuwaOL0yMffAT8W4y0AFW3W4KUykBqah9S40rB+Q='))

    def test_fields(self):
        request = AWSRequest()
        request.url = '/'
        request.method = 'POST'
        request.data = {'Foo': u'\u2713'}
        self.signer.add_auth(request)
        self.assertEqual(request.data['AWSAccessKeyId'], 'foo')
        self.assertEqual(request.data['Foo'], u'\u2713')
        self.assertEqual(request.data['Timestamp'], '2014-06-20T08:40:23Z')
        self.assertEqual(request.data['Signature'],
                         u'Tiecw+t51tok4dTT8B4bg47zxHEM/KcD55f2/x6K22o=')
        self.assertEqual(request.data['SignatureMethod'], 'HmacSHA256')
        self.assertEqual(request.data['SignatureVersion'], '2')

    def test_resign(self):
        # Make sure that resigning after e.g. retries works
        request = AWSRequest()
        request.url = '/'
        request.method = 'POST'
        params = {
            'Foo': u'\u2713',
            'Signature': u'VCtWuwaOL0yMffAT8W4y0AFW3W4KUykBqah9S40rB+Q='
        }
        result = self.signer.calc_signature(request, params)
        self.assertEqual(
            result, ('Foo=%E2%9C%93',
                     u'VCtWuwaOL0yMffAT8W4y0AFW3W4KUykBqah9S40rB+Q='))

    def test_get(self):
        request = AWSRequest()
        request.url = '/'
        request.method = 'GET'
        request.params = {'Foo': u'\u2713'}
        self.signer.add_auth(request)
        self.assertEqual(request.params['AWSAccessKeyId'], 'foo')
        self.assertEqual(request.params['Foo'], u'\u2713')
        self.assertEqual(request.params['Timestamp'], '2014-06-20T08:40:23Z')
        self.assertEqual(request.params['Signature'],
                         u'Un97klqZCONP65bA1+Iv4H3AcB2I40I4DBvw5ZERFPw=')
        self.assertEqual(request.params['SignatureMethod'], 'HmacSHA256')
        self.assertEqual(request.params['SignatureVersion'], '2')


class TestSigV3(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.credentials = botocore.credentials.Credentials(self.access_key,
                                                            self.secret_key)
        self.auth = botocore.auth.SigV3Auth(self.credentials)
        self.date_mock = mock.patch('botocore.auth.formatdate')
        self.formatdate = self.date_mock.start()
        self.formatdate.return_value = 'Thu, 17 Nov 2005 18:49:58 GMT'

    def tearDown(self):
        self.date_mock.stop()

    def test_signature_with_date_headers(self):
        request = AWSRequest()
        request.headers = {'Date': 'Thu, 17 Nov 2005 18:49:58 GMT'}
        request.url = 'https://route53.amazonaws.com'
        self.auth.add_auth(request)
        self.assertEqual(
            request.headers['X-Amzn-Authorization'],
            ('AWS3-HTTPS AWSAccessKeyId=access_key,Algorithm=HmacSHA256,'
             'Signature=M245fo86nVKI8rLpH4HgWs841sBTUKuwciiTpjMDgPs='))

    def test_resign_with_token(self):
        credentials = botocore.credentials.Credentials(
            access_key='foo', secret_key='bar', token='baz')
        auth = botocore.auth.SigV3Auth(credentials)
        request = AWSRequest()
        request.headers['Date'] = 'Thu, 17 Nov 2005 18:49:58 GMT'
        request.method = 'PUT'
        request.url = 'https://route53.amazonaws.com/'
        auth.add_auth(request)
        original_auth = request.headers['X-Amzn-Authorization']
        # Resigning the request shouldn't change the authorization
        # header.
        auth.add_auth(request)
        self.assertEqual(request.headers.get_all('X-Amzn-Authorization'),
                         [original_auth])


class TestS3SigV4Auth(BaseTestWithFixedDate):

    AuthClass = botocore.auth.S3SigV4Auth
    maxDiff = None

    def setUp(self):
        super(TestS3SigV4Auth, self).setUp()
        self.credentials = botocore.credentials.Credentials(
            access_key='foo', secret_key='bar', token='baz')
        self.auth = self.AuthClass(
            self.credentials, 'ec2', 'eu-central-1')
        self.request = AWSRequest(data=six.BytesIO(b"foo bar baz"))
        self.request.method = 'PUT'
        self.request.url = 'https://s3.eu-central-1.amazonaws.com/'

        self.client_config = mock.Mock()
        self.s3_config = {}
        self.client_config.s3 = self.s3_config

        self.request.context = {
            'client_config': self.client_config
        }

    def test_resign_with_content_hash(self):
        self.auth.add_auth(self.request)
        original_auth = self.request.headers['Authorization']

        self.auth.add_auth(self.request)
        self.assertEqual(self.request.headers.get_all('Authorization'),
                         [original_auth])

    def test_signature_is_not_normalized(self):
        request = AWSRequest()
        request.url = 'https://s3.amazonaws.com/bucket/foo/./bar/../bar'
        request.method = 'GET'
        credentials = botocore.credentials.Credentials('access_key',
                                                       'secret_key')
        auth = self.AuthClass(credentials, 's3', 'us-east-1')
        auth.add_auth(request)
        self.assertTrue(
            request.headers['Authorization'].startswith('AWS4-HMAC-SHA256'))

    def test_query_string_params_in_urls(self):
        if not hasattr(self.AuthClass, 'canonical_query_string'):
            raise unittest.SkipTest('%s does not expose interim steps' %
                                    self.AuthClass.__name__)

        request = AWSRequest()
        request.url = (
            'https://s3.amazonaws.com/bucket?'
            'marker=%C3%A4%C3%B6%C3%BC-01.txt&prefix'
        )
        request.data = {'Action': 'MyOperation'}
        request.method = 'GET'

        # Check that the canonical query string is correct formatting
        # by ensuring that query string paramters that are added to the
        # canonical query string are correctly formatted.
        cqs = self.auth.canonical_query_string(request)
        self.assertEqual('marker=%C3%A4%C3%B6%C3%BC-01.txt&prefix=', cqs)

    def _test_blacklist_header(self, header, value):
        request = AWSRequest()
        request.url = 'https://s3.amazonaws.com/bucket/foo'
        request.method = 'PUT'
        request.headers[header] = value
        credentials = botocore.credentials.Credentials('access_key',
                                                       'secret_key')
        auth = self.AuthClass(credentials, 's3', 'us-east-1')
        auth.add_auth(request)
        self.assertNotIn(header, request.headers['Authorization'])

    def test_blacklist_expect_headers(self):
        self._test_blacklist_header('expect', '100-continue')

    def test_blacklist_trace_id(self):
        self._test_blacklist_header('x-amzn-trace-id',
                                    'Root=foo;Parent=bar;Sampleid=1')

    def test_blacklist_headers(self):
        self._test_blacklist_header('user-agent', 'botocore/1.4.11')

    def test_uses_sha256_if_config_value_is_true(self):
        self.client_config.s3['payload_signing_enabled'] = True
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_does_not_use_sha256_if_config_value_is_false(self):
        self.client_config.s3['payload_signing_enabled'] = False
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_uses_sha256_if_md5_unset(self):
        self.request.context['has_streaming_input'] = True
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_uses_sha256_if_not_https(self):
        self.request.context['has_streaming_input'] = True
        self.request.headers.add_header('Content-MD5', 'foo')
        self.request.url = 'http://s3.amazonaws.com/bucket'
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_uses_sha256_if_not_streaming_upload(self):
        self.request.context['has_streaming_input'] = False
        self.request.headers.add_header('Content-MD5', 'foo')
        self.request.url = 'https://s3.amazonaws.com/bucket'
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_does_not_use_sha256_if_md5_set(self):
        self.request.context['has_streaming_input'] = True
        self.request.headers.add_header('Content-MD5', 'foo')
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_does_not_use_sha256_if_context_config_set(self):
        self.request.context['payload_signing_enabled'] = False
        self.request.headers.add_header('Content-MD5', 'foo')
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_sha256_if_context_set_on_http(self):
        self.request.context['payload_signing_enabled'] = False
        self.request.headers.add_header('Content-MD5', 'foo')
        self.request.url = 'http://s3.amazonaws.com/bucket'
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_sha256_if_context_set_without_md5(self):
        self.request.context['payload_signing_enabled'] = False
        self.request.url = 'https://s3.amazonaws.com/bucket'
        self.auth.add_auth(self.request)
        sha_header = self.request.headers['X-Amz-Content-SHA256']
        self.assertNotEqual(sha_header, 'UNSIGNED-PAYLOAD')


class TestSigV4(unittest.TestCase):
    def setUp(self):
        self.credentials = botocore.credentials.Credentials(
            access_key='foo', secret_key='bar')

    def create_signer(self, service_name='myservice', region='us-west-2'):
        auth = botocore.auth.SigV4Auth(
            self.credentials, service_name, region)
        return auth

    def test_canonical_query_string(self):
        request = AWSRequest()
        request.url = (
            'https://search-testdomain1-j67dwxlet67gf7ghwfmik2c67i.us-west-2.'
            'cloudsearch.amazonaws.com/'
            '2013-01-01/search?format=sdk&pretty=true&'
            'q.options=%7B%22defaultOperator%22%3A%20%22and%22%2C%20%22'
            'fields%22%3A%5B%22directors%5E10%22%5D%7D&q=George%20Lucas'
        )
        request.method = 'GET'
        auth = self.create_signer('cloudsearchdomain', 'us-west-2')
        actual = auth.canonical_query_string(request)
        # Here 'q' should come before 'q.options'.
        expected = ("format=sdk&pretty=true&q=George%20Lucas&q.options=%7B%22"
                    "defaultOperator%22%3A%20%22and%22%2C%20%22fields%22%3A%5B"
                    "%22directors%5E10%22%5D%7D")
        self.assertEqual(actual, expected)

    def test_thread_safe_timestamp(self):
        request = AWSRequest()
        request.url = (
            'https://search-testdomain1-j67dwxlet67gf7ghwfmik2c67i.us-west-2.'
            'cloudsearch.amazonaws.com/'
            '2013-01-01/search?format=sdk&pretty=true&'
            'q.options=%7B%22defaultOperator%22%3A%20%22and%22%2C%20%22'
            'fields%22%3A%5B%22directors%5E10%22%5D%7D&q=George%20Lucas'
        )
        request.method = 'GET'
        auth = self.create_signer('cloudsearchdomain', 'us-west-2')
        with mock.patch.object(
                botocore.auth.datetime, 'datetime',
                mock.Mock(wraps=datetime.datetime)) as mock_datetime:
            original_utcnow = datetime.datetime(2014, 1, 1, 0, 0)

            mock_datetime.utcnow.return_value = original_utcnow
            # Go through the add_auth process once. This will attach
            # a timestamp to the request at the beginning of auth.
            auth.add_auth(request)
            self.assertEqual(request.context['timestamp'], '20140101T000000Z')
            # Ensure the date is in the Authorization header
            self.assertIn('20140101', request.headers['Authorization'])
            # Now suppose the utc time becomes the next day all of a sudden
            mock_datetime.utcnow.return_value = datetime.datetime(
                2014, 1, 2, 0, 0)
            # Smaller methods like the canonical request and string_to_sign
            # should  have the timestamp attached to the request in their
            # body and not what the time is now mocked as. This is to ensure
            # there is no mismatching in timestamps when signing.
            cr = auth.canonical_request(request)
            self.assertIn('x-amz-date:20140101T000000Z', cr)
            self.assertNotIn('x-amz-date:20140102T000000Z', cr)

            sts = auth.string_to_sign(request, cr)
            self.assertIn('20140101T000000Z', sts)
            self.assertNotIn('20140102T000000Z', sts)

    def test_payload_is_binary_file(self):
        request = AWSRequest()
        request.data = six.BytesIO(u'\u2713'.encode('utf-8'))
        request.url = 'https://amazonaws.com'
        auth = self.create_signer()
        payload = auth.payload(request)
        self.assertEqual(
            payload,
            '1dabba21cdad44541f6b15796f8d22978fc7ea10c46aeceeeeb66c23b3ac7604')

    def test_payload_is_bytes_type(self):
        request = AWSRequest()
        request.data = u'\u2713'.encode('utf-8')
        request.url = 'https://amazonaws.com'
        auth = self.create_signer()
        payload = auth.payload(request)
        self.assertEqual(
            payload,
            '1dabba21cdad44541f6b15796f8d22978fc7ea10c46aeceeeeb66c23b3ac7604')

    def test_payload_not_signed_if_disabled_in_context(self):
        request = AWSRequest()
        request.data = u'\u2713'.encode('utf-8')
        request.url = 'https://amazonaws.com'
        request.context['payload_signing_enabled'] = False
        auth = self.create_signer()
        payload = auth.payload(request)
        self.assertEqual(payload, 'UNSIGNED-PAYLOAD')

    def test_content_sha256_set_if_payload_signing_disabled(self):
        request = AWSRequest()
        request.data = six.BytesIO(u'\u2713'.encode('utf-8'))
        request.url = 'https://amazonaws.com'
        request.context['payload_signing_enabled'] = False
        request.method = 'PUT'
        auth = self.create_signer()
        auth.add_auth(request)
        sha_header = request.headers['X-Amz-Content-SHA256']
        self.assertEqual(sha_header, 'UNSIGNED-PAYLOAD')

    def test_collapse_multiple_spaces(self):
        auth = self.create_signer()
        original = HTTPHeaders()
        original['foo'] = 'double  space'
        headers = auth.canonical_headers(original)
        self.assertEqual(headers, 'foo:double space')

    def test_trims_leading_trailing_spaces(self):
        auth = self.create_signer()
        original = HTTPHeaders()
        original['foo'] = '  leading  and  trailing  '
        headers = auth.canonical_headers(original)
        self.assertEqual(headers, 'foo:leading and trailing')

    def test_strips_http_default_port(self):
        request = AWSRequest()
        request.url = 'http://s3.us-west-2.amazonaws.com:80/'
        request.method = 'GET'
        auth = self.create_signer('s3', 'us-west-2')
        actual = auth.headers_to_sign(request)['host']
        expected = 's3.us-west-2.amazonaws.com'
        self.assertEqual(actual, expected)

    def test_strips_https_default_port(self):
        request = AWSRequest()
        request.url = 'https://s3.us-west-2.amazonaws.com:443/'
        request.method = 'GET'
        auth = self.create_signer('s3', 'us-west-2')
        actual = auth.headers_to_sign(request)['host']
        expected = 's3.us-west-2.amazonaws.com'
        self.assertEqual(actual, expected)

    def test_strips_http_auth(self):
        request = AWSRequest()
        request.url = 'https://username:password@s3.us-west-2.amazonaws.com/'
        request.method = 'GET'
        auth = self.create_signer('s3', 'us-west-2')
        actual = auth.headers_to_sign(request)['host']
        expected = 's3.us-west-2.amazonaws.com'
        self.assertEqual(actual, expected)

    def test_strips_default_port_and_http_auth(self):
        request = AWSRequest()
        request.url = 'http://username:password@s3.us-west-2.amazonaws.com:80/'
        request.method = 'GET'
        auth = self.create_signer('s3', 'us-west-2')
        actual = auth.headers_to_sign(request)['host']
        expected = 's3.us-west-2.amazonaws.com'
        self.assertEqual(actual, expected)


class TestSigV4Resign(BaseTestWithFixedDate):

    maxDiff = None
    AuthClass = botocore.auth.SigV4Auth

    def setUp(self):
        super(TestSigV4Resign, self).setUp()
        self.credentials = botocore.credentials.Credentials(
            access_key='foo', secret_key='bar', token='baz')
        self.auth = self.AuthClass(self.credentials, 'ec2', 'us-west-2')
        self.request = AWSRequest()
        self.request.method = 'PUT'
        self.request.url = 'https://ec2.amazonaws.com/'

    def test_resign_request_with_date(self):
        self.request.headers['Date'] = 'Thu, 17 Nov 2005 18:49:58 GMT'
        self.auth.add_auth(self.request)
        original_auth = self.request.headers['Authorization']

        self.auth.add_auth(self.request)
        self.assertEqual(self.request.headers.get_all('Authorization'),
                         [original_auth])

    def test_sigv4_without_date(self):
        self.auth.add_auth(self.request)
        original_auth = self.request.headers['Authorization']

        self.auth.add_auth(self.request)
        self.assertEqual(self.request.headers.get_all('Authorization'),
                         [original_auth])


class BasePresignTest(unittest.TestCase):
    def get_parsed_query_string(self, request):
        query_string_dict = parse_qs(urlsplit(request.url).query)
        # Also, parse_qs sets each value in the dict to be a list, but
        # because we know that we won't have repeated keys, we simplify
        # the dict and convert it back to a single value.
        for key in query_string_dict:
            query_string_dict[key] = query_string_dict[key][0]
        return query_string_dict


class TestSigV4Presign(BasePresignTest):

    maxDiff = None
    AuthClass = botocore.auth.SigV4QueryAuth

    def setUp(self):
        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.credentials = botocore.credentials.Credentials(self.access_key,
                                                            self.secret_key)
        self.service_name = 'myservice'
        self.region_name = 'myregion'
        self.auth = self.AuthClass(
            self.credentials, self.service_name, self.region_name, expires=60)
        self.datetime_patcher = mock.patch.object(
            botocore.auth.datetime, 'datetime',
            mock.Mock(wraps=datetime.datetime)
        )
        mocked_datetime = self.datetime_patcher.start()
        mocked_datetime.utcnow.return_value = datetime.datetime(
            2014, 1, 1, 0, 0)

    def tearDown(self):
        self.datetime_patcher.stop()

    def test_presign_no_params(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://ec2.us-east-1.amazonaws.com/'
        self.auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        self.assertEqual(
            query_string,
            {'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
             'X-Amz-Credential': ('access_key/20140101/myregion/'
                                  'myservice/aws4_request'),
             'X-Amz-Date': '20140101T000000Z',
             'X-Amz-Expires': '60',
             'X-Amz-Signature': ('c70e0bcdb4cd3ee324f71c78195445b878'
                                 '8315af0800bbbdbbb6d05a616fb84c'),
             'X-Amz-SignedHeaders': 'host'})

    def test_operation_params_before_auth_params(self):
        # The spec is picky about this.
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://ec2.us-east-1.amazonaws.com/?Action=MyOperation'
        self.auth.add_auth(request)
        # Verify auth params come after the existing params.
        self.assertIn(
            '?Action=MyOperation&X-Amz', request.url)

    def test_operation_params_before_auth_params_in_body(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://ec2.us-east-1.amazonaws.com/'
        request.data = {'Action': 'MyOperation'}
        self.auth.add_auth(request)
        # Same situation, the params from request.data come before the auth
        # params in the query string.
        self.assertIn(
            '?Action=MyOperation&X-Amz', request.url)

    def test_presign_with_spaces_in_param(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://ec2.us-east-1.amazonaws.com/'
        request.data = {'Action': 'MyOperation', 'Description': 'With Spaces'}
        self.auth.add_auth(request)
        # Verify we encode spaces as '%20, and we don't use '+'.
        self.assertIn('Description=With%20Spaces', request.url)

    def test_presign_with_empty_param_value(self):
        request = AWSRequest()
        request.method = 'POST'
        # actual URL format for creating a multipart upload
        request.url = 'https://s3.amazonaws.com/mybucket/mykey?uploads'
        self.auth.add_auth(request)
        # verify that uploads param is still in URL
        self.assertIn('uploads', request.url)

    def test_s3_sigv4_presign(self):
        auth = botocore.auth.S3SigV4QueryAuth(
            self.credentials, self.service_name, self.region_name, expires=60)
        request = AWSRequest()
        request.method = 'GET'
        request.url = (
            'https://s3.us-west-2.amazonaws.com/mybucket/keyname/.bar')
        auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        # We use a different payload:
        self.assertEqual(auth.payload(request), 'UNSIGNED-PAYLOAD')
        # which will result in a different X-Amz-Signature:
        self.assertEqual(
            query_string,
            {'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
             'X-Amz-Credential': ('access_key/20140101/myregion/'
                                  'myservice/aws4_request'),
             'X-Amz-Date': '20140101T000000Z',
             'X-Amz-Expires': '60',
             'X-Amz-Signature': ('ac1b8b9e47e8685c5c963d75e35e8741d55251'
                                 'cd955239cc1efad4dc7201db66'),
             'X-Amz-SignedHeaders': 'host'})

    def test_presign_with_security_token(self):
        self.credentials.token = 'security-token'
        auth = botocore.auth.S3SigV4QueryAuth(
            self.credentials, self.service_name, self.region_name, expires=60)
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://ec2.us-east-1.amazonaws.com/'
        auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        self.assertEqual(
            query_string['X-Amz-Security-Token'], 'security-token')

    def test_presign_where_body_is_json_bytes(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://myservice.us-east-1.amazonaws.com/'
        request.data = b'{"Param": "value"}'
        self.auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        expected_query_string = {
            'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
            'X-Amz-Credential': (
                'access_key/20140101/myregion/myservice/aws4_request'),
            'X-Amz-Expires': '60',
            'X-Amz-Date': '20140101T000000Z',
            'X-Amz-Signature': (
                '8e1d372d168d532313ce6df8f64a7dc51d'
                'e6f312a9cfba6e5b345d8a771e839c'),
            'X-Amz-SignedHeaders': 'host',
            'Param': 'value'
        }
        self.assertEqual(query_string, expected_query_string)

    def test_presign_where_body_is_json_string(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://myservice.us-east-1.amazonaws.com/'
        request.data = '{"Param": "value"}'
        self.auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        expected_query_string = {
            'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
            'X-Amz-Credential': (
                'access_key/20140101/myregion/myservice/aws4_request'),
            'X-Amz-Expires': '60',
            'X-Amz-Date': '20140101T000000Z',
            'X-Amz-Signature': (
                '8e1d372d168d532313ce6df8f64a7dc51d'
                'e6f312a9cfba6e5b345d8a771e839c'),
            'X-Amz-SignedHeaders': 'host',
            'Param': 'value'
        }
        self.assertEqual(query_string, expected_query_string)

    def test_presign_content_type_form_encoded_not_signed(self):
        request = AWSRequest()
        request.method = 'GET'
        request.url = 'https://myservice.us-east-1.amazonaws.com/'
        request.headers['Content-Type'] = (
            'application/x-www-form-urlencoded; charset=utf-8'
        )
        self.auth.add_auth(request)
        query_string = self.get_parsed_query_string(request)
        signed_headers = query_string.get('X-Amz-SignedHeaders')
        self.assertNotIn('content-type', signed_headers)


class BaseS3PresignPostTest(unittest.TestCase):
    def setUp(self):
        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.credentials = botocore.credentials.Credentials(
            self.access_key, self.secret_key)

        self.service_name = 'myservice'
        self.region_name = 'myregion'

        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.policy = {
            "expiration": "2007-12-01T12:00:00.000Z",
            "conditions": [
                {"acl": "public-read"},
                {"bucket": self.bucket},
                ["starts-with", "$key", self.key],
            ]
        }
        self.fields = {
            'key': self.key,
            'acl': 'public-read',
        }

        self.request = AWSRequest()
        self.request.url = 'https://s3.amazonaws.com/%s' % self.bucket
        self.request.method = 'POST'

        self.request.context['s3-presign-post-fields'] = self.fields
        self.request.context['s3-presign-post-policy'] = self.policy


class TestS3SigV4Post(BaseS3PresignPostTest):
    def setUp(self):
        super(TestS3SigV4Post, self).setUp()
        self.auth = botocore.auth.S3SigV4PostAuth(
            self.credentials, self.service_name, self.region_name)
        self.datetime_patcher = mock.patch.object(
            botocore.auth.datetime, 'datetime',
            mock.Mock(wraps=datetime.datetime)
        )
        mocked_datetime = self.datetime_patcher.start()
        mocked_datetime.utcnow.return_value = datetime.datetime(
            2014, 1, 1, 0, 0)

    def tearDown(self):
        self.datetime_patcher.stop()

    def test_presign_post(self):
        self.auth.add_auth(self.request)
        result_fields = self.request.context['s3-presign-post-fields']
        self.assertEqual(result_fields['x-amz-algorithm'], 'AWS4-HMAC-SHA256')
        self.assertEqual(
            result_fields['x-amz-credential'],
            'access_key/20140101/myregion/myservice/aws4_request')
        self.assertEqual(
            result_fields['x-amz-date'],
            '20140101T000000Z')

        result_policy = json.loads(base64.b64decode(
            result_fields['policy']).decode('utf-8'))
        self.assertEqual(result_policy['expiration'],
                         '2007-12-01T12:00:00.000Z')
        self.assertEqual(
            result_policy['conditions'],
            [{"acl": "public-read"}, {"bucket": "mybucket"},
             ["starts-with", "$key", "mykey"],
             {"x-amz-algorithm": "AWS4-HMAC-SHA256"},
             {"x-amz-credential":
              "access_key/20140101/myregion/myservice/aws4_request"},
             {"x-amz-date": "20140101T000000Z"}])
        self.assertIn('x-amz-signature', result_fields)

    def test_presign_post_with_security_token(self):
        self.credentials.token = 'my-token'
        self.auth = botocore.auth.S3SigV4PostAuth(
            self.credentials, self.service_name, self.region_name)
        self.auth.add_auth(self.request)
        result_fields = self.request.context['s3-presign-post-fields']
        self.assertEqual(result_fields['x-amz-security-token'], 'my-token')

    def test_empty_fields_and_policy(self):
        self.request = AWSRequest()
        self.request.url = 'https://s3.amazonaws.com/%s' % self.bucket
        self.request.method = 'POST'
        self.auth.add_auth(self.request)

        result_fields = self.request.context['s3-presign-post-fields']
        self.assertEqual(result_fields['x-amz-algorithm'], 'AWS4-HMAC-SHA256')
        self.assertEqual(
            result_fields['x-amz-credential'],
            'access_key/20140101/myregion/myservice/aws4_request')
        self.assertEqual(
            result_fields['x-amz-date'],
            '20140101T000000Z')

        result_policy = json.loads(base64.b64decode(
            result_fields['policy']).decode('utf-8'))
        self.assertEqual(
            result_policy['conditions'],
            [{"x-amz-algorithm": "AWS4-HMAC-SHA256"},
             {"x-amz-credential":
              "access_key/20140101/myregion/myservice/aws4_request"},
             {"x-amz-date": "20140101T000000Z"}])
        self.assertIn('x-amz-signature', result_fields)
