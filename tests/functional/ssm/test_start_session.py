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
import errno
import json

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest
from awscli.testutils import mock


class TestSessionManager(BaseAWSCommandParamsTest):
    @mock.patch('awscli.customizations.sessionmanager.check_call')
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_success(self, mock_check_output, mock_check_call):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.0.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]
        start_session_params = {"Target": "instance-id"}

        self.run_cmd(cmdline, expected_rc=0)

        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                json.dumps(expected_response),
                mock.ANY,
                "StartSession",
                mock.ANY,
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=self.environ,
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_with_new_version_plugin_success(
        self, mock_check_output, mock_check_call
    ):
        cmdline = "ssm start-session --target instance-id"
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.500.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]

        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"
        start_session_params = {"Target": "instance-id"}
        expected_env = self.environ.copy()
        expected_env.update({ssm_env_name: json.dumps(expected_response)})

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})

        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                ssm_env_name,
                mock.ANY,
                "StartSession",
                mock.ANY,
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=expected_env,
        )

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_fails(self, mock_check_output, mock_check_call):
        cmdline = "ssm start-session --target instance-id"
        mock_check_output.return_value = "1.2.500.0\n"
        mock_check_call.side_effect = OSError(errno.ENOENT, "some error")
        self.parsed_responses = [
            {
                "SessionId": "session-id",
                "TokenValue": "token-value",
                "StreamUrl": "stream-url",
            }
        ]
        self.run_cmd(cmdline, expected_rc=255)
        self.assertEqual(
            self.operations_called[0][0].name, "StartSession"
        )
        self.assertEqual(
            self.operations_called[0][1], {"Target": "instance-id"}
        )
        self.assertEqual(
            self.operations_called[1][0].name, "TerminateSession"
        )
        self.assertEqual(
            self.operations_called[1][1], {"SessionId": "session-id"}
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_get_plugin_version_fails(
        self, mock_check_output, mock_check_call
    ):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_output.side_effect = OSError(errno.ENOENT, 'some error')
        self.parsed_responses = [
            {
                "SessionId": "session-id",
                "TokenValue": "token-value",
                "StreamUrl": "stream-url",
            }
        ]
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
