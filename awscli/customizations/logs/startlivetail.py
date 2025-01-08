# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from enum import Enum
from functools import partial
from threading import Thread
import asyncio
import colorama
import contextlib
import json
import re
import signal
import sys
import time

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import (
    ANSI,
    to_formatted_text,
    fragment_list_to_text,
)
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Layout, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import Processor, Transformation

from awscli.compat import get_stdout_text_writer
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.utils import is_a_tty


DESCRIPTION = (
    "Starts a Live Tail streaming session for one or more log groups. "
    "A Live Tail session provides a near real-time streaming of log events "
    "as they are ingested into selected log groups. "
    "A session can go on for a maximum of 3 hours.\n\n"
    "By default, this command start a native tailing session "
    "where recent log events appear from the bottom, "
    "the log events are output as-is in Plain text.  You can run this command with --mode interactive, "
    "which starts an interactive tailing session. Interactive tailing provides the ability to "
    "highlight up to 5 terms in your logs. "
    "The severity codes are highlighted by default. The logs are output in JSON format if possible, "
    "but can be toggled to Plain text if desired. Interactive experience is disabled if --color is set to off, "
    "or if the output doesn't allow for color. \n\n"
    "You must have logs:StartLiveTail permission to perform this operation. "
    "If the log events matching the filters are more than 500 events per second, "
    "we sample the events to provide the real-time tailing experience.\n\n"
    "If you are using CloudWatch cross-account observability, "
    "you can use this operation in a monitoring account and start tailing on Log Group(s) "
    "present in the linked source accounts. "
    "For more information, see "
    "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html.\n\n"
    "Live Tail sessions incur charges by session usage time, per minute. "
    "For pricing details, please refer to "
    "https://aws.amazon.com/cloudwatch/pricing/."
)

LIST_SCHEMA = {"type": "array", "items": {"type": "string"}}

LOG_GROUP_IDENTIFIERS = {
    "name": "log-group-identifiers",
    "required": True,
    "positional_arg": False,
    "nargs": "+",
    "schema": LIST_SCHEMA,
    "help_text": (
        "The Log Group Identifiers are the ARNs for the CloudWatch Logs groups to tail. "
        "You can provide up to 10 Log Group Identifiers.\n\n"
        "Logs can be filtered by Log Stream(s) by providing  "
        "--log-stream-names or --log-stream-name-prefixes. "
        "If more than one Log Group is provided --log-stream-names and "
        "--log-stream-name-prefixes  is disabled. "
        "--log-stream-names and --log-stream-name-prefixes can't be provided simultaneously.\n\n"
        "Note -  The Log Group ARN must be in the following format. Replace REGION and "
        "ACCOUNT_ID with your Region and account ID. "
        "``arn:aws:logs:REGION :ACCOUNT_ID :log-group:LOG_GROUP_NAME``. A ``:*`` after the ARN is prohibited."
        "For more information about ARN format, "
        'see <a href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/iam-access-control-overview-cwl.html">CloudWatch Logs resources and operations</a>.'
    ),
}

LOG_STREAM_NAMES = {
    "name": "log-stream-names",
    "positional_arg": False,
    "nargs": "+",
    "schema": LIST_SCHEMA,
    "help_text": (
        "The list of stream names to filter logs by.\n\n This parameter cannot be "
        "specified when --log-stream-name-prefixes are also specified. "
        "This parameter cannot be specified when multiple log-group-identifiers are specified"
    ),
}

LOG_STREAM_NAME_PREFIXES = {
    "name": "log-stream-name-prefixes",
    "positional_arg": False,
    "nargs": "+",
    "schema": LIST_SCHEMA,
    "help_text": (
        "The prefix to filter logs by. Only events from log streams with names beginning "
        "with this prefix will be returned. \n\nThis parameter cannot be specified when "
        "--log-stream-names is also specified. This parameter cannot be specified when "
        "multiple log-group-identifiers are specified"
    ),
}

LOG_EVENT_FILTER_PATTERN = {
    "name": "log-event-filter-pattern",
    "positional_arg": False,
    "cli_type_name": "string",
    "help_text": (
        "The filter pattern to use. "
        'See <a href="https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html">Filter and Pattern Syntax</a> '
        "for details. If not provided, all the events are matched. "
        "This option can be used to include or exclude log events patterns.  "
        "Additionally, when multiple filter patterns are provided, they must be encapsulated by quotes."
    ),
}

