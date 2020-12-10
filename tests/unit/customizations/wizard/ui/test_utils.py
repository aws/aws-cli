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

from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout

from awscli.customizations.wizard.app import WizardTraverser
from awscli.customizations.wizard.ui.utils import (
    get_ui_control_by_buffer_name, move_to_previous_prompt
)


class TestGetUIControlByName(unittest.TestCase):
    def test_get_ui_control_by_name(self):
        layout = mock.Mock(Layout)
        desired_ui_control = mock.Mock()
        desired_ui_control.buffer.name = 'desired-buffer'
        other_ui_control = mock.Mock()
        other_ui_control.buffer.name = 'different-name'
        layout.find_all_controls.return_value = [
            object(),  # Does not have a buffer property
            other_ui_control,
            desired_ui_control
        ]
        self.assertIs(
            get_ui_control_by_buffer_name(layout, 'desired-buffer'),
            desired_ui_control
        )

    def test_raises_error_when_no_matching_ui_control_found(self):
        layout = mock.Mock(Layout)
        layout.find_all_controls.return_value = []
        with self.assertRaises(ValueError):
            get_ui_control_by_buffer_name(layout, 'buffer-does-not-exist')


class TestMoveToPreviousPrompt(unittest.TestCase):
    def test_move_to_previous_prompt(self):
        app = mock.Mock(Application)
        app.layout = mock.Mock(Layout)
        previous_control = mock.Mock()
        previous_control.buffer.name = 'previous'
        app.layout.find_all_controls.return_value = [
            previous_control,
        ]
        app.traverser = mock.Mock(WizardTraverser)
        app.traverser.previous_prompt.return_value = 'previous'

        move_to_previous_prompt(app)
        app.layout.focus.assert_called_with(previous_control)
