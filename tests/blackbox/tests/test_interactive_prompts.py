import asyncio
import os
from pathlib import Path
from typing import Final

import pytest

from credhelpers import credential_runtime
from ptyhelpers import (
    CTRL_C,
    TerminalStep,
    interrupt_at_prompt,
    run_on_terminal,
)

# The AWS CLI exits 128 + SIGINT when Ctrl-C interrupts a prompt.
INTERRUPTED_RC: Final = 130

# Every test here drives a pseudo-terminal through `ptyhelpers`, so its
# tests report as skipped on Windows.
pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="drives a POSIX pseudo-terminal"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("args", "prompt"),
    [
        pytest.param(
            ["configure", "sso"],
            "SSO session name (Recommended):",
            id="configure-sso",
        ),
        pytest.param(
            ["lambda", "wizard", "new-function"],
            "Function name:",
            id="lambda-wizard",
        ),
        pytest.param(["--cli-auto-prompt"], "> aws", id="cli-auto-prompt"),
    ],
)
async def test_interactive_prompt_interrupted_with_ctrl_c_exits_130(
    aws_cli: str, tmp_path: Path, args: list[str], prompt: str
) -> None:
    # Every prompt renders before the command needs AWS, and HOME isolates
    # the autoprompt history and SSO caches.
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        env["TERM"] = "xterm-256color"
        # The proxy runs on this event loop, so the blocking terminal loop
        # runs in a thread.
        session = await asyncio.to_thread(
            interrupt_at_prompt, [aws_cli, *args], env=env, prompt=prompt
        )
        assert session.steps_seen == 1, session.transcript
        assert session.returncode == INTERRUPTED_RC, session.transcript
        assert server.requests == []


@pytest.mark.asyncio
async def test_auto_prompt_completes_names_from_the_autocomplete_index(
    aws_cli: str, tmp_path: Path
) -> None:
    # Auto-prompt reads command and parameter names from the autocomplete
    # index. Each expected name is typed only partly before it is expected,
    # so only the completion menu can show it in full. Recognizing the
    # service, listing its operations, and listing an operation's parameters
    # each read a different part of the index.
    steps = [
        TerminalStep("> aws", b"ec2 describe-instance-sta"),
        TerminalStep("describe-instance-status", b"tus --include-all-inst"),
        TerminalStep("--include-all-instances", CTRL_C),
    ]
    async with credential_runtime(tmp_path, temp_home=True) as (server, env):
        env["TERM"] = "xterm-256color"
        session = await asyncio.to_thread(
            run_on_terminal,
            [aws_cli, "--cli-auto-prompt"],
            env=env,
            steps=steps,
        )
        assert session.steps_seen == len(steps), session.transcript
        assert session.returncode == INTERRUPTED_RC, session.transcript
        assert server.requests == []
