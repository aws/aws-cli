# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The fake credential daemon's constants, errors and helpers.

server.py and the mixins (_store, _signin, _faults) all import from here, so
none of them imports another.
"""

import contextlib
import dataclasses
import datetime
import hashlib
import json
import re
import secrets
import socket
import urllib.parse

PROTOCOL_VERSION = 1
VERSION = '0.0.0-mock'
MAX_LINE_BYTES = 1024 * 1024

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
DOMAIN_ERROR = -32000
# What credsd refuses while the caller's configuration doesn't
# validate. credential/describe is one too, which the fake doesn't have.
CONFIG_CHECKED_METHODS = (
    'credential/get',
    'credential/list',
    'credential/tag',
)

LOGIN_METHOD = 'credential/login'
# Sign-In's client for --remote, which the credential daemon sends in the
# authorize URL.
CROSS_DEVICE = urllib.parse.quote(
    'arn:aws:signin:::devtools/cross-device', safe=''
)
# Methods that can send progress notifications and wait for answers.
SIGN_IN_METHODS = ('credential/bootstrap', LOGIN_METHOD)
DEFAULT_MFA_DURATION = 12 * 3600
# Real credsd's CALLBACK_PORT_MIN (oauth/callback.rs).
AWS_LOGIN_MIN_CALLBACK_PORT = 1024
# The credential daemon's text for STS's error (iam_user.rs, error.rs).
WRONG_MFA_CODE_MESSAGE = (
    'provider error: MultiFactorAuthentication failed with invalid MFA one '
    'time pass code.'
)
# The credential daemon's material kind, its credential/list and
# credential/get kind, for every credential the CLI uses.
MATERIAL_KIND = 'session_credentials'

# credential/import's statuses and skip reason, in credsd's words
# (credsd-core rpc/methods.rs ImportStatus, import.rs decide).
IMPORT_IMPORTED = 'imported'
IMPORT_SKIPPED = 'skipped'
ALREADY_EXISTS = 'a credential with this name already exists'
# The credential daemon's source of each credential the CLI uses. The fake
# keeps it as Credential.kind, and list rows carry it as source.
KIND_LOGIN = 'aws_login'
KIND_IAM_USER = 'aws_iam_user'
KIND_SSO = 'aws_idc_sso'
PROVIDER_KINDS = {
    'aws_iam_user': KIND_IAM_USER,
    'aws_login': KIND_LOGIN,
    'aws_idc_sso': KIND_SSO,
    'sso': KIND_SSO,
}

# credsd's SessionStatus values, as credential/list sends them. Only an active
# or expiring credential is usable.
ACTIVE = 'active'
EXPIRING = 'expiring'
EXPIRED = 'expired'
SIGN_IN_REQUIRED = 'sign_in_required'
NO_SESSION = 'no_session'
CORRUPT = 'corrupt'
UNREADABLE = 'unreadable'
DECRYPT_FAILED = 'decrypt_failed'
UNKNOWN = 'unknown'
STATUSES = (
    ACTIVE,
    EXPIRING,
    EXPIRED,
    SIGN_IN_REQUIRED,
    NO_SESSION,
    CORRUPT,
    UNREADABLE,
    DECRYPT_FAILED,
    UNKNOWN,
)
USABLE_STATUSES = (ACTIVE, EXPIRING)
# The sources credential/logout signs out.
SIGN_IN_SOURCES = (KIND_LOGIN, KIND_SSO, 'aws_web_identity')
# credential/logout's provider values.
SSO_LOGOUT_ENDED = 'ended'
SSO_LOGOUT_TOKEN_REJECTED = 'token_rejected'
SSO_LOGOUT_FAILED = 'failed'
LOGOUT_LOCAL_ONLY = 'local_only'
LOGOUT_NONE = 'none'
SSO_LOGOUT_OUTCOMES = (
    SSO_LOGOUT_ENDED,
    SSO_LOGOUT_TOKEN_REJECTED,
    SSO_LOGOUT_FAILED,
)
# The start URL a failed SSO logout names for a seeded SSO credential,
# which has none of its own.
DEFAULT_START_URL = 'https://d-1234567890.awsapps.com/start'
# set_sso_logout's default: the session's own end.
_SESSION_END = object()

DEFAULT_ACCOUNT_ID = '123456789012'
DEFAULT_PRINCIPAL = (
    f'arn:aws:sts::{DEFAULT_ACCOUNT_ID}:assumed-role/Admin/alice'
)
DEFAULT_IAM_USER_PRINCIPAL = f'arn:aws:iam::{DEFAULT_ACCOUNT_ID}:user/alice'
DEFAULT_ROLES = (
    {
        'account_id': '123456789012',
        'account_name': 'dev',
        'role_name': 'Admin',
    },
    {
        'account_id': '123456789012',
        'account_name': 'dev',
        'role_name': 'ReadOnly',
    },
    {
        'account_id': '555555555555',
        'account_name': 'prod',
        'role_name': 'ReadOnly',
    },
)

_NAME_RE = re.compile(r'^(?!\.)[A-Za-z0-9._-]{1,64}$')
# credsd's credential tag rules (credsd-core tags.rs).
_TAG_KEY_RE = re.compile(r'[a-z0-9][a-z0-9._-]{0,62}')
_TAG_VALUE_RE = re.compile(r'[\x20-\x7e]{0,256}')
MAX_TAGS = 32
_FOLD = str.maketrans(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'
)
_NAME_PREFIX_RE = re.compile(r'^(?!\.)[A-Za-z0-9._-]{1,32}$')
_DISALLOWED_NAME_CHARACTER = re.compile(r'[^A-Za-z0-9._-]')
NAME_MAX_LENGTH = 64
_NAME_HASH_LENGTH = 8
_BASE64_RE = re.compile(r'[A-Za-z0-9+/]*|[A-Za-z0-9_-]*')
_SECRET_FIELDS = frozenset(
    [
        'access_key_id',
        'secret_access_key',
        'session_token',
        'token',
        'selection',
        'refresh_token',
    ]
)
_PARAMS = {
    'system/health': (),
    'credential/list': ('tags',),
    'credential/get': (
        'credential',
        'account_id',
        'role_name',
        'material',
        'request_id',
    ),
    'credential/import': (
        'credential',
        'access_key_id',
        'secret_access_key',
        'region',
        'session_token',
        'mfa_serial',
        'duration_seconds',
        'creator',
    ),
    'credential/logout': ('credential',),
    'credential/remove': ('credential',),
    'credential/bootstrap': (
        'credential',
        'name_prefix',
        'provider',
        'creator',
        'tags',
    ),
    'credential/tag': ('credential', 'set', 'unset'),
    'credential/bootstrap/respond': (
        'request_id',
        'roles',
        'selection',
    ),
    LOGIN_METHOD: ('credential',),
}
_PROVIDER_PARAMS = {
    KIND_LOGIN: ('type', 'region', 'remote', 'multi_role', 'callback_port'),
    KIND_SSO: (
        'type',
        'start_url',
        'sso_region',
        'scopes',
        'use_device_code',
        'select_account_and_role',
        'callback_port',
    ),
    KIND_IAM_USER: (
        'type',
        'access_key_id',
        'secret_access_key',
        'region',
        'mfa_serial',
        'duration_seconds',
    ),
}


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        error = {'code': self.code, 'message': self.message}
        if self.data is not None:
            error['data'] = self.data
        return error


class DomainError(RpcError):
    """A credential daemon domain error: code -32000 with ``data.code``."""

    def __init__(self, data_code, message, **data):
        super().__init__(DOMAIN_ERROR, message, dict(data, code=data_code))


class InvalidParams(RpcError):
    def __init__(self, message):
        super().__init__(INVALID_PARAMS, message)


@dataclasses.dataclass
class Credential:
    name: str
    kind: str
    principal: str = None
    account_id: str = None
    status: str = ACTIVE
    session_expires_at: datetime.datetime = None
    provider: dict = dataclasses.field(default_factory=dict)
    # What the credential daemon seals. Nothing here leaves the fake.
    secrets: dict = dataclasses.field(default_factory=dict, repr=False)
    # The MFA device stored at import, and the MFA session it started.
    mfa_serial: str = None
    mfa_duration: int = DEFAULT_MFA_DURATION
    mfa_expires_at: datetime.datetime = None
    tags: dict = dataclasses.field(default_factory=dict)

    def current_status(self, now):
        if self.status in USABLE_STATUSES and (
            self.session_expires_at is not None
            and now >= self.session_expires_at
        ):
            return EXPIRED
        return self.status

    def describe(self, now):
        row = {
            'credential': self.name,
            'kind': MATERIAL_KIND,
            'source': self.kind,
            'status': self.current_status(now),
            'tags': dict(self.tags),
        }
        return row


def _check_params(method, params):
    unknown = set(params) - set(_PARAMS[method])
    if unknown:
        raise InvalidParams(f'Unknown params for {method}: {sorted(unknown)}')


def _tag_error(name, detail):
    if name is None:
        return InvalidParams(detail)
    return InvalidParams(f"credential '{name}': {detail}")


def _fold_tag_keys(tags, name=None):
    """``tags`` with each key folded to lowercase (``A-Z`` only), as
    credsd does. Two spellings of one key are refused."""
    if not isinstance(tags, dict):
        raise _tag_error(name, 'tags must be an object')
    folded = {}
    spelled = {}
    for key, value in tags.items():
        low = key.translate(_FOLD)
        if low in spelled:
            raise _tag_error(
                name,
                f'tag keys {spelled[low]!r} and {key!r} are the same key '
                'once folded to lowercase',
            )
        spelled[low] = key
        folded[low] = value
    return folded


def _check_tag_key(key, name=None):
    if not _TAG_KEY_RE.fullmatch(key):
        raise _tag_error(
            name,
            f'tag key {key!r} must be 1-63 of a-z 0-9 . _ - starting with '
            'a-z or 0-9',
        )


def _check_tag_value(key, value, name=None):
    # Never echoes the value, as credsd doesn't.
    if not isinstance(value, str) or not _TAG_VALUE_RE.fullmatch(value):
        raise _tag_error(
            name,
            f'tag {key!r} value must be at most 256 bytes of printable ASCII',
        )


def _checked_tags(tags, name=None):
    """A credential's tags, folded and checked as credsd does."""
    tags = _fold_tag_keys(tags, name)
    if len(tags) > MAX_TAGS:
        raise _tag_error(name, f'{len(tags)} tags; the maximum is {MAX_TAGS}')
    for key, value in tags.items():
        _check_tag_key(key, name)
        _check_tag_value(key, value, name)
    return tags


