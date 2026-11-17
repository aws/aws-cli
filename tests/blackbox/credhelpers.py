"""Credential blackbox setup, independent SigV4 assertions, and the
single-run harness of the `aws configure export-credentials` suites.

All keys are synthetic. Provider tests must remove the upstream helper's
default credentials and isolate every file provider before invoking the CLI.

The export-credentials half, from `Sandbox` on, runs each scenario as a
plain blackbox test: write the provider files into a `Sandbox`, script
localstub servers behind the TLS intercept proxy, run `aws <globals>
configure export-credentials <args>` once through
`run_export_credentials`, and assert the outcome: the return code, the
stdout and stderr bytes, the normalized requests, and every file the
command created, changed, or removed under the sandbox.

What the service and the tools sharing a cache observe is asserted, not
how botocore happens to serialize it: requests compare by decoded body,
cache files through `JsonContent` and `RoleCacheContent`, and created
directories through `CREATED_DIRECTORY_MODE`. Error text that comes from
CPython or a C library rather than from the AWS CLI is matched with
`BytesStartingWith` on the AWS-authored part.
"""

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import shlex
import signal
import stat
import sys
import time
import uuid
from collections.abc import (
    AsyncIterator,
    Callable,
    Container,
    Mapping,
    Sequence,
)
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import parse_qs, parse_qsl, quote, urlsplit
from xml.sax.saxutils import escape

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature,
)
from localstub import (
    AsyncHTTPTestServer,
    AsyncTLSInterceptProxy,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponderContext,
    ResponseSpec,
)

from harness_plugin import child_environment, fold_newlines
from tests.blackbox.utils import (
    cli_env,
    empty_list_objects_response,
    mock_server,
    run_cli,
)

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet


def credential_env(
    proxy: AsyncTLSInterceptProxy, tmp_path: Path
) -> dict[str, str]:
    """The repo tests' command environment: upstream's, without its keys and
    without its AWS_MAX_ATTEMPTS=1.

    One attempt is outside the CRT client's 2 to 64, so with it the AWS CLI
    resolves `auto` to the classic client; without it, to the CRT client
    these tests exercise. Upstream's own tests keep upstream's environment.
    """
    env = cli_env(proxy)
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        del env[key]
    del env["AWS_MAX_ATTEMPTS"]
    # These paths suppress user config, ~/.boto, and /etc/boto.cfg without
    # changing HOME. Metadata is opt-in only in the dedicated IMDS tests.
    for key, name in (
        ("AWS_CONFIG_FILE", "config"),
        ("AWS_SHARED_CREDENTIALS_FILE", "credentials"),
        ("BOTO_CONFIG", "boto"),
    ):
        path = tmp_path / name
        path.write_text("", encoding="utf-8")
        env[key] = str(path)
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    return env


@asynccontextmanager
async def credential_runtime(
    tmp_path: Path, *, temp_home: bool = False
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with mock_server() as (server, proxy):
        env = credential_env(proxy, tmp_path)
        if temp_home:
            # SSO has no token-cache override. Isolate token and role caches
            # in the child environment without changing the caller's HOME.
            env["HOME"] = str(tmp_path)
            if sys.platform == "win32":
                # Both routes resolve `~` from USERPROFILE first there.
                env["USERPROFILE"] = str(tmp_path)
        yield server, env


def file_credentials(identity: str, token: str | None = None) -> str:
    text = (
        f"aws_access_key_id = AKID{identity}\n"
        f"aws_secret_access_key = {identity}-secret\n"
    )
    if token is not None:
        text += f"aws_session_token = {token}\n"
    return text


def write_config(
    env: dict[str, str], text: str, *, shared: bool = False
) -> None:
    key = "AWS_SHARED_CREDENTIALS_FILE" if shared else "AWS_CONFIG_FILE"
    Path(env[key]).write_text(text, encoding="utf-8")


def process_credentials(identity: str = "PROCESS") -> dict[str, object]:
    return {
        "Version": 1,
        "AccessKeyId": f"AKID{identity}",
        "SecretAccessKey": f"{identity}-secret",
        "SessionToken": f"{identity}-token",
    }


def metadata_credentials(identity: str = "CONTAINER") -> dict[str, object]:
    return {
        "AccessKeyId": f"AKID{identity}",
        "SecretAccessKey": f"{identity}-secret",
        "Token": f"{identity}-token",
        "Expiration": "2099-01-01T00:00:00Z",
    }


def credential_process(tmp_path: Path, source: str) -> tuple[str, Path]:
    script = tmp_path / "credential helper.py"
    log = tmp_path / "process-calls.jsonl"
    script.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        f"log = Path({str(log)!r})\n"
        "calls = len(log.read_text().splitlines()) if log.exists() else 0\n"
        "with log.open('a') as stream:\n"
        "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n" + source,
        encoding="utf-8",
    )
    return command_line([sys.executable, str(script)]), log


# shlex.quote's unquoted characters, plus the Windows path separator, so the
# interpreter's path stays unquoted: cmd.exe strips the outer quotes of a
# line that starts with one.
_WINDOWS_PLAIN_ARGUMENT = re.compile(r"[\w@%+=:,./\\-]+", re.ASCII)


def command_line(arguments: list[str]) -> str:
    """`arguments` quoted as a `credential_process` value.

    botocore splits the value with POSIX shell rules, except on Windows,
    where it splits as CommandLineToArgvW does and the CRT runs the line
    through cmd.exe. Windows quotes what `shlex.join` would, in double
    quotes, so an argument such as `;` stays quoted there too. Unquoted
    after whitespace, the CRT's profile parser would read it as a comment,
    a parity gap rather than what these tests measure.
    """
    if sys.platform != "win32":
        return shlex.join(arguments)
    quoted = []
    for argument in arguments:
        if _WINDOWS_PLAIN_ARGUMENT.fullmatch(argument):
            quoted.append(argument)
            continue
        # Either would need CommandLineToArgvW's backslash escaping.
        assert '"' not in argument, argument
        assert not argument.endswith("\\"), argument
        quoted.append(f'"{argument}"')
    return " ".join(quoted)


def json_process(
    tmp_path: Path, payload: dict[str, object]
) -> tuple[str, Path]:
    return credential_process(tmp_path, f"print({json.dumps(payload)!r})\n")


async def list_bucket(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    *arguments: str,
    responses: list[HTTPResponse] | None = None,
) -> tuple[bytes, bytes, int]:
    if responses is None:
        server.set_default_response(empty_list_objects_response())
    else:
        server.set_response_sequence(responses)
    return await run_cli(
        aws_cli,
        ["s3", "ls", "s3://credential-parity/", *arguments],
        env,
        timeout=20,
    )


async def rejected_role_request(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    *arguments: str,
) -> RecordedHTTPRequest:
    """The one STS call `s3 ls` makes before STS rejects it.

    STS rejects the call deliberately: a successful role response would
    write the CLI cache under the caller's HOME.
    """
    server.set_default_response(sts_error_xml(request_id="test-request"))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://credential-parity/", *arguments],
        env,
        timeout=20,
    )
    assert rc != 0, stdout
    assert b"stubbed STS rejection" in stderr, stderr.decode()
    assert len(server.requests) == 1
    request = server.requests[0]
    assert request.method == "POST"
    return request


def assert_signed_by(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    identity: str,
    token: str | None = None,
) -> None:
    stdout, stderr, rc = result
    assert rc == 0, f"stdout={stdout!r}, stderr={stderr!r}, rc={rc}"
    assert len(server.requests) == 1
    request = server.requests[0]
    assert request.method == "GET"
    assert request.headers.get("x-amz-security-token") == token
    assert_signature(request, f"AKID{identity}", f"{identity}-secret")


