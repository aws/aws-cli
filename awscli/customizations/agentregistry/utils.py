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
"""Discovery, prompting and token-shape helpers."""

import collections.abc
import http.client
import json
import logging
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

from botocore import UNSIGNED
from botocore.awsrequest import AWSResponse
from botocore.config import Config
from botocore.exceptions import NoRegionError
from botocore.history import get_global_history_recorder
from botocore.httpsession import get_cert_path

from awscli.customizations.agentregistry.constants import (
    BEARER_SCHEME,
    BEARER_SIGNATURE_VERSION,
    HTTP_TIMEOUT,
    MAX_PRINTED_TEXT,
    MAX_RESPONSE_BYTES,
    OIDC_METADATA_PATH,
    PRM_PATH,
    SERVICE,
    TOKEN_ENV_VAR,
    WANTED_SCOPES,
)

logger = logging.getLogger(__name__)


class AgentRegistryJWTError(Exception):
    pass


def botocore_session():
    """A plain botocore session, for callers that have no CLI session.

    Prefer the CLI's own session where there is one: a plain session ignores
    ``--profile`` and the other global options the CLI applies to its own.
    """
    import botocore.session

    return botocore.session.get_session()


def prompt(message):
    return input(message).strip()


def stdin_is_terminal():
    return sys.stdin is not None and sys.stdin.isatty()


def write_status(message):
    """Write progress to stderr so piped output stays machine-readable."""
    sys.stderr.write(message + '\n')


# C0 controls, DEL and C1 controls, plus the bidirectional formatting
# characters, which change how the text around them is displayed.
_CONTROL_CHARACTERS = re.compile(
    '[\x00-\x1f\x7f-\x9f\u200e\u200f\u202a-\u202e\u2066-\u2069]+'
)


def printable(text, limit=MAX_PRINTED_TEXT):
    """Make text from a remote party safe to print to a terminal.

    Identity providers and token endpoints choose the error text they return.
    Control characters are replaced with a space, so an ANSI escape sequence
    cannot recolour the output, move the cursor or clear the screen, and the
    result is capped so an oversized reply cannot flood the terminal.
    """
    text = _CONTROL_CHARACTERS.sub(' ', str(text or '')).strip()
    if len(text) > limit:
        text = text[:limit] + '...'
    return text


def url_origin(url):
    """``scheme://host[:port]`` of ``url``, without its path or query."""
    parts = urllib.parse.urlsplit(url or '')
    host = parts.hostname or ''
    try:
        if parts.port:
            host = f'{host}:{parts.port}'
    except ValueError:
        pass
    return f'{parts.scheme}://{host}' if parts.scheme else host


_DEFAULT_PORTS = {'https': 443, 'http': 80}


def comparable_endpoint(url):
    """``url`` with case, a default port and a trailing slash normalized.

    Botocore keeps an endpoint URL as given, so the same endpoint can be
    written ``https://Host:443/`` or ``https://host``. Two endpoints are the
    same if their comparable forms are equal.
    """
    parts = urllib.parse.urlsplit(url if isinstance(url, str) else '')
    scheme = parts.scheme.lower()
    try:
        port = parts.port
    except ValueError:
        port = None
    host = parts.hostname or ''
    if port is not None and port != _DEFAULT_PORTS.get(scheme):
        host = f'{host}:{port}'
    return scheme, host, parts.path.rstrip('/')


def printable_url(url):
    """``url`` as a message may show it: only its origin if it has a query.

    A presigned download URL carries its credentials in the query string, so
    an error message must not repeat it.
    """
    if not isinstance(url, str):
        return url
    return url_origin(url) if urllib.parse.urlsplit(url).query else url


def require_https(url, purpose):
    """Reject anything but an absolute ``https`` URL.

    Every endpoint this customization talks to directly carries or returns a
    credential, so plain HTTP, ``file:`` and other schemes the standard library
    would otherwise accept are refused outright, with no opt-out. Most of these
    URLs come from discovery documents and are printed, so a URL containing a
    control character is refused too.
    """
    parts = urllib.parse.urlsplit(url or '')
    if (
        parts.scheme != 'https'
        or not parts.hostname
        or _CONTROL_CHARACTERS.search(url)
    ):
        raise AgentRegistryJWTError(
            f'Refusing to use {purpose} {printable_url(url)!r}: only https '
            f'URLs are allowed.'
        )
    return url


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Fail on any redirect instead of following it.

    A followed redirect could move a request onto plain HTTP or another host
    after the URL itself was validated.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AgentRegistryJWTError(
            f'Refusing to follow a redirect (HTTP {code}) from '
            f'{printable_url(req.full_url)}.'
        )


