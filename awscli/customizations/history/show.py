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
import contextlib
import datetime
import json
import os
import shlex
import subprocess
import sys
import xml.parsers.expat
import xml.dom.minidom

import colorama

from awscli.compat import six
from awscli.compat import get_binary_stdout
from awscli.compat import get_default_platform_pager
from awscli.utils import is_a_tty
from awscli.customizations.commands import BasicCommand
from awscli.customizations.history.db import HISTORY_LOCATION_ENV_VAR
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.customizations.history.db import DatabaseConnection


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
            getattr(self, '_display_' + event_record['event_type'].lower(),
                    self._display_noop)(event_record)

    def _should_display(self, event_record):
        if self._include:
            if event_record['event_type'] in self._include:
                return True
            else:
                return False
        elif self._exclude:
            if event_record['event_type'] in self._exclude:
                return False
            else:
                return True
        else:
            return True

    def _display_noop(self, event_record):
        pass


class DetailedFormatter(Formatter):
    _CLI_COMMAND_TITLE = 'AWS CLI command entered'
    _CLI_VERSION_DESC = 'with AWS CLI version'
    _CLI_ARGUMENTS_DESC = 'with arguments'

    _API_CALL_TITLE = 'API call made'
    _API_CALL_SERVICE_DESC = 'to service'
    _API_CALL_OPERATION_DESC = 'using operation'
    _API_CALL_PARAMS_DESC = 'with parameters'

    _HTTP_REQUEST_TITLE = 'HTTP request sent'
    _ENDPOINT_URL_DESC = 'to URL'
    _HTTP_METHOD_DESC = 'with method'
    _HTTP_HEADERS_DESC = 'with headers'
    _HTTP_BODY_DESC = 'with body'

    _HTTP_RESPONSE_TITLE = 'HTTP response received'
    _HTTP_STATUS_CODE_DESC = 'with status code'

    _PARSED_RESPONSE_TITLE = 'HTTP response parsed'
    _PARSED_RESPONSE_DESC = 'parsed to'

    _CLI_RC_TITLE = 'AWS CLI command exited'
    _CLI_RC_DESC = 'with return code'

    _TITLE_COLOR = colorama.Style.BRIGHT
    _DESCRIPTION_COLOR = colorama.Fore.CYAN
    _DESCRIPTION_VALUE_COLOR = colorama.Style.NORMAL

    def __init__(self, output=None, include=None, exclude=None, colorize=True):
        super(DetailedFormatter, self).__init__(output, include, exclude)
        self._request_id_to_api_num = {}
        self._num_api_calls = 0
        self._colorize = colorize
        if self._colorize:
            colorama.init(autoreset=True, strip=False)

    def _display_cli_version(self, event_record):
        self._write_formatted_title(self._CLI_COMMAND_TITLE, event_record)
        self._write_formatted_description_with_value(
            self._CLI_VERSION_DESC, event_record['payload']
        )

    def _display_cli_arguments(self, event_record):
        self._write_formatted_description_with_value(
            self._CLI_ARGUMENTS_DESC, event_record['payload']
        )

    def _display_api_call(self, event_record):
        self._write_formatted_title(self._API_CALL_TITLE, event_record)
        payload = event_record['payload']
        self._write_formatted_description_with_value(
            self._API_CALL_SERVICE_DESC, payload['service']
        )
        self._write_formatted_description_with_value(
            self._API_CALL_OPERATION_DESC, payload['operation']
        )
        self._write_formatted_description_with_value(
            self._API_CALL_PARAMS_DESC,
            self._format_dictionary(payload['params'])
        )

    def _display_http_request(self, event_record):
        self._write_formatted_title(self._HTTP_REQUEST_TITLE, event_record)
        payload = event_record['payload']
        self._write_formatted_description_with_value(
            self._ENDPOINT_URL_DESC, payload['url']
        )
        self._write_formatted_description_with_value(
            self._HTTP_METHOD_DESC, payload['method']
        )
        self._write_formatted_description_with_value(
            self._HTTP_HEADERS_DESC,
            self._format_dictionary(payload['headers'])
        )
        self._write_formatted_description_with_value(
            self._HTTP_BODY_DESC,
            self._format_body(payload['body'], payload.get('streaming', False))
        )

    def _display_http_response(self, event_record):
        self._write_formatted_title(self._HTTP_RESPONSE_TITLE, event_record)
        payload = event_record['payload']
        self._write_formatted_description_with_value(
            self._HTTP_STATUS_CODE_DESC,
            self._format_dictionary(payload['status_code'])
        )
        self._write_formatted_description_with_value(
            self._HTTP_HEADERS_DESC,
            self._format_dictionary(payload['headers'])
        )
        self._write_formatted_description_with_value(
            self._HTTP_BODY_DESC,
            self._format_body(payload['body'], payload.get('streaming', False))
        )

    def _display_parsed_response(self, event_record):
        self._write_formatted_title(self._PARSED_RESPONSE_TITLE, event_record)
        self._write_formatted_description_with_value(
            self._PARSED_RESPONSE_DESC,
            self._format_dictionary(event_record['payload'])
        )

    def _display_cli_rc(self, event_record):
        self._write_formatted_title(self._CLI_RC_TITLE, event_record)
        self._write_formatted_description_with_value(
            self._CLI_RC_DESC, event_record['payload']
        )

    def _write_formatted_title(self, title, event_record):
        self._write_output(self._format_section_title(title, event_record))

    def _write_formatted_description_with_value(self, desc, value):
        self._write_output(
            self._format_description_with_value(desc, value))

    def _write_output(self, content):
        if isinstance(content, six.text_type):
            content = content.encode('utf-8')
        self._output.write(content)

    def _format_section_title(self, title, event_record):
        formatted_title = ''
        api_num = self._get_api_num(event_record)
        if api_num is not None:
            formatted_title += '[%s] ' % api_num
        formatted_title += title + ' at: '
        formatted_title = self._color_title(formatted_title)

        formatted_timestamp = self._color_description_value(
            self._format_timestamp(event_record['timestamp']))

        return '\n' + formatted_title + formatted_timestamp + '\n'

    def _format_timestamp(self, event_timestamp):
        return datetime.datetime.fromtimestamp(
            event_timestamp/1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def _get_api_num(self, event_record):
        request_id = event_record['request_id']
        if request_id:
            if request_id not in self._request_id_to_api_num:
                self._request_id_to_api_num[
                    request_id] = self._num_api_calls
                self._num_api_calls += 1
            return self._request_id_to_api_num[request_id]

    def _format_description_with_value(self, desc, value,
                                       description_color=_DESCRIPTION_COLOR):
        formatted_str = self._color_description(desc + ': ', description_color)
        formatted_str += self._color_description_value(str(value))
        formatted_str += '\n'
        return formatted_str

    def _color_title(self, text):
        return self._color_if_configured(text, self._TITLE_COLOR)

    def _color_description(self, text, color=_DESCRIPTION_COLOR):
        return self._color_if_configured(text, color)

    def _color_description_value(self, text):
        return self._color_if_configured(text, self._DESCRIPTION_VALUE_COLOR)

    def _color_if_configured(self, text, color):
        if self._colorize:
            return color + text + colorama.Style.RESET_ALL
        return text

    def _format_dictionary(self, obj):
        return json.dumps(obj=obj, sort_keys=True, indent=4)

    def _format_body(self, body, is_streaming):
        if not body:
            return 'There is no associated body'
        elif is_streaming:
            return 'The body is a stream and will not be displayed'
        elif self._is_xml(body):
            return self._format_xml(body)
        elif self._is_json_structure(body):
            return self._format_json_structure_string(body)
        else:
            return body

    def _is_xml(self, body):
        try:
            xml.dom.minidom.parseString(body)
        except xml.parsers.expat.ExpatError:
            return False
        return True

    def _format_xml(self, body):
        stripped_body = self._strip_whitespace(body)
        xml_dom = xml.dom.minidom.parseString(stripped_body)
        return xml_dom.toprettyxml(indent=' '*4, newl='\n')

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

    def _format_json_structure_string(self, body):
        obj = json.loads(body)
        return self._format_dictionary(obj)


class OutputStreamFactory(object):
    def __init__(self, popen=None):
        self._popen = popen
        if popen is None:
            self._popen = subprocess.Popen

    def get_output_stream(self, stream_type):
        """Get an output stream to write to

        The value is wrapped in a context manager so make sure to use
        a with statement.

        :type stream_type: string
        :param stream_type: The name of the stream to get. Valid values
             consist of pager and stdout.
        """
        stream_getter = getattr(self, '_get_' + stream_type + '_stream', None)
        if stream_getter is None:
            raise ValueError(
                'Stream type of %s is not supported' % stream_type)
        return stream_getter()

    @contextlib.contextmanager
    def _get_pager_stream(self):
        pager_cmd = self._get_pager_cmd()
        process = self._popen(pager_cmd, stdin=subprocess.PIPE)
        yield process.stdin
        process.stdin.close()
        process.wait()

    @contextlib.contextmanager
    def _get_stdout_stream(self):
        yield get_binary_stdout()

    def _get_pager_cmd(self):
        pager = get_default_platform_pager()
        if 'PAGER' in os.environ:
            pager = os.environ['PAGER']
        return shlex.split(pager)


class ShowCommand(BasicCommand):
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
            'the specified CLI command.')}
    ]

    def __init__(self, session, db_reader=None, output_stream_factory=None):
        super(ShowCommand, self).__init__(session)
        self._db_reader = db_reader
        if db_reader is None:
            connection = DatabaseConnection(
                os.environ.get(HISTORY_LOCATION_ENV_VAR, None))
            self._db_reader = DatabaseRecordReader(connection)
        self._output_stream_factory = output_stream_factory
        if output_stream_factory is None:
            self._output_stream_factory = OutputStreamFactory()

    def _run_main(self, parsed_args, parsed_globals):
        self._validate_args(parsed_args)
        with self._get_output_stream() as output_stream:
            formatter = self._get_formatter(parsed_args, output_stream)
            for record in self._get_record_iterator(parsed_args):
                formatter.display(record)
        return 0

    def _validate_args(self, parsed_args):
        if parsed_args.exclude and parsed_args.include:
            raise ValueError(
                'Either --exclude or --include can be provided but not both')

    def _get_formatter(self, parsed_args, output_stream):
        format_type = parsed_args.format
        formatter_kwargs = {
            'include': parsed_args.include,
            'exclude': parsed_args.exclude,
            'output': output_stream
        }
        if format_type == 'detailed':
            formatter_kwargs['colorize'] = self._should_use_color()
        return self.FORMATTERS[format_type](**formatter_kwargs)

    def _should_use_color(self):
        return is_a_tty()

    def _get_output_stream(self):
        if is_a_tty():
            return self._output_stream_factory.get_output_stream('pager')
        return self._output_stream_factory.get_output_stream('stdout')

    def _get_record_iterator(self, parsed_args):
        if parsed_args.command_id == 'latest':
            return self._db_reader.iter_latest_records()
        else:
            return self._db_reader.iter_records(parsed_args.command_id)
