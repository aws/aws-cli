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


def _generate_command_tests():
    driver = create_clidriver()
    help_command = driver.create_help_command()
    top_level_params = set(driver.create_help_command().arg_table)
    for command_name, command_obj in help_command.command_table.items():
        sub_help = command_obj.create_help_command()
        if hasattr(sub_help, 'command_table'):
            yield command_name, sub_help.command_table, top_level_params

@pytest.mark.validates_models
@pytest.mark.parametrize(
    "command_name, command_table, builtins",
    _generate_command_tests()
)
def test_no_shadowed_builtins(command_name, command_table, builtins):
    """Verify no command params are shadowed or prefixed by the built in param.

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

    Also, rather than being a test generator, we're going to just
    aggregate all the failures in one pass and surface them as
    a single test failure.

    """
    errors = []
    for sub_name, sub_command in command_table.items():
        op_help = sub_command.create_help_command()
        arg_table = op_help.arg_table
        for arg_name in arg_table:
            if any(p.startswith(arg_name) for p in builtins):
                # Then we are shadowing or prefixing a top level argument
                errors.append(
                    'Shadowing/Prefixing a top level option: '
                    '%s.%s.%s' % (command_name, sub_name, arg_name))
    if errors:
        raise AssertionError('\n' + '\n'.join(errors))
