import base64
import hashlib
import json
import math
import os
import re
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

import pytest
from localstub import HTTPResponse, RecordedHTTPRequest, ResponderContext

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CREATED_DIRECTORY_MODE,
    LOGIN_TOKEN_CACHE,
    SAMPLE_DPOP_PEM,
    SCOPE_DATE_PLACEHOLDER,
    BytesStartingWith,
    CliRun,
    Handler,
    HandlerFactory,
    JsonContent,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_credential_error,
    assert_dpop,
    assert_signature,
    assert_signed_by,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    list_bucket,
    os_error_path,
    role_cache_key,
    route_key,
    routed,
    run_export_credentials,
    signin_token,
    sts_success_xml,
    write_config,
)
from tests.blackbox.utils import empty_list_objects_response

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# botocore's LoginProvider and LoginCredentialFetcher (credentials.py:
# 2498-2711), the login cache (utils.py:3951-4017, 4051-4052, 4179-4205),
# and the DPoP proof (utils.py:4208-4257), through `aws configure
# export-credentials` (awscli/customizations/configure/exportcreds.py:
# 30-46, 266-282).
EnvChanges = Mapping[str, str | None]
Script = Mapping[RouteKey, Sequence[HTTPResponse]]
# (answered, finished): from the moment the stub answered a run's last
# signin request to the moment the run returned.
Window = tuple[float, float]


ACCOUNT: Final = "123456789012"
SESSION: Final = "login-session"
# sha256(utf-8 session name) in lowercase hex (utils.py:4051-4052), pinned
# as a known answer rather than recomputed.
CACHE_KEY: Final = (
    "95d15095f389110a52ff29aaa236fa390dbfaa8fcae2971309b43a6a5be26133"
)
CACHE_FILE: Final = f"{CACHE_KEY}.json"
DEFAULT_CACHE_DIR: Final = Path("home") / LOGIN_TOKEN_CACHE
LOGIN_CONFIG: Final = f"[default]\nlogin_session = {SESSION}\n"
CLIENT_ID: Final = "arn:aws:signin:::devtools/same-device"
OLD_REFRESH_TOKEN: Final = "old-refresh-token"
NEW_REFRESH_TOKEN: Final = "new-refresh-token"
PAST: Final = "2000-01-01T00:00:00Z"
FUTURE: Final = "2099-01-01T00:00:00Z"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
SIGNIN_HOST: Final = "us-east-1.signin.aws.amazon.com"
SIGNIN_PATH: Final = "/v1/token"
SIGNIN_URL: Final = f"https://{SIGNIN_HOST}{SIGNIN_PATH}"
SIGNIN_ROUTE: Final[RouteKey] = ("POST", SIGNIN_HOST, SIGNIN_PATH)
REFRESH_EXPIRES_IN: Final = 900
# A configured signin endpoint with a base path: the operation's path is
# appended to it (awsrequest.py:251-342), and the DPoP htu is that URL.
BASE_PATH_ENDPOINT: Final = "https://signin.example.invalid/base"
# The rest-json body botocore sends for CreateOAuth2Token: the tokenInput
# members (credentials.py:2573-2580).
REFRESH_BODY: Final[Mapping[str, object]] = {
    "clientId": CLIENT_ID,
    "refreshToken": OLD_REFRESH_TOKEN,
    "grantType": "refresh_token",
}
JSON_CONTENT_TYPE: Final = "application/json"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded"
# The signin client is UNSIGNED (credentials.py:2559-2561): no
# Authorization, X-Amz-Date, or session token, only the JSON body's type.
REFRESH_HEADERS: Final[Mapping[str, str | None]] = {
    "x-amz-security-token": None,
    "x-amz-sso_bearer_token": None,
    "x-aws-ec2-metadata-token": None,
    "x-aws-ec2-metadata-token-ttl-seconds": None,
    "authorization": None,
    "x-amz-date": None,
    "content-type": JSON_CONTENT_TYPE,
}
NO_REGION: Final[EnvChanges] = {"AWS_REGION": None, "AWS_DEFAULT_REGION": None}
CONFIGURATION_RC: Final = 253
PARAM_VALIDATION_RC: Final = 252
CLIENT_ERROR_RC: Final = 254
GENERAL_ERROR_RC: Final = 255
LOAD_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
# The framing of an error raised unwrapped by get_frozen_credentials.
ERROR_PREFIX: Final = "\naws: [ERROR]: "
TOKEN_LOAD_PREFIX: Final = "Error loading login session token: "
# credentials.py:2524-2529, verbatim ("a existing", "Please").
NO_SESSION: Final = (
    f"Unable to load a existing login session for session {SESSION}, "
    "Please reauthenticate with 'aws login'."
)
MISSING_FIELDS: Final = (
    f"{TOKEN_LOAD_PREFIX}Failed to load access token from token cache, "
    "missing one or more required fields."
)
KEY_LOAD_PREFIX: Final = (
    f"{TOKEN_LOAD_PREFIX}Unable to load private key from cached token: "
)
# The dpopKey "x": its one base64 character fails the decode, an error
# raised unwrapped by get_frozen_credentials (credentials.py:2633-2657).
BAD_BASE64_KEY: Final = "x"
PARAM_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (ParamValidation): "
    "Parameter validation failed:\n"
)
NO_REGION_ERROR: Final = (
    b"\naws: [ERROR]: An error occurred (NoRegion): You must specify a "
    b'region. You can also configure your region by running "aws '
    b'configure".\n'
)
# The LoginError subclasses' fixed texts (exceptions.py:762-789).
LOGIN_ERROR: Final = (
    "An unspecified error happened when resolving AWS credentials or "
    "refreshing a login session profile."
)
TOKEN_EXPIRED: Final = (
    "Your session has expired. Please reauthenticate using 'aws login'."
)
PASSWORD_CHANGED: Final = (
    "Unable to refresh login credentials because of a change in your "
    "password. Please reauthenticate with your new password using "
    "'aws login'."
)
INSUFFICIENT_PERMISSIONS: Final = (
    "Unable to create or refresh login credentials due to insufficient "
    "permissions. You may be missing permission for the "
    "'signin:CreateOAuth2Token' action."
)
STILL_EXPIRED: Final = (
    "Credentials were refreshed, but the refreshed credentials are still "
    "expired."
)
# The in-tree login test-case key (tests/unit/botocore/login/
# login-provider-test-cases.json): PKCS#8, no trailing newline. Public.
PKCS8_DPOP_PEM: Final = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg+PNauWi/ihtwHHbq\n"
    "1tgc8Vgpwx0qQlNSN38y+z0igWehRANCAAR2Ntw6BXJ1v8jb9XjzKZJ+gL5f/3Jq\n"
    "IqiH2PUGKWxoFwNlcNB83FivEXEzlTbuCQK5OezOYb3gbvHuzKkB0nDX\n"
    "-----END PRIVATE KEY-----"
)
# The form a refresh writes expiresAt in (credentials.py:2612-2614).
WRITTEN_EXPIRES_AT: Final = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
# The access token botocore reads and later replaces whole (credentials.py:
# 2602-2618); the default fixture expired long ago, so any read refreshes.
ACCESS_TOKEN: Final[Mapping[str, object]] = {
    "accessKeyId": "AKIDLOGIN",
    "secretAccessKey": "LOGIN-secret",
    "sessionToken": "LOGIN-token",
    "accountId": ACCOUNT,
    "expiresAt": PAST,
}
CACHED_OUTPUT: Final = export_credentials_output(
    "AKIDLOGIN", "LOGIN-secret", "LOGIN-token", FUTURE_EXPIRATION
)
ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/r"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
# A login profile as an assume-role source: the chain resolves it with
# the full profile provider chain (credentials.py:1819-1848). The signin
# client comes from the session (credentials.py:260-266), so its region is
# the session profile's (`target` has none), never the source profile's.
SOURCE_CHAIN_CONFIG: Final = f"""\
[profile target]
role_arn = {ROLE_ARN}
role_session_name = sess
source_profile = signin

[profile signin]
login_session = {SESSION}
region = eu-west-1
"""
# Marks a token key the fixture leaves out.
MISSING: Final = object()
needs_permission_checks = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores file permission bits",
)