def _tag_filter(wanted):
    """A credential/list ``tags`` filter, folded and checked. A ``null``
    value needs only the key."""
    if wanted is None:
        return {}
    wanted = _fold_tag_keys(wanted)
    for key, value in wanted.items():
        _check_tag_key(key)
        if value is not None:
            _check_tag_value(key, value)
    return wanted


def _tags_match(tags, wanted):
    return all(
        key in tags and (value is None or tags[key] == value)
        for key, value in wanted.items()
    )


def _require_str(params, key):
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise InvalidParams(f'{key} must be a non-empty string')
    return value


def _callback_port(provider):
    port = provider.get('callback_port', 0)
    if isinstance(port, bool) or not isinstance(port, int):
        raise InvalidParams('callback_port must be an integer')
    if 'callback_port' in provider and not 1 <= port <= 65535:
        raise InvalidParams('callback_port must be between 1 and 65535')
    return port


def _aws_login_callback_port(provider):
    # Real credsd's range and words for aws-login (bootstrap.rs, 066082d).
    port = provider.get('callback_port')
    if (
        isinstance(port, int)
        and not isinstance(port, bool)
        and not AWS_LOGIN_MIN_CALLBACK_PORT <= port <= 65535
    ):
        raise InvalidParams(
            f'callback_port must be {AWS_LOGIN_MIN_CALLBACK_PORT}\u201365535; '
            f'omit the field for an ephemeral port'
        )
    return _callback_port(provider)


