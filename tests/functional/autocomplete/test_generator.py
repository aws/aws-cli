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
from awscli.testutils import unittest, create_clidriver, temporary_file
from awscli.autocomplete import generator
from awscli.autocomplete.local import model, indexer
from awscli.autocomplete.serverside.indexer import create_apicall_indexer


class TestCanGenerateEntireIndex(unittest.TestCase):
    def test_can_generate_entire_index(self):
        # The point of this test is to make sure generating the index
        # doesn't break in some obvious way.  The specifics of index
        # generation are tested in tests/unit/autocomplete.  Here we just
        # generate the entire index and perform basic sanity checks.  It's
        # just a functional smoke test.
        driver = create_clidriver()
        with temporary_file('w') as f:
            index_generator = generator.IndexGenerator([
                indexer.create_model_indexer(f.name),
                create_apicall_indexer(f.name),
            ])
            index_generator.generate_index(driver)

            # Basic sanity checks.  Index generation for the entire CLI
            # takes a while so all the sanity checks are combined in a single
            # test method.
            model_index = model.ModelIndex(f.name)
            commands = model_index.command_names(lineage=['aws'])
            self.assertIn('ec2', commands)
            self.assertIn('s3', commands)
            self.assertIn('s3api', commands)
            global_args = model_index.arg_names(lineage=[], command_name='aws')
            self.assertIn('region', global_args)
            self.assertIn('endpoint-url', global_args)

            single_arg = model_index.get_argument_data(
                lineage=[], command_name='aws',
                arg_name='output')
            self.assertEqual(single_arg.argname, 'output')
            self.assertEqual(single_arg.command, 'aws')
            self.assertEqual(single_arg.parent, '')
            self.assertIsNone(single_arg.nargs)
