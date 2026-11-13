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
import argparse
from unittest import mock

import botocore.session
import pytest

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.multiregion import add_multi_regions_argument
from awscli.customizations.multiregion.arguments import (
    MULTI_REGIONS_DEST,
    MULTI_REGIONS_NAME,
    MultiRegionsArgument,
)
from awscli.customizations.multiregion.caller import (
    MultiRegionOperationCaller,
)
from awscli.customizations.multiregion.pagination import get_input_tokens
from awscli.customizations.multiregion.validation import (
    MultiRegionSpec,
    parse_multi_regions,
    validate_call_parameters,
    validate_options,
)


def operation_model(session, service_name, operation_name):
    return session.get_service_model(service_name).operation_model(
        operation_name
    )


def input_tokens_for(session, service_name, operation_name):
    """The operation's modeled pagination input token names.

    These are read out of the shipped paginator/service models, the same
    way the CLI driver reads them, rather than restated from a list kept
    in the CLI's own source.
    """
    return get_input_tokens(
        session,
        service_name,
        operation_model(session, service_name, operation_name),
    )


def globals_with(**kwargs):
    defaults = {'region': None, 'endpoint_url': None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def args_with(**kwargs):
    defaults = {'starting_token': None, 'generate_cli_skeleton': None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class FakeOperationCommand:
    """Stand-in for :class:`awscli.clidriver.ServiceOperation`.

    ``building-argument-table`` is emitted with the command object
    itself; the customization reads the command's name, its parent
    (service) name, and the operation and caller it runs in every region.
    """

    def __init__(self, parent_name, name):
        self.name = name
        self._parent_name = parent_name
        self._operation_model = mock.Mock()
        self._operation_caller = mock.Mock()


def make_argument(session):
    return MultiRegionsArgument(
        session, FakeOperationCommand('ec2', 'describe-vpcs')
    )


def build_argument_table(
    session,
    service_name,
    modeled_operation_name,
    cli_operation_name,
    argument_table=None,
):
    """Call the handler with the arguments the real event provides."""
    if argument_table is None:
        argument_table = {}
    command = FakeOperationCommand(service_name, cli_operation_name)
    add_multi_regions_argument(
        session=session,
        operation_model=operation_model(
            session, service_name, modeled_operation_name
        ),
        argument_table=argument_table,
        command=command,
    )
    return argument_table


class TestMultiRegionSpec:
    def test_no_regions_means_all(self):
        assert MultiRegionSpec().is_all is True

    def test_explicit_regions_are_a_tuple(self):
        spec = MultiRegionSpec(regions=['us-east-1', 'eu-west-1'])
        assert spec.regions == ('us-east-1', 'eu-west-1')
        assert spec.is_all is False

    def test_repr_shows_regions(self):
        spec = MultiRegionSpec(['us-east-1'])
        assert repr(spec) == "MultiRegionSpec(regions=('us-east-1',))"


class TestParseMultiRegions:
    def test_all_has_no_explicit_regions(self):
        spec = parse_multi_regions('all')
        assert spec.is_all is True
        assert spec.regions == ()

    def test_explicit_list_keeps_order(self):
        spec = parse_multi_regions('eu-west-1,us-east-1')
        assert spec.is_all is False
        assert spec.regions == ('eu-west-1', 'us-east-1')

    def test_whitespace_around_names_is_stripped(self):
        spec = parse_multi_regions('us-east-1 , eu-west-1')
        assert spec.regions == ('us-east-1', 'eu-west-1')

    def test_repeated_region_is_only_listed_once(self):
        # A region named twice is only called once, and the first
        # occurrence keeps its place in the order.
        spec = parse_multi_regions('us-east-1,eu-west-1,us-east-1')
        assert spec.regions == ('us-east-1', 'eu-west-1')

    def test_does_not_validate(self):
        spec = parse_multi_regions('all,not-a-region,')
        assert spec.regions == ('all', 'not-a-region', '')


def validate(value, session, parsed_globals=None):
    validate_options(
        parse_multi_regions(value), parsed_globals or globals_with(), session
    )


class TestValidateOptions:
    @pytest.mark.parametrize(
        'value',
        [
            'all',
            'us-east-1',
            'eu-west-1,us-east-1',
            'cn-north-1,cn-northwest-1',
            'us-gov-west-1,us-gov-east-1',
        ],
    )
    def test_valid_value_is_accepted(self, session, value):
        validate(value, session)

    def test_region_not_yet_in_shipped_region_list_is_accepted(self, session):
        # A name that matches the partition's regionRegex but that the
        # shipped endpoint data does not know about is deliberately
        # accepted so that a brand new region works before the CLI data
        # catches up.
        assert 'us-east-99' not in session.get_available_regions('ec2')
        validate('us-east-99', session)

    @pytest.mark.parametrize(
        'value, message',
        [
            ('us-east-1,', 'the region list has an empty entry'),
            ('', 'the region list has an empty entry'),
            ('not-a-region', '"not-a-region" is not a valid region name.'),
            (
                'us-east-1,cn-north-1',
                'all regions must be in the same partition (us-east-1 is '
                'in "aws", cn-north-1 is in "aws-cn").',
            ),
            (
                'all,us-east-1',
                '"all" cannot be combined with explicit region names.',
            ),
        ],
    )
    def test_invalid_value_is_rejected(self, session, value, message):
        with pytest.raises(ParamValidationError) as excinfo:
            validate(value, session)
        assert f'--multi-regions: {message}' in str(excinfo.value)

    @pytest.mark.parametrize(
        'parsed_globals, option',
        [
            (globals_with(region='us-east-1'), '--region'),
            (globals_with(endpoint_url='https://localhost'), '--endpoint-url'),
        ],
    )
    def test_conflicting_option_is_rejected(
        self, session, parsed_globals, option
    ):
        with pytest.raises(ParamValidationError) as excinfo:
            validate('us-east-1', session, parsed_globals)
        assert str(excinfo.value) == (
            f'{option} cannot be used together with --multi-regions.'
        )


class TestValidateCallParameters:
    def test_modeled_input_token_is_rejected(self, session):
        input_tokens = input_tokens_for(session, 'ec2', 'DescribeVpcs')
        assert input_tokens == frozenset(['NextToken'])
        with pytest.raises(ParamValidationError) as excinfo:
            validate_call_parameters({'NextToken': 'token'}, input_tokens)
        assert str(excinfo.value) == (
            'NextToken cannot be used together with --multi-regions '
            'because pagination tokens are specific to one region.'
        )

    def test_modeled_input_token_is_rejected_among_other_parameters(
        self, session
    ):
        input_tokens = input_tokens_for(session, 'dynamodb', 'ListTables')
        assert input_tokens == frozenset(['ExclusiveStartTableName'])
        with pytest.raises(ParamValidationError) as excinfo:
            validate_call_parameters(
                {'Limit': 5, 'ExclusiveStartTableName': 'widgets'},
                input_tokens,
            )
        assert 'ExclusiveStartTableName cannot be used together with ' in str(
            excinfo.value
        )

    def test_ordinary_parameters_pass(self, session):
        input_tokens = input_tokens_for(session, 'ec2', 'DescribeVpcs')
        assert (
            validate_call_parameters(
                {'VpcIds': ['vpc-1'], 'MaxResults': 5, 'DryRun': False},
                input_tokens,
            )
            is None
        )

    def test_empty_parameters_pass(self, session):
        input_tokens = input_tokens_for(session, 'ec2', 'DescribeVpcs')
        assert validate_call_parameters({}, input_tokens) is None

    def test_pagination_config_without_a_token_passes(self, session):
        input_tokens = input_tokens_for(session, 'ec2', 'DescribeVpcs')
        assert (
            validate_call_parameters(
                {'PaginationConfig': {'PageSize': 10, 'MaxItems': 100}},
                input_tokens,
            )
            is None
        )

    def test_token_of_another_operation_passes(self, session):
        # ``Marker`` paginates ``lambda list-functions`` but means
        # nothing to ``ec2 describe-vpcs``, so only the tokens this
        # operation models are rejected.
        input_tokens = input_tokens_for(session, 'ec2', 'DescribeVpcs')
        assert 'Marker' in input_tokens_for(session, 'lambda', 'ListFunctions')
        assert 'Marker' not in input_tokens
        assert validate_call_parameters({'Marker': 'token'}, input_tokens) is (
            None
        )


class TestAddMultiRegionsArgument:
    def test_added_to_an_eligible_command(self, session):
        argument_table = build_argument_table(
            session, 'ec2', 'DescribeVpcs', 'describe-vpcs'
        )
        assert list(argument_table) == [MULTI_REGIONS_NAME]
        argument = argument_table[MULTI_REGIONS_NAME]
        assert isinstance(argument, MultiRegionsArgument)
        assert argument.cli_name == '--multi-regions'
        assert argument.py_name == MULTI_REGIONS_DEST

    def test_not_added_to_an_ineligible_command(self, session):
        argument_table = build_argument_table(
            session, 'ec2', 'TerminateInstances', 'terminate-instances'
        )
        assert argument_table == {}

    def test_command_with_its_own_option_of_that_name_is_an_error(
        self, session
    ):
        # For example a service adding a --multi-regions parameter to an
        # allowlisted command.  Neither option may silently win.
        with pytest.raises(ValueError) as excinfo:
            build_argument_table(
                session,
                'ec2',
                'DescribeVpcs',
                'describe-vpcs',
                argument_table={MULTI_REGIONS_NAME: object()},
            )
        assert 'aws ec2 describe-vpcs already has a --multi-regions' in str(
            excinfo.value
        )

    def test_command_that_is_not_allowlisted_keeps_its_own_option(
        self, session
    ):
        own_option = object()
        argument_table = build_argument_table(
            session,
            'ec2',
            'TerminateInstances',
            'terminate-instances',
            argument_table={MULTI_REGIONS_NAME: own_option},
        )
        assert argument_table[MULTI_REGIONS_NAME] is own_option


class TestMultiRegionsArgumentResolve:
    def test_stores_the_spec_on_the_global_args(self, session):
        parsed_globals = globals_with()
        make_argument(session).resolve(
            args_with(multi_regions='us-east-1,eu-west-1'), parsed_globals
        )
        spec = parsed_globals.multi_regions
        assert isinstance(spec, MultiRegionSpec)
        assert spec.regions == ('us-east-1', 'eu-west-1')

    def test_stores_all(self, session):
        parsed_globals = globals_with()
        make_argument(session).resolve(
            args_with(multi_regions='all'), parsed_globals
        )
        assert parsed_globals.multi_regions.is_all is True

    def test_no_op_when_the_argument_is_absent(self, session):
        parsed_globals = globals_with()
        make_argument(session).resolve(args_with(), parsed_globals)
        assert not hasattr(parsed_globals, 'multi_regions')

    def test_no_op_when_the_argument_is_none(self, session):
        parsed_globals = globals_with()
        make_argument(session).resolve(
            args_with(multi_regions=None), parsed_globals
        )
        assert not hasattr(parsed_globals, 'multi_regions')

    def test_global_args_are_validated_before_the_region_list(self, session):
        # The conflicting option is reported even though the region list
        # would not parse either, so the user is told what to fix first.
        with pytest.raises(ParamValidationError) as excinfo:
            make_argument(session).resolve(
                args_with(multi_regions='not-a-region'),
                globals_with(region='us-west-2'),
            )
        assert str(excinfo.value) == (
            '--region cannot be used together with --multi-regions.'
        )


class TestResolveHandlerRegistration:
    def test_resolves_only_for_its_own_command(self):
        session = botocore.session.get_session()
        make_argument(session)
        other = globals_with()
        own = globals_with()

        session.emit(
            'operation-args-parsed.ec2.describe-subnets',
            parsed_args=args_with(multi_regions='us-east-1'),
            parsed_globals=other,
        )
        session.emit(
            'operation-args-parsed.ec2.describe-vpcs',
            parsed_args=args_with(multi_regions='us-east-1'),
            parsed_globals=own,
        )

        assert not hasattr(other, 'multi_regions')
        assert own.multi_regions.regions == ('us-east-1',)

    def test_replaces_the_operation_caller_of_its_own_command(self):
        session = botocore.session.get_session()
        command = FakeOperationCommand('ec2', 'describe-vpcs')
        single_region_caller = command._operation_caller
        MultiRegionsArgument(session, command)

        session.emit(
            'operation-args-parsed.ec2.describe-vpcs',
            parsed_args=args_with(multi_regions='us-east-1,eu-west-1'),
            parsed_globals=globals_with(),
        )

        # The fan-out happens where the single-region call would be made,
        # after every calling-command handler has run.
        caller = command._operation_caller
        assert isinstance(caller, MultiRegionOperationCaller)
        assert caller._operation_caller is single_region_caller
        assert caller._spec.regions == ('us-east-1', 'eu-west-1')

    def test_keeps_the_operation_caller_without_the_option(self):
        session = botocore.session.get_session()
        command = FakeOperationCommand('ec2', 'describe-vpcs')
        single_region_caller = command._operation_caller
        MultiRegionsArgument(session, command)

        for value in ('us-east-1', None):
            session.emit(
                'operation-args-parsed.ec2.describe-vpcs',
                parsed_args=args_with(multi_regions=value),
                parsed_globals=globals_with(),
            )

        assert command._operation_caller is single_region_caller
