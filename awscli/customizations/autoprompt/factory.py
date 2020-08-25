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

from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Float, FloatContainer, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout, ConditionalContainer
from prompt_toolkit.layout.menus import CompletionsMenu, MultiColumnCompletionsMenu
from prompt_toolkit.layout.processors import (
    BeforeInput, Processor, Transformation)
from prompt_toolkit.widgets import HorizontalLine, SearchToolbar


@Condition
def doc_section_visible():
    app = get_app()
    return getattr(app, 'show_doc')


@Condition
def is_multi_column():
    app = get_app()
    return getattr(app, 'multi_column', False)


@Condition
def is_one_column():
    app = get_app()
    return not getattr(app, 'multi_column', False)


class PromptToolkitFactory:
    DIMENSIONS = {
        'doc_window_height_max': 40,
        'doc_window_height_pref': 30,
        'input_buffer_height_min': 10,
        'menu_height_max': 16,
        'menu_scroll_offset': 2,
        'toolbar_height_max': 2
    }

    def __init__(self, completer):
        self._completer = completer

    def create_input_buffer(self, on_text_changed_callback=None):
        return Buffer(name='input_buffer', completer=self._completer,
                      complete_while_typing=True,
                      on_text_changed=on_text_changed_callback)

    def create_doc_buffer(self):
        return Buffer(name='doc_buffer', read_only=True)

    def create_bottom_toolbar_buffer(self):
        return Buffer(name='bottom_toolbar_buffer', read_only=True)

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

    def create_bottom_toolbar_container(self, toolbar_buffer,
                                        toolbar_text=None):
        if toolbar_text is None:
            toolbar_text = ToolbarHelpText()
        window = Window(
            BufferControl(buffer=toolbar_buffer,
                          input_processors=[FormatTextProcessor()]),
            height=Dimension(max=self.DIMENSIONS['toolbar_height_max']),
            style='bg:#3b3b3b',
            wrap_lines=True
        )
        # The only way to "modify" a read-only buffer in prompt_toolkit is to
        # create a new `prompt_toolkit.document.Document`. A 'cursor_position'
        # of 0 ensures that we place the cursor at the beginning so that we see
        # the toolbar text that we expect to see.
        new_document = Document(
            text=toolbar_text.input_buffer_key_binding_text,
            cursor_position=0
        )
        toolbar_buffer.set_document(new_document, bypass_readonly=True)
        return window

    def create_search_field(self):
        return SearchToolbar()

    def create_layout(self, on_input_buffer_text_changed=None,
                      input_buffer_container=None, doc_window=None,
                      search_field=None, bottom_toolbar_container=None):
        # This is the main layout, which consists of:
        # - The main input buffer with completion menus floating on top of it.
        # - A separating line between the input buffer and the doc window.
        # - A doc window to hold documentation.
        # - A separating line between the doc window and the toolbar.
        # - A toolbar denoting key bindings.
        if input_buffer_container is None:
            input_buffer = \
                self.create_input_buffer(on_input_buffer_text_changed)
            input_buffer_container = \
                self.create_input_buffer_container(input_buffer)
        if doc_window is None:
            doc_buffer = self.create_doc_buffer()
            doc_window = self.create_doc_window(doc_buffer)
        if search_field is None:
            search_field = SearchToolbar()
        if bottom_toolbar_container is None:
            bottom_toolbar_buffer = self.create_bottom_toolbar_buffer()
            bottom_toolbar_container = \
                self.create_bottom_toolbar_container(bottom_toolbar_buffer)
        return Layout(
            HSplit(
                [
                    input_buffer_container,
                    ConditionalContainer(HorizontalLine(), doc_section_visible),
                    ConditionalContainer(doc_window, doc_section_visible),
                    HorizontalLine(),
                    search_field,
                    bottom_toolbar_container
                ]
            )
        )

    def create_key_bindings(self):
        return PromptToolkitKeyBindings()


