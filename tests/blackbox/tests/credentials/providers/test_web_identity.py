import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, quote_plus

import pytest
from localstub import HTTPResponse, RecordedHTTPRequest

from credhelpers import (
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    STS_NAMESPACE,
    BytesStartingWith,
    CliRun,
    FileChanges,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    created_cache_directories,
    credential_runtime,
    export_credentials_output,
    rejected_role_request,
    role_cache_key,
    routed,
    run_export_credentials,
    seed_cli_cache,
    sts_error_xml,
    sts_success_xml,
    write_config,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# botocore AssumeRoleWithWebIdentityProvider (credentials.py:1886-1984),
# its fetcher (credentials.py:955-1027), and FileWebIdentityTokenLoader
# (utils.py:3215-3222) through `aws configure export-credentials`. The
# web-identity cases that compete with AssumeRole live in
# test_assume_role.py.
EnvChanges = Mapping[str, str | None]

ACCOUNT: Final = "123456789012"
WEB_ROLE: Final = "arn:aws:iam::210987654321:role/web"
VECTOR_ROLE: Final = f"arn:aws:iam::{ACCOUNT}:role/blackbox-credential-vector"
ENV_ROLE: Final = f"arn:aws:iam::{ACCOUNT}:role/EnvRole"
TOKEN: Final = "synthetic-web-token"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
ACTION: Final = "AssumeRoleWithWebIdentity"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
# credentials.py:817-820 appends `botocore-session-<int(time())>`; the
# harness normalizer turns the epoch into this placeholder.
GENERATED_NAME: Final = "botocore-session-<epoch>"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded; charset=utf-8"
LOAD_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
PARAM_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (ParamValidation): "
    "Parameter validation failed:\n"
)
# credentials.py:1952-1960, including the missing space before
# "configuration".
NO_ROLE_ARN: Final = (
    "The provided profile or the current environment is configured to "
    "assume role with web identity but has no role ARN configured. Ensure "
    "that the profile has the role_arnconfiguration set or the "
    "AWS_ROLE_ARN env var is set."
)
CONFIGURATION_RC: Final = 253
PARAM_VALIDATION_RC: Final = 252
CLIENT_ERROR_RC: Final = 254
STATIC_CREDENTIALS: Final = """\
[default]
aws_access_key_id = AKIDSTATIC
aws_secret_access_key = STATIC-secret
"""
NO_REGION: Final[EnvChanges] = {"AWS_REGION": None, "AWS_DEFAULT_REGION": None}
# A response whose elements come in the API reference's order rather than
# the model's, with members export never prints; the parser reads them by
# name (parsers.py:612-643).
FULL_RESPONSE_BODY: Final = (
    f'<{ACTION}Response xmlns="{STS_NAMESPACE}"><{ACTION}Result>'
    "<SubjectFromWebIdentityToken>amzn1.account.AF6RHO7KZU5XRVQJGXK6HB56KR2A"
    "</SubjectFromWebIdentityToken>"
    "<Audience>client.5498841531868486423.1548@apps.example.com</Audience>"
    "<AssumedRoleUser><Arn>arn:aws:sts::210987654321:assumed-role/w/s</Arn>"
    "<AssumedRoleId>AROAWEB:s</AssumedRoleId></AssumedRoleUser>"
    "<Credentials><SessionToken>WTOKEN</SessionToken>"
    "<SecretAccessKey>WSECRET</SecretAccessKey>"
    "<Expiration>2099-01-01T00:00:00Z</Expiration>"
    "<AccessKeyId>ASIAWEB</AccessKeyId></Credentials>"
    "<Provider>www.amazon.com</Provider>"
    "<PackedPolicySize>6</PackedPolicySize>"
    f"</{ACTION}Result><ResponseMetadata><RequestId>req-w</RequestId>"
    f"</ResponseMetadata></{ACTION}Response>"
).encode()


