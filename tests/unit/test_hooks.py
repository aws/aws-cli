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
        self.assertEqual(len(self.hook_calls), 3)
        self.assertEqual([e['event_name'] for e in self.hook_calls],
                         ['foo.bar.baz', 'foo.bar', 'foo'])


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


if __name__ == '__main__':
    unittest.main()
