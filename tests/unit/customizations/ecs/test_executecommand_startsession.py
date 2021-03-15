# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.ecs import executecommand


class TestExecuteCommand(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock(botocore.session.Session)
        self.client = mock.Mock()
        self.region = 'us-west-2'
        self.profile = 'testProfile'
        self.endpoint_url = 'testUrl'
        self.client.meta.region_name = self.region
        self.client.meta.endpoint_url = self.endpoint_url
        self.caller = executecommand.ExecuteCommandCaller(self.session)
        self.session.profile = self.profile
        self.session.create_client.return_value = self.client
        self.execute_command_params = {
            "cluster": "default",
            "task": "someTaskId",
            "command": "ls",
            "interactive": "true"}
        self.execute_command_response = {
            "containerName": "someContainerName",
            "containerArn": "ecs/someContainerArn",
            "taskArn": "ecs/someTaskArn",
            "session": {"sessionId": "session-id",
                        "tokenValue": "token-value",
                        "streamUrl": "stream-url"},
            "clusterArn": "ecs/someClusterArn",
            "interactive": "true"
        }
        self.describe_tasks_response = {
            "failures": [],
            "tasks": [
                {
                    "clusterArn": "ecs/someCLusterArn",
                    "desiredStatus": "RUNNING",
                    "createdAt": "1611619514.46",
                    "taskArn": "someTaskArn",
                    "containers": [
                        {
                            "containerArn": "ecs/someContainerArn",
                            "taskArn": "ecs/someTaskArn",
                            "name": "someContainerName",
                            "managedAgents": [
                             {
                                 "reason": "Execute Command Agent started",
                                 "lastStatus": "RUNNING",
                                 "lastStartedAt": "1611619528.272",
                                 "name": "ExecuteCommandAgent"
                             }
                             ],
                            "runtimeId": "someRuntimeId"
                        },
                        {
                            "containerArn": "ecs/dummyContainerArn",
                            "taskArn": "ecs/someTaskArn",
                            "name": "dummyContainerName",
                            "managedAgents": [
                                {
                                    "reason": "Execute Command Agent started",
                                    "lastStatus": "RUNNING",
                                    "lastStartedAt": "1611619528.272",
                                    "name": "ExecuteCommandAgent"
                                }
                            ],
                            "runtimeId": "dummyRuntimeId"
                        }
                    ],
                    "lastStatus": "RUNNING",
                    "enableExecuteCommand": "true"
                }
            ]
        }
        self.describe_tasks_response_fail = {
            "failures": [
                {
                    "reason": "MISSING",
                    "arn": "someTaskArn"
                }
            ],
            "tasks": []
        }
        self.ssm_request_parameters = {
            "Target": "ecs:someClusterArn_someTaskArn_someRuntimeId"
        }

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_when_calls_fails_from_ecs(self, mock_check_call):
        self.client.execute_command.side_effect = Exception('some exception')
        mock_check_call.return_value = 0
        with self.assertRaisesRegexp(Exception, 'some exception'):
            self.caller.invoke('ecs', 'ExecuteCommand', {}, mock.Mock())

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_when_session_manager_plugin_not_installed(self, mock_check_call):
        mock_check_call.side_effect = [OSError(errno.ENOENT, 'some error'), 0]

        with self.assertRaises(ValueError):
            self.caller.invoke('ecs', 'ExecuteCommand', {}, mock.Mock())

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_execute_command_success(self, mock_check_call):
        mock_check_call.return_value = 0

        self.client.execute_command.return_value = \
            self.execute_command_response
        self.client.describe_tasks.return_value = self.describe_tasks_response

        rc = self.caller.invoke('ecs', 'ExecuteCommand',
                                self.execute_command_params, mock.Mock())

        self.assertEquals(rc, 0)
        self.client.execute_command.\
            assert_called_with(**self.execute_command_params)

        mock_check_call_list = mock_check_call.call_args[0][0]
        mock_check_call_list[1] = json.loads(mock_check_call_list[1])
        self.assertEqual(
            mock_check_call_list,
            ['session-manager-plugin',
             self.execute_command_response["session"],
             self.region,
             'StartSession',
             self.profile,
             json.dumps(self.ssm_request_parameters),
             self.endpoint_url
             ]
        )

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_when_describe_task_fails(self, mock_check_call):
        mock_check_call.return_value = 0

        self.client.execute_command.return_value = \
            self.execute_command_response
        self.client.describe_tasks.side_effect = \
            Exception("Some Server Exception")

        with self.assertRaisesRegexp(Exception, 'Some Server Exception'):
            rc = self.caller.invoke('ecs', 'ExecuteCommand',
                                    self.execute_command_params, mock.Mock())
            self.assertEquals(rc, 0)
            self.client.execute_command. \
                assert_called_with(**self.execute_command_params)

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_when_describe_task_returns_no_tasks(self, mock_check_call):
        mock_check_call.return_value = 0

        self.client.execute_command.return_value = \
            self.execute_command_response
        self.client.describe_tasks.return_value = \
            self.describe_tasks_response_fail

        with self.assertRaises(Exception):
            rc = self.caller.invoke('ecs', 'ExecuteCommand',
                                    self.execute_command_params, mock.Mock())
            self.assertEquals(rc, 0)
            self.client.execute_command. \
                assert_called_with(**self.execute_command_params)

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_when_check_call_fails(self, mock_check_call):
        mock_check_call.side_effect = [0, Exception('some Exception')]

        self.client.execute_command.return_value = \
            self.execute_command_response
        self.client.describe_tasks.return_value = self.describe_tasks_response

        with self.assertRaises(Exception):
            self.caller.invoke('ecs', 'ExecuteCommand',
                               self.execute_command_params, mock.Mock())

            mock_check_call_list = mock_check_call.call_args[0][0]
            mock_check_call_list[1] = json.loads(mock_check_call_list[1])
            self.assertEqual(
                mock_check_call_list,
                ['session-manager-plugin',
                 self.execute_command_response["session"],
                 self.region,
                 'StartSession',
                 self.profile,
                 json.dumps(self.ssm_request_parameters),
                 self.endpoint_url],
            )