def token_with(
    *, access: Mapping[str, object] | None = None, **changes: object
) -> dict[str, object]:
    """The `aws login` token botocore needs, with `changes` applied.

    A changed key keeps its place, a new one is appended, and MISSING
    drops it.
    """
    token: dict[str, object] = {
        "accessToken": {**ACCESS_TOKEN, **(access or {})},
        "refreshToken": OLD_REFRESH_TOKEN,
        "clientId": CLIENT_ID,
        "dpopKey": SAMPLE_DPOP_PEM,
    }
    for key, value in changes.items():
        if value is MISSING:
            token.pop(key, None)
        else:
            token[key] = value
    return token


def expiring_in(seconds: int) -> str:
    """`now + seconds` in the `%Y-%m-%dT%H:%M:%SZ` form `aws login` writes."""
    moment = datetime.now(UTC) + timedelta(seconds=seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def isoformat(expires_at: str) -> str:
    """The Expiration export-credentials prints for a `...Z` expiresAt."""
    return datetime.fromisoformat(expires_at).isoformat()


def write_cache(
    sandbox: Sandbox,
    content: object,
    *,
    directory: Path = DEFAULT_CACHE_DIR,
    mode: int = CACHE_FILE_MODE,
) -> Path:
    """Write a login cache file under the sandbox root.

    `content` is written as given when it is bytes and through
    `json.dumps` (botocore's own writer, utils.py:3967-3968) otherwise.
    """
    data = content if isinstance(content, bytes) else json.dumps(content)
    return sandbox.write((directory / CACHE_FILE).as_posix(), data, mode=mode)


def refreshed_token(
    token: Mapping[str, object], expires_at: str
) -> JsonContent:
    """`token` after a successful refresh, as botocore writes it back.

    Every other key is kept; the access token is replaced whole, its
    account id carried over (credentials.py:2602-2619).
    """
    access = token["accessToken"]
    assert isinstance(access, Mapping)
    return JsonContent(
        {
            **token,
            "accessToken": {
                "accessKeyId": "AKIDNEW",
                "secretAccessKey": "NEW-secret",
                "sessionToken": "NEW-token",
                "accountId": access["accountId"],
                "expiresAt": expires_at,
            },
            "refreshToken": NEW_REFRESH_TOKEN,
        }
    )


def refreshed_output(expires_at: str) -> bytes:
    """The `--format process` stdout of the refreshed credentials.

    The Expiration is the written expiresAt through dateutil and
    isoformat(), whole seconds in UTC (credentials.py:2702-2711,
    exportcreds.py:38-40).
    """
    return export_credentials_output(
        "AKIDNEW", "NEW-secret", "NEW-token", isoformat(expires_at)
    )


def stamped_expires_at(
    run: CliRun,
    path: str,
    window: Window,
    expires_in: int = REFRESH_EXPIRES_IN,
) -> str:
    """The expiresAt the run wrote to `path`, checked against `window`.

    botocore stamps `now + expiresIn` after the response, cut to whole
    seconds (credentials.py:2598-2614), so the stamp is the second of a
    moment inside the window plus `expires_in`. A window inside one
    wall-clock second pins that stamp exactly; one that spans a second
    boundary admits the stamp of either second.
    """
    entry = run.changes.get(path)
    assert entry is not None, run.describe()
    _, content = entry
    assert isinstance(content, bytes), run.describe()
    expires_at = json.loads(content)["accessToken"]["expiresAt"]
    assert isinstance(expires_at, str), expires_at
    assert WRITTEN_EXPIRES_AT.fullmatch(expires_at), expires_at
    stamp = datetime.fromisoformat(expires_at).timestamp()
    answered, finished = window
    assert (
        math.floor(answered) + expires_in
        <= stamp
        <= math.floor(finished) + expires_in
    ), (expires_at, window)
    return expires_at


def load_error(message: str) -> bytes:
    """The stderr of an error raised while the chain loads (rc 253)."""
    return f"{LOAD_PREFIX}{message}\n".encode()


def raw_error(message: str) -> bytes:
    """The stderr of an error raised by get_frozen_credentials (unwrapped)."""
    return f"{ERROR_PREFIX}{message}\n".encode()


def framed_error(prefix: str = "", *parts: bytes) -> BytesStartingWith:
    """An unwrapped error whose text after `prefix` is CPython's.

    A KeyError's repr, a base64 or OSError message: only the framing,
    the AWS-authored `prefix`, and each of `parts` are asserted.
    """
    return BytesStartingWith(f"{ERROR_PREFIX}{prefix}".encode(), parts)


def param_error(line: str) -> bytes:
    return f"{PARAM_PREFIX}{line}\n".encode()


def client_error(
    code: str, message: str, *, details: str = "", retries: str = ""
) -> bytes:
    """A CreateOAuth2Token ClientError in the enhanced format (rc 254).

    write_error strips the message (awscli/errorformat.py:28-41).
    """
    summary = (
        f"An error occurred ({code}) when calling the "
        f"CreateOAuth2Token operation{retries}: {message}"
    )
    text = f"\naws: [ERROR]: {summary.strip()}\n"
    if details:
        text += f"\nAdditional error details:\n{details}\n"
    return text.encode()


def signin_error(status: int, code: str, **members: str) -> HTTPResponse:
    """A modeled signin error whose code travels in the body's `__type`."""
    return HTTPResponse.json({"__type": code, **members}, status=status)


def is_signin_request(request: RecordedHTTPRequest) -> bool:
    """Whether `request` is for CreateOAuth2Token at any signin endpoint."""
    return route_key(request)[2].endswith(SIGNIN_PATH)


def assert_dpop_bound(
    run: CliRun,
    private_pem: str,
    url: str = SIGNIN_URL,
    *,
    attempts: int = 1,
) -> None:
    """Every signin request carries a DPoP proof for `url`.

    Each proof is signed by the cached key and names the URL the request
    was sent to; whether a retry reuses a proof is the sender's choice.
    """
    proofs = [
        request.headers["dpop"]
        for request in run.raw_requests
        if is_signin_request(request)
    ]
    assert len(proofs) == attempts, proofs
    for proof in proofs:
        assert_dpop(proof, private_pem, url)


def assert_refresh_request(
    run: CliRun,
    *,
    host: str = SIGNIN_HOST,
    path: str = SIGNIN_PATH,
    attempts: int = 1,
) -> None:
    """`attempts` unsigned CreateOAuth2Token POSTs and nothing else.

    The body is REFRESH_BODY (credentials.py:2560-2580).
    """
    assert len(run.requests) == attempts, run.describe()
    for request in run.requests:
        assert (
            request.method,
            request.host,
            request.path,
            request.target,
            request.query,
            request.content_type,
            request.body,
            dict(request.headers),
            request.signing_scope,
        ) == (
            "POST",
            host,
            path,
            path,
            (),
            JSON_CONTENT_TYPE,
            REFRESH_BODY,
            REFRESH_HEADERS,
            None,
        ), run.describe()


async def run_login(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Script | None = None,
    *,
    env_changes: EnvChanges | None = None,
    globals_: Sequence[str] = (),
    cwd: Path | None = None,
    max_attempts: str | None = "1",
    handler: HandlerFactory | None = None,
) -> CliRun:
    """Run export-credentials with the signin stub serving `script`.

    Any request the script does not plan for gets the harness's 400.
    `env_changes` maps a variable to its value, or to None to remove it.
    """
    server, proxy = stub
    env = sandbox.env(proxy, max_attempts=max_attempts)
    for key, value in (env_changes or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    routes = dict(script or {})
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        env,
        globals_=globals_,
        cwd=cwd,
        handlers={server: handler or (lambda: routed(routes))},
    )


async def run_refresh(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Script,
    *,
    env_changes: EnvChanges | None = None,
    globals_: Sequence[str] = (),
) -> tuple[CliRun, Window]:
    """`run_login` that also returns the run's refresh Window.

    The window opens when the stub answers the last signin request (the
    CLI reads the response after that moment) and closes when the run
    returns, so it holds the moment botocore stamps the refresh.
    """
    answers: list[float] = []

    def timed() -> Handler:
        serve = routed(script)

        def answer(context: ResponderContext) -> HTTPResponse:
            response = serve(context)
            if is_signin_request(context.request):
                answers.append(time.time())
            return response

        return answer

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        env_changes=env_changes,
        globals_=globals_,
        handler=timed,
    )
    finished = time.time()
    assert answers, run.describe()
    return run, (answers[-1], finished)


