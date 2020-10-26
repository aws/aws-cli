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
import os

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Float, FloatContainer, HSplit, Window, VSplit
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout, ConditionalContainer
from prompt_toolkit.layout.menus import CompletionsMenu, MultiColumnCompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.widgets import HorizontalLine, SearchToolbar

from awscli.autoprompt.history import HistoryDriver, HistoryCompleter
from awscli.autoprompt.widgets import (
    HelpPanelWidget, ToolbarWidget, DebugPanelWidget
)
from awscli.autoprompt.filters import (
    is_one_column, is_multi_column, doc_section_visible,
    input_buffer_has_focus, doc_window_has_focus, is_history_mode
)


class PrompterKeyboardInterrupt(KeyboardInterrupt):
    pass


class CLIPromptBuffer(Buffer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completer = self.completer
        self._history_completer = HistoryCompleter(self)
        self.history_mode = False

    def switch_history_mode(self):
        self.history_mode = not self.history_mode
        if self.history_mode:
            self.completer = self._history_completer
            self.start_completion()
        else:
            self.completer = self._completer


class PromptToolkitFactory:
    DIMENSIONS = {
        'doc_window_height_max': 40,
        'doc_window_height_pref': 30,
        'input_buffer_height_min': 10,
        'menu_height_max': 16,
        'menu_scroll_offset': 2,
    }

    def __init__(self, completer):
        self._completer = completer

    def create_history(self):
        cache_dir = os.path.expanduser(
            os.path.join('~', '.aws', 'cli', 'cache'))
        history_filename = os.path.join(cache_dir, 'prompt_history.json')
        return HistoryDriver(history_filename)

    def create_input_buffer(self, on_text_changed_callback=None):
        history = self.create_history()
        return CLIPromptBuffer(
            name='input_buffer', completer=self._completer,
            history=history, complete_while_typing=True,
            on_text_changed=on_text_changed_callback)

    def create_doc_buffer(self):
        return Buffer(name='doc_buffer', read_only=True)

    def create_input_buffer_container(self, input_buffer):
        return FloatContainer(
            Window(
                BufferControl(
                    buffer=input_buffer,
                    input_processors=[BeforeInput('> aws ')]
                ),
                height=Dimension(
                    min=self.DIMENSIONS['input_buffer_height_min']
                ),
                wrap_lines=True
            ),
            [
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=MultiColumnCompletionsMenu(
                        extra_filter=is_multi_column
                    )
                ),
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(
                        extra_filter=is_one_column,
                        max_height=self.DIMENSIONS['menu_height_max'],
                        scroll_offset=self.DIMENSIONS['menu_scroll_offset']
                    )
                )
            ]
        )

    def create_doc_window(self, doc_buffer, search_field=None):
        if search_field is None:
            search_field = SearchToolbar()
        return Window(
            content=BufferControl(
                buffer=doc_buffer,
                search_buffer_control=search_field.control
            ),
            height=Dimension(
                max=self.DIMENSIONS['doc_window_height_max'],
                preferred=self.DIMENSIONS['doc_window_height_pref']
            ),
            wrap_lines=True
        )

    def create_search_field(self):
        return SearchToolbar()

    def create_layout(self, on_input_buffer_text_changed=None,
                      input_buffer_container=None, doc_window=None,
                      search_field=None):
        # This is the main layout, which consists of:
        # - The main input buffer with completion menus floating on top of it.
        # - A separating line between the input buffer and the doc window.
        # - A doc window to hold documentation.
        # - A separating line between the doc window and the toolbar.
        # - A toolbar denoting key bindings.
        # - A help panel
        # - A debug panel in case debug mode enabled
        if search_field is None:
            search_field = SearchToolbar()
        if input_buffer_container is None:
            input_buffer = \
                self.create_input_buffer(on_input_buffer_text_changed)
            input_buffer_container = \
                self.create_input_buffer_container(input_buffer)
        if doc_window is None:
            doc_buffer = self.create_doc_buffer()
            doc_window = self.create_doc_window(doc_buffer, search_field)
        return Layout(
            HSplit([
                VSplit([
                    HSplit([
                        input_buffer_container,
                        ConditionalContainer(HorizontalLine(),
                                             doc_section_visible),
                        ConditionalContainer(doc_window,
                                             doc_section_visible),
                    ]),
                    HelpPanelWidget(),
                    DebugPanelWidget(),
                ]),
                search_field,
                ToolbarWidget()
            ])
        )

    def create_key_bindings(self):
        return PromptToolkitKeyBindings()


