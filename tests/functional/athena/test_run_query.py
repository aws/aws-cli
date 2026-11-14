# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

_MUTATING = {
    'CreateWorkGroup',
    'CreateNamedQuery',
    'UpdateWorkGroup',
    'DeleteWorkGroup',
}


class TestRunQueryCommand(BaseAWSCommandParamsTest):
    def _lifecycle_responses(self):
        return [
            {
                'WorkGroup': {
                    'State': 'ENABLED',
                    'Configuration': {
                        'ResultConfiguration': {
                            'OutputLocation': 's3://results/'
                        },
                        'EngineVersion': {
                            'EffectiveEngineVersion': 'Athena engine version 3'
                        },
                    },
                }
            },
            {'QueryExecutionId': 'q-123'},
            {
                'QueryExecution': {
                    'Status': {'State': 'SUCCEEDED'},
                    'StatementType': 'DML',
                    'Statistics': {'DataScannedInBytes': 10},
                    'ResultConfiguration': {'OutputLocation': 's3://r/q.csv'},
                }
            },
            {
                'ResultSet': {
                    'ResultSetMetadata': {
                        'ColumnInfo': [{'Name': 'c1', 'Type': 'varchar'}]
                    },
                    'Rows': [
                        {'Data': [{'VarCharValue': 'c1'}]},
                        {'Data': [{'VarCharValue': 'hello'}]},
                    ],
                }
            },
        ]

    def test_runs_full_read_only_lifecycle(self):
        self.parsed_responses = self._lifecycle_responses()
        stdout, _, rc = self.run_cmd(
            [
                'athena',
                'run-query',
                '--sql',
                'SELECT c1 FROM t',
                '--workgroup',
                'primary',
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(
            names,
            [
                'GetWorkGroup',
                'StartQueryExecution',
                'GetQueryExecution',
                'GetQueryResults',
            ],
        )
        # No mutating operation is ever issued.
        self.assertFalse(_MUTATING.intersection(names))
        parsed = json.loads(stdout)
        self.assertEqual(parsed['query_execution_id'], 'q-123')
        self.assertEqual(parsed['rows'], [{'c1': 'hello'}])

    def test_failed_query_returns_operational_error(self):
        self.parsed_responses = [
            {
                'WorkGroup': {
                    'State': 'ENABLED',
                    'Configuration': {
                        'ResultConfiguration': {
                            'OutputLocation': 's3://results/'
                        }
                    },
                }
            },
            {'QueryExecutionId': 'q-9'},
            {
                'QueryExecution': {
                    'Status': {
                        'State': 'FAILED',
                        'StateChangeReason': 'bad column',
                        'AthenaError': {'ErrorCategory': 2},
                    },
                    'StatementType': 'DML',
                }
            },
        ]
        stdout, _, rc = self.run_cmd(
            [
                'athena',
                'run-query',
                '--sql',
                'SELECT x FROM t',
                '--workgroup',
                'primary',
                '--region',
                'us-east-1',
            ],
            expected_rc=255,
        )
        self.assertNotIn(
            'StopQueryExecution', [c[0].name for c in self.operations_called]
        )
