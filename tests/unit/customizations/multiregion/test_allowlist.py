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
import re

import pytest

from awscli.clidriver import create_clidriver
from awscli.customizations.multiregion.allowlist import (
    ALLOWED_OPERATIONS,
    is_eligible,
)
from awscli.customizations.multiregion.arguments import (
    MULTI_REGIONS_NAME,
    MultiRegionsArgument,
)
from awscli.customizations.multiregion.pagination import get_response_tokens
from awscli.customizations.paginate import get_paginator_config
from tests.unit.customizations.multiregion import is_mergeable


def allowlist_entries():
    return [
        (cli_service_name, operation_name)
        for cli_service_name, operations in sorted(ALLOWED_OPERATIONS.items())
        for operation_name in sorted(operations)
    ]


@pytest.fixture(scope='module')
def cli_command_table():
    return create_clidriver().subcommand_table


def get_command(cli_command_table, cli_service_name, operation_name):
    service = cli_command_table[cli_service_name]
    return service.subcommand_table[operation_name]


@pytest.mark.parametrize(
    'cli_service_name, operation_name', allowlist_entries()
)
def test_allowlisted_command_can_be_merged(
    session, cli_command_table, cli_service_name, operation_name
):
    """Every entry names a real command whose response can be merged."""
    assert cli_service_name in cli_command_table
    command = get_command(cli_command_table, cli_service_name, operation_name)
    operation_model = command._operation_model
    tokens = get_response_tokens(
        session, operation_model.service_model.service_name, operation_model
    )
    assert is_mergeable(operation_model, tokens)


@pytest.mark.parametrize(
    'cli_service_name, operation_name', allowlist_entries()
)
def test_allowlisted_command_has_no_multi_regions_option_of_its_own(
    cli_command_table, cli_service_name, operation_name
):
    # Building the argument table raises if the command already defines
    # the option, for example after a service adds a parameter of that
    # name.
    command = get_command(cli_command_table, cli_service_name, operation_name)
    argument = command.arg_table[MULTI_REGIONS_NAME]
    assert isinstance(argument, MultiRegionsArgument)


@pytest.mark.parametrize(
    'cli_service_name, operation_name', allowlist_entries()
)
def test_allowlisted_command_can_be_paged(
    session, cli_command_table, cli_service_name, operation_name
):
    # A command the service paginates but botocore has no paginator model
    # for cannot be paged with --starting-token.  Token names are only
    # guessed here, so a wrong guess fails this test instead of shipping.
    command = get_command(cli_command_table, cli_service_name, operation_name)
    operation_model = command._operation_model
    service_name = operation_model.service_model.service_name
    if get_paginator_config(session, service_name, operation_model.name):
        return
    input_shape = operation_model.input_shape
    members = input_shape.members if input_shape else {}
    assert not [
        name for name in members if re.search(r'(Token|Marker)s?$', name, re.I)
    ]


@pytest.mark.parametrize(
    'cli_service_name, operation_name', allowlist_entries()
)
def test_allowlisted_command_takes_no_required_input(
    cli_command_table, cli_service_name, operation_name
):
    command = get_command(cli_command_table, cli_service_name, operation_name)
    input_shape = command._operation_model.input_shape
    assert input_shape is None or not input_shape.required_members


@pytest.mark.parametrize(
    'cli_service_name, operation_name',
    [
        # Mutating.
        ('ec2', 'terminate-instances'),
        ('lambda', 'delete-function'),
        # Credentials, secrets and pre-signed URLs.
        ('sts', 'get-session-token'),
        ('dataexchange', 'list-jobs'),
        ('ecr', 'get-authorization-token'),
        ('secretsmanager', 'get-secret-value'),
        ('datazone', 'list-connections'),
        ('mailmanager', 'list-address-list-import-jobs'),
        # Global or account-wide.
        ('iam', 'list-users'),
        ('s3api', 'list-buckets'),
        ('controlcatalog', 'list-controls'),
        # Data-plane reads, some of them marked ``readonly`` by the model.
        ('dynamodb', 'scan'),
        ('sqs', 'receive-message'),
        ('s3vectors', 'get-vectors'),
        ('qconnect', 'list-messages'),
    ],
)
def test_command_that_is_not_allowlisted_is_rejected(
    cli_service_name, operation_name
):
    assert not is_eligible(cli_service_name, operation_name)


@pytest.mark.parametrize(
    'cli_service_name, operation_name',
    [
        # The same account-wide data in every region.
        ('ec2', 'describe-regions'),
        # A multi-region trail is returned by every region it covers.
        ('cloudtrail', 'describe-trails'),
        ('cloudtrail', 'list-trails'),
        # System tables are enabled for the whole account.
        ('athena', 'list-system-table-statuses'),
        # One landing zone per account, and the call can create its ARN.
        ('controltower', 'list-landing-zones'),
        # Catalogs provided by AWS rather than the account's resources.
        ('controltower', 'list-baselines'),
        ('resiliencehubv2', 'list-test-templates'),
        # Without filters, every public image or snapshot in the region.
        ('ec2', 'describe-images'),
        ('ec2', 'describe-snapshots'),
    ],
)
def test_command_returning_the_same_data_everywhere_is_not_eligible(
    cli_service_name, operation_name
):
    assert not is_eligible(cli_service_name, operation_name)


@pytest.mark.parametrize(
    'cli_service_name, operation_name',
    [
        # One of several identifier members has to be given, although the
        # model marks none of them as required.
        ('elbv2', 'describe-listeners'),
        ('elbv2', 'describe-rules'),
        ('logs', 'describe-log-streams'),
        ('odb', 'list-db-nodes'),
        # Without --clusters it only describes the "default" cluster.
        ('ecs', 'describe-clusters'),
    ],
)
def test_command_requiring_one_of_several_identifiers_is_not_eligible(
    cli_service_name, operation_name
):
    assert not is_eligible(cli_service_name, operation_name)