def _is_base64(text):
    # The credential daemon takes the standard or URL-safe alphabet, padded or
    # not.
    body = text.rstrip('=')
    if len(body) % 4 == 1:
        return False
    return _BASE64_RE.fullmatch(body) is not None


@contextlib.contextmanager
def _redirect_listener(port):
    """Listen on 127.0.0.1 for the browser's redirect, and yield the port."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            listener.bind(('127.0.0.1', port))
        except OSError as e:
            raise DomainError(
                'REDIRECT_PORT_IN_USE',
                f'Can\'t listen on port {port}: {e.strerror}',
            )
        listener.listen(1)
        yield listener.getsockname()[1]
    finally:
        listener.close()


def _reauth_detail(credential):
    # credsd's ReauthInput: a code for keys with an MFA device, else the
    # browser.
    if credential.kind == KIND_IAM_USER and credential.mfa_serial:
        return f'enter your MFA code for {credential.mfa_serial}'
    return 'complete SSO sign-in in a browser'


def _reauth_required(name, detail):
    """credsd's REAUTH_REQUIRED for a credential: its message, and
    ``credential`` and ``remediation`` in ``data``. credsd says "complete SSO
    sign-in in a browser" for every sign-in source, aws login included."""
    return DomainError(
        'REAUTH_REQUIRED',
        f"credential '{name}' requires re-authentication ({detail})",
        credential=name,
        remediation=f'creds login --credential {name}',
    )


