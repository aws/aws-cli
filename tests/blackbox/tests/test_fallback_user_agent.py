"""The `md/fallback` component of the User-Agent each request names.

The built binary's Python route names, in every request it sends, why the
router handed the invocation to Python: `md/fallback#<reason>`, with the
reason's name as `AWS_CLI_NATIVE_ROUTER=native`'s refusal prints it
(test_routing.py). The router stops at the first rule that sends the
invocation to Python, so a request names one reason. The native route
sends none.

Only the built binary routes, so every test is `native_only`; a run that
forces the Python route skips them, as every request there names
`env_override`.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import InMemoryS3, pattern_bytes, s3_runtime

pytestmark = [pytest.mark.asyncio, pytest.mark.native_only]

ROUTER: Final = "AWS_CLI_NATIVE_ROUTER"
FALLBACK: Final = "md/fallback#"
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
PLUGINS: Final = "[plugins]\n"


@dataclass(frozen=True)
class Case:
    arguments: tuple[str, ...]
    reason: str
    environment: Mapping[str, str] = field(default_factory=dict[str, str])
    config: str = ""


# A reason from each stage that decides a route: the router variable, which
# the entrypoint reads before it parses anything, the command line, the
# shared files read before the main parse, and the configuration in force.
PYTHON_ROUTED: Final = {
    "forced-python": Case(
        LISTING, "env_override", environment={ROUTER: "python"}
    ),
    "unsupported-command": Case(
        ("s3api", "list-objects-v2", "--bucket", BUCKET),
        "unsupported_command",
    ),
    "plugins-listing": Case(LISTING, "plugins", config=PLUGINS),
    # Upstream's CRT client sends the download's GetObject, as it does for
    # the native route.
    "plugins-download": Case(DOWNLOAD, "plugins", config=PLUGINS),
    # A single attempt is outside the CRT's standard strategy, which
    # native's listing retries with.
    "one-attempt": Case(
        LISTING, "retry_setting", environment={"AWS_MAX_ATTEMPTS": "1"}
    ),
}
NATIVE: Final = {"listing": LISTING, "download": DOWNLOAD}


def fallback_components(user_agent: str) -> list[str]:
    return [
        component
        for component in user_agent.split()
        if component.startswith(FALLBACK)
    ]


async def sent_user_agents(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    *,
    environment: Mapping[str, str],
    config: str = "",
) -> list[tuple[str, str]]:
    """The operation and User-Agent of each request a successful run sends."""
    work = tmp_path / "work"
    work.mkdir()
    store = InMemoryS3(OBJECTS)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
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
    assert user_agents, report
    return user_agents


@pytest.mark.parametrize("case", PYTHON_ROUTED)
async def test_python_route_names_its_reason_in_every_user_agent(
    aws_cli: str, tmp_path: Path, case: str
) -> None:
    settings = PYTHON_ROUTED[case]
    user_agents = await sent_user_agents(
        aws_cli,
        tmp_path,
        settings.arguments,
        environment=settings.environment,
        config=settings.config,
    )
    for operation, user_agent in user_agents:
        assert fallback_components(user_agent) == [
            f"{FALLBACK}{settings.reason}"
        ], f"{operation}: {user_agent}"


# Forced native routing refuses the fallback, so a run that succeeds ran
# natively.
@pytest.mark.parametrize("command", NATIVE)
async def test_native_route_names_no_fallback(
    aws_cli: str, tmp_path: Path, command: str
) -> None:
    user_agents = await sent_user_agents(
        aws_cli,
        tmp_path,
        NATIVE[command],
        environment={ROUTER: "native"},
    )
    for operation, user_agent in user_agents:
        assert fallback_components(user_agent) == [], (
            f"{operation}: {user_agent}"
        )
