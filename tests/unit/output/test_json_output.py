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
from botocore.compat import json
import platform
from awscli.formatter import JSONFormatter

from awscli.testutils import BaseAWSCommandParamsTest, unittest
from awscli.testutils import mock, skip_if_windows
from awscli.compat import StringIO, get_stdout_text_writer


class TestGetPasswordData(BaseAWSCommandParamsTest):

    COMMAND = 'iam add-user-to-group --group-name foo --user-name bar'

    def setUp(self):
        super(TestGetPasswordData, self).setUp()
        self.parsed_response = {}

    def test_empty_dict_response_prints_nothing(self):
        # This is the default response, but we want to be explicit
        # that we're returning an empty dict.
        self.parsed_response = {}
        stdout = self.run_cmd(self.COMMAND, expected_rc=0)[0]
        self.assertEqual(stdout, '')

    def test_empty_list_prints_list(self):
        self.parsed_response = []
        stdout = self.run_cmd(self.COMMAND, expected_rc=0)[0]
        self.assertEqual(stdout, '[]\n')

    def test_empty_string_prints_nothing(self):
        self.parsed_response = ''
        stdout = self.run_cmd(self.COMMAND, expected_rc=0)[0]
        self.assertEqual(stdout, '""\n')


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
                    "UserId": u"EXAMPLEUSERID",
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

    def test_zero_value_is_printed(self):
        # Even though the integer 0 is false-like, we still
        # should be printing it to stdout if a jmespath query
        # evaluates to 0.
        jmespath_query = '`0`'
        output = self.run_cmd('iam list-users --query %s' % jmespath_query,
                              expected_rc=0)[0]
        self.assertEqual(output, '0\n')

    def test_unknown_output_type_from_env_var(self):
        # argparse already handles the case with a bad --output
        # specified on the CLI, we need to verify that a bad
        # output format from the env var still gives an error.
        self.environ['AWS_DEFAULT_OUTPUT'] = 'bad-output-type'
        self.run_cmd('iam list-users', expected_rc=255)

    @skip_if_windows('Encoding tests only supported on mac/linux')
    def test_json_prints_unicode_chars(self):
        self.parsed_response['Users'][1]['UserId'] = u'\u2713'
        output = self.run_cmd('iam list-users', expected_rc=0)[0]
        with mock.patch('sys.stdout', StringIO()) as f:
            out = get_stdout_text_writer()
            out.write(u'\u2713')
            expected = f.getvalue()
        # We should not see the '\u<hex>' for of the unicode character.
        # It should be encoded into the default encoding.
        self.assertNotIn('\\u2713', output)
        self.assertIn(expected, output)


class TestFormattersHandleClosedPipes(unittest.TestCase):
    def test_fully_buffered_handles_io_error(self):
        args = mock.Mock(query=None)
        operation = mock.Mock(can_paginate=False)
        response = '{"Foo": "Bar"}'
        fake_closed_stream = mock.Mock(spec=StringIO)
        fake_closed_stream.flush.side_effect = IOError
        formatter = JSONFormatter(args)
        formatter('command_name', response, stream=fake_closed_stream)
        # We should not have let the IOError propagate, but
        # we still should have called the flush() on the
        # stream.
        fake_closed_stream.flush.assert_called_with()