def resolve_ca_bundle(session, parsed_globals=None):
    """The CA bundle the CLI is configured to trust, or None if there is none.

    Same sources and precedence as for AWS API calls: ``--ca-bundle``, then
    ``AWS_CA_BUNDLE`` or ``ca_bundle`` in the config file.
    """
    ca_bundle = getattr(parsed_globals, 'ca_bundle', None)
    return ca_bundle or session.get_config_variable('ca_bundle') or None


def _ssl_context(ca_bundle=None):
    """A verifying TLS context that trusts ``ca_bundle``.

    Without a configured bundle this trusts the same default bundle botocore
    uses for AWS API calls, rather than whatever the local OpenSSL build
    happens to point at.
    """
    path = ca_bundle or get_cert_path(True)
    try:
        if os.path.isdir(path):
            return ssl.create_default_context(capath=path)
        return ssl.create_default_context(cafile=path)
    except OSError as e:
        raise AgentRegistryJWTError(
            f'Could not load the CA bundle {path}: {e}'
        )


def _opener(ca_bundle=None):
    # Certificates are always verified. The CLI's option to skip certificate
    # verification is deliberately not honored here: these connections carry
    # bearer and refresh tokens, decide where the user signs in, and deliver
    # installable code, so an unverified connection would hand all of that to
    # whoever sits in the path.
    # build_opener keeps the default proxy handling, so HTTPS_PROXY still
    # applies.
    return urllib.request.build_opener(
        _RefuseRedirects,
        urllib.request.HTTPSHandler(context=_ssl_context(ca_bundle)),
    )


def urlopen(request, timeout=HTTP_TIMEOUT, purpose='endpoint', ca_bundle=None):
    """``urllib.request.urlopen`` with https enforced and redirects refused.

    ``ca_bundle`` is the bundle from :func:`resolve_ca_bundle`.
    """
    url = (
        request.full_url
        if isinstance(request, urllib.request.Request)
        else request
    )
    require_https(url, purpose)
    return _opener(ca_bundle).open(request, timeout=timeout)


def read_limited(response, url, limit=MAX_RESPONSE_BYTES):
    """The response body, refusing one larger than ``limit`` bytes."""
    body = response.read(limit + 1)
    if len(body) > limit:
        raise AgentRegistryJWTError(
            f'The response from {printable_url(url)} is too large: more than '
            f'{limit} bytes, so it was not read.'
        )
    return body


def read_error_body(error, limit):
    """At most ``limit`` bytes of an ``HTTPError``'s body, as text.

    The body comes over the same connection as the status, so reading it can
    time out or stop short. That loses only the detail, not the error, so the
    body is then ``''``.
    """
    try:
        body = error.read(limit)
    except (OSError, http.client.HTTPException, ValueError) as e:
        logger.debug(
            'Could not read the body of an HTTP %s response: %s',
            getattr(error, 'code', None),
            printable(e) or type(e).__name__,
        )
        return ''
    return body.decode('utf-8', 'replace') if isinstance(body, bytes) else ''


def oauth_error_code(body):
    """The ``error`` code in an OAuth error response, or None.

    RFC 6749, section 5.2: the token endpoint answers a failed request with
    a JSON object whose ``error`` member says why.
    """
    try:
        document = json.loads(body)
    except (ValueError, RecursionError):
        return None
    error = document.get('error') if isinstance(document, dict) else None
    return error if isinstance(error, str) else None


def http_get_json(url, timeout=HTTP_TIMEOUT, ca_bundle=None):
    with urlopen(url, timeout=timeout, ca_bundle=ca_bundle) as response:
        return json.loads(read_limited(response, url).decode('utf-8'))


def http_post_form(
    url, form, timeout=HTTP_TIMEOUT, ca_bundle=None, expect_json=True
):
    """POST a form and return the JSON reply.

    With ``expect_json=False`` the reply is not read and None is returned,
    for endpoints such as token revocation (RFC 7009) that answer with an
    empty body.
    """
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urlopen(request, timeout=timeout, ca_bundle=ca_bundle) as response:
        if not expect_json:
            return None
        return json.loads(read_limited(response, url).decode('utf-8'))


