"""Service-command blackbox runs: scripted parsed replies, decoded requests.

The ports of upstream's functional tests (`awscli.testutils`'
`BaseAWSCommandParamsTest`) run each command against the binary through
the TLS intercept proxy, in the environment that base class gives the CLI:
region us-east-1, its fake keys, a config file pinning the classic
transfer client, no shared credentials file, and one attempt per request,
as its patched endpoint answers each request once.

A test scripts the service's replies in parsed form, as upstream's
fixtures give them. `ApiSession` serializes each for the wire with the
botocore model of the operation its request decodes to (tests/awswire.py),
so the command parses the response the in-process test fed botocore, and
decodes every request back to its operation's parameters, the form
upstream's assertions compare. A reply given as an `HTTPResponse` goes to
the wire as it is, as upstream's `CLIRunner` tests queue theirs. Only the
CLI under test sees the wire.
"""

import functools
import traceback
from collections import deque
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from localstub import (
    AsyncHTTPTestServer,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponderContext,
)
from localstub.handlers import handle_expect_header

from awswire import AwsWireProtocol, create_aws_wire_protocol
from credhelpers import run_command
from tests.blackbox.utils import mock_server

REGION: Final = "us-east-1"
ACCESS_KEY: Final = "access_key"
SECRET_KEY: Final = "secret_key"
# Upstream's base class pins the classic transfer client; tests that need
# the CRT client configure it themselves.
CLASSIC_CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = classic\n"
)
# Its S3 transfer tests' base classes also run the classic client serially.
S3_TRANSFER_CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = classic\n"
    "  max_concurrent_requests = 1\n"
)
# The same transfers on the CRT client, which native runs as upstream's CRT
# client does, still one connection at a time.
CRT_TRANSFER_CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = crt\n"
    "  max_concurrent_requests = 1\n"
)


@dataclass(frozen=True)
class Reply:
    """One service response in parsed form.

    A `parsed` response with an `Error` that has a `Code` is the service's
    error, status 400 unless `status` says otherwise; any other is the
    operation's success, with its modeled status unless `status` says
    otherwise. `headers` override the serialized ones.
    """

    parsed: Mapping[str, Any] = field(default_factory=dict)
    status: int | None = None
    headers: Mapping[str, str] = field(default_factory=dict)


type ReplyLike = Reply | Mapping[str, Any] | HTTPResponse


@dataclass(frozen=True)
class Call:
    """One request the command sent, decoded to its operation."""

    operation: str
    params: dict[str, Any]
    request: RecordedHTTPRequest


@dataclass(frozen=True)
class CommandRun:
    """A finished command: its decoded output, status, and requests."""

    stdout: str
    stderr: str
    rc: int
    calls: tuple[Call, ...]

    @property
    def operations(self) -> list[str]:
        return [call.operation for call in self.calls]

    @property
    def operations_with_params(self) -> list[tuple[str, dict[str, Any]]]:
        """Each request's operation and parameters, the list upstream's
        `assert_operations_called` compares."""
        return [(call.operation, call.params) for call in self.calls]

    @property
    def last_params(self) -> dict[str, Any] | None:
        """The last request's parameters, upstream's `last_kwargs`."""
        return self.calls[-1].params if self.calls else None

    def describe(self) -> str:
        operations = ", ".join(self.operations) or "<none>"
        return (
            f"rc: {self.rc}\nrequests: {operations}\n"
            f"stdout:\n{self.stdout}\nstderr:\n{self.stderr}"
        )


def argv(template: str, **values: object) -> list[str]:
    """`template` split on whitespace, as upstream's `run_cmd` splits a
    command, with each word's fields then filled from `values`: a path
    stays one argument whatever it holds, where an f-string would split it
    at its spaces."""
    return [word.format(**values) for word in template.split()]


def _as_reply(reply: ReplyLike) -> Reply | HTTPResponse:
    if isinstance(reply, Reply | HTTPResponse):
        return reply
    return Reply(reply)


