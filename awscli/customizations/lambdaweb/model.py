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
import copy

from awscli.customizations.lambdaweb import constants

# CLI enum args whose valid values are DERIVED FROM THE MODEL (never
# hardcoded). Maps the ARG_TABLE arg name -> the model shape whose enum
# defines its choices.
ENUM_ARG_SHAPES = {
    'endpoint-type': 'EndpointType',
    'auth-type': 'AuthType',
    'auto-deployment-mode': 'AutoDeploymentMode',
    'application-log-level': 'ApplicationLogLevel',
    'system-log-level': 'SystemLogLevel',
}

ENVIRONMENT_VARIABLE_KEY_SHAPE = 'EnvironmentVariablesKeyString'


def _operation_input_shape(session, operation_name):
    return (
        session.get_service_model(constants.SERVICE_NAME)
        .operation_model(operation_name)
        .input_shape
    )


def copy_input_fields(session, operation_name, source):
    """Copy response fields with matching operation input member names.

    Response-only members are excluded recursively.
    """
    return _copy_for_shape(
        source, _operation_input_shape(session, operation_name)
    )


def update_input_member(session, operation_name, member_path, request, update):
    """Update a nested input member while honoring tagged-union boundaries.

    ``update`` receives the current value or ``None`` and returns its
    replacement.
    """
    *parents, leaf = member_path
    shape = _operation_input_shape(session, operation_name)
    container = request
    for member_name in parents:
        child = container.get(member_name, {})
        if shape.is_tagged_union:
            container.clear()
        container = container.setdefault(member_name, child)
        shape = shape.members[member_name]
    existing = container.get(leaf)
    if shape.is_tagged_union:
        container.clear()
    container[leaf] = update(existing)


def _copy_for_shape(value, shape):
    if value is None:
        return None
    if shape.type_name == 'structure' and isinstance(value, dict):
        if shape.is_document_type:
            return copy.deepcopy(value)
        return {
            name: _copy_for_shape(value[name], member_shape)
            for name, member_shape in shape.members.items()
            if name in value
        }
    if shape.type_name == 'list' and isinstance(value, list):
        return [_copy_for_shape(item, shape.member) for item in value]
    if shape.type_name == 'map' and isinstance(value, dict):
        return {
            key: _copy_for_shape(item, shape.value)
            for key, item in value.items()
        }
    return copy.deepcopy(value)


def enum_choices(session, shape_name):
    """Return the modeled enum values for a shape.

    Single source of truth: the service model. The choices offered by the
    CLI for an enum argument come straight from the shape's ``enum``, so
    they can never drift from what the service accepts.
    """
    return list(
        session.get_service_model(constants.SERVICE_NAME)
        .shape_for(shape_name)
        .enum
    )


# Model shape whose ``pattern`` each ``--regions`` entry must match.
REGION_SHAPE = 'Region'


def _shape_metadata(session, shape_name):
    return (
        session.get_service_model(constants.SERVICE_NAME)
        .shape_for(shape_name)
        .metadata
    )


def int_bounds(session, shape_name):
    """Return ``(min, max)`` for an integer shape, straight from the model.

    Either bound may be ``None`` if the model does not constrain it.
    """
    meta = _shape_metadata(session, shape_name)
    return meta.get('min'), meta.get('max')


def string_pattern(session, shape_name):
    """Return the regex ``pattern`` for a string shape, or ``None``."""
    return _shape_metadata(session, shape_name).get('pattern')