def tls_verification_disabled(parsed_globals):
    """Whether the CLI was told to skip TLS certificate verification.

    The CLI's option to skip certificate verification sets verify_ssl=False;
    otherwise it is None or the CA bundle path.
    """
    return getattr(parsed_globals, 'verify_ssl', None) is False


def require_verified_tls(parsed_globals):
    """Refuse to skip TLS certificate verification for a bearer token call.

    The API call itself is made by botocore, which honors the CLI's option to
    skip certificate verification. Unlike a SigV4 signature, a bearer token
    can be replayed by anyone who reads it, so an unverified connection would
    hand it to whoever sits in the path.
    """
    if tls_verification_disabled(parsed_globals):
        raise AgentRegistryJWTError(
            "TLS verification can't be disabled with --authorizer JWT: "
            'unlike a SigV4 signature, the bearer token can be replayed by '
            'anything that intercepts the connection. If you use a '
            'TLS-inspecting proxy, trust its certificate authority with '
            '--ca-bundle instead.'
        )


# Registered at most once per event emitter, however often it is armed.
_UNVERIFIED_TLS_CHECK_ID = 'agent-registry-refuse-bearer-over-unverified-tls'


def arm_unverified_tls_check(event_emitter, parsed_globals):
    """Refuse bearer-signed calls when TLS verification is skipped.

    Botocore's events do not say whether a client verifies certificates, so
    the check is registered, on ``before-sign``, only for a command run with
    the option to skip verification. A client copies its session's emitter
    when it is created, so arming the session's emitter covers the clients
    created after it, and arming ``client.meta.events`` covers that client.
    """
    if tls_verification_disabled(parsed_globals):
        event_emitter.register(
            f'before-sign.{SERVICE}',
            refuse_bearer_signature,
            unique_id=_UNVERIFIED_TLS_CHECK_ID,
        )


def refuse_bearer_signature(signature_version=None, **kwargs):
    """Refuse a request that botocore is about to sign with a bearer token.

    Runs on ``before-sign``, which botocore emits once it has chosen the
    signer, from the operation's and the service's auth schemes, the
    endpoint's and any ``auth_scheme_preference``, and before it gets the
    token to put on the request. So it covers every token botocore can
    send, from ``AWS_BEARER_TOKEN_AGENT_REGISTRY`` or an IAM Identity Center
    sign-in (an ``sso_session`` profile), and leaves SigV4 calls alone.
    """
    if signature_version == BEARER_SIGNATURE_VERSION:
        raise AgentRegistryJWTError(
            "TLS verification can't be disabled for a request signed with a "
            f'bearer token, from {TOKEN_ENV_VAR} or an IAM Identity Center '
            'sign-in: unlike a SigV4 signature, the bearer token can be '
            'replayed by anything that intercepts the connection. Drop '
            '--no-verify-ssl, or, if you use a TLS-inspecting proxy, trust '
            'its certificate authority with --ca-bundle instead. To sign '
            f'with SigV4, do not select {BEARER_SCHEME} in '
            'AWS_AUTH_SCHEME_PREFERENCE or auth_scheme_preference.'
        )


# The model's RegistryIdentifier pattern: a registry ARN or a bare registry
# id, with the id captured. Used with fullmatch(), because '$' would also
# accept a trailing newline.
_REGISTRY_IDENTIFIER = re.compile(
    r'(?:arn:aws(?:-[^:]+)?:agent-registry:[a-z0-9-]+:[0-9]{12}:registry/)?'
    r'([a-zA-Z0-9]{12,16})'
)


def bare_registry_id(identifier):
    """The registry id in a registry ARN or id.

    The API accepts either form, but the id is what names the registry in its
    Protected Resource Metadata path and what the token cache is keyed by, so
    an ARN and its id share one sign-in. Anything else is refused rather than
    placed in a URL path or used as a cache key.
    """
    match = (
        _REGISTRY_IDENTIFIER.fullmatch(identifier)
        if isinstance(identifier, str)
        else None
    )
    if not match:
        raise AgentRegistryJWTError(
            f'Refusing registry identifier {identifier!r}: expected a '
            f'registry id of 12 to 16 letters and digits, or a registry ARN '
            f'(arn:<partition>:agent-registry:<region>:<account>:registry/'
            f'<id>).'
        )
    return match.group(1)


