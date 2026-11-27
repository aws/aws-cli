# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Records and statuses the credential daemon returns."""

import collections
import enum
from dataclasses import dataclass

from botocore.exceptions import (
    CredentialDaemonError,
    CredentialDaemonProtocolError,
)


class Status(str, enum.Enum):
    """The credential daemon's credential/list statuses (SessionStatus).

    An active or expiring credential is signed in, and one with no session
    is signed out. The others hold a session that can't be used now. For
    comparisons only: text and config use the wire value.
    """

    ACTIVE = 'active'
    EXPIRING = 'expiring'
    EXPIRED = 'expired'
    SIGN_IN_REQUIRED = 'sign_in_required'
    NO_SESSION = 'no_session'


class Source(str, enum.Enum):
    """The credential daemon's source types, as credential/list rows say
    them. For comparisons only: text uses the wire value."""

    AWS_LOGIN = 'aws_login'
    IAM_USER = 'aws_iam_user'
    SSO = 'aws_idc_sso'


# The wire values as plain strings, for the fake and tests that build
# credential/list rows.
ACTIVE = Status.ACTIVE.value
EXPIRING = Status.EXPIRING.value
EXPIRED = Status.EXPIRED.value
SIGN_IN_REQUIRED = Status.SIGN_IN_REQUIRED.value
NO_SESSION = Status.NO_SESSION.value
AWS_LOGIN_SOURCE = Source.AWS_LOGIN.value
IAM_USER_SOURCE = Source.IAM_USER.value
SSO_SOURCE = Source.SSO.value


def credential_status(row):
    """Return a credential/list row's status, or None.

    ``creds list`` shows the statuses with spaces for underscores, so
    those are read too.
    """
    status = row.get('status')
    if not isinstance(status, str):
        return None
    return status.replace(' ', '_')


def credential_source(row):
    """Return a credential/list row's source type, such as
    ``aws_idc_sso``, or None."""
    source = row.get('source') if isinstance(row, dict) else None
    return source if isinstance(source, str) else None


@dataclass(frozen=True)
class CredentialRow:
    """One credential/list row, as the credential daemon sent it.

    ``name`` is the row's ``credential`` value, unchecked: callers check
    its type where they use it. ``source`` and ``status`` are strings or
    None (``credential_source``, ``credential_status``), and ``tags`` is
    the row's ``tags``. ``raw`` is the row itself. A row that isn't an
    object has only ``raw``.
    """

    name: object
    source: object
    status: object
    tags: object
    raw: object

    @classmethod
    def from_wire(cls, item):
        if not isinstance(item, dict):
            return cls(None, None, None, None, item)
        return cls(
            item.get('credential'),
            credential_source(item),
            credential_status(item),
            item.get('tags'),
            item,
        )

    @property
    def signed_in(self):
        """Whether the credential is signed in."""
        return self.status in (Status.ACTIVE, Status.EXPIRING)

    @property
    def signed_out(self):
        """Whether the credential has no session."""
        return self.status == Status.NO_SESSION


def find_credential_row(rows, name):
    """The ``CredentialRow`` of the credential named ``name``, or None."""
    return next(
        (
            row
            for row in rows
            if isinstance(row.raw, dict) and row.name == name
        ),
        None,
    )


def credential_names(rows, signed_out=True):
    """The names of the listed credentials, as a set. Without
    ``signed_out``, credentials with no session are left out."""
    return {
        row.name
        for row in rows
        if isinstance(row.raw, dict) and (signed_out or not row.signed_out)
    }


class SocketChecks(enum.Enum):
    """How much a connection checks before anything is sent on it.

    ``FULL``, for every call that sends a secret or starts a sign-in, runs
    every check, including the code signature check on macOS at every
    socket. ``PEER``, for the credential provider's credential/get, which
    sends only a credential's name, runs the socket's folder and owner
    checks and the peer uid check, but not the code signature check.
    Neither level turns the checks off.
    """

    FULL = 'full'
    PEER = 'peer'


# What credential/logout says happened at the identity provider, in its
# result's ``provider``.
PROVIDER_ENDED = 'ended'
PROVIDER_TOKEN_REJECTED = 'token_rejected'
PROVIDER_LOCAL_ONLY = 'local_only'
PROVIDER_FAILED = 'failed'
PROVIDER_NONE = 'none'
# The code credential/logout refuses a credential with, when its source has
# no sign-in to log out of, such as access keys.
LOGOUT_UNSUPPORTED_SOURCE = 'LOGOUT_UNSUPPORTED_SOURCE'


class LogoutResult(
    collections.namedtuple(
        'LogoutResult',
        ['signed_out', 'provider', 'start_url', 'access_token_expires_at'],
        defaults=(None, None, None),
    )
):
    """What ``credential/logout`` did.

    ``signed_out`` is whether there was a session to delete. The credential
    daemon always sends it as true or false; a reply without it, or with
    anything else, raises ``CredentialDaemonProtocolError``. ``provider``
    is what happened at the identity provider, one of the ``PROVIDER_*``
    values, or None when the reply doesn't say. For
    ``PROVIDER_FAILED``, the SSO session may still be live:
    ``start_url`` is where to sign out of it, and
    ``access_token_expires_at``, when present, is when the access token
    stops working. Both are as the credential daemon sent them, so strip
    control characters before printing them.
    """

    @classmethod
    def from_reply(cls, reply):
        signed_out = (
            reply.get('signed_out') if isinstance(reply, dict) else None
        )
        if not isinstance(signed_out, bool):
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The credential daemon sent a sign-out reply the CLI '
                    'can\'t read.'
                )
            )
        provider = _str_or_none(reply.get('provider'))
        start_url = None
        expires_at = None
        if provider == PROVIDER_FAILED:
            start_url = _str_or_none(reply.get('start_url'))
            expires_at = _str_or_none(reply.get('access_token_expires_at'))
        return cls(
            signed_out=signed_out,
            provider=provider,
            start_url=start_url,
            access_token_expires_at=expires_at,
        )

    @property
    def provider_failed(self):
        """Whether SSO didn't end the session, which may still be live."""
        return self.provider == PROVIDER_FAILED


def _str_or_none(value):
    if isinstance(value, str) and value:
        return value
    return None


def is_logout_unsupported(error):
    """Whether credential/logout refused a credential because its source
    has no sign-in, such as access keys."""
    return (
        isinstance(error, CredentialDaemonError)
        and error.code == LOGOUT_UNSUPPORTED_SOURCE
    )
