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


@Condition
def doc_section_visible():
    app = get_app()
    return getattr(app, 'show_doc')


@Condition
def help_section_visible():
    app = get_app()
    return getattr(app, 'show_help')


@Condition
def output_section_visible():
    app = get_app()
    return app.show_output


@Condition
def is_multi_column():
    app = get_app()
    return getattr(app, 'multi_column', False)


@Condition
def is_one_column():
    app = get_app()
    return not getattr(app, 'multi_column', False)


@Condition
def doc_window_has_focus():
    "Only activate these key bindings if doc window has focus."
    app = get_app()
    return app.current_buffer.name == 'doc_buffer'


@Condition
def search_input_has_focus():
    "Only activate these key bindings if doc window search has focus."
    app = get_app()
    return app.layout.current_window.style == 'class:search-toolbar'


@Condition
def input_buffer_has_focus():
    "Only activate these key bindings if input buffer has focus."
    app = get_app()
    return app.current_buffer.name == 'input_buffer'


@Condition
def is_history_mode():
    """Only activate these key bindings if input buffer has focus
       and history_mode is on """
    buffer = get_app().current_buffer
    return buffer.name == 'input_buffer' and buffer.history_mode


@Condition
def is_debug_mode():
    """Only activate these key bindings if input buffer has focus
       and history_mode is on """
    app = get_app()
    return app.debug
