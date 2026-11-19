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
"""On-disk cache for registry bearer tokens.

One file per endpoint and registry, in a folder alongside botocore's SSO
token cache and laid out the same way: the file name is a hash of the key and,
on POSIX, the folder is ``0700`` and each file ``0600``, the permissions
botocore uses for its own token files. On Windows, as for ``~/.aws/sso/cache``,
the user profile's default access control applies. Keeping entries apart means
parallel calls for different registries cannot overwrite each other, and a
token is only ever reused for the endpoint it was issued for.

The ``pending-revocation`` folder inside it holds the refresh tokens that
``sign-out`` removed with a sign-in but could not revoke, so that a later
``sign-out`` can retry the revocation. It has one file per endpoint and
registry too, each holding a list of tokens, written the same way and with
the same permissions. Its name is the registry id, then the hash an entry is
named by, so that a file that cannot be read can still be told apart as a
registry's. Nothing that signs in or refreshes reads it.
"""

import base64
import hashlib
import json
import logging
import os
import re
import tempfile
import time
import urllib.error

from botocore.exceptions import ClientError

from awscli.customizations.agentregistry.constants import (
    EXPIRY_SKEW_SECONDS,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    botocore_session,
    discover_registry,
    http_post_form,
    looks_like_signed_jwt,
    oauth_error_code,
    printable,
    read_error_body,
    redact_logs_and_history,
    same_issuer,
    select_bearer_token,
    write_status,
)

logger = logging.getLogger(__name__)

# Mirrors ~/.aws/sso/cache, where botocore keeps Identity Center tokens.
CACHE_DIR = os.path.join(
    os.path.expanduser('~'), '.aws', 'agent-registry', 'cache'
)

# The name of an entry file: the SHA-256 hex digest of its key.
_ENTRY_NAME = re.compile(r'[0-9a-f]{64}\.json')

# The folder, inside CACHE_DIR, of the refresh tokens sign-out could not
# revoke, and what is kept of each. A file there holds its registry and
# endpoint as an entry does, and is named '<registry id>.<entry name>'. The
# id is put in a path only if it has the form of a bare registry id
# (bare_registry_id); a file for any other id has the entry name alone.
_PENDING_REVOCATION = 'pending-revocation'
_REGISTRY_ID = re.compile(r'[a-zA-Z0-9]{12,16}')
_PENDING_NAME = re.compile(r'(?:([a-zA-Z0-9]{12,16})\.)?[0-9a-f]{64}\.json')
_PENDING_TOKEN_FIELDS = (
    'refreshToken',
    'revocationEndpoint',
    'clientId',
    'issuer',
)

# The temp file a write goes through before its rename. One left behind by a
# write that never finished, for example one killed mid-write, can hold a
# token; writes remove those older than this, and "sign-out --all" removes
# them all.
_TEMP_NAME = re.compile(r'\.tmp-[^/\\]*\.json')
_STALE_TEMP_SECONDS = 300

# The most of a token endpoint's error body that is read. It is parsed for
# its OAuth error code, which can follow a long error_description, so this
# is more than is shown.
_ERROR_BODY_BYTES = 64 * 1024

# The Cognito errors that mean the refresh token itself is no longer
# accepted, Cognito's equivalent of RFC 6749's invalid_grant. A refresh token
# that has expired, been revoked or is not valid for the app client gets
# NotAuthorizedException, as does one whose user is disabled; one spent by
# refresh token rotation gets RefreshTokenReuseException; one whose user was
# deleted gets UserNotFoundException, unless the pool hides that as
# NotAuthorizedException. None of them can succeed on a retry. The rest of
# GetTokensFromRefreshToken's errors, such as TooManyRequestsException,
# InternalErrorException, ForbiddenException (WAF), the Lambda trigger errors
# and ResourceNotFoundException (the pool or app client is gone, which a new
# sign-in cannot fix either), are not about the refresh token.
_COGNITO_REJECTIONS = frozenset(
    (
        'NotAuthorizedException',
        'RefreshTokenReuseException',
        'UserNotFoundException',
    )
)


