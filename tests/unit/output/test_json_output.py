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


class TestGetPasswordData(BaseAWSCommandParamsTest):

    prefix = 'iam add-user-to-group '

    def test_empty_response_prints_nothing(self):
        captured = cStringIO()
        # This is the default response, but we want to be explicit
        # that we're returning an empty dict.
        self.parsed_response = {}
        args = ' --group-name foo --user-name bar'
        cmdline = self.prefix + args
        result = {'GroupName': 'foo', 'UserName': 'bar'}
        stdout = self.assert_params_for_cmd(cmdline, result, expected_rc=0)[0]
        # We should have printed nothing because the parsed response
        # is an empty dict: {}.
        self.assertEqual(stdout, '')


class TestListUsers(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestListUsers, self).setUp()
        self.parsed_response = {
            'Users': [
                {
                    "UserName": "testuser-50",
                    "Path": "/",
                    "CreateDate": "2013-02-12T19:08:52Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::12345:user/testuser1"
                },
                {
                    "UserName": "testuser-51",
                    "Path": "/",
                    "CreateDate": "2012-10-14T23:53:39Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::123456:user/testuser2"
                },
            ]
        }

    def test_json_response(self):
        output = self.run_cmd('iam list-users', expected_rc=0)[0]
        parsed_output = json.loads(output)
        self.assertIn('Users', parsed_output)
        self.assertEqual(len(parsed_output['Users']), 2)
        self.assertEqual(sorted(parsed_output['Users'][0].keys()),
                         ['Arn', 'CreateDate', 'Path', 'UserId', 'UserName'])

    def test_jmespath_json_response(self):
        jmespath_query = 'Users[*].UserName'
        output = self.run_cmd('iam list-users --query %s' % jmespath_query,
                              expected_rc=0)[0]
        parsed_output = json.loads(output)
        self.assertEqual(parsed_output, ['testuser-50', 'testuser-51'])
