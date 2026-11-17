# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.clidriver import create_clidriver
from tests import ALL_SERVICES


def _all_operations():
    return [
        (model.service_name, name)
        for model in ALL_SERVICES
        for name in model.operation_names
    ]


class _ShadowingIndex:
    def __init__(self, command_names, iter_operation_commands):
        self.builtins = set(create_clidriver().create_help_command().arg_table)
        self._command_names = command_names
        self._iter_operation_commands = iter_operation_commands
        self._services = {}

    def lookup(self, service_name, operation_name):
        # Returns a list of (command_name, sub_name, arg_names) for every
        # command exposing the operation, which is empty when the CLI does
        # not expose it. A customization can keep a hidden alias, so there
        # may be more than one.
        if service_name not in self._services:
            self._services[service_name] = self._index_service(service_name)
        return self._services[service_name].get(operation_name, [])

    def _index_service(self, service_name):
        command_name = self._command_names.get(service_name)
        if command_name is None:
            return {}
        # A fresh driver per service keeps command tables from accumulating
        # across services. Only strings are kept once it is discarded.
        driver = create_clidriver()
        operations = {}
        commands = self._iter_operation_commands(
            driver, command_name, service_name
        )
        for _, sub_name, sub_command, operation_model in commands:
            operations.setdefault(operation_model.name, []).append(
                (command_name, sub_name, tuple(sub_command.arg_table))
            )
        return operations


@pytest.fixture(scope='module')
def shadowing_index(service_command_names, iter_operation_commands):
    return _ShadowingIndex(service_command_names, iter_operation_commands)


_ALL_OPERATIONS = _all_operations()


@pytest.mark.validates_models
@pytest.mark.parametrize(
    'service_name, operation_name',
    _ALL_OPERATIONS,
    ids=[
        f'{service_name}-{operation_name}'
        for service_name, operation_name in _ALL_OPERATIONS
    ],
)
def test_no_shadowed_builtins(
    service_name, operation_name, shadowing_index, record_property
):
    """Verify no command params are shadowed or prefixed by the built-in param.

    The CLI parses all command line options into a single namespace.
    This means that option names must be unique and cannot conflict
    with the top level params.

    For example, there's a top level param ``--version``.  If an
    operation for a service also provides a ``--version`` option,
    it can never be called because we'll assume the user meant
    the top level ``--version`` param.

    Beyond just direct shadowing, a param which prefixes a builtin
    is also effectively shadowed because argparse will expand
    prefixes of arguments. So `--end` would expand to `--endpoint-url`
    for instance.

    In order to ensure this doesn't happen, this test will go
    through every command table and ensure we're not shadowing
    any builtins.

    Each test case covers a single operation, so a failure reports
    every shadowed option of that operation and records exactly one
    service and operation.

    """
    exposed = shadowing_index.lookup(service_name, operation_name)
    if not exposed:
        # The CLI does not expose this operation.
        return
    # Store the service and operation in PyTest custom properties
    record_property('aws_service', service_name)
    record_property('aws_operation', operation_name)
    errors = []
    for command_name, sub_name, arg_names in exposed:
        shadowed = [
            arg_name
            for arg_name in arg_names
            if any(p.startswith(arg_name) for p in shadowing_index.builtins)
        ]
        errors.extend(
            'Shadowing/Prefixing a top level option: '
            f'{command_name}.{sub_name}.{arg_name}'
            for arg_name in shadowed
        )
    if errors:
        raise AssertionError('\n' + '\n'.join(errors))
