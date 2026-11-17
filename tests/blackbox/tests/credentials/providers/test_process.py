# credential_process through `aws configure export-credentials`: botocore
# credentials.py:1076-1160 and RefreshableCredentials (:383-692), on top of
# CPython's subprocess.py:1856-1994 and _posixsubprocess.c:665-865. Every
# scenario makes no HTTP request.
import contextlib
import json
import os
import shlex
import shutil
import signal
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest

from credhelpers import (
    CREATED_FILE_MODE,
    PROVIDER_OWNED_ENV,
    TRAP_PIPE_XFSZ_HUP,
    BytesStartingWith,
    CliRun,
    FileChanges,
    Sandbox,
    Stub,
    assert_credential_error,
    assert_signed_by,
    assert_signed_with,
    command_line,
    credential_process,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    json_process,
    list_bucket,
    process_credentials,
    run_export_credentials,
    run_s3_ls,
    without_s3,
    write_config,
)

# The helpers here are /bin/sh scripts on a POSIX PATH, and the tests check
# POSIX process behavior: exec errors, signals, process groups, inherited
# descriptors and shlex splitting, so the module skips where there is no
# fcntl or resource, as on Windows.
fcntl = pytest.importorskip("fcntl", reason="runs POSIX credential helpers")
resource = pytest.importorskip(
    "resource", reason="runs POSIX credential helpers"
)

pytestmark = pytest.mark.asyncio

# Load-time failures: exportcreds.py:269-275 wraps them in a
# ConfigurationError, rendered by the enhanced handler with rc 253.
CONFIGURATION_ERROR_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
CONFIGURATION_ERROR_RC: Final = 253
# Refresh-time failures surface from get_frozen_credentials() outside that
# try (exportcreds.py:280) and reach GeneralExceptionHandler, rc 255.
GENERAL_ERROR_PREFIX: Final = "\naws: [ERROR]: "
GENERAL_ERROR_RC: Final = 255
# InterruptExceptionHandler (errorhandler.py:373-379).
INTERRUPT_RC: Final = 128 + signal.SIGINT
# CredentialRetrievalError's template (exceptions.py:188-198), provider
# custom-process (credentials.py:1077).
PROCESS_ERROR: Final = "Error when retrieving credentials from custom-process:"
# A PATH that holds the system tools on macOS and Linux alike, so lookups
# never depend on the runner's own PATH.
SYSTEM_PATH: Final = "/usr/bin:/bin"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00Z"
PAST_EXPIRATION: Final = "2000-01-01T00:00:00Z"
STILL_EXPIRED: Final = (
    "Credentials were refreshed, but the refreshed credentials are still "
    "expired."
)
LARGE_STREAM_BYTES: Final = 2 * 1024 * 1024

# Writes its argv next to itself, then prints valid credentials.
ARGV_HELPER: Final = """\
import json
import sys
from pathlib import Path

Path(__file__).with_name("argv.json").write_text(
    json.dumps(sys.argv[1:]), encoding="utf-8"
)
print(
    json.dumps(
        {"Version": 1, "AccessKeyId": "AKIDARGV",
         "SecretAccessKey": "ARGV-secret"}
    )
)
"""
# Writes the environment keys named in argv (None when unset) next to
# itself, then prints valid credentials.
ENV_HELPER: Final = """\
import json
import os
import sys
from pathlib import Path

seen = {key: os.environ.get(key) for key in sys.argv[1:]}
Path(__file__).with_name("helper-env.json").write_text(
    json.dumps(seen), encoding="utf-8"
)
print(
    json.dumps(
        {"Version": 1, "AccessKeyId": "AKIDENV",
         "SecretAccessKey": "ENV-secret"}
    )
)
"""
# Reports the descriptors it inherited open as its access key. It lists
# /dev/fd (fdescfs on macOS, /proc/self/fd on Linux) rather than probing a
# fixed range, so no descriptor number escapes it. The listing's own
# directory descriptor is closed once listdir returns, so the fstat filter
# drops it.
FD_HELPER: Final = """\
import json
import os


def is_open(fd):
    try:
        os.fstat(fd)
    except OSError:
        return False
    return True


listed = sorted(int(name) for name in os.listdir("/dev/fd"))
fds = ",".join(str(fd) for fd in listed if is_open(fd))
print(
    json.dumps(
        {"Version": 1, "AccessKeyId": "FDS:" + fds,
         "SecretAccessKey": "FD-secret"}
    )
)
"""
# Reports the first line of its stdin as its access key.
STDIN_HELPER: Final = """\
import json
import sys

line = sys.stdin.readline().strip()
print(
    json.dumps(
        {"Version": 1, "AccessKeyId": "STDIN:" + line,
         "SecretAccessKey": "STDIN-secret"}
    )
)
"""
# Plays steps.json in order (the last one repeats): each step's stdout,
# stderr, and exit status. Every call appends its index and the profile
# chain it saw to calls.jsonl, which the run's file changes show.
SEQUENCE_HELPER: Final = """\
import json
import os
import sys
from pathlib import Path

here = Path(__file__).parent
log = here / "calls.jsonl"
calls = 0
if log.exists():
    calls = len(log.read_text(encoding="utf-8").splitlines())
with log.open("a", encoding="utf-8") as stream:
    chain = os.environ.get("_AWS_CLI_PROFILE_CHAIN")
    stream.write(json.dumps({"call": calls, "chain": chain}) + "\\n")
steps = json.loads((here / "steps.json").read_text(encoding="utf-8"))
step = steps[min(calls, len(steps) - 1)]
sys.stdout.write(step["stdout"])
sys.stderr.write(step["stderr"])
sys.exit(step["status"])
"""
# Fills stderr past any pipe buffer before writing stdout, so a reader
# that drains stdout to EOF first deadlocks.
LARGE_OUTPUT_HELPER: Final = f"""\
import json
import sys

sys.stderr.write("x" * {LARGE_STREAM_BYTES})
sys.stderr.flush()
sys.stdout.write(
    json.dumps(
        {{"Version": 1, "AccessKeyId": "AKIDLARGE",
          "SecretAccessKey": "LARGE-secret"}}
    )
    + " " * {LARGE_STREAM_BYTES}
)
"""
# Reports which of its parent's process group and session it shares as its
# access key.
PROCESS_GROUP_HELPER: Final = """\
import json
import os

parent = os.getppid()
shared = []
if os.getpgid(0) == os.getpgid(parent):
    shared.append("group")
if os.getsid(0) == os.getsid(parent):
    shared.append("session")
print(
    json.dumps(
        {"Version": 1, "AccessKeyId": "SHARED:" + ",".join(shared),
         "SecretAccessKey": "PG-secret"}
    )
)
"""
# Perl starts each %SIG entry at "IGNORE" for a signal ignored across exec
# and changes no disposition of its own, unlike CPython, which ignores
# PIPE and XFSZ at startup.
SIGNAL_OBSERVER: Final = """\
my @ignored = grep { ($SIG{$_} // "") eq "IGNORE" } qw(PIPE XFSZ HUP);
my $key = "IGNORED:" . join(",", @ignored);
print qq({"Version": 1, "AccessKeyId": "$key", "SecretAccessKey": "s"});
"""


