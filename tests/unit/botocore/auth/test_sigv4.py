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

"""Signature Version 4 test suite.

AWS provides a test suite for signature version 4:

https://github.com/awslabs/aws-c-auth/tree/v0.3.15/tests/aws-sig-v4-test-suite

This module contains logic to run these tests.  The test files were
placed in ./aws4_testsuite, and we're using those to dynamically
generate testcases based on these files.

"""

import datetime
import io
import logging
import os
import re
from http.server import BaseHTTPRequestHandler

import pytest

import botocore.auth
from botocore.awsrequest import AWSRequest
from botocore.compat import parse_qsl, urlsplit
from botocore.credentials import Credentials
from tests import FreezeTime

SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
ACCESS_KEY = 'AKIDEXAMPLE'
DATE = datetime.datetime(2015, 8, 30, 12, 36, 0, tzinfo=datetime.timezone.utc)
SERVICE = 'service'
REGION = 'us-east-1'

TESTSUITE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'aws4_testsuite'
)

# The following tests are not run.  Each test has a comment as
# to why the test is being ignored.
TESTS_TO_IGNORE = [
    # Bad request-line syntax, python's HTTP parser chokes on this.
    'normalize-path/get-space',
    # Multiple query params of the same key not supported by the SDKs.
    'get-vanilla-query-order-key-case',
    'get-vanilla-query-order-key',
    'get-vanilla-query-order-value',
]

log = logging.getLogger(__name__)


class RawHTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, raw_request):
        if isinstance(raw_request, str):
            raw_request = raw_request.encode('utf-8')
        self.rfile = io.BytesIO(raw_request)
        self.raw_requestline = self.rfile.readline()
        self.error_code = None
        self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


def generate_test_cases():
    for dirpath, dirnames, filenames in os.walk(TESTSUITE_DIR):
        if not any(f.endswith('.req') for f in filenames):
            continue

        test_case = os.path.relpath(dirpath, TESTSUITE_DIR).replace(
            os.sep, '/'
        )
        if test_case in TESTS_TO_IGNORE:
            log.debug("Skipping test: %s", test_case)
            continue

        yield test_case


@pytest.mark.parametrize("test_case", generate_test_cases())
@FreezeTime(module=botocore.auth.datetime, date=DATE)
def test_signature_version_4(test_case):
    _test_signature_version_4(test_case)


def create_request_from_raw_request(raw_request):
    request = AWSRequest()
    raw = RawHTTPRequest(raw_request)
    if raw.error_code is not None:
        raise Exception(raw.error_message)
    request.method = raw.command
    datetime_now = DATE
    request.context['timestamp'] = datetime_now.strftime('%Y%m%dT%H%M%SZ')
    for key, val in raw.headers.items():
        request.headers[key] = val
    request.data = raw.rfile.read()
    host = raw.headers.get('host', '')
    # For whatever reason, the BaseHTTPRequestHandler encodes
    # the first line of the response as 'iso-8859-1',
    # so we need decode this into utf-8.
    if isinstance(raw.path, str):
        raw.path = raw.path.encode('iso-8859-1').decode('utf-8')
    url = f'https://{host}{raw.path}'
    if '?' in url:
        split_url = urlsplit(url)
        params = dict(parse_qsl(split_url.query))
        request.url = split_url.path
        request.params = params
    else:
        request.url = url
    return request


def _test_signature_version_4(test_case):
    test_case = SignatureTestCase(test_case)
    request = create_request_from_raw_request(test_case.raw_request)

    auth = botocore.auth.SigV4Auth(test_case.credentials, SERVICE, REGION)
    actual_canonical_request = auth.canonical_request(request)
    actual_string_to_sign = auth.string_to_sign(
        request, actual_canonical_request
    )
    auth.add_auth(request)
    actual_auth_header = request.headers['Authorization']

    # Some stuff only works right when you go through auth.add_auth()
    # So don't assert the interim steps unless the end result was wrong.
    if actual_auth_header != test_case.authorization_header:
        assert_equal(
            actual_canonical_request,
            test_case.canonical_request,
            test_case.raw_request,
            'canonical_request',
        )

        assert_equal(
            actual_string_to_sign,
            test_case.string_to_sign,
            test_case.raw_request,
            'string_to_sign',
        )

        assert_equal(
            actual_auth_header,
            test_case.authorization_header,
            test_case.raw_request,
            'authheader',
        )


def assert_equal(actual, expected, raw_request, part):
    if actual != expected:
        message = f"The {part} did not match"
        message += f"\nACTUAL:{actual!r} !=\nEXPECT:{expected!r}"
        message += f'\nThe raw request was:\n{raw_request}'
        raise AssertionError(message)


class SignatureTestCase:
    def __init__(self, test_case):
        filepath = os.path.join(
            TESTSUITE_DIR, test_case, os.path.basename(test_case)
        )
        self.raw_request = open(filepath + '.req', encoding='utf-8').read()
        self.canonical_request = (
            open(filepath + '.creq', encoding='utf-8').read().replace('\r', '')
        )
        self.string_to_sign = (
            open(filepath + '.sts', encoding='utf-8').read().replace('\r', '')
        )
        self.authorization_header = (
            open(filepath + '.authz', encoding='utf-8')
            .read()
            .replace('\r', '')
        )
        self.signed_request = open(filepath + '.sreq', encoding='utf-8').read()

        token_pattern = r'^x-amz-security-token:(.*)$'
        token_match = re.search(
            token_pattern, self.canonical_request, re.MULTILINE
        )
        token = token_match.group(1) if token_match else None
        self.credentials = Credentials(ACCESS_KEY, SECRET_KEY, token)
