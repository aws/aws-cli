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
from tests import unittest

from botocore.hooks import EventHooks, HierarchicalEmitter, \
        first_non_none_response


class TestEventHooks(unittest.TestCase):

    def setUp(self):
        self.dispatch = EventHooks()
        self.called = False
        self.kwargs = {}

    def tearDown(self):
        pass

    def hook(self, **kwargs):
        self.called = True
        self.kwargs = kwargs
        return 'hook_response'

    def no_kwarg_hook(self):
        pass

    def test_register_then_emit_event(self):
        self.dispatch.register('before_send', self.hook)
        responses = self.dispatch.emit('before_send')

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], self.hook)
        self.assertEqual(responses[0][1], 'hook_response')
        self.assertTrue(self.called)

    def test_kwargs_passed_through_to_handlers(self):
        self.dispatch.register('before_send', self.hook)
        responses = self.dispatch.emit('before_send', foo='bar')
        self.assertEqual(self.kwargs, {'event_name': 'before_send',
                                       'foo': 'bar'})

    def test_register_must_accept_kwargs(self):
        with self.assertRaisesRegexp(ValueError,
                                     "must accept keyword arguments"):
            self.dispatch.register('before_send', self.no_kwarg_hook)

    def test_handler_must_be_callable(self):
        with self.assertRaisesRegexp(ValueError,
                                     "must be callable"):
            self.dispatch.register('before_send', "foo")

    def test_unregister_hook(self):
        self.dispatch.register('before_send', self.hook)
        self.dispatch.unregister('before_send', self.hook)
        self.dispatch.emit('before_send')

        self.assertFalse(self.called)

    def test_unregister_hook_that_does_not_exist(self):
        # should not raise an exception
        self.dispatch.unregister('before_send', self.hook)
        self.dispatch.emit('before_send')
        self.assertFalse(self.called)


class TestHierarchicalEventEmitter(unittest.TestCase):
    def setUp(self):
        self.hooks = EventHooks()
        self.emitter = HierarchicalEmitter(self.hooks)
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
        self.hooks = EventHooks()
        self.emitter = HierarchicalEmitter(self.hooks)
        self.hook_calls = []

    def hook(self, **kwargs):
        self.hook_calls.append(kwargs)

    def assert_hook_is_called_given_event(self, event):
        starting = len(self.hook_calls)
        self.emitter.emit(event)
        after = len(self.hook_calls)
        if not after - starting == 1:
            self.fail("Handler was not called for event: %s" % event)
        self.assertEqual(self.hook_calls[-1]['event_name'], event)

    def assert_hook_is_not_called_given_event(self, event):
        starting = len(self.hook_calls)
        self.emitter.emit(event)
        after = len(self.hook_calls)
        if not after == starting:
            self.fail("Handler was called for event but was not "
                      "suppose to be called: %s" % event)

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


if __name__ == '__main__':
    unittest.main()
