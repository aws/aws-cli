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
import time
from datetime import datetime, timedelta

from botocore.session import Session
from botocore.stub import Stubber
from dateutil import tz

from awscli.compat import StringIO
from awscli.customizations.logs.tail import (
    DetailedLogEventsFormatter,
    FollowLogEventsGenerator,
    NoFollowLogEventsGenerator,
    PrettyJSONLogEventsFormatter,
    ShortLogEventsFormatter,
    TimestampUtils,
)
from awscli.testutils import mock, unittest


class BaseLogEventsFormatterTest(unittest.TestCase):
    FORMATTER_CLS = None

    def setUp(self):
        self.log_event = {
            'timestamp': datetime(2018, 1, 1, 0, 29, 43, 79060, tz.tzutc()),
            'logStreamName': 'stream_name',
            'message': 'my message',
        }
        self.output = StringIO()

    def assert_formatted_display(self, expected_msg, **init_kwargs):
        self.FORMATTER_CLS(self.output, **init_kwargs).display_log_event(
            self.log_event
        )
        self.assertEqual(expected_msg, self.output.getvalue())


class TestShortLogEventsFormatter(BaseLogEventsFormatterTest):
    FORMATTER_CLS = ShortLogEventsFormatter

    def test_display(self):
        self.assert_formatted_display(
            '\x1b[32m2018-01-01T00:29:43\x1b[0m my message\n',
        )

    def test_display_no_color(self):
        self.assert_formatted_display(
            '2018-01-01T00:29:43 my message\n',
            colorize=False,
        )

    def test_ensures_single_newline_ending(self):
        self.log_event['message'] = self.log_event['message'] + '\n\n'
        self.assert_formatted_display(
            '2018-01-01T00:29:43 my message\n', colorize=False
        )

    def test_handles_unicode(self):
        self.log_event['message'] = self.log_event['message'] + '\u00e9'
        self.assert_formatted_display(
            '2018-01-01T00:29:43 my message\u00e9\n', colorize=False
        )


class TestPrettyJSONLogEventsFormatter(BaseLogEventsFormatterTest):
    FORMATTER_CLS = PrettyJSONLogEventsFormatter

    def test_no_json_is_same_as_detailed_output(self):
        # The messages aren't displayed in color so this is the same output
        # regardless of whether or not you enable color.
        self.assert_formatted_display(
            '\x1b[32m2018-01-01T00:29:43.079060+00:00\x1b[0m '
            '\x1b[36mstream_name\x1b[0m '
            'my message\n'
        )

    def test_has_json_message(self):
        self.log_event['message'] = '{"foo": {"bar": "baz"}}'
        self.assert_formatted_display(
            '2018-01-01T00:29:43.079060+00:00 stream_name \n'
            '{\n'
            '    "foo": {\n'
            '        "bar": "baz"\n'
            '    }\n'
            '}\n',
            colorize=False,
        )


class TestDetailedLogEventsFormatter(BaseLogEventsFormatterTest):
    FORMATTER_CLS = DetailedLogEventsFormatter

    def test_display(self):
        self.assert_formatted_display(
            '\x1b[32m2018-01-01T00:29:43.079060+00:00\x1b[0m '
            '\x1b[36mstream_name\x1b[0m '
            'my message\n'
        )

    def test_display_no_color(self):
        self.assert_formatted_display(
            '2018-01-01T00:29:43.079060+00:00 stream_name my message\n',
            colorize=False,
        )

    def test_ensures_single_newline_ending(self):
        self.log_event['message'] = self.log_event['message'] + '\n\n'
        self.assert_formatted_display(
            '2018-01-01T00:29:43.079060+00:00 stream_name my message\n',
            colorize=False,
        )

    def test_handles_unicode(self):
        self.log_event['message'] = self.log_event['message'] + '\u00e9'
        self.assert_formatted_display(
            '2018-01-01T00:29:43.079060+00:00 stream_name my message\u00e9\n',
            colorize=False,
        )

    def test_display_with_zero_microseconds(self):
        self.log_event['timestamp'] = datetime(
            2018, 1, 1, 0, 29, 43, 0, tz.tzutc()
        )
        DetailedLogEventsFormatter(self.output).display_log_event(
            self.log_event
        )
        self.assertEqual(
            '\x1b[32m2018-01-01T00:29:43.000000+00:00\x1b[0m '
            '\x1b[36mstream_name\x1b[0m '
            'my message\n',
            self.output.getvalue(),
        )


