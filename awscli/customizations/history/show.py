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
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.history.db import DatabaseRecordReader


class Formatter(object):
    def __init__(self, output=None, include=None, exclude=None):
        self._output = output
        if self._output is None:
            self._output = sys.stdout
        if include and exclude:
            raise ValueError(
                'Either input or exclude can be provided but not both')
        self._include = include
        self._exclude = exclude

    def display(self, event_record):
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
    _CLI_VERSION_FORMAT = (
        'The version of the AWS CLI was: {version}\n\n'
    )

    _CLI_ARGUMENTS_FORMAT = (
        'the arguments entered were: {arguments}\n\n'
    )

    _API_CALL_FORMAT = (
        'service: {service}\n\n'
        'operation: {operation}\n\n'
        'with parameters:\n{params}\n\n'
    )
    _HTTP_REQUEST_FORMAT = (
        'the method used for the http request was: {method}\n\n'
        'the headers of the http request was:\n{headers}\n\n'
        'the body of the http request was:\n{body}\n\n'
    )
    _HTTP_RESPONSE_FORMAT = (
        'the status code of the http response was: {status_code}\n\n'
        'the headers of the http response was:\n{headers}\n\n'
        'the body of the http response was:\n{body}\n\n'
    )
    _PARSED_RESPONSE_FORMAT = (
        'the parsed response was:\n{parsed}\n\n'
    )
    _CLI_RC_FORMAT = (
        'the return code of this command was: {rc}\n\n'
    )

    def _display_cli_version(self, event_record):
        self._output.write(
            self._CLI_VERSION_FORMAT.format(version=event_record['payload'])
        )

    def _display_cli_arguments(self, event_record):
        self._output.write(
            self._CLI_ARGUMENTS_FORMAT.format(
                arguments=event_record['payload'])
        )

    def _display_api_call(self, event_record):
        payload = event_record['payload']
        self._output.write(
            self._API_CALL_FORMAT.format(
                service=payload['service'],
                operation=payload['operation'],
                params=payload['params']
            )
        )

    def _display_http_request(self, event_record):
        payload = event_record['payload']
        self._output.write(
            self._HTTP_REQUEST_FORMAT.format(
                method=payload['method'],
                headers=payload['headers'],
                body=payload['body']
            )
        )

    def _display_http_response(self, event_record):
        payload = event_record['payload']
        self._output.write(
            self._HTTP_RESPONSE_FORMAT.format(
                status_code=payload['status_code'],
                headers=payload['headers'],
                body=payload['body']
            )
        )

    def _display_parsed_response(self, event_record):
        payload = event_record['payload']
        self._output.write(
            self._PARSED_RESPONSE_FORMAT.format(parsed=payload))

    def _display_cli_rc(self, event_record):
        self._output.write(
            self._CLI_RC_FORMAT.format(rc=event_record['payload']))


class ShowCommand(BasicCommand):
    NAME = 'show'
    DESCRIPTION = (
        'shows the various events related to running a specific cli command. '
        'if this command is ran without any positional arguments, it will '
        'display the events for the last cli command ran.'
    )
    FORMATTERS = {
        'detailed': DetailedFormatter
    }
    ARG_TABLE = [
        {'name': 'command_id', 'nargs': '?', 'default': 'latest',
         'positional_arg': True,
         'help_text': (
             'the id of the cli command to show. if this argument is '
             'omitted it will show the last the cli command ran.')},
        {'name': 'include', 'nargs': '+',
         'help_text': (
             'specifies which events to **only** include when showing the '
             'cli command.  this argument is mutually exclusive with '
             '``--exclude``.')},
        {'name': 'exclude', 'nargs': '+',
         'help_text': (
             'Specifies which events to exclude when showing the '
             'CLI command.  This argument is mutually exclusive with '
             '``--include``.')},
        {'name': 'format', 'choices': FORMATTERS.keys(),
         'default': 'detailed', 'help_text': (
            'Specifies which format to use in showing the events for '
            'the specified CLI command.')}
    ]

    def __init__(self, session, db_reader=None):
        super(ShowCommand, self).__init__(session)
        self._db_reader = db_reader
        if db_reader is None:
            self._db_reader = DatabaseRecordReader()

    def _run_main(self, parsed_args, parsed_globals):
        self._validate_args(parsed_args)
        formatter = self.FORMATTERS[parsed_args.format](
            include=parsed_args.include, exclude=parsed_args.exclude)
        for record in self._get_record_iterator(parsed_args):
            formatter.display(record)
        return 0

    def _validate_args(self, parsed_args):
        if parsed_args.exclude and parsed_args.include:
            raise ValueError(
                'Either --exclude or --include can be provided but not both')

    def _get_record_iterator(self, parsed_args):
        if parsed_args.command_id == 'latest':
            return self._db_reader.yield_latest_records()
        else:
            return self._db_reader.yield_records(parsed_args.command_id)
