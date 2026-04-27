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
import pytest

from awscli.botocore import xform_name
from awscli.clidriver import create_clidriver
from awscli.customizations.clientcontextparams import _SUPPORTED_TYPES

_SESSION = create_clidriver().session

_TYPE_TESTS = []
_COLLISION_TESTS = []

for _svc_name in _SESSION.get_available_services():
    _model = _SESSION.get_service_model(_svc_name)
    if not hasattr(_model, 'client_context_parameters'):
        continue
    _ctx_params = _model.client_context_parameters
    for _param in _ctx_params:
        _TYPE_TESTS.append((_svc_name, _param.name, _param.type))
    _ctx_names = {xform_name(p.name, '-') for p in _ctx_params}
    for _op_name in _model.operation_names:
        _op = _model.operation_model(_op_name)
        if _op.input_shape is None:
            continue
        _collisions = _ctx_names & {
            xform_name(m, '-') for m in _op.input_shape.members
        }
        if _collisions:
            _COLLISION_TESTS.append((_svc_name, _op_name, _collisions))


@pytest.mark.validates_models
@pytest.mark.parametrize("service_name, param_name, param_type", _TYPE_TESTS)
def test_client_context_param_types_are_supported(
    service_name, param_name, param_type, record_property
):
    if param_type not in _SUPPORTED_TYPES:
        record_property('aws_service', service_name)
        raise AssertionError(
            f'Client context param {param_name!r} on service '
            f'{service_name!r} has unsupported type {param_type!r}. '
            f'Supported types: {_SUPPORTED_TYPES}'
        )


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "service_name, operation_name, collisions", _COLLISION_TESTS
)
def test_client_context_params_do_not_collide_with_operation_inputs(
    service_name, operation_name, collisions, record_property
):
    # Only runs when a collision exists; unconditional failure is intentional.
    record_property('aws_service', service_name)
    record_property('aws_operation', operation_name)
    raise AssertionError(
        f'Client context param name(s) {collisions} on service '
        f'{service_name!r} collide with input members of '
        f'{operation_name!r}.'
    )
