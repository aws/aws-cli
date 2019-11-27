# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import Namespace

from botocore.paginate import PageIterator

from awscli.testutils import unittest, mock
from awscli.compat import StringIO
from awscli.formatter import YAMLDumper, StreamedYAMLFormatter


class FakePageIterator(PageIterator):
    def __init__(self, responses):
        self._responses = responses

    def __iter__(self):
        for response in self._responses:
            yield response


class TestYAMLDumper(unittest.TestCase):
    def setUp(self):
        self.dumper = YAMLDumper()
        self.output = StringIO()

    def test_dump_int(self):
        self.dumper.dump(1, self.output)
        self.assertEqual(self.output.getvalue(), '1\n')

    def test_dump_float(self):
        self.dumper.dump(1.2, self.output)
        self.assertEqual(self.output.getvalue(), '1.2\n')

    def test_dump_bool(self):
        self.dumper.dump(True, self.output)
        self.assertEqual(self.output.getvalue(), 'true\n')

    def test_dump_str(self):
        self.dumper.dump('foo', self.output)
        self.assertEqual(self.output.getvalue(), '"foo"\n')

    def test_dump_structure(self):
        self.dumper.dump({'key': 'val'}, self.output)
        self.assertEqual(self.output.getvalue(), 'key: val\n')

    def test_dump_list(self):
        self.dumper.dump(['val1', 'val2'], self.output)
        self.assertEqual(self.output.getvalue(), '- val1\n- val2\n')


class TestStreamedYAMLFormatter(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(query=None)
        self.formatter = StreamedYAMLFormatter(self.args)
        self.output = StringIO()

    def test_format_single_response(self):
        response = {
            'TableNames': [
                'MyTable'
            ]
        }
        self.formatter('list-tables', response, self.output)
        self.assertEqual(
            self.output.getvalue(),
            '- TableNames:\n'
            '  - MyTable\n'
        )

    def test_format_paginated_response(self):
        response = FakePageIterator([
            {
                'TableNames': [
                    'MyTable'
                ]
            },
            {
                'TableNames': [
                    'MyTable2'
                ]
            },
        ])
        self.formatter('list-tables', response, self.output)
        self.assertEqual(
            self.output.getvalue(),
            '- TableNames:\n'
            '  - MyTable\n'
            '- TableNames:\n'
            '  - MyTable2\n'
        )

    def test_flushes_after_io_error(self):
        io_error_dumper = mock.Mock(YAMLDumper)
        mock_output = mock.Mock()
        io_error_dumper.dump.side_effect = IOError()
        response = {
            'TableNames': [
                'MyTable'
            ]
        }
        formatter = StreamedYAMLFormatter(self.args, io_error_dumper)
        formatter('list-tables', response, mock_output)
        self.assertTrue(mock_output.flush.called)

    def test_stops_paginating_after_io_error(self):
        io_error_dumper = mock.Mock(YAMLDumper)
        mock_output = mock.Mock()
        io_error_dumper.dump.side_effect = IOError()
        response = FakePageIterator([
            {
                'TableNames': [
                    'MyTable'
                ]
            },
            {
                'TableNames': [
                    'MyTable2'
                ]
            },
        ])
        formatter = StreamedYAMLFormatter(self.args, io_error_dumper)
        formatter('list-tables', response, mock_output)
        # The dumper should have only been called once as the io error is
        # immediately raised and we should not have kept paginating.
        self.assertTrue(len(io_error_dumper.dump.call_args_list), 1)
        self.assertTrue(mock_output.flush.called)
