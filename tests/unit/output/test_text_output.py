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
from tests.unit import BaseAWSCommandParamsTest
import json
import os
import sys
import re

from six.moves import cStringIO
import mock


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
