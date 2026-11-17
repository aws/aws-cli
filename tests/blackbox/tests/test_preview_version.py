"""The preview tag on the version the built binary reports.

During the preview the built binary names its version as upstream's
`__version__` with a `-preview1` suffix, `aws-cli/<version>-preview1`, so
its requests can be told from upstream's. Both routes name it: in the
User-Agent of every request, in `--debug`'s `CLI version` line, and in
`aws --version`, which the Python route prints.

Only the built binary carries the tag, so every test is `native_only`; a run
that forces the Python route skips them, as test_fallback_user_agent.py's.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import InMemoryS3, pattern_bytes, s3_runtime

pytestmark = [pytest.mark.asyncio, pytest.mark.native_only]

# The checkout the binary was built in, whose upstream source names the
# version the tag follows.
REPOSITORY: Final = Path(__file__).resolve().parents[3]
UPSTREAM_VERSION: Final = re.search(
    r"^__version__ = '([^']+)'$",
    (REPOSITORY / "aws-cli" / "awscli" / "__init__.py").read_text(
        encoding="utf-8"
    ),
    re.MULTILINE,
)[1]
PRODUCT: Final = f"aws-cli/{UPSTREAM_VERSION}-preview1"

ROUTER: Final = "AWS_CLI_NATIVE_ROUTER"
BUCKET: Final = "bucket"
OBJECTS: Final = {
    (BUCKET, "download/object.txt"): pattern_bytes("object", 2048),
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
}
LISTING: Final = ("s3", "ls", f"s3://{BUCKET}/tree/")
DOWNLOAD: Final = (
    "s3",
    "cp",
    f"s3://{BUCKET}/download/object.txt",
    "object.txt",
    "--no-progress",
)


@dataclass(frozen=True)
class Case:
    arguments: tuple[str, ...]
    environment: Mapping[str, str]


# Forced native routing refuses the fallback, so a run that succeeds ran
# natively. The listing and the download send through different clients.
ROUTES: Final = {
    "native-listing": Case(LISTING, {ROUTER: "native"}),
    "native-download": Case(DOWNLOAD, {ROUTER: "native"}),
    "python-listing": Case(LISTING, {ROUTER: "python"}),
    "python-unsupported-command": Case(
        ("s3api", "list-objects-v2", "--bucket", BUCKET), {}
    ),
}
DEBUG_ROUTES: Final = ("native-listing", "python-listing")


@dataclass(frozen=True)
class Run:
    stdout: str
    stderr: str
    user_agents: list[tuple[str, str]]


async def run_aws(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    environment: Mapping[str, str],
) -> Run:
    """A successful run, with the operation and User-Agent of each request."""
    work = tmp_path / "work"
    work.mkdir()
    store = InMemoryS3(OBJECTS)
    async with s3_runtime(store, tmp_path) as (_, env):
        # The session id would open the session database under HOME.
        env["AWS_CLI_SESSION_ID_DISABLED"] = "true"
        env.update(environment)
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments], env, cwd=work, stdin=None
        )
    user_agents = [
        (
            request.operation_model.name,
            request.wire_request.headers.get("user-agent", ""),
        )
        for request in store.received
    ]
    report = (
        f"exit {returncode}\nstdout: {stdout!r}\nstderr: {stderr!r}\n"
        f"user agents: {user_agents}\nfailures: {store.failures}\n"
    )
    assert store.failures == [], report
    assert returncode == 0, report
    return Run(stdout.decode(), stderr.decode(), user_agents)


def product(user_agent: str) -> list[str]:
    return [
        component
        for component in user_agent.split()
        if component.startswith("aws-cli/")
    ]


@pytest.mark.parametrize("route", ROUTES)
async def test_every_request_names_the_preview(
    aws_cli: str, tmp_path: Path, route: str
) -> None:
    case = ROUTES[route]
    run = await run_aws(aws_cli, tmp_path, case.arguments, case.environment)
    assert run.user_agents, run
    for operation, user_agent in run.user_agents:
        assert product(user_agent) == [PRODUCT], f"{operation}: {user_agent}"


@pytest.mark.parametrize("route", DEBUG_ROUTES)
async def test_debug_log_names_the_preview(
    aws_cli: str, tmp_path: Path, route: str
) -> None:
    case = ROUTES[route]
    run = await run_aws(
        aws_cli, tmp_path, (*case.arguments, "--debug"), case.environment
    )
    assert f"CLI version: {PRODUCT} " in run.stderr, run.stderr


async def test_version_names_the_preview(
    aws_cli: str, tmp_path: Path
) -> None:
    run = await run_aws(aws_cli, tmp_path, ("--version",), {})
    assert run.stdout.split()[0] == PRODUCT, run.stdout
    assert run.user_agents == []
