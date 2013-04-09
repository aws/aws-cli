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

from awscli.hooks import EventHooks


def load_plugins(plugin_names, event_hooks=None):
    modules = _import_plugins(plugin_names)
    if event_hooks is None:
        event_hooks = EventHooks()
    cli = CLI(event_hooks)
    for plugin in modules:
        plugin.awscli_initialize(cli)
    return HierarchicalEmitter(event_hooks)


def _import_plugins(plugin_names):
    plugins = []
    for name in plugin_names:
        if '.' not in name:
            plugins.append(__import__(name))
    return plugins


class HierarchicalEmitter(object):
    def __init__(self, event_hooks):
        self._event_hooks = event_hooks

    def emit(self, event):
        responses = []
        # Invoke the event handlers from most specific
        # to least specific, each time stripping off a dot.
        while event:
            responses.extend(self._event_hooks.emit(event))
            next_event = event.rsplit('.', 1)
            if len(next_event) == 2:
                event = next_event[0]
            else:
                event = None
        return responses


class CLI(object):
    def __init__(self, event_hooks):
        self._event_hooks = event_hooks

    def before_call(self, handler, service_name=None, operation_name=None):
        op_event_name = self._get_event_name(service_name, operation_name)
        if op_event_name:
            event_name = 'before_call.%s' % op_event_name
        else:
            event_name = 'before_call'
        self._event_hooks.register(event_name, handler)

    def after_call(self, handler, service_name=None, operation_name=None):
        op_event_name = self._get_event_name(service_name, operation_name)
        if op_event_name:
            event_name = 'after_call.%s' % op_event_name
        else:
            event_name = 'after_call'
        self._event_hooks.register(event_name, handler)

    def _get_event_name(self, service_name, operation_name):
        if service_name is None:
            return ''
        if service_name is not None and operation_name is None:
            return service_name
        elif service_name is not None and operation_name is not None:
            return '%s.%s' % (service_name, operation_name)
