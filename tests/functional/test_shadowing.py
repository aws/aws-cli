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
from botocore.model import OperationModel

from awscli.clidriver import create_clidriver


def _walk_command_tree(command_path, command_obj):
    """Yield ``(command_path, help_command)`` for a command and every
    descendant.

    Services expose operations two levels deep, but customizations inject
    commands at other depths (for example ``aws <service> wait <waiter>``),
    and not every command is backed by an ``OperationModel``.  We recurse
    the full command tree so that every command's options are audited.
    """
    help_command = command_obj.create_help_command()
    yield command_path, help_command
    for sub_name, sub_command in getattr(
        help_command, 'command_table', {}
    ).items():
        # ``help`` is a synthetic command available in every command table.
        if sub_name == 'help':
            continue
        yield from _walk_command_tree(
            f'{command_path}.{sub_name}', sub_command
        )


def _generate_command_tests():
    driver = create_clidriver()
    help_command = driver.create_help_command()
    top_level_params = set(driver.create_help_command().arg_table.keys())
    for command_name, command_obj in list(help_command.command_table.items()):
        if command_name == 'help':
            continue
        for command_path, sub_help in _walk_command_tree(
            command_name, command_obj
        ):
            arg_table = getattr(sub_help, 'arg_table', None)
            if not arg_table:
                continue
            model = getattr(sub_help, 'obj', None)
            if isinstance(model, OperationModel):
                service_name = model.service_model.service_name
                operation_name = model.name
            else:
                service_name = command_name
                operation_name = None
            yield (
                command_path,
                service_name,
                operation_name,
                arg_table,
                top_level_params,
            )


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "command_path, service_name, operation_name, arg_table, builtins",
    _generate_command_tests(),
)
def test_no_shadowed_builtins(
    command_path,
    service_name,
    operation_name,
    arg_table,
    builtins,
    record_property,
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
    through every command in the command tree, at every depth and
    including customizations, and ensure we're not shadowing any
    builtins.  Because each command's options are checked against
    the current builtins, this also catches a newly added builtin
    that would shadow an existing command option.

    Note that a builtin which is a prefix of a longer command option
    (e.g. ``--region`` and ``--region-name``) is not flagged: the
    command option is still reachable by its full name.

    Also, rather than being a test generator, we're going to just
    aggregate all the failures in one pass and surface them as
    a single test failure.

    """
    errors = []
    for arg_name in arg_table:
        if any(p.startswith(arg_name) for p in builtins):
            # Then we are shadowing or prefixing a top level argument
            errors.append(
                'Shadowing/Prefixing a top level option: '
                f'{command_path}.{arg_name}'
            )
    if errors:
        # Store the service and operation in
        # PyTest custom properties
        record_property('aws_service', service_name)
        record_property('aws_operation', operation_name)
        raise AssertionError('\n' + '\n'.join(errors))