# Any data plane operation will do: the service's endpoint rules do not
# depend on the operation or its parameters. The registry id only fills in
# the request path, which is removed again. This operation adds no query
# string, so any query in the request URL came with the endpoint.
_ENDPOINT_PROBE_OPERATION = 'ListDiscoverableRegistryRecords'
_ENDPOINT_PROBE_REGISTRY_ID = 'endpointprobe'

# Where else an endpoint URL is configured, for an error that names the
# setting to fix. --endpoint-url, when given, overrides all of them.
_CONFIGURED_ENDPOINT_SETTINGS = (
    'AWS_ENDPOINT_URL_AGENT_REGISTRY, AWS_ENDPOINT_URL or endpoint_url in '
    'the config file'
)


def refuse_endpoint_query(url, parsed_globals):
    """Refuse a registry endpoint URL with a query string or fragment.

    The API call keeps them, but the endpoint the commands work with does
    not: it keys the cached sign-in, is recorded with each installed skill,
    and is where the registry's metadata is read from. So that one endpoint
    always means one registry, an endpoint is only a scheme, host and path.
    """
    parts = urllib.parse.urlsplit(url)
    if not parts.query and not parts.fragment:
        return
    setting = (
        '--endpoint-url'
        if getattr(parsed_globals, 'endpoint_url', None)
        else _CONFIGURED_ENDPOINT_SETTINGS
    )
    raise AgentRegistryJWTError(
        f'Refusing registry endpoint {url_origin(url)}: it has a query string '
        f'or fragment, and a registry endpoint can only have a scheme, host '
        f'and path. Remove the query string or fragment from {setting}.'
    )


def resolve_data_plane_endpoint(
    session, parsed_globals, region, https_only=True
):
    """The endpoint the data plane API call itself will be sent to.

    The bearer token goes to this endpoint, and its metadata decides which
    identity provider the user is sent to, so it is resolved by botocore from
    the same session and arguments as the API call. That applies
    ``--endpoint-url``, ``AWS_ENDPOINT_URL_*``, ``endpoint_url`` in the config
    file and the service's endpoint rules. Building the client needs no
    credentials. ``https_only=False`` is for a SigV4 call, which botocore may
    send over plain HTTP to a local endpoint. An endpoint with a query string
    or fragment is refused either way (:func:`refuse_endpoint_query`).

    The endpoint is read from a request that is stopped before it is signed
    or sent, as botocore's ``SSOTokenFetcherAuth`` finds the SSO OIDC
    endpoint: a ``before-call`` handler returns a response in its place.
    """
    try:
        client = session.create_client(
            SERVICE,
            region_name=region,
            endpoint_url=getattr(parsed_globals, 'endpoint_url', None),
            config=Config(signature_version=UNSIGNED),
        )
    except NoRegionError:
        raise AgentRegistryJWTError(
            'A region is required to locate the registry endpoint. Pass '
            '--region or configure a default region.'
        )
    requests = []

    def capture_request(params, **kwargs):
        requests.append(params)
        return AWSResponse(None, 200, {}, None), {}

    # client.meta.endpoint_url comes from the legacy resolver, which can
    # differ from the endpoint rules a request is actually sent by.
    client.meta.events.register_first(
        f'before-call.{SERVICE}.{_ENDPOINT_PROBE_OPERATION}', capture_request
    )
    client.list_discoverable_registry_records(
        registryId=_ENDPOINT_PROBE_REGISTRY_ID
    )
    if not requests:
        raise AgentRegistryJWTError('Could not resolve the registry endpoint.')
    # The request URL is the endpoint, including any base path, followed by
    # the operation's path and the endpoint's query and fragment, if any.
    refuse_endpoint_query(requests[0]['url'], parsed_globals)
    parts = urllib.parse.urlsplit(requests[0]['url'])
    path = parts.path.removesuffix(requests[0]['url_path'])
    endpoint = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, path, '', '')
    )
    if https_only:
        require_https(endpoint, 'registry endpoint')
    return endpoint.rstrip('/')


# RFC 6749, section 3.3: a scope token is printable ASCII other than space,
# double quote and backslash.
_SCOPE_TOKEN = re.compile(r'[\x21\x23-\x5b\x5d-\x7e]+')

