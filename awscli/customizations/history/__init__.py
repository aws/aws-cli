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
import logging

from botocore.history import get_global_history_recorder

from awscli.compat import sqlite3
from awscli.customizations.commands import BasicCommand
from awscli.customizations.history.constants import HISTORY_FILENAME_ENV_VAR
from awscli.customizations.history.constants import DEFAULT_HISTORY_FILENAME
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import RecordBuilder
from awscli.customizations.history.db import DatabaseHistoryHandler
from awscli.customizations.history.show import ShowCommand


LOG = logging.getLogger(__name__)


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

        history_recorder = get_global_history_recorder()
        history_recorder.add_handler(db_handler)
        history_recorder.enable()


def _should_enable_cli_history(session, parsed_args):
    if parsed_args.command == 'history':
        return False
    elif sqlite3 is None:
        LOG.debug(
            'sqlite3 is not available. Skipping check to enable CLI history.')
        return False
    else:
        scoped_config = session.get_scoped_config()
        return scoped_config.get('cli_history') == 'enabled'


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
        {'name': 'show', 'command_class': ShowCommand}
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            raise ValueError("usage: aws [options] <command> <subcommand> "
                             "[parameters]\naws: error: too few arguments")
