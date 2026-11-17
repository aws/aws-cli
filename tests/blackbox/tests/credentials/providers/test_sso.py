import asyncio
import hashlib
import json
import os
import re
import shlex
import socket
import sys
import urllib.request
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    CloseConnection,
    HTTPResponse,
    RecordedHTTPRequest,
)

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    CREATED_DIRECTORY_MODE,
    SCOPE_DATE_PLACEHOLDER,
    SSO_TOKEN_CACHE,
    BytesStartingWith,
    CliRun,
    FileChanges,
    JsonContent,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    TreeEntry,
    assert_credential_error,
    assert_signature,
    cache_tree_normalizer,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    kill_process_group,
    list_bucket,
    oidc_token,
    os_error_path,
    route_key,
    routed,
    run_export_credentials,
    seed_cli_cache,
    sso_role_cache_key,
    sso_role_credentials,
    sts_success_xml,
    write_config,
    write_sso_token,
)
from harness_plugin import child_environment
from tests.blackbox.utils import empty_list_objects_response

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# botocore's SSOProvider (credentials.py:2362-2495) and SSOCredentialFetcher
# (credentials.py:2259-2359) behind the CLI's role-cache injection
# (customizations/sso/__init__.py:38-44), SSOTokenProvider and
# DeferredRefreshableToken (tokens.py:68-163, 180-337), and SSOTokenLoader
# (utils.py:3803-3834), through `aws configure export-credentials`.
#
# The SSO and SSO-OIDC endpoints are configured `.invalid` hosts that only
# the TLS intercept proxy can reach, so a run that ignored HTTPS_PROXY
# connects nowhere. The endpoint-resolution rows use the default hosts,
# also through the proxy. The refused and stalled connection tests need an
# endpoint that refuses or stalls a connection, which the intercept proxy
# (it accepts every CONNECT) cannot do: they use plain-HTTP loopback
# endpoints reached directly through NO_PROXY.
EnvChanges = Mapping[str, str | None]
Script = Mapping[RouteKey, Sequence[HTTPResponse]]
TokenValue = str | int | timedelta | None
# What a failed run prints on stderr: a message in the enhanced framing,
# or a matcher for one whose text is CPython's.
Stderr = str | BytesStartingWith
# (method, path, sorted query, media type, decoded body, compared headers,
# SigV4 scope) of one request; the label names its host.
RequestShape = tuple[
    str,
    str,
    tuple[tuple[str, str], ...],
    str | None,
    object,
    dict[str, str | None],
    tuple[str, ...] | None,
]

ACCOUNT: Final = "123456789012"
ROLE: Final = "EdgeRole"
SESSION: Final = "edge-session"
START_URL: Final = "https://edge.invalid/start"
SSO_REGION: Final = "us-west-2"
SSO_ENDPOINT: Final = "https://portal.sso.stub.invalid"
OIDC_ENDPOINT: Final = "https://oidc.stub.invalid"
SSO_HOST: Final = "portal.sso.stub.invalid"
OIDC_HOST: Final = "oidc.stub.invalid"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
ROLE_PATH: Final = "/federation/credentials"
TOKEN_PATH: Final = "/token"
REGISTER_PATH: Final = "/client/register"
# GetRoleCredentials sends both as query parameters, percent-encoded
# with `-._~` safe (credentials.py:2337-2341, utils.py:93, 720-785).
ROLE_QUERY: Final = f"role_name={ROLE}&account_id={ACCOUNT}"
TARGET_ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/Target"
# sha1("edge-session") (utils.py:3809-3813) and the SSO role-cache key,
# sha1 of the compact sorted JSON (credentials.py:2287-2307). Literal so a
# helper bug cannot hide a wrong path.
TOKEN_FILE: Final = (
    f"home/{SSO_TOKEN_CACHE.as_posix()}/"
    "a483adfd3cb49ca97baef484511cd4c03fb6545a.json"
)
CLI_DIR: Final = "home/.aws/cli"
CLI_CACHE_DIR: Final = f"home/{CLI_CACHE.as_posix()}"
ROLE_CACHE_FILE: Final = (
    f"{CLI_CACHE_DIR}/78035f50172e518999a69d81e78b663f10195ba6.json"
)
# The assume-role cache key of the target profile (credentials.py:
# 830-850).
AR_CACHE_FILE: Final = (
    f"{CLI_CACHE_DIR}/3bee88f7a80f1110ed5131fc1f66b74e83a0bc95.json"
)
FUTURE: Final = "2099-01-01T00:00:00+00:00"
FUTURE_Z: Final = "2099-01-01T00:00:00Z"
UTC_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
TOKEN_TIME: Final = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
# Remaining lifetimes of a seeded token. A token inside the refresh window
# behaves the same for any remaining time in (0, 900) s; 12 minutes keeps
# 120 s from the 600 s boundary and 180 s from the 900 s refresh window,
# so a refresh here shows the window is 900 s, not 600 s. 14 and 16
# minutes sit 60 s either side of the 900 s windows (tokens.py:182, 318;
# credentials.py:720, 785-789).
INSIDE_WINDOW: Final = timedelta(minutes=12)
EXPIRED: Final = timedelta(minutes=-5)
FRESH: Final = timedelta(minutes=60)
SIXTEEN_MINUTES: Final = timedelta(minutes=16)
FOURTEEN_MINUTES: Final = timedelta(minutes=14)
# A legacy token has no refresh window: it is used until it expires
# (credentials.py:2325-2335).
LEGACY_NEAR_EXPIRY: Final = timedelta(minutes=3)
REGISTRATION_LIFETIME: Final = timedelta(days=90)
REGISTRATION_EXPIRED: Final = timedelta(days=-1)
REFRESH_EXPIRES_IN: Final = 3600
READ_ONLY_MODE: Final = 0o400
SHARED_MODE: Final = 0o644
CLIENT_ERROR_RC: Final = 254
CONFIGURATION_RC: Final = 253
GENERAL_RC: Final = 255
# A stalled connection outlasts the attempt without a byte of response.
STALL_SECONDS: Final = 60.0
READ_TIMEOUT_GLOBALS: Final = ("--cli-read-timeout", "1")
# The refused endpoint's port: outside the ephemeral ranges bind(0) draws
# from (49152-65535 on macOS and Windows, 32768-60999 on Linux).
REFUSED_PORT: Final = 1
REFUSAL_CHECK_SECONDS: Final = 1.0
needs_permission_checks = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores file modes",
)
# The SSO and SSO-OIDC clients are UNSIGNED (credentials.py:2315-2320,
# tokens.py:254-260) and send JSON bodies (serialize.py:1047-1056); the
# AssumeRole call is a SigV4-signed form POST (serialize.py:232).
JSON_CONTENT_TYPE: Final = "application/json"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded"
SIGV4_ALGORITHM: Final = "AWS4-HMAC-SHA256"
# The framing of an error raised unwrapped during the deferred fetch.
ERROR_PREFIX: Final = b"\naws: [ERROR]: "

TOKEN_EXPIRED: Final = (
    "Error when retrieving token from sso: Token has expired and refresh "
    "failed"
)
UNAUTHORIZED: Final = (
    "The SSO session associated with this profile has expired or is "
    "otherwise invalid. To refresh this SSO session run aws sso login with "
    "the corresponding profile."
)
LOAD_PREFIX: Final = (
    "An error occurred (Configuration): Unable to retrieve credentials: "
)
NO_TOKEN: Final = (
    f"Error loading SSO Token: Token for {SESSION} does not exist"
)
INVALID_TOKEN: Final = (
    f"Error loading SSO Token: Token for {START_URL} is invalid"
)
STILL_EXPIRED: Final = (
    "Credentials were refreshed, but the refreshed credentials are still "
    "expired."
)

PROFILE_EDGE: Final = f"""\
[profile edge]
sso_session = {SESSION}
sso_account_id = {ACCOUNT}
sso_role_name = {ROLE}
"""
SESSION_SECTION: Final = f"""
[sso-session {SESSION}]
sso_start_url = {START_URL}
sso_region = {SSO_REGION}
"""
# An sso-session profile and its session.
SSO_CONFIG: Final = PROFILE_EDGE + SESSION_SECTION
# The profile also carries both session keys.
PROFILE_WITH_SESSION_KEYS: Final = (
    PROFILE_EDGE + f"sso_start_url = {START_URL}\nsso_region = {SSO_REGION}\n"
)
LEGACY_CONFIG: Final = f"""\
[profile edge]
sso_start_url = {START_URL}
sso_region = {SSO_REGION}
sso_account_id = {ACCOUNT}
sso_role_name = {ROLE}
"""
TARGET_PROFILE: Final = f"""
[profile target]
role_arn = {TARGET_ROLE_ARN}
source_profile = edge
role_session_name = sess
region = us-east-1
"""
# An assume-role profile whose source profile is the SSO one.
AR_CONFIG: Final = SSO_CONFIG + TARGET_PROFILE

