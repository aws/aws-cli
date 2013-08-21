#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest
import botocore.auth
import botocore.credentials
from botocore.compat import HTTPHeaders
import six

try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit

CS1 = ("PUT\nc8fdb181845a4ca6b8fec737b3581d76\ntext/html\n"
       "Thu, 17 Nov 2005 18:49:58 GMT\nx-amz-magic:abracadabra\n"
       "x-amz-meta-author:foo@bar.com\n/quotes/nelson")
SIG1 = 'jZNOcbfWmD/A/f3hSvVzXZjM2HU='


class TestHMACV1(unittest.TestCase):

    def setUp(self):
        access_key = '44CF9590006BF252F707'
        secret_key = 'OtxrzxIsfpFjA7SwPzILwy8Bw21TLhquhboDYROV'
        self.credentials = botocore.credentials.Credentials(access_key,
                                                            secret_key)
        self.hmacv1 = botocore.auth.HmacV1Auth(self.credentials, None, None)

    def test_put(self):
        headers = {'Date': 'Thu, 17 Nov 2005 18:49:58 GMT',
                   'Content-Md5': 'c8fdb181845a4ca6b8fec737b3581d76',
                   'Content-Type': 'text/html',
                   'X-Amz-Meta-Author': 'foo@bar.com',
                   'X-Amz-Magic': 'abracadabra'}
        http_headers = HTTPHeaders.from_dict(headers)
        split = urlsplit('/quotes/nelson')
        cs = self.hmacv1.canonical_string('PUT', split, http_headers)
        assert cs == CS1
        sig = self.hmacv1.get_signature('PUT', split, http_headers)
        assert sig == SIG1

    def test_duplicate_headers(self):
        pairs = [('Date', 'Thu, 17 Nov 2005 18:49:58 GMT'),
                 ('Content-Md5', 'c8fdb181845a4ca6b8fec737b3581d76'),
                 ('Content-Type', 'text/html'),
                 ('X-Amz-Meta-Author', 'bar@baz.com'),
                 ('X-Amz-Meta-Author', 'foo@bar.com'),
                 ('X-Amz-Magic', 'abracadabra')]

        http_headers = HTTPHeaders.from_pairs(pairs)
        split = urlsplit('/quotes/nelson')
        sig = self.hmacv1.get_signature('PUT', split, http_headers)
        self.assertEqual(sig, 'kIdMxyiYB+F+83zYGR6sSb3ICcE=')

    def test_query_string(self):
        split = urlsplit('/quotes/nelson?uploads')
        pairs = [('Date', 'Thu, 17 Nov 2005 18:49:58 GMT'),]
        sig = self.hmacv1.get_signature('PUT', split,
                                        HTTPHeaders.from_pairs(pairs))
        self.assertEqual(sig, 'P7pBz3Z4p3GxysRSJ/gR8nk7D4o=')

    def test_bucket_operations(self):
        # Check that the standard operations on buckets that are
        # specified as query strings end up in the canonical resource.
        operations = ('acl', 'cors', 'lifecycle', 'policy',
                      'notification', 'logging', 'tagging',
                      'requestPayment', 'versioning', 'website')
        for operation in operations:
            url = '/quotes?%s' % operation
            split = urlsplit(url)
            cr = self.hmacv1.canonical_resource(split)
            self.assertEqual(cr, '/quotes?%s' % operation)
        
