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
"""OAuth authorization-code flow with PKCE against a loopback redirect.

The loopback listener and the sign-in prompt are the CLI's own, shared with
``aws sso login`` and ``aws login``: ``AuthCodeFetcher`` waits for the
redirect in its strict mode, and the SSO authorization handlers show the
link and open the browser.
"""

import base64
import hashlib
import http.client
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

from botocore.exceptions import (
    AuthCodeFetcherError,
    PendingAuthorizationExpiredError,
)

from awscli.customizations.agentregistry.constants import (
    CALLBACK_HOST,
    CALLBACK_PORT_ENV_VAR,
    DEFAULT_CALLBACK_PORT,
    HTTP_TIMEOUT,
    MAX_PRINTED_TEXT,
    TOKEN_ENV_VAR,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    printable,
    printable_url,
    read_error_body,
    read_limited,
    require_https,
    select_bearer_token,
    urlopen,
    write_status,
)
from awscli.customizations.sso.utils import (
    AuthCodeFetcher,
    OpenBrowserHandler,
    PrintOnlyHandler,
    open_browser_with_original_ld_path,
)

# Enough bytes for MAX_PRINTED_TEXT characters of UTF-8.
_ERROR_BODY_BYTES = 4 * MAX_PRINTED_TEXT

_PORT_DIGITS = re.compile(r'[0-9]{1,5}')

# Error codes that point at the registry owner's app client setup, and what
# to tell them. They come back on the sign-in redirect (RFC 6749, section
# 4.1.2.1) or from the token endpoint (section 5.2).
_OWNER_HINTS = {
    'invalid_client': (
        'The registry owner must configure the app client as a public client '
        'with no client secret.'
    ),
    'unauthorized_client': (
        'The app client does not allow the authorization-code grant; the '
        'registry owner must allow it.'
    ),
    'unsupported_response_type': (
        'The app client does not allow the authorization-code grant; the '
        'registry owner must allow it.'
    ),
    'invalid_scope': (
        'The app client does not allow the requested scopes ({scopes}); the '
        'registry owner must allow them.'
    ),
}


def pkce_pair():
    """Return a PKCE ``(verifier, challenge)`` pair using S256 per RFC 7636."""
    verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32))
        .decode('ascii')
        .rstrip('=')
    )
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return verifier, challenge


def callback_port():
    """The redirect port, fixed so it can be pre-registered with the provider."""
    override = os.environ.get(CALLBACK_PORT_ENV_VAR)
    if not override:
        return DEFAULT_CALLBACK_PORT
    # Plain ASCII digits only: int() would also accept signs, underscores,
    # surrounding spaces and other scripts' digits.
    port = int(override) if _PORT_DIGITS.fullmatch(override) else 0
    if not 1 <= port <= 65535:
        raise AgentRegistryJWTError(
            f'{CALLBACK_PORT_ENV_VAR} must be a port number from 1 to 65535, '
            f'got {printable(override)!r}.'
        )
    return port


def _listen(port):
    """The loopback listener for the redirect, on ``port``.

    ``AuthCodeFetcher`` binds the loopback address only, never every
    interface: anything that can reach the port can try to deliver a code.
    """
    try:
        fetcher = AuthCodeFetcher(redirect_port=port)
    except AuthCodeFetcherError as e:
        raise AgentRegistryJWTError(
            f'Could not listen on {CALLBACK_HOST}:{port} for the sign-in '
            f'redirect ({e.kwargs.get("error_msg", e)}). Free the port, or '
            f'set {CALLBACK_PORT_ENV_VAR} to another port that is also '
            f'registered as a callback URL with the identity provider.'
        )
    return fetcher


def _show_link(url, open_browser):
    """Show the sign-in link on stderr, and open it unless told not to.

    There is no cross-device advice: the redirect has to come back to the
    listener on this machine. A browser that cannot be launched is not
    fatal, because the link is always printed for manual use.
    """
    if open_browser:
        # Restores the original LD_LIBRARY_PATH, so a bundled (PyInstaller)
        # CLI can start the system browser on Linux.
        handler = OpenBrowserHandler(
            outfile=sys.stderr,
            open_browser=open_browser_with_original_ld_path,
        )
    else:
        handler = PrintOnlyHandler(outfile=sys.stderr)
    handler(
        userCode=None,
        verificationUri=url,
        verificationUriComplete=url,
        cross_device_flag=None,
    )


def _timeout_minutes(fetcher):
    return fetcher.overall_timeout // 60


def _timeout_message(fetcher, port, callback):
    return (
        f'Timed out after {_timeout_minutes(fetcher)} minutes waiting for '
        f'the sign-in redirect to {callback}. Either:\n'
        f'  - The browser is not running on this machine. Over SSH, forward '
        f'the port first (ssh -L {port}:{CALLBACK_HOST}:{port} <host>) and '
        f'run the command again with --no-browser to open the printed link '
        f'yourself, or export a token as {TOKEN_ENV_VAR}, which '
        f'--authorizer JWT then sends as is.\n'
        f'  - The sign-in page showed an error, for example a redirect '
        f'mismatch or "not allowed to access this app". The registry owner '
        f'must check the app client: the callback URL {callback} is '
        f'registered, the authorization-code flow is allowed, and you are '
        f'permitted to use it.'
    )


