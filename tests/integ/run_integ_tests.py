#!/usr/bin/env python3
"""Run the upstream AWS CLI integration tests against the built binary.

Opt-in through `cargo xtask integ`; never part of `cargo xtask build` or
`cargo xtask test`. The upstream harness already supports an external CLI:
awscli.testutils.aws() runs the command named by AWS_TEST_COMMAND instead
of the bundled Python entry point, so pytest drives the binary this repo
builds.

The suite imports awscli and its tests directly from the read-only source
tree under aws-cli/. A cached venv holds the upstream hash-pinned runtime
dependencies and this repo's pytest closure; awscli itself is never built
or installed into that venv.

The suite talks to real AWS. Credentials must resolve from the caller's
environment or ~/.aws (this runner never sets HOME), and the tests create
and delete real S3 buckets, so use a dedicated test account. The tests
never see the caller's config file: AWS_CONFIG_FILE names a runner-owned
file instead, so personal settings such as an s3 target_bandwidth cannot
change what they observe (see isolate_config). Everything after `--` on
the `cargo xtask integ` command line is forwarded to pytest, e.g.
`cargo xtask integ -- -k test_mv`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# This runner is executed by path, so the only import path it gets is
# sys.path[0], its own directory. The venv layout is shared with the other
# harness runners and therefore lives one level up, in tests/. Append rather
# than prepend: tests/ holds sibling directories that would otherwise
# register as namespace packages for names like `argparse`, and nothing here
# needs to outrank the stdlib.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from venv_paths import venv_python_path

VENV_DEPS_REVISION = "2"
DEFAULT_TESTS_PATH = "tests/integration/customizations/s3/test_plugin.py"
UPSTREAM_RUNTIME_REQUIREMENTS = (
    "requirements/download-deps/system-sandbox-lock.txt"
)
# Manifest of upstream tests that cannot execute at all, per host platform.
UNSUPPORTED_MANIFESTS = {"win32": "integ_unsupported_win32.txt"}

# Importing awscli first installs the meta-path finder that aliases
# botocore to the bundled awscli.botocore; the venv carries no standalone
# botocore distribution. It resolves against the caller's own config, and
# the frozen credentials come back over a pipe, never through a file.
CREDENTIALS_PREFLIGHT = """\
import json
import sys

import awscli
import botocore.session

session = botocore.session.Session()
credentials = session.get_credentials()
if credentials is None:
    sys.exit(1)
frozen = credentials.get_frozen_credentials()
json.dump(
    {
        "profile": session.profile,
        "method": credentials.method,
        "access_key": frozen.access_key,
        "secret_key": frozen.secret_key,
        "token": frozen.token,
    },
    sys.stdout,
)
"""

# Credential sources that resolve the same way once AWS_CONFIG_FILE names
# the runner-owned config. Every other source (SSO, credential_process,
# role_arn, keys in the config file) needs the caller's config, so its
# credentials are frozen before the run and exported to the tests.
CONFIG_INDEPENDENT_CREDENTIAL_METHODS = frozenset(
    {"env", "shared-credentials-file"}
)


@dataclass(frozen=True)
class CallerCredentials:
    """What CREDENTIALS_PREFLIGHT resolved from the caller's config."""

    profile: str | None
    method: str
    access_key: str
    secret_key: str
    token: str | None


