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
from awscli.autocomplete.db import DatabaseConnection


def create_model_indexer(filename):
    index = ModelIndexer(DatabaseConnection(filename))
    return index


class ModelIndexer(object):
    # TODO add full names to custom commands to get rid of this map
    _HIGH_LEVEL_SERVICE_FULL_NAMES = {
        's3': 'High level S3 commands',
        'ddb': 'High level DynamoDB commands'
    }

    _NON_SERVICE_COMMANDS = ['configure', 'history', 'cli-dev']

    _CREATE_CMD_TABLE = """\
        CREATE TABLE IF NOT EXISTS command_table (
          command TEXT, 
          full_name TEXT,
          parent TEXT REFERENCES command_table,
          PRIMARY KEY (command, parent)
        );
    """
    _CREATE_PARAM_TABLE = """\
        CREATE TABLE IF NOT EXISTS param_table (
          param_id INTEGER PRIMARY KEY,
          argname TEXT,
          type_name TEXT,
          command TEXT,
          parent TEXT,
          nargs TEXT,
          positional_arg TEXT,
          required INTEGER,
          FOREIGN KEY (command, parent) REFERENCES
            command_table(command, parent)
        );
    """

    _CREATE_COMMAND_TABLE_INDEX = """\
        CREATE INDEX parent_index 
            ON command_table(parent);
    """

    _CREATE_PARAM_TABLE_INDEX = """\
        CREATE INDEX parent_command_index 
            ON param_table(parent, command);
    """

    def __init__(self, db_connection):
        self._db_connection = db_connection

    def generate_index(self, clidriver):
        self._create_tables()
        parent = 'aws'
        self._db_connection.execute(
            'INSERT OR REPLACE INTO command_table (command, parent)'
            'VALUES (:command, :parent)',
            command=parent,
            parent='',
        )
        help_command_table = clidriver.create_help_command().command_table
        command_table = clidriver.subcommand_table
        self._generate_arg_index(command=parent, parent='',
                                 arg_table=clidriver.arg_table)
        self._generate_command_index(command_table, parent=parent,
                                     help_command_table=help_command_table)

        self._generate_table_indexes()

    def _create_tables(self):
        self._db_connection.execute(self._CREATE_CMD_TABLE)
        self._db_connection.execute(self._CREATE_PARAM_TABLE)

    def _generate_arg_index(self, command, parent, arg_table):
        for name, value in arg_table.items():
            # SQLite has no boolean data type, so we use Integer instead
            required = 1 if value.required else 0
            self._db_connection.execute(
                'INSERT INTO param_table '
                '(argname, type_name, command, parent, nargs, positional_arg,'
                'required)'
                ' VALUES (:argname, :type_name, :command, :parent, :nargs, '
                '         :positional_arg, :required)',
                argname=name, type_name=value.cli_type_name,
                command=command, parent=parent,
                nargs=value.nargs, positional_arg=value.positional_arg,
                required=required
            )

    def _get_service_full_name(self, name, help_command_table):
        if help_command_table and name not in self._NON_SERVICE_COMMANDS:
            if name in self._HIGH_LEVEL_SERVICE_FULL_NAMES:
                return self._HIGH_LEVEL_SERVICE_FULL_NAMES[name]
            service = help_command_table.get(name)
            if service:
                return service.service_model.metadata['serviceFullName']

    def _generate_command_index(self, command_table,
                                parent, help_command_table=None):
        for name, command in command_table.items():
            full_name = self._get_service_full_name(name, help_command_table)
            self._db_connection.execute(
                'INSERT INTO command_table (command, parent, full_name) '
                'VALUES (:command, :parent, :full_name)',
                command=name, parent=parent, full_name=full_name
            )
            self._generate_arg_index(command=name, parent=parent,
                                     arg_table=command.arg_table)
            self._generate_command_index(command.subcommand_table,
                                         parent='%s.%s' % (parent, name))

    def _generate_table_indexes(self):
        self._db_connection.execute(self._CREATE_COMMAND_TABLE_INDEX)
        self._db_connection.execute(self._CREATE_PARAM_TABLE_INDEX)