@pytest.fixture
def perl() -> str:
    path = shutil.which("perl")
    if path is None:
        pytest.skip("no perl to report inherited signal dispositions")
    return path


async def run_process(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    *,
    env: Mapping[str, str | None] | None = None,
    globals_: Sequence[str] = (),
    cmd_args: Sequence[str] = (),
    stdin: bytes | None = b"",
    cwd: Path | None = None,
    launcher: Sequence[str] = (),
    pass_fds: Sequence[int] = (),
) -> CliRun:
    """Run one scenario's command; an `env` value of None unsets the key."""
    server, proxy = stub
    run_env = sandbox.env(proxy)
    for key, value in (env or {}).items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        run_env,
        globals_=globals_,
        cmd_args=cmd_args,
        stdin=stdin,
        cwd=cwd,
        launcher=launcher,
        pass_fds=pass_fds,
    )


async def listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    *,
    env: Mapping[str, str | None] | None = None,
    cwd: Path | None = None,
) -> CliRun:
    """Run `s3 ls` once with `env` applied, as `run_process` does."""
    server, proxy = stub
    run_env = sandbox.env(proxy)
    for key, value in (env or {}).items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    return await run_s3_ls(
        aws_cli, sandbox, [server], run_env, s3=server, cwd=cwd
    )


def assert_signed(
    run: CliRun, access_key: str, token: str | None = None
) -> None:
    """The listing carries `access_key` and `token`, and the process
    provider sent no request of its own."""
    assert_signed_with(run, access_key, token)
    assert without_s3(run).requests == (), run.describe()


def quoted(path: Path | str) -> str:
    return shlex.quote(str(path))


@contextlib.contextmanager
def extra_descriptors(lowest: int) -> Iterator[tuple[int, int]]:
    """Both ends of a pipe, as the lowest free descriptors >= `lowest`.

    Skips when RLIMIT_NOFILE leaves no room that high, since then the
    worker cannot hold, and so cannot leak, such a descriptor.
    """
    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft != resource.RLIM_INFINITY and soft < lowest + 2:
        pytest.skip(f"RLIMIT_NOFILE {soft} leaves no fd at {lowest}")
    with contextlib.ExitStack() as stack:
        pipe = os.pipe()
        for end in pipe:
            stack.callback(os.close, end)
        renumbered: list[int] = []
        for end in pipe:
            fd = fcntl.fcntl(end, fcntl.F_DUPFD_CLOEXEC, lowest)
            stack.callback(os.close, fd)
            renumbered.append(fd)
        yield renumbered[0], renumbered[1]


def configure(
    sandbox: Sandbox, command: str, *, section: str = "default"
) -> None:
    sandbox.config.write_text(
        f"[{section}]\ncredential_process = {command}\n", encoding="utf-8"
    )


def credentials_json(identity: str, **extra: object) -> str:
    """The helper document for AKID<identity> / <identity>-secret."""
    document: dict[str, object] = {
        "Version": 1,
        "AccessKeyId": f"AKID{identity}",
        "SecretAccessKey": f"{identity}-secret",
        **extra,
    }
    return json.dumps(document)


def exported(identity: str) -> bytes:
    return export_credentials_output(f"AKID{identity}", f"{identity}-secret")


def printing_script(identity: str) -> str:
    """A /bin/sh helper printing AKID<identity> credentials (no PATH use)."""
    return f"#!/bin/sh\nprintf '%s' '{credentials_json(identity)}'\n"


def emitter(
    sandbox: Sandbox,
    *,
    stdout: bytes = b"",
    stderr: bytes = b"",
    status: int = 0,
) -> str:
    """A helper writing exactly these bytes and exiting with `status`."""
    out = sandbox.write("emit/stdout", stdout)
    err = sandbox.write("emit/stderr", stderr)
    script = sandbox.write(
        "emit/helper",
        f"#!/bin/sh\n/bin/cat {quoted(out)}\n/bin/cat {quoted(err)} >&2\n"
        f"exit {status}\n",
        mode=0o755,
    )
    return quoted(script)


def process_error(text: str) -> str:
    """`str(CredentialRetrievalError)` after the CLI's outer strip()."""
    return f"{PROCESS_ERROR} {text}".strip()


def load_error(message: str) -> bytes:
    return f"{CONFIGURATION_ERROR_PREFIX}{message}\n".encode()


def general_error(message: str) -> bytes:
    return f"{GENERAL_ERROR_PREFIX}{message}\n".encode()


def load_failure(*operands: str) -> BytesStartingWith:
    """A load-time error whose text is CPython's or a library's.

    Only the AWS-authored prefix is the CLI's; the rest (an OSError's
    `[Errno N] ...`, a decoder message) must still name `operands`.
    """
    return BytesStartingWith(
        CONFIGURATION_ERROR_PREFIX.encode(),
        tuple(operand.encode() for operand in operands),
    )


def assert_run(
    run: CliRun,
    expected: tuple[int, bytes, bytes | BytesStartingWith],
    changes: FileChanges | None,
) -> None:
    """Assert rc, stdout, and stderr, no requests, and exactly `changes`.

    `changes` None means the run wrote nothing: only the helpers that keep
    a log write anything.
    """
    assert (run.returncode, run.stdout, run.stderr) == expected, run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == ({} if changes is None else changes), run.describe()


def assert_load_error(
    run: CliRun, message: str, changes: FileChanges | None = None
) -> None:
    assert_run(
        run, (CONFIGURATION_ERROR_RC, b"", load_error(message)), changes
    )


def assert_load_failure(run: CliRun, *operands: str) -> None:
    assert_run(
        run, (CONFIGURATION_ERROR_RC, b"", load_failure(*operands)), None
    )


def assert_general_error(
    run: CliRun, message: str, changes: FileChanges | None = None
) -> None:
    assert_run(run, (GENERAL_ERROR_RC, b"", general_error(message)), changes)


