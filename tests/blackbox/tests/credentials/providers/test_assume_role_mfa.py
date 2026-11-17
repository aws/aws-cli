import asyncio
import os
import select
import signal
import subprocess
import sys
import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer, HTTPResponse

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
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
    expected_request,
    export_credentials_command,
    export_credentials_output,
    finish_run,
    metadata_credentials,
    role_cache_key,
    routed,
    run_export_credentials,
    seed_cli_cache,
    start_run,
    sts_success_xml,
)
from harness_plugin import command_environment
from ptyhelpers import (
    CONTROLLING_TERMINAL_LAUNCHER,
    SESSION_TIMEOUT_SECONDS,
    TERMINAL_SIZE,
    PromptAction,
    PromptOutcome,
    kill_session,
    local_flags,
    read_terminal,
    run_prompted,
    wait_for_session_exit,
)

# Every test here drives a POSIX pseudo-terminal, and loading this module
# opens one, so the module skips where there is no termios, as on Windows.
termios = pytest.importorskip(
    "termios", reason="drives a POSIX pseudo-terminal"
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# The MFA prompt of botocore's AssumeRoleCredentialFetcher
# (credentials.py:917-942) through `aws configure export-credentials`:
# `Enter MFA code for {mfa_serial}: `, read before the source credentials
# are frozen, and the CLI handler chain's framing of each outcome.
#
# Terminal runs put stdin (and stderr, unless a row pipes it) on a
# pseudo-terminal and stdout on a pipe, in a new session. With no
# controlling terminal the prompt reads fd 0 (the `stdin` ids); the
# `dev-tty` ids make the terminal the controlling one, so the prompt
# reads /dev/tty. Each answer is typed once its prompt is visible. Pipe
# runs put fd 0 on a pipe. There upstream also warns, in CPython
# getpass's words, that input may be echoed; those lines are not
# asserted.
#
# Not here: a second refresh of one MFA credentials object
# (`Cannot refresh credentials: MFA token required.`), which
# export-credentials never reaches, a stdin line over 1 MiB, and
# non-UTF-8 locales.
ACCOUNT: Final = "123456789012"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded"
SIGV4: Final = "AWS4-HMAC-SHA256"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
# botocore's generated RoleSessionName as the request normalizer leaves it.
GENERATED_NAME: Final = "botocore-session-<epoch>"
PROMPT_PREFIX: Final = "Enter MFA code for"
SERIAL: Final = f"arn:aws:iam::{ACCOUNT}:mfa/user"
MFA_PROFILE: Final = ("--profile", "mfa")
BASE_KEYS: Final = ("AKIDBASE", "basesecret")
ROLE_M: Final = f"arn:aws:iam::{ACCOUNT}:role/RoleM"
# The single-hop profile: `mfa` sourcing static `base`.
SINGLE_HOP: Final = f"""\
[profile mfa]
role_arn = {ROLE_M}
source_profile = base
mfa_serial = {SERIAL}

[profile base]
aws_access_key_id = AKIDBASE
aws_secret_access_key = basesecret
"""
# A two-hop chain: A (mfa) sources B (mfa), which sources C (static).
CHAIN: Final = f"""\
[profile A]
role_arn = arn:aws:iam::{ACCOUNT}:role/RoleA
source_profile = B
mfa_serial = arn:aws:iam::{ACCOUNT}:mfa/userA

[profile B]
role_arn = arn:aws:iam::{ACCOUNT}:role/RoleB
source_profile = C
mfa_serial = arn:aws:iam::{ACCOUNT}:mfa/userB

[profile C]
aws_access_key_id = AKIDC
aws_secret_access_key = csecret
"""
CHAIN_PROFILE: Final = ("--profile", "A")
CHAIN_KEYS: Final = ("AKIDC", "csecret")
ENVIRONMENT_SOURCE: Final = f"""\
[profile E]
role_arn = arn:aws:iam::{ACCOUNT}:role/RoleE
credential_source = Environment
mfa_serial = arn:aws:iam::{ACCOUNT}:mfa/userE
"""
CONTAINER_SOURCE: Final = f"""\
[profile K]
role_arn = arn:aws:iam::{ACCOUNT}:role/RoleK
credential_source = EcsContainer
mfa_serial = arn:aws:iam::{ACCOUNT}:mfa/userK
"""
CONTAINER_PATH: Final = "/creds"
# The CLI's error framing (errorhandler.py:391-399). An EOFError or a
# decode error fills the rest with CPython's own text, so only this part
# is asserted.
ERROR_PREFIX: Final = b"aws: [ERROR]:"
PARAM_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (ParamValidation): "
    "Parameter validation failed:\n"
)
# Terminal-run launchers are Python, never /bin/sh: macOS's /bin/sh (bash
# 3.2), started as a session leader with a terminal on fd 0, makes that
# terminal its controlling one, which would silently turn every `stdin`
# row into a /dev/tty row. Each launcher execs argv[1:] in place.
#
# Resets SIGINT and SIGHUP to their defaults, so a run never inherits the
# runner's ignored dispositions (a shell ignores SIGINT for an
# asynchronous job, nohup ignores SIGHUP). Rows that need an inherited
# SIG_IGN add their own launcher after this one.
DEFAULT_SIGNALS_LAUNCHER: Final = (
    sys.executable,
    "-c",
    "import os, signal, sys; "
    "signal.signal(signal.SIGINT, signal.SIG_DFL); "
    "signal.signal(signal.SIGHUP, signal.SIG_DFL); "
    "os.execv(sys.argv[1], sys.argv[1:])",
)
IGNORE_SIGINT_LAUNCHER: Final = (
    sys.executable,
    "-c",
    "import os, signal, sys; "
    "signal.signal(signal.SIGINT, signal.SIG_IGN); "
    "os.execv(sys.argv[1], sys.argv[1:])",
)
# How long an interrupt_then_type step waits between the signal and the
# keys, so a reader that wrongly honors the ignored signal has seen it.
SIGNAL_SETTLE_SECONDS: Final = 0.2