ROLE_CACHE_DOCUMENT: Final = {
    "ProviderType": "sso",
    "Credentials": {
        "AccessKeyId": "AKIDSSO",
        "SecretAccessKey": "SSOSECRET",
        "SessionToken": "SSOTOKEN",
        "Expiration": FUTURE_Z,
        "AccountId": ACCOUNT,
    },
}
ROLE_CACHE: Final = RoleCacheContent(ROLE_CACHE_DOCUMENT)
OUT_SSO: Final = export_credentials_output(
    "AKIDSSO", "SSOSECRET", "SSOTOKEN", FUTURE
)
OUT_ROLE: Final = export_credentials_output(
    "AKIDROLE", "ROLESECRET", "ROLETOKEN", FUTURE
)
# The CreateToken refresh of the seeded token (tokens.py:262-268).
REFRESH_BODY: Final[Mapping[str, object]] = {
    "grantType": "refresh_token",
    "clientId": "CID",
    "clientSecret": "CSECRET",
    "refreshToken": "OLD-REFRESH",
}
ASSUME_ROLE_BODY: Final[Mapping[str, list[str]]] = {
    "Action": ["AssumeRole"],
    "Version": ["2011-06-15"],
    "RoleSessionName": ["sess"],
    "RoleArn": [TARGET_ROLE_ARN],
}
# The assume-role cache entry for STS_OK: its credentials with the account
# id taken from the assumed role's ARN (credentials.py:746-758, 852-857).
AR_CACHE: Final = RoleCacheContent(
    {
        "Credentials": {
            "AccessKeyId": "AKIDROLE",
            "SecretAccessKey": "ROLESECRET",
            "SessionToken": "ROLETOKEN",
            "Expiration": FUTURE,
            "AccountId": ACCOUNT,
        }
    }
)

SSO_OK: Final = sso_role_credentials()
OIDC_OK: Final = oidc_token()
STS_OK: Final = sts_success_xml(
    access_key="AKIDROLE",
    secret_key="ROLESECRET",
    session_token="ROLETOKEN",
    assumed_role_id="AROAEXAMPLE:sess",
    arn=f"arn:aws:sts::{ACCOUNT}:assumed-role/Target/sess",
    request_id="req-1",
)
# A CreateToken server error.
OIDC_500: Final = HTTPResponse.json(
    {"error": "server_error", "error_description": "boom"},
    status=500,
    headers={"x-amzn-errortype": "InternalServerException"},
)
# A CreateToken rejection of the refresh token.
OIDC_INVALID_GRANT: Final = HTTPResponse.json(
    {
        "error": "invalid_grant",
        "error_description": "Invalid refresh token provided",
    },
    status=400,
    headers={
        "x-amzn-errortype": (
            "InvalidGrantException:"
            "http://internal.amazon.com/coral/com.amazonaws.ssooidc/"
        )
    },
)
# CreateToken successes that lack or zero a field.
OIDC_NO_REFRESH_TOKEN: Final = oidc_token(refresh_token=None)
OIDC_EXPIRES_NOW: Final = oidc_token(expires_in=0)
OIDC_NO_EXPIRES_IN: Final = HTTPResponse.json(
    {
        "accessToken": "NEW-ACCESS",
        "tokenType": "Bearer",
        "refreshToken": "NEW-REFRESH",
    }
)


def error_output(message: str) -> bytes:
    """The enhanced framing's stderr for `message` (errorhandler.py)."""
    return f"\naws: [ERROR]: {message}\n".encode()


def framed_error(*parts: bytes) -> BytesStartingWith:
    """An unwrapped error whose text after the framing is CPython's.

    A KeyError's repr, an OSError's `[Errno N] ...`, a datetime
    TypeError: only the framing and each of `parts` are asserted.
    """
    return BytesStartingWith(ERROR_PREFIX, parts)


def client_error(
    code: str, message: str, *, retries: int | None = None
) -> str:
    """A GetRoleCredentials ClientError as the enhanced handler prints it.

    ` (reached max retries: N)` appears once MaxAttemptsReached is set
    (exceptions.py:529-538).
    """
    suffix = "" if retries is None else f" (reached max retries: {retries})"
    return (
        f"An error occurred ({code}) when calling the GetRoleCredentials "
        f"operation{suffix}: {message}"
    )


def role_error(
    status: int, message: str, error_type: str | None = None
) -> HTTPResponse:
    """A GetRoleCredentials error with `message` in its JSON body."""
    headers = {} if error_type is None else {"x-amzn-errortype": error_type}
    return HTTPResponse.json(
        {"message": message}, status=status, headers=headers
    )


def role_response(**credentials: object) -> HTTPResponse:
    """A GetRoleCredentials body with `credentials` replaced."""
    document: dict[str, object] = {
        "accessKeyId": "AKIDSSO",
        "secretAccessKey": "SSOSECRET",
        "sessionToken": "SSOTOKEN",
        "expiration": 4070908800000,
    }
    document.update(credentials)
    return HTTPResponse.json({"roleCredentials": document})


def utc_text(moment: datetime) -> str:
    return moment.strftime(UTC_FORMAT)


def exported_at(moment: datetime, identity: str = "SSO") -> bytes:
    """Export output for credentials expiring at `moment` (seconds kept)."""
    return export_credentials_output(
        f"AKID{identity}",
        f"{identity}SECRET",
        f"{identity}TOKEN",
        moment.replace(microsecond=0).isoformat(),
    )


@dataclass(frozen=True)
class Token:
    """A seeded sso-session token with `remaining` lifetime left.

    `changes` replaces fields: a timedelta becomes `now + delta` in the
    token's own format, None drops the key, anything else is written as
    is (extra keys are appended).
    """

    remaining: timedelta
    changes: Mapping[str, TokenValue] = field(default_factory=dict)

    def document(self) -> dict[str, object]:
        now = datetime.now(UTC)
        document: dict[str, object] = {
            "startUrl": START_URL,
            "region": SSO_REGION,
            "accessToken": "OLD-ACCESS",
            "expiresAt": utc_text(now + self.remaining),
            "clientId": "CID",
            "clientSecret": "CSECRET",
            "registrationExpiresAt": utc_text(now + REGISTRATION_LIFETIME),
            "refreshToken": "OLD-REFRESH",
        }
        for key, value in self.changes.items():
            if value is None:
                document.pop(key, None)
            elif isinstance(value, timedelta):
                document[key] = utc_text(now + value)
            else:
                document[key] = value
        return document


def seed_token(
    sandbox: Sandbox,
    token: Token,
    *,
    key: str = SESSION,
    mode: int = CACHE_FILE_MODE,
) -> dict[str, object]:
    """Write `token` as botocore's token cache would hold it."""
    document = token.document()
    write_sso_token(sandbox.home, key, mode=mode, **document)
    return document


def seed_role_cache(sandbox: Sandbox, expiration: str = FUTURE_Z) -> None:
    """Seed the SSO role cache with AKIDCACHED credentials."""
    document = {
        "ProviderType": "sso",
        "Credentials": {
            "AccessKeyId": "AKIDCACHED",
            "SecretAccessKey": "CACHEDSECRET",
            "SessionToken": "CACHEDTOKEN",
            "Expiration": expiration,
            "AccountId": ACCOUNT,
        },
    }
    seed_cli_cache(sandbox.home, Path(ROLE_CACHE_FILE).stem, document)


def refreshed_token(
    seeded: Mapping[str, object],
    *,
    refresh_token: str | None = "NEW-REFRESH",
    expires_in: int = REFRESH_EXPIRES_IN,
    region: str = SSO_REGION,
) -> JsonContent:
    """The written-back token after normalization (tokens.py:262-283).

    startUrl and region come from the sso-session config, the
    registration is copied verbatim, every other old key is dropped, and
    refreshToken appears only when the response had one. `expiresAt` is
    the normalizer's placeholder for `now + expires_in`.
    """
    document: dict[str, object] = {
        "startUrl": START_URL,
        "region": region,
        "accessToken": "NEW-ACCESS",
        "expiresAt": f"<now+{expires_in}s>",
        "clientId": seeded["clientId"],
        "clientSecret": seeded["clientSecret"],
        "registrationExpiresAt": seeded["registrationExpiresAt"],
    }
    if refresh_token is not None:
        document["refreshToken"] = refresh_token
    return JsonContent(document)


@dataclass(frozen=True)
class Hosts:
    """Where one scenario's SSO, SSO-OIDC, and STS calls go."""

    sso: str = SSO_HOST
    oidc: str = OIDC_HOST
    sts: str = STS_HOST
    sso_path: str = ROLE_PATH
    oidc_path: str = TOKEN_PATH

    def label(self, request: NormalizedRequest) -> str:
        """`sso(<bearer token>)`, `oidc`, `sts`, or the request line.

        A call is named by Host and path, so one host may serve several.
        """
        route = (request.host, request.path)
        if route == (self.sso, self.sso_path):
            bearer = dict(request.headers)["x-amz-sso_bearer_token"]
            return f"sso({bearer})"
        if route == (self.oidc, self.oidc_path):
            return "oidc"
        if route == (self.sts, "/"):
            return "sts"
        return f"{request.method} {request.host} {request.target}"

    def script(
        self,
        *,
        oidc: Sequence[HTTPResponse] = (),
        sso: Sequence[HTTPResponse] = (),
        sts: Sequence[HTTPResponse] = (),
    ) -> dict[RouteKey, list[HTTPResponse]]:
        return {
            ("POST", self.oidc, self.oidc_path): list(oidc),
            ("GET", self.sso, self.sso_path): list(sso),
            ("POST", self.sts, "/"): list(sts),
        }


PROXIED: Final = Hosts()
DEFAULT_HOSTS: Final = Hosts(
    sso="portal.sso.us-west-2.amazonaws.com",
    oidc="oidc.us-west-2.amazonaws.com",
)
NO_CONFIGURED_ENDPOINTS: Final[EnvChanges] = {
    "AWS_ENDPOINT_URL_SSO": None,
    "AWS_ENDPOINT_URL_SSO_OIDC": None,
}


@pytest_asyncio.fixture
async def recorder() -> AsyncIterator[AsyncHTTPTestServer]:
    """A plain-HTTP SSO-OIDC endpoint on loopback, reached directly."""
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(OIDC_OK)
        yield server


