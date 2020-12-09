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
from awscli.testutils import unittest, mock

from prompt_toolkit.layout import walk
from prompt_toolkit.application import DummyApplication

from awscli.customizations.wizard.ui.layout import (
    RunWizardDialog, WizardErrorBar
)


class TestRunWizardDialog(unittest.TestCase):
    def get_title_text(self, dialog):
        container = dialog.container
        frame_label = self.get_child_containers(container, 'frame.label')[0]
        # Frame label texts are wrapped in a couple of lambdas that need to be
        # unrolled.
        return self._build_text_from_ui_control(frame_label.content.text()())

    def get_button_texts(self, dialog):
        container = dialog.container
        button_texts = []
        for button in self.get_child_containers(container, 'button'):
            button_texts.append(
                self._build_text_from_ui_control(button.content.text)
            )
        return button_texts

    def get_child_containers(self, container, with_style_cls=None):
        child_containers = []
        for child_container in walk(container):
            if with_style_cls:
                if self._matches_style_cls(child_container, with_style_cls):
                    child_containers.append(child_container)
            else:
                child_containers.append(child_container)
        return child_containers

    def _matches_style_cls(self, container, style_cls):
        if hasattr(container, 'style'):
            container_style = container.style
            if callable(container_style):
                container_style = container_style()
            return f'class:{style_cls}' in container_style
        return False

    def _build_text_from_ui_control(self, ui_control_text):
        text = ''
        for text_component in ui_control_text():
            text += text_component[1]
        return text

    def test_from_done_section_definition(self):
        done_section = {}
        dialog = RunWizardDialog.from_done_section_definition(done_section)
        self.assertIn('Run wizard?', self.get_title_text(dialog))
        self.assertEqual(
            self.get_button_texts(dialog),
            [
                '<   Yes    >',
                '<   Back   >'
            ]
        )

    def test_override_title_in_done_section_definition(self):
        done_section = {
            'description': 'Override title'
        }
        dialog = RunWizardDialog.from_done_section_definition(done_section)
        self.assertIn('Override title', self.get_title_text(dialog))

    def test_override_button_list_in_done_section_definition(self):
        done_section = {
            'options': [
                'yes'
            ]
        }
        dialog = RunWizardDialog.from_done_section_definition(done_section)
        self.assertEqual(
            self.get_button_texts(dialog),
            [
                '<   Yes    >',
            ]
        )

    def test_override_button_text_in_done_section_definition(self):
        done_section = {
            'options': [
                {
                    'name': 'yes',
                    'description': 'Y'
                },
                {
                    'name': 'back',
                    'description': 'B'
                },
            ]
        }
        dialog = RunWizardDialog.from_done_section_definition(done_section)
        self.assertEqual(
            self.get_button_texts(dialog),
            [
                '<    Y     >',
                '<    B     >',
            ]
        )


class TestWizardErrorBar(unittest.TestCase):
    def setUp(self):
        self.error_bar = WizardErrorBar()
        self.app = DummyApplication()
        self.app.error_bar_visible = None
        self.get_app = mock.patch(
            'awscli.customizations.wizard.ui.layout.get_app',
            return_value=self.app)
        self.get_app.start()

    def tearDown(self):
        self.get_app.stop()

    def assert_error_bar_is_visible(self):
        self.assertTrue(self.error_bar.container.filter())

    def assert_error_bar_is_not_visible(self):
        self.assertFalse(self.error_bar.container.filter())

    def get_error_bar_message(self):
        return self.get_error_bar_buffer().text

    def get_error_bar_buffer(self):
        for child in walk(self.error_bar.container, skip_hidden=True):
            if hasattr(child, 'content') and \
                    hasattr(child.content, 'buffer') and \
                    child.content.buffer.name == 'error_bar':
                return child.content.buffer
        return None

    def test_visible_when_exception(self):
        self.error_bar.display_error(Exception('Error message'))
        self.assert_error_bar_is_visible()
        self.assertIn('Error message', self.get_error_bar_message())

    def test_not_visible_by_default(self):
        self.assert_error_bar_is_not_visible()

    def test_can_clear_error_bar(self):
        self.error_bar.display_error(Exception('Error message'))
        self.assert_error_bar_is_visible()
        self.error_bar.clear()
        self.assert_error_bar_is_not_visible()

    def test_can_override_existing_error(self):
        self.error_bar.display_error(Exception('Original'))
        self.error_bar.display_error(Exception('Override'))
        error_bar_message = self.get_error_bar_message()
        self.assertNotIn('Original', error_bar_message)
        self.assertIn('Override', error_bar_message)
