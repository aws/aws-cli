from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, quote_plus, urlsplit

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    AsyncTLSInterceptProxy,
    HTTPResponse,
    RecordedHTTPRequest,
)

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    SCOPE_DATE_PLACEHOLDER,
    BytesStartingWith,
    CliRun,
    FileChanges,
    HandlerFactory,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_signature,
    created_cache_directories,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    json_process,
    metadata_credentials,
    os_error_path,
    process_credentials,
    rejected_role_request,
    role_cache_key,
    routed,
    run_export_credentials,
    seed_cli_cache,
    sts_success_xml,
    write_config,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# botocore AssumeRoleProvider (credentials.py:1543-1883) and its fetcher
# (credentials.py:719-952) through `aws configure export-credentials`.
# Web-identity env and token-file handling lives in
# test_web_identity.py, and the MFA prompt in test_assume_role_mfa.py.
EnvChanges = Mapping[str, str | None]
CacheEntry = tuple[Mapping[str, object], RoleCacheContent]

ACCOUNT: Final = "123456789012"
ROLE_A: Final = f"arn:aws:iam::{ACCOUNT}:role/RoleA"
ROLE_B: Final = f"arn:aws:iam::{ACCOUNT}:role/RoleB"
VECTOR_ROLE: Final = f"arn:aws:iam::{ACCOUNT}:role/blackbox-credential-vector"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
WIRE_EXPIRATION: Final = "2099-01-01T00:00:00Z"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
STS_VERSION: Final = "2011-06-15"
# credentials.py:817-820 appends `botocore-session-<int(time())>`; the
# harness normalizer turns the epoch into this placeholder.
GENERATED_NAME: Final = "botocore-session-<epoch>"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded"
SIGV4: Final = "AWS4-HMAC-SHA256"
SOURCE_PROFILE: Final = """\
[profile src]
aws_access_key_id = AKIDSRC
aws_secret_access_key = SRC-secret
"""
ROLE_PROFILE: Final = f"""\
[default]
role_arn = {ROLE_A}
source_profile = src
"""
STATIC_ROLE_CONFIG: Final = ROLE_PROFILE + "\n" + SOURCE_PROFILE
# The source chain's ConfigProvider reads the token from the config file
# (credentials.py:1461-1484); a credentials-file section without
# aws_access_key_id contributes nothing (credentials.py:1397-1415).
TOKEN_SOURCE_PROFILE: Final = (
    SOURCE_PROFILE + "aws_session_token = SRC-token\n"
)
# exportcreds.py:266-279 wraps every load() error; the deferred fetch runs
# outside that try and reaches the CLI handlers raw (errorhandler.py:
# 116-131).
LOAD_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
GENERAL_PREFIX: Final = b"\naws: [ERROR]: "
PARAM_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (ParamValidation): "
    "Parameter validation failed:\n"
)
NO_REGION_ERROR: Final = (
    b"\naws: [ERROR]: An error occurred (NoRegion): You must specify a "
    b'region. You can also configure your region by running "aws '
    b'configure".\n'
)
CONFIGURATION_RC: Final = 253
PARAM_VALIDATION_RC: Final = 252
GENERAL_RC: Final = 255
# credentials.py:719-789: an entry is expired inside 15 minutes. Each
# seeded expiry keeps 60 s from that window.
FRESH_ENTRY_SECONDS: Final = 16 * 60
STALE_ENTRY_SECONDS: Final = 14 * 60
# Inside the 10-minute mandatory window but 2 minutes past 300 s.
SHORT_LIVED_SECONDS: Final = 7 * 60
IMDS_HOST: Final = "169.254.169.254"
IMDS_TOKEN_PATH: Final = "/latest/api/token"
IMDS_ROLE_PATH: Final = "/latest/meta-data/iam/security-credentials/"
IMDS_ROLE: Final = "blackbox-role"
IMDS_TOKEN: Final = "imds-token"
# botocore sends its default IMDS token TTL on the PUT (utils.py:341, 412).
IMDS_TOKEN_TTL: Final = "21600"


@pytest_asyncio.fixture
async def metadata() -> AsyncIterator[AsyncHTTPTestServer]:
    async with AsyncHTTPTestServer() as server:
        yield server


def role_response(
    identity: str = "ROLEA",
    *,
    action: str = "AssumeRole",
    expiration: str = WIRE_EXPIRATION,
) -> HTTPResponse:
    """A successful STS answer whose credentials are named by `identity`."""
    return sts_success_xml(
        action=action,
        access_key=f"ASIA{identity}",
        secret_key=f"{identity}-secret",
        session_token=f"{identity}-token",
        expiration=expiration,
        assumed_role_id=f"AROA{identity}:s",
        arn=f"arn:aws:sts::{ACCOUNT}:assumed-role/{identity}/s",
    )


