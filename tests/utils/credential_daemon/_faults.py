# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Fault injection: failures, approvals on demand, and what the fake reports,
for tests.

A mixin of ``FakeCredentialDaemon`` (server.py), which holds the state
it reads and the rest of the fake.
"""

import datetime

from tests.utils.credential_daemon._protocol import (
    _SESSION_END,
    CONFIG_CHECKED_METHODS,
    SSO_LOGOUT_OUTCOMES,
    DomainError,
    approval_data,
)


class FaultsMixin:
    def expire(self, name):
        """End a session, or a static-key credential's MFA session."""
        with self._lock:
            credential = self._lookup(name)
            past = self._now() - datetime.timedelta(seconds=1)
            if credential.mfa_expires_at is not None:
                credential.mfa_expires_at = past
            else:
                credential.session_expires_at = past

    def fail_next(self, method, code, message=None, count=1, **data):
        """Make the next ``count`` calls to ``method`` fail with ``code``."""
        error = DomainError(code, message or f'Injected {code}', **data)
        with self._lock:
            self._failures.setdefault(method, []).extend([error] * count)

    def set_config_invalid(self, errors):
        """Make the caller's configuration not validate, as when its
        config.toml or credentials.toml parses but has, say, a bad tag key:
        ``CONFIG_CHECKED_METHODS`` refuse with ``CONFIG_INVALID`` until it's
        set to None again, as in credsd."""
        with self._lock:
            self._config_errors = errors

    def set_sso_logout(self, provider, access_token_expires_at=_SESSION_END):
        """Say what SSO does when an SSO credential is logged out:
        ``ended`` (the default), ``token_rejected`` or ``failed``. A
        ``failed`` result names the credential's start URL and
        ``access_token_expires_at``: the session's end unless given, or
        none when it's None, as when the credential daemon can't read the
        token."""
        if provider not in SSO_LOGOUT_OUTCOMES:
            raise ValueError(f'Unknown SSO logout result: {provider}')
        with self._lock:
            self._sso_logout = (provider, access_token_expires_at)

    def need_approval_next(self, method, description, request_id=None):
        """Make the next call to ``method`` wait for approval, as the
        credential daemon answers a gated call such as ``credential/remove``.

        The error's data is shaped as the credential daemon sends it (see
        ``approval_data``). Nothing is changed. Returns the request id.
        """
        data = approval_data(description, request_id)
        self.fail_next(
            method,
            'APPROVAL_REQUIRED',
            message=f'approval required: {description}',
            **data,
        )
        return data['challenge']['id']

    def _refuse_if_config_invalid(self, method):
        with self._lock:
            errors = self._config_errors
        if errors is not None and method in CONFIG_CHECKED_METHODS:
            raise DomainError(
                'CONFIG_INVALID',
                f'caller configuration does not validate: {errors}; fix it, '
                'then run: creds revalidate',
            )

    def _raise_injected(self, method):
        with self._lock:
            failures = self._failures.get(method)
            error = failures.pop(0) if failures else None
        if error is not None:
            raise error