def web_response(identity: str = "WEB") -> HTTPResponse:
    return sts_success_xml(
        action=ACTION,
        access_key=f"ASIA{identity}",
        secret_key=f"{identity}-secret",
        session_token=f"{identity}-token",
        assumed_role_id=f"AROA{identity}:s",
        arn=f"arn:aws:sts::{ACCOUNT}:assumed-role/web/s",
        request_id=f"req-{identity}",
    )


def cached_web(identity: str = "WEB") -> RoleCacheContent:
    """The role-cache entry for `web_response`, by what botocore reads.

    The AssumedRoleUser ARN's account becomes Credentials.AccountId.
    """
    return RoleCacheContent(
        {
            "Credentials": {
                "AccessKeyId": f"ASIA{identity}",
                "SecretAccessKey": f"{identity}-secret",
                "SessionToken": f"{identity}-token",
                "Expiration": FUTURE_EXPIRATION,
                "AccountId": ACCOUNT,
            }
        }
    )


def exported(identity: str = "WEB") -> bytes:
    return export_credentials_output(
        f"ASIA{identity}",
        f"{identity}-secret",
        f"{identity}-token",
        FUTURE_EXPIRATION,
    )


def web_body(*pairs: tuple[str, str]) -> bytes:
    """The AssumeRoleWithWebIdentity form body, `pairs` after Version.

    GENERATED_NAME is the normalizer's placeholder and stays raw.
    """
    fields = [("Action", ACTION), ("Version", "2011-06-15"), *pairs]
    return "&".join(
        f"{quote_plus(key)}="
        + (value if value == GENERATED_NAME else quote_plus(value))
        for key, value in fields
    ).encode()


def default_body(token: str = TOKEN, role: str = WEB_ROLE) -> bytes:
    """The body for `role` and `token` with a generated session name."""
    return web_body(
        ("RoleArn", role),
        ("RoleSessionName", GENERATED_NAME),
        ("WebIdentityToken", token),
    )


def web_call(
    body: bytes, *, host: str = STS_HOST, target: str = "/"
) -> NormalizedRequest:
    """One AssumeRoleWithWebIdentity call without any SigV4 material.

    The fetcher builds its client with signature_version=UNSIGNED
    (credentials.py:1009-1020), so neither Authorization, X-Amz-Date, nor
    a security token is sent.
    """
    headers = {"content-type": FORM_CONTENT_TYPE}
    return NormalizedRequest(
        method="POST",
        host=host,
        path=target,
        target=target,
        query=(),
        content_type=FORM_CONTENT_TYPE,
        body_bytes=body,
        headers=tuple((name, headers.get(name)) for name in COMPARED_HEADERS),
        user_agent=None,
        signing_scope=None,
    )


def cache_path(args: Mapping[str, object]) -> str:
    return f"home/{CLI_CACHE.as_posix()}/{role_cache_key(args)}.json"


def created_cache(
    args: Mapping[str, object], content: RoleCacheContent
) -> FileChanges:
    """The changes of a run that created the role cache with one entry.

    `args` are the arguments the entry's key is made from; the entry is
    written 0600 (utils.py:3991-4006).
    """
    changes = created_cache_directories()
    changes[cache_path(args)] = (CACHE_FILE_MODE, content)
    return changes


def load_error(message: str) -> bytes:
    return f"{LOAD_PREFIX}{message}\n".encode()


def param_error(line: str) -> bytes:
    return f"{PARAM_PREFIX}{line}\n".encode()


def web_profile(
    token_file: str | os.PathLike[str] | None,
    *,
    role: str | None = WEB_ROLE,
    extra: str = "",
) -> str:
    lines = ["[default]"]
    if role is not None:
        lines.append(f"role_arn = {role}")
    if token_file is not None:
        lines.append(f"web_identity_token_file = {os.fspath(token_file)}")
    return "\n".join(lines) + "\n" + extra