def status(message: str) -> None:
    print(f"run_integ_tests: {message}", file=sys.stderr, flush=True)


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    result = subprocess.run(args, cwd=cwd, env=env)
    if result.returncode != 0:
        command = " ".join(args)
        raise SystemExit(
            f"command failed with exit code {result.returncode}: {command}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def host_python_id() -> str:
    version = sys.version_info
    return (
        f"{sys.implementation.name} "
        f"{version.major}.{version.minor}.{version.micro}"
    )


def shell_quote(path: Path) -> str:
    """Quote for the shell awscli.testutils.aws() spawns with shell=True.

    awscli/testutils.py interpolates AWS_TEST_COMMAND into a command line
    and runs it through the shell, so a path containing a space needs
    quoting to survive as one token. cmd.exe does not understand POSIX
    single quotes, and a Windows path cannot contain a double quote, so
    double quotes are exact there.
    """
    if sys.platform == "win32":
        return f'"{path}"'
    return shlex.quote(str(path))


def make_tree_writable(root: Path) -> None:
    """Give the owner write permission on root and everything under it.

    The staged copy must accept writes from pip (aws-cli's pep517 backend
    generates the auto-complete index under build/) and from pytest
    (.pytest_cache and assertion-rewrite bytecode), and shutil.rmtree
    needs writable directories. On Windows the same chmod is what clears
    FILE_ATTRIBUTE_READONLY, without which rmtree fails with WinError 5.

    Symlinks are skipped: stat()/chmod() follow them, so a dangling one
    anywhere in the tree would raise FileNotFoundError, and rmtree unlinks
    a symlink without needing its target to be writable.
    """
    root.chmod(root.stat().st_mode | 0o200)
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        path.chmod(path.stat().st_mode | 0o200)


def remove_tree(path: Path) -> None:
    make_tree_writable(path)
    shutil.rmtree(path)


def remove_legacy_staging(cache_dir: Path) -> None:
    """Remove the writable source copy created by older runner versions."""
    staging = cache_dir / "staging"
    if not staging.exists():
        return
    status(f"removing obsolete aws-cli staging tree under {staging}")
    remove_tree(staging)


def ensure_venv(
    cache_dir: Path,
    runtime_requirements: Path,
    test_requirements: Path,
) -> Path:
    """Provision the cached test venv.

    It holds the upstream hash-pinned awscli runtime dependencies plus
    this repo's hash-pinned pytest closure. The awscli package and tests
    are imported directly from the source tree instead of being installed.
    The first provision downloads from PyPI; reruns hit the marker and
    return immediately.
    """
    venv_dir = cache_dir / "venv"
    marker = venv_dir / ".zippy-integ-deps"
    python = venv_python_path(venv_dir)
    marker_text = (
        f"{VENV_DEPS_REVISION}\n"
        f"{sha256(runtime_requirements)}\n"
        f"{sha256(test_requirements)}\n"
        f"{host_python_id()}\n"
    )
    if (
        python.exists()
        and marker.exists()
        and marker.read_text(encoding="utf-8") == marker_text
    ):
        return python
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    status(f"provisioning the test harness venv under {venv_dir}")
    run([sys.executable, "-m", "venv", str(venv_dir)])
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--only-binary=:all:",
            "--require-hashes",
            "--requirement",
            str(runtime_requirements),
            "--requirement",
            str(test_requirements),
        ]
    )
    marker.write_text(marker_text, encoding="utf-8")
    return python


def source_environment(source: Path, cache_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{source}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(source)
    )
    env["PYTHONPYCACHEPREFIX"] = str(cache_dir / "pycache")
    return env


def resolve_credentials(
    venv_python: Path,
    source: Path,
    env: dict[str, str],
) -> CallerCredentials:
    result = subprocess.run(
        [str(venv_python), "-c", CREDENTIALS_PREFLIGHT],
        cwd=source,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "run_integ_tests: no AWS credentials resolved. The integration "
            "tests create and delete real S3 buckets; configure credentials "
            "for a dedicated test account (environment or ~/.aws) before "
            "running `cargo xtask integ`."
        )
    return CallerCredentials(**json.loads(result.stdout))


