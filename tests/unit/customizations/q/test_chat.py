# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from unittest.mock import patch

import pytest

from awscli.customizations.q import inject_commands, register_q_commands
from awscli.customizations.q.chat import ChatCommand
from awscli.customizations.q.utils import Q_EXTENSION_PATH
from awscli.testutils import mock


def test_register_q_commands():
    event_emitter = mock.Mock()
    register_q_commands(event_emitter)
    event_emitter.register.assert_called_once_with(
        'building-command-table.main', inject_commands
    )


class TestChatCommand:
    def setup_method(self):
        self.session = mock.Mock()
        self.mock_subprocess = patch('subprocess.check_call').start()
        self.chat_command = ChatCommand(self.session)

    @patch('pathlib.Path.is_file', return_value=True)
    def test_chat_subprocess_call(self, mock_is_file):
        self.chat_command._run_main([], None)

        # Verify Q extension was called with correct argument
        self.mock_subprocess.assert_called_once_with(Q_EXTENSION_PATH)

    @patch('pathlib.Path.is_file', return_value=False)
    def test_chat_subprocess_not_called_when_no_file(self, mock_is_file):
        # Execute the command and expect RuntimeError because
        # the Q extension is not installed
        with pytest.raises(RuntimeError):
            self.chat_command._run_main([], None)

        # Verify Q extension was not called
        self.mock_subprocess.assert_not_called()
