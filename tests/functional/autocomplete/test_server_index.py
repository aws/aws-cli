import os

from awscli import clidriver
from awscli.autocomplete import db, generator
from awscli.autocomplete.serverside import model
from awscli.autocomplete.serverside.indexer import APICallIndexer
from awscli.autocomplete.local.indexer import ModelIndexer
from awscli.testutils import unittest


def _ddb_only_command_table(command_table, **kwargs):
    for key in list(command_table):
        if key != 'dynamodb':
            del command_table[key]


class TestCanGenerateServerIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_connection = db.DatabaseConnection(":memory:")
        index_generator = generator.IndexGenerator(
            [ModelIndexer(cls.db_connection),
             APICallIndexer(cls.db_connection)],
        )
        driver = clidriver.create_clidriver()
        driver.session.register('building-command-table.main',
                                _ddb_only_command_table)
        index_generator.generate_index(driver)

    def test_can_query_model_from_index(self):
        lookup = model.DBCompletionLookup(self.db_connection)
        # We'll query a few lookups to ensure that we indexed them
        # correctly.
        result = lookup.get_server_completion_data(
            ['aws', 'dynamodb'], 'delete-table', 'table-name')
        self.assertEqual(
            result,
            {'completions': [
                {'jp_expr': 'TableNames[]',
                 'operation': 'list_tables',
                 'parameters': {},
                 'service': 'dynamodb'}]}
        )
        result = lookup.get_server_completion_data(
            ['aws', 'dynamodb'], 'update-global-table', 'global-table-name')
        self.assertEqual(
            result,
            {'completions': [
                {'jp_expr': 'GlobalTables[].GlobalTableName',
                 'operation': 'list_global_tables',
                 'parameters': {},
                 'service': 'dynamodb'}]}
        )

    def test_returns_none_if_no_lookup_data_found(self):
        lookup = model.DBCompletionLookup(self.db_connection)
        self.assertIsNone(
            lookup.get_server_completion_data(
                ['aws', 'dynamodb'], 'delete-table', 'unknown-param'))
        self.assertIsNone(
            lookup.get_server_completion_data(
                ['aws', 'dynamodb'], 'unknown-operation', 'foo'))
        self.assertIsNone(
            lookup.get_server_completion_data(
                ['aws', 'unknown-service'], 'unknown-operation', 'foo'))


class TestCanHandleNoCompletionData(unittest.TestCase):
    def setUp(self):
        self.db_connection = db.DatabaseConnection(":memory:")

    def tearDown(self):
        self.db_connection.close()

    def _disable_cli_loaders(self, event_name, session, **kwargs):
        loader = session.get_component('data_loader')
        for path in loader.search_paths[::]:
            if path.endswith(os.path.join('awscli', 'data')):
                loader.search_paths.remove(path)

    def test_no_errors_when_missing_completion_data(self):
        index_generator = generator.IndexGenerator(
            [ModelIndexer(self.db_connection),
             APICallIndexer(self.db_connection)],
        )
        driver = clidriver.create_clidriver()
        # We're going to remove the CLI data path from the loader.
        # This will result in the loader not being able to find any
        # completion data, which allows us to verify the behavior when
        # there's no completion data.
        driver.session.register('building-command-table.main',
                                _ddb_only_command_table)
        driver.session.register('building-command-table.dynamodb',
                                self._disable_cli_loaders)
        index_generator.generate_index(driver)
        # We shouldn't get any data now because we couldn't load
        # completion data.
        lookup = model.DBCompletionLookup(self.db_connection)
        result = lookup.get_server_completion_data(
            ['aws', 'dynamodb'], 'delete-table', 'table-name')
        self.assertIsNone(result)