def assert_exported(
    run: CliRun, stdout: bytes, changes: FileChanges | None = None
) -> None:
    assert_run(run, (0, stdout, b""), changes)


def written(relative: str, content: str) -> FileChanges:
    """A run's only change: a helper created `relative` with `content`."""
    return {relative: (CREATED_FILE_MODE, content.encode())}


@dataclass(frozen=True)
class ExecCase:
    command: str
    # What the error must name: the command as configured.
    operand: str


def missing_on_path(sandbox: Sandbox) -> ExecCase:
    name = "nonexistent-cmd-xyz"
    return ExecCase(name, name)


def no_shebang(sandbox: Sandbox) -> ExecCase:
    # execv never falls back to /bin/sh, unlike execvp.
    path = sandbox.write("noshebang.sh", "echo hi\n", mode=0o755)
    return ExecCase(quoted(path), str(path))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(missing_on_path, id="missing-on-path"),
        pytest.param(no_shebang, id="no-shebang"),
    ],
)
async def test_process_exec_failure_fails_at_load(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    build: Callable[[Sandbox], ExecCase],
) -> None:
    case = build(sandbox)
    configure(sandbox, case.command)

    run = await run_process(aws_cli, sandbox, stub, env={"PATH": SYSTEM_PATH})

    # The OSError's text is CPython's and the C library's.
    assert_load_failure(run, case.operand)


@pytest.mark.parametrize(
    "config",
    [
        # Upstream bug, matched for parity: an empty value is not "no
        # process configured" (credentials.py:1087 checks `is None`), and
        # Popen([]) crashes with an IndexError (subprocess.py:1856).
        pytest.param(b"[default]\ncredential_process =\n", id="empty-command"),
        pytest.param(
            b'[default]\ncredential_process = /bin/echo "abc\n',
            id="unclosed-quote",
        ),
    ],
)
async def test_process_command_rejected_before_spawn(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: bytes,
) -> None:
    sandbox.config.write_bytes(config)

    run = await run_process(aws_cli, sandbox, stub, env={"PATH": SYSTEM_PATH})

    # The message is CPython's (IndexError, shlex's ValueError).
    assert_load_failure(run)


def path_fixtures(sandbox: Sandbox) -> None:
    """One `helper` per directory, each failing apart from p2's: p1 is
    0644 and p3 has no shebang."""
    sandbox.write("p1/helper", printing_script("P1"), mode=0o644)
    sandbox.write("p2/helper", printing_script("P2"), mode=0o755)
    sandbox.write("p3/helper", "echo hi\n", mode=0o755)


@pytest.mark.parametrize(
    "first",
    [
        pytest.param("p1", id="eacces-then-runs"),
        # execvp would run p3's script with /bin/sh instead.
        pytest.param("p3", id="enoexec-then-runs"),
    ],
)
async def test_process_path_search_skips_unusable_candidates(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    first: str,
) -> None:
    path_fixtures(sandbox)
    configure(sandbox, "helper")
    search = f"{sandbox.root / first}:{sandbox.root / 'p2'}"

    run = await run_process(aws_cli, sandbox, stub, env={"PATH": search})

    # A candidate that fails to exec moves the search on
    # (_posixsubprocess.c:823-839).
    assert_exported(run, exported("P2"))


@pytest.mark.parametrize("first", ["p1", "p3"])
async def test_process_path_search_signs_listing_with_runnable_candidate(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    first: str,
) -> None:
    path_fixtures(sandbox)
    configure(sandbox, "helper")
    search = f"{sandbox.root / first}:{sandbox.root / 'p2'}"

    run = await listing(aws_cli, sandbox, stub, env={"PATH": search})

    assert_signed(run, "AKIDP2")


@dataclass(frozen=True)
class CwdCase:
    path: str | None
    command: str
    cwd: str
    runs: bool


@pytest.mark.parametrize(
    "case",
    [
        # An empty PATH entry is the cwd (os.get_exec_path splits, so empty
        # entries survive).
        pytest.param(
            CwdCase("/usr/bin::/bin", "cwdhelper", "work", True),
            id="middle-empty-entry",
        ),
        pytest.param(CwdCase("", "cwdhelper", "work", True), id="empty-path"),
        # Unset PATH is os.defpath, /bin:/usr/bin, which has no cwd entry.
        pytest.param(
            CwdCase(None, "sh cwdhelper", "work", True),
            id="unset-path-searches-default",
        ),
        pytest.param(
            CwdCase(SYSTEM_PATH, "cwdhelper", "work", False),
            id="cwd-not-searched",
        ),
        pytest.param(
            CwdCase(SYSTEM_PATH, "work/cwdhelper", ".", True),
            id="relative-from-parent",
        ),
    ],
)
async def test_process_resolves_command_against_cwd(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    case: CwdCase,
) -> None:
    sandbox.write("work/cwdhelper", printing_script("CWD"), mode=0o755)
    configure(sandbox, case.command)

    run = await run_process(
        aws_cli,
        sandbox,
        stub,
        env={"PATH": case.path},
        cwd=sandbox.root / case.cwd,
    )

    if case.runs:
        assert_exported(run, exported("CWD"))
    else:
        assert_load_failure(run, case.command)


@pytest.mark.parametrize(
    ("path", "command", "cwd"),
    [
        pytest.param(
            "/usr/bin::/bin", "cwdhelper", "work", id="middle-empty-entry"
        ),
        pytest.param("", "cwdhelper", "work", id="empty-path"),
        pytest.param(
            None, "sh cwdhelper", "work", id="unset-path-searches-default"
        ),
        pytest.param(
            SYSTEM_PATH, "work/cwdhelper", ".", id="relative-from-parent"
        ),
    ],
)
async def test_process_command_resolved_against_cwd_signs_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    path: str | None,
    command: str,
    cwd: str,
) -> None:
    sandbox.write("work/cwdhelper", printing_script("CWD"), mode=0o755)
    configure(sandbox, command)

    run = await listing(
        aws_cli, sandbox, stub, env={"PATH": path}, cwd=sandbox.root / cwd
    )

    assert_signed(run, "AKIDCWD")


