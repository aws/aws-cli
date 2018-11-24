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
from datetime import datetime

from dateutil import tz

from awscli.testutils import mock, BaseAWSCommandParamsTest


class TestTailCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestTailCommand, self).setUp()
        self.group_name = 'mygroup'
        self.stream_name = 'mystream'
        self.response_log_timestamp = 1100  # 1.1 seconds
        self.formatted_log_timestamp = '1970-01-01T00:00:01.100000+00:00'
        self.formatted_short_log_timestamp = '1970-01-01T00:00:01'
        self.message = 'my message\n'
        self.parsed_responses = [
            {
                "events": [
                    {
                        'eventId': 'event1',
                        'logStreamName': self.stream_name,
                        'message': self.message,
                        'timestamp': self.response_log_timestamp,
                        'ingestionTime': self.response_log_timestamp,
                    }
                ]
            }
        ]

    def tearDown(self):
        super(TestTailCommand, self).tearDown()

    def test_tail(self):
        stdout, _, _ = self.assert_params_for_cmd(
            'logs tail %s' % self.group_name,
            params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': mock.ANY
            }
        )
        self.assertEqual(
            stdout,
            '%s %s %s' % (
                self.formatted_log_timestamp, self.stream_name, self.message)
        )

    def test_tail_paginated(self):
        self.parsed_responses = [
            {
                "events": [
                    {
                        'eventId': 'event1',
                        'logStreamName': self.stream_name,
                        'message': self.message,
                        'timestamp': self.response_log_timestamp,
                        'ingestionTime': self.response_log_timestamp,
                    }
                ],
                'nextToken': 'token'
            },
            {
                "events": [
                    {
                        'eventId': 'event2',
                        'logStreamName': self.stream_name,
                        'message': self.message,
                        'timestamp': self.response_log_timestamp,
                        'ingestionTime': self.response_log_timestamp,
                    }
                ],
            }
        ]
        stdout, _, _ = self.run_cmd('logs tail %s' % self.group_name)
        self.assertEqual(len(self.operations_called), 2)
        self.assertEqual(
            self.operations_called[0][0].name, 'FilterLogEvents')
        self.assertEqual(
            self.operations_called[0][1],
            {
                'logGroupName': 'mygroup',
                'interleaved': True,
                'startTime': mock.ANY,
            }
        )
        self.assertEqual(
            self.operations_called[1][0].name, 'FilterLogEvents')
        self.assertEqual(
            self.operations_called[1][1],
            {
                'logGroupName': 'mygroup',
                'interleaved': True,
                'startTime': mock.ANY,
                'nextToken': 'token'
            }
        )
        self.assertEqual(
            stdout,
            '%s %s %s' % (
                self.formatted_log_timestamp, self.stream_name,
                self.message) * 2
        )

    def test_tail_with_follow(self):
        self.parsed_responses = [
            {
                "events": [
                    {
                        'eventId': 'event1',
                        'logStreamName': self.stream_name,
                        'message': self.message,
                        'timestamp': self.response_log_timestamp,
                        'ingestionTime': self.response_log_timestamp,
                    }
                ],
            },
            {
                "events": [
                    {
                        'eventId': 'event2',
                        'logStreamName': self.stream_name,
                        'message': self.message,
                        'timestamp': self.response_log_timestamp,
                        'ingestionTime': self.response_log_timestamp,
                    }
                ],
            }
        ]
        with mock.patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt]
            stdout, _, _ = self.run_cmd(
                'logs tail %s --follow' % self.group_name)
            self.assertEqual(
                stdout,
                '%s %s %s' % (
                    self.formatted_log_timestamp, self.stream_name,
                    self.message) * 2
            )

    def test_tail_defaults_to_10m(self):
        datetime_mock = mock.Mock(wraps=datetime)
        datetime_mock.utcnow = mock.Mock(
            return_value=datetime(1970, 1, 1, 0, 10, 1, tzinfo=tz.tzutc()))
        with mock.patch('awscli.customizations.logs.tail.datetime',
                        new=datetime_mock):
            self.assert_params_for_cmd(
                'logs tail %s' % self.group_name,
                params={
                    'logGroupName': self.group_name,
                    'interleaved': True,
                    'startTime': 1000,
                }
            )

    def test_tail_with_since(self):
        self.assert_params_for_cmd(
            'logs tail %s --since 1970-01-01T00:00:01' % self.group_name,
            params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': 1000
            }
        )

    def test_tail_with_relative_since(self):
        datetime_mock = mock.Mock(wraps=datetime)
        datetime_mock.utcnow = mock.Mock(
            return_value=datetime(1970, 1, 1, 0, 0, 2, tzinfo=tz.tzutc()))
        with mock.patch('awscli.customizations.logs.tail.datetime',
                        new=datetime_mock):
            self.assert_params_for_cmd(
                'logs tail %s --since 1s' % self.group_name,
                params={
                    'logGroupName': self.group_name,
                    'interleaved': True,
                    'startTime': 1000,
                }
            )

    def test_tail_with_filter_pattern(self):
        self.assert_params_for_cmd(
            'logs tail %s --filter-pattern Pattern' % self.group_name,
            params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': mock.ANY,
                'filterPattern': 'Pattern'
            }
        )

    def test_tail_with_short_format(self):
        stdout, _, _ = self.run_cmd(
            'logs tail %s --format short' % self.group_name)
        self.assertEqual(
            stdout,
            '%s %s' % (self.formatted_short_log_timestamp, self.message)
        )

    def test_tail_with_color_on(self):
        stdout, _, _ = self.run_cmd(
            'logs tail %s --color on' % self.group_name)
        self.assertEqual(
            stdout,
            "\x1b[32m%s\x1b[0m \x1b[36m%s\x1b[0m %s" % (
                self.formatted_log_timestamp, self.stream_name, self.message)
        )

    def test_tail_with_color_off(self):
        stdout, _, _ = self.run_cmd(
            'logs tail %s --color off' % self.group_name)
        self.assertEqual(
            stdout,
            "%s %s %s" % (
                self.formatted_log_timestamp, self.stream_name, self.message)
        )

    def test_tail_no_color_when_tty(self):
        with mock.patch(
                'awscli.customizations.logs.tail.is_a_tty') as mock_is_a_tty:
            mock_is_a_tty.return_value = True
            stdout, _, _ = self.run_cmd(
                'logs tail %s' % self.group_name)
        self.assertEqual(
            stdout,
            "\x1b[32m%s\x1b[0m \x1b[36m%s\x1b[0m %s" % (
                self.formatted_log_timestamp, self.stream_name, self.message)
        )