MODE = {
    "name": "mode",
    "positional_arg": False,
    "default": "print-only",
    "choices": ["interactive", "print-only"],
    "help_text": (
        "The command support the following modes:\n\n"
        "<ul>"
        "<li> interative - "
        "Starts a Live Tail session in interactive mode. "
        "In an interactive session, you can highlight as many as five terms in the tailed logs. "
        "The severity codes are highlighted by default. Press h to enter the highlight "
        "mode and then type in the terms to be highlighted, "
        "one at a time, and press enter. Press c to clear the highlighted term(s). "
        "Press t to toggle formatting between JSON/Plain text. "
        "Press Esc to exit the Live Tail session. The interactive experience is disabled if you specify —color as off, "
        "or if coloring is not allowed by your output. "
        "Press up / down keys to scroll up or down between log events, "
        "use Ctrl + u / Ctrl + d to scroll faster. Press q to scroll to latest log events."
        "</li>"
        "<li> print-only - "
        "Starts a LiveTail session in print-only mode. "
        "In print-only mode logs are tailed and are printed as-is. This mode can be used "
        "in conjunction with other shell commands. "
        "</li>"
        "</ul>"
    ),
}


def signal_handler(printer, signum, frame):
    printer.interrupt_session = True


@contextlib.contextmanager
def handle_signal(printer):
    signal_list = [signal.SIGINT, signal.SIGTERM]
    if sys.platform != "win32":
        signal_list.append(signal.SIGPIPE)
    actual_signals = []
    for user_signal in signal_list:
        actual_signals.append(
            signal.signal(user_signal, partial(signal_handler, printer))
        )
    try:
        yield
    finally:
        for sig, user_signal in enumerate(signal_list):
            signal.signal(user_signal, actual_signals[sig])


MAX_KEYWORDS_ALLOWED = 5
COLOR_LIST = [
    colorama.Fore.CYAN,
    colorama.Fore.MAGENTA,
    colorama.Fore.BLUE,
    colorama.Fore.LIGHTYELLOW_EX,
    colorama.Fore.LIGHTGREEN_EX,
]


class ColorNotAllowedInInteractiveModeError(ParamValidationError):
    pass


class OutputFormat(Enum):
    JSON = "JSON"
    PLAIN_TEXT = "Plain text"


class InputState(Enum):
    HIGHLIGHT = "highlight"
    CLEAR = "clear"
    DISABLED = "disabled"


class LiveTailSessionMetadata:
    def __init__(self) -> None:
        self._session_start_time = time.time()
        self._is_sampled = False

    @property
    def session_start_time(self):
        return self._session_start_time

    @property
    def is_sampled(self):
        return self._is_sampled

    def update_metadata(self, session_metadata):
        self._is_sampled = session_metadata["sampled"]


class Keyword:
    def __init__(self, text: str, color=None):
        self._text = text.lower().strip()
        self._color = color or self._get_color()
        self._occurrence_count = 0
        self._regex_pattern = re.compile(re.escape(self._text))
        self._removal_regex_pattern = re.compile(
            re.escape(self._color + self._text + colorama.Style.RESET_ALL)
        )

    @property
    def text(self):
        return self._text

    @property
    def color(self):
        return self._color

    def _get_color(self):
        if self._text == "error":
            return colorama.Fore.RED
        elif self._text == "info":
            return colorama.Fore.GREEN
        elif self._text == "warn":
            return colorama.Fore.YELLOW

    def get_string_to_print(self):
        text_to_print = self._text
        if len(self._text) > 15:
            text_to_print = self._text[:10] + "..."
        return (
            self._color
            + text_to_print
            + colorama.Style.RESET_ALL
            + ": "
            + str(self._occurrence_count)
        )

    def _add_color_to_string(self, log_event: str, start, end):
        string_to_replace = log_event[start:end]
        return (
            log_event[:start]
            + self._color
            + string_to_replace
            + colorama.Style.RESET_ALL
            + log_event[end:]
        )

    def _remove_color_from_string(self, log_event: str, start, end):
        string_with_color = log_event[start:end]
        string_without_color = string_with_color.split(self._color)[-1].split(
            colorama.Style.RESET_ALL
        )[0]
        return log_event[:start] + string_without_color + log_event[end:]

    def highlight(self, log_event: str):
        matchings = list(self._regex_pattern.finditer(log_event.lower()))[::-1]
        self._occurrence_count += len(matchings)
        for match in matchings:
            log_event = self._add_color_to_string(
                log_event, match.start(), match.end()
            )

        return log_event

    def remove_highlighting(self, log_event: str):
        matchings = list(
            self._removal_regex_pattern.finditer(log_event.lower())
        )[::-1]
        self._occurrence_count -= len(matchings)
        for match in matchings:
            log_event = self._remove_color_from_string(
                log_event, match.start(), match.end()
            )

        return log_event


