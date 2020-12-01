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
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from awscli.customizations.wizard.ui.utils import get_ui_control_by_buffer_name


@Condition
def details_visible():
    return get_app().details_visible


@Condition
def prompt_has_details():
    return get_app().traverser.current_prompt_has_details()


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
        event.app.details_visible = False
        layout.focus(next_control)

    @kb.add(Keys.BackTab)
    def previous_prompt(event):
        submit_current_answer(event)
        previous_prompt = event.app.traverser.previous_prompt()
        layout = event.app.layout
        previous_control = get_ui_control_by_buffer_name(
            layout, previous_prompt)
        event.app.details_visible = False
        layout.focus(previous_control)

    @kb.add(Keys.F2)
    def focus_on_details_panel(event):
        if event.app.details_visible:
            layout = event.app.layout
            if layout.current_buffer and \
                    layout.current_buffer.name == 'details_buffer':
                current_prompt = event.app.traverser.get_current_prompt()
                current_control = get_ui_control_by_buffer_name(
                    layout, current_prompt)
                layout.focus(current_control)
            else:
                details_buffer = layout.get_buffer_by_name('details_buffer')
                layout.focus(details_buffer)

    @kb.add(Keys.F3, filter=prompt_has_details)
    def show_details(event):
        event.app.details_visible = not event.app.details_visible
        layout = event.app.layout
        current_prompt = event.app.traverser.get_current_prompt()
        current_control = get_ui_control_by_buffer_name(
            layout, current_prompt)
        if not event.app.details_visible:
            layout.focus(current_control)
        else:
            if callable(current_control.on_toggle):
                current_control.on_toggle(current_control.buffer.text)

    return kb
