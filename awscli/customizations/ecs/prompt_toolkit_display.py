import asyncio

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, ScrollablePane, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame


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
            window_height = (
                event.app.output.get_size().rows - 3
            )  # Frame top, frame bottom, status bar
            if self.window.vertical_scroll < max(
                0, self.content_lines - window_height
            ):
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
        self.control.text = ANSI(text)
        self.content_lines = len(text.split('\n'))
        if status_text:
            self.status_control.text = status_text
        self.app.invalidate()

    async def run(self):
        """Run the display app."""
        await self.app.run_async()
