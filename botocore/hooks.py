# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import inspect
import six
from collections import defaultdict


class BaseEventHooks(object):
    def emit(self, event_name, **kwargs):
        return []

    def register(self, event_name, handler):
        pass

    def unregister(self, event_name, handler):
        pass


class EventHooks(BaseEventHooks):
    def __init__(self):
        # event_name -> [handler, ...]
        self._handlers = defaultdict(list)

    def emit(self, event_name, **kwargs):
        """Call all handlers subscribed to an event.

        :type event_name: str
        :param event_name: The name of the event to emit.

        :type **kwargs: dict
        :param **kwargs: Arbitrary kwargs to pass through to the
            subscribed handlers.  The ``event_name`` will be injected
            into the kwargs so it's not necesary to add this to **kwargs.

        :rtype: list of tuples
        :return: A list of ``(handler_func, handler_func_return_value)``

        """
        kwargs['event_name'] = event_name
        responses = []
        for handler in self._handlers[event_name]:
            response = handler(**kwargs)
            responses.append((handler, response))
        return responses

    def register(self, event_name, handler):
        self._verify_is_callable(handler)
        self._verify_accept_kwargs(handler)
        self._handlers[event_name].append(handler)

    def unregister(self, event_name, handler):
        try:
            self._handlers[event_name].remove(handler)
        except ValueError:
            pass

    def _verify_is_callable(self, func):
        if not six.callable(func):
            raise ValueError("Event handler %s must be callable." % func)

    def _verify_accept_kwargs(self, func):
        """Verifies a callable accepts kwargs

        :type func: callable
        :param func: A callable object.

        :returns: True, if ``func`` accepts kwargs, otherwise False.

        """
        try:
            argspec = inspect.getargspec(func)
        except TypeError:
            return False
        else:
            if argspec[2] is None:
                raise ValueError("Event handler %s must accept keyword "
                                 "arguments (**kwargs)" % func)


class HierarchicalEmitter(BaseEventHooks):
    def __init__(self, event_hooks):
        self._event_hooks = event_hooks

    def emit(self, event, **kwargs):
        responses = []
        # Invoke the event handlers from most specific
        # to least specific, each time stripping off a dot.
        while event:
            responses.extend(self._event_hooks.emit(event, **kwargs))
            next_event = event.rsplit('.', 1)
            if len(next_event) == 2:
                event = next_event[0]
            else:
                event = None
        return responses

    def register(self, event_name, handler):
        return self._event_hooks.register(event_name, handler)

    def unregister(self, event_name, handler):
        return self._event_hooks.unregister(event_name, handler)
