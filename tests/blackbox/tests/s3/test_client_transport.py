"""The trust store and proxy settings of `s3 ls` and `s3 cp`.

Each test runs one command against the in-memory bucket of s3store.py and
asserts the result lines, the exit status, what was moved, and the requests
the bucket answered. Every blackbox test already reaches the bucket through
the TLS intercept proxy named by HTTPS_PROXY and trusts the proxy's CA
through AWS_CA_BUNDLE (credential_env), so these tests cover the other ways
to name the CA and a proxy bypass.
"""

import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pytest
import trustme
from localstub import AsyncHTTPTestServer, AsyncTLSInterceptProxy
from localstub.handlers import handle_expect_header

from credhelpers import CommandTimeoutError, credential_env, run_command
from nethelpers import ClientHelloRecorder, refusing_port
from s3store import (
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
LOOPBACK: Final = "127.0.0.1"
# The CLI writes LastModified in local time, and s3_runtime pins TZ=UTC.
LISTED_TIME: Final = "2026-01-02 03:04:05"
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): pattern_bytes("object", 2048),
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
    (BUCKET, "tree/b.txt"): pattern_bytes("tree b", 1500),
    (BUCKET, "tree/nested/c.txt"): pattern_bytes("tree c", 700),
}
DOWNLOAD_BODY: Final = SEED_OBJECTS[(BUCKET, "download/object.txt")]
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)


@dataclass(frozen=True)
class Command:
    """One command line and everything a successful run of it shows."""

    name: str
    arguments: tuple[str, ...]
    stdout: str
    local_files: Mapping[str, bytes] = field(default_factory=dict[str, bytes])
    downloaded_files: Mapping[str, bytes] = field(
        default_factory=dict[str, bytes]
    )
    uploaded_objects: Mapping[ObjectKey, bytes] = field(
        default_factory=dict[ObjectKey, bytes]
    )
    # Whether `s3 cp` moves the data with its transfer client.
    transfers: bool = True


def listed_line(key: str) -> str:
    """A recursive listing's object line (subcommands.py:868)."""
    size = len(SEED_OBJECTS[(BUCKET, key)])
    return f"{LISTED_TIME} {size:>10} {key}\n"


LS: Final = Command(
    "ls",
    ("s3", "ls", f"s3://{BUCKET}/tree/", "--recursive"),
    "".join(
        listed_line(key)
        for key in ("tree/a.txt", "tree/b.txt", "tree/nested/c.txt")
    ),
    transfers=False,
)
DOWNLOAD: Final = Command(
    "download",
    ("s3", "cp", f"s3://{BUCKET}/download/object.txt", "object.txt"),
    f"download: s3://{BUCKET}/download/object.txt to .{os.sep}object.txt\n",
    downloaded_files={"object.txt": DOWNLOAD_BODY},
)
UPLOAD: Final = Command(
    "upload",
    ("s3", "cp", "upload.txt", f"s3://{BUCKET}/up/upload.txt"),
    f"upload: .{os.sep}upload.txt to s3://{BUCKET}/up/upload.txt\n",
    local_files={"upload.txt": UPLOAD_FILE},
    uploaded_objects={(BUCKET, "up/upload.txt"): UPLOAD_FILE},
)
COMMANDS: Final = [
    pytest.param(command, id=command.name)
    for command in (LS, DOWNLOAD, UPLOAD)
]


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: InMemoryS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )


def name_ca_bundle(env: dict[str, str], source: str, path: str) -> list[str]:
    """Name the CA bundle at `path` through `source`: AWS_CA_BUNDLE, the
    --ca-bundle flag, the profile's ca_bundle, or REQUESTS_CA_BUNDLE.
    Returns the arguments it adds to the command."""
    if source == "env":
        env["AWS_CA_BUNDLE"] = path
    elif source == "flag":
        return ["--ca-bundle", path]
    elif source == "profile":
        Path(env["AWS_CONFIG_FILE"]).write_text(
            f"[default]\nca_bundle = {path}\n", encoding="utf-8"
        )
    else:
        env["REQUESTS_CA_BUNDLE"] = path
    return []


