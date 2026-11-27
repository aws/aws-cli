# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The SEP's modeled provider test cases, run against the CLI's credential
chain.

``credential-daemon-provider-test-cases.json`` is copied unchanged from
the SEP's test cases. Replace the file to pick up a
newer SEP revision; ``test_the_copy_has_the_seps_59_cases`` counts every case, so one that
is added or dropped shows up. Tests of CLI behavior the SEP doesn't model
stay in ``test_provider.py``.

Each case gets its own short temporary root (sun_path is short): ``HOME``,
the config files, the link's targets and an ``env`` socket. Every socket is
a scripted daemon that records whether it was dialed and answers the case's
exchanges. The case resolves through the session's credential chain, with
the container and instance metadata providers replaced by the case's next
provider, AssumeRole stubbed, and the clock at the SEP's fixed "now".

As the SEP's notes on implementation say:

* ``appliesTo`` cases that don't list botocore (the JVM system property
  ones) are skipped.
* ``requiresCredentialRefresh`` cases run and are expected failures until
  the CLI adopts the Credential Refresh SEP: botocore refreshes expired
  credentials before use, and has no way to mark credentials rejected.
* After a failed credential/get the CLI also calls credential/list, to
  advise how to sign in again; that call is allowed after the case's one
  request.
* ``featureIds`` are compared as a set, as botocore records them. Without
  ``CREDENTIAL_DAEMON`` in the user agent's feature table, ``Aq`` isn't
  expected.
* Where the CLI's existing behavior differs from a case's outcome
  (``DIFFERENCES``), the case is an expected failure, with the reason.
"""

import contextlib
import datetime
import importlib.util
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

import botocore.credentials
import botocore.useragent
from botocore.context import get_context, start_as_current_context
from botocore.credentials import (
    CredentialProvider,
    Credentials,
    DeferredRefreshableCredentials,
    RefreshableCredentials,
)
from botocore.exceptions import (
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonError,
    CredentialDaemonNotRunningError,
    CredentialDaemonProtocolError,
    CredentialDaemonReauthRequiredError,
    CredentialDaemonRequestRejectedError,
    CredentialDaemonUnsupportedMaterialError,
    InvalidConfigError,
)
from botocore.session import Session

from awscli.testutils import skip_if_windows
from tests import mock

CASES = json.loads(
    (
        Path(__file__).parent / 'credential-daemon-provider-test-cases.json'
    ).read_text()
)
SDK = 'botocore'
# The SEP's fixed "now".
NOW = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
NEXT_SECRET = 'next-secret'
ASSUMED = {
    'AccessKeyId': 'ASIAASSUMED',
    'SecretAccessKey': 'assumed-secret',
    'SessionToken': 'assumed-token',
    'Expiration': NOW + datetime.timedelta(hours=1),
}
ERRORS = {
    'NOT_RUNNING': CredentialDaemonNotRunningError,
    'PROTOCOL_ERROR': CredentialDaemonProtocolError,
    'UNSUPPORTED_MATERIAL': CredentialDaemonUnsupportedMaterialError,
    'REAUTH_REQUIRED': CredentialDaemonReauthRequiredError,
    'CREDENTIAL_NOT_FOUND': CredentialDaemonCredentialNotFoundError,
    'REQUEST_REJECTED': CredentialDaemonRequestRejectedError,
    'INVALID_CONFIG': InvalidConfigError,
}
# Errors that carry the credential daemon's code, as in the SEP's Errors
# table. A request-rejected error keeps the daemon's own code.
CODES = {'REAUTH_REQUIRED', 'CREDENTIAL_NOT_FOUND', 'UNSUPPORTED_MATERIAL'}
PLATFORMS = {'linux': 'linux', 'macos': 'darwin'}
# What the CLI may send after a failed credential/get, for its advice.
ADVICE_METHODS = {'credential/list'}
# Cases where the CLI's existing behavior and the SEP's expected outcome
# differ. The CLI isn't changed for them; each is an open question for the
# SEP.
DIFFERENCES = {
    'source-profile': (
        'botocore also records CREDENTIALS_PROFILE (n) for every '
        'source_profile it resolves (upstream #9751), so the request '
        'carries n, o, Aq and i; the SEP lists o, Aq and i'
    ),
}


def reports_the_daemon_feature_id():
    mappings = getattr(botocore.useragent, '_USERAGENT_FEATURE_MAPPINGS', {})
    return 'CREDENTIAL_DAEMON' in mappings


def reply_line(reply, request):
    if isinstance(reply, str):
        return reply.encode('utf-8')
    reply = dict(reply)
    if reply.get('id') == '$id':
        reply['id'] = request['id']
    pad_to = reply.pop('$padTo', None)
    if pad_to is None:
        return json.dumps(reply).encode('utf-8')
    reply['result'] = dict(reply['result'], padding='')
    line = json.dumps(reply).encode('utf-8')
    reply['result']['padding'] = 'x' * (pad_to - len(line))
    line = json.dumps(reply).encode('utf-8')
    assert len(line) == pad_to
    return line


class ScriptedDaemon:
    """Listens on ``path``, notes each connection, and answers each request
    with the next exchange's reply lines; with none left, it hangs up."""

    def __init__(self, path, exchanges=()):
        self.path = str(path)
        self.dialed = threading.Event()
        self.requests = []
        self._exchanges = list(exchanges)
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.path)
        self._server.listen(4)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while True:
            try:
                connection, _ = self._server.accept()
            except OSError:
                return
            self.dialed.set()
            with connection, connection.makefile('rb') as reader:
                line = reader.readline()
                if not line:
                    continue
                request = json.loads(line)
                self.requests.append(request)
                if not self._exchanges:
                    continue
                exchange = self._exchanges.pop(0)
                for reply in exchange.get('replyLines', []):
                    connection.sendall(reply_line(reply, request) + b'\n')

    def was_dialed(self):
        # A connect lands in the backlog before accept() runs, so wait a
        # little for the thread, and look at the backlog too.
        if self.dialed.wait(0.2):
            return True
        self._server.setblocking(False)
        try:
            self._server.accept()[0].close()
        except (BlockingIOError, OSError):
            return False
        return True

    def close(self):
        try:
            self._server.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._server.close()
        self._thread.join(5)


