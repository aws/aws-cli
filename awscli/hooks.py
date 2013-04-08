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
import inspect
import six
from collections import defaultdict


class EventHooks(object):
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