async def run_aws(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    *,
    arguments: tuple[str, ...] = (),
    environment: Mapping[str, str] | None = None,
    trust: str | None = "env",
    distrust: tuple[str, ...] = (),
    plain_endpoint: bool = False,
    timeout: float = 30.0,
) -> Run:
    """Run `command` once in tmp_path/work against the seeded bucket.

    `trust` names how the command trusts the proxy's CA (`name_ca_bundle`):
    AWS_CA_BUNDLE, as every blackbox test does, or another source, or None
    for none at all. Each source in `distrust` names a bundle of another CA,
    which the proxy's certificate does not chain to. `plain_endpoint` sends
    the command straight to the bucket's plain-HTTP address with
    --endpoint-url.
    """
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, command.local_files)
    store = InMemoryS3(SEED_OBJECTS)
    full = [aws_cli, *command.arguments, *arguments]
    if command.transfers:
        full.append("--no-progress")
    async with s3_runtime(store, tmp_path) as (server, env):
        if plain_endpoint:
            full += ["--endpoint-url", server.url.rstrip("/")]
        ca = env.pop("AWS_CA_BUNDLE")
        if distrust:
            other = tmp_path / "other-ca.pem"
            other.write_bytes(trustme.CA().cert_pem.bytes())
            for source in distrust:
                full += name_ca_bundle(env, source, str(other))
        if trust is not None:
            full += name_ca_bundle(env, trust, ca)
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            full, env, cwd=work, stdin=None, timeout=timeout
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


def assert_succeeded(run: Run, command: Command, stderr: str = "") -> None:
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        command.stdout,
        stderr,
    ), report
    assert run.local_files == {
        **command.local_files,
        **command.downloaded_files,
    }, report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **command.uploaded_objects,
    }, report
    assert run.store.received, report


def signed(run: Run) -> list[bool]:
    return [
        "Authorization" in request.wire_request.headers
        for request in run.store.received
    ]


# The CA bundle named by the global argument or the profile's ca_bundle
# instead of AWS_CA_BUNDLE. botocore resolves all three into the session's
# ca_bundle (configprovider.py:66), and the CRT client `s3 cp` runs gets
# the same value as its trust store (customizations/s3/factory.py:530-536).
@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("trust", ["flag", "profile"])
async def test_ca_bundle_source_trusts_the_endpoint(
    aws_cli: str, tmp_path: Path, command: Command, trust: str
) -> None:
    run = await run_aws(aws_cli, tmp_path, command, trust=trust)
    assert_succeeded(run, command)
    assert all(signed(run)), run.describe()


# When more than one source names a CA bundle, the --ca-bundle flag wins,
# then AWS_CA_BUNDLE, then the profile's ca_bundle (botocore
# configprovider.py:66), for the CRT client too (factory.py:530-536). The
# winner names the proxy's CA and every other source another CA, so the
# command reaches the bucket only through the winner.
@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize(
    ("trust", "distrust"),
    [
        pytest.param("env", ("profile",), id="env-over-profile"),
        pytest.param("flag", ("env", "profile"), id="flag-over-all"),
    ],
)
async def test_ca_bundle_precedence_trusts_the_winning_source(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    trust: str,
    distrust: tuple[str, ...],
) -> None:
    run = await run_aws(
        aws_cli, tmp_path, command, trust=trust, distrust=distrust
    )
    assert_succeeded(run, command)
    assert all(signed(run)), run.describe()


# urllib3's warning for a request sent without verifying the proxy's
# certificate (urllib3/connectionpool.py).
INSECURE_REQUEST_WARNING: Final = (
    "urllib3/connectionpool.py:1097: InsecureRequestWarning: Unverified "
    "HTTPS request is being made to host '127.0.0.1'. Adding certificate "
    "verification is strongly advised. See: https://urllib3.readthedocs.io/"
    "en/latest/advanced-usage.html#tls-warnings\n"
)


