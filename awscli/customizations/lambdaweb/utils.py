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

from awscli.customizations.lambdaweb import model
from awscli.customizations.lambdaweb.exceptions import (
    InvalidArgumentValueError,
    InvalidKeyValueError,
)


def create_nested_client(session, service_name, **kwargs):
    """Test-seam wrapper around session.create_client."""
    return session.create_client(service_name, **kwargs)


def get_partition_for_region(session, region):
    """Resolve partition via endpoint_resolver; session has no direct accessor."""
    resolver = session.get_component('endpoint_resolver')
    return resolver.get_partition_for_region(region)


def validate_int_in_model_range(session, flag, shape_name, value):
    """Validate early so role/upload aren't orphaned on out-of-range values."""
    if value is None:
        return
    low, high = model.int_bounds(session, shape_name)
    below = low is not None and value < low
    above = high is not None and value > high
    if below or above:
        if low is not None and high is not None:
            limit = f'between {low} and {high}'
        elif low is not None:
            limit = f'{low} or greater'
        else:
            limit = f'{high} or less'
        raise InvalidArgumentValueError(f'{flag} must be {limit}: got {value}')


def validate_regions_against_model(session, flag, regions):
    """Fail fast on invalid regions before role creation / upload."""
    pattern = model.string_pattern(session, model.REGION_SHAPE)
    if not pattern:
        return
    compiled = re.compile(pattern)
    for region in regions:
        if not compiled.fullmatch(region):
            raise InvalidArgumentValueError(
                f"{flag} entry '{region}' is not a valid AWS Region."
            )


def is_tty(stream):
    """Report whether *stream* is a TTY; closed streams count as non-TTY."""
    isatty = getattr(stream, 'isatty', None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except ValueError:
        return False


def parse_kv(items, *, label='--env / --tags', reject_empty_values=False):
    """Parse KEY=VAL items; reject empty values when the model forbids them."""
    if not items:
        return {}
    result = {}
    for item in items:
        if '=' not in item:
            raise InvalidKeyValueError(
                f"{label} entry must be KEY=VAL: got '{item}'"
            )
        key, value = item.split('=', 1)
        if not key:
            raise InvalidKeyValueError(
                f"{label} key must not be empty: got '{item}'"
            )
        if reject_empty_values and value == '':
            raise InvalidKeyValueError(
                f"{label} value for key '{key}' must not be empty. To "
                'preserve an existing value, omit the option.'
            )
        result[key] = value
    return result


def strip_empty(value):
    """Recursively drop ``None``, ``''``, ``[]``, and ``{}`` members.

    ``0`` and ``False`` are meaningful values (e.g. ``--rate-limit 0``) and
    are always kept; only unset/empty placeholders are removed so the API
    request never sends them.
    """
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            cleaned_item = strip_empty(item)
            if cleaned_item is None:
                continue
            if cleaned_item == '' or cleaned_item == [] or cleaned_item == {}:
                continue
            cleaned[key] = cleaned_item
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            cleaned_item = strip_empty(item)
            if cleaned_item is None:
                continue
            if cleaned_item == '' or cleaned_item == [] or cleaned_item == {}:
                continue
            cleaned_list.append(cleaned_item)
        return cleaned_list
    return value
