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
"""Lazy-initializing event emitter for the AWS CLI plugin system.

LazyInitEmitter wraps a HierarchicalEmitter and uses the plugin registry
to initialize plugins on demand. Before emitting event X, it finds all
initializer entries whose event patterns match X (using the same
prefix/wildcard semantics as HierarchicalEmitter), calls each initializer
at most once, then delegates to the underlying emitter for normal dispatch.
"""

import copy
import importlib
import logging

from botocore.hooks import HierarchicalEmitter, PrefixTrie

from awscli.handlers_registry import CommandTableOp
from awscli.lazy import LazyCommand

logger = logging.getLogger(__name__)


class LazyInitEmitter(HierarchicalEmitter):
    """HierarchicalEmitter that lazily initializes plugins from a registry.

    The registry maps event patterns to lists of (module, fn_name) tuples.
    Before emitting any event, this emitter checks whether there are
    uninitialised plugins whose event patterns match the event being emitted.
    If so, it imports and calls them, then proceeds with normal dispatch.
    """

    def __init__(self, plugin_registry=None, main_command_table_ops=None):
        super().__init__()
        self._init_trie = PrefixTrie()
        # set of (module, fn_name)
        self._initialized = set()
        # number of entries not yet initialized
        self._pending_count = 0
        # event_name -> list of entries from init trie
        self._init_cache: dict[str, list] = {}
        self._registry = plugin_registry or {}
        self._main_ops = main_command_table_ops
        self._main_ops_applied = False
        if self._registry:
            self.load_registry(self._registry)

    def load_registry(self, registry):
        unique = set()
        for event_pattern, entries in registry.items():
            for entry in entries:
                self._init_trie.append_item(event_pattern, entry)
                if entry not in unique:
                    unique.add(entry)
                    self._pending_count += 1
        self._init_cache = {}

    @property
    def initialized_count(self):
        return len(self._initialized)

    def _apply_main_command_table_ops(self, kwargs):
        """Apply pre-computed renames and LazyCommand additions.

        This replaces the normal lazy-init path for
        building-command-table.main entries, avoiding the import of
        heavy plugin modules until the command is actually invoked.
        """
        command_table = kwargs.get('command_table')
        session = kwargs.get('session')
        if command_table is None or session is None:
            return

        super()._emit('before-load-plugins.building-command-table.main', {})
        for op in self._main_ops:
            if op[0] == CommandTableOp.RENAME:
                _, old_name, new_name = op
                if old_name in command_table:
                    current = command_table[old_name]
                    command_table[new_name] = current
                    current.name = new_name
                    del command_table[old_name]
            elif op[0] == CommandTableOp.ADD:
                _, cmd_name, cmd_module, cmd_class = op
                command_table[cmd_name] = LazyCommand(
                    cmd_name,
                    session,
                    cmd_module,
                    cmd_class,
                )
            else:
                raise RuntimeError(f'Unknown command table ops entry: {op}')

        # Mark all building-command-table.main entries as initialized so
        # _ensure_initialized never imports them. The ops list fully
        # accounts for all plugins registered against this event.
        for entry in self._registry.get('building-command-table.main', []):
            entry = tuple(entry)
            if entry not in self._initialized:
                self._initialized.add(entry)
                self._pending_count -= 1
        super()._emit('after-load-plugins.building-command-table.main', {})

    def _ensure_initialized(self, event_name):
        """Initialize any plugins whose event patterns match event_name."""
        if self._pending_count == 0:
            return
        candidates = self._init_cache.get(event_name)
        if candidates is None:
            candidates = self._init_trie.prefix_search(event_name)
            self._init_cache[event_name] = candidates
            super()._emit(f'before-load-plugins.{event_name}', {})
            for entry in candidates:
                if entry not in self._initialized:
                    self._initialized.add(entry)
                    self._pending_count -= 1
                    module_path, fn_name = entry
                    logger.debug(
                        'Lazy-initializing plugin %s.%s for event %s',
                        module_path,
                        fn_name,
                        event_name,
                    )
                    mod = importlib.import_module(module_path)
                    fn = getattr(mod, fn_name)
                    fn(self)
            super()._emit(f'after-load-plugins.{event_name}', {})

    def _emit(self, event_name, kwargs, stop_on_response=False):
        if (
            self._main_ops
            and not self._main_ops_applied
            and event_name == 'building-command-table.main'
        ):
            self._main_ops_applied = True
            self._apply_main_command_table_ops(kwargs)
        self._ensure_initialized(event_name)
        return super()._emit(event_name, kwargs, stop_on_response)

    def __copy__(self):
        new_instance = self.__class__()
        new_state = self.__dict__.copy()
        new_state['_handlers'] = copy.copy(self._handlers)
        new_state['_unique_id_handlers'] = copy.copy(self._unique_id_handlers)
        new_state['_init_trie'] = copy.copy(self._init_trie)
        new_state['_initialized'] = copy.copy(self._initialized)
        new_state['_main_ops_applied'] = self._main_ops_applied
        new_instance.__dict__ = new_state
        return new_instance
