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
import os
import argparse
import xml.dom.minidom

from botocore.session import Session

from awscli.compat import ensure_text_type
from awscli.compat import StringIO
from awscli.utils import OutputStreamFactory
from awscli.testutils import unittest, mock, FileCreator
from awscli.customizations.history.show import ShowCommand
from awscli.customizations.history.show import Formatter
from awscli.customizations.history.show import DetailedFormatter
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.customizations.exceptions import ParamValidationError


class FakeError(Exception):
    pass


class RecordingFormatter(Formatter):
    def __init__(self, output=None, include=None, exclude=None):
        super(RecordingFormatter, self).__init__(
            output=output, include=include, exclude=exclude)
        self.history = []

    def _display(self, event_record):
        self.history.append(event_record)


class TestFormatter(unittest.TestCase):
    def test_display_no_filters(self):
        formatter = RecordingFormatter()
        event_record = {'event_type': 'my_event'}
        other_event_record = {'event_type': 'my_other_event'}
        formatter.display(event_record)
        formatter.display(other_event_record)
        self.assertEqual(
            formatter.history,
            [
                event_record,
                other_event_record
            ]
        )

    def test_include_specified_event_type(self):
        formatter = RecordingFormatter(include=['my_event'])
        event_record = {'event_type': 'my_event'}
        formatter.display(event_record)
        self.assertEqual(formatter.history, [event_record])

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
            formatter.history, [other_event_record])

    def test_raises_error_when_both_include_and_exclude(self):
        with self.assertRaises(ParamValidationError):
            Formatter(include=['one_event'], exclude=['other_event'])


