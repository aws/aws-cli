# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Sign-in flows: credential/bootstrap and credential/login for each provider
kind, and the approvals that gate them.

A mixin of ``FakeCredentialDaemon`` (server.py), which holds the state
it reads and the rest of the fake.
"""

import datetime
import re
import threading
import urllib.parse

from tests.utils.credential_daemon._protocol import (
    _NAME_PREFIX_RE,
    _PROVIDER_PARAMS,
    ACTIVE,
    CROSS_DEVICE,
    DEFAULT_MFA_DURATION,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    LOGIN_METHOD,
    NO_SESSION,
    PROVIDER_KINDS,
    SIGN_IN_REQUIRED,
    WRONG_MFA_CODE_MESSAGE,
    Credential,
    DomainError,
    InvalidParams,
    _account_from_arn,
    _aws_login_callback_port,
    _callback_port,
    _check_params,
    _checked_tags,
    _describe_identity_change,
    _fake_secrets,
    _identity_digest,
    _identity_mismatch,
    _is_base64,
    _iso,
    _nonce,
    _params_digest,
    _redirect_listener,
    _require_name,
    _require_str,
    _same_login_source,
    approval_data,
    identity_credential_name,
    identity_record,
    principal_of,
)


class SignInMixin:
    # Sign-in flows. They run on their own thread, so they take the lock
    # only around state changes, never while waiting on the customer.

    def waiting_signins(self):
        """Names of sign-ins waiting on the browser ('' for multi-role)."""
        with self._lock:
            return sorted('' if key is None else key for key in self._signins)

    def complete_signin(self, name=None):
        """Finish waiting browser sign-ins: one name, or all of them."""
        with self._lock:
            keys = list(self._signins) if name is None else [name]
            events = [e for key in keys for e in self._signins.get(key, [])]
        for event in events:
            event.set()
        return len(events)

    def approve(self, request_id=None):
        """Approve a waiting approval request, as a person does with the
        credential daemon's own tool: one id, or the latest one. Returns
        the id."""
        with self._lock:
            if request_id is None:
                if not self._approvals:
                    raise InvalidParams('No approval requests')
                request_id = list(self._approvals)[-1]
            if request_id not in self._approvals:
                raise InvalidParams(f'No approval request {request_id}')
            self._approvals[request_id][1] = True
        return request_id

    def approval_requests(self):
        """Ids of approval requests not yet approved."""
        with self._lock:
            return [
                request_id
                for request_id, (_, approved) in self._approvals.items()
                if not approved
            ]

    def bootstrap(self, params, interaction):
        self.record('credential/bootstrap', params)
        self._raise_injected('credential/bootstrap')
        _check_params('credential/bootstrap', params)
        if params.get('tags') is not None:
            # Checked and folded before anything else, as credsd does.
            params = dict(
                params,
                tags=_checked_tags(params['tags'], params.get('credential')),
            )
        else:
            # null is the same as leaving tags out.
            params = {k: v for k, v in params.items() if k != 'tags'}
        provider = params.get('provider')
        if not isinstance(provider, dict):
            raise InvalidParams('provider must be an object')
        kind = PROVIDER_KINDS.get(provider.get('type'))
        if kind is None:
            raise InvalidParams(
                f'Unknown provider type: {provider.get("type")}'
            )
        unknown = set(provider) - set(_PROVIDER_PARAMS[kind])
        if unknown:
            raise InvalidParams(f'Unknown provider fields: {sorted(unknown)}')
        return self._bootstrap_kinds()[kind](params, provider, interaction)

    def _bootstrap_kinds(self):
        """The sign-in for each provider kind."""
        return {
            KIND_IAM_USER: self._bootstrap_iam_user_kind,
            KIND_SSO: self._bootstrap_sso_kind,
            KIND_LOGIN: self._bootstrap_login_kind,
        }

    def _bootstrap_iam_user_kind(self, params, provider, interaction):
        if 'name_prefix' in params:
            raise InvalidParams(
                'name_prefix is only accepted for an aws_login provider'
            )
        return self._bootstrap_iam_user(params, provider)

    def _bootstrap_sso_kind(self, params, provider, interaction):
        if 'name_prefix' in params:
            raise InvalidParams('Only an aws-login sign-in takes name_prefix')
        return self._bootstrap_sso(params, provider, interaction)

    def _bootstrap_login_kind(self, params, provider, interaction):
        if provider.get('multi_role'):
            if 'name_prefix' in params:
                raise InvalidParams(
                    'Only an aws-login sign-in takes name_prefix'
                )
            return self._bootstrap_roles(params, provider, interaction)
        if 'name_prefix' in params:
            return self._bootstrap_login_by_identity(
                params, provider, interaction
            )
        return self._bootstrap_login(params, provider, interaction)

    def _bootstrap_iam_user(self, params, provider):
        """Store static keys, or replace a credential's with approval."""
        name = _require_name(params, 'credential')
        keys = {
            'access_key_id': _require_str(provider, 'access_key_id'),
            'secret_access_key': _require_str(provider, 'secret_access_key'),
        }
        # credsd's words for a provider without a region.
        if 'region' not in provider:
            raise InvalidParams('missing field `region`')
        if not isinstance(provider['region'], str):
            raise InvalidParams('region must be a string')
        mfa_serial = None
        if provider.get('mfa_serial') is not None:
            mfa_serial = _require_str(provider, 'mfa_serial')
        duration = provider.get('duration_seconds', DEFAULT_MFA_DURATION)
        if not isinstance(duration, int) or not 900 <= duration <= 129600:
            raise InvalidParams('duration_seconds must be 900 to 129600')
        with self._lock:
            if name in self._credentials:
                self._spend_approval(name, _params_digest(params))
            principal = self.iam_user_principal
            self._credentials[name] = Credential(
                name=name,
                kind=KIND_IAM_USER,
                principal=principal,
                account_id=_account_from_arn(principal),
                secrets=keys,
                mfa_serial=mfa_serial,
                mfa_duration=duration,
                tags=self._tags_after_bootstrap(name, params),
            )
        return {}

    def _use_approval(self, digest):
        """Use an approved request for exactly ``digest``, once. Returns
        whether there was one."""
        for request_id, (approved_digest, approved) in list(
            self._approvals.items()
        ):
            if approved and approved_digest == digest:
                del self._approvals[request_id]
                return True
        return False

    def _spend_approval(self, name, digest):
        """Use an approval of exactly these params, or ask for one, as
        credsd's gate does for a bootstrap that replaces a credential."""
        if self._use_approval(digest):
            return
        data = approval_data(f'replace credential {name!r}')
        data['challenge']['digest'] = digest
        self._approvals[data['challenge']['id']] = [digest, False]
        raise DomainError(
            'APPROVAL_REQUIRED',
            f'Replacing {name} needs approval',
            **data,
        )

    def login(self, params, interaction):
        """Start an MFA session for static keys stored with a device, or
        another credential's own sign-in."""
        self.record(LOGIN_METHOD, params)
        self._raise_injected(LOGIN_METHOD)
        _check_params(LOGIN_METHOD, params)
        name = _require_name(params, 'credential')
        with self._lock:
            credential = self._lookup(name)
            kind = credential.kind
            if kind == KIND_IAM_USER and credential.status == NO_SESSION:
                # As for keys credential/remove deleted.
                raise DomainError(
                    'CREDENTIAL_NOT_FOUND', f'No credential named {name}'
                )
            serial = credential.mfa_serial
        if kind != KIND_IAM_USER:
            return self._login_session(credential, interaction)
        if serial is None:
            return {}
        interaction.notify('mfa_required', serial=serial)
        code = interaction.answer().get('selection')
        if (
            not isinstance(code, str)
            or not re.fullmatch(r'\d{6}', code)
            or code == '000000'
        ):
            raise DomainError('INTERNAL', WRONG_MFA_CODE_MESSAGE)
        with self._lock:
            credential.mfa_expires_at = self._now() + datetime.timedelta(
                seconds=credential.mfa_duration
            )
        return {}

    def _login_session(self, credential, interaction):
        """Sign an aws login or SSO credential in again, as the credential
        daemon's login does for them."""
        name = credential.name
        if credential.kind == KIND_SSO and self._renews_unattended(credential):
            # credsd's login_sso: the refresh token it holds renews the
            # session, with no progress and no device code.
            with self._lock:
                credential.secrets = _fake_secrets(credential.kind)
                credential.status = ACTIVE
                credential.session_expires_at = self._session_expiry(
                    credential.kind
                )
            return {}
        if credential.kind == KIND_SSO:
            region = credential.provider.get('sso_region') or 'us-east-1'
            uri = f'https://device.sso.{region}.amazonaws.com/'
            self._browser_step(
                name,
                interaction,
                'device_code',
                user_code='MOCK-CODE',
                verification_uri=uri,
                verification_uri_complete=f'{uri}?user_code=MOCK-CODE',
                expires_in=600,
            )
        else:
            region = credential.provider.get('region') or 'us-east-1'
            self._sign_in(name, region, {}, interaction)
            principal, _ = self._identity()
            with self._lock:
                recorded = credential.principal
                if principal_of(recorded) is None or (
                    principal_of(recorded) != principal_of(principal)
                ):
                    raise _identity_mismatch(name, recorded, principal)
                # The same principal, with the new session.
                credential.principal = principal
        with self._lock:
            credential.secrets = _fake_secrets(credential.kind)
            credential.status = ACTIVE
            credential.session_expires_at = self._session_expiry(
                credential.kind
            )
        return {}

    def _renews_unattended(self, credential):
        """Whether an SSO credential still holds a refresh token that
        works: it has a session, maybe expired, that isn't signed out or
        marked for a new sign-in."""
        with self._lock:
            return bool(credential.secrets) and credential.status not in (
                NO_SESSION,
                SIGN_IN_REQUIRED,
            )

    def _bootstrap_login(self, params, provider, interaction):
        name = _require_name(params, 'credential')
        region = provider.get('region') or 'us-east-1'
        with self._lock:
            # Before the sign-in, as credsd's admit: anything of that name
            # but an aws login session in this region needs approval.
            approved = self._check_replace(name, KIND_LOGIN, params, region)
        self._sign_in(name, region, provider, interaction)
        principal, account_id = self._identity()
        with self._lock:
            # The state can change while the customer is in the browser.
            self._commit_login(name, region, principal, params, approved)
            self._store_session(
                name,
                KIND_LOGIN,
                principal,
                account_id,
                {'region': region},
                params,
            )
        return {'credential': name, 'identity': identity_record(principal)}

    def _bootstrap_login_by_identity(self, params, provider, interaction):
        if 'credential' in params:
            raise InvalidParams('Give credential or name_prefix, not both')
        prefix = params.get('name_prefix')
        if not isinstance(prefix, str) or not _NAME_PREFIX_RE.match(prefix):
            raise InvalidParams(
                f'Invalid name_prefix {prefix!r}: use up to 32 of '
                f'A-Z a-z 0-9 . _ - and don\'t start with "."'
            )
        region = provider.get('region') or 'us-east-1'
        # The name isn't known until the sign-in, so mock/complete_signin
        # takes the prefix.
        self._sign_in(prefix, region, provider, interaction)
        principal, account_id = self._identity()
        name = identity_credential_name(prefix, principal)
        with self._lock:
            approved = self._check_replace(name, KIND_LOGIN, params, region)
            self._commit_login(name, region, principal, params, approved)
            self._store_session(
                name,
                KIND_LOGIN,
                principal,
                account_id,
                {'region': region},
                params,
            )
        return {'credential': name, 'identity': identity_record(principal)}

    def _commit_login(self, name, region, principal, params, approved):
        """Decide, after the sign-in, whether it may replace what ``name``
        holds now, as credsd's commit_bootstrap does. Call it under the
        lock. Raises ``APPROVAL_REQUIRED`` and saves nothing when it can't.
        """
        existing = self._credentials.get(name)
        if existing is None:
            return
        if not _same_login_source(existing, region):
            # Something else took the name during the sign-in.
            self._check_replace(name, KIND_LOGIN, params, region, approved)
            return
        recorded = principal_of(existing.principal)
        current = principal_of(principal)
        if recorded is not None and recorded == current:
            return
        digest = _identity_digest(_params_digest(params), recorded, current)
        if self._use_approval(digest):
            return
        data = approval_data(
            _describe_identity_change(
                name, region, existing.principal, principal
            )
        )
        data['challenge']['digest'] = digest
        request_id = data['challenge']['id']
        data['remediation'] = (
            'this sign-in is for a different account or role than the '
            'credential records, so nothing was saved. sudo creds request '
            f'approve {request_id}, then re-run the same bootstrap and sign '
            'in as the same account and role again'
        )
        self._approvals[request_id] = [digest, False]
        raise DomainError(
            'APPROVAL_REQUIRED',
            f'Replacing {name} needs approval',
            **data,
        )

    def _bootstrap_sso(self, params, provider, interaction):
        name = _require_name(params, 'credential')
        start_url = _require_str(provider, 'start_url')
        sso_region = _require_str(provider, 'sso_region')
        with self._lock:
            approved = self._check_replace(name, KIND_SSO, params)
        if provider.get('use_device_code'):
            uri = f'https://device.sso.{sso_region}.amazonaws.com/'
            self._browser_step(
                name,
                interaction,
                'device_code',
                user_code='MOCK-CODE',
                verification_uri=uri,
                verification_uri_complete=f'{uri}?user_code=MOCK-CODE',
                expires_in=600,
            )
        else:
            port = _callback_port(provider)
            with _redirect_listener(port) as port:
                redirect_uri = urllib.parse.quote(
                    f'http://127.0.0.1:{port}/oauth/callback', safe=''
                )
                self._browser_step(
                    name,
                    interaction,
                    'authorize_url',
                    url=(
                        f'https://oidc.{sso_region}.amazonaws.com/authorize?'
                        f'response_type=code&client_id=mock'
                        f'&redirect_uri={redirect_uri}&state={_nonce()}'
                    ),
                )
        if provider.get('select_account_and_role'):
            self._select_account_and_role(interaction)
        with self._lock:
            self._check_replace(name, KIND_SSO, params, approved=approved)
            credential = self._store_session(
                name,
                KIND_SSO,
                None,
                None,
                {
                    'start_url': start_url,
                    'sso_region': sso_region,
                    'scopes': provider.get('scopes') or ['sso:account:access'],
                },
                params,
            )
        return {
            'name': name,
            'expires_at': _iso(credential.session_expires_at),
        }

    def _sign_in(self, name, region, provider, interaction):
        query = f'response_type=code&client_id=mock&state={_nonce()}'
        url = f'https://{region}.signin.aws.amazon.com/v1/authorize?{query}'
        if provider.get('remote'):
            if provider.get('callback_port') is not None:
                raise DomainError(
                    'PROVIDER_UNAVAILABLE',
                    'aws-login cannot set both callback_port and remote: a '
                    'remote login binds no loopback listener',
                )
            redirect_uri = urllib.parse.quote(
                f'https://{region}.signin.aws.amazon.com/v1/sessions/'
                f'confirmation',
                safe='',
            )
            url = url.replace('client_id=mock', f'client_id={CROSS_DEVICE}')
            interaction.notify(
                'authorize_code', url=f'{url}&redirect_uri={redirect_uri}'
            )
            self._read_authorization_code(interaction)
            return
        with _redirect_listener(_aws_login_callback_port(provider)) as port:
            redirect_uri = urllib.parse.quote(
                f'http://127.0.0.1:{port}/oauth/callback', safe=''
            )
            self._browser_step(
                name,
                interaction,
                'authorize_url',
                url=f'{url}&redirect_uri={redirect_uri}',
            )

    def _read_authorization_code(self, interaction):
        # One code, as the credential daemon takes. Like the credential
        # daemon, the fake strips all whitespace and decodes it first. Codes
        # that start with "invalid" and decode fail the state check, to test
        # that error.
        code = interaction.answer().get('selection')
        code = re.sub(r'\s', '', code) if isinstance(code, str) else None
        if code is None or not _is_base64(code):
            raise DomainError(
                'PROVIDER_UNAVAILABLE',
                'that is not the value Sign-In displayed; copy the whole '
                'code from the browser',
            )
        if not code or code.startswith('invalid'):
            raise DomainError(
                'PROVIDER_UNAVAILABLE',
                'the pasted Sign-In code belongs to a different login; '
                'start over',
            )

    def _browser_step(self, name, interaction, notification_type, **fields):
        """Send the browser step, then wait until the customer finishes it."""
        if self._signin == 'auto':
            interaction.notify(notification_type, **fields)
            interaction.sleep(self._signin_delay)
            return
        event = threading.Event()
        with self._lock:
            self._signins.setdefault(name, []).append(event)
        try:
            # Registered before the step goes out, so complete_signin
            # works as soon as the client sees it.
            interaction.notify(notification_type, **fields)
            interaction.wait_for(event)
        finally:
            with self._lock:
                waiting = self._signins.get(name, [])
                if event in waiting:
                    waiting.remove(event)
                if not waiting:
                    self._signins.pop(name, None)

    def _identity(self):
        if self._backing is not None:
            return self._backing.identity()
        with self._lock:
            principal = self.next_principal
        return principal, _account_from_arn(principal)

    def _check_replace(self, name, kind, params, region=None, approved=False):
        """Ask for approval before a sign-in replaces a credential, as
        credsd's gate does: anything that exists, except an aws login
        session in ``region`` replaced by an aws login sign-in, which
        ``_commit_login`` decides by who signed in. Call it under the lock.

        Returns whether an approval was spent. Pass that back as
        ``approved`` for the second check after the browser step, so one
        approval covers the sign-in.
        """
        existing = self._credentials.get(name)
        if existing is None or approved:
            return approved
        if kind == KIND_LOGIN and _same_login_source(existing, region):
            return False
        self._spend_approval(name, _params_digest(params))
        return True