@pytest.fixture
def refused_endpoint() -> str:
    """A loopback URL whose port refuses connections, checked here.

    A bound but non-listening socket does not refuse on macOS (the SYN is
    dropped and the connect times out), and a released ephemeral port
    could be handed to another xdist worker's server before the run.
    REFUSED_PORT lies below every ephemeral range and nothing in the suite
    binds a fixed port, so it keeps refusing.
    """
    address = ("127.0.0.1", REFUSED_PORT)
    try:
        with socket.create_connection(address, timeout=REFUSAL_CHECK_SECONDS):
            pass
    except ConnectionRefusedError:
        return f"http://127.0.0.1:{REFUSED_PORT}"
    except OSError as error:
        pytest.skip(f"127.0.0.1:{REFUSED_PORT} does not refuse: {error}")
    pytest.skip(f"something listens on 127.0.0.1:{REFUSED_PORT}")


def apply_env(env: dict[str, str], changes: EnvChanges) -> None:
    for key, value in changes.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value


def sso_env(
    sandbox: Sandbox,
    stub: Stub,
    *,
    max_attempts: str | None = "1",
    env: EnvChanges | None = None,
) -> dict[str, str]:
    """The sandbox env with the proxied SSO and SSO-OIDC endpoints."""
    _, proxy = stub
    run_env = sandbox.env(proxy, max_attempts=max_attempts)
    run_env.update(
        AWS_ENDPOINT_URL_SSO=SSO_ENDPOINT,
        AWS_ENDPOINT_URL_SSO_OIDC=OIDC_ENDPOINT,
    )
    apply_env(run_env, env or {})
    return run_env


async def run_sso(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Script | None = None,
    *,
    profile: str = "edge",
    env: EnvChanges | None = None,
    max_attempts: str | None = "1",
    globals_: Sequence[str] = (),
    extra_servers: Sequence[AsyncHTTPTestServer] = (),
) -> CliRun:
    """Run export-credentials once; the proxied stub is routed.

    The SSO and SSO-OIDC endpoints are the configured proxied hosts
    unless `env` changes them. Unscripted requests get the 400 tripwire.
    """
    server, _ = stub
    routes = dict(script or {})
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server, *extra_servers],
        sso_env(sandbox, stub, max_attempts=max_attempts, env=env),
        globals_=("--profile", profile, *globals_),
        handlers={server: lambda: routed(routes)},
    )


def sent_headers(values: Mapping[str, str]) -> dict[str, str | None]:
    """Every compared header: absent (None) unless named in `values`."""
    return {**dict.fromkeys(COMPARED_HEADERS), **values}


def request_shape(request: NormalizedRequest) -> RequestShape:
    return (
        request.method,
        request.path,
        request.query,
        request.content_type,
        request.body,
        dict(request.headers),
        request.signing_scope,
    )


def role_request(bearer: str, hosts: Hosts, query: str) -> RequestShape:
    """An unsigned GetRoleCredentials call (credentials.py:2315-2346).

    GET with no body and no Content-Type; the bearer token travels only in
    `x-amz-sso_bearer_token`.
    """
    return (
        "GET",
        hosts.sso_path,
        tuple(sorted(parse_qsl(query, keep_blank_values=True))),
        None,
        None,
        sent_headers({"x-amz-sso_bearer_token": bearer}),
        None,
    )


def create_token_request(
    hosts: Hosts, body: Mapping[str, object]
) -> RequestShape:
    """An unsigned CreateToken refresh (tokens.py:254-268)."""
    return (
        "POST",
        hosts.oidc_path,
        (),
        JSON_CONTENT_TYPE,
        dict(body),
        sent_headers({"content-type": JSON_CONTENT_TYPE}),
        None,
    )


def assume_role_request(body: Mapping[str, list[str]]) -> RequestShape:
    """AssumeRole signed with the SSO role credentials and their token.

    The STS client takes the source credentials (credentials.py:944-952).
    The scope is us-east-1: the sts ruleset signs aws-global as us-east-1
    (data/sts/2011-06-15/endpoint-rule-set-1.json).
    """
    return (
        "POST",
        "/",
        (),
        FORM_CONTENT_TYPE,
        dict(body),
        sent_headers(
            {
                "x-amz-security-token": "SSOTOKEN",
                "authorization": SIGV4_ALGORITHM,
                "x-amz-date": AMZ_DATE_PLACEHOLDER,
                "content-type": FORM_CONTENT_TYPE,
            }
        ),
        ("AKIDSSO", SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts"),
    )


def assert_requests(
    run: CliRun,
    labels: Sequence[str],
    hosts: Hosts = PROXIED,
    *,
    query: str = ROLE_QUERY,
    body: Mapping[str, object] = REFRESH_BODY,
) -> None:
    """The run's calls, in order, and everything each one carried."""
    named = [hosts.label(request) for request in run.requests]
    assert named == list(labels), run.describe()
    for request, name in zip(run.requests, named, strict=True):
        if name.startswith("sso("):
            expected = role_request(name[len("sso(") : -1], hosts, query)
        elif name == "oidc":
            expected = create_token_request(hosts, body)
        else:
            expected = assume_role_request(ASSUME_ROLE_BODY)
        assert request_shape(request) == expected, request.describe()


def assert_exported(run: CliRun, stdout: bytes = OUT_SSO) -> None:
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert run.stdout == stdout, run.describe()


def assert_failed(run: CliRun, returncode: int, message: Stderr) -> None:
    stderr = error_output(message) if isinstance(message, str) else message
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        b"",
        stderr,
    ), run.describe()


def assert_token_rewritten(
    run: CliRun,
    sandbox: Sandbox,
    expected: JsonContent,
    *,
    expires_in: int = REFRESH_EXPIRES_IN,
) -> None:
    """The token file holds `expected`, mode kept, expiresAt to the second.

    The write-back opens the existing file in place (utils.py:3999-4006),
    so its mode is unchanged; `expiresAt` is `%Y-%m-%dT%H:%M:%SZ`
    (tokens.py:53-60).
    """
    assert sandbox.sealed is not None
    mode, content = run.tree[TOKEN_FILE]
    assert mode == sandbox.sealed[TOKEN_FILE][0], run.describe()
    assert isinstance(content, bytes)
    assert TOKEN_TIME.fullmatch(json.loads(content)["expiresAt"]), content
    normalized = cache_tree_normalizer(
        {TOKEN_FILE: (mode, content)}, expires_in=(expires_in,)
    )
    assert normalized[TOKEN_FILE] == (mode, expected), content


def role_cache_created(
    path: str = ROLE_CACHE_FILE, content: RoleCacheContent = ROLE_CACHE
) -> FileChanges:
    """A new role-cache file: 0600 under newly created directories."""
    return {
        CLI_DIR: (CREATED_DIRECTORY_MODE, None),
        CLI_CACHE_DIR: (CREATED_DIRECTORY_MODE, None),
        path: (CACHE_FILE_MODE, content),
    }


class TokenAfter(Enum):
    KEPT = auto()
    REFRESHED = auto()
    REFRESHED_WITHOUT_REFRESH_TOKEN = auto()
    REWRITTEN_EXPIRED = auto()


@dataclass(frozen=True)
class Refresh:
    """One refresh-family row; `error` None means exported and cached."""

    token: Token
    oidc: tuple[HTTPResponse, ...]
    requests: tuple[str, ...]
    error: Stderr | None = None
    token_after: TokenAfter = TokenAfter.KEPT


def assert_token_after(
    run: CliRun,
    sandbox: Sandbox,
    seeded: Mapping[str, object],
    after: TokenAfter,
) -> None:
    if after is TokenAfter.KEPT:
        assert TOKEN_FILE not in run.changes, run.describe()
    elif after is TokenAfter.REFRESHED:
        assert_token_rewritten(run, sandbox, refreshed_token(seeded))
    elif after is TokenAfter.REFRESHED_WITHOUT_REFRESH_TOKEN:
        assert_token_rewritten(
            run, sandbox, refreshed_token(seeded, refresh_token=None)
        )
    else:
        assert_token_rewritten(
            run,
            sandbox,
            refreshed_token(seeded, expires_in=0),
            expires_in=0,
        )


REFRESH_ROWS: Final = [
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW), (OIDC_500,), ("oidc", "sso(OLD-ACCESS)")
        ),
        id="oidc-500-falls-back-to-cached-token",
    ),
    pytest.param(
        Refresh(Token(EXPIRED), (OIDC_500,), ("oidc",), error=TOKEN_EXPIRED),
        id="oidc-500-expired-token-fails",
    ),
    pytest.param(
        Refresh(Token(SIXTEEN_MINUTES), (OIDC_OK,), ("sso(OLD-ACCESS)",)),
        id="sixteen-minutes-left-no-refresh",
    ),
    pytest.param(
        Refresh(
            Token(FOURTEEN_MINUTES),
            (OIDC_OK,),
            ("oidc", "sso(NEW-ACCESS)"),
            token_after=TokenAfter.REFRESHED,
        ),
        id="fourteen-minutes-left-refreshes-and-writes-back",
    ),
    pytest.param(
        Refresh(
            Token(
                INSIDE_WINDOW,
                {"registrationExpiresAt": REGISTRATION_EXPIRED},
            ),
            (OIDC_OK,),
            ("sso(OLD-ACCESS)",),
        ),
        id="registration-expired-skips-refresh",
    ),
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW, {"refreshToken": None}),
            (OIDC_OK,),
            ("sso(OLD-ACCESS)",),
        ),
        id="no-refresh-token-skips-refresh",
    ),
    pytest.param(
        Refresh(
            Token(EXPIRED, {"refreshToken": None}),
            (OIDC_OK,),
            (),
            error=TOKEN_EXPIRED,
        ),
        id="expired-without-refresh-token-fails",
    ),
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW),
            (OIDC_INVALID_GRANT,),
            ("oidc", "sso(OLD-ACCESS)"),
        ),
        id="invalid-grant-falls-back-to-cached-token",
    ),
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW, {"extraKey": "dropme"}),
            (OIDC_NO_REFRESH_TOKEN,),
            ("oidc", "sso(NEW-ACCESS)"),
            token_after=TokenAfter.REFRESHED_WITHOUT_REFRESH_TOKEN,
        ),
        id="response-without-refresh-token-drops-it-and-extra-keys",
    ),
    # Upstream bug, matched for parity: a refresh is saved even when its
    # expiresIn of 0 leaves it already expired, overwriting a still-valid
    # token before the export fails (tokens.py:316-322).
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW),
            (OIDC_EXPIRES_NOW,),
            ("oidc",),
            error=TOKEN_EXPIRED,
            token_after=TokenAfter.REWRITTEN_EXPIRED,
        ),
        id="expires-in-zero-overwrites-valid-token-then-fails",
    ),
    pytest.param(
        Refresh(
            Token(INSIDE_WINDOW),
            (OIDC_NO_EXPIRES_IN,),
            ("oidc",),
            error=framed_error(),
        ),
        id="response-without-expires-in-is-fatal",
    ),
]


