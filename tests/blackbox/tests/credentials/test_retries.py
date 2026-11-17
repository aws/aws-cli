import itertools
import uuid
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    CloseConnection,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponseSpec,
)

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    SCOPE_DATE_PLACEHOLDER,
    BytesStartingWith,
    CliRun,
    FileChanges,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_signature,
    created_cache_directories,
    expected_request,
    export_credentials_output,
    role_cache_key,
    routed,
    run_export_credentials,
    sts_error_xml,
    sts_success_xml,
    unexpected_request,
)
from tests.blackbox.utils import mock_server

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# botocore's standard retry loop for the AssumeRole client: the
# configuration lookups and their validation (configprovider.py:153-154,
# 602-624; config.py:397-402), the send loop (endpoint.py:190-229), the
# retry decision and quota (retries/standard.py:139-710), backoff
# (retries/standard.py:337-437), and the amz-sdk-request header's attempt
# and ttl fields (handlers.py:1017-1029, endpoint.py:147-188). STS is a
# direct plain-HTTP endpoint with NO_PROXY: through the TLS intercept
# proxy a dropped connection is a ProxyConnectionError instead. Backoff is
# random, so the attempt count shows a retry happened; wall-clock gaps are
# asserted only against a retry-after value, never as a tight upper bound
# a loaded runner could break.
GapCheck = Callable[[Sequence[float]], None]