def _restrict_permissions(path, mode=0o600):
    """Make a cache file or folder accessible only by its owner.

    ``os.chmod`` has no meaningful effect on Windows, where POSIX mode bits are
    not enforced, so the file is created with a restrictive mode instead of
    relaxed-then-tightened. On Windows the containing directory under the user
    profile provides the practical boundary.
    """
    if os.name == 'nt':
        return
    try:
        os.chmod(path, mode)
    except OSError as e:
        logger.debug('Could not restrict permissions on %s: %s', path, e)


def _file_name(endpoint, registry_id):
    key = f'{endpoint}|{registry_id}'.encode()
    return hashlib.sha256(key).hexdigest() + '.json'


def entry_path(endpoint, registry_id):
    """The file for ``registry_id`` at ``endpoint``.

    ``endpoint`` is the one botocore resolves for the API call and
    ``registry_id`` is the bare id, so an ARN and its id share an entry while
    the same id at another endpoint, region or partition does not.
    """
    return os.path.join(CACHE_DIR, _file_name(endpoint, registry_id))


def pending_revocation_dir():
    """The folder of the refresh tokens that sign-out could not revoke."""
    return os.path.join(CACHE_DIR, _PENDING_REVOCATION)


def _pending_file_name(endpoint, registry_id):
    name = _file_name(endpoint, registry_id)
    if isinstance(registry_id, str) and _REGISTRY_ID.fullmatch(registry_id):
        return f'{registry_id}.{name}'
    return name


def pending_revocation_path(endpoint, registry_id):
    """The file of the pending revocations for ``registry_id`` at ``endpoint``.

    ``<registry id>.<entry name>``, where the entry name is the one
    :func:`entry_path` gives, or the entry name alone for a registry id not
    in the form of a bare one.
    """
    return os.path.join(
        pending_revocation_dir(), _pending_file_name(endpoint, registry_id)
    )


def pending_revocation_registry(path):
    """The registry id in the name of the pending-revocation file ``path``.

    None if the name has none. Unlike the file's contents, this is known
    even for a file that cannot be read.
    """
    match = _PENDING_NAME.fullmatch(os.path.basename(path))
    return match.group(1) if match else None


def _temp_files(directory):
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    return [
        os.path.join(directory, name)
        for name in names
        if _TEMP_NAME.fullmatch(name)
    ]


def list_temp_files():
    """Temp files of writes in progress or left unfinished.

    Those of the entries and those of the pending revocations. A write of
    either is complete before anything depends on it, so removing one loses
    nothing that was saved.
    """
    return _temp_files(CACHE_DIR) + _temp_files(pending_revocation_dir())


def _remove_stale_temp_files(directory):
    cutoff = time.time() - _STALE_TEMP_SECONDS
    for path in _temp_files(directory):
        try:
            if os.lstat(path).st_mtime < cutoff:
                os.remove(path)
        except OSError as e:
            logger.debug('Could not remove %s: %s', path, e)