def new_terminal_local_flags() -> int:
    """The c_lflag of a new pseudo-terminal, where every terminal run starts.

    No launcher here changes the local flags, so a run that restores the
    terminal leaves exactly these behind.
    """
    controller_fd, terminal_fd = os.openpty()
    try:
        flags = local_flags(controller_fd)
    finally:
        os.close(terminal_fd)
        os.close(controller_fd)
    if flags is None:
        raise RuntimeError("cannot read a new terminal's local flags")
    return flags


TERMINAL_LOCAL_FLAGS: Final = new_terminal_local_flags()


@pytest_asyncio.fixture
async def container() -> AsyncIterator[AsyncHTTPTestServer]:
    """A plain-HTTP loopback container endpoint (no proxy is used)."""
    async with AsyncHTTPTestServer() as server:
        yield server


@dataclass(frozen=True)
class Session:
    """What the user does on the terminal.

    `answers[i]` is typed once the prompt has appeared `i + 1` times (a
    callable step runs instead). Then, at the next prompt, `sigint` sends
    SIGINT to the run, or `hang_up` closes the terminal's controller side
    (stderr_piped only). `ctty` makes the terminal the controlling one,
    so the prompt reads /dev/tty. With `stderr_piped`, stderr is a pipe of
    its own instead of the terminal.
    """

    answers: tuple[bytes | PromptAction, ...] = ()
    sigint: bool = False
    hang_up: bool = False
    ctty: bool = False
    stderr_piped: bool = False
    launcher: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.hang_up and not self.stderr_piped:
            raise ValueError("hang_up needs stderr_piped")
        if self.hang_up and self.sigint:
            raise ValueError("a session either hangs up or interrupts")

    def actions(self, observe: Callable[[], None]) -> list[PromptAction]:
        steps = [
            typist(answer) if isinstance(answer, bytes) else answer
            for answer in self.answers
        ]
        if self.sigint:
            steps.append(interrupt)
        return [observing(observe, step) for step in steps]


def typist(data: bytes) -> PromptAction:
    def type_answer(controller_fd: int, pid: int) -> None:
        del pid
        os.write(controller_fd, data)

    return type_answer


def interrupt(controller_fd: int, pid: int) -> None:
    del controller_fd
    os.kill(pid, signal.SIGINT)


def interrupt_then_type(data: bytes) -> PromptAction:
    """SIGINT the run, then type `data` (an ignored-SIGINT row)."""

    def step(controller_fd: int, pid: int) -> None:
        os.kill(pid, signal.SIGINT)
        time.sleep(SIGNAL_SETTLE_SECONDS)
        os.write(controller_fd, data)

    return step


def observing(observe: Callable[[], None], step: PromptAction) -> PromptAction:
    def act(controller_fd: int, pid: int) -> None:
        observe()
        step(controller_fd, pid)

    return act


@dataclass(frozen=True)
class TerminalRun:
    """One run on a terminal: its `CliRun` plus what only a terminal shows.

    `run.stderr` is what fd 2 received: the terminal's bytes, or the pipe's
    when stderr was piped. `terminal` is every byte read from the
    terminal (prompts written to /dev/tty or to a stderr on the terminal,
    error texts there, and the line discipline's echo). The local flags
    are the terminal's c_lflag when the first prompt appeared and after
    the run exited (None when not sampled). `observed` holds, for each
    scripted step, the request count per server when the step ran, which
    pins the prompt's position relative to every request.
    """

    run: CliRun
    terminal: bytes
    lflag_at_prompt: int | None
    lflag_after_exit: int | None
    observed: tuple[tuple[int, ...], ...]

    def describe(self) -> str:
        return self.run.describe() + (
            f"terminal: {self.terminal!r}\n"
            f"lflag at prompt: {flags_text(self.lflag_at_prompt)}, "
            f"after exit: {flags_text(self.lflag_after_exit)}\n"
            f"requests per server at each step: {self.observed}\n"
        )


def flags_text(flags: int | None) -> str:
    return "unsampled" if flags is None else f"{flags:#x}"


class Controller:
    """A terminal's controller fd that can be closed once, early or late."""

    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.closed = False

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self.fd)


