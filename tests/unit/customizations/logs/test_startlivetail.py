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
from awscli.compat import StringIO
from awscli.customizations.logs.startlivetail import (
    LiveTailLogEventsCollector,
    LiveTailSessionMetadata,
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

        self.assertEqual(metadata_update["sampled"], self.session_metadata.is_sampled)


class PrintOnlyPrinterTest(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.log_events = []
        self.printer = PrintOnlyPrinter(self.output, self.log_events)

    def test_print_log_events(self):
        self.log_events.extend(["First LogEvent", "Second LogEvent", "Third LogEvent"])
        expected_msg = "\n".join(self.log_events) + "\n"

        self.printer._print_log_events()

        self.output.seek(0)
        self.assertEqual(expected_msg, self.output.read())
        self.assertEqual(0, len(self.log_events))

    def test_session_interrupt_while_printing(self):
        self.log_events.extend(["First LogEvent", "Second LogEvent", "Third LogEvent"])
        expected_msg = "\n".join(self.log_events) + "\n"

        self.printer.interrupt_session = True
        self.printer.run()

        self.output.seek(0)
        self.assertEqual(expected_msg, self.output.read())
        self.assertEqual(0, len(self.log_events))

    def test_exception_while_printing(self):
        self.log_events.extend(["First LogEvent", "Second LogEvent", "Third LogEvent"])
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
        self.response_stream.__iter__ = mock.MagicMock(return_value=iter(updates))

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
