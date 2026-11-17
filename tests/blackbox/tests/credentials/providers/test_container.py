import itertools
import socket
import time
from collections.abc import AsyncIterator, Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    CloseConnection,
    HTTPResponse,
    ResponderContext,
    ResponseSpec,
)

from credhelpers import (
    COMPARED_HEADERS,
    BytesStartingWith,
    CliRun,
    FileChanges,
    Handler,
    HandlerFactory,
    Sandbox,
    Stub,
    assert_credential_error,
    assert_signed_by,
    assert_signed_with,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    is_s3_request,
    json_process,
    list_bucket,
    metadata_credentials,
    os_error_path,
    process_credentials,
    run_aws,
    run_export_credentials,
    run_s3_ls,
    unexpected_request,
    without_s3,
    write_config,
)
from tests.blackbox.utils import put_object_response

pytestmark = pytest.mark.asyncio

# botocore ContainerProvider (credentials.py:2075-2156) and
# ContainerMetadataFetcher (utils.py:2904-3023) through `aws configure
# export-credentials`. The fetcher sends no request through a proxy
# (httpsession.py:220-243 with proxies=None), so every test points
# HTTP_PROXY at a tripwire server whose requests would be visible;
# HTTPS_PROXY stays at the TLS intercept proxy, whose stub records any
# https request that took it.
RELATIVE_URI: Final = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
FULL_URI: Final = "AWS_CONTAINER_CREDENTIALS_FULL_URI"
AUTH_TOKEN: Final = "AWS_CONTAINER_AUTHORIZATION_TOKEN"
AUTH_TOKEN_FILE: Final = "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"
CREDENTIALS_PATH: Final = "/creds"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
PAST_EXPIRATION: Final = "2000-01-01T00:00:00Z"
ACCEPT_JSON: Final = "application/json"
# Every compared header a container request leaves out: the fetcher sends
# only Accept and an optional Authorization, and no body
# (utils.py:2974-2977, 2996-2999; credentials.py:2102-2129).
UNSENT_HEADERS: Final = tuple(
    name for name in COMPARED_HEADERS if name != "authorization"
)
# exportcreds.py:266-279 wraps load errors; a refresh at freeze time is
# outside that try and prints the bare message (errorhandler.py:391-399).
LOAD_ERROR_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
LOAD_ERROR_RC: Final = 253
FREEZE_ERROR_RC: Final = 255
# utils.py:2936-2960, with the two spaces after the period.
ALLOWED_HOSTS_TEXT: Final = (
    "Can only retrieve metadata from a loopback address or one of these "
    "hosts: 169.254.170.2, 169.254.170.23, fd00:ec2::23, localhost"
)
# credentials.py:2131-2140 wraps MetadataRetrievalError (exceptions.py:
# 704-705) in CredentialRetrievalError (exceptions.py:188-198).
RETRIEVAL_PREFIX: Final = (
    "Error when retrieving credentials from container-role: "
    "Error retrieving metadata: "
)
TRANSPORT_PREFIX: Final = (
    RETRIEVAL_PREFIX
    + "Received error when attempting to retrieve container metadata: "
)
INVALID_JSON_TEXT: Final = (
    RETRIEVAL_PREFIX
    + "Unable to parse JSON returned from container metadata services"
)
INVALID_TOKEN_TEXT: Final = "Auth token value is not a legal header value"
STILL_EXPIRED_TEXT: Final = (
    "Credentials were refreshed, but the refreshed credentials are still "
    "expired."
)
# The refresh windows of credentials.py:77-78 are 900 s (advisory) and
# 600 s (mandatory); each initial expiry keeps 60 s or more from both.
ADVISORY_SECONDS: Final = 12 * 60
MANDATORY_SECONDS: Final = 5 * 60
# Three attempts with a 1 s sleep after every failure (utils.py:2905-2907,
# :2974-2994). Upstream also sleeps after the last one; the timing rows
# assert only the sleeps between attempts, with 0.1 s of clock and
# scheduling slack below each.
ATTEMPTS: Final = 3
MIN_SLEEP_SECONDS: Final = 0.9

# tcpmux: below every ephemeral range bind(0) draws from (49152-65535 on
# macOS and Windows, 32768-60999 on Linux), and nothing in the suite binds
# a fixed port, so no test server is handed it during the run. Any user
# may still bind it (macOS allows 0.0.0.0:1 without root, as does Linux
# with ip_unprivileged_port_start=0), so `require_refusal` checks that it
# refuses before a test uses it. (A bound socket that never listens is no
# substitute: macOS drops the SYN and the client sees a connect timeout
# instead.)
REFUSED_PORT: Final = 1
REFUSAL_CHECK_SECONDS: Final = 1.0

# The fetcher's connect and read timeout is 2 s (utils.py:2905). A stalled
# response stays silent for twice that before the stub closes the
# connection, so a client that times out on schedule never sees the close
# instead, even on a loaded machine.
STALL_SECONDS: Final = 4.0

ContainerRequest = tuple[str, str, str, str | None, str | None]


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


def bind_ipv6(host: str) -> None:
    """Bind a throwaway IPv6 TCP socket to `host` on any free port."""
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as listener:
        listener.bind((host, 0))


def require_ipv6_bind(host: str) -> str:
    """`host` once a TCP socket binds it over IPv6; skips otherwise.

    A machine with IPv6 disabled (Linux `ipv6.disable=1`, or
    `disable_ipv6` on `lo`) fails the `socket()` or the `bind()`, so a
    stub that listens on `host` would error the test instead of skipping
    it. urllib3 makes the same check on `::1` and resolves only IPv4
    addresses when it fails (util/connection.py:103-137).
    """
    try:
        bind_ipv6(host)
    except OSError as error:
        pytest.skip(f"cannot listen on {host}: {error}")
    return host