def assert_signature(
    request: RecordedHTTPRequest, access_key: str, secret_key: str
) -> None:
    # Reconstruct from the wire, not either implementation's signing API.
    authorization = request.headers["authorization"]
    algorithm, fields = authorization.split(" ", 1)
    attributes = dict(field.split("=", 1) for field in fields.split(", "))
    key, scope = attributes["Credential"].split("/", 1)
    assert key == access_key
    names = attributes["SignedHeaders"].split(";")
    headers = "".join(
        f"{name}:{' '.join(request.headers[name].split())}\n" for name in names
    )
    url = urlsplit(request.effective_path)
    query = "&".join(
        f"{quote(key, safe='-_.~')}={quote(value, safe='-_.~')}"
        for key, value in sorted(parse_qsl(url.query, keep_blank_values=True))
    )
    payload_hash = request.headers.get(
        "x-amz-content-sha256",
        hashlib.sha256(request.wire_body_bytes).hexdigest(),
    )
    canonical = "\n".join(
        [
            request.method,
            url.path or "/",
            query,
            headers,
            attributes["SignedHeaders"],
            payload_hash,
        ]
    )
    string_to_sign = "\n".join(
        [
            algorithm,
            request.headers["x-amz-date"],
            scope,
            hashlib.sha256(canonical.encode()).hexdigest(),
        ]
    )
    signing_key = f"AWS4{secret_key}".encode()
    for part in scope.split("/"):
        signing_key = hmac.digest(signing_key, part.encode(), "sha256")
    assert (
        attributes["Signature"]
        == hmac.new(signing_key, string_to_sign.encode(), "sha256").hexdigest()
    )


def assert_credential_error(
    result: tuple[bytes, bytes, int], server: AsyncHTTPTestServer
) -> None:
    stdout, stderr, rc = result
    assert rc != 0, f"unexpected success: stdout={stdout!r}, stderr={stderr!r}"
    assert stderr
    assert not server.requests, (
        "invalid credentials must not sign an S3 request"
    )
    assert b"native implementation unavailable" not in stderr, stderr.decode()


# --- Single-run export-credentials harness -------------------------------


def _runner_umask() -> int:
    """The runner's umask, which the CLI and every helper it runs inherit.

    os.umask reads the mask only by replacing it, so it goes straight back.
    """
    mask = os.umask(0o022)
    os.umask(mask)
    return mask


# The command words every export-credentials run puts between its global
# options and its own arguments.
EXPORT_CREDENTIALS: Final = ("configure", "export-credentials")
RUN_TIMEOUT_SECONDS: Final = 30.0
# How far a time-derived value may sit from the moment it is normalized
# and still become a placeholder. Covers the command's run time with
# margin and stays far below every refresh window the suites pin (300 s).
TIME_TOLERANCE_SECONDS: Final = 120.0
# Headers a NormalizedRequest records, absent (None) being distinct from
# empty. A SigV4 Authorization keeps only its algorithm: its scope is
# NormalizedRequest.signing_scope, and `assert_signature` checks the
# signature on the raw request. A current X-Amz-Date is masked.
COMPARED_HEADERS: Final = (
    "x-amz-security-token",
    "x-amz-sso_bearer_token",
    "x-aws-ec2-metadata-token",
    "x-aws-ec2-metadata-token-ttl-seconds",
    "authorization",
    "x-amz-date",
    "content-type",
)
# Hosts whose User-Agent a test may ask normalize_request to record: IMDS
# sends the bare `aws-cli/<ver>` (botocore utils.py:488-490), every other
# client a build-specific one. Tests with a configured IMDS endpoint add
# its Host value.
IMDS_HOSTS: Final = ("169.254.169.254", "[fd00:ec2::254]")
IMDS_TOKEN_URL: Final = "http://169.254.169.254/latest/api/token"
# The token URL under AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE=IPv6
# (botocore utils.py:88, 374-392).
IMDS_IPV6_TOKEN_URL: Final = "http://[fd00:ec2::254]/latest/api/token"
# The IMDS safety check's first endpoint. Names under `.invalid` never
# resolve (RFC 6761 section 6.4), so a command that ignored HTTP_PROXY
# connects nowhere. botocore accepts the hostname (utils.py:1162-1165).
IMDS_SAFETY_ENDPOINT: Final = "http://imds-proxy-check.invalid/"
IMDS_SAFETY_TOKEN_URL: Final = f"{IMDS_SAFETY_ENDPOINT}latest/api/token"
# The STS safety check's first endpoint, which never resolves for the same
# reason; only the intercept proxy can answer it.
STS_SAFETY_ENDPOINT: Final = "https://sts-proxy-check.invalid"
# Environment keys the providers themselves set for a credential_process
# child. Env-dump assertions use these plus the keys the test set; the
# runtime's own extras (AWS_DATA_PATH, LC_CTYPE, PyInstaller's
# PYINSTALLER_RESET_ENVIRONMENT, ...) are not provider behavior.
PROVIDER_OWNED_ENV: Final = ("_AWS_CLI_PROFILE_CHAIN",)
# A launch prefix for a run's `launcher`: it starts the command with
# SIGPIPE, SIGXFSZ, and SIGHUP ignored.
TRAP_PIPE_XFSZ_HUP: Final = (
    "/bin/sh",
    "-c",
    "trap '' PIPE XFSZ HUP; exec \"$@\"",
    "sh",
)
SIGV4_ALGORITHM_PREFIX: Final = "AWS4-"
# botocore's SIGV4_TIMESTAMP (auth.py:58), the X-Amz-Date format.
AMZ_DATE_FORMAT: Final = "%Y%m%dT%H%M%SZ"
# What a current X-Amz-Date becomes in NormalizedRequest.headers, and the
# credential scope's date when it is that X-Amz-Date's day.
AMZ_DATE_PLACEHOLDER: Final = "<x-amz-date>"
SCOPE_DATE_PLACEHOLDER: Final = "<x-amz-date day>"
# botocore's default role session name, `botocore-session-<int(time())>`
# (credentials.py:817-820).
GENERATED_SESSION_NAME: Final = re.compile(
    rb"(RoleSessionName=botocore-session-)([0-9]+)"
)
SESSION_EPOCH_PLACEHOLDER: Final = b"<epoch>"
UNEXPECTED_REQUEST_BODY: Final = "unexpected request"
STS_NAMESPACE: Final = "https://sts.amazonaws.com/doc/2011-06-15/"
SSO_TOKEN_CACHE: Final = Path(".aws/sso/cache")
LOGIN_TOKEN_CACHE: Final = Path(".aws/login/cache")
CLI_CACHE: Final = Path(".aws/cli/cache")
# botocore's JSONFileCache creates cache files 0600 (utils.py:3991-4006).
# Windows reports any writable file as 0o666: it has no mode bits.
CACHE_FILE_MODE: Final = 0o600 if os.name == "posix" else 0o666
# The mode a plain open() (0o666) gives a file a helper writes, under the
# runner's umask.
CREATED_FILE_MODE: Final = 0o666 & ~_runner_umask()
# The role cache's directories under the sandbox root, outermost first,
# which JSONFileCache creates with os.makedirs on its first write
# (utils.py:4000-4001).
CLI_CACHE_DIRECTORIES: Final = (
    "home/.aws",
    "home/.aws/cli",
    f"home/{CLI_CACHE.as_posix()}",
)
DPOP_MAX_AGE_SECONDS: Final = 300
P256_COORDINATE_BYTES: Final = 32
SAFETY_ROLE_ARN: Final = "arn:aws:iam::123456789012:role/proxy-safety"
SAFETY_TIMEOUT_SECONDS: Final = 20.0
TEST_COMMAND_ENV_VAR: Final = "AWS_TEST_COMMAND"
# The telemetry database upstream keeps in HOME's CLI_CACHE, with its WAL
# and rollback-journal companions (awscli/telemetry.py:35-36, 84-91).
TELEMETRY_DB_NAMES: Final = frozenset(
    {"session.db", "session.db-wal", "session.db-shm", "session.db-journal"}
)
# The public SEC1 test key of upstream tests/unit/botocore/
# test_credentials.py:65-71 (SAMPLE_SIGN_IN_DPOP_PEM), never a real key.
SAMPLE_DPOP_PEM: Final = (
    "-----BEGIN EC PRIVATE KEY-----\n"
    "MHcCAQEEIDXxfh2F6vl+AX+tK/jvY5ll6aZ9n8sI2ODsWCmrsxSDoAoGCCqGSM49\n"
    "AwEHoUQDQgAERKnl1X15pEx7ebbMQ0dFw6VeOuCjEuh3NT8dwnBHYyF/7YDy8+Fu\n"
    "Cx+4wgiSs9sRD3LaDKCjIbbmEq07Jw59YQ==\n"
    "-----END EC PRIVATE KEY-----\n"
)