def cached_role(
    identity: str = "ROLEA", *, expiration: str = FUTURE_EXPIRATION
) -> RoleCacheContent:
    """The role-cache entry for `role_response(identity)`.

    credentials.py:752-759 caches the parsed response with AccountId added
    from the assumed-role ARN (credentials.py:852-859).
    """
    return RoleCacheContent(
        {
            "Credentials": {
                "AccessKeyId": f"ASIA{identity}",
                "SecretAccessKey": f"{identity}-secret",
                "SessionToken": f"{identity}-token",
                "Expiration": expiration,
                "AccountId": ACCOUNT,
            }
        }
    )


def exported(
    identity: str = "ROLEA", expiration: str = FUTURE_EXPIRATION
) -> bytes:
    return export_credentials_output(
        f"ASIA{identity}",
        f"{identity}-secret",
        f"{identity}-token",
        expiration,
    )


def form_body(action: str, *pairs: tuple[str, str]) -> bytes:
    """A query-protocol body: Action, Version, then `pairs`.

    NormalizedRequest compares the decoded form, so the pairs' order is
    the sender's. GENERATED_NAME stays raw: it is the normalizer's
    placeholder, not a sent value.
    """
    fields = [("Action", action), ("Version", STS_VERSION), *pairs]
    return "&".join(
        f"{quote_plus(key)}="
        + (value if value == GENERATED_NAME else quote_plus(value))
        for key, value in fields
    ).encode()


def assume_role_body(role: str = ROLE_A) -> bytes:
    """The AssumeRole body for `role` with a generated session name."""
    return form_body(
        "AssumeRole", ("RoleArn", role), ("RoleSessionName", GENERATED_NAME)
    )


def compared(values: Mapping[str, str]) -> tuple[tuple[str, str | None], ...]:
    """Every compared header: its value in `values`, else None."""
    return tuple((name, values.get(name)) for name in COMPARED_HEADERS)


def sts_call(
    body: bytes,
    *,
    signer: str | None = "AKIDSRC",
    token: str | None = None,
    region: str = "us-east-1",
    host: str = STS_HOST,
    target: str = "/",
) -> NormalizedRequest:
    """One STS query-protocol POST as the normalizer records it.

    A call signed with `signer`'s key carries a SigV4 Authorization and
    X-Amz-Date scoped to `region` and sts, plus x-amz-security-token when
    the signing credentials have `token`. signer=None is an unsigned call,
    which carries none of them.
    """
    headers = {"content-type": FORM_CONTENT_TYPE}
    if signer is not None:
        headers["authorization"] = SIGV4
        headers["x-amz-date"] = AMZ_DATE_PLACEHOLDER
    if token is not None:
        headers["x-amz-security-token"] = token
    return NormalizedRequest(
        method="POST",
        host=host,
        path=target,
        target=target,
        query=(),
        content_type=FORM_CONTENT_TYPE,
        body_bytes=body,
        headers=compared(headers),
        user_agent=None,
        signing_scope=(
            None
            if signer is None
            else (signer, SCOPE_DATE_PLACEHOLDER, region, "sts")
        ),
    )


def metadata_call(
    method: str,
    host: str,
    target: str,
    headers: Mapping[str, str] | None = None,
) -> NormalizedRequest:
    """One bodyless, unsigned metadata request."""
    return NormalizedRequest(
        method=method,
        host=host,
        path=urlsplit(target).path,
        target=target,
        query=(),
        content_type=None,
        body_bytes=b"",
        headers=compared(headers or {}),
        user_agent=None,
        signing_scope=None,
    )


def cache_path(args: Mapping[str, object]) -> str:
    return f"home/{CLI_CACHE.as_posix()}/{role_cache_key(args)}.json"


def created_cache(*entries: CacheEntry) -> FileChanges:
    """The changes of a run that created the role cache with `entries`.

    Each entry is the AssumeRole arguments its key is made from and the
    content written, 0600 (utils.py:3991-4006).
    """
    changes = created_cache_directories()
    for args, content in entries:
        changes[cache_path(args)] = (CACHE_FILE_MODE, content)
    return changes


def load_error(message: str) -> bytes:
    return f"{LOAD_PREFIX}{message}\n".encode()


def general_error(message: str) -> bytes:
    return GENERAL_PREFIX + f"{message}\n".encode()


def param_error(*lines: str) -> bytes:
    return (PARAM_PREFIX + "\n".join(lines) + "\n").encode()


def utc_in(seconds: int) -> str:
    moment = datetime.now(UTC).replace(microsecond=0)
    return (moment + timedelta(seconds=seconds)).isoformat()


def cached_credentials(expiration: str) -> dict[str, object]:
    """A seeded role-cache entry with ASIACACHED credentials."""
    return {
        "Credentials": {
            "AccessKeyId": "ASIACACHED",
            "SecretAccessKey": "CACHED-secret",
            "SessionToken": "CACHED-token",
            "Expiration": expiration,
        }
    }


