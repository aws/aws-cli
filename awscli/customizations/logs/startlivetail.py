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
from functools import partial
from threading import Thread
import contextlib
import signal
import sys
import time

from awscli.compat import get_stdout_text_writer
from awscli.customizations.commands import BasicCommand
from awscli.utils import is_a_tty


DESCRIPTION = (
    "Starts a Live Tail streaming session for one or more log groups. "
    "A Live Tail session provides a near real-time streaming of "
    "log events as they are ingested into selected log groups. "
    "A session can go on for a maximum of 3 hours.\n\n"
    "You must have logs:StartLiveTail permission to perform this operation. "
    "If the log events matching the filters are more than 500 events per second, "
    "we sample the events to provide the real-time tailing experience.\n\n"
    "If you are using CloudWatch cross-account observability, "
    "you can use this operation in a monitoring account and start tailing on "
    "Log Group(s) present in the linked source accounts. "
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
        "If more than one Log Group is provided "
        "--log-stream-names and --log-stream-name-prefixes  is disabled. "
        "--log-stream-names and --log-stream-name-prefixes can't be provided simultaneously.\n\n"
        "Note -  The Log Group ARN must be in the following format. "
        "Replace REGION and ACCOUNT_ID with your Region and account ID. "
        "``arn:aws:logs:REGION :ACCOUNT_ID :log-group:LOG_GROUP_NAME``. "
        "A ``:*`` after the ARN is prohibited."
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


class PrintOnlyPrinter:
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


class PrintOnlyUI:
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
            kwargs["logStreamNamePrefixes"] = parsed_args.log_stream_name_prefixes
        if parsed_args.log_event_filter_pattern is not None:
            kwargs["logEventFilterPattern"] = parsed_args.log_event_filter_pattern

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

        log_events_collector = LiveTailLogEventsCollector(
            self._output, ui, response["responseStream"], log_events, session_metadata
        )
        log_events_collector.daemon = True

        log_events_collector.start()
        ui.run()

        log_events_collector.stop()
        sys.exit(0)