@dataclass(frozen=True)
class Unreadable:
    """Snapshot value of an entry the harness may not read or list."""

    def __repr__(self) -> str:
        return "UNREADABLE"


UNREADABLE: Final = Unreadable()


@dataclass(frozen=True)
class SymlinkTarget:
    """Snapshot value of a symbolic link: where it points, unresolved."""

    target: str


# Matchers stand in for an expected value inside a compared tuple or dict:
# `bytes == matcher` and `int == matcher` fall back to the matcher's
# __eq__, so `run.changes == {path: (CACHE_FILE_MODE, JsonContent(...))}`
# reads like an exact comparison.


@dataclass(frozen=True, eq=False)
class CreatedDirectoryMode:
    """Matches the mode of a directory the CLI creates for a cache.

    Upstream's os.makedirs gives 0o777 under the umask (utils.py:
    4000-4001). Any mode the owner can use that grants nothing beyond
    that matches, so a stricter 0o700 passes.
    """

    umask: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, int):
            return NotImplemented
        allowed = 0o777 & ~self.umask
        return other & 0o700 == 0o700 and other & ~allowed == 0

    def __repr__(self) -> str:
        return f"<0o700 up to {0o777 & ~self.umask:#o}>"


CREATED_DIRECTORY_MODE: Final = CreatedDirectoryMode(_runner_umask())


def _parse_json(content: object) -> tuple[bool, object]:
    """(True, value) when `content` is bytes holding one JSON document."""
    if not isinstance(content, bytes):
        return False, None
    try:
        return True, json.loads(content)
    except ValueError:
        return False, None


@dataclass(frozen=True, eq=False)
class JsonContent:
    """Matches file bytes that parse to `document`.

    Separators, key order, and string escapes are the writer's choice;
    another SDK reading the file sees only the parsed value.
    """

    document: object

    def __eq__(self, other: object) -> bool:
        if isinstance(other, JsonContent):
            return self.document == other.document
        if not isinstance(other, bytes):
            return NotImplemented
        parsed, value = _parse_json(other)
        return parsed and value == self.document


# The Credentials members botocore reads back from a role-cache entry
# (credentials.py:759-766, 785-788). AssumedRoleUser, ResponseMetadata,
# and ProviderType are written but never read, so they are no contract.
ROLE_CACHE_CREDENTIAL_KEYS: Final = (
    "AccessKeyId",
    "SecretAccessKey",
    "SessionToken",
    "Expiration",
    "AccountId",
)


def _role_cache_view(document: object) -> object:
    """The read-back part of a role-cache document, or the document."""
    if not isinstance(document, dict):
        return document
    credentials = document.get("Credentials")
    if not isinstance(credentials, dict):
        return {"Credentials": credentials}
    return {
        "Credentials": {
            key: credentials[key]
            for key in ROLE_CACHE_CREDENTIAL_KEYS
            if key in credentials
        }
    }


@dataclass(frozen=True, eq=False)
class RoleCacheContent:
    """Matches a `~/.aws/cli/cache` entry by the members botocore reads.

    `document` is the expected entry; only its Credentials members in
    ROLE_CACHE_CREDENTIAL_KEYS, and those of the file, are compared.
    """

    document: object

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RoleCacheContent):
            return _role_cache_view(self.document) == _role_cache_view(
                other.document
            )
        if not isinstance(other, bytes):
            return NotImplemented
        parsed, value = _parse_json(other)
        return parsed and _role_cache_view(value) == _role_cache_view(
            self.document
        )


@dataclass(frozen=True, eq=False)
class BytesStartingWith:
    """Matches bytes that start with `prefix` and contain each `part`.

    For an error whose tail is CPython's or the C library's wording (an
    OSError's `[Errno N] ...`, a decoder message): assert the AWS-authored
    prefix and the operands a user needs, such as the path.
    """

    prefix: bytes
    parts: tuple[bytes, ...] = ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, bytes):
            return NotImplemented
        return other.startswith(self.prefix) and all(
            part in other for part in self.parts
        )


def os_error_path(path: Path | str) -> bytes:
    """`path` as an OSError message names it: quoted, as its repr.

    The repr doubles each backslash of a Windows path.
    """
    return repr(os.fspath(path)).encode()


TreeEntry = tuple[int, bytes | object | None]
Tree = dict[str, TreeEntry]
# A run's file changes: the new entry of every path it created or changed,
# None for every path it removed.
FileChanges = dict[str, TreeEntry | None]
RouteKey = tuple[str, str, str]
# The (server, proxy) pair a `stub` fixture yields.
Stub = tuple[AsyncHTTPTestServer, AsyncTLSInterceptProxy]
Handler = Callable[[ResponderContext], ResponseSpec]
HandlerFactory = Callable[[], Handler]


@dataclass(frozen=True)
class NormalizedRequest:
    """The parts of one recorded request a test asserts on.

    `target` is the raw request-target, so origin form and the absolute
    form of a proxied request differ. `body_bytes` is the body as sent,
    except for botocore's generated role session name, whose epoch
    becomes SESSION_EPOCH_PLACEHOLDER. Equality compares `body`, its
    decoded form, so form parameter order, percent-encoding choices, and
    JSON formatting are the sender's; Content-Type compares by media type
    alone. `headers` pairs every compared header name with its value,
    None when absent. `signing_scope` is (access key, date, region,
    service) of a SigV4 Authorization, None for an unsigned request.

    `TokenCode` keeps no placeholder: the typed MFA code and its exact
    encoding (`123456++` for trailing spaces, `%0D` for a kept CR) are what
    the MFA tests assert. A DPoP proof travels only in the `DPoP` header,
    which `assert_dpop` checks on the raw request.
    """

    method: str
    host: str
    path: str
    target: str
    query: tuple[tuple[str, str], ...]
    content_type: str | None
    body_bytes: bytes = field(compare=False)
    headers: tuple[tuple[str, str | None], ...]
    user_agent: str | None
    signing_scope: tuple[str, ...] | None
    # `body_bytes` decoded by `decode_body`.
    body: object = field(init=False)

    def __post_init__(self) -> None:
        media_type = _media_type(self.content_type)
        object.__setattr__(self, "content_type", media_type)
        object.__setattr__(
            self,
            "headers",
            tuple(
                (name, _media_type(value) if name == "content-type" else value)
                for name, value in self.headers
            ),
        )
        object.__setattr__(
            self, "body", decode_body(self.body_bytes, media_type)
        )

    def describe(self) -> str:
        lines = [
            f"{self.method} {self.target} host={self.host}",
            f"    headers: {dict(self.headers)}",
            f"    body: {self.body_bytes!r}",
        ]
        if self.user_agent is not None:
            lines.append(f"    user-agent: {self.user_agent}")
        if self.signing_scope is not None:
            lines.append(f"    signing scope: {self.signing_scope}")
        return "\n".join(lines)


def signing_scope(request: RecordedHTTPRequest) -> tuple[str, ...]:
    """(access key, date, region, service) of a SigV4 Authorization.

    A SigV4 header without a well-formed credential scope comes back
    whole, as a one-element tuple, so a malformed header fails the
    assertion that reads it rather than the harness.
    """
    authorization = request.headers.get("authorization") or ""
    algorithm, _, fields = authorization.partition(" ")
    if not algorithm.startswith(SIGV4_ALGORITHM_PREFIX):
        raise ValueError(f"not a SigV4 Authorization: {authorization!r}")
    attributes = dict(
        part.strip().partition("=")[::2] for part in fields.split(",")
    )
    parts = tuple(attributes.get("Credential", "").split("/"))
    if len(parts) != 5 or parts[4] != "aws4_request":
        return (authorization,)
    return parts[:4]