ACCOUNT: Final = "123456789012"
ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/r"
SESSION_NAME: Final = "sess"
SOURCE_KEY: Final = "AKIDSOURCE"
SOURCE_SECRET: Final = "sourcesecret"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded; charset=utf-8"
GENERAL_RC: Final = 255
CLIENT_ERROR_RC: Final = 254
GENERAL_PREFIX: Final = b"\naws: [ERROR]: "
# A fixed Date makes the ttl deterministic: Date plus the 60 s default
# read timeout (endpoint.py:147-178).
FIXED_DATE: Final = "Thu, 08 Oct 2026 07:52:05 GMT"
FIXED_TTL: Final = "20261008T075305Z"
NEW_RETRIES_ENV: Final = "AWS_NEW_RETRIES_2026"
CONFIG: Final = """\
[default]
role_arn = {role_arn}
source_profile = src
role_session_name = {session}
{default_extra}
[profile src]
aws_access_key_id = {key}
aws_secret_access_key = {secret}
{source_extra}"""
CACHE_ARGS: Final = {"RoleSessionName": SESSION_NAME, "RoleArn": ROLE_ARN}
REQUEST_BODY: Final = (
    "Action=AssumeRole&Version=2011-06-15&RoleSessionName=sess&RoleArn="
    + quote_plus(ROLE_ARN)
).encode()
# The role cache's Credentials for sts_success_xml(), AccountId added
# from the assumed-role ARN (credentials.py:852-859).
ROLE_CACHE: Final = RoleCacheContent(
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
EXPORTED: Final = export_credentials_output(
    "AKIDROLE", "ROLE-secret", "ROLE-token", FUTURE_EXPIRATION
)


@pytest_asyncio.fixture
async def stub() -> AsyncIterator[Stub]:
    """The TLS intercept route, which no case should take.

    Its server answers with the harness's 400 tripwire and is recorded
    with the direct endpoint, so a misrouted call is a visible request.
    """
    async with mock_server() as (server, proxy):
        server.set_default_response(unexpected_request())
        yield server, proxy


@pytest_asyncio.fixture
async def sts() -> AsyncIterator[AsyncHTTPTestServer]:
    """The direct STS endpoint."""
    async with AsyncHTTPTestServer() as server:
        yield server


def sts_host(server: AsyncHTTPTestServer) -> str:
    return server.url.removeprefix("http://").rstrip("/")


INTERNAL: Final = sts_error_xml(
    "InternalFailure", "internal", status=500, headers={"Date": FIXED_DATE}
)
UNDATED_INTERNAL: Final = sts_error_xml(
    "InternalFailure", "internal", status=500
)
DROPPED: Final = CloseConnection()


def succeeded() -> HTTPResponse:
    return sts_success_xml(headers={"Date": FIXED_DATE})


def internal_dated(date: str) -> HTTPResponse:
    return sts_error_xml(
        "InternalFailure", "internal", status=500, headers={"Date": date}
    )


def general_error(message: str) -> str:
    return f"\naws: [ERROR]: {message.strip()}\n"


def client_error(code: str, message: str, retries: int | None) -> str:
    """ClientError's framed text (exceptions.py:509-541)."""
    suffix = "" if retries is None else f" (reached max retries: {retries})"
    return general_error(
        f"An error occurred ({code}) when calling the AssumeRole "
        f"operation{suffix}: {message}"
    )


def at_least(seconds: float) -> GapCheck:
    """Each wait lasts at least `seconds`."""

    def check(gaps: Sequence[float]) -> None:
        assert all(gap >= seconds for gap in gaps), gaps

    return check


def between(low: float, high: float) -> GapCheck:
    """Each wait lasts at least `low` seconds and ends before `high`."""

    def check(gaps: Sequence[float]) -> None:
        assert all(low <= gap < high for gap in gaps), gaps

    return check


@dataclass(frozen=True)
class Settings:
    """The retry inputs of one case.

    `max_attempts` is AWS_MAX_ATTEMPTS (None leaves it unset), `env` adds
    variables, and the extras are lines for the active profile and for
    its source profile.
    """

    max_attempts: str | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    default_extra: str = ""
    source_extra: str = ""
    globals_: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    """One retry case: the scripted answers and what the CLI does.

    `attempts` is the request count; each request's amz-sdk-request names
    its attempt number. `ttls`, when given, is the ttl field of each
    attempt's amz-sdk-request, None where absent. `stderr` may name
    `{url}`, the endpoint's URL. `cached` means the run succeeded and
    wrote the role cache.
    """

    responses: tuple[ResponseSpec, ...]
    returncode: int
    attempts: int
    stderr: str | BytesStartingWith = ""
    cached: bool = False
    ttls: tuple[str | None, ...] | None = None
    settings: Settings = field(default_factory=Settings)
    backoff: GapCheck | None = None


MODE: Final = "AWS_RETRY_MODE"


def env_attempts(value: str) -> Settings:
    return Settings(max_attempts=value)


def env_mode(value: str) -> Settings:
    return Settings(env={MODE: value})


def cache_path() -> str:
    return f"home/.aws/cli/cache/{role_cache_key(CACHE_ARGS)}.json"


def cached_changes() -> FileChanges:
    """The run's only changes: the role cache entry, and its dirs."""
    changes = created_cache_directories()
    changes[cache_path()] = (CACHE_FILE_MODE, ROLE_CACHE)
    return changes


def sdk_request_fields(request: RecordedHTTPRequest) -> dict[str, str]:
    """amz-sdk-request's `name=value` fields, split on ";"."""
    value = request.headers.get("amz-sdk-request") or ""
    pairs = (part.strip().partition("=") for part in value.split(";"))
    return {name: text for name, _, text in pairs if name}


def signed_by_source(run: CliRun) -> None:
    for request in run.raw_requests:
        assert_signature(request, SOURCE_KEY, SOURCE_SECRET)


def one_invocation_id(run: CliRun) -> None:
    """Every attempt of the call carries one amz-sdk-invocation-id.

    The first attempt sets it to str(uuid.uuid4()) and later attempts keep
    it (endpoint.py:180-184, handlers.py:1017-1029). The header is left
    out of NormalizedRequest, so this is its only check.
    """
    ids = {
        request.headers.get("amz-sdk-invocation-id")
        for request in run.raw_requests
    }
    assert len(ids) <= 1, run.describe()
    for value in ids:
        assert value is not None, run.describe()
        parsed = uuid.UUID(value)
        assert (parsed.version, str(parsed)) == (4, value), run.describe()


async def run_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> CliRun:
    tunnel_server, proxy = stub
    settings = scenario.settings
    sandbox.config.write_text(
        CONFIG.format(
            role_arn=ROLE_ARN,
            session=SESSION_NAME,
            key=SOURCE_KEY,
            secret=SOURCE_SECRET,
            default_extra=settings.default_extra,
            source_extra=settings.source_extra,
        ),
        encoding="utf-8",
    )
    sandbox.seal()
    env = sandbox.env(proxy, max_attempts=settings.max_attempts)
    env.update(AWS_ENDPOINT_URL_STS=sts.url, NO_PROXY="127.0.0.1")
    env.update(settings.env)
    script: dict[RouteKey, list[ResponseSpec]] = {
        ("POST", sts_host(sts), "/"): list(scenario.responses)
    }
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [sts, tunnel_server],
        env,
        globals_=settings.globals_,
        handlers={sts: lambda: routed(script)},
    )


