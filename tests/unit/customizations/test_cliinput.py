# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.cliinput import CliInputJSONArgument
from awscli.customizations.cliinput import CliInputYAMLArgument


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

    def create_args(self, value):
        parsed_args = mock.Mock()
        parsed_args.cli_input_json = value
        return parsed_args

    def test_register_argument_action(self):
        self.session.register.assert_any_call(
            'calling-command.*', self.argument.add_to_call_parameters
        )

    def test_add_to_call_parameters_no_file(self):
        parsed_args = self.create_args(self.input_json)
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'foo', 'B': 'bar'})

    def test_add_to_call_parameters_with_file(self):
        parsed_args = self.create_args('file://' + self.temp_file)
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'foo', 'B': 'bar'})

    def test_add_to_call_parameters_bad_json(self):
        parsed_args = self.create_args(self.input_json + ',')
        call_parameters = {}
        with self.assertRaises(ParamError):
            self.argument.add_to_call_parameters(
                service_operation=None, call_parameters=call_parameters,
                parsed_args=parsed_args, parsed_globals=None
            )

    def test_add_to_call_parameters_no_clobber(self):
        parsed_args = self.create_args(self.input_json)
        # The value for ``A`` should not be clobbered by the input JSON
        call_parameters = {'A': 'baz'}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'baz', 'B': 'bar'})

    def test_no_add_to_call_parameters(self):
        parsed_args = self.create_args(None)
        call_parameters = {'A': 'baz'}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        # Nothing should have been added to the call parameters because
        # ``cli_input_json`` is not in the ``parsed_args``
        self.assertEqual(call_parameters, {'A': 'baz'})

    def test_input_is_not_a_map(self):
        # These are still valid JSON, but they are not valid input for this
        # argument
        invalid_values = ['"foo"', '1', '[]', 'False', 'null']
        for invalid_value in invalid_values:
            parsed_args = self.create_args(invalid_value)
            with self.assertRaises(ParamError):
                self.argument.add_to_call_parameters(
                    service_operation=None, call_parameters={},
                    parsed_args=parsed_args, parsed_globals=None
                )


class TestCliInputYAMLArgument(TestCliInputJSONArgument):
    def setUp(self):
        super(TestCliInputYAMLArgument, self).setUp()
        self.argument = CliInputYAMLArgument(self.session)
        self.input_yaml = "A: foo\nB: bar"

    def create_args(self, value):
        parsed_args = mock.Mock()
        parsed_args.cli_input_yaml = value
        return parsed_args

    def test_input_yaml_string(self):
        parsed_args = self.create_args(self.input_yaml)
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'foo', 'B': 'bar'})

    def test_input_yaml_bytes(self):
        input_yaml = "A: !!binary Zm9v\nB: bar"
        parsed_args = self.create_args(input_yaml)
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': b'foo', 'B': 'bar'})

    def test_input_yaml_set(self):
        input_yaml = "foo: !!set {1, 2, 3}"
        parsed_args = self.create_args(input_yaml)
        call_parameters = {}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'foo': set([1, 2, 3])})

    def test_invalid_yaml(self):
        parsed_args = self.create_args(self.input_yaml + '\n,')
        call_parameters = {}
        with self.assertRaises(ParamError):
            self.argument.add_to_call_parameters(
                service_operation=None, call_parameters=call_parameters,
                parsed_args=parsed_args, parsed_globals=None
            )

    def test_yaml_does_not_overwrite(self):
        parsed_args = self.create_args(self.input_yaml)
        # The value for ``A`` should not be clobbered by the input YAML
        call_parameters = {'A': 'baz'}
        self.argument.add_to_call_parameters(
            service_operation=None, call_parameters=call_parameters,
            parsed_args=parsed_args, parsed_globals=None
        )
        self.assertEqual(call_parameters, {'A': 'baz', 'B': 'bar'})