def _write_entry(path, entry, directory=None):
    """Write ``entry`` to ``path``, in ``directory`` or else ``CACHE_DIR``."""
    directory = directory or CACHE_DIR
    for folder in dict.fromkeys((CACHE_DIR, directory)):
        os.makedirs(folder, mode=0o700, exist_ok=True)
        # makedirs leaves an existing directory's mode alone, so tighten it
        # too.
        _restrict_permissions(folder, 0o700)
    _remove_stale_temp_files(directory)
    # On POSIX, mkstemp creates the file 0600, so the token is never readable
    # by others, and the rename replaces the entry in one step, so a reader
    # never sees a partial write.
    fd, temp = tempfile.mkstemp(dir=directory, prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(entry, f, indent=2)
        os.replace(temp, path)
    except BaseException:
        try:
            os.remove(temp)
        except OSError:
            pass
        raise


def _read_json(path):
    try:
        with open(path) as f:
            document = json.load(f)
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def read_entry(endpoint, registry_id):
    """The cached entry for ``registry_id`` at ``endpoint``, or None."""
    entry = _read_json(entry_path(endpoint, registry_id))
    if (
        entry is None
        or entry.get('endpoint') != endpoint
        or entry.get('registryId') != registry_id
    ):
        return None
    return entry


def list_entries():
    """Every entry file as ``(path, entry)``, with None if unreadable."""
    try:
        names = sorted(os.listdir(CACHE_DIR))
    except OSError:
        return []
    return [
        (
            os.path.join(CACHE_DIR, name),
            _read_json(os.path.join(CACHE_DIR, name)),
        )
        for name in names
        if _ENTRY_NAME.fullmatch(name)
    ]


# --- Pending revocations ----------------------------------------------------


def _pending_tokens(document):
    """The document's list of pending tokens, or None if it is malformed.

    Each token must have a refresh token and a revocation endpoint, and the
    fields of :data:`_PENDING_TOKEN_FIELDS` it has must be strings.
    """
    tokens = document.get('tokens')
    if not isinstance(tokens, list) or not tokens:
        return None
    for token in tokens:
        if (
            not isinstance(token, dict)
            or not token.get('refreshToken')
            or not token.get('revocationEndpoint')
            or not all(
                isinstance(token[field], str)
                for field in _PENDING_TOKEN_FIELDS
                if field in token
            )
        ):
            return None
    return tokens


def read_pending_revocation(path):
    """The pending revocations in ``path``, as ``(document, problem)``.

    ``document`` is ``{'registryId', 'endpoint', 'tokens'}``, each token
    holding the fields of :data:`_PENDING_TOKEN_FIELDS`, and ``problem`` is
    None. A file that cannot be read, or holds anything else, is
    ``(None, why)``; a missing one is ``(None, None)``. The refresh tokens of
    a document that is read are redacted from the CLI's logs and history.
    """
    try:
        with open(path) as f:
            document = json.load(f)
    except FileNotFoundError:
        return None, None
    except OSError as e:
        return None, str(e)
    except (ValueError, RecursionError):
        return None, 'it is not valid JSON'
    if not isinstance(document, dict):
        return None, 'it is not a JSON object'
    registry_id = document.get('registryId')
    endpoint = document.get('endpoint')
    if not (
        isinstance(registry_id, str)
        and registry_id
        and isinstance(endpoint, str)
        and endpoint
    ):
        return None, 'it names no registry or no endpoint'
    if os.path.basename(path) != _pending_file_name(endpoint, registry_id):
        return None, 'its name does not match the registry and endpoint in it'
    tokens = _pending_tokens(document)
    if tokens is None:
        return None, 'it holds no list of refresh tokens to revoke'
    redact_logs_and_history(*(token['refreshToken'] for token in tokens))
    return {
        'registryId': registry_id,
        'endpoint': endpoint,
        'tokens': tokens,
    }, None


def list_pending_revocations():
    """Every pending-revocation file as ``(path, document, problem)``.

    As :func:`read_pending_revocation` reads it. A folder that exists but
    cannot be listed is reported as a file that cannot be read.
    """
    directory = pending_revocation_dir()
    try:
        names = sorted(os.listdir(directory))
    except FileNotFoundError:
        return []
    except OSError as e:
        return [(directory, None, str(e))]
    pending = []
    for name in names:
        if not _PENDING_NAME.fullmatch(name):
            continue
        path = os.path.join(directory, name)
        document, problem = read_pending_revocation(path)
        if document is not None or problem is not None:
            pending.append((path, document, problem))
    return pending


def add_pending_revocation(entry):
    """Keep the refresh token of ``entry``, whose revocation failed.

    It is added to the list for the entry's registry and endpoint, once.
    Raises ``OSError`` if it cannot be written, or
    :class:`AgentRegistryJWTError` if the entry lacks what is kept, or the
    list already there cannot be read: that file is never overwritten,
    since it can hold tokens of its own.
    """
    registry_id = entry.get('registryId')
    endpoint = entry.get('endpoint')
    if not (
        isinstance(registry_id, str)
        and registry_id
        and isinstance(endpoint, str)
        and endpoint
    ):
        raise AgentRegistryJWTError(
            'the cached sign-in names no registry or no endpoint'
        )
    token = {
        field: entry[field]
        for field in _PENDING_TOKEN_FIELDS
        if isinstance(entry.get(field), str) and entry[field]
    }
    if 'refreshToken' not in token or 'revocationEndpoint' not in token:
        raise AgentRegistryJWTError(
            'the cached sign-in has no refresh token or revocation endpoint '
            'that can be kept'
        )
    path = pending_revocation_path(endpoint, registry_id)
    document, problem = read_pending_revocation(path)
    if problem is not None:
        raise AgentRegistryJWTError(f'could not read {path}: {problem}')
    tokens = document['tokens'] if document else []
    if all(kept['refreshToken'] != token['refreshToken'] for kept in tokens):
        tokens = [*tokens, token]
    _write_entry(
        path,
        {'registryId': registry_id, 'endpoint': endpoint, 'tokens': tokens},
        directory=pending_revocation_dir(),
    )


def remove_pending_revocations(path, revoked):
    """Remove the ``revoked`` refresh tokens from the file at ``path``.

    The file is read again first, so a token that another sign-out kept
    meanwhile stays; nothing locks the file across processes, so this
    narrows that race but cannot close it. The file is deleted once it
    holds no token. Raises ``OSError`` if it cannot be written or deleted,
    and :class:`AgentRegistryJWTError` if it cannot be read.
    """
    document, problem = read_pending_revocation(path)
    if problem is not None:
        raise AgentRegistryJWTError(f'could not read {path}: {problem}')
    if document is None:
        return
    left = [
        token
        for token in document['tokens']
        if token['refreshToken'] not in revoked
    ]
    if not left:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    elif len(left) < len(document['tokens']):
        _write_entry(
            path,
            dict(document, tokens=left),
            directory=pending_revocation_dir(),
        )


def _jwt_exp(token):
    """The ``exp`` claim of a JWT, read without verification.

    Used only to schedule a refresh. ``expires_in`` describes the access token,
    so when the id_token is cached instead its own expiry is what matters.
    """
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))['exp'])
    except Exception:
        return None