def isolate_config(
    cache_dir: Path,
    credentials: CallerCredentials,
    env: dict[str, str],
) -> None:
    """Point the tests at a runner-owned config file.

    The upstream fixtures copy whatever AWS_CONFIG_FILE names into each
    parameterized test and then run `aws configure set
    s3.preferred_transfer_client ...` against the copy, so every setting
    in the caller's config reaches the tests. An s3 target_bandwidth, for
    one, makes the classic client warn on stderr, failing each test that
    asserts an empty stderr. The suite pins its own region, and
    TestLs::test_ls_with_no_env_vars checks that none needs configuring,
    so the file holds only the sections that let botocore find the
    selected profile.

    The caller's environment and credentials file still apply. Credentials
    that only the caller's config could produce are exported frozen, so
    temporary ones must outlive the run.
    """
    sections = ["[default]"]
    if credentials.profile not in (None, "default"):
        sections.append(f"[profile {credentials.profile}]")
    config_file = cache_dir / "aws-config"
    config_file.write_text("\n".join(sections) + "\n", encoding="utf-8")
    env["AWS_CONFIG_FILE"] = str(config_file)
    if credentials.method in CONFIG_INDEPENDENT_CREDENTIAL_METHODS:
        return
    env["AWS_ACCESS_KEY_ID"] = credentials.access_key
    env["AWS_SECRET_ACCESS_KEY"] = credentials.secret_key
    if credentials.token is None:
        env.pop("AWS_SESSION_TOKEN", None)
    else:
        env["AWS_SESSION_TOKEN"] = credentials.token


def read_node_ids(manifest: Path) -> list[str]:
    node_ids: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            node_ids.append(entry)
    return node_ids


def collection_only(pytest_args: list[str]) -> bool:
    return any(arg in ("--collect-only", "--co") for arg in pytest_args)


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Unrecognized arguments are forwarded to pytest; abbreviation
        # matching would swallow pytest options that share a prefix with
        # the runner's own.
        allow_abbrev=False,
    )
    parser.add_argument("--aws-binary", required=True)
    parser.add_argument(
        "--aws-cli-source",
        required=True,
        help="application-owned aws-cli source tree",
    )
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument(
        "--tests-path",
        default=DEFAULT_TESTS_PATH,
        help="tests to run, relative to the aws-cli tree root",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help=(
            "ignore the expected-failures manifest to rebaseline it; the "
            "platform-unsupported manifest still applies"
        ),
    )
    return parser.parse_known_args()


def deselected_node_ids(harness_dir: Path, run_all: bool) -> list[str]:
    """Node ids to pass to pytest as --deselect, in manifest order."""
    node_ids: list[str] = []
    if not run_all:
        node_ids += read_node_ids(harness_dir / "integ_expected_failures.txt")
    # Tests upstream declares POSIX-only cannot execute here at all, so
    # they are not a baseline --run-all should re-measure.
    unsupported = UNSUPPORTED_MANIFESTS.get(sys.platform)
    if unsupported is not None:
        node_ids += read_node_ids(harness_dir / unsupported)
    return node_ids


def main() -> None:
    args, pytest_args = parse_args()
    harness_dir = Path(__file__).resolve().parent
    aws_binary = Path(args.aws_binary).resolve()
    if not aws_binary.is_file():
        raise SystemExit(f"AWS_TEST_COMMAND does not exist: {aws_binary}")
    cache_dir = Path(args.cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    source = Path(args.aws_cli_source).resolve()
    runtime_requirements = source / UPSTREAM_RUNTIME_REQUIREMENTS
    if not runtime_requirements.is_file():
        raise SystemExit(
            f"{source} does not contain {UPSTREAM_RUNTIME_REQUIREMENTS}"
        )

    remove_legacy_staging(cache_dir)
    venv_python = ensure_venv(
        cache_dir,
        runtime_requirements,
        harness_dir / "integ_test_requirements.txt",
    )
    env = source_environment(source, cache_dir)
    env["AWS_TEST_COMMAND"] = shell_quote(aws_binary)
    # Collection never talks to AWS, so `--collect-only` runs without
    # credentials.
    if not collection_only(pytest_args):
        credentials = resolve_credentials(venv_python, source, env)
        isolate_config(cache_dir, credentials, env)

    command = [
        str(venv_python),
        "-m",
        "pytest",
        "-c",
        str(harness_dir / "integ_pytest.ini"),
        f"--rootdir={source}",
        "-p",
        "no:cacheprovider",
        f"--basetemp={cache_dir / 'pytest-temp'}",
    ]
    for node_id in deselected_node_ids(harness_dir, args.run_all):
        command.extend(["--deselect", node_id])
    command.append(args.tests_path)
    command.extend(pytest_args)

    result = subprocess.run(command, cwd=source, env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
