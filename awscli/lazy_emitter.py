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
to initialize plugins on demand.  Before emitting event X, it finds all
initializer entries whose event patterns match X (using the same
prefix/wildcard semantics as HierarchicalEmitter), calls each initializer
at most once, then delegates to the underlying emitter for normal dispatch.
"""
import copy
import importlib
import logging

from botocore.hooks import HierarchicalEmitter, _PrefixTrie

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
        self._init_trie = _PrefixTrie()
        self._initialized = set()  # set of (module, fn_name, type)
        self._pending_count = 0  # number of entries not yet initialized
        self._init_cache = {}  # event_name -> list of entries from init trie
        self._direct_patterns = {}  # event_pattern -> set of entries
        self._main_ops = main_command_table_ops
        self._main_ops_applied = False
        if plugin_registry:
            self._load_registry(plugin_registry)

    def _load_registry(self, registry):
        unique = set()
        for event_pattern, entries in registry.items():
            for entry in entries:
                self._init_trie.append_item(event_pattern, entry)
                if entry[2] == 'direct':
                    self._direct_patterns.setdefault(
                        event_pattern, set()
                    ).add(entry)
                if entry not in unique:
                    unique.add(entry)
                    self._pending_count += 1
        self._init_cache = {}

    def _apply_main_command_table_ops(self, kwargs):
        """Apply pre-computed renames and LazyCommand additions.

        This replaces the normal lazy-init path for
        building-command-table.main entries, avoiding the import of
        heavy plugin modules until the command is actually invoked.
        """
        from awscli.lazy import LazyCommand

        command_table = kwargs.get('command_table')
        session = kwargs.get('session')
        if command_table is None or session is None:
            return

        for op in self._main_ops:
            if op[0] == 'rename':
                _, old_name, new_name, _mod, _fn = op
                if old_name in command_table:
                    current = command_table[old_name]
                    command_table[new_name] = current
                    current.name = new_name
                    del command_table[old_name]
            elif op[0] == 'add':
                _, cmd_name, cmd_module, cmd_class, _mod, _fn = op
                command_table[cmd_name] = LazyCommand(
                    cmd_name, session, cmd_module, cmd_class,
                )

        # Mark only the building-command-table.main entries that are
        # accounted for by MAIN_COMMAND_TABLE_OPS as initialized, so
        # _ensure_initialized never imports them.  Entries that register
        # against building-command-table.main but are NOT represented
        # by an add/rename op must still be lazily initialized normally.
        covered_plugins = set()
        for op in self._main_ops:
            if op[0] == 'rename':
                covered_plugins.add((op[3], op[4]))
            elif op[0] == 'add':
                covered_plugins.add((op[4], op[5]))
        from awscli.handlers_registry import PLUGIN_REGISTRY
        for entry in PLUGIN_REGISTRY.get('building-command-table.main', []):
            entry = tuple(entry)
            if (entry[0], entry[1]) in covered_plugins:
                if entry not in self._initialized:
                    self._initialized.add(entry)
                    self._pending_count -= 1

    def _ensure_initialized(self, event_name):
        """Initialize any plugins whose event patterns match event_name."""
        if self._pending_count == 0:
            return
        candidates = self._init_cache.get(event_name)
        if candidates is None:
            candidates = self._init_trie.prefix_search(event_name)
            self._init_cache[event_name] = candidates
        for entry in candidates:
            if entry not in self._initialized:
                import awscli.perf_timer as T
                self._initialized.add(entry)
                self._pending_count -= 1
                module_path, fn_name, entry_type = entry
                logger.debug(
                    'Lazy-initializing plugin %s.%s (%s) for event %s',
                    module_path, fn_name, entry_type, event_name,
                )
                with T.timer(f"init_import:{module_path}:{fn_name}"):
                    mod = importlib.import_module(module_path)
                    fn = getattr(mod, fn_name)
                with T.timer(f"init_register:{module_path}:{fn_name}"):
                    if entry_type == 'direct':
                        # Direct handler: register fn as a handler for the
                        # event pattern it was originally associated with.
                        # For classes (e.g. ParamShorthandParser), instantiate.
                        handler = fn() if isinstance(fn, type) else fn
                        # Find the event pattern this entry was stored under.
                        # We need to register against the original pattern,
                        # not the emitted event_name.
                        self._register_direct_handler(entry, handler)
                    else:
                        # Initializer function: call fn(event_handlers)
                        if isinstance(fn, type):
                            fn(self)
                        else:
                            fn(self)

    def _register_direct_handler(self, entry, handler):
        """Register a direct handler against its original event pattern."""
        for event_pattern, entries in self._direct_patterns.items():
            if entry in entries:
                self.register(event_pattern, handler)
                return

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
        new_state['_direct_patterns'] = copy.copy(self._direct_patterns)
        new_state['_init_trie'] = copy.copy(self._init_trie)
        new_state['_initialized'] = copy.copy(self._initialized)
        new_state['_main_ops_applied'] = self._main_ops_applied
        new_instance.__dict__ = new_state
        return new_instance
