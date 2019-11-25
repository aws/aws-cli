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
from tests.functional.history import BaseHistoryCommandParamsTest

from awscli.testutils import create_clidriver, mock


class TestShowCommand(BaseHistoryCommandParamsTest):
    def test_show_latest(self):
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
        # Test that the CLI specific events are present such as arguments
        # entered and version
        #
        # The show command writes the history out as binary to the attached
        # stream so we want to determine if the values are in the binary
        # stdout stream
        self.assertIn('describe-regions', stdout)
        self.assertIn('version', stdout)

    def test_show_nothing_when_no_history(self):
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

    def test_show_with_include(self):
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
        stdout, _, _ = self.run_cmd(
            'history show --include CLI_ARGUMENTS', expected_rc=0)
        # Make sure the CLI version was not included because of the filter.
        #
        # The show command writes the history out as binary to the attached
        # stream so we want to determine if the values are in the binary
        # stdout stream
        self.assertIn('describe-regions', stdout)
        self.assertNotIn('version', stdout)

    def test_show_with_exclude(self):
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
        stdout, _, _ = self.run_cmd(
            'history show --exclude CLI_ARGUMENTS', expected_rc=0)
        # Make sure the API call was not included because of the filter,
        # but all other events such as the version are included.
        #
        # The show command writes the history out as binary to the attached
        # stream so we want to determine if the values are in the binary
        # stdout stream
        self.assertNotIn('describe-regions', stdout)
        self.assertIn('version', stdout)
