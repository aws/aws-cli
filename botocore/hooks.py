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
        # We keep a reference to the handlers for quick
        # read only access (we never modify self._handlers).
        self._handlers = event_hooks._handlers

    def emit(self, event_name, **kwargs):
        responses = []
        # Invoke the event handlers from most specific
        # to least specific, each time stripping off a dot.
        handlers_to_call = self._handlers_for_event(event_name)
        kwargs['event_name'] = event_name
        responses = []
        for handler in handlers_to_call:
            response = handler(**kwargs)
            responses.append((handler, response))
        return responses

    def _handlers_for_event(self, event):
        # Given an event name, find all the handlers we need to call
        # and return them in order.
        if '.' not in event:
            # Simplest case, no hierarchical events, just return
            # the exact match.
            return self._handlers[event]
        else:
            handlers = []
            parts = event.split('.')
            for event_name in sorted(self._handlers.keys(), reverse=True):
                event_name_split = event_name.split('.')
                if len(event_name_split) > len(parts):
                    continue
                if all(e1 == e2 for e1, e2 in zip(event_name_split, parts)):
                    handlers.extend(self._handlers[event_name])
                elif '*' in event_name:
                    for subpart, desired_subpart in zip(event_name_split,
                                                        parts):
                        if subpart == '*':
                            continue
                        if not subpart == desired_subpart:
                            break
                    else:
                        handlers.extend(self._handlers[event_name])
            return handlers

    def register(self, event_name, handler):
        return self._event_hooks.register(event_name, handler)

    def unregister(self, event_name, handler):
        return self._event_hooks.unregister(event_name, handler)