# More advertised scopes than this is not a list to request, and a longer
# scope is not one the authorizer accepts (ACPS AllowedScopeType: 1 to 255).
MAX_ADVERTISED_SCOPES = 50
MAX_SCOPE_LENGTH = 255

# What a registry's Protected Resource Metadata says about signing in: the
# issuer it trusts and the scopes it advertises, which may be none.
RegistryAuthorization = collections.namedtuple(
    'RegistryAuthorization', ['issuer', 'scopes']
)


def _advertised_scopes(document, url):
    """The valid ``scopes_supported`` in the metadata, or ``[]``.

    A field of the wrong shape is ignored rather than refused: the scopes
    are only extras to request, and the defaults still work.
    """
    scopes = document.get('scopes_supported')
    if scopes is None:
        return []
    if (
        not isinstance(scopes, list)
        or len(scopes) > MAX_ADVERTISED_SCOPES
        or not all(
            isinstance(scope, str)
            and len(scope) <= MAX_SCOPE_LENGTH
            and _SCOPE_TOKEN.fullmatch(scope)
            for scope in scopes
        )
    ):
        logger.debug(
            'Ignoring scopes_supported in %s: not a list of at most %s '
            'scope tokens of at most %s characters',
            url,
            MAX_ADVERTISED_SCOPES,
            MAX_SCOPE_LENGTH,
        )
        return []
    return list(dict.fromkeys(scopes))


def discover_registry(endpoint, registry_id, ca_bundle=None):
    """Fetch RFC 9728 Protected Resource Metadata for the registry.

    Returns the issuer it trusts and the scopes it advertises, as a
    :data:`RegistryAuthorization`. Unauthenticated by design, so a caller
    with no credentials can learn where to authenticate. ``registry_id`` is
    the bare id from :func:`bare_registry_id`; it is quoted all the same, so
    it can only ever fill its own path segment.
    """
    url = endpoint + PRM_PATH.format(
        registry_id=urllib.parse.quote(registry_id, safe='')
    )
    logger.debug('Fetching protected resource metadata from %s', url)
    try:
        document = http_get_json(url, ca_bundle=ca_bundle)
    except urllib.error.HTTPError as e:
        raise AgentRegistryJWTError(
            f'Could not read protected resource metadata for registry '
            f'{registry_id} (HTTP {e.code}). Confirm the registry id and that '
            f'the registry uses a CUSTOM_JWT authorizer.'
        )
    except (
        urllib.error.URLError,
        ValueError,
        OSError,
        http.client.HTTPException,
    ) as e:
        # OSError and HTTPException: a read that timed out or stopped short.
        raise AgentRegistryJWTError(
            f'Could not read protected resource metadata from {url}: '
            f'{printable(e) or type(e).__name__}'
        )
    if not isinstance(document, dict):
        raise AgentRegistryJWTError(
            f'The protected resource metadata at {url} is not a JSON object.'
        )
    servers = document.get('authorization_servers') or []
    if not isinstance(servers, list):
        raise AgentRegistryJWTError(
            f'The protected resource metadata at {url} lists its '
            f'authorization_servers in something other than a JSON array.'
        )
    if not servers:
        raise AgentRegistryJWTError(
            f'Registry {registry_id} published no authorization servers, so '
            f'it is not configured for JWT authorization.'
        )
    if not isinstance(servers[0], str):
        raise AgentRegistryJWTError(
            f'The protected resource metadata at {url} names an '
            f'authorization server that is not a URL string.'
        )
    return RegistryAuthorization(
        require_https(servers[0], 'authorization server'),
        _advertised_scopes(document, url),
    )


# The discovery document entries the sign-in flow builds requests from.
_OIDC_ENDPOINT_KEYS = ('authorization_endpoint', 'token_endpoint')


def same_issuer(first, second):
    """Issuer identifiers compared exactly, but for one trailing slash."""
    return first.removesuffix('/') == second.removesuffix('/')


