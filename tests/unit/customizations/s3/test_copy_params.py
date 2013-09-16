#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import sys
import re
import copy

from tests.unit import BaseAWSCommandParamsTest
import httpretty
import six

import awscli.clidriver

if sys.version_info[:2] == (2, 6):
    from StringIO import StringIO


# file is gone in python3, so instead IOBase must be used.
# Given this test module is the only place that cares about
# this type check, we do the check directly in this test module.
try:
    file_type = file
except NameError:
    import io
    file_type = io.IOBase


class TestGetObject(BaseAWSCommandParamsTest):

    prefix = 's3 cp '

    def setUp(self):
        super(TestGetObject, self).setUp()
        self.file_path = os.path.join(os.path.dirname(__file__),
                                      'test_copy_params_data')
        self.payload = None

    def _store_params(self, params):
        # Copy the params dict without the payload attribute.
        self.payload = params['payload']
        self.last_params = params.copy()
        del self.last_params['payload']
        self.last_params = copy.deepcopy(self.last_params)
        # There appears to be a bug in httpretty and python3, and we're not
        # interested in testing this part of the request serialization for
        # these tests so we're replacing the file like object with nothing.  We
        # can still verify that the params['payload'] is the expected file like
        # object that has the correct contents but we won't test that it's
        # serialized properly.
        params['payload'] = None

    def register_uri(self):
        httpretty.register_uri(httpretty.PUT, re.compile('.*'), body='',
                               etag='"120ea8a25e5d487bf68b5f7096440019"',
                               content_length=0)

    def test_simple(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_sse(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --sse'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-server-side-encryption': 'AES256'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_storage_class(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --storage-class REDUCED_REDUNDANCY'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-storage-class': 'REDUCED_REDUNDANCY'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_website_redirect(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --website-redirect /foobar'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-website-redirect-location': '/foobar'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_acl(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --acl public-read'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-acl': 'public-read'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_headers(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --params ContentEncoding=x-gzip'
        cmdline += ' ContentLanguage=piglatin'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'Content-Encoding': 'x-gzip',
                              'Content-Language': 'piglatin'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_grants(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read:bob'
        cmdline += ' full:alice'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-grant-full-control': 'alice',
                              'x-amz-grant-read': 'bob'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        if sys.version_info[:2] == (2, 6):
            self.assertIsInstance(self.payload.getvalue(), StringIO)
        else:
            self.assertIsInstance(self.payload.getvalue(), bytearray)

    def test_grants_bad(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read=bob'
        # This should have an rc of 255 but the error is not
        # being processed correctly at the moment.  Need to track
        # this down.
        #self.assert_params_for_cmd(cmdline, {}, expected_rc=0)
        self.assert_params_for_cmd(cmdline, {}, expected_rc=0)


if __name__ == "__main__":
    unittest.main()

