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
from collections import defaultdict
from datetime import datetime, timedelta
import re
import time

from botocore.utils import parse_timestamp, datetime2timestamp
from dateutil import tz
import colorama

from awscli.compat import get_stdout_text_writer
from awscli.utils import is_a_tty
from awscli.customizations.commands import BasicCommand


class BaseLogEventsFormatter(object):
    _TIMESTAMP_COLOR = colorama.Fore.GREEN

    def __init__(self, output, colorize=True):
        self._output = output
        self._colorize = colorize
        if self._colorize:
            colorama.init(autoreset=True, strip=False)

    def display_log_event(self, log_event):
        raise NotImplementedError('display_log_event()')

    def _color_if_configured(self, text, color):
        if self._colorize:
            return color + text + colorama.Style.RESET_ALL
        return text

    def _write_log_event(self, log_event):
        log_event = self._ensure_single_newline_ending(log_event)
        self._output.write(log_event)

    def _ensure_single_newline_ending(self, log):
        return log.rstrip() + '\n'


class ShortLogEventsFormatter(BaseLogEventsFormatter):
    def display_log_event(self, log_event):
        log_event = '%s %s' % (
            self._format_timestamp(log_event['timestamp']),
            log_event['message']
        )
        self._write_log_event(log_event)

    def _format_timestamp(self, timestamp):
        return self._color_if_configured(
            timestamp.strftime("%Y-%m-%dT%H:%M:%S"), self._TIMESTAMP_COLOR)


class DetailedLogEventsFormatter(BaseLogEventsFormatter):
    _STREAM_NAME_COLOR = colorama.Fore.CYAN

    def display_log_event(self, log_event):
        log_event = '%s %s %s' % (
            self._format_timestamp(log_event['timestamp']),
            self._color_if_configured(
                log_event['logStreamName'], self._STREAM_NAME_COLOR),
            log_event['message']
        )
        self._write_log_event(log_event)

    def _format_timestamp(self, timestamp):
        return self._color_if_configured(
            timestamp.isoformat(), self._TIMESTAMP_COLOR)


class TailCommand(BasicCommand):
    NAME = 'tail'
    DESCRIPTION = (
        'Tails the logs for a CloudWatch Logs group. By default, the command '
        'returns logs from all associated CloudWatch Logs streams during the '
        'past ten minutes. Note that there is no guarantee for exact '
        'timestamp ordering of logs.'
    )
    ARG_TABLE = [
        {
            'name': 'group_name',
            'positional_arg': True,
            'help_text': 'The name of the CloudWatch Logs group.',
        },
        {
            'name': 'since',
            'default': '10m',
            'help_text': (
                'From what time to begin displaying logs. By default, logs '
                'will be displayed starting from ten minutes in the past. '
                'The value provided can be an ISO 8601 timestamp or a '
                'relative time. For relative times, provide a number and a '
                'single unit. Supported units include:\n\n'
                '<ul>'
                '<li> ``s`` - seconds </li>'
                '<li> ``m`` - minutes </li>'
                '<li> ``h`` - hours </li>'
                '<li> ``d`` - days </li>'
                '<li> ``w`` - weeks </li>'
                '</ul>'
                'For example, a value of ``5m`` would indicate to '
                'display logs starting five minutes in the past. '
                'Note that multiple units are **not** supported '
                '(i.e. ``5h30m``)'
            )
        },
        {
            'name': 'follow',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Whether to continuously poll for new logs. By default, the '
                'command will exit once there are no more logs to display. '
                'To exit from this mode, use Control-C.'
            )
        },
        {
            'name': 'format',
            'default': 'detailed',
            'choices': ['detailed', 'short'],
            'help_text': (
                'The format to display the logs. The following formats are '
                'supported:\n\n'
                '<ul>'
                '<li> detailed - This the default format. It prints out the '
                'timestamp with millisecond precision and timezones, the '
                'log stream name, and the log message.'
                '</li>'
                '<li> short - A shortened format. It prints out the '
                'a shortened timestamp and the log message.'
                '</li>'
                '</ul>'
            )
        },
        {
            'name': 'filter-pattern',
            'help_text': (
                'The filter pattern to use. See '
                '<a href="http://docs.aws.amazon.com/AmazonCloudWatch/'
                'latest/logs/FilterAndPatternSyntax.html">Filter and '
                'Pattern Syntax</a> for details. If not provided, all '
                'the events are matched'
            )
        },


    ]
    _FORMAT_TO_FORMATTER_CLS = {
        'detailed': DetailedLogEventsFormatter,
        'short': ShortLogEventsFormatter
    }

    def _run_main(self, parsed_args, parsed_globals):
        logs_client = self._session.create_client(
            'logs', region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        logs_generator = self._get_log_events_generator(
            logs_client, parsed_args.follow)
        log_events = logs_generator.iter_log_events(
            parsed_args.group_name, start=parsed_args.since,
            filter_pattern=parsed_args.filter_pattern)
        self._output_log_events(parsed_args, parsed_globals, log_events)
        return 0

    def _get_log_events_generator(self, logs_client, follow):
        timestamp_utils = TimestampUtils()
        if follow:
            return FollowLogEventsGenerator(logs_client, timestamp_utils)
        else:
            return NoFollowLogEventsGenerator(logs_client, timestamp_utils)

    def _output_log_events(self, parsed_args, parsed_globals, log_events):
        output = get_stdout_text_writer()
        logs_formatter = self._FORMAT_TO_FORMATTER_CLS[parsed_args.format](
            output, colorize=self._should_use_color(parsed_globals))
        for event in log_events:
            logs_formatter.display_log_event(event)

    def _should_use_color(self, parsed_globals):
        if parsed_globals.color == 'on':
            return True
        elif parsed_globals.color == 'off':
            return False
        return is_a_tty()


class TimestampUtils(object):
    _RELATIVE_TIMESTAMP_REGEX = re.compile(
        r"(?P<amount>\d+)(?P<unit>s|m|h|d|w)$"
    )
    _TO_SECONDS = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 24 * 3600,
        'w': 7 * 24 * 3600,
    }

    def __init__(self, now=None):
        self._now = now
        if now is None:
            self._now = datetime.utcnow

    def to_epoch_millis(self, timestamp):
        re_match = self._RELATIVE_TIMESTAMP_REGEX.match(timestamp)
        if re_match:
            datetime_value = self._relative_timestamp_to_datetime(
                int(re_match.group('amount')), re_match.group('unit')
            )
        else:
            datetime_value = parse_timestamp(timestamp)
        return int(datetime2timestamp(datetime_value) * 1000)

    def to_datetime(self, millis_timestamp):
        return datetime.fromtimestamp(millis_timestamp / 1000.0, tz.tzutc())

    def _relative_timestamp_to_datetime(self, amount, unit):
        multiplier = self._TO_SECONDS[unit]
        return self._now() + timedelta(seconds=amount * multiplier * -1)


