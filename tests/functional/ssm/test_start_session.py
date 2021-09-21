# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import mock
import errno
import json

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest


class TestSessionManager(BaseAWSCommandParamsTest):

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_success(self, mock_check_call):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_call.return_value = 0
        self.parsed_responses = [{
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }]
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        actual_response = json.loads(mock_check_call.call_args[0][0][1])
        self.assertEqual(
            {"SessionId": "session-id",
             "TokenValue": "token-value",
             "StreamUrl": "stream-url"},
            actual_response)

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_fails(self, mock_check_call):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_call.side_effect = OSError(errno.ENOENT, 'some error')
        self.parsed_responses = [{
            "SessionId": "session-id"
        }]
        self.run_cmd(cmdline, expected_rc=255)
        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        self.assertEqual(self.operations_called[1][0].name,
                         'TerminateSession')
        self.assertEqual(self.operations_called[1][1],
                         {'SessionId': 'session-id'})


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_start_session_output(self):
        self.driver.main(['ssm', 'start-session', 'help'])
        self.assert_contains('Output\n======\n\nNone')