class LiveTailKeyBindings(KeyBindings):
    def __init__(
        self,
        ui,
        prompt_buffer: Buffer,
        output_buffer: Buffer,
        keywords_to_highlight: dict,
    ) -> None:
        super().__init__()
        self._ui = ui
        self._input_buffer = prompt_buffer
        self._input_state = InputState.DISABLED
        self._log_output_buffer = output_buffer
        self._available_colors = COLOR_LIST.copy()
        self._keywords_to_highlight = keywords_to_highlight
        self._is_exit_set = False
        self._attach_keybindings()

    @property
    def input_state(self):
        return self._input_state

    def _attach_keybindings(self):
        @Condition
        def is_input_disabled():
            return self._input_state == InputState.DISABLED

        @Condition
        def is_input_highlight():
            return self._input_state == InputState.HIGHLIGHT

        @Condition
        def is_input_clear():
            return self._input_state == InputState.CLEAR

        @Condition
        def is_prompt_active():
            return (
                get_app().layout.current_control
                == self._ui.prompt_buffer_control
            )

        @Condition
        def is_cursor_at_bottom():
            return self._log_output_buffer.cursor_position == len(
                self._log_output_buffer.text
            )

        @Condition
        def is_keyword_addition_allowed():
            return len(self._keywords_to_highlight) < MAX_KEYWORDS_ALLOWED

        @Condition
        def is_clear_keyword_allowed():
            return len(self._keywords_to_highlight) > 0

        @Condition
        def is_exit_set():
            return self._is_exit_set

        @self.add("<any>", filter=is_input_disabled)
        def _(event: KeyPressEvent):
            pass

        @self.add("<any>", filter=is_input_highlight)
        def _(event: KeyPressEvent):
            self._input_buffer.insert_text(event.data)

        @self.add("<any>", filter=is_input_clear)
        def _(event: KeyPressEvent):
            if event.data.isdigit():
                keyword_idx = int(event.data) - 1
                keywords = list(self._keywords_to_highlight.keys())
                if 0 <= keyword_idx < len(keywords):
                    removed_keyword = self._keywords_to_highlight.pop(
                        keywords[keyword_idx]
                    )
                    self._available_colors.insert(0, removed_keyword.color)
                    event.app.create_background_task(
                        self._ui.remove_term_from_buffer(removed_keyword)
                    )
                    self._reset(event)

        @self.add("h", filter=is_input_disabled & is_keyword_addition_allowed)
        def _(event: KeyPressEvent):
            self._input_state = InputState.HIGHLIGHT
            self._ui.update_bottom_toolbar(self._ui.HIGHLIGHT_INSTRUCTIONS)
            self._ui.update_quit_button(self._ui.EXIT_HIGHLIGHT)
            event.app.invalidate()

        @self.add("c", filter=is_input_disabled & is_clear_keyword_allowed)
        def _(event: KeyPressEvent):
            self._input_state = InputState.CLEAR

            clear_intructions = ""
            keyword_counter = 1
            for keyword in self._keywords_to_highlight.keys():
                clear_intructions += (
                    str(keyword_counter) + ": " + keyword + "    "
                )
                keyword_counter += 1
            clear_intructions += "ENTER: All"

            self._ui.update_bottom_toolbar(clear_intructions)
            self._ui.update_quit_button(self._ui.EXIT_CLEAR)
            event.app.invalidate()

        @self.add("t", filter=is_input_disabled)
        def _(event: KeyPressEvent):
            self._ui.toggle_formatting()
            self._ui.update_bottom_toolbar(self._ui.get_instructions())

        @self.add("q", filter=is_input_disabled & ~is_prompt_active)
        def _(event: KeyPressEvent):
            self._ui.handle_scrolling(False)
            event.app.layout.focus(self._input_buffer)

        @self.add("enter", filter=is_input_highlight)
        def _(event: KeyPressEvent):
            if (
                self._input_buffer.text.lower()
                not in self._keywords_to_highlight.keys()
                and len(self._input_buffer.text) > 0
            ):
                keyword_color = self._available_colors.pop(0)
                keyword = Keyword(self._input_buffer.text, keyword_color)
                self._keywords_to_highlight[keyword.text] = keyword
                event.app.create_background_task(
                    self._ui.highlight_term_in_buffer(keyword)
                )

            self._reset(event)

        @self.add("enter", filter=is_input_clear)
        def _(event: KeyPressEvent):
            for keyword in self._keywords_to_highlight.values():
                event.app.create_background_task(
                    self._ui.remove_term_from_buffer(keyword)
                )

            self._keywords_to_highlight.clear()
            self._available_colors = COLOR_LIST.copy()
            self._reset(event)

        @self.add("backspace")
        def _(event: KeyPressEvent):
            self._input_buffer.text = self._input_buffer.text[:-1]

        @self.add("escape", filter=~is_input_disabled)
        def _(event: KeyPressEvent):
            self._reset(event)

        @self.add("c-c", filter=is_prompt_active & ~is_exit_set)
        @self.add("escape", filter=is_input_disabled & ~is_exit_set)
        def _(event: KeyPressEvent):
            self._is_exit_set = True
            event.app.exit()

        @self.add("up", filter=is_prompt_active)
        def _(event: KeyPressEvent):
            event.app.layout.focus(self._log_output_buffer)
            self._ui.handle_scrolling(True)

        @self.add("c-u")
        def _(event: KeyPressEvent):
            if is_prompt_active():
                event.app.layout.focus(self._log_output_buffer)
                self._ui.handle_scrolling(True)
            else:
                self._log_output_buffer.cursor_up(20)

        @self.add("down", filter=is_cursor_at_bottom)
        def _(event: KeyPressEvent):
            self._ui.handle_scrolling(False)
            event.app.layout.focus(self._input_buffer)

        @self.add("c-d")
        def _(event: KeyPressEvent):
            if is_cursor_at_bottom():
                self._ui.handle_scrolling(False)
                event.app.layout.focus(self._input_buffer)
            else:
                self._log_output_buffer.cursor_down(20)

    def _reset(self, event):
        self._input_state = InputState.DISABLED
        self._ui.update_bottom_toolbar(self._ui.get_instructions())
        self._ui.update_quit_button(self._ui.EXIT_SESSION)
        self._input_buffer.reset()
        self._ui.update_metadata()
        event.app.invalidate()