async def run_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Mapping[RouteKey, Sequence[HTTPResponse]] | None = None,
    *,
    env: EnvChanges | None = None,
    globals_: Sequence[str] = (),
    cwd: Path | None = None,
) -> CliRun:
    """Run export-credentials once with STS scripted by route.

    Unscripted requests get the harness's 400 tripwire.
    """
    server, proxy = stub
    run_env = sandbox.env(proxy)
    for key, value in (env or {}).items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    routes = dict(script or {})
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        run_env,
        globals_=globals_,
        cwd=cwd,
        handlers={server: lambda: routed(routes)},
    )


def assert_exported(run: CliRun, identity: str = "WEB") -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        exported(identity),
        b"",
    ), run.describe()


def assert_static(run: CliRun) -> None:
    """The credentials file answered: no request and nothing written."""
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        export_credentials_output("AKIDSTATIC", "STATIC-secret"),
        b"",
    ), run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


def assert_failed(run: CliRun, returncode: int, stderr: bytes) -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        b"",
        stderr,
    ), run.describe()


def assert_rejected(run: CliRun, returncode: int, stderr: bytes) -> None:
    """A failure before any request that leaves the sandbox untouched."""
    assert_failed(run, returncode, stderr)
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


async def test_web_identity_profile_sends_unsigned_call_and_caches_response(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token))
    response = HTTPResponse.raw(
        FULL_RESPONSE_BODY, headers={"Content-Type": "text/xml"}
    )

    run = await run_scenario(aws_cli, sandbox, stub, {STS_ROUTE: [response]})

    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        export_credentials_output(
            "ASIAWEB", "WSECRET", "WTOKEN", FUTURE_EXPIRATION
        ),
        b"",
    ), run.describe()
    assert run.requests == (web_call(default_body()),), run.describe()
    # A key the real CLI wrote.
    key = "8cf789dc0f2dfbd28563568437f1ad8466bf2f19"
    cached = {
        "Credentials": {
            "AccessKeyId": "ASIAWEB",
            "SecretAccessKey": "WSECRET",
            "SessionToken": "WTOKEN",
            "Expiration": FUTURE_EXPIRATION,
            "AccountId": "210987654321",
        }
    }
    assert run.changes == {
        **created_cache_directories(),
        f"home/{CLI_CACHE.as_posix()}/{key}.json": (
            CACHE_FILE_MODE,
            RoleCacheContent(cached),
        ),
    }, run.describe()


PROFILE_TOKEN_LINE: Final = "web_identity_token_file = {profile_token}\n"


