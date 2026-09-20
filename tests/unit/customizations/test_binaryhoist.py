# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
from awscli.customizations.binaryhoist import InjectingArgument


class TestInjectingArgument(unittest.TestCase):
    def setUp(self):
        self.argument = InjectingArgument(
            'TerminologyData',
            'File',
            name='data-file',
            cli_type_name='blob',
            required=False,
        )

    def test_none_value_does_not_add_to_params(self):
        parameters = {}
        self.argument.add_to_params(parameters, None)
        self.assertEqual(parameters, {})

    def test_value_is_wrapped_in_serialized_member(self):
        parameters = {}
        self.argument.add_to_params(parameters, b'data')
        self.assertEqual(parameters, {'TerminologyData': {'File': b'data'}})

    def test_value_merges_with_existing_serialized_arg(self):
        parameters = {'TerminologyData': {'Format': 'CSV'}}
        self.argument.add_to_params(parameters, b'data')
        self.assertEqual(
            parameters,
            {'TerminologyData': {'Format': 'CSV', 'File': b'data'}},
        )
