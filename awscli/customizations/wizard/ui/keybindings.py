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


def get_default_keybindings():
    kb = KeyBindings()

    @kb.add('c-c')
    def exit_(event):
        event.app.exit()

    def submit_current_answer(event):
        current_buffer = event.app.current_buffer
        event.app.values[current_buffer.name] = current_buffer.text

    @kb.add('tab')
    @kb.add('enter')
    def next_prompt(event):
        submit_current_answer(event)
        event.app.layout.focus_next()

    @kb.add('s-tab')
    def last_prompt(event):
        submit_current_answer(event)
        event.app.layout.focus_last()

    return kb
