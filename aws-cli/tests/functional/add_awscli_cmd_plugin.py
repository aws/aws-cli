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
from awscli.customizations.commands import BasicCommand


def awscli_initialize(event_emitter):
    event_emitter.register('building-command-table.main', add_plugin_cmd)


def add_plugin_cmd(command_table, session, **kwargs):
    command_table['plugin-test-cmd'] = PluginTestCommand(session)


class PluginTestCommand(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        return 0
