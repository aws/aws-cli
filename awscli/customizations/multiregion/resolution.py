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

import logging

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    CredentialRetrievalError,
    InvalidConfigError,
    LoginError,
    NoAuthTokenError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
    RefreshWithMFAUnsupportedError,
    SSOError,
    TokenRetrievalError,
    UnknownCredentialError,
)
from botocore.utils import ensure_boolean

from awscli.customizations.exceptions import ConfigurationError

LOG = logging.getLogger(__name__)

# Regions not enabled for the account are never called.
_ENABLED_OPT_STATUSES = ['ENABLED', 'ENABLED_BY_DEFAULT']

# Credential and configuration failures.  Every region would fail the
# same way, so they are reported as they are, not as a failure to list
# the enabled regions with advice to list the regions explicitly.
_CREDENTIAL_ERRORS = (
    CredentialRetrievalError,
    InvalidConfigError,
    LoginError,
    NoAuthTokenError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
    RefreshWithMFAUnsupportedError,
    SSOError,
    TokenRetrievalError,
    UnknownCredentialError,
)

# Error codes of requests whose credentials were rejected.
_AUTH_FAILURE_CODES = frozenset(
    [
        'AuthFailure',
        'ExpiredToken',
        'ExpiredTokenException',
        'IncompleteSignature',
        'InvalidClientTokenId',
        'InvalidSignatureException',
        'RequestExpired',
        'SignatureDoesNotMatch',
        'UnrecognizedClientException',
    ]
)


class ResolvedRegions:
    """The regions a command will be run in."""

    def __init__(self, regions, skip_missing_hosts=False):
        self.regions = list(regions)
        self.skip_missing_hosts = skip_missing_hosts


def resolve_regions(session, spec, service_name, verify=None, offline=False):
    """Resolve a ``MultiRegionSpec`` into the regions to call."""
    if not spec.is_all:
        # Every listed region is called, so a missing one is reported.
        return ResolvedRegions(spec.regions)
    current_region = session.get_config_variable('region')
    if not current_region:
        raise ConfigurationError(
            '--multi-regions all needs a default region to find the '
            'partition and the regions enabled for the account. Set '
            'AWS_REGION or the region setting of your profile, or list the '
            'regions explicitly.'
        )
    partition = get_partition_for_region(session, current_region)
    service_regions = session.get_available_regions(service_name, partition)
    if offline:
        # Without calling AWS, every region with an endpoint is used.
        regions = service_regions or _get_partition_regions(session, partition)
        return ResolvedRegions(sorted(regions))
    enabled_regions = _get_enabled_regions(session, current_region, verify)
    if not service_regions:
        # No endpoint data for the service: DNS decides.
        LOG.debug(
            'No endpoint data for service %s in partition %s; calling '
            'every enabled region.',
            service_name,
            partition,
        )
        return ResolvedRegions(
            sorted(enabled_regions), skip_missing_hosts=True
        )
    omitted = sorted(set(enabled_regions) - set(service_regions))
    if omitted:
        LOG.debug(
            'Leaving out %s: %s has no endpoint there.', omitted, service_name
        )
    regions = sorted(set(enabled_regions) & set(service_regions))
    if not regions:
        raise ConfigurationError(
            f'{service_name} is not available in any region enabled for '
            'this account.'
        )
    # Not every FIPS or dual-stack endpoint is listed, so DNS decides.
    return ResolvedRegions(
        regions, skip_missing_hosts=_uses_endpoint_variant(session)
    )


def get_partition_for_region(session, region):
    resolver = session._get_internal_component('endpoint_resolver')
    return resolver.get_partition_for_region(region)


def _get_partition_regions(session, partition):
    for entry in session.get_data('endpoints')['partitions']:
        if entry['partition'] == partition:
            return list(entry['regions'])
    return []


def _uses_endpoint_variant(session):
    return any(
        ensure_boolean(session.get_config_variable(setting))
        for setting in ('use_fips_endpoint', 'use_dualstack_endpoint')
    )


def _get_enabled_regions(session, region, verify=None):
    """account list-regions, falling back to ec2 describe-regions."""
    errors = []
    for lister in (_list_regions_with_account, _list_regions_with_ec2):
        try:
            regions = lister(session, region, verify)
        except (ClientError, BotoCoreError) as e:
            if _is_credential_failure(e):
                raise
            LOG.debug('Could not list enabled regions: %s', e, exc_info=True)
            errors.append(str(e))
            continue
        if regions:
            return regions
        # An account always has an enabled region; try the next source.
        LOG.debug('%s returned no regions.', lister.__name__)
        errors.append(f'{lister.__name__} returned no regions')
    raise ConfigurationError(
        '--multi-regions all could not determine which regions are '
        'enabled for this account. Specify the regions explicitly with '
        '--multi-regions <region>,<region>. The following errors '
        'occurred:\n' + '\n'.join(errors)
    )


def _is_credential_failure(error):
    if isinstance(error, _CREDENTIAL_ERRORS):
        return True
    if isinstance(error, ClientError):
        code = error.response.get('Error', {}).get('Code')
        return code in _AUTH_FAILURE_CODES
    return False


def _list_regions_with_account(session, region, verify=None):
    client = session.create_client(
        'account', region_name=region, verify=verify
    )
    pages = client.get_paginator('list_regions').paginate(
        RegionOptStatusContains=_ENABLED_OPT_STATUSES
    )
    return [
        entry['RegionName']
        for page in pages
        for entry in page.get('Regions', [])
    ]


def _list_regions_with_ec2(session, region, verify=None):
    client = session.create_client('ec2', region_name=region, verify=verify)
    # Without AllRegions, only enabled regions are returned.
    response = client.describe_regions()
    return [entry['RegionName'] for entry in response.get('Regions', [])]
