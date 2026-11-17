import asyncio
import dataclasses
import functools
import json
import socket
import ssl
import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    CloseConnection,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponseSpec,
)
from localstub.ca import TLSProxyCA

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    IMDS_HOSTS,
    SCOPE_DATE_PLACEHOLDER,
    BytesStartingWith,
    CliRun,
    FileChanges,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_credential_error,
    assert_signature,
    assert_signed_by,
    assert_signed_with,
    created_cache_directories,
    credential_env,
    credential_process,
    export_credentials_output,
    list_bucket,
    metadata_credentials,
    normalize_request,
    process_credentials,
    role_cache_key,
    routed,
    run_aws,
    run_command,
    run_export_credentials,
    run_s3_ls,
    sts_success_xml,
    unexpected_request,
    without_s3,
    write_config,
)
from tests.blackbox.utils import mock_server

# Every test reaches IMDS, so each one first requires the session check
# that the CLI sends IMDS traffic through HTTP_PROXY (conftest.py).
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures(
        "imds_routes_through_proxy", "sts_routes_through_proxy"
    ),
]

# botocore InstanceMetadataProvider (credentials.py:1163-1190) and
# InstanceMetadataFetcher (utils.py:338-656) through `aws configure
# export-credentials`, with HTTP_PROXY at the metadata stub so requests for
# the link-local endpoint arrive there in absolute form; rows whose proxy
# faults configure CONFIGURED_BASE instead. AWS_REGION stays set unless a
# test is about the CLI's IMDS region lookup (awscli/utils.py:96-209).
IMDS_HOST: Final = "169.254.169.254"
IPV6_HOST: Final = "[fd00:ec2::254]"
# A configured endpoint under `.invalid` never resolves (RFC 6761), so a
# CLI that ignored HTTP_PROXY for it would reach nothing.
CONFIGURED_HOST: Final = "imds.invalid"
CONFIGURED_BASE: Final = f"http://{CONFIGURED_HOST}"
ENDPOINT_VAR: Final = "AWS_EC2_METADATA_SERVICE_ENDPOINT"
MODE_VAR: Final = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE"
TOKEN_PATH: Final = "/latest/api/token"
ROLE_LIST_PATH: Final = "/latest/meta-data/iam/security-credentials/"
PLACEMENT_PATH: Final = "/latest/meta-data/placement/region"
ROLE: Final = "test-role"
TOKEN: Final = "imds-token"
TOKEN_TTL: Final = "21600"
TOKEN_HEADER: Final = "x-aws-ec2-metadata-token"
TTL_HEADER: Final = "x-aws-ec2-metadata-token-ttl-seconds"
IMDS_REGION: Final = "us-west-2"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
LOAD_ERROR_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
LOAD_ERROR_RC: Final = 253
FREEZE_ERROR_RC: Final = 255
NO_CREDENTIALS: Final = "no credentials found"
# The least s2n delays the close of a connection whose handshake it failed.
S2N_BLINDING_MIN_SECONDS: Final = 10.0
# A username and password in a proxy's URL.
PROXY_LOGIN: Final = "user:proxy-secret"
# The native route's `--debug` record of a proxy it does not use.
PROXY_UNSUPPORTED: Final = (
    "The proxy for the instance metadata service is not supported (only an "
    "http:// proxy given as host:port, without a username or password, is), "
    "so the service is not asked for credentials"
)
# Far below the attempts and the timeout a row that must not wait sets.
PROMPT_SECONDS: Final = 5.0
# What `s3 ls` reports when no provider has credentials.
LISTING_NO_CREDENTIALS: Final = (
    b"\naws: [ERROR]: An error occurred (NoCredentials): Unable to locate "
    b'credentials. You can configure credentials by running "aws login".\n'
)
# utils.py:497-501.
V1_DISABLED_TEXT: Final = (
    "Error retrieving metadata: Unable to retrieve token for use in IMDSv2 "
    "call and IMDSv1 has been disabled"
)
# The IMDS extension window (utils.py:623-656): 900 s plus randint(120,
# 600), so an extended expiry lands 1020-1500 s from now.
EXTENSION_MIN_SECONDS: Final = 900 + 120
EXTENSION_MAX_SECONDS: Final = 900 + 600
EXTENDED_PLACEHOLDER: Final = "<extended expiry>"
STS_HOST: Final = f"sts.{IMDS_REGION}.amazonaws.com"
ROLE_ARN: Final = "arn:aws:iam::123456789012:role/r"
# AssumeRole requires two characters or more (ParamValidation otherwise).
SESSION_NAME: Final = "imds-session"
# The role cache under the sandbox root.
CLI_CACHE_DIR: Final = f"home/{CLI_CACHE.as_posix()}"
# The media type of botocore's query serializer (serialize.py:231-233).
STS_CONTENT_TYPE: Final = "application/x-www-form-urlencoded"
# The role cache entry for sts_success_xml(): its credentials, with the
# assumed role's account added (credentials.py:852-857, 917-924). The
# CLI's default iso8601 timestamp parser has already turned the wire
# expiry into an isoformat() string (awscli/customizations/
# timestampformat.py:45-46, 73-74).
ROLE_CACHE_ENTRY: Final = RoleCacheContent(
    {
        "Credentials": {
            "AccessKeyId": "AKIDROLE",
            "SecretAccessKey": "ROLE-secret",
            "SessionToken": "ROLE-token",
            "Expiration": FUTURE_EXPIRATION,
            "AccountId": "123456789012",
        }
    }
)
# Every compared header an IMDS request leaves out: the fetcher signs
# nothing and sends no body (utils.py:408-416, 444-470).
UNSIGNED_HEADERS: Final = tuple(
    name for name in COMPARED_HEADERS if name not in (TOKEN_HEADER, TTL_HEADER)
)

# tcpmux: below every ephemeral range bind(0) draws from (49152-65535 on
# macOS and Windows, 32768-60999 on Linux), and nothing in the suite binds
# a fixed port, so no test server is handed it during the run. Any user
# may still bind it (macOS allows 0.0.0.0:1 without root, as does Linux
# with ip_unprivileged_port_start=0), so `refused_port` checks that it
# refuses before a test uses it. (A bound socket that never listens is no
# substitute: macOS drops the SYN and the client sees a connect timeout
# instead.)
REFUSED_PORT: Final = 1
REFUSAL_CHECK_SECONDS: Final = 1.0

# The transport-fault rows pin the metadata timeout (connect and read,
# utils.py:343-370) to 1 s. A stalled response stays silent for three
# times that before the stub closes the connection, so a client that
# times out on schedule never sees the close instead, even on a loaded
# machine.
FAULT_TIMEOUT: Final = "1"
STALL_SECONDS: Final = 3.0

ImdsRequest = tuple[str, str, str | None]
Script = dict[RouteKey, list[ResponseSpec]]


def dropped() -> CloseConnection:
    """A connection closed without a byte of response."""
    return CloseConnection()


def stalled() -> CloseConnection:
    """STALL_SECONDS of silence, then a close."""
    return CloseConnection(delay=STALL_SECONDS)


def require_refusal(port: int) -> int:
    """`port` once a loopback connect to it is refused; skips otherwise.

    A row that expects a refused connection would otherwise fail
    confusingly when something listens on the port, or when a sandbox or
    firewall fails the connect some other way.
    """
    address = ("127.0.0.1", port)
    try:
        with socket.create_connection(address, timeout=REFUSAL_CHECK_SECONDS):
            pass
    except ConnectionRefusedError:
        return port
    except OSError as error:
        pytest.skip(f"127.0.0.1:{port} does not refuse: {error}")
    pytest.skip(f"something listens on 127.0.0.1:{port}")


@pytest.fixture
def refused_port() -> int:
    """REFUSED_PORT, checked to refuse loopback connections."""
    return require_refusal(REFUSED_PORT)


@pytest_asyncio.fixture
async def stub() -> AsyncIterator[Stub]:
    """The TLS proxy and the STS stub, which trips on any request."""
    async with mock_server() as (server, proxy):
        server.set_default_response(unexpected_request())
        yield server, proxy


@pytest_asyncio.fixture
async def metadata() -> AsyncIterator[AsyncHTTPTestServer]:
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(unexpected_request())
        yield server


@pytest_asyncio.fixture
async def forwarder() -> AsyncIterator[AsyncHTTPTestServer]:
    """A second plain stub, for rows that need a separate HTTP_PROXY."""
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(unexpected_request())
        yield server