@pytest.mark.parametrize(
    ("body", "stderr"),
    [
        pytest.param(
            "echo about to die >&2\nkill -9 $$\n",
            "about to die",
            id="sigkill-with-stderr",
        ),
        pytest.param(
            f"printf '%s' '{credentials_json('KILLED')}'\nkill -9 $$\n",
            "",
            id="sigkill-after-valid-stdout",
        ),
    ],
)
async def test_process_signal_death_reports_captured_stderr(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    body: str,
    stderr: str,
) -> None:
    helper = sandbox.write("dies.sh", f"#!/bin/sh\n{body}", mode=0o755)
    configure(sandbox, quoted(helper))

    run = await run_process(aws_cli, sandbox, stub)

    # returncode -N is just `!= 0`; the signal never appears
    # (credentials.py:1117-1120).
    assert_load_error(run, process_error(stderr))


async def test_process_helper_reads_inherited_stdin(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, sandbox.helper("stdin.py", STDIN_HELPER))

    run = await run_process(aws_cli, sandbox, stub, stdin=b"piped-data\n")

    assert_exported(
        run, export_credentials_output("STDIN:piped-data", "STDIN-secret")
    )


@pytest.mark.parametrize(
    "extra_fds_from",
    [
        pytest.param(None, id="stdin-pipe"),
        # close_fds=True closes everything above 2, whatever its number.
        pytest.param(3, id="extra-inherited-fds"),
    ],
)
async def test_process_helper_inherits_only_standard_fds(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    extra_fds_from: int | None,
) -> None:
    configure(sandbox, sandbox.helper("fds.py", FD_HELPER))
    with contextlib.ExitStack() as stack:
        extra_fds = (
            ()
            if extra_fds_from is None
            else stack.enter_context(extra_descriptors(extra_fds_from))
        )
        run = await run_process(aws_cli, sandbox, stub, pass_fds=extra_fds)

    assert_exported(run, export_credentials_output("FDS:0,1,2", "FD-secret"))


async def test_process_helper_starts_with_pipe_and_xfsz_restored(
    aws_cli: str, sandbox: Sandbox, stub: Stub, perl: str
) -> None:
    observer = sandbox.write("signals.pl", SIGNAL_OBSERVER)
    configure(sandbox, f"{quoted(perl)} {quoted(observer)}")

    run = await run_process(
        aws_cli, sandbox, stub, launcher=TRAP_PIPE_XFSZ_HUP
    )

    # Started with PIPE, XFSZ, and HUP ignored, the helper gets PIPE and
    # XFSZ back at SIG_DFL (_posixsubprocess.c:757-759) and HUP still
    # ignored.
    assert_exported(run, export_credentials_output("IGNORED:HUP", "s"))


async def test_process_helper_stays_in_cli_process_group(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, sandbox.helper("group.py", PROCESS_GROUP_HELPER))

    run = await run_process(aws_cli, sandbox, stub)

    # No setsid and no setpgid in the child (_posixsubprocess.c:771-779 are
    # skipped).
    assert_exported(
        run, export_credentials_output("SHARED:group,session", "PG-secret")
    )


async def test_process_child_env_passes_user_variables_through(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    keys = [*PROVIDER_OWNED_ENV, "USER_VARIABLE"]
    helper = sandbox.helper("env.py", ENV_HELPER)
    configure(sandbox, f"{helper} {shlex.join(keys)}")

    run = await run_process(aws_cli, sandbox, stub, env={"USER_VARIABLE": "5"})

    # A user's variable reaches the helper unchanged, and the recursion
    # barrier adds the profile chain (exportcreds.py:240-268;
    # test_export_credentials_command.py owns its format). The helper
    # records them in helper-env.json in argv order.
    seen = {"_AWS_CLI_PROFILE_CHAIN": "default", "USER_VARIABLE": "5"}
    assert_exported(
        run,
        export_credentials_output("AKIDENV", "ENV-secret"),
        written("helper-env.json", json.dumps(seen)),
    )


@pytest.mark.parametrize(
    ("arguments", "argv"),
    [
        pytest.param(
            "'one two' '$HOME' '*' ';'",
            ["one two", "$HOME", "*", ";"],
            id="quoted-literals",
        ),
        pytest.param('"#x" #y', ["#x", "#y"], id="hash-is-literal"),
        pytest.param("x ;y", ["x", ";y"], id="no-inline-comment"),
        pytest.param('"" a', ["", "a"], id="empty-quoted-token"),
        pytest.param('"a\\b"', ["a\\b"], id="double-quoted-backslash"),
        pytest.param('"a\\"b"', ['a"b'], id="double-quoted-escaped-quote"),
        pytest.param('"a\\$b"', ["a\\$b"], id="double-quoted-dollar-kept"),
        pytest.param("'a\\b'", ["a\\b"], id="single-quoted-backslash"),
        pytest.param("a\\b", ["ab"], id="unquoted-escape"),
        pytest.param('a"b c"d', ["ab cd"], id="segments-concatenate"),
        pytest.param(
            "a\x0bb c\x0cd",
            ["a\x0bb", "c\x0cd"],
            id="vertical-tab-and-form-feed-are-word-characters",
        ),
        pytest.param(
            "~ ~/x $HOME ${HOME}",
            ["~", "~/x", "$HOME", "${HOME}"],
            id="no-expansion",
        ),
    ],
)
async def test_process_command_split_by_posix_shlex(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    arguments: str,
    argv: list[str],
) -> None:
    configure(sandbox, f"{sandbox.helper('argv.py', ARGV_HELPER)} {arguments}")

    run = await run_process(aws_cli, sandbox, stub)

    # shlex.split(s), comments off and posix on (compat.py:176-183).
    assert_exported(
        run,
        export_credentials_output("AKIDARGV", "ARGV-secret"),
        written("argv.json", json.dumps(argv)),
    )


CONFIG_SHAPE_ROWS = [
    # RawConfigParser joins continuation lines with "\n"; shlex then
    # treats it as whitespace.
    pytest.param(
        "credential_process = {helper} first\n  --flag\n",
        ["first", "--flag"],
        id="continuation-line",
    ),
    # `\<LF>` keeps the newline, unlike sh.
    pytest.param(
        "credential_process = {helper} a\\\n  b\n",
        ["a\nb"],
        id="escaped-newline",
    ),
    # Option names are lowercased (configloader.py:109-200).
    pytest.param(
        "CREDENTIAL_PROCESS = {helper} upper\n", ["upper"], id="upper-key"
    ),
]


@pytest.mark.parametrize(
    ("template", "argv"),
    CONFIG_SHAPE_ROWS,
)
async def test_process_config_value_shapes_reach_helper_argv(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    template: str,
    argv: list[str],
) -> None:
    helper = sandbox.helper("argv.py", ARGV_HELPER)
    sandbox.config.write_text(
        "[default]\n" + template.format(helper=helper), encoding="utf-8"
    )

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(
        run,
        export_credentials_output("AKIDARGV", "ARGV-secret"),
        written("argv.json", json.dumps(argv)),
    )


@pytest.mark.parametrize(("template", "argv"), CONFIG_SHAPE_ROWS)
async def test_process_config_value_shapes_sign_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    template: str,
    argv: list[str],
) -> None:
    helper = sandbox.helper("argv.py", ARGV_HELPER)
    sandbox.config.write_text(
        "[default]\n" + template.format(helper=helper), encoding="utf-8"
    )

    run = await listing(aws_cli, sandbox, stub)

    assert_signed(run, "AKIDARGV")


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        pytest.param(
            b"boom line1\nline2\n",
            load_error(process_error("boom line1\nline2")),
            id="multi-line-stderr",
        ),
        pytest.param(b"", load_error(process_error("")), id="empty-stderr"),
        # Upstream bug, matched for parity: stderr.decode('utf-8') is
        # strict and unwrapped (credentials.py:1117-1120), so a helper's
        # non-UTF-8 stderr becomes CPython's codec error, not the process
        # error.
        pytest.param(b"\xff", load_failure(), id="non-utf8-stderr"),
    ],
)
async def test_process_nonzero_exit_ignores_stdout_and_reports_stderr(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    stderr: bytes,
    expected: bytes | BytesStartingWith,
) -> None:
    command = emitter(
        sandbox,
        stdout=credentials_json("IGNORED").encode(),
        stderr=stderr,
        status=1,
    )
    configure(sandbox, command)

    run = await run_process(aws_cli, sandbox, stub)

    assert_run(run, (CONFIGURATION_ERROR_RC, b"", expected), None)


