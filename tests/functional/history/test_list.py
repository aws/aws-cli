# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.compat import ensure_text_type

from tests.functional.history import BaseHistoryCommandParamsTest
from awscli.testutils import create_clidriver


class TestListCommand(BaseHistoryCommandParamsTest):
    def test_show_nothing_when_no_history_and_call_made(self):
        self.environ['AWS_CONFIG_FILE'] = ''
        self.driver = create_clidriver()
        self.parsed_responses = [
            {
                "Regions": [
                    {
                        "Endpoint": "ec2.ap-south-1.amazonaws.com",
                        "RegionName": "ap-south-1"
                    },
                ]
            }
        ]
        self.run_cmd('ec2 describe-regions', expected_rc=0)
        stdout, _, _ = self.run_cmd('history show', expected_rc=0)
        # The history show should not display anything as no history should
        # have been collected
        self.assertEqual('', stdout)

    def test_show_nothing_when_no_history(self):
        out, err, rc = self.run_cmd('history list', expected_rc=255)
        error_message = (
            'No commands were found in your history. Make sure you have '
            'enabled history mode by adding "cli_history = enabled" '
            'to the config file.'
        )
        self.assertEqual('', ensure_text_type(out))
        self.assertEqual('\n%s\n' % error_message, ensure_text_type(err))

    def test_show_one_call_present(self):
        self.parsed_responses = [
            {
                "Regions": [
                    {
                        "Endpoint": "ec2.ap-south-1.amazonaws.com",
                        "RegionName": "ap-south-1"
                    },
                ]
            }
        ]
        _, _, rc = self.run_cmd('ec2 describe-regions', expected_rc=0)
        self.history_recorder.record('CLI_RC', rc, 'CLI')
        stdout, _, _ = self.run_cmd('history list', expected_rc=0)
        self.assertIn('ec2 describe-regions', stdout)

    def test_multiple_calls_present(self):
            self.parsed_responses = [
                {
                    "Regions": [
                        {
                            "Endpoint": "ec2.ap-south-1.amazonaws.com",
                            "RegionName": "ap-south-1"
                        },
                    ]
                },
                {
                    "UserId": "foo",
                    "Account": "bar",
                    "Arn": "arn:aws:iam::1234567:user/baz"
                }
            ]
            _, _, rc = self.run_cmd('ec2 describe-instances', expected_rc=0)
            self.history_recorder.record('CLI_RC', rc, 'CLI')
            _, _, rc = self.run_cmd('sts get-caller-identity', expected_rc=0)
            self.history_recorder.record('CLI_RC', rc, 'CLI')
            stdout, _, _ = self.run_cmd('history list', expected_rc=0)
            self.assertIn('ec2 describe-instances', stdout)
            self.assertIn('sts get-caller-identity', stdout)
