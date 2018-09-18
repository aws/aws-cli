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
import mock
import errno
import json
import botocore.session

from awscli.customizations import sessionmanager
from awscli.testutils import unittest


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock(botocore.session.Session)
        self.client = mock.Mock()
        self.region = 'us-west-2'
        self.client.meta.region_name = self.region
        self.session.create_client.return_value = self.client
        self.caller = sessionmanager.StartSessionCaller(self.session)

    def test_start_session_when_non_custom_start_session_fails(self):
        self.client.start_session.side_effect = Exception('some exception')
        params = {}
        with self.assertRaisesRegexp(Exception, 'some exception'):
            self.caller.invoke('ssm', 'StartSession', params, mock.Mock())

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_success_scenario(self, mock_check_call):
        mock_check_call.return_value = 0

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }

        self.client.start_session.return_value = start_session_response

        rc = self.caller.invoke('ssm', 'StartSession',
                                start_session_params, mock.Mock())
        self.assertEquals(rc, 0)
        self.client.start_session.assert_called_with(**start_session_params)
        mock_check_call_list = mock_check_call.call_args[0][0]
        mock_check_call_list[1] = json.loads(mock_check_call_list[1])
        self.assertEqual(
            mock_check_call_list,
            ['session-manager-plugin',
             start_session_response,
             self.region,
             'StartSession']
        )

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_when_check_call_fails(self, mock_check_call):
        mock_check_call.side_effect = OSError(errno.ENOENT, 'some error')

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }

        terminate_session_params = {
            "SessionId": "session-id"
        }

        self.client.start_session.return_value = start_session_response

        with self.assertRaises(ValueError):
            self.caller.invoke('ssm', 'StartSession',
                               start_session_params, mock.Mock())

            self.client.start_session.assert_called_with(
                **start_session_params)
            self.client.terminate_session.assert_called_with(
                **terminate_session_params)

            mock_check_call_list = mock_check_call.call_args[0][0]
            mock_check_call_list[1] = json.loads(mock_check_call_list[1])
            self.assertEqual(
                mock_check_call_list,
                ['session-manager-plugin',
                 start_session_response,
                 self.region,
                 'StartSession']
            )
