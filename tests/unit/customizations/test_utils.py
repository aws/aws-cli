# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
from tests import BaseAWSHelpOutputTest

import mock

from awscli.customizations import utils


class TestCommandTableRenames(BaseAWSHelpOutputTest):

    def test_rename_command_table(self):
        handler = lambda command_table, **kwargs: utils.rename_command(
            command_table, 'ec2', 'fooec2')
        # Verify that we can rename a top level command.
        self.session.register('building-command-table.main', handler)
        self.driver.main(['fooec2', 'help'])
        self.assert_contains('fooec2')

        # We can also see subcommands help as well.
        self.driver.main(['fooec2', 'run-instances', 'help'])
        self.assert_contains('run-instances')