async def test_process_success_discards_stderr(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    command = emitter(
        sandbox,
        stdout=credentials_json("NOISY").encode(),
        stderr=b"warning: ignored\n",
    )
    configure(sandbox, command)

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, exported("NOISY"))


async def test_process_success_with_stderr_signs_listing(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    command = emitter(
        sandbox,
        stdout=credentials_json("NOISY").encode(),
        stderr=b"warning: ignored\n",
    )
    configure(sandbox, command)

    run = await listing(aws_cli, sandbox, stub)

    assert_signed(run, "AKIDNOISY")


async def test_process_non_utf8_stdout_fails_at_load(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, emitter(sandbox, stdout=b"\xff"))

    run = await run_process(aws_cli, sandbox, stub)

    # stdout.decode('utf-8') is strict (credentials.py:1121); the codec's
    # message is CPython's.
    assert_load_failure(run)


@pytest.mark.parametrize(
    "stdout",
    [
        pytest.param(b"", id="empty"),
        # A lenient reader would take the first value and ignore the rest.
        pytest.param(b'{"a":1}x', id="extra"),
    ],
)
async def test_process_stdout_not_one_json_document_fails_at_load(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    stdout: bytes,
) -> None:
    configure(sandbox, emitter(sandbox, stdout=stdout))

    run = await run_process(aws_cli, sandbox, stub)

    # The decoder's message is CPython's json module's.
    assert_load_failure(run)


# Upstream bug, matched for parity: a document that is not an object
# crashes on parsed.get('Version', ...) (credentials.py:1122) with an
# AttributeError instead of a process error.
async def test_process_non_object_document_fails_at_load(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, emitter(sandbox, stdout=b"[1]"))

    run = await run_process(aws_cli, sandbox, stub)

    assert_load_failure(run)


async def test_process_document_surrounded_by_json_whitespace_parses(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    document = b" \t\n" + credentials_json("SPACED").encode() + b"\n\r "
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, exported("SPACED"))


async def test_process_document_surrounded_by_json_whitespace_signs_listing(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    document = b" \t\n" + credentials_json("SPACED").encode() + b"\n\r "
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await listing(aws_cli, sandbox, stub)

    assert_signed(run, "AKIDSPACED")


def version_document(version: str | None) -> bytes:
    """Valid keys with `"Version": <version>`; None leaves the key out."""
    fields = '"AccessKeyId": "AKIDVER", "SecretAccessKey": "VER-secret"'
    if version is None:
        return f"{{{fields}}}".encode()
    return f'{{"Version": {version}, {fields}}}'.encode()


async def test_process_version_equal_to_one_is_accepted(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # `version != 1` under JSON number equality (credentials.py:1123).
    configure(sandbox, emitter(sandbox, stdout=version_document("1.0")))

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, export_credentials_output("AKIDVER", "VER-secret"))


@pytest.mark.parametrize(
    ("document", "rendered"),
    [
        pytest.param(
            version_document(None),
            "<Version key not provided>",
            id="missing",
        ),
        pytest.param(version_document("2"), "2", id="two"),
        pytest.param(version_document('"1"'), "1", id="string-one"),
        # The version check runs before the required keys.
        pytest.param(b'{"Version": 2}', "2", id="before-required-keys"),
    ],
)
async def test_process_unsupported_version_is_rejected(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    document: bytes,
    rendered: str,
) -> None:
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await run_process(aws_cli, sandbox, stub)

    assert_load_error(
        run,
        process_error(
            f"Unsupported version '{rendered}' for credential process "
            "provider, supported versions: 1"
        ),
    )


async def test_process_duplicate_version_last_one_accepted(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    document = (
        b'{"Version": 2, "AccessKeyId": "AKIDVER", '
        b'"SecretAccessKey": "VER-secret", "Version": 1}'
    )
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, export_credentials_output("AKIDVER", "VER-secret"))


@pytest.mark.parametrize(
    "document",
    [
        pytest.param(version_document("1.0"), id="version-equal-to-one"),
        pytest.param(
            b'{"Version": 2, "AccessKeyId": "AKIDVER", '
            b'"SecretAccessKey": "VER-secret", "Version": 1}',
            id="duplicate-version-last-one",
        ),
    ],
)
async def test_process_accepted_version_signs_listing(
    aws_cli: str, sandbox: Sandbox, stub: Stub, document: bytes
) -> None:
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await listing(aws_cli, sandbox, stub)

    assert_signed(run, "AKIDVER")


@pytest.mark.parametrize(
    ("document", "key"),
    [
        pytest.param(
            b'{"Version": 1, "SecretAccessKey": "s"}',
            "AccessKeyId",
            id="access-key",
        ),
        pytest.param(
            b'{"Version": 1, "AccessKeyId": "a"}',
            "SecretAccessKey",
            id="secret-key",
        ),
    ],
)
async def test_process_missing_required_key_names_it(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    document: bytes,
    key: str,
) -> None:
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await run_process(aws_cli, sandbox, stub)

    # The key's quoting is `str(KeyError)`'s (credentials.py:1139-1143).
    prefix = (
        f"{CONFIGURATION_ERROR_PREFIX}{PROCESS_ERROR} "
        "Missing required key in response: "
    )
    assert_run(
        run,
        (
            CONFIGURATION_ERROR_RC,
            b"",
            BytesStartingWith(prefix.encode(), (key.encode(),)),
        ),
        None,
    )


def values_document(field: str, value: str) -> bytes:
    """A version-1 document whose `field` holds the raw JSON `value`."""
    fields = {
        "AccessKeyId": '"AKIDVAL"',
        "SecretAccessKey": '"VAL-secret"',
        field: value,
    }
    body = ", ".join(f'"{name}": {text}' for name, text in fields.items())
    return f'{{"Version": 1, {body}}}'.encode()


# Values a credential field may hold: there is no type or emptiness
# validation (credentials.py:1131-1138), and `--format process` prints
# what json.loads made of them (exportcreds.py:140-153).
@pytest.mark.parametrize(
    ("field", "text", "stdout"),
    [
        pytest.param(
            "AccessKeyId",
            '""',
            export_credentials_output("", "VAL-secret"),
            id="access-key-empty",
        ),
        pytest.param(
            "AccessKeyId",
            '"AKIDé中"',
            export_credentials_output("AKIDé中", "VAL-secret"),
            id="access-key-raw-non-ascii",
        ),
        # Upstream bug, matched for parity: a NaN access key is printed as
        # a bare NaN, which is not JSON (json.dumps allows NaN).
        pytest.param(
            "AccessKeyId",
            "NaN",
            b'{\n  "Version": 1,\n  "AccessKeyId": NaN,\n'
            b'  "SecretAccessKey": "VAL-secret"\n}\n',
            id="access-key-nan",
        ),
        pytest.param(
            "SessionToken",
            '""',
            export_credentials_output("AKIDVAL", "VAL-secret", ""),
            id="session-token-empty-kept",
        ),
        pytest.param(
            "SessionToken",
            "null",
            export_credentials_output("AKIDVAL", "VAL-secret"),
            id="session-token-null-omitted",
        ),
        pytest.param(
            "Unknown",
            '{"x": [1]}',
            export_credentials_output("AKIDVAL", "VAL-secret"),
            id="extra-key",
        ),
    ],
)
async def test_process_credential_values_pass_through_unvalidated(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    field: str,
    text: str,
    stdout: bytes,
) -> None:
    configure(sandbox, emitter(sandbox, stdout=values_document(field, text)))

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, stdout)


# The values above that botocore can sign with. An empty token sends no
# header: SigV4Auth adds it only when truthy (botocore/auth.py:458-461).
@pytest.mark.parametrize(
    ("field", "text", "access_key", "token"),
    [
        pytest.param("AccessKeyId", '""', "", None, id="access-key-empty"),
        pytest.param(
            "AccessKeyId",
            '"AKIDé中"',
            "AKIDé中",
            None,
            id="access-key-raw-non-ascii",
        ),
        pytest.param(
            "SessionToken", '"SESS"', "AKIDVAL", "SESS", id="session-token"
        ),
        pytest.param(
            "SessionToken", '""', "AKIDVAL", None, id="session-token-empty"
        ),
        pytest.param(
            "SessionToken", "null", "AKIDVAL", None, id="session-token-null"
        ),
        pytest.param("Unknown", '{"x": [1]}', "AKIDVAL", None, id="extra-key"),
    ],
)
async def test_process_credential_values_sign_listing_unvalidated(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    field: str,
    text: str,
    access_key: str,
    token: str | None,
) -> None:
    configure(sandbox, emitter(sandbox, stdout=values_document(field, text)))

    run = await listing(aws_cli, sandbox, stub)

    assert_signed(run, access_key, token)


async def test_process_unparseable_expiration_fails_at_load(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    document = values_document("Expiration", '"garbage"')
    configure(sandbox, emitter(sandbox, stdout=document))

    run = await run_process(aws_cli, sandbox, stub)

    # create_from_metadata parses any non-None Expiration with dateutil
    # (credentials.py:440-464, 629-631), inside load(); the parser's
    # message is dateutil's.
    assert_load_failure(run)


Step = dict[str, object]


def step(stdout: str = "", stderr: str = "", status: int = 0) -> Step:
    return {"stdout": stdout, "stderr": stderr, "status": status}


def sequence(sandbox: Sandbox, *steps: Step) -> str:
    """The SEQUENCE_HELPER command playing `steps`."""
    sandbox.write("steps.json", json.dumps(list(steps)))
    return sandbox.helper("sequence.py", SEQUENCE_HELPER)


def utc_in(minutes: float) -> str:
    """`now + minutes` in whole seconds as `YYYY-MM-DDTHH:MM:SSZ`.

    Fixed when the test builds its fixtures, so the expected output is
    known before the run. The command starts within seconds, so every
    offset used here stays at least 60 s from the 10- and 15-minute window
    edges.
    """
    moment = datetime.now(UTC).replace(microsecond=0)
    return (moment + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def printed_expiration(text: str) -> str:
    """isoformat() of a `...Z` expiry (credentials.py:629-631)."""
    assert text.endswith("Z"), text
    return text[:-1] + "+00:00"


def old_step(expiration: str) -> Step:
    return step(
        credentials_json(
            "OLD", SessionToken="OLD-token", Expiration=expiration
        )
    )


def new_step(**fields: object) -> Step:
    return step(credentials_json("NEW", SessionToken="NEW-token", **fields))


def old_output(expiration: str) -> bytes:
    return export_credentials_output(
        "AKIDOLD", "OLD-secret", "OLD-token", printed_expiration(expiration)
    )


def helper_calls(count: int) -> FileChanges:
    """calls.jsonl after `count` helper runs, each seeing the run's profile
    chain (exportcreds.py:266-268 sets it once, before resolving)."""
    log = "".join(
        json.dumps({"call": index, "chain": "default"}) + "\n"
        for index in range(count)
    )
    return written("calls.jsonl", log)


@pytest.mark.parametrize(
    ("minutes", "refreshed"),
    [
        # Mandatory (< 10 min) and advisory (< 15 min) windows
        # (credentials.py:77-78, 560-588).
        pytest.param(-1, lambda: FUTURE_EXPIRATION, id="expired"),
        pytest.param(5, lambda: FUTURE_EXPIRATION, id="mandatory"),
        # One refresh only, even when the new expiry is advisory too.
        pytest.param(12, lambda: utc_in(13), id="advisory-to-advisory"),
    ],
)
async def test_process_refresh_window_respawns_and_prints_new_credentials(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    minutes: float,
    refreshed: Callable[[], str],
) -> None:
    expiration = refreshed()
    command = sequence(
        sandbox, old_step(utc_in(minutes)), new_step(Expiration=expiration)
    )
    configure(sandbox, command)

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(
        run,
        export_credentials_output(
            "AKIDNEW",
            "NEW-secret",
            "NEW-token",
            printed_expiration(expiration),
        ),
        helper_calls(2),
    )


async def test_process_advisory_refresh_failure_keeps_old_credentials(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    expiration = utc_in(12)
    failure = step(stderr="nope\n", status=1)
    configure(sandbox, sequence(sandbox, old_step(expiration), failure))

    run = await run_process(aws_cli, sandbox, stub)

    # A failure inside _refresh_using (credentials.py:590-611) is
    # swallowed in the advisory window and logged to botocore's
    # NullHandler only, so nothing reaches stderr.
    assert_exported(run, old_output(expiration), helper_calls(2))


@pytest.mark.parametrize(
    ("minutes", "failure", "message"),
    [
        pytest.param(
            5,
            step(stderr="nope\n", status=1),
            process_error("nope"),
            id="exit-1-mandatory",
        ),
        pytest.param(
            -1,
            step(credentials_json("NEW", Version=2)),
            process_error(
                "Unsupported version '2' for credential process provider, "
                "supported versions: 1"
            ),
            id="version-2-expired",
        ),
    ],
)
async def test_process_mandatory_refresh_failure_is_raised_raw(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    minutes: float,
    failure: Step,
    message: str,
) -> None:
    configure(sandbox, sequence(sandbox, old_step(utc_in(minutes)), failure))

    run = await run_process(aws_cli, sandbox, stub)

    assert_general_error(run, message, helper_calls(2))


# Upstream bug, matched for parity: a refreshed document without
# Expiration reaches dateutil's parse() as None (credentials.py:650),
# outside the try, so it fails even in the advisory window, where a failed
# refresh is otherwise swallowed. The TypeError's text is dateutil's.
async def test_process_refresh_without_expiration_fails(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, sequence(sandbox, old_step(utc_in(12)), new_step()))

    run = await run_process(aws_cli, sandbox, stub)

    assert_run(
        run,
        (
            GENERAL_ERROR_RC,
            b"",
            BytesStartingWith(GENERAL_ERROR_PREFIX.encode()),
        ),
        helper_calls(2),
    )


async def test_process_still_expired_after_refresh_from_past_expiry(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, sequence(sandbox, old_step(PAST_EXPIRATION)))

    run = await run_process(aws_cli, sandbox, stub)

    assert_general_error(run, STILL_EXPIRED, helper_calls(2))


async def test_process_drains_stdout_and_stderr_concurrently(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    configure(sandbox, sandbox.helper("large.py", LARGE_OUTPUT_HELPER))

    run = await run_process(aws_cli, sandbox, stub)

    # communicate() polls both pipes until both reach EOF, so 2 MiB of
    # stderr ahead of stdout cannot deadlock.
    assert_exported(
        run, export_credentials_output("AKIDLARGE", "LARGE-secret")
    )


async def test_process_reads_output_until_every_writer_closes(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # The helper exits at once; a background child it leaves holding the
    # pipes writes the document a second later.
    late = (
        "#!/bin/sh\n"
        f"( sleep 1; printf '%s' '{credentials_json('LATE')}' ) &\n"
        "exit 0\n"
    )
    configure(sandbox, quoted(sandbox.write("late.sh", late, mode=0o755)))

    run = await run_process(aws_cli, sandbox, stub)

    assert_exported(run, exported("LATE"))


async def test_process_sigint_while_helper_runs_exits_130(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    # The helper interrupts its parent, then outlives CPython's 0.25 s
    # child wait (subprocess.py:1222-1234) without writing anything.
    interrupt = "#!/bin/sh\nkill -INT $PPID\nsleep 1\n"
    helper = sandbox.write("interrupt.sh", interrupt, mode=0o755)
    configure(sandbox, quoted(helper))

    run = await run_process(aws_cli, sandbox, stub)

    assert_run(run, (INTERRUPT_RC, b"\n", b""), None)


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


ENV_KEYS = {
    "AWS_ACCESS_KEY_ID": "AKIDENV",
    "AWS_SECRET_ACCESS_KEY": "ENV-secret",
}


def without(payload: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in payload.items() if name != key}


def printed(payload: dict[str, object]) -> str:
    return f"print({json.dumps(payload)!r})\n"


def process_profile(command: str, section: str = "default") -> str:
    return f"[{section}]\ncredential_process = {command}\n"


def process_calls(log: Path) -> list[list[str]]:
    return [json.loads(line) for line in log.read_text().splitlines()]


@pytest.mark.parametrize(
    ("source", "token"),
    [
        pytest.param(
            printed(process_credentials()), "PROCESS-token", id="static"
        ),
        pytest.param(
            printed(
                {**process_credentials(), "Expiration": "2099-01-01T00:00:00Z"}
            ),
            "PROCESS-token",
            id="expiring",
        ),
        pytest.param(
            printed(without(process_credentials(), "SessionToken")),
            None,
            id="no-token",
        ),
        pytest.param(
            printed(process_credentials())
            + 'print("warning", file=sys.stderr)\n',
            "PROCESS-token",
            id="stderr",
        ),
    ],
)
async def test_credentials_process_output_signs_with_process_credentials(
    aws_cli: str, tmp_path: Path, source: str, token: str | None
) -> None:
    command, log = credential_process(tmp_path, source)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "PROCESS", token)
    assert process_calls(log) == [[]]


async def test_credentials_process_command_line_passes_quoted_arguments(
    aws_cli: str, tmp_path: Path
) -> None:
    arguments = ["one two", "$HOME", "*", ";"]
    command, log = json_process(tmp_path, process_credentials())
    command += " " + command_line(arguments)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "PROCESS", "PROCESS-token")
    assert process_calls(log) == [arguments]


async def test_credentials_process_in_shared_file_signs_with_process(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command), shared=True)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "PROCESS", "PROCESS-token")
    assert process_calls(log) == [[]]


async def test_credentials_process_explicit_profile_precedes_environment(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command, "profile selected"))
        env.update(ENV_KEYS)
        result = await list_bucket(
            aws_cli, server, env, "--profile", "selected"
        )
    assert_signed_by(result, server, "PROCESS", "PROCESS-token")
    assert process_calls(log) == [[]]


async def test_credentials_shared_keys_precede_process_without_running_it(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        write_config(
            env, "[default]\n" + file_credentials("SHARED"), shared=True
        )
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "SHARED")
    assert not log.exists()


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            printed(without(process_credentials(), "Version")),
            id="missing-version",
        ),
        pytest.param(
            printed({**process_credentials(), "Version": 2}),
            id="wrong-version",
        ),
        pytest.param(
            printed({**process_credentials(), "Version": "1"}),
            id="string-version",
        ),
        pytest.param(
            printed(without(process_credentials(), "AccessKeyId")),
            id="missing-key",
        ),
        pytest.param(
            printed(without(process_credentials(), "SecretAccessKey")),
            id="missing-secret",
        ),
        pytest.param("print('not json')\n", id="invalid-json"),
        pytest.param(
            printed(process_credentials())
            + "print('credential helper failed', file=sys.stderr)\n"
            "sys.exit(1)\n",
            id="nonzero-exit",
        ),
        pytest.param(
            printed(
                {**process_credentials(), "Expiration": "2000-01-01T00:00:00Z"}
            ),
            id="expired",
        ),
    ],
)
async def test_credentials_process_errors_fail_before_request(
    aws_cli: str, tmp_path: Path, source: str
) -> None:
    command, log = credential_process(tmp_path, source)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert log.exists()
    assert_credential_error(result, server)


