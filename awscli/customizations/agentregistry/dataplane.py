# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""The data plane client of the commands that read from a registry.

``list-skills`` and ``install-skill`` take the same sign-in arguments and
set up their client the same way, here, so the two cannot drift apart.
"""

import collections

from botocore.config import Config

from awscli.customizations.agentregistry.constants import (
    AUTHORIZER_DOCS,
    BEARER_SCHEME,
    CLIENT_ID_DOCS,
    NO_BROWSER_DOCS,
    SERVICE,
)
from awscli.customizations.agentregistry.providers import use_bearer_token
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    arm_unverified_tls_check,
    redact_logs_and_history,
    require_verified_tls,
    resolve_ca_bundle,
    resolve_data_plane_endpoint,
)

# The record type of a skill, by which the listing is filtered.
SKILL_RECORD_TYPE = 'SKILL'

# The most records ListDiscoverableRegistryRecords returns in one page (its
# maxResults); the service's default is less, so asking for the most halves
# the calls needed to read every page.
SKILL_RECORD_PAGE_SIZE = 100

# Read by create_data_plane_client.
SIGN_IN_ARGUMENTS = [
    {
        'name': 'authorizer',
        'choices': ['JWT', 'SIGV4'],
        'help_text': AUTHORIZER_DOCS,
    },
    {'name': 'client-id', 'help_text': CLIENT_ID_DOCS},
    {
        'name': 'no-browser',
        'action': 'store_true',
        'help_text': NO_BROWSER_DOCS,
    },
]

# The commands' descriptions end with this.
SIGN_IN_DESCRIPTION = (
    'Use ``--authorizer JWT`` for a registry configured with a custom JWT '
    'authorizer; omit it for SigV4. With ``--authorizer JWT``, signs you in '
    'through the browser if there is no usable cached sign-in, and caches '
    'the sign-in for later commands; ``--no-browser`` prints the sign-in '
    'link instead of opening a browser. Remove a cached sign-in with '
    '``sign-out``.'
)

# The client to call, and what else a command needs to know about the call:
# the endpoint it goes to, which is where an installed skill is recorded as
# coming from, and the region and CA bundle for any other request.
DataPlane = collections.namedtuple(
    'DataPlane', ['client', 'endpoint', 'region', 'ca_bundle']
)


def create_data_plane_client(session, parsed_args, parsed_globals):
    """The client for the registry in ``parsed_args``, as a :data:`DataPlane`.

    ``parsed_args`` has ``registry_id`` and the :data:`SIGN_IN_ARGUMENTS`.
    Everything that can fail without a network call is checked first: a
    region is required, and ``--authorizer JWT`` refuses to skip TLS
    certificate verification, before any sign-in. The endpoint is resolved
    from the same session and arguments as the call, and must be https with
    JWT. With JWT, the bearer token is then put in place
    (:func:`use_bearer_token`), which works only because the client is
    created after it, and the client's own config selects the bearer scheme,
    ahead of any ``auth_scheme_preference`` in the environment or config
    file. Without JWT, the client is created as botocore would create it,
    and botocore still signs with a bearer token when the caller selects the
    bearer scheme; with TLS verification skipped, the client refuses any call
    it would sign that way (:func:`arm_unverified_tls_check`).
    """
    region = parsed_globals.region or session.get_config_variable('region')
    if not region:
        raise AgentRegistryJWTError(
            'A region is required. Pass --region or configure a default '
            'region.'
        )
    ca_bundle = resolve_ca_bundle(session, parsed_globals)
    # A BatchGet response, which --debug logs and CLI history records,
    # carries presigned download URLs.
    redact_logs_and_history()
    jwt = bool(parsed_args.authorizer) and (
        parsed_args.authorizer.upper() == 'JWT'
    )
    if jwt:
        require_verified_tls(parsed_globals)
    # Where the call goes: the key of the cached sign-in.
    endpoint = resolve_data_plane_endpoint(
        session, parsed_globals, region, https_only=jwt
    )
    config = None
    if jwt:
        use_bearer_token(
            session,
            endpoint,
            parsed_args.registry_id,
            client_id=parsed_args.client_id,
            ca_bundle=ca_bundle,
            open_browser=not parsed_args.no_browser,
        )
        config = Config(auth_scheme_preference=BEARER_SCHEME)
    client = session.create_client(
        SERVICE,
        region_name=region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl,
        config=config,
    )
    arm_unverified_tls_check(client.meta.events, parsed_globals)
    return DataPlane(client, endpoint, region, ca_bundle)


def skill_record_pages(client, registry_id):
    """The registry's skill records, a list for each page of the listing.

    Read with the ``ListDiscoverableRegistryRecords`` paginator, filtered to
    ``SKILL`` records, with ``client`` as :func:`create_data_plane_client`
    created it, so the same sign-in. Whatever the service does with the
    filter, only records that are dicts of type ``SKILL`` are kept. Each page
    asks for the most records the service returns in one, so reading them
    all takes as few calls as it can. Pages are requested one at a time, as
    the caller asks for them.
    """
    paginator = client.get_paginator('list_discoverable_registry_records')
    pages = paginator.paginate(
        registryId=registry_id,
        filters=[{'name': 'recordType', 'values': [SKILL_RECORD_TYPE]}],
        PaginationConfig={'PageSize': SKILL_RECORD_PAGE_SIZE},
    )
    for page in pages:
        yield [
            record
            for record in page.get('registryRecords') or []
            if isinstance(record, dict)
            and record.get('recordType') == SKILL_RECORD_TYPE
        ]