def run_with_piped_stderr(
    command: Sequence[str],
    env: Mapping[str, str],
    actions: Sequence[PromptAction],
    *,
    cwd: Path,
    ctty: bool = False,
    launcher: Sequence[str] = (),
    hang_up: bool = False,
    timeout: float = SESSION_TIMEOUT_SECONDS,
) -> tuple[PromptOutcome, bytes]:
    """`run_prompted` with stderr on its own pipe: (outcome, stderr).

    The prompt goes to /dev/tty when the terminal controls the session
    and to stderr otherwise, so prompts are counted on both streams. Every
    stream is drained until it closes, as ptyhelpers does. With `hang_up`,
    the controller side is closed at the prompt after the last action, as
    closing a terminal window does; the flags after exit are then
    unsampled.
    """
    deadline = time.monotonic() + timeout
    argv = [
        *(CONTROLLING_TERMINAL_LAUNCHER if ctty else ()),
        *launcher,
        *command,
    ]
    controller_fd, terminal_fd = os.openpty()
    try:
        termios.tcsetwinsize(terminal_fd, TERMINAL_SIZE)
        process = subprocess.Popen(
            argv,
            stdin=terminal_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=command_environment(env),
            cwd=cwd,
            start_new_session=True,
        )
    except BaseException:
        os.close(controller_fd)
        raise
    finally:
        os.close(terminal_fd)
    controller = Controller(controller_fd)
    try:
        terminal, stdout, stderr, lflag_at_prompt = drive_split_streams(
            process, controller, actions, hang_up, deadline
        )
        returncode = wait_for_session_exit(process, deadline)
        lflag_after_exit = (
            None if controller.closed else local_flags(controller.fd)
        )
    finally:
        controller.close()
        if process.poll() is None:
            kill_session(process)
            process.wait()
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
    outcome = PromptOutcome(
        transcript=terminal,
        stdout=stdout,
        returncode=returncode,
        lflag_at_prompt=lflag_at_prompt,
        lflag_after_exit=lflag_after_exit,
    )
    return outcome, stderr


def drive_split_streams(
    process: subprocess.Popen[bytes],
    controller: Controller,
    actions: Sequence[PromptAction],
    hang_up: bool,
    deadline: float,
) -> tuple[bytes, bytes, bytes, int | None]:
    """Read terminal, stdout, and stderr until all close or the deadline.

    Returns (terminal, stdout, stderr, local flags at the first prompt).
    """
    assert process.stdout is not None
    assert process.stderr is not None
    prompt = PROMPT_PREFIX.encode()
    terminal, stdout, stderr = bytearray(), bytearray(), bytearray()
    buffers = {
        controller.fd: terminal,
        process.stdout.fileno(): stdout,
        process.stderr.fileno(): stderr,
    }
    open_fds = list(buffers)
    performed = 0
    lflag_at_prompt: int | None = None
    while open_fds and (remaining := deadline - time.monotonic()) > 0:
        readable, _, _ = select.select(open_fds, [], [], remaining)
        if not readable:
            break
        for fd in readable:
            chunk = read_terminal(fd)
            if chunk:
                buffers[fd] += chunk
            else:
                open_fds.remove(fd)
        seen = terminal.count(prompt) + stderr.count(prompt)
        if seen and lflag_at_prompt is None and not controller.closed:
            lflag_at_prompt = local_flags(controller.fd)
        while performed < min(seen, len(actions)):
            actions[performed](controller.fd, process.pid)
            performed += 1
        if hang_up and seen > len(actions) and not controller.closed:
            if controller.fd in open_fds:
                open_fds.remove(controller.fd)
            controller.close()
    return bytes(terminal), bytes(stdout), bytes(stderr), lflag_at_prompt


async def run_terminal(
    aws_cli: str,
    sandbox: Sandbox,
    servers: Sequence[AsyncHTTPTestServer],
    env: Mapping[str, str],
    session: Session,
    *,
    globals_: Sequence[str] = MFA_PROFILE,
    handlers: Mapping[AsyncHTTPTestServer, HandlerFactory] | None = None,
) -> TerminalRun:
    """Run export-credentials once on a terminal, driven by `session`.

    Like `run_aws`, the run starts from the sealed sandbox with fresh
    server recordings and handlers, in the sandbox root.
    """
    start_run(sandbox, servers, handlers)
    observed: list[tuple[int, ...]] = []

    def observe() -> None:
        observed.append(tuple(len(server.requests) for server in servers))

    # The reset comes first, so a row's own launcher (an inherited
    # SIG_IGN) still applies.
    launcher = (*DEFAULT_SIGNALS_LAUNCHER, *session.launcher)
    command = export_credentials_command(aws_cli, globals_=globals_)
    actions = session.actions(observe)
    if session.stderr_piped:
        outcome, stderr = await asyncio.to_thread(
            run_with_piped_stderr,
            command,
            env,
            actions,
            cwd=sandbox.root,
            ctty=session.ctty,
            launcher=launcher,
            hang_up=session.hang_up,
        )
    else:
        outcome = await asyncio.to_thread(
            run_prompted,
            command,
            env,
            PROMPT_PREFIX,
            actions,
            cwd=sandbox.root,
            ctty=session.ctty,
            launcher=launcher,
        )
        stderr = outcome.transcript
    run = finish_run(
        sandbox,
        servers,
        argv=(
            *(CONTROLLING_TERMINAL_LAUNCHER if session.ctty else ()),
            *launcher,
            *command,
        ),
        returncode=outcome.returncode,
        stdout=outcome.stdout,
        stderr=stderr,
    )
    return TerminalRun(
        run=run,
        terminal=outcome.transcript,
        lflag_at_prompt=outcome.lflag_at_prompt,
        lflag_after_exit=outcome.lflag_after_exit,
        observed=tuple(observed),
    )