def attempt_request(sts: AsyncHTTPTestServer) -> NormalizedRequest:
    """One AssumeRole attempt to the direct endpoint.

    SigV4 with the source profile's static keys, so no session token
    (auth.py:454-461), scoped to AWS_REGION's us-east-1.
    """
    return expected_request(
        "POST",
        sts_host(sts),
        "/",
        body=REQUEST_BODY,
        headers={
            "authorization": "AWS4-HMAC-SHA256",
            "x-amz-date": AMZ_DATE_PLACEHOLDER,
            "content-type": FORM_CONTENT_TYPE,
        },
        signing_scope=(SOURCE_KEY, SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts"),
    )


def assert_run(
    run: CliRun, scenario: Scenario, sts: AsyncHTTPTestServer
) -> None:
    stdout = EXPORTED if scenario.cached else b""
    stderr = (
        scenario.stderr
        if isinstance(scenario.stderr, BytesStartingWith)
        else scenario.stderr.format(url=sts.url).encode()
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        scenario.returncode,
        stdout,
        stderr,
    ), run.describe()
    fields = [sdk_request_fields(request) for request in run.raw_requests]
    assert [sent.get("attempt") for sent in fields] == [
        str(attempt) for attempt in range(1, scenario.attempts + 1)
    ], run.describe()
    if scenario.ttls is not None:
        assert [sent.get("ttl") for sent in fields] == list(scenario.ttls), (
            run.describe()
        )
    # Every attempt is the same signed form POST to the direct endpoint;
    # none reaches the intercept proxy.
    assert run.requests == (attempt_request(sts),) * scenario.attempts, (
        run.describe()
    )
    expected = cached_changes() if scenario.cached else {}
    assert run.changes == expected, run.describe()


async def assert_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> None:
    run = await run_scenario(aws_cli, sandbox, stub, sts, scenario)
    assert_run(run, scenario, sts)
    signed_by_source(run)
    one_invocation_id(run)
    if scenario.backoff is not None:
        # When each attempt of this run reached STS.
        arrivals = [sts.get_request_timestamp(r) for r in sts.requests]
        pairs = itertools.pairwise(arrivals)
        scenario.backoff([later - earlier for earlier, later in pairs])


SLOW: Final = pytest.mark.slow
SEQUENCE_ROWS: Final = [
    pytest.param(
        Scenario((succeeded(),), 0, 1, cached=True),
        id="200-first-attempt",
    ),
    pytest.param(
        # Three attempts by default (retries/standard.py:44).
        Scenario(
            (INTERNAL,) * 3,
            CLIENT_ERROR_RC,
            3,
            client_error("InternalFailure", "internal", 2),
        ),
        id="500-three-times",
        marks=SLOW,
    ),
    pytest.param(
        Scenario(
            (DROPPED,) * 3,
            GENERAL_RC,
            3,
            general_error(
                "Connection was closed before we received a valid response "
                'from endpoint URL: "{url}".'
            ),
        ),
        id="dropped-connection-three-times",
        marks=SLOW,
    ),
    pytest.param(
        # Upstream bug, matched for parity: a response without a Date
        # leaves the previous attempt's ttl in place, so later attempts
        # send a stale one (endpoint.py:162-177).
        Scenario(
            (INTERNAL, UNDATED_INTERNAL, UNDATED_INTERNAL),
            CLIENT_ERROR_RC,
            3,
            client_error("InternalFailure", "internal", 2),
            ttls=(None, FIXED_TTL, FIXED_TTL),
        ),
        id="stale-ttl-after-undated-response",
        marks=SLOW,
    ),
]


@pytest.mark.parametrize("scenario", SEQUENCE_ROWS)
async def test_retry_sequence_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, sts, scenario)


def one_retry(
    date: str | None, ttl: str | None, *, globals_: tuple[str, ...] = ()
) -> Scenario:
    """A 500 carrying `date`, then a success: attempt 2's header shows
    the ttl derived from it, or none."""
    first = UNDATED_INTERNAL if date is None else internal_dated(date)
    return Scenario(
        (first, succeeded()),
        0,
        2,
        cached=True,
        ttls=(None, ttl),
        settings=Settings(globals_=globals_),
    )


TTL_ROWS: Final = [
    pytest.param(one_retry(FIXED_DATE, FIXED_TTL), id="gmt"),
    pytest.param(one_retry(None, None), id="no-date"),
    pytest.param(
        one_retry(
            FIXED_DATE,
            "20261008T075210Z",
            globals_=("--cli-read-timeout", "5"),
        ),
        id="read-timeout-5",
    ),
]