def normalize_request(
    request: RecordedHTTPRequest,
    *,
    imds_hosts: Sequence[str] = (),
    compared_headers: Sequence[str] = COMPARED_HEADERS,
) -> NormalizedRequest:
    """Reduce a recorded request to what a test asserts on.

    Left out: amz-sdk-invocation-id, amz-sdk-request, Accept,
    Accept-Encoding, Content-Length, header order, the SigV4 signature and
    signed-header list, and User-Agent outside `imds_hosts` (none by
    default). An X-Amz-Date within TIME_TOLERANCE_SECONDS of now becomes
    AMZ_DATE_PLACEHOLDER, and a signing scope dated that X-Amz-Date's day
    gets SCOPE_DATE_PLACEHOLDER as its date; any other value is kept as
    sent. Pass extra names in `compared_headers` (amz-sdk-request with a
    fixed stub Date) or hosts in `imds_hosts` (IMDS_HOSTS, plus a
    configured IMDS endpoint) with functools.partial.
    """
    url = urlsplit(request.effective_path)
    host = request.headers.get("host", "")
    authorization = request.headers.get("authorization")
    signed = authorization is not None and authorization.startswith(
        SIGV4_ALGORITHM_PREFIX
    )
    return NormalizedRequest(
        method=request.method,
        host=host,
        path=url.path,
        target=request.target,
        query=tuple(sorted(parse_qsl(url.query, keep_blank_values=True))),
        content_type=request.headers.get("content-type"),
        body_bytes=GENERATED_SESSION_NAME.sub(
            _session_name_placeholder, request.body or b""
        ),
        headers=tuple(
            (name, compared_header(request, name)) for name in compared_headers
        ),
        user_agent=(
            request.headers.get("user-agent") if host in imds_hosts else None
        ),
        signing_scope=_dated_scope(request) if signed else None,
    )


def _session_name_placeholder(match: re.Match[bytes]) -> bytes:
    """`botocore-session-<epoch>` for a current epoch, else the match.

    An epoch far from now is not botocore's generated name, so it stays
    and is asserted exactly.
    """
    if abs(int(match[2]) - time.time()) > TIME_TOLERANCE_SECONDS:
        return match[0]
    return match[1] + SESSION_EPOCH_PLACEHOLDER


def _current_amz_date(request: RecordedHTTPRequest) -> str | None:
    """The request's X-Amz-Date if it is one well-formed, current value."""
    values = request.headers.get_all("x-amz-date")
    if values is None or len(values) != 1:
        return None
    try:
        moment = datetime.strptime(values[0], AMZ_DATE_FORMAT)
    except ValueError:
        return None
    offset = moment.replace(tzinfo=UTC).timestamp() - time.time()
    if abs(offset) > TIME_TOLERANCE_SECONDS:
        return None
    return values[0]


def _dated_scope(request: RecordedHTTPRequest) -> tuple[str, ...]:
    """`signing_scope` with its date masked when it is X-Amz-Date's day."""
    scope = signing_scope(request)
    amz_date = _current_amz_date(request)
    if len(scope) != 4 or amz_date is None or scope[1] != amz_date[:8]:
        return scope
    return (scope[0], SCOPE_DATE_PLACEHOLDER, *scope[2:])


def compared_header(request: RecordedHTTPRequest, name: str) -> str | None:
    """A header's value as recorded: None when absent, repeats joined."""
    values = request.headers.get_all(name)
    if values is None:
        return None
    value = ", ".join(values)
    if name == "authorization" and value.startswith(SIGV4_ALGORITHM_PREFIX):
        return value.split(" ", 1)[0]
    if name == "x-amz-date" and _current_amz_date(request) is not None:
        return AMZ_DATE_PLACEHOLDER
    return value


def _media_type(content_type: str | None) -> str | None:
    """A Content-Type's media type, lowercased, without parameters."""
    if content_type is None:
        return None
    return content_type.split(";", 1)[0].strip().lower()


def decode_body(body: bytes, content_type: str | None) -> object:
    """Form bodies as parse_qs, JSON bodies as values, else the bytes.

    Undecodable form bytes stay distinct as surrogate escapes.
    """
    if not body:
        return None
    media_type = _media_type(content_type) or ""
    if media_type == "application/x-www-form-urlencoded":
        return parse_qs(
            body.decode("utf-8", "surrogateescape"),
            keep_blank_values=True,
            errors="surrogateescape",
        )
    if media_type.endswith("json"):
        try:
            return json.loads(body)
        except ValueError:
            return body
    return body


def expected_request(
    method: str,
    host: str,
    target: str,
    *,
    body: bytes = b"",
    headers: Mapping[str, str] | None = None,
    signing_scope: tuple[str, ...] | None = None,
) -> NormalizedRequest:
    """A NormalizedRequest literal; unnamed compared headers are absent.

    `target` is the request-target as sent, its path and query split out
    as normalize_request splits them. The Content-Type is the one in
    `headers`, and no User-Agent is recorded.
    """
    sent = dict(headers or {})
    url = urlsplit(target)
    return NormalizedRequest(
        method=method,
        host=host,
        path=url.path,
        target=target,
        query=tuple(sorted(parse_qsl(url.query, keep_blank_values=True))),
        content_type=sent.get("content-type"),
        body_bytes=body,
        headers=tuple((name, sent.get(name)) for name in COMPARED_HEADERS),
        user_agent=None,
        signing_scope=signing_scope,
    )