@pytest.mark.parametrize("row", REFRESH_ROWS)
async def test_sso_token_refresh_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Refresh,
) -> None:
    sandbox.config.write_text(SSO_CONFIG)
    seeded = seed_token(sandbox, row.token)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=row.oidc, sso=[SSO_OK]),
    )

    assert_requests(run, row.requests)
    expected: FileChanges = {}
    if row.error is None:
        assert_exported(run)
        expected = role_cache_created()
    else:
        assert_failed(run, GENERAL_RC, row.error)
    changes = dict(run.changes)
    assert_token_after(run, sandbox, seeded, row.token_after)
    changes.pop(TOKEN_FILE, None)
    assert changes == expected, run.describe()


async def test_sso_token_write_back_keeps_a_0644_mode(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.config.write_text(SSO_CONFIG)
    seeded = seed_token(sandbox, Token(INSIDE_WINDOW), mode=SHARED_MODE)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK]),
    )

    assert_requests(run, ("oidc", "sso(NEW-ACCESS)"))
    assert_exported(run)
    assert_token_after(run, sandbox, seeded, TokenAfter.REFRESHED)
    changes = dict(run.changes)
    changes.pop(TOKEN_FILE)
    assert changes == role_cache_created(), run.describe()


@needs_permission_checks
async def test_sso_read_only_token_write_back_fails_after_the_refresh(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The write-back opens the token file in place (utils.py:4002-4004);
    # the failure names it, and the role cache is never written.
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(INSIDE_WINDOW), mode=READ_ONLY_MODE)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK]),
    )

    assert_requests(run, ("oidc",))
    assert_failed(
        run,
        GENERAL_RC,
        framed_error(os_error_path(sandbox.root / TOKEN_FILE)),
    )
    assert run.changes == {}, run.describe()


async def test_sso_refused_create_token_is_fatal(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    refused_endpoint: str,
) -> None:
    # Upstream bug, matched for parity: only a ClientError falls back to
    # the cached token (tokens.py:303-307), so an EndpointConnectionError
    # during the refresh is fatal although the token is still valid.
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(INSIDE_WINDOW))

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(sso=[SSO_OK]),
        env={
            "AWS_ENDPOINT_URL_SSO_OIDC": refused_endpoint,
            "NO_PROXY": "127.0.0.1",
        },
    )

    assert_requests(run, ())
    assert_failed(
        run,
        GENERAL_RC,
        f'Could not connect to the endpoint URL: "{refused_endpoint}/token"',
    )
    assert run.changes == {}


async def test_sso_create_token_read_timeout_is_fatal(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    recorder: AsyncHTTPTestServer,
) -> None:
    # `--cli-read-timeout 1` reaches the OIDC client through the CLI's
    # default client config; ReadTimeoutError (exceptions.py:137-138) is
    # not a ClientError, so it is fatal to the refresh.
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(INSIDE_WINDOW))
    recorder.set_default_response(CloseConnection(delay=STALL_SECONDS))
    endpoint = recorder.url.removesuffix("/")

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(sso=[SSO_OK]),
        env={"AWS_ENDPOINT_URL_SSO_OIDC": endpoint, "NO_PROXY": "127.0.0.1"},
        globals_=READ_TIMEOUT_GLOBALS,
        extra_servers=[recorder],
    )

    direct = Hosts(oidc=endpoint.removeprefix("http://"))
    assert_requests(run, ("oidc",), direct)
    assert_failed(
        run,
        GENERAL_RC,
        f'Read timeout on endpoint URL: "{endpoint}/token"',
    )
    assert run.changes == {}


@dataclass(frozen=True)
class RoleCall:
    """A GetRoleCredentials error row."""

    responses: tuple[HTTPResponse, ...]
    returncode: int
    message: str
    max_attempts: str | None = None


TOO_MANY: Final = role_error(
    429, "Too many requests", "TooManyRequestsException"
)

ROLE_CALL_ROWS: Final = [
    pytest.param(
        RoleCall(
            (
                role_error(
                    401,
                    "Session token not found or invalid",
                    "UnauthorizedException",
                ),
            ),
            GENERAL_RC,
            UNAUTHORIZED,
            max_attempts="1",
        ),
        id="unauthorized-error-type-maps-to-sso-message",
    ),
    pytest.param(
        RoleCall(
            (
                HTTPResponse.json(
                    {
                        "__type": (
                            "com.amazonaws.switchboard.portal"
                            "#UnauthorizedException"
                        ),
                        "message": "Session token not found or invalid",
                    },
                    status=401,
                ),
            ),
            GENERAL_RC,
            UNAUTHORIZED,
        ),
        id="unauthorized-body-type-maps-to-sso-message",
    ),
    pytest.param(
        RoleCall(
            (role_error(401, "Session token not found or invalid"),),
            CLIENT_ERROR_RC,
            client_error("401", "Session token not found or invalid"),
        ),
        id="bare-401-is-a-client-error",
    ),
    pytest.param(
        RoleCall(
            (TOO_MANY,) * 3,
            CLIENT_ERROR_RC,
            client_error(
                "TooManyRequestsException", "Too many requests", retries=2
            ),
        ),
        id="throttled-three-attempts",
        marks=pytest.mark.slow,
    ),
]


@pytest.mark.parametrize("row", ROLE_CALL_ROWS)
async def test_sso_get_role_credentials_errors_match_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: RoleCall,
) -> None:
    # Only the UnauthorizedException code maps to the SSO message
    # (credentials.py:2342-2346); every other error is a ClientError, rc
    # 254, and nothing is cached.
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(FRESH))

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(sso=row.responses),
        max_attempts=row.max_attempts,
    )

    labels = ("sso(OLD-ACCESS)",) * len(row.responses)
    assert_requests(run, labels)
    assert_failed(run, row.returncode, row.message)
    assert run.changes == {}


def session_section(*lines: str, name: str = SESSION) -> str:
    """An `[sso-session <name>]` section holding `lines`."""
    return f"\n[sso-session {name}]\n" + "".join(f"{line}\n" for line in lines)


def token_provider_missing(key: str, profile: str = "edge") -> Stderr:
    """SSOTokenProvider's missing-keys error (tokens.py:233-243).

    The keys follow as a Python list repr, so only the key's name is
    asserted after the AWS-authored text.
    """
    message = (
        f'The profile "{profile}" is configured to use the SSO token '
        "provider but is missing the following configuration: "
    )
    return BytesStartingWith(ERROR_PREFIX + message.encode(), (key.encode(),))


def token_provider_no_session(
    name: str = SESSION, profile: str = "edge"
) -> str:
    """SSOTokenProvider's empty or absent session (tokens.py:222-230)."""
    return (
        f'The profile "{profile}" is configured to use the SSO token '
        f'provider but the "{name}" sso_session configuration does not '
        "exist."
    )


def provider_missing(keys: str, profile: str = "edge") -> str:
    """SSOProvider's missing-keys load error (credentials.py:2427-2434)."""
    return (
        f'{LOAD_PREFIX}The profile "{profile}" is configured to use SSO but '
        f"is missing required configuration: {keys}"
    )


def provider_mismatch(key: str, profile_value: str, session_value: str) -> str:
    """The profile/session disagreement (credentials.py:2450-2457)."""
    return (
        f"{LOAD_PREFIX}The value for {key} is inconsistent between profile "
        f"({profile_value}) and sso-session ({session_value})."
    )


def invalid_region(region: str) -> str:
    """InvalidRegionError (exceptions.py:399-406, utils.py:1168-1175)."""
    return f"Provided region_name '{region}' doesn't match a supported format."


@dataclass(frozen=True)
class ConfigError:
    """A configuration row that fails before any request."""

    config: str
    returncode: int
    message: Stderr
    token: bool = True
    env: Mapping[str, str | None] = field(default_factory=dict)


NO_SUCH_SESSION: Final = 'The specified sso-session does not exist: "nope"'
ACCOUNT_LINE: Final = f"sso_account_id = {ACCOUNT}"
ROLE_LINE: Final = f"sso_role_name = {ROLE}"
START_LINE: Final = f"sso_start_url = {START_URL}"
REGION_LINE: Final = f"sso_region = {SSO_REGION}"

