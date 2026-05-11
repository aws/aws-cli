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
from unittest.mock import MagicMock, patch

import pytest

from awscli.lazy import LazyCommand


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def mock_command_class():
    cls = MagicMock()
    instance = MagicMock()
    cls.return_value = instance
    return cls


@pytest.fixture
def mock_module(mock_command_class):
    module = MagicMock()
    module.MyCommand = mock_command_class
    return module


class TestLazyCommandResolution:
    def test_does_not_import_on_construction(self, session):
        with patch('importlib.import_module') as imp:
            LazyCommand('cmd', session, 'some.module', 'MyCommand')
        imp.assert_not_called()

    def test_imports_module_on_call(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            cmd(['arg1'], MagicMock())
        mock_module.MyCommand.assert_called_once_with(session)

    def test_imports_module_on_help(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            cmd.create_help_command()
        mock_module.MyCommand.assert_called_once_with(session)

    def test_imports_module_on_arg_table(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            _ = cmd.arg_table
        mock_module.MyCommand.assert_called_once_with(session)

    def test_imports_module_on_subcommand_table(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            _ = cmd.subcommand_table
        mock_module.MyCommand.assert_called_once_with(session)

    def test_resolves_only_once(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module) as imp:
            cmd(['arg1'], MagicMock())
            cmd(['arg2'], MagicMock())
        imp.assert_called_once_with('some.module')

    def test_delegates_call_to_real_command(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        args = ['arg1']
        parsed_globals = MagicMock()
        with patch('importlib.import_module', return_value=mock_module):
            cmd(args, parsed_globals)
        mock_module.MyCommand.return_value.assert_called_once_with(
            args, parsed_globals
        )

    def test_delegates_help_to_real_command(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            result = cmd.create_help_command()
        assert result == mock_module.MyCommand.return_value.create_help_command()


class TestLazyCommandProperties:
    def test_name_returns_initial_name(self, session):
        cmd = LazyCommand('my-cmd', session, 'some.module', 'MyCommand')
        assert cmd.name == 'my-cmd'

    def test_name_setter_updates_name(self, session):
        cmd = LazyCommand('old-name', session, 'some.module', 'MyCommand')
        cmd.name = 'new-name'
        assert cmd.name == 'new-name'

    def test_lineage_defaults_to_self(self, session):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        assert cmd.lineage == [cmd]

    def test_lineage_setter_updates_lineage(self, session):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        new_lineage = [MagicMock(), cmd]
        cmd.lineage = new_lineage
        assert cmd.lineage == new_lineage

    def test_lineage_propagated_to_real_on_resolve(self, session, mock_module):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        new_lineage = [MagicMock(), cmd]
        cmd.lineage = new_lineage
        with patch('importlib.import_module', return_value=mock_module):
            cmd.create_help_command()
        assert mock_module.MyCommand.return_value.lineage == new_lineage

    def test_lineage_setter_propagates_to_already_resolved(
        self, session, mock_module
    ):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        with patch('importlib.import_module', return_value=mock_module):
            cmd.create_help_command()
        new_lineage = [MagicMock(), cmd]
        cmd.lineage = new_lineage
        assert mock_module.MyCommand.return_value.lineage == new_lineage

    def test_lineage_not_propagated_if_not_resolved(self, session):
        cmd = LazyCommand('cmd', session, 'some.module', 'MyCommand')
        new_lineage = [MagicMock(), cmd]
        # Should not raise even though underlying command is not resolved.
        cmd.lineage = new_lineage
        assert cmd.lineage == new_lineage