@pytest.mark.parametrize("minutes", [-1, 5, 12], ids=["expired", "5", "12"])
async def test_credentials_process_refresh_before_signing_uses_new_credentials(
    aws_cli: str, tmp_path: Path, minutes: int
) -> None:
    expiration = datetime.now(UTC) + timedelta(minutes=minutes)
    old = {**process_credentials("OLD"), "Expiration": expiration.isoformat()}
    new = {**process_credentials("NEW"), "Expiration": "2099-01-01T00:00:00Z"}
    command, log = credential_process(
        tmp_path,
        f"print({json.dumps(old)!r} if calls == 0 else {json.dumps(new)!r})\n",
    )
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "NEW", "NEW-token")
    assert len(log.read_text().splitlines()) == 2


def failing_refresh_process(tmp_path: Path, minutes: int) -> tuple[str, Path]:
    # Botocore retries within its 15-minute advisory window but only makes
    # a failed refresh fatal inside the 10-minute mandatory window. Use
    # minutes of margin instead of sleeping across a wall-clock boundary.
    expiration = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {
        **process_credentials(),
        "Expiration": expiration.isoformat(),
    }
    return credential_process(
        tmp_path,
        "if calls:\n"
        "    print('refresh failed', file=sys.stderr)\n"
        "    sys.exit(1)\n"
        f"print({json.dumps(payload)!r})\n",
    )