CONFIG_ERROR_ROWS: Final = [
    pytest.param(
        ConfigError(
            PROFILE_WITH_SESSION_KEYS + session_section(REGION_LINE),
            GENERAL_RC,
            token_provider_missing("sso_start_url"),
        ),
        id="session-lacks-start-url-fails-at-client-creation",
    ),
    pytest.param(
        ConfigError(
            PROFILE_WITH_SESSION_KEYS + session_section(),
            GENERAL_RC,
            token_provider_no_session(),
        ),
        id="empty-session-section",
    ),
    pytest.param(
        ConfigError(
            LEGACY_CONFIG.replace(REGION_LINE, "sso_region = us_east_1"),
            GENERAL_RC,
            invalid_region("us_east_1"),
            token=False,
        ),
        id="invalid-region-legacy-profile",
    ),
    pytest.param(
        ConfigError(
            PROFILE_EDGE + f"{REGION_LINE}\n" + session_section(REGION_LINE),
            CONFIGURATION_RC,
            provider_missing("sso_start_url"),
        ),
        id="merged-config-lacks-start-url-fails-at-load",
    ),
    pytest.param(
        ConfigError(
            PROFILE_EDGE.replace(SESSION, "nope") + SESSION_SECTION,
            CONFIGURATION_RC,
            LOAD_PREFIX + NO_SUCH_SESSION,
        ),
        id="nonexistent-session-fails-at-load",
    ),
    pytest.param(
        ConfigError(
            f"[profile edge]\n{ACCOUNT_LINE}\n",
            CONFIGURATION_RC,
            provider_missing("sso_role_name, sso_start_url, sso_region"),
            token=False,
        ),
        id="account-id-alone-engages-sso",
    ),
    pytest.param(
        ConfigError(
            PROFILE_EDGE + "sso_region = us-east-1\n" + SESSION_SECTION,
            CONFIGURATION_RC,
            provider_mismatch("sso_region", "us-east-1", SSO_REGION),
        ),
        id="profile-and-session-region-disagree",
    ),
    pytest.param(
        ConfigError(
            PROFILE_EDGE
            + "region = us-east-1\n"
            + session_section(START_LINE, REGION_LINE, "region = eu-west-1"),
            CONFIGURATION_RC,
            provider_mismatch("region", "us-east-1", "eu-west-1"),
        ),
        id="non-sso-key-disagreement-is-checked-too",
    ),
    # Upstream bug, matched for parity: an empty sso_region passes region
    # validation (utils.py:1172 allows an empty label) and builds a host
    # with an empty label.
    pytest.param(
        ConfigError(
            PROFILE_EDGE + session_section(START_LINE, "sso_region ="),
            GENERAL_RC,
            "Invalid endpoint: https://portal.sso..amazonaws.com",
            env=NO_CONFIGURED_ENDPOINTS,
        ),
        id="empty-region-builds-an-invalid-endpoint",
    ),
]


@pytest.mark.parametrize("row", CONFIG_ERROR_ROWS)
async def test_sso_configuration_errors_match_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: ConfigError,
) -> None:
    # SSOProvider.load's own checks fire inside export-credentials' try and
    # are wrapped (rc 253, exportcreds.py:269-276); the token provider's,
    # region validation, and endpoint errors fire at the first
    # create_client, during the deferred fetch, and print bare (rc 255).
    sandbox.config.write_text(row.config)
    if row.token:
        seed_token(sandbox, Token(FRESH))

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK], sts=[STS_OK]),
        env=row.env,
    )

    assert_requests(run, ())
    assert_failed(run, row.returncode, row.message)
    assert run.changes == {}


async def test_sso_fresh_role_cache_skips_broken_session_config(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # A role cache entry with 15 minutes or more left returns before any
    # client is created (credentials.py:746-758, 771-789), so neither the
    # token provider's config check nor the token file is reached.
    sandbox.config.write_text(
        PROFILE_WITH_SESSION_KEYS + session_section(REGION_LINE)
    )
    seed_role_cache(sandbox)

    run = await run_sso(aws_cli, sandbox, stub, PROXIED.script())

    assert_requests(run, ())
    assert_exported(
        run,
        export_credentials_output(
            "AKIDCACHED", "CACHEDSECRET", "CACHEDTOKEN", FUTURE
        ),
    )
    assert run.changes == {}


async def test_sso_profile_keys_in_credentials_file_are_merged(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # SSOProvider reads session.full_config, where credentials-file
    # sections update config-file profiles (session.py:384-414).
    sandbox.config.write_text(SESSION_SECTION.lstrip())
    sandbox.credentials.write_text(
        f"[edge]\nsso_session = {SESSION}\n{ACCOUNT_LINE}\n{ROLE_LINE}\n"
    )
    seed_token(sandbox, Token(FRESH))

    run = await run_sso(aws_cli, sandbox, stub, PROXIED.script(sso=[SSO_OK]))

    assert_requests(run, ("sso(OLD-ACCESS)",))
    assert_exported(run)
    assert run.changes == role_cache_created()


@dataclass(frozen=True)
class Chain:
    """An assume-role profile whose source profile is SSO."""

    remaining: timedelta
    requests: tuple[str, ...]
    seed_sso_role_cache: bool = False


CHAIN_ROWS: Final = [
    pytest.param(
        Chain(FRESH, ("sso(OLD-ACCESS)", "sts")),
        id="writes-only-the-assume-role-cache",
    ),
    pytest.param(
        Chain(INSIDE_WINDOW, ("oidc", "sso(NEW-ACCESS)", "sts")),
        id="refreshes-the-token-before-the-sso-call",
    ),
    pytest.param(
        Chain(FRESH, ("sso(OLD-ACCESS)", "sts"), seed_sso_role_cache=True),
        id="ignores-a-fresh-sso-role-cache",
    ),
]


def assert_sts_signed_by_sso(run: CliRun) -> None:
    """The one AssumeRole call is signed by SSO.

    SigV4 with the SSO role credentials and their session token, verified
    from the wire (credhelpers.assert_signature).
    """
    sts = [
        request
        for request in run.raw_requests
        if route_key(request) == ("POST", STS_HOST, "/")
    ]
    assert len(sts) == 1, f"expected one STS request, got {len(sts)}"
    assert sts[0].headers.get("x-amz-security-token") == "SSOTOKEN"
    assert_signature(sts[0], "AKIDSSO", "SSOSECRET")


def assert_assume_role_cached(entry: TreeEntry | None) -> None:
    """A new 0600 assume-role cache file holding AR_CACHE's credentials."""
    assert entry == (CACHE_FILE_MODE, AR_CACHE), entry


@pytest.mark.parametrize("row", CHAIN_ROWS)
async def test_sso_source_profile_for_assume_role_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Chain,
) -> None:
    # The source chain's SSOProvider keeps the builder's in-memory cache
    # (credentials.py:1832-1846; only the top-level provider gets the file
    # cache), and the source credentials are frozen before the STS client
    # exists (credentials.py:944-952).
    sandbox.config.write_text(AR_CONFIG)
    seeded = seed_token(sandbox, Token(row.remaining))
    if row.seed_sso_role_cache:
        seed_role_cache(sandbox)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK], sts=[STS_OK]),
        profile="target",
    )

    assert_requests(run, row.requests)
    assert_sts_signed_by_sso(run)
    refreshed = "oidc" in row.requests
    assert_token_after(
        run,
        sandbox,
        seeded,
        TokenAfter.REFRESHED if refreshed else TokenAfter.KEPT,
    )
    changes = dict(run.changes)
    changes.pop(TOKEN_FILE, None)
    assert_exported(run, OUT_ROLE)
    assert_assume_role_cached(changes.pop(AR_CACHE_FILE))
    # A seeded SSO role cache already made the directories; it is neither
    # read nor rewritten.
    expected: FileChanges = {}
    if not row.seed_sso_role_cache:
        expected = {
            CLI_DIR: (CREATED_DIRECTORY_MODE, None),
            CLI_CACHE_DIR: (CREATED_DIRECTORY_MODE, None),
        }
    assert changes == expected, run.describe()


async def test_sso_source_fresh_assume_role_cache_needs_no_token(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The assume-role cache hit returns before the source profile is
    # resolved (credentials.py:746-758), so no token file is needed.
    sandbox.config.write_text(AR_CONFIG)
    seed_cli_cache(
        sandbox.home,
        Path(AR_CACHE_FILE).stem,
        {
            "Credentials": {
                "AccessKeyId": "AKIDARCACHED",
                "SecretAccessKey": "ARCACHEDSECRET",
                "SessionToken": "ARCACHEDTOKEN",
                "Expiration": FUTURE,
            }
        },
    )

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(),
        profile="target",
    )

    assert_requests(run, ())
    assert_exported(
        run,
        export_credentials_output(
            "AKIDARCACHED", "ARCACHEDSECRET", "ARCACHEDTOKEN", FUTURE
        ),
    )
    assert run.changes == {}