def scenario_env(
    sandbox: Sandbox,
    proxy: AsyncTLSInterceptProxy,
    changes: EnvChanges | None = None,
) -> dict[str, str]:
    env = sandbox.env(proxy)
    for key, value in (changes or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


async def run_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Mapping[RouteKey, Sequence[HTTPResponse]] | None = None,
    *,
    env: EnvChanges | None = None,
    globals_: Sequence[str] = (),
    servers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
) -> CliRun:
    """Run export-credentials once with STS scripted by route.

    Any request the script does not name gets the harness's 400 tripwire,
    so an unscripted STS call fails the run. `servers` adds plain-HTTP
    metadata servers ahead of the STS stub.
    """
    server, proxy = stub
    routes = dict(script or {})
    extra = dict(servers or {})
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [*extra, server],
        scenario_env(sandbox, proxy, env),
        globals_=globals_,
        handlers={**extra, server: lambda: routed(routes)},
    )


def assert_exported(
    run: CliRun, identity: str = "ROLEA", expiration: str = FUTURE_EXPIRATION
) -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        exported(identity, expiration),
        b"",
    ), run.describe()


def assert_failed(
    run: CliRun, returncode: int, stderr: bytes | BytesStartingWith
) -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        b"",
        stderr,
    ), run.describe()


def assert_rejected(
    run: CliRun, returncode: int, stderr: bytes | BytesStartingWith
) -> None:
    """A failure before any request that leaves the sandbox untouched."""
    assert_failed(run, returncode, stderr)
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


def assert_signed(
    run: CliRun, access_key: str, secret_key: str, index: int = 0
) -> None:
    """Request `index` carries a valid SigV4 signature by this key."""
    assert_signature(run.raw_requests[index], access_key, secret_key)


async def test_assume_role_static_source_signs_with_source_keys(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_credentials_file_source_sends_session_token(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(ROLE_PROFILE)
    sandbox.credentials.write_text(
        "[src]\n"
        "aws_access_key_id = AKIDSRC\n"
        "aws_secret_access_key = SRC-secret\n"
        "aws_session_token = SRC-token\n"
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    assert_exported(run)
    assert run.requests == (
        sts_call(assume_role_body(), token="SRC-token"),
    ), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_chain_assumes_inner_role_first(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\nsource_profile = b\n\n"
        f"[profile b]\nrole_arn = {ROLE_B}\nsource_profile = c\n\n"
        "[profile c]\n"
        "aws_access_key_id = AKIDC\n"
        "aws_secret_access_key = C-secret\n"
    )

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response("ROLEB"), role_response()]},
    )

    assert_exported(run)
    assert run.requests == (
        sts_call(assume_role_body(ROLE_B), signer="AKIDC"),
        sts_call(assume_role_body(), signer="ASIAROLEB", token="ROLEB-token"),
    ), run.describe()
    assert_signed(run, "AKIDC", "C-secret")
    assert_signed(run, "ASIAROLEB", "ROLEB-secret", 1)
    # One provider instance resolves both hops, so both use the disk cache
    # (credentials.py:1673, customizations/assumerole.py:19-49).
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_B}, cached_role("ROLEB")),
        ({"RoleArn": ROLE_A}, cached_role()),
    ), run.describe()


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = b\n\n"
            f"[profile b]\nrole_arn = {ROLE_B}\nsource_profile = c\n"
            "aws_access_key_id = AKIDB\n"
            "aws_secret_access_key = B-secret\n\n"
            "[profile c]\n"
            "aws_access_key_id = AKIDC\n"
            "aws_secret_access_key = C-secret\n",
            id="static-source-ends-chain",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = default\n"
            "aws_access_key_id = AKIDB\n"
            "aws_secret_access_key = B-secret\n",
            id="self-reference-with-static-keys",
        ),
    ],
)
async def test_assume_role_static_keys_take_precedence_over_role_arn(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
) -> None:
    sandbox.config.write_text(config)

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body(), signer="AKIDB"),), (
        run.describe()
    )
    assert_signed(run, "AKIDB", "B-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


@pytest.mark.parametrize(
    ("config", "message"),
    [
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = default\n",
            "from profile default which has already been visited. "
            "Visited profiles: ['default']",
            id="self-reference",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = b\n"
            f"[profile b]\nrole_arn = {ROLE_B}\nsource_profile = default\n",
            "from profile default which has already been visited. "
            "Visited profiles: ['default', 'b']",
            id="two-profile-loop",
        ),
    ],
)
async def test_assume_role_profile_loop_raises_infinite_loop_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    message: str,
) -> None:
    sandbox.config.write_text(config)

    run = await run_scenario(aws_cli, sandbox, stub)

    # exceptions.py:688-693 lists the visited profiles in visiting order.
    assert_rejected(
        run,
        CONFIGURATION_RC,
        load_error(
            "Infinite loop in credential configuration detected. "
            f"Attempting to load {message}"
        ),
    )


