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
"""Signature Version 4 test suite.

AWS provides a test suite for signature version 4:

    http://docs.aws.amazon.com/general/latest/gr/signature-v4-test-suite.html

This module contains logic to run these tests.  The test files were
placed in ./aws4_testsuite, and we're using nose's test generators to
dynamically generate testcases based on these files.

"""
import os
import logging
from six import BytesIO
from six.moves import BaseHTTPServer
import six

import nose.tools as t
from nose import with_setup

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

try:
    from urllib.parse import urlsplit
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import urlsplit
    from urlparse import parse_qsl


CREDENTIAL_SCOPE = "KEYNAME/20110909/us-west-1/s3/aws4_request"
SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
ACCESS_KEY = 'AKIDEXAMPLE'
DATE_STRING = 'Mon, 09 Sep 2011 23:36:00 GMT'
TIMESTAMP = '20110909T233600Z'

TESTSUITE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'aws4_testsuite')

# The following tests are not run.  Each test has a comment as
# to why the test is being ignored.
TESTS_TO_IGNORE = [
    # Bad POST syntax, python's HTTP parser chokes on this.
    'post-vanilla-query-space',
    # Bad POST syntax, python's HTTP parser chokes on this.
    'post-vanilla-query-nonunreserved',
    # Multiple query params of the same key not supported by
    # the SDKs.
    'get-vanilla-query-order-key-case',
    # Multiple query params of the same key not supported by
    # the SDKs.
    'get-vanilla-query-order-value',
]
if not six.PY3:
    TESTS_TO_IGNORE += [
        # NO support
        'get-header-key-duplicate',
        'get-header-value-order',
    ]

log = logging.getLogger(__name__)


class RawHTTPRequest(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, raw_request):
        if isinstance(raw_request, six.text_type):
            raw_request = raw_request.encode('utf-8')
        self.rfile = BytesIO(raw_request)
        self.raw_requestline = self.rfile.readline()
        self.error_code = None
        self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


def test_generator():
    for test_case in set(os.path.splitext(i)[0]
                         for i in os.listdir(TESTSUITE_DIR)):
        if test_case in TESTS_TO_IGNORE:
            log.debug("Skipping test: %s", test_case)
            continue
        yield (_test_signature_version_4, test_case)


def create_request_from_raw_request(raw_request):
    raw_request = raw_request.replace('http/1.1', 'HTTP/1.1')
    request = AWSRequest()
    raw = RawHTTPRequest(raw_request)
    if raw.error_code is not None:
        raise Exception(raw.error_message)
    request.method = raw.command
    for key, val in raw.headers.items():
        request.headers[key] = val
    request.data = raw.rfile.read().decode('utf-8')
    host = raw.headers.get('host', '')
    # For whatever reason, the BaseHTTPRequestHandler encodes
    # the first line of the response as 'iso-8859-1',
    # so we need decode this into utf-8.
    if isinstance(raw.path, six.text_type):
        raw.path = raw.path.encode('iso-8859-1').decode('utf-8')
    url = 'https://%s%s' % (host, raw.path)
    if '?' in url:
        split_url = urlsplit(url)
        params = dict(parse_qsl(split_url.query))
        request.url = split_url.path
        request.params = params
    else:
        request.url = url
    return request


def _test_signature_version_4(test_case):
    test_case = _SignatureTestCase(test_case)
    request = create_request_from_raw_request(test_case.raw_request)

    auth = SigV4Auth(test_case.credentials, 'host', 'us-east-1')
    auth.timestamp = TIMESTAMP

    actual_canonical_request = auth.canonical_request(request)
    assert_equal(actual_canonical_request, test_case.canonical_request,
                 test_case.raw_request, 'canonical_request')

    actual_string_to_sign = auth.string_to_sign(request,
                                                actual_canonical_request)
    assert_equal(actual_string_to_sign, test_case.string_to_sign,
                 test_case.raw_request, 'string_to_sign')

    auth.add_auth(request)
    actual_auth_header = request.headers['Authorization']
    assert_equal(actual_auth_header, test_case.authorization_header,
                 test_case.raw_request, 'authheader')


def assert_equal(actual, expected, raw_request, part):
    if actual != expected:
        message = "The %s did not match" % part
        message += "\nACTUAL:%r !=\nEXPECT:%r" % (actual, expected)
        message += '\nThe raw request was:\n%s' % raw_request
        raise AssertionError(message)


class _SignatureTestCase(object):
    def __init__(self, test_case):
        p = os.path.join
        self.raw_request = open(p(TESTSUITE_DIR, test_case + '.req')).read()
        self.canonical_request = open(
            p(TESTSUITE_DIR, test_case + '.creq')).read().replace('\r', '')
        self.string_to_sign = open(
            p(TESTSUITE_DIR, test_case + '.sts')).read().replace('\r', '')
        self.authorization_header = open(
            p(TESTSUITE_DIR, test_case + '.authz')).read().replace('\r', '')
        self.signed_request = open(p(TESTSUITE_DIR, test_case + '.sreq')).read()

        self.credentials = Credentials(ACCESS_KEY, SECRET_KEY)
