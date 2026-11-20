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

from awscli.customizations.multiregion.allowlist import is_eligible
from awscli.customizations.multiregion.arguments import (
    MULTI_REGIONS_NAME,
    MultiRegionsArgument,
)


def register_multi_region(event_handlers):
    event_handlers.register(
        'building-argument-table', add_multi_regions_argument
    )


def add_multi_regions_argument(session, argument_table, command, **kwargs):
    """Add ``--multi-regions`` to the commands in the allowlist."""
    if not is_eligible(command._parent_name, command.name):
        return
    if MULTI_REGIONS_NAME in argument_table:
        raise ValueError(
            f'aws {command._parent_name} {command.name} already has a '
            f'--{MULTI_REGIONS_NAME} option; remove the command from '
            'ALLOWED_OPERATIONS.'
        )
    argument = MultiRegionsArgument(session, command)
    argument.add_to_arg_table(argument_table)
