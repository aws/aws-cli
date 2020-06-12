# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from prompt_toolkit import Application

from awscli.autocomplete.main import create_autocompleter
from awscli.clidriver import create_clidriver
from awscli.customizations.autoprompt.factory import PromptToolkitFactory
from awscli.customizations.autoprompt.prompttoolkit import (
    PromptToolkitCompleter, PromptToolkitPrompter
)
from awscli.testutils import unittest


class TestPromptToolkitPrompterBuffer(unittest.TestCase):
    """This set of tests tests that we set the buffer (aka "construction zone")
    correctly. Some of these tests test against specific edge cases that have
    previously been known to produce unexpected behavior.

    """
    def setUp(self):
        self.completion_source = create_autocompleter()
        self.completer = PromptToolkitCompleter(self.completion_source)
        self.factory = PromptToolkitFactory(self.completer)
        self.driver = create_clidriver()
        self.app = self.create_application()
        self.prompter = PromptToolkitPrompter(
            completion_source=self.completion_source, driver=self.driver,
            app=self.app)
        self.prompter.input_buffer = self.factory.create_input_buffer()
        self.prompter.doc_buffer = self.factory.create_doc_buffer()

    def get_updated_input_buffer_text(self, original_args):
        self.prompter.args = original_args
        self.prompter.pre_run()
        return self.prompter.input_buffer.document.text

    def create_application(self):
        layout = self.factory.create_layout()
        return Application(layout=layout)

    def test_reset_buffer_text_if_invalid_command_entered(self):
        original_args = ['ec2', 'fake']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, '')

    def test_dont_reset_buffer_text_if_complete_command_entered(self):
        original_args = ['ec2']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 ')

    def test_dont_reset_buffer_text_if_file_path_entered(self):
        original_args = ['s3', 'mv', '/path/to/file/1', 's3://path/to/file/2']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 mv /path/to/file/1 s3://path/to/file/2 ')

    def test_dont_reset_buffer_text_if_s3_ls_entered(self):
        original_args = ['s3', 'ls']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 ls ')

    def test_dont_reset_buffer_text_if_s3_ls_space_entered(self):
        original_args = ['s3', 'ls ']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 ls ')

    def test_reset_buffer_text_if_invalid_command_with_option_entered(self):
        original_args = ['ec2', 'fake', '--output']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, '')

    def test_dont_reset_buffer_text_if_valid_command_with_option_entered(self):
        original_args = ['ec2', 'describe-instances', '--output']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 describe-instances --output ')

    def test_reset_buffer_text_if_empty_aws_command_entered(self):
        original_args = [' ']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, ' ')