def fetch_oidc_metadata(issuer, ca_bundle=None):
    """The issuer's OIDC discovery document, or ``{}`` if it has none.

    Only an HTTP 404 counts as having no document; each provider explains
    that in its own terms. Any other failure to read it, such as an
    untrusted certificate, is reported as such rather than being mistaken
    for a missing document. A document that can be read but has the wrong
    shape is refused here, so it fails clearly instead of deep inside the
    sign-in flow. So is one published for another issuer (OpenID Connect
    Discovery, section 4.3): ``issuer`` is the one the registry's Protected
    Resource Metadata names, and every endpoint used for sign-in comes from
    this document.
    """
    require_https(issuer, 'issuer')
    url = issuer.rstrip('/') + OIDC_METADATA_PATH
    try:
        metadata = http_get_json(url, ca_bundle=ca_bundle)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise AgentRegistryJWTError(
                f'Could not read the OIDC discovery document of issuer '
                f'{issuer}: {printable(e)}'
            )
        logger.debug('No OIDC discovery document at %s', url)
        return {}
    except urllib.error.URLError as e:
        hint = ''
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            hint = (
                ' Use --ca-bundle to trust a custom certificate authority, '
                'such as one that inspects TLS traffic on a corporate network.'
            )
        raise AgentRegistryJWTError(
            f'Could not reach the OIDC discovery document of issuer '
            f'{issuer}: {printable(e.reason)}.{hint}'
        )
    except (ValueError, OSError, http.client.HTTPException) as e:
        raise AgentRegistryJWTError(
            f'Could not read the OIDC discovery document of issuer '
            f'{issuer}: {printable(e) or type(e).__name__}'
        )
    if not isinstance(metadata, dict):
        raise AgentRegistryJWTError(
            f'The OIDC discovery document at {url} is not a JSON object.'
        )
    for key in _OIDC_ENDPOINT_KEYS:
        value = metadata.get(key)
        if value is not None and not isinstance(value, str):
            raise AgentRegistryJWTError(
                f'The OIDC discovery document at {url} has a {key} that is '
                f'not a URL string.'
            )
    published = metadata.get('issuer')
    if not isinstance(published, str) or not same_issuer(published, issuer):
        named = (
            f'the issuer {printable(published)!r}'
            if isinstance(published, str)
            else 'no issuer'
        )
        raise AgentRegistryJWTError(
            f'The OIDC discovery document at {url} names {named}, not '
            f'{issuer}, which the registry trusts. Refusing to sign in with '
            f'endpoints published for another issuer.'
        )
    return metadata


def requested_scopes(metadata):
    supported = metadata.get('scopes_supported') or []
    # A string would be matched by substring, and anything else would fail.
    if not isinstance(supported, list):
        supported = []
    if not supported:
        return ['openid']
    chosen = [scope for scope in WANTED_SCOPES if scope in supported]
    return chosen or ['openid']


def with_scopes(defaults, extra):
    """The provider's default scopes and then ``extra``, once each."""
    return list(dict.fromkeys([*defaults, *extra]))


def looks_like_signed_jwt(token):
    """True for a three-part JWS.

    A five-part token is a JWE. Some providers issue an encrypted or opaque
    access token by default, and such a token cannot be validated by the
    registry's authorizer.
    """
    return isinstance(token, str) and len(token.split('.')) == 3


def select_bearer_token(payload):
    """Pick the token the registry can validate.

    Prefers the access token, which is what a resource server is meant to
    receive. Falls back to the id token when the access token is opaque or
    encrypted, because for some providers that is the only signed JWT
    available without registering an API resource.
    """
    if not isinstance(payload, dict):
        raise AgentRegistryJWTError(
            'The identity provider returned a token response that is not a '
            'JSON object.'
        )
    access = payload.get('access_token')
    if looks_like_signed_jwt(access):
        return access, 'access_token'
    # Falling back to the id_token is deliberate: providers such as Auth0
    # return an encrypted or opaque access token unless the owner registers
    # an API, which leaves the signed id_token as the only JWT the registry
    # can validate. Its audience is the client id, so the registry authorizer
    # must set allowedAudience to a client id dedicated to the CLI.
    identity = payload.get('id_token')
    if looks_like_signed_jwt(identity):
        write_status(
            'Note: the provider returned an opaque or encrypted access token, '
            'so the signed id_token is being used instead.'
        )
        return identity, 'id_token'
    if isinstance(access, str) and access:
        raise AgentRegistryJWTError(
            'The provider returned an access token that is not a signed JWT '
            f'({len(access.split("."))} segments) and no usable id_token, so '
            'the registry cannot validate it. The registry owner can '
            'configure the identity provider to issue signed JWT access '
            'tokens for this client.'
        )
    raise AgentRegistryJWTError(
        'The identity provider returned no access token.'
    )


