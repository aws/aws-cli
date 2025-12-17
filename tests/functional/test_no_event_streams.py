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
_ALLOWED_COMMANDS = ['s3api select-object-content']


def _generate_command_tests():
    driver = create_clidriver()
    help_command = driver.create_help_command()
    for command_name, command_obj in list(help_command.command_table.items()):
        sub_help = command_obj.create_help_command()
        if hasattr(sub_help, 'command_table'):
            for sub_name, sub_command in sub_help.command_table.items():
                op_help = sub_command.create_help_command()
                model = op_help.obj
                if isinstance(model, OperationModel):
                    yield command_name, sub_name, sub_command, model


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "command_name, sub_name, sub_command, model", _generate_command_tests()
)
def test_no_event_stream_unless_allowed(
        command_name,
        sub_name,
        sub_command,
        model,
        record_property
):
    full_command = f'{command_name} {sub_name}'
    if (
            (
                model.has_event_stream_input
                or model.has_event_stream_output
            )
            and full_command not in _ALLOWED_COMMANDS
    ):
        # Store the service and operation in
        # PyTest custom properties
        record_property(
            'aws_service', model.service_model.service_name
        )
        record_property('aws_operation', model.name)
        supported_commands = '\n'.join(_ALLOWED_COMMANDS)
        assert full_command in _ALLOWED_COMMANDS, (
            f'The {full_command} command uses event streams '
            'which is only supported for these operations:\n'
            f'{supported_commands}'
        )
