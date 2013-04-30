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

from botocore.hooks import EventHooks, HierarchicalEmitter

log = logging.getLogger('awscli.plugin')


def load_plugins(plugin_mapping, event_hooks=None):
    """

    :type plugin_mapping: dict
    :param plugin_mapping: A dict of plugin name to import path,
        e.g. ``{"plugingName": "package.modulefoo"}``.

    :type event_hooks: ``EventHooks``
    :param event_hooks: Event hook emitter.

    :rtype: HierarchicalEmitter
    :return: An event emitter object.

    """
    modules = _import_plugins(plugin_mapping)
    if event_hooks is None:
        event_hooks = EventHooks()
    cli = CLI(event_hooks)
    for name, plugin in zip(plugin_mapping.keys(), modules):
        log.debug("Initializing plugin %s: %s", name, plugin)
        plugin.awscli_initialize(cli)
    return HierarchicalEmitter(event_hooks)


def _import_plugins(plugin_names):
    plugins = []
    for name, path in plugin_names.items():
        log.debug("Importing plugin %s: %s", name, path)
        if '.' not in name:
            plugins.append(__import__(path))
    return plugins


class CLI(object):
    def __init__(self, event_hooks):
        self._event_hooks = event_hooks

    def register(self, event_name, handler):
        self._event_hooks.register(event_name, handler)
