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
from unittest.mock import Mock

import pytest

from awscli.botocore.config import Config
from awscli.customizations.clientcontextparams import (
    ClientContextParamArgument,
    _apply_client_context_params,
    inject_client_context_params,
)


def _make_context_param(name, param_type='boolean', documentation=''):
    param = Mock()
    param.name = name
    param.type = param_type
    param.documentation = documentation
    return param


def _make_operation_model(context_params):
    operation_model = Mock()
    operation_model.service_model.service_name = 's3'
    operation_model.service_model.client_context_parameters = context_params
    return operation_model


@pytest.fixture
def session():
    s = Mock()
    s.get_default_client_config.return_value = None
    return s


@pytest.fixture
def argument_table():
    return {}


def _inject(argument_table, session, context_params):
    inject_client_context_params(
        argument_table=argument_table,
        operation_model=_make_operation_model(context_params),
        event_name='building-argument-table.s3api.list-buckets',
        session=session,
    )


def test_no_context_params_does_nothing(argument_table, session):
    _inject(argument_table, session, [])
    assert argument_table == {}
    session.register.assert_not_called()


def test_no_client_context_parameters_attr_does_nothing(
    argument_table, session
):
    operation_model = Mock()
    del operation_model.service_model.client_context_parameters
    inject_client_context_params(
        argument_table=argument_table,
        operation_model=operation_model,
        event_name='building-argument-table.s3api.list-buckets',
        session=session,
    )
    assert argument_table == {}


def test_boolean_param_injects_positive_and_negative_with_group(
    argument_table, session
):
    _inject(argument_table, session, [_make_context_param('ForcePathStyle')])
    pos = argument_table['force-path-style']
    neg = argument_table['no-force-path-style']
    assert isinstance(pos, ClientContextParamArgument)
    assert isinstance(neg, ClientContextParamArgument)
    assert pos.group_name == 'force-path-style'
    assert neg.group_name == 'force-path-style'


def test_string_param_injected_without_negative_or_group(
    argument_table, session
):
    _inject(
        argument_table,
        session,
        [_make_context_param('Endpoint', param_type='string')],
    )
    assert 'endpoint' in argument_table
    assert 'no-endpoint' not in argument_table
    assert argument_table['endpoint'].group_name is None


def test_collision_skips_param(argument_table, session):
    argument_table['accelerate'] = Mock()
    _inject(argument_table, session, [_make_context_param('Accelerate')])
    assert not isinstance(
        argument_table['accelerate'], ClientContextParamArgument
    )
    assert 'no-accelerate' not in argument_table


def test_unsupported_type_skips_param(argument_table, session):
    _inject(
        argument_table,
        session,
        [_make_context_param('Count', param_type='integer')],
    )
    assert 'count' not in argument_table


def _apply(session, param_defs, **attr_values):
    parsed_args = argparse.Namespace(**attr_values)
    _apply_client_context_params(param_defs, session, parsed_args)


def test_merges_with_existing_config(session):
    session.get_default_client_config.return_value = Config(read_timeout=30)
    _apply(
        session,
        [('force-path-style', 'ForcePathStyle')],
        force_path_style=True,
    )
    config = session.set_default_client_config.call_args[0][0]
    assert config.client_context_params == {'force_path_style': True}
    assert config.read_timeout == 30


def test_string_add_to_parser():
    arg = ClientContextParamArgument(
        name='endpoint',
        context_param_name='Endpoint',
        param_type='string',
    )
    parser = argparse.ArgumentParser()
    arg.add_to_parser(parser)
    result = parser.parse_args(['--endpoint', 'custom.example.com'])
    assert result.endpoint == 'custom.example.com'