def _require_name(params, key='name'):
    name = params.get(key)
    _validate_name(name)
    return name


def _validate_name(name):
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise InvalidParams(
            f'Invalid credential name {name!r}: use up to 64 of '
            f'A-Z a-z 0-9 . _ - and don\'t start with "."'
        )


def identity_credential_name(prefix, principal):
    """The name the credential daemon gives a ``name_prefix`` aws-login
    credential, as credsd's ``name_under`` and ``normalize_name`` do.

    ``login.`` and ``arn:aws:sts::111111111111:assumed-role/Admin/alice`` give
    ``login.111111111111-role-Admin``, whatever the session. An IAM user
    gives ``login.<account>-user-<user name>`` and the root user
    ``login.<account>-root``. A name with characters the credential daemon
    doesn't take, or longer than 64, is cleaned up.
    """
    identity = identity_record(principal)
    kind = identity['kind']
    account = identity['account']
    if kind == 'role':
        raw = f'{prefix}{account}-role-{identity["name"]}'
    elif kind == 'user':
        raw = f'{prefix}{account}-user-{identity["name"].rsplit("/", 1)[-1]}'
    elif kind == 'root':
        raw = f'{prefix}{account}-root'
    else:
        raw = f'{prefix}{principal}'
    if _NAME_RE.match(raw):
        return raw
    converted = _DISALLOWED_NAME_CHARACTER.sub('-', raw)
    converted = converted[: NAME_MAX_LENGTH - _NAME_HASH_LENGTH - 1]
    converted = converted.lstrip('.')
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f'{converted}-{digest[:_NAME_HASH_LENGTH]}'


def identity_record(principal):
    """The identity credsd records for an aws login sign-in, from the
    caller ARN.

    A role ARN gives ``kind`` ``role`` with the role and session names, an
    IAM user ``user`` with the user's path and name, and the root user
    ``root``. credsd refuses any other ARN; the fake keeps it, with an
    empty ``kind``.
    """
    identity = {
        'arn': principal,
        'partition': '',
        'account': '',
        'kind': '',
        'name': '',
        'session': '',
    }
    parts = principal.split(':', 5) if isinstance(principal, str) else []
    if len(parts) != 6 or parts[0] != 'arn':
        return identity
    _, partition, service, _, account, resource = parts
    identity['partition'] = partition
    identity['account'] = account
    if service == 'sts' and resource.startswith('assumed-role/'):
        role, _, session = resource[len('assumed-role/') :].partition('/')
        if role and session:
            identity.update(kind='role', name=role, session=session)
    elif service == 'iam' and resource.startswith('user/'):
        name = resource[len('user/') :]
        if name:
            identity.update(kind='user', name=name)
    elif service == 'iam' and resource == 'root':
        identity['kind'] = 'root'
    return identity


def principal_of(principal):
    """The principal credsd compares for an aws login sign-in: partition,
    account, kind and role or user name, without the session. None for no
    principal, or one credsd can't read."""
    identity = identity_record(principal)
    if not identity['kind']:
        return None
    return tuple(
        identity[key] for key in ('partition', 'account', 'kind', 'name')
    )