@pytest.mark.parametrize(
    ("profile", "env", "pairs", "key_args"),
    [
        pytest.param(
            # An empty token-file key keeps AssumeRole from claiming the
            # profile and is then masked by the variable.
            f"role_arn = {WEB_ROLE}\nweb_identity_token_file =\n",
            {"AWS_WEB_IDENTITY_TOKEN_FILE": "{env_token}"},
            (
                ("RoleArn", WEB_ROLE),
                ("RoleSessionName", GENERATED_NAME),
                ("WebIdentityToken", "env-web-token"),
            ),
            {"RoleArn": WEB_ROLE, "WebIdentityToken": "env-web-token"},
            id="token-file-from-env-role-from-profile",
        ),
        pytest.param(
            PROFILE_TOKEN_LINE,
            {"AWS_ROLE_ARN": ENV_ROLE},
            (
                ("RoleArn", ENV_ROLE),
                ("RoleSessionName", GENERATED_NAME),
                ("WebIdentityToken", "profile-web-token"),
            ),
            {"RoleArn": ENV_ROLE, "WebIdentityToken": "profile-web-token"},
            id="role-from-env-token-file-from-profile",
        ),
        pytest.param(
            f"role_arn = {WEB_ROLE}\n{PROFILE_TOKEN_LINE}"
            "role_session_name = profile-session\n",
            {
                "AWS_WEB_IDENTITY_TOKEN_FILE": "{env_token}",
                "AWS_ROLE_ARN": ENV_ROLE,
                "AWS_ROLE_SESSION_NAME": "env-session",
            },
            (
                ("RoleSessionName", "env-session"),
                ("RoleArn", ENV_ROLE),
                ("WebIdentityToken", "env-web-token"),
            ),
            {
                "RoleArn": ENV_ROLE,
                "RoleSessionName": "env-session",
                "WebIdentityToken": "env-web-token",
            },
            id="env-beats-profile-per-key",
        ),
        pytest.param(
            f"role_arn = {WEB_ROLE}\n{PROFILE_TOKEN_LINE}"
            "role_session_name = profile-session\n",
            {"AWS_ROLE_SESSION_NAME": ""},
            (
                ("RoleSessionName", GENERATED_NAME),
                ("RoleArn", WEB_ROLE),
                ("WebIdentityToken", "profile-web-token"),
            ),
            {"RoleArn": WEB_ROLE, "WebIdentityToken": "profile-web-token"},
            id="empty-env-session-name-masks-profile",
        ),
    ],
)
async def test_web_identity_each_key_prefers_env_over_profile(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    profile: str,
    env: dict[str, str],
    pairs: tuple[tuple[str, str], ...],
    key_args: dict[str, str],
) -> None:
    paths = {
        "profile_token": sandbox.write("profile-token", "profile-web-token"),
        "env_token": sandbox.write("env-token", "env-web-token"),
    }
    sandbox.config.write_text("[default]\n" + profile.format(**paths))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [web_response()]},
        env={key: value.format(**paths) for key, value in env.items()},
    )

    # credentials.py:1918-1944 falls back key by key, and a set variable
    # wins even when empty.
    assert_exported(run)
    assert run.requests == (web_call(web_body(*pairs)),), run.describe()
    assert run.changes == created_cache(key_args, cached_web()), run.describe()


async def test_web_identity_explicit_profile_ignores_env_role_arn(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token, role=None))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        env={"AWS_ROLE_ARN": ENV_ROLE},
        globals_=("--profile", "default"),
    )

    assert_rejected(run, CONFIGURATION_RC, load_error(NO_ROLE_ARN))


async def test_web_identity_explicit_profile_ignores_env_session_name(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(
        web_profile(token, extra="role_session_name = profile-session\n")
    )

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [web_response()]},
        env={"AWS_ROLE_SESSION_NAME": "env-session"},
        globals_=("--profile", "default"),
    )

    assert_exported(run)
    assert run.requests == (
        web_call(
            web_body(
                ("RoleSessionName", "profile-session"),
                ("RoleArn", WEB_ROLE),
                ("WebIdentityToken", TOKEN),
            )
        ),
    ), run.describe()
    key = {
        "RoleArn": WEB_ROLE,
        "RoleSessionName": "profile-session",
        "WebIdentityToken": TOKEN,
    }
    assert run.changes == created_cache(key, cached_web()), run.describe()


async def test_web_identity_env_inputs_beat_static_files_without_flag(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.credentials.write_text(STATIC_CREDENTIALS)
    sandbox.config.write_text(
        "[default]\n"
        "aws_access_key_id = AKIDCONFIG\n"
        "aws_secret_access_key = CONFIG-secret\n"
    )

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [web_response()]},
        env={
            "AWS_WEB_IDENTITY_TOKEN_FILE": str(token),
            "AWS_ROLE_ARN": ENV_ROLE,
        },
    )

    # Only --profile disables the env inputs (test_chain_order.py
    # covers AWS_PROFILE); web identity runs before both shared files in
    # the chain.
    assert_exported(run)
    assert run.requests == (web_call(default_body(role=ENV_ROLE)),), (
        run.describe()
    )
    assert run.changes == created_cache(
        {"RoleArn": ENV_ROLE, "WebIdentityToken": TOKEN}, cached_web()
    ), run.describe()


async def test_web_identity_empty_env_token_file_falls_through(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token))
    sandbox.credentials.write_text(STATIC_CREDENTIALS)

    run = await run_scenario(
        aws_cli, sandbox, stub, env={"AWS_WEB_IDENTITY_TOKEN_FILE": ""}
    )

    # The empty variable masks the profile's path, the provider returns
    # None (credentials.py:1946-1950), and the next one answers.
    assert_static(run)


