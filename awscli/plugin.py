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


def first_non_none_response(responses, default=None):
    """Find first non None response in a list of tuples.

    This function can be used to find the first non None response from
    handlers connected to an event.  This is useful if you are interested
    in the returned responses from event handlers. Example usage::

        print(first_non_none_response([(func1, None), (func2, 'foo'),
                                       (func3, 'bar')]))
        # This will print 'foo'

    :type responses: list of tuples
    :param responses: The responses from the ``EventHooks.emit`` method.
        This is a list of tuples, and each tuple is
        (handler, handler_response).

    :param default: If no non-None responses are found, then this default
        value will be returned.

    :return: The first non-None response in the list of tuples.

    """
    for response in responses:
        if response[1] is not None:
            return response[1]
    return default


class CLI(object):
    def __init__(self, event_hooks):
        self._event_hooks = event_hooks

    def register(self, event_name, handler):
        self._event_hooks.register(event_name, handler)