class Sandbox:
    """Provider files and HOME under one root, and what a run changed.

    Write the fixtures, then run the CLI with `run_export_credentials` or
    `run_aws`. The first run seals the sandbox unless the test called
    `seal()` itself, and every run reports in `CliRun.changes` how the
    tree differs from the sealed one, so a test asserts everything the
    command wrote.
    """

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "sandbox"
        self.home = self.root / "home"
        self._sealed: Tree | None = None
        self.home.mkdir(parents=True)
        for path in (self.config, self.credentials, self.boto):
            path.write_text("", encoding="utf-8")

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def credentials(self) -> Path:
        return self.root / "credentials"

    @property
    def boto(self) -> Path:
        return self.root / "boto"

    @property
    def sealed(self) -> Tree | None:
        """The tree `seal()` recorded, or None before it is called."""
        return self._sealed

    def write(
        self, relative: str, content: str | bytes, *, mode: int | None = None
    ) -> Path:
        """Write a file under the root, creating its parents."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        path.write_bytes(data)
        if mode is not None:
            path.chmod(mode)
        return path

    def helper(self, name: str, source: str) -> str:
        """Write a Python helper script; returns its shell-quoted command.

        Helpers and the logs they keep live in the sandbox, so what a
        helper writes during a run shows up in that run's changes.
        """
        script = self.write(name, source)
        return command_line([sys.executable, str(script)])

    def env(
        self,
        proxy: AsyncTLSInterceptProxy,
        *,
        max_attempts: str | None = "1",
    ) -> dict[str, str]:
        """The child environment a run starts from.

        Upstream's `cli_env` with the fake keys removed and every file
        provider pointed into the sandbox. HOME is the sandbox's, never the
        runner's, and AWS_CLI_SESSION_ID_DISABLED keeps the CLI from writing
        its telemetry session.db there.
        AWS_MAX_ATTEMPTS pins one attempt unless `max_attempts` is None
        (retry tests only). TZ and BOTO_EXPERIMENTAL__ADD_PROXY_HOST_HEADER
        are never passed.
        """
        env = cli_env(proxy)
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "TZ",
            "BOTO_EXPERIMENTAL__ADD_PROXY_HOST_HEADER",
        ):
            env.pop(key, None)
        env.update(
            AWS_CONFIG_FILE=str(self.config),
            AWS_SHARED_CREDENTIALS_FILE=str(self.credentials),
            BOTO_CONFIG=str(self.boto),
            AWS_EC2_METADATA_DISABLED="true",
            AWS_CLI_SESSION_ID_DISABLED="true",
            HOME=str(self.home),
        )
        if sys.platform == "win32":
            # Both routes resolve `~` from USERPROFILE first there.
            env["USERPROFILE"] = str(self.home)
        if max_attempts is None:
            env.pop("AWS_MAX_ATTEMPTS", None)
        else:
            env["AWS_MAX_ATTEMPTS"] = max_attempts
        return env

    def seal(self) -> None:
        """Record the current tree as the one `changes()` compares with."""
        self._sealed = self.snapshot()

    def changes(self, tree: Tree | None = None) -> FileChanges:
        """How `tree` (by default the tree now) differs from the sealed one.

        Maps every created or changed path to its new (mode, content) and
        every removed path to None; unchanged paths are left out.
        """
        if self._sealed is None:
            raise RuntimeError("seal() the sandbox after writing its fixtures")
        return tree_changes(
            self._sealed, self.snapshot() if tree is None else tree
        )

    def snapshot(self) -> Tree:
        """Every entry under the root: (mode, bytes | None | marker).

        Directories map to None, symbolic links to SymlinkTarget, and an
        entry the harness may not read or list to UNREADABLE. The
        telemetry database's own files are left out; an entry elsewhere
        with one of their names is not.
        """
        telemetry_dir = self.home / CLI_CACHE
        tree: Tree = {}
        pending = [self.root]
        while pending:
            directory = pending.pop()
            for path in sorted(directory.iterdir()):
                if directory == telemetry_dir and _is_telemetry_db(path):
                    continue
                relative = path.relative_to(self.root).as_posix()
                tree[relative] = _snapshot_entry(path, pending)
        return dict(sorted(tree.items()))


def tree_changes(before: Tree, after: Tree) -> FileChanges:
    """Entries `after` added or changed, and None for each it removed."""
    changes: FileChanges = {
        path: entry
        for path, entry in after.items()
        if before.get(path) != entry
    }
    changes.update({path: None for path in before if path not in after})
    return dict(sorted(changes.items()))


def _is_telemetry_db(path: Path) -> bool:
    """Whether `path` is a regular file named like a telemetry DB file."""
    return path.name in TELEMETRY_DB_NAMES and stat.S_ISREG(
        path.lstat().st_mode
    )


def _snapshot_entry(path: Path, pending: list[Path]) -> TreeEntry:
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return mode, SymlinkTarget(os.readlink(path))
    if stat.S_ISDIR(info.st_mode):
        if not os.access(path, os.R_OK | os.X_OK):
            return mode, UNREADABLE
        pending.append(path)
        return mode, None
    try:
        return mode, path.read_bytes()
    except PermissionError:
        return mode, UNREADABLE


@dataclass(frozen=True)
class CliRun:
    """One CLI run in a sandbox, and what it left behind."""

    returncode: int
    stdout: bytes
    stderr: bytes
    requests: tuple[NormalizedRequest, ...]
    # The whole sandbox after the run, and how it differs from the sealed
    # tree.
    tree: Tree
    changes: FileChanges
    argv: tuple[str, ...] = ()
    # The recorded requests behind `requests`, for checks that need the
    # wire (SigV4 signatures, DPoP proofs).
    raw_requests: tuple[RecordedHTTPRequest, ...] = field(
        default=(), repr=False
    )

    def describe(self) -> str:
        lines = [
            f"--- {shlex.join(self.argv)}",
            f"returncode: {self.returncode}",
            f"stdout: {self.stdout!r}",
            f"stderr: {self.stderr!r}",
            f"requests ({len(self.requests)}):",
        ]
        lines.extend(
            f"  [{index}] {request.describe()}"
            for index, request in enumerate(self.requests)
        )
        lines.append(f"changes ({len(self.changes)}):")
        lines.extend(
            f"  {path} removed"
            if entry is None
            else f"  {path} {entry[0]:#o} {_describe_content(entry[1])}"
            for path, entry in self.changes.items()
        )
        return "\n".join(lines) + "\n"


def _describe_content(content: object) -> str:
    if isinstance(content, bytes):
        return f"{len(content)} bytes {content[:200]!r}"
    if content is None:
        return "directory"
    return repr(content)


class CommandTimeoutError(AssertionError):
    """A command outlived its deadline and was killed with its group."""


async def run_command(
    command: Sequence[str],
    env: Mapping[str, str],
    *,
    cwd: Path,
    stdin: bytes | None = b"",
    launcher: Sequence[str] = (),
    pass_fds: Sequence[int] = (),
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> tuple[bytes, bytes, int]:
    """Run one command: (stdout, stderr, returncode).

    The child gets its own session, so it never shares the developer's
    terminal, and a pipe carrying `stdin` as fd 0. `stdin=None` gives it
    /dev/null instead. `pass_fds` are
    inherited in addition to fds 0-2. On timeout the whole process group
    is killed and CommandTimeoutError raised; Windows has no process
    groups, so there only the child is killed. The child gets the
    harness's Windows plumbing and its output LF line endings, as
    `run_cli` gives them.
    """
    argv = [*launcher, *command]
    process = await asyncio.create_subprocess_exec(
        *argv,
        env=child_environment(env),
        cwd=cwd,
        stdin=(
            asyncio.subprocess.DEVNULL
            if stdin is None
            else asyncio.subprocess.PIPE
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
        pass_fds=tuple(pass_fds),
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(stdin), timeout
        )
    except TimeoutError:
        if os.name == "posix":
            kill_process_group(process.pid)
        else:
            process.kill()
        await process.wait()
        raise CommandTimeoutError(
            f"{shlex.join(argv)} did not exit within {timeout} s"
        ) from None
    assert process.returncode is not None
    stdout, stderr = fold_newlines(argv, stdout, stderr)
    return stdout, stderr, process.returncode


def kill_process_group(pid: int) -> None:
    """SIGKILL the session `pid` leads, ignoring one that already ended."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, signal.SIGKILL)


def export_credentials_output(
    access_key: str,
    secret_key: str,
    session_token: str | None = None,
    expiration: str | None = None,
) -> bytes:
    """The `--format process` stdout for these credentials.

    Indented JSON plus a newline, with SessionToken and Expiration
    (already isoformat()) only when set (awscli/customizations/configure/
    exportcreds.py:140-153).
    """
    output: dict[str, object] = {
        "Version": 1,
        "AccessKeyId": access_key,
        "SecretAccessKey": secret_key,
    }
    if session_token is not None:
        output["SessionToken"] = session_token
    if expiration is not None:
        output["Expiration"] = expiration
    text = json.dumps(output, indent=2, separators=(",", ": "))
    return (text + "\n").encode()


def export_credentials_command(
    aws_cli: str,
    *,
    globals_: Sequence[str] = (),
    cmd_args: Sequence[str] = (),
) -> list[str]:
    """`aws <globals> configure export-credentials <args>`."""
    return [aws_cli, *globals_, *EXPORT_CREDENTIALS, *cmd_args]


