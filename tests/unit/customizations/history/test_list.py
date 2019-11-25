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
import argparse
import datetime

from botocore.session import Session

from awscli.compat import StringIO
from awscli.compat import ensure_text_type
from awscli.utils import OutputStreamFactory
from awscli.testutils import unittest, mock
from awscli.customizations.history.list import ListCommand
from awscli.customizations.history.list import RecordAdapter
from awscli.customizations.history.list import TextFormatter
from awscli.customizations.history.db import DatabaseRecordReader


class TestRecordAdapter(unittest.TestCase):
    def test_no_records_no_next(self):
        source = iter([])
        adapter = RecordAdapter(source)
        self.assertFalse(adapter.has_next())

    def test_one_record_has_next(self):
        source = iter([1])
        adapter = RecordAdapter(source)
        self.assertTrue(adapter.has_next())

    def test_can_iterate(self):
        source = iter([1, 2, 3])
        adapter = RecordAdapter(source)
        result = [r for r in adapter]
        self.assertEqual(result, [1, 2, 3])


class TestTextFormatter(unittest.TestCase):
    _COL_WIDTHS = {
        'id_a': 10,
        'timestamp': 23,
        'args': 10,
        'rc': 10
    }

    def setUp(self):
        self.output_stream = StringIO()
        self.formatter = TextFormatter(self._COL_WIDTHS, self.output_stream)

        self.timestamp = 1511376242067
        command_time = datetime.datetime.fromtimestamp(self.timestamp / 1000)
        self.formatted_time = datetime.datetime.strftime(
            command_time, '%Y-%m-%d %I:%M:%S %p')

    def _format_records(self, records):
        adapter = RecordAdapter(iter(records))
        self.formatter(adapter)

    def test_can_emit_single_row(self):
        self._format_records([
            {
                'id_a': 'foo',
                'timestamp': self.timestamp,
                'args': '["s3", "ls"]',
                'rc': 0
            }
        ])
        expected_output = 'foo       %s s3 ls     0\n' % self.formatted_time
        actual_output = ensure_text_type(self.output_stream.getvalue())
        self.assertEqual(expected_output, actual_output)

    def test_can_emit_multiple_rows(self):
        self._format_records([
            {
                'id_a': 'foo',
                'timestamp': self.timestamp,
                'args': '["s3", "ls"]',
                'rc': 0
            },
            {
                'id_a': 'bar',
                'timestamp': self.timestamp,
                'args': '["s3", "cp"]',
                'rc': 1
            }
        ])
        expected_output = ('foo       %s s3 ls     0\n'
                           'bar       %s s3 cp     1\n') % (
                               self.formatted_time, self.formatted_time)
        actual_output = ensure_text_type(self.output_stream.getvalue())
        self.assertEqual(expected_output, actual_output)

    def test_can_truncate_args(self):
        # Truncate the argument if it won't fit in the space alotted to the
        # arguments field.
        self._format_records([
            {
                'id_a': 'foo',
                'timestamp': self.timestamp,
                'args': ('["s3", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                         'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]'),
                'rc': 0
            }
        ])
        expected_output = 'foo       %s s3 aaa... 0\n' % self.formatted_time
        actual_output = ensure_text_type(self.output_stream.getvalue())
        self.assertEqual(expected_output, actual_output)


class TestListCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)

        self.output_stream_factory = mock.Mock(OutputStreamFactory)

        # MagicMock is needed because it can handle context managers.
        # Normal Mock will throw AttributeErrors
        output_stream_context = mock.MagicMock()
        self.output_stream = mock.Mock()
        output_stream_context.__enter__.return_value = self.output_stream

        self.output_stream_factory.get_output_stream.return_value = \
            output_stream_context

        self.db_reader = mock.Mock(DatabaseRecordReader)
        self.db_reader.iter_all_records.return_value = iter([])

        self.list_cmd = ListCommand(
            self.session, self.db_reader, self.output_stream_factory)

        self.parsed_args = argparse.Namespace()

        self.parsed_globals = argparse.Namespace()
        self.parsed_globals.color = 'auto'

    def _make_record(self, cid, time, args, rc):
        record = {
            'id_a': cid,
            'timestamp': time,
            'args': args,
            'rc': rc
        }
        return record

    def test_does_call_iter_all_records(self):
        with self.assertRaises(RuntimeError):
            self.list_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.db_reader.iter_all_records.called)

    def test_list_does_write_values_to_stream(self):
        self.db_reader.iter_all_records.return_value = iter([
            self._make_record('abc', 1511376242067, '["s3", "ls"]', '0')
        ])
        self.list_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.output_stream.write.called)

    @mock.patch('awscli.customizations.history.list.OutputStreamFactory')
    def test_uses_sr_less_flags(self, mock_factory):
        ListCommand(self.session)
        mock_factory.assert_called_with(self.session, default_less_flags='SR')
