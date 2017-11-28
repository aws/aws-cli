# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime

from awscli.compat import default_pager
from awscli.customizations.history.commands import HistorySubcommand


class ListCommand(HistorySubcommand):
    NAME = 'list'
    DESCRIPTION = (
        'Shows a list of previously run commands and their command_ids. '
        'Each row shows only a bare minimum of details including the '
        'command_id, date, arguments and return code. You can use the '
        '``history show`` with the command_id to see more details about '
        'a particular entry.'
    )
    _COL_WIDTHS = {
        'id_a': 38,
        'timestamp': 24,
        'args': 50,
        'rc': 0
    }

    def _run_main(self, parsed_args, parsed_globals):
        self._connect_to_history_db()
        try:
            raw_records = self._db_reader.iter_all_records()
            records = RecordAdapter(raw_records)
            if not records.has_next():
                raise RuntimeError(
                    'No commands were found in your history. Make sure you have '
                    'enabled history mode by adding "cli_history = enabled" '
                    'to the config file.')

            preferred_pager = self._get_preferred_pager()
            with self._get_output_stream(preferred_pager) as output_stream:
                formatter = TextFormatter(self._COL_WIDTHS, output_stream)
                formatter(records)
        finally:
            self._close_history_db()
        return 0

    def _get_preferred_pager(self):
        preferred_pager = default_pager
        if preferred_pager.startswith('less'):
            preferred_pager = 'less -SR'
        return preferred_pager


class RecordAdapter(object):
    """This class is just to read one ahead to make sure there are records

    If there are no records we can just exit early.
    """
    def __init__(self, records):
        self._records = records
        self._next = None
        self._advance()

    def has_next(self):
        return self._next is not None

    def _advance(self):
        try:
            self._next = next(self._records)
        except StopIteration:
            self._next = None

    def __iter__(self):
        while self.has_next():
            yield self._next
            self._advance()


class TextFormatter(object):
    def __init__(self, col_widths, output_stream):
        self._col_widths = col_widths
        self._output_stream = output_stream

    def _format_time(self, timestamp):
        command_time = datetime.datetime.fromtimestamp(timestamp / 1000)
        formatted = datetime.datetime.strftime(
            command_time, '%Y-%m-%d %I:%M:%S %p')
        return formatted

    def _format_args(self, args, arg_width):
        json_value = json.loads(args)
        formatted = ' '.join(json_value[:2])
        if len(formatted) >= arg_width:
            formatted = '%s...' % formatted[:arg_width-4]
        return formatted

    def _format_record(self, record):
        fmt_string = "{0:<%s}{1:<%s}{2:<%s}{3}\n" % (
            self._col_widths['id_a'],
            self._col_widths['timestamp'],
            self._col_widths['args']
        )
        record_line = fmt_string.format(
            record['id_a'],
            self._format_time(record['timestamp']),
            self._format_args(record['args'], self._col_widths['args']),
            record['rc']
        )
        return record_line

    def __call__(self, record_adapter):
        for record in record_adapter:
            formatted_record = self._format_record(record)
            self._output_stream.write(formatted_record.encode('utf-8'))
