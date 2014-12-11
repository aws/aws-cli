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
from awscli.compat import six
import mock

from botocore.model import DenormalizedStructureBuilder

from awscli.testutils import unittest
from awscli.customizations.generatecliskeleton import \
    GenerateCliSkeletonArgument


class TestGenerateCliSkeleton(unittest.TestCase):
    def setUp(self):
        self.operation_object = mock.Mock()
        self.argument = GenerateCliSkeletonArgument(self.operation_object)

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
        self.operation_object.model.input_shape = shape

        # This is what the json should should look like after being
        # generated to standard output.
        self.ref_json_output = \
            '{\n    "A": {\n        "B": ""\n    }\n}\n'

    def test_register_argument_action(self):
        register_args = self.operation_object.session.register.call_args_list
        self.assertEqual(register_args[0][0][0], 'calling-command.*')
        self.assertEqual(register_args[0][0][1],
                         self.argument.generate_json_skeleton)

    def test_generate_json_skeleton(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = True
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_json_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure the contents printed to standard output are correct.
            self.assertEqual(self.ref_json_output, mock_stdout.getvalue())
            # Ensure it is the correct return code of zero.
            self.assertEqual(rc, 0)

    def test_no_generate_json_skeleton(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = False
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_json_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure nothing is printed to standard output
            self.assertEqual('', mock_stdout.getvalue())
            # Ensure nothing is returned because it was never called.
            self.assertEqual(rc, None)


    def test_generate_json_skeleton_no_input_shape(self):
        parsed_args = mock.Mock()
        parsed_args.generate_cli_skeleton = True
        # Set the input shape to ``None``.
        self.operation_object.model.input_shape = None
        with mock.patch('sys.stdout', six.StringIO()) as mock_stdout:
            rc = self.argument.generate_json_skeleton(
                service_operation=self.service_operation, call_parameters=None,
                parsed_args=parsed_args, parsed_globals=None
            )
            # Ensure the contents printed to standard output are correct,
            # which should be an empty dictionary.
            self.assertEqual('{}\n', mock_stdout.getvalue())
            # Ensure it is the correct return code of zero.
            self.assertEqual(rc, 0)