def stale_socket(path):
    # A socket file nothing listens on.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(path))
    sock.close()


class NextProvider(CredentialProvider):
    """The case's next provider in the chain, in place of the container
    and instance metadata providers."""

    METHOD = 'sep-next-provider'

    def __init__(self, access_key):
        super().__init__()
        self.access_key = access_key
        self.called = False

    def load(self):
        self.called = True
        return Credentials(self.access_key, NEXT_SECRET, method=self.METHOD)


class Case:
    def __init__(self, case, root, monkeypatch):
        self.case = case
        self.root = root
        self.daemons = {}
        self._monkeypatch = monkeypatch
        try:
            self._set_up()
        except BaseException:
            # Close the daemons already started.
            self.close()
            raise

    def _set_up(self):
        case = self.case
        root = self.root
        monkeypatch = self._monkeypatch
        daemon = case.get('daemon', {})
        exchanges = daemon.get('exchanges', [])
        environment = case.get('environment', {})
        unset = case.get('unsetEnvironment', [])
        home = root / 'home'
        cwd = root / 'cwd'
        cwd.mkdir(mode=0o700)
        monkeypatch.chdir(cwd)
        relative_home = environment.get('HOME') == 'relative'
        if 'HOME' in unset:
            monkeypatch.delenv('HOME', raising=False)
            # The link would be here if HOME counted.
            home = cwd
        elif relative_home:
            monkeypatch.setenv('HOME', 'relative')
            home = cwd / 'relative'
        else:
            monkeypatch.setenv('HOME', str(home))
        home.mkdir(exist_ok=True)
        aws = home / '.aws'
        aws.mkdir(mode=0o700)
        link = aws / 'credential-daemon.sock'
        if 'HOME' in unset or relative_home:
            # Under the cwd too, for a lookup that resolves against it.
            (cwd / '.aws').mkdir(mode=0o700, exist_ok=True)
        targets = root / 'daemon'
        targets.mkdir(mode=0o700)
        env_dir = root / 'env'
        env_dir.mkdir(mode=0o700)
        env_path = env_dir / 'env.sock'
        relative_env = (
            environment.get('AWS_CREDENTIAL_DAEMON_SOCKET') == 'relative'
        )
        for name in daemon.get('sockets', []):
            if name == 'link':
                target = targets / 'link.sock'
                self._listen('link', target, exchanges)
                link.symlink_to(target)
                if 'HOME' in unset or relative_home:
                    other = cwd / '.aws' / 'credential-daemon.sock'
                    if not os.path.lexists(other):
                        other.symlink_to(target)
            elif name == 'link-stale':
                target = targets / 'stale.sock'
                stale_socket(target)
                link.symlink_to(target)
            elif name == 'link-dangling':
                link.symlink_to(root / 'gone' / 'missing-daemon.sock')
            elif name == 'home-socket':
                self._listen('home-socket', link, exchanges)
            elif name == 'env':
                if relative_env:
                    # Created at the relative path under the cwd, below.
                    continue
                self._listen('env', env_path, exchanges)
            elif name == 'env-file':
                env_path.touch()
            elif name == 'sysprop':
                # A JVM system property; only JVM SDKs run these cases.
                continue
            else:
                raise AssertionError(f'unknown socket {name}')
        config = root / 'config'
        config.write_text(case['configContents'])
        credentials = root / 'credentials'
        credentials.write_text(case.get('credentialsContents', ''))
        monkeypatch.setenv('AWS_CONFIG_FILE', str(config))
        monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials))
        monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')
        monkeypatch.setenv('AWS_PROFILE', case['profile'])
        for key, value in environment.items():
            if key == 'HOME':
                continue
            if key == 'AWS_CREDENTIAL_DAEMON_SOCKET':
                if value == 'env':
                    value = str(env_path)
                elif value == 'relative':
                    relative = Path('env.sock')
                    self._listen('env', cwd / relative, exchanges)
                    value = str(relative)
            monkeypatch.setenv(key, value)

    def _listen(self, role, path, exchanges):
        self.daemons[role] = ScriptedDaemon(path, exchanges)

    def dialed(self):
        return sorted(
            role
            for role, daemon in self.daemons.items()
            if daemon.was_dialed()
        )

    def close(self):
        for daemon in self.daemons.values():
            daemon.close()