class TestTimestampUtils(unittest.TestCase):
    def setUp(self):
        self.mock_now = mock.Mock()
        self.set_now()
        self.timestamp_utils = TimestampUtils(self.mock_now)

    def set_now(self, year=1970, month=1, day=1, hour=0, minute=0, sec=0):
        self.now = datetime(
            year, month, day, hour, minute, sec, tzinfo=tz.tzutc()
        )
        self.mock_now.return_value = self.now

    def test_to_epoch_absolute_timezone_unaware(self):
        self.assertEqual(
            self.timestamp_utils.to_epoch_millis('1970-01-01T00:00:01.000000'),
            1000,
        )

    def test_to_epoch_absolute_timezone_aware(self):
        self.assertEqual(
            self.timestamp_utils.to_epoch_millis(
                '1970-01-01T00:00:01.000000-01:00'
            ),
            3601000,
        )

    def test_to_epoch_relative_second(self):
        self.set_now(sec=2)
        self.assertEqual(self.timestamp_utils.to_epoch_millis('1s'), 1000)

    def test_to_epoch_relative_multiple_seconds(self):
        self.set_now(sec=5)
        self.assertEqual(self.timestamp_utils.to_epoch_millis('2s'), 3000)

    def test_to_epoch_relative_minute(self):
        self.set_now(minute=2)
        self.assertEqual(self.timestamp_utils.to_epoch_millis('1m'), 60 * 1000)

    def test_to_epoch_relative_hour(self):
        self.set_now(hour=2)
        self.assertEqual(
            self.timestamp_utils.to_epoch_millis('1h'), (60 * 60) * 1000
        )

    def test_to_epoch_relative_day(self):
        self.set_now(day=3)  # 1970-01-03
        self.assertEqual(
            self.timestamp_utils.to_epoch_millis('1d'),
            (24 * 60 * 60) * 1000,  # 1970-01-02
        )

    def test_to_epoch_relative_week(self):
        self.set_now(day=9)  # 1970-01-08
        self.assertEqual(
            self.timestamp_utils.to_epoch_millis('1w'),
            (24 * 60 * 60) * 1000,  # 1970-01-02
        )

    def test_to_datetime(self):
        self.assertEqual(
            self.timestamp_utils.to_datetime(1000),
            datetime(1970, 1, 1, 0, 0, 1, tzinfo=tz.tzutc()),
        )


class BaseLogEventsGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.client = self.session.create_client(
            'logs', region_name='us-west-2'
        )
        self.stubber = Stubber(self.client)
        self.group_name = 'groupName'
        self.start = '1970-01-01T00:00:01.000000'
        self.expected_start_as_milli_epoch = 1000
        self.filter_pattern = 'mypattern'
        self.log_stream_names = ['foo-stream', 'bar-stream']
        self.log_stream_name_prefix = 'foo'
        self.log_timestamp = 1000
        self.expected_log_timestamp_as_datetime = datetime(
            1970, 1, 1, 0, 0, 1, tzinfo=tz.tzutc()
        )

    def get_event(self, event_id, event_message, timestamp=None):
        if timestamp is None:
            timestamp = self.log_timestamp
        return {
            'eventId': event_id,
            'message': event_message,
            'timestamp': timestamp,
            'ingestionTime': self.log_timestamp,
        }

    def get_expected_event(self, event_id, event_message, add_seconds=0):
        return {
            'eventId': event_id,
            'message': event_message,
            'timestamp': self.expected_log_timestamp_as_datetime
            + timedelta(seconds=add_seconds),
            'ingestionTime': self.expected_log_timestamp_as_datetime,
        }


class TestNoFollowLogEventsGenerator(BaseLogEventsGeneratorTest):
    def test_iter_log_events(self):
        logs_generator = NoFollowLogEventsGenerator(
            self.client, TimestampUtils()
        )

        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message'),
                    self.get_event('event-2', 'event-2-message'),
                ],
                'nextToken': 'token',
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': self.expected_start_as_milli_epoch,
                'filterPattern': self.filter_pattern,
                'logStreamNames': self.log_stream_names,
                'logStreamNamePrefix': self.log_stream_name_prefix,
            },
        )
        # Add a new page that has no more results
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-3', 'event-3-message'),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': self.expected_start_as_milli_epoch,
                'filterPattern': self.filter_pattern,
                'logStreamNames': self.log_stream_names,
                'logStreamNamePrefix': self.log_stream_name_prefix,
                'nextToken': 'token',
            },
        )
        with self.stubber:
            log_events_iter = logs_generator.iter_log_events(
                self.group_name,
                self.start,
                self.filter_pattern,
                self.log_stream_names,
                self.log_stream_name_prefix,
            )
            actual_log_events = [event for event in log_events_iter]
        self.assertEqual(
            actual_log_events,
            [
                self.get_expected_event('event-1', 'event-1-message'),
                self.get_expected_event('event-2', 'event-2-message'),
                self.get_expected_event('event-3', 'event-3-message'),
            ],
        )


