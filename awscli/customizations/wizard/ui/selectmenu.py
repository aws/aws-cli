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
from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout import Float, FloatContainer, Layout
from prompt_toolkit.layout.containers import ScrollOffsets, Window
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.utils import get_cwidth


def select_menu(
    items, display_format=None, max_height=10, enable_filter=False,
    no_results_message=None
):
    """Presents a list of options and allows the user to select one.

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

    :type enable_filter: bool
    :param enable_filter: Enable keyboard filtering of items.

    :type no_results_message: str
    :param no_results_message: Message to show when filtering returns no results.

    :returns: The selected element from the items list.
    """
    app_bindings = KeyBindings()

    @app_bindings.add('c-c')
    def exit_app(event):
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    min_height = min(max_height, len(items))
    if enable_filter:
        # Add 1 to height for filter line
        min_height = min(max_height + 1, len(items) + 1)
        menu_control = FilterableSelectionMenuControl(
            items, display_format=display_format,
            no_results_message=no_results_message
        )
    else:
        menu_control = SelectionMenuControl(
            items, display_format=display_format
        )

    menu_window = Window(
        menu_control,
        always_hide_cursor=False,
        height=Dimension(min=min_height, max=min_height),
        scroll_offsets=ScrollOffsets(),
        right_margins=[ScrollbarMargin()],
    )

    # Using a FloatContainer was the only way I was able to succesfully
    # limit the height and width of the window.
    content = FloatContainer(
        Window(height=Dimension(min=min_height, max=min_height)),
        [Float(menu_window, top=0, left=0)],
    )
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
            trimmed_text = (text[: max(1, max_width - 3)] + '...')[:max_width]
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
        if not items:
            return self.MIN_WIDTH
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
            is_selected = i == self._selection
            return self._menu_item_fragment(item, is_selected, width)

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=self._selection or 0),
            line_count=len(self._get_items()),
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


class FilterableSelectionMenuControl(SelectionMenuControl):
    """Menu that supports keyboard filtering of items"""

    def __init__(self, items, display_format=None, cursor='>', no_results_message=None):
        super().__init__(items, display_format=display_format, cursor=cursor)
        self._filter_text = ''
        self._filtered_items = items if items else []
        self._all_items = items if items else []
        self._filter_enabled = True
        self._no_results_message = no_results_message or 'No matching items found'

    def _get_items(self):
        if callable(self._all_items):
            self._all_items = self._all_items()
        return self._filtered_items

    def preferred_width(self, max_width):
        # Ensure minimum width for search display
        min_search_width = max(20, len("Search: " + self._filter_text) + 5)

        # Get width from filtered items
        items = self._filtered_items
        if not items:
            # Width for no results message
            no_results_width = get_cwidth(self._no_results_message) + 4
            return max(no_results_width, min_search_width)

        if self._display_format:
            items_display = [self._display_format(i) for i in items]
        else:
            items_display = [str(i) for i in items]

        if items_display:
            max_item_width = max(get_cwidth(i) for i in items_display)
            max_item_width += self._format_overhead
        else:
            max_item_width = self.MIN_WIDTH

        max_item_width = max(max_item_width, min_search_width)

        if max_item_width < self.MIN_WIDTH:
            max_item_width = self.MIN_WIDTH
        return min(max_width, max_item_width)

    def _update_filtered_items(self):
        """Update the filtered items based on the current filter text"""
        if not self._filter_text:
            self._filtered_items = self._all_items
        else:
            filter_lower = self._filter_text.lower()
            self._filtered_items = [
                item
                for item in self._all_items
                if filter_lower
                in (
                    self._display_format(item)
                    if self._display_format
                    else str(item)
                ).lower()
            ]

        # Reset selection if it's out of bounds
        if self._selection >= len(self._filtered_items):
            self._selection = 0

    def preferred_height(self, width, max_height, wrap_lines, get_line_prefix):
        # Add 1 extra line for the filter display
        return min(max_height, len(self._get_items()) + 1)

    def create_content(self, width, height):
        def get_line(i):
            # First line shows the filter
            if i == 0:
                filter_display = (
                    f"Search: {self._filter_text}_"
                    if self._filter_enabled
                    else f"Search: {self._filter_text}"
                )
                return [('class:filter', filter_display)]

            # Show "No results" message if filtered items is empty
            if not self._filtered_items:
                if i == 1:
                    return [
                        ('class:no-results', f'  {self._no_results_message}')
                    ]
                return [('', '')]

            # Adjust for the filter line
            item_index = i - 1
            if item_index >= len(self._filtered_items):
                return [('', '')]

            item = self._filtered_items[item_index]
            is_selected = item_index == self._selection
            return self._menu_item_fragment(item, is_selected, width)

        # Ensure at least 2 lines (search + no results or items)
        line_count = max(2, len(self._filtered_items) + 1)
        cursor_y = self._selection + 1 if self._filtered_items else 0

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=cursor_y),
            line_count=line_count,
        )

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add('up')
        def move_up(event):
            if len(self._filtered_items) > 0:
                self._move_cursor(-1)

        @kb.add('down')
        def move_down(event):
            if len(self._filtered_items) > 0:
                self._move_cursor(1)

        @kb.add('enter')
        def app_result(event):
            if len(self._filtered_items) > 0:
                result = self._filtered_items[self._selection]
                event.app.exit(result=result)

        @kb.add('backspace')
        def delete_char(event):
            if self._filter_text:
                self._filter_text = self._filter_text[:-1]
                self._update_filtered_items()

        @kb.add('c-u')
        def clear_filter(event):
            self._filter_text = ''
            self._update_filtered_items()

        # Add support for typing any character
        from string import printable

        for char in printable:
            if char not in ('\n', '\r', '\t'):

                @kb.add(char)
                def add_char(event, c=char):
                    self._filter_text += c
                    self._update_filtered_items()

        return kb


class CollapsableSelectionMenuControl(SelectionMenuControl):
    """Menu that collapses to text with selection when loses focus"""

    def __init__(
        self,
        items,
        display_format=None,
        cursor='>',
        selection_capture_buffer=None,
        on_toggle=None,
    ):
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

    def preferred_height(self, width, max_height, wrap_lines, get_line_prefix):
        if get_app().layout.has_focus(self):
            return super().preferred_height(
                width, max_height, wrap_lines, get_line_prefix
            )
        else:
            return 1

    def _get_items(self):
        items = super()._get_items()
        # Initialize buffer selection text if it had not been set previously
        # (e.g. it was the first time items were retrieved)
        if items is None:
            return ['']
        if not self.buffer.text:
            self.buffer.text = items[self._selection]
            if callable(self.on_toggle):
                self.on_toggle(self.buffer.text)
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
