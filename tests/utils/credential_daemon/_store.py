# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential store: rows, tags, lookups and the credential/* reads and
writes.

A mixin of ``FakeCredentialDaemon`` (server.py), which holds the state
it reads and the rest of the fake.
"""

import datetime

from tests.utils.credential_daemon._protocol import (
    _SESSION_END,
    ACTIVE,
    ALREADY_EXISTS,
    DEFAULT_PRINCIPAL,
    DEFAULT_START_URL,
    IMPORT_IMPORTED,
    IMPORT_SKIPPED,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    LOGOUT_LOCAL_ONLY,
    LOGOUT_NONE,
    MATERIAL_KIND,
    NO_SESSION,
    SIGN_IN_SOURCES,
    SSO_LOGOUT_FAILED,
    STATUSES,
    USABLE_STATUSES,
    Credential,
    DomainError,
    InvalidParams,
    _account_from_arn,
    _check_tag_key,
    _checked_tags,
    _fake_secrets,
    _fold_tag_keys,
    _iso,
    _reauth_detail,
    _reauth_required,
    _require_name,
    _require_str,
    _session_credentials,
    _tag_filter,
    _tags_match,
    _validate_name,
)


class StoreMixin:
    def credential(self, name):
        with self._lock:
            return self._credentials.get(name)

    def seed(
        self,
        name,
        kind=KIND_LOGIN,
        principal=DEFAULT_PRINCIPAL,
        status=ACTIVE,
        account_id=None,
        mfa_serial=None,
        tags=None,
    ):
        """Add a credential as if someone had already created it.

        ``tags`` are its tags: none unless given, as for a credential
        another tool made.
        """
        _validate_name(name)
        # Any source, as well as the three the CLI creates: tests seed ones
        # such as unsupported (see the module docstring).
        if not isinstance(kind, str) or not kind:
            raise InvalidParams(f'Unknown kind: {kind}')
        if status not in STATUSES:
            raise InvalidParams(f'Unknown status: {status}')
        credential = Credential(
            name=name,
            kind=kind,
            principal=principal,
            account_id=account_id or _account_from_arn(principal),
            status=status,
            session_expires_at=self._session_expiry(kind),
            mfa_serial=mfa_serial,
            tags=_checked_tags(tags or {}, name),
        )
        if status in USABLE_STATUSES:
            credential.secrets = _fake_secrets(kind)
        with self._lock:
            self._credentials[name] = credential
        return credential

    def list_rows(self):
        """Return the credential/list rows, as the fake sends them."""
        return self._list({})['credentials']

    def _list(self, params):
        wanted = _tag_filter(params.get('tags'))
        now = self._now()
        with self._lock:
            rows = [
                credential.describe(now)
                for _, credential in sorted(self._credentials.items())
                if _tags_match(credential.tags, wanted)
            ]
        return {'credentials': rows}

    def _tag(self, params):
        """credsd's credential/tag: ``set``, then ``unset``, in one
        write, with no approval."""
        name = _require_name(params, 'credential')
        to_set = _fold_tag_keys(params.get('set', {}), name)
        unset = params.get('unset', [])
        if not isinstance(unset, list) or not all(
            isinstance(key, str) for key in unset
        ):
            raise InvalidParams('unset must be an array of strings')
        to_unset = list(_fold_tag_keys(dict.fromkeys(unset, ''), name))
        for key in to_unset:
            _check_tag_key(key, name)
        both = [key for key in to_unset if key in to_set]
        if both:
            raise InvalidParams(
                f"credential '{name}': tag {both[0]!r} is both set and unset"
            )
        _checked_tags(to_set, name)
        with self._lock:
            credential = self._lookup(name)
            tags = dict(credential.tags, **to_set)
            for key in to_unset:
                tags.pop(key, None)
            credential.tags = _checked_tags(tags, name)
        return {}

    def _get(self, params):
        name = _require_name(params, 'credential')
        material = params.get('material', 'session_credentials')
        # The credential daemon never hands out the SSO access token.
        if material != 'session_credentials':
            raise InvalidParams(f'Unknown material: {material}')
        now = self._now()
        with self._lock:
            credential = self._lookup(name)
            self._ensure_signed_in(credential, now)
            account_id = credential.account_id
            if credential.kind == KIND_SSO:
                account_id = _require_str(params, 'account_id')
                _require_str(params, 'role_name')
                expires_at = now + datetime.timedelta(hours=1)
            elif credential.kind == KIND_IAM_USER:
                expires_at = self._iam_user_expiry(credential, now)
            else:
                expires_at = now + datetime.timedelta(
                    seconds=self._credential_lifetime
                )
            if credential.session_expires_at is not None:
                expires_at = min(expires_at, credential.session_expires_at)
        result = {
            'credential': name,
            'kind': MATERIAL_KIND,
            'material': _session_credentials(account_id),
            'expires_at': _iso(expires_at),
            'provenance': 'cached_shared',
        }
        if self._backing is not None:
            frozen, expiry = self._backing.credentials()
            result['material'].update(
                access_key_id=frozen.access_key,
                secret_access_key=frozen.secret_key,
                session_token=frozen.token,
            )
            if expiry is not None:
                result['expires_at'] = _iso(min(expiry, expires_at))
        return result

    def _iam_user_expiry(self, credential, now):
        if credential.mfa_serial is None:
            return now + datetime.timedelta(seconds=self._iam_user_lifetime)
        # The credential daemon never falls back to credentials without MFA.
        if (
            credential.mfa_expires_at is None
            or now >= credential.mfa_expires_at
        ):
            raise DomainError(
                'REAUTH_REQUIRED',
                f'{credential.name} needs an MFA code',
                remediation=f'Log in to {credential.name} with an MFA code',
            )
        return credential.mfa_expires_at

    def _import(self, params):
        name = _require_name(params, 'credential')
        keys = {
            'access_key_id': _require_str(params, 'access_key_id'),
            'secret_access_key': _require_str(params, 'secret_access_key'),
        }
        # credsd's words for a request without a region. Any string is a
        # region to credsd.
        if 'region' not in params:
            raise InvalidParams('missing field `region`')
        if not isinstance(params['region'], str):
            raise InvalidParams('region must be a string')
        if params.get('session_token') is not None:
            keys['session_token'] = _require_str(params, 'session_token')
        # credsd's ImportProfile has no mfa_serial or duration_seconds and
        # drops them with no error, so imported keys never have a device.
        with self._lock:
            if name in self._credentials:
                # As in credsd, import only adds: a name that exists is
                # skipped, whoever created it, and nothing is stored.
                return {
                    'credential': name,
                    'status': IMPORT_SKIPPED,
                    'reason': ALREADY_EXISTS,
                }
            principal = self.iam_user_principal
            self._credentials[name] = Credential(
                name=name,
                kind=KIND_IAM_USER,
                principal=principal,
                account_id=_account_from_arn(principal),
                secrets=keys,
            )
        return {
            'credential': name,
            'status': IMPORT_IMPORTED,
            'principal': principal,
        }

    def _logout(self, params):
        name = _require_name(params, 'credential')
        with self._lock:
            credential = self._lookup(name)
            if credential.kind not in SIGN_IN_SOURCES:
                # credsd's code; the message is shorter than credsd's.
                raise DomainError(
                    'LOGOUT_UNSUPPORTED_SOURCE',
                    "The credential's source has no sign-in to log out of; "
                    'remove it with credential/remove.',
                )
            if credential.current_status(self._now()) == NO_SESSION:
                # Nothing to delete, and nothing is sent to SSO.
                return {'signed_out': False, 'provider': LOGOUT_NONE}
            result = {'signed_out': True, 'provider': LOGOUT_LOCAL_ONLY}
            if credential.kind == KIND_SSO:
                result.update(self._sso_logout_result(credential))
            credential.secrets.clear()
            credential.status = NO_SESSION
        return result

    def _sso_logout_result(self, credential):
        provider, expires_at = self._sso_logout
        result = {'provider': provider}
        if provider != SSO_LOGOUT_FAILED:
            return result
        result['start_url'] = credential.provider.get(
            'start_url', DEFAULT_START_URL
        )
        if expires_at is _SESSION_END:
            expires_at = credential.session_expires_at
        if expires_at is not None:
            if isinstance(expires_at, datetime.datetime):
                expires_at = _iso(expires_at)
            result['access_token_expires_at'] = expires_at
        return result

    def _remove(self, params):
        name = _require_name(params, 'credential')
        with self._lock:
            self._lookup(name)
            del self._credentials[name]
        return {}

    def _store_session(
        self, name, kind, principal, account_id, provider, params
    ):
        credential = Credential(
            name=name,
            kind=kind,
            principal=principal,
            account_id=account_id,
            session_expires_at=self._session_expiry(kind),
            provider=provider,
            secrets=_fake_secrets(kind),
            tags=self._tags_after_bootstrap(name, params),
        )
        self._credentials[name] = credential
        return credential

    def _tags_after_bootstrap(self, name, params):
        """The tags ``name`` gets from a bootstrap with ``params``: its
        ``tags`` if given, or else the ones a credential it replaces had.
        Call it under the lock."""
        if 'tags' in params:
            return dict(params['tags'])
        existing = self._credentials.get(name)
        return dict(existing.tags) if existing is not None else {}

    def _session_expiry(self, kind):
        if kind not in (KIND_LOGIN, KIND_SSO):
            return None
        return self._now() + datetime.timedelta(seconds=self._session_lifetime)

    def _lookup(self, name):
        credential = self._credentials.get(name)
        if credential is None:
            raise DomainError(
                'CREDENTIAL_NOT_FOUND', f'No credential named {name}'
            )
        return credential

    def _ensure_signed_in(self, credential, now):
        if credential.current_status(now) not in USABLE_STATUSES:
            raise _reauth_required(credential.name, _reauth_detail(credential))