class TestFollowLogEventsGenerator(BaseLogEventsGeneratorTest):
    def setUp(self):
        super(TestFollowLogEventsGenerator, self).setUp()
        self.mock_sleep = mock.Mock(time.sleep)
        self.logs_generator = FollowLogEventsGenerator(
            self.client, TimestampUtils(), self.mock_sleep
        )

    def test_iter_log_events(self):
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message'),
                    self.get_event('event-2', 'event-2-message'),
                ],
                'nextToken': 'token',
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': self.expected_start_as_milli_epoch,
                'filterPattern': self.filter_pattern,
                'logStreamNames': self.log_stream_names,
                'logStreamNamePrefix': self.log_stream_name_prefix,
            },
        )
        # Add a new page that has no nextToken
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-3', 'event-3-message'),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': self.expected_start_as_milli_epoch,
                'filterPattern': self.filter_pattern,
                'logStreamNames': self.log_stream_names,
                'logStreamNamePrefix': self.log_stream_name_prefix,
                'nextToken': 'token',
            },
        )
        self.mock_sleep.side_effect = KeyboardInterrupt()
        with self.stubber:
            log_events_iter = self.logs_generator.iter_log_events(
                self.group_name,
                self.start,
                self.filter_pattern,
                self.log_stream_names,
                self.log_stream_name_prefix,
            )
            actual_log_events = [event for event in log_events_iter]
        self.mock_sleep.assert_called_once_with(5)
        self.assertEqual(
            actual_log_events,
            [
                self.get_expected_event('event-1', 'event-1-message'),
                self.get_expected_event('event-2', 'event-2-message'),
                self.get_expected_event('event-3', 'event-3-message'),
            ],
        )

    def test_polls_with_last_next_token(self):
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message', 1000),
                ],
                'nextToken': 'token',
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
            },
        )
        # Add a new page that has no nextToken
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-2', 'event-2-message', 2000),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'nextToken': 'token',
            },
        )

        # Because there is no token for the last page, it should remove
        # token from the kwargs and update startTime with the max
        # timestamp from the prvious response events
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-3', 'event-3-message', 3000),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': 2000,
            },
        )
        self.mock_sleep.side_effect = [None, KeyboardInterrupt()]
        with self.stubber:
            log_events_iter = self.logs_generator.iter_log_events(
                self.group_name
            )
            actual_log_events = [event for event in log_events_iter]
        self.mock_sleep.assert_has_calls([mock.call(5), mock.call(5)])
        self.assertEqual(
            actual_log_events,
            [
                self.get_expected_event('event-1', 'event-1-message'),
                self.get_expected_event('event-2', 'event-2-message', 1),
                self.get_expected_event('event-3', 'event-3-message', 2),
            ],
        )

    def test_iter_log_events_filters_empty_events_list(self):
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
            },
        )
        # Add a new page that has events
        # It should make a call with the same parameters as the
        # previous one
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message'),
                    self.get_event('event-2', 'event-2-message'),
                    self.get_event('event-3', 'event-3-message'),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
            },
        )
        self.mock_sleep.side_effect = [None, KeyboardInterrupt()]
        with self.stubber:
            log_events_iter = self.logs_generator.iter_log_events(
                self.group_name
            )
            actual_log_events = [event for event in log_events_iter]
        self.mock_sleep.assert_has_calls([mock.call(5), mock.call(5)])
        self.assertEqual(
            actual_log_events,
            [
                self.get_expected_event('event-1', 'event-1-message'),
                self.get_expected_event('event-2', 'event-2-message'),
                self.get_expected_event('event-3', 'event-3-message'),
            ],
        )

    def test_iter_log_events_filters_old_events(self):
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message'),
                    self.get_event('event-2', 'event-2-message'),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
            },
        )
        # Add a new page that has no nextToken
        # It should update startTime with the max timestamp
        # from the prvious response events
        self.stubber.add_response(
            'filter_log_events',
            service_response={
                'events': [
                    self.get_event('event-1', 'event-1-message'),
                    self.get_event('event-2', 'event-2-message'),
                    self.get_event('event-3', 'event-3-message'),
                ],
            },
            expected_params={
                'logGroupName': self.group_name,
                'interleaved': True,
                'startTime': self.get_event('event-2', 'event-2-message')[
                    'timestamp'
                ],
            },
        )
        self.mock_sleep.side_effect = [None, KeyboardInterrupt()]
        with self.stubber:
            log_events_iter = self.logs_generator.iter_log_events(
                self.group_name
            )
            actual_log_events = [event for event in log_events_iter]
        self.mock_sleep.assert_has_calls([mock.call(5), mock.call(5)])
        self.assertEqual(
            actual_log_events,
            [
                self.get_expected_event('event-1', 'event-1-message'),
                self.get_expected_event('event-2', 'event-2-message'),
                self.get_expected_event('event-3', 'event-3-message'),
            ],
        )
