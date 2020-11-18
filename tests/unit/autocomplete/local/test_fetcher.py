# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest, mock

from awscli.autocomplete.local.fetcher import CliDriverFetcher


class FakeDriver:
    def __init__(self):
        global_arg = mock.Mock()
        global_arg.documentation = 'global arg doc'
        self.arg_table = {'arg': global_arg}

        help_command = mock.Mock()
        help_command.obj = 'fake_operational_model'

        arg = mock.Mock()
        arg.documentation = 'arg doc'
        arg_table = {'instance-ids': arg}

        sub_subcommand = mock.Mock()
        sub_subcommand.arg_table = arg_table
        sub_subcommand.create_help_command.return_value = help_command

        subcommand = mock.Mock()
        subcommand.subcommand_table = {'describe-instances': sub_subcommand}
        subcommand_table = {'ec2': subcommand}
        self.subcommand_table = subcommand_table


class TestCliDriverFetcher(unittest.TestCase):
    def setUp(self) -> None:
        self.fetcher = CliDriverFetcher(FakeDriver())

    def test_get_argument_documentation(self):
        help_text = self.fetcher.get_argument_documentation(
            ['aws', 'ec2'], 'describe-instances', 'instance-ids')
        self.assertEqual(help_text, 'arg doc')

    def test_get_global_arg_documentation(self):
        help_text = self.fetcher.get_global_arg_documentation('arg')
        self.assertEqual(help_text, 'global arg doc')

    def test_get_operational_model(self):
        operational_model = self.fetcher.get_operation_model(
            ['aws', 'ec2'], 'describe-instances')
        self.assertEqual(operational_model, 'fake_operational_model')