async def test_web_identity_empty_profile_token_file_finds_no_credentials(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(web_profile(""))

    run = await run_scenario(aws_cli, sandbox, stub)

    # The key's presence still keeps AssumeRole out (credentials.py:
    # 1633-1642) while the empty path makes web identity return None.
    assert_rejected(
        run,
        CONFIGURATION_RC,
        b"\naws: [ERROR]: An error occurred (Configuration): "
        b"Unable to retrieve credentials: no credentials found\n",
    )


@pytest.mark.parametrize(
    ("role", "env"),
    [
        pytest.param(
            WEB_ROLE, {"AWS_ROLE_ARN": ""}, id="empty-env-role"
        ),
        pytest.param(None, {}, id="no-role"),
    ],
)
async def test_web_identity_without_role_arn_raises_at_load(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    role: str | None,
    env: dict[str, str],
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token, role=role))

    run = await run_scenario(aws_cli, sandbox, stub, env=env)

    assert_rejected(run, CONFIGURATION_RC, load_error(NO_ROLE_ARN))


@pytest.mark.parametrize(
    ("content", "sent"),
    [
        pytest.param(b"tok+/= \n", "tok+/= \n", id="quote-plus-encoding"),
        pytest.param(
            "tök€n😀".encode(),
            "tök€n😀",
            id="non-ascii-utf8",
            # The public AWS CLI does the same there.
            marks=pytest.mark.skipif(
                os.name != "posix",
                reason="Windows reads the token file in the locale "
                "encoding, not UTF-8",
            ),
        ),
    ],
)
async def test_web_identity_token_read_in_text_mode_and_sent_untrimmed(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: bytes,
    sent: str,
) -> None:
    token = sandbox.write("token", content)
    sandbox.config.write_text(web_profile(token))

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [web_response()]}
    )

    # utils.py:3215-3222 reads the file as UTF-8 text and does not strip
    # it; the cache key holds the decoded text.
    assert_exported(run)
    assert run.requests == (web_call(default_body(sent)),), run.describe()
    key = {"RoleArn": WEB_ROLE, "WebIdentityToken": sent}
    assert run.changes == created_cache(key, cached_web()), run.describe()


@pytest.mark.parametrize(
    ("settings", "content", "pairs", "key"),
    [
        pytest.param(
            "role_session_name = vector-session\n",
            TOKEN,
            (
                ("RoleSessionName", "vector-session"),
                ("RoleArn", VECTOR_ROLE),
                ("WebIdentityToken", TOKEN),
            ),
            "83a7abe5d957bc08a21f2f6db1ab64e65ae201c9",
            id="explicit-session-name",
        ),
        pytest.param(
            "",
            f"{TOKEN}\n",
            (
                ("RoleArn", VECTOR_ROLE),
                ("RoleSessionName", GENERATED_NAME),
                ("WebIdentityToken", f"{TOKEN}\n"),
            ),
            "ffdb428cbbeecbda94217e053642d9f813b5d61e",
            id="trailing-newline-in-key",
        ),
    ],
)
async def test_web_identity_cache_key_matches_vector(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    settings: str,
    content: str,
    pairs: tuple[tuple[str, str], ...],
    key: str,
) -> None:
    token = sandbox.write("token", content)
    sandbox.config.write_text(
        web_profile(token, role=VECTOR_ROLE, extra=settings)
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [web_response()]}
    )

    # The key is the SHA-1 of the arguments' sorted JSON (credentials.py:
    # 830-850), spelled out rather than computed by role_cache_key.
    assert_exported(run)
    assert run.requests == (web_call(web_body(*pairs)),), run.describe()
    assert run.changes == {
        **created_cache_directories(),
        f"home/{CLI_CACHE.as_posix()}/{key}.json": (
            CACHE_FILE_MODE,
            cached_web(),
        ),
    }, run.describe()