def _owner_hint(error, scopes):
    """An owner-facing hint for an OAuth error code, or ``''``."""
    hint = _OWNER_HINTS.get(error) if isinstance(error, str) else None
    if not hint:
        return ''
    return ' ' + hint.format(scopes=' '.join(scopes or []) or 'none')


def _token_error_hint(body, scopes):
    """The owner-facing hint for a token endpoint error body, or ``''``."""
    try:
        error = json.loads(body).get('error')
    except (ValueError, AttributeError):
        return ''
    return _owner_hint(error, scopes)


# The authorization request parameters this flow sets. Any of them already in
# the authorization endpoint's query is dropped, so a discovery document
# cannot preset where the code is sent or which state is accepted.
_SIGN_IN_PARAMETERS = frozenset(
    (
        'response_type',
        'client_id',
        'redirect_uri',
        'state',
        'code_challenge',
        'code_challenge_method',
        'scope',
    )
)

# Parameters that would override those: a request object (RFC 9101) carries
# its own copies, and response_mode changes how the code comes back.
_OVERRIDING_PARAMETERS = frozenset(('request', 'request_uri', 'response_mode'))


def sign_in_link(authorize_endpoint, query):
    """The authorization endpoint with ``query`` merged into its own query.

    RFC 6749, section 3.1, allows the endpoint to carry a query, which must
    be kept. It allows no fragment, so one is dropped.
    """
    parts = urllib.parse.urlsplit(authorize_endpoint)
    dropped = _SIGN_IN_PARAMETERS | _OVERRIDING_PARAMETERS | set(query)
    kept = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(
            parts.query, keep_blank_values=True
        )
        if key not in dropped
    ]
    merged = urllib.parse.urlencode(kept + list(query.items()))
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, merged, '')
    )


def _wait_for_code(fetcher, state, port, scopes):
    """The authorization code the redirect brings back.

    Only a GET on the callback path carrying ``state`` ends the wait. Any
    other request, including a redirect for another sign-in, is answered with
    an error and neither shown nor acted on.
    """
    callback = fetcher.redirect_uri_with_port()
    try:
        code, _ = fetcher.get_auth_code_and_state(expected_state=state)
    except PendingAuthorizationExpiredError:
        raise AgentRegistryJWTError(_timeout_message(fetcher, port, callback))
    result = fetcher.error
    if result:
        # The state matched, so this is the provider's answer, but whoever
        # sent the redirect still chose the text.
        error = printable(result['error'])
        detail = printable(result.get('error_description'))
        raise AgentRegistryJWTError(
            f'Sign-in failed: {error} {detail}'.strip()
            + _owner_hint(result['error'], scopes)
        )
    return code


def run_browser_login(
    authorize_endpoint,
    token_endpoint,
    client_id,
    scopes,
    ca_bundle=None,
    open_browser=True,
):
    """Show a sign-in link, await the redirect, exchange the code for tokens.

    The password is only ever entered in the browser, so MFA and federated
    sign-in work unchanged. ``ca_bundle`` is used to verify the token
    endpoint. With ``open_browser=False`` the link is printed but no browser
    is started; the redirect still has to reach the listener on this machine.
    """
    # Both come from discovery; validate before anything is shown or sent.
    require_https(authorize_endpoint, 'authorization endpoint')
    require_https(token_endpoint, 'token endpoint')

    verifier, challenge = pkce_pair()
    # Never empty: the listener only accepts a redirect that carries it.
    state = secrets.token_urlsafe(24)
    port = callback_port()
    fetcher = _listen(port)
    callback = fetcher.redirect_uri_with_port()
    try:
        query = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': callback,
            'state': state,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
        }
        if scopes:
            query['scope'] = ' '.join(scopes)
        _show_link(sign_in_link(authorize_endpoint, query), open_browser)
        write_status(
            f'Waiting for sign-in to complete (up to '
            f'{_timeout_minutes(fetcher)} minutes)...'
        )
        code = _wait_for_code(fetcher, state, port, scopes)
    finally:
        # The wait closes the listener too, but not on an interrupt.
        fetcher.http_server.server_close()

    form = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': callback,
        'code_verifier': verifier,
    }
    request = urllib.request.Request(
        token_endpoint,
        data=urllib.parse.urlencode(form).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urlopen(
            request,
            timeout=HTTP_TIMEOUT,
            purpose='token endpoint',
            ca_bundle=ca_bundle,
        ) as response:
            body = read_limited(response, token_endpoint)
        payload = json.loads(body.decode('utf-8'))
    except urllib.error.HTTPError as e:
        # The provider chooses the body; read only as much as is shown.
        body = read_error_body(e, _ERROR_BODY_BYTES)
        raise AgentRegistryJWTError(
            f'Code exchange failed at {printable_url(token_endpoint)} '
            f'(HTTP {e.code}): {printable(body)}'
            f'{_token_error_hint(body, scopes)}'
        )
    except (
        urllib.error.URLError,
        ValueError,
        OSError,
        http.client.HTTPException,
    ) as e:
        # OSError and HTTPException: a read that timed out or stopped short.
        raise AgentRegistryJWTError(
            f'Code exchange failed at {printable_url(token_endpoint)}: '
            f'{printable(e) or type(e).__name__}'
        )

    # Normalise so callers always read payload['access_token'] and get a token
    # the registry can validate.
    token, source = select_bearer_token(payload)
    payload['access_token'] = token
    payload['token_source'] = source
    write_status('Signed in.\n')
    return payload
