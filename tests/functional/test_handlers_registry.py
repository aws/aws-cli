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

from awscli.handlers_registry import (
    MAIN_COMMAND_TABLE_OPS,
    PLUGIN_REGISTRY,
    CommandTableOp,
)


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


def test_all_registry_entries_are_importable():
    """Every (module, fn_name) in PLUGIN_REGISTRY must resolve to a
    callable. This catches typos, stale entries, and missing modules.
    """
    violations = []
    seen = set()
    for entries in PLUGIN_REGISTRY.values():
        for module_path, fn_name in entries:
            if (module_path, fn_name) in seen:
                continue
            seen.add((module_path, fn_name))
            try:
                mod = importlib.import_module(module_path)
            except ImportError as e:
                violations.append(f'{module_path}: {e}')
                continue
            fn = getattr(mod, fn_name, None)
            if fn is None:
                violations.append(f'{module_path}.{fn_name} does not exist')
            elif not callable(fn):
                violations.append(f'{module_path}.{fn_name} is not callable')
    assert not violations, (
        'The following PLUGIN_REGISTRY entries are invalid:\n'
        + '\n'.join(f'  - {v}' for v in violations)
    )


def test_all_main_command_table_ops_modules_are_importable():
    """Every module referenced in MAIN_COMMAND_TABLE_OPS 'add' entries
    must be importable and contain the specified class.
    """
    violations = []
    for op in MAIN_COMMAND_TABLE_OPS:
        if op[0] != CommandTableOp.ADD:
            continue
        _, cmd_name, cmd_module, cmd_class = op
        try:
            mod = importlib.import_module(cmd_module)
        except ImportError as e:
            violations.append(f'{cmd_module}: {e}')
            continue
        cls_name = cmd_class.split('.')[-1]
        if not hasattr(mod, cls_name):
            violations.append(
                f'{cmd_module}.{cls_name} does not exist '
                f'(referenced by add {cmd_name!r})'
            )
    assert not violations, (
        'The following MAIN_COMMAND_TABLE_OPS entries are invalid:\n'
        + '\n'.join(f'  - {v}' for v in violations)
    )