async def run_aws(
    aws_cli: str,
    args: Sequence[str],
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    env: Mapping[str, str],
    *,
    stdin: bytes | None = b"",
    cwd: Path | None = None,
    launcher: Sequence[str] = (),
    pass_fds: Sequence[int] = (),
    normalize: Callable[
        [RecordedHTTPRequest], NormalizedRequest
    ] = normalize_request,
    handlers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> CliRun:
    """Run `aws <args>` once in `sandbox` and record what it did.

    Seals the sandbox first unless the test already did. Before the run
    every server's recording is cleared and each `handlers` factory
    installs a fresh handler on its server, since clearing does not
    rewind a handler's own state; a later run in the same test therefore
    starts its scripts over. `cwd` defaults to the sandbox root, never the
    runner's aws-cli/ directory. `env` is passed as given, so the router
    mode is the runner's. Requests are normalized per server, in `servers`
    order, then in arrival order.
    """
    start_run(sandbox, servers, handlers)
    command = [aws_cli, *args]
    stdout, stderr, returncode = await run_command(
        command,
        env,
        cwd=sandbox.root if cwd is None else cwd,
        stdin=stdin,
        launcher=launcher,
        pass_fds=pass_fds,
        timeout=timeout,
    )
    return finish_run(
        sandbox,
        servers,
        argv=(*launcher, *command),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        normalize=normalize,
    )


def start_run(
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    handlers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
) -> None:
    """Prepare a run the test launches itself, as `run_aws` prepares one.

    Seals the sandbox unless the test already did, clears every server's
    recording, and installs a fresh handler from each `handlers` factory.
    Launch the command, then build its CliRun with `finish_run`.
    """
    factories = dict(handlers or {})
    if any(server not in servers for server in factories):
        raise ValueError("handlers names a server that is not in servers")
    if sandbox.sealed is None:
        sandbox.seal()
    for server in servers:
        server.clear_requests()
        factory = factories.get(server)
        if factory is not None:
            server.handler = factory()


def finish_run(
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    *,
    argv: Sequence[str],
    returncode: int,
    stdout: bytes,
    stderr: bytes,
    normalize: Callable[
        [RecordedHTTPRequest], NormalizedRequest
    ] = normalize_request,
) -> CliRun:
    """The CliRun of a finished run that `start_run` prepared.

    Requests are normalized per server, in `servers` order, then in
    arrival order, and the changes are the sandbox's since it was sealed.
    """
    raw = tuple(request for server in servers for request in server.requests)
    tree = sandbox.snapshot()
    return CliRun(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        requests=tuple(normalize(request) for request in raw),
        tree=tree,
        changes=sandbox.changes(tree),
        argv=tuple(argv),
        raw_requests=raw,
    )


async def run_export_credentials(
    aws_cli: str,
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    env: Mapping[str, str],
    *,
    globals_: Sequence[str] = (),
    cmd_args: Sequence[str] = (),
    stdin: bytes | None = b"",
    cwd: Path | None = None,
    launcher: Sequence[str] = (),
    pass_fds: Sequence[int] = (),
    normalize: Callable[
        [RecordedHTTPRequest], NormalizedRequest
    ] = normalize_request,
    handlers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> CliRun:
    """`run_aws` with `<globals> configure export-credentials <args>`."""
    return await run_aws(
        aws_cli,
        [*globals_, *EXPORT_CREDENTIALS, *cmd_args],
        sandbox,
        servers,
        env,
        stdin=stdin,
        cwd=cwd,
        launcher=launcher,
        pass_fds=pass_fds,
        normalize=normalize,
        handlers=handlers,
        timeout=timeout,
    )


# The bucket `run_s3_ls` lists, and the virtual-hosted name its listing
# request reaches through the TLS intercept proxy.
LISTED_BUCKET: Final = "credential-parity"
LISTED_BUCKET_HOST: Final = f"{LISTED_BUCKET}.s3.us-east-1.amazonaws.com"


def is_s3_request(request: RecordedHTTPRequest | NormalizedRequest) -> bool:
    """Whether `request` is a listing request `run_s3_ls` made to S3."""
    if isinstance(request, NormalizedRequest):
        return request.host == LISTED_BUCKET_HOST
    return request.headers.get("host") == LISTED_BUCKET_HOST


def _answering_listing(inner: HandlerFactory | None) -> HandlerFactory:
    """`inner`, or the 400 tripwire, with S3 listings answered empty."""

    def factory() -> Handler:
        delegate = inner() if inner is not None else None

        def handler(context: ResponderContext) -> ResponseSpec:
            if is_s3_request(context.request):
                return empty_list_objects_response()
            if delegate is None:
                return unexpected_request()
            return delegate(context)

        return handler

    return factory


async def run_s3_ls(
    aws_cli: str,
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    env: Mapping[str, str],
    *,
    s3: AsyncHTTPTestServer,
    globals_: Sequence[str] = (),
    cwd: Path | None = None,
    handlers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
) -> CliRun:
    """`run_aws` with `<globals> s3 ls s3://LISTED_BUCKET/`.

    `s3`, the server behind the TLS intercept proxy, answers the listing
    with an empty bucket and anything else with its `handlers` entry, or
    the tripwire. AWS_MAX_ATTEMPTS is dropped: native declines a single
    attempt as a retry setting, so with it the listing would always run
    on Python and never exercise the CRT providers.
    """
    if s3 not in servers:
        raise ValueError("s3 is not in servers")
    factories = dict(handlers or {})
    factories[s3] = _answering_listing(factories.get(s3))
    run_env = {k: v for k, v in env.items() if k != "AWS_MAX_ATTEMPTS"}
    return await run_aws(
        aws_cli,
        [*globals_, "s3", "ls", f"s3://{LISTED_BUCKET}/"],
        sandbox,
        servers,
        run_env,
        cwd=cwd,
        handlers=factories,
    )


def without_s3(run: CliRun) -> CliRun:
    """`run` with its S3 listing requests left out: the provider's own."""
    kept = [
        (request, raw)
        for request, raw in zip(run.requests, run.raw_requests, strict=True)
        if not is_s3_request(raw)
    ]
    return replace(
        run,
        requests=tuple(request for request, _ in kept),
        raw_requests=tuple(raw for _, raw in kept),
    )


def _header_text(request: RecordedHTTPRequest, name: str) -> str | None:
    """Header `name` as the UTF-8 the client wrote.

    localstub decodes header bytes as Latin-1; re-encoding recovers them
    losslessly, so a non-ASCII key compares against the text exported.
    """
    value = request.headers.get(name)
    if value is None:
        return None
    return value.encode("latin-1").decode("utf-8", "surrogateescape")


def signed_access_key(request: RecordedHTTPRequest) -> str | None:
    """The access key in a SigV4 Authorization's credential scope.

    Read up to the scope's four trailing `/` fields, so a key holding a
    comma or a colon, as some process-helper keys do, comes back whole.
    """
    authorization = _header_text(request, "authorization") or ""
    _, found, rest = authorization.partition("Credential=")
    if not found:
        return None
    credential = rest.split(", SignedHeaders=", 1)[0]
    return credential.rsplit("/", 4)[0]


def assert_signed_with(
    run: CliRun, access_key: str, token: str | None
) -> None:
    """Every S3 request carries `access_key` and `token`, and one was made.

    The token is the X-Amz-Security-Token header, None when absent.
    """
    signed = [
        (
            signed_access_key(raw),
            _header_text(raw, "x-amz-security-token"),
        )
        for raw in run.raw_requests
        if is_s3_request(raw)
    ]
    assert signed, run.describe()
    assert signed == [(access_key, token)] * len(signed), run.describe()


def assert_signed_as_exported(run: CliRun, exported: bytes) -> None:
    """The S3 listing carries the access key and token `exported` holds.

    `exported` is the export-credentials JSON the same setup prints. An
    empty exported token sends no header: SigV4Auth adds it only when
    truthy (botocore/auth.py:458-461).
    """
    document = json.loads(exported)
    assert_signed_with(
        run, document["AccessKeyId"], document.get("SessionToken") or None
    )


def successes(
    rows: Sequence["ParameterSet"], index: int = -1
) -> list["ParameterSet"]:
    """The rows whose outcome, the value at `index`, has returncode 0."""
    return [row for row in rows if row.values[index].returncode == 0]


def route_key(request: RecordedHTTPRequest) -> RouteKey:
    """(method, Host, path without query) of a request, as `routed` keys."""
    path = urlsplit(request.effective_path).path
    return request.method, request.headers.get("host", ""), path


def unexpected_request() -> HTTPResponse:
    """The tripwire for any request a script did not plan for."""
    return HTTPResponse.text(UNEXPECTED_REQUEST_BODY, status=400)


def routed(script: Mapping[RouteKey, Sequence[ResponseSpec]]) -> Handler:
    """A handler serving each route's responses in order, then a 400.

    Routing by (method, Host, path) makes a change in call order a visible
    failure instead of crossing a shared response sequence. The handler
    consumes its script, so pass a factory, `lambda: routed(script)`,
    through `handlers=`; every run installs a fresh one. It is not
    consulted while a response sequence is set on the same server.
    """
    queues = {key: list(responses) for key, responses in script.items()}

    def handler(context: ResponderContext) -> ResponseSpec:
        queue = queues.get(route_key(context.request))
        if not queue:
            return unexpected_request()
        return queue.pop(0)

    return handler


def sts_success_xml(
    *,
    action: str = "AssumeRole",
    access_key: str = "AKIDROLE",
    secret_key: str = "ROLE-secret",
    session_token: str = "ROLE-token",
    expiration: str = "2099-01-01T00:00:00Z",
    assumed_role_id: str = "AROA:s",
    arn: str = "arn:aws:sts::123456789012:assumed-role/r/s",
    request_id: str = "r",
    headers: Mapping[str, str] | None = None,
) -> HTTPResponse:
    """An STS `<action>Response` with credentials and the assumed role.

    The AssumedRoleUser ARN's account becomes Credentials.AccountId in
    the role cache. Content-Type is text/xml and nothing else is sent
    unless `headers` adds it (a fixed Date, for instance), so the cached
    ResponseMetadata.HTTPHeaders is deterministic.
    """
    body = (
        f'<{action}Response xmlns="{STS_NAMESPACE}"><{action}Result>'
        "<Credentials>"
        f"<AccessKeyId>{escape(access_key)}</AccessKeyId>"
        f"<SecretAccessKey>{escape(secret_key)}</SecretAccessKey>"
        f"<SessionToken>{escape(session_token)}</SessionToken>"
        f"<Expiration>{escape(expiration)}</Expiration>"
        "</Credentials><AssumedRoleUser>"
        f"<AssumedRoleId>{escape(assumed_role_id)}</AssumedRoleId>"
        f"<Arn>{escape(arn)}</Arn>"
        f"</AssumedRoleUser></{action}Result><ResponseMetadata>"
        f"<RequestId>{escape(request_id)}</RequestId>"
        f"</ResponseMetadata></{action}Response>"
    )
    return HTTPResponse.raw(
        body.encode(),
        headers={"Content-Type": "text/xml", **(headers or {})},
    )


def sts_error_xml(
    code: str = "AccessDenied",
    message: str = "stubbed STS rejection",
    *,
    status: int = 403,
    error_type: str = "Sender",
    request_id: str = "r",
    headers: Mapping[str, str] | None = None,
) -> HTTPResponse:
    """An STS ErrorResponse. Not retried for a 4xx non-throttling code."""
    body = (
        f'<ErrorResponse xmlns="{STS_NAMESPACE}"><Error>'
        f"<Type>{escape(error_type)}</Type><Code>{escape(code)}</Code>"
        f"<Message>{escape(message)}</Message></Error>"
        f"<RequestId>{escape(request_id)}</RequestId></ErrorResponse>"
    )
    return HTTPResponse.raw(
        body.encode(),
        status=status,
        headers={"Content-Type": "text/xml", **(headers or {})},
    )


def sso_role_credentials(
    *,
    access_key: str = "AKIDSSO",
    secret_key: str = "SSOSECRET",
    session_token: str = "SSOTOKEN",
    expiration: int = 4070908800000,
) -> HTTPResponse:
    """A GetRoleCredentials response; `expiration` is epoch milliseconds."""
    return HTTPResponse.json(
        {
            "roleCredentials": {
                "accessKeyId": access_key,
                "secretAccessKey": secret_key,
                "sessionToken": session_token,
                "expiration": expiration,
            }
        }
    )


def oidc_token(
    *,
    access_token: str = "NEW-ACCESS",
    token_type: str = "Bearer",
    expires_in: int = 3600,
    refresh_token: str | None = "NEW-REFRESH",
) -> HTTPResponse:
    """An SSO-OIDC CreateToken response; refresh_token=None omits it."""
    body: dict[str, object] = {
        "accessToken": access_token,
        "tokenType": token_type,
        "expiresIn": expires_in,
    }
    if refresh_token is not None:
        body["refreshToken"] = refresh_token
    return HTTPResponse.json(body)


def signin_token(
    *,
    access_key: str = "AKIDNEW",
    secret_key: str = "NEW-secret",
    session_token: str = "NEW-token",
    token_type: str = "aws_sigv4",
    expires_in: int = 900,
    refresh_token: str | None = "new-refresh-token",
) -> HTTPResponse:
    """A signin CreateOAuth2Token response (the tokenOutput payload)."""
    body: dict[str, object] = {
        "accessToken": {
            "accessKeyId": access_key,
            "secretAccessKey": secret_key,
            "sessionToken": session_token,
        },
        "tokenType": token_type,
        "expiresIn": expires_in,
    }
    if refresh_token is not None:
        body["refreshToken"] = refresh_token
    return HTTPResponse.json(body)


def write_json_file(path: Path, value: object, *, mode: int) -> Path:
    """`json.dumps(value)` at `path` with `mode` (utils.py:3967-3968).

    Missing parent directories are created with the default mode, as
    botocore's os.makedirs does.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(mode)
    return path


def write_sso_token(
    home: Path, key: str, *, mode: int = CACHE_FILE_MODE, **fields: object
) -> Path:
    """Seed `~/.aws/sso/cache/<sha1(key)>.json` with `fields`, in order.

    `key` is the sso-session name, or the start URL for a legacy profile
    (botocore utils.py:3809-3813).
    """
    name = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return write_json_file(
        home / SSO_TOKEN_CACHE / f"{name}.json", fields, mode=mode
    )


def write_login_token(
    directory: Path,
    name: str,
    *,
    mode: int = CACHE_FILE_MODE,
    **fields: object,
) -> Path:
    """Seed `<directory>/<sha256(name)>.json`, `name` the login_session.

    botocore utils.py:4051-4052 keys the file by the raw session name.
    """
    key = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return write_json_file(directory / f"{key}.json", fields, mode=mode)


def seed_cli_cache(
    home: Path, key: str, value: object, *, mode: int = CACHE_FILE_MODE
) -> Path:
    """Seed `~/.aws/cli/cache/<key>.json`, the role-credential cache."""
    return write_json_file(home / CLI_CACHE / f"{key}.json", value, mode=mode)


def created_cache_directories(existing: Container[str] = ()) -> FileChanges:
    """The role-cache directories a first cache write creates.

    Every one of CLI_CACHE_DIRECTORIES that `existing` (a sealed tree, for
    instance) lacks, as a new directory with CREATED_DIRECTORY_MODE.
    """
    return {
        path: (CREATED_DIRECTORY_MODE, None)
        for path in CLI_CACHE_DIRECTORIES
        if path not in existing
    }


def role_cache_key(args: Mapping[str, object]) -> str:
    """The assume-role cache key for `args` (credentials.py:830-850).

    Pass the AssumeRole arguments botocore keys by: RoleArn, and
    RoleSessionName unless generated, plus any of SerialNumber,
    ExternalId, DurationSeconds, and Policy (parsed) that are set.
    """
    text = json.dumps(dict(args), sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sso_role_cache_key(args: Mapping[str, object]) -> str:
    """The SSO role-credential cache key (credentials.py:2287-2307).

    `args` holds roleName and accountId plus sessionName, or startUrl for
    a legacy profile; the JSON is compact.
    """
    text = json.dumps(dict(args), sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def cache_tree_normalizer(
    tree: Mapping[str, TreeEntry | None],
    *,
    expires_in: Sequence[int] = (),
    now: float | None = None,
    tolerance: float = TIME_TOLERANCE_SECONDS,
) -> FileChanges:
    """`tree` (or a run's changes) with refreshed token expiries masked.

    A `.json` entry that parses becomes a JsonContent of its value with
    every `expiresAt` within `tolerance` of `now + s`, for an `s` in
    `expires_in`, replaced by `<now+<s>s>` (a refreshed token's
    `now + expiresIn`). Anything else is kept byte for byte.
    """
    current = time.time() if now is None else now

    def normalize(value: object) -> object:
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if not isinstance(value, dict):
            return value
        result: dict[str, object] = {}
        for key, item in value.items():
            if key == "expiresAt" and isinstance(item, str):
                result[key] = _expiry_placeholder(
                    item, expires_in, current, tolerance
                )
            else:
                result[key] = normalize(item)
        return result

    normalized: FileChanges = {}
    for path, entry in tree.items():
        if entry is None or not path.endswith(".json"):
            normalized[path] = entry
            continue
        parsed, document = _parse_json(entry[1])
        normalized[path] = (
            (entry[0], JsonContent(normalize(document))) if parsed else entry
        )
    return normalized


def _expiry_placeholder(
    value: str, expires_in: Sequence[int], now: float, tolerance: float
) -> str:
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    if moment.tzinfo is None:
        return value
    offset = moment.timestamp() - now
    for seconds in expires_in:
        if abs(offset - seconds) <= tolerance:
            return f"<now+{seconds}s>"
    return value


def b64url(data: bytes) -> str:
    """Unpadded base64url, as botocore utils.py:4208-4209 writes it."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def assert_dpop(proof: str, private_pem: str, url: str) -> None:
    """Verify a DPoP proof against the key in a login token's `dpopKey`.

    The structure botocore's `build_dpop_header` produces (utils.py:
    4212-4246): an unpadded compact JWS whose header names ES256 and the
    key's public JWK, whose claims are htm=POST, htu=`url`, a current
    integer iat, and a uuid4 jti, signed with raw r||s over the first two
    segments. The JSON is compared parsed, not byte for byte.
    """
    segments = proof.split(".")
    assert len(segments) == 3, f"DPoP proof is not a compact JWS: {proof!r}"
    assert "=" not in proof, f"DPoP proof is padded: {proof!r}"
    header = json.loads(_b64url_decode(segments[0]))
    claims = json.loads(_b64url_decode(segments[1]))
    signature = _b64url_decode(segments[2])
    key = serialization.load_pem_private_key(private_pem.encode(), None)
    assert isinstance(key, ec.EllipticCurvePrivateKey)
    numbers = key.public_key().public_numbers()
    assert header == {
        "typ": "dpop+jwt",
        "alg": "ES256",
        "jwk": {
            "kty": "EC",
            "x": b64url(numbers.x.to_bytes(P256_COORDINATE_BYTES, "big")),
            "y": b64url(numbers.y.to_bytes(P256_COORDINATE_BYTES, "big")),
            "crv": "P-256",
        },
    }
    assert isinstance(claims, dict), claims
    assert sorted(claims) == ["htm", "htu", "iat", "jti"], claims
    assert (claims["htm"], claims["htu"]) == ("POST", url)
    assert isinstance(claims["iat"], int), claims
    assert abs(claims["iat"] - time.time()) < DPOP_MAX_AGE_SECONDS, claims
    assert isinstance(claims["jti"], str), claims
    assert uuid.UUID(claims["jti"]).version == 4, claims
    assert len(signature) == 2 * P256_COORDINATE_BYTES, signature
    r = int.from_bytes(signature[:P256_COORDINATE_BYTES], "big")
    s = int.from_bytes(signature[P256_COORDINATE_BYTES:], "big")
    try:
        key.public_key().verify(
            encode_dss_signature(r, s),
            f"{segments[0]}.{segments[1]}".encode(),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature:
        raise AssertionError("DPoP signature does not verify") from None


async def reaches_sts_through_proxy(
    command: Sequence[str],
    workdir: Path,
    *,
    extra_env: Mapping[str, str] | None = None,
) -> bool:
    """Whether `command` sends a web-identity STS call via HTTPS_PROXY.

    Runs `command` (`aws configure export-credentials`) in a fresh sandbox
    under `workdir` whose default profile assumes a role with a web
    identity token (an unsigned STS call), behind the TLS intercept proxy.
    STS answers 403, so nothing is cached. The first run sets
    AWS_ENDPOINT_URL_STS to STS_SAFETY_ENDPOINT, which never resolves, so a
    command that ignored HTTPS_PROXY reaches no STS. Only once that call
    arrived does a second run check that the default STS endpoint is
    proxied too.
    """
    sandbox = Sandbox(workdir)
    token = sandbox.write("web-identity-token", "proxy-safety-token")
    sandbox.config.write_text(
        "[default]\n"
        f"role_arn = {SAFETY_ROLE_ARN}\n"
        f"web_identity_token_file = {token}\n"
        "role_session_name = proxy-safety\n",
        encoding="utf-8",
    )
    base_env = extra_env or {}
    if not await _sts_calls_proxied(
        command,
        sandbox,
        {**base_env, "AWS_ENDPOINT_URL_STS": STS_SAFETY_ENDPOINT},
    ):
        return False
    return await _sts_calls_proxied(command, sandbox, base_env)


async def _sts_calls_proxied(
    command: Sequence[str], sandbox: Sandbox, extra_env: Mapping[str, str]
) -> bool:
    """Whether one run sent any request through the TLS intercept proxy."""
    async with mock_server() as (server, proxy):
        server.set_default_response(sts_error_xml())
        env = {**sandbox.env(proxy), **extra_env}
        await run_command(
            command, env, cwd=sandbox.root, timeout=SAFETY_TIMEOUT_SECONDS
        )
        return bool(server.requests)


async def reaches_imds_through_proxy(
    command: Sequence[str],
    workdir: Path,
    *,
    extra_env: Mapping[str, str] | None = None,
) -> bool:
    """Whether `command` sends its IMDS token PUTs in absolute form.

    Runs `command` (`aws configure export-credentials`) with no other
    credentials, IMDS enabled, and HTTP_PROXY at a plain stub, which
    answers each token PUT with 400 so botocore stops there (utils.py:
    420-427, 576-578). The first run configures IMDS_SAFETY_ENDPOINT,
    which never resolves, so a command that ignored HTTP_PROXY reaches no
    IMDS. Only once that PUT arrived does a second run check that the
    default IPv4 link-local endpoint is proxied too, and only once that
    PUT arrived does a third run, with
    AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE=IPv6, check the IPv6 endpoint
    that the IPv6-mode IMDS rows send to. Reaching either real endpoint
    then takes a second, independent bug.
    """
    sandbox = Sandbox(workdir)
    base_env = extra_env or {}
    # Stage 1: an endpoint that never resolves, so a proxy bypass connects
    # nowhere.
    configured = await _imds_token_puts(
        command,
        sandbox,
        {
            **base_env,
            "AWS_EC2_METADATA_SERVICE_ENDPOINT": IMDS_SAFETY_ENDPOINT,
        },
    )
    if IMDS_SAFETY_TOKEN_URL not in configured:
        return False
    # Stage 2: the IPv4 default endpoint.
    if IMDS_TOKEN_URL not in await _imds_token_puts(
        command, sandbox, base_env
    ):
        return False
    # Stage 3: the IPv6 endpoint, which only the endpoint mode selects.
    return IMDS_IPV6_TOKEN_URL in await _imds_token_puts(
        command,
        sandbox,
        {**base_env, "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE": "IPv6"},
    )


async def _imds_token_puts(
    command: Sequence[str], sandbox: Sandbox, extra_env: Mapping[str, str]
) -> list[str]:
    """The request-targets of the PUTs one run sent through HTTP_PROXY."""
    async with (
        mock_server() as (_, proxy),
        AsyncHTTPTestServer() as metadata,
    ):
        metadata.set_default_response(unexpected_request())
        env = sandbox.env(proxy)
        env.update(extra_env)
        env.update(AWS_EC2_METADATA_DISABLED="false", HTTP_PROXY=metadata.url)
        await run_command(
            command, env, cwd=sandbox.root, timeout=SAFETY_TIMEOUT_SECONDS
        )
        return [
            request.target
            for request in metadata.requests
            if request.method == "PUT"
        ]