@pytest.mark.parametrize(
    ("config", "message"),
    [
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = nope\n",
            'The source_profile "nope" referenced in the profile "default" '
            "does not exist.",
            id="missing-source-profile",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile =\n",
            'The source_profile "" referenced in the profile "default" '
            "does not exist.",
            id="empty-source-profile",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\nsource_profile = src\n"
            "credential_source = Environment\n\n" + SOURCE_PROFILE,
            'The profile "default" contains both source_profile and '
            "credential_source.",
            id="source-profile-and-credential-source",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\n",
            "Partial credentials found in assume-role, missing: "
            "source_profile or credential_source",
            id="no-source",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\n"
            "aws_access_key_id = AKIDB\naws_secret_access_key = B-secret\n",
            "Partial credentials found in assume-role, missing: "
            "source_profile or credential_source",
            id="static-keys-unused",
        ),
        pytest.param(
            f"[default]\nrole_arn = {ROLE_A}\n"
            "credential_source = environment\n",
            'The credential source "environment" referenced in profile '
            '"default" is not valid.',
            id="lowercase-credential-source",
        ),
    ],
)
async def test_assume_role_invalid_role_config_raises_at_load(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    message: str,
) -> None:
    sandbox.config.write_text(config)

    run = await run_scenario(aws_cli, sandbox, stub)

    assert_rejected(run, CONFIGURATION_RC, load_error(message))


@pytest.mark.parametrize(
    ("env", "message"),
    [
        pytest.param(
            {},
            "Error when retrieving credentials from Environment: No "
            "credentials found in credential_source referenced in profile "
            "default",
            id="environment-empty",
        ),
        pytest.param(
            {"AWS_ACCESS_KEY_ID": "AKIDENV"},
            "Partial credentials found in env, missing: AWS_SECRET_ACCESS_KEY",
            id="environment-partial",
        ),
    ],
)
async def test_assume_role_credential_source_without_credentials_raises(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    env: dict[str, str],
    message: str,
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\ncredential_source = Environment\n"
    )

    # The explicit profile drops the chain's own EnvProvider (credentials.py:
    # 151-171), so only the named source can produce the error.
    run = await run_scenario(
        aws_cli, sandbox, stub, env=env, globals_=("--profile", "default")
    )

    assert_rejected(run, CONFIGURATION_RC, load_error(message))


async def test_assume_role_environment_source_signs_with_env_keys(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\ncredential_source = Environment\n"
    )

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        env={
            "AWS_ACCESS_KEY_ID": "AKIDENV",
            "AWS_SECRET_ACCESS_KEY": "ENV-secret",
            "AWS_SESSION_TOKEN": "ENV-token",
        },
        globals_=("--profile", "default"),
    )

    assert_exported(run)
    assert run.requests == (
        sts_call(assume_role_body(), signer="AKIDENV", token="ENV-token"),
    ), run.describe()
    assert_signed(run, "AKIDENV", "ENV-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_container_source_fetches_before_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    metadata: AsyncHTTPTestServer,
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\ncredential_source = EcsContainer\n"
    )
    host = f"127.0.0.1:{metadata.port}"
    container = {
        ("GET", host, "/creds"): [HTTPResponse.json(metadata_credentials())]
    }

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        env={"AWS_CONTAINER_CREDENTIALS_FULL_URI": f"{metadata.url}creds"},
        servers={metadata: lambda: routed(container)},
    )

    assert_exported(run)
    assert run.requests == (
        metadata_call("GET", host, "/creds"),
        sts_call(
            assume_role_body(),
            signer="AKIDCONTAINER",
            token="CONTAINER-token",
        ),
    ), run.describe()
    assert run.raw_requests[0].headers["accept"] == "application/json"
    assert_signed(run, "AKIDCONTAINER", "CONTAINER-secret", 1)
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


@pytest.mark.usefixtures("imds_routes_through_proxy")
async def test_assume_role_imds_source_fetches_before_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    metadata: AsyncHTTPTestServer,
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\n"
        "credential_source = Ec2InstanceMetadata\n"
    )
    imds = {
        ("PUT", IMDS_HOST, IMDS_TOKEN_PATH): [HTTPResponse.text(IMDS_TOKEN)],
        ("GET", IMDS_HOST, IMDS_ROLE_PATH): [HTTPResponse.text(IMDS_ROLE)],
        ("GET", IMDS_HOST, IMDS_ROLE_PATH + IMDS_ROLE): [
            HTTPResponse.json(metadata_credentials("IMDS"))
        ],
    }

    # IMDS goes through HTTP_PROXY (utils.py:366-369), here the metadata
    # stub, so no request can reach the real link-local endpoint.
    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        env={"AWS_EC2_METADATA_DISABLED": "false", "HTTP_PROXY": metadata.url},
        servers={metadata: lambda: routed(imds)},
    )

    assert_exported(run)
    session = {"x-aws-ec2-metadata-token": IMDS_TOKEN}
    assert run.requests == (
        metadata_call(
            "PUT",
            IMDS_HOST,
            f"http://{IMDS_HOST}{IMDS_TOKEN_PATH}",
            {"x-aws-ec2-metadata-token-ttl-seconds": IMDS_TOKEN_TTL},
        ),
        metadata_call(
            "GET", IMDS_HOST, f"http://{IMDS_HOST}{IMDS_ROLE_PATH}", session
        ),
        metadata_call(
            "GET",
            IMDS_HOST,
            f"http://{IMDS_HOST}{IMDS_ROLE_PATH}{IMDS_ROLE}",
            session,
        ),
        sts_call(assume_role_body(), signer="AKIDIMDS", token="IMDS-token"),
    ), run.describe()
    assert_signed(run, "AKIDIMDS", "IMDS-secret", 3)
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


