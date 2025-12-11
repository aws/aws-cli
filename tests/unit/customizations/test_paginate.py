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
import pytest

from awscli.customizations.paginate import PageArgument
from awscli.testutils import mock, unittest

from botocore.exceptions import DataNotFoundError, PaginationError
from botocore.model import OperationModel
from awscli.help import OperationHelpCommand, OperationDocumentEventHandler

from awscli.customizations import paginate

@pytest.fixture
def max_items_page_arg():
    return PageArgument('max-items', 'documentation', int, 'MaxItems')

class TestPaginateBase(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock()
        self.paginator_model = mock.Mock()
        self.pagination_config = {
            'input_token': 'Foo',
            'limit_key': 'Bar',
        }
        self.paginator_model.get_paginator.return_value = \
            self.pagination_config
        self.session.get_paginator_model.return_value = self.paginator_model

        self.operation_model = mock.Mock()
        self.foo_param = mock.Mock()
        self.foo_param.name = 'Foo'
        self.foo_param.type_name = 'string'
        self.bar_param = mock.Mock()
        self.bar_param.type_name = 'string'
        self.bar_param.name = 'Bar'
        self.params = [self.foo_param, self.bar_param]
        self.operation_model.input_shape.members = {"Foo": self.foo_param,
                                                    "Bar": self.bar_param}


class TestArgumentTableModifications(TestPaginateBase):

    def test_customize_arg_table(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation_model,
                                     'building-argument-table.foo.bar',
                                     self.session)
        # We should mark the built in input_token as 'hidden'.
        self.assertTrue(argument_table['foo']._UNDOCUMENTED)
        # Also need to hide the limit key.
        self.assertTrue(argument_table['bar']._UNDOCUMENTED)
        # We also need to inject starting-token and max-items.
        self.assertIn('starting-token', argument_table)
        self.assertIn('max-items', argument_table)
        self.assertIn('page-size', argument_table)
        # And these should be PageArguments.
        self.assertIsInstance(argument_table['starting-token'],
                              paginate.PageArgument)
        self.assertIsInstance(argument_table['max-items'],
                              paginate.PageArgument)
        self.assertIsInstance(argument_table['page-size'],
                              paginate.PageArgument)

    def test_operation_with_no_paginate(self):
        # Operations that don't paginate are left alone.
        self.paginator_model.get_paginator.side_effect = ValueError()
        argument_table = {
            'foo': 'FakeArgObject',
            'bar': 'FakeArgObject',
        }
        starting_table = argument_table.copy()
        paginate.unify_paging_params(argument_table, self.operation_model,
                                     'building-argument-table.foo.bar',
                                     self.session)
        self.assertEqual(starting_table, argument_table)

    def test_service_with_no_paginate(self):
        # Operations that don't paginate are left alone.
        self.session.get_paginator_model.side_effect = \
            DataNotFoundError(data_path='foo.paginators.json')
        argument_table = {
            'foo': 'FakeArgObject',
            'bar': 'FakeArgObject',
        }
        starting_table = argument_table.copy()
        paginate.unify_paging_params(argument_table, self.operation_model,
                                     'building-argument-table.foo.bar',
                                     self.session)
        self.assertEqual(starting_table, argument_table)


class TestHelpDocumentationModifications(TestPaginateBase):
    def test_injects_pagination_help_text(self):
        with mock.patch('awscli.customizations.paginate.get_paginator_config',
                   return_value={'result_key': 'abc'}):
            help_command = OperationHelpCommand(
                mock.Mock(), mock.Mock(), mock.Mock(), 'foo', OperationDocumentEventHandler)
            help_command.obj = mock.Mock(OperationModel)
            help_command.obj.name = 'foo'
            paginate.add_paging_description(help_command)
            self.assertIn('``foo`` is a paginated operation. Multiple API',
                          help_command.doc.getvalue().decode())
            self.assertIn('following query expressions: ``abc``',
                          help_command.doc.getvalue().decode())

    def test_shows_result_keys_when_array(self):
        with mock.patch('awscli.customizations.paginate.get_paginator_config',
                   return_value={'result_key': ['abc', '123']}):
            help_command = OperationHelpCommand(
                mock.Mock(), mock.Mock(), mock.Mock(), 'foo', OperationDocumentEventHandler)
            help_command.obj = mock.Mock(OperationModel)
            help_command.obj.name = 'foo'
            paginate.add_paging_description(help_command)
            self.assertIn('following query expressions: ``abc``, ``123``',
                          help_command.doc.getvalue().decode())

    def test_does_not_show_result_key_if_not_present(self):
        with mock.patch('awscli.customizations.paginate.get_paginator_config',
                   return_value={'limit_key': 'aaa'}):
            help_command = OperationHelpCommand(
                mock.Mock(), mock.Mock(), mock.Mock(), 'foo', OperationDocumentEventHandler)
            help_command.obj = mock.Mock(OperationModel)
            help_command.obj.name = 'foo'
            paginate.add_paging_description(help_command)
            self.assertIn('``foo`` is a paginated operation. Multiple API',
                          help_command.doc.getvalue().decode())
            self.assertNotIn('following query expressions',
                             help_command.doc.getvalue().decode())

    def test_does_not_inject_when_no_pagination(self):
        with mock.patch('awscli.customizations.paginate.get_paginator_config',
                   return_value=None):
            help_command = OperationHelpCommand(
                mock.Mock(), mock.Mock(), mock.Mock(), 'foo', OperationDocumentEventHandler)
            help_command.obj = mock.Mock(OperationModel)
            help_command.obj.name = 'foo'
            paginate.add_paging_description(help_command)
            self.assertNotIn('``foo`` is a paginated operation',
                             help_command.doc.getvalue().decode())


class TestStringLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestStringLimitKey, self).setUp()
        self.bar_param.type_name = 'string'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation_model,
                                     'building-argument-table.foo.bar',
                                     self.session)
        # Max items should be the same type as bar, which may not be an int
        self.assertEqual('string', argument_table['max-items'].cli_type_name)


class TestIntegerLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestIntegerLimitKey, self).setUp()
        self.bar_param.type_name = 'integer'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        paginate.unify_paging_params(argument_table, self.operation_model,
                                     'building-argument-table.foo.bar',
                                     self.session)
        # Max items should be the same type as bar, which may not be an int
        self.assertEqual('integer', argument_table['max-items'].cli_type_name)


class TestBadLimitKey(TestPaginateBase):

    def setUp(self):
        super(TestBadLimitKey, self).setUp()
        self.bar_param.type_name = 'bad'

    def test_integer_limit_key(self):
        argument_table = {
            'foo': mock.Mock(),
            'bar': mock.Mock(),
        }
        with self.assertRaises(TypeError):
            paginate.unify_paging_params(argument_table, self.operation_model,
                                         'building-argument-table.foo.bar',
                                         self.session)


class TestShouldEnablePagination(TestPaginateBase):
    def setUp(self):
        super(TestShouldEnablePagination, self).setUp()
        self.parsed_globals = mock.Mock()
        self.parsed_args = mock.Mock()
        self.parsed_args.starting_token = None
        self.parsed_args.page_size = None
        self.parsed_args.max_items = None

    def test_should_not_enable_pagination(self):
        # Here the user has specified a manual pagination argument,
        # so we should turn pagination off.
        # From setUp(), the limit_key is 'Bar'
        input_tokens = ['foo', 'bar']
        self.parsed_globals.paginate = True
        # Corresponds to --bar 10
        self.parsed_args.foo = None
        self.parsed_args.bar = 10
        paginate.check_should_enable_pagination(
            input_tokens, {}, {}, self.parsed_args, self.parsed_globals)
        # We should have turned paginate off because the
        # user specified --bar 10
        self.assertFalse(self.parsed_globals.paginate)

    def test_should_enable_pagination_with_no_args(self):
        input_tokens = ['foo', 'bar']
        self.parsed_globals.paginate = True
        # Corresponds to not specifying --foo nor --bar
        self.parsed_args.foo = None
        self.parsed_args.bar = None
        paginate.check_should_enable_pagination(
            input_tokens, {}, {}, self.parsed_args, self.parsed_globals)
        # We should have turned paginate off because the
        # user specified --bar 10
        self.assertTrue(self.parsed_globals.paginate)

    def test_default_to_pagination_on_when_ambiguous(self):
        input_tokens = ['foo', 'max-items']
        self.parsed_globals.paginate = True
        # Here the user specifies --max-items 10 This is ambiguous because the
        # input_token also contains 'max-items'.  Should we assume they want
        # pagination turned off or should we assume that this is the normalized
        # --max-items?
        # Will we default to assuming they meant the normalized
        # --max-items.
        self.parsed_args.foo = None
        self.parsed_args.max_items = 10
        paginate.check_should_enable_pagination(
            input_tokens, {}, {}, self.parsed_args, self.parsed_globals)
        self.assertTrue(self.parsed_globals.paginate,
                        "Pagination was not enabled.")

    def test_fall_back_to_original_max_items_when_pagination_turned_off(self):
        input_tokens = ['max-items']
        # User specifies --no-paginate.
        self.parsed_globals.paginate = False
        # But also specifies --max-items 10, which is normally a pagination arg
        # we replace.  However, because they've explicitly turned off
        # pagination, we should put back the original arg.
        self.parsed_args.max_items = 10
        shadowed_args = {'max-items': mock.sentinel.ORIGINAL_ARG}
        arg_table = {'max-items': mock.sentinel.PAGINATION_ARG}

        paginate.check_should_enable_pagination(
            input_tokens, shadowed_args, arg_table,
            self.parsed_args, self.parsed_globals)

    def test_shadowed_args_are_replaced_when_pagination_turned_off(self):
        input_tokens = ['foo', 'bar']
        self.parsed_globals.paginate = True
        # Corresponds to --bar 10
        self.parsed_args.foo = None
        self.parsed_args.bar = 10
        shadowed_args = {'foo': mock.sentinel.ORIGINAL_ARG}
        arg_table = {'foo': mock.sentinel.PAGINATION_ARG}
        paginate.check_should_enable_pagination(
            input_tokens, shadowed_args, arg_table,
            self.parsed_args, self.parsed_globals)
        # We should have turned paginate off because the
        # user specified --bar 10
        self.assertFalse(self.parsed_globals.paginate)
        self.assertEqual(arg_table['foo'], mock.sentinel.ORIGINAL_ARG)

    def test_shadowed_args_are_replaced_when_pagination_set_off(self):
        input_tokens = ['foo', 'bar']
        self.parsed_globals.paginate = False
        # Corresponds to --bar 10
        self.parsed_args.foo = None
        self.parsed_args.bar = 10
        shadowed_args = {'foo': mock.sentinel.ORIGINAL_ARG}
        arg_table = {'foo': mock.sentinel.PAGINATION_ARG}
        paginate.check_should_enable_pagination(
            input_tokens, shadowed_args, arg_table,
            self.parsed_args, self.parsed_globals)
        # We should have turned paginate off because the
        # user specified --bar 10
        self.assertFalse(self.parsed_globals.paginate)
        self.assertEqual(arg_table['foo'], mock.sentinel.ORIGINAL_ARG)


