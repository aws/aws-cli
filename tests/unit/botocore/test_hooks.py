# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import copy
import functools

from tests import unittest
from functools import partial

from botocore.hooks import HierarchicalEmitter, first_non_none_response


class TestHierarchicalEventEmitter(unittest.TestCase):
    def setUp(self):
        self.emitter = HierarchicalEmitter()
        self.hook_calls = []

    def hook(self, **kwargs):
        self.hook_calls.append(kwargs)

    def test_non_dot_behavior(self):
        self.emitter.register('no-dot', self.hook)
        self.emitter.emit('no-dot')
        self.assertEqual(len(self.hook_calls), 1)

    def test_with_dots(self):
        self.emitter.register('foo.bar.baz', self.hook)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 1)

    def test_catch_all_hook(self):
        self.emitter.register('foo', self.hook)
        self.emitter.register('foo.bar', self.hook)
        self.emitter.register('foo.bar.baz', self.hook)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 3, self.hook_calls)
        # The hook is called with the same event name three times.
        self.assertEqual([e['event_name'] for e in self.hook_calls],
                         ['foo.bar.baz', 'foo.bar.baz', 'foo.bar.baz'])

    def test_hook_called_in_proper_order(self):
        # We should call the hooks from most specific to least
        # specific.
        calls = []
        self.emitter.register('foo', lambda **kwargs: calls.append('foo'))
        self.emitter.register('foo.bar',
                              lambda **kwargs: calls.append('foo.bar'))
        self.emitter.register('foo.bar.baz',
                              lambda **kwargs: calls.append('foo.bar.baz'))

        self.emitter.emit('foo.bar.baz')
        self.assertEqual(calls, ['foo.bar.baz', 'foo.bar', 'foo'])


class TestStopProcessing(unittest.TestCase):
    def setUp(self):
        self.emitter = HierarchicalEmitter()
        self.hook_calls = []

    def hook1(self, **kwargs):
        self.hook_calls.append('hook1')

    def hook2(self, **kwargs):
        self.hook_calls.append('hook2')
        return 'hook2-response'

    def hook3(self, **kwargs):
        self.hook_calls.append('hook3')
        return 'hook3-response'

    def test_all_hooks(self):
        # Here we register three hooks and sanity check
        # that all three would be called by a normal emit.
        # This ensures our hook calls are setup properly for
        # later tests.
        self.emitter.register('foo', self.hook1)
        self.emitter.register('foo', self.hook2)
        self.emitter.register('foo', self.hook3)
        self.emitter.emit('foo')

        self.assertEqual(self.hook_calls, ['hook1', 'hook2', 'hook3'])

    def test_stop_processing_after_first_response(self):
        # Here we register three hooks, but only the first
        # two should ever execute.
        self.emitter.register('foo', self.hook1)
        self.emitter.register('foo', self.hook2)
        self.emitter.register('foo', self.hook3)
        handler, response = self.emitter.emit_until_response('foo')

        self.assertEqual(response, 'hook2-response')
        self.assertEqual(self.hook_calls, ['hook1', 'hook2'])

    def test_no_responses(self):
        # Here we register a handler that will not return a response
        # and ensure we get back proper values.
        self.emitter.register('foo', self.hook1)
        responses = self.emitter.emit('foo')

        self.assertEqual(self.hook_calls, ['hook1'])
        self.assertEqual(responses, [(self.hook1, None)])

    def test_no_handlers(self):
        # Here we have no handlers, but still expect a tuple of return
        # values.
        handler, response = self.emitter.emit_until_response('foo')

        self.assertIsNone(handler)
        self.assertIsNone(response)


class TestFirstNonNoneResponse(unittest.TestCase):
    def test_all_none(self):
        self.assertIsNone(first_non_none_response([]))

    def test_first_non_none(self):
        correct_value = 'correct_value'
        wrong_value = 'wrong_value'
        # The responses are tuples of (handler, response),
        # and we don't care about the handler so we just use a value of
        # None.
        responses = [(None, None), (None, correct_value), (None, wrong_value)]
        self.assertEqual(first_non_none_response(responses), correct_value)

    def test_default_value_if_non_none_found(self):
        responses = [(None, None), (None, None)]
        # If no response is found and a default value is passed in, it will
        # be returned.
        self.assertEqual(
            first_non_none_response(responses, default='notfound'), 'notfound')


