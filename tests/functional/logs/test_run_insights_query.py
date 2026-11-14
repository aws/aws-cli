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

# Operations that would create, modify or delete state. The command must never
# issue any of these; the functional test asserts it.
_MUTATING = {
    'CreateLogGroup',
    'DeleteLogGroup',
    'PutLogEvents',
    'PutRetentionPolicy',
    'DeleteQueryDefinition',
}

# A window well in the past so it is never clamped to "now" and the single log
# group (no retention policy) always holds data in it, keeping the test
# deterministic regardless of the wall clock.
_START = '2024-01-01T00:00:00Z'
_END = '2024-01-01T01:00:00Z'

_ARN = 'arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/fn'


class TestRunInsightsQueryCommand(BaseAWSCommandParamsTest):
    def _lifecycle_responses(self):
        return [
            # 1. ListLogGroups discovers the group by name pattern.
            {
                'logGroups': [
                    {'logGroupName': '/aws/lambda/fn', 'logGroupArn': _ARN}
                ]
            },
            # 2. DescribeLogGroups enriches retention (none -> queryable).
            {
                'logGroups': [
                    {'logGroupName': '/aws/lambda/fn', 'arn': _ARN + ':*'}
                ]
            },
            # 3. StartQuery returns a non-blank queryId.
            {'queryId': 'q-1'},
            # 4. GetQueryResults returns a terminal, Complete result on the
            #    first poll so the bounded poller never sleeps.
            {
                'status': 'Complete',
                'results': [
                    [
                        {'field': '@message', 'value': 'hello'},
                        {'field': '@ptr', 'value': 'p1'},
                    ]
                ],
                'statistics': {},
            },
        ]

    def test_runs_full_read_only_lifecycle(self):
        self.parsed_responses = self._lifecycle_responses()
        stdout, _, rc = self.run_cmd(
            [
                'logs',
                'run-insights-query',
                '--log-group-names',
                '/aws/lambda/fn',
                '--query-string',
                'fields @timestamp, @message',
                '--start-time',
                _START,
                '--end-time',
                _END,
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(
            names,
            [
                'ListLogGroups',
                'DescribeLogGroups',
                'StartQuery',
                'GetQueryResults',
            ],
        )
        # No mutating operation is ever issued.
        self.assertFalse(_MUTATING.intersection(names))
        parsed = json.loads(stdout)
        self.assertEqual(parsed['row_count'], 1)
        self.assertEqual(parsed['rows'], [{'@message': 'hello', '@ptr': 'p1'}])

    def test_unknown_query_command_runs_instead_of_rejecting(self):
        # An unrecognized leading token is advisory now: the command dispatches
        # the full read-only lifecycle instead of rejecting locally (the server
        # would reject a query that is truly malformed).
        self.parsed_responses = self._lifecycle_responses()
        self.run_cmd(
            [
                'logs',
                'run-insights-query',
                '--log-group-names',
                '/aws/lambda/fn',
                '--query-string',
                'boguscmd @message',
                '--start-time',
                _START,
                '--end-time',
                _END,
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(
            names,
            [
                'ListLogGroups',
                'DescribeLogGroups',
                'StartQuery',
                'GetQueryResults',
            ],
        )

    def test_source_query_skips_resolution(self):
        # A query that begins with SOURCE selects its own log groups:
        # --log-group-names is omitted, no ListLogGroups/DescribeLogGroups run,
        # and StartQuery carries neither logGroupNames nor logGroupIdentifiers.
        self.parsed_responses = [
            {'queryId': 'q-1'},
            {
                'status': 'Complete',
                'results': [[{'field': '@ptr', 'value': 'p1'}]],
                'statistics': {},
            },
        ]
        self.run_cmd(
            [
                'logs',
                'run-insights-query',
                '--query-string',
                "SOURCE logGroups(namePrefix: ['/aws/lambda']) | "
                'fields @timestamp, @message',
                '--start-time',
                _START,
                '--end-time',
                _END,
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(names, ['StartQuery', 'GetQueryResults'])
        start_params = self.operations_called[0][1]
        self.assertNotIn('logGroupNames', start_params)
        self.assertNotIn('logGroupIdentifiers', start_params)

    def test_since_relative_window(self):
        # --since makes --start-time/--end-time optional and runs the full
        # read-only lifecycle over a now-relative window.
        self.parsed_responses = self._lifecycle_responses()
        self.run_cmd(
            [
                'logs',
                'run-insights-query',
                '--log-group-names',
                '/aws/lambda/fn',
                '--query-string',
                'fields @timestamp, @message',
                '--since',
                '1h',
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(
            names,
            [
                'ListLogGroups',
                'DescribeLogGroups',
                'StartQuery',
                'GetQueryResults',
            ],
        )

    def test_since_conflicts_with_start_time(self):
        # --since and --start-time together are rejected as a param error
        # (exit code 252) before any AWS call.
        self.parsed_responses = self._lifecycle_responses()
        self.run_cmd(
            [
                'logs',
                'run-insights-query',
                '--log-group-names',
                '/aws/lambda/fn',
                '--query-string',
                'fields @message',
                '--since',
                '1h',
                '--start-time',
                _START,
                '--region',
                'us-east-1',
            ],
            expected_rc=252,
        )
        self.assertEqual(self.operations_called, [])