async def test_sso_endpoints_come_from_the_session_profile_for_a_source(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # ConfiguredEndpointProvider reads the session's scoped config
    # (session.py:932-935, 990-999), so the target's services section
    # routes the source's SSO and OIDC calls and the source profile's own
    # endpoint_url is never consulted.
    sandbox.config.write_text(
        PROFILE_EDGE
        + "endpoint_url = https://ignored.stub.invalid\n"
        + SESSION_SECTION
        + TARGET_PROFILE
        + "services = target-services\n"
        + "\n[services target-services]\n"
        + "sso =\n  endpoint_url = https://target-sso.stub.invalid\n"
        + "sso_oidc =\n  endpoint_url = https://target-oidc.stub.invalid\n"
    )
    seeded = seed_token(sandbox, Token(INSIDE_WINDOW))
    hosts = Hosts(
        sso="target-sso.stub.invalid", oidc="target-oidc.stub.invalid"
    )

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        hosts.script(oidc=[OIDC_OK], sso=[SSO_OK], sts=[STS_OK]),
        profile="target",
        env=NO_CONFIGURED_ENDPOINTS,
    )

    assert_requests(run, ("oidc", "sso(NEW-ACCESS)", "sts"), hosts)
    assert_exported(run, OUT_ROLE)
    assert_sts_signed_by_sso(run)
    # As in the refreshes-the-token-before-the-sso-call case: the token is
    # rewritten and only the assume-role cache is created, under new
    # directories.
    assert_token_after(run, sandbox, seeded, TokenAfter.REFRESHED)
    changes = dict(run.changes)
    changes.pop(TOKEN_FILE)
    assert_assume_role_cached(changes.pop(AR_CACHE_FILE, None))
    assert changes == {
        CLI_DIR: (CREATED_DIRECTORY_MODE, None),
        CLI_CACHE_DIR: (CREATED_DIRECTORY_MODE, None),
    }, run.describe()


CORRUPT: Final = b"{not json"


@dataclass(frozen=True)
class RoleCacheRow:
    """A role cache entry with `cached` left (None: corrupt)."""

    cached: timedelta | None
    token: Token | None
    requests: tuple[str, ...]
    error: Stderr | None = None
    expiration_format: str = UTC_FORMAT


ROLE_CACHE_ROWS: Final = [
    pytest.param(
        RoleCacheRow(SIXTEEN_MINUTES, None, ()),
        id="sixteen-minutes-left-no-token",
    ),
    pytest.param(
        RoleCacheRow(
            SIXTEEN_MINUTES, None, (), expiration_format="%Y-%m-%dT%H:%M:%SUTC"
        ),
        id="sixteen-minutes-left-utc-suffix",
    ),
    pytest.param(
        RoleCacheRow(FOURTEEN_MINUTES, None, (), NO_TOKEN),
        id="fourteen-minutes-left-reads-the-missing-token",
    ),
    pytest.param(
        RoleCacheRow(FOURTEEN_MINUTES, Token(FRESH), ("sso(OLD-ACCESS)",)),
        id="fourteen-minutes-left-refetches-in-place",
    ),
    # Upstream bug, matched for parity: JSONFileCache turns a corrupt
    # entry into a KeyError (utils.py:3974-3981) after its `in` check
    # passed, so the fetch fails instead of treating it as a miss
    # (credentials.py:771-779).
    pytest.param(
        RoleCacheRow(None, Token(FRESH), (), framed_error()),
        id="corrupt-role-cache-is-fatal",
    ),
]


@pytest.mark.parametrize("row", ROLE_CACHE_ROWS)
async def test_sso_role_cache_window_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: RoleCacheRow,
) -> None:
    # An entry is reused only with 900 s or more left (credentials.py:
    # 785-789).
    sandbox.config.write_text(SSO_CONFIG)
    moment = datetime.now(UTC) + (row.cached or timedelta())
    if row.cached is None:
        sandbox.write(ROLE_CACHE_FILE, CORRUPT, mode=CACHE_FILE_MODE)
    else:
        seed_role_cache(sandbox, moment.strftime(row.expiration_format))
    if row.token is not None:
        seed_token(sandbox, row.token)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK]),
    )

    assert_requests(run, row.requests)
    assert TOKEN_FILE not in run.changes, run.describe()
    if row.error is not None:
        assert_failed(run, GENERAL_RC, row.error)
        assert run.changes == {}, run.describe()
    elif row.requests:
        assert_exported(run)
        assert run.changes == {
            ROLE_CACHE_FILE: (CACHE_FILE_MODE, ROLE_CACHE),
        }, run.describe()
    else:
        assert_exported(run, exported_at(moment, "CACHED"))
        assert run.changes == {}, run.describe()


LEGACY_TOKEN_KEY: Final = hashlib.sha1(START_URL.encode()).hexdigest()
LEGACY_TOKEN_FILE: Final = (
    f"home/{SSO_TOKEN_CACHE.as_posix()}/{LEGACY_TOKEN_KEY}.json"
)
LEGACY_ROLE_CACHE_FILE: Final = (
    f"{CLI_CACHE_DIR}/"
    + sso_role_cache_key(
        {"accountId": ACCOUNT, "roleName": ROLE, "startUrl": START_URL}
    )
    + ".json"
)


@dataclass(frozen=True)
class TokenFileError:
    """A token-file row that fails before any request."""

    content: Token | bytes | None
    message: Stderr
    legacy: bool = False


TOKEN_FILE_ERROR_ROWS: Final = [
    pytest.param(TokenFileError(None, NO_TOKEN), id="session-token-absent"),
    pytest.param(
        TokenFileError(Token(FRESH, {"accessToken": None}), INVALID_TOKEN),
        id="session-token-without-access-token-names-the-start-url",
    ),
    pytest.param(
        TokenFileError(CORRUPT, framed_error()),
        id="session-token-corrupt",
    ),
    # Upstream bug, matched for parity: an expiresAt without an offset
    # parses naive and its subtraction from an aware now raises
    # (tokens.py:314-316).
    pytest.param(
        TokenFileError(
            Token(FRESH, {"expiresAt": "2099-01-01T00:00:00"}),
            framed_error(),
        ),
        id="session-token-naive-expiry",
    ),
    pytest.param(
        TokenFileError(Token(EXPIRED), UNAUTHORIZED, legacy=True),
        id="legacy-token-expired-is-never-refreshed",
    ),
]


@pytest.mark.parametrize("row", TOKEN_FILE_ERROR_ROWS)
async def test_sso_token_file_errors_match_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: TokenFileError,
) -> None:
    # SSOTokenLoader (utils.py:3815-3834) and the expiry parses
    # (credentials.py:2325-2335, tokens.py:309-318) raise unwrapped during
    # the deferred fetch, so each prints bare with rc 255.
    sandbox.config.write_text(LEGACY_CONFIG if row.legacy else SSO_CONFIG)
    content = row.content
    if isinstance(content, Token):
        content = json.dumps(content.document()).encode()
    if content is not None:
        path = LEGACY_TOKEN_FILE if row.legacy else TOKEN_FILE
        sandbox.write(path, content, mode=CACHE_FILE_MODE)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK]),
    )

    assert_requests(run, ())
    assert_failed(run, GENERAL_RC, row.message)
    assert run.changes == {}


@pytest.mark.parametrize(
    ("expires_at", "legacy"),
    [
        pytest.param("2099-10-08T12:00:00.123Z", False, id="fraction-session"),
        pytest.param("2099-10-08T12:00:00.123Z", True, id="fraction-legacy"),
        pytest.param(
            "2099-10-08 12:00:00+05:30", False, id="space-and-offset-session"
        ),
    ],
)
async def test_sso_token_expiry_forms_parse_like_dateutil(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    expires_at: str,
    legacy: bool,
) -> None:
    sandbox.config.write_text(LEGACY_CONFIG if legacy else SSO_CONFIG)
    seed_token(
        sandbox,
        Token(FRESH, {"expiresAt": expires_at}),
        key=START_URL if legacy else SESSION,
    )

    run = await run_sso(aws_cli, sandbox, stub, PROXIED.script(sso=[SSO_OK]))

    assert_requests(run, ("sso(OLD-ACCESS)",))
    assert_exported(run)
    cache = LEGACY_ROLE_CACHE_FILE if legacy else ROLE_CACHE_FILE
    assert run.changes == role_cache_created(cache)


async def test_sso_legacy_token_near_expiry_is_used_without_refresh(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The legacy flow reads sha1(start URL) and only rejects an expired
    # token (credentials.py:2325-2335): no window, no CreateToken, even
    # with every refresh key present. Its role cache is keyed by startUrl.
    sandbox.config.write_text(LEGACY_CONFIG)
    seed_token(sandbox, Token(LEGACY_NEAR_EXPIRY), key=START_URL)

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(oidc=[OIDC_OK], sso=[SSO_OK]),
    )

    assert_requests(run, ("sso(OLD-ACCESS)",))
    assert_exported(run)
    assert run.changes == role_cache_created(LEGACY_ROLE_CACHE_FILE)


def role_cache_content(expiration: str) -> RoleCacheContent:
    """ROLE_CACHE with its credentials expiring at `expiration`."""
    credentials = ROLE_CACHE_DOCUMENT["Credentials"]
    assert isinstance(credentials, dict)
    return RoleCacheContent(
        {"Credentials": {**credentials, "Expiration": expiration}}
    )


@dataclass(frozen=True)
class RoleShape:
    """A GetRoleCredentials body; `cached` None means nothing is written."""

    response: HTTPResponse
    error: Stderr
    cached: str | None


ROLE_SHAPE_ROWS: Final = [
    pytest.param(
        RoleShape(
            role_response(expiration=1700000000000),
            STILL_EXPIRED,
            "2023-11-14T22:13:20Z",
        ),
        id="past-expiration-is-cached-then-rejected",
    ),
    pytest.param(
        RoleShape(HTTPResponse.json({}), framed_error(), None),
        id="missing-role-credentials",
    ),
]


@pytest.mark.parametrize("row", ROLE_SHAPE_ROWS)
async def test_sso_role_credentials_response_shapes_match_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: RoleShape,
) -> None:
    # The response maps through credentials.py:2347-2358 (expiration via
    # _parse_timestamp, :2309-2313), is cached (:753-755), and only then is
    # checked for expiry (credentials.py:614-626).
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(FRESH))

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(sso=[row.response]),
    )

    assert_requests(run, ("sso(OLD-ACCESS)",))
    assert_failed(run, GENERAL_RC, row.error)
    expected: FileChanges = {}
    if row.cached is not None:
        expected = role_cache_created(content=role_cache_content(row.cached))
    assert run.changes == expected, run.describe()


