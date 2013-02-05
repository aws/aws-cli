# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import six

try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit

import botocore.auth
import botocore.credentials
from botocore.awsrequest import AWSRequest


class TestSignatureVersion3(unittest.TestCase):

    def setUp(self):
        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.credentials = botocore.credentials.Credentials(self.access_key,
                                                            self.secret_key)
        self.auth = botocore.auth.SigV3Auth(self.credentials, None, None)

    def test_signature_with_date_headers(self):
        request = AWSRequest()
        request.headers = {'Date': 'Thu, 17 Nov 2005 18:49:58 GMT'}
        request.url = 'https://route53.amazonaws.com'
        self.auth.add_auth(request)
        self.assertEqual(
            request.headers['X-Amzn-Authorization'],
            ('AWS3-HTTPS AWSAccessKeyId=access_key,Algorithm=HmacSHA256,'
             'Signature=M245fo86nVKI8rLpH4HgWs841sBTUKuwciiTpjMDgPs='))
