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
import sys
import logging

from botocore.history import get_global_history_recorder
from botocore.exceptions import ProfileNotFound

from awscli.compat import sqlite3
from awscli.customizations.commands import BasicCommand
from awscli.customizations.history.constants import HISTORY_FILENAME_ENV_VAR
from awscli.customizations.history.constants import DEFAULT_HISTORY_FILENAME
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import RecordBuilder
from awscli.customizations.history.db import DatabaseHistoryHandler
from awscli.customizations.history.show import ShowCommand
from awscli.customizations.history.list import ListCommand


LOG = logging.getLogger(__name__)
HISTORY_RECORDER = get_global_history_recorder()


def register_history_mode(event_handlers):
    event_handlers.register(
        'session-initialized', attach_history_handler)


def register_history_commands(event_handlers):
    event_handlers.register(
        "building-command-table.main", add_history_commands)


def attach_history_handler(session, parsed_args, **kwargs):
    if _should_enable_cli_history(session, parsed_args):
        LOG.debug('Enabling CLI history')

        history_filename = os.environ.get(
            HISTORY_FILENAME_ENV_VAR, DEFAULT_HISTORY_FILENAME)
        if not os.path.isdir(os.path.dirname(history_filename)):
            os.makedirs(os.path.dirname(history_filename))

        connection = DatabaseConnection(history_filename)
        writer = DatabaseRecordWriter(connection)
        record_builder = RecordBuilder()
        db_handler = DatabaseHistoryHandler(writer, record_builder)

        HISTORY_RECORDER.add_handler(db_handler)
        HISTORY_RECORDER.enable()


def _should_enable_cli_history(session, parsed_args):
    if parsed_args.command == 'history':
        return False
    try:
        scoped_config = session.get_scoped_config()
    except ProfileNotFound:
        # If the profile does not exist, cli history is definitely not
        # enabled, but don't let the error get propagated as commands down
        # the road may handle this such as the configure set command with
        # a --profile flag set.
        return False
    has_history_enabled = scoped_config.get('cli_history') == 'enabled'
    if has_history_enabled and sqlite3 is None:
        if has_history_enabled:
            sys.stderr.write(
                'cli_history is enabled but sqlite3 is unavailable. '
                'Unable to collect CLI history.\n'
            )
        return False
    return has_history_enabled


def add_history_commands(command_table, session, **kwargs):
    command_table['history'] = HistoryCommand(session)


class HistoryCommand(BasicCommand):
    NAME = 'history'
    DESCRIPTION = (
        'Commands to interact with the history of AWS CLI commands ran '
        'over time. To record the history of AWS CLI commands set '
        '``cli_history`` to ``enabled`` in the ``~/.aws/config`` file. '
        'This can be done by running:\n\n'
        '``$ aws configure set cli_history enabled``'
    )
    SUBCOMMANDS = [
        {'name': 'show', 'command_class': ShowCommand},
        {'name': 'list', 'command_class': ListCommand}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            raise ValueError("usage: aws [options] <command> <subcommand> "
                             "[parameters]\naws: error: too few arguments")
