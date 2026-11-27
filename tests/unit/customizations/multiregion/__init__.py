# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import functools

from awscli.clidriver import create_clidriver
from awscli.customizations.multiregion.pagination import get_pagination_tokens


@functools.cache
def cli_command_table():
    """The top-level CLI command table, built once for the test run."""
    return create_clidriver().subcommand_table


def get_cli_command(cli_service_name, operation_name):
    """The CLI command for a service and hyphenated subcommand name."""
    service_command = cli_command_table()[cli_service_name]
    return service_command.subcommand_table[operation_name]


def botocore_service_name(cli_service_name):
    # A few top-level commands, such as ``eventsv2``, are not named after
    # the botocore service they are bound to.
    return cli_command_table()[cli_service_name].service_model.service_name


def get_operation_model(session, cli_service_name, operation_name):
    """Load the model for a hyphenated CLI subcommand name."""
    command = get_cli_command(cli_service_name, operation_name)
    service_model = session.get_service_model(
        botocore_service_name(cli_service_name)
    )
    return service_model.operation_model(command._operation_model.name)


def is_mergeable(operation_model, response_tokens):
    """Whether a command's response can be merged across regions.

    This is the rule a command has to meet to be added to the allowlist:
    apart from pagination tokens, every member is a list of structures,
    which is concatenated and whose items each record their region.  A
    plain value or a document has nowhere certain to record its region.
    """
    output_shape = operation_model.output_shape
    if output_shape is None or output_shape.type_name != 'structure':
        return False
    data_members = [
        member
        for name, member in output_shape.members.items()
        if name not in response_tokens
    ]
    return bool(data_members) and all(
        member.type_name == 'list' and _is_structure(member.member)
        for member in data_members
    )


def _is_structure(shape):
    # A document is modeled as a structure but can hold any JSON value.
    return shape.type_name == 'structure' and not shape.is_document_type


def response_tokens(session, cli_service_name, operation_name):
    _, tokens = get_pagination_tokens(
        session,
        botocore_service_name(cli_service_name),
        get_operation_model(session, cli_service_name, operation_name),
    )
    return tokens


def output_members(operation_model):
    output_shape = operation_model.output_shape
    return {} if output_shape is None else output_shape.members
