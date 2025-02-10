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
import re
import copy

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator

import awscli.clidriver

# file is gone in python3, so instead IOBase must be used.
# Given this test module is the only place that cares about
# this type check, we do the check directly in this test module.
try:
    file_type = file
except NameError:
    import io
    file_type = io.IOBase


class TestPutObject(BaseAWSCommandParamsTest):

    maxDiff = None
    prefix = 's3api put-object'

    def setUp(self):
        super(TestPutObject, self).setUp()
        self.file_path = os.path.join(os.path.dirname(__file__),
                                      'test_put_object_data')
        self.files = FileCreator()

    def tearDown(self):
        super(TestPutObject, self).tearDown()
        self.files.remove_all()

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --body %s' % self.file_path
        result = {'uri_params': {'Bucket': 'mybucket',
                                 'Key': 'mykey'},
                  'headers': {'Expect': '100-continue'}}
        expected = {
            'Bucket': 'mybucket',
            'Key': 'mykey'
        }
        self.assert_params_for_cmd(cmdline, expected, ignore_params=['Body'])
        self.assertEqual(self.last_kwargs['Body'].name, self.file_path)

    def test_headers(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --body %s' % self.file_path
        cmdline += ' --acl public-read'
        cmdline += ' --content-encoding x-gzip'
        cmdline += ' --content-type text/plain'
        expected = {
            'ACL': 'public-read',
            'Bucket': 'mybucket',
            'ContentEncoding': 'x-gzip',
            'ContentType': 'text/plain',
            'Key': 'mykey'
        }
        self.assert_params_for_cmd(cmdline, expected, ignore_params=['Body'])
        self.assertEqual(self.last_kwargs['Body'].name, self.file_path)

    def test_website_redirect(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --acl public-read'
        cmdline += ' --website-redirect-location http://www.example.com/'
        expected = {
            'ACL': 'public-read',
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'WebsiteRedirectLocation': 'http://www.example.com/'
        }
        self.assert_params_for_cmd(cmdline, expected)

    def test_sse_key_with_binary_file(self):
        # Create contents that do not get mapped to ascii
        contents = b'\xc2'
        filename = self.files.create_file('key', contents, mode='wb')
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --sse-customer-algorithm AES256'
        cmdline += ' --sse-customer-key fileb://%s' % filename
        expected = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'SSECustomerAlgorithm': 'AES256',
            'SSECustomerKey': 'wg==',  # Note the key gets base64 encoded.
            'SSECustomerKeyMD5': 'ZGXa0dMXUr4/MoPo9w/u9w=='
        }
        self.assert_params_for_cmd(cmdline, expected)


if __name__ == "__main__":
    unittest.main()
