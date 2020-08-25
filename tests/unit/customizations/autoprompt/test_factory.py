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
import mock

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import DummyCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout import Window
from prompt_toolkit.widgets import SearchToolbar

from awscli.customizations.autoprompt.factory import (
    FormatTextProcessor, PromptToolkitKeyBindings, PromptToolkitFactory,
    ToolbarHelpText
)
from awscli.testutils import unittest


class TestPromptToolkitFactory(unittest.TestCase):
    def setUp(self):
        self.factory = PromptToolkitFactory(completer=DummyCompleter())

    def dummy_callback(self, *args, **kwargs):
        return

    def test_can_create_input_buffer(self):
        buffer = self.factory.create_input_buffer()
        self.assertEqual(buffer.name, 'input_buffer')

    def test_can_create_input_buffer_with_callback(self):
        buffer = self.factory.create_input_buffer(self.dummy_callback)
        self.assertTrue(buffer.on_text_changed is not None)

    def test_can_create_doc_buffer(self):
        buffer = self.factory.create_doc_buffer()
        self.assertEqual(buffer.name, 'doc_buffer')

    def test_can_create_bottom_toolbar_buffer(self):
        buffer = self.factory.create_bottom_toolbar_buffer()
        self.assertEqual(buffer.name, 'bottom_toolbar_buffer')

    def test_can_create_input_buffer_container(self):
        buffer = mock.Mock(spec=Buffer)
        container = self.factory.create_input_buffer_container(buffer)
        self.assertTrue(container.content is not None)

    def test_can_create_doc_window(self):
        buffer = mock.Mock(spec=Buffer)
        container = self.factory.create_doc_window(buffer)
        self.assertTrue(container.content is not None)

    def test_can_create_bottom_toolbar_container(self):
        buffer = mock.Mock(spec=Buffer)
        container = self.factory.create_bottom_toolbar_container(buffer)
        self.assertTrue(container.content is not None)

    def test_can_create_search_field(self):
        search_field = self.factory.create_search_field()
        self.assertIsInstance(search_field, SearchToolbar)

    def test_can_create_layout(self):
        layout = self.factory.create_layout()
        self.assertTrue(layout.container is not None)

    def test_can_create_layout_with_input_buffer_callback_specified(self):
        layout = self.factory.create_layout(
            on_input_buffer_text_changed=self.dummy_callback)
        self.assertTrue(layout.container is not None)

    def test_can_create_layout_with_input_buffer_container_specified(self):
        layout = self.factory.create_layout(input_buffer_container=Window())
        self.assertTrue(layout.container is not None)

    def test_can_create_layout_with_doc_window_specified(self):
        layout = self.factory.create_layout(doc_window=Window())
        self.assertTrue(layout.container is not None)

    def test_can_create_layout_with_search_field_specified(self):
        search_field = SearchToolbar()
        layout = self.factory.create_layout(search_field=search_field)
        self.assertTrue(layout.container is not None)

    def test_can_create_layout_with_bottom_toolbar_container_specified(self):
        layout = self.factory.create_layout(bottom_toolbar_container=Window())
        self.assertTrue(layout.container is not None)

    def test_can_create_key_bindings(self):
        key_bindings = self.factory.create_key_bindings()
        self.assertIsInstance(key_bindings, PromptToolkitKeyBindings)


class TestFormatTextProcessor(unittest.TestCase):
    def setUp(self):
        self.format_text_processor = FormatTextProcessor()

    def test_can_apply_transformation(self):
        text_input = mock.Mock()
        text_input.fragments = [('', '<style fg="black">[tab]</style>text1')]
        transformed_text = \
            self.format_text_processor.apply_transformation(text_input)
        actual_fragments = transformed_text.fragments
        expected_fragments = FormattedText([('fg:black', '[tab]'),
                                            ('', 'text1')])
        self.assertEqual(actual_fragments, expected_fragments)

    def test_can_apply_transformation_on_multiple_tags(self):
        text_input = mock.Mock()
        text_input.fragments = [('', (
                                        '<style fg="black">[tab]</style>text1'
                                        '<style fg="red">[up]</style>text2'
                                        '<style fg="blue">[down]</style>text3'
                                     ))]
        transformed_text = \
            self.format_text_processor.apply_transformation(text_input)
        actual_fragments = transformed_text.fragments
        expected_fragments = FormattedText(
            [
                ('fg:black', '[tab]'), ('', 'text1'),
                ('fg:red', '[up]'), ('', 'text2'),
                ('fg:blue', '[down]'), ('', 'text3')
            ])
        self.assertEqual(actual_fragments, expected_fragments)


class TestToolbarHelpText(unittest.TestCase):
    def test_can_get_input_buffer_key_bindings(self):
        style = '<style>'
        spacing = ''
        self.toolbar_help_text = ToolbarHelpText(style=style, spacing=spacing)
        actual_text = self.toolbar_help_text.input_buffer_key_binding_text
        expected_text = (
            f'{style}[TAB]</style> Cycle Forward'
            f'{style}[SHIFT+TAB]</style> Cycle Backward'
            f'{style}[UP]</style> Cycle Forward'
            f'{style}[DOWN]</style> Cycle Backward'
            f'{style}[SPACE]</style> Autocomplete Choice'
            f'{style}[ENTER]</style> Autocomplete Choice/Execute Command'
            f'{style}[F1]</style> Focus on Docs'
            f'{style}[F2]</style> Hide/Show on Docs'
            f'{style}[F3]</style> One/Multi column prompt'
        )
        self.assertEqual(actual_text, expected_text)

    def test_can_get_doc_window_key_bindings(self):
        style = '<style>'
        spacing = ''
        self.toolbar_help_text = ToolbarHelpText(style=style, spacing=spacing)
        actual_text = self.toolbar_help_text.doc_window_key_binding_text
        expected_text = (
            f'{style}[/]</style> Search Forward'
            f'{style}[?]</style> Search Backward'
            f'{style}[n]</style> Find Next Match'
            f'{style}[N]</style> Find Previous Match'
            f'{style}[w]</style> Go Up a Page'
            f'{style}[z]</style> Go Down a Page'
            f'{style}[j]</style> Go Up a Line'
            f'{style}[k]</style> Go Down a Line'
            f'{style}[g]</style> Go to Top'
            f'{style}[G]</style> Go to Bottom'
            f'{style}[F1] or [q]</style> Focus on Input'
        )
        self.assertEqual(actual_text, expected_text)