def prompt_for(serial: str) -> bytes:
    """botocore's prompt text (credentials.py:930-934), UTF-8."""
    return f"{PROMPT_PREFIX} {serial}: ".encode()


def on_terminal(text: bytes) -> bytes:
    """`text` as a terminal shows it: ONLCR turns "\\n" into "\\r\\n"."""
    return text.replace(b"\n", b"\r\n")


def too_short(name: str, length: int, minimum: int) -> str:
    """validate.py:136-143 for a string under its model's min length."""
    return (
        f"Invalid length for parameter {name}, value: {length}, "
        f"valid min length: {minimum}"
    )


def param_error(*lines: str) -> bytes:
    """The ParamValidation framing (errorhandler.py:179-182, 236-247)."""
    return (PARAM_PREFIX + "\n".join(lines) + "\n").encode()


def role_arn(role: str) -> str:
    return f"arn:aws:iam::{ACCOUNT}:role/{role}"


def serial_for(user: str) -> str:
    return f"arn:aws:iam::{ACCOUNT}:mfa/{user}"


def role_response(role: str) -> HTTPResponse:
    """AssumeRole credentials ASIA<ROLE>/<role>-secret/<role>-token."""
    return sts_success_xml(
        access_key=f"ASIA{role.upper()}",
        secret_key=f"{role}-secret",
        session_token=f"{role}-token",
        assumed_role_id=f"AROA{role.upper()}:s",
        arn=f"arn:aws:sts::{ACCOUNT}:assumed-role/{role}/s",
    )


def exported(role: str) -> bytes:
    return export_credentials_output(
        f"ASIA{role.upper()}",
        f"{role}-secret",
        f"{role}-token",
        FUTURE_EXPIRATION,
    )


def role_keys(role: str) -> tuple[str, str]:
    return f"ASIA{role.upper()}", f"{role}-secret"


def cached_role(
    role: str, expiration: str = FUTURE_EXPIRATION
) -> dict[str, object]:
    """The role-cache entry for `role_response(role)`, as read back.

    botocore caches the parsed response with Credentials.AccountId added
    from the assumed role ARN (credentials.py:852-860, called at :923),
    timestamps as the CLI's iso8601 parser leaves them; only Credentials
    is read back.
    """
    return {
        "Credentials": {
            "AccessKeyId": f"ASIA{role.upper()}",
            "SecretAccessKey": f"{role}-secret",
            "SessionToken": f"{role}-token",
            "Expiration": expiration,
            "AccountId": ACCOUNT,
        }
    }


def cache_key(role: str, serial: str) -> str:
    """The role-cache key: RoleArn and SerialNumber, never TokenCode.

    The generated RoleSessionName is left out (credentials.py:830-850),
    and TokenCode is added only to a copy of the kwargs at prompt time.
    """
    return role_cache_key({"RoleArn": role_arn(role), "SerialNumber": serial})


def cache_entry(role: str, serial: str) -> str:
    return cache_path(cache_key(role, serial))


def cache_path(key: str) -> str:
    return f"home/{CLI_CACHE.as_posix()}/{key}.json"


def cache_written(
    sandbox: Sandbox, files: Mapping[str, dict[str, object]]
) -> FileChanges:
    """The run's changes when it writes the role-cache `files`, by path.

    Each file holds its entry, mode 0600, and the first write also
    creates whichever cache directories the sealed sandbox lacked
    (utils.py:3991-4006).
    """
    changes = created_cache_directories(sandbox.sealed or {})
    for path, document in files.items():
        changes[path] = (CACHE_FILE_MODE, RoleCacheContent(document))
    return dict(sorted(changes.items()))


def assume_role_body(role: str, serial: str, code: str) -> bytes:
    """botocore's AssumeRole form body for an MFA profile.

    SerialNumber from the profile (credentials.py:1659-1661), RoleArn and
    the generated RoleSessionName from the fetcher (credentials.py:
    804-820), and the prompted TokenCode (credentials.py:926-942).
    """
    return form_body(
        ("SerialNumber", serial),
        ("RoleArn", role_arn(role)),
        ("RoleSessionName", GENERATED_NAME),
        ("TokenCode", code),
    )


def form_body(*pairs: tuple[str, str]) -> bytes:
    """An AssumeRole query body: Action, Version, then `pairs`.

    NormalizedRequest compares the decoded form, so the order is the
    sender's. GENERATED_NAME is the normalizer's placeholder and stays
    raw.
    """
    fields = [("Action", "AssumeRole"), ("Version", "2011-06-15"), *pairs]
    return "&".join(
        f"{quote_plus(name)}="
        + (value if value == GENERATED_NAME else quote_plus(value))
        for name, value in fields
    ).encode()


