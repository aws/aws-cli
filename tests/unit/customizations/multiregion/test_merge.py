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

from awscli.compat import StringIO
from awscli.customizations.multiregion.merge import (
    REGION_SCOPE_KEY,
    SCOPE_KEY,
    annotate_response,
    merge_responses,
)
from awscli.formatter import YAMLFormatter
from tests.unit.customizations.multiregion import (
    get_operation_model,
    is_mergeable,
    output_members,
    response_tokens,
)

EAST = 'us-east-1'
WEST = 'eu-west-1'


def scope(region):
    return {REGION_SCOPE_KEY: region}


def collect_scopes(value, found=None):
    """Collect every ``_CliScope`` dict nested anywhere in ``value``."""
    if found is None:
        found = []
    if isinstance(value, dict):
        for key, member in value.items():
            if key == SCOPE_KEY:
                found.append(member)
            else:
                collect_scopes(member, found)
    elif isinstance(value, list):
        for element in value:
            collect_scopes(element, found)
    return found


def dump_yaml(response):
    formatter = YAMLFormatter(Namespace(query=None))
    stream = StringIO()
    formatter('DescribeVpcs', response, stream)
    return stream.getvalue()


def get_output_shape(session, cli_service_name, operation_name):
    return get_operation_model(
        session, cli_service_name, operation_name
    ).output_shape


def member_shape(shape, path):
    """The shape of a member path such as ``Reservations[].Instances[]``."""
    current = shape
    for step in path.split('.'):
        if step.endswith('[]'):
            current = current.members[step[:-2]]
            assert current.type_name == 'list', path
            current = current.member
        else:
            current = current.members[step]
    return current


def modeled_list_members(operation_model):
    """Output member names that are lists, taken from the model."""
    return {
        name
        for name, member in output_members(operation_model).items()
        if member.type_name == 'list'
    }


class TestAnnotateResponse:
    def test_labels_each_object_of_a_top_level_list(self):
        annotated = annotate_response(
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}, EAST
        )
        assert annotated == {
            'Vpcs': [
                {'VpcId': 'vpc-1', SCOPE_KEY: scope(EAST)},
                {'VpcId': 'vpc-2', SCOPE_KEY: scope(EAST)},
            ]
        }

    def test_labels_a_top_level_object(self):
        # A structure, a map or a document object alike.
        annotated = annotate_response(
            {'Table': {'TableName': 't'}, 'Tags': {'env': 'prod'}}, EAST
        )
        assert annotated == {
            'Table': {'TableName': 't', SCOPE_KEY: scope(EAST)},
            'Tags': {'env': 'prod', SCOPE_KEY: scope(EAST)},
        }

    def test_does_not_label_nested_objects(self):
        # Only the top layer: a nested list keeps its objects as they are.
        response = {
            'Reservations': [
                {
                    'ReservationId': 'r-1',
                    'Instances': [
                        {'InstanceId': 'i-1', 'Tags': [{'Key': 'k'}]}
                    ],
                }
            ]
        }

        annotated = annotate_response(response, EAST)

        reservation = annotated['Reservations'][0]
        assert reservation[SCOPE_KEY] == scope(EAST)
        assert reservation['Instances'] == [
            {'InstanceId': 'i-1', 'Tags': [{'Key': 'k'}]}
        ]

    def test_leaves_a_null_list_element_alone(self):
        annotated = annotate_response({'Vpcs': [None]}, EAST)
        assert annotated == {'Vpcs': [None]}

    def test_does_not_label_the_response_itself(self):
        assert SCOPE_KEY not in annotate_response({'Vpcs': []}, EAST)

    def test_does_not_mutate_its_input(self):
        vpc = {'VpcId': 'vpc-1'}
        response = {'Vpcs': [vpc]}

        annotate_response(response, EAST)

        assert response == {'Vpcs': [{'VpcId': 'vpc-1'}]}

    def test_every_labelled_object_gets_its_own_scope_dict(self):
        annotated = annotate_response(
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}, EAST
        )
        first, second = annotated['Vpcs']
        assert first[SCOPE_KEY] is not second[SCOPE_KEY]


class TestScopeDictsAreDistinctObjects:
    """A shared ``_CliScope`` dict makes YAML emit anchors and aliases."""

    def test_annotated_response_has_no_yaml_anchors_or_aliases(self):
        # Two objects with identical scope contents are the case a shared
        # dict would collapse into an anchor and an alias.
        annotated = annotate_response(
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}, EAST
        )

        output = dump_yaml(annotated)

        assert '&id' not in output
        assert '*id' not in output
        assert output.count(EAST) == 2


