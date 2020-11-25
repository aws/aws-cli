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
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from awscli.customizations.wizard.ui.utils import get_ui_control_by_buffer_name


def get_default_keybindings():
    kb = KeyBindings()

    @kb.add(Keys.ControlC)
    def exit_(event):
        event.app.exit()

    def submit_current_answer(event):
        current_prompt = event.app.traverser.get_current_prompt()
        prompt_buffer = get_ui_control_by_buffer_name(
            event.app.layout, current_prompt).buffer
        event.app.traverser.submit_prompt_answer(prompt_buffer.text)

    @kb.add(Keys.Tab)
    @kb.add(Keys.Enter)
    def next_prompt(event):
        submit_current_answer(event)
        next_prompt = event.app.traverser.next_prompt()
        layout = event.app.layout
        next_control = get_ui_control_by_buffer_name(layout, next_prompt)
        layout.focus(next_control)

    @kb.add(Keys.BackTab)
    def previous_prompt(event):
        submit_current_answer(event)
        previous_prompt = event.app.traverser.previous_prompt()
        layout = event.app.layout
        previous_control = get_ui_control_by_buffer_name(
            layout, previous_prompt)
        layout.focus(previous_control)

    return kb