class _Responder:
    """Answers each request with the next scripted reply.

    One reply, or none, answers every request, as upstream's single
    `parsed_response` does; a sequence answers one request each, in
    order, as its `parsed_responses` does, and a request past its end
    fails the test.
    """

    def __init__(
        self,
        protocol: AwsWireProtocol,
        service_hint: str,
        replies: ReplyLike | Sequence[ReplyLike] | None,
    ) -> None:
        self.protocol = protocol
        self.service_hint = service_hint
        self.repeated: Reply | HTTPResponse | None = None
        self.queued: deque[Reply | HTTPResponse] = deque()
        if replies is None:
            self.repeated = Reply()
        elif isinstance(replies, Reply | HTTPResponse | Mapping):
            self.repeated = _as_reply(replies)
        else:
            self.queued.extend(_as_reply(reply) for reply in replies)
        self.calls: list[Call] = []
        self.failures: list[str] = []

    def respond(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        try:
            reconstructed = self.protocol.reconstruct(
                request, service_hint=self.service_hint
            )
            operation = reconstructed.operation_model
            self.calls.append(
                Call(operation.name, reconstructed.params, request)
            )
            reply = self._next_reply(operation.name)
            if isinstance(reply, HTTPResponse):
                return reply
            return self.protocol.serialize_parsed_response(
                operation,
                reply.parsed,
                status_code=reply.status,
                headers=reply.headers,
                request=request,
            )
        except Exception as error:
            self.failures.append(
                f"{request.method} {request.target}: "
                f"{type(error).__name__}: {error}\n"
                f"{traceback.format_exc()}"
            )
            return HTTPResponse.raw(
                b"the scripted service failed to answer the request",
                status=500,
                headers={"Content-Type": "text/plain"},
            )

    def _next_reply(self, operation: str) -> Reply | HTTPResponse:
        if self.repeated is not None:
            return self.repeated
        if not self.queued:
            raise AssertionError(f"no scripted reply is left for {operation}")
        return self.queued.popleft()


@functools.cache
def _protocol() -> AwsWireProtocol:
    # Each model costs a parse of its botocore JSON, so the session's
    # tests share one protocol.
    return create_aws_wire_protocol()


def upstream_env(
    proxy_url: str,
    ca_path: str,
    directory: Path,
    config: str,
    *,
    single_attempt: bool = True,
) -> dict[str, str]:
    """The environment upstream's base class gives the CLI, routed through
    the proxy, with its files in `directory` and `config` as its config
    file.

    The shared credentials file and every other file a provider could read
    are pinned empty, and the instance metadata service is off: no test
    credential comes from them. Without `single_attempt` the attempt count
    is the default: one attempt is outside the CRT client's 2 to 64.
    """
    files = {"config": config, "credentials": "", "boto": ""}
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
    env = {
        "AWS_DEFAULT_REGION": REGION,
        "AWS_ACCESS_KEY_ID": ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": SECRET_KEY,
        "AWS_CONFIG_FILE": str(directory / "config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(directory / "credentials"),
        "AWS_MAX_ATTEMPTS": "1",
        "AWS_EC2_METADATA_DISABLED": "true",
        "BOTO_CONFIG": str(directory / "boto"),
        "HTTPS_PROXY": proxy_url,
        "HTTP_PROXY": proxy_url,
        "AWS_CA_BUNDLE": ca_path,
    }
    if not single_attempt:
        del env["AWS_MAX_ATTEMPTS"]
    return env


class ApiSession:
    """One test's service: the scripted server behind the proxy, the
    command environment, and the working directory commands run in.

    `env` and `cwd` are the test's to change between commands.
    """

    def __init__(
        self,
        aws_cli: str,
        server: AsyncHTTPTestServer,
        env: dict[str, str],
        cwd: Path,
    ) -> None:
        self.aws_cli = aws_cli
        self.server = server
        self.env = env
        self.cwd = cwd

    @property
    def config_path(self) -> Path:
        return Path(self.env["AWS_CONFIG_FILE"])

    async def run(
        self,
        cmd: str | Sequence[str],
        *,
        replies: ReplyLike | Sequence[ReplyLike] | None = None,
        expected_rc: int | None = 0,
        stdin: bytes | None = b"",
        service: str | None = None,
    ) -> CommandRun:
        """Run `aws <cmd>` once against `replies`.

        A string command splits on whitespace, as upstream's `run_cmd`
        splits it, so a path goes in a list or through `argv`. `service`
        names the service whose model decodes the
        requests when the command's first word does not; `expected_rc`
        None accepts any status.
        """
        argv = cmd.split() if isinstance(cmd, str) else list(cmd)
        responder = _Responder(_protocol(), service or argv[0], replies)
        self.server.clear_requests()
        self.server.handler = responder.respond
        stdout, stderr, rc = await run_command(
            [self.aws_cli, *argv], self.env, cwd=self.cwd, stdin=stdin
        )
        result = CommandRun(
            stdout.decode(),
            stderr.decode(),
            rc,
            tuple(responder.calls),
        )
        if responder.failures:
            failures = "\n".join(responder.failures)
            raise AssertionError(
                f"the scripted service failed:\n{failures}\n"
                f"{result.describe()}"
            )
        if expected_rc is not None:
            assert rc == expected_rc, result.describe()
        return result

    async def assert_params_for_cmd(
        self,
        cmd: str | Sequence[str],
        params: Mapping[str, Any] | None = None,
        *,
        expected_rc: int = 0,
        stderr_contains: str | None = None,
        ignore_params: Sequence[str] = (),
        replies: ReplyLike | Sequence[ReplyLike] | None = None,
    ) -> CommandRun:
        """Run `cmd` and compare its last request's parameters with
        `params`, as upstream's method of the same name does."""
        result = await self.run(
            cmd, replies=replies, expected_rc=expected_rc
        )
        if stderr_contains is not None:
            assert stderr_contains in result.stderr, result.describe()
        if params is not None:
            assert result.last_params is not None, result.describe()
            actual = {
                key: value
                for key, value in result.last_params.items()
                if key not in ignore_params
            }
            assert actual == params, result.describe()
        return result


@asynccontextmanager
async def api_session(
    aws_cli: str,
    tmp_path: Path,
    config: str = CLASSIC_CONFIG,
    *,
    single_attempt: bool = True,
) -> AsyncIterator[ApiSession]:
    """A session whose commands run in `tmp_path`/work, apart from the
    environment's files in `tmp_path`/env, as upstream keeps its config in
    a directory of its own. `config` and `single_attempt` are
    `upstream_env`'s."""
    cwd = tmp_path / "work"
    directory = tmp_path / "env"
    cwd.mkdir()
    directory.mkdir()
    async with mock_server(handle_expect_header) as (server, proxy):
        env = upstream_env(
            proxy.endpoint_url,
            str(proxy.ca.ca_pem_path()),
            directory,
            config,
            single_attempt=single_attempt,
        )
        yield ApiSession(aws_cli, server, env, cwd)
