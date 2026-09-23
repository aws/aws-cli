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

from tests import ALL_SERVICES

# Excluded commands must be registered in awscli/customizations/removals.py
_ALLOWED_COMMANDS = ['s3api select-object-content']


def _has_event_stream_member(service_model):
    # Checking every operation resolves and caches its input and output
    # shapes on ALL_SERVICES, which every xdist worker would then hold for
    # the whole run. Shapes from shape_for are not cached, so use them to
    # skip services that have no event stream member at all.
    return any(
        service_model.shape_for(shape_name).event_stream_name
        for shape_name in service_model.shape_names
    )


def _event_stream_operations():
    operations = []
    for service_model in ALL_SERVICES:
        if not _has_event_stream_member(service_model):
            continue
        for operation_name in service_model.operation_names:
            operation_model = service_model.operation_model(operation_name)
            if (
                operation_model.has_event_stream_input
                or operation_model.has_event_stream_output
            ):
                operations.append((service_model.service_name, operation_name))
    return operations


_EVENT_STREAM_OPERATIONS = _event_stream_operations()


@pytest.mark.validates_models
@pytest.mark.parametrize(
    'service_name, operation_name',
    _EVENT_STREAM_OPERATIONS,
    ids=[
        f'{service_name}-{operation_name}'
        for service_name, operation_name in _EVENT_STREAM_OPERATIONS
    ],
)
def test_no_event_stream_unless_allowed(
    service_name,
    operation_name,
    service_command_names,
    iter_operation_commands,
    cli_driver,
    record_property,
):
    command_name = service_command_names.get(service_name)
    if command_name is None:
        # The CLI does not expose this service.
        return
    # An operation can be exposed under more than one name when a
    # customization keeps a hidden alias, so check every command for it.
    commands = iter_operation_commands(cli_driver, command_name, service_name)
    full_commands = [
        f'{command_name} {sub_name}'
        for _, sub_name, _, operation_model in commands
        if operation_model.name == operation_name
    ]
    if not full_commands:
        # The CLI does not expose this operation: it is removed in
        # removals.py or replaced by a customization.
        return
    # Store the service and operation in PyTest custom properties
    record_property('aws_service', service_name)
    record_property('aws_operation', operation_name)
    disallowed = [
        full_command
        for full_command in full_commands
        if full_command not in _ALLOWED_COMMANDS
    ]
    supported_commands = '\n'.join(_ALLOWED_COMMANDS)
    assert not disallowed, (
        f'The {", ".join(disallowed)} command uses event streams '
        'which is only supported for these operations:\n'
        f'{supported_commands}'
    )
