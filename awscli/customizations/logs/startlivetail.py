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


class ColorNotAllowedInInteractiveModeError(ParamValidationError):
    pass


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
        from awscli.customizations.logs.ui import (
            InteractiveUI,
            LiveTailLogEventsCollector,
            LiveTailSessionMetadata,
            PrintOnlyUI,
        )
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
