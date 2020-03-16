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
import os
import shutil
import tempfile

import ruamel.yaml as yaml

from awscli.testutils import BaseAWSCommandParamsTest, capture_input


class TestPut(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestPut, self).setUp()
        self.parsed_response = {}
        self.tempdir = tempfile.mkdtemp()
        self.original_tag_handlers = yaml.YAML(typ='safe').constructor\
            .yaml_constructors.copy()

    def tearDown(self):
        super(TestPut, self).tearDown()
        shutil.rmtree(self.tempdir)
        # This line looks wrong, right?  Well... the "yaml_constructors"
        # is actually a class attribute that's shared across *all* of the
        # yaml.YAML() instances.  Because the ddb customization registers
        # a custom handler for the binary and float types, this will break
        # other code (and tests) that rely on the default behavior.  So
        # to fix this, we put back the original tag handlers that we saved
        # in self.original_tag_handlers to ensure we handle binary and
        # float types correctly.
        yaml.YAML(typ='safe').constructor.yaml_constructors.update(
            self.original_tag_handlers)

    def assert_yaml_response_equal(self, response, expected):
        with self.assertRaises(ValueError):
            json.loads(response)
        loaded = yaml.safe_load(response)
        self.assertEqual(loaded, expected)

    def test_simple_put(self):
        command = ['ddb', 'put', 'mytable', '{foo: bar}']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"S": "bar"}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, ['PutItem'])

    def test_batch_write(self):
        command = [
            'ddb', 'put', 'mytable', '[{foo: bar}, {foo: bar}]'
        ]
        expected_params = {
            'ReturnConsumedCapacity': 'NONE',
            'RequestItems': {
                'mytable': [
                    {'PutRequest': {'Item': {'foo': {'S': 'bar'}}}},
                    {'PutRequest': {'Item': {'foo': {'S': 'bar'}}}},
                ]
            }
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, ['BatchWriteItem'])

    def test_batch_write_multiple_batches(self):
        items = ', '.join(["{foo: bar}" for _ in range(40)])
        command = [
            'ddb', 'put', 'mytable', '[%s]' % items
        ]
        self.run_cmd(command, expected_rc=0)
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, [
            'BatchWriteItem', 'BatchWriteItem'
        ])

        first_params = self.operations_called[0][1]
        num_items = len(first_params['RequestItems']['mytable'])
        self.assertEqual(num_items, 25)
        self.assertEqual(first_params.get('ReturnConsumedCapacity'), 'NONE')

        second_params = self.operations_called[1][1]
        num_items = len(second_params['RequestItems']['mytable'])
        self.assertEqual(num_items, 15)
        self.assertEqual(second_params.get('ReturnConsumedCapacity'), 'NONE')

    def test_batch_write_unprocessed_items(self):
        self.parsed_responses = [
            {
                'UnprocessedItems': {'mytable': [
                    {'PutRequest': {'Item': {'foo': {'S': 'bar'}}}},
                ]}
            },
            {
                'UnprocessedItems': {'mytable': [
                    {'PutRequest': {'Item': {'foo': {'S': 'bar'}}}},
                ]}
            },
            {},
        ]

        items = ', '.join(["{foo: bar}" for _ in range(40)])
        command = [
            'ddb', 'put', 'mytable', '[%s]' % items
        ]
        self.run_cmd(command, expected_rc=0)
        operations_called = [o[0].name for o in self.operations_called]
        self.assertEqual(operations_called, [
            'BatchWriteItem', 'BatchWriteItem', 'BatchWriteItem',
        ])

        first_params = self.operations_called[0][1]
        num_items = len(first_params['RequestItems']['mytable'])
        self.assertEqual(num_items, 25)

        second_params = self.operations_called[1][1]
        num_items = len(second_params['RequestItems']['mytable'])
        self.assertEqual(num_items, 16)

        third_params = self.operations_called[2][1]
        num_items = len(third_params['RequestItems']['mytable'])
        self.assertEqual(num_items, 1)

    def test_put_with_condition(self):
        command = [
            'ddb', 'put', 'mytable', '{foo: bar}',
            '--condition', 'attribute_exists(foo)',
        ]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'ConditionExpression': 'attribute_exists(#n0)',
            'ExpressionAttributeNames': {'#n0': 'foo'},
            'Item': {"foo": {"S": "bar"}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )

    def test_batch_write_with_condition(self):
        command = [
            'ddb', 'put', 'mytable', '[{foo: bar}, {foo: bar}]',
            '--condition', 'attribute_exists(foo)',
        ]
        _, stderr, _ = self.assert_params_for_cmd(command, expected_rc=252)
        self.assertIn('--condition is not supported', stderr)

    def test_load_items_from_file(self):
        filename = os.path.join(self.tempdir, 'items.yml')
        with open(filename, 'w') as f:
            f.write('{foo: bar}\n')

        command = ['ddb', 'put', 'mytable', 'file://%s' % filename]
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"S": "bar"}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )

    def test_load_items_from_stdin(self):
        command = ['ddb', 'put', 'mytable', '-']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"S": "bar"}},
        }
        with capture_input(b'{foo: bar}'):
            self.assert_params_for_cmd(
                command, expected_params, expected_rc=0
            )

    def test_put_bytes(self):
        command = ['ddb', 'put', 'mytable', '{foo: !!binary "4pyT"}']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"B": b'\xe2\x9c\x93'}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )

    def test_put_int(self):
        command = ['ddb', 'put', 'mytable', '{foo: 1}']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"N": "1"}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )

    def test_put_float(self):
        command = ['ddb', 'put', 'mytable', '{foo: 1.1}']
        expected_params = {
            'TableName': 'mytable',
            'ReturnConsumedCapacity': 'NONE',
            'Item': {"foo": {"N": "1.1"}},
        }
        self.assert_params_for_cmd(
            command, expected_params, expected_rc=0
        )