def seed(
    sandbox: Sandbox,
    token: object,
    *,
    config: str = LOGIN_CONFIG,
    directory: Path = DEFAULT_CACHE_DIR,
    mode: int = CACHE_FILE_MODE,
) -> str:
    """Write the profile and its token, seal: the token's sandbox path."""
    sandbox.config.write_text(config, encoding="utf-8")
    path = write_cache(sandbox, token, directory=directory, mode=mode)
    sandbox.seal()
    return path.relative_to(sandbox.root).as_posix()


@pytest.mark.parametrize(
    ("directory", "env_changes"),
    [
        pytest.param(
            Path("login-cache"),
            {"AWS_LOGIN_CACHE_DIRECTORY": "{root}/login-cache"},
            id="override-directory",
        ),
        pytest.param(
            Path("home/login-dir"),
            {"AWS_LOGIN_CACHE_DIRECTORY": "~/$MYDIR", "MYDIR": "login-dir"},
            id="override-expands-variable-then-user",
        ),
    ],
)
async def test_login_cached_token_exports_without_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    directory: Path,
    env_changes: Mapping[str, str],
) -> None:
    seed(
        sandbox,
        token_with(access={"expiresAt": FUTURE}),
        directory=directory,
    )
    env = {
        key: value.format(root=sandbox.root)
        for key, value in env_changes.items()
    }

    run = await run_login(aws_cli, sandbox, stub, env_changes=env)

    assert run.returncode == 0, run.describe()
    assert run.stdout == CACHED_OUTPUT
    assert run.stderr == b""
    assert run.requests == ()
    assert run.changes == {}, run.describe()


