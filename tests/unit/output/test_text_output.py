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
from awscli.testutils import unittest
import json
import os
import sys
import re
import locale

from awscli.compat import six
from six.moves import cStringIO
import mock

from awscli.formatter import Formatter


class TestListUsers(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestListUsers, self).setUp()
        self.first_parsed_response = {
            'Users': [
                {
                    "UserName": "testuser-50",
                    "Path": "/",
                    "CreateDate": "2013-02-12T19:08:52Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::12345:user/testuser1"
                },
            ],
            'Groups': []
        }
        self.second_parsed_response = {
            'Users': [
                {
                    "UserName": "testuser-51",
                    "Path": "/",
                    "CreateDate": "2012-10-14T23:53:39Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::123456:user/testuser2"
                },
            ],
            'Groups': []
        }

    def patch_make_request(self):
        make_request_patch = self.make_request_patch.start()
        make_request_patch.side_effect = [
            (self.http_response, self.first_parsed_response),
            (self.http_response, self.second_parsed_response),
        ]
        self.make_request_is_patched = True

    def test_text_response(self):
        output = self.run_cmd('iam list-users --output text', expected_rc=0)[0]
        self.assertEqual(
            output,
            ('USERS\tarn:aws:iam::12345:user/testuser1\t2013-02-12T19:08:52Z\t'
             '/\tEXAMPLEUSERID\ttestuser-50\n'))

        # Test something with a jmespath expression.
        output = self.run_cmd(
            'rds describe-engine-default-parameters ' \
            '--db-parameter-group-family mysql5.1 --output text',
            expected_rc=0)[0]
        self.assertEqual(
            output,
            'ENGINEDEFAULTS\tNone\n')


class CustomFormatter(Formatter):
    def __call__(self, operation, response, stream=None):
        self.stream = self._get_default_stream()


class TestDefaultStream(BaseAWSCommandParamsTest):
    @unittest.skipIf(six.PY3, "Text writer only vaild on py3.")
    def test_default_stream_with_table_output(self):
        formatter = CustomFormatter(None)
        stream = cStringIO()
        with mock.patch('sys.stdout', stream):
            formatter(None, None)
            formatter.stream.write(u'\u00e9')
        # Ensure the unicode data is written as UTF-8 by default.
        self.assertEqual(
            formatter.stream.getvalue(),
            u'\u00e9'.encode(locale.getpreferredencoding()))
