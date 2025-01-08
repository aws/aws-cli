# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from awscli.testutils import mock, unittest, FileCreator, skip_if_windows
from awscli.customizations.arguments import NestedBlobArgumentHoister
from awscli.customizations.arguments import OverrideRequiredArgsArgument
from awscli.customizations.arguments import StatefulArgument
from awscli.customizations.arguments import QueryOutFileArgument
from awscli.customizations.arguments import resolve_given_outfile_path
from awscli.customizations.arguments import is_parsed_result_successful
from awscli.customizations.exceptions import ParamValidationError


class TestOverrideRequiredArgsArgument(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.argument = OverrideRequiredArgsArgument(self.session)

        # Set up a sample argument_table
        self.argument_table = {}
        self.mock_arg = mock.Mock()
        self.mock_arg.required = True
        self.argument_table['mock-arg'] = self.mock_arg

    def test_register_argument_action(self):
        register_args = self.session.register.call_args
        self.assertEqual(register_args[0][0],
                         'before-building-argument-table-parser')
        self.assertEqual(register_args[0][1],
                         self.argument.override_required_args)

    def test_override_required_args_if_in_cmdline(self):
        args = ['--no-required-args']
        self.argument.override_required_args(self.argument_table, args)
        self.assertFalse(self.mock_arg.required)

    def test_no_override_required_args_if_not_in_cmdline(self):
        args = []
        self.argument.override_required_args(self.argument_table, args)
        self.assertTrue(self.mock_arg.required)


class TestStatefulArgument(unittest.TestCase):
    def test_persists_value_when_added_to_params(self):
        self.session = mock.Mock()
        arg = StatefulArgument('test')
        arg.add_to_params({}, 'foo')
        self.assertEqual('foo', arg.value)


class TestArgumentHelpers(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def test_only_validates_filename_when_set(self):
        resolve_given_outfile_path(None)

    def test_works_with_valid_filename(self):
        filename = self.files.create_file('valid', '')
        self.assertEqual(filename, resolve_given_outfile_path(filename))

    def test_works_with_relative_filename(self):
        filename = '../valid'
        self.assertEqual(filename, resolve_given_outfile_path(filename))

    def test_raises_when_cannot_write_to_file(self):
        filename = os.sep.join(['_path', 'not', '_exist_', 'file.xyz'])
        with self.assertRaises(ParamValidationError):
            resolve_given_outfile_path(filename)

    def test_checks_if_valid_result(self):
        result = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        self.assertTrue(is_parsed_result_successful(result))

    def test_checks_if_invalid_result(self):
        result = {'ResponseMetadata': {'HTTPStatusCode': 300}}
        self.assertFalse(is_parsed_result_successful(result))


class TestQueryFileArgument(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def test_proxies_to_super_ctor(self):
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'bar.baz', 'event', 0o600)
        self.assertEqual('foo', arg.name)
        self.assertEqual('bar.baz', arg.query)

    def test_adds_default_help_text(self):
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'bar.baz', 'event', 0o600)
        self.assertEqual(('Saves the command output contents of bar.baz '
                          'to the given filename'), arg.documentation)

    def test_does_not_add_help_text_if_set(self):
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'bar.baz', 'event', 0o600,
                                   help_text='abc')
        self.assertEqual('abc', arg.documentation)

    def test_saves_query_to_file(self):
        outfile = self.files.create_file('not-empty-test', '')
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'baz', 'event', 0o600)
        arg.add_to_params({}, outfile)
        arg.save_query({'ResponseMetadata': {'HTTPStatusCode': 200},
                        'baz': 'abc123'})
        with open(outfile) as fp:
            self.assertEqual('abc123', fp.read())
        self.assertEqual(1, session.register.call_count)
        session.register.assert_called_with('event', arg.save_query)

    def test_does_not_save_when_not_set(self):
        session = mock.Mock()
        QueryOutFileArgument(session, 'foo', 'baz', 'event', 0o600)
        self.assertEqual(0, session.register.call_count)

    def test_saves_query_to_file_as_empty_string_when_none_result(self):
        outfile = self.files.create_file('none-test', '')
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'baz', 'event', 0o600)
        arg.add_to_params({}, outfile)
        arg.save_query({'ResponseMetadata': {'HTTPStatusCode': 200}})
        with open(outfile) as fp:
            self.assertEqual('', fp.read())

    @skip_if_windows("Test not valid on windows.")
    def test_permissions_on_created_file(self):
        outfile = self.files.create_file('not-empty-test', '')
        session = mock.Mock()
        arg = QueryOutFileArgument(session, 'foo', 'baz', 'event', 0o600)
        arg.add_to_params({}, outfile)
        arg.save_query({'ResponseMetadata': {'HTTPStatusCode': 200},
                        'baz': 'abc123'})
        with open(outfile) as fp:
            fp.read()
        self.assertEqual(os.stat(outfile).st_mode & 0xFFF, 0o600)


