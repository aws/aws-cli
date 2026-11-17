import asyncio
import base64
import contextlib
import functools
import socket
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Final, Self
from urllib.parse import quote_plus, urlsplit

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer, CloseConnection, HTTPResponse

from credhelpers import (
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    BytesStartingWith,
    CliRun,
    NormalizedRequest,
    RoleCacheContent,
    Sandbox,
    Stub,
    created_cache_directories,
    decode_body,
    export_credentials_output,
    normalize_request,
    role_cache_key,
    run_export_credentials,
    sts_success_xml,
    unexpected_request,
)
from tests.blackbox.utils import mock_server

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# How botocore's URLLib3Session (httpsession.py:453-517) reports transport
# failures of the STS client, and how it picks a route (proxy selection,
# httpsession.py:220-276; NO_PROXY, utils.py:3026-3051). Every case is an
# unsigned AssumeRoleWithWebIdentity call, and each test names its route:
# direct (a plain-HTTP endpoint with NO_PROXY), tunnel (the default https
# endpoint through HTTPS_PROXY), or forward (a plain-HTTP endpoint through
# HTTP_PROXY). A nonstandard status line, which localstub cannot
# produce, comes from FaultRelay. One attempt per case:
# retries of these failures are test_retries.py's, and a dropped
# connection is its dropped-connection-three-times row. Not covered: a
# CONNECT that never answers, TLS handshake timeouts, OpenSSL error texts,
# and a missing CA bundle behind an unreachable endpoint.
EnvChanges = Mapping[str, str | None]
# (method, Host, request-target, Content-Type media type, decoded body,
# compared headers, SigV4 scope) of one request.
RequestShape = tuple[
    str,
    str,
    str,
    str | None,
    object,
    dict[str, str | None],
    tuple[str, ...] | None,
]

LOOPBACK: Final = "127.0.0.1"
WEB_ACCOUNT: Final = "210987654321"
WEB_ROLE_ARN: Final = f"arn:aws:iam::{WEB_ACCOUNT}:role/w"
SESSION_NAME: Final = "sess"
WEB_TOKEN: Final = "synthetic-web-token"
ACTION: Final = "AssumeRoleWithWebIdentity"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_URL: Final = f"https://{STS_HOST}/"
# The CONNECT request-target and Host urllib3 sends for the tunnel.
STS_AUTHORITY: Final = f"{STS_HOST}:443"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
GENERAL_RC: Final = 255
CLIENT_ERROR_RC: Final = 254
TOKEN_FILE: Final = "web-identity-token"
CLI_CACHE_DIR: Final = f"home/{CLI_CACHE.as_posix()}"
CONFIG: Final = f"""\
[default]
role_arn = {WEB_ROLE_ARN}
web_identity_token_file = {{token}}
role_session_name = {SESSION_NAME}
"""
FORM_MEDIA_TYPE: Final = "application/x-www-form-urlencoded"
# credentials.py:793-815 and 1022-1027: the configured RoleSessionName,
# RoleArn, then the token.
WEB_BODY: Final = (
    f"Action={ACTION}&Version=2011-06-15&RoleSessionName={SESSION_NAME}"
    f"&RoleArn={quote_plus(WEB_ROLE_ARN)}&WebIdentityToken={WEB_TOKEN}"
).encode()
CACHE_ARGS: Final = {
    "RoleSessionName": SESSION_NAME,
    "RoleArn": WEB_ROLE_ARN,
    "WebIdentityToken": WEB_TOKEN,
}
# The response header FaultRelay acts on; clients never see it.
RELAY_FAULT: Final = "X-Relay-Fault"
RELAY_READ_BYTES: Final = 65536
HEAD_END: Final = b"\r\n\r\n"
# Longer than --cli-read-timeout 1, short enough to keep the case under
# 5 s.
STALL_SECONDS: Final = 3
READ_TIMEOUT_GLOBALS: Final = ("--cli-read-timeout", "1")
PROXY_AUTHORIZATION: Final = "proxy-authorization"
normalize_with_proxy_auth: Final = functools.partial(
    normalize_request,
    compared_headers=(*COMPARED_HEADERS, PROXY_AUTHORIZATION),
)


