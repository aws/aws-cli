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
import json

import colorama
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.input import create_pipe_input

from awscli.compat import StringIO
from awscli.customizations.logs.startlivetail import (
    COLOR_LIST,
    InputState,
    InteractivePrinter,
    InteractiveUI,
    Keyword,
    LiveTailBuffer,
    LiveTailKeyBindings,
    LiveTailLogEventsCollector,
    LiveTailSessionMetadata,
    OutputFormat,
    PrintOnlyPrinter,
    PrintOnlyUI,
)
from awscli.testutils import mock, unittest


class LiveTailSessionMetadataTest(unittest.TestCase):
    def setUp(self):
        self.session_metadata = LiveTailSessionMetadata()

    def test_metadata_update(self):
        metadata_update = {"sampled": True}
        self.session_metadata.update_metadata(metadata_update)

        self.assertEqual(
            metadata_update["sampled"], self.session_metadata.is_sampled
        )


class PrintOnlyPrinterTest(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.log_events = []
        self.printer = PrintOnlyPrinter(self.output, self.log_events)

    def test_print_log_events(self):
        self.log_events.extend(
            ["First LogEvent", "Second LogEvent", "Third LogEvent"]
        )
        expected_msg = "\n".join(self.log_events) + "\n"

        self.printer._print_log_events()

        self.output.seek(0)
        self.assertEqual(expected_msg, self.output.read())
        self.assertEqual(0, len(self.log_events))

    def test_session_interrupt_while_printing(self):
        self.log_events.extend(
            ["First LogEvent", "Second LogEvent", "Third LogEvent"]
        )
        expected_msg = "\n".join(self.log_events) + "\n"

        self.printer.interrupt_session = True
        self.printer.run()

        self.output.seek(0)
        self.assertEqual(expected_msg, self.output.read())
        self.assertEqual(0, len(self.log_events))

    def test_exception_while_printing(self):
        self.log_events.extend(
            ["First LogEvent", "Second LogEvent", "Third LogEvent"]
        )
        self.printer._print_log_events = mock.MagicMock(
            side_effect=BrokenPipeError("BrokenPipe")
        )

        # No exception should be raised
        self.printer.run()


class PrintOnlyUITest(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.log_events = []
        self.ui = PrintOnlyUI(self.output, self.log_events)

    def test_exit(self):
        self.ui.exit()

        self.assertEqual(True, self.ui._printer.interrupt_session)


class LiveTailLogEventsCollectorTest(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.log_events = []
        self.response_stream = mock.Mock()
        self.ui = PrintOnlyUI(self.output, self.log_events)
        self.session_metadata = LiveTailSessionMetadata()
        self.log_events_collector = LiveTailLogEventsCollector(
            self.output,
            self.ui,
            self.response_stream,
            self.log_events,
            self.session_metadata,
        )

    def test_log_event_collection(self):
        updates = [
            {"sessionStart": "The session is started"},
            {
                "sessionUpdate": {
                    "sessionMetadata": {"sampled": False},
                    "sessionResults": [
                        {"message": "LogEvent1"},
                        {"message": "LogEvent2"},
                    ],
                }
            },
        ]
        self.response_stream.__iter__ = mock.MagicMock(
            return_value=iter(updates)
        )

        self.log_events_collector._collect_log_events()

        self.assertEqual(2, len(self.log_events))
        self.assertEqual(["LogEvent1", "LogEvent2"], self.log_events)
        self.assertIsNone(self.log_events_collector._exception)

    def test_log_event_collection_with_unexpected_update(self):
        updates = [{"unexpectedUpdate": "The session is started"}]
        self.response_stream.extend(updates)
        self.ui.exit = mock.MagicMock()

        self.log_events_collector._collect_log_events()

        self.assertIsNotNone(self.log_events_collector._exception)

    def test_stop_with_exception(self):
        exception_message = "SessionStreamingException"
        self.log_events_collector._exception = Exception(exception_message)

        self.log_events_collector.stop()

        self.output.seek(0)
        self.assertEqual(exception_message + "\n", self.output.read())

    def test_stop_without_exception(self):
        self.response_stream.close = mock.MagicMock()

        self.log_events_collector.stop()
        self.response_stream.close.assert_not_called()


class KeywordTest(unittest.TestCase):
    def setUp(self) -> None:
        self.keyword = None

    def test_text(self):
        text = "KEYWORD"
        self.keyword = Keyword(text, COLOR_LIST[0])

        self.assertEqual(text.lower(), self.keyword.text)

    def test_color_protected_keywords(self):
        text = "INFO"
        self.keyword = Keyword(text)

        self.assertEqual(text.lower(), self.keyword.text)
        self.assertEqual(colorama.Fore.GREEN, self.keyword._color)

        text = "ERROR"
        self.keyword = Keyword(text)

        self.assertEqual(text.lower(), self.keyword.text)
        self.assertEqual(colorama.Fore.RED, self.keyword._color)

        text = "WARN"
        self.keyword = Keyword(text)

        self.assertEqual(text.lower(), self.keyword.text)
        self.assertEqual(colorama.Fore.YELLOW, self.keyword._color)

    def test_color_unprotected_keywords(self):
        text = "random"
        keyword_1 = Keyword(text, COLOR_LIST[0])

        self.assertEqual(text.lower(), keyword_1.text)
        self.assertTrue(keyword_1._color in COLOR_LIST)

        text = "something_else_random"
        keyword_2 = Keyword(text, COLOR_LIST[1])

        self.assertEqual(text.lower(), keyword_2.text)
        self.assertTrue(keyword_2._color in COLOR_LIST)

        self.assertNotEqual(keyword_1._color, keyword_2._color)

    def test_string_to_print(self):
        text = "INFO"
        self.keyword = Keyword(text)

        self.assertEqual(
            colorama.Fore.GREEN
            + text.lower()
            + colorama.Style.RESET_ALL
            + ": 0",
            self.keyword.get_string_to_print(),
        )

    def test_add_color_to_string(self):
        text = "INFO"
        log_event = "This is an INFO log"
        self.keyword = Keyword(text)

        colored_log_event = self.keyword._add_color_to_string(
            log_event, 11, 15
        )

        self.assertEqual(
            "This is an "
            + colorama.Fore.GREEN
            + text
            + colorama.Style.RESET_ALL
            + " log",
            colored_log_event,
        )

    def test_remove_color_from_string(self):
        text = "INFO"
        log_event = "This is an INFO log"
        self.keyword = Keyword(text)

        colored_log_event = self.keyword._add_color_to_string(
            log_event, 11, 15
        )
        uncolored_log_event = self.keyword._remove_color_from_string(
            log_event, 15, 19
        )

        self.assertEqual(log_event, uncolored_log_event)

    def test_highlight(self):
        text = "INFO"
        log_event = "This is an INFO log with info occurring a lot of times. Because we are testing INFO."
        self.keyword = Keyword(text)

        log_event_after_highlighting = self.keyword.highlight(log_event)

        self.assertEqual(
            "This is an "
            + colorama.Fore.GREEN
            + text
            + colorama.Style.RESET_ALL
            + " log with "
            + colorama.Fore.GREEN
            + text.lower()
            + colorama.Style.RESET_ALL
            + " occurring a lot of times. Because we are testing "
            + colorama.Fore.GREEN
            + text
            + colorama.Style.RESET_ALL
            + ".",
            log_event_after_highlighting,
        )


class InteractivePrinterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ui = mock.Mock(spec=InteractiveUI)
        self.output = LiveTailBuffer()
        self.log_events = []
        self.session_metadata = LiveTailSessionMetadata()
        self.keyword_highlight = {}
        self.printer = InteractivePrinter(
            self.ui,
            self.output,
            self.log_events,
            self.session_metadata,
            self.keyword_highlight,
        )

    def test_color_log_event(self):
        log_event = "[INFO] this is a log event with KEYWORD"
        keyword = Keyword("KEYWORD", COLOR_LIST[0])
        self.keyword_highlight[keyword.text] = keyword

        colored_log_event = self.printer._color_log_event(log_event)

        self.assertEqual(
            "["
            + colorama.Fore.GREEN
            + "INFO"
            + colorama.Style.RESET_ALL
            + "] this is a log event with "
            + COLOR_LIST[0]
            + "KEYWORD"
            + colorama.Style.RESET_ALL,
            colored_log_event,
        )

    def test_format_log_event_json(self):
        log_event = '{ "message": "This is a LogEvent", "logger": "self" }'
        json_log_event = json.dumps(json.loads(log_event), indent=4)

        formatted_log_event = self.printer._format_log_event(log_event)

        self.assertEqual(json_log_event, formatted_log_event)

    def test_format_log_event_not_json(self):
        log_event = "this is a log event"

        formatted_log_event = self.printer._format_log_event(log_event)

        self.assertEqual(log_event, formatted_log_event)

    def test_toggle_formatting(self):
        self.printer.toggle_formatting()

        self.assertEqual(OutputFormat.PLAIN_TEXT, self.printer.output_format)

    def test_print_log_events(self):
        self.session_metadata.update_metadata({"sampled": True})
        log_event_1 = "[ERROR] in todays log."
        log_event_2 = '{ "severity": "INFO", "message": "This keyword will be highlighted." }'
        self.log_events.extend([log_event_1, log_event_2])
        keyword = Keyword("keyword", COLOR_LIST[0])
        self.keyword_highlight[keyword.text] = keyword
        expected_output = "{}\n{}\n".format(
            self.printer._color_log_event(
                self.printer._format_log_event(log_event_1)
            ),
            self.printer._color_log_event(
                self.printer._format_log_event(log_event_2)
            ),
        )

        self.printer._print_log_events()

        self.assertEqual(expected_output, self.output.text)
        self.assertEqual(2, self.printer.log_events_displayed)
        self.assertEqual(True, self.printer.is_sampled)
        self.assertEqual(0, len(self.log_events))
        self.ui.update_metadata.assert_called_once_with()


class LiveTailBufferTest(unittest.TestCase):
    def setUp(self) -> None:
        self.buffer = LiveTailBuffer()
        self.layout = mock.MagicMock()

    def test_add_text_when_not_in_focus(self):
        self.layout.has_focus.return_value = False

        self.buffer.add_text("random text")

        self.assertEqual("random text", self.buffer.text)
        self.assertEqual(len(self.buffer.text), self.buffer.cursor_position)


class LiveTailKeyBindingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ui = mock.Mock(InteractiveUI)
        self.prompt_buffer = Buffer()
        self.output_buffer = Buffer()
        self.ui._application = mock.Mock(Application)
        self.keyword_highlight = {}
        self.key_bindings = LiveTailKeyBindings(
            self.ui,
            self.prompt_buffer,
            self.output_buffer,
            self.keyword_highlight,
        )

    def test_reset(self):
        event = mock.Mock()
        event.app = self.ui._application
        self.key_bindings._reset(event)

        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)
        self.assertEqual("", self.key_bindings._input_buffer.text)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.get_instructions()
        )
        self.ui.update_quit_button.assert_called_once_with(
            self.ui.EXIT_SESSION
        )
        self.ui._application.invalidate.assert_called_once_with()

    def test_any_key_binding(self):
        self.key_bindings.get_bindings_for_keys("a")[0].handler(
            mock.Mock(spec=KeyPressEvent)
        )

        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)

        # if input is in highlight mode, text can be added to the buffer
        self.key_bindings.get_bindings_for_keys("h")[-1].handler(
            mock.Mock(spec=KeyPressEvent)
        )
        keypress_a = mock.Mock(spec=KeyPressEvent)
        keypress_a.data = "a"
        self.key_bindings.get_bindings_for_keys("a")[1].handler(keypress_a)

        self.assertEqual("a", self.key_bindings._input_buffer.text)

        # adding text buffer to the keyword
        print(self.key_bindings.bindings)
        self.key_bindings.bindings[7].handler(mock.Mock(spec=KeyPressEvent))

        # moving the input to clear mode
        keypress_c = mock.Mock(spec=KeyPressEvent)
        keypress_c.app = self.ui._application
        self.key_bindings.get_bindings_for_keys("c")[-1].handler(keypress_c)
        keypress_1 = mock.Mock(spec=KeyPressEvent)
        keypress_1.data = "1"
        self.key_bindings.get_bindings_for_keys("1")[2].handler(keypress_1)

        self.assertEqual(0, len(self.keyword_highlight))
        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)
        self.assertEqual("", self.key_bindings._input_buffer.text)
        self.ui.update_bottom_toolbar.assert_called_with(
            self.ui.get_instructions()
        )
        self.ui.update_quit_button.assert_called_with(self.ui.EXIT_SESSION)
        self.ui._application.invalidate.assert_called_with()

    def test_h_key_binding(self):
        keypress_h = mock.Mock(spec=KeyPressEvent)
        keypress_h.app = self.ui._application
        self.key_bindings.get_bindings_for_keys("h")[-1].handler(keypress_h)

        self.assertEqual(InputState.HIGHLIGHT, self.key_bindings._input_state)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.HIGHLIGHT_INSTRUCTIONS
        )
        self.ui.update_quit_button.assert_called_once_with(
            self.ui.EXIT_HIGHLIGHT
        )
        self.ui._application.invalidate.assert_called_once_with()

        self.key_bindings._reset(keypress_h)

        self.keyword_highlight["text1"] = Keyword("text1", COLOR_LIST[0])
        self.keyword_highlight["text2"] = Keyword("text2", COLOR_LIST[1])
        self.keyword_highlight["text3"] = Keyword("text3", COLOR_LIST[2])
        self.keyword_highlight["text4"] = Keyword("text4", COLOR_LIST[3])
        self.keyword_highlight["text5"] = Keyword("text5", COLOR_LIST[4])

        # Filter condition for keybinding is False if there are 5 or greater keywords
        self.assertFalse(
            self.key_bindings.get_bindings_for_keys("h")[-1].filter()
        )

    def test_c_key_binding(self):
        keypress_c = mock.Mock(spec=KeyPressEvent)
        keypress_c.app = self.ui._application

        # Nothing is executed unless there's a keyword to clean
        self.assertFalse(
            self.key_bindings.get_bindings_for_keys("c")[-1].filter()
        )
        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)

        keyword = Keyword("text", COLOR_LIST[0])
        self.keyword_highlight[keyword.text] = keyword

        self.key_bindings.get_bindings_for_keys("c")[-1].handler(keypress_c)

        self.assertEqual(InputState.CLEAR, self.key_bindings._input_state)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            "1: text    ENTER: All"
        )
        self.ui.update_quit_button.assert_called_once_with(self.ui.EXIT_CLEAR)
        self.ui._application.invalidate.assert_called_once_with()

    def test_t_key_binding(self):
        self.key_bindings.get_bindings_for_keys("t")[-1].handler(
            mock.Mock(spec=KeyPressEvent)
        )

        self.ui.toggle_formatting.assert_called_once_with()
        self.ui.get_instructions.assert_called_once_with()
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.get_instructions()
        )

    def test_q_key_binding(self):
        keypress_q = mock.Mock(spec=KeyPressEvent)
        keypress_q.app = self.ui._application
        self.ui._application.layout = mock.Mock()
        self.ui._application.layout.has_focus.return_value = False

        self.key_bindings.get_bindings_for_keys("q")[-1].handler(keypress_q)

        self.ui.handle_scrolling.assert_called_once_with(False)
        self.ui._application.layout.focus.assert_called_once_with(
            self.prompt_buffer
        )

    def test_enter_key_binding(self):
        # enter pressed when input disabled
        keypress_enter = mock.Mock(spec=KeyPressEvent)
        keypress_enter.app = self.ui._application
        self.key_bindings.bindings[7].handler(keypress_enter)

        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)
        self.assertEqual("", self.key_bindings._input_buffer.text)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.get_instructions()
        )
        self.ui.update_quit_button.assert_called_once_with(
            self.ui.EXIT_SESSION
        )
        self.ui._application.invalidate.assert_called_once_with()

        # going to highlight mode
        keypress_h = mock.Mock(spec=KeyPressEvent)
        keypress_h.app = self.ui._application
        self.key_bindings.get_bindings_for_keys("h")[-1].handler(keypress_h)
        self.key_bindings._input_buffer.text = "keyword"

        self.key_bindings.bindings[7].handler(keypress_enter)

        # assert keywords added to highlight
        self.assertTrue("keyword" in self.keyword_highlight)
        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)
        self.assertEqual("", self.key_bindings._input_buffer.text)
        self.ui.update_bottom_toolbar.assert_called_with(
            self.ui.get_instructions()
        )
        self.ui.update_quit_button.assert_called_with(self.ui.EXIT_SESSION)
        self.ui._application.invalidate.assert_called_with()

        # going to clear mode
        keypress_c = mock.Mock(spec=KeyPressEvent)
        keypress_c.app = self.ui._application
        self.key_bindings.get_bindings_for_keys("c")[-1].handler(keypress_c)
        self.key_bindings.bindings[8].handler(keypress_enter)

        # assert keywords cleared
        self.assertEqual(0, len(self.keyword_highlight))
        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)
        self.assertEqual("", self.key_bindings._input_buffer.text)
        self.ui.update_bottom_toolbar.assert_called_with(
            self.ui.get_instructions()
        )
        self.ui.update_quit_button.assert_called_with(self.ui.EXIT_SESSION)
        self.ui._application.invalidate.assert_called_with()

    def test_backspace_key_binding(self):
        self.prompt_buffer.text = "text"

        self.key_bindings.bindings[9].handler(mock.Mock(spec=KeyPressEvent))

        self.assertEqual("tex", self.prompt_buffer.text)

    def test_escape_key_binding(self):
        escape_event = mock.Mock(spec=KeyPressEvent)
        escape_event.app = self.ui._application

        self.key_bindings.bindings[11].handler(escape_event)

        self.ui._application.exit.assert_called_once_with()

        # if in highlight mode, escape gets you out of highlight
        self.key_bindings._input_state = InputState.HIGHLIGHT

        self.key_bindings.bindings[10].handler(escape_event)

        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)

        # if in clear mode, escape gets you out of clear
        self.key_bindings._input_state = InputState.CLEAR

        self.key_bindings.bindings[10].handler(escape_event)

        self.assertEqual(InputState.DISABLED, self.key_bindings._input_state)

    def test_ctrl_c_key_binding(self):
        escape_event = mock.Mock(spec=KeyPressEvent)
        escape_event.app = self.ui._application

        self.key_bindings.bindings[12].handler(escape_event)

        self.ui._application.exit.assert_called_once_with()


