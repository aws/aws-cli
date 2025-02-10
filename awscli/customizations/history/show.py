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
import datetime
import json
import sys
import xml.parsers.expat
import xml.dom.minidom

import colorama

from awscli.table import COLORAMA_KWARGS
from awscli.customizations.history.commands import HistorySubcommand
from awscli.customizations.history.filters import RegexFilter


class Formatter(object):
    def __init__(self, output=None, include=None, exclude=None):
        """Formats and outputs CLI history events

        :type output: File-like obj
        :param output: The stream to write the formatted event to. By default
            sys.stdout is used.

        :type include: list
        :param include: A filter specifying which event to only be displayed.
            This parameter is mutually exclusive with exclude.

        :type exclude: list
        :param exclude: A filter specifying which events to exclude from being
            displayed. This parameter is mutually exclusive with include.

        """
        self._output = output
        if self._output is None:
            self._output = sys.stdout
        if include and exclude:
            raise ValueError(
                'Either input or exclude can be provided but not both')
        self._include = include
        self._exclude = exclude

    def display(self, event_record):
        """Displays a formatted version of the event record

        :type event_record: dict
        :param event_record: The event record to format and display.
        """
        if self._should_display(event_record):
            self._display(event_record)

    def _display(self, event_record):
        raise NotImplementedError('_display()')

    def _should_display(self, event_record):
        if self._include:
            return event_record['event_type'] in self._include
        elif self._exclude:
            return event_record['event_type'] not in self._exclude
        else:
            return True