# --- Log and history redaction ----------------------------------------------

_REDACTED = '<redacted>'
# Recorded in place of a history payload that could not be redacted.
_REDACTION_FAILED = '<redaction failed>'

# A bearer credential in an Authorization header, in str or bytes repr. The
# token alphabet is RFC 6750's b64token.
_BEARER_CREDENTIAL = re.compile(
    r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE
)

# A compact JWS (three parts) or JWE (five parts, some possibly empty). Every
# such token starts with the base64url encoding of '{"'. Botocore logs the
# bodies of the Cognito refresh call, which carry the refresh token and the
# new tokens.
_COMPACT_JWT = re.compile(r'eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]*){2,4}')

# The credential parts of a presigned S3 URL, such as the artifact download
# URL in a BatchGet response body.
_PRESIGNED_URL_CREDENTIAL = re.compile(
    r'((?:X-Amz-Signature|X-Amz-Credential|X-Amz-Security-Token)=)'
    r'[^&\s\'"\\]+',
    re.IGNORECASE,
)

# Fields that hold a token, whatever the token looks like: a rotated refresh
# token can be opaque, and is in botocore's logs before it is known here.
_TOKEN_FIELDS = (
    'RefreshToken',
    'AccessToken',
    'IdToken',
    'refresh_token',
    'access_token',
    'id_token',
)
_TOKEN_FIELD_NAMES = '|'.join(_TOKEN_FIELDS)
# "Field": "value" in JSON, and 'Field': 'value' in a Python repr.
_JSON_TOKEN_FIELD = re.compile(
    rf'("(?:{_TOKEN_FIELD_NAMES})"\s*:\s*")(?:[^"\\]|\\.)*(")'
)
_REPR_TOKEN_FIELD = re.compile(
    rf"('(?:{_TOKEN_FIELD_NAMES})'\s*:\s*')(?:[^'\\]|\\.)*(')"
)
# field=value in a form-encoded body or query string.
_FORM_TOKEN_FIELD = re.compile(rf'(\b(?:{_TOKEN_FIELD_NAMES})=)[^&\s\'"\\]*')

# Shorter values would redact ordinary text.
_MIN_SECRET_LENGTH = 8

# The loggers the CLI attaches its --debug handlers to, and the root logger.
_REDACTED_LOGGERS = ('', 'botocore', 'awscli', 's3transfer', 'urllib3')


def redact_secrets(text, secrets=()):
    """``text`` with bearer tokens, JWTs and presigned URL credentials removed.

    So are the values of token fields, in JSON, a Python repr or a form.
    ``secrets`` are literal values to remove as well, such as the bearer token
    in use, which need not look like a JWT.
    """
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, _REDACTED)
    text = _JSON_TOKEN_FIELD.sub(rf'\g<1>{_REDACTED}\g<2>', text)
    text = _REPR_TOKEN_FIELD.sub(rf'\g<1>{_REDACTED}\g<2>', text)
    text = _FORM_TOKEN_FIELD.sub(rf'\g<1>{_REDACTED}', text)
    text = _BEARER_CREDENTIAL.sub(rf'\g<1>{_REDACTED}', text)
    text = _COMPACT_JWT.sub(_REDACTED, text)
    return _PRESIGNED_URL_CREDENTIAL.sub(rf'\g<1>{_REDACTED}', text)


class _RedactSecrets(logging.Filter):
    """Removes credentials from a log record before a handler writes it.

    Attached to handlers rather than loggers, because a logger's filters do
    not apply to records propagated from its children, such as
    ``botocore.endpoint``.
    """

    def __init__(self):
        super().__init__()
        self.secrets = set()

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:
            # The handler reports a record that cannot be formatted.
            return True
        redacted = redact_secrets(message, self.secrets)
        if redacted != message:
            record.msg = redacted
            record.args = None
        if record.exc_info and not record.exc_text:
            # Formatters reuse exc_text instead of formatting the traceback
            # again.
            record.exc_text = redact_secrets(
                logging.Formatter().formatException(record.exc_info),
                self.secrets,
            )
        return True


_LOG_REDACTION = _RedactSecrets()


