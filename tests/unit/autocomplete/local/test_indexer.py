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
import os
import shutil

from awscli.testutils import unittest, mock
from awscli.autocomplete import db
from awscli.autocomplete.local import indexer, model
import tempfile

from botocore.session import Session


# Quick note about these tests.  sqlite3 is used as the data store for the
# index cache.  When testing this we have two options.  We can either invoke
# various methods from the indexer and the query the generate sqlite DB and
# make sure the records make sense, or we can invoke various methods from the
# indexer and then use our ``ModelIndex`` class to query the index.  The
# ``ModelIndex`` is an abstraction that hides sqlite3 from the clients of the
# index.  I've decided to test the two together, that is, use our indexer and
# the ``ModelIndexer`` to ensure we're getting the right data.  This has the
# downsides that we don't verify anything that we're writing to our sqlite3
# database.  We could be writing inefficient or completely wrong data to our
# DB, but as last the ``ModelIndexer`` understands how to query the data, we'll
# never know.  The reason I think this approach makes sense is that I suspect
# the schema will change as this feature is developed, and it's more important
# to ensure that we can read the index we generate compared to verifying the
# contents of the index.  Once this schema has stabilized we could go in and
# write tests that work at the sqlite3 layer.

class DummyCommand(object):
    def __init__(self, command_name, subcommand_table=None, arg_table=None):
        self.name = command_name
        if subcommand_table is None:
            subcommand_table = {}
        self.subcommand_table = subcommand_table
        if arg_table is None:
            arg_table = {}
        self.arg_table = arg_table


class DummyArg(object):
    def __init__(self, name, cli_type_name='string', nargs=None,
                 positional_arg=False):
        self.name = name
        self.cli_type_name = cli_type_name
        self.nargs = nargs
        self.positional_arg = positional_arg


class TestCanRetrieveCommands(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.aws_command = DummyCommand(
            # The CLIDriver doesn't actually have a ``name`` property,
            # but it should probably be 'aws'.
            command_name=None,
            arg_table={
                'region': DummyArg('region'),
                'endpoint-url': DummyArg('endpoint-url'),
            },
            subcommand_table={
                'ec2': DummyCommand(
                    command_name='ec2',
                    subcommand_table={
                        'describe-instances': DummyCommand(
                            'describe-instances',
                            arg_table={
                                'instance-ids': DummyArg('instance-ids'),
                                'filters': DummyArg(
                                    'filters', 'list', nargs='+'),
                            }
                        ),
                        'run-instances': DummyCommand('run-instances'),
                    }
                ),
                's3': DummyCommand(
                    command_name='s3',
                    subcommand_table={
                        'list-objects': DummyCommand('list-objects'),
                        'put-object': DummyCommand('put-object'),
                    }
                )
            }
        )
        # Ideally we just use ':memory:', but that's for
        # a specific sqlite3 connection so we'd have to
        # update our interfaces to return/accept a db connection.
        # I'd prefer not to have db connections as part of the
        # indexing interface.
        self.temp_dir = tempfile.mkdtemp()
        self.tempfile = os.path.join(self.temp_dir, 'temp.db')
        self.db_conn = db.DatabaseConnection(self.tempfile)
        self.indexer = indexer.ModelIndexer(self.db_conn)
        self.query = model.ModelIndex(self.tempfile)

    def tearDown(self):
        self.db_conn.close()
        # TODO: This object is impossible to clean up after properly it should
        # take a db connection instead of a filename so it doesn't have a
        # private copy of the database connection.
        self.query._db_connection.close()
        shutil.rmtree(self.temp_dir)

    def test_can_retrieve_top_level_commands(self):
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.command_names(lineage=['aws'])),
            set(['ec2', 's3'])
        )

    def test_can_retrieve_operation_names(self):
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.command_names(lineage=['aws', 'ec2'])),
            set(['describe-instances', 'run-instances']),
        )

    def test_can_retrieve_global_params(self):
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.arg_names(lineage=[], command_name='aws')),
            set(['region', 'endpoint-url']),
        )

    def test_can_retrieve_service_params(self):
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.arg_names(lineage=['aws', 'ec2'],
                                     command_name='describe-instances')),
            set(['instance-ids', 'filters']),
        )

    def test_can_retrieve_correct_commands_when_shadowed(self):
        # Suppose that 's3' had a 'describe-instances' operation.  We
        # should be able to differentiate between this command and the
        # one in ec2 via the ``parent`` arg.
        s3_commands = self.aws_command.subcommand_table['s3'].subcommand_table
        s3_commands['describe-instances'] = DummyCommand('describe-instances')
        self.indexer.generate_index(self.aws_command)
        # The 'ec2' version has several params in its arg table, but this
        # 's3' version should have no params because we didn't add an arg
        # table.
        self.assertEqual(
            set(self.query.arg_names(lineage=['aws', 's3'],
                                     command_name='describe-instances')),
            set([]),
        )

    def test_empty_list_when_no_args(self):
        # Service commands don't have arguments.
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.arg_names(lineage=['aws'],
                                     command_name='ec2')),
            set([]),
        )

    def test_empty_list_on_unknown_service(self):
        self.indexer.generate_index(self.aws_command)
        self.assertEqual(
            set(self.query.command_names(lineage=['aws', 'foobar'])),
            set([]),
        )

    def test_can_get_argument_data(self):
        self.indexer.generate_index(self.aws_command)
        arg_data = self.query.get_argument_data(
            lineage=['aws', 'ec2'],
            command_name='describe-instances',
            arg_name='filters',

        )
        self.assertEqual(
            arg_data,
            model.CLIArgument(
                argname='filters',
                type_name='list',
                command='describe-instances',
                parent='aws.ec2',
                nargs='+',
                positional_arg='0',
            ),
        )


class TestCanCreateModelIndexer(unittest.TestCase):

    def test_can_create_model_indexer(self):
        index = indexer.create_model_indexer('/tmp/a/b/c/d')
        self.assertIsInstance(index, indexer.ModelIndexer)
