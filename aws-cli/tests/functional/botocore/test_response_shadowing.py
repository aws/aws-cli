# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import pytest

from tests import ALL_SERVICES


def _assert_not_shadowed(key, service_name, shapes):
    errors = [
        f'{service_name}.{name}: shape "{shape.name}" shadows '
        f'the botocore response key "{key}"'
        for name, shape in shapes
        if shape is not None and key in shape.members
    ]
    assert not errors, '\n'.join(errors)


@pytest.mark.parametrize(
    'service_model', ALL_SERVICES, ids=lambda model: model.service_name
)
def test_response_metadata_is_not_shadowed(service_model):
    _assert_not_shadowed(
        'ResponseMetadata',
        service_model.service_name,
        (
            (name, service_model.operation_model(name).output_shape)
            for name in service_model.operation_names
        ),
    )


@pytest.mark.parametrize(
    'service_model', ALL_SERVICES, ids=lambda model: model.service_name
)
def test_exceptions_do_not_shadow_response_metadata(service_model):
    _assert_not_shadowed(
        'ResponseMetadata',
        service_model.service_name,
        ((shape.name, shape) for shape in service_model.error_shapes),
    )


@pytest.mark.parametrize(
    'service_model', ALL_SERVICES, ids=lambda model: model.service_name
)
def test_exceptions_do_not_shadow_error(service_model):
    _assert_not_shadowed(
        'Error',
        service_model.service_name,
        ((shape.name, shape) for shape in service_model.error_shapes),
    )