def _lifetime(expires_in):
    """``expires_in`` in whole seconds, or None if it is absent or unusable.

    The token endpoint chooses the value, and some send it as a string. One
    that is not a number, or is negative, is treated as absent, so the
    expiry comes from the token's own ``exp`` instead.
    """
    if isinstance(expires_in, bool):
        return None
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError, OverflowError):
        return None
    return seconds if seconds >= 0 else None


def save_token(
    endpoint,
    registry_id,
    token,
    expires_in,
    refresh_token,
    client_id=None,
    issuer=None,
    revocation_endpoint=None,
    pool_region=None,
    token_endpoint=None,
    scopes=None,
):
    """Write the entry for ``registry_id`` at ``endpoint``.

    ``pool_region`` (Amazon Cognito) or ``token_endpoint`` (any other OIDC
    issuer) says how the token is refreshed, ``revocation_endpoint`` is
    where ``sign-out`` revokes the refresh token, and ``scopes`` are those
    the token was issued for. A failed write is reported but not fatal: the
    token is still used for this call.
    """
    expires_in = _lifetime(expires_in)
    expires_at = int(time.time()) + (expires_in or 0)
    claimed = _jwt_exp(token)
    if claimed:
        expires_at = min(expires_at, claimed) if expires_in else claimed
    entry = {
        'registryId': registry_id,
        'endpoint': endpoint,
        'clientId': client_id,
        'issuer': issuer,
        'accessToken': token,
        'expiresAt': expires_at,
        'refreshToken': refresh_token,
        'revocationEndpoint': revocation_endpoint,
        'poolRegion': pool_region,
        'tokenEndpoint': token_endpoint,
        'scopes': list(scopes) if scopes else None,
    }
    entry = {key: value for key, value in entry.items() if value}
    try:
        _write_entry(entry_path(endpoint, registry_id), entry)
    except OSError as e:
        write_status(
            f'Warning: could not save the sign-in for registry {registry_id} '
            f'to the token cache ({printable(e)}). A fresh sign-in will be '
            f'needed next time.'
        )


def _expires_at(entry):
    value = entry.get('expiresAt')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return value


def _entry_scopes(entry):
    """The scopes the entry's token was issued for, in order."""
    scopes = entry.get('scopes')
    if not isinstance(scopes, list):
        return []
    return [scope for scope in scopes if isinstance(scope, str)]


def _matches(entry, client_id, scopes=()):
    """True if the entry is for ``client_id`` and has every one of ``scopes``.

    Without a ``client_id`` or ``scopes``, any entry matches.
    """
    registry_id = entry.get('registryId')
    if client_id and client_id != entry.get('clientId'):
        logger.debug(
            'Cached sign-in for %s is for another client id', registry_id
        )
        return False
    if not set(scopes) <= set(_entry_scopes(entry)):
        logger.debug(
            'Cached sign-in for %s lacks an advertised scope', registry_id
        )
        return False
    return True


