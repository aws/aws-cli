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


class CliDriverFetcher:

    def __init__(self, cli_driver):
        self._cli_driver = cli_driver

    def _get_command(self, lineage, current_command):
        subcommand_table = self._cli_driver.subcommand_table
        for arg in lineage[1:]:
            subcommand = subcommand_table[arg]
            subcommand_table = subcommand.subcommand_table
        return subcommand_table.get(current_command)

    def _get_argument(self, lineage, current_command, arg_name):
        command = self._get_command(lineage, current_command)
        if command:
            return command.arg_table.get(arg_name)

    def get_operation_model(self, lineage, current_command):
        if len(lineage) > 1 and current_command:
            command = self._get_command(lineage, current_command)
            return command.create_help_command().obj

    def get_argument_model(self, lineage, current_command, arg_name):
        return getattr(self._get_argument(
            lineage, current_command, arg_name), 'argument_model', None)

    def get_argument_documentation(self, lineage, current_command, arg_name):
        return getattr(self._get_argument(
            lineage, current_command, arg_name), 'documentation', '')

    def get_global_arg_documentation(self, arg_name):
        return self._cli_driver.arg_table[arg_name].documentation

    def get_global_arg_choices(self, arg_name):
        if arg_name in self._cli_driver.arg_table:
            return self._cli_driver.arg_table[arg_name].choices
