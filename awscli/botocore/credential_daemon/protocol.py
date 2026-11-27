# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential daemon's JSON-RPC replies and errors."""

from botocore.credential_daemon.messages import _with_approval_instructions
from botocore.credential_daemon.text import strip_control_characters
from botocore.exceptions import (
    CredentialDaemonApprovalRequiredError,
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonCredentialUnusableError,
    CredentialDaemonIdentityMismatchError,
    CredentialDaemonProtocolError,
    CredentialDaemonProviderUnavailableError,
    CredentialDaemonReauthRequiredError,
    CredentialDaemonRequestRejectedError,
)

_DOMAIN_ERROR = -32000


_ERRORS_BY_CODE = {
    'REAUTH_REQUIRED': CredentialDaemonReauthRequiredError,
    'CREDENTIAL_NOT_FOUND': CredentialDaemonCredentialNotFoundError,
    'PROVIDER_UNAVAILABLE': CredentialDaemonProviderUnavailableError,
    'APPROVAL_REQUIRED': CredentialDaemonApprovalRequiredError,
    'CONFIG_DRIFTED': CredentialDaemonCredentialUnusableError,
    # The caller's config.toml or credentials.toml parses but doesn't
    # validate, so credsd refuses to read or list credentials until it's
    # fixed and revalidated.
    'CONFIG_INVALID': CredentialDaemonCredentialUnusableError,
    'INTEGRITY_UNVERIFIABLE': CredentialDaemonCredentialUnusableError,
    'CUSTODY_BROKEN': CredentialDaemonCredentialUnusableError,
    # credential/login signed in as another principal than the credential
    # records, or it records none. The sign-in finished and
    # was refused, and the old session still works, so it isn't
    # AUTH_CANCELLED, REAUTH_REQUIRED or an unusable credential.
    'IDENTITY_MISMATCH': CredentialDaemonIdentityMismatchError,
}
# Shown after the credential daemon's message for these codes, so the
# customer can tell them apart.
_CODE_SHOWN = frozenset(
    (
        'CONFIG_DRIFTED',
        'CONFIG_INVALID',
        'INTEGRITY_UNVERIFIABLE',
        'CUSTODY_BROKEN',
        'IDENTITY_MISMATCH',
    )
)


def _result_from_reply(message):
    # The SEP's reply shape: jsonrpc "2.0" and exactly one of result and
    # error. The reply's id isn't compared with the request's: a connection
    # carries one request, so its reply is for that request. The messages
    # say what's wrong but never quote the reply, which can carry secrets.
    if message.get('jsonrpc') != '2.0':
        raise CredentialDaemonProtocolError(
            error_msg=(
                'The credential daemon sent a reply whose jsonrpc '
                'isn\'t "2.0".'
            )
        )
    # A null result or error counts as absent (the SEP).
    has_result = message.get('result') is not None
    has_error = message.get('error') is not None
    if has_result and has_error:
        raise CredentialDaemonProtocolError(
            error_msg=(
                'The credential daemon sent a reply with both result and '
                'error.'
            )
        )
    if has_error:
        raise _error_from_response(message['error'])
    if not has_result:
        raise CredentialDaemonProtocolError(
            error_msg=(
                'The credential daemon sent a reply with neither result nor '
                'error.'
            )
        )
    return message['result']


def _error_from_response(error):
    if not isinstance(error, dict):
        return CredentialDaemonProtocolError(
            error_msg=(
                'The credential daemon sent an error the CLI can\'t read.'
            )
        )
    # ``daemon_message`` is only ever what the credential daemon sent; the
    # fallback text is for display only.
    daemon_message = error.get('message')
    if isinstance(daemon_message, str):
        daemon_message = (
            strip_control_characters(daemon_message).strip() or None
        )
    else:
        daemon_message = None
    message = daemon_message or 'The credential daemon returned an error.'
    data = error.get('data')
    if not isinstance(data, dict):
        data = {}
    if error.get('code') != _DOMAIN_ERROR:
        # The credential daemon refused the request itself: a CLI bug, or a
        # credential daemon version this CLI doesn't match. The SEP counts it
        # as any other error reply.
        return CredentialDaemonRequestRejectedError(
            error_msg=(
                f'The credential daemon rejected the request: {message}'
            ),
            code=error.get('code'),
            data=data,
            daemon_message=daemon_message,
        )
    code = data.get('code')
    if code is not None and not isinstance(code, str):
        # A list or an object isn't a code, and can't be looked up.
        return CredentialDaemonProtocolError(
            error_msg=(
                'The credential daemon sent an error code the CLI '
                'can\'t read.'
            )
        )
    error_class = _ERRORS_BY_CODE.get(code)
    if error_class is None:
        # The SEP's REQUEST_REJECTED, naming the credential daemon's code.
        # ``code`` stays the credential daemon's, so commands can still act on
        # codes they know, such as AUTH_CANCELLED.
        shown = message
        if isinstance(code, str) and code:
            shown = f'{message} ({strip_control_characters(code)})'
        return CredentialDaemonRequestRejectedError(
            error_msg=shown,
            code=code,
            data=data,
            daemon_message=daemon_message,
        )
    if code == 'APPROVAL_REQUIRED':
        message = _with_approval_instructions(message, data)
    elif code in _CODE_SHOWN:
        message = f'{message} ({code})'
    return error_class(
        error_msg=message,
        code=code,
        data=data,
        daemon_message=daemon_message,
    )