class TestDetailedFormatter(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.formatter = DetailedFormatter(self.output, colorize=False)

    def get_pretty_xml(self, xml_str):
        xml_dom = xml.dom.minidom.parseString(xml_str)
        return xml_dom.toprettyxml(indent=' '*4, newl='\n')

    def assert_output(self, for_event, contains):
        self.formatter.display(for_event)
        collected_output = ensure_text_type(self.output.getvalue())
        for line in contains:
            self.assertIn(line, collected_output)

    def test_display_cli_version(self):
        self.assert_output(
            for_event={
                'event_type': 'CLI_VERSION',
                'id': 'my-id',
                'payload': 'aws-cli/1.11.188',
                'timestamp': 86400000,
                'request_id': None
            },
            contains=[
                'AWS CLI command entered',
                'with AWS CLI version: aws-cli/1.11.188'
            ]
        )

    def test_can_use_color(self):
        self.formatter = DetailedFormatter(self.output, colorize=True)
        self.assert_output(
            for_event={
                'event_type': 'CLI_VERSION',
                'id': 'my-id',
                'payload': 'aws-cli/1.11.188',
                'timestamp': 86400000,
                'request_id': None
            },
            contains=[
                '\x1b[1mAWS CLI command entered',
                '\x1b[36mwith AWS CLI version:'
            ]
        )

    def test_display_cli_arguments(self):
        self.assert_output(
            for_event={
                'event_type': 'CLI_ARGUMENTS',
                'id': 'my-id',
                'payload': ['ec2', 'describe-regions'],
                'timestamp': 86400000,
                'request_id': None
            },
            contains=[
                 "with arguments: ['ec2', 'describe-regions']"
            ]
        )

    def test_display_api_call(self):
        self.assert_output(
            for_event={
                'event_type': 'API_CALL',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'service': 'ec2',
                    'operation': 'DescribeRegions',
                    'params': {}
                },
                'timestamp': 86400000,
            },
            contains=[
                'to service: ec2\n',
                'using operation: DescribeRegions\n',
                'with parameters: {}\n'
            ]
        )

    def test_two_different_api_calls_have_different_numbers(self):
        event = {
            'event_type': 'API_CALL',
            'id': 'my-id',
            'request_id': 'some-id',
            'payload': {
                'service': 'ec2',
                'operation': 'DescribeRegions',
                'params': {}
            },
            'timestamp': 86400000,
        }
        self.formatter.display(event)
        collected_output = ensure_text_type(self.output.getvalue())
        self.assertIn('[0] API call made', collected_output)

        other_event = {
            'event_type': 'API_CALL',
            'id': 'my-id',
            'request_id': 'other-id',
            'payload': {
                'service': 'ec2',
                'operation': 'DescribeRegions',
                'params': {}
            },
            'timestamp': 86400000,
        }
        self.formatter.display(other_event)
        new_output = ensure_text_type(self.output.getvalue())[
            len(collected_output):]
        self.assertIn('[1] API call made', new_output)

    def test_display_http_request(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': 'This is my body'
                },
                'timestamp': 86400000,
            },
            contains=[
                'to URL: https://myservice.us-west-2.amazonaws.com\n',
                'with method: GET\n',
                'with headers: {}\n',
                'with body: This is my body\n'
            ]
        )

    def test_display_http_request_filter_signature(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {
                        'Authorization': (
                            'Signature=d7fa4de082b598a0ac08b756db438c630a6'
                            'cc79c4f3d1636cf69fac0e7c1abcd'
                        )
                    },
                    'body': 'This is my body'
                },
                'timestamp': 86400000,
            },
            contains=[
                '"Authorization": "Signature=d7fa..."'
            ]
        )

    def test_display_http_request_with_streaming_body(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': 'This should not be printed out',
                    'streaming': True
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: The body is a stream and will not be displayed',
            ]
        )

    def test_display_http_request_with_no_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': None
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: There is no associated body'
            ]
        )

    def test_display_http_request_with_empty_string_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': ''
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: There is no associated body'
            ]
        )

    def test_display_http_request_with_xml_payload(self):
        xml_body = '<?xml version="1.0" ?><foo><bar>text</bar></foo>'
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': xml_body
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: ' + self.get_pretty_xml(xml_body)
            ]
        )

    def test_display_http_request_with_xml_payload_and_whitespace(self):
        xml_body = '<?xml version="1.0" ?><foo><bar>text</bar></foo>'
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': self.get_pretty_xml(xml_body)
                },
                'timestamp': 86400000,
            },
            # The XML should not be prettified more than once if the body
            # of the request was already prettied.
            contains=[
                'with body: ' + self.get_pretty_xml(xml_body)
            ]
        )

    def test_display_http_request_with_json_struct_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': '{"foo": "bar"}'
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: {\n'
                '    "foo": "bar"\n'
                '}'
            ]
        )

    def test_shares_api_number_across_events_of_same_api_call(self):
        self.assert_output(
            for_event={
                'event_type': 'API_CALL',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'service': 'ec2',
                    'operation': 'DescribeRegions',
                    'params': {}
                },
                'timestamp': 86400000,
            },
            contains=[
                '[0] API call made'
            ]
        )
        self.assert_output(
            for_event={
                'event_type': 'HTTP_REQUEST',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'method': 'GET',
                    'url': 'https://myservice.us-west-2.amazonaws.com',
                    'headers': {},
                    'body': 'This is my body'
                },
                'timestamp': 86400000,
            },
            contains=[
                '[0] HTTP request sent'
            ]
        )

    def test_display_http_response(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': 'This is my body'
                },
                'timestamp': 86400000,
            },
            contains=[
                '[0] HTTP response received',
                'with status code: 200\n',
                'with headers: {}\n',
                'with body: This is my body\n'

            ]
        )

    def test_display_http_response_with_streaming_body(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': 'This should not be printed out',
                    'streaming': True
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: The body is a stream and will not be displayed'
            ]
        )

    def test_display_http_response_with_no_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': None
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: There is no associated body'
            ]
        )

    def test_display_http_response_with_empty_string_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': ''
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: There is no associated body'
            ]
        )

    def test_display_http_response_with_xml_payload(self):
        xml_body = '<?xml version="1.0" ?><foo><bar>text</bar></foo>'
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': xml_body
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: ' + self.get_pretty_xml(xml_body)
            ]
        )

    def test_display_http_response_with_xml_payload_and_whitespace(self):
        xml_body = '<?xml version="1.0" ?><foo><bar>text</bar></foo>'
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': self.get_pretty_xml(xml_body)
                },
                'timestamp': 86400000,
            },
            # The XML should not be prettified more than once if the body
            # of the response was already prettied.
            contains=[
                'with body: ' + self.get_pretty_xml(xml_body)
            ]
        )

    def test_display_http_response_with_json_struct_payload(self):
        self.assert_output(
            for_event={
                'event_type': 'HTTP_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {
                    'status_code': 200,
                    'headers': {},
                    'body': '{"foo": "bar"}'
                },
                'timestamp': 86400000,
            },
            contains=[
                'with body: {\n',
                '    "foo": "bar"\n',
                '}',
            ]
        )

    def test_display_parsed_response(self):
        self.assert_output(
            for_event={
                'event_type': 'PARSED_RESPONSE',
                'id': 'my-id',
                'request_id': 'some-id',
                'payload': {},
                'timestamp': 86400000,
            },
            contains=[
                '[0] HTTP response parsed',
                'parsed to: {}'
            ]
        )

    def test_display_cli_rc(self):
        self.assert_output(
            for_event={
                'event_type': 'CLI_RC',
                'id': 'my-id',
                'payload': 0,
                'timestamp': 86400000,
                'request_id': None
            },
            contains=[
                'AWS CLI command exited',
                'with return code: 0'
            ]
        )

    def test_display_unknown_type(self):
        event = {
            'event_type': 'UNKNOWN',
            'id': 'my-id',
            'payload': 'foo',
            'timestamp': 86400000,
            'request_id': None
        }
        self.formatter.display(event)
        collected_output = ensure_text_type(self.output.getvalue())
        self.assertEqual('', collected_output)


