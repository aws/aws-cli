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
from awscli.testutils import unittest, mock
from awscli.autocomplete import generator
from awscli.autocomplete.local import indexer
from awscli.clidriver import CLIDriver


class TestGenerateCompletionIndex(unittest.TestCase):

    def test_use_high_level_generator_for_index_creation(self):
        model_index = mock.Mock(spec=indexer.ModelIndexer)
        clidriver = mock.Mock(spec=CLIDriver)
        index = generator.IndexGenerator([model_index])
        index.generate_index(clidriver)
        model_index.generate_index.assert_called_with(clidriver)
