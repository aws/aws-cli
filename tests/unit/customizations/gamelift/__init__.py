# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
from awscli.testutils import mock
from awscli.customizations.gamelift import register_gamelift_commands
from awscli.customizations.gamelift import inject_commands
from awscli.customizations.gamelift.uploadbuild import UploadBuildCommand
from awscli.customizations.gamelift.getlog import GetGameSessionLogCommand


class TestRegisterGameLiftCommands(unittest.TestCase):
    def test_register_gamelift_commands(self):
        event_emitter = mock.Mock()
        register_gamelift_commands(event_emitter)
        event_emitter.register.assert_called_once_with(
            'building-command-table.gamelift', inject_commands)


class TestInjectCommands(unittest.TestCase):
    def test_inject_commands(self):
        command_table = {}
        session = mock.Mock()
        inject_commands(command_table, session)
        self.assertIn('upload-build', command_table)
        self.assertIsInstance(
            command_table['upload-build'], UploadBuildCommand)
        self.assertIn('get-game-session-log', command_table)
        self.assertIsInstance(
            command_table['get-game-session-log'], GetGameSessionLogCommand)
