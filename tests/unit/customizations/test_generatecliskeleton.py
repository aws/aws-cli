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

from botocore.model import DenormalizedStructureBuilder

from awscli.compat import six
from awscli.testutils import unittest, capture_output
from awscli.customizations.generatecliskeleton import \
    GenerateCliSkeletonArgument


class TestGenerateCliSkeleton(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        # Create a mock service operation object
        self.service_operation = mock.Mock()

        # Make an arbitrary input model shape.
        self.input_shape = {
            'A': {
                'type': 'structure',
                'members': {
                    'B': {'type': 'string'},
                }
            }
        }
        shape = DenormalizedStructureBuilder().with_members(
            self.input_shape).build_model()
        self.operation_model = mock.Mock(input_shape=shape)
        self.argument = GenerateCliSkeletonArgument(
            self.session, self.operation_model)

        # This is what the json should should look like after being
        # generated to standard output.
        self.ref_json_output = \
            '{\n    "A": {\n        "B": ""\n    }\n}\n'

    def assert_skeleton_equals(self, arg_value, expected_output,
                               expected_rc=0, input_shape=None):
        argument = self.argument
        if input_shape is not None:
            argument = self.create_argument(input_shape)
        parsed_args = mock.Mock(generate_cli_skeleton=arg_value)
        with capture_output() as output:
            rc = argument.generate_skeleton(
                service_operation=self.service_operation,
                parsed_args=parsed_args,
                parsed_globals=None,
                call_parameters=None,
            )
            self.assertEqual(rc, expected_rc)
            self.assertEqual(output.stdout.getvalue(), expected_output)

    def create_argument(self, input_shape):
        builder = DenormalizedStructureBuilder().with_members(input_shape)
        operation_model = mock.Mock(input_shape=builder.build_model())
        return GenerateCliSkeletonArgument(self.session, operation_model)

    def test_register_argument_action(self):
        register_args = self.session.register.call_args_list
        self.assertEqual(register_args[0][0][0], 'calling-command.*')
        self.assertEqual(register_args[0][0][1],
                         self.argument.generate_skeleton)

    def test_no_override_required_args_when_output(self):
        argument_table = {}
        mock_arg = mock.Mock()
        mock_arg.required = True
        argument_table['required-arg'] = mock_arg
        args = ['--generate-cli-skeleton', 'output']
        self.argument.override_required_args(argument_table, args)
        self.assertTrue(argument_table['required-arg'].required)

    def test_override_required_args_when_input(self):
        argument_table = {}
        mock_arg = mock.Mock()
        mock_arg.required = True
        argument_table['required-arg'] = mock_arg
        args = ['--generate-cli-skeleton']
        self.argument.override_required_args(argument_table, args)
        self.assertFalse(argument_table['required-arg'].required)

    def test_override_required_args_when_output_present_but_not_value(self):
        argument_table = {}
        mock_arg = mock.Mock()
        mock_arg.required = True
        argument_table['required-arg'] = mock_arg
        args = ['--generate-cli-skeleton', '--some-other-param', 'output']
        self.argument.override_required_args(argument_table, args)
        self.assertFalse(argument_table['required-arg'].required)

    def test_generate_json_skeleton(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = 'input'
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure the contents printed to standard output are correct.
            self.assertEqual(self.ref_json_output, mock_stdout.getvalue())
            # Ensure it is the correct return code of zero.
            self.assertEqual(rc, 0)

    def test_no_generate_json_skeleton(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = None
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure nothing is printed to standard output
            self.assertEqual('', mock_stdout.getvalue())
            # Ensure nothing is returned because it was never called.
            self.assertEqual(rc, None)

    def test_generate_json_skeleton_no_input_shape(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = 'input'
        # Set the input shape to ``None``.
        self.argument = GenerateCliSkeletonArgument(
            self.session, mock.Mock(input_shape=None))
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure the contents printed to standard output are correct,
            # which should be an empty dictionary.
            self.assertEqual('{}\n', mock_stdout.getvalue())
            # Ensure it is the correct return code of zero.
            self.assertEqual(rc, 0)

    def test_generate_json_skeleton_with_timestamp(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = 'input'
        input_shape = {
            'A': {
                'type': 'structure',
                'members': {
                    'B': {'type': 'timestamp'},
                }
            }
        }
        shape = DenormalizedStructureBuilder().with_members(
            input_shape).build_model()
        operation_model = mock.Mock(input_shape=shape)
        argument = GenerateCliSkeletonArgument(
            self.session, operation_model)
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = argument.generate_skeleton(
                call_parameters=None, parsed_args=parsed_args,
                parsed_globals=None
            )
            self.assertEqual(
                '{\n'
                '    "A": {\n'
                '        "B": "1970-01-01T00:00:00"\n'
                '    }\n'
                '}\n', mock_stdout.getvalue())
            self.assertEqual(rc, 0)

    def test_generate_yaml_input_skeleton(self):
        expected = (
            "A:\n"
            "  B: ''\n"
        )
        self.assert_skeleton_equals('yaml-input', expected)

    def test_generate_yaml_input_with_bytes(self):
        input_shape = {
            'A': {
                'type': 'structure',
                'members': {
                    'B': {'type': 'blob'},
                }
            }
        }
        expected = (
            "A:\n"
            "  B: !!binary ''\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_with_comments(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'docstring'
            }
        }
        expected = (
            "A: ''  # docstring.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_with_nested_comments(self):
        input_shape = {
            'A': {
                'type': 'structure',
                'documentation': 'top-level docstring',
                'members': {
                    'B': {
                        'type': 'string',
                        'documentation': 'nested docstring'
                    }
                }
            }
        }
        expected = (
            "A:  # top-level docstring.\n"
            "  B: ''  # nested docstring.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_with_required_member(self):
        input_shape = {
            'A': {
                'type': 'structure',
                'documentation': 'top-level docstring',
                'members': {
                    'B': {
                        'type': 'string',
                        'documentation': 'nested docstring'
                    }
                },
                'required': ['B']
            }
        }
        expected = (
            "A:  # top-level docstring.\n"
            "  B: ''  # [REQUIRED] nested docstring.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_ignores_newline(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'one-line\ntwo-line'
            }
        }
        expected = (
            "A: ''  # one-line two-line.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_ignores_line_separator_char(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'one-line\u2028two-line'
            }
        }
        expected = (
            "A: ''  # one-line two-line.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_removes_xml_tags(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': '<p>text</p>'
            }
        }
        expected = (
            "A: ''  # text.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_can_handle_broken_xml(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': '<p>text'
            }
        }
        expected = (
            "A: ''  # <p>text.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_uses_only_content_before_first_period(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'First sentence. Second Sentence'
            }
        }
        expected = (
            "A: ''  # First sentence.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_uses_only_content_before_first_colon(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'First sentence: * Option 1 * Option 2'
            }
        }
        expected = (
            "A: ''  # First sentence.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)

    def test_generate_yaml_input_includes_enums_in_comments(self):
        input_shape = {
            'A': {
                'type': 'string',
                'documentation': 'First sentence.',
                'enum': ['ENUM1']
            }
        }
        expected = (
            "A: ENUM1  # First sentence. Valid values are: ENUM1.\n"
        )
        self.assert_skeleton_equals(
            'yaml-input', expected, input_shape=input_shape)