@pytest.mark.parametrize(
    ("config", "credentials", "message"),
    [
        pytest.param(
            "[profile src]\naws_secret_access_key = SRC-secret\n",
            "",
            'The source profile "src" must have credentials.',
            id="secret-key-only",
        ),
        pytest.param(
            "[profile src]\naws_access_key_id = AKIDSRC\n",
            "",
            "Partial credentials found in config-file, missing: "
            "aws_secret_access_key",
            id="access-key-only-config-file",
        ),
        pytest.param(
            "",
            "[src]\naws_access_key_id = AKIDSRC\n",
            "Partial credentials found in shared-credentials-file, missing: "
            "aws_secret_access_key",
            id="access-key-only-credentials-file",
        ),
    ],
)
async def test_assume_role_source_without_full_credentials_raises(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    credentials: str,
    message: str,
) -> None:
    sandbox.config.write_text(ROLE_PROFILE + "\n" + config)
    sandbox.credentials.write_text(credentials)

    run = await run_scenario(aws_cli, sandbox, stub)

    assert_rejected(run, CONFIGURATION_RC, load_error(message))


@pytest.mark.parametrize(
    "settings",
    [
        # A duration that is not an integer is dropped (credentials.py:
        # 1713-1717), not an error.
        pytest.param(
            "duration_seconds = abc\n", id="duration-not-an-int"
        ),
        # An empty session name is replaced by the generated one, and the
        # generated name stays out of the cache key.
        pytest.param(
            "role_session_name =\n", id="empty-session-name-generated"
        ),
    ],
)
async def test_assume_role_unusable_setting_falls_back_to_default(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    settings: str,
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\nsource_profile = src\n{settings}\n"
        + SOURCE_PROFILE
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    # credentials.py:830-850: sorted JSON of the arguments, without a
    # generated session name.
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_all_arguments_cache_key_matches_vector(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {VECTOR_ROLE}\nsource_profile = src\n"
        "role_session_name = vector-session\n"
        "external_id = vector-external\n"
        "duration_seconds = 1800\n\n" + SOURCE_PROFILE
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    # The SHA-1 of the arguments' sorted JSON (credentials.py:830-850),
    # spelled out rather than computed by role_cache_key.
    key = "3e49cdb42bffbf23b5af6ef248e5eba188562b21"
    assert_exported(run)
    assert run.requests == (
        sts_call(
            form_body(
                "AssumeRole",
                ("RoleSessionName", "vector-session"),
                ("ExternalId", "vector-external"),
                ("DurationSeconds", "1800"),
                ("RoleArn", VECTOR_ROLE),
            )
        ),
    ), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == {
        **created_cache_directories(),
        f"home/{CLI_CACHE.as_posix()}/{key}.json": (
            CACHE_FILE_MODE,
            cached_role(),
        ),
    }, run.describe()


@pytest.mark.parametrize(
    ("role", "settings", "line"),
    [
        pytest.param(
            ROLE_A,
            "duration_seconds = 100\n",
            "Invalid value for parameter DurationSeconds, value: 100, "
            "valid min value: 900",
            id="duration-below-minimum",
        ),
        pytest.param(
            "arn:aws:iam::1:r/x",
            "",
            "Invalid length for parameter RoleArn, value: 18, "
            "valid min length: 20",
            id="short-role-arn",
        ),
    ],
)
async def test_assume_role_invalid_arguments_fail_validation_before_send(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    role: str,
    settings: str,
    line: str,
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {role}\nsource_profile = src\n{settings}\n"
        + SOURCE_PROFILE
    )

    run = await run_scenario(aws_cli, sandbox, stub)

    assert_rejected(run, PARAM_VALIDATION_RC, param_error(line))


async def test_assume_role_empty_role_arn_still_triggers_provider(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        "[default]\nrole_arn =\nsource_profile = src\n\n" + SOURCE_PROFILE
    )

    run = await run_scenario(aws_cli, sandbox, stub)

    # The trigger tests key presence (credentials.py:1633-1642), so the
    # empty ARN reaches validation instead of falling through the chain.
    assert_rejected(
        run,
        PARAM_VALIDATION_RC,
        param_error(
            "Invalid length for parameter RoleArn, value: 0, "
            "valid min length: 20"
        ),
    )


async def test_assume_role_web_identity_source_is_memory_cached(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", "synthetic-web-token")
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\nsource_profile = b\n\n"
        f"[profile b]\nrole_arn = {ROLE_B}\n"
        f"web_identity_token_file = {token}\n"
    )
    inner = role_response("ROLEB", action="AssumeRoleWithWebIdentity")

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [inner, role_response()]}
    )

    assert_exported(run)
    assert run.requests == (
        sts_call(
            form_body(
                "AssumeRoleWithWebIdentity",
                ("RoleArn", ROLE_B),
                ("RoleSessionName", GENERATED_NAME),
                ("WebIdentityToken", "synthetic-web-token"),
            ),
            signer=None,
        ),
        sts_call(assume_role_body(), signer="ASIAROLEB", token="ROLEB-token"),
    ), run.describe()
    assert_signed(run, "ASIAROLEB", "ROLEB-secret", 1)
    # A source profile's web identity uses the builder's in-memory cache
    # (credentials.py:241), so only RoleA reaches the disk.
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_env_token_file_does_not_complete_role_profile(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", "synthetic-web-token")
    sandbox.config.write_text(f"[default]\nrole_arn = {ROLE_A}\n")

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        env={"AWS_WEB_IDENTITY_TOKEN_FILE": str(token)},
    )

    # AssumeRole runs before web identity in the chain and only the
    # profile's keys decide its trigger.
    assert_rejected(
        run,
        CONFIGURATION_RC,
        load_error(
            "Partial credentials found in assume-role, missing: "
            "source_profile or credential_source"
        ),
    )


