# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import BaseAWSCommandParamsTest, BaseAWSHelpOutputTest


class TestListStreams(BaseAWSCommandParamsTest):

    prefix = ['kinesis', 'list-streams']

    def test_exclusive_start_stream_name_disables_auto_pagination(self):
        cmdline = self.prefix + ['--exclusive-start-stream-name', 'stream-1']
        self.parsed_responses = [
            {
                'StreamNames': ['stream-1', 'stream-2'],
                'StreamSummaries': [
                    {'StreamName': 'stream-1'},
                    {'StreamName': 'stream-2'},
                ],
                'HasMoreStreams': True,
                'NextToken': 'token',
            }
        ]
        expected_params = {'ExclusiveStartStreamName': 'stream-1'}
        stdout, _, _ = self.assert_params_for_cmd(cmdline, expected_params)
        output = json.dumps(stdout)
        self.assertIn('NextToken', output)
        self.assertIn('HasMoreStreams', output)

    def test_exclusive_start_stream_name_incompatible_with_page_args(self):
        cmdline = self.prefix + ['--exclusive-start-stream-name', 'stream-1']
        cmdline += ['--page-size', '1']
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Error during pagination: Cannot specify', stderr)
        self.assertIn('--page-size', stderr)


class TestListStreamsHelp(BaseAWSHelpOutputTest):
    def test_exclusive_start_stream_name_is_undocumented(self):
        self.driver.main(['kinesis', 'list-streams', 'help'])
        self.assert_not_contains('--exclusive-start-steam-name')
