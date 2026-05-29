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
import pytest

from awscli.handlers_registry import MAIN_COMMAND_TABLE_OPS, CommandTableOp
from awscli.lazy import LazyCommand
from awscli.testutils import BaseAWSHelpOutputTest, mock

# Derive test parameters from MAIN_COMMAND_TABLE_OPS.
_ADD_OPS = [op for op in MAIN_COMMAND_TABLE_OPS if op[0] == CommandTableOp.ADD]
_RENAME_OPS = [
    op for op in MAIN_COMMAND_TABLE_OPS if op[0] == CommandTableOp.RENAME
]
_ADD_CMD_NAMES = [op[1] for op in _ADD_OPS]
_RENAME_NEW_NAMES = [op[2] for op in _RENAME_OPS]


class TestLazyCommandHelpRenders(BaseAWSHelpOutputTest):
    def test_added_command_help_renders(self):
        for cmd_name in _ADD_CMD_NAMES:
            with self.subTest(cmd_name=cmd_name):
                self.driver.main([cmd_name, 'help'])
                self.assert_contains(cmd_name)

    def test_renamed_command_help_renders(self):
        for new_name in _RENAME_NEW_NAMES:
            with self.subTest(new_name=new_name):
                self.driver.main([new_name, 'help'])
                self.assert_contains(new_name)


class TestLazyCommandIsTransparent(BaseAWSHelpOutputTest):
    def test_added_commands_appear_in_top_level_help(self):
        self.driver.main(['help'])
        for cmd_name in _ADD_CMD_NAMES:
            self.assert_contains(cmd_name)

    def test_lazy_command_has_subcommands(self):
        command_table = self.driver.subcommand_table
        s3_cmd = command_table['s3']
        assert isinstance(s3_cmd, LazyCommand)
        subcommands = s3_cmd.subcommand_table
        assert 'ls' in subcommands
        assert 'cp' in subcommands


class TestLazyCommandErrorPaths:
    def test_invalid_module_path_raises_on_resolve(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.nonexistent.module',
            'FakeCommand',
        )
        with pytest.raises(ModuleNotFoundError):
            cmd([], mock.MagicMock())

    def test_invalid_class_name_raises_on_resolve(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.customizations.dynamodb.ddb',
            'NonexistentClass',
        )
        with pytest.raises(AttributeError):
            cmd([], mock.MagicMock())

    def test_invalid_module_path_raises_on_help(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.nonexistent.module',
            'FakeCommand',
        )
        with pytest.raises(ModuleNotFoundError):
            cmd.create_help_command()