# --no-verify-ssl turns certificate verification off for both clients, so
# bundles that do not trust the proxy's CA do not matter. urllib3 warns
# about each request botocore's own client sends, the listing and a
# download's HeadObject; the transfer client warns about none.
@pytest.mark.parametrize(
    ("command", "warnings"),
    [
        pytest.param(LS, 1, id="ls"),
        pytest.param(DOWNLOAD, 1, id="download"),
        pytest.param(UPLOAD, 0, id="upload"),
    ],
)
async def test_no_verify_ssl_ignores_untrusted_ca_bundles(
    aws_cli: str, tmp_path: Path, command: Command, warnings: int
) -> None:
    run = await run_aws(
        aws_cli,
        tmp_path,
        command,
        arguments=("--no-verify-ssl",),
        trust=None,
        distrust=("env", "profile"),
    )
    assert_succeeded(run, command, INSECURE_REQUEST_WARNING * warnings)


# REQUESTS_CA_BUNDLE is read by botocore's own clients only
# (botocore/endpoint.py:439-448), so `s3 ls` trusts the endpoint. The CRT
# client resolves its trust store without it (factory.py:530-536) and
# fails the TLS handshake of the transfer.
async def test_requests_ca_bundle_trusts_the_listing_only(
    aws_cli: str, tmp_path: Path
) -> None:
    run = await run_aws(aws_cli, tmp_path, LS, trust="requests")
    assert_succeeded(run, LS)


@dataclass(frozen=True)
class HandshakeRun:
    """A command run against the bucket behind a ClientHelloRecorder.

    `returncode` is None when the command was still running at its
    deadline and was killed.
    """

    returncode: int | None
    local_files: dict[str, bytes]
    store: InMemoryS3
    server_names: list[str | None]

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
            f"ClientHello server names: {self.server_names}\n"
        )


# A client that trusts the proxy's CA sends its request within milliseconds
# of its ClientHello. One that rejects the proxy's certificate sends nothing
# more: s2n holds the connection through its blinding delay, 10 to 30
# seconds, before the CLI hears of the failure. Each run is killed at this
# deadline instead of waiting that out; the trusted run of the same command
# shows the deadline leaves time for its request.
HANDSHAKE_DEADLINE_SECONDS: Final = 5.0
ENDPOINT_HOST: Final = f"{BUCKET}.s3.us-east-1.amazonaws.com"