class PromptToolkitKeyBindings:
    def __init__(self, keybindings=None):
        if keybindings is None:
            keybindings = KeyBindings()
        self._kb = keybindings

        @self._kb.add(Keys.Enter, filter=input_buffer_has_focus)
        def _(event):
            buffer = event.app.current_buffer
            is_completing = getattr(buffer, 'complete_state', False)
            current_document = buffer.document
            if not is_completing:
                buffer.append_to_history()
                event.app.exit()
            else:
                # I didn't find better way to make a choice and close prompter
                # than reset buffer and change it to selected part
                if buffer.history_mode:
                    buffer.switch_history_mode()
                buffer.cancel_completion()
                event.app.current_buffer.reset()
                updated_document = Document(
                    text=current_document.text,
                    cursor_position=current_document.cursor_position)
                buffer.set_document(updated_document)
                # If prompter suggested us something ended with slash and
                # started with 'file://' or 'fileb://' it should be path ended
                # with directory then we run completion again
                cur_word = current_document.get_word_under_cursor(WORD=True)
                if cur_word.endswith(os.sep) \
                        and cur_word.startswith(('file://', 'fileb://')):
                    buffer.start_completion()

        @self._kb.add(Keys.Escape, filter=is_history_mode)
        def _(event):
            buffer = event.app.current_buffer
            buffer.cancel_completion()
            buffer.switch_history_mode()

        @self._kb.add(' ', filter=is_history_mode)
        def _(event):
            """Exit from history mode if something was selected or
            just add space to the end of the text and keep suggesting"""
            buffer = event.app.current_buffer
            if (buffer.complete_state
                    and buffer.complete_state.current_completion):
                buffer.switch_history_mode()
            buffer.insert_text(' ')

        @self._kb.add(Keys.F3)
        def _(event):
            current_buffer = event.app.current_buffer
            if current_buffer.name != 'input_buffer':
                layout = event.app.layout
                input_buffer = layout.get_buffer_by_name('input_buffer')
                layout.focus(input_buffer)
            event.app.show_doc = not getattr(event.app, 'show_doc')

        @self._kb.add(Keys.F4)
        def _(event):
            event.app.multi_column = not getattr(
                event.app, 'multi_column', True
            )

        @self._kb.add(Keys.F1)
        def _(event):
            event.app.show_help = not event.app.show_help

        @self._kb.add(Keys.ControlR, filter=input_buffer_has_focus)
        def _(event):
            buffer = event.app.current_buffer
            buffer.cancel_completion()
            buffer.switch_history_mode()

        @self._kb.add(Keys.ControlC)
        @self._kb.add(Keys.ControlD)
        def _(event):
            layout = event.app.layout
            input_buffer = layout.get_buffer_by_name('input_buffer')
            text = f'> aws {input_buffer.document.text}'
            event.app.exit(exception=PrompterKeyboardInterrupt(text))

        @self._kb.add(Keys.F2, filter=doc_section_visible)
        @self._kb.add('q', filter=doc_window_has_focus)
        def _(event):
            # It may make sense to add the 'Escape' key as a binding to move
            # the focus from the doc window to the input buffer. However, there
            # is a noticeable lag after pressing 'Escape', so I've left it out
            # for now.
            layout = event.app.layout
            current_buffer = event.app.current_buffer
            if current_buffer.name == 'input_buffer':
                doc_buffer = layout.get_buffer_by_name('doc_buffer')
                event.app.layout.focus(doc_buffer)
            else:
                input_buffer = layout.get_buffer_by_name('input_buffer')
                layout.focus(input_buffer)

        @self._kb.add('w', filter=doc_window_has_focus)
        def _(event):
            # Scroll up one unit equal to the height of the doc window.
            # Note: The scroll isn't exactly equal to the height of the doc
            # window. As there doesn't appear to be a way to get the exact
            # height of the doc window, the next best we can do is to grab the
            # preferred height of the Window.
            window_height = event.app.layout.current_window.height.preferred
            event.app.current_buffer.cursor_up(window_height)

        @self._kb.add('z', filter=doc_window_has_focus)
        def _(event):
            # Scroll down one unit equal to the height of the doc window.
            # Note: The scroll isn't exactly equal to the height of the doc
            # window. As there doesn't appear to be a way to get the exact
            # height of the doc window, the next best we can do is to grab the
            # preferred height of the Window.
            window_height = event.app.layout.current_window.height.preferred
            event.app.current_buffer.cursor_down(window_height)

        @self._kb.add('k', filter=doc_window_has_focus)
        def _(event):
            # Scroll up one line in the doc window.
            event.app.layout.current_buffer.cursor_up(1)

        @self._kb.add('j', filter=doc_window_has_focus)
        def _(event):
            # Scroll down one line in the doc window.
            event.app.layout.current_buffer.cursor_down(1)

        @self._kb.add('g', filter=doc_window_has_focus)
        def _(event):
            # Go to top of the doc window.
            document = event.app.layout.current_buffer.document
            current_row = document.cursor_position_row
            # `cursor_up() throws an error if its input is < 1`
            if current_row >= 1:
                event.app.layout.current_buffer.cursor_up(current_row)

        @self._kb.add('G', filter=doc_window_has_focus)
        def _(event):
            # Go to bottom of the doc window.
            document = event.app.layout.current_buffer.document
            current_row = document.cursor_position_row
            num_rows = document.line_count
            lines_to_bottom_delta = num_rows - current_row
            event.app.layout.current_buffer.cursor_down(lines_to_bottom_delta)

    @property
    def keybindings(self):
        return self._kb
