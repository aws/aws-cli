# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from __future__ import unicode_literals
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.layout import Layout, FloatContainer, Float
from prompt_toolkit.layout.controls import UIControl, UIContent
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.containers import ScrollOffsets, Window


def select_menu(items, display_format=None, max_height=10):
    """ Presents a list of options and allows the user to select one.

    This presents a static list of options and prompts the user to select one.
    This is similar to a completion menu but is different in that it does not
    allow a user to type and the returned value is always a member of the list.

    :type items: list
    :param list: The list of items to be selected from. If this list contains
    elements that are not strings the display_format option must be specified.

    :type display_format: Callable[[Any], str]
    :param display_format: A callable that takes a single element from the
    items list as input and returns a string used to represent the item in the
    menu.

    :type max_height: int
    :param max_height: The max number of items to show in the list at a time.

    :returns: The selected element from the items list.
    """
    app_bindings = KeyBindings()

    @app_bindings.add('c-c')
    def exit_app(event):
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    min_height = min(max_height, len(items))
    menu_window = Window(
        SelectionMenuControl(items, display_format=display_format),
        always_hide_cursor=False,
        height=Dimension(min=min_height, max=min_height),
        scroll_offsets=ScrollOffsets(),
        right_margins=[ScrollbarMargin()],
    )

    # Using a FloatContainer was the only way I was able to succesfully
    # limit the height and width of the window.
    content = FloatContainer(
        Window(height=Dimension(min=min_height, max=min_height)),
        [Float(menu_window, top=0, left=0)])
    app = Application(
        layout=Layout(content),
        key_bindings=app_bindings,
        erase_when_done=True,
    )
    return app.run()


def _trim_text(text, max_width):
    """
    Trim the text to `max_width`, append dots when the text is too long.
    Returns (text, width) tuple.
    """
    width = get_cwidth(text)

    # When the text is too wide, trim it.
    if width > max_width:
        # When there are no double width characters, just use slice operation.
        if len(text) == width:
            trimmed_text = (text[:max(1, max_width - 3)] + '...')[:max_width]
            return trimmed_text, len(trimmed_text)

        # Otherwise, loop until we have the desired width. (Rather
        # inefficient, but ok for now.)
        else:
            trimmed_text = ''
            for c in text:
                if get_cwidth(trimmed_text + c) <= max_width - 3:
                    trimmed_text += c
            trimmed_text += '...'

            return (trimmed_text, get_cwidth(trimmed_text))
    else:
        return text, width


class SelectionMenuControl(UIControl):
    MIN_WIDTH = 7
    # The char width overhead of formatting the text into the menu

    def __init__(self, items, display_format=None, cursor='>'):
        self._items = items
        self._selection = 0
        self._cursor = cursor
        self._display_format = display_format
        self._format_overhead = 3 + len(cursor)

    def _get_items(self):
        if callable(self._items):
            self._items = self._items()
        return self._items

    def is_focusable(self):
        return True

    def preferred_width(self, max_width):
        items = self._get_items()
        if self._display_format:
            items = (self._display_format(i) for i in items)
        max_item_width = max(get_cwidth(i) for i in items)
        max_item_width += self._format_overhead
        if max_item_width < self.MIN_WIDTH:
            max_item_width = self.MIN_WIDTH
        return min(max_width, max_item_width)

    def preferred_height(self, width, max_height, wrap_lines, get_line_prefix):
        return min(max_height, len(self._get_items()))

    def _menu_item_fragment(self, item, is_selected, menu_width):
        if is_selected:
            cursor = self._cursor
            style_str = 'class:completion-menu.completion.current'
        else:
            cursor = ' ' * len(self._cursor)
            style_str = 'class:completion-menu.completion'

        if self._display_format:
            item = self._display_format(item)

        text, tw = _trim_text(item, menu_width - self._format_overhead)
        padding = ' ' * (menu_width - self._format_overhead - tw)
        return [(style_str, '%s %s%s  ' % (cursor, text, padding))]

    def create_content(self, width, height):
        def get_line(i):
            item = self._get_items()[i]
            is_selected = (i == self._selection)
            return self._menu_item_fragment(item, is_selected, width)

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=self._selection or 0),
            line_count=len(self._get_items())
        )

    def _move_cursor(self, delta):
        self._selection += delta

        num_items = len(self._get_items())
        if self._selection >= num_items:
            self._selection = 0
        elif self._selection < 0:
            self._selection = num_items - 1

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add('up')
        def move_up(event):
            self._move_cursor(-1)

        @kb.add('down')
        def move_down(event):
            self._move_cursor(1)

        @kb.add('enter')
        def app_result(event):
            result = self._get_items()[self._selection]
            event.app.exit(result=result)

        return kb


class CollapsableSelectionMenuControl(SelectionMenuControl):
    """Menu that collapses to text with selection when loses focus"""
    def __init__(self, items, display_format=None, cursor='>',
                 selection_capture_buffer=None, on_toggle=None):
        super().__init__(items, display_format=display_format, cursor=cursor)
        if not selection_capture_buffer:
            selection_capture_buffer = Buffer()
        self.buffer = selection_capture_buffer
        self._has_ever_entered_select_menu = False
        self.on_toggle = on_toggle

    def create_content(self, width, height):
        if get_app().layout.has_focus(self):
            self._has_ever_entered_select_menu = True
            return super().create_content(width, height)
        else:
            def get_line(i):
                content = ''
                if self._has_ever_entered_select_menu:
                    content = self._get_items()[self._selection]
                return [('', content)]

            return UIContent(get_line=get_line, line_count=1)

    def preferred_height(self, width, max_height, wrap_lines,
                         get_line_prefix):
        if get_app().layout.has_focus(self):
            return super().preferred_height(
                width, max_height, wrap_lines, get_line_prefix)
        else:
            return 1

    def _get_items(self):
        items = super()._get_items()
        # Initialize buffer selection text if it had not been set previously
        # (e.g. it was the first time items were retrieved)
        if not self.buffer.text:
            self.buffer.text = items[self._selection]
        return items

    def _move_cursor(self, delta):
        super()._move_cursor(delta)
        self.buffer.text = self._get_items()[self._selection]
        if callable(self.on_toggle):
            self.on_toggle(self.buffer.text)

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add('up')
        def move_up(event):
            self._move_cursor(-1)

        @kb.add('down')
        def move_down(event):
            self._move_cursor(1)

        return kb