def _fresh_token(entry):
    """The entry's token if it is a signed JWT that is not about to expire."""
    token = entry.get('accessToken')
    if (
        looks_like_signed_jwt(token)
        and _expires_at(entry) - EXPIRY_SKEW_SECONDS > time.time()
    ):
        return token
    return None


def _registry_changed(entry, endpoint, registry_id, ca_bundle):
    """Why the registry's metadata rules out a refresh, and its scopes.

    Checked only before a refresh. A registry that now trusts another issuer
    would get a token it rejects, and the refresh token would go to an issuer
    the registry no longer trusts; one that now advertises a scope the entry
    lacks needs a sign-in that requests it. Returns ``(reason, scopes)``,
    with no reason if neither changed. If the metadata cannot be read, the
    refresh goes ahead.
    """
    try:
        registry = discover_registry(
            endpoint, registry_id, ca_bundle=ca_bundle
        )
    except Exception as e:
        logger.debug(
            'Could not check the issuer and scopes of registry %s before '
            'refreshing: %s',
            registry_id,
            printable(e),
        )
        return None, []
    issuer = entry.get('issuer')
    if (
        isinstance(issuer, str)
        and issuer
        and not same_issuer(registry.issuer, issuer)
    ):
        return (
            f'The registry now trusts {printable(registry.issuer)}, not '
            f'{printable(issuer)}',
            registry.scopes,
        )
    if not _matches(entry, None, registry.scopes):
        return (
            "The registry now asks for scopes the cached sign-in doesn't "
            'have',
            registry.scopes,
        )
    return None, registry.scopes


def load_token(
    endpoint,
    registry_id,
    client_id=None,
    session=None,
    ca_bundle=None,
):
    """Return a usable cached token, refreshing silently when possible.

    A ``client_id`` other than the one the entry was signed in with is a miss,
    so the sign-in that follows replaces the entry. So is a registry that now
    trusts another issuer or advertises a scope the entry lacks, checked
    before a refresh; a token that is still valid is used as is. So is a
    refresh token the identity provider no longer accepts. Every caller signs
    in after a miss. Any other failure to refresh, such as a timeout or a
    server error, raises :class:`AgentRegistryJWTError` instead, because a
    sign-in would not fix it and would wait for a browser that unattended
    callers do not have. ``ca_bundle`` is used to verify the identity
    provider during a refresh.
    """
    entry = read_entry(endpoint, registry_id)
    if not entry or not _matches(entry, client_id):
        return None
    token = _fresh_token(entry)
    if token:
        logger.debug('Using cached bearer token for registry %s', registry_id)
        return token
    refresh_token = entry.get('refreshToken')
    if not isinstance(refresh_token, str) or not refresh_token:
        return None

    reason, advertised = _registry_changed(
        entry, endpoint, registry_id, ca_bundle
    )
    if reason:
        write_status(f'{reason}; signing in again.')
        return None

    # Read the entry again right before refreshing, since another process
    # may have refreshed it during the metadata check: with rotation, sending
    # the refresh token read earlier would replay one it already spent. This
    # narrows that race but cannot close it, as nothing locks the entry
    # across processes; the failure handling below covers the rest.
    latest = read_entry(endpoint, registry_id)
    if (
        not latest
        or not _matches(latest, client_id, advertised)
        or latest.get('issuer') != entry.get('issuer')
    ):
        # Signed out or signed in again meanwhile; the issuer that was just
        # checked is the one to send a refresh token to.
        return None
    if _refreshed_meanwhile(entry, latest):
        token = _fresh_token(latest)
        if token:
            logger.debug(
                'Using the sign-in another process refreshed for %s',
                registry_id,
            )
            return token
    entry = latest
    refresh_token = entry.get('refreshToken')
    if not isinstance(refresh_token, str) or not refresh_token:
        return None

    logger.debug('Cached token expired; refreshing for %s', registry_id)
    redact_logs_and_history(refresh_token)
    try:
        token, expires_in, rotated = _refresh(entry, session, ca_bundle)
    except Exception as e:
        # Another process may have refreshed meanwhile, and with rotation
        # that spends the refresh token this one sent.
        latest = read_entry(endpoint, registry_id)
        if (
            latest
            and _matches(latest, client_id, advertised)
            and _refreshed_meanwhile(entry, latest)
        ):
            token = _fresh_token(latest)
            if token:
                logger.debug(
                    'Using the sign-in another process refreshed for %s',
                    registry_id,
                )
                return token
        rejected, reason = _refresh_failure(e)
        # The reason can carry text chosen by the identity provider.
        if rejected:
            write_status(
                f'The identity provider no longer accepts the cached sign-in '
                f'for registry {registry_id} ({printable(reason)}); signing '
                f'in again.'
            )
            return None
        raise AgentRegistryJWTError(
            f'Could not refresh the cached sign-in for registry '
            f'{registry_id} ({printable(reason)}). Try again; to sign in '
            f'from scratch instead, run aws agent-registry sign-out '
            f'--registry-id {registry_id} first.'
        )
    if not token:
        return None
    # Carry every provider hint forward, otherwise the *next* refresh has
    # nothing to work with. A provider that rotates refresh tokens invalidates
    # the old one, so keep the new one when it is issued.
    if not isinstance(rotated, str) or not rotated:
        rotated = refresh_token
    redact_logs_and_history(token, rotated)
    save_token(
        endpoint,
        registry_id,
        token=token,
        expires_in=expires_in or 3600,
        refresh_token=rotated,
        client_id=entry.get('clientId'),
        issuer=entry.get('issuer'),
        revocation_endpoint=entry.get('revocationEndpoint'),
        pool_region=entry.get('poolRegion'),
        token_endpoint=entry.get('tokenEndpoint'),
        scopes=_entry_scopes(entry),
    )
    return token


