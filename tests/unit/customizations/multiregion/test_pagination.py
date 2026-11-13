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
from argparse import Namespace

import pytest
from botocore.paginate import Paginator

from awscli.customizations.multiregion.pagination import (
    get_input_tokens,
    get_response_tokens,
    pop_pagination_tokens,
)
from tests.unit.customizations.multiregion import (
    botocore_service_name,
    get_operation_model,
    is_mergeable,
    output_members,
    response_tokens,
)


def shipped_paginator(session, cli_service_name, operation_name):
    """The paginator config as it is shipped in the CLI's data files."""
    paginator_model = session.get_paginator_model(
        botocore_service_name(cli_service_name)
    )
    operation_model = get_operation_model(
        session, cli_service_name, operation_name
    )
    return paginator_model.get_paginator(operation_model.name)


def as_name_set(value):
    """A paginator config entry is either one name or a list of names."""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    return set(value)


def aggregate_file_systems(session, file_systems, max_items):
    """Page over canned responses the way the multi-region caller does.

    The caller runs ``paginator.paginate(...).build_full_result()``, so
    the member names a merged response actually has to deal with are the
    ones botocore's aggregation produces rather than the ones the
    service model names.  ``efs describe-file-systems`` is used because
    its shipped paginator config is a plain single-key one.
    """
    config = shipped_paginator(session, 'efs', 'describe-file-systems')
    operation_model = get_operation_model(
        session, 'efs', 'describe-file-systems'
    )
    pages = [{'FileSystems': list(file_systems)}]
    paginator = Paginator(
        lambda **kwargs: pages.pop(0), config, operation_model
    )
    return paginator.paginate(
        PaginationConfig={'MaxItems': max_items}
    ).build_full_result()


@pytest.fixture(scope='module')
def resume_token_member(session):
    """The name botocore's aggregation stores a resume token under.

    It renames the service's own token, so every paginated response has
    to treat that name as pagination state whatever the model calls it.
    The name is read off a real aggregation rather than written down
    here.
    """
    truncated = aggregate_file_systems(
        session,
        [{'FileSystemId': 'fs-1'}, {'FileSystemId': 'fs-2'}],
        max_items=1,
    )
    added = set(truncated) - {'FileSystems'}
    assert len(added) == 1, truncated
    return added.pop()


class TestPopPaginationTokens:
    @pytest.mark.parametrize(
        'cli_service_name, operation_name, list_member',
        [
            ('ec2', 'describe-vpcs', 'Vpcs'),
            ('rds', 'describe-db-instances', 'DBInstances'),
            # Echoes the ``Marker`` it was called with next to the
            # ``NextMarker`` for the following page.
            ('efs', 'describe-file-systems', 'FileSystems'),
            ('kms', 'list-aliases', 'Aliases'),
        ],
    )
    def test_removes_the_real_pagination_members(
        self, session, cli_service_name, operation_name, list_member
    ):
        # The token names come from the shipped models, so this breaks if
        # a token that belongs to one region is ever printed.
        tokens = response_tokens(session, cli_service_name, operation_name)
        assert tokens
        response = dict(
            {list_member: [{'Id': 'a'}]}, **{token: 'tok' for token in tokens}
        )

        assert pop_pagination_tokens(response, tokens) is True
        assert response == {list_member: [{'Id': 'a'}]}

    @pytest.mark.parametrize('empty_token', ['', None])
    def test_an_empty_token_is_removed_but_is_not_truncation(
        self, empty_token
    ):
        # A service that always sends the member back, with nothing in
        # it, has not truncated anything.
        response = {'Vpcs': [], 'NextToken': empty_token}

        assert pop_pagination_tokens(response, {'NextToken'}) is False
        assert response == {'Vpcs': []}

    def test_keeps_a_member_that_is_not_a_token(self):
        response = {'Vpcs': [], 'OwningAccounts': ['012345678901']}

        assert pop_pagination_tokens(response, {'NextToken'}) is False
        assert response == {'Vpcs': [], 'OwningAccounts': ['012345678901']}


