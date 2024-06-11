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
from awscli.testutils import mock, BaseAWSCommandParamsTest


class TestStartLiveTailCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestStartLiveTailCommand, self).setUp()
        self.log_group_identifiers = [
            "arn:aws:logs:us-east-1:123456789012:log-group:mygroup"
        ]
        self.log_stream_names = ["mystream"]
        self.log_stream_name_prefixes = ["mystream"]
        self.log_event_filter_pattern = "filterPattern"

        self.raw_stream = mock.Mock()
        self.raw_stream.stream = mock.MagicMock(return_value=[])
        self.event_stream = mock.Mock()
        self.updates = iter(
            [
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
        )
        self.parsed_responses = [{"responseStream": self.event_stream}]

    def tearDown(self):
        super(TestStartLiveTailCommand, self).tearDown()

    def test_start_live_tail(self):
        self.event_stream.__iter__ = mock.MagicMock(return_value=self.updates)

        stdout, _, _ = self.assert_params_for_cmd(
            "logs start-live-tail --log-group-identifiers {}".format(
                " ".join(self.log_group_identifiers)
            ),
            params={"logGroupIdentifiers": self.log_group_identifiers},
        )
        self.assertEqual(stdout, "LogEvent1\nLogEvent2\n")

    def test_start_live_tail_with_log_stream_names(self):
        self.event_stream.__iter__ = mock.MagicMock(return_value=self.updates)

        stdout, _, _ = self.assert_params_for_cmd(
            "logs start-live-tail --log-group-identifiers {} --log-stream-names {}".format(
                " ".join(self.log_group_identifiers), " ".join(self.log_stream_names)
            ),
            params={
                "logGroupIdentifiers": self.log_group_identifiers,
                "logStreamNames": self.log_stream_names,
            },
        )
        self.assertEqual(stdout, "LogEvent1\nLogEvent2\n")

    def test_start_live_tail_with_log_stream_name_prefixes(self):
        self.event_stream.__iter__ = mock.MagicMock(return_value=self.updates)

        stdout, _, _ = self.assert_params_for_cmd(
            "logs start-live-tail --log-group-identifiers {} --log-stream-name-prefixes {}".format(
                " ".join(self.log_group_identifiers),
                " ".join(self.log_stream_name_prefixes),
            ),
            params={
                "logGroupIdentifiers": self.log_group_identifiers,
                "logStreamNamePrefixes": self.log_stream_name_prefixes,
            },
        )
        self.assertEqual(stdout, "LogEvent1\nLogEvent2\n")

    def test_start_live_tail_with_filter_pattern(self):
        self.event_stream.__iter__ = mock.MagicMock(return_value=self.updates)

        stdout, _, _ = self.assert_params_for_cmd(
            "logs start-live-tail --log-group-identifiers {} --log-event-filter-pattern {}".format(
                " ".join(self.log_group_identifiers), self.log_event_filter_pattern
            ),
            params={
                "logGroupIdentifiers": self.log_group_identifiers,
                "logEventFilterPattern": self.log_event_filter_pattern,
            },
        )
        self.assertEqual(stdout, "LogEvent1\nLogEvent2\n")
