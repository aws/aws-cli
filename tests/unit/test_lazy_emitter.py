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

from awscli.handlers_registry import CommandTableOp
from awscli.lazy import LazyCommand
from awscli.lazy_emitter import LazyInitEmitter


@pytest.fixture
def mock_module():
    """Create a mock module with a callable init function."""
    module = MagicMock()
    module.my_init = MagicMock()
    return module


class TestLazyInitEmitterPrefixMatching:
    def test_bare_prefix_entry_initialized_on_dotted_emit(self, mock_module):
        # Entry registered against 'building-command-table' (bare prefix)
        # should be initialized when 'building-command-table.main' is emitted.
        registry = {
            'building-command-table': [
                ('test.module', 'my_init'),
            ],
        }
        emitter = LazyInitEmitter()
        emitter.load_registry(registry)

        with patch('importlib.import_module', return_value=mock_module):
            emitter.emit('building-command-table.main', command_table={})

        assert emitter.initialized_count == 1
        mock_module.my_init.assert_called_once()

    def test_exact_match_entry_initialized(self, mock_module):
        registry = {
            'building-command-table.main': [
                ('test.module', 'my_init'),
            ],
        }
        emitter = LazyInitEmitter()
        emitter.load_registry(registry)

        with patch('importlib.import_module', return_value=mock_module):
            emitter.emit('building-command-table.main', command_table={})

        assert emitter.initialized_count == 1
        mock_module.my_init.assert_called_once()

    def test_unrelated_entry_not_initialized(self, mock_module):
        # Entry registered against 'building-command-table.ecs' should NOT
        # be initialized when 'building-command-table.main' is emitted.
        registry = {
            'building-command-table.ecs': [
                ('test.module', 'my_init'),
            ],
        }
        emitter = LazyInitEmitter()
        emitter.load_registry(registry)

        with patch('importlib.import_module', return_value=mock_module):
            emitter.emit('building-command-table.main', command_table={})

        assert emitter.initialized_count == 0
        mock_module.my_init.assert_not_called()

    def test_multiple_prefix_levels_all_initialized(self, mock_module):
        # Both 'building-command-table' and 'building-command-table.main'
        # entries should be initialized when 'building-command-table.main'
        # is emitted.
        mock_module.other_init = MagicMock()
        registry = {
            'building-command-table': [
                ('test.module', 'my_init'),
            ],
            'building-command-table.main': [
                ('test.module', 'other_init'),
            ],
        }
        emitter = LazyInitEmitter()
        emitter.load_registry(registry)

        with patch('importlib.import_module', return_value=mock_module):
            emitter.emit('building-command-table.main', command_table={})

        assert emitter.initialized_count == 2
        mock_module.my_init.assert_called_once()
        mock_module.other_init.assert_called_once()

    def test_entry_initialized_only_once(self, mock_module):
        registry = {
            'building-command-table': [
                ('test.module', 'my_init'),
            ],
        }
        emitter = LazyInitEmitter()
        emitter.load_registry(registry)

        with patch('importlib.import_module', return_value=mock_module):
            emitter.emit('building-command-table.main', command_table={})
            emitter.emit('building-command-table.ecs', command_table={})

        assert emitter.initialized_count == 1
        mock_module.my_init.assert_called_once()


class TestMainCommandTableOps:
    def test_covered_plugins_not_imported(self, mock_module):
        registry = {
            'building-command-table.main': [
                ('heavy.module', 'register_add_cmd'),
            ],
        }
        main_ops = [
            (CommandTableOp.ADD, 'my-cmd', 'heavy.module', 'MyCommand'),
        ]
        emitter = LazyInitEmitter(main_command_table_ops=main_ops)
        emitter.load_registry(registry)

        command_table = {'existing': MagicMock(name='existing')}
        session = MagicMock()

        with (
            patch('awscli.lazy_emitter.PLUGIN_REGISTRY', registry),
            patch('importlib.import_module', return_value=mock_module) as imp,
        ):
            emitter.emit(
                'building-command-table.main',
                command_table=command_table,
                session=session,
            )

        # The heavy module should NOT have been imported via _ensure_initialized
        imp.assert_not_called()
        # But the entry should be marked as initialized
        assert emitter.initialized_count == 1

    def test_rename_op_applied_to_command_table(self):
        registry = {
            'building-command-table.main': [
                ('rename.module', 'register_rename'),
            ],
        }
        main_ops = [
            (CommandTableOp.RENAME, 'old-name', 'new-name'),
        ]
        emitter = LazyInitEmitter(main_command_table_ops=main_ops)
        emitter.load_registry(registry)

        cmd = MagicMock()
        cmd.name = 'old-name'
        command_table = {'old-name': cmd}
        session = MagicMock()

        with patch('awscli.lazy_emitter.PLUGIN_REGISTRY', registry):
            emitter.emit(
                'building-command-table.main',
                command_table=command_table,
                session=session,
            )

        assert 'old-name' not in command_table
        assert 'new-name' in command_table
        assert command_table['new-name'] is cmd
        assert cmd.name == 'new-name'

    def test_add_op_creates_lazy_command(self):
        registry = {
            'building-command-table.main': [
                ('add.module', 'register_add'),
            ],
        }
        main_ops = [
            (CommandTableOp.ADD, 'my-cmd', 'add.module.impl', 'MyCommand'),
        ]
        emitter = LazyInitEmitter(main_command_table_ops=main_ops)
        emitter.load_registry(registry)

        command_table = {}
        session = MagicMock()

        with patch('awscli.lazy_emitter.PLUGIN_REGISTRY', registry):
            emitter.emit(
                'building-command-table.main',
                command_table=command_table,
                session=session,
            )

        assert 'my-cmd' in command_table
        assert isinstance(command_table['my-cmd'], LazyCommand)
        assert command_table['my-cmd'].name == 'my-cmd'

    def test_main_ops_skips_covered_but_initializes_bare_prefix(
        self, mock_module
    ):
        # Entries registered against bare 'building-command-table' must
        # still be initialized even when main_ops are applied.
        registry = {
            'building-command-table': [
                ('global.module', 'register_global'),
            ],
            'building-command-table.main': [
                ('heavy.module', 'register_add_cmd'),
            ],
        }
        main_ops = [
            (CommandTableOp.ADD, 'my-cmd', 'heavy.module', 'MyCommand'),
        ]
        emitter = LazyInitEmitter(main_command_table_ops=main_ops)
        emitter.load_registry(registry)

        command_table = {}
        session = MagicMock()

        mock_global = MagicMock()
        mock_global.register_global = MagicMock()

        def import_side_effect(mod_path):
            # Ensures that no module besides global.module
            # (including heavy.module) are imported. heavy.module should not be
            # imported because it is present in main_command_table_ops.
            if mod_path == 'global.module':
                return mock_global
            raise AssertionError(f'Unexpected import of {mod_path!r}')

        with (
            patch('awscli.lazy_emitter.PLUGIN_REGISTRY', registry),
            patch('importlib.import_module', side_effect=import_side_effect),
        ):
            emitter.emit(
                'building-command-table.main',
                command_table=command_table,
                session=session,
            )

        mock_global.register_global.assert_called_once()
        assert emitter.initialized_count == 2
