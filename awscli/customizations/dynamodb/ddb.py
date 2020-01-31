# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.commands import BasicCommand
from awscli.customizations.dynamodb.subcommands import (
    SelectCommand, PutCommand,
)


def register_ddb(events):
    events.register("building-command-table.main", add_ddb)


def add_ddb(command_table, session, **kwargs):
    command_table['ddb'] = DDB(session)


class DDB(BasicCommand):
    NAME = 'ddb'
    DESCRIPTION = 'High level DynamoDB commands.'
    SYNOPSIS = "aws ddb <Command> [<Arg> ...]"
    SUBCOMMANDS = [
        {'name': 'select', 'command_class': SelectCommand},
        {'name': 'put', 'command_class': PutCommand},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            self._raise_usage_error()
