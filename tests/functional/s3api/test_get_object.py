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
from awscli.testutils import BaseAWSCommandParamsTest
import os
import re

from awscli.compat import six

import awscli.clidriver


class TestGetObject(BaseAWSCommandParamsTest):

    prefix = 's3api get-object'

    def setUp(self):
        super(TestGetObject, self).setUp()
        self.parsed_response = {'Body': six.StringIO()}

    def remove_file_if_exists(self, filename):
        if os.path.isfile(filename):
            os.remove(filename)

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' outfile'
        self.addCleanup(self.remove_file_if_exists, 'outfile')
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                              'Key': 'mykey'})

    def test_range(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --range bytes=0-499'
        cmdline += ' outfile'
        self.addCleanup(self.remove_file_if_exists, 'outfile')
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                              'Key': 'mykey',
                                              'Range': 'bytes=0-499'})

    def test_response_headers(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' --response-cache-control No-cache'
        cmdline += ' --response-content-encoding x-gzip'
        cmdline += ' outfile'
        self.addCleanup(self.remove_file_if_exists, 'outfile')
        self.assert_params_for_cmd(
            cmdline, {
                'Bucket': 'mybucket', 'Key': 'mykey',
                'ResponseCacheControl': 'No-cache',
                'ResponseContentEncoding': 'x-gzip'
            }
        )

    def test_streaming_output_arg_with_error_response(self):
        # Checking that the StreamingOutputArg handles the
        # case where it's passed an error body.  Previously
        # it would propogate a KeyError so we want to ensure
        # this case is handled.
        self.parsed_response = {
            'Error': {
                'Code': 'AuthError', 'Message': 'SomeError'
            }
        }
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --key mykey'
        cmdline += ' outfile'
        self.addCleanup(self.remove_file_if_exists, 'outfile')
        self.assert_params_for_cmd(
            cmdline, {'Bucket': 'mybucket', 'Key': 'mykey'})


if __name__ == "__main__":
    unittest.main()