async def test_login_token_outside_300_seconds_is_not_refreshed(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # 390 s left is inside the credentials' mandatory window, so a refresh
    # runs, but the fetcher refreshes only under 300 s left and returns
    # the disk token (credentials.py:2548-2557): a 600 s or 900 s
    # threshold would send a request.
    expires_at = expiring_in(390)
    seed(sandbox, token_with(access={"expiresAt": expires_at}))

    run = await run_login(aws_cli, sandbox, stub)

    assert run.returncode == 0, run.describe()
    assert run.stdout == export_credentials_output(
        "AKIDLOGIN", "LOGIN-secret", "LOGIN-token", isoformat(expires_at)
    )
    assert run.stderr == b""
    assert run.requests == ()
    assert run.changes == {}, run.describe()


async def test_login_token_inside_300_seconds_refreshes_and_writes_back(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    token = token_with(access={"expiresAt": expiring_in(240)})
    path = seed(sandbox, token)

    run, window = await run_refresh(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [signin_token()]}
    )

    assert run.returncode == 0, run.describe()
    written = stamped_expires_at(run, path, window)
    assert run.stdout == refreshed_output(written)
    assert run.stderr == b""
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {
        path: (CACHE_FILE_MODE, refreshed_token(token, written))
    }, run.describe()


@pytest.mark.parametrize(
    ("dpop_key", "private_pem"),
    [
        pytest.param(
            SAMPLE_DPOP_PEM.replace("\n", "\r\n"),
            SAMPLE_DPOP_PEM,
            id="sec1-crlf",
        ),
        pytest.param(PKCS8_DPOP_PEM, PKCS8_DPOP_PEM, id="pkcs8"),
    ],
)
async def test_login_refresh_signs_dpop_with_cached_key_forms(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    dpop_key: str,
    private_pem: str,
) -> None:
    token = token_with(dpopKey=dpop_key)
    path = seed(sandbox, token)

    run, window = await run_refresh(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [signin_token()]}
    )

    assert run.returncode == 0, run.describe()
    written = stamped_expires_at(run, path, window)
    assert run.stdout == refreshed_output(written)
    assert run.stderr == b""
    assert_refresh_request(run)
    assert_dpop_bound(run, private_pem)
    assert run.changes == {
        path: (CACHE_FILE_MODE, refreshed_token(token, written))
    }, run.describe()