async def test_sso_role_credentials_inside_the_cache_window_are_printed(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Credentials with 12 minutes left are cached and printed; only the
    # next fetch would find the entry stale. The expiration's milliseconds
    # are truncated.
    sandbox.config.write_text(SSO_CONFIG)
    seed_token(sandbox, Token(FRESH))
    moment = (datetime.now(UTC) + INSIDE_WINDOW).replace(microsecond=0)
    milliseconds = int(moment.timestamp()) * 1000 + 999

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        PROXIED.script(sso=[role_response(expiration=milliseconds)]),
    )

    assert_requests(run, ("sso(OLD-ACCESS)",))
    assert_exported(run, exported_at(moment))
    assert run.changes == role_cache_created(
        content=role_cache_content(utc_text(moment))
    )


@pytest.mark.parametrize(
    ("role", "encoded"),
    [
        pytest.param("a+b=c,d@e", "a%2Bb%3Dc%2Cd%40e", id="iam-punctuation"),
        pytest.param(
            "rôle",
            "r%C3%B4le",
            id="non-ascii",
            # The public AWS CLI does the same there.
            marks=pytest.mark.skipif(
                os.name != "posix",
                reason="Windows reads the config file in the locale "
                "encoding, not UTF-8",
            ),
        ),
    ],
)
async def test_sso_role_name_is_percent_encoded_and_keys_the_cache(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    role: str,
    encoded: str,
) -> None:
    # percent_encode over UTF-8 with `-._~` safe (utils.py:720-785), so a
    # `+` cannot read as a space; the role cache key hashes the raw name,
    # \u-escaped (credentials.py:2287-2307).
    sandbox.config.write_text(
        SSO_CONFIG.replace(ROLE_LINE, f"sso_role_name = {role}"),
        encoding="utf-8",
    )
    seed_token(sandbox, Token(FRESH))
    key = sso_role_cache_key(
        {"accountId": ACCOUNT, "roleName": role, "sessionName": SESSION}
    )

    run = await run_sso(aws_cli, sandbox, stub, PROXIED.script(sso=[SSO_OK]))

    assert_requests(
        run,
        ("sso(OLD-ACCESS)",),
        query=f"role_name={encoded}&account_id={ACCOUNT}",
    )
    assert_exported(run)
    assert run.changes == role_cache_created(f"{CLI_CACHE_DIR}/{key}.json")


async def test_sso_refresh_writes_config_values_and_registration(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The cached token's startUrl and region are ignored: the OIDC client
    # uses the session's sso_region and the write-back takes both from
    # config (tokens.py:254-283). The registration is copied verbatim and
    # other keys dropped; non-ASCII survives in the request and the file.
    sandbox.config.write_text(SSO_CONFIG)
    seeded = seed_token(
        sandbox,
        Token(
            INSIDE_WINDOW,
            {
                "startUrl": "https://stale.invalid/start",
                "region": "eu-central-1",
                "clientSecret": "CSÉCRET",
                "registrationExpiresAt": "2099-12-31T00:00:00.500+00:00",
                "extraKey": "dropme",
            },
        ),
    )

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        DEFAULT_HOSTS.script(oidc=[OIDC_OK], sso=[SSO_OK]),
        env=NO_CONFIGURED_ENDPOINTS,
    )

    assert_requests(
        run,
        ("oidc", "sso(NEW-ACCESS)"),
        DEFAULT_HOSTS,
        body={**REFRESH_BODY, "clientSecret": "CSÉCRET"},
    )
    assert_exported(run)
    assert_token_rewritten(run, sandbox, refreshed_token(seeded))
    changes = dict(run.changes)
    changes.pop(TOKEN_FILE)
    assert changes == role_cache_created(), run.describe()


@dataclass(frozen=True)
class Endpoints:
    """Where the SSO and OIDC calls go for one endpoint configuration."""

    hosts: Hosts
    env: Mapping[str, str | None] = field(default_factory=dict)
    profile_lines: str = ""
    sections: str = ""
    region: str = SSO_REGION


FIPS: Final = {"AWS_USE_FIPS_ENDPOINT": "true"}
GLOBAL_ENDPOINT: Final = {"AWS_ENDPOINT_URL": "https://all.stub.invalid"}
SERVICES_LINE: Final = "services = edge-services\n"
SERVICES_SECTION: Final = (
    "\n[services edge-services]\n"
    "sso =\n  endpoint_url = https://svc-sso.stub.invalid\n"
    "sso_oidc =\n  endpoint_url = https://svc-oidc.stub.invalid\n"
)
PROFILE_ENDPOINT_LINE: Final = "endpoint_url = https://profile.stub.invalid\n"

ENDPOINT_ROWS: Final = [
    pytest.param(Endpoints(DEFAULT_HOSTS), id="default-endpoints"),
    pytest.param(
        Endpoints(
            Hosts(
                sso="portal.sso-fips.us-west-2.amazonaws.com",
                oidc="oidc-fips.us-west-2.amazonaws.com",
            ),
            profile_lines="use_fips_endpoint = true\n",
        ),
        id="fips-from-profile",
    ),
    pytest.param(
        Endpoints(
            Hosts(
                sso="portal.sso.us-west-2.api.aws",
                oidc="oidc.us-west-2.api.aws",
            ),
            env={"AWS_USE_DUALSTACK_ENDPOINT": "true"},
        ),
        id="dualstack",
    ),
    pytest.param(
        Endpoints(
            Hosts(
                sso="portal.sso.cn-north-1.amazonaws.com.cn",
                oidc="oidc.cn-north-1.amazonaws.com.cn",
            ),
            region="cn-north-1",
        ),
        id="china-partition",
    ),
    pytest.param(
        Endpoints(
            Hosts(sso="svc-sso.stub.invalid", oidc="svc-oidc.stub.invalid"),
            profile_lines=SERVICES_LINE,
            sections=SERVICES_SECTION,
        ),
        id="services-section",
    ),
    pytest.param(
        Endpoints(
            Hosts(sso="all.stub.invalid", oidc="all.stub.invalid"),
            env=GLOBAL_ENDPOINT,
            profile_lines=SERVICES_LINE + PROFILE_ENDPOINT_LINE,
            sections=SERVICES_SECTION,
        ),
        id="global-variable-beats-services-and-profile",
    ),
    pytest.param(
        Endpoints(
            Hosts(
                sso_path=f"/prefix{ROLE_PATH}",
                oidc_path=f"/prefix{TOKEN_PATH}",
            ),
            env={
                "AWS_ENDPOINT_URL_SSO": f"{SSO_ENDPOINT}/prefix",
                "AWS_ENDPOINT_URL_SSO_OIDC": f"{OIDC_ENDPOINT}/prefix",
            },
        ),
        id="endpoint-path-without-trailing-slash",
    ),
    pytest.param(
        Endpoints(
            PROXIED,
            env={
                **FIPS,
                "AWS_ENDPOINT_URL_SSO": SSO_ENDPOINT,
                "AWS_ENDPOINT_URL_SSO_OIDC": OIDC_ENDPOINT,
            },
        ),
        id="configured-endpoint-disables-fips",
    ),
    pytest.param(
        Endpoints(
            DEFAULT_HOSTS,
            env={
                "AWS_ENDPOINT_URL_SSO": SSO_ENDPOINT,
                "AWS_ENDPOINT_URL_SSO_OIDC": OIDC_ENDPOINT,
                "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS": "true",
            },
        ),
        id="ignore-configured-endpoint-urls",
    ),
]


@pytest.mark.parametrize("row", ENDPOINT_ROWS)
async def test_sso_endpoint_resolution_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Endpoints,
) -> None:
    # Both clients resolve through ConfiguredEndpointProvider (configprovider
    # .py:821-850) and then the sso and sso-oidc rulesets with the
    # sso_region; a configured endpoint forces FIPS and dual-stack off
    # (args.py:654-701) and is joined with the operation path
    # (awsrequest.py:317-342). The token is refreshed so both clients call.
    sandbox.config.write_text(
        PROFILE_EDGE
        + row.profile_lines
        + session_section(START_LINE, f"sso_region = {row.region}")
        + row.sections
    )
    seeded = seed_token(sandbox, Token(INSIDE_WINDOW))

    run = await run_sso(
        aws_cli,
        sandbox,
        stub,
        row.hosts.script(oidc=[OIDC_OK], sso=[SSO_OK]),
        env={**NO_CONFIGURED_ENDPOINTS, **row.env},
    )

    assert_requests(run, ("oidc", "sso(NEW-ACCESS)"), row.hosts)
    assert_exported(run)
    assert_token_rewritten(
        run, sandbox, refreshed_token(seeded, region=row.region)
    )
    changes = dict(run.changes)
    changes.pop(TOKEN_FILE)
    assert changes == role_cache_created(), run.describe()


