#!/usr/bin/env python
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime

import ruamel.yaml as yaml

from awscli.compat import ensure_text_type
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import skip_if_windows


class TestYAMLOutput(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestYAMLOutput, self).setUp()
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
                    "UserId": u"EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::123456:user/testuser2"
                },
            ]
        }

    def test_yaml_response(self):
        stdout, _, _ = self.run_cmd(
            'iam list-users --output yaml', expected_rc=0
        )
        expected = (
            "Users:\n"
            "- Arn: arn:aws:iam::12345:user/testuser1\n"
            "  CreateDate: '2013-02-12T19:08:52Z'\n"
            "  Path: /\n"
            "  UserId: EXAMPLEUSERID\n"
            "  UserName: testuser-50\n"
            "- Arn: arn:aws:iam::123456:user/testuser2\n"
            "  CreateDate: '2012-10-14T23:53:39Z'\n"
            "  Path: /\n"
            "  UserId: EXAMPLEUSERID\n"
            "  UserName: testuser-51\n"
        )
        self.assertEqual(stdout, expected)
        parsed_output = yaml.safe_load(stdout)
        self.assertEqual(self.parsed_response, parsed_output)

    def test_empty_dict_response_prints_nothing(self):
        self.parsed_response = {}
        stdout, _, _ = self.run_cmd(
            'sts get-caller-identity --output yaml',
            expected_rc=0
        )
        self.assertEqual(stdout, '')

    def test_empty_list_prints_list(self):
        self.parsed_response = []
        stdout, _, _ = self.run_cmd(
            'sts get-caller-identity --output yaml', expected_rc=0
        )
        self.assertEqual(stdout, '[]\n')

    def test_empty_string_prints_nothing(self):
        self.parsed_response = ''
        stdout, _, _ = self.run_cmd(
            'sts get-caller-identity --output yaml', expected_rc=0
        )
        self.assertEqual(stdout, '""\n')

    def test_jmespath_yaml_response(self):
        jmespath_query = 'Users[*].UserName'
        stdout, _, _ = self.run_cmd(
            'iam list-users --output yaml --query %s' % jmespath_query,
            expected_rc=0
        )
        parsed_output = yaml.safe_load(stdout)
        self.assertEqual(parsed_output, ['testuser-50', 'testuser-51'])

    def test_print_int(self):
        self.parsed_response = {
            'Count': 1
        }
        command = (
            'dynamodb scan --output yaml --table-name foo --select COUNT '
            '--query Count'
        )
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        self.assertEqual(stdout, '1\n')

    def test_print_float(self):
        self.parsed_response = {
            'ConsumedCapacity': {
                'CapacityUnits': 0.5
            }
        }
        command = (
            'dynamodb scan --output yaml --table-name foo '
            '--query ConsumedCapacity.CapacityUnits'
        )
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        self.assertEqual(stdout, '0.5\n')

    def test_print_none(self):
        self.parsed_response = {
            'ConsumedCapacity': None
        }
        command = (
            'dynamodb scan --output yaml --table-name foo --query '
            'ConsumedCapacity'
        )
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        self.assertEqual(stdout, 'null\n')

    def test_print_bool(self):
        self.parsed_response = {
            "Contents": [],
            "IsTruncated": False,
        }
        command = (
            's3api list-objects --output yaml --no-paginate '
            '--bucket foo --query IsTruncated'
        )
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        self.assertEqual(stdout, 'false\n')

    def test_print_timestamp_raises_error(self):
        now = datetime.datetime.now()
        self.parsed_response = {
            "Buckets": [{
                "CreationDate": now,
                "Name": "foo",
            }]
        }
        command = (
            's3api list-buckets --output yaml --query Buckets[0].CreationDate'
        )
        _, stderr, _ = self.run_cmd(command, expected_rc=255)
        expected = 'not JSON serializable'
        self.assertIn(expected, stderr)

    def test_print_string_literal(self):
        jmespath_query = 'Users[0].UserName'
        stdout, _, _ = self.run_cmd(
            'iam list-users --output yaml --query %s' % jmespath_query,
            expected_rc=0
        )
        self.assertEqual(stdout, '"testuser-50"\n')

    @skip_if_windows('Encoding tests only supported on mac/linux')
    def test_yaml_prints_unicode_chars(self):
        self.parsed_response['Users'][1]['UserId'] = u'\u2713'
        stdout, _, _ = self.run_cmd(
            'iam list-users --output yaml', expected_rc=0
        )
        self.assertIn(u'\u2713', ensure_text_type(stdout))

    @skip_if_windows('Encoding tests only supported on mac/linux')
    def test_unicode_yaml_scalar(self):
        self.parsed_response['Users'][1]['UserId'] = u'\u2713'
        stdout, _, _ = self.run_cmd(
            [
                'iam', 'list-users', '--output', 'yaml', '--query',
                'Users[1].UserId'
            ],
            expected_rc=0
        )
        self.assertIn(u'\u2713', ensure_text_type(stdout))