async def test_assume_role_corrupt_cache_entry_fails_without_request(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    sandbox.write(cache_path({"RoleArn": ROLE_A}), b"{not json", mode=0o600)

    run = await run_scenario(aws_cli, sandbox, stub)

    # Upstream bug, matched for parity: an unparseable cache entry is
    # fatal instead of a cache miss; JSONFileCache turns the parse error
    # into a KeyError of the key (utils.py:3975-3982), whose repr is the
    # message. The entry is left as it was.
    assert_rejected(run, GENERAL_RC, BytesStartingWith(GENERAL_PREFIX))


async def test_assume_role_cache_write_failure_raises_after_sts_call(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    entry = sandbox.root / cache_path({"RoleArn": ROLE_A})
    entry.mkdir(parents=True)

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    # utils.py:3991-4006 opens the entry after the API call returned; a
    # directory there fails the run, naming the path, and nothing is
    # written.
    assert_failed(
        run, GENERAL_RC, BytesStartingWith(GENERAL_PREFIX, (os_error_path(entry),))
    )
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == {}, run.describe()


async def test_assume_role_expired_response_is_cached_then_raises(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    response = role_response(expiration="2000-01-01T00:00:00Z")

    run = await run_scenario(aws_cli, sandbox, stub, {STS_ROUTE: [response]})

    # The fetcher caches before the refresher checks expiry
    # (credentials.py:752-759, 614-626).
    assert_failed(
        run,
        GENERAL_RC,
        general_error(
            "Credentials were refreshed, but the refreshed credentials are "
            "still expired."
        ),
    )
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        (
            {"RoleArn": ROLE_A},
            cached_role(expiration="2000-01-01T00:00:00+00:00"),
        ),
    ), run.describe()


async def test_assume_role_short_lived_response_is_exported(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    expiration = utc_in(SHORT_LIVED_SECONDS)
    response = role_response(expiration=expiration)

    run = await run_scenario(aws_cli, sandbox, stub, {STS_ROUTE: [response]})

    # One fetch: the refreshed credentials are inside the mandatory window
    # but not expired, so they are used as they are.
    assert_exported(run, expiration=expiration)
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role(expiration=expiration)),
    ), run.describe()


@pytest.mark.parametrize(
    ("expiration", "exported_as"),
    [
        pytest.param("2099-01-01T00:00:00Z", FUTURE_EXPIRATION, id="zulu"),
        # An older JSONFileCache wrote `%Z` timestamps.
        pytest.param(
            "2099-01-01T00:00:00UTC", FUTURE_EXPIRATION, id="legacy-utc-name"
        ),
        pytest.param(
            "2099-01-01T00:00:00-05:00",
            "2099-01-01T00:00:00-05:00",
            id="offset-kept",
        ),
    ],
)
async def test_assume_role_cache_hit_exports_without_sts_call(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    expiration: str,
    exported_as: str,
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    seed_cli_cache(
        sandbox.home,
        role_cache_key({"RoleArn": ROLE_A}),
        cached_credentials(expiration),
    )

    run = await run_scenario(aws_cli, sandbox, stub)

    # credentials.py:746-769 reads every Expiration form a botocore writer
    # produces, and a hit leaves the entry as it was.
    assert_exported(run, "CACHED", exported_as)
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


async def test_assume_role_cache_hit_skips_inner_hops(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\nsource_profile = b\n\n"
        f"[profile b]\nrole_arn = {ROLE_B}\nsource_profile = src\n\n"
        + SOURCE_PROFILE
    )
    expiration = utc_in(FRESH_ENTRY_SECONDS)
    seed_cli_cache(
        sandbox.home,
        role_cache_key({"RoleArn": ROLE_A}),
        cached_credentials(expiration),
    )

    run = await run_scenario(aws_cli, sandbox, stub)

    # The source freeze runs only on a miss (credentials.py:916-924), so
    # RoleB is never assumed.
    assert_exported(run, "CACHED", expiration)
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


async def test_assume_role_cache_hit_still_fails_on_empty_source(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        f"[default]\nrole_arn = {ROLE_A}\ncredential_source = Environment\n"
    )
    seed_cli_cache(
        sandbox.home,
        role_cache_key({"RoleArn": ROLE_A}),
        cached_credentials(FUTURE_EXPIRATION),
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, globals_=("--profile", "default")
    )

    # Source chains resolve during load() (credentials.py:1819-1850), so
    # an empty source fails the run even though the cache could answer.
    assert_rejected(
        run,
        CONFIGURATION_RC,
        load_error(
            "Error when retrieving credentials from Environment: No "
            "credentials found in credential_source referenced in profile "
            "default"
        ),
    )


async def test_assume_role_stale_cache_entry_is_refetched_and_replaced(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)
    seed_cli_cache(
        sandbox.home,
        role_cache_key({"RoleArn": ROLE_A}),
        cached_credentials(utc_in(STALE_ENTRY_SECONDS)),
    )

    run = await run_scenario(
        aws_cli, sandbox, stub, {STS_ROUTE: [role_response()]}
    )

    # credentials.py:785-789: under 900 s left is a miss, and the entry
    # is replaced with the new credentials.
    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == {
        cache_path({"RoleArn": ROLE_A}): (CACHE_FILE_MODE, cached_role())
    }, run.describe()


@pytest.mark.parametrize(
    ("setting", "cached"),
    [
        pytest.param("", "2099-01-01T00:00:00.123000+00:00", id="default"),
        pytest.param(
            "cli_timestamp_format = wire\n",
            "2099-01-01T00:00:00.123Z",
            id="wire",
        ),
    ],
)
async def test_assume_role_timestamp_format_decides_cached_expiration(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    setting: str,
    cached: str,
) -> None:
    sandbox.config.write_text(ROLE_PROFILE + setting + "\n" + SOURCE_PROFILE)
    response = role_response(expiration="2099-01-01T00:00:00.123Z")

    run = await run_scenario(aws_cli, sandbox, stub, {STS_ROUTE: [response]})

    # customizations/timestampformat.py:41-80 picks the parser for the
    # top-level profile; the cache stores its string, and the export
    # normalizes either.
    assert_exported(run, expiration="2099-01-01T00:00:00.123000+00:00")
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role(expiration=cached)),
    ), run.describe()


