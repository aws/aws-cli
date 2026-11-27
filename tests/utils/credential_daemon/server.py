# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""A fake credential daemon for tests and local development.

The fake speaks the credential daemon JSON-RPC protocol the CLI uses: one JSON
object per line, at most 1 MiB, over a Unix socket. Every credential is
kept in memory. Unless ``backing_profile`` is set, the fake never calls
AWS and every credential it returns is fake.

As in credsd, every method that
names a credential takes it as ``{"credential": "<name>"}``, and unknown
params are refused with -32602. ``credential/get`` names the credential in
its result's ``credential`` and adds ``provenance``. ``credential/list`` rows
carry only ``credential``, ``kind``, ``source``, ``status`` and ``tags``,
as credsd's ``CredentialSummary`` does with credential tags (no
``creator``, ``principal``, ``account_id`` or ``expires_at``), with credsd's
statuses: ``active``, ``expiring``, ``expired``, ``sign_in_required``,
``no_session``, ``corrupt``, ``unreadable``, ``decrypt_failed`` and
``unknown``. ``credential/logout`` signs out only sign-in sources
(``aws_login``, ``aws_idc_sso`` and ``aws_web_identity``) and refuses any
other with ``LOGOUT_UNSUPPORTED_SOURCE``. It returns ``{signed_out,
provider}``: ``signed_out`` is false only with ``provider: none``, when there
was no session. An SSO sign-out reports what SSO did (``ended`` unless a
test sets ``token_rejected`` or ``failed`` with ``set_sso_logout``), and
``failed`` adds ``start_url`` and, unless the test drops it,
``access_token_expires_at``. Any other sign-in is ``local_only``.
``credential/remove`` deletes a credential, and misses with
``CREDENTIAL_NOT_FOUND``. ``REAUTH_REQUIRED`` for a credential that isn't
signed in is in credsd's words, "credential '<name>' requires
re-authentication (<what to do>)", with ``credential`` and ``remediation``
("creds login --credential <name>") in ``data``; keys whose MFA session
ended still get the fake's own "<name> needs an MFA code". Tags are as in
credsd's credential tags: ``credential/list`` takes a ``tags`` filter (every
pair must match; a
``null`` value needs only the key), ``credential/bootstrap`` takes ``tags``
(given, they become the credential's tags; left out, a credential it
replaces keeps its tags and a new one has none), and ``credential/tag``
takes ``credential``, ``set`` and ``unset``, with no approval. Keys fold to
lowercase (``A-Z`` only) and are 1 to 63 of ``a-z 0-9 . _ -`` starting with
``a-z`` or ``0-9``; values are at most 256 bytes of printable ASCII; a
credential has at most 32 tags. Anything else, two spellings of one key, or
a key both set and unset, is refused with -32602 and changes nothing.
``credential/import`` takes no tags. As in credsd, while the
caller's configuration parses but doesn't validate (``set_config_invalid``),
``credential/get``, ``credential/list`` and ``credential/tag`` refuse with
``CONFIG_INVALID`` ("caller configuration does not validate: <errors>; fix
it, then run: creds revalidate"); credsd's ``credential/describe`` does too,
and the fake doesn't have it. ``credential/import``
needs ``region``, the region for the STS calls the credential daemon
makes with the keys, and refuses a request without one with -32602
(credsd's "missing field `region`"). It only adds, as credsd's does:
a name that exists already, whoever created it, gets ``status:
skipped`` with a ``reason`` and nothing is stored. A new one gets
``status: imported``. Like credsd's, it has no ``mfa_serial`` or
``duration_seconds`` and drops them with no error, so imported keys never
have an MFA device. These parts are assumptions, because the
credential daemon hasn't defined them yet:

* ``credential/login`` is a working name for the credential daemon's
  ``environment/login``. For static keys stored with an MFA device
  (``mfa_serial`` at ``credential/bootstrap``), it sends a ``mfa_required``
  progress notification with ``serial``, answered with ``{selection: <code>}``
  through ``credential/bootstrap/respond``. It returns ``{}``, with or without
  a device, as the credential daemon does; ``credential/get`` says when the
  MFA session expires. On an aws login or SSO credential it starts that
  credential's sign-in, as the credential daemon does: aws login sends
  ``authorize_url``. SSO, as credsd's ``login_sso`` does, first renews
  unattended with the refresh token it holds and sends nothing; only when
  that fails (the credential is signed out, or ``sign_in_required``) does it
  send ``device_code``. It needs no approval, and keeps the stored start URL,
  region, scopes, account and role.
* A wrong MFA code (``000000`` or anything that isn't 6 digits in the fake)
  fails with ``INTERNAL`` and the credential daemon's ``provider error: ``
  text around STS's message. It leaves an MFA session that is already running
  in place.
* ``credential/login`` on keys with no session fails with
  ``CREDENTIAL_NOT_FOUND``, as for keys that ``credential/remove`` deleted.
* For keys stored with an MFA device (``duration_seconds`` is the MFA session
  length, 900 to 129600, default 12 hours), ``credential/get`` fails with
  ``REAUTH_REQUIRED`` until ``credential/login`` and after the MFA session
  expires.
* Only storing the keys again changes the stored MFA device.
* SSO credentials have the kind ``aws_idc_sso``. Their ``credential/bootstrap``
  provider has ``type``, ``start_url``, ``sso_region``, ``scopes``,
  ``use_device_code`` and ``callback_port``.
* The fake reports ``active``, ``expired`` (a session past its end) and
  ``no_session`` (signed out) by itself. Tests can seed any other status.
* Tests can seed a source the CLI never creates, such as credsd's
  ``aws_roles_anywhere``, ``static_secret``, ``aws_web_identity`` or
  ``unsupported`` (credsd's catch-all for a source
  it can't decode). Its row carries that source, and ``credential/logout``
  signs it out only if it's a sign-in source, as above. Only ``aws_login``
  and ``aws_idc_sso`` sessions end; any other source has no session end,
  as access keys don't.
* Progress notification types and fields: ``authorize_url`` with ``url``. A
  ``--remote`` sign-in sends one ``authorize_code`` with ``url`` instead of
  ``authorize_url``, answered with ``{selection: <the pasted code>}``, as the
  credential daemon does.
* As in credsd, the credential daemon records who an aws login
  sign-in signed in as. A sign-in that replaces an aws login credential in
  the same region needs no approval only as the same principal: the same
  partition, account, kind (``role``, ``user`` or ``root``) and role or user
  name, whatever the session. Another principal, or a credential with no
  record of one (in the fake, no principal), fails with
  ``APPROVAL_REQUIRED`` after the sign-in and saves nothing. The challenge
  says ``replace existing credential '<name>' with a new aws-login (region
  <region>) signed in as <kind> <name> in account <account> (<partition>);
  it was <the same for the record, or "no recorded sign-in">``. The approval
  is bound to the params and both principals, so it doesn't approve a re-run
  that signs in as someone else. There's no progress message to answer.
* ``AUTH_CANCELLED`` is the error after no roles chosen.
* As in credsd, an aws login ``credential/bootstrap`` result carries
  ``credential`` (the name) and ``identity`` (``{arn, partition, account,
  kind, name, session}``), and no expiry. The multi-role
  result carries ``name``, ``principal`` and ``expires_at``. The
  ``credential/import`` result carries ``principal`` next to credsd's
  ``credential`` and ``status``.
* An ``aws-login`` ``credential/bootstrap`` takes ``name_prefix`` instead of
  ``credential``, and needs exactly one of them. As in credsd, the
  credential daemon then names the credential after the principal that
  signed in, not the session: the prefix, then ``<account>-role-<role>`` for
  a role, ``<account>-user-<user name>`` (path dropped) for an IAM user, and
  ``<account>-root`` for the root user. Any other principal gets the prefix
  and the whole principal. The result's ``credential`` says which name it
  chose.
* That name is cleaned up as credsd's ``normalize_name`` does: each character
  outside ``A-Z a-z 0-9 . _ -`` becomes ``-``, the name is cut to 55
  characters, a leading ``.`` is dropped, and ``-`` and 8 hex digits of the
  SHA-256 of the uncleaned name are added, whenever anything changed.
* A ``name_prefix`` sign-in as the principal a credential of that name
  records refreshes it in place, with no approval. A credential of that name
  that isn't an aws login session in that region needs approval, as any
  replace does. A prefix is 1 to 32 of ``A-Z a-z 0-9 . _ -``, not starting
  with ``.``. SSO and multi-role sign-ins don't take one.
* As in credsd (``same_provider_source``), a ``credential/bootstrap`` over a
  name that exists needs approval (``APPROVAL_REQUIRED``) before the sign-in,
  except an aws login sign-in over an aws login credential in the same
  region, which is decided by principal after it. So does an SSO sign-in
  over an SSO credential: signing it in again goes through ``credential/login``, which
  needs none. ``data`` has only credsd's ``challenge`` and ``remediation``.
* As in credsd, an ``aws_iam_user`` ``credential/bootstrap`` takes
  ``access_key_id``, ``secret_access_key`` and ``region`` (required), and
  ``mfa_serial`` and ``duration_seconds``. It returns ``{}``. Over a name that
  exists, whatever it holds, it fails with ``APPROVAL_REQUIRED``
  and changes nothing. ``data`` has an object ``challenge`` and a
  ``remediation`` string. Once ``approve`` (or ``mock/approve``) approves the
  challenge, the same bootstrap again, with the same params, replaces the
  credential's keys and MFA device. Each approval is used once. The credential
  daemon doesn't yet skip approval when the new keys belong to the same IAM
  user.
* The credential daemon always sends ``expires_at`` for session credentials.
  The CLI, like credsd's own client, refuses session credentials without one.
* An SSO or aws login ``credential/bootstrap`` provider can have
  ``callback_port``, as ``--redirect-port`` gives it. The credential daemon's
  ``aws-login`` provider takes ``callback_port``; its SSO provider has no port
  field yet, so SSO's ``callback_port`` is a working assumption. For aws login
  the fake, like the credential daemon, refuses a port below 1024; for SSO it
  takes 1-65535. The CLI assumes SSO's range is aws-login's, 1024-65535, and
  refuses other ports itself before calling the credential daemon. For the
  browser sign-in, the fake listens on 127.0.0.1 at that port, or any free port
  without it, for the sign-in's redirect, and names it in the authorize URL's
  ``redirect_uri``. ``REDIRECT_PORT_IN_USE`` is a working error code for a port
  it can't listen on.
* The caller may name itself with a flat ``"creator": "<tool name>"`` on
  ``credential/bootstrap`` and ``credential/import``. Like
  credsd, the fake accepts it and keeps nothing: no row says who created a
  credential, and approval doesn't depend on it. Credential tags say it
  instead.
* As in credsd, ``credential/login`` for an aws login credential
  saves the sign-in only as the principal the credential records, signed-out
  credentials included. Anything else, a credential with no record included,
  fails with ``IDENTITY_MISMATCH`` in credsd's words and saves nothing.
* Progress notifications also carry the ``request_id`` of their
  ``credential/bootstrap`` or ``credential/login`` call.
  ``credential/bootstrap/respond`` can send it back, but needn't: one sign-in
  runs per connection.
* A ``--remote`` sign-in takes one code. The credential daemon decodes it
  (base64 of ``code=...&state=...``) and checks its state. The fake refuses a
  code that isn't base64 with the credential daemon's decode message, and an
  empty code or one that starts with ``invalid`` with its state message, both
  as ``PROVIDER_UNAVAILABLE``. Like the credential daemon, the fake refuses
  ``remote`` with ``callback_port``.
* Closing the connection cancels a running ``credential/bootstrap`` or
  ``credential/login``. ``aws configure mfa-login`` relies on it when the
  customer gives no MFA code.
* ``credential/get`` results include the credential daemon's ``kind``, the
  material kind (``session_credentials``). It doesn't say the credential's
  source, so the CLI's user agent sends only ``CREDENTIAL_DAEMON``.
* An SSO ``credential/bootstrap`` sends ``select_account`` and ``select_role``
  only when its provider has ``select_account_and_role``, as for ``aws
  configure sso``. ``select_account`` carries ``accounts: [{"id", "name",
  "email"}]`` and ``select_role`` carries ``roles: [<role name>]``.
  ``credential/bootstrap/respond`` answers with ``{"account_id"}`` and then
  ``{"role_name"}``. The result then names the account and role chosen, and the
  credential isn't bound to them.
* The credential daemon listens at its own ``credsd/credsd.sock`` paths,
  which the SDKs reach through a link at ``~/.aws/credential-daemon.sock``
  (SEP, Socket location). The fake listens wherever it's told, and
  ``daemon.sock`` is its file name.

``mock/*`` methods only exist in the fake. Tests and developers use them
to complete sign-ins, change who signs in and inject failures.
"""

import json
import logging
import os
import queue
import shutil
import socket
import socketserver
import stat
import struct
import tempfile
import threading
import time

from tests.utils.credential_daemon._faults import FaultsMixin
from tests.utils.credential_daemon._protocol import (
    _PARAMS,
    _PROVIDER_PARAMS,
    _SESSION_END,
    DEFAULT_IAM_USER_PRINCIPAL,
    DEFAULT_PRINCIPAL,
    DEFAULT_ROLES,
    INVALID_REQUEST,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    MAX_LINE_BYTES,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PROTOCOL_VERSION,
    SIGN_IN_METHODS,
    SSO_LOGOUT_ENDED,
    USABLE_STATUSES,
    VERSION,
    DomainError,
    InvalidParams,
    RpcError,
    _check_params,
    _iso,
    _redact,
    _require_name,
    _require_str,
    _role_name,
    _utcnow,
    _validate_name,
)
from tests.utils.credential_daemon._signin import SignInMixin
from tests.utils.credential_daemon._store import StoreMixin

# Other tools load this file by path and read these names off it.
__all__ = [
    'KIND_IAM_USER',
    'KIND_LOGIN',
    'KIND_SSO',
    'USABLE_STATUSES',
    '_PROVIDER_PARAMS',
]


LOG = logging.getLogger(__name__)


def default_socket_path():
    """A per-user socket path for running the fake by hand."""
    base = os.environ.get('XDG_RUNTIME_DIR')
    if not base or not os.path.isdir(base):
        base = tempfile.gettempdir()
    return os.path.join(
        base, f'credential-daemon-mock-{os.getuid()}', 'daemon.sock'
    )


class _ConnectionClosed(Exception):
    """The client hung up while a sign-in was waiting on it."""


class _Interaction:
    """What a sign-in needs from the connection that started it."""

    def __init__(self, request_id, send, answers, closed, deadline):
        self.request_id = request_id
        self._send = send
        self._answers = answers
        self._closed = closed
        self._deadline = deadline

    def notify(self, notification_type, **fields):
        params = dict(fields, type=notification_type)
        params['request_id'] = self.request_id
        self._send(
            {
                'jsonrpc': '2.0',
                'method': 'notifications/progress',
                'params': params,
            }
        )

    def answer(self):
        """Wait for the client's credential/bootstrap/respond."""
        while True:
            self._check()
            try:
                return self._answers.get(timeout=0.05)
            except queue.Empty:
                pass

    def wait_for(self, event):
        while not event.wait(0.05):
            self._check()

    def sleep(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self._check()
            time.sleep(min(0.05, max(0, end - time.monotonic())))
        self._check()

    def _check(self):
        if self._closed.is_set():
            raise _ConnectionClosed()
        if time.monotonic() >= self._deadline:
            raise DomainError('AUTH_TIMEOUT', 'The sign-in timed out')


class _ConnectionHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self._write_lock = threading.Lock()
        self._closed = threading.Event()
        self._answers = {}
        self._answers_lock = threading.Lock()
        self.server.connections.add(self)

    def finish(self):
        self._closed.set()
        self.server.connections.discard(self)
        try:
            super().finish()
        except OSError:
            pass

    def close_connection(self):
        self._closed.set()
        try:
            self.request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def handle(self):
        while not self._closed.is_set():
            try:
                line = self.rfile.readline(MAX_LINE_BYTES + 1)
            except OSError:
                break
            if not line:
                break
            if len(line) > MAX_LINE_BYTES and not line.endswith(b'\n'):
                # The rest of the line is still unread, so there's no
                # way to find the next message. Report it and hang up.
                self._send_error(
                    None,
                    RpcError(INVALID_REQUEST, 'Messages are limited to 1 MiB'),
                )
                break
            if line.strip():
                self._handle_line(line)

    def _handle_line(self, line):
        try:
            message = json.loads(line)
        except ValueError:
            self._send_error(None, RpcError(PARSE_ERROR, 'Parse error'))
            return
        if isinstance(message, list):
            self._send_error(
                None, InvalidParams('Batch requests are not supported')
            )
            return
        if (
            not isinstance(message, dict)
            or message.get('jsonrpc') != '2.0'
            or not isinstance(message.get('method'), str)
        ):
            request_id = (
                message.get('id') if isinstance(message, dict) else None
            )
            self._send_error(
                request_id, RpcError(INVALID_REQUEST, 'Invalid request')
            )
            return
        request_id = message.get('id')
        is_notification = 'id' not in message
        method = message['method']
        params = message.get('params')
        try:
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise InvalidParams('params must be an object')
            if method in SIGN_IN_METHODS:
                if not is_notification:
                    self._start_signin(request_id, method, params)
                return
            if method == 'credential/bootstrap/respond':
                result = self._deliver_answer(params)
            else:
                result = self.server.fake.dispatch(method, params)
        except RpcError as e:
            if not is_notification:
                self._send_error(request_id, e)
            return
        except Exception:
            LOG.exception('Unexpected error handling %s', method)
            if not is_notification:
                self._send_error(
                    request_id, DomainError('INTERNAL', 'Internal error')
                )
            return
        if not is_notification:
            self._send({'jsonrpc': '2.0', 'id': request_id, 'result': result})

    def _start_signin(self, request_id, method, params):
        answers = queue.Queue()
        with self._answers_lock:
            if request_id in self._answers:
                raise InvalidParams(f'Sign-in {request_id} is already running')
            self._answers[request_id] = answers
        interaction = _Interaction(
            request_id,
            self._send,
            answers,
            self._closed,
            time.monotonic() + self.server.fake.auth_timeout,
        )
        threading.Thread(
            target=self._run_signin,
            args=(request_id, method, params, interaction),
            daemon=True,
        ).start()

    def _run_signin(self, request_id, method, params, interaction):
        fake = self.server.fake
        run = (
            fake.bootstrap if method == 'credential/bootstrap' else fake.login
        )
        try:
            result = run(params, interaction)
        except _ConnectionClosed:
            LOG.debug('Client hung up during sign-in %s', request_id)
        except RpcError as e:
            self._send_error(request_id, e)
        except Exception:
            LOG.exception('Unexpected error in sign-in %s', request_id)
            self._send_error(
                request_id, DomainError('INTERNAL', 'Internal error')
            )
        else:
            self._send({'jsonrpc': '2.0', 'id': request_id, 'result': result})
        finally:
            with self._answers_lock:
                self._answers.pop(request_id, None)

    def _deliver_answer(self, params):
        _check_params('credential/bootstrap/respond', params)
        with self._answers_lock:
            request_id = params.get('request_id')
            if request_id is None and len(self._answers) == 1:
                request_id = next(iter(self._answers))
            answers = self._answers.get(request_id)
        if answers is None:
            raise InvalidParams('No sign-in is waiting for an answer')
        answer = {k: v for k, v in params.items() if k != 'request_id'}
        self.server.fake.record('credential/bootstrap/respond', answer)
        answers.put(answer)
        return {}

    def _send_error(self, request_id, error):
        self._send(
            {'jsonrpc': '2.0', 'id': request_id, 'error': error.to_dict()}
        )

    def _send(self, message):
        data = json.dumps(message, separators=(',', ':')).encode('utf-8')
        with self._write_lock:
            try:
                self.wfile.write(data + b'\n')
                self.wfile.flush()
            except (OSError, ValueError):
                self._closed.set()


if hasattr(socketserver, 'UnixStreamServer'):
    _UnixStreamServer = socketserver.UnixStreamServer
else:

    class _UnixStreamServer:
        # Windows has no Unix stream server. The fake never runs there (the
        # functional tests' fake fixture skips on win32), but this module
        # still imports, so tests that don't need the fake are collected.
        def __init__(self, *args, **kwargs):
            raise RuntimeError('The fake credential daemon needs Unix sockets')


class _UnixServer(socketserver.ThreadingMixIn, _UnixStreamServer):
    daemon_threads = True
    # stop() hangs up every connection itself.
    block_on_close = False

    def __init__(self, path, fake):
        self.fake = fake
        self.connections = set()
        # Create the socket owner-only from the start, not after a chmod.
        old_umask = os.umask(0o177)
        try:
            super().__init__(path, _ConnectionHandler)
        finally:
            os.umask(old_umask)

    def verify_request(self, request, client_address):
        return _peer_is_current_user(request)


def _peer_is_current_user(sock):
    if not hasattr(socket, 'SO_PEERCRED'):
        # Elsewhere the 0600 socket in a 0700 directory is the only guard.
        return True
    # struct ucred: pid_t, then uid_t and gid_t, which are unsigned.
    creds = sock.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('iII')
    )
    _, uid, _ = struct.unpack('iII', creds)
    if uid != os.getuid():
        LOG.warning('Refused a connection from uid %s', uid)
        return False
    return True


def _prepare_socket_path(path):
    """Make sure only the current user can reach the socket."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, mode=0o700, exist_ok=True)
    info = os.lstat(directory)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise RuntimeError(
            f'{directory} must be a directory you own with mode 0700'
        )
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError(f'{path} exists and is not a socket you own')
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe.connect(path)
    except OSError:
        os.unlink(path)  # Left behind by a fake that has stopped.
    else:
        raise RuntimeError(f'A daemon is already listening on {path}')
    finally:
        probe.close()


class _BackingProfile:
    """Real credentials from another profile, so commands can reach AWS."""

    def __init__(self, profile):
        import botocore.session

        self._profile = profile
        self._session = botocore.session.Session(profile=profile)
        self._lock = threading.Lock()

    def identity(self):
        try:
            sts = self._session.create_client('sts', region_name='us-east-1')
            response = sts.get_caller_identity()
        except Exception as e:
            raise DomainError('PROVIDER_UNAVAILABLE', str(e))
        return response['Arn'], response['Account']

    def credentials(self):
        with self._lock:
            try:
                credentials = self._session.get_credentials()
                frozen = credentials.get_frozen_credentials()
            except Exception as e:
                raise DomainError('PROVIDER_UNAVAILABLE', str(e))
        expiry = getattr(credentials, '_expiry_time', None)
        return frozen, expiry


class FakeCredentialDaemon(StoreMixin, SignInMixin, FaultsMixin):
    """An in-memory credential daemon on a Unix socket.

    Use it as a context manager in tests::

        with FakeCredentialDaemon() as fake:
            client = RawClient(fake.socket_path)

    ``signin='auto'`` completes each browser sign-in after
    ``signin_delay`` seconds. ``signin='manual'`` waits until
    ``complete_signin()`` or the ``mock/complete_signin`` call.
    """

    def __init__(
        self,
        socket_path=None,
        signin='auto',
        signin_delay=0.0,
        auth_timeout=300,
        credential_lifetime=900,
        iam_user_lifetime=3600,
        session_lifetime=90 * 24 * 3600,
        backing_profile=None,
        clock=None,
    ):
        if signin not in ('auto', 'manual'):
            raise ValueError(f'signin must be auto or manual, not {signin}')
        self._socket_path = socket_path
        self._signin = signin
        self._signin_delay = signin_delay
        self.auth_timeout = auth_timeout
        self._credential_lifetime = credential_lifetime
        self._iam_user_lifetime = iam_user_lifetime
        self._session_lifetime = session_lifetime
        self._backing = (
            _BackingProfile(backing_profile) if backing_profile else None
        )
        self._clock = clock or _utcnow
        self._lock = threading.RLock()
        self._stop_lock = threading.Lock()
        self._credentials = {}
        self._signins = {}
        self._failures = {}
        # Why the caller's configuration doesn't validate, while it doesn't
        # (set_config_invalid).
        self._config_errors = None
        # Approval requests for gated bootstraps: id -> [digest, approved].
        self._approvals = {}
        self.protocol_version = PROTOCOL_VERSION
        # What an SSO credential/logout reports SSO did (set_sso_logout).
        self._sso_logout = (SSO_LOGOUT_ENDED, _SESSION_END)
        self.next_principal = DEFAULT_PRINCIPAL
        self.iam_user_principal = DEFAULT_IAM_USER_PRINCIPAL
        self.roles = [dict(role) for role in DEFAULT_ROLES]
        # Every call, with secrets redacted, for tests to assert on.
        self.calls = []
        self._server = None
        self._thread = None
        self._owned_dir = None
        self._methods = {
            'system/health': self._health,
            'credential/list': self._list,
            'credential/get': self._get,
            'credential/import': self._import,
            'credential/logout': self._logout,
            'credential/remove': self._remove,
            'credential/tag': self._tag,
            'mock/state': self._mock_state,
            'mock/complete_signin': self._mock_complete_signin,
            'mock/set_principal': self._mock_set_principal,
            'mock/set_roles': self._mock_set_roles,
            'mock/seed': self._mock_seed,
            'mock/expire': self._mock_expire,
            'mock/fail': self._mock_fail,
            'mock/approve': self._mock_approve,
            'mock/reset': self._mock_reset,
        }

    @property
    def socket_path(self):
        return self._socket_path

    def start(self):
        if self._socket_path is None:
            # A short path: Unix socket paths are limited to ~100 bytes.
            self._owned_dir = tempfile.mkdtemp(
                prefix='credential-daemon-mock-'
            )
            self._socket_path = os.path.join(self._owned_dir, 'daemon.sock')
        else:
            _prepare_socket_path(self._socket_path)
        self._server = _UnixServer(self._socket_path, self)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={'poll_interval': 0.05},
            daemon=True,
        )
        self._thread.start()
        return self

    def serve_forever(self):
        """Serve until interrupted, starting the fake if needed."""
        if self._server is None:
            self.start()
        try:
            while self._thread.is_alive():
                self._thread.join(0.5)
        finally:
            self.stop()

    def stop(self):
        # serve_forever() stops the fake too, so stop() can run twice.
        with self._stop_lock:
            if self._server is None:
                return
            self._server.shutdown()
            for connection in list(self._server.connections):
                connection.close_connection()
            self._server.server_close()
            self._thread.join(5)
            self._server = None
            if os.path.lexists(self._socket_path):
                os.unlink(self._socket_path)
            if self._owned_dir is not None:
                shutil.rmtree(self._owned_dir, ignore_errors=True)
                self._owned_dir = None
                self._socket_path = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc_info):
        self.stop()

    # Python API for tests. The mock/* calls use the same methods.

    def reset(self):
        with self._lock:
            self._credentials.clear()
            self._failures.clear()
            self._config_errors = None
            self._approvals.clear()
            self._sso_logout = (SSO_LOGOUT_ENDED, _SESSION_END)
            self.next_principal = DEFAULT_PRINCIPAL
            self.roles = [dict(role) for role in DEFAULT_ROLES]
            self.calls.clear()

    def record(self, method, params):
        with self._lock:
            self.calls.append((method, _redact(params)))
        LOG.debug('%s %s', method, json.dumps(_redact(params)))

    # Protocol.

    def dispatch(self, method, params):
        handler = self._methods.get(method)
        if handler is None:
            raise RpcError(METHOD_NOT_FOUND, f'Method not found: {method}')
        self.record(method, params)
        self._raise_injected(method)
        if method in _PARAMS:
            _check_params(method, params)
        self._refuse_if_config_invalid(method)
        return handler(params)

    def _health(self, params):
        return {'protocol': self.protocol_version, 'version': VERSION}

    def _bootstrap_roles(self, params, provider, interaction):
        region = provider.get('region') or 'us-east-1'
        self._sign_in(None, region, provider, interaction)
        principal, _ = self._identity()
        user = principal.rsplit('/', 1)[-1]
        with self._lock:
            offered = {}
            for role in self.roles:
                role = dict(role, name=_role_name(role))
                existing = self._credentials.get(role['name'])
                role['configured'] = (
                    existing is not None and existing.kind == KIND_LOGIN
                )
                offered[(role['account_id'], role['role_name'])] = role
        interaction.notify(
            'select_role', roles=list(offered.values()), multiple=True
        )
        chosen = interaction.answer().get('roles')
        if not isinstance(chosen, list) or not chosen:
            raise DomainError('AUTH_CANCELLED', 'No roles were chosen')
        picks = []
        for pick in chosen:
            if not isinstance(pick, dict):
                raise InvalidParams('Each chosen role must be an object')
            role = offered.get((pick.get('account_id'), pick.get('role_name')))
            if role is None:
                raise InvalidParams(f'{pick} wasn\'t offered')
            name = pick.get('name') or role['name']
            _validate_name(name)
            picks.append((name, role))
        results = []
        with self._lock:
            for name, _ in picks:
                self._check_replace(name, KIND_LOGIN, params)
            for name, role in picks:
                role_principal = (
                    f'arn:aws:sts::{role["account_id"]}:assumed-role/'
                    f'{role["role_name"]}/{user}'
                )
                credential = self._store_session(
                    name,
                    KIND_LOGIN,
                    role_principal,
                    role['account_id'],
                    {'region': region, 'role_name': role['role_name']},
                    params,
                )
                results.append(
                    {
                        'name': name,
                        'principal': role_principal,
                        'account_id': role['account_id'],
                        'role_name': role['role_name'],
                        'expires_at': _iso(credential.session_expires_at),
                    }
                )
        return {'credentials': results}

    def _select_account_and_role(self, interaction):
        """Ask for one account and one of its roles, as the credential daemon
        does after calling ListAccounts and ListAccountRoles itself."""
        with self._lock:
            roles = [dict(role) for role in self.roles]
        accounts = {}
        for role in roles:
            accounts.setdefault(
                role['account_id'],
                {
                    'id': role['account_id'],
                    'name': role.get('account_name'),
                    'email': f'{role.get("account_name")}@example.com',
                },
            )
        interaction.notify('select_account', accounts=list(accounts.values()))
        account_id = interaction.answer().get('account_id')
        if account_id not in accounts:
            raise InvalidParams(f'Unknown account: {account_id}')
        names = [
            r['role_name'] for r in roles if r['account_id'] == account_id
        ]
        interaction.notify('select_role', roles=names)
        role_name = interaction.answer().get('role_name')
        if role_name not in names:
            raise InvalidParams(f'Unknown role: {role_name}')
        return {'account_id': account_id, 'role_name': role_name}

    def _now(self):
        return self._clock()

    # mock/* calls.

    def _mock_state(self, params):
        now = self._now()
        with self._lock:
            return {
                'credentials': [
                    credential.describe(now)
                    for _, credential in sorted(self._credentials.items())
                ],
                'next_principal': self.next_principal,
                'roles': self.roles,
                'waiting_signins': self.waiting_signins(),
            }

    def _mock_complete_signin(self, params):
        name = params.get('name')
        return {'completed': self.complete_signin(name)}

    def _mock_set_principal(self, params):
        principal = _require_str(params, 'principal')
        with self._lock:
            self.next_principal = principal
        return {'principal': principal}

    def _mock_set_roles(self, params):
        roles = params.get('roles')
        required = ('account_id', 'role_name')
        if not isinstance(roles, list) or not all(
            isinstance(role, dict) and all(k in role for k in required)
            for role in roles
        ):
            raise InvalidParams(
                'roles must be objects with account_id and ' 'role_name'
            )
        with self._lock:
            self.roles = [dict(role) for role in roles]
        return {'roles': self.roles}

    def _mock_seed(self, params):
        kwargs = {
            key: params[key]
            for key in (
                'kind',
                'principal',
                'status',
                'account_id',
                'mfa_serial',
                'tags',
            )
            if key in params
        }
        credential = self.seed(_require_name(params), **kwargs)
        return credential.describe(self._now())

    def _mock_expire(self, params):
        self.expire(_require_name(params))
        return {}

    def _mock_fail(self, params):
        method = _require_str(params, 'method')
        code = _require_str(params, 'code')
        count = params.get('count', 1)
        if not isinstance(count, int) or count < 1:
            raise InvalidParams('count must be a positive integer')
        self.fail_next(method, code, params.get('message'), count)
        return {}

    def _mock_approve(self, params):
        return {'request_id': self.approve(params.get('request_id'))}

    def _mock_reset(self, params):
        self.reset()
        return {}