@pytest.mark.parametrize(
    ("globals_", "env_changes", "url"),
    [
        pytest.param(
            ("--region", "us-west-2"),
            {},
            "https://us-west-2.signin.aws.amazon.com/v1/token",
            id="region-flag",
        ),
        pytest.param(
            ("--region", "cn-north-1"),
            {},
            "https://cn-north-1.signin.amazonaws.cn/v1/token",
            id="china-partition",
        ),
        pytest.param(
            (),
            {"AWS_USE_FIPS_ENDPOINT": "true"},
            "https://signin-fips.us-east-1.amazonaws.com/v1/token",
            id="fips",
        ),
        pytest.param(
            (),
            {"AWS_USE_DUALSTACK_ENDPOINT": "true"},
            "https://signin.us-east-1.api.aws/v1/token",
            id="dual-stack",
        ),
        pytest.param(
            (),
            {"AWS_ENDPOINT_URL_SIGNIN": f"{BASE_PATH_ENDPOINT}/"},
            f"{BASE_PATH_ENDPOINT}{SIGNIN_PATH}",
            id="signin-endpoint-with-path",
        ),
        pytest.param(
            (),
            {
                "AWS_ENDPOINT_URL": "https://global.example.invalid",
                "AWS_ENDPOINT_URL_SIGNIN": "https://service.example.invalid",
            },
            f"https://service.example.invalid{SIGNIN_PATH}",
            id="signin-endpoint-env-beats-global",
        ),
        pytest.param(
            ("--endpoint-url", "https://ignored.example.invalid"),
            {},
            SIGNIN_URL,
            id="endpoint-url-flag-ignored",
        ),
    ],
)
async def test_login_refresh_endpoint_sets_request_url_and_dpop_htu(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    globals_: tuple[str, ...],
    env_changes: Mapping[str, str | None],
    url: str,
) -> None:
    token = token_with()
    token_path = seed(sandbox, token)
    parts = url.removeprefix("https://").split("/", 1)
    host, path = parts[0], f"/{parts[1]}"

    run, window = await run_refresh(
        aws_cli,
        sandbox,
        stub,
        {("POST", host, path): [signin_token()]},
        env_changes=env_changes,
        globals_=globals_,
    )

    assert run.returncode == 0, run.describe()
    written = stamped_expires_at(run, token_path, window)
    assert run.stdout == refreshed_output(written)
    assert run.stderr == b""
    assert_refresh_request(run, host=host, path=path)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM, url)
    assert run.changes == {
        token_path: (CACHE_FILE_MODE, refreshed_token(token, written))
    }, run.describe()


async def test_login_write_back_preserves_unknown_keys_and_mode(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Unknown keys survive the dict.update and the file keeps its 0644
    # mode; the access token is replaced whole, so its unknown key goes;
    # the response's tokenType and idToken are never written
    # (credentials.py:2602-2619).
    token: dict[str, object] = {
        "idToken": "header.payload.signature",
        "clientId": CLIENT_ID,
        "accessToken": {**ACCESS_TOKEN, "extraInner": [1, 2]},
        "extraField": {"keep": True, "nested": None},
        "dpopKey": SAMPLE_DPOP_PEM,
        "refreshToken": OLD_REFRESH_TOKEN,
        "unicode": "café ☃",
        "count": 7,
    }
    path = seed(sandbox, token, mode=0o644)
    response = signin_token()
    body = json.loads(response.body)
    body["idToken"] = "new.id.token"

    run, window = await run_refresh(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [HTTPResponse.json(body)]}
    )

    assert run.returncode == 0, run.describe()
    written = stamped_expires_at(run, path, window)
    assert run.stdout == refreshed_output(written)
    assert run.stderr == b""
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    expected = {
        "idToken": "header.payload.signature",
        "clientId": CLIENT_ID,
        "accessToken": {
            "accessKeyId": "AKIDNEW",
            "secretAccessKey": "NEW-secret",
            "sessionToken": "NEW-token",
            "accountId": ACCOUNT,
            "expiresAt": written,
        },
        "extraField": {"keep": True, "nested": None},
        "dpopKey": SAMPLE_DPOP_PEM,
        "refreshToken": NEW_REFRESH_TOKEN,
        "unicode": "café ☃",
        "count": 7,
    }
    # The rewrite keeps the mode the seeded file has: 0o644 where the
    # filesystem has mode bits.
    seeded_mode = sandbox.sealed[path][0]
    assert run.changes == {path: (seeded_mode, JsonContent(expected))}, (
        run.describe()
    )


async def test_login_without_cache_file_asks_to_reauthenticate(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.config.write_text(LOGIN_CONFIG, encoding="utf-8")

    run = await run_login(aws_cli, sandbox, stub)

    assert run.returncode == CONFIGURATION_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == load_error(f"{TOKEN_LOAD_PREFIX}{NO_SESSION}")
    assert run.requests == ()
    assert run.changes == {}, run.describe()


@pytest.mark.parametrize(
    ("content", "stderr"),
    [
        pytest.param(
            token_with(refreshToken=MISSING),
            load_error(MISSING_FIELDS),
            id="no-refreshToken",
        ),
        pytest.param(
            b"{not json",
            BytesStartingWith(LOAD_PREFIX.encode()),
            id="invalid-json",
        ),
    ],
)
async def test_login_load_error_is_wrapped_as_configuration_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: object,
    stderr: bytes | BytesStartingWith,
) -> None:
    seed(sandbox, content)

    run = await run_login(aws_cli, sandbox, stub)

    assert run.returncode == CONFIGURATION_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == stderr
    assert run.requests == ()
    assert run.changes == {}, run.describe()