class Scenario:
    """One IMDS test's servers and environment, and the run they serve."""

    def __init__(
        self,
        aws_cli: str,
        sandbox: Sandbox,
        stub: Stub,
        metadata: AsyncHTTPTestServer,
    ) -> None:
        self.aws_cli = aws_cli
        self.sandbox = sandbox
        self.server, proxy = stub
        self.metadata = metadata
        self.env = sandbox.env(proxy)
        self.env.update(
            AWS_EC2_METADATA_DISABLED="false", HTTP_PROXY=metadata.url
        )

    @property
    def direct_host(self) -> str:
        return f"127.0.0.1:{self.metadata.port}"

    def without_region(self) -> None:
        for key in ("AWS_REGION", "AWS_DEFAULT_REGION"):
            self.env.pop(key, None)

    def use_configured_endpoint(self) -> None:
        """Configure CONFIGURED_BASE, for rows whose proxy faults.

        A client that fell back to a direct connection when the proxy
        refused, dropped, stalled, or garbled a request would then reach
        no IMDS, never the real link-local one.
        """
        self.env[ENDPOINT_VAR] = CONFIGURED_BASE

    def send_direct(self, proxy: AsyncHTTPTestServer) -> None:
        """Configure the metadata stub as the endpoint, bypassing `proxy`.

        `proxy` stays HTTP_PROXY, so a request that ignored NO_PROXY
        would reach it instead of the stub.
        """
        self.env.update(
            {
                ENDPOINT_VAR: self.metadata.url,
                "HTTP_PROXY": proxy.url,
                "NO_PROXY": "127.0.0.1",
            }
        )

    def send_secure(self, port: int) -> str:
        """Configure `https` on loopback `port` as the endpoint, and return
        the host its requests name.

        HTTPS_PROXY stays the TLS proxy S3 is reached through, so NO_PROXY
        names the endpoint: a request for it that went to that proxy would
        reach the STS stub, which trips.
        """
        host = f"127.0.0.1:{port}"
        self.env.update(
            {ENDPOINT_VAR: f"https://{host}", "NO_PROXY": "127.0.0.1"}
        )
        return host

    async def run(
        self,
        script: Script,
        *,
        servers: Sequence[AsyncHTTPTestServer] = (),
        scripts: Mapping[AsyncHTTPTestServer, Script] | None = None,
        globals_: Sequence[str] = (),
        normalize: Callable[
            [RecordedHTTPRequest], NormalizedRequest
        ] = normalize_request,
    ) -> CliRun:
        """Run export-credentials once against fresh routed handlers.

        `script` routes the metadata stub; `scripts` routes other servers
        (the STS stub behind the TLS proxy, a second HTTP_PROXY). Every
        server's requests are recorded, so one that reaches the wrong
        server shows up in the run.
        """
        routes_by_server = {self.metadata: script, **(scripts or {})}
        return await run_export_credentials(
            self.aws_cli,
            self.sandbox,
            [self.metadata, self.server, *servers],
            self.env,
            globals_=globals_,
            normalize=normalize,
            handlers={
                server: functools.partial(routed, routes)
                for server, routes in routes_by_server.items()
            },
        )

    async def list(
        self,
        script: Script,
        *,
        servers: Sequence[AsyncHTTPTestServer] = (),
        globals_: Sequence[str] = (),
    ) -> CliRun:
        """Run `s3 ls` once against fresh routed handlers, as `run` does.

        The STS stub answers the S3 listing and trips on anything else.
        """
        return await run_s3_ls(
            self.aws_cli,
            self.sandbox,
            [self.metadata, self.server, *servers],
            self.env,
            s3=self.server,
            globals_=globals_,
            handlers={self.metadata: functools.partial(routed, script)},
        )


@pytest.fixture
def scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    metadata: AsyncHTTPTestServer,
) -> Scenario:
    return Scenario(aws_cli, sandbox, stub, metadata)


def assert_outcome(
    run: CliRun,
    returncode: int,
    stdout: bytes = b"",
    stderr: bytes | BytesStartingWith = b"",
    *,
    changes: FileChanges | None = None,
) -> None:
    """The run's exit status, output, and file changes.

    IMDS credentials are never cached, so a run changes no file unless
    `changes` says otherwise.
    """
    assert (run.returncode, run.stdout, run.stderr, run.changes) == (
        returncode,
        stdout,
        stderr,
        changes or {},
    ), run.describe()


def text(body: str, code: int = 200) -> HTTPResponse:
    return HTTPResponse.text(body, status=code)


def credentials_json(
    identity: str = "IMDS", **overrides: object
) -> HTTPResponse:
    return HTTPResponse.json({**metadata_credentials(identity), **overrides})


def imds_script(
    *,
    host: str = IMDS_HOST,
    prefix: str = "",
    token: Sequence[ResponseSpec] = (),
    role_list: Sequence[ResponseSpec] = (),
    credentials: Sequence[ResponseSpec] = (),
    role: str = ROLE,
    placement: Sequence[ResponseSpec] = (),
) -> Script:
    """The routes of one IMDS host; each route serves its list in order."""
    paths = (
        (("PUT", TOKEN_PATH), token),
        (("GET", ROLE_LIST_PATH), role_list),
        (("GET", ROLE_LIST_PATH + role), credentials),
        (("GET", PLACEMENT_PATH), placement),
    )
    return {
        (method, host, prefix + path): list(responses)
        for (method, path), responses in paths
        if responses
    }


def v2_script(
    credentials: HTTPResponse | Sequence[ResponseSpec] | None = None,
    *,
    host: str = IMDS_HOST,
    token: Sequence[ResponseSpec] | None = None,
    role_list: Sequence[ResponseSpec] | None = None,
    placement: Sequence[ResponseSpec] = (),
) -> Script:
    """One token, the role name, and `credentials` (default: valid ones)."""
    if credentials is None:
        credentials = [credentials_json()]
    elif isinstance(credentials, HTTPResponse):
        credentials = [credentials]
    return imds_script(
        host=host,
        token=[text(TOKEN)] if token is None else token,
        role_list=[text(ROLE)] if role_list is None else role_list,
        credentials=credentials,
        placement=placement,
    )


def token_put(base: str = f"http://{IMDS_HOST}") -> ImdsRequest:
    return ("PUT", base + TOKEN_PATH, None)


def metadata_get(
    path: str, token: str | None, base: str = f"http://{IMDS_HOST}"
) -> ImdsRequest:
    return ("GET", base + path, token)


def credential_round(
    token: str | None = TOKEN,
    *,
    base: str = f"http://{IMDS_HOST}",
    role: str = ROLE,
) -> list[ImdsRequest]:
    """PUT token, GET the role list, GET the role's credentials."""
    return [
        token_put(base),
        metadata_get(ROLE_LIST_PATH, token, base),
        metadata_get(ROLE_LIST_PATH + role, token, base),
    ]


def region_round(token: str | None = TOKEN) -> list[ImdsRequest]:
    """The CLI region lookup: PUT token, GET the instance's region."""
    return [token_put(), metadata_get(PLACEMENT_PATH, token)]


def requests_seen(run: CliRun) -> list[ImdsRequest]:
    """(method, target, x-aws-ec2-metadata-token) of every request.

    Also checks the rest of every request: the TTL header exactly on a
    token PUT (utils.py:408-416, 444-470), no body, none of the other
    compared headers (Authorization, X-Amz-Date, a security token,
    Content-Type), and, for an absolute-form target, a Host header that
    names the target's host.
    """
    seen = []
    for request in run.requests:
        headers = dict(request.headers)
        ttl = TOKEN_TTL if request.method == "PUT" else None
        assert headers[TTL_HEADER] == ttl, run.describe()
        assert all(headers[name] is None for name in UNSIGNED_HEADERS), (
            run.describe()
        )
        assert request.body_bytes == b"", run.describe()
        netloc = urlsplit(request.target).netloc
        assert netloc in ("", request.host), run.describe()
        seen.append((request.method, request.target, headers[TOKEN_HEADER]))
    return seen


def assert_listed(
    run: CliRun, requests: list[ImdsRequest], identity: str = "IMDS"
) -> None:
    """The listing carries `identity`'s key and token, and the provider's
    own requests are `requests`."""
    assert_signed_with(run, f"AKID{identity}", f"{identity}-token")
    assert requests_seen(without_s3(run)) == requests


def imds_output(
    identity: str = "IMDS",
    *,
    access_key: str | None = None,
    with_token: bool = True,
    expiration: str = FUTURE_EXPIRATION,
) -> bytes:
    """The export of `metadata_credentials(identity)` as printed."""
    return export_credentials_output(
        f"AKID{identity}" if access_key is None else access_key,
        f"{identity}-secret",
        f"{identity}-token" if with_token else None,
        expiration,
    )


def load_error(message: str) -> bytes:
    return f"{LOAD_ERROR_PREFIX}{message}\n".encode()


def freeze_error(message: str) -> bytes:
    return f"\naws: [ERROR]: {message}\n".encode()


async def cli_user_agent(scenario: Scenario) -> str:
    """`aws-cli/<version>`, the IMDS User-Agent (session.py:526-527).

    Runs with the scenario's environment, so HOME is the sandbox's and
    telemetry is off.
    """
    stdout, stderr, returncode = await run_command(
        [scenario.aws_cli, "--version"],
        scenario.env,
        cwd=scenario.sandbox.root,
    )
    assert returncode == 0, stderr
    return stdout.decode().split()[0]


async def test_imds_v2_sends_token_and_truncated_user_agent(
    scenario: Scenario,
) -> None:
    run = await scenario.run(
        v2_script(),
        normalize=functools.partial(normalize_request, imds_hosts=IMDS_HOSTS),
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round()
    user_agent = await cli_user_agent(scenario)
    assert user_agent.startswith("aws-cli/")
    assert [request.user_agent for request in run.requests] == [user_agent] * 3


async def test_imds_v2_signs_listing(scenario: Scenario) -> None:
    run = await scenario.list(v2_script())

    assert_listed(run, credential_round())


# 404 returns no token at once; 500 does once its attempts are spent
# (utils.py:418-424).
@pytest.mark.parametrize("code", [404, 500])
async def test_imds_token_status_falls_back_to_v1(
    scenario: Scenario, code: int
) -> None:
    run = await scenario.run(v2_script(token=[text("no token", code)]))

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round(None)


@pytest.mark.parametrize("code", [404, 500])
async def test_imds_token_status_falls_back_to_v1_and_signs_listing(
    scenario: Scenario, code: int
) -> None:
    run = await scenario.list(v2_script(token=[text("no token", code)]))

    assert_listed(run, credential_round(None))


async def test_imds_token_400_stops_without_credentials(
    scenario: Scenario,
) -> None:
    run = await scenario.run(v2_script(token=[text("bad request", 400)]))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert requests_seen(run) == [token_put()]


@pytest.mark.parametrize("source", ["env-uppercase", "config"])
async def test_imds_v1_disabled_without_token_raises(
    scenario: Scenario, source: str
) -> None:
    if source == "config":
        scenario.sandbox.config.write_text(
            "[default]\nec2_metadata_v1_disabled = true\n"
        )
    else:
        scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "TRUE"

    run = await scenario.run(v2_script(token=[text("nf", 404)]))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(V1_DISABLED_TEXT))
    assert requests_seen(run) == [token_put()]


