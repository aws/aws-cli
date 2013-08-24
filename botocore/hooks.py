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
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


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

    def register(self, event_name, handler, unique_id=None):
        self._verify_is_callable(handler)
        self._verify_accept_kwargs(handler)
        self._register(event_name, handler, unique_id)

    def unregister(self, event_name, handler=None, unique_id=None):
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

    def _register(self, event_name, handler, unique_id=None):
        self._handlers[event_name].append(handler)

    def unregister(self, event_name, handler, unique_id=None):
        try:
            self._handlers[event_name].remove(handler)
        except ValueError:
            pass


class HierarchicalEmitter(BaseEventHooks):
    def __init__(self):
        # We keep a reference to the handlers for quick
        # read only access (we never modify self._handlers).
        # A cache of event name to handler list.
        self._lookup_cache = {}
        self._handlers = _PrefixTrie()
        # This is used to ensure that unique_id's are only
        # registered once.
        self._unique_id_cache = {}

    def emit(self, event_name, **kwargs):
        responses = []
        # Invoke the event handlers from most specific
        # to least specific, each time stripping off a dot.
        handlers_to_call = self._lookup_cache.get(event_name)
        if handlers_to_call is None:
            handlers_to_call = self._handlers.prefix_search(event_name)
            self._lookup_cache[event_name] = handlers_to_call
        elif not handlers_to_call:
            # Short circuit and return an empty response is we have
            # no handlers to call.  This is the common case where
            # for the majority of signals, nothing is listening.
            return []
        kwargs['event_name'] = event_name
        responses = []
        for handler in handlers_to_call:
            logger.debug('Event %s: calling handler %s', event_name, handler)
            response = handler(**kwargs)
            responses.append((handler, response))
        return responses

    def _register(self, event_name, handler, unique_id=None):
        if unique_id is not None:
            if unique_id in self._unique_id_cache:
                # We've already registered a handler using this unique_id
                # so we don't need to register it again.
                return
            else:
                # Note that the trie knows nothing about the unique
                # id.  We track uniqueness in this class via the
                # _unique_id_cache.
                self._handlers.append_item(event_name, handler)
                self._unique_id_cache[unique_id] = handler
        else:
            self._handlers.append_item(event_name, handler)
        # Super simple caching strategy for now, if we change the registrations
        # clear the cache.  This has the opportunity for smarter invalidations.
        self._lookup_cache = {}

    def unregister(self, event_name, handler=None, unique_id=None):
        if unique_id is not None:
            try:
                handler = self._unique_id_cache.pop(unique_id)
            except KeyError:
                # There's no handler matching that unique_id so we have
                # nothing to unregister.
                return
        try:
            self._handlers.remove_item(event_name, handler)
            self._lookup_cache = {}
        except ValueError:
            pass


class _PrefixTrie(object):
    """Specialized prefix trie that handles wildcards.

    The prefixes in this case are based on dot separated
    names so 'foo.bar.baz' is::

        foo -> bar -> baz

    Wildcard support just means that having a key such as 'foo.bar.*.baz' will
    be matched with a call to ``get_items(key='foo.bar.ANYTHING.baz')``.

    You can think of this prefix trie as the equivalent as defaultdict(list),
    except that it can do prefix searches:

        foo.bar.baz -> A
        foo.bar -> B
        foo -> C

    Calling ``get_items('foo.bar.baz')`` will return [A + B + C], from
    most specific to least specific.

    """
    def __init__(self):
        # Each dictionary can be though of as a node, where a node
        # has values associated with the node, and children is a link
        # to more nodes.  So 'foo.bar' would have a 'foo' node with
        # a 'bar' node as a child of foo.
        # {'foo': {'children': {'bar': {...}}}}.
        self._root = {'chunk': None, 'children': {}, 'values': None}

    def append_item(self, key, value):
        """Add an item to a key.

        If a value is already associated with that key, the new
        value is appended to the list for the key.
        """
        key_parts = key.split('.')
        current = self._root
        for part in key_parts:
            if part not in current['children']:
                new_child = {'chunk': part, 'values': None, 'children': {}}
                current['children'][part] = new_child
                current = new_child
            else:
                current = current['children'][part]
        if current['values'] is None:
            current['values'] = [value]
        else:
            current['values'].append(value)

    def prefix_search(self, key):
        """Collect all items that are prefixes of key.

        Prefix in this case are delineated by '.' characters so
        'foo.bar.baz' is a 3 chunk sequence of 3 "prefixes" (
        "foo", "bar", and "baz").

        """
        collected = deque()
        key_parts = key.split('.')
        current = self._root
        self._get_items(current, key_parts, collected, 0)
        return collected

    def _get_items(self, starting_node, key_parts, collected, starting_index):
        stack = [(starting_node, starting_index)]
        key_parts_len = len(key_parts)
        # Traverse down the nodes, where at each level we add the
        # next part from key_parts as well as the wildcard element '*'.
        # This means for each node we see we potentially add two more
        # elements to our stack.
        while stack:
            current_node, index = stack.pop()
            if current_node['values']:
                seq = reversed(current_node['values'])
                # We're using extendleft because we want
                # the values associated with the node furthest
                # from the root to come before nodes closer
                # to the root.
                collected.extendleft(seq)
            if not index == key_parts_len:
                children = current_node['children']
                directs = children.get(key_parts[index])
                wildcard = children.get('*')
                next_index = index + 1
                if wildcard is not None:
                    stack.append((wildcard, next_index))
                if directs is not None:
                    stack.append((directs, next_index))

    def remove_item(self, key, value):
        """Remove an item associated with a key.

        If the value is not associated with the key a ``ValueError``
        will be raised.  If the key does not exist in the trie, a
        ``ValueError`` will be raised.

        """
        key_parts = key.split('.')
        current = self._root
        self._remove_item(current, key_parts, value, index=0)

    def _remove_item(self, current_node, key_parts, value, index):
        if current_node is None:
            return
        elif index < len(key_parts):
            next_node = current_node['children'].get(key_parts[index])
            if next_node is not None:
                self._remove_item(next_node, key_parts, value, index + 1)
                if index == len(key_parts) - 1:
                    next_node['values'].remove(value)
                if not next_node['children'] and not next_node['values']:
                    # Then this is a leaf node with no values so
                    # we can just delete this link from the parent node.
                    # This makes subsequent search faster in the case
                    # where a key does not exist.
                    del current_node['children'][key_parts[index]]
            else:
                raise ValueError(
                    "key is not in trie: %s" % '.'.join(key_parts))
