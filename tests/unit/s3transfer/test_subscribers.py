# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from s3transfer.exceptions import InvalidSubscriberMethodError
from s3transfer.subscribers import BaseSubscriber
from tests import unittest


class ExtraMethodsSubscriber(BaseSubscriber):
    def extra_method(self):
        return 'called extra method'


class NotCallableSubscriber(BaseSubscriber):
    on_done = 'foo'


class NoKwargsSubscriber(BaseSubscriber):
    def on_done(self):
        pass


class OverrideMethodSubscriber(BaseSubscriber):
    def on_queued(self, **kwargs):
        return kwargs


class OverrideConstructorSubscriber(BaseSubscriber):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2


class TestSubscribers(unittest.TestCase):
    def test_can_instantiate_base_subscriber(self):
        try:
            BaseSubscriber()
        except InvalidSubscriberMethodError:
            self.fail('BaseSubscriber should be instantiable')

    def test_can_call_base_subscriber_method(self):
        subscriber = BaseSubscriber()
        try:
            subscriber.on_done(future=None)
        except Exception as e:
            self.fail(
                'Should be able to call base class subscriber method. '
                f'instead got: {e}'
            )

    def test_subclass_can_have_and_call_additional_methods(self):
        subscriber = ExtraMethodsSubscriber()
        self.assertEqual(subscriber.extra_method(), 'called extra method')

    def test_can_subclass_and_override_method_from_base_subscriber(self):
        subscriber = OverrideMethodSubscriber()
        # Make sure that the overridden method is called
        self.assertEqual(subscriber.on_queued(foo='bar'), {'foo': 'bar'})

    def test_can_subclass_and_override_constructor_from_base_class(self):
        subscriber = OverrideConstructorSubscriber('foo', arg2='bar')
        # Make sure you can create a custom constructor.
        self.assertEqual(subscriber.arg1, 'foo')
        self.assertEqual(subscriber.arg2, 'bar')

    def test_invalid_arguments_in_constructor_of_subclass_subscriber(self):
        # The override constructor should still have validation of
        # constructor args.
        with self.assertRaises(TypeError):
            OverrideConstructorSubscriber()

    def test_not_callable_in_subclass_subscriber_method(self):
        with self.assertRaisesRegex(
            InvalidSubscriberMethodError, 'must be callable'
        ):
            NotCallableSubscriber()

    def test_no_kwargs_in_subclass_subscriber_method(self):
        with self.assertRaisesRegex(
            InvalidSubscriberMethodError, 'must accept keyword'
        ):
            NoKwargsSubscriber()
