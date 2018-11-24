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
    _CREATE_CMD_TABLE = """\
        CREATE TABLE IF NOT EXISTS command_table (
          command TEXT,
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
          FOREIGN KEY (command, parent) REFERENCES
            command_table(command, parent)
        );
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
        command_table = clidriver.subcommand_table
        self._generate_arg_index(command=parent, parent='',
                                 arg_table=clidriver.arg_table)
        self._generate_command_index(command_table, parent=parent)

    def _create_tables(self):
        self._db_connection.execute(self._CREATE_CMD_TABLE)
        self._db_connection.execute(self._CREATE_PARAM_TABLE)

    def _generate_arg_index(self, command, parent, arg_table):
        for name, value in arg_table.items():
            self._db_connection.execute(
                'INSERT INTO param_table '
                '(argname, type_name, command, parent, nargs, positional_arg)'
                ' VALUES (:argname, :type_name, :command, :parent, :nargs, '
                '         :positional_arg)',
                argname=name, type_name=value.cli_type_name,
                command=command, parent=parent,
                nargs=value.nargs, positional_arg=value.positional_arg
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
