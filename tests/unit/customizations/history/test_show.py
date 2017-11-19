# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import argparse

from botocore.session import Session

from awscli.testutils import unittest, mock
from awscli.customizations.history.show import ShowCommand
from awscli.customizations.history.show import Formatter
from awscli.customizations.history.db import DatabaseRecordReader


class RecordingFormatter(Formatter):
    def __init__(self, output=None, include=None, exclude=None):
        super(RecordingFormatter, self).__init__(
            output=output, include=include, exclude=exclude)
        self.history = []

    def _display_my_event(self, event_record):
        self.history.append(('my_event', event_record))

    def _display_my_other_event(self, event_record):
        self.history.append(('my_other_event', event_record))


class TestFormatter(unittest.TestCase):
    def test_display_known_event_type(self):
        formatter = RecordingFormatter()
        event_record = {'event_type': 'my_event'}
        other_event_record = {'event_type': 'my_other_event'}
        formatter.display(event_record)
        formatter.display(other_event_record)
        self.assertEqual(
            formatter.history,
            [
                ('my_event', event_record),
                ('my_other_event', other_event_record)
            ]
        )

    def test_display_known_event_type_case_insensitive(self):
        formatter = RecordingFormatter()
        event_record = {'event_type': 'MY_EVENT'}
        formatter.display(event_record)
        self.assertEqual(formatter.history, [('my_event', event_record)])

    def test_display_unknown_event_type(self):
        formatter = RecordingFormatter()
        event_record = {'event_type': 'unknown'}
        formatter.display(event_record)
        self.assertEqual(formatter.history, [])

    def test_include_specified_event_type(self):
        formatter = RecordingFormatter(include=['my_event'])
        event_record = {'event_type': 'my_event'}
        formatter.display(event_record)
        self.assertEqual(formatter.history, [('my_event', event_record)])

    def test_include_on_unspecified_event_type(self):
        formatter = RecordingFormatter(include=['my_event'])
        other_event_record = {'event_type': 'my_other_event'}
        formatter.display(other_event_record)
        self.assertEqual(formatter.history, [])

    def test_exclude_on_specified_event_type(self):
        formatter = RecordingFormatter(exclude=['my_event'])
        event_record = {'event_type': 'my_event'}
        formatter.display(event_record)
        self.assertEqual(formatter.history, [])

    def test_exclude_on_unspecified_event_type(self):
        formatter = RecordingFormatter(exclude=['my_event'])
        other_event_record = {'event_type': 'my_other_event'}
        formatter.display(other_event_record)
        self.assertEqual(
            formatter.history, [('my_other_event', other_event_record)])

    def test_raises_error_when_both_include_and_exclude(self):
        with self.assertRaises(ValueError):
            Formatter(include=['one_event'], exclude=['other_event'])


class DetailedFormatter(unittest.TestCase):
    def test_display_cli_version(self):
        pass

    def test_display_cli_arguments(self):
        pass

    def test_display_api_call(self):
        pass

    def test_display_http_request(self):
        pass

    def test_display_http_response(self):
        pass

    def test_display_parsed_response(self):
        pass

    def test_display_cli_rc(self):
        pass


class TestShowCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)

        self.db_reader = mock.Mock(DatabaseRecordReader)
        self.db_reader.yield_latest_records.return_value = []
        self.db_reader.yield_records.return_value = []

        self.show_cmd = ShowCommand(self.session, self.db_reader)

        self.formatter = mock.Mock(Formatter)
        self.show_cmd.FORMATTERS['mock'] = self.formatter

        self.parsed_args = argparse.Namespace()
        self.parsed_globals = argparse.Namespace()
        self.parsed_args.format = 'mock'
        self.parsed_args.include = None
        self.parsed_args.exclude = None

    def test_show_latest(self):
        self.parsed_args.command_id = 'latest'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.db_reader.yield_latest_records.called)

    def test_show_specific_id(self):
        self.parsed_args.command_id = 'some-specific-id'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.db_reader.yield_records.call_args,
            mock.call('some-specific-id')
        )

    def test_uses_view(self):
        formatter = mock.Mock(Formatter)
        self.show_cmd.FORMATTERS['myformatter'] = formatter

        return_record = {'id': 'myid', 'event_type': 'CLI_RC', 'payload': 0}
        self.db_reader.yield_latest_records.return_value = [return_record]

        self.parsed_args.format = 'myformatter'
        self.parsed_args.command_id = 'latest'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

        self.assertTrue(formatter.called)
        self.assertEqual(
            formatter.return_value.display.call_args_list,
            [mock.call(return_record)]
        )

    def test_uses_include(self):
        self.parsed_args.command_id = 'latest'
        self.parsed_args.include = ['API_CALL']
        self.parsed_args.exclude = None
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

        self.assertEqual(
            self.formatter.call_args,
            mock.call(include=['API_CALL'], exclude=None)
        )

    def test_uses_exclude(self):
        self.parsed_args.command_id = 'latest'
        self.parsed_args.include = None
        self.parsed_args.exclude = ['CLI_RC']
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

        self.assertEqual(
            self.formatter.call_args,
            mock.call(include=None, exclude=['CLI_RC'])
        )

    def test_raises_error_when_both_include_and_exclude(self):
        self.parsed_args.include = ['API_CALL']
        self.parsed_args.exclude = ['CLI_RC']
        with self.assertRaises(ValueError):
            self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
