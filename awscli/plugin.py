# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging

from typing import Dict, Optional
from botocore.hooks import HierarchicalEmitter

log = logging.getLogger('awscli.plugin')

BUILTIN_PLUGINS = {'__builtin__': 'awscli.handlers'}


def load_plugins(
    plugin_mapping: Dict[str, str],
    event_hooks: Optional[HierarchicalEmitter] = None,
    include_builtins: bool = True
) -> HierarchicalEmitter:
    """

    :type plugin_mapping: dict
    :param plugin_mapping: A dict of plugin name to import path,
        e.g. ``{"plugingName": "package.modulefoo"}``.

    :type event_hooks: ``EventHooks``
    :param event_hooks: Event hook emitter.  If one if not provided,
        an emitter will be created and returned.  Otherwise, the
        passed in ``event_hooks`` will be used to initialize plugins.

    :type include_builtins: bool
    :param include_builtins: If True, the builtin awscli plugins (specified in
        ``BUILTIN_PLUGINS``) will be included in the list of plugins to load.

    :rtype: HierarchicalEmitter
    :return: An event emitter object.

    """
    if include_builtins:
        plugin_mapping = {**plugin_mapping, **BUILTIN_PLUGINS}  # Avoid mutating input
    modules = _import_plugins(plugin_mapping)
    if event_hooks is None:
        event_hooks = HierarchicalEmitter()
    for name, plugin in zip(plugin_mapping.keys(), modules):
        log.debug("Initializing plugin %s: %s", name, plugin)
        if not hasattr(plugin, 'awscli_initialize'):
            log.error("Plugin %s does not have an awscli_initialize method.", name)
            continue
        plugin.awscli_initialize(event_hooks)
    log.info("Successfully initialized %d plugins.", len(modules))
    return event_hooks

def _import_module(path: str):
    if '.' not in path:
        return __import__(path)
    package, module = path.rsplit('.', 1)
    return __import__(path, fromlist=[module])

def _import_plugins(plugin_names: Dict[str, str]):
    plugins = []
    for name, path in plugin_names.items():
        log.debug("Importing plugin %s: %s", name, path)
        try:
            plugins.append(_import_module(path))
        except ImportError as e:
            log.error("Failed to import plugin %s: %s", name, e)
    return plugins