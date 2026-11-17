"""The embedded AWS CLI: what its offline commands read from the payload.

The commands here run on the Python route, so they assert the embedding
contract, not upstream's commands: the interpreter boots, the payload holds
the models, documents, and wizards those commands read, the CLI sees its
original argv, its text ends lines as the platform does, and a development
hook the shipped binary must not honor stays inert. None makes a request.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer

from credhelpers import credential_runtime, run_command
from harness_plugin import BUILD, child_environment

pytestmark = pytest.mark.asyncio

# What prompt_toolkit says when the wizard's input is not a terminal: its
# Posix input warns, and its win32 output raises NoConsoleScreenBufferError,
# whose two TERM-selected wordings share this phrase.
NO_TERMINAL: Final = (
    "Windows console" if sys.platform == "win32"
    else "Warning: Input is not a terminal"
)
# The pager the help test pins, so a developer's own MANPAGER or PAGER cannot
# decide whether the document reaches stdout. Windows' default, `more`,
# streams to a pipe.
PAGER: Final = "more" if sys.platform == "win32" else "/bin/cat"
# The prefix of the former parse-capture hook's variables, which the
# shipped binary ignores.
CAPTURE_PREFIX: Final = b"AWSCLI_PARSE_CAPTURE"


@pytest_asyncio.fixture
async def offline_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        yield server, env


@pytest.mark.parametrize(
    "arguments,expected",
    [
        (["iam", "list-users", "--generate-cli-skeleton"], '"PathPrefix"'),
        (
            ["configure", "wizard", "help"],
            "Interactive command for creating and configuring AWS resources",
        ),
        (["dynamodb", "wizard", "help"], "new-table"),
        (["events", "wizard", "help"], "new-rule"),
        (["iam", "wizard", "help"], "new-role"),
        (["lambda", "wizard", "help"], "new-function"),
        (
            ["lambda", "wizard", "new-function", "help"],
            "This wizard will create a new AWS Lambda function for you",
        ),
    ],
    ids=[
        "iam-model",
        "configure-wizards",
        "dynamodb-wizards",
        "events-wizards",
        "iam-wizards",
        "lambda-wizards",
        "lambda-wizard-definition",
    ],
)
async def test_offline_commands_read_the_embedded_payload(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    arguments: list[str],
    expected: str,
) -> None:
    server, env = offline_runtime
    env["MANPAGER"] = PAGER
    stdout, stderr, rc = await run_command(
        [aws_cli, *arguments], env, cwd=tmp_path
    )
    assert rc == 0, stderr.decode()
    assert expected in stdout.decode()
    assert not server.requests


# `cli_help_output = url` prints a topic's page address from the payload's
# topic index instead of rendering the topic.
async def test_a_help_topic_url_comes_from_the_embedded_payload(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = offline_runtime
    env["MANPAGER"] = PAGER
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[default]\ncli_help_output = url\n", encoding="utf-8"
    )
    stdout, stderr, rc = await run_command(
        [aws_cli, "help", "config-vars"], env, cwd=tmp_path
    )
    assert rc == 0, stderr.decode()
    assert "topic/config-vars.html" in stdout.decode()
    assert not server.requests


async def test_a_wizard_without_a_terminal_says_so(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = offline_runtime
    stdout, stderr, rc = await run_command(
        [aws_cli, "lambda", "wizard", "new-function"], env, cwd=tmp_path
    )
    assert rc == 255, stderr.decode()
    assert NO_TERMINAL in stderr.decode()
    assert not server.requests


# `aws sso login` resolves a custom start URL with the default CA bundle of
# the awscli copy of botocore's httpsession, so the payload must carry that
# copy's default too: the command then reaches the closed port, where a
# missing bundle would fail to open it first. So the command runs with no
# bundle and no proxy of the harness's. The refusal reads differently on
# Windows. Only the embedded payload carries that default; the system
# payload runs the system's AWS CLI.
@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows words the refusal differently"
)
@pytest.mark.skipif(
    BUILD.python_payload != "embedded",
    reason="asserts the embedded payload's default bundle",
)
async def test_sso_login_reaches_its_start_url_with_the_embedded_bundle(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = offline_runtime
    for name in ("AWS_CA_BUNDLE", "HTTPS_PROXY", "HTTP_PROXY"):
        del env[name]
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[profile sso]\n"
        "sso_start_url = https://127.0.0.1:9/start\n"
        "sso_region = us-east-1\n",
        encoding="utf-8",
    )
    stdout, stderr, rc = await run_command(
        [aws_cli, "sso", "login", "--profile", "sso", "--no-browser"],
        env,
        cwd=tmp_path,
    )
    assert (rc, stdout) == (253, b""), stderr.decode()
    assert "Failed to resolve start URL: " in stderr.decode()
    assert stderr.decode().endswith("Connection refused\n")
    assert not server.requests


# A development build once loaded and ran the source a variable named. The
# shipped binary must neither read nor run it, on either route, and must
# not name the variables at all.
@pytest.mark.parametrize(
    "router,arguments,status,expected",
    [
        ("auto", ["--version"], 0, "aws-cli/2."),
        ("python", ["s3", "cp"], 252,
         "the following arguments are required: paths"),
    ],
    ids=["version", "python-parse-failure"],
)
async def test_the_former_parse_capture_hook_is_inert(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    router: str,
    arguments: list[str],
    status: int,
    expected: str,
) -> None:
    server, env = offline_runtime
    marker = tmp_path / "executed"
    hook = tmp_path / "hook.py"
    hook.write_text(
        "import os\n"
        f"open({str(marker)!r}, 'w').write('executed')\n",
        encoding="utf-8",
    )
    # A FIFO without a writer blocks even an attempted read, which catches
    # a hook that reads its source but no longer runs it.
    sources = [hook]
    if hasattr(os, "mkfifo"):
        fifo = tmp_path / "unreadable"
        os.mkfifo(fifo)
        sources.append(fifo)
    for source in sources:
        env.update(
            AWSCLI_PARSE_CAPTURE=str(marker),
            AWSCLI_PARSE_CAPTURE_TOOL=str(source),
            AWS_CLI_NATIVE_ROUTER=router,
        )
        stdout, stderr, rc = await run_command(
            [aws_cli, *arguments], env, cwd=tmp_path, timeout=20
        )
        assert rc == status, stderr.decode()
        assert expected in (stdout + stderr).decode()
        assert not marker.exists()
    assert CAPTURE_PREFIX not in Path(aws_cli).read_bytes()
    assert not server.requests


# On Windows both routes write each text '\n' as '\r\n', as the AWS CLI
# release does; every other test reads output with that folded back, so
# this one reads the bytes as written, from a command each route renders.
@pytest.mark.parametrize(
    "router,arguments,status,stream",
    [
        ("auto", ["--version"], 0, "stdout"),
        ("auto", ["s3", "ls", "--bogus"], 252, "stderr"),
        ("python", ["s3", "ls", "--bogus"], 252, "stderr"),
    ],
    ids=["version", "native-error", "python-error"],
)
async def test_text_lines_end_as_the_platform_ends_them(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    router: str,
    arguments: list[str],
    status: int,
    stream: str,
) -> None:
    server, env = offline_runtime
    env["AWS_CLI_NATIVE_ROUTER"] = router
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        *arguments,
        env=child_environment(env),
        cwd=tmp_path,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), 60)
    assert process.returncode == status, stderr.decode()
    text = stdout if stream == "stdout" else stderr
    if sys.platform == "win32":
        assert text.endswith(b"\r\n"), text
        assert text.count(b"\n") == text.count(b"\r\n"), text
    else:
        assert text.endswith(b"\n"), text
        assert b"\r" not in text, text
    assert not server.requests