class BaseLogEventsGenerator(object):
    def __init__(self, client, timestamp_utils):
        self._client = client
        self._timestamp_utils = timestamp_utils

    def iter_log_events(self, group_name, start=None, filter_pattern=None):
        filter_logs_events_kwargs = self._get_filter_logs_events_kwargs(
            group_name, start, filter_pattern)
        log_events = self._filter_log_events(filter_logs_events_kwargs)
        for log_event in log_events:
            self._convert_event_timestamps(log_event)
            yield log_event

    def _filter_log_events(self, filter_logs_events_kwargs):
        raise NotImplementedError('_filter_log_events()')

    def _get_filter_logs_events_kwargs(self, group_name, start,
                                       filter_pattern):
        kwargs = {
            'logGroupName': group_name,
            'interleaved': True
        }
        if start is not None:
            kwargs['startTime'] = self._timestamp_utils.to_epoch_millis(start)
        if filter_pattern is not None:
            kwargs['filterPattern'] = filter_pattern
        return kwargs

    def _convert_event_timestamps(self, event):
        event['ingestionTime'] = self._timestamp_utils.to_datetime(
            event['ingestionTime'])
        event['timestamp'] = self._timestamp_utils.to_datetime(
            event['timestamp'])


class NoFollowLogEventsGenerator(BaseLogEventsGenerator):
    def _filter_log_events(self, filter_logs_events_kwargs):
        paginator = self._client.get_paginator('filter_log_events')
        for page in paginator.paginate(**filter_logs_events_kwargs):
            for log_event in page['events']:
                yield log_event


class FollowLogEventsGenerator(BaseLogEventsGenerator):
    _TIME_TO_SLEEP = 5

    def __init__(self, client, timestamp_utils, sleep=None):
        super(FollowLogEventsGenerator, self).__init__(client, timestamp_utils)
        self._sleep = sleep
        if sleep is None:
            self._sleep = time.sleep

    def _filter_log_events(self, filter_logs_events_kwargs):
        try:
            for event in self._do_filter_log_events(filter_logs_events_kwargs):
                yield event
        except KeyboardInterrupt:
            # The only way to exit from the --follow is to Ctrl-C. So
            # we should exit the iterator rather than having the
            # KeyboardInterrupt propogate to the rest of the command.
            return

    def _get_latest_events_and_timestamp(self, event_ids_per_timestamp):
        if event_ids_per_timestamp:
            # Keep only ids of the events with the newest timestamp
            newest_timestamp = max(event_ids_per_timestamp.keys())
            event_ids_per_timestamp = defaultdict(
                set, {newest_timestamp: event_ids_per_timestamp[newest_timestamp]}
            )
        return event_ids_per_timestamp

    def _reset_filter_log_events_params(self, fle_kwargs, event_ids_per_timestamp):
        # Remove nextToken and update startTime for the next request
        # with the timestamp of the newest event
        if event_ids_per_timestamp:
            fle_kwargs['startTime'] = max(
                event_ids_per_timestamp.keys()
            )
        fle_kwargs.pop('nextToken', None)

    def _do_filter_log_events(self, filter_logs_events_kwargs):
        event_ids_per_timestamp = defaultdict(set)
        while True:
            response = self._client.filter_log_events(
                **filter_logs_events_kwargs)
            for event in response['events']:
                # For the case where we've hit the last page, we will be
                # reusing the newest timestamp of the received events to keep polling.
                # This means it is possible that duplicate log events with same timestamp
                # are returned back which we do not want to yield again.
                # We only want to yield log events that we have not seen.
                if event['eventId'] not in event_ids_per_timestamp[event['timestamp']]:
                    event_ids_per_timestamp[event['timestamp']].add(event['eventId'])
                    yield event
            event_ids_per_timestamp = self._get_latest_events_and_timestamp(
                event_ids_per_timestamp
            )
            if 'nextToken' in response:
                filter_logs_events_kwargs['nextToken'] = response['nextToken']
            else:
                self._reset_filter_log_events_params(
                    filter_logs_events_kwargs,
                    event_ids_per_timestamp
                )
                self._sleep(self._TIME_TO_SLEEP)
