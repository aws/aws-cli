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

from botocore.hooks import HierarchicalEmitter

log = logging.getLogger('awscli.plugin')

BUILTIN_PLUGINS = {'__builtin__': 'awscli.handlers'}


def load_plugins(plugin_mapping, event_hooks=None, include_builtins=True):
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
        plugin_mapping.update(BUILTIN_PLUGINS)
    modules = _import_plugins(plugin_mapping)
    if event_hooks is None:
        event_hooks = HierarchicalEmitter()
    for name, plugin in zip(plugin_mapping.keys(), modules):
        log.debug("Initializing plugin %s: %s", name, plugin)
        plugin.awscli_initialize(event_hooks)
    return event_hooks


def _import_plugins(plugin_names):
    plugins = []
    for name, path in plugin_names.items():
        log.debug("Importing plugin %s: %s", name, path)
        if '.' not in path:
            plugins.append(__import__(path))
        else:
            package, module = path.rsplit('.', 1)
            module = __import__(path, fromlist=[module])
            plugins.append(module)
    return plugins