class FaultRelay:
    """A plain-HTTP relay in front of a localstub server, for a status
    line localstub cannot produce.

    Requests reach `upstream` byte for byte, so it records them as usual.
    A response carrying RELAY_FAULT `status <line>` reaches the client
    minus RELAY_FAULT, under `<line>`. `url` has localstub's
    AsyncHTTPTestServer form (an endpoint, trailing slash). Leaving the
    context closes the listener and cancels the connections still open.
    """

    def __init__(self, upstream: AsyncHTTPTestServer) -> None:
        port = urlsplit(upstream.url).port
        assert port is not None, upstream.url
        self._upstream_port = port
        self._server: asyncio.Server | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    async def __aenter__(self) -> Self:
        self._server = await asyncio.start_server(self._accept, LOOPBACK, 0)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        assert self._server is not None
        self._server.close()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._server.wait_closed()

    @property
    def url(self) -> str:
        assert self._server is not None
        port = self._server.sockets[0].getsockname()[1]
        return f"http://{LOOPBACK}:{port}/"

    def _accept(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.create_task(self._serve(reader, writer))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _serve(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            LOOPBACK, self._upstream_port
        )
        pump = asyncio.create_task(forward_bytes(reader, upstream_writer))
        try:
            await relay_responses(upstream_reader, writer)
        finally:
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)
            for stream in (upstream_writer, writer):
                stream.close()
                with contextlib.suppress(OSError):
                    await stream.wait_closed()


