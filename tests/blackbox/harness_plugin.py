"""Pytest plugin run.py loads into both blackbox test sessions.

Upstream's blackbox tests run unmodified, with the environment upstream's
`cli_env` gives every command, against one AWS CLI binary. This plugin gives
every command the OS plumbing a Windows child needs, the variables run.py's
`--env` sets, and the default signal state a POSIX child expects, folds
Windows line endings back to the LF the tests assert on, skips the tests
upstream skips on Windows and the `native_only` tests when the binary is
another AWS CLI or `--env` forces the Python route, marks the entries of the
ledgers the runner applies as strict expected failures on the route they
fail on, and ends the run with their summary, which warns when another
process held the CRT process lock as it started. It also gives the tests
run.py's description of the build (`BUILD`).
"""

from __future__ import annotations

import json
import os
import signal
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import awscrt.s3
import pytest
import tests.blackbox.utils

# The result ledger is shared with the other harnesses and lives one level
# up. Append rather than prepend: tests/ holds sibling directories that
# would otherwise register as namespace packages for names like `argparse`.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from expectations import (
    ExpectationKind,
    ExpectedResult,
    counted_tests,
    python_router_forced,
    read_combined_expectations,
)

_EXPECTATIONS_ENV_VAR: Final = "AWS_BLACKBOX_EXPECTATIONS"
_COMMAND_ENVIRONMENT_ENV_VAR: Final = "AWS_BLACKBOX_COMMAND_ENVIRONMENT"
# run.py sets it to `external` when the binary is another AWS CLI.
_BINARY_KIND_ENV_VAR: Final = "AWS_BLACKBOX_BINARY_KIND"
# run.py describes the build here, as JSON.
_BUILD_ENV_VAR: Final = "AWS_BLACKBOX_BUILD"
_NATIVE_ONLY_SKIP_REASON: Final = (
    "native_only: asserts behavior only the built binary has"
)
_PYTHON_ROUTE_SKIP_REASON: Final = (
    "native_only: asserts the native route, and --env forces the Python one"
)
# The variable that selects the built binary's route.
_ROUTER_ENV_VAR: Final = "AWS_CLI_NATIVE_ROUTER"
_SELECTED_EXPECTATIONS_KEY: Final = pytest.StashKey[
    dict[str, ExpectedResult]
]()
_CRT_PROCESS_LOCK_HELD_KEY: Final = pytest.StashKey[bool]()

# The name upstream's TransferManagerFactory locks while it runs the CRT
# client (awscli/customizations/s3/factory.py).
_CRT_PROCESS_LOCK_NAME: Final = "aws-cli"

# The run's summary: what each ledger's entries did, by their category.
_SUMMARY_LINES: Final = (
    (
        ExpectationKind.SHARED_HARNESS_FAILURE,
        "Upstream failures: {} failed (the public AWS CLI fails them too)",
    ),
    (
        ExpectationKind.UPSTREAM_ISSUE,
        "Upstream issues: {} failed (the public AWS CLI fails them too)",
    ),
    (
        ExpectationKind.PARITY_GAP,
        "Known native gaps: {} failed (the public AWS CLI passes them)",
    ),
    (
        ExpectationKind.LAUNCHER_DIFFERENCE,
        "Launcher differences: {} failed (the public AWS CLI passes them)",
    ),
)

_upstream_run_cli = tests.blackbox.utils.run_cli

# Every test hands `run_cli` the command's whole environment, built from
# scratch by `cli_env` or by the test itself. POSIX survives that, but a
# Windows child does not: WinSock and _ssl cannot initialize without
# SystemRoot, Path.home() reads USERPROFILE and never HOME, and the
# interpreter, built without _wmi, reads platform.machine() from the
# PROCESSOR_* pair. Forward the runner's own OS plumbing, and only that: no
# AWS_*, *_PROXY, SSL_* or PYTHON* name leaks in from the shell.
# TZ joins them because run.py pins it on Windows, and the expected local
# times this process computes must match the child's.
_WINDOWS_ENVIRONMENT_PASSTHROUGH: Final = (
    "ComSpec",
    "HOMEDRIVE",
    "HOMEPATH",
    "PROCESSOR_ARCHITECTURE",
    "PROCESSOR_ARCHITEW6432",
    "SystemRoot",
    "TEMP",
    "TMP",
    "TZ",
    "USERPROFILE",
)
HOST_ENVIRONMENT: Final[dict[str, str]] = (
    {
        name: os.environ[name]
        for name in _WINDOWS_ENVIRONMENT_PASSTHROUGH
        if name in os.environ
    }
    if os.name == "nt"
    else {}
)
# The variables run.py's `--env` sets in every command's environment, over
# whatever the test sets there, such as the router variable that sends each
# command down one route.
COMMAND_ENVIRONMENT: Final[dict[str, str]] = json.loads(
    os.environ.get(_COMMAND_ENVIRONMENT_ENV_VAR, "{}")
)
# Whether `--env` sends every command down the Python route, where a native
# gap's test passes and the native route's own tests do not apply.
PYTHON_ROUTE: Final = python_router_forced(
    COMMAND_ENVIRONMENT.get(_ROUTER_ENV_VAR)
)