async def test_credentials_process_refresh_failure_in_mandatory_window_fails(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = failing_refresh_process(tmp_path, 5)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)
    assert len(log.read_text().splitlines()) >= 2


async def test_credentials_process_refresh_failure_in_advisory_window_signs(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = failing_refresh_process(tmp_path, 12)
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "PROCESS", "PROCESS-token")
    assert len(log.read_text().splitlines()) >= 2


async def test_credentials_unsigned_skips_process(
    aws_cli: str, tmp_path: Path
) -> None:
    command, log = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env, "--no-sign-request")
    assert result[2] == 0, result[1].decode()
    assert len(server.requests) == 1
    assert "authorization" not in server.requests[0].headers
    assert "x-amz-security-token" not in server.requests[0].headers
    assert not log.exists()


# A helper that inherits SIGPIPE ignored keeps it ignored across `exec`, so a
# pipeline such as `yes | head -n1` inside it never stops. The AWS CLI runs
# the helper through `subprocess`, which restores the default action. This
# helper reads its own ignored-signal mask from /proc, records it, and fails
# at once when SIGPIPE is in it, so the test cannot hang.
POSIX_SHELL = shutil.which("sh")
# Bit 12 of /proc's SigIgn mask is signal 13, SIGPIPE.
SIGPIPE_MASK = 1 << 12
SIGPIPE_HELPER = r"""ignored=
while read -r name value; do
    if [ "$name" = "SigIgn:" ]; then ignored=$value; fi
done < "/proc/$$/status"
printf '%s\n' "$ignored" > "$1"
if [ -z "$ignored" ]; then
    echo "no SigIgn line in /proc/$$/status" >&2
    exit 2
fi
if [ $(( 0x$ignored & 0x1000 )) -ne 0 ]; then
    echo "SIGPIPE is ignored: SigIgn $ignored" >&2
    exit 1
fi
printf '%s%s\n' '{"Version": 1, "AccessKeyId": "AKIDHELPER",' \
    ' "SecretAccessKey": "HELPER-secret"}'
"""