class InteractiveUITest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.output = StringIO
        self.log_events = []
        self.session_metadata = LiveTailSessionMetadata()
        self.ui = InteractiveUI(
            self.log_events, self.session_metadata, app_output=DummyOutput(),
            app_input=create_pipe_input()
        )

    def test_update_toolbar(self):
        text = "new text"

        self.ui.update_bottom_toolbar(text)

        self.assertEqual(text, self.ui._bottom_toolbar.text)

    def test_update_quit_button(self):
        text = "new text"

        self.ui.update_quit_button(text)

        self.assertEqual(text, self.ui._quit_button.text)

    def test_metadata_update(self):
        keyword = Keyword("text", COLOR_LIST[0])
        self.ui._keywords_to_highlight[keyword.text] = keyword

        self.ui.update_metadata()

        self.assertTrue(keyword.text in self.ui._metadata.text.value)

    def test_get_instructions(self):
        instructions = self.ui.INSTRUCTIONS.format(
            colorama.Fore.GREEN
            + OutputFormat.JSON.value
            + colorama.Style.RESET_ALL,
            OutputFormat.PLAIN_TEXT.value,
        )
        self.assertEqual(instructions, self.ui.get_instructions().value)

        self.ui._log_events_printer.toggle_formatting()
        instructions = self.ui.INSTRUCTIONS.format(
            OutputFormat.JSON.value,
            colorama.Fore.GREEN
            + OutputFormat.PLAIN_TEXT.value
            + colorama.Style.RESET_ALL,
        )
        self.assertEqual(instructions, self.ui.get_instructions().value)

        self.ui._is_scroll_active = True
        instructions = (
            self.ui.INSTRUCTIONS.format(
                OutputFormat.JSON.value,
                colorama.Fore.GREEN
                + OutputFormat.PLAIN_TEXT.value
                + colorama.Style.RESET_ALL,
            )
            + "    q: Scroll to latest"
        )
        self.assertEqual(instructions, self.ui.get_instructions().value)

    def test_handle_scrolling(self):
        self.ui.get_instructions = mock.MagicMock(return_value="instructions")
        self.ui.update_bottom_toolbar = mock.MagicMock()

        self.ui.handle_scrolling(True)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.get_instructions()
        )

        self.ui._key_bindings._input_state = InputState.HIGHLIGHT
        self.ui.handle_scrolling(True)
        self.ui.update_bottom_toolbar.assert_called_once_with(
            self.ui.get_instructions()
        )

        self.ui._output._pause_buffer.text = "random text"
        self.ui._trim_buffer = mock.MagicMock()
        self.ui._application.create_background_task = mock.MagicMock()
        self.ui.handle_scrolling(False)
        self.assertEqual("random text", self.ui._output.text)
        self.assertEqual(
            len(self.ui._output.text), self.ui._output.cursor_position
        )
        self.assertEqual("", self.ui._output._pause_buffer.text)
        self.ui._trim_buffer.assert_called_once_with(self.ui._output)

    async def test_highlight_term_in_buffer(self):
        keyword = Keyword("INFO")
        log_event = "This is an INFO log"
        self.ui._output.text = log_event
        self.ui._output.pause_buffer.text = log_event

        await self.ui.highlight_term_in_buffer(keyword)

        self.assertEqual(keyword.highlight(log_event), self.ui._output.text)
        self.assertEqual(
            keyword.highlight(log_event), self.ui._output._pause_buffer.text
        )

    async def test_remove_highlight_term_in_buffer(self):
        keyword = Keyword("INFO")
        log_event = "This is an INFO log"
        colored_log_event = keyword.highlight(log_event)
        self.ui._output.text = colored_log_event
        self.ui._output.pause_buffer.text = colored_log_event

        await self.ui.remove_term_from_buffer(keyword)

        self.assertEqual(log_event, self.ui._output.text)
        self.assertEqual(log_event, self.ui._output._pause_buffer.text)

    async def test_trim_buffer(self):
        self.ui._MAX_LINE_COUNT = 1
        log_event = Buffer()
        log_event.text += "text\n"
        log_event.text += "text\n"

        log_event_after_trim = await self.ui._trim_buffer(log_event)

        self.assertEqual("text\n", log_event_after_trim)

    def test_exit(self):
        self.ui._application.exit = mock.MagicMock()

        self.ui.exit()

        self.ui._application.exit.assert_called_once_with()