@dataclass(frozen=True)
class Build:
    """The build the binary came from, as run.py describes it: the static
    build, or a system build, which links the system's libpython of
    `python_abi`, links the CRT statically or shared, and runs the embedded
    or the system's AWS CLI."""

    link_mode: str = "static"
    crt_link: str = "static"
    python_payload: str = "embedded"
    python_abi: str | None = None


# The build whose executable and payload the tests check.
BUILD: Final = Build(**json.loads(os.environ.get(_BUILD_ENV_VAR, "{}")))

# On Windows both routes write each text '\n' as '\r\n', as the AWS CLI
# release does, and every test asserts on bare '\n'. Folding '\r\n' back is
# the exact inverse of that translation, and it leaves the bare '\r' of a
# progress redraw alone. test_payload.py reads the CRLF bytes as written.
_CHILD_TRANSLATES_NEWLINES: Final = os.name == "nt"

# Upstream skips these on Windows in tests/functional/s3/test_sync_command.py
# ("Can't rename to same file"), but not in their blackbox copies. On a
# case-insensitive filesystem the two keys download concurrently to one
# file, so one rename races the other and either route fails with
# WinError 183 on some runs. The ledger cannot hold them: its expected
# failures are strict, and these pass on other runs.
_WINDOWS_SKIP_REASON: Final = (
    "upstream skips on Windows: can't rename to same file"
)
_WINDOWS_SKIPS: Final = frozenset(
    "tests/blackbox/test_sync_command.py::TestSyncCaseConflict::" + name
    for name in (
        "test_warn_with_case_conflicts_in_s3",
        "test_ignore_with_case_conflicts_in_s3",
    )
)


def _streams_payload_to_stdout(args: Sequence[str]) -> bool:
    """Whether the command's stdout is an object's bytes rather than text.

    `s3 cp s3://bucket/key -` writes the download to stdout untranslated on
    both routes, so a payload's own '\\r\\n' arrives as written and must not
    be folded. Its progress and errors still go to stderr as text.
    """
    for index in range(len(args) - 1):
        if (args[index], args[index + 1]) == ("s3", "cp"):
            operands = list(args[index + 2 :])
            remote = [
                position
                for position, operand in enumerate(operands)
                if operand.startswith("s3://")
            ]
            return bool(remote) and "-" in operands[remote[0] + 1 :]
    return False


def command_environment(env: Mapping[str, str]) -> dict[str, str]:
    """`env` with the variables run.py's `--env` sets, over its own."""
    return {**env, **COMMAND_ENVIRONMENT}


def child_environment(env: Mapping[str, str]) -> dict[str, str]:
    """`command_environment(env)` plus the OS plumbing a Windows child needs
    to start.

    A name `env` already sets keeps its value over the plumbing, so a test
    that isolates the home directory still does.
    """
    return command_environment({**HOST_ENVIRONMENT, **env})


def fold_newlines(
    args: Sequence[str], stdout: bytes, stderr: bytes
) -> tuple[bytes, bytes]:
    """The command's output with Windows line endings folded back to LF.

    `args` is the command line, which tells whether stdout is a payload
    that must keep its bytes. Elsewhere the output is returned unchanged.
    """
    if not _CHILD_TRANSLATES_NEWLINES:
        return stdout, stderr
    if not _streams_payload_to_stdout(args):
        stdout = stdout.replace(b"\r\n", b"\n")
    return stdout, stderr.replace(b"\r\n", b"\n")


async def _run_cli(
    aws_cli: str,
    args: list[str],
    env: dict[str, str],
    **options: Any,
) -> tuple[bytes, bytes, int]:
    """Upstream's launcher, with Windows plumbing and LF line endings."""
    stdout, stderr, returncode = await _upstream_run_cli(
        aws_cli, args, child_environment(env), **options
    )
    stdout, stderr = fold_newlines(args, stdout, stderr)
    return stdout, stderr, returncode


# Replaced on import: `-p` plugins load before any conftest or test module,
# and those bind it with `from tests.blackbox.utils import ...`.
tests.blackbox.utils.run_cli = _run_cli


def _reset_inherited_signal_state() -> None:
    """Start every command with the signal state a terminal would give it.

    A POSIX child inherits ignored signals and the blocked-signal mask
    across exec, and some launchers start this run with SIGINT and SIGQUIT
    ignored, as a non-interactive shell does for a background job. CPython
    then installs no KeyboardInterrupt handler, so a test that interrupts
    the AWS CLI sees it ignore the signal. Give each ignored signal its
    default action, SIGINT its KeyboardInterrupt handler, which a child's
    exec resets to the default, and unblock every signal. SIGPIPE and
    SIGXFSZ stay ignored here: CPython ignores them itself, and
    `subprocess` restores their defaults in every child. Windows has no
    inherited dispositions or signal mask, and no SIGQUIT.
    """
    if os.name != "posix":
        return
    own = {signal.SIGPIPE, signal.SIGXFSZ}
    for number in signal.valid_signals():
        if number in own or signal.getsignal(number) is not signal.SIG_IGN:
            continue
        signal.signal(
            number,
            signal.default_int_handler
            if number == signal.SIGINT
            else signal.SIG_DFL,
        )
    signal.pthread_sigmask(signal.SIG_SETMASK, ())