@pytest.mark.parametrize(
    ("changes", "env_changes", "returncode", "stderr"),
    [
        pytest.param(
            {"dpopKey": BAD_BASE64_KEY},
            {},
            GENERAL_ERROR_RC,
            framed_error(KEY_LOAD_PREFIX),
            id="dpopKey-bad-base64",
        ),
        pytest.param(
            {"refreshToken": ""},
            {},
            PARAM_VALIDATION_RC,
            param_error(
                "Invalid length for parameter tokenInput.refreshToken, "
                "value: 0, valid min length: 1"
            ),
            id="refreshToken-empty",
        ),
        pytest.param(
            {},
            NO_REGION,
            CONFIGURATION_RC,
            NO_REGION_ERROR,
            id="no-region",
        ),
    ],
)
async def test_login_refresh_fails_before_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    changes: dict[str, object],
    env_changes: Mapping[str, str | None],
    returncode: int,
    stderr: bytes | BytesStartingWith,
) -> None:
    seed(sandbox, token_with(**changes))

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [signin_token()]},
        env_changes=env_changes,
    )

    assert run.returncode == returncode, run.describe()
    assert run.stdout == b""
    assert run.stderr == stderr
    assert run.requests == ()
    assert run.changes == {}, run.describe()


async def test_login_fresh_disk_token_exports_without_a_region(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # 420 s is in the mandatory window, and the refresh returns the
    # re-read token before creating the signin client (credentials.py:
    # 559-610, 2548-2557), so no region is needed.
    expires_at = expiring_in(420)
    seed(sandbox, token_with(access={"expiresAt": expires_at}))

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [signin_token()]},
        env_changes=NO_REGION,
    )

    assert run.returncode == 0, run.describe()
    assert run.stdout == export_credentials_output(
        "AKIDLOGIN", "LOGIN-secret", "LOGIN-token", isoformat(expires_at)
    )
    assert run.stderr == b""
    assert run.requests == ()
    assert run.changes == {}, run.describe()


@pytest.mark.parametrize(
    ("response", "returncode", "stderr"),
    [
        pytest.param(
            signin_error(
                401,
                "AccessDeniedException",
                error="TOKEN_EXPIRED",
                message="expired",
            ),
            GENERAL_ERROR_RC,
            raw_error(TOKEN_EXPIRED),
            id="access-denied-token-expired",
        ),
        pytest.param(
            HTTPResponse.json(
                {"error": "TOKEN_EXPIRED", "message": "expired"},
                status=401,
                headers={
                    "x-amzn-errortype": (
                        "AccessDeniedException:http://internal.amazon.com/"
                    )
                },
            ),
            GENERAL_ERROR_RC,
            raw_error(TOKEN_EXPIRED),
            id="access-denied-code-in-header",
        ),
        pytest.param(
            signin_error(
                403,
                "com.amazon.signin#AccessDeniedException",
                error="USER_CREDENTIALS_CHANGED",
                message="changed",
            ),
            GENERAL_ERROR_RC,
            raw_error(PASSWORD_CHANGED),
            id="access-denied-user-credentials-changed",
        ),
        pytest.param(
            signin_error(
                403,
                "AccessDeniedException",
                error="INSUFFICIENT_PERMISSIONS",
                message="denied",
            ),
            GENERAL_ERROR_RC,
            raw_error(INSUFFICIENT_PERMISSIONS),
            id="access-denied-insufficient-permissions",
        ),
        pytest.param(
            signin_error(
                403,
                "AccessDeniedException",
                error="server_error",
                message="other",
            ),
            GENERAL_ERROR_RC,
            raw_error(LOGIN_ERROR),
            id="access-denied-other-error",
        ),
        pytest.param(
            signin_error(400, "UnmodeledException", message="odd"),
            CLIENT_ERROR_RC,
            client_error("UnmodeledException", "odd"),
            id="unmodeled-error-code",
        ),
    ],
)
async def test_login_refresh_error_response_leaves_cache_untouched(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    response: HTTPResponse,
    returncode: int,
    stderr: bytes,
) -> None:
    # The default retry policy: none of these errors is retried, so one
    # request is sent (credentials.py:2581-2589).
    seed(sandbox, token_with())

    run = await run_login(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [response]}, max_attempts=None
    )

    assert run.returncode == returncode, run.describe()
    assert run.stdout == b""
    assert run.stderr == stderr
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {}, run.describe()


@pytest.mark.slow
async def test_login_refresh_retries_server_error_with_dpop_proofs(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    seed(sandbox, token_with())
    failure = signin_error(
        500, "InternalServerException", error="server_error", message="boom"
    )

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [failure, failure, failure]},
        max_attempts=None,
    )

    assert run.returncode == CLIENT_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == client_error(
        "InternalServerException",
        "boom",
        details="error: server_error",
        retries=" (reached max retries: 2)",
    )
    assert_refresh_request(run, attempts=3)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM, attempts=3)
    assert run.changes == {}, run.describe()


async def test_login_refresh_too_many_requests_is_not_retried(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The signin model's TooManyRequestsError has no retryable trait, so
    # the standard policy makes one attempt.
    seed(sandbox, token_with())
    throttled = signin_error(
        429, "TooManyRequestsError", error="server_error", message="slow"
    )

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [throttled, signin_token()]},
        max_attempts=None,
    )

    assert run.returncode == CLIENT_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == client_error(
        "TooManyRequestsError", "slow", details="error: server_error"
    )
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {}, run.describe()


async def test_login_refresh_response_without_credentials_fails(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The response's accessToken is read without a check (credentials.py:
    # 2598-2618), so its absence fails the run and nothing is written.
    seed(sandbox, token_with())
    body = json.loads(signin_token().body)
    del body["accessToken"]

    run = await run_login(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [HTTPResponse.json(body)]}
    )

    assert run.returncode == GENERAL_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == framed_error()
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {}, run.describe()