class BaseLiveTailPrinter:
    def run(self):
        raise NotImplementedError()


class BaseLiveTailUI:
    def exit(self):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()


class LiveTailBuffer(Buffer):
    def __init__(self):
        super().__init__()
        self._pause_buffer = Buffer()

    @property
    def pause_buffer(self):
        return self._pause_buffer

    def add_text(self, data: str) -> bool:
        if not get_app().layout.has_focus(self):
            self.text += data
            self.cursor_position = len(self.text)
        else:
            self._pause_buffer.text += data


class InteractivePrinter(BaseLiveTailPrinter):
    _PROTECTED_KEYWORDS = [Keyword("ERROR"), Keyword("INFO"), Keyword("WARN")]

    def __init__(
        self,
        ui,
        output: LiveTailBuffer,
        log_events: list,
        session_metadata: LiveTailSessionMetadata,
        keywords_to_highlight: dict,
    ) -> None:
        self._ui = ui
        self._output = output
        self._log_events = log_events
        self._session_metadata = session_metadata
        self._log_events_displayed = 0
        self._is_sampled = False
        self._keywords_to_highlight = keywords_to_highlight
        self._format = OutputFormat.JSON
        colorama.init(autoreset=True, strip=False)

    @property
    def log_events_displayed(self):
        return self._log_events_displayed

    @property
    def is_sampled(self):
        return self._is_sampled

    @property
    def output_format(self):
        return self._format

    def toggle_formatting(self):
        self._format = (
            OutputFormat.PLAIN_TEXT
            if self._format == OutputFormat.JSON
            else OutputFormat.JSON
        )

    def _color_log_event(self, log_event: str):
        for keyword in (
            list(self._keywords_to_highlight.values())
            + self._PROTECTED_KEYWORDS
        ):
            log_event = keyword.highlight(log_event)

        return log_event

    def _format_log_event(self, log_event: str):
        if self._format == OutputFormat.JSON:
            try:
                log_event = json.loads(log_event)
                return json.dumps(log_event, indent=4)
            except json.decoder.JSONDecodeError:
                pass

        return log_event

    def _print_log_events(self):
        self._log_events_displayed = len(self._log_events)
        self._is_sampled = self._session_metadata.is_sampled
        self._ui.update_metadata()
        for log_event in self._log_events:
            log_event = self._format_log_event(log_event)
            self._output.add_text(self._color_log_event(log_event) + "\n")

        self._log_events.clear()

    async def run(self):
        while True:
            self._print_log_events()
            await asyncio.sleep(1)