async def forward_bytes(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    with contextlib.suppress(OSError):
        while data := await reader.read(RELAY_READ_BYTES):
            writer.write(data)
            await writer.drain()


async def read_response(
    reader: asyncio.StreamReader,
) -> tuple[bytes, bytes] | None:
    """(head, body) of the next response, None at end of stream.

    localstub frames every response it writes here by Content-Length.
    """
    try:
        head = await reader.readuntil(HEAD_END)
    except asyncio.IncompleteReadError:
        return None
    length = 0
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            length = int(value)
    return head, await reader.readexactly(length)


def fault_of(head: bytes) -> str | None:
    marker = RELAY_FAULT.lower().encode() + b":"
    for line in head.split(b"\r\n")[1:]:
        if line.lower().startswith(marker):
            return line[len(marker) :].strip().decode("ascii")
    return None


def with_status_line(head: bytes, status_line: str) -> bytes:
    """`head` under `status_line`, without the RELAY_FAULT header."""
    marker = RELAY_FAULT.lower().encode() + b":"
    lines = head.split(b"\r\n")
    kept = [line for line in lines[1:] if not line.lower().startswith(marker)]
    return b"\r\n".join([status_line.encode("ascii"), *kept])


def parse_fault(fault: str) -> tuple[str, str]:
    """(action, argument) of a RELAY_FAULT value, or ValueError.

    relay_fault() calls this when a test builds the response, so a
    mistyped fault fails the test there instead of inside a relay task,
    whose error would only look like a closed connection to the client.
    """
    action, _, argument = fault.partition(" ")
    if action == "status" and argument.startswith("HTTP/"):
        return action, argument
    raise ValueError(f"unknown relay fault {fault!r}")


async def relay_responses(
    upstream: asyncio.StreamReader, client: asyncio.StreamWriter
) -> None:
    while (response := await read_response(upstream)) is not None:
        head, body = response
        fault = fault_of(head)
        if fault is None:
            client.write(head + body)
            await client.drain()
            continue
        _, status_line = parse_fault(fault)
        client.write(with_status_line(head, status_line) + body)
        await client.drain()


def relay_fault(fault: str, *, status: int = 200) -> HTTPResponse:
    """A response FaultRelay replaces with `fault` (see parse_fault)."""
    parse_fault(fault)
    return HTTPResponse.raw(b"", status=status, headers={RELAY_FAULT: fault})


def closed_port() -> int:
    """A loopback port nothing listens on: bound once, then released."""
    with socket.socket() as sock:
        sock.bind((LOOPBACK, 0))
        return sock.getsockname()[1]


@pytest_asyncio.fixture
async def stub() -> AsyncIterator[Stub]:
    """The tunnel route's TLS proxy and the server behind it.

    The server answers every request with the harness's 400 tripwire, so
    a call that took the tunnel by mistake shows up as a request.
    """
    async with mock_server() as (server, proxy):
        server.set_default_response(unexpected_request())
        yield server, proxy


@pytest_asyncio.fixture
async def endpoint() -> AsyncIterator[AsyncHTTPTestServer]:
    """A second plain-HTTP server: a direct endpoint or a stub proxy."""
    async with AsyncHTTPTestServer() as server:
        server.set_default_response(unexpected_request())
        yield server


@pytest_asyncio.fixture
async def relay(endpoint: AsyncHTTPTestServer) -> AsyncIterator[FaultRelay]:
    async with FaultRelay(endpoint) as fault_relay:
        yield fault_relay


def web_identity_success() -> HTTPResponse:
    return sts_success_xml(
        action=ACTION,
        access_key="ASIAWEB",
        secret_key="WEB-secret",
        session_token="WEB-token",
        assumed_role_id="AROAWEB:s",
        arn=f"arn:aws:sts::{WEB_ACCOUNT}:assumed-role/w/s",
    )


EXPORTED: Final = export_credentials_output(
    "ASIAWEB", "WEB-secret", "WEB-token", FUTURE_EXPIRATION
)


# The role cache entry for web_identity_success(); the account comes from
# the assumed-role ARN.
CACHED_WEB_IDENTITY: Final = RoleCacheContent(
    {
        "Credentials": {
            "AccessKeyId": "ASIAWEB",
            "SecretAccessKey": "WEB-secret",
            "SessionToken": "WEB-token",
            "Expiration": FUTURE_EXPIRATION,
            "AccountId": WEB_ACCOUNT,
        }
    }
)


def cache_path() -> str:
    return f"{CLI_CACHE_DIR}/{role_cache_key(CACHE_ARGS)}.json"


def general_error(message: str) -> bytes:
    return f"\naws: [ERROR]: {message.strip()}\n".encode()


def authority(url: str) -> str:
    return urlsplit(url).netloc


async def run_web_identity(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    servers: Sequence[AsyncHTTPTestServer],
    env: EnvChanges,
    *,
    globals_: Sequence[str] = (),
    proxy_auth: bool = False,
) -> CliRun:
    """Run one web-identity export-credentials.

    The intercept route's server is always recorded after `servers`, so a
    request on an unintended route shows up. `proxy_auth` also records
    Proxy-Authorization.
    """
    tunnel_server, proxy = stub
    token = sandbox.write(TOKEN_FILE, WEB_TOKEN)
    sandbox.config.write_text(CONFIG.format(token=token), encoding="utf-8")
    run_env = sandbox.env(proxy)
    for key, value in env.items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [*servers, tunnel_server],
        run_env,
        globals_=globals_,
        normalize=(
            normalize_with_proxy_auth if proxy_auth else normalize_request
        ),
    )


def assert_failed(
    run: CliRun,
    stderr: bytes | BytesStartingWith,
    *,
    returncode: int = GENERAL_RC,
) -> None:
    """The run failed with `stderr`, printed nothing, and wrote nothing."""
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        b"",
        stderr,
    ), run.describe()
    assert run.changes == {}, run.describe()


def assert_cached(run: CliRun) -> None:
    """The run created the role cache, and its directories, and no more.

    The sandbox HOME has no `.aws` yet, so every level is created
    (utils.py:3991-4006).
    """
    assert run.changes == {
        **created_cache_directories(),
        cache_path(): (CACHE_FILE_MODE, CACHED_WEB_IDENTITY),
    }, run.describe()


