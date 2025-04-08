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


def _all_service_error_shapes():
    for service_model in ALL_SERVICES:
        yield from service_model.error_shapes


def _all_operations():
    for service_model in ALL_SERVICES:
        for operation_name in service_model.operation_names:
            yield service_model.operation_model(operation_name).output_shape


def _assert_not_shadowed(key, shape):
    if not shape:
        return

    assert (
        key not in shape.members
    ), f'Found shape "{shape.name}" that shadows the botocore response key "{key}"'


@pytest.mark.parametrize("operation_output_shape", _all_operations())
def test_response_metadata_is_not_shadowed(operation_output_shape):
    _assert_not_shadowed('ResponseMetadata', operation_output_shape)


@pytest.mark.parametrize("error_shape", _all_service_error_shapes())
def test_exceptions_do_not_shadow_response_metadata(error_shape):
    _assert_not_shadowed('ResponseMetadata', error_shape)


@pytest.mark.parametrize("error_shape", _all_service_error_shapes())
def test_exceptions_do_not_shadow_error(error_shape):
    _assert_not_shadowed('Error', error_shape)