class TestWildcardHandlers(unittest.TestCase):
    def setUp(self):
        self.emitter = HierarchicalEmitter()
        self.hook_calls = []

    def hook(self, **kwargs):
        self.hook_calls.append(kwargs)

    def register(self, event_name):
        func = partial(self.hook, registered_with=event_name)
        self.emitter.register(event_name, func)
        return func

    def assert_hook_is_called_given_event(self, event):
        starting = len(self.hook_calls)
        self.emitter.emit(event)
        after = len(self.hook_calls)
        if not after > starting:
            self.fail("Handler was not called for event: %s" % event)
        self.assertEqual(self.hook_calls[-1]['event_name'], event)

    def assert_hook_is_not_called_given_event(self, event):
        starting = len(self.hook_calls)
        self.emitter.emit(event)
        after = len(self.hook_calls)
        if not after == starting:
            self.fail("Handler was called for event but was not "
                      "suppose to be called: %s, last_event: %s" %
                      (event, self.hook_calls[-1]))

    def test_one_level_wildcard_handler(self):
        self.emitter.register('foo.*.baz', self.hook)
        # Also register for a number of other events to check
        # for false positives.
        self.emitter.register('other.bar.baz', self.hook)
        self.emitter.register('qqq.baz', self.hook)
        self.emitter.register('dont.call.me', self.hook)
        self.emitter.register('dont', self.hook)
        # These calls should trigger our hook.
        self.assert_hook_is_called_given_event('foo.bar.baz')
        self.assert_hook_is_called_given_event('foo.qux.baz')
        self.assert_hook_is_called_given_event('foo.anything.baz')

        # These calls should not match our hook.
        self.assert_hook_is_not_called_given_event('foo')
        self.assert_hook_is_not_called_given_event('foo.bar')
        self.assert_hook_is_not_called_given_event('bar.qux.baz')
        self.assert_hook_is_not_called_given_event('foo-bar')

    def test_hierarchical_wildcard_handler(self):
        self.emitter.register('foo.*.baz', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.qux')
        self.assert_hook_is_called_given_event('foo.bar.baz.qux.foo')
        self.assert_hook_is_called_given_event('foo.qux.baz.qux')
        self.assert_hook_is_called_given_event('foo.qux.baz.qux.foo')

        self.assert_hook_is_not_called_given_event('bar.qux.baz.foo')

    def test_multiple_wildcard_events(self):
        self.emitter.register('foo.*.*.baz', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_called_given_event('foo.ANY.THING.baz')
        self.assert_hook_is_called_given_event('foo.AT.ALL.baz')

        # More specific than what we registered for.
        self.assert_hook_is_called_given_event('foo.bar.baz.baz.extra')
        self.assert_hook_is_called_given_event('foo.bar.baz.baz.extra.stuff')

        # Too short:
        self.assert_hook_is_not_called_given_event('foo')
        self.assert_hook_is_not_called_given_event('foo.bar')
        self.assert_hook_is_not_called_given_event('foo.bar.baz')

        # Bad ending segment.
        self.assert_hook_is_not_called_given_event('foo.ANY.THING.notbaz')
        self.assert_hook_is_not_called_given_event('foo.ANY.THING.stillnotbaz')

    def test_can_unregister_for_wildcard_events(self):
        self.emitter.register('foo.*.*.baz', self.hook)
        # Call multiple times to verify caching behavior.
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')

        self.emitter.unregister('foo.*.*.baz', self.hook)
        self.assert_hook_is_not_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_not_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_not_called_given_event('foo.bar.baz.baz')

        self.emitter.register('foo.*.*.baz', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')

    def test_unregister_does_not_exist(self):
        self.emitter.register('foo.*.*.baz', self.hook)
        self.emitter.unregister('foo.*.*.baz', self.hook)
        self.emitter.unregister('foo.*.*.baz', self.hook)
        self.assert_hook_is_not_called_given_event('foo.bar.baz.baz')

    def test_cache_cleared_properly(self):
        self.emitter.register('foo.*.*.baz', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')

        self.emitter.register('foo.*.*.bar', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.baz')
        self.assert_hook_is_called_given_event('foo.bar.baz.bar')

        self.emitter.unregister('foo.*.*.baz', self.hook)
        self.assert_hook_is_called_given_event('foo.bar.baz.bar')
        self.assert_hook_is_not_called_given_event('foo.bar.baz.baz')

    def test_complicated_register_unregister(self):
        r = self.emitter.register
        u = partial(self.emitter.unregister, handler=self.hook)
        r('foo.bar.baz.qux', self.hook)
        r('foo.bar.baz', self.hook)
        r('foo.bar', self.hook)
        r('foo', self.hook)

        u('foo.bar.baz')
        u('foo')
        u('foo.bar')

        self.assert_hook_is_called_given_event('foo.bar.baz.qux')

        self.assert_hook_is_not_called_given_event('foo.bar.baz')
        self.assert_hook_is_not_called_given_event('foo.bar')
        self.assert_hook_is_not_called_given_event('foo')

    def test_register_multiple_handlers_for_same_event(self):
        self.emitter.register('foo.bar.baz', self.hook)
        self.emitter.register('foo.bar.baz', self.hook)

        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 2)

    def test_register_with_unique_id(self):
        self.emitter.register('foo.bar.baz', self.hook, unique_id='foo')
        # Since we're using the same unique_id, this registration is ignored.
        self.emitter.register('foo.bar.baz', self.hook, unique_id='foo')
        # This also works across event names, so this registration is ignored
        # as well.
        self.emitter.register('foo.other', self.hook, unique_id='foo')

        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 1)

        self.hook_calls = []

        self.emitter.emit('foo.other')
        self.assertEqual(len(self.hook_calls), 0)

    def test_remove_handler_with_unique_id(self):
        hook2 = lambda **kwargs: self.hook_calls.append(kwargs)
        self.emitter.register('foo.bar.baz', self.hook, unique_id='foo')
        self.emitter.register('foo.bar.baz', hook2)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 2)

        # Reset the hook calls.
        self.hook_calls = []

        self.emitter.unregister('foo.bar.baz', hook2)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 1)

        self.hook_calls = []

        # Can provide the unique_id to unregister.
        self.emitter.unregister('foo.bar.baz', unique_id='foo')
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 0)

        # Same as with not specifying a unique_id, you can call
        # unregister multiple times and not get an exception.
        self.emitter.unregister('foo.bar.baz', unique_id='foo')

    def test_remove_handler_with_and_without_unique_id(self):
        self.emitter.register('foo.bar.baz', self.hook, unique_id='foo')
        self.emitter.register('foo.bar.baz', self.hook)

        self.emitter.unregister('foo.bar.baz', self.hook)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 1)

        self.hook_calls = []

        self.emitter.unregister('foo.bar.baz', self.hook)
        self.emitter.emit('foo.bar.baz')
        self.assertEqual(len(self.hook_calls), 0)

    def test_register_with_uses_count_initially(self):
        self.emitter.register('foo', self.hook, unique_id='foo',
                              unique_id_uses_count=True)
        # Subsequent calls must set ``unique_id_uses_count`` to True.
        with self.assertRaises(ValueError):
            self.emitter.register('foo', self.hook, unique_id='foo')

    def test_register_with_uses_count_not_initially(self):
        self.emitter.register('foo', self.hook, unique_id='foo')
        # Subsequent calls must set ``unique_id_uses_count`` to False.
        with self.assertRaises(ValueError):
            self.emitter.register('foo', self.hook, unique_id='foo',
                                  unique_id_uses_count=True)

    def test_register_with_uses_count_unregister(self):
        self.emitter.register('foo', self.hook, unique_id='foo',
                              unique_id_uses_count=True)
        self.emitter.register('foo', self.hook, unique_id='foo',
                              unique_id_uses_count=True)
        # Event was registered to use a count so it must be specified
        # that a count is used when unregistering
        with self.assertRaises(ValueError):
            self.emitter.unregister('foo', self.hook, unique_id='foo')
        # Event should not have been unregistered.
        self.emitter.emit('foo')
        self.assertEqual(len(self.hook_calls), 1)
        self.emitter.unregister('foo', self.hook, unique_id='foo',
                                unique_id_uses_count=True)
        # Event still should not be unregistered.
        self.hook_calls = []
        self.emitter.emit('foo')
        self.assertEqual(len(self.hook_calls), 1)
        self.emitter.unregister('foo', self.hook, unique_id='foo',
                                unique_id_uses_count=True)
        # Now the event should be unregistered.
        self.hook_calls = []
        self.emitter.emit('foo')
        self.assertEqual(len(self.hook_calls), 0)

    def test_register_with_no_uses_count_unregister(self):
        self.emitter.register('foo', self.hook, unique_id='foo')
        # The event was not registered to use a count initially
        with self.assertRaises(ValueError):
            self.emitter.unregister('foo', self.hook, unique_id='foo',
                                    unique_id_uses_count=True)

    def test_handlers_called_in_order(self):
        def handler(call_number, **kwargs):
            kwargs['call_number'] = call_number
            self.hook_calls.append(kwargs)

        self.emitter.register('foo', partial(handler, call_number=1))
        self.emitter.register('foo', partial(handler, call_number=2))
        self.emitter.emit('foo')
        self.assertEqual([k['call_number'] for k in self.hook_calls],
                         [1, 2])

    def test_handler_call_order_with_hierarchy(self):
        def handler(call_number, **kwargs):
            kwargs['call_number'] = call_number
            self.hook_calls.append(kwargs)

        # We go from most specific to least specific, and each level is called
        # in the order they were registered for that particular hierarchy
        # level.
        self.emitter.register('foo.bar.baz', partial(handler, call_number=1))
        self.emitter.register('foo.bar', partial(handler, call_number=3))
        self.emitter.register('foo', partial(handler, call_number=5))
        self.emitter.register('foo.bar.baz', partial(handler, call_number=2))
        self.emitter.register('foo.bar', partial(handler, call_number=4))
        self.emitter.register('foo', partial(handler, call_number=6))

        self.emitter.emit('foo.bar.baz')
        self.assertEqual([k['call_number'] for k in self.hook_calls],
                         [1, 2, 3, 4, 5, 6])

    def test_register_first_single_level(self):
        def handler(call_number, **kwargs):
            kwargs['call_number'] = call_number
            self.hook_calls.append(kwargs)

        # Handlers registered through register_first() are always called
        # before handlers registered with register().
        self.emitter.register('foo', partial(handler, call_number=3))
        self.emitter.register('foo', partial(handler, call_number=4))
        self.emitter.register_first('foo', partial(handler, call_number=1))
        self.emitter.register_first('foo', partial(handler, call_number=2))
        self.emitter.register('foo', partial(handler, call_number=5))

        self.emitter.emit('foo')
        self.assertEqual([k['call_number'] for k in self.hook_calls],
                         [1, 2, 3, 4, 5])

    def test_register_first_hierarchy(self):
        def handler(call_number, **kwargs):
            kwargs['call_number'] = call_number
            self.hook_calls.append(kwargs)

        self.emitter.register('foo', partial(handler, call_number=5))
        self.emitter.register('foo.bar', partial(handler, call_number=2))

        self.emitter.register_first('foo', partial(handler, call_number=4))
        self.emitter.register_first('foo.bar', partial(handler, call_number=1))

        self.emitter.register('foo', partial(handler, call_number=6))
        self.emitter.register('foo.bar', partial(handler, call_number=3))

        self.emitter.emit('foo.bar')
        self.assertEqual([k['call_number'] for k in self.hook_calls],
                         [1, 2, 3, 4, 5, 6])

    def test_register_last_hierarchy(self):
        def handler(call_number, **kwargs):
            kwargs['call_number'] = call_number
            self.hook_calls.append(kwargs)

        self.emitter.register_last('foo', partial(handler, call_number=3))
        self.emitter.register('foo', partial(handler, call_number=2))
        self.emitter.register_first('foo', partial(handler, call_number=1))
        self.emitter.emit('foo')
        self.assertEqual([k['call_number'] for k in self.hook_calls],
                         [1, 2, 3])

    def test_register_unregister_first_last(self):
        self.emitter.register('foo', self.hook)
        self.emitter.register_last('foo.bar', self.hook)
        self.emitter.register_first('foo.bar.baz', self.hook)

        self.emitter.unregister('foo.bar.baz', self.hook)
        self.emitter.unregister('foo.bar', self.hook)
        self.emitter.unregister('foo', self.hook)

        self.emitter.emit('foo')
        self.assertEqual(self.hook_calls, [])

    def test_copy_emitter(self):
        # Here we're not testing copy directly, we're testing
        # the observable behavior from copying an event emitter.
        first = []
        def first_handler(id_name, **kwargs):
            first.append(id_name)

        second = []
        def second_handler(id_name, **kwargs):
            second.append(id_name)

        self.emitter.register('foo.bar.baz', first_handler)
        # First time we emit, only the first handler should be called.
        self.emitter.emit('foo.bar.baz', id_name='first-time')
        self.assertEqual(first, ['first-time'])
        self.assertEqual(second, [])

        copied_emitter = copy.copy(self.emitter)
        # If we emit from the copied emitter, we should still
        # only see the first handler called.
        copied_emitter.emit('foo.bar.baz', id_name='second-time')
        self.assertEqual(first, ['first-time', 'second-time'])
        self.assertEqual(second, [])

        # However, if we register an event handler with the copied
        # emitter, the first emitter will not see this.
        copied_emitter.register('foo.bar.baz', second_handler)

        copied_emitter.emit('foo.bar.baz', id_name='third-time')
        self.assertEqual(first, ['first-time', 'second-time', 'third-time'])
        # And now the second handler is called.
        self.assertEqual(second, ['third-time'])

        # And vice-versa, emitting from the original emitter
        # will not trigger the second_handler.
        # We'll double check this by unregistering/re-registering
        # the event handler.
        self.emitter.unregister('foo.bar.baz', first_handler)
        self.emitter.register('foo.bar.baz', first_handler)
        self.emitter.emit('foo.bar.baz', id_name='last-time')
        self.assertEqual(second, ['third-time'])

    def test_copy_emitter_with_unique_id_event(self):
        # Here we're not testing copy directly, we're testing
        # the observable behavior from copying an event emitter.
        first = []
        def first_handler(id_name, **kwargs):
            first.append(id_name)

        second = []
        def second_handler(id_name, **kwargs):
            second.append(id_name)

        self.emitter.register('foo', first_handler, 'bar')
        self.emitter.emit('foo', id_name='first-time')
        self.assertEqual(first, ['first-time'])
        self.assertEqual(second, [])

        copied_emitter = copy.copy(self.emitter)

        # If we register an event handler with the copied
        # emitter, the event should not get registered again
        # because the unique id was already used.
        copied_emitter.register('foo', second_handler, 'bar')
        copied_emitter.emit('foo', id_name='second-time')
        self.assertEqual(first, ['first-time', 'second-time'])
        self.assertEqual(second, [])

        # If we unregister the first event from the copied emitter,
        # We should be able to register the second handler.
        copied_emitter.unregister('foo', first_handler, 'bar')
        copied_emitter.register('foo', second_handler, 'bar')
        copied_emitter.emit('foo', id_name='third-time')
        self.assertEqual(first, ['first-time', 'second-time'])
        self.assertEqual(second, ['third-time'])

        # The original event emitter should have the unique id event still
        # registered though.
        self.emitter.emit('foo', id_name='fourth-time')
        self.assertEqual(first, ['first-time', 'second-time', 'fourth-time'])
        self.assertEqual(second, ['third-time'])

    def test_copy_events_with_partials(self):
        # There's a bug in python2.6 where you can't deepcopy
        # a partial object.  We want to ensure that doesn't
        # break when a partial is hooked up as an event handler.
        def handler(a, b, **kwargs):
            return b

        f = functools.partial(handler, 1)
        self.emitter.register('a.b', f)
        copied = copy.copy(self.emitter)
        self.assertEqual(copied.emit_until_response(
            'a.b', b='return-val')[1], 'return-val')


if __name__ == '__main__':
    unittest.main()