async def test_web_identity_relative_token_path_resolves_against_cwd(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.write("work/token", "relative-web-token")
    sandbox.config.write_text(web_profile("token"))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [web_response()]},
        cwd=sandbox.root / "work",
    )

    assert_exported(run)
    assert run.requests == (web_call(default_body("relative-web-token")),), (
        run.describe()
    )
    key = {"RoleArn": WEB_ROLE, "WebIdentityToken": "relative-web-token"}
    assert run.changes == created_cache(key, cached_web()), run.describe()


async def test_web_identity_unexpanded_tilde_token_path_raises_at_load(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # The file exists under HOME, but the path is opened as written:
    # FileWebIdentityTokenLoader does not expand `~` (utils.py:3215-3222).
    sandbox.write("home/nope-tok", TOKEN)
    sandbox.config.write_text(web_profile("~/nope-tok"))

    run = await run_scenario(aws_cli, sandbox, stub)

    # The fetcher reads the token for its cache key when load() builds it
    # (credentials.py:994-1007, 724), inside the export try. The OSError
    # text after the path's name is CPython's and the C library's.
    assert (run.returncode, run.stdout, run.stderr) == (
        CONFIGURATION_RC,
        b"",
        BytesStartingWith(LOAD_PREFIX.encode(), (b"~/nope-tok",)),
    ), run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


async def test_web_identity_empty_token_fails_validation_before_send(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", "")
    sandbox.config.write_text(web_profile(token))

    run = await run_scenario(aws_cli, sandbox, stub)

    assert_rejected(
        run,
        PARAM_VALIDATION_RC,
        param_error(
            "Invalid length for parameter WebIdentityToken, value: 0, "
            "valid min length: 4"
        ),
    )


async def test_web_identity_ignores_assume_role_only_settings(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(
        web_profile(
            token,
            extra=(
                "duration_seconds = 100\n"
                "external_id = x\n"
                f"mfa_serial = arn:aws:iam::{ACCOUNT}:mfa/user\n"
            ),
        )
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [web_response()]}
    )

    # credentials.py:1962-1965 reads only role_session_name, so there is
    # no MFA prompt and no invalid DurationSeconds.
    assert_exported(run)
    assert run.requests == (web_call(default_body()),), run.describe()
    assert run.changes == created_cache(
        {"RoleArn": WEB_ROLE, "WebIdentityToken": TOKEN}, cached_web()
    ), run.describe()


async def test_web_identity_service_error_raises_client_error(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token))
    rejection = sts_error_xml(
        "InvalidIdentityToken", "stubbed token rejection", status=400
    )

    run = await run_scenario(aws_cli, sandbox, stub, {STS_ROUTE: [rejection]})

    # With one attempt the first attempt is the last (retries/standard.py:
    # 440-454), so the message carries the max-retries suffix. A failed
    # call caches nothing.
    assert_failed(
        run,
        CLIENT_ERROR_RC,
        b"\naws: [ERROR]: An error occurred (InvalidIdentityToken) when "
        b"calling the AssumeRoleWithWebIdentity operation (reached max "
        b"retries: 0): stubbed token rejection\n",
    )
    assert run.requests == (web_call(default_body()),), run.describe()
    assert run.changes == {}, run.describe()


@pytest.mark.parametrize(
    ("seeded_token", "requests", "changes"),
    [
        pytest.param(TOKEN, (), {}, id="hit"),
        pytest.param(
            "older-web-token",
            (web_call(default_body()),),
            {
                cache_path({"RoleArn": WEB_ROLE, "WebIdentityToken": TOKEN}): (
                    CACHE_FILE_MODE,
                    cached_web("CACHED"),
                )
            },
            id="token-changed-key-misses",
        ),
    ],
)
async def test_web_identity_cache_is_keyed_by_token_contents(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    seeded_token: str,
    requests: tuple[NormalizedRequest, ...],
    changes: FileChanges,
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token))
    seed_cli_cache(
        sandbox.home,
        role_cache_key(
            {"RoleArn": WEB_ROLE, "WebIdentityToken": seeded_token}
        ),
        {
            "Credentials": {
                "AccessKeyId": "ASIACACHED",
                "SecretAccessKey": "CACHED-secret",
                "SessionToken": "CACHED-token",
                "Expiration": FUTURE_EXPIRATION,
            }
        },
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [web_response("CACHED")]}
    )

    # The key holds the token's contents: the same token hits the seeded
    # entry, and a changed one misses it and adds an entry beside it.
    assert_exported(run, "CACHED")
    assert run.requests == requests, run.describe()
    assert run.changes == changes, run.describe()


