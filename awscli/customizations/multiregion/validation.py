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

from botocore.exceptions import UnknownRegionError

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.multiregion.resolution import (
    get_partition_for_region,
)

# The value of --multi-regions that means every enabled region.
ALL_REGIONS = 'all'


class MultiRegionSpec:
    """The regions the user asked for.

    Either every region enabled for the account (``all``) or an explicit,
    ordered list of region names.
    """

    def __init__(self, regions=()):
        self.regions = tuple(regions)

    @property
    def is_all(self):
        return not self.regions

    def __repr__(self):
        return f'MultiRegionSpec(regions={self.regions!r})'


def parse_multi_regions(value):
    """Turn the raw ``--multi-regions`` value into a ``MultiRegionSpec``."""
    # A region named twice is still only called once.
    names = list(dict.fromkeys(name.strip() for name in value.split(',')))
    if names == [ALL_REGIONS]:
        return MultiRegionSpec()
    return MultiRegionSpec(names)


def validate_options(spec, parsed_globals, session):
    """Reject an invalid ``--multi-regions`` value or conflicting options."""
    for option, used in (
        ('--region', getattr(parsed_globals, 'region', None)),
        ('--endpoint-url', getattr(parsed_globals, 'endpoint_url', None)),
    ):
        if used:
            raise ParamValidationError(
                f'{option} cannot be used together with --multi-regions.'
            )
    if '' in spec.regions:
        raise ParamValidationError(
            '--multi-regions: the region list has an empty entry. Specify '
            'a comma separated list of region names or the keyword "all".'
        )
    if ALL_REGIONS in spec.regions:
        raise ParamValidationError(
            '--multi-regions: "all" cannot be combined with explicit '
            'region names.'
        )
    _check_single_partition(spec.regions, session)


def _check_single_partition(names, session):
    partitions = {}
    for name in names:
        try:
            partitions[name] = get_partition_for_region(session, name)
        except UnknownRegionError:
            raise ParamValidationError(
                f'--multi-regions: "{name}" is not a valid region name.'
            )
    for name in names[1:]:
        if partitions[name] != partitions[names[0]]:
            raise ParamValidationError(
                '--multi-regions: all regions must be in the same '
                f'partition ({names[0]} is in "{partitions[names[0]]}", '
                f'{name} is in "{partitions[name]}").'
            )


def validate_call_parameters(parameters, input_tokens):
    """Reject manually supplied, region specific pagination tokens."""
    for name in sorted(parameters):
        if name in input_tokens:
            raise ParamValidationError(
                f'{name} cannot be used together with --multi-regions '
                'because pagination tokens are specific to one region.'
            )