NO_REGION: Final[EnvChanges] = {"AWS_REGION": None, "AWS_DEFAULT_REGION": None}
# Configured endpoints; the TLS proxy intercepts any host.
SERVICE_ENDPOINT: Final = "https://sts-env.example.test"
SERVICE_ENDPOINT_WITH_PATH: Final = "https://sts-env.example.test:8443/svc"
WEST_PROFILE: Final = f"""\
[default]
role_arn = {ROLE_A}
source_profile = src
region = us-west-2
"""


def with_source(top: str, source_settings: str = "") -> str:
    """`top`, then the static source profile with extra settings."""
    return top + "\n" + SOURCE_PROFILE + source_settings


@pytest.mark.parametrize(
    ("config", "env", "globals_", "host", "path", "region"),
    [
        pytest.param(
            with_source(WEST_PROFILE),
            NO_REGION,
            (),
            "sts.us-west-2.amazonaws.com",
            "/",
            "us-west-2",
            id="profile-region",
        ),
        pytest.param(
            with_source(WEST_PROFILE),
            {
                **NO_REGION,
                "AWS_ENDPOINT_URL_STS": SERVICE_ENDPOINT_WITH_PATH,
            },
            (),
            "sts-env.example.test:8443",
            "/svc",
            "us-west-2",
            id="service-endpoint-env-path-kept",
        ),
        pytest.param(
            with_source(ROLE_PROFILE),
            NO_REGION,
            (),
            "sts.amazonaws.com",
            "/",
            "us-east-1",
            id="no-region-global-endpoint",
        ),
        pytest.param(
            with_source(ROLE_PROFILE),
            {},
            ("--region", "us-east-2"),
            "sts.us-east-2.amazonaws.com",
            "/",
            "us-east-2",
            id="region-flag-beats-env",
        ),
        pytest.param(
            with_source(ROLE_PROFILE, "region = us-west-2\n"),
            NO_REGION,
            (),
            "sts.amazonaws.com",
            "/",
            "us-east-1",
            id="source-profile-region-ignored",
        ),
        pytest.param(
            with_source(
                WEST_PROFILE, "endpoint_url = https://src.example.test\n"
            ),
            NO_REGION,
            (),
            "sts.us-west-2.amazonaws.com",
            "/",
            "us-west-2",
            id="source-profile-endpoint-ignored",
        ),
        pytest.param(
            with_source(ROLE_PROFILE),
            {**NO_REGION, "AWS_USE_FIPS_ENDPOINT": "true"},
            (),
            "sts-fips.aws-global.amazonaws.com",
            "/",
            "us-east-1",
            id="no-region-fips",
        ),
        pytest.param(
            with_source(ROLE_PROFILE),
            {"AWS_REGION": "cn-north-1"},
            (),
            "sts.cn-north-1.amazonaws.com.cn",
            "/",
            "cn-north-1",
            id="china-partition",
        ),
    ],
)
async def test_assume_role_endpoint_and_signing_region_follow_matrix(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    env: EnvChanges,
    globals_: tuple[str, ...],
    host: str,
    path: str,
    region: str,
) -> None:
    sandbox.config.write_text(config)

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {("POST", host, path): [role_response()]},
        env=env,
        globals_=globals_,
    )

    # The STS client takes the top-level profile's session region,
    # aws-global when there is none, and signs for the region the endpoint
    # ruleset or the legacy scope gives.
    assert_exported(run)
    assert run.requests == (
        sts_call(assume_role_body(), region=region, host=host, target=path),
    ), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_endpoint_without_region_raises_no_region(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        env={**NO_REGION, "AWS_ENDPOINT_URL_STS": SERVICE_ENDPOINT},
    )

    # A configured endpoint has no aws-global fallback; signers.py:304-306
    # raises while signing, before any byte is sent.
    assert_rejected(run, CONFIGURATION_RC, NO_REGION_ERROR)