WEST_REGION: Final[EnvChanges] = {**NO_REGION, "AWS_REGION": "us-west-2"}
SERVICE_ENDPOINT_WITH_PATH: Final = "https://sts-env.example.test:8443/svc"


@pytest.mark.parametrize(
    ("env", "host", "path"),
    [
        pytest.param(
            WEST_REGION, "sts.us-west-2.amazonaws.com", "/", id="region"
        ),
        pytest.param(
            NO_REGION, "sts.amazonaws.com", "/", id="no-region-global"
        ),
        pytest.param(
            {
                **NO_REGION,
                "AWS_ENDPOINT_URL_STS": SERVICE_ENDPOINT_WITH_PATH,
            },
            "sts-env.example.test:8443",
            "/svc",
            id="no-region-service-endpoint-env",
        ),
    ],
)
async def test_web_identity_endpoint_matrix_never_needs_region(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    env: EnvChanges,
    host: str,
    path: str,
) -> None:
    token = sandbox.write("token", TOKEN)
    sandbox.config.write_text(web_profile(token))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {("POST", host, path): [web_response()]},
        env=env,
    )

    # The unsigned call needs no signing region, so a configured endpoint
    # without a region is still sent. test_config_resolution.py owns the
    # endpoint-source precedence.
    assert_exported(run)
    assert run.requests == (
        web_call(default_body(), host=host, target=path),
    ), run.describe()
    assert run.changes == created_cache(
        {"RoleArn": WEB_ROLE, "WebIdentityToken": TOKEN}, cached_web()
    ), run.describe()


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


ROLE_ARN = "arn:aws:iam::123456789012:role/blackbox-credential-parity"
ROLE_PROFILE = (
    f"[default]\nrole_arn = {ROLE_ARN}\nrole_session_name = parity-session\n"
)


def assert_web_identity_request(request: RecordedHTTPRequest) -> None:
    fields = parse_qs(request.text)
    assert fields["Action"] == ["AssumeRoleWithWebIdentity"]
    assert fields["RoleArn"] == [ROLE_ARN]
    assert fields["RoleSessionName"] == ["parity-session"]
    assert fields["WebIdentityToken"] == ["synthetic-web-token"]
    assert "authorization" not in request.headers


def write_web_token(tmp_path: Path) -> Path:
    path = tmp_path / "web-token"
    path.write_text("synthetic-web-token")
    return path


async def test_credentials_web_identity_file_sends_unsigned_web_identity_role(
    aws_cli: str, tmp_path: Path
) -> None:
    path = write_web_token(tmp_path)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, ROLE_PROFILE + f"web_identity_token_file = {path}\n")
        request = await rejected_role_request(aws_cli, server, env)
    assert_web_identity_request(request)


async def test_credentials_web_identity_env_sends_unsigned_web_identity_role(
    aws_cli: str, tmp_path: Path
) -> None:
    path = write_web_token(tmp_path)
    async with credential_runtime(tmp_path) as (server, env):
        env.update(
            AWS_ROLE_ARN=ROLE_ARN,
            AWS_ROLE_SESSION_NAME="parity-session",
            AWS_WEB_IDENTITY_TOKEN_FILE=str(path),
        )
        request = await rejected_role_request(aws_cli, server, env)
    assert_web_identity_request(request)
