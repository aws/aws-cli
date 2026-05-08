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
"""Built-in CLI extensions.

Load built-in CLI extensions from the plugin registry
(`awscli/handlers_registry.py`). If the supplied event handler is a
LazyInitEmitter, we load the registry so that the LazyInitEmitter can handle
lazy plugin initialization. Otherwise, we fall back to loading all plugins in
the registry eagerly.
"""
from awscli.handlers_registry import PLUGIN_REGISTRY


def awscli_initialize(event_handlers):
    """Load the plugin registry into the emitter.

    If the emitter is a LazyInitEmitter, the registry is loaded into its
    initializer trie for on-demand initialization. Otherwise, all built-in
    plugins are eagerly initialized.
    """
    from awscli.lazy_emitter import LazyInitEmitter
    if isinstance(event_handlers, LazyInitEmitter):
        event_handlers.load_registry(PLUGIN_REGISTRY)
    else:
        # Fallback to eagerly initializing all built-in plugins.
        import importlib
        seen = set()
        for event_pattern, entries in PLUGIN_REGISTRY.items():
            for entry in entries:
                if entry not in seen:
                    seen.add(entry)
                    module_path, fn_name, entry_type = entry
                    mod = importlib.import_module(module_path)
                    fn = getattr(mod, fn_name)
                    if entry_type == 'direct':
                        handler = fn() if isinstance(fn, type) else fn
                        event_handlers.register(event_pattern, handler)
                    else:
                        if isinstance(fn, type):
                            fn(event_handlers)
                        else:
                            fn(event_handlers)