async def test_login_refresh_still_expired_fails_after_write_back(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    token = token_with()
    path = seed(sandbox, token)

    run, window = await run_refresh(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [signin_token(expires_in=0)]},
    )

    assert run.returncode == GENERAL_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == raw_error(STILL_EXPIRED)
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    written = stamped_expires_at(run, path, window, 0)
    assert run.changes == {
        path: (CACHE_FILE_MODE, refreshed_token(token, written))
    }, run.describe()


@needs_permission_checks
async def test_login_write_back_to_read_only_file_fails_after_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The refresh token was already spent on the server when the write
    # fails; the error names the token file.
    path = seed(sandbox, token_with(), mode=0o400)

    run = await run_login(
        aws_cli, sandbox, stub, {SIGNIN_ROUTE: [signin_token()]}
    )

    assert run.returncode == GENERAL_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == framed_error("", os_error_path(sandbox.root / path))
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {}, run.describe()


async def test_login_write_back_with_empty_cache_directory_fails_in_cwd(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Upstream bug, matched for parity: an empty AWS_LOGIN_CACHE_DIRECTORY
    # reads `<key>.json` from the cwd (utils.py:4181-4182), but the
    # write-back's makedirs('') fails (utils.py:3999-4000) after the
    # refresh token was spent.
    directory = Path("cwd-cache")
    seed(sandbox, token_with(), directory=directory)

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        {SIGNIN_ROUTE: [signin_token()]},
        env_changes={"AWS_LOGIN_CACHE_DIRECTORY": ""},
        cwd=sandbox.root / directory,
    )

    assert run.returncode == GENERAL_ERROR_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == framed_error()
    assert_refresh_request(run)
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert run.changes == {}, run.describe()


def assert_sts_signed_by_refreshed_login(run: CliRun) -> None:
    """The AssumeRole call is signed with the refreshed login credentials."""
    (request,) = [
        request
        for request in run.raw_requests
        if request.headers.get("host") == STS_HOST
    ]
    assert_signature(request, "AKIDNEW", "NEW-secret")
    assert request.headers.get("x-amz-security-token") == "NEW-token"