@dataclass(frozen=True)
class StsCall:
    """One AssumeRole call: its form body, signing keys, and token.

    The call is SigV4-signed for sts in us-east-1 with `keys`, and sends
    `token` as X-Amz-Security-Token (absent when None).
    """

    body: bytes
    keys: tuple[str, str]
    token: str | None = None

    def request(self) -> NormalizedRequest:
        headers = {
            "authorization": SIGV4,
            "x-amz-date": AMZ_DATE_PLACEHOLDER,
            "content-type": FORM_CONTENT_TYPE,
        }
        if self.token is not None:
            headers["x-amz-security-token"] = self.token
        return expected_request(
            "POST",
            STS_HOST,
            "/",
            body=self.body,
            headers=headers,
            signing_scope=(
                self.keys[0],
                SCOPE_DATE_PLACEHOLDER,
                "us-east-1",
                "sts",
            ),
        )


def mfa_call(
    role: str,
    serial: str,
    code: str,
    keys: tuple[str, str],
    token: str | None = None,
) -> StsCall:
    """The AssumeRole call of an MFA profile that typed `code`."""
    return StsCall(assume_role_body(role, serial, code), keys, token)


def assert_requests(
    run: CliRun,
    *calls: StsCall,
    others: Sequence[NormalizedRequest] = (),
) -> None:
    """The run's requests: the STS `calls`, then `others`, exactly.

    Each STS call's SigV4 signature is checked on the raw request.
    """
    expected = (*(call.request() for call in calls), *others)
    assert run.requests == expected, run.describe()
    sts = [
        request
        for request in run.raw_requests
        if request.headers.get("host") == STS_HOST
    ]
    for request, call in zip(sts, calls, strict=True):
        assert_signature(request, *call.keys)


def assert_echo_off_then_restored(run: TerminalRun) -> None:
    """ECHO was off at the prompt, and the terminal restored after exit.

    The terminal starts with TERMINAL_LOCAL_FLAGS, ECHO among them. Which
    other flags the reader changes while it reads is its own choice.
    """
    assert TERMINAL_LOCAL_FLAGS & termios.ECHO
    assert run.lflag_at_prompt is not None, run.describe()
    assert not run.lflag_at_prompt & termios.ECHO, run.describe()
    assert run.lflag_after_exit == TERMINAL_LOCAL_FLAGS, run.describe()


def assert_never_prompted(run: TerminalRun) -> None:
    """No prompt appeared: no step ran and the terminal was not touched."""
    assert run.observed == (), run.describe()
    assert run.lflag_at_prompt is None, run.describe()
    assert run.lflag_after_exit == TERMINAL_LOCAL_FLAGS, run.describe()


def assert_exported(run: TerminalRun, role: str, terminal: bytes) -> None:
    assert (run.run.returncode, run.run.stdout) == (0, exported(role)), (
        run.describe()
    )
    assert run.terminal == terminal, run.describe()


def assert_failed(
    run: TerminalRun,
    returncode: int,
    stdout: bytes,
    terminal: bytes | BytesStartingWith,
) -> None:
    assert (run.run.returncode, run.run.stdout) == (returncode, stdout), (
        run.describe()
    )
    assert run.terminal == terminal, run.describe()


def assert_nothing_sent(run: TerminalRun) -> None:
    """No request went out and no file was written."""
    assert run.run.requests == (), run.describe()
    assert run.run.changes == {}, run.describe()


async def run_single_hop(
    aws_cli: str, sandbox: Sandbox, stub: Stub, session: Session
) -> TerminalRun:
    """The single-hop profile with one scripted RoleM response."""
    server, proxy = stub
    sandbox.config.write_text(SINGLE_HOP)
    sandbox.seal()
    script = {STS_ROUTE: [role_response("RoleM")]}
    return await run_terminal(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        session,
        handlers={server: lambda: routed(script)},
    )


async def run_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    session: Session,
    *,
    responses: Sequence[HTTPResponse] = (),
) -> TerminalRun:
    """The two-hop chain, STS answering `responses` in order."""
    server, proxy = stub
    sandbox.config.write_text(CHAIN)
    sandbox.seal()
    script = {STS_ROUTE: list(responses)}
    return await run_terminal(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        session,
        globals_=CHAIN_PROFILE,
        handlers={server: lambda: routed(script)},
    )


def assert_single_hop_success(
    run: TerminalRun, sandbox: Sandbox, code: str
) -> None:
    """RoleM exported, TokenCode=`code` sent, and its cache file written.

    The terminal showed the prompt and the newline written after the read.
    """
    assert_exported(run, "RoleM", prompt_for(SERIAL) + b"\r\n")
    assert_requests(run.run, mfa_call("RoleM", SERIAL, code, BASE_KEYS))
    assert run.observed == ((0,),), run.describe()
    assert run.run.changes == cache_written(
        sandbox, {cache_entry("RoleM", SERIAL): cached_role("RoleM")}
    ), run.describe()
    assert_echo_off_then_restored(run)


@pytest.mark.parametrize(
    ("typed", "ctty", "code"),
    [
        pytest.param(b"123456\n", False, "123456", id="valid-stdin"),
        pytest.param(b"123456\n", True, "123456", id="valid-dev-tty"),
        # ICRNL turns the typed CR into the line's end.
        pytest.param(b"123456\r", True, "123456", id="cr-dev-tty"),
        pytest.param(
            b"123457\x7f6\n", True, "123456", id="verase-edit-dev-tty"
        ),
        pytest.param(
            b"123456  \n", True, "123456  ", id="trailing-spaces-dev-tty"
        ),
    ],
)
async def test_mfa_prompt_sends_typed_line_as_token_code(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    typed: bytes,
    ctty: bool,
    code: str,
) -> None:
    session = Session(answers=(typed,), ctty=ctty)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    assert_single_hop_success(run, sandbox, code)


