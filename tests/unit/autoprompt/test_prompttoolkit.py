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
import logging
import mock

from prompt_toolkit.completion import Completion, CompleteEvent
from prompt_toolkit.document import Document

from awscli.autocomplete.completer import CompletionResult
from awscli.autoprompt.logger import PromptToolkitHandler
from awscli.autoprompt.prompttoolkit import (
    PromptToolkitCompleter, loggers_handler_switcher
)
from awscli.testutils import unittest


class TestPromptToolkitCompleter(unittest.TestCase):
    def setUp(self):
        self.completion_source = mock.Mock()
        self.completion_source.autocomplete = mock.Mock()

    def assert_completions_match_expected(self, actual_completions,
                                          expected_completion_objects):
        expected_completions = (
            completion for completion in expected_completion_objects)
        for actual, expected in zip(actual_completions, expected_completions):
            self.assertEqual(actual.text, expected.text)
            self.assertEqual(actual.start_position, expected.start_position)
            self.assertEqual(actual.display, expected.display)

    def test_get_completions(self):
        expected_completion_objects = [
            Completion('create-image', 0, 'create-image', ''),
            Completion('describe-instances', 0, 'describe-instances', '')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('create-image'),
            CompletionResult('describe-instances')
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)

    def test_get_completions_has_no_completions(self):
        self.completion_source.autocomplete.return_value = []
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assertRaises(StopIteration, lambda: next(actual_completions))

    def test_get_completions_sorted_by_required(self):
        expected_completion_objects = [
            Completion('--name', 0, '--name (required)', ''),
            Completion('--instance-id', 0, '--instance-id (required)', ''),
            Completion('--debug', 0, '--debug', '')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('--debug', required=False),
            CompletionResult('--name', required=True),
            CompletionResult('--instance-id', required=True)
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)

    def test_get_completions_with_auto_prompt_overrides_filtered_out(self):
        expected_completion_objects = [
            Completion('--name', 0, '--name (required)', ''),
            Completion('--instance-id', 0, '--instance-id (required)', ''),
            Completion('--debug', 0, '--debug', '')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('--debug', required=False),
            CompletionResult('--name', required=True),
            CompletionResult('--instance-id', required=True),
            CompletionResult('--cli-auto-prompt', required=False),
            CompletionResult('--no-cli-auto-prompt', required=False),
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)

    def test_get_completions_with_duplicates_removed(self):
        expected_completion_objects = [
            Completion('--name', 0, '--name (required)', ''),
            Completion('--instance-id', 0, '--instance-id (required)', ''),
            Completion('--debug', 0, '--debug', '')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('--debug', required=False),
            CompletionResult('--debug', required=False),
            CompletionResult('--name', required=True),
            CompletionResult('--name', required=True),
            CompletionResult('--instance-id', required=True)
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)

    def test_get_completions_with_overrides_and_duplicates_removed(self):
        expected_completion_objects = [
            Completion('--name', 0, '--name (required)', ''),
            Completion('--instance-id', 0, '--instance-id (required)', ''),
            Completion('--debug', 0, '--debug', '')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('--debug', required=False),
            CompletionResult('--debug', required=False),
            CompletionResult('--name', required=True),
            CompletionResult('--name', required=True),
            CompletionResult('--instance-id', required=True),
            CompletionResult('--cli-auto-prompt', required=False),
            CompletionResult('--no-cli-auto-prompt', required=False),
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)

    def test_get_completions_with_display_meta(self):
        expected_completion_objects = [
            Completion('--name', 0, '--name (required)',
                       '[string] A name for the new image.'),
            Completion('--instance-id', 0, '--instance-id (required)',
                       '[string] The ID of the instance.'),
            Completion('--debug', 0, '--debug',
                       '[boolean] Turn on debug logging.')
        ]
        self.completion_source.autocomplete.return_value = [
            CompletionResult('--debug', required=False, cli_type_name='string',
                             help_text='The ID of the instance.'),
            CompletionResult('--name', required=True, cli_type_name='string',
                             help_text='A name for the new image.'),
            CompletionResult('--instance-id', required=True,
                             cli_type_name='boolean',
                             help_text='Turn on debug logging.')
        ]
        self.completer = PromptToolkitCompleter(self.completion_source)
        actual_completions = self.completer.get_completions(Document(),
                                                            CompleteEvent())
        self.assert_completions_match_expected(actual_completions,
                                               expected_completion_objects)


class TestLoggersHandlerSwitcher(unittest.TestCase):
    def test_can_switch_and_restore_handlers(self):
        log = logging.getLogger('test_prompt_logger')
        log.handlers = []
        log.addHandler(logging.StreamHandler())
        log.addHandler(logging.NullHandler())
        with loggers_handler_switcher():
            handlers = log.handlers
            self.assertEqual(len(handlers), 1)
            self.assertIsInstance(handlers[0], PromptToolkitHandler)
        handlers = log.handlers
        self.assertEqual(len(handlers), 2)
        self.assertIsInstance(handlers[0], logging.StreamHandler)
        self.assertIsInstance(handlers[1], logging.NullHandler)