class TestEnsurePagingParamsNotSet(TestPaginateBase):
    def setUp(self):
        super(TestEnsurePagingParamsNotSet, self).setUp()
        self.parsed_args = mock.Mock()

        self.parsed_args.starting_token = None
        self.parsed_args.page_size = None
        self.parsed_args.max_items = None

    def test_pagination_params_raise_error_with_no_paginate(self):
        self.parsed_args.max_items = 100

        with self.assertRaises(PaginationError):
            paginate.ensure_paging_params_not_set(self.parsed_args, {})

    def test_can_handle_missing_page_size(self):
        # Not all pagination operations have a page_size.
        del self.parsed_args.page_size
        self.assertIsNone(paginate.ensure_paging_params_not_set(
            self.parsed_args, {}))


class TestNonPositiveMaxItems:
    def test_positive_integer_does_not_raise_warning(self, max_items_page_arg, capsys):
        max_items_page_arg.add_to_params({}, 1)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_zero_raises_warning(self, max_items_page_arg, capsys):
        max_items_page_arg.add_to_params({}, 0)
        captured = capsys.readouterr()
        assert "Non-positive values for --max-items" in captured.err

    def test_negative_integer_raises_warning(self, max_items_page_arg, capsys):
        max_items_page_arg.add_to_params({}, -1)
        captured = capsys.readouterr()
        assert "Non-positive values for --max-items" in captured.err