@pytest.mark.parametrize(
    ("typed", "length"),
    [
        pytest.param(b"12345\n", 5, id="five-digits"),
        pytest.param(b"\n", 0, id="empty"),
    ],
)
async def test_mfa_prompt_short_code_fails_validation_before_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    typed: bytes,
    length: int,
) -> None:
    session = Session(answers=(typed,), ctty=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    error = param_error(too_short("TokenCode", length, 6))
    assert_failed(
        run, 252, b"", prompt_for(SERIAL) + b"\r\n" + on_terminal(error)
    )
    assert run.observed == ((0,),), run.describe()
    assert_nothing_sent(run)
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_end_of_input_fails_without_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(answers=(b"\x04",), ctty=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    assert_failed(
        run, 255, b"", BytesStartingWith(prompt_for(SERIAL), (ERROR_PREFIX,))
    )
    assert run.observed == ((0,),), run.describe()
    assert_nothing_sent(run)
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_sigint_exits_130_with_newline_on_stdout(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # Without a controlling terminal only a signal interrupts the read.
    session = Session(sigint=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    # InterruptExceptionHandler writes the newline to stdout and returns
    # 130 (errorhandler.py:372-378).
    assert_failed(run, 130, b"\n", prompt_for(SERIAL))
    assert run.observed == ((0,),), run.describe()
    assert_nothing_sent(run)
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_ctrl_c_on_controlling_terminal_exits_130(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(answers=(b"\x03",), ctty=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    assert_failed(run, 130, b"\n", prompt_for(SERIAL))
    assert run.observed == ((0,),), run.describe()
    assert_nothing_sent(run)
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_with_inherited_ignored_sigint_keeps_reading(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(
        answers=(interrupt_then_type(b"123456\n"),),
        launcher=IGNORE_SIGINT_LAUNCHER,
    )

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    assert_single_hop_success(run, sandbox, "123456")


async def test_mfa_prompt_invalid_utf8_on_dev_tty_fails_without_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(answers=(b"12\xff456\n",), ctty=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    # /dev/tty decodes strictly, so the read itself fails; the rest of
    # the message is the codec's.
    assert_failed(
        run, 255, b"", BytesStartingWith(prompt_for(SERIAL), (ERROR_PREFIX,))
    )
    assert run.observed == ((0,),), run.describe()
    assert_nothing_sent(run)
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_with_stderr_piped_prompts_on_dev_tty(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(answers=(b"123456\n",), ctty=True, stderr_piped=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    # With a controlling terminal the prompt and its newline go there, so
    # a captured stderr (a credential_process caller) stays clean.
    assert_exported(run, "RoleM", prompt_for(SERIAL) + b"\r\n")
    assert run.run.stderr == b"", run.describe()
    assert_requests(run.run, mfa_call("RoleM", SERIAL, "123456", BASE_KEYS))
    assert run.observed == ((0,),), run.describe()
    assert run.run.changes == cache_written(
        sandbox, {cache_entry("RoleM", SERIAL): cached_role("RoleM")}
    ), run.describe()
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_terminal_hang_up_ends_prompt(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(hang_up=True, ctty=True, stderr_piped=True)

    run = await run_single_hop(aws_cli, sandbox, stub, session)

    # Closing the terminal at the prompt must fail the run without a
    # request. Upstream dies of SIGHUP's default action; a run the
    # harness had to kill at its deadline hung.
    assert run.run.returncode not in (0, -signal.SIGKILL), run.describe()
    assert run.run.stdout == b"", run.describe()
    assert_nothing_sent(run)


async def test_mfa_prompt_skipped_for_fresh_cache_entry(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    seed_cli_cache(
        sandbox.home, cache_key("RoleM", SERIAL), cached_role("RoleM")
    )

    run = await run_single_hop(aws_cli, sandbox, stub, Session())

    assert_exported(run, "RoleM", b"")
    assert run.run.stderr == b"", run.describe()
    assert_never_prompted(run)
    # The cached entry is read, not rewritten.
    assert_nothing_sent(run)


async def test_mfa_prompt_runs_again_for_entry_inside_expiry_window(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # 450 s left: inside the fetcher's 900 s window (credentials.py:720,
    # 785-789), and at least 150 s from each of the 300, 600, and 900 s
    # boundaries.
    soon = (datetime.now(UTC) + timedelta(seconds=450)).isoformat()
    seed_cli_cache(
        sandbox.home, cache_key("RoleM", SERIAL), cached_role("RoleM", soon)
    )

    run = await run_single_hop(
        aws_cli, sandbox, stub, Session(answers=(b"123456\n",))
    )

    # The new credentials overwrite the seeded entry in place.
    assert_single_hop_success(run, sandbox, "123456")


def chain_prompts() -> bytes:
    return (
        prompt_for(serial_for("userA"))
        + b"\r\n"
        + prompt_for(serial_for("userB"))
        + b"\r\n"
    )


async def test_mfa_chain_prompts_outer_then_inner_before_any_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    session = Session(answers=(b"111111\n", b"222222\n"), ctty=True)

    run = await run_chain(
        aws_cli,
        sandbox,
        stub,
        session,
        responses=[role_response("RoleB"), role_response("RoleA")],
    )

    # Prompt A, prompt B, STS(B) from C, then STS(A) from B: the prompt
    # runs before the source is frozen (credentials.py:916-952).
    assert_exported(run, "RoleA", chain_prompts())
    assert run.observed == ((0,), (0,)), run.describe()
    assert_requests(
        run.run,
        mfa_call("RoleB", serial_for("userB"), "222222", CHAIN_KEYS),
        mfa_call(
            "RoleA",
            serial_for("userA"),
            "111111",
            role_keys("RoleB"),
            "RoleB-token",
        ),
    )
    assert run.run.changes == cache_written(
        sandbox,
        {
            cache_entry("RoleA", serial_for("userA")): cached_role("RoleA"),
            cache_entry("RoleB", serial_for("userB")): cached_role("RoleB"),
        },
    ), run.describe()
    assert_echo_off_then_restored(run)


async def test_mfa_chain_short_outer_code_fails_after_inner_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # A's code is validated only after B's call returned and B's cache
    # file was written.
    session = Session(answers=(b"12345\n", b"222222\n"))

    run = await run_chain(
        aws_cli, sandbox, stub, session, responses=[role_response("RoleB")]
    )

    error = on_terminal(param_error(too_short("TokenCode", 5, 6)))
    assert_failed(run, 252, b"", chain_prompts() + error)
    assert run.observed == ((0,), (0,)), run.describe()
    assert_requests(
        run.run, mfa_call("RoleB", serial_for("userB"), "222222", CHAIN_KEYS)
    )
    assert run.run.changes == cache_written(
        sandbox,
        {cache_entry("RoleB", serial_for("userB")): cached_role("RoleB")},
    ), run.describe()
    assert_echo_off_then_restored(run)


async def test_mfa_chain_with_inner_cached_prompts_outer_only(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    seed_cli_cache(
        sandbox.home,
        cache_key("RoleB", serial_for("userB")),
        cached_role("RoleB"),
    )
    session = Session(answers=(b"111111\n",))

    run = await run_chain(
        aws_cli, sandbox, stub, session, responses=[role_response("RoleA")]
    )

    assert_exported(run, "RoleA", prompt_for(serial_for("userA")) + b"\r\n")
    assert run.observed == ((0,),), run.describe()
    assert_requests(
        run.run,
        mfa_call(
            "RoleA",
            serial_for("userA"),
            "111111",
            role_keys("RoleB"),
            "RoleB-token",
        ),
    )
    assert run.run.changes == cache_written(
        sandbox,
        {cache_entry("RoleA", serial_for("userA")): cached_role("RoleA")},
    ), run.describe()
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_with_empty_environment_source_never_prompts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    server, proxy = stub
    sandbox.config.write_text(ENVIRONMENT_SOURCE)
    sandbox.seal()

    run = await run_terminal(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        Session(),
        globals_=("--profile", "E"),
    )

    # The sourced provider loads eagerly inside session.get_credentials()
    # (credentials.py:1864-1883), so the failure is the load framing.
    error = (
        b"\naws: [ERROR]: An error occurred (Configuration): Unable to "
        b"retrieve credentials: Error when retrieving credentials from "
        b"Environment: No credentials found in credential_source referenced "
        b"in profile E\n"
    )
    assert_failed(run, 253, b"", on_terminal(error))
    assert_never_prompted(run)
    assert_nothing_sent(run)


async def run_container_source(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    container: AsyncHTTPTestServer,
    session: Session,
) -> TerminalRun:
    """Profile K: credential_source = EcsContainer at the loopback stub."""
    server, proxy = stub
    sandbox.config.write_text(CONTAINER_SOURCE)
    sandbox.seal()
    env = sandbox.env(proxy)
    host = f"127.0.0.1:{container.port}"
    env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = (
        f"http://{host}{CONTAINER_PATH}"
    )
    sts_script = {STS_ROUTE: [role_response("RoleK")]}
    container_script = {
        ("GET", host, CONTAINER_PATH): [
            HTTPResponse.json(metadata_credentials())
        ]
    }
    return await run_terminal(
        aws_cli,
        sandbox,
        [server, container],
        env,
        session,
        globals_=("--profile", "K"),
        handlers={
            server: lambda: routed(sts_script),
            container: lambda: routed(container_script),
        },
    )


def container_request(container: AsyncHTTPTestServer) -> NormalizedRequest:
    """The container GET: direct, unsigned, no authorization token.

    No token is configured (utils.py:2974-2977), so no Authorization.
    """
    host = f"127.0.0.1:{container.port}"
    return expected_request("GET", host, CONTAINER_PATH)


async def test_mfa_prompt_with_container_source_fetches_before_prompting(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    container: AsyncHTTPTestServer,
) -> None:
    run = await run_container_source(
        aws_cli, sandbox, stub, container, Session(answers=(b"123456\n",))
    )

    serial = serial_for("userK")
    assert_exported(run, "RoleK", prompt_for(serial) + b"\r\n")
    # The container GET completed before the prompt.
    assert run.observed == ((0, 1),), run.describe()
    assert_requests(
        run.run,
        mfa_call(
            "RoleK",
            serial,
            "123456",
            ("AKIDCONTAINER", "CONTAINER-secret"),
            "CONTAINER-token",
        ),
        others=(container_request(container),),
    )
    assert run.run.changes == cache_written(
        sandbox, {cache_entry("RoleK", serial): cached_role("RoleK")}
    ), run.describe()
    assert_echo_off_then_restored(run)


async def test_mfa_prompt_cache_key_keeps_every_argument_but_token_code(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # The prompt adds TokenCode to a copy of the call's arguments
    # (credentials.py:926-942), so the cache key keeps every configured
    # argument and the serial, but not the code (credentials.py:830-850).
    server, proxy = stub
    sandbox.config.write_text(
        SINGLE_HOP.replace(
            "source_profile = base\n",
            "source_profile = base\nrole_session_name = sess\n"
            "external_id = ext-id\nduration_seconds = 1800\n",
        )
    )
    sandbox.seal()
    script = {STS_ROUTE: [role_response("RoleM")]}

    run = await run_terminal(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        Session(answers=(b"123456\n",)),
        handlers={server: lambda: routed(script)},
    )

    assert_exported(run, "RoleM", prompt_for(SERIAL) + b"\r\n")
    assert run.observed == ((0,),), run.describe()
    body = form_body(
        ("RoleSessionName", "sess"),
        ("ExternalId", "ext-id"),
        ("SerialNumber", SERIAL),
        ("DurationSeconds", "1800"),
        ("RoleArn", ROLE_M),
        ("TokenCode", "123456"),
    )
    assert_requests(run.run, StsCall(body, BASE_KEYS))
    key = role_cache_key(
        {
            "RoleSessionName": "sess",
            "ExternalId": "ext-id",
            "SerialNumber": SERIAL,
            "DurationSeconds": 1800,
            "RoleArn": ROLE_M,
        }
    )
    assert run.run.changes == cache_written(
        sandbox, {cache_path(key): cached_role("RoleM")}
    ), run.describe()
    assert_echo_off_then_restored(run)


async def run_pipe(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    *,
    config: str = SINGLE_HOP,
    globals_: Sequence[str] = MFA_PROFILE,
    responses: Sequence[HTTPResponse] = (),
    stdin: bytes = b"",
) -> CliRun:
    """Run once with fd 0 a pipe carrying `stdin`."""
    server, proxy = stub
    sandbox.config.write_text(config)
    sandbox.seal()
    script = {STS_ROUTE: list(responses)}
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        globals_=globals_,
        stdin=stdin,
        handlers={server: lambda: routed(script)},
    )


@pytest.mark.parametrize(
    "stdin",
    [
        pytest.param(b"123456\n", id="line"),
        pytest.param(b"123456", id="no-newline"),
    ],
)
async def test_mfa_prompt_on_pipe_reads_line(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    stdin: bytes,
) -> None:
    run = await run_pipe(
        aws_cli,
        sandbox,
        stub,
        responses=[role_response("RoleM")],
        stdin=stdin,
    )

    # Without a terminal the prompt goes to stderr.
    assert (run.returncode, run.stdout) == (0, exported("RoleM")), (
        run.describe()
    )
    assert prompt_for(SERIAL) in run.stderr, run.describe()
    assert_requests(run, mfa_call("RoleM", SERIAL, "123456", BASE_KEYS))
    assert run.changes == cache_written(
        sandbox, {cache_entry("RoleM", SERIAL): cached_role("RoleM")}
    ), run.describe()


async def test_mfa_prompt_on_exhausted_stdin_fails_without_request(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    run = await run_pipe(aws_cli, sandbox, stub, stdin=b"")

    # The read ends at end of file; upstream's EOFError has no message of
    # its own after the CLI's error prefix.
    assert (run.returncode, run.stdout, run.stderr) == (
        255,
        b"",
        BytesStartingWith(b"", (prompt_for(SERIAL), ERROR_PREFIX)),
    ), run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


async def test_mfa_chain_on_pipe_reads_one_line_per_prompt(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    # One buffered stdin serves both prompts: the outer prompt takes the
    # first line and the inner one the second.
    run = await run_pipe(
        aws_cli,
        sandbox,
        stub,
        config=CHAIN,
        globals_=CHAIN_PROFILE,
        responses=[role_response("RoleB"), role_response("RoleA")],
        stdin=b"111111\n222222\n",
    )

    assert (run.returncode, run.stdout) == (0, exported("RoleA")), (
        run.describe()
    )
    outer = run.stderr.find(prompt_for(serial_for("userA")))
    inner = run.stderr.find(prompt_for(serial_for("userB")))
    assert 0 <= outer < inner, run.describe()
    assert_requests(
        run,
        mfa_call("RoleB", serial_for("userB"), "222222", CHAIN_KEYS),
        mfa_call(
            "RoleA",
            serial_for("userA"),
            "111111",
            role_keys("RoleB"),
            "RoleB-token",
        ),
    )
    assert run.changes == cache_written(
        sandbox,
        {
            cache_entry("RoleA", serial_for("userA")): cached_role("RoleA"),
            cache_entry("RoleB", serial_for("userB")): cached_role("RoleB"),
        },
    ), run.describe()