# On import, before any conftest or test starts a command.
_reset_inherited_signal_state()


def _select_expectations(
    node_ids: Iterable[str],
) -> dict[str, ExpectedResult] | None:
    """Map the run's collected node IDs to their ledger entries.

    Returns None when --run-all disabled the ledgers.
    """
    manifests = os.environ.get(_EXPECTATIONS_ENV_VAR)
    if manifests is None:
        return None
    try:
        parsed = read_combined_expectations(
            [Path(manifest) for manifest in manifests.split(os.pathsep)]
        )
    except SystemExit as error:
        raise pytest.UsageError(str(error)) from error
    expectations = {expectation.node_id: expectation for expectation in parsed}
    return {
        node_id: expectations[node_id]
        for node_id in node_ids
        if node_id in expectations
    }


def _crt_process_lock_held() -> bool:
    """Whether another process holds the AWS CLI's CRT process lock.

    While one does, the AWS CLI resolves `auto` to the classic client, so
    the repo tests do not exercise the CLI's default client.
    """
    lock = awscrt.s3.CrossProcessLock(_CRT_PROCESS_LOCK_NAME)
    try:
        lock.acquire()
    except RuntimeError:
        return True
    lock.release()
    return False


def pytest_configure(config: pytest.Config) -> None:
    # aws-cli/pyproject.toml's marker registration does not apply to this
    # run, so register the one the blackbox tests use here, with upstream's
    # description, beside the repo tests' own `native_only`.
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line(
        "markers",
        "native_only(condition): asserts behavior only the built binary "
        "has, such as an error for an invalid native setting, everywhere "
        "or where the optional condition holds; a run against another AWS "
        "CLI skips it there",
    )
    config.stash[_SELECTED_EXPECTATIONS_KEY] = {}
    # A pytest-xdist worker starts while its siblings run commands that hold
    # the lock, so only the session's first process reads it.
    config.stash[_CRT_PROCESS_LOCK_HELD_KEY] = not hasattr(
        config, "workerinput"
    ) and _crt_process_lock_held()


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if os.name == "nt":
        for item in items:
            if item.nodeid in _WINDOWS_SKIPS:
                item.add_marker(pytest.mark.skip(reason=_WINDOWS_SKIP_REASON))
    native_only_skip = None
    if os.environ.get(_BINARY_KIND_ENV_VAR) == "external":
        native_only_skip = _NATIVE_ONLY_SKIP_REASON
    elif PYTHON_ROUTE:
        native_only_skip = _PYTHON_ROUTE_SKIP_REASON
    if native_only_skip is not None:
        for item in items:
            marker = item.get_closest_marker("native_only")
            if marker is not None and all(marker.args):
                item.add_marker(pytest.mark.skip(reason=native_only_skip))
    selected = _select_expectations(item.nodeid for item in items)
    if selected is None:
        return
    for item in items:
        expectation = selected.get(item.nodeid)
        if expectation is None or not expectation.expects_failure(
            python_router=PYTHON_ROUTE
        ):
            continue
        item.add_marker(
            pytest.mark.xfail(
                reason=f"{expectation.kind.value}: {expectation.reason}",
                strict=True,
            )
        )
    config.stash[_SELECTED_EXPECTATIONS_KEY] = selected


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(
    node: Any,
    ids: Sequence[str],
) -> None:
    """Rebuild the selection in the pytest-xdist controller.

    With `-n`, collection and the hook above run only in the workers, so the
    controller's stash would stay empty. Every worker reports the same
    post-modifyitems node IDs, so any one of them yields the selection.
    """
    selected = _select_expectations(ids)
    if selected is not None:
        node.config.stash[_SELECTED_EXPECTATIONS_KEY] = selected


def pytest_terminal_summary(
    terminalreporter: Any,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    del exitstatus
    terminalreporter.write_sep("=", "blackbox ledger")
    if config.stash[_CRT_PROCESS_LOCK_HELD_KEY]:
        terminalreporter.write_line(
            "warning: another process held the AWS CLI's CRT process lock "
            "when the run started, so `auto` resolved to the classic client"
        )
    if os.environ.get(_EXPECTATIONS_ENV_VAR) is None:
        terminalreporter.write_line("Ledger not applied")
        return
    selected = config.stash[_SELECTED_EXPECTATIONS_KEY]
    xfailed = {
        report.nodeid for report in terminalreporter.stats.get("xfailed", ())
    }
    if PYTHON_ROUTE:
        terminalreporter.write_line(
            "Python route: the known native gaps do not apply"
        )
    for kind, label in _SUMMARY_LINES:
        entries = {
            node_id
            for node_id, expectation in selected.items()
            if expectation.kind is kind
            and expectation.expects_failure(python_router=PYTHON_ROUTE)
        }
        if entries:
            terminalreporter.write_line(
                label.format(counted_tests(len(entries & xfailed)))
            )
