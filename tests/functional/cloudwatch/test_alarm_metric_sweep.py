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

# Any of these appearing in operations_called would mean the "read-only" command
# issued a write; the suite asserts none ever do.
_MUTATING = {
    'PutMetricAlarm',
    'DeleteAlarms',
    'SetAlarmState',
    'PutDashboard',
    'PutMetricData',
    'TagResource',
}


class TestAlarmMetricSweepCommand(BaseAWSCommandParamsTest):
    def _metric_alarm_responses(self):
        return [
            # resolve_alarm exact hit
            {
                'MetricAlarms': [
                    {
                        'AlarmName': 'cpu-high',
                        'AlarmArn': (
                            'arn:aws:cloudwatch:us-east-1:1:alarm:cpu-high'
                        ),
                        'StateValue': 'ALARM',
                        'Namespace': 'AWS/EC2',
                        'MetricName': 'CPUUtilization',
                        'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-1'}],
                        'Statistic': 'Average',
                        'Period': 300,
                        'Threshold': 80.0,
                        'ComparisonOperator': 'GreaterThanThreshold',
                        'EvaluationPeriods': 1,
                    }
                ],
                'CompositeAlarms': [],
            },
            {'AlarmHistoryItems': []},
            {
                'MetricDataResults': [
                    {
                        'Id': 'alarm_metric',
                        'Label': 'cpu-high',
                        'Timestamps': ['2023-11-14T19:00:00Z'],
                        'Values': [42.0],
                        'StatusCode': 'Complete',
                    }
                ]
            },
            {
                'MetricDataResults': [
                    {
                        'Id': 'zs0',
                        'Label': 'CPUUtilization',
                        'Timestamps': ['2023-11-14T19:00:00Z'],
                        'Values': [42.0],
                        'StatusCode': 'Complete',
                    }
                ]
            },
        ]

    def test_command_is_registered_and_runs_read_only(self):
        self.parsed_responses = self._metric_alarm_responses()
        # Default window (last 3h from "now") keeps the request within
        # CloudWatch's 455-day retention regardless of when the test runs.
        stdout, _, rc = self.run_cmd(
            [
                'cloudwatch',
                'alarm-metric-sweep',
                '--alarm-name',
                'cpu-high',
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        # Resolution begins with an exact DescribeAlarms and only read ops run.
        self.assertEqual(names[0], 'DescribeAlarms')
        self.assertTrue(
            all(n.startswith(('Describe', 'Get', 'List')) for n in names)
        )
        self.assertFalse(_MUTATING.intersection(names))
        parsed = json.loads(stdout)
        self.assertEqual(parsed['target']['alarm_name'], 'cpu-high')
        self.assertEqual(parsed['target']['match'], 'exact')

    def test_missing_alarm_is_operational_error(self):
        # Exact miss then prefix miss -> NOT_FOUND -> rc 255.
        self.parsed_responses = [
            {'MetricAlarms': [], 'CompositeAlarms': []},
            {'MetricAlarms': [], 'CompositeAlarms': []},
        ]
        _, stderr, rc = self.run_cmd(
            [
                'cloudwatch',
                'alarm-metric-sweep',
                '--alarm-name',
                'ghost',
                '--region',
                'us-east-1',
            ],
            expected_rc=255,
        )
        self.assertIn('NOT_FOUND', stderr)

    def test_invalid_parameter_rejected_before_any_call(self):
        self.parsed_responses = []
        self.run_cmd(
            [
                'cloudwatch',
                'alarm-metric-sweep',
                '--alarm-name',
                'cpu-high',
                '--period-s',
                '0',
                '--region',
                'us-east-1',
            ],
            expected_rc=252,
        )
        # Nothing was dispatched to AWS for bad input.
        self.assertEqual(self.operations_called, [])