class TestMergeResponses:
    def test_concatenates_lists_in_the_order_the_regions_were_called(self):
        east = annotate_response(
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}, EAST
        )
        west = annotate_response({'Vpcs': [{'VpcId': 'vpc-3'}]}, WEST)

        assert merge_responses([west, east]) == {
            'Vpcs': [
                {'VpcId': 'vpc-3', SCOPE_KEY: scope(WEST)},
                {'VpcId': 'vpc-1', SCOPE_KEY: scope(EAST)},
                {'VpcId': 'vpc-2', SCOPE_KEY: scope(EAST)},
            ]
        }

    def test_concatenates_scalar_list_members(self):
        responses = [
            {'Identities': ['example.com']},
            {'Identities': ['example.net', 'example.org']},
        ]
        assert merge_responses(responses) == {
            'Identities': ['example.com', 'example.net', 'example.org']
        }

    def test_merges_empty_lists_into_an_empty_list(self):
        assert merge_responses([{'Vpcs': []}, {'Vpcs': []}]) == {'Vpcs': []}

    def test_keeps_a_member_present_in_only_some_regions(self):
        responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}]},
            {'Vpcs': [{'VpcId': 'vpc-2'}], 'Extra': [{'Id': 'e'}]},
        ]
        assert merge_responses(responses) == {
            'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}],
            'Extra': [{'Id': 'e'}],
        }

    def test_turns_a_structure_into_a_list_with_one_element_per_region(self):
        east = annotate_response({'Table': {'TableName': 't'}}, EAST)
        west = annotate_response({'Table': {'TableName': 't'}}, WEST)

        assert merge_responses([east, west]) == {
            'Table': [
                {'TableName': 't', SCOPE_KEY: scope(EAST)},
                {'TableName': 't', SCOPE_KEY: scope(WEST)},
            ]
        }

    def test_no_responses_merge_to_an_empty_response(self):
        assert merge_responses([]) == {}


MERGEABLE_OPERATIONS = [
    ('ec2', 'describe-vpcs'),
    ('ec2', 'describe-instances'),
    ('lambda', 'list-functions'),
    ('rds', 'describe-db-instances'),
    # The response echoes the ``Marker`` the request was given, which
    # has to be tolerated as pagination state.
    ('efs', 'describe-file-systems'),
]

# Each region's single object becomes one element of a list.
SINGLE_STRUCTURE_OPERATIONS = [
    ('dynamodb', 'describe-table'),
    ('kms', 'describe-key'),
    ('eks', 'describe-cluster'),
    ('acm', 'describe-certificate'),
]

# A plain value has nowhere to record its region.
UNMERGEABLE_OPERATIONS = [
    ('secretsmanager', 'describe-secret'),
    ('sts', 'get-caller-identity'),
]


class TestIsMergeable:
    """The rule for adding a command to the allowlist, against the models."""

    @pytest.mark.parametrize(
        'cli_service_name, operation_name', MERGEABLE_OPERATIONS
    )
    def test_list_response_is_mergeable(
        self, session, cli_service_name, operation_name
    ):
        operation_model = get_operation_model(
            session, cli_service_name, operation_name
        )
        tokens = response_tokens(session, cli_service_name, operation_name)
        # Arrange check: the response really is made of lists plus
        # pagination state, which is what makes it mergeable.
        assert modeled_list_members(operation_model)
        assert (
            set(output_members(operation_model))
            - modeled_list_members(operation_model)
            <= tokens
        )
        assert is_mergeable(operation_model, tokens) is True

    @pytest.mark.parametrize(
        'cli_service_name, operation_name', SINGLE_STRUCTURE_OPERATIONS
    )
    def test_single_structure_response_is_mergeable(
        self, session, cli_service_name, operation_name
    ):
        operation_model = get_operation_model(
            session, cli_service_name, operation_name
        )
        tokens = response_tokens(session, cli_service_name, operation_name)
        members = output_members(operation_model)
        assert any(
            members[name].type_name == 'structure'
            for name in set(members) - tokens
        )
        assert is_mergeable(operation_model, tokens) is True

    @pytest.mark.parametrize(
        'cli_service_name, operation_name', UNMERGEABLE_OPERATIONS
    )
    def test_scalar_member_response_is_not_mergeable(
        self, session, cli_service_name, operation_name
    ):
        operation_model = get_operation_model(
            session, cli_service_name, operation_name
        )
        tokens = response_tokens(session, cli_service_name, operation_name)
        # Arrange check: at least one member is a scalar that is not
        # pagination state, so no merge keeps every region's data.
        assert (
            set(output_members(operation_model))
            - modeled_list_members(operation_model)
            - tokens
        )
        assert is_mergeable(operation_model, tokens) is False

    @pytest.mark.parametrize(
        'cli_service_name, operation_name, member',
        [
            ('ses', 'list-identities', 'Identities'),
            ('dynamodb', 'list-tables', 'TableNames'),
        ],
    )
    def test_list_of_plain_values_is_not_mergeable(
        self, session, cli_service_name, operation_name, member
    ):
        # The names could not say which region each came from.
        operation_model = get_operation_model(
            session, cli_service_name, operation_name
        )
        names = output_members(operation_model)[member]
        assert names.member.type_name == 'string'
        tokens = response_tokens(session, cli_service_name, operation_name)
        assert is_mergeable(operation_model, tokens) is False

    def test_map_member_is_mergeable(self, session):
        # ``lambda list-tags`` returns a map of tags, which becomes a list
        # with one labelled map per region.
        operation_model = get_operation_model(session, 'lambda', 'list-tags')
        tags = output_members(operation_model)['Tags']
        assert tags.type_name == 'map'
        tokens = response_tokens(session, 'lambda', 'list-tags')
        assert is_mergeable(operation_model, tokens) is True

    def test_a_list_of_maps_is_mergeable(self, session):
        # The lists can be concatenated, and each map labelled.
        operation_model = get_operation_model(
            session, 'ssm', 'describe-patch-properties'
        )
        properties = output_members(operation_model)['Properties']
        assert properties.type_name == 'list'
        assert properties.member.type_name == 'map'
        tokens = response_tokens(session, 'ssm', 'describe-patch-properties')

        assert is_mergeable(operation_model, tokens) is True

    def test_response_with_no_output_shape_is_not_mergeable(self, session):
        operation_model = get_operation_model(session, 'sqs', 'delete-queue')
        assert operation_model.output_shape is None
        assert is_mergeable(operation_model, frozenset()) is False