@pytest_asyncio.fixture
async def metadata() -> AsyncIterator[AsyncHTTPTestServer]:
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(unexpected_request())
        yield server


@pytest_asyncio.fixture
async def metadata_ipv6() -> AsyncIterator[AsyncHTTPTestServer]:
    """A metadata stub on the IPv6 loopback address `::1`."""
    async with AsyncHTTPTestServer(host=require_ipv6_bind("::1")) as server:
        server.set_default_response(unexpected_request())
        yield server


@pytest_asyncio.fixture
async def tripwire() -> AsyncIterator[AsyncHTTPTestServer]:
    """HTTP_PROXY for every test: the container fetcher must ignore it."""
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(unexpected_request())
        yield server


class Scenario:
    """One container test's servers and environment, and its one run."""

    def __init__(
        self,
        aws_cli: str,
        sandbox: Sandbox,
        stub: Stub,
        metadata: AsyncHTTPTestServer,
        tripwire: AsyncHTTPTestServer,
    ) -> None:
        self.aws_cli = aws_cli
        self.sandbox = sandbox
        self.server, proxy = stub
        self.metadata = metadata
        self.tripwire = tripwire
        self.env = sandbox.env(proxy)
        self.env["HTTP_PROXY"] = tripwire.url

    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.metadata.port}"

    def url(self, path: str = CREDENTIALS_PATH) -> str:
        return f"http://{self.host}{path}"

    async def run(
        self,
        handler: HandlerFactory,
        *,
        globals_: Sequence[str] = (),
        endpoint: AsyncHTTPTestServer | None = None,
    ) -> CliRun:
        """Run export-credentials once with a fresh handler.

        `handler` serves `endpoint`, a metadata stub other than the
        scenario's (default: the scenario's own). The tripwire and the
        STS stub are recorded too, so a request that took a proxy shows
        up in the run.
        """
        servers = [self.metadata, self.tripwire, self.server]
        if endpoint is None:
            endpoint = self.metadata
        else:
            servers.append(endpoint)
        return await run_export_credentials(
            self.aws_cli,
            self.sandbox,
            servers,
            self.env,
            globals_=globals_,
            handlers={endpoint: handler},
        )

    async def list(
        self,
        handler: HandlerFactory,
        *,
        globals_: Sequence[str] = (),
        endpoint: AsyncHTTPTestServer | None = None,
    ) -> CliRun:
        """Run `s3 ls` once with a fresh handler, as `run` does.

        The STS stub answers the S3 listing; the rest is as in `run`.
        """
        servers = [self.metadata, self.tripwire, self.server]
        if endpoint is None:
            endpoint = self.metadata
        else:
            servers.append(endpoint)
        return await run_s3_ls(
            self.aws_cli,
            self.sandbox,
            servers,
            self.env,
            s3=self.server,
            globals_=globals_,
            handlers={endpoint: handler},
        )


@pytest.fixture
def scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    metadata: AsyncHTTPTestServer,
    tripwire: AsyncHTTPTestServer,
) -> Scenario:
    return Scenario(aws_cli, sandbox, stub, metadata, tripwire)


def assert_outcome(
    run: CliRun,
    returncode: int,
    stdout: bytes = b"",
    stderr: bytes | BytesStartingWith = b"",
    *,
    changes: FileChanges | None = None,
) -> None:
    """The run's exit status, output, and file changes.

    Container credentials are never cached, so a run changes no file
    unless `changes` says otherwise.
    """
    assert (run.returncode, run.stdout, run.stderr, run.changes) == (
        returncode,
        stdout,
        stderr,
        changes or {},
    ), run.describe()


def serve(*responses: ResponseSpec) -> HandlerFactory:
    """A handler factory serving `responses` in order, then a 400."""

    def factory() -> Handler:
        queue = list(responses)

        def handler(context: ResponderContext) -> ResponseSpec:
            return queue.pop(0) if queue else unexpected_request()

        return handler

    return factory


class ArrivalLog:
    """A handler factory that also timestamps the run's requests.

    The run installs its handler just before the command starts, so the
    run lasts from `start` to no later than the moment of the check.
    """

    def __init__(self, inner: HandlerFactory) -> None:
        self.inner = inner
        self.start = 0.0
        self.arrivals: list[float] = []

    def __call__(self) -> Handler:
        handler = self.inner()
        self.start = time.monotonic()
        self.arrivals = []

        def timed(context: ResponderContext) -> ResponseSpec:
            self.arrivals.append(time.monotonic())
            return handler(context)

        return timed

    def assert_sleeps(self, run: CliRun) -> None:
        """The run slept between its ATTEMPTS failed attempts.

        Its last ATTEMPTS requests (the failed ones) are MIN_SLEEP_SECONDS
        or more apart, and the run lasted ATTEMPTS - 1 such sleeps or
        more, which also covers attempts that never reached the stub.
        """
        end = time.monotonic()
        failed = self.arrivals[-ATTEMPTS:]
        gaps = [
            round(later - earlier, 3)
            for earlier, later in itertools.pairwise(failed)
        ]
        lasted = end - self.start
        slept = all(gap >= MIN_SLEEP_SECONDS for gap in gaps)
        assert slept and lasted >= (ATTEMPTS - 1) * MIN_SLEEP_SECONDS, (
            f"run lasted {lasted:.3f} s; gaps between its failed attempts: "
            f"{gaps}\n{run.describe()}"
        )


