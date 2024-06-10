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
import pytest
from botocore.model import OperationModel

from awscli.clidriver import create_clidriver


# Excluded commands must be registered in awscli/customizations/removals.py
_ALLOWED_COMMANDS = [
    's3api select-object-content'
]


@pytest.mark.validates_models
def test_no_event_stream_unless_allowed():
    driver = create_clidriver()
    help_command = driver.create_help_command()
    errors = []
    for command_name, command_obj in help_command.command_table.items():
        sub_help = command_obj.create_help_command()
        if hasattr(sub_help, 'command_table'):
            for sub_name, sub_command in sub_help.command_table.items():
                op_help = sub_command.create_help_command()
                model = op_help.obj
                if isinstance(model, OperationModel):
                    full_command = '%s %s' % (command_name, sub_name)
                    if model.has_event_stream_input or \
                            model.has_event_stream_output:
                        if full_command in _ALLOWED_COMMANDS:
                            continue
                        supported_commands = '\n'.join(_ALLOWED_COMMANDS)
                        errors.append(
                            'The "%s" command uses event streams '
                            'which is only supported for these operations:\n'
                            '%s' % (full_command, supported_commands)
                        )
    if errors:
        raise AssertionError('\n' + '\n'.join(errors))
