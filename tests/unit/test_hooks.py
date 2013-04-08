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
from tests import unittest

from awscli.hooks import EventHooks


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


if __name__ == '__main__':
    unittest.main()
