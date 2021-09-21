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
import mock
import os
import shutil
import tempfile

from awscli.testutils import unittest
from awscli.argprocess import ParamError
from awscli.customizations.cliinputjson import CliInputJSONArgument


class TestCliInputJSONArgument(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.argument = CliInputJSONArgument(self.session)

        # Create the various forms the data could come in. The two main forms
        # are as a string and or as a path to a file.
        self.input_json = '{"A": "foo", "B": "bar"}'

        # Make a temporary file
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'foo.json')
        with open(self.temp_file, 'w') as f:
            f.write(self.input_json)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_register_argument_action(self):
        register_args = self.session.register.call_args_list
        self.assertEqual(register_args[0][0][0], 'calling-command.*')
        self.assertEqual(register_args[0][0][1],
                         self.argument.add_to_call_parameters)

    def test_add_to_call_parameters_no_file(self):
        parsed_args = mock.Mock()
        # Make the value a JSON string
        parsed_args.cli_input_json = self.input_json
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'foo', 'B': 'bar'})

    def test_add_to_call_parameters_with_file(self):
        parsed_args = mock.Mock()
        # Make the value a file with JSON located inside.
        parsed_args.cli_input_json = 'file://' + self.temp_file
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'foo', 'B': 'bar'})

    def test_add_to_call_parameters_bad_json(self):
        parsed_args = mock.Mock()
        # Create a bad JSON input
        parsed_args.cli_input_json = self.input_json + ','
        call_parameters = {}
        with self.assertRaises(ParamError):
            self.argument.add_to_call_parameters(
                service_operation=None, call_parameters=call_parameters,
                parsed_args=parsed_args, parsed_globals=None
            )

    def test_add_to_call_parameters_no_clobber(self):
        parsed_args = mock.Mock()
        parsed_args.cli_input_json = self.input_json
        # The value for ``A`` should not be clobbered by the input JSON
        call_parameters = {'A': 'baz'}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'baz', 'B': 'bar'})

    def test_no_add_to_call_parameters(self):
        parsed_args = mock.Mock()
        parsed_args.cli_input_json = None
        call_parameters = {'A': 'baz'}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        # Nothing should have been added to the call parameters because
        # ``cli_input_json`` is not in the ``parsed_args``
        self.assertEqual(call_parameters, {'A': 'baz'})
