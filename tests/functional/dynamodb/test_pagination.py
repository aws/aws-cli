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
import json

from awscli.testutils import BaseAWSCommandParamsTest


class TestPagination(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestPagination, self).setUp()
        self.first_response = {
            "Items": [{"Key": {"B": "MjEzNw=="}}],
            "Count": 1,
            "ScannedCount": 1,
            "ConsumedCapacity": 1,
            "LastEvaluatedKey": {"Key": {"B":"MjEzNw=="}}
        }
        self.second_response = {
            "Items": [],
            "Count": 0,
            "ScannedCount": 1,
            "ConsumedCapacity": 1
        }

    def test_scan_pagination_binary_last_evaluated_key(self):
        self.parsed_responses = [self.first_response, self.second_response]
        self.run_cmd('dynamodb scan --table-name test', expected_rc=0)
        self.assertEqual(len(self.operations_called), 2)
        # The start key in the second request should have been parsed to binary
        sent_start_key = self.operations_called[1][1].get('ExclusiveStartKey')
        expected_start_key = {"Key": {"B": b'2137'}}
        self.assertEqual(sent_start_key, expected_start_key)

    def test_pagination_disabled_works(self):
        self.parsed_responses = [self.first_response]
        cmd = 'dynamodb scan --table-name table --no-paginate --output json'
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        # Ensure the base64 encoded last evaluated key is in stdout
        self.assertIn('"MjEzNw=="', stdout)
