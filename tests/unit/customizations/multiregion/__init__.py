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
from botocore import xform_name

from awscli.customizations.multiregion.pagination import get_response_tokens

# A few top-level CLI commands are not named after the botocore service
# they are bound to.  The multi-region rules are keyed by the name the
# user types, while the model has to be looked up under the botocore name.
CLI_TO_BOTOCORE_SERVICE_NAME = {
    'agent-toolkit': 'agenttoolkit',
    'eventsv2': 'eventbridgev2',
    's3api': 's3',
}


def botocore_service_name(cli_service_name):
    return CLI_TO_BOTOCORE_SERVICE_NAME.get(cli_service_name, cli_service_name)


def modeled_operation_names(service_model):
    """Map hyphenated CLI subcommand names to modeled operation names."""
    return {
        xform_name(name, '-'): name for name in service_model.operation_names
    }


def get_operation_model(session, cli_service_name, operation_name):
    """Load the model for a hyphenated CLI subcommand name."""
    service_model = session.get_service_model(
        botocore_service_name(cli_service_name)
    )
    modeled_name = modeled_operation_names(service_model)[operation_name]
    return service_model.operation_model(modeled_name)


def is_mergeable(operation_model, response_tokens):
    """Whether a command's response can be merged across regions.

    This is the rule a command has to meet to be added to the allowlist:
    apart from pagination tokens, every member is a list of objects, which
    is concatenated, or an object, which becomes a list with one entry per
    region.  An object is a structure or a map; a plain value or a
    document has nowhere certain to record its region.
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
        _is_object(member.member if member.type_name == 'list' else member)
        for member in data_members
    )


def _is_object(shape):
    # A document is modeled as a structure but can hold any JSON value.
    return shape.type_name == 'map' or (
        shape.type_name == 'structure' and not shape.is_document_type
    )


def response_tokens(session, cli_service_name, operation_name):
    return get_response_tokens(
        session,
        botocore_service_name(cli_service_name),
        get_operation_model(session, cli_service_name, operation_name),
    )


def output_members(operation_model):
    output_shape = operation_model.output_shape
    return {} if output_shape is None else output_shape.members