def credentials_response(
    identity: str = "CONTAINER", **overrides: object
) -> HTTPResponse:
    """A metadata credentials body with `overrides` replacing its fields."""
    payload = {**metadata_credentials(identity), **overrides}
    return HTTPResponse.json(payload)


def expiring(identity: str, seconds: int) -> tuple[HTTPResponse, str]:
    """Credentials expiring `seconds` from now, and their export text."""
    moment = datetime.now(UTC).replace(microsecond=0) + timedelta(
        seconds=seconds
    )
    response = credentials_response(
        identity, Expiration=moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    return response, moment.isoformat()


def container_output(identity: str = "CONTAINER") -> bytes:
    return export_credentials_output(
        f"AKID{identity}",
        f"{identity}-secret",
        f"{identity}-token",
        FUTURE_EXPIRATION,
    )


def load_error(message: str) -> bytes:
    return f"{LOAD_ERROR_PREFIX}{message}\n".encode()


def freeze_error(message: str) -> bytes:
    return f"\naws: [ERROR]: {message}\n".encode()


def requests_seen(run: CliRun) -> list[ContainerRequest]:
    """(method, Host, target, Authorization, Accept) of every request.

    Also checks the rest of every request: no body and none of the other
    compared headers (no SigV4 signature, X-Amz-Date, security token, or
    Content-Type).
    """
    seen = []
    for request, raw in zip(run.requests, run.raw_requests, strict=True):
        headers = dict(request.headers)
        assert all(headers[name] is None for name in UNSENT_HEADERS), (
            run.describe()
        )
        assert request.body_bytes == b"", run.describe()
        seen.append(
            (
                request.method,
                request.host,
                request.target,
                headers["authorization"],
                raw.headers.get("accept"),
            )
        )
    return seen


def credential_gets(
    scenario: Scenario,
    count: int = 1,
    *,
    target: str = CREDENTIALS_PATH,
    authorization: str | None = None,
) -> list[ContainerRequest]:
    request = ("GET", scenario.host, target, authorization, ACCEPT_JSON)
    return [request] * count


def assert_listed(
    run: CliRun,
    gets: list[ContainerRequest],
    identity: str = "CONTAINER",
    token: str | None = "",
) -> None:
    """The listing carries `identity`'s key and token, and the provider's
    own requests are `gets`. `token` "" means `<identity>-token`."""
    assert_signed_with(
        run, f"AKID{identity}", f"{identity}-token" if token == "" else token
    )
    assert requests_seen(without_s3(run)) == gets


@pytest.mark.parametrize(
    ("env_token", "file_token", "authorization"),
    [
        (None, None, None),
        ("Basic ENV", None, "Basic ENV"),
        ("Basic ENV", "Basic FILE", "Basic FILE"),
        ("Basic ENV", "", ""),
    ],
    ids=["none", "env", "file-over-env", "empty-file-over-env"],
)
async def test_container_full_uri_sends_authorization_from_token_source(
    scenario: Scenario,
    env_token: str | None,
    file_token: str | None,
    authorization: str | None,
) -> None:
    scenario.env[FULL_URI] = scenario.url("/creds?task=123")
    if env_token is not None:
        scenario.env[AUTH_TOKEN] = env_token
    if file_token is not None:
        token_file = scenario.sandbox.write("auth-token", file_token)
        scenario.env[AUTH_TOKEN_FILE] = str(token_file)

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == credential_gets(
        scenario, target="/creds?task=123", authorization=authorization
    )


@pytest.mark.parametrize(
    ("env_token", "file_token", "authorization"),
    [
        (None, None, None),
        ("Basic ENV", None, "Basic ENV"),
        ("Basic ENV", "Basic FILE", "Basic FILE"),
        ("Basic ENV", "", ""),
    ],
    ids=["none", "env", "file-over-env", "empty-file-over-env"],
)
async def test_container_full_uri_signs_listing_with_token_source(
    scenario: Scenario,
    env_token: str | None,
    file_token: str | None,
    authorization: str | None,
) -> None:
    scenario.env[FULL_URI] = scenario.url("/creds?task=123")
    if env_token is not None:
        scenario.env[AUTH_TOKEN] = env_token
    if file_token is not None:
        token_file = scenario.sandbox.write("auth-token", file_token)
        scenario.env[AUTH_TOKEN_FILE] = str(token_file)

    run = await scenario.list(serve(credentials_response()))

    assert_listed(
        run,
        credential_gets(
            scenario, target="/creds?task=123", authorization=authorization
        ),
    )


@pytest.mark.parametrize(
    ("env_token", "file_token"),
    [
        ("invalid\r\ntoken", None),
        # A token file written with `echo`.
        ("valid-env-token", "Bearer FILE\n"),
    ],
    ids=["env-crlf", "file-trailing-lf"],
)
async def test_container_token_with_line_break_fails_before_request(
    scenario: Scenario, env_token: str, file_token: str | None
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    scenario.env[AUTH_TOKEN] = env_token
    if file_token is not None:
        token_file = scenario.sandbox.write("auth-token", file_token)
        scenario.env[AUTH_TOKEN_FILE] = str(token_file)

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(INVALID_TOKEN_TEXT))
    assert run.requests == ()


async def test_container_missing_token_file_fails_before_request(
    scenario: Scenario,
) -> None:
    # The file is read even with an env token set, and the OSError after
    # the prefix is CPython's and the C library's wording.
    scenario.env[FULL_URI] = scenario.url()
    scenario.env[AUTH_TOKEN] = "valid-env-token"
    token_path = str(scenario.sandbox.root / "auth-token")
    scenario.env[AUTH_TOKEN_FILE] = token_path

    run = await scenario.run(serve(credentials_response()))

    stderr = BytesStartingWith(
        LOAD_ERROR_PREFIX.encode(), (os_error_path(token_path),)
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert run.requests == ()


def unsupported_host(hostname: str) -> bytes:
    return load_error(f"Unsupported host '{hostname}'.  {ALLOWED_HOSTS_TEXT}")


@pytest.mark.parametrize(
    ("uri", "stderr"),
    [
        pytest.param(
            "http://169.254.0.1/foo",
            unsupported_host("169.254.0.1"),
            id="link-local",
        ),
        pytest.param(
            "http://somewhere.invalid/foo",
            unsupported_host("somewhere.invalid"),
            id="dns-name",
        ),
        pytest.param(
            "http://localhost./creds",
            unsupported_host("localhost."),
            id="trailing-dot",
        ),
        pytest.param(
            "http://0x7f000001/creds", unsupported_host("0x7f000001"), id="hex"
        ),
        # Set but empty still selects the provider; the quoted host is
        # Python's repr of None.
        pytest.param(
            "",
            BytesStartingWith(
                f"{LOAD_ERROR_PREFIX}Unsupported host ".encode(),
                (ALLOWED_HOSTS_TEXT.encode(),),
            ),
            id="empty",
        ),
    ],
)
async def test_container_url_outside_allowlist_is_rejected_before_request(
    scenario: Scenario, uri: str, stderr: bytes | BytesStartingWith
) -> None:
    scenario.env[FULL_URI] = uri

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert run.requests == ()


async def test_container_unsupported_scheme_is_raised_unwrapped(
    scenario: Scenario,
) -> None:
    # A loopback host passes the allowlist, then the HTTP client rejects
    # the scheme; the client's own wording follows botocore's prefix.
    scenario.env[FULL_URI] = "ftp://127.0.0.1:1/creds"

    run = await scenario.run(serve(credentials_response()))

    prefix = (
        f"{LOAD_ERROR_PREFIX}An HTTP Client raised an unhandled exception: "
    )
    stderr = BytesStartingWith(prefix.encode(), (b"ftp",))
    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert run.requests == ()


async def test_container_allowlist_folds_case_before_request(
    scenario: Scenario,
) -> None:
    port = scenario.metadata.port
    scenario.env[FULL_URI] = f"http://LOCALHOST:{port}/creds"

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == [
        ("GET", f"localhost:{port}", CREDENTIALS_PATH, None, ACCEPT_JSON)
    ]


async def test_container_allowlist_folds_case_when_signing_listing(
    scenario: Scenario,
) -> None:
    port = scenario.metadata.port
    scenario.env[FULL_URI] = f"http://LOCALHOST:{port}/creds"

    run = await scenario.list(serve(credentials_response()))

    assert_listed(
        run,
        [("GET", f"localhost:{port}", CREDENTIALS_PATH, None, ACCEPT_JSON)],
    )


async def test_container_profile_flag_keeps_container_environment(
    scenario: Scenario,
) -> None:
    scenario.sandbox.config.write_text("[profile empty]\nregion = us-east-1\n")
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(
        serve(credentials_response()), globals_=["--profile", "empty"]
    )

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == credential_gets(scenario)


async def test_container_profile_flag_signs_listing_from_container(
    scenario: Scenario,
) -> None:
    scenario.sandbox.config.write_text("[profile empty]\nregion = us-east-1\n")
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.list(
        serve(credentials_response()), globals_=["--profile", "empty"]
    )

    assert_listed(run, credential_gets(scenario))


async def test_container_relative_uri_with_userinfo_reaches_its_host(
    scenario: Scenario,
) -> None:
    scenario.env[RELATIVE_URI] = f"@{scenario.host}/rel?x=1"
    scenario.env[AUTH_TOKEN] = "Basic ENV"

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == credential_gets(
        scenario, target="/rel?x=1", authorization="Basic ENV"
    )


async def test_container_relative_uri_with_userinfo_signs_listing(
    scenario: Scenario,
) -> None:
    scenario.env[RELATIVE_URI] = f"@{scenario.host}/rel?x=1"
    scenario.env[AUTH_TOKEN] = "Basic ENV"

    run = await scenario.list(serve(credentials_response()))

    assert_listed(
        run,
        credential_gets(
            scenario, target="/rel?x=1", authorization="Basic ENV"
        ),
    )


async def test_container_relative_uri_with_userinfo_signs_upload(
    scenario: Scenario,
) -> None:
    # An ECS task's `s3 cp` of a local file: the PutObject is signed with
    # the container's credentials. AWS_MAX_ATTEMPTS is dropped as
    # `run_s3_ls` drops it, so native runs the upload.
    scenario.env[RELATIVE_URI] = f"@{scenario.host}/rel?x=1"
    scenario.env[AUTH_TOKEN] = "Basic ENV"
    source = scenario.sandbox.root / "upload.txt"
    source.write_bytes(b"foo")
    env = {k: v for k, v in scenario.env.items() if k != "AWS_MAX_ATTEMPTS"}

    def stored() -> Handler:
        def handler(context: ResponderContext) -> ResponseSpec:
            if is_s3_request(context.request):
                return put_object_response()
            return unexpected_request()

        return handler

    run = await run_aws(
        scenario.aws_cli,
        ["s3", "cp", str(source), "s3://credential-parity/key"],
        scenario.sandbox,
        [scenario.metadata, scenario.tripwire, scenario.server],
        env,
        handlers={
            scenario.metadata: serve(credentials_response()),
            scenario.server: stored,
        },
    )

    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    uploads = [request for request in run.requests if is_s3_request(request)]
    assert [request.method for request in uploads] == ["PUT"], run.describe()
    assert_listed(
        run,
        credential_gets(
            scenario, target="/rel?x=1", authorization="Basic ENV"
        ),
    )


async def test_container_relative_uri_with_userinfo_wins_over_full_uri(
    scenario: Scenario,
) -> None:
    scenario.env[RELATIVE_URI] = f"@{scenario.host}/relative"
    scenario.env[FULL_URI] = scenario.url("/full")

    run = await scenario.run(serve(credentials_response()))

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == credential_gets(scenario, target="/relative")


async def test_container_relative_uri_with_userinfo_signs_over_full_uri(
    scenario: Scenario,
) -> None:
    scenario.env[RELATIVE_URI] = f"@{scenario.host}/relative"
    scenario.env[FULL_URI] = scenario.url("/full")

    run = await scenario.list(serve(credentials_response()))

    assert_listed(run, credential_gets(scenario, target="/relative"))


@pytest.mark.slow
async def test_container_refused_connection_is_retried_and_wrapped(
    scenario: Scenario,
) -> None:
    url = f"http://127.0.0.1:{require_refusal(REFUSED_PORT)}/creds"
    scenario.env[FULL_URI] = url
    log = ArrivalLog(serve())

    run = await scenario.run(log)

    message = (
        f'{TRANSPORT_PREFIX}Could not connect to the endpoint URL: "{url}"'
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert run.requests == ()
    log.assert_sleeps(run)


@pytest.mark.slow
async def test_container_https_url_skips_allowlist(scenario: Scenario) -> None:
    # Any https URL skips the host check (utils.py:2936-2940). The host
    # never resolves (RFC 6761), so every attempt fails to connect, sleeps,
    # and is retried; the error names the URL as configured.
    uri = "https://somewhere.invalid/creds"
    scenario.env[FULL_URI] = uri
    log = ArrivalLog(serve())

    run = await scenario.run(log)

    message = (
        f'{TRANSPORT_PREFIX}Could not connect to the endpoint URL: "{uri}"'
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert run.requests == ()
    log.assert_sleeps(run)


@pytest.mark.slow
async def test_container_transport_error_is_retried_and_wrapped(
    scenario: Scenario,
) -> None:
    # ConnectionClosedError (a close without a response) and
    # ReadTimeoutError are RETRYABLE_HTTP_ERRORS members, wrapped and
    # retried (utils.py:2974-2994, :3015-3020); the last attempt's error
    # names the URL as configured.
    scenario.env[FULL_URI] = scenario.url()
    log = ArrivalLog(serve(dropped(), dropped(), stalled()))

    run = await scenario.run(log)

    message = (
        f'{TRANSPORT_PREFIX}Read timeout on endpoint URL: "{scenario.url()}"'
    )
    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert requests_seen(run) == credential_gets(scenario, ATTEMPTS)
    log.assert_sleeps(run)


async def test_container_ipv6_loopback_passes_allowlist(
    scenario: Scenario, metadata_ipv6: AsyncHTTPTestServer
) -> None:
    # Any loopback address passes, IPv6 too (utils.py:2936-2960).
    host = f"[::1]:{metadata_ipv6.port}"
    scenario.env[FULL_URI] = f"http://{host}{CREDENTIALS_PATH}"

    run = await scenario.run(
        serve(credentials_response()), endpoint=metadata_ipv6
    )

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == [
        ("GET", host, CREDENTIALS_PATH, None, ACCEPT_JSON)
    ]


async def test_container_ipv6_loopback_signs_listing(
    scenario: Scenario, metadata_ipv6: AsyncHTTPTestServer
) -> None:
    host = f"[::1]:{metadata_ipv6.port}"
    scenario.env[FULL_URI] = f"http://{host}{CREDENTIALS_PATH}"

    run = await scenario.list(
        serve(credentials_response()), endpoint=metadata_ipv6
    )

    assert_listed(run, [("GET", host, CREDENTIALS_PATH, None, ACCEPT_JSON)])


def status(code: int, body: str = "") -> HTTPResponse:
    return HTTPResponse.text(body, status=code)


def non_200_text(code: int, body: str) -> str:
    return (
        f"{RETRIEVAL_PREFIX}Received non 200 response {code} from container "
        f"metadata: {body}"
    ).strip()


@pytest.mark.slow
@pytest.mark.parametrize(
    ("responses", "message"),
    [
        (
            [status(404, "not found body")] * ATTEMPTS,
            non_200_text(404, "not found body"),
        ),
        ([HTTPResponse.text("not json")] * ATTEMPTS, INVALID_JSON_TEXT),
    ],
    ids=["404", "invalid-json"],
)
async def test_container_failing_fetch_retries_three_times(
    scenario: Scenario, responses: list[HTTPResponse], message: str
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    log = ArrivalLog(serve(*responses))

    run = await scenario.run(log)

    assert_outcome(run, LOAD_ERROR_RC, stderr=load_error(message))
    assert requests_seen(run) == credential_gets(scenario, ATTEMPTS)
    log.assert_sleeps(run)


LATER_ATTEMPT_ROWS = [
    pytest.param(
        [
            HTTPResponse.text(
                "moved", status=302, headers={"Location": "/elsewhere"}
            )
        ],
        id="302-not-followed",
    ),
    pytest.param([status(201, "created")], id="201"),
]


@pytest.mark.parametrize(
    "responses",
    LATER_ATTEMPT_ROWS,
)
async def test_container_fetch_succeeds_on_a_later_attempt(
    scenario: Scenario, responses: list[HTTPResponse]
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(serve(*responses, credentials_response()))

    assert_outcome(run, 0, container_output())
    assert requests_seen(run) == credential_gets(scenario, len(responses) + 1)


@pytest.mark.parametrize("responses", LATER_ATTEMPT_ROWS)
async def test_container_fetch_on_a_later_attempt_signs_listing(
    scenario: Scenario, responses: list[HTTPResponse]
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.list(serve(*responses, credentials_response()))

    assert_listed(run, credential_gets(scenario, len(responses) + 1))


async def test_container_missing_token_member_fails_at_load(
    scenario: Scenario,
) -> None:
    # Token is required, though a null one is accepted. The message after
    # the prefix is a Python KeyError's repr of the member name.
    scenario.env[FULL_URI] = scenario.url()
    payload = dict(metadata_credentials())
    del payload["Token"]

    run = await scenario.run(serve(HTTPResponse.json(payload)))

    stderr = BytesStartingWith(LOAD_ERROR_PREFIX.encode(), (b"Token",))
    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert requests_seen(run) == credential_gets(scenario)


# Fields a metadata response may carry that the provider ignores.
EXTRA_FIELDS: Final = {
    "Code": "Success",
    "Type": "AWS-HMAC",
    "LastUpdated": "2026-01-01T00:00:00Z",
    "AccountId": "123456789012",
}


@pytest.mark.parametrize(
    ("overrides", "stdout"),
    [
        (
            {"Token": None},
            export_credentials_output(
                "AKIDCONTAINER", "CONTAINER-secret", None, FUTURE_EXPIRATION
            ),
        ),
        (
            EXTRA_FIELDS,
            container_output(),
        ),
    ],
    ids=["token-null", "extra-fields"],
)
async def test_container_credential_values_are_not_type_checked(
    scenario: Scenario, overrides: dict[str, object], stdout: bytes
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(serve(credentials_response(**overrides)))

    assert_outcome(run, 0, stdout)
    assert requests_seen(run) == credential_gets(scenario)


@pytest.mark.parametrize(
    ("overrides", "token"),
    [({"Token": None}, None), (EXTRA_FIELDS, "")],
    ids=["token-null", "extra-fields"],
)
async def test_container_credential_values_unchecked_sign_listing(
    scenario: Scenario, overrides: dict[str, object], token: str | None
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.list(serve(credentials_response(**overrides)))

    assert_listed(run, credential_gets(scenario), token=token)


async def test_container_expiration_parse_failure_is_raised(
    scenario: Scenario,
) -> None:
    # The parser's message after the prefix is dateutil's.
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(serve(credentials_response(Expiration="garbage")))

    stderr = BytesStartingWith(LOAD_ERROR_PREFIX.encode(), (b"garbage",))
    assert_outcome(run, LOAD_ERROR_RC, stderr=stderr)
    assert requests_seen(run) == credential_gets(scenario)


async def test_container_naive_expiration_fails_at_freeze(
    scenario: Scenario,
) -> None:
    # Upstream bug, matched for parity: an expiration without a UTC offset
    # loads, then the first expiry check subtracts an aware "now" from it
    # outside the load wrapper (credentials.py:518-520, 549), so the
    # command exits 255 with CPython's TypeError message.
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(
        serve(credentials_response(Expiration="2099-01-01T00:00:00"))
    )

    stderr = BytesStartingWith(b"\naws: [ERROR]: ")
    assert_outcome(run, FREEZE_ERROR_RC, stderr=stderr)
    assert requests_seen(run) == credential_gets(scenario)


def expired(identity: str = "OLD") -> HTTPResponse:
    return credentials_response(identity, Expiration=PAST_EXPIRATION)


@pytest.mark.parametrize(
    ("second", "returncode", "stdout", "stderr"),
    [
        (credentials_response("NEW"), 0, container_output("NEW"), b""),
        (
            expired("NEW"),
            FREEZE_ERROR_RC,
            b"",
            freeze_error(STILL_EXPIRED_TEXT),
        ),
    ],
    ids=["refreshed", "still-expired"],
)
async def test_container_expired_credentials_refresh_at_freeze(
    scenario: Scenario,
    second: HTTPResponse,
    returncode: int,
    stdout: bytes,
    stderr: bytes,
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.run(serve(expired(), second))

    assert_outcome(run, returncode, stdout, stderr)
    assert requests_seen(run) == credential_gets(scenario, 2)


async def test_container_expired_credentials_refresh_before_signing(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.list(serve(expired(), credentials_response("NEW")))

    assert_listed(run, credential_gets(scenario, 2), "NEW")


@pytest.mark.slow
async def test_container_advisory_refresh_failure_keeps_old_credentials(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    first, expiration = expiring("OLD", ADVISORY_SECONDS)
    log = ArrivalLog(serve(first, *[status(404, "nf")] * ATTEMPTS))

    run = await scenario.run(log)

    stdout = export_credentials_output(
        "AKIDOLD", "OLD-secret", "OLD-token", expiration
    )
    assert_outcome(run, 0, stdout)
    assert requests_seen(run) == credential_gets(scenario, 1 + ATTEMPTS)
    log.assert_sleeps(run)


@pytest.mark.slow
async def test_container_advisory_refresh_failure_signs_with_old_credentials(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    first, _ = expiring("OLD", ADVISORY_SECONDS)

    run = await scenario.list(serve(first, *[status(404, "nf")] * ATTEMPTS))

    assert_listed(run, credential_gets(scenario, 1 + ATTEMPTS), "OLD")


@pytest.mark.slow
async def test_container_mandatory_refresh_failure_raises(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    first, _ = expiring("OLD", MANDATORY_SECONDS)
    log = ArrivalLog(serve(first, *[status(404, "nf")] * ATTEMPTS))

    run = await scenario.run(log)

    assert_outcome(
        run, FREEZE_ERROR_RC, stderr=freeze_error(non_200_text(404, "nf"))
    )
    assert requests_seen(run) == credential_gets(scenario, 1 + ATTEMPTS)
    log.assert_sleeps(run)


async def test_container_refresh_in_advisory_window_returns_new_credentials(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    first, _ = expiring("OLD", ADVISORY_SECONDS)

    run = await scenario.run(serve(first, credentials_response("NEW")))

    assert_outcome(run, 0, container_output("NEW"))
    assert requests_seen(run) == credential_gets(scenario, 2)


async def test_container_refresh_in_advisory_window_signs_with_new_credentials(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    first, _ = expiring("OLD", ADVISORY_SECONDS)

    run = await scenario.list(serve(first, credentials_response("NEW")))

    assert_listed(run, credential_gets(scenario, 2), "NEW")


# A listing whose endpoint fails: botocore raises the provider's error as it
# creates the listing's client, before any S3 request, and the general
# handler prints it with status 255 (errorhandler.py:391-399).
LISTING_ERROR_RC: Final = 255


@pytest.mark.slow
async def test_container_failing_endpoint_fails_listing_after_three_attempts(
    scenario: Scenario,
) -> None:
    scenario.env[FULL_URI] = scenario.url()
    scenario.env[AUTH_TOKEN] = "Basic ENV"
    log = ArrivalLog(serve(*[status(404, "not found")] * ATTEMPTS))

    run = await scenario.list(log)

    assert_outcome(
        run,
        LISTING_ERROR_RC,
        stderr=freeze_error(non_200_text(404, "not found")),
    )
    assert requests_seen(run) == credential_gets(
        scenario, ATTEMPTS, authorization="Basic ENV"
    )
    log.assert_sleeps(run)


@pytest.mark.parametrize("field", ["AccessKeyId", "Token"])
async def test_container_answer_without_a_member_fails_listing(
    scenario: Scenario, field: str
) -> None:
    # A JSON answer that is not credentials fails on its first missing
    # member, untried again; the message is the KeyError's, the key's repr
    # (credentials.py:2145-2151).
    scenario.env[FULL_URI] = scenario.url()
    payload = dict(metadata_credentials())
    del payload[field]

    run = await scenario.list(serve(HTTPResponse.json(payload)))

    assert_outcome(run, LISTING_ERROR_RC, stderr=freeze_error(f"'{field}'"))
    assert requests_seen(run) == credential_gets(scenario)


# Every credential feature id botocore registers; the listing's client
# carries the answering provider's in its User-Agent `m/` list.
CREDENTIAL_FEATURES: Final = frozenset(
    "e g v w h i k n o p q r s t u x z 0 AC AD".split()
)


async def test_container_listing_user_agent_names_the_provider(
    scenario: Scenario,
) -> None:
    # The provider registers CREDENTIALS_HTTP (`z`) as it answers while
    # botocore creates the listing's client (credentials.py:2137,
    # session.py:916-937).
    scenario.env[FULL_URI] = scenario.url()

    run = await scenario.list(serve(credentials_response()))

    assert run.returncode == 0, run.describe()
    listings = [raw for raw in run.raw_requests if is_s3_request(raw)]
    features = [
        {
            feature
            for part in raw.headers["user-agent"].split()
            if part.startswith("m/")
            for feature in part[2:].split(",")
        }
        & CREDENTIAL_FEATURES
        for raw in listings
    ]
    assert features == [{"z"}], run.describe()


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


VALID_CREDENTIALS = HTTPResponse.json(metadata_credentials())
EXPIRED_CREDENTIALS = HTTPResponse.json(
    {**metadata_credentials("OLD"), "Expiration": "2000-01-01T00:00:00Z"}
)
NOT_FOUND = HTTPResponse.text("not found", status=404)
NOT_JSON = HTTPResponse.text("not json")

EarlierProvider = Callable[[Path, dict[str, str]], None]


def environment_keys(tmp_path: Path, env: dict[str, str]) -> None:
    env.update(
        AWS_ACCESS_KEY_ID="AKIDEARLIER", AWS_SECRET_ACCESS_KEY="EARLIER-secret"
    )


def environment_key_without_secret(
    tmp_path: Path, env: dict[str, str]
) -> None:
    env["AWS_ACCESS_KEY_ID"] = "AKIDEARLIER"


def shared_file_keys(tmp_path: Path, env: dict[str, str]) -> None:
    write_config(env, "[default]\n" + file_credentials("EARLIER"), shared=True)


def config_file_keys(tmp_path: Path, env: dict[str, str]) -> None:
    write_config(env, "[default]\n" + file_credentials("EARLIER"))


def write_earlier_process(
    tmp_path: Path, env: dict[str, str], *dropped: str
) -> None:
    payload = process_credentials("EARLIER")
    for field in dropped:
        del payload[field]
    command, _ = json_process(tmp_path, payload)
    write_config(env, f"[default]\ncredential_process = {command}\n")


def process_keys(tmp_path: Path, env: dict[str, str]) -> None:
    write_earlier_process(tmp_path, env, "SessionToken")


def process_without_secret(tmp_path: Path, env: dict[str, str]) -> None:
    write_earlier_process(tmp_path, env, "SessionToken", "SecretAccessKey")


# Botocore ContainerProvider and ContainerMetadataFetcher behavior, exercised
# over HTTP rather than mocking the fetcher. ECS must bypass the S3 proxy.
@pytest.mark.parametrize(
    "env_token,file_token,expected",
    [
        (None, None, None),
        ("Basic ENV", None, "Basic ENV"),
        (None, "Basic FILE", "Basic FILE"),
        ("Basic ENV", "Basic FILE", "Basic FILE"),
    ],
    ids=["none", "environment", "file", "file-over-env"],
)
async def test_container_credentials_authorization_sends_expected_header(
    aws_cli: str,
    tmp_path: Path,
    env_token: str | None,
    file_token: str | None,
    expected: str | None,
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(metadata_credentials())
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = (
            metadata.url + "credentials?task=123"
        )
        if env_token is not None:
            env["AWS_CONTAINER_AUTHORIZATION_TOKEN"] = env_token
        if file_token is not None:
            path = tmp_path / "auth-token"
            path.write_text(file_token)
            env["AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"] = str(path)
        result = await list_bucket(aws_cli, s3, env)
    assert_signed_by(result, s3, "CONTAINER", "CONTAINER-token")
    assert len(metadata.requests) == 1
    request = metadata.requests[0]
    assert request.method == "GET"
    assert request.effective_path == "/credentials?task=123"
    assert request.headers.get("authorization") == expected


@pytest.mark.parametrize(
    "provider",
    [
        pytest.param(environment_keys, id="environment"),
        pytest.param(shared_file_keys, id="shared"),
        pytest.param(config_file_keys, id="config"),
        pytest.param(process_keys, id="process"),
    ],
)
async def test_container_credentials_earlier_provider_signs_without_lookup(
    aws_cli: str, tmp_path: Path, provider: EarlierProvider
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(metadata_credentials())
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = (
            metadata.url + "credentials"
        )
        provider(tmp_path, env)
        result = await list_bucket(aws_cli, s3, env)
    assert_signed_by(result, s3, "EARLIER")
    assert not metadata.requests, "earlier provider must prevent ECS lookup"


@pytest.mark.parametrize(
    "provider",
    [
        pytest.param(environment_key_without_secret, id="partial-environment"),
        pytest.param(process_without_secret, id="failed-process"),
    ],
)
async def test_container_credentials_earlier_provider_failure_skips_lookup(
    aws_cli: str, tmp_path: Path, provider: EarlierProvider
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(metadata_credentials())
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = (
            metadata.url + "credentials"
        )
        provider(tmp_path, env)
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert not metadata.requests, "earlier provider must prevent ECS lookup"


@pytest.mark.parametrize(
    "contents", [None, "invalid-token\n"], ids=["missing-file", "file-newline"]
)
async def test_container_credentials_unusable_token_file_fails_before_lookup(
    aws_cli: str, tmp_path: Path, contents: str | None
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(metadata_credentials())
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        env["AWS_CONTAINER_AUTHORIZATION_TOKEN"] = "valid-env-token"
        path = tmp_path / "auth-token"
        if contents is not None:
            path.write_text(contents)
        env["AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"] = str(path)
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert not metadata.requests


async def test_container_credentials_env_token_newline_fails_before_lookup(
    aws_cli: str, tmp_path: Path
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(metadata_credentials())
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        env["AWS_CONTAINER_AUTHORIZATION_TOKEN"] = "invalid\r\ntoken"
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert not metadata.requests


@pytest.mark.parametrize(
    "field", ["AccessKeyId", "SecretAccessKey", "Token", "Expiration"]
)
async def test_container_credentials_missing_fields_fail_without_retry(
    aws_cli: str, tmp_path: Path, field: str
) -> None:
    payload = metadata_credentials()
    del payload[field]
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(payload)
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert len(metadata.requests) == 1


@pytest.mark.parametrize("token", [None, ""])
async def test_container_credentials_optional_token_value_signs_without_token(
    aws_cli: str, tmp_path: Path, token: str | None
) -> None:
    payload = {**metadata_credentials(), "Token": token}
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_json_response(payload)
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        result = await list_bucket(aws_cli, s3, env)
    assert_signed_by(result, s3, "CONTAINER")


@pytest.mark.parametrize(
    "responses,request_count",
    [
        ([NOT_FOUND, NOT_JSON, VALID_CREDENTIALS], 3),
        ([EXPIRED_CREDENTIALS, VALID_CREDENTIALS], 2),
    ],
    ids=["retry-success", "refresh"],
)
async def test_container_credentials_retry_or_refresh_signs_when_valid(
    aws_cli: str,
    tmp_path: Path,
    responses: list[HTTPResponse],
    request_count: int,
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_response_sequence(responses)
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        result = await list_bucket(aws_cli, s3, env)
    assert_signed_by(result, s3, "CONTAINER", "CONTAINER-token")
    assert len(metadata.requests) == request_count


@pytest.mark.parametrize(
    "response,request_count",
    [(NOT_FOUND, 3), (NOT_JSON, 3), (EXPIRED_CREDENTIALS, 2)],
    ids=["http-error", "invalid-json", "expired"],
)
async def test_container_credentials_persistent_bad_response_fails(
    aws_cli: str,
    tmp_path: Path,
    response: HTTPResponse,
    request_count: int,
) -> None:
    async with (
        credential_runtime(tmp_path) as (s3, env),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_default_response(response)
        env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = metadata.url
        result = await list_bucket(aws_cli, s3, env)
    assert_credential_error(result, s3)
    assert len(metadata.requests) == request_count