class TestPaginationTokens:
    PAGINATED = [
        ('ec2', 'describe-vpcs'),
        ('lambda', 'list-functions'),
        ('cloudwatch', 'list-metrics'),
        ('rds', 'describe-db-instances'),
        ('efs', 'describe-file-systems'),
        ('dynamodb', 'list-tables'),
        ('kms', 'list-aliases'),
        ('elbv2', 'describe-load-balancers'),
    ]

    @pytest.mark.parametrize('cli_service_name, operation_name', PAGINATED)
    def test_input_tokens_come_from_the_shipped_paginator_model(
        self, session, cli_service_name, operation_name
    ):
        config = shipped_paginator(session, cli_service_name, operation_name)
        operation_model = get_operation_model(
            session, cli_service_name, operation_name
        )

        tokens = get_input_tokens(
            session, botocore_service_name(cli_service_name), operation_model
        )

        assert tokens == as_name_set(config['input_token'])

    @pytest.mark.parametrize('cli_service_name, operation_name', PAGINATED)
    def test_response_tokens_come_from_the_shipped_paginator_model(
        self, session, cli_service_name, operation_name, resume_token_member
    ):
        config = shipped_paginator(session, cli_service_name, operation_name)
        expected = (
            as_name_set(config.get('output_token'))
            | as_name_set(config.get('input_token'))
            | as_name_set(config.get('more_results'))
            # The aggregation the caller pages with contributes a token
            # member of its own, under a name of its own choosing.
            | {resume_token_member}
        )

        tokens = response_tokens(session, cli_service_name, operation_name)

        assert tokens == expected

    def test_the_aggregated_resume_token_is_pagination_state(
        self, session, resume_token_member
    ):
        # A truncated listing comes back from ``build_full_result`` with
        # a resume token under a name the service model never mentions.
        # It belongs to the region that issued it, so it has to be
        # recognised as pagination state rather than merged as data.
        config = shipped_paginator(session, 'efs', 'describe-file-systems')
        assert resume_token_member != config['output_token']
        assert resume_token_member not in output_members(
            get_operation_model(session, 'efs', 'describe-file-systems')
        )
        truncated = aggregate_file_systems(
            session,
            [{'FileSystemId': 'fs-1'}, {'FileSystemId': 'fs-2'}],
            max_items=1,
        )
        complete = aggregate_file_systems(
            session, [{'FileSystemId': 'fs-1'}], max_items=10
        )
        assert resume_token_member in truncated
        assert resume_token_member not in complete

        tokens = response_tokens(session, 'efs', 'describe-file-systems')

        assert resume_token_member in tokens
        assert pop_pagination_tokens(truncated, tokens) is True
        assert truncated == {'FileSystems': [{'FileSystemId': 'fs-1'}]}

    def test_an_echoed_input_token_is_pagination_state(self, session):
        # ``efs describe-file-systems`` returns the ``Marker`` it was
        # called with next to the ``NextMarker`` for the following page.
        # Both are pagination state, so the response is still mergeable.
        config = shipped_paginator(session, 'efs', 'describe-file-systems')
        operation_model = get_operation_model(
            session, 'efs', 'describe-file-systems'
        )
        members = output_members(operation_model)
        assert config['input_token'] != config['output_token']
        assert config['input_token'] in members
        assert config['output_token'] in members

        tokens = response_tokens(session, 'efs', 'describe-file-systems')

        assert config['input_token'] in tokens
        assert is_mergeable(operation_model, tokens) is True
        assert (
            is_mergeable(operation_model, tokens - {config['input_token']})
            is False
        )

    def test_a_more_results_member_is_pagination_state(self, session):
        # ``kms list-aliases`` reports whether there is another page with
        # a boolean whose name looks nothing like a token, so only the
        # paginator model can identify it, and the response is mergeable
        # only because it does.
        config = shipped_paginator(session, 'kms', 'list-aliases')
        operation_model = get_operation_model(session, 'kms', 'list-aliases')
        more_results = config['more_results']
        assert output_members(operation_model)[more_results].type_name == (
            'boolean'
        )

        tokens = response_tokens(session, 'kms', 'list-aliases')

        assert more_results in tokens
        assert is_mergeable(operation_model, tokens) is True
        assert is_mergeable(operation_model, tokens - {more_results}) is False

    def test_tokens_are_taken_from_the_model_not_from_member_names(
        self, session, resume_token_member
    ):
        # ``dynamodb list-tables`` paginates with members whose names
        # look nothing like a token, so only the paginator model can
        # identify them.
        config = shipped_paginator(session, 'dynamodb', 'list-tables')
        operation_model = get_operation_model(
            session, 'dynamodb', 'list-tables'
        )
        for name in (config['input_token'], config['output_token']):
            assert 'Token' not in name
            assert 'Marker' not in name

        tokens = response_tokens(session, 'dynamodb', 'list-tables')

        assert tokens == {
            config['input_token'],
            config['output_token'],
            resume_token_member,
        }
        assert set(output_members(operation_model)) - tokens == {'TableNames'}

    def test_no_tokens_without_a_paginator_model(self, session):
        # Token names are never guessed from member names; the allowlist
        # only has commands without a paginator model that take no token.
        with pytest.raises(ValueError):
            shipped_paginator(session, 'apigatewayv2', 'get-vpc-links')
        operation_model = get_operation_model(
            session, 'apigatewayv2', 'get-vpc-links'
        )
        assert 'NextToken' in output_members(operation_model)

        assert response_tokens(session, 'apigatewayv2', 'get-vpc-links') == (
            frozenset()
        )
        assert get_input_tokens(session, 'apigatewayv2', operation_model) == (
            frozenset()
        )

    def test_no_tokens_for_an_unpaginated_operation(self, session):
        # ``sts get-caller-identity`` has no paginator model either, and
        # none of its members looks like a token, so the fallback finds
        # nothing rather than guessing.
        with pytest.raises(ValueError):
            shipped_paginator(session, 'sts', 'get-caller-identity')
        operation_model = get_operation_model(
            session, 'sts', 'get-caller-identity'
        )
        assert output_members(operation_model)

        assert (
            get_response_tokens(session, 'sts', operation_model) == frozenset()
        )
        assert get_input_tokens(session, 'sts', operation_model) == frozenset()
