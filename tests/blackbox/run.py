#!/usr/bin/env python3
"""Run upstream and repo-specific blackbox tests against one AWS CLI binary.

Upstream's tests run unmodified from the read-only aws-cli/tests/blackbox
tree alongside this directory's tests. Both suites drive AWS_TEST_COMMAND
through localstub's TLS intercept proxy and mock server with fake
credentials, so they need no AWS credentials and make no AWS API calls.

Each suite runs in its own pytest session and cached venv, both holding the
upstream hash-pinned runtime dependencies, which the tests package imports.
Upstream's tests get upstream's blackbox test lock, as upstream runs them;
the repo tests get this directory's hash-pinned requirements.txt, which pins
the newer localstub they need. The first provision downloads those wheels.
Test runs use only local network connections afterward.

AWS_TEST_COMMAND is the binary under test, in its default configuration
unless `--env NAME=VALUE` sets NAME in the environment of every command it
runs, over the environment each test gives the command.
Upstream's tests run with upstream's environment, AWS_MAX_ATTEMPTS=1
included. The repo tests drop that setting, so the AWS CLI resolves `auto`
to the CRT client they exercise, unless another AWS CLI process holds the
machine-wide CRT process lock, which every CRT transfer takes. The tests
run serially so no command holds it for another; with pytest-xdist's `-n`,
which client a transfer gets depends on its siblings.

Every test must pass against the public AWS CLI, except the upstream tests
`--upstream-failures` lists, which it fails in upstream's own environment,
and the repo tests marked `native_only`, which assert behavior only the
built binary has, everywhere or where the marker's condition holds, such as
on Windows alone. `--binary-kind external` says the binary is another AWS
CLI, so the run skips the `native_only` tests, as a run whose `--env` forces
the built binary's Python route does. `--known-gaps` names the ledger of
tests the built binary fails and the public AWS CLI passes. The run marks
the entries of both ledgers as strict expected failures on the route they
fail on: a native gap's test passes on the Python route; `--run-all`
ignores them.

The built binary is the static build unless `--link-mode system` says it
is a system build, with its `--crt-link`, `--python-payload`, and the ABI
of the system Python it links, `--python-abi`; the tests of the
executable and its payload check that build's contract.

`--suite upstream` or `--suite repo` runs that session alone; by default
both run. Arguments the runner does not recognize are forwarded to every
session, for example `-k test_ls -x`. `--junit-dir` writes each session's
JUnit XML report there, as upstream.xml and repo.xml.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# This runner is executed by path, so the only import path it gets is
# sys.path[0], its own directory. The shared harness modules live one level
# up. Append rather than prepend: tests/ holds sibling directories that
# would otherwise register as namespace packages for names like `argparse`,
# and nothing here needs to outrank the stdlib.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import harness_venv
from expectations import ExpectationKind, read_combined_expectations

VENV_DEPS_REVISION: Final = "1"
UPSTREAM_RUNTIME_REQUIREMENTS: Final = (
    "requirements/download-deps/system-sandbox-lock.txt"
)
UPSTREAM_TESTS: Final = "tests/blackbox"
UPSTREAM_TEST_REQUIREMENTS: Final = "requirements-test-blackbox-lock.txt"
EXPECTATIONS_ENV_VAR: Final = "AWS_BLACKBOX_EXPECTATIONS"
# The harness plugin reads `--env`'s variables from here, as JSON.
COMMAND_ENVIRONMENT_ENV_VAR: Final = "AWS_BLACKBOX_COMMAND_ENVIRONMENT"
BINARY_KIND_ENV_VAR: Final = "AWS_BLACKBOX_BINARY_KIND"
# The harness plugin reads the build's description from here, as JSON.
BUILD_ENV_VAR: Final = "AWS_BLACKBOX_BUILD"
TEST_TIMEOUT_SECONDS: Final = 60 * 60
# pytest's exit status when a session selects no tests, as `-k` can leave
# one of the two sessions.
NO_TESTS_COLLECTED: Final = 5


@dataclass(frozen=True)
class Suite:
    """One pytest session: a test tree and the venv its tests run in."""

    name: str
    tests: str
    test_requirements: Path
    venv: Path


def assignment(argument: str) -> tuple[str, str]:
    """`NAME=VALUE` split at its first `=`."""
    name, separator, value = argument.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError(
            f"expected NAME=VALUE, not {argument!r}"
        )
    return name, value


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Unrecognized arguments go to pytest. Abbreviation matching could
        # otherwise consume pytest options that share a runner-option prefix.
        allow_abbrev=False,
    )
    parser.add_argument("--aws-binary", required=True)
    parser.add_argument(
        "--binary-kind",
        required=True,
        choices=("built", "external"),
        help="whether the binary is this repository's or another AWS CLI",
    )
    parser.add_argument(
        "--link-mode",
        choices=("static", "system"),
        default="static",
        help="how the built binary links its runtime",
    )
    parser.add_argument(
        "--crt-link",
        choices=("static", "shared"),
        help="how a system build links the CRT",
    )
    parser.add_argument(
        "--python-payload",
        choices=("embedded", "system"),
        help="which AWS CLI a system build runs: its own or the system's",
    )
    parser.add_argument(
        "--python-abi",
        help="the libpython a system build links, such as python3.14",
    )
    parser.add_argument(
        "--aws-cli-source",
        required=True,
        help="application-owned aws-cli source tree",
    )
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument(
        "--known-gaps",
        type=Path,
        help="ledger of tests the binary fails and the public AWS CLI passes",
    )
    parser.add_argument(
        "--upstream-failures",
        type=Path,
        help="ledger of upstream tests the public AWS CLI fails",
    )
    parser.add_argument(
        "--suite",
        choices=("upstream", "repo"),
        help="run this session alone instead of both",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="apply neither ledger and show raw failures",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        type=assignment,
        metavar="NAME=VALUE",
        help="set NAME in the environment of every AWS CLI command",
    )
    parser.add_argument(
        "--junit-dir",
        type=Path,
        help="write each session's JUnit XML report into this directory",
    )
    args, forwarded = parser.parse_known_args()
    system = (args.crt_link, args.python_payload, args.python_abi)
    if args.link_mode == "system" and None in system:
        parser.error(
            "--link-mode system requires --crt-link, --python-payload, "
            "and --python-abi"
        )
    if args.link_mode == "static" and system != (None, None, None):
        parser.error(
            "--crt-link, --python-payload, and --python-abi describe a "
            "system build"
        )
    return args, forwarded


def build_description(args: argparse.Namespace) -> dict[str, str | None]:
    """The build the plugin hands the tests: the static build's, unless
    the options describe a system build."""
    if args.link_mode == "static":
        return {
            "link_mode": "static",
            "crt_link": "static",
            "python_payload": "embedded",
            "python_abi": None,
        }
    return {
        "link_mode": "system",
        "crt_link": args.crt_link,
        "python_payload": args.python_payload,
        "python_abi": args.python_abi,
    }


def test_environment(
    source: Path,
    harness_dir: Path,
    cache_dir: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    python_paths = [str(source), str(harness_dir)]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["PYTHONPYCACHEPREFIX"] = str(cache_dir / "pycache")
    if os.name == "nt":
        # Upstream's fixtures stamp objects with the 1970 epoch. West of UTC
        # that is a local time before the epoch, which the Microsoft C
        # runtime's localtime() rejects, so dateutil fails on the Python
        # route as it does in the AWS CLI release. Pin UTC here, where pytest
        # computes expected local times; the plugin forwards it to every
        # command.
        env["TZ"] = "UTC"
    return env


def validate_ledger(
    ledger: Path,
    kind: ExpectationKind,
    prefix: str = "",
    *,
    also: Collection[ExpectationKind] = (),
) -> None:
    """Every entry of `ledger` is of `kind` or one of `also`, for a test
    under `prefix`."""
    kinds = (kind, *also)
    for expectation in read_combined_expectations([ledger]):
        if expectation.kind not in kinds:
            raise SystemExit(
                f"{ledger}: {expectation.node_id} is "
                f"{expectation.kind.value}; this ledger lists only "
                f"{' or '.join(k.value for k in kinds)} entries"
            )
        if not expectation.node_id.startswith(prefix):
            raise SystemExit(
                f"{ledger}: {expectation.node_id} is not under {prefix}"
            )


def upstream_issue_ledger(known_gaps: Path, cache_dir: Path) -> Path:
    """A ledger of the upstream-issue entries of `known_gaps` alone."""
    ledger = cache_dir / "upstream-issues.txt"
    ledger.write_text(
        "".join(
            f"{expectation.node_id}  # {expectation.kind.value}: "
            f"{expectation.reason}\n"
            for expectation in read_combined_expectations([known_gaps])
            if expectation.kind is ExpectationKind.UPSTREAM_ISSUE
        ),
        encoding="utf-8",
    )
    return ledger


def run_suite(
    suite: Suite,
    runtime_requirements: Path,
    env: dict[str, str],
    source: Path,
    pytest_args: Sequence[str],
) -> int:
    venv_python = harness_venv.ensure_venv(
        suite.venv,
        [runtime_requirements, suite.test_requirements],
        VENV_DEPS_REVISION,
    )
    command = [
        str(venv_python),
        "-m",
        "pytest",
        "-p",
        "harness_plugin",
        f"--rootdir={source}",
        "-p",
        "no:cacheprovider",
        f"--basetemp={suite.venv.parent / 'pytest-temp'}",
        suite.tests,
        *pytest_args,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=source,
            env=env,
            check=False,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            f"{suite.name} blackbox tests exceeded "
            f"{TEST_TIMEOUT_SECONDS} seconds"
        ) from error
    return result.returncode


def combined_returncode(returncodes: Sequence[int]) -> int:
    """The run's exit status: the first failing session's, ignoring a
    session that selected no tests unless every session did."""
    ran = [code for code in returncodes if code != NO_TESTS_COLLECTED]
    if not ran:
        return NO_TESTS_COLLECTED
    return next((code for code in ran if code != 0), 0)


def main() -> None:
    args, pytest_args = parse_args()
    harness_venv.validate_host_python("blackbox tests")
    harness_dir = Path(__file__).resolve().parent
    aws_binary = Path(args.aws_binary).resolve()
    if not aws_binary.is_file():
        raise SystemExit(f"AWS binary does not exist: {aws_binary}")
    cache_dir = Path(args.cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    source = Path(args.aws_cli_source).resolve()
    runtime_requirements = source / UPSTREAM_RUNTIME_REQUIREMENTS
    suites = [
        Suite(
            name="upstream",
            tests=UPSTREAM_TESTS,
            test_requirements=source / UPSTREAM_TEST_REQUIREMENTS,
            venv=cache_dir / "upstream" / "venv",
        ),
        Suite(
            name="repo",
            tests=str(harness_dir / "tests"),
            test_requirements=harness_dir / "requirements.txt",
            venv=cache_dir / "repo" / "venv",
        ),
    ]
    if args.suite is not None:
        suites = [suite for suite in suites if suite.name == args.suite]
    for path in [
        runtime_requirements,
        source / UPSTREAM_TESTS,
        source / UPSTREAM_TEST_REQUIREMENTS,
    ]:
        if not path.exists():
            raise SystemExit(f"{source} does not contain {path}")

    env = test_environment(source, harness_dir, cache_dir)
    env["AWS_TEST_COMMAND"] = str(aws_binary)
    # The plugin skips the `native_only` tests for an external binary.
    env[BINARY_KIND_ENV_VAR] = args.binary_kind
    env[BUILD_ENV_VAR] = json.dumps(build_description(args))
    env.pop(EXPECTATIONS_ENV_VAR, None)
    env.pop(COMMAND_ENVIRONMENT_ENV_VAR, None)
    if args.env:
        env[COMMAND_ENVIRONMENT_ENV_VAR] = json.dumps(dict(args.env))
    ledgers = []
    if args.upstream_failures is not None and not args.run_all:
        # The public AWS CLI passes every repo test.
        validate_ledger(
            args.upstream_failures,
            ExpectationKind.SHARED_HARNESS_FAILURE,
            f"{UPSTREAM_TESTS}/",
        )
        ledgers.append(args.upstream_failures)
    if args.known_gaps is not None and not args.run_all:
        validate_ledger(
            args.known_gaps,
            ExpectationKind.PARITY_GAP,
            also=(
                ExpectationKind.UPSTREAM_ISSUE,
                ExpectationKind.LAUNCHER_DIFFERENCE,
            ),
        )
        ledgers.append(args.known_gaps)
    elif not args.run_all:
        # Another AWS CLI fails the known-gap ledger's upstream issues too,
        # but none of its native gaps or launcher differences.
        ledgers.append(
            upstream_issue_ledger(harness_dir / "failures.txt", cache_dir)
        )
    if ledgers:
        # Validated before pytest starts; the plugin applies strict
        # expected-failure markers and prints the summary.
        read_combined_expectations(ledgers)
        env[EXPECTATIONS_ENV_VAR] = os.pathsep.join(
            str(ledger.resolve()) for ledger in ledgers
        )
    if args.junit_dir is not None:
        args.junit_dir.mkdir(parents=True, exist_ok=True)

    returncodes = []
    for suite in suites:
        suite_args = list(pytest_args)
        if args.junit_dir is not None:
            report = args.junit_dir.resolve() / f"{suite.name}.xml"
            suite_args.append(f"--junitxml={report}")
        returncodes.append(
            run_suite(suite, runtime_requirements, env, source, suite_args)
        )
    sys.exit(combined_returncode(returncodes))


if __name__ == "__main__":
    main()
