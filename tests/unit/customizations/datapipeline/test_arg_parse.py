# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.datapipeline import ParameterValuesInlineArgument
from awscli.testutils import unittest


class TestParameterValuesInlineArgument(unittest.TestCase):
    def test_over_2_values_with_same_key(self):
        parameters = {}
        argument = ParameterValuesInlineArgument('parameter-values')
        argument.add_to_params(
            parameters,
            [
                'param1=value1',
                'param1=value2',
                'param1=value3',
            ],
        )
        self.assertEqual(
            parameters['parameterValues'],
            [
                {"id": "param1", "stringValue": "value1"},
                {"id": "param1", "stringValue": "value2"},
                {"id": "param1", "stringValue": "value3"},
            ],
        )