def _same_login_source(credential, region):
    """Whether ``credential`` is an aws login session in ``region``, as
    credsd's ``same_provider_source``. A seeded one has no region, and
    counts as any."""
    if credential.kind != KIND_LOGIN:
        return False
    stored = (credential.provider or {}).get('region')
    return stored is None or region is None or stored == region


def _identity_digest(params_digest, recorded, current):
    """What an identity-change approval is bound to, as credsd's
    ``identity_bound_digest``: the params, the principal on record (or
    none) and the one that signed in."""
    text = json.dumps(
        ['aws-login-identity', params_digest, recorded, current],
        separators=(',', ':'),
    )
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _who(principal):
    identity = identity_record(principal)
    return (
        f'{identity["kind"]} {identity["name"]} in account '
        f'{identity["account"]} ({identity["partition"]})'
    )


def _describe_identity_change(name, region, recorded, principal):
    """credsd's ``describe_identity_change`` challenge text."""
    was = (
        _who(recorded)
        if principal_of(recorded) is not None
        else 'no recorded sign-in'
    )
    return (
        f"replace existing credential '{name}' with a new aws-login (region "
        f'{region}) signed in as {_who(principal)}; it was {was}'
    )


def _identity_mismatch(name, recorded, principal):
    """credsd's ``login_identity_check`` error, for a ``credential/login``
    that signed in as another principal."""
    if principal_of(recorded) is None:
        was = 'it has no recorded sign-in'
    else:
        identity = identity_record(recorded)
        was = (
            f'it is recorded for {identity["kind"]} {identity["name"]} in '
            f'account {identity["account"]}'
        )
    now = identity_record(principal)
    return DomainError(
        'IDENTITY_MISMATCH',
        f"credential '{name}' signed in as {now['kind']} {now['name']} in "
        f"account {now['account']}, but {was}; nothing was saved. Signing "
        'in as another account or role replaces the credential, which '
        "needs approval: re-run 'creds bootstrap --credential "
        f"{name}' with its aws-login provider",
    )


def _role_name(role):
    name = re.sub(
        r'[^A-Za-z0-9._-]',
        '-',
        f'{role["role_name"]}-' f'{role["account_id"]}',
    )
    return name.lstrip('.')[:64]


def _account_from_arn(arn):
    parts = arn.split(':') if isinstance(arn, str) else []
    if len(parts) > 4 and parts[4]:
        return parts[4]
    return DEFAULT_ACCOUNT_ID


def _session_credentials(account_id):
    return {
        'type': 'session_credentials',
        'access_key_id': 'ASIA' + secrets.token_hex(8).upper(),
        'secret_access_key': secrets.token_urlsafe(30),
        'session_token': 'FakeSessionToken/' + secrets.token_urlsafe(48),
        'account_id': account_id,
    }


def _fake_secrets(kind):
    if kind == KIND_IAM_USER:
        return {
            'access_key_id': 'AKIA' + secrets.token_hex(8).upper(),
            'secret_access_key': secrets.token_urlsafe(30),
        }
    return {'refresh_token': 'FakeRefreshToken/' + secrets.token_urlsafe(32)}


def _redact(value):
    if isinstance(value, dict):
        return {
            key: '<redacted>' if key in _SECRET_FIELDS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def approval_data(description, request_id=None):
    """The ``data`` of an ``APPROVAL_REQUIRED`` error, as the credential
    daemon sends it: a ``challenge`` object (``Challenge`` in credsd-core
    presence.rs) and a ``remediation`` string, its own instructions for
    approving.
    """
    request_id = request_id or f'req-{_nonce()}'
    return {
        'challenge': {
            'id': request_id,
            'digest': '0' * 64,
            'description': description,
            'expires_in_secs': 900,
            'accepts': 'any',
            'presence_key': None,
        },
        'remediation': f'sudo creds request approve {request_id}',
    }


def _params_digest(params):
    """A digest of a request's params, as credsd binds an approval to the
    exact request. ``creator`` isn't one of credsd's bootstrap params."""
    signed = {key: value for key, value in params.items() if key != 'creator'}
    text = json.dumps(signed, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _nonce():
    return secrets.token_urlsafe(8)


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(value):
    return value.astimezone(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