class DetailedFormatter(Formatter):
    _SIG_FILTER = RegexFilter(
        'Signature=([a-z0-9]{4})[a-z0-9]{60}',
        r'Signature=\1...',
    )

    _SECTIONS = {
        'CLI_VERSION': {
            'title': 'AWS CLI command entered',
            'values': [
                {'description': 'with AWS CLI version'}
            ]
        },
        'CLI_ARGUMENTS': {
            'values': [
                {'description': 'with arguments'}
            ]
        },
        'API_CALL': {
            'title': 'API call made',
            'values': [
                {
                    'description': 'to service',
                    'payload_key': 'service'
                },
                {
                    'description': 'using operation',
                    'payload_key': 'operation'
                },
                {
                    'description': 'with parameters',
                    'payload_key': 'params',
                    'value_format': 'dictionary'
                }
            ]
        },
        'HTTP_REQUEST': {
            'title': 'HTTP request sent',
            'values': [
                {
                    'description': 'to URL',
                    'payload_key': 'url'
                },
                {
                    'description': 'with method',
                    'payload_key': 'method'
                },
                {
                    'description': 'with headers',
                    'payload_key': 'headers',
                    'value_format': 'dictionary',
                    'filters': [_SIG_FILTER]
                },
                {
                    'description': 'with body',
                    'payload_key': 'body',
                    'value_format': 'http_body'
                }

            ]
        },
        'HTTP_RESPONSE': {
            'title': 'HTTP response received',
            'values': [
                {
                    'description': 'with status code',
                    'payload_key': 'status_code'
                },
                {
                    'description': 'with headers',
                    'payload_key': 'headers',
                    'value_format': 'dictionary'
                },
                {
                    'description': 'with body',
                    'payload_key': 'body',
                    'value_format': 'http_body'
                }
            ]
        },
        'PARSED_RESPONSE': {
            'title': 'HTTP response parsed',
            'values': [
                {
                    'description': 'parsed to',
                    'value_format': 'dictionary'
                }
            ]
        },
        'CLI_RC': {
            'title': 'AWS CLI command exited',
            'values': [
                {'description': 'with return code'}
            ]
        },
    }

    _COMPONENT_COLORS = {
        'title': colorama.Style.BRIGHT,
        'description': colorama.Fore.CYAN
    }

    def __init__(self, output=None, include=None, exclude=None, colorize=True):
        super(DetailedFormatter, self).__init__(output, include, exclude)
        self._request_id_to_api_num = {}
        self._num_api_calls = 0
        self._colorize = colorize
        self._value_pformatter = SectionValuePrettyFormatter()
        if self._colorize:
            colorama.init(**COLORAMA_KWARGS)

    def _display(self, event_record):
        section_definition = self._SECTIONS.get(event_record['event_type'])
        if section_definition is not None:
            self._display_section(event_record, section_definition)

    def _display_section(self, event_record, section_definition):
        if 'title' in section_definition:
            self._display_title(section_definition['title'], event_record)
        for value_definition in section_definition['values']:
            self._display_value(value_definition, event_record)

    def _display_title(self, title, event_record):
        formatted_title = self._format_section_title(title, event_record)
        self._write_output(formatted_title)

    def _display_value(self, value_definition, event_record):
        value_description = value_definition['description']
        event_record_payload = event_record['payload']
        value = event_record_payload
        if 'payload_key' in value_definition:
            value = event_record_payload[value_definition['payload_key']]
        formatted_value = self._format_description(value_description)
        formatted_value += self._format_value(
            value, event_record, value_definition.get('value_format')
        )
        if 'filters' in value_definition:
            for text_filter in value_definition['filters']:
                formatted_value = text_filter.filter_text(formatted_value)
        self._write_output(formatted_value)

    def _write_output(self, content):
        if isinstance(content, str):
            content = content.encode('utf-8')
        self._output.write(content)

    def _format_section_title(self, title, event_record):
        formatted_title = title
        api_num = self._get_api_num(event_record)
        if api_num is not None:
            formatted_title = ('[%s] ' % api_num) + formatted_title
        formatted_title = self._color_if_configured(formatted_title, 'title')
        formatted_title += '\n'

        formatted_timestamp = self._format_description('at time')
        formatted_timestamp += self._format_value(
            event_record['timestamp'], event_record, value_format='timestamp')

        return '\n' + formatted_title + formatted_timestamp

    def _get_api_num(self, event_record):
        request_id = event_record['request_id']
        if request_id:
            if request_id not in self._request_id_to_api_num:
                self._request_id_to_api_num[
                    request_id] = self._num_api_calls
                self._num_api_calls += 1
            return self._request_id_to_api_num[request_id]

    def _format_description(self, value_description):
        return self._color_if_configured(
            value_description + ': ', 'description')

    def _format_value(self, value, event_record, value_format=None):
        if value_format:
            formatted_value = self._value_pformatter.pformat(
                value, value_format, event_record)
        else:
            formatted_value = str(value)
        return formatted_value + '\n'

    def _color_if_configured(self, text, component):
        if self._colorize:
            color = self._COMPONENT_COLORS[component]
            return color + text + colorama.Style.RESET_ALL
        return text