class TestNestedBlobArgumentHoister(unittest.TestCase):
    def setUp(self):
        self.blob_hoister = NestedBlobArgumentHoister(
            'complexArgX', 'valueY', 'argY', 'argYDoc', '.argYDocAddendum')

        self.arg_table = {
            'complexArgX': mock.Mock(
                required=True,
                documentation='complexArgXDoc',
                argument_model=mock.Mock(
                    members={
                        'valueY': mock.Mock(
                            type_name='blob',
                        )
                    }
                )
            )
        }

    def test_apply_to_arg_table(self):
        self.blob_hoister(None, self.arg_table)

        self.assertFalse(self.arg_table['complexArgX'].required)
        self.assertEqual(
            self.arg_table['complexArgX'].documentation,
            'complexArgXDoc.argYDocAddendum')

        argY = self.arg_table['argY']
        self.assertFalse(argY.required)
        self.assertEqual(argY.documentation, 'argYDoc')
        self.assertEqual(argY.argument_model.type_name, 'blob')

    def test_populates_underlying_complex_arg(self):
        self.blob_hoister(None, self.arg_table)
        argY = self.arg_table['argY']

        # parameters bag doesn't
        # already contain 'ComplexArgX'
        parameters = {
            'any': 'other',
        }
        argY.add_to_params(parameters, 'test-value')
        self.assertEqual('other', parameters['any'])
        self.assertEqual('test-value', parameters['ComplexArgX']['valueY'])

    def test_preserves_member_values_in_underlying_complex_arg(self):
        self.blob_hoister(None, self.arg_table)
        argY = self.arg_table['argY']

        # parameters bag already contains 'ComplexArgX'
        # but that does not contain 'valueY'
        parameters = {
            'any': 'other',
            'ComplexArgX': {
                'another': 'one',
            }
        }
        argY.add_to_params(parameters, 'test-value')
        self.assertEqual('other', parameters['any'])
        self.assertEqual('one', parameters['ComplexArgX']['another'])
        self.assertEqual('test-value', parameters['ComplexArgX']['valueY'])

    def test_overrides_target_member_in_underlying_complex_arg(self):
        self.blob_hoister(None, self.arg_table)
        argY = self.arg_table['argY']

        # parameters bag already contains 'ComplexArgX'
        # and that already contains 'valueY'
        parameters = {
            'any': 'other',
            'ComplexArgX': {
                'another': 'one',
                'valueY': 'doomed',
            }
        }
        argY.add_to_params(parameters, 'test-value')
        self.assertEqual('other', parameters['any'])
        self.assertEqual('one', parameters['ComplexArgX']['another'])
        self.assertEqual('test-value', parameters['ComplexArgX']['valueY'])

    def test_not_apply_to_mismatch_arg_type(self):
        nonmatching_arg_table = {
            'complexArgX': mock.Mock(
                required=True,
                documentation='complexArgXDoc',
                argument_model=mock.Mock(
                    members={
                        'valueY': mock.Mock(
                            type_name='string',
                        )
                    }
                )
            )
        }

        self.blob_hoister(None, nonmatching_arg_table)

        self.assertTrue(nonmatching_arg_table['complexArgX'].required)
        self.assertEqual(
            nonmatching_arg_table['complexArgX'].documentation, 'complexArgXDoc')
        self.assertFalse('argY' in self.arg_table)
