# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import make_hidden_command_alias
from awscli.customizations.utils import rename_command


def register_rename_otel_commands(event_emitter):
    event_emitter.register(
        'building-command-table.cloudwatch',
        rename_otel_commands
    )


def rename_otel_commands(command_table, **kwargs):
    """Rename o-tel commands to otel, keeping o-tel as hidden aliases."""
    renames = {
        'get-o-tel-enrichment': 'get-otel-enrichment',
        'start-o-tel-enrichment': 'start-otel-enrichment',
        'stop-o-tel-enrichment': 'stop-otel-enrichment',
    }
    for old_name, new_name in renames.items():
        if old_name in command_table:
            rename_command(command_table, old_name, new_name)
            make_hidden_command_alias(
                command_table, new_name, old_name
            )
