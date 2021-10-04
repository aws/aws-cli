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
import glob
import os
import tempfile

from awscli.testutils import unittest
from awscli.autocomplete import generator
from awscli.autocomplete.local import model


class TestCanGenerateEntireIndex(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tempfile = os.path.join(self.temp_dir, 'temp.db')
        self.model_index = model.ModelIndex(self.tempfile)

    def tearDown(self):
        self.model_index._db_connection.close()

    def assert_no_temp_index_files(self):
        # When generating the index, it generates it in a file different from
        # its final location so that only a completely built index is ever at
        # the final location. This intermediary file shares the same name as
        # final location except it has an additional suffix extension (e.g.,
        # ``.temp`` at the end). So this check ensures there are no lingering
        # intermediary files from building the index (even if the suffix
        # extension changes in the future).
        possible_matches = glob.glob(f'{self.tempfile}.*')
        self.assertEqual(possible_matches, [])

    def test_can_generate_entire_index(self):
        # The point of this test is to make sure generating the index
        # doesn't break in some obvious way.  The specifics of index
        # generation are tested in tests/unit/autocomplete.  Here we just
        # generate the entire index and perform basic sanity checks.  It's
        # just a functional smoke test.
        generator.generate_index(self.tempfile)

        # Basic sanity checks.  Index generation for the entire CLI
        # takes a while so all the sanity checks are combined in a single
        # test method.
        self.assertTrue(os.path.exists(self.tempfile))
        self.assert_no_temp_index_files()

        commands = self.model_index.command_names(lineage=['aws'])
        self.assertIn('ec2', commands)
        self.assertIn('s3', commands)
        self.assertIn('s3api', commands)
        global_args = self.model_index.arg_names(lineage=[],
                                                 command_name='aws')
        self.assertIn('region', global_args)
        self.assertIn('endpoint-url', global_args)

        single_arg = self.model_index.get_argument_data(
            lineage=[], command_name='aws',
            arg_name='output')
        self.assertEqual(single_arg.argname, 'output')
        self.assertEqual(single_arg.command, 'aws')
        self.assertEqual(single_arg.parent, '')
        self.assertIsNone(single_arg.nargs)