@pytest.fixture
def short_root():
    # sun_path is 104 bytes on macOS and 108 on Linux; pytest's tmp_path
    # can pass it.
    with tempfile.TemporaryDirectory(dir='/tmp', prefix='sp') as root:
        os.chmod(root, 0o700)
        yield Path(os.path.realpath(root))


def _frozen_now():
    return NOW


@contextlib.contextmanager
def frozen_clock():
    """Every credential's clock at the SEP's fixed "now"."""

    def frozen(function):
        return tuple(
            _frozen_now if value is botocore.credentials._local_now else value
            for value in function.__defaults__
        )

    with contextlib.ExitStack() as stack:
        for cls in (RefreshableCredentials, DeferredRefreshableCredentials):
            stack.enter_context(
                mock.patch.object(
                    cls.__init__, '__defaults__', frozen(cls.__init__)
                )
            )
        stack.enter_context(
            mock.patch.object(botocore.credentials, '_local_now', _frozen_now)
        )
        yield


class Resolution:
    """Resolves the case's profile through the session's chain."""

    def __init__(self, case):
        self.case = case
        self.next_provider = NextProvider(
            case.get('nextProvider', {}).get('accessKeyId', 'AKIDNEXT')
        )
        self.assume_role_clients = []
        self.features = set()

    def _assume_role_client(self, service_name, **kwargs):
        client = mock.Mock()
        client.assume_role.return_value = {
            'Credentials': dict(ASSUMED),
            'AssumedRoleUser': {
                'Arn': 'arn:aws:sts::123456789012:assumed-role/Admin/x'
            },
        }
        self.assume_role_clients.append(kwargs)
        return client

    def resolve(self):
        session = Session()
        resolver = session.get_component('credential_provider')
        for name in ('container-role', 'iam-role'):
            resolver.remove(name)
        resolver.providers.append(self.next_provider)
        resolver.get_provider(
            'assume-role'
        )._client_creator = self._assume_role_client
        platform = PLATFORMS[self.case['platform']]
        emulated = not sys.platform.startswith(platform)
        with contextlib.ExitStack() as stack:
            stack.enter_context(frozen_clock())
            stack.enter_context(start_as_current_context())
            stack.enter_context(mock.patch('sys.platform', platform))
            if emulated and _has_module('botocore.credential_daemon.trust'):
                # The emulated platform can't read this one's peer uid; the
                # scripted daemon runs in this process, as the caller.
                stack.enter_context(
                    mock.patch(
                        'botocore.credential_daemon.trust._peer_uid',
                        return_value=os.geteuid(),
                    )
                )
            try:
                credentials = session.get_credentials()
                frozen = (
                    None
                    if credentials is None
                    else credentials.get_frozen_credentials()
                )
            finally:
                self.features = set(get_context().features)
        return credentials, frozen


def _has_module(name):
    return importlib.util.find_spec(name) is not None


def invalidate(*_):
    # The Credential Refresh SEP's invalidation: botocore has no way to
    # mark credentials a service rejected.
    raise NotImplementedError(
        'botocore has no credential invalidation until the Credential '
        'Refresh SEP'
    )


def _marks(case):
    applies_to = case.get('appliesTo')
    if applies_to is not None and SDK not in applies_to:
        return [
            pytest.mark.skip(
                reason=f"Only {', '.join(applies_to)} run this case"
            )
        ]
    if case['id'] in DIFFERENCES:
        return [pytest.mark.xfail(strict=True, reason=DIFFERENCES[case['id']])]
    if case.get('requiresCredentialRefresh'):
        return [
            pytest.mark.xfail(
                strict=True,
                reason='Needs the Credential Refresh SEP, which the CLI '
                "hasn't adopted",
            )
        ]
    return []