@pytest.mark.skipif(
    POSIX_SHELL is None or not Path("/proc/self/status").exists(),
    reason="needs sh and /proc/<pid>/status",
)
async def test_credentials_process_starts_with_default_sigpipe(
    aws_cli: str, tmp_path: Path
) -> None:
    helper = tmp_path / "sigpipe helper.sh"
    helper.write_text(SIGPIPE_HELPER, encoding="utf-8")
    record = tmp_path / "helper-sigign.txt"
    command = command_line([str(POSIX_SHELL), str(helper), str(record)])
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        result = await list_bucket(aws_cli, server, env)
    assert record.exists(), f"the helper never ran: {result!r}"
    ignored = record.read_text(encoding="utf-8").strip()
    assert int(ignored, 16) & SIGPIPE_MASK == 0, (
        f"helper inherited SIGPIPE ignored (SigIgn {ignored})"
    )
    assert_signed_by(result, server, "HELPER")


# This setting is already guarded by native admission: in auto mode
# this is a fallback regression test, and in forced-native mode it
# describes a missing capability.
async def test_credentials_guarded_process_precedes_config_keys(
    aws_cli: str, tmp_path: Path
) -> None:
    command, _ = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(
            env,
            "[default]\n"
            + file_credentials("CONFIG")
            + f"credential_process = {command}\n",
        )
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "PROCESS", "PROCESS-token")
