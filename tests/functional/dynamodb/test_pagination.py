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
        super().setUp()
        self.first_response = {
            "Items": [{"Key": {"B": "MjEzNw=="}}],
            "Count": 1,
            "ScannedCount": 1,
            "ConsumedCapacity": 1,
            "LastEvaluatedKey": {"Key": {"B": "MjEzNw=="}},
        }
        self.second_response = {
            "Items": [],
            "Count": 0,
            "ScannedCount": 1,
            "ConsumedCapacity": 1,
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


class TestConsumedCapacityAggregation(BaseAWSCommandParamsTest):
    """CLI-4199: ConsumedCapacity must be summed across paginated pages.

    Numeric leaves (top-level, Table.*, and per-index maps via wildcard result
    keys) are summed; TableName is taken from the first page.
    """

    def _page(self, consumed_capacity, last_key=None):
        page = {
            "Items": [{"Key": {"S": "item"}}],
            "Count": 1,
            "ScannedCount": 1,
            "ConsumedCapacity": consumed_capacity,
        }
        if last_key is not None:
            page["LastEvaluatedKey"] = last_key
        return page

    def test_scan_sums_total_consumed_capacity(self):
        self.parsed_responses = [
            self._page(
                {"TableName": "T", "CapacityUnits": 100.0},
                last_key={"Key": {"S": "a"}},
            ),
            self._page({"TableName": "T", "CapacityUnits": 102.0}),
        ]
        cmd = (
            'dynamodb scan --table-name T --output json '
            '--return-consumed-capacity TOTAL'
        )
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        result = json.loads(stdout)
        self.assertEqual(result["ConsumedCapacity"]["CapacityUnits"], 202.0)
        self.assertEqual(result["ConsumedCapacity"]["TableName"], "T")
        self.assertEqual(result["Count"], 2)
        self.assertEqual(result["ScannedCount"], 2)

    def test_scan_sums_index_consumed_capacity_wildcard(self):
        # The per-index map is keyed by a runtime index name; the wildcard
        # result key sums each index across pages, and distinct indexes keep
        # distinct counters.
        self.parsed_responses = [
            self._page(
                {
                    "TableName": "T",
                    "CapacityUnits": 100.0,
                    "Table": {"CapacityUnits": 0.0},
                    "GlobalSecondaryIndexes": {
                        "gsi-a": {"CapacityUnits": 40.0},
                        "gsi-b": {"CapacityUnits": 10.0},
                    },
                },
                last_key={"Key": {"S": "a"}},
            ),
            self._page(
                {
                    "TableName": "T",
                    "CapacityUnits": 102.0,
                    "Table": {"CapacityUnits": 0.0},
                    "GlobalSecondaryIndexes": {
                        "gsi-a": {"CapacityUnits": 2.0},
                        "gsi-b": {"CapacityUnits": 5.0},
                    },
                }
            ),
        ]
        cmd = (
            'dynamodb scan --table-name T --index-name gsi-a '
            '--output json --return-consumed-capacity INDEXES'
        )
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        cc = json.loads(stdout)["ConsumedCapacity"]
        self.assertEqual(cc["CapacityUnits"], 202.0)
        self.assertEqual(cc["Table"]["CapacityUnits"], 0.0)
        gsi = cc["GlobalSecondaryIndexes"]
        self.assertEqual(gsi["gsi-a"]["CapacityUnits"], 42.0)
        self.assertEqual(gsi["gsi-b"]["CapacityUnits"], 15.0)

    def test_query_sums_total_consumed_capacity(self):
        self.parsed_responses = [
            self._page(
                {"TableName": "T", "CapacityUnits": 5.5},
                last_key={"Key": {"S": "a"}},
            ),
            self._page({"TableName": "T", "CapacityUnits": 4.5}),
        ]
        cmd = (
            'dynamodb query --table-name T --output json '
            '--key-condition-expression Id=:id '
            '--expression-attribute-values {":id":{"S":"x"}} '
            '--return-consumed-capacity TOTAL'
        )
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        result = json.loads(stdout)
        self.assertEqual(result["ConsumedCapacity"]["CapacityUnits"], 10.0)

    def test_no_consumed_capacity_when_not_requested(self):
        # No ConsumedCapacity in the responses -> it must be entirely absent
        # from the aggregated output (no summed value, and no phantom
        # {"TableName": null} from the non_aggregate leaf).
        self.parsed_responses = [
            {
                "Items": [{"Key": {"S": "a"}}],
                "Count": 1,
                "ScannedCount": 1,
                "LastEvaluatedKey": {"Key": {"S": "a"}},
            },
            {"Items": [{"Key": {"S": "b"}}], "Count": 1, "ScannedCount": 1},
        ]
        cmd = 'dynamodb scan --table-name T --output json'
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        result = json.loads(stdout)
        self.assertEqual(result["Count"], 2)
        self.assertNotIn("ConsumedCapacity", result)

    def test_scan_sums_vector_index_consumed_capacity(self):
        self.parsed_responses = [
            self._page(
                {
                    "TableName": "T",
                    "CapacityUnits": 1.0,
                    "VectorIndexes": {
                        "vidx": {
                            "VectorSearchRequestBytes": 100.0,
                            "VectorWriteRequestBytes": 0.0,
                        }
                    },
                },
                last_key={"Key": {"S": "a"}},
            ),
            self._page(
                {
                    "TableName": "T",
                    "CapacityUnits": 1.0,
                    "VectorIndexes": {
                        "vidx": {
                            "VectorSearchRequestBytes": 50.0,
                            "VectorWriteRequestBytes": 0.0,
                        }
                    },
                }
            ),
        ]
        cmd = (
            'dynamodb scan --table-name T --output json '
            '--return-consumed-capacity INDEXES'
        )
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        cc = json.loads(stdout)["ConsumedCapacity"]
        self.assertEqual(
            cc["VectorIndexes"]["vidx"]["VectorSearchRequestBytes"], 150.0
        )
