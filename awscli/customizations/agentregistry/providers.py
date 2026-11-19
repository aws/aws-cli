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
"""Identity provider adapters for JWT registries."""

import logging
import os
import re

from botocore import UNSIGNED
from botocore.config import Config

from awscli.customizations.agentregistry import cache
from awscli.customizations.agentregistry.browserflow import run_browser_login
from awscli.customizations.agentregistry.cache import read_entry, save_token
from awscli.customizations.agentregistry.constants import TOKEN_ENV_VAR
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    bare_registry_id,
    discover_registry,
    fetch_oidc_metadata,
    note_preset_token,
    printable,
    prompt,
    redact_logs_and_history,
    remember_signed_in_registry,
    requested_scopes,
    require_https,
    same_issuer,
    select_bearer_token,
    stdin_is_terminal,
    url_origin,
    with_scopes,
    write_status,
)

logger = logging.getLogger(__name__)

# The Cognito API a cached refresh token is exchanged through. Unlike
# InitiateAuth with REFRESH_TOKEN_AUTH, it returns the new refresh token when
# the app client rotates them. Events name the service by its hyphenized
# service id, Cognito Identity Provider, not by cognito-idp.
_REFRESH_OPERATION = 'GetTokensFromRefreshToken'
_REFRESH_BEFORE_SEND = (
    f'before-send.cognito-identity-provider.{_REFRESH_OPERATION}'
)


def identify_provider(issuer):
    for provider_cls in (CognitoProvider, GenericOidcProvider):
        if provider_cls.matches(issuer):
            return provider_cls(issuer)
    raise AgentRegistryJWTError(
        f'Unsupported identity provider: {printable(issuer)}'
    )


def sign_in(
    session,
    endpoint,
    registry_id,
    client_id=None,
    ca_bundle=None,
    open_browser=True,
):
    """Sign in to the registry through the browser; return the bearer token.

    The one sign-in of ``list-skills`` and ``install-skill``: the
    registry's Protected Resource Metadata names the issuer it trusts and the
    scopes it advertises, which are requested on top of the provider's
    defaults, and the token is cached for ``endpoint`` and ``registry_id``.
    The client id is ``client_id`` (``--client-id``), else the cached sign-in's
    for the same issuer, else asked for at a terminal. With
    ``open_browser=False`` (``--no-browser``) the sign-in link is only
    printed.
    """
    registry = discover_registry(endpoint, registry_id, ca_bundle=ca_bundle)
    provider = identify_provider(registry.issuer)
    write_status(f'\nRegistry {registry_id} trusts: {registry.issuer}')
    write_status(f'Detected identity provider: {provider.display_name}')
    if not client_id:
        client_id = _previous_client_id(endpoint, registry_id, registry.issuer)
    return provider.authenticate(
        session=session,
        endpoint=endpoint,
        registry_id=registry_id,
        client_id=client_id,
        ca_bundle=ca_bundle,
        # Requested on top of the provider's defaults (RFC 9728).
        extra_scopes=registry.scopes,
        open_browser=open_browser,
    )


def use_bearer_token(
    session,
    endpoint,
    registry_id,
    client_id=None,
    ca_bundle=None,
    open_browser=True,
):
    """Make this process send a bearer token: a pre-set, cached or new one.

    A token already in ``AWS_BEARER_TOKEN_AGENT_REGISTRY`` is sent as is: no
    cache, discovery or sign-in. Otherwise the cached sign-in for
    ``endpoint`` and the bare registry id is used, refreshed if need be, and
    without a usable one this signs in (see :func:`sign_in`). The token is
    exported for the client created next, which works only because no client
    has been created yet; that client selects the bearer scheme in its own
    config. The before-send guard keeps the token off plain HTTP whichever
    way it came.
    """
    preset = os.environ.get(TOKEN_ENV_VAR)
    if preset:
        redact_logs_and_history(preset)
        note_preset_token(('--client-id', '--no-browser'))
        return
    # The cache key and the metadata path, also when given an ARN.
    registry_id = bare_registry_id(registry_id)
    token = cache.load_token(
        endpoint,
        registry_id,
        client_id=client_id,
        session=session,
        ca_bundle=ca_bundle,
    )
    if not token:
        token = sign_in(
            session,
            endpoint,
            registry_id,
            client_id=client_id,
            ca_bundle=ca_bundle,
            open_browser=open_browser,
        )
    redact_logs_and_history(token)
    remember_signed_in_registry(registry_id)
    os.environ[TOKEN_ENV_VAR] = token
    logger.debug('Exported %s', TOKEN_ENV_VAR)


def _previous_client_id(endpoint, registry_id, issuer):
    """The client id of the cached sign-in, if it was with ``issuer``.

    A fresh sign-in can follow a cache miss for many reasons, such as a
    newly advertised scope or a refresh that failed, and should not ask for
    a client id it already knows. One for another issuer would belong to
    another app, so it is not reused.
    """
    entry = read_entry(endpoint, registry_id)
    if not entry:
        return None
    client_id = entry.get('clientId')
    previous = entry.get('issuer')
    if (
        not isinstance(client_id, str)
        or not client_id
        or not isinstance(previous, str)
        or not same_issuer(previous, issuer)
    ):
        return None
    write_status(
        f'Using client id {printable(client_id)} from the previous sign-in.'
    )
    return client_id


