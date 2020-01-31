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
import json

import ruamel.yaml as yaml

from awscli.testutils import BaseAWSCommandParamsTest


class BaseSelectTest(BaseAWSCommandParamsTest):
    def assert_yaml_response_equal(self, response, expected):
        with self.assertRaises(ValueError):
            json.loads(response)
        loaded = yaml.safe_load(response)
        self.assertEqual(loaded, expected)


class TestSelect(BaseSelectTest):
    def setUp(self):
        super(TestSelect, self).setUp()
        self.parsed_response = {
            "Count": 1,
            "Items": [{"foo": {"S": "spam"}}],
            "ScannedCount": 1,
        }

    def test_simple_select(self):
        command = ['ddb', 'select', 'mytable']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, ['Scan'])
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_query(self):
        self.parsed_response = {
            "Count": 1,
            "Items": [{"foo": {"N": "2"}}],
            "ScannedCount": 1,
        }
        command = [
            'ddb', 'select', 'mytable', '--key-condition', 'foo = 1'
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'KeyConditionExpression': '#n0 = :n1',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {':n1': {'N': '1'}}
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, ['Query'])

    def test_select_with_index_name(self):
        command = ['ddb', 'select', 'mytable', '--index-name', 'myindex']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'IndexName': 'myindex',
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_projection(self):
        command = [
            'ddb', 'select', 'mytable', '--projection', 'foo'
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'ProjectionExpression': '#n0',
            'ExpressionAttributeNames': {'#n0': 'foo'},
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_filter(self):
        self.parsed_response = {
            "Count": 1,
            "Items": [{"foo": {"N": "2"}}],
            "ScannedCount": 1,
        }
        command = [
            'ddb', 'select', 'mytable', '--filter', 'foo BETWEEN 1 AND 3'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': '#n0 BETWEEN :n1 AND :n2',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                ':n1': {'N': '1'},
                ':n2': {'N': '3'},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_filter_with_function(self):
        command = [
            'ddb', 'select', 'mytable', '--filter', 'contains(foo, "bar")'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': 'contains(#n0, :n1)',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                ':n1': {'S': 'bar'},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_filter_with_set(self):
        command = [
            'ddb', 'select', 'mytable', '--filter', 'foo = {1, 2, 3}'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': '#n0 = :n1',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                ':n1': {'NS': ['1', '2', '3']},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_filter_with_bytes(self):
        command = [
            'ddb', 'select', 'mytable', '--filter', 'foo <> b"4pyT"'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': '#n0 <> :n1',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                # This will be base64 encoded during serialization
                ':n1': {'B': b'\xe2\x9c\x93'},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_filter_with_list(self):
        command = [
            'ddb', 'select', 'mytable', '--filter', 'foo <> [-1, 2, "3"]'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': '#n0 <> :n1',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                ':n1': {'L': [
                    {'N': '-1'}, {'N': '2'}, {'S': '3'},
                ]},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_filter_with_map(self):
        command = [
            'ddb', 'select', 'mytable', '--filter', 'foo <> {"bar": 4}'
        ]

        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'FilterExpression': '#n0 <> :n1',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'ExpressionAttributeValues': {
                ':n1': {'M': {"bar": {"N": "4"}}},
            }
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_attributes_all(self):
        command = [
            'ddb', 'select', 'mytable', '--attributes', 'ALL'
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'Select': 'ALL_ATTRIBUTES',
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_attributes_all_projected(self):
        command = [
            'ddb', 'select', 'mytable', '--attributes', 'ALL_PROJECTED',
            '--index-name', 'myindex',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'Select': 'ALL_PROJECTED_ATTRIBUTES',
            'IndexName': 'myindex',
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_attributes_count(self):
        self.parsed_response = {
            "Count": 1,
            "ScannedCount": 1,
        }
        command = [
            'ddb', 'select', 'mytable', '--attributes', 'COUNT'
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'Select': 'COUNT',
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_consistent_read(self):
        command = [
            'ddb', 'select', 'mytable', '--consistent-read',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_no_consistent_read(self):
        command = [
            'ddb', 'select', 'mytable', '--no-consistent-read',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': False,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_no_return_consumed_capacity(self):
        command = [
            'ddb', 'select', 'mytable', '--no-return-consumed-capacity',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_return_consumed_capacity(self):
        command = [
            'ddb', 'select', 'mytable', '--return-consumed-capacity',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'TOTAL',
            'ConsistentRead': True,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_return_consumed_capacity_with_index(self):
        command = [
            'ddb', 'select', 'mytable', '--return-consumed-capacity',
            '--index-name', 'myindex',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'INDEXES',
            'ConsistentRead': True,
            'IndexName': 'myindex',
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response)

    def test_select_with_query(self):
        command = [
            'ddb', 'select', 'mytable', '--query', 'Items'
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        self.assert_yaml_response_equal(stdout, self.parsed_response['Items'])

    def test_select_returns_bytes(self):
        self.parsed_response = {
            "Count": 1,
            "Items": [{"foo": {"B": b"\xe2\x9c\x93"}}],
            "ScannedCount": 1,
        }
        command = ['ddb', 'select', 'mytable']
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        expected = {
            'Count': 1,
            'Items': [{"foo": b'\xe2\x9c\x93'}],
            "ScannedCount": 1,
        }
        self.assert_yaml_response_equal(stdout, expected)

    def test_consumed_capacity_omitted_if_none(self):
        self.parsed_response = {
            "Count": 1,
            "Items": [{"foo": {"S": "spam"}}],
            "ScannedCount": 1,
            "ConsumedCapacity": None,
        }
        command = ['ddb', 'select', 'mytable']
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        expected = {
            "Count": 1,
            "Items": [{"foo": "spam"}],
            "ScannedCount": 1,
        }
        self.assert_yaml_response_equal(stdout, expected)

    def test_select_with_multiple_expressions(self):
        self.parsed_response = {
            'Count': 1,
            'Items': [{'name': {'S': 'macbook'}, 'price': {'N': '2000'}}],
            'ScannedCount': 1,
        }
        command = [
            'ddb', 'select', 'laptops',
            '--projection', 'name, price',
            '--filter', 'price < 3000',
            '--key-condition', 'name = "macbook"',
        ]
        expected = {
            'TableName': 'laptops',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'ProjectionExpression': '#n0, #n1',
            'FilterExpression': '#n2 < :n3',
            'KeyConditionExpression': '#n4 = :n5',
            'ExpressionAttributeNames': {
                '#n0': 'name',
                '#n1': 'price',
                '#n2': 'price',
                '#n4': 'name',
            },
            'ExpressionAttributeValues': {
                ':n3': {'N': '3000'},
                ':n5': {'S': 'macbook'},
            }

        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected, expected_rc=0
        )

    def test_select_project_complex_identifier(self):
        self.parsed_response = {
            'Count': 1,
            'Items': [{
                'name': {'S': 'spam n eggs'},
                'ingredients': {'L': [{'M': {'name': {'S': 'spam'}}}]},
            }]
        }
        command = [
            'ddb', 'select', 'recipes',
            '--projection', 'name, ingredients[8].name',
        ]
        expected = {
            'TableName': 'recipes',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'ProjectionExpression': '#n0, #n1[8].#n2',
            'ExpressionAttributeNames': {
                '#n0': 'name',
                '#n1': 'ingredients',
                '#n2': 'name',
            }
        }
        self.assert_params_for_cmd(
            command, expected, expected_rc=0
        )

    def test_select_does_not_support_yaml_stream(self):
        cmdline = 'ddb select mytable --output yaml-stream'
        stdout, _, _ = self.assert_params_for_cmd(
            cmdline, expected_rc=252,
            stderr_contains='yaml-stream output format is not supported',
        )

    def test_select_parsing_error_rc(self):
        cmdline = 'ddb select mytable --filter a=?!f'
        stdout, _, _ = self.assert_params_for_cmd(
            cmdline, expected_rc=252,
        )


class TestSelectPagination(BaseSelectTest):
    def setUp(self):
        super(TestSelectPagination, self).setUp()
        self.parsed_responses = [
            {
                "Count": 1,
                "Items": [{"foo": {"N": "1"}}],
                "ScannedCount": 1,
                "LastEvaluatedKey": {"foo": {"N": "1"}},
            },
            {
                "Count": 1,
                "Items": [{"foo": {"N": "2"}}],
                "ScannedCount": 1,
            },
        ]

    def test_select_paginates(self):
        command = [
            'ddb', 'select', 'mytable'
        ]
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        expected_response = {
            'Count': 2,
            'Items': [
                {'foo': 1},
                {'foo': 2}
            ],
            'ScannedCount': 2
        }
        self.assert_yaml_response_equal(stdout, expected_response)

    def test_no_paginate(self):
        command = [
            'ddb', 'select', 'mytable', '--no-paginate'
        ]
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        expected_response = {
            "Count": 1,
            "Items": [{"foo": 1}],
            "ScannedCount": 1,
            "LastEvaluatedKey": {"foo": 1},
        }
        self.assert_yaml_response_equal(stdout, expected_response)

    def test_no_paginate_with_paging_params_set(self):
        command = [
            'ddb', 'select', 'mytable', '--no-paginate', '--max-items', '1'
        ]
        _, stderr, _ = self.run_cmd(command, expected_rc=252)
        self.assertIn('Cannot specify --no-paginate along with ', stderr)

    def test_max_items(self):
        command = [
            'ddb', 'select', 'mytable', '--max-items', '1'
        ]
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        expected_response = {
            'Count': 1,
            'Items': [
                {'foo': 1},
            ],
            'ScannedCount': 1,
            'NextToken': (
                'eyJFeGNsdXNpdmVTdGFydEtleSI6IHsiZm9vIjogeyJOIjogIjEifX19'
            ),
        }
        self.assert_yaml_response_equal(stdout, expected_response)

    def test_page_size(self):
        command = [
            'ddb', 'select', 'mytable', '--page-size', '1'
        ]
        stdout, _, _ = self.run_cmd(command, expected_rc=0)
        params = self.operations_called[1][1]
        expected_initial_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'ExclusiveStartKey': {"foo": {"N": "1"}},
            'Limit': 1,
        }
        self.assertEqual(params, expected_initial_params)

        expected_response = {
            'Count': 2,
            'Items': [
                {'foo': 1},
                {'foo': 2}
            ],
            'ScannedCount': 2
        }
        self.assert_yaml_response_equal(stdout, expected_response)

    def test_starting_token(self):
        self.parsed_responses = [{
            "Count": 1,
            "Items": [{"foo": {"N": "2"}}],
            "ScannedCount": 1,
        }]
        command = [
            'ddb', 'select', 'mytable', '--starting-token',
            'eyJFeGNsdXNpdmVTdGFydEtleSI6IHsiZm9vIjogeyJOIjogIjEifX19',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConsistentRead': True,
            'ExclusiveStartKey': {"foo": {"N": "1"}},
        }
        stdout, _, _ = self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        expected_response = {
            'Count': 0,
            'Items': [
                {'foo': 2}
            ],
            'ScannedCount': 0
        }
        self.assert_yaml_response_equal(stdout, expected_response)

