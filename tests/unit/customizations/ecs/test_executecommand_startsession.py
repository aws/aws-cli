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
import botocore.session
import json
import errno

import unittest
from awscli.customizations.ecs import executeCommand


class TestExecuteCommand(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock(botocore.session.Session)
        self.client = mock.Mock()
        self.region = 'us-west-2'
        self.endpoint_url = 'testUrl'
        self.client.meta.region_name = self.region
        self.client.meta.endpoint_url = self.endpoint_url
        self.caller = executeCommand.ExecuteCommandCaller(self.session)
        self.session.create_client.return_value = self.client

    @mock.patch('awscli.customizations.ecs.executeCommand.check_call')
    def test_execute_command_when_calls_fails_from_ecs(self, mock_check_call):
        self.client.execute_command.side_effect = Exception('some exception')
        mock_check_call.return_value = 0
        with self.assertRaisesRegexp(Exception, 'some exception'):
            self.caller.invoke('ecs', 'ExecuteCommand', {}, mock.Mock())

    @mock.patch('awscli.customizations.ecs.executeCommand.check_call')
    def test_execute_command_session_manager_plugin_not_installed_scenario(self, mock_check_call):
        mock_check_call.side_effect = [OSError(errno.ENOENT, 'some error'), 0]

        with self.assertRaises(ValueError):
            self.caller.invoke('ecs', 'ExecuteCommand', {}, mock.Mock())

    @mock.patch('awscli.customizations.ecs.executeCommand.check_call')
    def test_execute_command_success_scenario(self, mock_check_call):
        mock_check_call.return_value = 0
        execute_command_params = {
            "cluster": "default",
            "task": "someTaskId",
            "command": "ls",
            "interactive": "true"
        }

        execute_command_response = {
            "containerName": "someContainerName",
            "containerArn": "someContainerArn",
            "taskArn": "someTaskArn",
            "session": {"sessionId": "session-id", "tokenValue": "token-value", "streamUrl": "stream-url"},
            "clusterArn": "someClusterArn",
            "interactive": "true"
        }

        self.client.execute_command.return_value = execute_command_response

        rc = self.caller.invoke('ecs', 'ExecuteCommand', execute_command_params, mock.Mock())

        self.assertEquals(rc, 0)
        self.client.execute_command.assert_called_with(**execute_command_params)

        mock_check_call_list = mock_check_call.call_args[0][0]
        mock_check_call_list[1] = json.loads(mock_check_call_list[1])
        self.assertEqual(
            mock_check_call_list,
            ['session-manager-plugin',
             execute_command_response["session"],
             self.region,
             'StartSession']
        )

    @mock.patch('awscli.customizations.ecs.executeCommand.check_call')
    def test_execute_command_when_check_call_fails(self, mock_check_call):
        mock_check_call.side_effect = [0, Exception('some Exception')]

        execute_command_params = {
            "cluster": "default",
            "task": "someTaskId",
            "command": "ls",
            "interactive": "true"
        }

        execute_command_response = {
            "containerName": "someContainerName",
            "containerArn": "someContainerArn",
            "taskArn": "someTaskArn",
            "session": {"sessionId": "session-id", "tokenValue": "token-value", "streamUrl": "stream-url"},
            "clusterArn": "someClusterArn",
            "interactive": "true"
        }

        self.client.execute_command.return_value = execute_command_response

        with self.assertRaises(Exception):
            self.caller.invoke('ecs', 'ExecuteCommand', execute_command_params, mock.Mock())

            mock_check_call_list = mock_check_call.call_args[0][0]
            mock_check_call_list[1] = json.loads(mock_check_call_list[1])
            self.assertEqual(
                mock_check_call_list,
                ['session-manager-plugin',
                 execute_command_response["session"],
                 self.region,
                 'StartSession'])
