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
from tests import unittest
import awscli.clidriver

# file is gone in python3, so instead IOBase must be used.
# Given this test module is the only place that cares about
# this type check, we do the check directly in this test module.
try:
    file_type = file
except NameError:
    import io
    file_type = io.IOBase


class TestGetObject(unittest.TestCase):

    def setUp(self):
        self.driver = awscli.clidriver.CLIDriver()
        self.prefix = 'aws s3 put-object'
        self.file_path = os.path.join(os.path.dirname(__file__),
                                      'test_put_object_data')

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --body %s' % self.file_path
        uri_params = {'Bucket': 'mybucket',
                      'Key': 'mykey'}
        headers = {}
        params = self.driver.test(cmdline)
        self.assertEqual(params['uri_params'], uri_params)
        self.assertEqual(params['headers'], headers)
        self.assertIsInstance(params['payload'], file_type)

    def test_headers(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --body %s' % self.file_path
        cmdline += ' --acl public-read'
        cmdline += ' --content-encoding x-gzip'
        cmdline += ' --content-type text/plain'
        uri_params = {'Bucket': 'mybucket',
                      'Key': 'mykey'}
        headers = {'x-amz-acl': 'public-read',
                   'Content-Encoding': 'x-gzip',
                   'Content-Type': 'text/plain'}
        params = self.driver.test(cmdline)
        self.assertEqual(params['uri_params'], uri_params)
        self.assertEqual(params['headers'], headers)
        # Not sure how best to check if the payload contains a file object.
        # In Python 2.x, this would be of type file but in Python3.x
        # it is an instance of io.IOBase.  I'm just going to check to
        # see if it has a read method.
        self.assertTrue(hasattr(params['payload'], 'read'))


if __name__ == "__main__":
    unittest.main()
