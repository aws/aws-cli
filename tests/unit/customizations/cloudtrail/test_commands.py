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
from mock import Mock
from awscli.testutils import unittest
from awscli.customizations import cloudtrail

class TestCloudTrailPlumbing(unittest.TestCase):
    def test_initialization_registers_injector(self):
        cli = Mock()
        cloudtrail.initialize(cli)
        cli.register.assert_called_with('building-command-table.cloudtrail',
                                        cloudtrail.inject_commands)

    def test_injection_adds_two_commands_to_cmd_table(self):
        command_table = {}
        session = Mock()
        cloudtrail.inject_commands(command_table, session)
        self.assertIn('validate-logs', command_table)