def sent_headers(
    values: Mapping[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Every compared header: absent (None) unless named in `values`."""
    return {**dict.fromkeys(COMPARED_HEADERS), **(values or {})}


def web_identity_call(host: str, target: str = "/") -> RequestShape:
    """The unsigned web-identity call (credentials.py:1009-1020).

    Its form body, Content-Type, and no Authorization, X-Amz-Date, or
    security token.
    """
    return (
        "POST",
        host,
        target,
        FORM_MEDIA_TYPE,
        decode_body(WEB_BODY, FORM_MEDIA_TYPE),
        sent_headers({"content-type": FORM_MEDIA_TYPE}),
        None,
    )


def tunnel_connect(
    headers: Mapping[str, str | None] | None = None,
) -> RequestShape:
    """urllib3's CONNECT for the STS tunnel: no body, no AWS headers."""
    return (
        "CONNECT",
        STS_AUTHORITY,
        STS_AUTHORITY,
        None,
        None,
        sent_headers(headers),
        None,
    )


def request_shape(request: NormalizedRequest) -> RequestShape:
    return (
        request.method,
        request.host,
        request.target,
        request.content_type,
        request.body,
        dict(request.headers),
        request.signing_scope,
    )


def assert_requests(run: CliRun, expected: Sequence[RequestShape]) -> None:
    """Every request, in server order, and everything each one carried."""
    assert [request_shape(request) for request in run.requests] == list(
        expected
    ), run.describe()


def direct_env(url: str) -> dict[str, str]:
    return {"AWS_ENDPOINT_URL_STS": url, "NO_PROXY": LOOPBACK}


async def test_direct_refused_endpoint_is_endpoint_connection_error(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # Direct route. urllib3's NewConnectionError becomes
    # EndpointConnectionError naming the request URL, path included
    # (httpsession.py:498-499, exceptions.py:122-123).
    url = f"http://{LOOPBACK}:{closed_port()}/svc"
    run = await run_web_identity(aws_cli, sandbox, stub, [], direct_env(url))
    assert_failed(
        run,
        general_error(f'Could not connect to the endpoint URL: "{url}"'),
    )
    assert_requests(run, [])


async def test_tunnel_dead_proxy_is_masked_proxy_connection_error(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # Tunnel route to a proxy port nothing listens on. ProxyError becomes
    # ProxyConnectionError with the user name and password masked
    # (httpsession.py:197-212, 500-503).
    address = f"{LOOPBACK}:{closed_port()}"
    run = await run_web_identity(
        aws_cli,
        sandbox,
        stub,
        [],
        {"HTTPS_PROXY": f"http://proxyuser:proxysecret@{address}"},
    )
    assert_failed(
        run,
        general_error(
            f'Failed to connect to proxy URL: "http://***:***@{address}"'
        ),
    )
    assert_requests(run, [])


PROXY_AUTH_REJECTED: Final = HTTPResponse.raw(
    b"", status=407, headers={"Proxy-Authenticate": 'Basic realm="stub"'}
)


async def test_tunnel_connect_rejected_is_proxy_connection_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    endpoint: AsyncHTTPTestServer,
) -> None:
    # Tunnel route through a stub proxy that answers CONNECT with 407:
    # urllib3's ProxyError. The CONNECT carries Basic auth built from the
    # userinfo, unquoted before encoding (httpsession.py:245-276).
    endpoint.set_default_response(PROXY_AUTH_REJECTED)
    address = authority(endpoint.url)
    run = await run_web_identity(
        aws_cli,
        sandbox,
        stub,
        [endpoint],
        {"HTTPS_PROXY": f"http://us%40er:p%3Ass@{address}"},
        proxy_auth=True,
    )
    assert_failed(
        run,
        general_error(
            f'Failed to connect to proxy URL: "http://***:***@{address}"'
        ),
    )
    authorization = "Basic " + base64.b64encode(b"us@er:p:ss").decode()
    assert_requests(
        run, [tunnel_connect({PROXY_AUTHORIZATION: authorization})]
    )


async def test_direct_stalled_response_is_read_timeout_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    endpoint: AsyncHTTPTestServer,
) -> None:
    # Direct route; no response byte within --cli-read-timeout 1:
    # ReadTimeoutError (httpsession.py:506-507, exceptions.py:137-138).
    endpoint.set_default_response(CloseConnection(delay=STALL_SECONDS))
    run = await run_web_identity(
        aws_cli,
        sandbox,
        stub,
        [endpoint],
        direct_env(endpoint.url),
        globals_=READ_TIMEOUT_GLOBALS,
    )
    assert_failed(
        run,
        general_error(f'Read timeout on endpoint URL: "{endpoint.url}"'),
    )
    assert_requests(run, [web_identity_call(authority(endpoint.url))])


async def test_tunnel_missing_ca_bundle_is_ssl_error(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # Tunnel route through a reachable proxy: urllib3 loads AWS_CA_BUNDLE
    # when it wraps the tunnel, after CONNECT, and the OSError becomes
    # SSLError (httpsession.py:496-497). The OSError's own text is
    # CPython's and the C library's. An unreachable proxy is not covered.
    missing = sandbox.root / "missing-ca.pem"
    run = await run_web_identity(
        aws_cli, sandbox, stub, [], {"AWS_CA_BUNDLE": str(missing)}
    )
    assert_failed(
        run,
        BytesStartingWith(
            f"\naws: [ERROR]: SSL validation failed for {STS_URL} ".encode()
        ),
    )
    assert_requests(run, [])


async def test_direct_http_endpoint_ignores_missing_ca_bundle(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    endpoint: AsyncHTTPTestServer,
) -> None:
    # Direct route to a plain-HTTP endpoint: no TLS, so the bundle is never
    # loaded and the call succeeds.
    endpoint.set_default_response(web_identity_success())
    env = {
        **direct_env(endpoint.url),
        "AWS_CA_BUNDLE": str(sandbox.root / "missing-ca.pem"),
    }
    run = await run_web_identity(aws_cli, sandbox, stub, [endpoint], env)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        EXPORTED,
        b"",
    ), run.describe()
    assert_requests(run, [web_identity_call(authority(endpoint.url))])
    assert_cached(run)


@pytest.mark.parametrize(
    "proxied",
    [
        pytest.param(False, id="no-proxy-goes-direct"),
        pytest.param(True, id="http-proxy-forwards-absolute-form"),
    ],
)
async def test_http_endpoint_route_follows_no_proxy(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    endpoint: AsyncHTTPTestServer,
    proxied: bool,
) -> None:
    # A plain-HTTP endpoint with HTTP_PROXY at a recording stub. NO_PROXY
    # matching the host sends the call direct, and nothing reaches the
    # proxy; without it the call is forwarded to the proxy with an
    # absolute request-target (httpsession.py:237-243, 423-440).
    response = web_identity_success()
    async with AsyncHTTPTestServer() as proxy_stub:
        proxy_stub.set_default_response(
            response if proxied else unexpected_request()
        )
        endpoint.set_default_response(
            unexpected_request() if proxied else response
        )
        env: dict[str, str | None] = {
            "AWS_ENDPOINT_URL_STS": endpoint.url,
            "HTTP_PROXY": proxy_stub.url,
            "NO_PROXY": None if proxied else LOOPBACK,
        }
        run = await run_web_identity(
            aws_cli,
            sandbox,
            stub,
            [endpoint, proxy_stub],
            env,
        )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        EXPORTED,
        b"",
    ), run.describe()
    target = endpoint.url if proxied else "/"
    assert_requests(run, [web_identity_call(authority(endpoint.url), target)])
    assert_cached(run)


async def test_direct_generic_error_uses_standard_phrase(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    endpoint: AsyncHTTPTestServer,
    relay: FaultRelay,
) -> None:
    # On the direct route, an empty 5xx body is a generic error whose
    # Message is the status's standard phrase, whatever reason phrase the
    # wire carried (parsers.py:291-326).
    endpoint.set_default_response(
        relay_fault("status HTTP/1.1 503 Slow Down Please", status=503)
    )
    run = await run_web_identity(
        aws_cli,
        sandbox,
        stub,
        [endpoint],
        direct_env(relay.url),
    )
    assert_failed(
        run,
        general_error(
            f"An error occurred (503) when calling the {ACTION} "
            "operation (reached max retries: 0): Service Unavailable"
        ),
        returncode=CLIENT_ERROR_RC,
    )
    assert_requests(run, [web_identity_call(authority(relay.url))])