def _redacted(value, secrets):
    """A copy of a history payload with credentials removed.

    Copies rather than edits: an ``HTTP_REQUEST`` payload holds the headers
    of the request about to be sent, which must keep its token.
    """
    if isinstance(value, str):
        return redact_secrets(value, secrets)
    if isinstance(value, bytes):
        try:
            text = value.decode('utf-8')
        except UnicodeDecodeError:
            return value
        redacted = redact_secrets(text, secrets)
        return value if redacted == text else redacted.encode('utf-8')
    if isinstance(value, collections.abc.Mapping):
        return {
            key: (
                _REDACTED
                if key in _TOKEN_FIELDS and isinstance(item, (str, bytes))
                else _redacted(item, secrets)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redacted(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_redacted(item, secrets) for item in value)
    return value


def _redact_history(recorder):
    """Make ``recorder`` redact every payload before any handler sees it.

    With ``cli_history = enabled``, botocore records each request's headers
    and body and each response's body into the history database, which would
    store the bearer token, a refresh token sent to Cognito and presigned
    download URLs in plain text. The recorder has no hook for this, so its
    public ``record`` method is wrapped on the instance; botocore calls it
    through that instance, and handlers added later are covered too. Every
    payload is redacted, even one the recorder then discards because history
    is off, since only the recorder knows whether it keeps a payload.
    """
    record = recorder.record
    if getattr(record, 'redacts_secrets', False):
        return

    def redacting_record(event_type, payload, source='BOTOCORE'):
        try:
            payload = _redacted(payload, _LOG_REDACTION.secrets)
        except Exception as e:
            # Never the raw payload, and never an error on the request path.
            logger.debug(
                'Could not redact a %s history record (%s)',
                event_type,
                type(e).__name__,
            )
            payload = _REDACTION_FAILED
        record(event_type, payload, source)

    redacting_record.redacts_secrets = True
    recorder.record = redacting_record


def redact_logs_and_history(
    *secrets, loggers=_REDACTED_LOGGERS, recorder=None
):
    """Keep credentials out of the CLI's logs and its history database.

    Adds ``secrets`` to the literal values removed, alongside bearer tokens,
    JWTs and presigned URL credentials, and applies the removal to the
    handlers currently on ``loggers`` (including the ``--debug`` ones) and to
    the global history ``recorder``. The CLI attaches its ``--debug`` and
    history handlers before any command runs, so calling this at the start
    of a command covers everything the command logs or records.
    """
    _LOG_REDACTION.secrets.update(
        secret
        for secret in secrets
        if isinstance(secret, str) and len(secret) >= _MIN_SECRET_LENGTH
    )
    for name in loggers:
        for handler in logging.getLogger(name).handlers:
            # addFilter ignores a filter that is already attached.
            handler.addFilter(_LOG_REDACTION)
    _redact_history(recorder or get_global_history_recorder())


# --- Bearer token notes -----------------------------------------------------


def note_preset_token(arguments=()):
    """Say that a token already in the environment is sent as is.

    ``arguments`` are the command's sign-in arguments, which go unused too.
    """
    unused = ['the cached sign-in', *arguments]
    if len(unused) == 1:
        listed, verb = unused[0], 'is'
    else:
        listed, verb = f'{", ".join(unused[:-1])} and {unused[-1]}', 'are'
    write_status(
        f'Using the token in {TOKEN_ENV_VAR}; {listed} {verb} not used.'
    )


# The registry whose cached sign-in this command sends, for the hint on a
# 401. A CLI process runs one command.
_SIGNED_IN = {'registry_id': None, 'hinted': False}


def remember_signed_in_registry(registry_id):
    _SIGNED_IN['registry_id'] = registry_id


def hint_sign_out_on_unauthorized(http_response=None, **kwargs):
    """After a 401 to a call with a cached sign-in, say how to start over.

    Registered for ``after-call``, which botocore emits before it raises the
    error, so the error itself is unchanged. Returns None, so it never
    replaces the response.
    """
    registry_id = _SIGNED_IN['registry_id']
    if (
        registry_id is None
        or _SIGNED_IN['hinted']
        or getattr(http_response, 'status_code', None) != 401
    ):
        return
    _SIGNED_IN['hinted'] = True
    write_status(
        "If the registry's sign-in settings changed, run: aws "
        f'agent-registry sign-out --registry-id {registry_id}'
    )