def _client_id(client_id, label):
    """``--client-id``, or the answer to a prompt when there is a terminal.

    Protected Resource Metadata does not publish the client id, so without
    either there is nothing to sign in with.
    """
    if client_id:
        return client_id
    if not stdin_is_terminal():
        raise AgentRegistryJWTError(
            'An OAuth client id is required, and standard input is not a '
            'terminal to prompt for it. Pass --client-id with the id the '
            'registry owner provides.'
        )
    client_id = prompt(f'{label} (from the registry owner): ')
    if not client_id:
        raise AgentRegistryJWTError(
            'An OAuth client id is required. Protected Resource Metadata '
            'does not publish it, so the registry owner must provide it.'
        )
    return client_id


def _granted_scopes(payload, requested):
    """The scopes to store with the sign-in: those requested, and granted.

    The token response may name the granted scopes (RFC 6749, section 5.1),
    and some identity providers name them differently (Entra reports
    ``.default``) or leave one out. Storing only those would make every
    refresh find an advertised scope missing and sign in again, so the
    requested scopes are always kept.
    """
    granted = payload.get('scope')
    if not isinstance(granted, str):
        granted = ''
    return list(dict.fromkeys([*requested, *granted.split()]))


def _refuse_plain_http_refresh(request, **kwargs):
    """Never send a refresh token to Cognito on a non-https connection."""
    require_https(request.url, 'Cognito endpoint')


def _revocation_endpoint(metadata):
    """The RFC 7009 endpoint ``sign-out`` revokes the refresh token at."""
    value = metadata.get('revocation_endpoint')
    return value if isinstance(value, str) and value else None


class BaseProvider:
    display_name = 'unknown'

    def __init__(self, issuer):
        # Exactly as the registry's metadata publishes it, so the discovery
        # document can be checked against it.
        self.issuer = issuer

    @classmethod
    def matches(cls, issuer):
        raise NotImplementedError

    def authenticate(self, **kwargs):
        raise NotImplementedError