async def test_assume_role_command_ca_bundle_does_not_reach_sts(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(STATIC_ROLE_CONFIG)

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        globals_=("--ca-bundle", "/nonexistent/ca.pem"),
    )

    # The flag configures only the command's own client (clidriver.py:
    # 1093); STS still verifies against AWS_CA_BUNDLE.
    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body()),), run.describe()
    assert_signed(run, "AKIDSRC", "SRC-secret")
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


async def test_assume_role_no_sign_request_sends_unsigned_call(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(ROLE_PROFILE + "\n" + TOKEN_SOURCE_PROFILE)

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        globals_=("--no-sign-request",),
    )

    # Upstream bug, matched for parity: --no-sign-request also reaches the
    # AssumeRole client, which then drops the source's key and token
    # (session.py:890-891) and sends the call unsigned.
    assert_exported(run)
    assert run.requests == (sts_call(assume_role_body(), signer=None),), (
        run.describe()
    )
    assert run.changes == created_cache(
        ({"RoleArn": ROLE_A}, cached_role())
    ), run.describe()


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


PARITY_ROLE_ARN = "arn:aws:iam::123456789012:role/blackbox-credential-parity"
PARITY_ROLE_PROFILE = (
    f"[default]\nrole_arn = {PARITY_ROLE_ARN}\n"
    "role_session_name = parity-session\n"
)
PARITY_SOURCE_PROFILE_ROLE = PARITY_ROLE_PROFILE + (
    "source_profile = source\nexternal_id = parity-external\n"
    "duration_seconds = 1800\n"
)


def assert_assume_role_request(
    request: RecordedHTTPRequest, token: str | None
) -> dict[str, list[str]]:
    fields = parse_qs(request.text)
    assert fields["Action"] == ["AssumeRole"]
    assert fields["RoleArn"] == [PARITY_ROLE_ARN]
    assert fields["RoleSessionName"] == ["parity-session"]
    assert_signature(request, "AKIDSOURCE", "SOURCE-secret")
    assert request.headers.get("x-amz-security-token") == token
    return fields


async def test_credentials_shared_source_profile_sends_signed_assume_role(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, PARITY_SOURCE_PROFILE_ROLE)
        write_config(
            env, "[source]\n" + file_credentials("SOURCE"), shared=True
        )
        request = await rejected_role_request(aws_cli, server, env)
    fields = assert_assume_role_request(request, None)
    assert fields["ExternalId"] == ["parity-external"]
    assert fields["DurationSeconds"] == ["1800"]


async def test_credentials_environment_source_sends_signed_assume_role(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        write_config(
            env, PARITY_ROLE_PROFILE + "credential_source = Environment\n"
        )
        env.update(
            AWS_ACCESS_KEY_ID="AKIDSOURCE",
            AWS_SECRET_ACCESS_KEY="SOURCE-secret",
        )
        # An explicit profile skips top-level env credentials but permits
        # credential_source=Environment for AssumeRole.
        request = await rejected_role_request(
            aws_cli, server, env, "--profile", "default"
        )
    assert_assume_role_request(request, None)


async def test_credentials_process_source_profile_sends_signed_assume_role(
    aws_cli: str, tmp_path: Path
) -> None:
    command, _ = json_process(tmp_path, process_credentials("SOURCE"))
    async with credential_runtime(tmp_path) as (server, env):
        write_config(
            env,
            PARITY_SOURCE_PROFILE_ROLE
            + f"[profile source]\ncredential_process = {command}\n",
        )
        request = await rejected_role_request(aws_cli, server, env)
    fields = assert_assume_role_request(request, "SOURCE-token")
    assert fields["ExternalId"] == ["parity-external"]
    assert fields["DurationSeconds"] == ["1800"]
