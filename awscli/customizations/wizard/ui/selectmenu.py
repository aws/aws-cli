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
from prompt_toolkit.key_binding.key_bindings import (
    KeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout import Float, FloatContainer, Layout
from prompt_toolkit.layout.containers import HSplit, ScrollOffsets, Window
from prompt_toolkit.layout.controls import BufferControl, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.utils import get_cwidth

SEARCH_PROMPT = 'Search: '


def select_menu(
    items,
    display_format=None,
    max_height=10,
    enable_filter=False,
    no_results_message=None,
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
    :param enable_filter: Show a search bar above the menu that lets the user
    narrow the list down by typing.

    :type no_results_message: str
    :param no_results_message: Message to show when the filter matches no
    items. Only used when ``enable_filter`` is set.

    :returns: The selected element from the items list.
    """
    if callable(items):
        items = items()

    app_bindings = KeyBindings()

    @app_bindings.add('c-c')
    def exit_app(event):
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    if enable_filter:
        menu_control = FilterableSelectionMenuControl(
            items,
            display_format=display_format,
            no_results_message=no_results_message,
        )
    else:
        menu_control = SelectionMenuControl(
            items,
            display_format=display_format,
        )

    menu_height = min(max_height, len(items))
    menu_window = Window(
        menu_control,
        # The cursor belongs in the search bar when filtering is enabled.
        always_hide_cursor=enable_filter,
        height=Dimension(min=menu_height, max=menu_height),
        scroll_offsets=ScrollOffsets(),
        right_margins=[ScrollbarMargin()],
    )

    if enable_filter:
        # The search bar takes up an extra line above the menu. Menu
        # navigation is bound at the application level because the search
        # buffer, not the menu, holds the focus.
        search_window = Window(
            BufferControl(buffer=menu_control.filter_buffer),
            height=Dimension.exact(1),
            get_line_prefix=lambda line_number, wrap_count: [
                ('class:filter', SEARCH_PROMPT)
            ],
        )
        float_content = HSplit([search_window, menu_window])
        focused_element = search_window
        min_height = menu_height + 1
        key_bindings = merge_key_bindings(
            [app_bindings, menu_control.get_key_bindings()]
        )
    else:
        float_content = menu_window
        focused_element = None
        min_height = menu_height
        key_bindings = app_bindings

    # Using a FloatContainer was the only way I was able to succesfully
    # limit the height and width of the window.
    content = FloatContainer(
        Window(height=Dimension(min=min_height, max=min_height)),
        [Float(float_content, top=0, left=0)],
    )
    app = Application(
        layout=Layout(content, focused_element=focused_element),
        key_bindings=key_bindings,
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

    def _display_text(self, item):
        if self._display_format:
            return self._display_format(item)
        return item

    def preferred_width(self, max_width):
        items = self._get_items()
        widths = [get_cwidth(self._display_text(i)) for i in items]
        max_item_width = max(widths, default=0)
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
        return [(style_str, f'{cursor} {text}{padding}  ')]

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
    """Menu that supports filtering its items with a search buffer.

    The search text is stored in a ``prompt_toolkit`` ``Buffer``. This means
    all text editing behavior (unicode input, bracketed pastes, cursor
    movement and the standard readline shortcuts such as ``Ctrl-U`` and
    ``Ctrl-W``) is handled by ``prompt_toolkit`` instead of being
    reimplemented here.
    """

    DEFAULT_NO_RESULTS_MESSAGE = 'No matching items found'

    def __init__(
        self,
        items,
        display_format=None,
        cursor='>',
        no_results_message=None,
        filter_buffer=None,
    ):
        super().__init__(items, display_format=display_format, cursor=cursor)
        self._no_results_message = (
            no_results_message or self.DEFAULT_NO_RESULTS_MESSAGE
        )
        self._filtered_items = None
        if filter_buffer is None:
            filter_buffer = Buffer(multiline=False)
        self.filter_buffer = filter_buffer
        self.filter_buffer.on_text_changed += self._on_filter_text_changed

    @property
    def filter_text(self):
        return self.filter_buffer.text

    def _get_items(self):
        """Return the items matching the current filter text."""
        if self._filtered_items is None:
            self._filtered_items = self._filter_items(super()._get_items())
        return self._filtered_items

    def _filter_items(self, items):
        filter_text = self.filter_text.strip().lower()
        if not filter_text:
            return list(items)
        return [
            item
            for item in items
            if filter_text in str(self._display_text(item)).lower()
        ]

    def _on_filter_text_changed(self, buffer=None):
        # Keep the previously highlighted item selected when it survives the
        # new filter, otherwise fall back to the first match. The previous
        # selection is read from the cached list because it still reflects
        # the filter text from before this change.
        previously_selected = None
        if self._filtered_items and self._selection < len(
            self._filtered_items
        ):
            previously_selected = self._filtered_items[self._selection]
        self._filtered_items = None
        self._selection = 0
        if previously_selected is not None:
            for i, item in enumerate(self._get_items()):
                if item == previously_selected:
                    self._selection = i
                    break

    def selected_item(self):
        """The highlighted item, or ``None`` when nothing matches the filter."""
        items = self._get_items()
        if not items:
            return None
        if self._selection >= len(items):
            self._selection = 0
        return items[self._selection]

    def move_selection(self, delta):
        if self._get_items():
            self._move_cursor(delta)

    def preferred_width(self, max_width):
        width = max(
            super().preferred_width(max_width),
            get_cwidth(self._no_results_message) + self._format_overhead,
        )
        return min(max_width, width)

    def preferred_height(self, width, max_height, wrap_lines, get_line_prefix):
        return min(max_height, max(1, len(self._get_items())))

    def create_content(self, width, height):
        if self._get_items():
            return super().create_content(width, height)

        def get_line(i):
            if i == 0:
                return [('class:no-results', f' {self._no_results_message}')]
            return [('', '')]

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=0),
            line_count=1,
        )

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add('up')
        def move_up(event):
            self.move_selection(-1)

        @kb.add('down')
        def move_down(event):
            self.move_selection(1)

        @kb.add('enter')
        def app_result(event):
            selected = self.selected_item()
            if selected is not None:
                event.app.exit(result=selected)

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
