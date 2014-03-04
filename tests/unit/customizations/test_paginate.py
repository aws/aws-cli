# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import mock

from awscli.customizations import paginate


class TestPaginateBase(unittest.TestCase):

    def setUp(self):
        self.operation = mock.Mock()
        self.operation.can_paginate = True
        self.foo_param = mock.Mock()
        self.foo_param.cli_name = 'foo'
        self.foo_param.name = 'Foo'
        self.foo_param.type = 'string'
        self.bar_param = mock.Mock()
        self.bar_param.cli_name = 'bar'
        self.bar_param.type = 'string'
        self.bar_param.name = 'Bar'
        self.params = [self.foo_param, self.bar_param]
        self.operation.pagination = {
            'input_token': 'Foo',
            'limit_key': 'Bar',
        }
        self.operation.params = self.params


class TestArgumentTableModifications(TestPaginateBase):

    def test_customize_arg_table(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation,
                                     'building-argument-table.foo.bar')
        # We should mark the built in input_token as 'hidden'.
        self.assertTrue(argument_table['foo']._UNDOCUMENTED)
        # Also need to hide the limit key.
        self.assertTrue(argument_table['bar']._UNDOCUMENTED)
        # We also need to inject startin-token and max-items.
        self.assertIn('starting-token', argument_table)
        self.assertIn('max-items', argument_table)
        # And these should be PageArguments.
        self.assertIsInstance(argument_table['starting-token'],
                              paginate.PageArgument)
        self.assertIsInstance(argument_table['max-items'],
                              paginate.PageArgument)

    def test_operation_with_no_paginate(self):
        # Operations that don't paginate are left alone.
        self.operation.can_paginate = False
        argument_table = {
            'foo': 'FakeArgObject',
            'bar': 'FakeArgObject',
        }
        starting_table = argument_table.copy()
        paginate.unify_paging_params(argument_table, self.operation,
                                     'building-argument-table.foo.bar')
        self.assertEqual(starting_table, argument_table)


class TestStringLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestStringLimitKey, self).setUp()
        self.bar_param.type = 'string'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation,
                                     'building-argument-table.foo.bar')
        # Max items should be the same type as bar, which may not be an int
        self.assertEqual('string', argument_table['max-items']._parse_type)


class TestIntegerLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestIntegerLimitKey, self).setUp()
        self.bar_param.type = 'integer'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation,
                                     'building-argument-table.foo.bar')
        # Max items should be the same type as bar, which may not be an int
        self.assertEqual('integer', argument_table['max-items']._parse_type)


class TestBadLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestBadLimitKey, self).setUp()
        self.bar_param.type = 'bad'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        with self.assertRaises(TypeError):
            paginate.unify_paging_params(argument_table, self.operation,
                                         'building-argument-table.foo.bar')