class SectionValuePrettyFormatter(object):
    def pformat(self, value, value_format, event_record):
        return getattr(self, '_pformat_' + value_format)(value, event_record)

    def _pformat_timestamp(self, event_timestamp, event_record=None):
        return datetime.datetime.fromtimestamp(
            event_timestamp/1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def _pformat_dictionary(self, obj, event_record=None):
        return json.dumps(obj=obj, sort_keys=True, indent=4)

    def _pformat_http_body(self, body, event_record):
        if not body:
            return 'There is no associated body'
        elif event_record['payload'].get('streaming', False):
            return 'The body is a stream and will not be displayed'
        elif self._is_xml(body):
            # TODO: Figure out a way to minimize the number of times we have
            # to parse the XML. Currently at worst, it will take three times.
            # One to determine if it is XML, another to strip whitespace, and
            # a third to convert to make it pretty. This is an issue as it
            # can cause issues when there are large XML payloads such as
            # an s3 ListObjects call.
            return self._get_pretty_xml(body)
        elif self._is_json_structure(body):
            return self._get_pretty_json(body)
        else:
            return body

    def _get_pretty_xml(self, body):
        # The body is parsed and whitespace is stripped because some services
        # like ec2 already return pretty XML and if toprettyxml() was applied
        # to it, it will add even more newlines and spaces on top of it.
        # So this just removes all whitespace from the start to prevent the
        # chance of adding to much newlines and spaces when toprettyxml()
        # is called.
        stripped_body = self._strip_whitespace(body)
        xml_dom = xml.dom.minidom.parseString(stripped_body)
        return xml_dom.toprettyxml(indent=' '*4, newl='\n')

    def _get_pretty_json(self, body):
        # The json body is loaded so it can be dumped in a format that
        # is desired.
        obj = json.loads(body)
        return self._pformat_dictionary(obj)

    def _is_xml(self, body):
        try:
            xml.dom.minidom.parseString(body)
        except xml.parsers.expat.ExpatError:
            return False
        return True

    def _strip_whitespace(self, xml_string):
        xml_dom = xml.dom.minidom.parseString(xml_string)
        return ''.join(
            [line.strip() for line in xml_dom.toxml().splitlines()]
        )

    def _is_json_structure(self, body):
        if body.startswith('{'):
            try:
                json.loads(body)
                return True
            except json.decoder.JSONDecodeError:
                return False
        return False


class ShowCommand(HistorySubcommand):
    NAME = 'show'
    DESCRIPTION = (
        'Shows the various events related to running a specific CLI command. '
        'If this command is ran without any positional arguments, it will '
        'display the events for the last CLI command ran.'
    )
    FORMATTERS = {
        'detailed': DetailedFormatter
    }
    ARG_TABLE = [
        {'name': 'command_id', 'nargs': '?', 'default': 'latest',
         'positional_arg': True,
         'help_text': (
             'The ID of the CLI command to show. If this positional argument '
             'is omitted, it will show the last the CLI command ran.')},
        {'name': 'include', 'nargs': '+',
         'help_text': (
             'Specifies which events to **only** include when showing the '
             'CLI command. This argument is mutually exclusive with '
             '``--exclude``.')},
        {'name': 'exclude', 'nargs': '+',
         'help_text': (
             'Specifies which events to exclude when showing the '
             'CLI command. This argument is mutually exclusive with '
             '``--include``.')},
        {'name': 'format', 'choices': FORMATTERS.keys(),
         'default': 'detailed', 'help_text': (
            'Specifies which format to use in showing the events for '
            'the specified CLI command. The following formats are '
            'supported:\n\n'
            '<ul>'
            '<li> detailed - This the default format. It prints out a '
            'detailed overview of the CLI command ran. It displays all '
            'of the key events in the command lifecycle where each '
            'important event has a title and its important values '
            'underneath. The events are ordered by timestamp and events of '
            'the same API call are associated together with the '
            '[``api_id``] notation where events that share the same '
            '``api_id`` belong to the lifecycle of the same API call.'
            '</li>'
            '</ul>'
            )
         }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        self._connect_to_history_db()
        try:
            self._validate_args(parsed_args)
            with self._get_output_stream() as output_stream:
                formatter = self._get_formatter(
                    parsed_args, parsed_globals, output_stream)
                for record in self._get_record_iterator(parsed_args):
                    formatter.display(record)
        finally:
            self._close_history_db()
        return 0

    def _validate_args(self, parsed_args):
        if parsed_args.exclude and parsed_args.include:
            raise ValueError(
                'Either --exclude or --include can be provided but not both')

    def _get_formatter(self, parsed_args, parsed_globals, output_stream):
        format_type = parsed_args.format
        formatter_kwargs = {
            'include': parsed_args.include,
            'exclude': parsed_args.exclude,
            'output': output_stream
        }
        if format_type == 'detailed':
            formatter_kwargs['colorize'] = self._should_use_color(
                parsed_globals)
        return self.FORMATTERS[format_type](**formatter_kwargs)

    def _get_record_iterator(self, parsed_args):
        if parsed_args.command_id == 'latest':
            return self._db_reader.iter_latest_records()
        else:
            return self._db_reader.iter_records(parsed_args.command_id)