class BufferControlColorProcessor(Processor):
    def apply_transformation(self, transformation_input):
        fragments = to_formatted_text(
            ANSI(fragment_list_to_text(transformation_input.fragments))
        )
        return Transformation(fragments)


class InteractiveUI(BaseLiveTailUI):
    EXIT_SESSION = "Esc: Exit"
    EXIT_HIGHLIGHT = "Esc: Exit Highlight"
    EXIT_CLEAR = "Ecs: Exit Clear"
    INSTRUCTIONS = "h: Highlight Terms (MAX 5)    c: Clear Highlighted Terms    t: Toggle Formatting ({}/{})    up/down: Scroll    ctrl+u/ctrl+d: Fast Scroll"
    HIGHLIGHT_INSTRUCTIONS = "Type Term and press ENTER"
    _MAX_LINE_COUNT = 1000

    def __init__(
        self,
        log_events,
        session_metadata: LiveTailSessionMetadata,
        app_output=None,
    ) -> None:
        self._log_events = log_events
        self._session_metadata = session_metadata
        self._keywords_to_highlight = {}
        self._output = LiveTailBuffer()
        self._is_scroll_active = False
        self._log_events_printer = InteractivePrinter(
            self,
            self._output,
            self._log_events,
            self._session_metadata,
            self._keywords_to_highlight,
        )
        self._create_ui(app_output)

    def _create_ui(self, app_output):
        prompt_buffer = Buffer()
        self._prompt_buffer_control = BufferControl(prompt_buffer)
        prompt_buffer_window = Window(self._prompt_buffer_control)
        prompt_text_window = Window(
            FormattedTextControl(">"), dont_extend_width=True, width=1
        )
        self._key_bindings = LiveTailKeyBindings(
            self, prompt_buffer, self._output, self._keywords_to_highlight
        )

        output_buffer_control = BufferControl(
            self._output, input_processors=[BufferControlColorProcessor()]
        )
        log_output_container = Window(output_buffer_control, wrap_lines=True)

        dashed_line_container = Window(height=1, char="-")
        metadata_container = self._create_metadata()
        bottom_toolbar_container = self._create_bottom_toolbar()

        containers = HSplit(
            [
                log_output_container,
                dashed_line_container,
                VSplit(
                    [
                        prompt_text_window,
                        prompt_buffer_window,
                    ],
                    height=1,
                ),
                metadata_container,
                bottom_toolbar_container,
            ]
        )
        layout = Layout(containers, prompt_buffer_window)

        self._application = Application(
            layout,
            key_bindings=self._key_bindings,
            refresh_interval=1,
            output=app_output,
        )

    @property
    def prompt_buffer_control(self):
        return self._prompt_buffer_control

    def _create_bottom_toolbar(self):
        self._quit_button = FormattedTextControl(self.EXIT_SESSION)
        self._bottom_toolbar = FormattedTextControl(self.get_instructions())

        return HSplit(
            [
                Window(
                    self._bottom_toolbar,
                    wrap_lines=True,
                    dont_extend_height=True,
                    height=Dimension(min=1),
                    char=" ",
                    style="class:bottom-toolbar.text",
                ),
                Window(
                    self._quit_button,
                    wrap_lines=True,
                    dont_extend_height=True,
                    height=Dimension(min=1),
                    style="class:bottom-toolbar.text",
                    align=WindowAlign.RIGHT,
                ),
            ]
        )

    def update_bottom_toolbar(self, new_text):
        self._bottom_toolbar.text = new_text

    def update_quit_button(self, new_text):
        self._quit_button.text = new_text

    def toggle_formatting(self):
        self._log_events_printer.toggle_formatting()

    def get_instructions(self):
        if self._log_events_printer.output_format == OutputFormat.JSON:
            instructions = self.INSTRUCTIONS.format(
                colorama.Fore.GREEN
                + OutputFormat.JSON.value
                + colorama.Style.RESET_ALL,
                OutputFormat.PLAIN_TEXT.value,
            )
        else:
            instructions = self.INSTRUCTIONS.format(
                OutputFormat.JSON.value,
                colorama.Fore.GREEN
                + OutputFormat.PLAIN_TEXT.value
                + colorama.Style.RESET_ALL,
            )

        if self._is_scroll_active:
            instructions += "    q: Scroll to latest"

        return ANSI(instructions)

    def handle_scrolling(self, is_scroll_active):
        self._is_scroll_active = is_scroll_active

        if not self._is_scroll_active:
            self._output.text += self._output.pause_buffer.text
            self._output.cursor_position = len(self._output.text)
            self._output.pause_buffer.reset()
            self._application.create_background_task(
                self._trim_buffer(self._output)
            )

        if self._key_bindings.input_state == InputState.DISABLED:
            self.update_bottom_toolbar(self.get_instructions())
            self._application.invalidate()

    def _create_metadata(self):
        self._metadata = FormattedTextControl(
            text="Highlighted Terms: {}, 0 events/sec, Sampled: No | 00:00:00"
        )
        return Window(
            self._metadata,
            wrap_lines=True,
            dont_extend_height=True,
            align=WindowAlign.RIGHT,
        )

    def update_metadata(self):
        current_time = time.time()
        elapsed_time = int(
            current_time - self._session_metadata.session_start_time
        )
        hours = "{:02d}".format(elapsed_time // 3600)
        minutes = "{:02d}".format((elapsed_time // 60) % 60)
        seconds = "{:02d}".format(elapsed_time % 60)
        keyword_count_map = ", ".join(
            [
                value.get_string_to_print()
                for value in self._keywords_to_highlight.values()
            ]
        )
        events_per_second = self._log_events_printer.log_events_displayed
        is_sampled = "Yes" if self._log_events_printer.is_sampled else "No"

        self._metadata.text = ANSI(
            f"Highlighted Terms: {{{keyword_count_map}}}, {events_per_second} events/sec, Sampled: {is_sampled} | {hours}:{minutes}:{seconds}"
        )

    async def highlight_term_in_buffer(self, keyword: Keyword):
        self._output.text = keyword.highlight(self._output.text)
        self._output.pause_buffer.text = keyword.highlight(
            self._output.pause_buffer.text
        )

    async def remove_term_from_buffer(self, keyword: Keyword):
        self._output.text = keyword.remove_highlighting(self._output.text)
        self._output.pause_buffer.text = keyword.remove_highlighting(
            self._output.pause_buffer.text
        )

    async def _trim_buffer(self, buffer: Buffer):
        lines_to_be_removed = max(
            buffer.document.line_count - self._MAX_LINE_COUNT - 1, 0
        )
        return buffer.text.split("\n", lines_to_be_removed)[-1]

    async def _trim_buffers(self):
        while True:
            if self._is_scroll_active:
                self._output.pause_buffer.text = await self._trim_buffer(
                    self._output.pause_buffer
                )
            else:
                self._output.text = await self._trim_buffer(self._output)

            await asyncio.sleep(2)

    async def _render_metadata(self):
        while True:
            self.update_metadata()
            await asyncio.sleep(1)

    def exit(self):
        self._application.exit()

    async def _run_ui(self):
        self._application.create_background_task(self._log_events_printer.run())
        self._application.create_background_task(self._render_metadata())
        self._application.create_background_task(self._trim_buffers())

        await self._application.run_async()

    def run(self):
        asyncio.get_event_loop().run_until_complete(self._run_ui())


class PrintOnlyPrinter(BaseLiveTailPrinter):
    def __init__(self, output, log_events) -> None:
        self._output = output
        self._log_events = log_events
        self.interrupt_session = False

    def _print_log_events(self):
        for log_event in self._log_events:
            self._output.write(log_event + "\n")
            self._output.flush()

        self._log_events.clear()

    def run(self):
        try:
            while True:
                self._print_log_events()

                if self.interrupt_session:
                    break

                time.sleep(1)
        except (BrokenPipeError, KeyboardInterrupt):
            pass


class PrintOnlyUI(BaseLiveTailUI):
    def __init__(self, output, log_events) -> None:
        self._log_events = log_events
        self._printer = PrintOnlyPrinter(output, self._log_events)

    def exit(self):
        self._printer.interrupt_session = True

    def run(self):
        with handle_signal(self._printer):
            self._printer.run()


class LiveTailLogEventsCollector(Thread):
    def __init__(
        self,
        output,
        ui,
        response_stream,
        log_events: list,
        session_metadata: LiveTailSessionMetadata,
    ) -> None:
        super().__init__()
        self._output = output
        self._ui = ui
        self._response_stream = response_stream
        self._log_events = log_events
        self._session_metadata = session_metadata
        self._exception = None

    def _collect_log_events(self):
        try:
            for event in self._response_stream:
                if not "sessionUpdate" in event:
                    continue

                session_update = event["sessionUpdate"]
                self._session_metadata.update_metadata(
                    session_update["sessionMetadata"]
                )
                logEvents = session_update["sessionResults"]
                for logEvent in logEvents:
                    self._log_events.append(logEvent["message"])
        except Exception as e:
            self._exception = e

        self._ui.exit()

    def stop(self):
        if self._exception is not None:
            self._output.write(str(self._exception) + "\n")
            self._output.flush()

    def run(self):
        self._collect_log_events()


class StartLiveTailCommand(BasicCommand):
    NAME = "start-live-tail"
    DESCRIPTION = DESCRIPTION
    ARG_TABLE = [
        LOG_GROUP_IDENTIFIERS,
        LOG_STREAM_NAMES,
        LOG_STREAM_NAME_PREFIXES,
        LOG_EVENT_FILTER_PATTERN,
        MODE,
    ]

    def __init__(self, session):
        super(StartLiveTailCommand, self).__init__(session)
        self._output = get_stdout_text_writer()

    def _get_client(self, parsed_globals):
        return self._session.create_client(
            "logs",
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )

    def _get_start_live_tail_kwargs(self, parsed_args):
        kwargs = {"logGroupIdentifiers": parsed_args.log_group_identifiers}

        if parsed_args.log_stream_names is not None:
            kwargs["logStreamNames"] = parsed_args.log_stream_names
        if parsed_args.log_stream_name_prefixes is not None:
            kwargs["logStreamNamePrefixes"] = (
                parsed_args.log_stream_name_prefixes
            )
        if parsed_args.log_event_filter_pattern is not None:
            kwargs["logEventFilterPattern"] = (
                parsed_args.log_event_filter_pattern
            )

        return kwargs

    def _is_color_allowed(self, color):
        if color == "on":
            return True
        elif color == "off":
            return False
        return is_a_tty()

    def _run_main(self, parsed_args, parsed_globals):
        self._client = self._get_client(parsed_globals)

        start_live_tail_kwargs = self._get_start_live_tail_kwargs(parsed_args)
        response = self._client.start_live_tail(**start_live_tail_kwargs)

        log_events = []
        session_metadata = LiveTailSessionMetadata()

        ui = PrintOnlyUI(self._output, log_events)
        if parsed_args.mode == "interactive":
            if not self._is_color_allowed(parsed_globals.color):
                raise ColorNotAllowedInInteractiveModeError(
                    "Color is not allowed by your output. Use print-only mode or enable color."
                )
            ui = InteractiveUI(log_events, session_metadata)

        log_events_collector = LiveTailLogEventsCollector(
            self._output,
            ui,
            response["responseStream"],
            log_events,
            session_metadata,
        )
        log_events_collector.daemon = True

        log_events_collector.start()
        ui.run()

        log_events_collector.stop()
