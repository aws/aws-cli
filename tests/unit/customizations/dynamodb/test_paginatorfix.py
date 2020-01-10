# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.dynamodb.paginatorfix import \
    parse_last_evaluated_key_binary


class TestParseLastEvaluatedKeyBinary(unittest.TestCase):
    def assert_parsed_output(self, last_key_value, expected_output):
        parsed = {
            'LastEvaluatedKey': {
                'FooKeyName': last_key_value,
            }
        }
        parse_last_evaluated_key_binary(parsed=parsed)
        self.assertEqual(last_key_value, expected_output)

    def test_ignores_response_without_last_evaluated_key(self):
        parsed = {'Items': []}
        parse_last_evaluated_key_binary(parsed=parsed)
        self.assertEqual(parsed, {'Items': []})

    def test_parses_binary_key(self):
        self.assert_parsed_output({'B': 'Zm9v'}, {'B': b'foo'})

    def test_ignores_strings(self):
        self.assert_parsed_output({'S': 'Zm9v'}, {'S': 'Zm9v'})

    def test_ignores_numbers(self):
        self.assert_parsed_output({'N': 2}, {'N': 2})
