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
import importlib
from collections import OrderedDict

import botocore.session

from awscli.handlers_registry import PLUGIN_REGISTRY


class _AuditEmitter:
    """Minimal emitter that records event names without side effects."""

    def __init__(self):
        self.registrations = []

    def register(self, event_name, *args, **kwargs):
        self.registrations.append(event_name)

    register_first = register
    register_last = register


class _CallbackCollector:
    """Emitter that captures callbacks registered against a specific event."""

    def __init__(self, target_event):
        self._target_event = target_event
        self.callbacks = []

    def register(self, event_name, handler, *args, **kwargs):
        if event_name == self._target_event:
            self.callbacks.append(handler)

    register_first = register
    register_last = register


def test_main_command_table_plugins_only_register_against_main():
    """Plugins listed under building-command-table.main must not register
    against any other events.

    This invariant allows the lazy-loading system to skip importing these
    plugin modules entirely and instead apply pre-computed renames and
    LazyCommand additions from MAIN_COMMAND_TABLE_OPS.  If a plugin
    mixes building-command-table.main registrations with other events,
    split it into separate functions: one that only registers against
    building-command-table.main, and another for the remaining events.
    """
    main_entries = PLUGIN_REGISTRY.get('building-command-table.main', [])
    violations = []
    for module_path, fn_name, entry_type in main_entries:
        emitter = _AuditEmitter()
        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name)
        fn(emitter)
        non_main = [
            e for e in emitter.registrations
            if e != 'building-command-table.main'
        ]
        if non_main:
            violations.append(
                f'{module_path}.{fn_name} also registers against: '
                f'{non_main}'
            )
    assert not violations, (
        'The following building-command-table.main plugins register '
        'against additional events. Split each into separate functions '
        'so that the building-command-table.main function only registers '
        'against that single event:\n'
        + '\n'.join(f'  - {v}' for v in violations)
    )


def test_main_command_table_callbacks_only_add_or_rename():
    """Callbacks registered against building-command-table.main must only
    add new commands or rename existing ones.

    MAIN_COMMAND_TABLE_OPS replaces these callbacks at runtime with
    LazyCommand additions and direct renames.  If a callback also
    modifies existing command table entries (e.g. changes properties on
    a command object), that modification would be silently lost.
    """
    session = botocore.session.Session()
    services = session.get_available_services()

    main_entries = PLUGIN_REGISTRY.get('building-command-table.main', [])
    violations = []

    for module_path, fn_name, entry_type in main_entries:
        collector = _CallbackCollector('building-command-table.main')
        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name)
        fn(collector)

        for callback in collector.callbacks:
            cb_name = f'{callback.__module__}.{callback.__qualname__}'

            # Build a fresh command table for each callback.
            class _Placeholder:
                def __init__(self, name):
                    self.name = name

            command_table = OrderedDict()
            for svc in services:
                command_table[svc] = _Placeholder(svc)

            snap_id_to_key = {id(v): k for k, v in command_table.items()}
            snap_id_to_name = {id(v): v.name for k, v in command_table.items()}

            callback(command_table=command_table, session=session)

            # Classify every change.
            new_id_to_key = {id(v): k for k, v in command_table.items()}
            renamed_ids = set()

            # Detect renames.
            for obj_id, new_key in new_id_to_key.items():
                old_key = snap_id_to_key.get(obj_id)
                if old_key is not None and old_key != new_key:
                    renamed_ids.add(obj_id)

            # Detect modifications: an existing (non-renamed) entry whose
            # .name property changed, or any entry that was removed.
            for obj_id, old_key in snap_id_to_key.items():
                if obj_id in renamed_ids:
                    continue
                if obj_id not in new_id_to_key:
                    violations.append(
                        f'{cb_name} removed command {old_key!r}'
                    )
                    continue
                new_key = new_id_to_key[obj_id]
                cmd = command_table[new_key]
                if cmd.name != snap_id_to_name[obj_id]:
                    violations.append(
                        f'{cb_name} modified .name on {new_key!r} '
                        f'without renaming'
                    )

    assert not violations, (
        'Callbacks registered against building-command-table.main must '
        'only add or rename commands. The following callbacks perform '
        'other modifications that would be lost when replaced by '
        'MAIN_COMMAND_TABLE_OPS:\n'
        + '\n'.join(f'  - {v}' for v in violations)
    )
