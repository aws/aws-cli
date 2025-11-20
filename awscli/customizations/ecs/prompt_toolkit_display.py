import asyncio
import re

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, ScrollablePane, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame


def _get_visual_line_length(line):
    """Get the visual length of a line, excluding ANSI escape codes."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', line))


class Display:
    def __init__(self):
        self.control = FormattedTextControl(text="")
        self.window = ScrollablePane(
            Window(
                content=self.control, wrap_lines=True, dont_extend_width=False
            ),
            show_scrollbar=True,
        )
        self.status_control = FormattedTextControl(
            text="up/down to scroll, q to quit"
        )
        self.content_lines = 0
        self.raw_text = ""
        kb = KeyBindings()

        @kb.add('q')
        @kb.add('c-c')
        def quit_app(event):
            event.app.exit()

        @kb.add('up')
        def scroll_up(event):
            if self.window.vertical_scroll > 0:
                self.window.vertical_scroll -= 1

        @kb.add('down')
        def scroll_down(event):
            # Frame top, frame bottom, status bar
            window_height = event.app.output.get_size().rows - 3

            # Account for frame borders and scrollbar
            window_width = event.app.output.get_size().columns - 4
            total_display_lines = 0

            for line in self.raw_text.split('\n'):
                visual_length = _get_visual_line_length(line)
                if visual_length == 0:
                    total_display_lines += 1
                else:
                    total_display_lines += max(
                        1, (visual_length + window_width - 1) // window_width
                    )

            max_scroll = max(0, total_display_lines - window_height)
            if self.window.vertical_scroll < max_scroll:
                self.window.vertical_scroll += 1

        self.app = Application(
            layout=Layout(
                HSplit(
                    [
                        Frame(self.window),
                        Window(content=self.status_control, height=1),
                    ]
                )
            ),
            key_bindings=kb,
            full_screen=True,
        )

    def display(self, text, status_text=""):
        """Update display with ANSI colored text."""
        self.raw_text = text
        self.control.text = ANSI(text)
        self.content_lines = len(text.split('\n'))

        self._validate_scroll_position()

        if status_text:
            self.status_control.text = status_text
        self.app.invalidate()

    def _validate_scroll_position(self):
        """Ensure scroll position is valid for current content."""
        if not hasattr(self.app, 'output') or not self.app.output:
            return

        try:
            window_height = self.app.output.get_size().rows - 3
            window_width = self.app.output.get_size().columns - 4

            total_display_lines = 0
            for line in self.raw_text.split('\n'):
                visual_length = _get_visual_line_length(line)
                if visual_length == 0:
                    total_display_lines += 1
                else:
                    total_display_lines += max(
                        1, (visual_length + window_width - 1) // window_width
                    )

            max_scroll = max(0, total_display_lines - window_height)
            if self.window.vertical_scroll > max_scroll:
                self.window.vertical_scroll = max_scroll
        except (AttributeError, OSError):
            # If we can't determine terminal size, leave scroll position unchanged
            pass

    async def run(self):
        """Run the display app."""
        await self.app.run_async()