class CognitoProvider(BaseProvider):
    """Amazon Cognito user pools.

    Sign-in uses the pool's hosted UI, whose endpoints OIDC discovery
    advertises once the pool has a domain. Silent refresh uses Cognito's
    unauthenticated ``GetTokensFromRefreshToken`` API, so no AWS credentials
    are needed. Both the region and the pool id are derived from the issuer
    URL.
    """

    display_name = 'Amazon Cognito'

    # Issuer form: https://cognito-idp.<region>.amazonaws.com/<pool-id>. Matched
    # on the exact host, so a lookalike such as https://evil.example/cognito-idp
    # .us-east-1.amazonaws.com/... is treated as an ordinary OIDC issuer.
    _ISSUER = re.compile(
        r'^https://cognito-idp\.([a-z0-9-]+)\.amazonaws\.com(?:\.cn)?'
        r'/([a-z0-9-]+_[A-Za-z0-9]+)$'
    )

    @classmethod
    def matches(cls, issuer):
        return bool(cls._ISSUER.match(issuer.rstrip('/')))

    @property
    def pool_id(self):
        return self._ISSUER.match(self.issuer.rstrip('/')).group(2)

    @property
    def pool_region(self):
        return self._ISSUER.match(self.issuer.rstrip('/')).group(1)

    def authenticate(
        self,
        session,
        endpoint,
        registry_id,
        client_id=None,
        ca_bundle=None,
        extra_scopes=(),
        open_browser=True,
        **kwargs,
    ):
        write_status(f'User pool: {self.pool_id}')
        client_id = _client_id(client_id, 'Cognito app client id')
        return self._browser_login(
            endpoint,
            registry_id,
            client_id,
            ca_bundle,
            extra_scopes,
            open_browser=open_browser,
        )

    def _browser_login(
        self,
        endpoint,
        registry_id,
        client_id,
        ca_bundle,
        extra_scopes=(),
        open_browser=True,
    ):
        """Sign in through the pool's hosted UI.

        Once a pool has a domain, OIDC discovery advertises the hosted UI's
        ``authorization_endpoint`` and ``token_endpoint``, so nothing beyond
        the client id is needed. A pool without a domain advertises neither.
        The endpoints only ever come from the pool's own discovery document,
        which is checked against the issuer the registry trusts.
        """
        metadata = fetch_oidc_metadata(self.issuer, ca_bundle=ca_bundle)
        authorize_endpoint = metadata.get('authorization_endpoint')
        token_endpoint = metadata.get('token_endpoint')
        if not (authorize_endpoint and token_endpoint):
            raise AgentRegistryJWTError(
                f'Pool {self.pool_id} has no domain, so OIDC discovery '
                f'advertises no sign-in endpoint. The registry owner must add '
                f'a domain to the user pool (in the Amazon Cognito console: '
                f'Branding, then Domain).'
            )

        scopes = with_scopes(['openid'], extra_scopes)
        payload = run_browser_login(
            authorize_endpoint=authorize_endpoint,
            token_endpoint=token_endpoint,
            client_id=client_id,
            scopes=scopes,
            ca_bundle=ca_bundle,
            open_browser=open_browser,
        )
        save_token(
            endpoint,
            registry_id,
            token=payload['access_token'],
            expires_in=payload.get('expires_in'),
            refresh_token=payload.get('refresh_token'),
            client_id=client_id,
            issuer=self.issuer,
            revocation_endpoint=_revocation_endpoint(metadata),
            pool_region=self.pool_region,
            scopes=_granted_scopes(payload, scopes),
        )
        return payload['access_token']

    @classmethod
    def refresh_endpoint(cls, cached):
        """The Cognito endpoint to refresh ``cached`` at, or None.

        ``https://cognito-idp.<region>.amazonaws.com[.cn]``, the scheme and
        host of the issuer saved at sign-in, which is checked again here, as
        the cache file can be edited. None if the entry has no issuer, or one
        that is not a Cognito user pool's in the entry's ``poolRegion``.
        """
        issuer = cached.get('issuer')
        if not isinstance(issuer, str):
            return None
        match = cls._ISSUER.fullmatch(issuer.rstrip('/'))
        if not match or match.group(1) != cached.get('poolRegion'):
            return None
        return url_origin(issuer)

    @classmethod
    def refresh(cls, session, cached, ca_bundle=None):
        """Exchange a cached refresh token for new tokens.

        Returns ``(token, expires_in, rotated_refresh_token)``; the last is
        None unless the app client rotates refresh tokens. All three are None,
        a cache miss that leads to a new sign-in, if the entry names no
        Cognito issuer to send the refresh token to (:meth:`refresh_endpoint`).
        """
        endpoint_url = cls.refresh_endpoint(cached)
        if not endpoint_url:
            logger.debug(
                'Cached Cognito sign-in has no usable issuer; not refreshing'
            )
            return None, None, None
        # The refresh token is a reusable credential, so it only ever goes to
        # the pool that issued it. An explicit endpoint_url takes precedence
        # over AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER, AWS_ENDPOINT_URL
        # and endpoint_url in the config file, which would otherwise send it
        # to any host.
        client = session.create_client(
            'cognito-idp',
            region_name=cached['poolRegion'],
            endpoint_url=endpoint_url,
            config=Config(signature_version=UNSIGNED),
            verify=ca_bundle,
        )
        # Defense in depth: the endpoint above is always https, and the check
        # is on the request about to be sent, after every endpoint rule and
        # before-send hook. Only this client is affected.
        client.meta.events.register(
            _REFRESH_BEFORE_SEND, _refuse_plain_http_refresh
        )
        response = client.get_tokens_from_refresh_token(
            ClientId=cached['clientId'],
            RefreshToken=cached['refreshToken'],
        )
        result = response.get('AuthenticationResult') or {}
        # Same selection as at sign-in.
        token, _ = select_bearer_token(
            {
                'access_token': result.get('AccessToken'),
                'id_token': result.get('IdToken'),
            }
        )
        return token, result.get('ExpiresIn'), result.get('RefreshToken')


class GenericOidcProvider(BaseProvider):
    """Any other OIDC issuer.

    Reached for providers such as Okta, Entra and Auth0. Unlike Cognito, a
    standards-compliant issuer advertises a usable ``authorization_endpoint``,
    so the sign-in link needs no extra configuration.
    """

    display_name = 'generic OIDC provider'

    @classmethod
    def matches(cls, issuer):
        return issuer.startswith('https://')

    def authenticate(
        self,
        endpoint,
        registry_id,
        client_id=None,
        ca_bundle=None,
        extra_scopes=(),
        open_browser=True,
        **kwargs,
    ):
        metadata = fetch_oidc_metadata(self.issuer, ca_bundle=ca_bundle)
        token_endpoint = metadata.get('token_endpoint')
        authorize_endpoint = metadata.get('authorization_endpoint')
        if not (authorize_endpoint and token_endpoint):
            raise AgentRegistryJWTError(
                f'{self.issuer} does not advertise both an '
                f'authorization_endpoint and a token_endpoint, so a sign-in '
                f'link cannot be built.'
            )

        client_id = _client_id(client_id, 'OAuth client id')
        scopes = with_scopes(requested_scopes(metadata), extra_scopes)
        payload = run_browser_login(
            authorize_endpoint=authorize_endpoint,
            token_endpoint=token_endpoint,
            client_id=client_id,
            scopes=scopes,
            ca_bundle=ca_bundle,
            open_browser=open_browser,
        )
        save_token(
            endpoint,
            registry_id,
            token=payload['access_token'],
            expires_in=payload.get('expires_in'),
            refresh_token=payload.get('refresh_token'),
            client_id=client_id,
            issuer=self.issuer,
            revocation_endpoint=_revocation_endpoint(metadata),
            token_endpoint=token_endpoint,
            scopes=_granted_scopes(payload, scopes),
        )
        return payload['access_token']