@pytest.mark.parametrize("scenario", TTL_ROWS)
async def test_retry_ttl_derived_from_response_date(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> None:
    # ttl = Date + read_timeout; without a Date there is none
    # (endpoint.py:147-178).
    await assert_scenario(aws_cli, sandbox, stub, sts, scenario)


def config_error(
    message: str | BytesStartingWith, settings: Settings
) -> Scenario:
    """A retry setting rejected at client creation: no request."""
    stderr = general_error(message) if isinstance(message, str) else message
    return Scenario((), GENERAL_RC, 0, stderr, settings=settings)


def below_one(value: int) -> str:
    """InvalidMaxRetryAttemptsError (exceptions.py:652-658)."""
    return (
        f'Value provided to "max_attempts": {value} must be an integer '
        "greater than or equal to one."
    )


def bad_mode(value: str) -> str:
    """InvalidRetryModeError (exceptions.py:661-667)."""
    return (
        f'Invalid value provided to "mode": "{value}" must be one of: '
        '"standard" or "adaptive"'
    )


def retried_success(settings: Settings) -> Scenario:
    """A 500 then a success, with at least two attempts allowed."""
    return Scenario(
        (INTERNAL, succeeded()), 0, 2, cached=True, settings=settings
    )


CONFIGURATION_ROWS: Final = [
    pytest.param(
        # int()'s wording, naming the rejected value.
        config_error(
            BytesStartingWith(GENERAL_PREFIX, (b"abc",)), env_attempts("abc")
        ),
        id="env-max-attempts-letters",
    ),
    pytest.param(
        config_error(below_one(0), env_attempts("0")),
        id="env-max-attempts-zero",
    ),
    pytest.param(
        config_error(bad_mode("legacy"), env_mode("legacy")),
        id="env-retry-mode-legacy",
    ),
    pytest.param(
        config_error(bad_mode("STANDARD"), env_mode("STANDARD")),
        id="env-retry-mode-case-sensitive",
    ),
    pytest.param(
        retried_success(env_mode("adaptive")), id="env-retry-mode-adaptive"
    ),
    pytest.param(
        Scenario(
            (INTERNAL,),
            CLIENT_ERROR_RC,
            1,
            client_error("InternalFailure", "internal", 0),
            settings=Settings(default_extra="max_attempts = 1\n"),
        ),
        id="active-profile-max-attempts",
    ),
    pytest.param(
        retried_success(
            Settings(max_attempts="2", default_extra="max_attempts = abc\n")
        ),
        id="env-max-attempts-over-invalid-profile",
    ),
    pytest.param(
        config_error(
            bad_mode("legacy"), Settings(default_extra="retry_mode = legacy\n")
        ),
        id="profile-retry-mode-legacy",
    ),
    pytest.param(
        retried_success(
            Settings(
                env={MODE: "standard"}, default_extra="retry_mode = legacy\n"
            )
        ),
        id="env-retry-mode-over-invalid-profile",
    ),
]


@pytest.mark.parametrize("scenario", CONFIGURATION_ROWS)
async def test_retry_configuration_resolved_like_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> None:
    # Env over the active profile over the default 3, then the
    # max_attempts and mode checks, all when the STS client is created.
    await assert_scenario(aws_cli, sandbox, stub, sts, scenario)


def retry_after(milliseconds: str) -> HTTPResponse:
    return sts_error_xml(
        "InternalFailure",
        "internal",
        status=500,
        headers={"Date": FIXED_DATE, "x-amz-retry-after": milliseconds},
    )


BACKOFF_ROWS: Final = [
    pytest.param(
        Scenario(
            (retry_after("1500"), succeeded()),
            0,
            2,
            cached=True,
            backoff=at_least(1.5),
        ),
        id="honors-retry-after",
    ),
    # The variable that opted into these retries before 2.40.0 opts out of
    # nothing now.
    pytest.param(
        Scenario(
            (retry_after("1500"), succeeded()),
            0,
            2,
            cached=True,
            settings=Settings(env={NEW_RETRIES_ENV: "false"}),
            backoff=at_least(1.5),
        ),
        id="retired-variable-honors-retry-after",
    ),
    # The backoff of a first retry is below 50 ms, so the wait is capped
    # at about 5 seconds.
    pytest.param(
        Scenario(
            (retry_after("7000"), succeeded()),
            0,
            2,
            cached=True,
            backoff=between(5, 7),
        ),
        id="caps-retry-after",
    ),
]


@pytest.mark.parametrize("scenario", BACKOFF_ROWS)
async def test_retry_backoff_honors_retry_after(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    sts: AsyncHTTPTestServer,
    scenario: Scenario,
) -> None:
    # botocore waits at least the x-amz-retry-after a response names, but
    # at most 5 seconds past its own backoff (retries/standard.py
    # `ExponentialBackoff.delay_amount`). Since 2.40.0 that is its only
    # retry behavior, and AWS_NEW_RETRIES_2026 is no longer read.
    await assert_scenario(aws_cli, sandbox, stub, sts, scenario)
