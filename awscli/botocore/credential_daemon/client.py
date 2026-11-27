# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential daemon's methods."""

import logging
import threading
import time

from botocore.credential_daemon.config import CLI_TAGS
from botocore.credential_daemon.discovery import default_socket_path
from botocore.credential_daemon.model import (
    CredentialRow,
    LogoutResult,
    SocketChecks,
)
from botocore.credential_daemon.transport import (
    CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    MAX_MESSAGE_BYTES,
    MAX_REPLY_LINE_BYTES,
    _Connection,
)
from botocore.exceptions import (
    CredentialDaemonError,
    CredentialDaemonProtocolError,
)

# One logger name for the package, as before the split, so --debug
# output is the same.
logger = logging.getLogger('botocore.credential_daemon')


# How the CLI names itself to the credential daemon, as the creator. The
# CLI never reads it back: credential/list rows don't carry it.
CLIENT_NAME = 'aws-cli'


# The credential daemon gives up on a sign-in after 300 seconds.
SIGN_IN_TIMEOUT = 330
# A logout waits up to 10 seconds for the user's write lock and holds it up
# to 60, with up to 30 of them spent on the SSO refresh and Logout calls.
LOGOUT_TIMEOUT = 75


class CredentialDaemonClient:
    """Calls the credential daemon's JSON-RPC API.

    Each call opens its own connection, so one client can be shared between
    threads; the socket a thread last dialed is kept per thread, and a
    pinned socket is looked up once under a lock. Every call sends its one
    request and nothing else, as ``credential/get`` does in the SEP.
    Requests and responses are never logged, because they carry secrets.

    Each call has two timeouts, as in the SEP: ``connect_timeout`` (1
    second by default) for connecting, and ``timeout`` (5 seconds by
    default) for the whole call. Sign-in calls, which wait on the
    customer, use ``SIGN_IN_TIMEOUT`` for the whole call instead, and
    ``logout``, which can wait on SSO, uses ``LOGOUT_TIMEOUT``.

    ``bootstrap`` and ``store_keys`` send ``creator``, the tool's name, for
    a credential daemon that records which tool created the credential.
    Nothing here depends on it. ``creator`` is ``aws-cli`` unless a test
    sets another, or None to send none. They send no tags, so a credential
    they replace keeps its tags; callers add ``CLI_TAGS`` after a
    successful bootstrap with ``mark_created_by_cli``, which keeps the
    credential's other tags.

    Without ``socket_path``, the socket is looked up again on every call
    and never cached, so a refresh dials the daemon a new process would.
    One call uses one lookup. A command that makes several calls, such
    as a list and then a logout for each
    row, passes ``pin_socket=True``: the first lookup is kept for every
    later call, in every thread, so the command can't act on one daemon's
    rows in another daemon.

    Every connection is checked before anything is sent on it
    (``check_socket``, ``check_peer`` and, on macOS,
    ``check_code_signature``): who owns the socket and the folders above
    it, which user serves it, and on macOS that the process serving it is
    the signed credential daemon (the system socket must also be owned
    and served by root). A failure raises
    ``CredentialDaemonUntrustedSocketError`` and nothing is sent.
    ``checks`` picks the level (``SocketChecks``): ``FULL``, the default,
    for commands that send secrets or start sign-ins, runs every check;
    ``PEER``, for the credential provider's credential/get, runs all but
    the code signature check.
    """

    def __init__(
        self,
        socket_path=None,
        pin_socket=False,
        timeout=DEFAULT_TIMEOUT,
        creator=CLIENT_NAME,
        connect_timeout=CONNECT_TIMEOUT,
        checks=SocketChecks.FULL,
    ):
        self._socket_path = socket_path
        self._pin_socket = pin_socket
        self._checks = SocketChecks(checks)
        # The path this thread's last call dialed, for error messages.
        self._dialed = threading.local()
        # Guards pinning, so the first lookup is the one every thread keeps.
        self._pin_lock = threading.Lock()
        self._timeout = timeout
        self._connect_timeout = connect_timeout
        self._creator = creator

    @property
    def socket_path(self):
        """The socket the last call dialed, or the one the next would.

        Before any call, it's advisory unless the socket is pinned: the
        next call looks the socket up again. A pinned client keeps this
        lookup for every call.
        """
        if self._socket_path is not None:
            return self._socket_path
        last_socket_path = getattr(self._dialed, 'socket_path', None)
        if last_socket_path is not None:
            return last_socket_path
        if self._pin_socket:
            return self._resolve_socket_path()
        return default_socket_path()

    def list_credentials(self, tags=None):
        """Return a ``CredentialRow`` per credential, with no secrets.

        Each row has the credential's ``source`` and ``tags``. With
        ``tags``, only credentials with every one of those tags are listed.
        """
        params = {'tags': dict(tags)} if tags else None
        result = self._call('credential/list', params)
        rows = result.get('credentials') if isinstance(result, dict) else None
        if not isinstance(rows, list):
            raise CredentialDaemonProtocolError(
                error_msg=(
                    'The credential daemon sent a credential '
                    'list the CLI can\'t read.'
                )
            )
        return [CredentialRow.from_wire(row) for row in rows]

    def get_credentials(self, name, account_id=None, role_name=None):
        """Return short-lived credentials, refreshed by the credential daemon
        if needed.

        SSO credentials need the account and role. The credential daemon names
        the credential in ``credential``, in the request and the reply.
        """
        params = {'credential': name}
        if account_id is not None:
            params['account_id'] = account_id
        if role_name is not None:
            params['role_name'] = role_name
        return self._call(
            'credential/get', params, max_line_bytes=MAX_REPLY_LINE_BYTES
        )

    def store_keys(
        self,
        name,
        access_key_id,
        secret_access_key,
        region,
    ):
        """Store static keys as credential ``name``, sealed by the
        credential daemon.

        This is ``credential/bootstrap`` with the ``aws_iam_user`` provider,
        for new keys and replaced ones alike. ``region`` is where the
        credential daemon makes its STS calls with the keys; it's required.
        No MFA device is sent: this release has no MFA sign-in for keys in
        the credential daemon.

        A new name is stored at once. Over a name that exists, the
        credential daemon asks for approval first (``APPROVAL_REQUIRED``)
        and approves only a request with exactly the same params, so the
        approved retry must send the same keys and region.
        """
        provider = {
            'type': 'aws_iam_user',
            'access_key_id': access_key_id,
            'secret_access_key': secret_access_key,
            'region': region,
        }
        params = self._bootstrap_params(
            {'credential': name, 'provider': provider}
        )
        return self._call('credential/bootstrap', params)

    def logout(self, name):
        """Sign a credential out, keeping its entry, and return a
        ``LogoutResult``.

        The credential daemon deletes the credential's session. For SSO it
        first ends the session at SSO; if that fails, the local session is
        still deleted and ``provider`` is ``PROVIDER_FAILED``. Only sign-in
        credentials (aws login, SSO, web identity) can be signed out: the
        credential daemon refuses any other with
        ``LOGOUT_UNSUPPORTED_SOURCE`` (see ``is_logout_unsupported``).
        The call can wait on SSO, so it uses ``LOGOUT_TIMEOUT``.
        """
        return LogoutResult.from_reply(
            self._call(
                'credential/logout',
                {'credential': name},
                timeout=LOGOUT_TIMEOUT,
            )
        )

    def remove(self, name):
        """Delete a credential and everything it holds, such as access
        keys."""
        return self._call('credential/remove', {'credential': name})

    def bootstrap(
        self, provider, name=None, on_progress=None, name_prefix=None
    ):
        """Run a whole sign-in in one call and return its result.

        ``on_progress(progress)`` gets each progress message, such as
        ``authorize_url`` or ``authorize_code``. If it returns a dict, the
        dict is sent to the credential daemon as the answer. Closing the
        connection cancels the sign-in, so if ``on_progress`` raises, the
        credential daemon stops too. With ``name_prefix`` instead of ``name``,
        the credential daemon names the credential after who signs in and
        returns the name.
        """
        params = self._bootstrap_params({'provider': provider})
        if name is not None:
            params['credential'] = name
        if name_prefix is not None:
            params['name_prefix'] = name_prefix
        return self._call(
            'credential/bootstrap',
            params,
            on_progress=on_progress,
            timeout=SIGN_IN_TIMEOUT,
        )

    def _bootstrap_params(self, params):
        """Add what every credential/bootstrap sends: ``creator``.

        No ``tags``: with them, the credential daemon would replace the
        credential's whole tag set, dropping tags the customer added.
        Without them, a replaced credential keeps its tags.
        """
        if self._creator is not None:
            params['creator'] = self._creator
        return params

    def tag(self, name, set_tags=None, unset=None):
        """Edit credential ``name``'s tags with ``credential/tag``.

        ``set_tags`` are added, overwriting the value of a key the
        credential already has, then the ``unset`` keys are removed. Tags
        not named keep their values. Tag edits need no approval.
        """
        params = {'credential': name}
        if set_tags:
            params['set'] = dict(set_tags)
        if unset:
            params['unset'] = list(unset)
        return self._call('credential/tag', params)

    def mark_created_by_cli(self, name):
        """Add ``CLI_TAGS`` to credential ``name``, keeping its other tags.

        Returns whether it worked. A failure is logged, not raised, so a
        sign-in or store that already succeeded still does.
        """
        try:
            self.tag(name, set_tags=CLI_TAGS)
        except CredentialDaemonError as e:
            logger.debug(
                'Failed to tag a credential created-by=aws-cli: %s', e
            )
            return False
        return True

    def _call(
        self,
        method,
        params=None,
        on_progress=None,
        timeout=None,
        max_line_bytes=MAX_MESSAGE_BYTES,
    ):
        logger.debug('Calling the credential daemon %s', method)
        # The call timeout covers connecting and the call. Sign-in calls
        # pass their own, longer one.
        call_timeout = timeout or self._timeout
        deadline = time.monotonic() + call_timeout
        path = self._resolve_socket_path()
        with _Connection.open(
            path,
            min(self._connect_timeout, call_timeout),
            checks=self._checks,
        ) as connection:
            return connection.call(
                method,
                params,
                on_progress,
                deadline,
                call_timeout,
                max_line_bytes,
            )

    def probe(self):
        """Connect to the socket the next call would dial, and close the
        connection. Nothing is sent.

        A pinned client keeps that socket for its later calls. Raises what
        a call would if nothing answers there or a check fails.
        """
        path = self._resolve_socket_path()
        _Connection.open(
            path,
            min(self._connect_timeout, self._timeout),
            checks=self._checks,
        ).close()

    def _resolve_socket_path(self):
        if self._socket_path is not None:
            return self._socket_path
        if self._pin_socket:
            with self._pin_lock:
                if self._socket_path is None:
                    self._socket_path = default_socket_path()
                path = self._socket_path
        else:
            path = default_socket_path()
        self._dialed.socket_path = path
        return path