async def run_until_deadline(
    aws_cli: str, tmp_path: Path, command: Command, trust: str | None
) -> HandshakeRun:
    """Run `command` as `run_aws` does, behind a ClientHelloRecorder, and
    kill it at HANDSHAKE_DEADLINE_SECONDS."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    write_tree(work, command.local_files)
    store = InMemoryS3(SEED_OBJECTS)
    recorder = ClientHelloRecorder()
    full = [aws_cli, *command.arguments]
    if command.transfers:
        full.append("--no-progress")
    async with (
        AsyncHTTPTestServer(
            on_headers_received=handle_expect_header
        ) as server,
        AsyncTLSInterceptProxy(server=server, ca=recorder) as proxy,
    ):
        server.handler = store.respond
        env = credential_env(proxy, tmp_path)
        env.update(
            AWS_ACCESS_KEY_ID="AKIDS3STORE",
            AWS_SECRET_ACCESS_KEY="s3store-secret",
            # The fewest attempts the CRT client takes (factory.py
            # MIN_CRT_MAX_ATTEMPTS), so `auto` still runs on it.
            AWS_MAX_ATTEMPTS="2",
        )
        ca = env.pop("AWS_CA_BUNDLE")
        if trust is not None:
            full += name_ca_bundle(env, trust, ca)
        returncode: int | None
        try:
            _, _, returncode = await run_command(
                full,
                env,
                cwd=work,
                stdin=None,
                timeout=HANDSHAKE_DEADLINE_SECONDS,
            )
        except CommandTimeoutError:
            returncode = None
    return HandshakeRun(
        returncode=returncode,
        local_files=read_tree(work),
        store=store,
        server_names=recorder.server_names,
    )


def assert_refused_handshake(
    run: HandshakeRun, command: Command, operations: list[str]
) -> None:
    """The command began TLS with the proxy for the bucket's host and sent
    no request past `operations`, which botocore's own client sent, and
    moved nothing.

    A download killed at the deadline leaves the empty temporary file it
    would have removed on failing, so only its destination must be absent.
    """
    report = run.describe()
    assert run.returncode != 0, report
    assert run.store.failures == [], report
    assert set(run.server_names) == {ENDPOINT_HOST}, report
    assert run.store.operations() == operations, report
    created = {
        name: body
        for name, body in run.local_files.items()
        if name not in command.local_files
    }
    assert not created.keys() & command.downloaded_files.keys(), report
    assert not any(created.values()), report
    assert run.store.objects == SEED_OBJECTS, report


async def assert_trusted_run_reaches_the_bucket(
    aws_cli: str, tmp_path: Path, command: Command
) -> None:
    """With the proxy's CA trusted, the same command completes before the
    deadline, so a refused run's silence is not the deadline's doing."""
    run = await run_until_deadline(aws_cli, tmp_path, command, "env")
    report = run.describe()
    assert run.returncode == 0, report
    assert run.store.failures == [], report
    assert set(run.server_names) == {ENDPOINT_HOST}, report
    assert run.local_files == {
        **command.local_files,
        **command.downloaded_files,
    }, report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **command.uploaded_objects,
    }, report


# The CRT client resolves its trust store without REQUESTS_CA_BUNDLE
# (factory.py:530-536), so it rejects the proxy's certificate and the
# transfer sends no request. Only botocore's HeadObject of a download, sent
# by a client that does read it, reaches the bucket.
@pytest.mark.parametrize(
    ("command", "operations"),
    [
        pytest.param(DOWNLOAD, ["HeadObject"], id="download"),
        pytest.param(UPLOAD, [], id="upload"),
    ],
)
async def test_requests_ca_bundle_is_not_the_transfer_trust_store(
    aws_cli: str, tmp_path: Path, command: Command, operations: list[str]
) -> None:
    await assert_trusted_run_reaches_the_bucket(
        aws_cli, tmp_path / "trusted", command
    )
    run = await run_until_deadline(
        aws_cli, tmp_path / "untrusted", command, "requests"
    )
    assert_refused_handshake(run, command, operations)


# With no CA bundle anywhere, both clients verify against the default trust
# store, which does not hold the proxy's CA, so each command rejects the
# proxy's certificate before any request reaches the bucket.
@pytest.mark.parametrize("command", COMMANDS)
async def test_default_trust_store_does_not_trust_the_proxy_ca(
    aws_cli: str, tmp_path: Path, command: Command
) -> None:
    await assert_trusted_run_reaches_the_bucket(
        aws_cli, tmp_path / "trusted", command
    )
    run = await run_until_deadline(
        aws_cli, tmp_path / "untrusted", command, None
    )
    assert_refused_handshake(run, command, [])


def closed_port() -> int:
    """A loopback port nothing listens on: bound once, then released."""
    with socket.socket() as sock:
        sock.bind((LOOPBACK, 0))
        return sock.getsockname()[1]


# NO_PROXY naming the endpoint's host sends every request straight to it,
# past proxies nothing listens on: botocore's clients through
# should_bypass_proxies (botocore/utils.py:3039), and the CRT client through
# aws-c-http's environment proxy settings (proxy_connection.c, no_proxy.c).
# A proxied request would fail to connect.
@pytest.mark.parametrize("command", COMMANDS)
async def test_no_proxy_sends_requests_straight_to_the_endpoint(
    aws_cli: str, tmp_path: Path, command: Command
) -> None:
    dead_proxy = f"http://{LOOPBACK}:{closed_port()}"
    run = await run_aws(
        aws_cli,
        tmp_path,
        command,
        environment={
            "HTTPS_PROXY": dead_proxy,
            "HTTP_PROXY": dead_proxy,
            "NO_PROXY": LOOPBACK,
        },
        plain_endpoint=True,
    )
    assert_succeeded(run, command)


# --no-sign-request sends every request without Authorization, the
# transfer client's too (factory.py:400-404).
@pytest.mark.parametrize("command", COMMANDS)
async def test_no_sign_request_sends_no_authorization(
    aws_cli: str, tmp_path: Path, command: Command
) -> None:
    run = await run_aws(
        aws_cli, tmp_path, command, arguments=("--no-sign-request",)
    )
    assert_succeeded(run, command)
    assert not any(signed(run)), run.describe()


# Each scheme's proxy variables, as botocore's clients and the CRT client
# read them: the lowercase one over the uppercase one, an empty lowercase
# one turning the uppercase one off, and NO_PROXY bypassing both for the
# hosts it names (urllib.request.getproxies_environment, botocore
# utils.py:3039, aws-c-http proxy_connection.c). The proxy and the endpoint
# both refuse connections, so every command fails before any request. A
# listing or download names the address it tried, the proxy's credentials
# masked; the CRT client's upload reports either refusal alike.
PROXY_MODES: Final = ("upper", "lower", "disabled", "direct", "bypassed")
# Windows names environment variables without regard to case, so there the
# lowercase variable is the uppercase one.
CASE_SENSITIVE_ENVIRONMENT: Final = pytest.mark.skipif(
    os.name == "nt", reason="Windows environment names ignore case"
)
PROXY_OPERATIONS: Final = {
    "list": ("s3", "ls", f"s3://{BUCKET}/"),
    "upload": ("s3", "cp", "input", f"s3://{BUCKET}/object", "--no-progress"),
    "download": (
        "s3",
        "cp",
        f"s3://{BUCKET}/object",
        "output",
        "--no-progress",
    ),
    "upload-recursive": (
        "s3",
        "cp",
        "inputs",
        f"s3://{BUCKET}/",
        "--recursive",
        "--no-progress",
    ),
    "download-recursive": (
        "s3",
        "cp",
        f"s3://{BUCKET}/",
        "output",
        "--recursive",
        "--no-progress",
    ),
}
PROXY_LOCAL_FILES: Final = {"input": UPLOAD_FILE, "inputs/object": UPLOAD_FILE}


def proxy_case(scheme: str, operation: str, mode: str) -> object:
    return pytest.param(
        scheme,
        operation,
        mode,
        id=f"{scheme}-{operation}-{mode}",
        marks=(
            CASE_SENSITIVE_ENVIRONMENT if mode in ("lower", "disabled") else ()
        ),
    )


PROXY_CASES: Final = [
    *(
        proxy_case(scheme, operation, mode)
        for scheme in ("http", "https")
        for operation in ("list", "upload")
        for mode in PROXY_MODES
    ),
    *(
        proxy_case("http", operation, "upper")
        for operation in ("download", "upload-recursive", "download-recursive")
    ),
]


def proxy_environment(
    scheme: str, mode: str, proxy: str, decoy: str
) -> dict[str, str]:
    """The variables `mode` sets for the endpoint's `scheme`."""
    upper = f"{scheme.upper()}_PROXY"
    lower = upper.lower()
    if mode == "upper":
        return {upper: proxy}
    if mode == "lower":
        return {upper: decoy, lower: proxy}
    if mode == "disabled":
        return {upper: proxy, lower: ""}
    if mode == "bypassed":
        return {upper: proxy, "NO_PROXY": "localhost, 127.0.0.1"}
    return {lower: ""}


