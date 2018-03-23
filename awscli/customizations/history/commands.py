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
import os

from awscli.compat import is_windows
from awscli.utils import is_a_tty
from awscli.utils import OutputStreamFactory

from awscli.customizations.commands import BasicCommand
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.constants import HISTORY_FILENAME_ENV_VAR
from awscli.customizations.history.constants import DEFAULT_HISTORY_FILENAME
from awscli.customizations.history.db import DatabaseRecordReader


class HistorySubcommand(BasicCommand):
    def __init__(self, session, db_reader=None, output_stream_factory=None):
        super(HistorySubcommand, self).__init__(session)
        self._db_reader = db_reader
        self._output_stream_factory = output_stream_factory
        if output_stream_factory is None:
            self._output_stream_factory = OutputStreamFactory()

    def _connect_to_history_db(self):
        if self._db_reader is None:
            connection = DatabaseConnection(self._get_history_db_filename())
            self._db_reader = DatabaseRecordReader(connection)

    def _close_history_db(self):
        self._db_reader.close()

    def _get_history_db_filename(self):
        filename = os.environ.get(
            HISTORY_FILENAME_ENV_VAR, DEFAULT_HISTORY_FILENAME)
        if not os.path.exists(filename):
            raise RuntimeError(
                'Could not locate history. Make sure cli_history is set to '
                'enabled in the ~/.aws/config file'
            )
        return filename

    def _should_use_color(self, parsed_globals):
        if parsed_globals.color == 'on':
            return True
        elif parsed_globals.color == 'off':
            return False
        return is_a_tty() and not is_windows

    def _get_output_stream(self, preferred_pager=None):
        if is_a_tty():
            return self._output_stream_factory.get_pager_stream(
                preferred_pager)
        return self._output_stream_factory.get_stdout_stream()