class PromptToolkitKeyBindings:
    def __init__(self, keybindings=None, toolbar_text=None):
        if keybindings is None:
            keybindings = KeyBindings()
        self._kb = keybindings
        if toolbar_text is None:
            toolbar_text = ToolbarHelpText()
        self._toolbar_text = toolbar_text

        @Condition
        def _input_buffer_has_focus():
            "Only activate these key bindings if input buffer has focus."
            app = get_app()
            return app.current_buffer.name == 'input_buffer'

        @Condition
        def _doc_window_has_focus():
            "Only activate these key bindings if doc window has focus."
            app = get_app()
            return app.current_buffer.name == 'doc_buffer'

        @self._kb.add(Keys.Enter, filter=_input_buffer_has_focus)
        def _(event):
            buffer = event.app.current_buffer
            is_completing = getattr(buffer, 'complete_state', False)
            current_document = buffer.document
            if not is_completing:
                event.app.exit()
            else:
                # I didn't find better way to make a choice and close prompter
                # than reset buffer and change it to selected part
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

        @self._kb.add(Keys.F2)
        def _(event):
            current_buffer = event.app.current_buffer
            if current_buffer.name != 'input_buffer':
                layout = event.app.layout
                toolbar_buffer = layout.get_buffer_by_name(
                    'bottom_toolbar_buffer')
                input_buffer = layout.get_buffer_by_name('input_buffer')
                layout.focus(input_buffer)
                text = self._toolbar_text.input_buffer_key_binding_text
                new_document = Document(text=text, cursor_position=0)
                toolbar_buffer.set_document(new_document, bypass_readonly=True)
            event.app.show_doc = not getattr(event.app, 'show_doc')

        @self._kb.add(Keys.F3)
        def _(event):
            event.app.multi_column = not getattr(
                event.app, 'multi_column', True
            )

        @self._kb.add(Keys.ControlC)
        @self._kb.add(Keys.ControlD)
        def _(event):
            layout = event.app.layout
            input_buffer = layout.get_buffer_by_name('input_buffer')
            print(input_buffer.document.text)
            event.app.exit(exception=KeyboardInterrupt)

        @self._kb.add(Keys.F1, filter=doc_section_visible)
        @self._kb.add('q', filter=_doc_window_has_focus)
        def _(event):
            # It may make sense to add the 'Escape' key as a binding to move
            # the focus from the doc window to the input buffer. However, there
            # is a noticeable lag after pressing 'Escape', so I've left it out
            # for now.
            layout = event.app.layout
            toolbar_buffer = layout.get_buffer_by_name('bottom_toolbar_buffer')
            current_buffer = event.app.current_buffer
            if current_buffer.name == 'input_buffer':
                doc_buffer = layout.get_buffer_by_name('doc_buffer')
                event.app.layout.focus(doc_buffer)
                text = self._toolbar_text.doc_window_key_binding_text
            else:
                input_buffer = layout.get_buffer_by_name('input_buffer')
                layout.focus(input_buffer)
                text = self._toolbar_text.input_buffer_key_binding_text
            new_document = Document(text=text, cursor_position=0)
            toolbar_buffer.set_document(new_document, bypass_readonly=True)

        @self._kb.add('w', filter=_doc_window_has_focus)
        def _(event):
            # Scroll up one unit equal to the height of the doc window.
            # Note: The scroll isn't exactly equal to the height of the doc
            # window. As there doesn't appear to be a way to get the exact
            # height of the doc window, the next best we can do is to grab the
            # preferred height of the Window.
            window_height = event.app.layout.current_window.height.preferred
            event.app.current_buffer.cursor_up(window_height)

        @self._kb.add('z', filter=_doc_window_has_focus)
        def _(event):
            # Scroll down one unit equal to the height of the doc window.
            # Note: The scroll isn't exactly equal to the height of the doc
            # window. As there doesn't appear to be a way to get the exact
            # height of the doc window, the next best we can do is to grab the
            # preferred height of the Window.
            window_height = event.app.layout.current_window.height.preferred
            event.app.current_buffer.cursor_down(window_height)

        @self._kb.add('k', filter=_doc_window_has_focus)
        def _(event):
            # Scroll up one line in the doc window.
            event.app.layout.current_buffer.cursor_up(1)

        @self._kb.add('j', filter=_doc_window_has_focus)
        def _(event):
            # Scroll down one line in the doc window.
            event.app.layout.current_buffer.cursor_down(1)

        @self._kb.add('g', filter=_doc_window_has_focus)
        def _(event):
            # Go to top of the doc window.
            document = event.app.layout.current_buffer.document
            current_row = document.cursor_position_row
            # `cursor_up() throws an error if its input is < 1`
            if current_row >= 1:
                event.app.layout.current_buffer.cursor_up(current_row)

        @self._kb.add('G', filter=_doc_window_has_focus)
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


class FormatTextProcessor(Processor):
    """This Processor is used to transform formatted text into a useable
    format inside a ``prompt_toolkit.buffer.Buffer``.

    """
    def apply_transformation(self, text_input):
        # https://python-prompt-toolkit.readthedocs.io/en/master/pages/reference.html#module-prompt_toolkit.formatted_text
        fragments = to_formatted_text(
            HTML(fragment_list_to_text(text_input.fragments)))
        return Transformation(fragments)


class ToolbarHelpText:
    def __init__(self, style=None, spacing=None):
        if style is None:
            style = '<style fg="darkturquoise">'
        self._style = style
        if spacing is None:
            spacing = '    '
        self._spacing = spacing
        self.input_buffer_key_binding_text = (
            f'{self._style}[TAB]</style> Cycle Forward{self._spacing}'
            f'{self._style}[SHIFT+TAB]</style> Cycle Backward{self._spacing}'
            f'{self._style}[UP]</style> Cycle Forward{self._spacing}'
            f'{self._style}[DOWN]</style> Cycle Backward{self._spacing}'
            f'{self._style}[SPACE]</style> Autocomplete Choice{self._spacing}'
            f'{self._style}[ENTER]</style> Autocomplete Choice/Execute Command{self._spacing}'
            f'{self._style}[F1]</style> Focus on Docs{self._spacing}'
            f'{self._style}[F2]</style> Hide/Show on Docs{self._spacing}'
            f'{self._style}[F3]</style> One/Multi column prompt'
        )
        self.doc_window_key_binding_text = (
            f'{self._style}[/]</style> Search Forward{self._spacing}'
            f'{self._style}[?]</style> Search Backward{self._spacing}'
            f'{self._style}[n]</style> Find Next Match{self._spacing}'
            f'{self._style}[N]</style> Find Previous Match{self._spacing}'
            f'{self._style}[w]</style> Go Up a Page{self._spacing}'
            f'{self._style}[z]</style> Go Down a Page{self._spacing}'
            f'{self._style}[j]</style> Go Up a Line{self._spacing}'
            f'{self._style}[k]</style> Go Down a Line{self._spacing}'
            f'{self._style}[g]</style> Go to Top{self._spacing}'
            f'{self._style}[G]</style> Go to Bottom{self._spacing}'
            f'{self._style}[F1] or [q]</style> Focus on Input'
        )