def refusal(
    operation: str, mode: str, endpoint: str, proxy_port: int
) -> tuple[int, str]:
    """The exit status and stderr of `operation` under `mode`.

    The download cases run only through the proxy, so only a listing
    reports the endpoint it tried.
    """
    if mode in ("upper", "lower"):
        tried = (
            "Failed to connect to proxy URL: "
            f'"http://***:***@{LOOPBACK}:{proxy_port}"'
        )
    else:
        tried = (
            "Could not connect to the endpoint URL: "
            f'"{endpoint}/{BUCKET}?list-type=2&prefix=&delimiter=%2F'
            '&encoding-type=url"'
        )
    if operation == "list":
        return 255, f"\naws: [ERROR]: {tried}\n"
    if operation.startswith("download"):
        return 1, f"fatal error: {tried}\n"
    source = (
        f"inputs{os.sep}object"
        if operation == "upload-recursive"
        else f".{os.sep}input"
    )
    return 1, (
        f"upload failed: {source} to s3://{BUCKET}/object "
        "AWS_IO_SOCKET_CONNECTION_REFUSED: socket connection refused.\n"
    )


@pytest.mark.parametrize(("scheme", "operation", "mode"), PROXY_CASES)
async def test_proxy_settings_choose_which_refusing_address_fails(
    aws_cli: str, tmp_path: Path, scheme: str, operation: str, mode: str
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, PROXY_LOCAL_FILES)
    store = InMemoryS3()
    with (
        refusing_port() as endpoint_port,
        refusing_port() as proxy_port,
        refusing_port() as decoy_port,
    ):
        endpoint = f"{scheme}://{LOOPBACK}:{endpoint_port}"
        async with s3_runtime(store, tmp_path) as (_, env):
            del env["HTTPS_PROXY"], env["HTTP_PROXY"]
            # Every attempt is refused, so two attempts, the fewest the CRT
            # client takes (factory.py MIN_CRT_MAX_ATTEMPTS), keep the
            # retry backoff short.
            env["AWS_MAX_ATTEMPTS"] = "2"
            env.update(
                proxy_environment(
                    scheme,
                    mode,
                    f"http://user:secret@{LOOPBACK}:{proxy_port}",
                    f"http://{LOOPBACK}:{decoy_port}",
                )
            )
            stdout, stderr, returncode = await run_command(
                [
                    aws_cli,
                    *PROXY_OPERATIONS[operation],
                    "--endpoint-url",
                    endpoint,
                ],
                env,
                cwd=work,
                stdin=None,
            )
    status, expected = refusal(operation, mode, endpoint, proxy_port)
    assert (returncode, decoded(stdout), decoded(stderr)) == (
        status,
        "",
        expected,
    )
    assert read_tree(work) == PROXY_LOCAL_FILES
    assert store.received == []


