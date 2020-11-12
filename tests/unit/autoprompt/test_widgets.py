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
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout import (
    HSplit, Window, ConditionalContainer, FloatContainer
)
from prompt_toolkit.widgets import Dialog

from awscli.autoprompt import widgets
from awscli.testutils import unittest


class TestHelpPanelWidget(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.HelpPanelWidget()
        self.assertIsInstance(widget.container, ConditionalContainer)


class TestToolbarWidget(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.ToolbarWidget()
        self.assertIsInstance(widget.container, HSplit)


class TestHistorySignToolbarView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.HistorySignToolbarView()
        self.assertIsInstance(widget.content, Window)

    def test_buffer_has_correct_wording(self):
        widget = widgets.HistorySignToolbarView()
        buffer = widget.content.content.buffer
        self.assertEqual(buffer.document.text, widget.help_text)


class TestInputToolbarView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.InputToolbarView()
        self.assertIsInstance(widget.content, Window)

    def test_buffer_has_correct_wording(self):
        widget = widgets.InputToolbarView()
        buffer = widget.content.content.buffer
        self.assertEqual(buffer.document.text, widget.help_text)


class TestDocToolbarView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.DocToolbarView()
        self.assertIsInstance(widget.content, Window)

    def test_buffer_has_correct_wording(self):
        widget = widgets.DocToolbarView()
        buffer = widget.content.content.buffer
        self.assertEqual(buffer.document.text, widget.help_text)


class TestDebugToolbarView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.DebugToolbarView()
        self.assertIsInstance(widget.content, Window)

    def test_buffer_has_correct_wording(self):
        widget = widgets.DebugToolbarView()
        buffer = widget.content.content.buffer
        self.assertEqual(buffer.document.text, widget.help_text)


class TestDocHelpView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.DocHelpView()
        self.assertIsInstance(widget.content, HSplit)

    def test_frame_has_correct_title(self):
        widget = widgets.DocHelpView()
        title = widget.create_window(Buffer()).title
        self.assertEqual(title, widget.TITLE)

    def test_buffer_has_correct_wording(self):
        widget = widgets.DocHelpView()
        buffer = widget.create_buffer()
        self.assertEqual(buffer.document.text, widget.help_text)


class TestInputHelpView(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.InputHelpView()
        self.assertIsInstance(widget.content, HSplit)

    def test_frame_has_correct_title(self):
        widget = widgets.InputHelpView()
        title = widget.create_window(Buffer()).title
        self.assertEqual(title, widget.TITLE)

    def test_buffer_has_correct_wording(self):
        widget = widgets.InputHelpView()
        buffer = widget.create_buffer()
        self.assertEqual(buffer.document.text, widget.help_text)


class TestDebugPanelWidget(unittest.TestCase):
    def test_can_create_container(self):
        widget = widgets.DebugPanelWidget()
        self.assertIsInstance(widget.container, ConditionalContainer)

    def test_can_create_save_dialog(self):
        widget = widgets.DebugPanelWidget()
        save_dialog = widget.create_save_file_dialog()
        self.assertIsInstance(save_dialog, Dialog)

    def test_can_create_float_container_with_correct_bindings(self):
        widget = widgets.DebugPanelWidget()
        self.assertIsInstance(widget.float_container, FloatContainer)
        key_bindings = widget.float_container.key_bindings.\
                                get_bindings_starting_with_keys('')
        self.assertEqual(len(key_bindings), 1)
        self.assertEqual(key_bindings[0].keys, ('c-s',))


class TestFormatTextProcessor(unittest.TestCase):
    def setUp(self):
        self.format_text_processor = widgets.FormatTextProcessor()

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
        text_input.fragments = [
            ('',
             ('<style fg="black">[tab]</style>text1'
              '<style fg="red">[up]</style>text2'
              '<style fg="blue">[down]</style>text3')
        )]
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