class TestShowCommand(unittest.TestCase):
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
        self.db_reader.iter_latest_records.return_value = []
        self.db_reader.iter_records.return_value = []

        self.show_cmd = ShowCommand(
            self.session, self.db_reader, self.output_stream_factory)

        self.formatter = mock.Mock(Formatter)
        self.add_formatter('mock', self.formatter)

        self.parsed_args = argparse.Namespace()
        self.parsed_args.format = 'mock'
        self.parsed_args.include = None
        self.parsed_args.exclude = None

        self.parsed_globals = argparse.Namespace()
        self.parsed_globals.color = 'auto'

        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def test_does_close_connection(self):
        self.parsed_args.command_id = 'latest'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.db_reader.close.called)

    def test_does_close_connection_with_error(self):
        self.parsed_args.command_id = 'latest'
        self.db_reader.iter_latest_records.side_effect = FakeError('ERROR')
        with self.assertRaises(FakeError):
            self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.db_reader.close.called)

    def test_detects_if_history_exists(self):
        self.show_cmd = ShowCommand(self.session)
        self.parsed_args.command_id = 'latest'

        db_filename = os.path.join(self.files.rootdir, 'name.db')
        with mock.patch('os.environ', {'AWS_CLI_HISTORY_FILE': db_filename}):
            with self.assertRaisesRegexp(
                    RuntimeError, 'Could not locate history'):
                self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

    def add_formatter(self, formatter_name, formatter):
        # We do not want to be adding to the dictionary directly because
        # the dictionary is scoped to the class as well so even a formatter
        # to an instance of the class will add it to the class as well.
        formatters = self.show_cmd.FORMATTERS.copy()
        formatters[formatter_name] = formatter
        self.show_cmd.FORMATTERS = formatters

    def test_show_latest(self):
        self.parsed_args.command_id = 'latest'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertTrue(self.db_reader.iter_latest_records.called)

    def test_show_specific_id(self):
        self.parsed_args.command_id = 'some-specific-id'
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.db_reader.iter_records.call_args,
            mock.call('some-specific-id')
        )

    def test_uses_format(self):
        formatter = mock.Mock(Formatter)
        self.add_formatter('myformatter', formatter)

        return_record = {'id': 'myid', 'event_type': 'CLI_RC', 'payload': 0}
        self.db_reader.iter_latest_records.return_value = [return_record]

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
            mock.call(
                include=['API_CALL'], exclude=None,
                output=self.output_stream)
        )

    def test_uses_exclude(self):
        self.parsed_args.command_id = 'latest'
        self.parsed_args.include = None
        self.parsed_args.exclude = ['CLI_RC']
        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=['CLI_RC'],
                output=self.output_stream)
        )

    def test_raises_error_when_both_include_and_exclude(self):
        self.parsed_args.include = ['API_CALL']
        self.parsed_args.exclude = ['CLI_RC']
        with self.assertRaises(ParamValidationError):
            self.show_cmd._run_main(self.parsed_args, self.parsed_globals)

    @mock.patch('awscli.customizations.history.commands.is_windows', False)
    @mock.patch('awscli.customizations.history.commands.is_a_tty')
    def test_detailed_formatter_is_a_tty(self, mock_is_a_tty):
        mock_is_a_tty.return_value = True
        self.formatter = mock.Mock(DetailedFormatter)
        self.add_formatter('detailed', self.formatter)
        self.parsed_args.format = 'detailed'
        self.parsed_args.command_id = 'latest'

        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=None,
                output=self.output_stream, colorize=True
            )
        )

    @mock.patch('awscli.customizations.history.commands.is_windows', False)
    @mock.patch('awscli.customizations.history.commands.is_a_tty')
    def test_detailed_formatter_not_a_tty(self, mock_is_a_tty):
        mock_is_a_tty.return_value = False
        self.formatter = mock.Mock(DetailedFormatter)
        self.add_formatter('detailed', self.formatter)
        self.parsed_args.format = 'detailed'
        self.parsed_args.command_id = 'latest'

        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=None,
                output=self.output_stream, colorize=False
            )
        )

    @mock.patch('awscli.customizations.history.commands.is_windows', True)
    def test_detailed_formatter_no_color_for_windows(self):
        self.formatter = mock.Mock(DetailedFormatter)
        self.add_formatter('detailed', self.formatter)
        self.parsed_args.format = 'detailed'
        self.parsed_args.command_id = 'latest'

        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=None,
                output=self.output_stream, colorize=False
            )
        )

    @mock.patch('awscli.customizations.history.commands.is_windows', True)
    @mock.patch('awscli.customizations.history.commands.is_a_tty')
    def test_force_color(self, mock_is_a_tty):
        self.formatter = mock.Mock(DetailedFormatter)
        self.add_formatter('detailed', self.formatter)
        self.parsed_args.format = 'detailed'
        self.parsed_args.command_id = 'latest'

        self.parsed_globals.color = 'on'
        # Even with settings that would typically turn off color, it
        # should be turned on because it was explicitly turned on
        mock_is_a_tty.return_value = False

        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=None,
                output=self.output_stream, colorize=True
            )
        )

    @mock.patch('awscli.customizations.history.commands.is_windows', False)
    @mock.patch('awscli.customizations.history.commands.is_a_tty')
    def test_disable_color(self, mock_is_a_tty):
        self.formatter = mock.Mock(DetailedFormatter)
        self.add_formatter('detailed', self.formatter)
        self.parsed_args.format = 'detailed'
        self.parsed_args.command_id = 'latest'

        self.parsed_globals.color = 'off'
        # Even with settings that would typically enable color, it
        # should be turned off because it was explicitly turned off
        mock_is_a_tty.return_value = True

        self.show_cmd._run_main(self.parsed_args, self.parsed_globals)
        self.assertEqual(
            self.formatter.call_args,
            mock.call(
                include=None, exclude=None,
                output=self.output_stream, colorize=False
            )
        )
