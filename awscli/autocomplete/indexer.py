# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import sqlite3


LOG = logging.getLogger(__name__)


def create_model_indexer(filename):
    index = ModelIndexer(DatabaseConnection(filename))
    return index


class ModelIndexer(object):
    def __init__(self, db_connection):
        self._db_connection = db_connection

    def generate_index(self, clidriver):
        parent = 'aws'
        self._db_connection.execute(
            'INSERT OR REPLACE INTO command_table (command)'
            'VALUES (:command)',
            command=parent
        )
        command_table = clidriver.subcommand_table
        self._generate_arg_index(command=parent, parent='',
                                 arg_table=clidriver.arg_table)
        self._generate_command_index(command_table, parent=parent)

    def _generate_arg_index(self, command, parent, arg_table):
        for name, value in arg_table.items():
            self._db_connection.execute(
                'INSERT INTO param_table '
                '(argname, type_name, command, parent, nargs)'
                ' VALUES (:argname, :type_name, :command, :parent, :nargs)',
                argname=name, type_name=value.cli_type_name,
                command=command, parent=parent,
                nargs=value.nargs,
            )

    def _generate_command_index(self, command_table, parent):
        for name, command in command_table.items():
            self._db_connection.execute(
                'INSERT INTO command_table (command, parent) '
                'VALUES (:command, :parent)',
                command=name, parent=parent,
            )
            self._generate_arg_index(command=name, parent=parent,
                                     arg_table=command.arg_table)
            self._generate_command_index(command.subcommand_table,
                                         parent='%s.%s' % (parent, name))


# This is similar to DBConnection in awscli.customization.history.
# I'd like to reuse code, but we also have the contraint that we don't
# want to import anything outside of awscli.autocomplete to ensure
# our startup time is as minimal as possible.
class DatabaseConnection(object):
    _CREATE_CMD_TABLE = """\
        CREATE TABLE IF NOT EXISTS command_table (
          command TEXT,
          parent TEXT REFERENCES command_table,
          PRIMARY KEY (command, parent)
        );
    """
    _CREATE_PARAM_TABLE = """\
        CREATE TABLE IF NOT EXISTS param_table (
          argname TEXT,
          type_name TEXT,
          command TEXT,
          parent TEXT,
          nargs TEXT,
          FOREIGN KEY (command, parent) REFERENCES
            command_table(command, parent)
        );
    """
    _ENABLE_WAL = 'PRAGMA journal_mode=WAL'

    def __init__(self, db_filename):
        self._db_conn = None
        self._db_filename = db_filename

    @property
    def _connection(self):
        if self._db_conn is None:
            self._db_conn = sqlite3.connect(
                self._db_filename, check_same_thread=False,
                isolation_level=None)
            self._ensure_database_setup()
        return self._db_conn

    def close(self):
        self._connection.close()

    def execute(self, query, **kwargs):
        return self._connection.execute(query, kwargs)

    def _ensure_database_setup(self):
        self._create_table()
        self._try_to_enable_wal()

    def _create_table(self):
        self.execute(self._CREATE_CMD_TABLE)
        self.execute(self._CREATE_PARAM_TABLE)

    def _try_to_enable_wal(self):
        try:
            self.execute(self._ENABLE_WAL)
        except sqlite3.Error:
            # This is just a performance enhancement so it is optional. Not all
            # systems will have a sqlite compiled with the WAL enabled.
            LOG.debug('Failed to enable sqlite WAL.')