@pytest.mark.parametrize("source", ["env-uppercase", "config"])
async def test_imds_v1_disabled_without_token_fails_listing(
    scenario: Scenario, source: str
) -> None:
    # The fetcher's error is raised as the client is created, so the
    # general handler reports it and no listing is sent.
    if source == "config":
        scenario.sandbox.config.write_text(
            "[default]\nec2_metadata_v1_disabled = true\n"
        )
    else:
        scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "TRUE"

    run = await scenario.list(v2_script(token=[text("nf", 404)]))

    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(V1_DISABLED_TEXT))
    assert requests_seen(run) == [token_put()]


async def test_imds_v1_disabled_with_token_400_finds_no_credentials(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "true"

    run = await scenario.run(v2_script(token=[text("bad request", 400)]))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert requests_seen(run) == [token_put()]


async def test_imds_v1_disabled_with_token_200_uses_v2(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "true"

    run = await scenario.run(v2_script(token=[text(TOKEN)]))

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round()


async def test_imds_v1_disabled_with_token_200_signs_listing(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "true"

    run = await scenario.list(v2_script(token=[text(TOKEN)]))

    assert_listed(run, credential_round())


async def test_imds_v1_disabled_requires_literal_true(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "1"

    run = await scenario.run(v2_script(token=[text("nf", 404)]))

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round(None)


async def test_imds_v1_disabled_not_literal_true_signs_listing_with_v1(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "1"

    run = await scenario.list(v2_script(token=[text("nf", 404)]))

    assert_listed(run, credential_round(None))


async def test_imds_role_list_failure_finds_no_credentials(
    scenario: Scenario,
) -> None:
    run = await scenario.run(v2_script(role_list=[text("nf", 404)]))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert requests_seen(run) == credential_round()[:2]


def without(*names: str) -> HTTPResponse:
    payload = {
        key: value
        for key, value in metadata_credentials("IMDS").items()
        if key not in names
    }
    return HTTPResponse.json(payload)


@pytest.mark.parametrize(
    "credentials",
    [
        without("Token"),
        HTTPResponse.json(
            {"Code": "AssumeRoleUnauthorizedAccess", "Message": "x"}
        ),
    ],
    ids=["no-token", "code-and-message"],
)
async def test_imds_unusable_credentials_find_no_credentials(
    scenario: Scenario, credentials: HTTPResponse
) -> None:
    run = await scenario.run(v2_script(credentials))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert requests_seen(run) == credential_round()


async def test_imds_credential_values_are_not_type_checked(
    scenario: Scenario,
) -> None:
    # Unlike SDKs that require Code == "Success", botocore reads only the
    # credential members.
    run = await scenario.run(v2_script(credentials_json(Code="Failure")))

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round()


async def test_imds_credential_values_unchecked_sign_listing(
    scenario: Scenario,
) -> None:
    run = await scenario.list(v2_script(credentials_json(Code="Failure")))

    assert_listed(run, credential_round())


async def test_imds_disabled_value_skips_imds(scenario: Scenario) -> None:
    scenario.env["AWS_EC2_METADATA_DISABLED"] = "TrUe"

    run = await scenario.run(v2_script())

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert run.requests == ()


async def test_imds_disabled_requires_literal_true(scenario: Scenario) -> None:
    scenario.env["AWS_EC2_METADATA_DISABLED"] = "1"

    run = await scenario.run(v2_script())

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round()


async def test_imds_disabled_not_literal_true_signs_listing(
    scenario: Scenario,
) -> None:
    scenario.env["AWS_EC2_METADATA_DISABLED"] = "1"

    run = await scenario.list(v2_script())

    assert_listed(run, credential_round())


def set_num_attempts(scenario: Scenario, source: str, value: str) -> None:
    if source == "env":
        scenario.env["AWS_METADATA_SERVICE_NUM_ATTEMPTS"] = value
    else:
        scenario.sandbox.config.write_text(
            f"[default]\nmetadata_service_num_attempts = {value}\n"
        )


async def test_imds_zero_num_attempts_sends_no_request(
    scenario: Scenario,
) -> None:
    set_num_attempts(scenario, "env", "0")

    run = await scenario.run(v2_script())

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert run.requests == ()


NUM_ATTEMPT_ROWS = [
    (
        ("env", "2"),
        v2_script(role_list=[text("error", 500), text(ROLE)]),
        [
            token_put(),
            metadata_get(ROLE_LIST_PATH, TOKEN),
            *credential_round()[1:],
        ],
    ),
    (
        ("env", "2"),
        v2_script(token=[text("error", 500), text("error", 500)]),
        [token_put(), *credential_round(None)],
    ),
    (
        ("config", "2"),
        v2_script(credentials=[text("not json"), credentials_json()]),
        [
            *credential_round(),
            metadata_get(ROLE_LIST_PATH + ROLE, TOKEN),
        ],
    ),
]


@pytest.mark.parametrize(
    ("setting", "script", "expected"),
    NUM_ATTEMPT_ROWS,
    ids=["two-role-500", "two-token-500", "config-two"],
)
async def test_imds_num_attempts_bounds_each_request(
    scenario: Scenario,
    setting: tuple[str, str],
    script: Script,
    expected: list[ImdsRequest],
) -> None:
    set_num_attempts(scenario, *setting)

    run = await scenario.run(script)

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == expected


@pytest.mark.parametrize(("setting", "script", "expected"), NUM_ATTEMPT_ROWS)
async def test_imds_num_attempts_bound_requests_before_signing_listing(
    scenario: Scenario,
    setting: tuple[str, str],
    script: Script,
    expected: list[ImdsRequest],
) -> None:
    set_num_attempts(scenario, *setting)

    run = await scenario.list(script)

    assert_listed(run, expected)


MODE_ERROR: Final = (
    "Invalid EC2 Instance Metadata endpoint mode: {} Valid endpoint modes "
    "(case-insensitive): ('ipv4', 'ipv6')."
)
ENDPOINT_ERROR: Final = "Invalid endpoint EC2 Instance Metadata endpoint: {}"


# The CLI builds the credential resolver when its session starts
# (awscli/customizations/assumerole.py:19-21), so an invalid IMDS setting
# fails every command, before any provider runs and even with env keys.
@pytest.mark.parametrize(
    ("setting", "stderr"),
    [
        pytest.param(
            ("ec2_metadata_service_endpoint_mode", "IPv3"),
            freeze_error(MODE_ERROR.format("IPv3")),
            id="mode-config",
        ),
        pytest.param(
            (ENDPOINT_VAR, "not.a:valid:dom@in"),
            freeze_error(ENDPOINT_ERROR.format("not.a:valid:dom@in")),
            id="endpoint-bad-host",
        ),
        pytest.param(
            ("ec2_metadata_service_endpoint", "127.0.0.1"),
            freeze_error(ENDPOINT_ERROR.format("127.0.0.1")),
            id="endpoint-config-no-scheme",
        ),
        # The timeout must be an integer; the message is CPython's int().
        pytest.param(
            ("AWS_METADATA_SERVICE_TIMEOUT", "1.5"),
            BytesStartingWith(b"\naws: [ERROR]: ", (b"1.5",)),
            id="timeout-float",
        ),
    ],
)
async def test_imds_config_error_aborts_resolver_build_despite_env_credentials(
    scenario: Scenario,
    setting: tuple[str, str],
    stderr: bytes | BytesStartingWith,
) -> None:
    name, value = setting
    if name.isupper():
        scenario.env[name] = value
    else:
        scenario.sandbox.config.write_text(f"[default]\n{name} = {value}\n")
    scenario.env.update(AWS_ACCESS_KEY_ID="AKIDENV", AWS_SECRET_ACCESS_KEY="s")

    run = await scenario.run(v2_script())

    assert_outcome(run, FREEZE_ERROR_RC, stderr=stderr)
    assert run.requests == ()


INTEGER_ERROR: Final = "invalid literal for int() with base 10: {}"
HTTP_CLIENT_ERROR: Final = "An HTTP Client raised an unhandled exception: {}"
TIMEOUT_NOT_POSITIVE: Final = (
    "Attempted to set connect timeout to {}, but the timeout cannot be set "
    "to a value less than or equal to 0."
)
# The native route's error for an endpoint URL in a form it does not read.
UNSUPPORTED_ENDPOINT: Final = HTTP_CLIENT_ERROR.format(
    "cannot ask the instance metadata service for credentials: this form of "
    "ec2_metadata_service_endpoint is not supported"
)
# A username and password in an endpoint's URL.
ENDPOINT_LOGIN: Final = "user:endpoint-secret"

REFUSED_SETTINGS = [
    pytest.param(
        ("ec2_metadata_service_endpoint_mode", "IPv3"),
        MODE_ERROR.format("IPv3"),
        id="mode-config",
    ),
    pytest.param(
        (MODE_VAR, ""),
        MODE_ERROR.format(""),
        id="mode-empty",
    ),
    pytest.param(
        (ENDPOINT_VAR, "not.a:valid:dom@in"),
        ENDPOINT_ERROR.format("not.a:valid:dom@in"),
        id="endpoint-bad-host",
    ),
    pytest.param(
        ("ec2_metadata_service_endpoint", "127.0.0.1"),
        ENDPOINT_ERROR.format("127.0.0.1"),
        id="endpoint-config-no-scheme",
    ),
    pytest.param(
        ("AWS_METADATA_SERVICE_TIMEOUT", "1.5"),
        INTEGER_ERROR.format("'1.5'"),
        id="timeout-float",
    ),
    pytest.param(
        ("AWS_METADATA_SERVICE_TIMEOUT", ""),
        INTEGER_ERROR.format("''"),
        id="timeout-empty",
    ),
    pytest.param(
        ("metadata_service_num_attempts", "two"),
        INTEGER_ERROR.format("'two'"),
        id="attempts-config-word",
    ),
]


def configure(scenario: Scenario, name: str, value: str) -> None:
    """Set a variable, or a key of the default profile."""
    if name.isupper():
        scenario.env[name] = value
    else:
        scenario.sandbox.config.write_text(
            f"[default]\n{name} = {value}\n", encoding="utf-8"
        )


# The refusal fails `s3 ls` as it fails every command: with keys in the
# environment that would have signed the listing, and for a listing that
# signs nothing. No provider is asked and nothing is sent.
@pytest.mark.parametrize(("setting", "message"), REFUSED_SETTINGS)
@pytest.mark.parametrize(
    "globals_", [(), ("--no-sign-request",)], ids=["signed", "unsigned"]
)
async def test_imds_config_error_fails_listing_despite_env_credentials(
    scenario: Scenario,
    setting: tuple[str, str],
    message: str,
    globals_: tuple[str, ...],
) -> None:
    configure(scenario, *setting)
    scenario.env.update(AWS_ACCESS_KEY_ID="AKIDENV", AWS_SECRET_ACCESS_KEY="s")

    run = await scenario.list(v2_script(), globals_=globals_)

    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


async def run_with_metadata_timeout(
    scenario: Scenario, command: list[str], timeout: str | None = "1.5"
) -> CliRun:
    """`aws COMMAND` with `timeout` for the metadata service's: by default
    one botocore refuses, and none at all for None."""
    if timeout is not None:
        scenario.env["AWS_METADATA_SERVICE_TIMEOUT"] = timeout
    env = {k: v for k, v in scenario.env.items() if k != "AWS_MAX_ATTEMPTS"}
    return await run_aws(
        scenario.aws_cli,
        command,
        scenario.sandbox,
        [scenario.metadata, scenario.server],
        env,
    )


# The session starts before the command reads its own arguments, so the
# refusal comes ahead of the command's own usage error.
@pytest.mark.parametrize(
    "command",
    [
        ["s3", "ls", "--no-such-option"],
        ["s3", "ls", "--page-size", "many"],
        ["s3", "cp"],
        ["s3"],
        # A `--query` the AWS CLI compiles changes nothing.
        ["--query", "Contents", "s3", "cp"],
    ],
    ids=[
        "unknown-option",
        "bad-value",
        "missing-paths",
        "no-subcommand",
        "missing-paths-with-query",
    ],
)
async def test_imds_config_error_precedes_command_usage_error(
    scenario: Scenario, command: list[str]
) -> None:
    run = await run_with_metadata_timeout(scenario, command)

    message = INTEGER_ERROR.format("'1.5'")
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


# A top-level argument is handled before the session starts, so its error
# comes first, for a command that would run and for one that fails in its
# own parse: an endpoint URL without a scheme, and one whose brackets
# `urlparse` raises for.
@pytest.mark.parametrize(
    ("url", "returncode", "message"),
    [
        ("x", 252, b'Bad value for --endpoint-url "x": scheme is missing.'),
        ("http://[", 255, freeze_error("Invalid IPv6 URL")),
        (
            "http://[127.0.0.1]",
            255,
            freeze_error("An IPv4 address cannot be in brackets"),
        ),
    ],
    ids=["no-scheme", "open-bracket", "ipv4-in-brackets"],
)
@pytest.mark.parametrize(
    "command", [["s3", "ls"], ["s3", "cp"]], ids=["listing", "missing-paths"]
)
async def test_imds_config_error_follows_top_level_argument_error(
    scenario: Scenario,
    url: str,
    returncode: int,
    message: bytes,
    command: list[str],
) -> None:
    run = await run_with_metadata_timeout(
        scenario, ["--endpoint-url", url, *command]
    )

    assert run.returncode == returncode, run.describe()
    assert message in run.stderr, run.describe()
    assert b"invalid literal for int()" not in run.stderr, run.describe()
    assert run.requests == ()


# `urlparse` also raises for a host whose NFKC form gains a `/`, `?`, `#`,
# `@`, or `:`, as U+2100 gains its slash. The native route has no
# normalization tables, takes the URL, and reports the refused setting:
# failures.txt, `parity-gap`.
async def test_imds_config_error_follows_endpoint_url_normalization_error(
    scenario: Scenario,
) -> None:
    run = await run_with_metadata_timeout(
        scenario, ["--endpoint-url", "http://a\u2100b", "s3", "cp"]
    )

    message = (
        "netloc 'a\u2100b' contains invalid characters under NFKC "
        "normalization"
    )
    assert_outcome(run, 255, stderr=freeze_error(message))
    assert run.requests == ()


# `--query` is a top-level argument too: the AWS CLI compiles the
# expression before its session starts, so one that does not compile is
# what it reports for a command that fails in its own parse, whatever the
# metadata settings. The native route does not compile JMESPath. It reports
# the command's usage error, with the same status, or the setting it
# refuses: failures.txt, `parity-gap`, both.
@pytest.mark.parametrize(
    "timeout", [None, "1.5"], ids=["valid-settings", "refused-setting"]
)
async def test_imds_invalid_query_is_reported_ahead_of_failing_command(
    scenario: Scenario, timeout: str | None
) -> None:
    run = await run_with_metadata_timeout(
        scenario, ["--query", "[", "s3", "cp"], timeout
    )

    assert run.returncode == 252, run.describe()
    assert b"Bad value for --query [: " in run.stderr, run.describe()
    assert run.requests == ()


# A variable whose value is not Unicode is still the setting's first
# source, and its text is not `true`: the service is not disabled, a fetch
# without a token goes on, and the address is the IPv4 one, whatever the
# profile's key says.
@pytest.mark.parametrize(
    ("variable", "key"),
    [
        ("AWS_EC2_METADATA_DISABLED", None),
        ("AWS_EC2_METADATA_V1_DISABLED", "ec2_metadata_v1_disabled"),
        ("AWS_IMDS_USE_IPV6", "imds_use_ipv6"),
    ],
    ids=["disabled", "v1-disabled", "use-ipv6"],
)
async def test_imds_boolean_variable_not_unicode_is_not_true_signs_listing(
    scenario: Scenario, variable: str, key: str | None
) -> None:
    scenario.env[variable] = "true\udcff"
    if key is not None:
        scenario.sandbox.config.write_text(f"[default]\n{key} = true\n")

    run = await scenario.list(v2_script(token=[text("nf", 404)]))

    assert_listed(run, credential_round(None))


# `int()` reads whitespace around the number: this is two attempts.
async def test_imds_num_attempts_read_as_python_int_signs_listing(
    scenario: Scenario,
) -> None:
    set_num_attempts(scenario, "env", " 2 ")
    script = v2_script(role_list=[text("error", 500), text(ROLE)])

    run = await scenario.list(script)

    assert_listed(
        run,
        [
            token_put(),
            metadata_get(ROLE_LIST_PATH, TOKEN),
            *credential_round()[1:],
        ],
    )


# No attempt sends nothing.
@pytest.mark.parametrize("value", ["-1", "-0"])
async def test_imds_num_attempts_below_one_finds_no_credentials_for_listing(
    scenario: Scenario, value: str
) -> None:
    set_num_attempts(scenario, "env", value)

    run = await scenario.list(v2_script())

    assert_outcome(run, LOAD_ERROR_RC, stderr=LISTING_NO_CREDENTIALS)
    assert run.requests == ()


# A timeout urllib3 refuses fails the first request, before anything is
# sent: one that is not positive (util/timeout.py). The number is printed
# as Python's int prints it.
@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("0", TIMEOUT_NOT_POSITIVE.format("0")),
        ("-0", TIMEOUT_NOT_POSITIVE.format("0")),
        (" -05 ", TIMEOUT_NOT_POSITIVE.format("-5")),
    ],
    ids=["zero", "negative-zero", "negative"],
)
async def test_imds_timeout_refused_by_http_client_fails_listing(
    scenario: Scenario, value: str, reason: str
) -> None:
    scenario.env["AWS_METADATA_SERVICE_TIMEOUT"] = value

    run = await scenario.list(v2_script())

    message = HTTP_CLIENT_ERROR.format(reason)
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


# With no attempt there is no request for the timeout to fail.
async def test_imds_refused_timeout_without_attempts_finds_no_credentials(
    scenario: Scenario,
) -> None:
    scenario.env.update(
        AWS_METADATA_SERVICE_TIMEOUT="0", AWS_METADATA_SERVICE_NUM_ATTEMPTS="0"
    )

    run = await scenario.list(v2_script())

    assert_outcome(run, LOAD_ERROR_RC, stderr=LISTING_NO_CREDENTIALS)
    assert run.requests == ()


ENDPOINT_ROWS = [
    ({MODE_VAR: "IPv6"}, "", f"http://{IPV6_HOST}"),
    ({"AWS_IMDS_USE_IPV6": "true"}, "", f"http://{IPV6_HOST}"),
    ({}, "imds_use_ipv6 = TRUE\n", f"http://{IPV6_HOST}"),
    ({MODE_VAR: "ipv4"}, "imds_use_ipv6 = true\n", f"http://{IMDS_HOST}"),
    ({ENDPOINT_VAR: f"{CONFIGURED_BASE}/"}, "", CONFIGURED_BASE),
    (
        {},
        f"ec2_metadata_service_endpoint = {CONFIGURED_BASE}\n",
        CONFIGURED_BASE,
    ),
    ({ENDPOINT_VAR: f"{CONFIGURED_BASE}/p"}, "", f"{CONFIGURED_BASE}/p"),
    (
        {MODE_VAR: "ipv6", ENDPOINT_VAR: CONFIGURED_BASE},
        "",
        CONFIGURED_BASE,
    ),
    ({ENDPOINT_VAR: ""}, "", f"http://{IMDS_HOST}"),
]


@pytest.mark.parametrize(
    ("settings", "config", "base"),
    ENDPOINT_ROWS,
    ids=[
        "mode-ipv6",
        "use-ipv6-env",
        "use-ipv6-config",
        "mode-wins-over-use-ipv6",
        "endpoint-env",
        "endpoint-config",
        "endpoint-path-prefix",
        "endpoint-wins-over-ipv6",
        "endpoint-empty",
    ],
)
async def test_imds_endpoint_selection_sets_request_target(
    scenario: Scenario, settings: dict[str, str], config: str, base: str
) -> None:
    scenario.env.update(settings)
    if config:
        scenario.sandbox.config.write_text(f"[default]\n{config}")
    host, _, prefix = base.removeprefix("http://").partition("/")
    prefix = f"/{prefix}" if prefix else ""

    run = await scenario.run(
        imds_script(
            host=host,
            prefix=prefix,
            token=[text(TOKEN)],
            role_list=[text(ROLE)],
            credentials=[credentials_json()],
        )
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round(base=base)
    assert {request.host for request in run.requests} == {host}


@pytest.mark.parametrize(("settings", "config", "base"), ENDPOINT_ROWS)
async def test_imds_endpoint_selection_targets_requests_before_signing(
    scenario: Scenario, settings: dict[str, str], config: str, base: str
) -> None:
    scenario.env.update(settings)
    if config:
        scenario.sandbox.config.write_text(f"[default]\n{config}")
    host, _, prefix = base.removeprefix("http://").partition("/")
    prefix = f"/{prefix}" if prefix else ""

    run = await scenario.list(
        imds_script(
            host=host,
            prefix=prefix,
            token=[text(TOKEN)],
            role_list=[text(ROLE)],
            credentials=[credentials_json()],
        )
    )

    assert_listed(run, credential_round(base=base))
    assert {r.host for r in without_s3(run).requests} == {host}


async def test_imds_no_proxy_sends_configured_endpoint_direct(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    scenario.send_direct(forwarder)

    run = await scenario.run(
        v2_script(host=scenario.direct_host), servers=[forwarder]
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round(base="")
    assert {request.host for request in run.requests} == {scenario.direct_host}


async def test_imds_no_proxy_direct_endpoint_signs_listing(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    scenario.send_direct(forwarder)

    run = await scenario.list(
        v2_script(host=scenario.direct_host), servers=[forwarder]
    )

    assert_listed(run, credential_round(base=""))
    hosts = {request.host for request in without_s3(run).requests}
    assert hosts == {scenario.direct_host}


# A configured endpoint is a stand-in for the service, not an AWS product,
# so the native route reads its URL as far as it sends requests and is
# owed no more. Both routes read a scheme in any case.
@pytest.mark.parametrize(
    "template", ["HTTP://127.0.0.1:{port}"], ids=["scheme-uppercase"]
)
async def test_imds_configured_endpoint_spelling_signs_listing(
    scenario: Scenario, forwarder: AsyncHTTPTestServer, template: str
) -> None:
    scenario.send_direct(forwarder)
    scenario.env[ENDPOINT_VAR] = template.format(port=scenario.metadata.port)

    run = await scenario.list(
        v2_script(host=scenario.direct_host), servers=[forwarder]
    )

    assert_listed(run, credential_round(base=""))
    hosts = {request.host for request in without_s3(run).requests}
    assert hosts == {scenario.direct_host}


# botocore accepts an endpoint whose port urllib3 cannot read as it builds
# its chain; the fetch then fails at its first request with botocore's
# error (utils.py:437-440).
@pytest.mark.parametrize(
    ("template", "message"),
    [
        (
            "http://127.0.0.1:x",
            ENDPOINT_ERROR.format("http://127.0.0.1:x/latest/api/token"),
        ),
        (
            "http://127.0.0.1:65536/",
            ENDPOINT_ERROR.format("http://127.0.0.1:65536/latest/api/token"),
        ),
    ],
    ids=["port-not-a-number", "port-out-of-range"],
)
async def test_imds_endpoint_urllib3_refuses_fails_listing(
    scenario: Scenario,
    forwarder: AsyncHTTPTestServer,
    template: str,
    message: str,
) -> None:
    scenario.send_direct(forwarder)
    scenario.env[ENDPOINT_VAR] = template.format(host=scenario.direct_host)

    run = await scenario.list(
        v2_script(host=scenario.direct_host), servers=[forwarder]
    )

    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


# A username and password in the endpoint's URL. The native route asks the
# endpoint without them, and nothing it prints, `--debug` included, has
# the password.
@pytest.mark.native_only
async def test_imds_endpoint_login_is_dropped_and_never_shown(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    scenario.send_direct(forwarder)
    scenario.env[ENDPOINT_VAR] = (
        f"http://{ENDPOINT_LOGIN}@{scenario.direct_host}"
    )

    run = await scenario.list(
        v2_script(host=scenario.direct_host),
        servers=[forwarder],
        globals_=["--debug"],
    )

    password = ENDPOINT_LOGIN.partition(":")[2].encode()
    assert run.returncode == 0, run.describe()
    assert password not in run.stdout + run.stderr, run.describe()
    assert_listed(run, credential_round(base=""))
    hosts = {request.host for request in without_s3(run).requests}
    assert hosts == {scenario.direct_host}


# The AWS CLI names an endpoint it refuses as it is configured, username
# and password included. The native route deliberately never prints them,
# which failures.txt lists as a `parity-gap`.
async def test_imds_invalid_endpoint_with_login_is_named_as_configured(
    scenario: Scenario,
) -> None:
    endpoint = f"http://{ENDPOINT_LOGIN}@bad_host"
    scenario.env[ENDPOINT_VAR] = endpoint

    run = await scenario.list(v2_script())

    message = ENDPOINT_ERROR.format(endpoint)
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


@pytest.mark.native_only
async def test_imds_invalid_endpoint_is_named_without_its_login(
    scenario: Scenario,
) -> None:
    scenario.env[ENDPOINT_VAR] = f"http://{ENDPOINT_LOGIN}@bad_host"

    run = await scenario.list(v2_script(), globals_=["--no-sign-request"])

    message = ENDPOINT_ERROR.format("http://***@bad_host")
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


# Forms of an endpoint's URL the native route does not read: a space
# before the scheme, and an IPv6 address with a zone. botocore accepts each
# as it builds its chain, so a command that has credentials elsewhere is
# not affected. A fetch that would use the endpoint fails before anything
# is sent, with an error that says the form is not supported. Neither has
# a test on the AWS CLI's route, where it would look up a name or leave
# loopback.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "template",
    [" http://{host}", "http://[fe80::1%eth0]"],
    ids=["leading-space", "ipv6-zone"],
)
async def test_imds_unsupported_endpoint_form_fails_listing(
    scenario: Scenario, forwarder: AsyncHTTPTestServer, template: str
) -> None:
    scenario.send_direct(forwarder)
    scenario.env[ENDPOINT_VAR] = template.format(host=scenario.direct_host)

    run = await scenario.list(
        v2_script(host=scenario.direct_host), servers=[forwarder]
    )

    message = freeze_error(UNSUPPORTED_ENDPOINT)
    assert_outcome(run, FREEZE_ERROR_RC, stderr=message)
    assert run.requests == ()


@pytest.mark.native_only
async def test_imds_unsupported_endpoint_form_is_unused_with_env_credentials(
    scenario: Scenario,
) -> None:
    scenario.env.update(
        {ENDPOINT_VAR: " http://imds.invalid"},
        AWS_ACCESS_KEY_ID="AKIDENV",
        AWS_SECRET_ACCESS_KEY="ENV-secret",
    )

    run = await scenario.list(v2_script())

    assert_signed_with(run, "AKIDENV", None)
    assert requests_seen(without_s3(run)) == []


@asynccontextmanager
async def tls_front(
    context: ssl.SSLContext, backend: AsyncHTTPTestServer
) -> AsyncIterator[int]:
    """A loopback port that terminates TLS with `context` and relays each
    connection's bytes to `backend`, so a plain stub serves `https`."""

    async def pump(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while data := await reader.read(65536):
                writer.write(data)
                await writer.drain()
        except OSError:
            # A client that closes without a TLS goodbye.
            pass
        finally:
            writer.close()

    async def relay(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            "127.0.0.1", backend.port
        )
        await asyncio.gather(
            pump(reader, upstream_writer), pump(upstream_reader, writer)
        )

    server = await asyncio.start_server(relay, "127.0.0.1", 0, ssl=context)
    async with server:
        yield server.sockets[0].getsockname()[1]


# An `https` endpoint. botocore's fetcher builds its session without the
# CLI's CA settings (utils.py:367-370), so it verifies such an endpoint
# against botocore's own bundle (httpsession.py:96-103) and no stand-in can
# serve one to the AWS CLI. The built binary deliberately verifies it with
# the command's trust, the bundle AWS_CA_BUNDLE names here, which is the
# TLS proxy's CA. So these tests are `native_only`.
@pytest.mark.native_only
async def test_imds_https_endpoint_trusted_by_ca_bundle_signs_listing(
    scenario: Scenario, stub: Stub
) -> None:
    _, proxy = stub
    context = proxy.ca.issue_context("127.0.0.1")

    async with tls_front(context, scenario.metadata) as port:
        host = scenario.send_secure(port)
        run = await scenario.list(v2_script(host=host))

    assert_listed(run, credential_round(base=""))
    assert {r.host for r in without_s3(run).requests} == {host}


# A certificate the bundle does not verify, or one for another name, fails
# each request as a connection that could not be made does: the fetcher
# finds no credentials, and neither the stub nor S3 sees a request. The
# command ends at once: s2n, the CRT's TLS on Linux, would otherwise hold
# each connection whose handshake it failed open for 10 to 30 s.
@pytest.mark.native_only
@pytest.mark.parametrize("fault", ["untrusted-ca", "wrong-name"])
async def test_imds_https_endpoint_unverified_finds_no_credentials(
    scenario: Scenario, stub: Stub, fault: str
) -> None:
    _, proxy = stub
    if fault == "untrusted-ca":
        context = TLSProxyCA().issue_context("127.0.0.1")
    else:
        context = proxy.ca.issue_context(CONFIGURED_HOST)

    async with tls_front(context, scenario.metadata) as port:
        host = scenario.send_secure(port)
        started = time.monotonic()
        run = await scenario.list(v2_script(host=host))
        elapsed = time.monotonic() - started

    assert_outcome(run, LOAD_ERROR_RC, stderr=LISTING_NO_CREDENTIALS)
    assert run.requests == ()
    assert elapsed < S2N_BLINDING_MIN_SECONDS


@pytest.mark.parametrize(
    "template",
    ["http://127.0.0.1:{port}", "127.0.0.1:{port}"],
    ids=["with-scheme", "without-scheme"],
)
async def test_imds_refused_proxy_aborts_credential_resolution(
    refused_port: int, scenario: Scenario, template: str
) -> None:
    scenario.use_configured_endpoint()
    scenario.env["HTTP_PROXY"] = template.format(port=refused_port)

    run = await scenario.run(v2_script(host=CONFIGURED_HOST))

    message = (
        f'Failed to connect to proxy URL: "http://127.0.0.1:{refused_port}"'
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert run.requests == ()


async def test_imds_refused_proxy_fails_listing(
    refused_port: int, scenario: Scenario
) -> None:
    scenario.use_configured_endpoint()
    scenario.env["HTTP_PROXY"] = f"127.0.0.1:{refused_port}"

    run = await scenario.list(v2_script(host=CONFIGURED_HOST))

    message = (
        f'Failed to connect to proxy URL: "http://127.0.0.1:{refused_port}"'
    )
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


# A proxy in front of the service is not an AWS product, so the built
# binary's native route has only the simple case: a cleartext proxy that
# takes no username and password, in front of an `http` endpoint. The AWS
# CLI logs in to a proxy whose URL has a username and password
# (httpsession.py:245-256), which failures.txt lists as a `parity-gap`.
async def test_imds_proxy_with_credentials_signs_listing(
    scenario: Scenario,
) -> None:
    scenario.use_configured_endpoint()
    scenario.env["HTTP_PROXY"] = f"http://{PROXY_LOGIN}@{scenario.direct_host}"

    run = await scenario.list(v2_script(host=CONFIGURED_HOST))

    assert_listed(run, credential_round(base=CONFIGURED_BASE))


# On a machine that is no instance such a proxy has no credentials to
# give, and both routes end alike. The AWS CLI asks through the proxy and
# gets no token and no role (utils.py:424-425, 471-487); the native route
# asks nothing. Either way no provider has credentials.
async def test_imds_proxy_with_credentials_refusing_finds_no_credentials(
    scenario: Scenario,
) -> None:
    scenario.use_configured_endpoint()
    scenario.env["HTTP_PROXY"] = f"http://{PROXY_LOGIN}@{scenario.direct_host}"
    forbidden = text("Forbidden", 403)
    script = imds_script(
        host=CONFIGURED_HOST, token=[forbidden], role_list=[forbidden]
    )

    run = await scenario.list(script)

    assert_outcome(run, LOAD_ERROR_RC, stderr=LISTING_NO_CREDENTIALS)
    asked = credential_round(None, base=CONFIGURED_BASE)[:2]
    assert requests_seen(run) in ([], asked)


# The native route does not leave such a proxy to Python and does not use
# it. The service is not asked, whatever attempts and timeout are
# configured, and the chain ends with no credentials, as it does for a
# service that cannot be reached. The proxy here is the metadata stub,
# which would answer.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "template",
    ["http://{login}@{host}", "https://{host}"],
    ids=["proxy-with-credentials", "proxy-over-tls"],
)
async def test_imds_unsupported_proxy_finds_no_credentials(
    scenario: Scenario, template: str
) -> None:
    scenario.use_configured_endpoint()
    scenario.env.update(
        HTTP_PROXY=template.format(
            login=PROXY_LOGIN, host=scenario.direct_host
        ),
        AWS_METADATA_SERVICE_NUM_ATTEMPTS="1000",
        AWS_METADATA_SERVICE_TIMEOUT="100",
    )

    started = time.monotonic()
    run = await scenario.list(v2_script(host=CONFIGURED_HOST))
    elapsed = time.monotonic() - started

    assert_outcome(run, LOAD_ERROR_RC, stderr=LISTING_NO_CREDENTIALS)
    assert run.requests == ()
    assert elapsed < PROMPT_SECONDS


# `--debug` says once why the service was not asked, and nothing the
# command prints names the proxy's password.
@pytest.mark.native_only
async def test_imds_unsupported_proxy_is_named_in_debug_output(
    scenario: Scenario,
) -> None:
    scenario.use_configured_endpoint()
    scenario.env["HTTP_PROXY"] = f"http://{PROXY_LOGIN}@{scenario.direct_host}"

    run = await scenario.list(
        v2_script(host=CONFIGURED_HOST), globals_=["--debug"]
    )

    record = f" - awscli.native.credentials - DEBUG - {PROXY_UNSUPPORTED}\n"
    password = PROXY_LOGIN.partition(":")[2].encode()
    assert run.returncode == LOAD_ERROR_RC, run.describe()
    assert run.stderr.count(record.encode()) == 1, run.describe()
    assert run.stderr.endswith(LISTING_NO_CREDENTIALS), run.describe()
    assert password not in run.stdout + run.stderr, run.describe()
    assert run.requests == ()


# A proxy in front of an `https` endpoint would be a tunnel, which the
# native route does not build. The endpoint is one the user named, so the
# fetch fails before any request, with an error that says why.
@pytest.mark.native_only
async def test_imds_https_endpoint_through_proxy_fails_listing(
    scenario: Scenario,
) -> None:
    # HTTPS_PROXY stays the TLS proxy S3 is reached through.
    scenario.env[ENDPOINT_VAR] = f"https://{CONFIGURED_HOST}"

    run = await scenario.list(v2_script(host=CONFIGURED_HOST))

    message = (
        "An HTTP Client raised an unhandled exception: cannot ask the "
        "instance metadata service for credentials: an https endpoint is "
        "not supported through a proxy"
    )
    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(message))
    assert run.requests == ()


def set_fault_timing(scenario: Scenario) -> None:
    """The 1 s timeout of the fault rows, with two attempts per request.

    The second attempt is what tells a retried fault from one that is
    not (utils.py:418-436, 470-485).
    """
    scenario.env.update(
        AWS_METADATA_SERVICE_TIMEOUT=FAULT_TIMEOUT,
        AWS_METADATA_SERVICE_NUM_ATTEMPTS="2",
    )


async def test_imds_token_read_timeout_falls_back_to_v1_without_retry(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    # A token ReadTimeoutError returns None at once, attempts left or not
    # (utils.py:427-428), as on a container whose hop limit drops the PUT.
    set_fault_timing(scenario)
    scenario.send_direct(forwarder)

    run = await scenario.run(
        v2_script(host=scenario.direct_host, token=[stalled()]),
        servers=[forwarder],
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round(None, base="")


async def test_imds_token_read_timeout_signs_listing_with_v1(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    set_fault_timing(scenario)
    scenario.send_direct(forwarder)

    run = await scenario.list(
        v2_script(host=scenario.direct_host, token=[stalled()]),
        servers=[forwarder],
    )

    assert_listed(run, credential_round(None, base=""))


async def test_imds_role_list_read_timeout_is_retried(
    scenario: Scenario,
) -> None:
    # Unlike the token PUT, `_get_request` retries a ReadTimeoutError
    # with the other RETRYABLE_HTTP_ERRORS (utils.py:470-485).
    set_fault_timing(scenario)
    scenario.use_configured_endpoint()

    run = await scenario.run(
        v2_script(host=CONFIGURED_HOST, role_list=[stalled(), text(ROLE)])
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == [
        token_put(CONFIGURED_BASE),
        metadata_get(ROLE_LIST_PATH, TOKEN, CONFIGURED_BASE),
        *credential_round(base=CONFIGURED_BASE)[1:],
    ]


async def test_imds_role_list_read_timeout_retried_before_signing(
    scenario: Scenario,
) -> None:
    set_fault_timing(scenario)
    scenario.use_configured_endpoint()

    run = await scenario.list(
        v2_script(host=CONFIGURED_HOST, role_list=[stalled(), text(ROLE)])
    )

    assert_listed(
        run,
        [
            token_put(CONFIGURED_BASE),
            metadata_get(ROLE_LIST_PATH, TOKEN, CONFIGURED_BASE),
            *credential_round(base=CONFIGURED_BASE)[1:],
        ],
    )


async def test_imds_direct_token_connection_closed_is_retried_then_v1(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    # A connection closed without a response is ConnectionClosedError, a
    # RETRYABLE_HTTP_ERRORS member (utils.py:429-436); exhausted attempts
    # fall back to v1.
    set_fault_timing(scenario)
    scenario.send_direct(forwarder)

    run = await scenario.run(
        v2_script(host=scenario.direct_host, token=[dropped(), dropped()]),
        servers=[forwarder],
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == [
        token_put(""),
        *credential_round(None, base=""),
    ]


async def test_imds_token_connection_closed_retried_then_v1_signs_listing(
    scenario: Scenario, forwarder: AsyncHTTPTestServer
) -> None:
    set_fault_timing(scenario)
    scenario.send_direct(forwarder)

    run = await scenario.list(
        v2_script(host=scenario.direct_host, token=[dropped(), dropped()]),
        servers=[forwarder],
    )

    assert_listed(run, [token_put(""), *credential_round(None, base="")])


async def test_imds_token_with_newline_fails_header_validation(
    scenario: Scenario,
) -> None:
    # The token is used as returned, so its line feed fails the HTTP
    # client's header check and no metadata GET is sent; the check's own
    # wording is the HTTP client's.
    run = await scenario.run(v2_script(token=[text(f"{TOKEN}\n")]))

    prefix = (
        f"{LOAD_ERROR_PREFIX}An HTTP Client raised an unhandled exception: "
    )
    assert_outcome(
        run, LOAD_ERROR_RC, stderr=BytesStartingWith(prefix.encode())
    )
    assert requests_seen(run) == [token_put()]


async def test_imds_credential_source_without_credentials_raises(
    scenario: Scenario,
) -> None:
    scenario.sandbox.config.write_text(
        "[default]\n"
        f"role_arn = {ROLE_ARN}\n"
        "credential_source = Ec2InstanceMetadata\n"
    )

    run = await scenario.run(v2_script(token=[text("bad request", 400)]))

    # credentials.py:1864-1877.
    message = (
        "Error when retrieving credentials from Ec2InstanceMetadata: No "
        "credentials found in credential_source referenced in profile "
        "default"
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert requests_seen(run) == [token_put()]


def utc_text(moment: datetime, fraction: str = "") -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + fraction + "Z"


def from_now(seconds: int) -> datetime:
    return datetime.now(UTC).replace(microsecond=0) + timedelta(
        seconds=seconds
    )


def assert_extended(run: CliRun, started: float, finished: float) -> None:
    """The run printed an expiry in the extension window.

    botocore rewrites the expiry to `utcnow() + 900 s + randint(120, 600)`
    truncated to whole seconds (utils.py:630-646), so the printed value
    lies 1020-1500 s after the run, less up to one truncated second. It
    prints through `isoformat()` (exportcreds.py:38-40), whose exact shape
    (`T` separator, `+00:00`, no fraction) is pinned here because the
    masking that follows hides it.
    """
    assert run.returncode == 0, run.describe()
    printed = json.loads(run.stdout)["Expiration"]
    moment = datetime.fromisoformat(printed)
    assert printed == moment.isoformat(), printed
    assert moment.utcoffset() == timedelta(0), printed
    assert moment.microsecond == 0, printed
    earliest = started + EXTENSION_MIN_SECONDS - 1
    latest = finished + EXTENSION_MAX_SECONDS
    assert earliest <= moment.timestamp() <= latest, printed


def mask_extended(run: CliRun) -> CliRun:
    """`run` with its random extended expiry replaced by a placeholder."""
    printed = json.loads(run.stdout)["Expiration"]
    stdout = run.stdout.replace(
        printed.encode(), EXTENDED_PLACEHOLDER.encode()
    )
    return dataclasses.replace(run, stdout=stdout)


@pytest.mark.parametrize(
    "expiration",
    ["2000-01-01T00:00:00Z", 16 * 60],
    ids=["expired", "16-minutes"],
)
async def test_imds_strict_expiration_inside_window_is_extended(
    scenario: Scenario, expiration: str | int
) -> None:
    if isinstance(expiration, int):
        expiration = utc_text(from_now(expiration))
    started = time.time()

    run = await scenario.run(
        v2_script(credentials_json(Expiration=expiration))
    )

    assert_extended(run, started, time.time())
    assert_outcome(
        mask_extended(run), 0, imds_output(expiration=EXTENDED_PLACEHOLDER)
    )
    assert requests_seen(run) == credential_round()


@pytest.mark.parametrize(
    "expiration",
    ["2000-01-01T00:00:00Z", 16 * 60],
    ids=["expired", "16-minutes"],
)
async def test_imds_strict_expiration_inside_window_signs_listing(
    scenario: Scenario, expiration: str | int
) -> None:
    if isinstance(expiration, int):
        expiration = utc_text(from_now(expiration))

    run = await scenario.list(
        v2_script(credentials_json(Expiration=expiration))
    )

    assert_listed(run, credential_round())


async def test_imds_expiration_outside_strict_window_is_kept(
    scenario: Scenario,
) -> None:
    # 30 minutes is 300 s past the latest extension trigger (1500 s).
    moment = from_now(30 * 60)
    expiration = utc_text(moment)

    run = await scenario.run(
        v2_script(credentials_json(Expiration=expiration))
    )

    assert_outcome(run, 0, imds_output(expiration=moment.isoformat()))
    assert requests_seen(run) == credential_round()


async def test_imds_expiration_outside_strict_window_signs_listing(
    scenario: Scenario,
) -> None:
    expiration = utc_text(from_now(30 * 60))

    run = await scenario.list(
        v2_script(credentials_json(Expiration=expiration))
    )

    assert_listed(run, credential_round())


async def test_imds_expiration_parse_failure_is_raised(
    scenario: Scenario,
) -> None:
    # The parser's message after the prefix is dateutil's.
    run = await scenario.run(
        v2_script(credentials_json(Expiration="not a date"))
    )

    stderr = BytesStartingWith(LOAD_ERROR_PREFIX.encode(), (b"not a date",))
    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert requests_seen(run) == credential_round()


def expiring(identity: str, seconds: int | None) -> tuple[HTTPResponse, str]:
    """Credentials in the `.000Z` form strptime rejects (no extension).

    `seconds` None gives credentials that expired in 2000.
    """
    if seconds is None:
        moment = datetime(2000, 1, 1, tzinfo=UTC)
    else:
        moment = from_now(seconds)
    response = credentials_json(identity, Expiration=utc_text(moment, ".000"))
    return response, moment.isoformat()


def refresh_script(*credentials: HTTPResponse) -> Script:
    """Two full rounds, serving `credentials` in order."""
    return v2_script(
        list(credentials),
        token=[text(TOKEN), text(TOKEN)],
        role_list=[text(ROLE), text(ROLE)],
    )


async def test_imds_refresh_replaces_credentials(scenario: Scenario) -> None:
    # Expired credentials the extension skips are refreshed at freeze with
    # a second full round.
    first, _ = expiring("OLD", None)
    second, second_printed = expiring("NEW", 60 * 60)

    run = await scenario.run(refresh_script(first, second))

    assert_outcome(run, 0, imds_output("NEW", expiration=second_printed))
    assert requests_seen(run) == credential_round() * 2


async def test_imds_refresh_signs_listing_with_new_credentials(
    scenario: Scenario,
) -> None:
    first, _ = expiring("OLD", None)
    second, _ = expiring("NEW", 60 * 60)

    run = await scenario.list(refresh_script(first, second))

    assert_listed(run, credential_round() * 2, "NEW")


def env_credentials(scenario: Scenario) -> bytes:
    scenario.env.update(
        AWS_ACCESS_KEY_ID="AKIDENV", AWS_SECRET_ACCESS_KEY="ENV-secret"
    )
    return export_credentials_output("AKIDENV", "ENV-secret")


@pytest.mark.parametrize(
    "placement",
    [text(IMDS_REGION), text("nf", 404)],
    ids=["region", "placement-404"],
)
async def test_imds_region_lookup_without_region_precedes_imds_credentials(
    scenario: Scenario, placement: HTTPResponse
) -> None:
    scenario.without_region()

    run = await scenario.run(
        v2_script(token=[text(TOKEN)] * 2, placement=[placement])
    )

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == [*region_round(), *credential_round()]


async def test_imds_region_lookup_without_region_precedes_env_credentials(
    scenario: Scenario,
) -> None:
    scenario.without_region()
    stdout = env_credentials(scenario)

    run = await scenario.run(v2_script(placement=[text(IMDS_REGION)]))

    assert_outcome(run, 0, stdout)
    assert requests_seen(run) == region_round()


async def test_imds_region_lookup_token_400_leaves_region_unset(
    scenario: Scenario,
) -> None:
    scenario.without_region()

    run = await scenario.run(v2_script(token=[text("bad request", 400)] * 2))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(NO_CREDENTIALS))
    assert requests_seen(run) == [token_put(), token_put()]


@pytest.mark.parametrize("source", ["profile", "flag"])
async def test_imds_configured_region_skips_region_lookup(
    scenario: Scenario, source: str
) -> None:
    scenario.without_region()
    globals_: list[str] = []
    if source == "profile":
        scenario.sandbox.config.write_text("[default]\nregion = eu-west-1\n")
    else:
        globals_ = ["--region", "eu-west-1"]

    run = await scenario.run(v2_script(), globals_=globals_)

    assert_outcome(run, 0, imds_output())
    assert requests_seen(run) == credential_round()


async def test_imds_disabled_skips_region_lookup(scenario: Scenario) -> None:
    scenario.without_region()
    scenario.env["AWS_EC2_METADATA_DISABLED"] = "true"
    stdout = env_credentials(scenario)

    run = await scenario.run(v2_script(placement=[text(IMDS_REGION)]))

    assert_outcome(run, 0, stdout)
    assert run.requests == ()


async def test_imds_region_lookup_v1_disabled_error_precedes_credentials(
    scenario: Scenario,
) -> None:
    # Upstream bug, matched for parity: with no region configured the
    # CLI's IMDS region lookup runs first and its v1-disabled error is not
    # caught, so the command fails although env credentials are set
    # (awscli/utils.py:96-209).
    scenario.without_region()
    scenario.env["AWS_EC2_METADATA_V1_DISABLED"] = "true"
    env_credentials(scenario)

    run = await scenario.run(
        v2_script(token=[text("nf", 404)], placement=[text(IMDS_REGION)])
    )

    assert_outcome(run, FREEZE_ERROR_RC, stderr=freeze_error(V1_DISABLED_TEXT))
    assert requests_seen(run) == [token_put()]


def assert_signed_by_imds(run: CliRun) -> None:
    """The one STS call was SigV4-signed with the IMDS credentials."""
    sts = [r for r in run.raw_requests if r.headers.get("host") == STS_HOST]
    assert len(sts) == 1, run.describe()
    assert sts[0].headers.get("x-amz-security-token") == "IMDS-token"
    assert_signature(sts[0], "AKIDIMDS", "IMDS-secret")


async def test_imds_region_lookup_signs_sts_in_imds_region(
    scenario: Scenario,
) -> None:
    # The assume-role STS client takes its region from the IMDS region,
    # which the CLI reads as given; how often it is looked up is the CLI's
    # business.
    scenario.without_region()
    scenario.sandbox.config.write_text(
        "[default]\n"
        f"role_arn = {ROLE_ARN}\n"
        "credential_source = Ec2InstanceMetadata\n"
        f"role_session_name = {SESSION_NAME}\n"
    )
    region = text(IMDS_REGION)
    sts_route = ("POST", STS_HOST, "/")

    run = await scenario.run(
        v2_script(token=[text(TOKEN)] * 4, placement=[region] * 3),
        scripts={scenario.server: {sts_route: [sts_success_xml()]}},
    )

    stdout = export_credentials_output(
        "AKIDROLE", "ROLE-secret", "ROLE-token", FUTURE_EXPIRATION
    )
    key = role_cache_key(
        {"RoleArn": ROLE_ARN, "RoleSessionName": SESSION_NAME}
    )
    assert_outcome(
        run,
        0,
        stdout,
        changes={
            **created_cache_directories(),
            f"{CLI_CACHE_DIR}/{key}.json": (CACHE_FILE_MODE, ROLE_CACHE_ENTRY),
        },
    )
    imds_run = dataclasses.replace(
        run,
        requests=tuple(r for r in run.requests if r.host != STS_HOST),
    )
    region_lookup = region_round()
    seen = requests_seen(imds_run)
    assert region_lookup[1] in seen, run.describe()
    assert [
        request for request in seen if request not in region_lookup
    ] == credential_round()[1:], run.describe()
    sts = [r for r in run.requests if r.host == STS_HOST]
    assert [(r.method, r.target) for r in sts] == [("POST", "/")]
    assert sts[0].body == {
        "Action": ["AssumeRole"],
        "Version": ["2011-06-15"],
        "RoleArn": [ROLE_ARN],
        "RoleSessionName": [SESSION_NAME],
    }
    assert dict(sts[0].headers) == {
        **dict.fromkeys(COMPARED_HEADERS),
        "x-amz-security-token": "IMDS-token",
        "authorization": "AWS4-HMAC-SHA256",
        "x-amz-date": AMZ_DATE_PLACEHOLDER,
        "content-type": STS_CONTENT_TYPE,
    }
    assert sts[0].signing_scope == (
        "AKIDIMDS",
        SCOPE_DATE_PLACEHOLDER,
        IMDS_REGION,
        "sts",
    )
    assert_signed_by_imds(run)


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


IMDS_TOKEN = HTTPResponse.text("imds-token")
IMDS_ROLE = HTTPResponse.text("test-role")
IMDS_CREDENTIALS = HTTPResponse.json(metadata_credentials("IMDS"))
IMDS_PAYLOAD_WITHOUT_TOKEN = {
    key: value
    for key, value in metadata_credentials("IMDS").items()
    if key != "Token"
}
PROCESS_PAYLOAD_WITHOUT_SECRET = {
    key: value
    for key, value in process_credentials().items()
    if key != "SecretAccessKey"
}


def serve_imds(
    metadata: AsyncHTTPTestServer, responses: list[HTTPResponse]
) -> None:
    metadata.set_default_response(
        HTTPResponse.text("unexpected request", status=400)
    )
    metadata.set_response_sequence(responses)


def serve_imds_credentials(metadata: AsyncHTTPTestServer) -> None:
    serve_imds(metadata, [IMDS_TOKEN, IMDS_ROLE, IMDS_CREDENTIALS])


async def list_bucket_with_imds(
    aws_cli: str, tmp_path: Path, responses: list[HTTPResponse]
) -> tuple[tuple[bytes, bytes, int], AsyncHTTPTestServer, AsyncHTTPTestServer]:
    async with mock_server() as (s3, proxy), AsyncHTTPTestServer() as metadata:
        serve_imds(metadata, responses)
        env = credential_env(proxy, tmp_path)
        env["AWS_EC2_METADATA_DISABLED"] = "false"
        env["HTTP_PROXY"] = metadata.url
        # HTTPS S3 still goes through its own local TLS intercept proxy.
        result = await list_bucket(aws_cli, s3, env)
    return result, s3, metadata


def assert_imds_requests(
    metadata: AsyncHTTPTestServer, count: int, session_token: str | None
) -> None:
    assert len(metadata.requests) == count
    first = metadata.requests[0]
    assert first.method == "PUT"
    assert urlsplit(first.effective_path).path == "/latest/api/token"
    assert first.headers["x-aws-ec2-metadata-token-ttl-seconds"] == "21600"
    for request in metadata.requests[1:]:
        assert request.method == "GET"
        token = request.headers.get("x-aws-ec2-metadata-token")
        assert token == session_token


# Intercept the default IMDS HTTP endpoint through a loopback proxy: no
# endpoint override and no link-local connection.
# Derived from botocore's TestIMDSFetcher/TestInstanceMetadataFetcher.
@pytest.mark.parametrize(
    "token,credentials,session_token",
    [
        pytest.param(IMDS_TOKEN, IMDS_CREDENTIALS, "imds-token", id="v2"),
        *(
            pytest.param(
                HTTPResponse.text("unsupported", status=status),
                IMDS_CREDENTIALS,
                None,
                id=f"v1-{status}",
            )
            for status in (403, 404, 405)
        ),
        pytest.param(
            HTTPResponse.text(""), IMDS_CREDENTIALS, "", id="empty-token"
        ),
        pytest.param(
            IMDS_TOKEN,
            HTTPResponse.json(
                {
                    **metadata_credentials("IMDS"),
                    "Expiration": "2000-01-01T00:00:00Z",
                }
            ),
            "imds-token",
            id="expired",
        ),
    ],
)
async def test_imds_credentials_token_exchange_signs_with_instance_role(
    aws_cli: str,
    tmp_path: Path,
    token: HTTPResponse,
    credentials: HTTPResponse,
    session_token: str | None,
) -> None:
    result, s3, metadata = await list_bucket_with_imds(
        aws_cli, tmp_path, [token, IMDS_ROLE, credentials]
    )
    assert_signed_by(result, s3, "IMDS", "IMDS-token")
    assert_imds_requests(metadata, 3, session_token)


@pytest.mark.parametrize(
    "responses,request_count",
    [
        pytest.param(
            [
                HTTPResponse.text("bad request", status=400),
                IMDS_ROLE,
                IMDS_CREDENTIALS,
            ],
            1,
            id="token-400",
        ),
        pytest.param(
            [
                IMDS_TOKEN,
                IMDS_ROLE,
                HTTPResponse.json(IMDS_PAYLOAD_WITHOUT_TOKEN),
            ],
            3,
            id="missing-token",
        ),
        pytest.param(
            [
                IMDS_TOKEN,
                IMDS_ROLE,
                HTTPResponse.json(
                    {
                        "Code": "AssumeRoleUnauthorizedAccess",
                        "Message": "denied",
                    }
                ),
            ],
            3,
            id="service-error",
        ),
        pytest.param(
            [IMDS_TOKEN, HTTPResponse.text(""), IMDS_CREDENTIALS],
            2,
            id="role-empty",
        ),
        pytest.param(
            [
                IMDS_TOKEN,
                HTTPResponse.text("retry later", status=429),
                IMDS_CREDENTIALS,
            ],
            2,
            id="role-error",
        ),
        pytest.param(
            [IMDS_TOKEN, IMDS_ROLE, HTTPResponse.text("not json")],
            3,
            id="credentials-invalid-json",
        ),
    ],
)
async def test_imds_credentials_bad_exchange_fails_before_request(
    aws_cli: str,
    tmp_path: Path,
    responses: list[HTTPResponse],
    request_count: int,
) -> None:
    result, s3, metadata = await list_bucket_with_imds(
        aws_cli, tmp_path, responses
    )
    assert_credential_error(result, s3)
    assert_imds_requests(metadata, request_count, "imds-token")


@pytest.mark.parametrize("disabled", ["true", "TrUe"])
async def test_imds_credentials_disabled_skips_imds(
    aws_cli: str, tmp_path: Path, disabled: str
) -> None:
    async with mock_server() as (s3, proxy), AsyncHTTPTestServer() as metadata:
        env = credential_env(proxy, tmp_path)
        env["AWS_EC2_METADATA_DISABLED"] = disabled
        env["HTTP_PROXY"] = metadata.url
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert not metadata.requests


# A profile that supplies credentials ends the chain: when its
# credential_process fails, botocore reports the error instead of signing as
# the instance role.
@pytest.mark.parametrize(
    "source",
    [
        "print('credential helper failed')\nsys.exit(1)\n",
        "print('not json')\n",
        f"print({json.dumps(PROCESS_PAYLOAD_WITHOUT_SECRET)!r})\n",
    ],
    ids=["nonzero-exit", "invalid-json", "missing-secret"],
)
async def test_imds_credentials_not_used_after_credential_process_fails(
    aws_cli: str, tmp_path: Path, source: str
) -> None:
    command, log = credential_process(tmp_path, source)
    async with mock_server() as (s3, proxy), AsyncHTTPTestServer() as metadata:
        serve_imds_credentials(metadata)
        env = credential_env(proxy, tmp_path)
        env["AWS_EC2_METADATA_DISABLED"] = "false"
        env["HTTP_PROXY"] = metadata.url
        write_config(env, f"[default]\ncredential_process = {command}\n")
        result = await list_bucket(aws_cli, s3, env)
    assert log.exists()
    assert_credential_error(result, s3)
    assert not metadata.requests


# botocore treats an empty aws_secret_access_key as present and signs with the
# profile's keys; it never reaches the instance role.
@pytest.mark.parametrize("shared", [True, False], ids=["shared", "config"])
async def test_imds_credentials_not_used_after_empty_profile_secret(
    aws_cli: str, tmp_path: Path, shared: bool
) -> None:
    async with mock_server() as (s3, proxy), AsyncHTTPTestServer() as metadata:
        serve_imds_credentials(metadata)
        env = credential_env(proxy, tmp_path)
        env["AWS_EC2_METADATA_DISABLED"] = "false"
        env["HTTP_PROXY"] = metadata.url
        write_config(
            env,
            "[default]\naws_access_key_id = AKIDEMPTY\n"
            "aws_secret_access_key =\n",
            shared=shared,
        )
        stdout, stderr, rc = await list_bucket(aws_cli, s3, env)
    assert rc == 0, f"stdout={stdout!r}, stderr={stderr!r}, rc={rc}"
    assert not metadata.requests
    assert len(s3.requests) == 1
    assert_signature(s3.requests[0], "AKIDEMPTY", "")
