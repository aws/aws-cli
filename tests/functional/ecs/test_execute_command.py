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
import errno
import json

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest


class TestExecuteCommand(BaseAWSCommandParamsTest):

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_execute_command_success(self, mock_check_call):
        cmdline = 'ecs execute-command --cluster someCluster ' \
                  '--task someTaskId ' \
                  '--interactive --command ls ' \
                  '--region us-west-2'
        mock_check_call.return_value = 0
        self.parsed_responses = [{
            "containerName": "someContainerName",
            "containerArn": "someContainerArn",
            "taskArn": "someTaskArn",
            "session": {"sessionId": "session-id",
                        "tokenValue": "token-value",
                        "streamUrl": "stream-url"},
            "clusterArn": "someCluster",
            "interactive": "true"
        }, {
            "failures": [],
            "tasks": [
                {
                    "clusterArn": "ecs/someCLuster",
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
        }]
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name,
                         'ExecuteCommand'
                         )
        actual_response = json.loads(mock_check_call.call_args[0][0][1])
        self.assertEqual(
            {"sessionId": "session-id",
             "tokenValue": "token-value",
             "streamUrl": "stream-url"},
            actual_response
        )

    @mock.patch('awscli.customizations.ecs.executecommand.check_call')
    def test_execute_command_fails(self, mock_check_call):
        cmdline = 'ecs execute-command --cluster someCluster ' \
                  '--task someTaskId ' \
                  '--interactive --command ls ' \
                  '--region us-west-2'
        mock_check_call.side_effect = OSError(errno.ENOENT, 'some error')
        self.run_cmd(cmdline, expected_rc=255)


class TestHelpOutput(BaseAWSHelpOutputTest):

    def test_execute_command_output(self):
        self.driver.main(['ecs', 'execute-command', 'help'])
        self.assert_contains('Output\n======\n\nNone')
