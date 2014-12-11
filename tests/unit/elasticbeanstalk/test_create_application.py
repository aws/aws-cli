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
from awscli.testutils import BaseAWSCommandParamsTest, unittest
import sys
from awscli.compat import six


class TestUpdateConfigurationTemplate(BaseAWSCommandParamsTest):

    prefix = 'elasticbeanstalk create-application'

    def test_ascii(self):
        cmdline = self.prefix
        cmdline += ' --application-name FooBar'
        result = {'ApplicationName': 'FooBar',}
        self.assert_params_for_cmd(cmdline, result)

    @unittest.skipIf(
        six.PY3, 'Unicode cmd line test only is relevant to python2.')
    def test_py2_bytestring_unicode(self):
        # In Python2, sys.argv is a list of bytestrings that are encoded
        # in whatever encoding the terminal uses.  We have an extra step
        # where we need to decode the bytestring into unicode.  In
        # python3, sys.argv is a list of unicode objects so this test
        # doesn't make sense for python3.
        cmdline = self.prefix
        app_name = u'\u2713'
        cmdline += u' --application-name %s' % app_name
        encoding = getattr(sys.stdin, 'encoding')
        if encoding is None:
            encoding = 'utf-8'
        cmdline = cmdline.encode(encoding)
        result = {'ApplicationName': u'\u2713',}
        self.assert_params_for_cmd(cmdline, result)
