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
import tempfile
import shutil

from awscli.compat import ensure_text_type
from awscli.customizations.wizard import ui
from awscli.testutils import unittest, mock, cd


class TestFileCompleter(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.mkdtemp()
        self.completer = ui.FileCompleter()

    def tearDown(self):
        shutil.rmtree(self.temporary_directory)

    def touch_file(self, filename):
        with open(os.path.join(self.temporary_directory, filename), 'w'):
            pass

    def get_completions_given_user_input(self, user_input):
        user_input = mock.Mock(text=ensure_text_type(user_input))

        with cd(self.temporary_directory):
            completions = list(
                self.completer.get_completions(user_input, None))
            return completions

    def test_can_list_children_of_dir_with_prefix(self):
        self.touch_file('foo.txt')
        self.touch_file('bar.txt')
        self.touch_file('baz.txt')

        completions = self.get_completions_given_user_input(u'./b')
        self.assertEqual(
            [c.text for c in completions], [os.path.join('.', 'bar.txt'),
                                            os.path.join('.', 'baz.txt')])

    def test_full_path_included_if_full_path_used_as_text(self):
        self.touch_file('foo.txt')

        completions = self.get_completions_given_user_input(
            self.temporary_directory + u'/'
        )
        self.assertEqual(
            [c.text for c in completions],
            [os.path.join(self.temporary_directory, 'foo.txt')]
        )

    def test_file_not_exists_returns_empy_list(self):
        completions = self.get_completions_given_user_input(
            self.temporary_directory + u'/asdf/does-not-exist'
        )
        self.assertEqual(completions, [])