async def test_login_source_profile_refreshes_before_assume_role(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    token = token_with()
    path = seed(sandbox, token, config=SOURCE_CHAIN_CONFIG)
    script = {SIGNIN_ROUTE: [signin_token()], STS_ROUTE: [sts_success_xml()]}

    run, window = await run_refresh(
        aws_cli, sandbox, stub, script, globals_=("--profile", "target")
    )

    assert run.returncode == 0, run.describe()
    assert run.stdout == export_credentials_output(
        "AKIDROLE", "ROLE-secret", "ROLE-token", FUTURE_EXPIRATION
    )
    assert run.stderr == b""
    signin, assume_role = run.requests
    assert (
        signin.method,
        signin.host,
        signin.target,
        signin.query,
        signin.content_type,
        signin.body,
        dict(signin.headers),
        signin.signing_scope,
    ) == (
        "POST",
        SIGNIN_HOST,
        SIGNIN_PATH,
        (),
        JSON_CONTENT_TYPE,
        REFRESH_BODY,
        REFRESH_HEADERS,
        None,
    ), run.describe()
    # AssumeRole as the query protocol's form POST (credentials.py:
    # 793-815), signed for the session's us-east-1 with the refreshed keys.
    assert (
        assume_role.method,
        assume_role.host,
        assume_role.target,
        assume_role.body,
        dict(assume_role.headers),
        assume_role.signing_scope,
    ) == (
        "POST",
        STS_HOST,
        "/",
        {
            "Action": ["AssumeRole"],
            "Version": ["2011-06-15"],
            "RoleSessionName": ["sess"],
            "RoleArn": [ROLE_ARN],
        },
        {
            "x-amz-security-token": "NEW-token",
            "x-amz-sso_bearer_token": None,
            "x-aws-ec2-metadata-token": None,
            "x-aws-ec2-metadata-token-ttl-seconds": None,
            "authorization": "AWS4-HMAC-SHA256",
            "x-amz-date": AMZ_DATE_PLACEHOLDER,
            "content-type": FORM_CONTENT_TYPE,
        },
        ("AKIDNEW", SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts"),
    ), run.describe()
    assert_dpop_bound(run, SAMPLE_DPOP_PEM)
    assert_sts_signed_by_refreshed_login(run)
    written = stamped_expires_at(run, path, window)
    role_cache = role_cache_key(
        {"RoleArn": ROLE_ARN, "RoleSessionName": "sess"}
    )
    # The AssumeRole credentials with AccountId taken from the assumed
    # role's ARN (credentials.py:852-859), in a 0600 file under new
    # directories (utils.py:3999-4004).
    role_entry = RoleCacheContent(
        {
            "Credentials": {
                "AccessKeyId": "AKIDROLE",
                "SecretAccessKey": "ROLE-secret",
                "SessionToken": "ROLE-token",
                "Expiration": FUTURE_EXPIRATION,
                "AccountId": ACCOUNT,
            }
        }
    )
    assert run.changes == {
        "home/.aws/cli": (CREATED_DIRECTORY_MODE, None),
        "home/.aws/cli/cache": (CREATED_DIRECTORY_MODE, None),
        f"home/.aws/cli/cache/{role_cache}.json": (
            CACHE_FILE_MODE,
            role_entry,
        ),
        path: (CACHE_FILE_MODE, refreshed_token(token, written)),
    }, run.describe()


async def test_login_source_profile_ignores_source_region_for_signin(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Without AWS_REGION the session profile `target` has no region, so
    # the signin client creation raises NoRegion inside the source
    # credentials' refresh, before any request; the source profile's
    # eu-west-1 is never consulted. The eu-west-1 routes would answer a
    # client that took it, so such a client would succeed instead.
    seed(sandbox, token_with(), config=SOURCE_CHAIN_CONFIG)
    script = {
        ("POST", "eu-west-1.signin.aws.amazon.com", SIGNIN_PATH): [
            signin_token()
        ],
        ("POST", "sts.eu-west-1.amazonaws.com", "/"): [sts_success_xml()],
    }

    run = await run_login(
        aws_cli,
        sandbox,
        stub,
        script,
        env_changes=NO_REGION,
        globals_=("--profile", "target"),
    )

    assert run.returncode == CONFIGURATION_RC, run.describe()
    assert run.stdout == b""
    assert run.stderr == NO_REGION_ERROR
    assert run.requests == ()
    assert run.changes == {}, run.describe()


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


PARITY_SESSION = "parity-session"
# Public test key from upstream test_credentials.py, never a real login key.
DPOP_KEY = (
    "-----BEGIN EC PRIVATE KEY-----\n"
    "MHcCAQEEIDXxfh2F6vl+AX+tK/jvY5ll6aZ9n8sI2ODsWCmrsxSDoAoGCCqGSM49\n"
    "AwEHoUQDQgAERKnl1X15pEx7ebbMQ0dFw6VeOuCjEuh3NT8dwnBHYyF/7YDy8+Fu\n"
    "Cx+4wgiSs9sRD3LaDKCjIbbmEq07Jw59YQ==\n"
    "-----END EC PRIVATE KEY-----\n"
)
DECOY_LOGIN_CONFIG = (
    f"[default]\nlogin_session = {PARITY_SESSION}\n"
    + file_credentials("DECOY")
)


def write_json(path: Path, data: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_login_token(directory: Path, expires_at: str) -> Path:
    key = hashlib.sha256(PARITY_SESSION.encode()).hexdigest()
    token = {
        "accessToken": {
            "accessKeyId": "AKIDLOGIN",
            "secretAccessKey": "LOGIN-secret",
            "sessionToken": "LOGIN-token",
            "accountId": "123456789012",
            "expiresAt": expires_at,
        },
        "refreshToken": "old-refresh-token",
        "clientId": "synthetic-client",
        "dpopKey": DPOP_KEY,
    }
    return write_json(directory / f"{key}.json", token)


def endpoint(request: RecordedHTTPRequest) -> str:
    path = urlsplit(request.effective_path).path
    return f"{request.method} https://{request.headers['host']}{path}"


async def test_login_missing_token_does_not_fall_through_to_static_keys(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, DECOY_LOGIN_CONFIG)
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)
    assert b"login" in result[1]


@pytest.mark.parametrize(
    "override", [False, True], ids=["cached", "cache-override"]
)
async def test_login_cached_credentials_sign_request(
    aws_cli: str, tmp_path: Path, override: bool
) -> None:
    cache = tmp_path / ("login-cache" if override else ".aws/login/cache")
    write_login_token(cache, FUTURE)
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        if override:
            env["AWS_LOGIN_CACHE_DIRECTORY"] = str(cache)
        write_config(env, DECOY_LOGIN_CONFIG)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "LOGIN", "LOGIN-token")


async def test_login_expired_credentials_refresh_with_dpop_proof(
    aws_cli: str, tmp_path: Path
) -> None:
    cache = write_login_token(tmp_path / ".aws/login/cache", PAST)
    refreshed = HTTPResponse.json(
        {
            "accessToken": {
                "accessKeyId": "AKIDNEW",
                "secretAccessKey": "NEW-secret",
                "sessionToken": "NEW-token",
            },
            "refreshToken": "new-refresh-token",
            "expiresIn": 900,
            "tokenType": "aws_sigv4",
        }
    )
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        write_config(env, DECOY_LOGIN_CONFIG)
        _, stderr, rc = await list_bucket(
            aws_cli,
            server,
            env,
            responses=[refreshed, empty_list_objects_response()],
        )
    assert rc == 0, stderr.decode()
    refresh, s3 = server.requests
    token_url = "https://us-east-1.signin.aws.amazon.com/v1/token"
    assert endpoint(refresh) == f"POST {token_url}"
    assert json.loads(refresh.text) == {
        "clientId": "synthetic-client",
        "refreshToken": "old-refresh-token",
        "grantType": "refresh_token",
    }
    header, claims, signature = (
        base64.urlsafe_b64decode(part + "==")
        for part in refresh.headers["dpop"].split(".")
    )
    header, claims = json.loads(header), json.loads(claims)
    assert (header["typ"], header["alg"]) == ("dpop+jwt", "ES256")
    assert (claims["htm"], claims["htu"]) == ("POST", token_url)
    assert len(signature) == 64  # raw ES256 r || s
    assert s3.headers["x-amz-security-token"] == "NEW-token"
    assert_signature(s3, "AKIDNEW", "NEW-secret")
    saved = json.loads(cache.read_text())
    assert saved["accessToken"]["accessKeyId"] == "AKIDNEW"
    assert saved["refreshToken"] == "new-refresh-token"
    assert saved["dpopKey"] == DPOP_KEY
