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
from nose.tools import assert_in

from awscli.autocomplete import main, generator
from awscli.autocomplete.local import indexer
from awscli import clidriver
from awscli import testutils


def _ec2_only_command_table(command_table, **kwargs):
    for key in list(command_table):
        if key != 'ec2':
            del command_table[key]


def test_smoke_test_completer():
    # Verify we can:
    # 1. Generate part of the completion index
    # 2. Create a completer with the factory function
    # 3. Generate completions using this index.
    #
    # We don't generate the entire completion index for all commands.
    # We're more interested in the end to end flow.  The test_generator.py
    # file verifies that we can generate the entire index so we don't need
    # to do this twice (it takes a while).
    with testutils.temporary_file('w') as f:
        _generate_index(f.name)
        completions = _autocomplete(f.name, 'aws ec2 desc')
        # The API can change so we won't assert a specific list, but we'll
        # pick a few operations that we know will always be there.
        completion_strings = [c.result for c in completions]
        assert_in('describe-instances', completion_strings)
        assert_in('describe-regions', completion_strings)


def _autocomplete(filename, command_line):
    completer = main.create_autocompleter(filename)
    return completer.autocomplete(command_line)


def _generate_index(filename):
    # This will eventually be moved into some utility function.
    index_generator = generator.IndexGenerator(
        [indexer.create_model_indexer(filename)],
    )
    driver = clidriver.create_clidriver()
    driver.session.register('building-command-table.main',
                            _ec2_only_command_table)
    index_generator.generate_index(driver)
