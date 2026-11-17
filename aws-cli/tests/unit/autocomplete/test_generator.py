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
from awscli.autocomplete import generator
from awscli.autocomplete.local import indexer
from awscli.clidriver import CLIDriver
from awscli.testutils import mock, unittest


class TestGenerateCompletionIndex(unittest.TestCase):
    def test_use_high_level_generator_for_index_creation(self):
        model_index = mock.Mock(spec=indexer.ModelIndexer)
        clidriver = mock.Mock(spec=CLIDriver)
        index = generator.IndexGenerator([model_index])
        index.generate_index(clidriver)
        model_index.generate_index.assert_called_with(clidriver)

    @mock.patch('awscli.autocomplete.generator.IndexGenerator')
    @mock.patch('awscli.autocomplete.generator.clidriver.create_clidriver')
    @mock.patch('awscli.autocomplete.generator.db.DatabaseConnection')
    def test_generates_index_in_transaction(
        self, database_connection, _create_clidriver, _index_generator
    ):
        generator._do_generate_index('index.db')

        database_connection.return_value.execute.assert_has_calls(
            [mock.call('BEGIN'), mock.call('COMMIT')]
        )
