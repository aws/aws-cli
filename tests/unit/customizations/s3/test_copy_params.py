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
        httpretty.register_uri(httpretty.GET, re.compile('.*'), body='',
                               status_code=200)
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
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_sse(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --sse'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-server-side-encryption': 'AES256'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_storage_class(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --storage-class REDUCED_REDUNDANCY'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-storage-class': 'REDUCED_REDUNDANCY'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_website_redirect(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --website-redirect /foobar'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-website-redirect-location': '/foobar'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_acl(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --acl public-read'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-acl': 'public-read'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_content_params(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --content-encoding x-gzip'
        cmdline += ' --content-language piglatin'
        cmdline += ' --cache-control max-age=3600,must-revalidate'
        cmdline += ' --content-disposition attachment;filename="fname.ext"'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'Content-Encoding': 'x-gzip',
                              'Content-Language': 'piglatin',
                              'Content-Disposition': 'attachment;filename="fname.ext"',
                              'Cache-Control': 'max-age=3600,must-revalidate'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_grants(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read=bob'
        cmdline += ' full=alice'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'x-amz-grant-full-control': 'alice',
                              'x-amz-grant-read': 'bob'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)

    def test_grants_bad(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read:bob'
        self.assert_params_for_cmd(cmdline, expected_rc=1)

    def test_content_type(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --content-type text/xml'
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'Content-Type': 'text/xml'}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertIsInstance(self.payload.getvalue(), file_type)


if __name__ == "__main__":
    unittest.main()