# `aws sso login`'s authorization code flow (botocore utils.py:3561-3760)
# through the same stub: RegisterClient, then CreateToken once the test
# has followed the sign-in page's redirect to the CLI's callback
# (customizations/sso/utils.py:250-330).
# An AWS-owned start URL, which `aws sso login` uses without resolving it
# over HTTP first (customizations/sso/resolve.py).
LOGIN_CONFIG: Final = (
    SSO_CONFIG.replace(START_URL, "https://d-0000000000.awsapps.com/start")
    + "sso_registration_scopes = sso:account:access\n"
)
LOGIN_SCRIPT: Final[Script] = {
    ("POST", OIDC_HOST, REGISTER_PATH): [
        HTTPResponse.json(
            {
                "clientId": "LOGIN-CID",
                "clientSecret": "LOGIN-CSECRET",
                "clientIdIssuedAt": 1767225600,
                "clientSecretExpiresAt": 4102444800,
            }
        )
    ],
    ("POST", OIDC_HOST, TOKEN_PATH): [
        oidc_token(access_token="LOGIN-ACCESS", refresh_token="LOGIN-REFRESH")
    ],
}
LOGIN_TIMEOUT_SECONDS: Final = 15.0
# The browser `webbrowser` runs for $BROWSER records the URL it is opened
# with and leaves the redirect to the test; the rename keeps the test from
# reading a partial URL.
BROWSER_SCRIPT: Final = (
    "import os, sys\n"
    "path, url = sys.argv[1:]\n"
    "with open(path + '.tmp', 'w') as stream:\n"
    "    stream.write(url)\n"
    "os.replace(path + '.tmp', path)\n"
)


async def browser_opened(
    opened_url: Path, process: asyncio.subprocess.Process
) -> str:
    """The URL the CLI opened the browser with, once it has."""
    while not opened_url.exists():
        if process.returncode is not None:
            output, _ = await process.communicate()
            pytest.fail(
                f"aws sso login exited {process.returncode} without opening "
                f"a browser:\n{output.decode(errors='replace')}"
            )
        await asyncio.sleep(0.05)
    return opened_url.read_text(encoding="utf-8")


async def redirect_to_callback(authorize_url: str) -> None:
    """Follow the sign-in page's redirect to the CLI's local callback."""
    query = parse_qs(urlsplit(authorize_url).query)
    params = urlencode({"code": "LOGIN-CODE", "state": query["state"][0]})
    callback = f"{query['redirect_uri'][0]}?{params}"
    # The callback is local, whatever proxy the runner's shell sets.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get() -> None:
        with opener.open(callback, timeout=10) as response:
            response.read()

    await asyncio.to_thread(get)


async def sso_login(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> tuple[int, bytes]:
    """Run `aws sso login --profile edge` to completion.

    Returns its exit status and combined output.
    """
    server, _ = stub
    opened_url = sandbox.root / "opened-url"
    browser = sandbox.write("browser.py", BROWSER_SCRIPT)
    command = [Path(sys.executable).as_posix(), "-I", browser.as_posix()]
    env = sso_env(sandbox, stub)
    env["BROWSER"] = f"{shlex.join([*command, opened_url.as_posix()])} %s"
    server.clear_requests()
    server.handler = routed(LOGIN_SCRIPT)
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        "sso",
        "login",
        "--profile",
        "edge",
        env=child_environment(env),
        cwd=sandbox.root,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        authorize_url = await asyncio.wait_for(
            browser_opened(opened_url, process), LOGIN_TIMEOUT_SECONDS
        )
        await redirect_to_callback(authorize_url)
        output, _ = await asyncio.wait_for(
            process.communicate(), LOGIN_TIMEOUT_SECONDS
        )
    finally:
        if process.returncode is None:
            kill_process_group(process.pid)
            await process.wait()
    assert process.returncode is not None
    return process.returncode, output


async def test_sso_token_written_by_sso_login_is_read_by_export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Both commands share the token cache: `aws sso login` writes
    # sha1(session name) in ~/.aws/sso/cache (utils.py:3803-3834), and
    # export-credentials presents its access token without refreshing it.
    sandbox.config.write_text(LOGIN_CONFIG)

    returncode, output = await sso_login(aws_cli, sandbox, stub)
    assert returncode == 0, output
    sandbox.seal()
    assert sandbox.sealed is not None
    assert sandbox.sealed[TOKEN_FILE][0] == CACHE_FILE_MODE

    run = await run_sso(aws_cli, sandbox, stub, PROXIED.script(sso=[SSO_OK]))

    assert_requests(run, ("sso(LOGIN-ACCESS)",))
    assert_exported(run)
    assert run.changes == role_cache_created()


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


PARITY_START_URL = "https://credential-parity.invalid/start"
PARITY_SESSION = "parity-session"
PAST = "2000-01-01T00:00:00Z"


SSO_TOKEN = {
    "startUrl": PARITY_START_URL,
    "region": "us-west-2",
    "accessToken": "cached-access-token",
    "expiresAt": FUTURE_Z,
    "clientId": "synthetic-client",
    "clientSecret": "synthetic-client-secret",
    "registrationExpiresAt": FUTURE_Z,
}
EXPIRED_SSO_TOKEN = {**SSO_TOKEN, "expiresAt": PAST}
REFRESHABLE_SSO_TOKEN = {
    **EXPIRED_SSO_TOKEN,
    "refreshToken": "old-refresh-token",
}
ROLE_CREDENTIALS = HTTPResponse.json(
    {
        "roleCredentials": {
            "accessKeyId": "AKIDSSO",
            "secretAccessKey": "SSO-secret",
            "sessionToken": "SSO-token",
            "expiration": 4070908800000,
        }
    }
)


def sso_config(*, legacy: bool) -> str:
    profile = (
        "[default]\n"
        "sso_account_id = 123456789012\n"
        "sso_role_name = ParityRole\n" + file_credentials("DECOY")
    )
    if not legacy:
        profile += (
            f"sso_session = {PARITY_SESSION}\n"
            f"[sso-session {PARITY_SESSION}]\n"
        )
    return profile + (
        f"sso_start_url = {PARITY_START_URL}\nsso_region = us-west-2\n"
    )


def write_json(path: Path, data: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def seed_parity_sso_token(
    home: Path, token: dict[str, object], *, legacy: bool
) -> Path:
    # Legacy profiles key the cache by start URL, sso-session ones by name.
    name = PARITY_START_URL if legacy else PARITY_SESSION
    key = hashlib.sha1(name.encode()).hexdigest()
    return write_json(home / ".aws/sso/cache" / f"{key}.json", token)


def endpoint(request: RecordedHTTPRequest) -> str:
    path = urlsplit(request.effective_path).path
    return f"{request.method} https://{request.headers['host']}{path}"


def assert_sso_signed(
    role: RecordedHTTPRequest, s3: RecordedHTTPRequest, bearer_token: str
) -> None:
    assert endpoint(role) == (
        "GET https://portal.sso.us-west-2.amazonaws.com/federation/credentials"
    )
    assert parse_qs(urlsplit(role.effective_path).query) == {
        "account_id": ["123456789012"],
        "role_name": ["ParityRole"],
    }
    assert role.headers["x-amz-sso_bearer_token"] == bearer_token
    assert "authorization" not in role.headers
    assert s3.headers["x-amz-security-token"] == "SSO-token"
    assert_signature(s3, "AKIDSSO", "SSO-secret")


@pytest.mark.parametrize("legacy", [True, False], ids=["legacy", "session"])
async def test_sso_cached_token_signs_with_role_credentials(
    aws_cli: str, tmp_path: Path, legacy: bool
) -> None:
    seed_parity_sso_token(tmp_path, SSO_TOKEN, legacy=legacy)
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, sso_config(legacy=legacy))
        _, stderr, rc = await list_bucket(
            aws_cli,
            server,
            env,
            responses=[ROLE_CREDENTIALS, empty_list_objects_response()],
        )
    assert rc == 0, stderr.decode()
    role, s3 = server.requests
    assert_sso_signed(role, s3, "cached-access-token")


async def test_sso_expired_token_refreshes_and_updates_cache(
    aws_cli: str, tmp_path: Path
) -> None:
    cache = seed_parity_sso_token(
        tmp_path, REFRESHABLE_SSO_TOKEN, legacy=False
    )
    refreshed = HTTPResponse.json(
        {
            "accessToken": "refreshed-access-token",
            "refreshToken": "new-refresh-token",
            "expiresIn": 3600,
            "tokenType": "Bearer",
        }
    )
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, sso_config(legacy=False))
        _, stderr, rc = await list_bucket(
            aws_cli,
            server,
            env,
            responses=[
                refreshed,
                ROLE_CREDENTIALS,
                empty_list_objects_response(),
            ],
        )
    assert rc == 0, stderr.decode()
    refresh, role, s3 = server.requests
    assert (
        endpoint(refresh) == "POST https://oidc.us-west-2.amazonaws.com/token"
    )
    assert json.loads(refresh.text) == {
        "grantType": "refresh_token",
        "clientId": "synthetic-client",
        "clientSecret": "synthetic-client-secret",
        "refreshToken": "old-refresh-token",
    }
    assert_sso_signed(role, s3, "refreshed-access-token")
    saved = json.loads(cache.read_text())
    assert saved["accessToken"] == "refreshed-access-token"
    assert saved["refreshToken"] == "new-refresh-token"
    assert saved["expiresAt"] != PAST


@pytest.mark.parametrize(
    "legacy,token",
    [
        # Legacy profiles never refresh, even with a usable refresh token.
        (True, REFRESHABLE_SSO_TOKEN),
        (False, EXPIRED_SSO_TOKEN),
        (False, {**REFRESHABLE_SSO_TOKEN, "registrationExpiresAt": PAST}),
    ],
    ids=["legacy", "missing-refresh-token", "expired-registration"],
)
async def test_sso_expired_unrefreshable_token_fails_before_request(
    aws_cli: str, tmp_path: Path, legacy: bool, token: dict[str, object]
) -> None:
    cache = seed_parity_sso_token(tmp_path, token, legacy=legacy)
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, sso_config(legacy=legacy))
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)
    assert b"expired" in result[1]
    assert json.loads(cache.read_text()) == token


async def test_sso_missing_token_does_not_fall_through_to_static_keys(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, sso_config(legacy=True))
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)
    assert b"Token" in result[1]