@skip_if_windows('The credential daemon socket is for Linux and macOS.')
@pytest.mark.parametrize(
    'case',
    [pytest.param(c, id=c['id'], marks=_marks(c)) for c in CASES],
)
def test_sep_provider_case(case, short_root, monkeypatch):
    setup = Case(case, short_root, monkeypatch)
    try:
        _check(case, setup)
    finally:
        setup.close()


def _check(case, setup):
    outcome = case['outcome']
    resolution = Resolution(case)
    if outcome['result'] == 'error':
        with pytest.raises(Exception) as e:
            credentials, _ = resolution.resolve()
            if 'invalidatedAccessKeyId' in case:
                invalidate(credentials, case['invalidatedAccessKeyId'])
        _check_error(outcome, e.value)
        if outcome.get('terminal'):
            assert not resolution.next_provider.called
    else:
        credentials, frozen = resolution.resolve()
        if 'invalidatedAccessKeyId' in case:
            invalidate(credentials, case['invalidatedAccessKeyId'])
        _check_credentials(case, resolution, credentials, frozen)
    _check_requests(case, setup)
    _check_dialed(outcome, setup)


def _check_error(outcome, error):
    code = outcome.get('errorCode')
    kind = outcome.get('errorKind')
    if code is not None:
        assert isinstance(error, ERRORS[code]), repr(error)
        if code in CODES:
            assert error.code == code
    elif kind == 'ssoConfig':
        assert isinstance(error, InvalidConfigError), repr(error)
    else:
        assert isinstance(error, CredentialDaemonError), repr(error)
    message = str(error)
    for text in outcome.get('messageContains', []):
        assert text in message
    for text in outcome.get('messageNotContains', []):
        assert text not in message


def _check_credentials(case, resolution, credentials, frozen):
    outcome = case['outcome']
    source = outcome['source']
    if outcome['result'] == 'notResolved' or source == 'nextProvider':
        assert resolution.next_provider.called
        assert frozen.access_key == resolution.next_provider.access_key
    elif source == 'environment':
        assert frozen.access_key == outcome['accessKeyId']
    elif source == 'assumeRole':
        assert frozen.access_key == ASSUMED['AccessKeyId']
        assert len(resolution.assume_role_clients) == 1
    else:
        assert source == 'daemon'
        assert frozen.access_key == outcome['accessKeyId']
        if 'secretAccessKey' in outcome:
            assert frozen.secret_key == outcome['secretAccessKey']
        if 'sessionToken' in outcome:
            assert frozen.token == outcome['sessionToken']
        if 'expiresAt' in outcome:
            assert credentials._expiry_time == _time(outcome['expiresAt'])
        if 'accountId' in outcome:
            assert frozen.account_id == outcome['accountId']
    if source == 'assumeRole' and outcome['dialed'] != 'none':
        # The role was assumed with the daemon's credentials.
        daemon_key = _daemon_access_key(case)
        assert (
            resolution.assume_role_clients[0]['aws_access_key_id']
            == daemon_key
        )
    if source != 'nextProvider':
        assert not resolution.next_provider.called
    if 'featureIds' in outcome:
        expected = set(outcome['featureIds'])
        if not reports_the_daemon_feature_id():
            expected.discard('Aq')
        assert resolution.features == expected


def _daemon_access_key(case):
    reply = case['daemon']['exchanges'][0]['replyLines'][0]
    return reply['result']['material']['access_key_id']


def _time(value):
    return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))


def _check_requests(case, setup):
    # Each exchange's request, exactly, then only the CLI's advice calls.
    exchanges = case.get('daemon', {}).get('exchanges', [])
    requests = [
        request
        for daemon in setup.daemons.values()
        for request in daemon.requests
    ]
    expected = [
        (e['expectedRequest']['method'], e['expectedRequest'].get('params'))
        for e in exchanges
    ]
    sent = [(r['method'], r.get('params')) for r in requests]
    assert sent[: len(expected)] == expected
    assert {method for method, _ in sent[len(expected) :]} <= ADVICE_METHODS


def _check_dialed(outcome, setup):
    dialed = setup.dialed()
    if outcome['dialed'] == 'none':
        assert dialed == []
    elif outcome['dialed'] in setup.daemons:
        # Only that socket: no other location is tried.
        assert dialed == [outcome['dialed']]
    else:
        # A stale or missing target: nothing else was dialed.
        assert dialed == []


def test_the_copy_has_the_seps_59_cases():
    # The SEP has 59 cases at the copied commit. A case added to or
    # dropped from the copy shows up here.
    assert len(CASES) == 59
    assert len({c['id'] for c in CASES}) == len(CASES)