def _refresh_failure(error):
    """``(rejected, reason)`` for an exception a refresh raised.

    ``rejected`` is True only if the identity provider refused the refresh
    token itself, the one failure a new sign-in fixes: RFC 6749's
    ``invalid_grant`` (section 5.2), or one of :data:`_COGNITO_REJECTIONS`.
    """
    if isinstance(error, urllib.error.HTTPError):
        body = read_error_body(error, _ERROR_BODY_BYTES)
        # RFC 6749 sends invalid_grant with HTTP 400, but providers differ:
        # some use 401, and Auth0 uses 403. With a 5xx, the server failed.
        rejected = (
            400 <= error.code < 500
            and oauth_error_code(body) == 'invalid_grant'
        )
        detail = f': {body}' if body.strip() else ''
        return rejected, f'HTTP {error.code} from the token endpoint{detail}'
    if isinstance(error, ClientError):
        code = error.response.get('Error', {}).get('Code')
        return code in _COGNITO_REJECTIONS, str(error)
    if isinstance(error, urllib.error.URLError):
        return False, str(error.reason) or type(error).__name__
    return False, str(error) or type(error).__name__


def _refreshed_meanwhile(entry, latest):
    """True if ``latest`` was written after ``entry``, by another refresh."""
    return latest.get('refreshToken') != entry.get('refreshToken') or (
        _expires_at(latest) > _expires_at(entry)
    )


def _refresh(entry, session, ca_bundle=None):
    """Return ``(token, expires_in, rotated_refresh_token)``."""
    if entry.get('poolRegion'):
        # Cognito refreshes through its own API rather than an OAuth grant.
        from awscli.customizations.agentregistry.providers import (
            CognitoProvider,
        )

        return CognitoProvider.refresh(
            session or botocore_session(), entry, ca_bundle
        )
    if entry.get('tokenEndpoint'):
        # Any other OIDC issuer: RFC 6749 refresh_token grant.
        payload = http_post_form(
            entry['tokenEndpoint'],
            {
                'grant_type': 'refresh_token',
                'refresh_token': entry['refreshToken'],
                'client_id': entry.get('clientId', ''),
            },
            ca_bundle=ca_bundle,
        )
        # Same selection as at sign-in: some providers return an encrypted
        # access token on refresh, which the registry cannot validate.
        token, _ = select_bearer_token(payload)
        return token, payload.get('expires_in'), payload.get('refresh_token')
    return None, None, None