# A blank REQUESTS_CA_BUNDLE is botocore's error when it builds the
# command's client, before any request (endpoint.py:436-460), with the
# general handler's status. botocore reads it only without AWS_CA_BUNDLE.
@pytest.mark.parametrize(
    "arguments",
    [
        ["s3", "ls", f"s3://{BUCKET}"],
        ["s3", "cp", f"s3://{BUCKET}/key", "./never-written"],
    ],
    ids=["ls", "cp"],
)
async def test_blank_requests_ca_bundle_fails_before_any_request(
    aws_cli: str, tmp_path: Path, arguments: list[str]
) -> None:
    async with s3_runtime(InMemoryS3(), tmp_path) as (server, env):
        del env["AWS_CA_BUNDLE"]
        env["REQUESTS_CA_BUNDLE"] = ""
        result = await run_command([aws_cli, *arguments], env, cwd=tmp_path)
    assert result == (
        b"",
        b"\naws: [ERROR]: Invalid CA bundle: the configured value "
        b"(ca_bundle, AWS_CA_BUNDLE, REQUESTS_CA_BUNDLE, or verify) "
        b"resolved to an empty or whitespace-only string. Provide a valid "
        b"path to a CA bundle file.\n",
        255,
    ), result[1].decode()
    assert not server.requests
    assert not (tmp_path / "never-written").exists()
