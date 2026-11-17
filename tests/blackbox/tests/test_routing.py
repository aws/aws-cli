"""Routing: which inputs the built binary runs natively and which it hands
to Python, and why.

`AWS_CLI_NATIVE_ROUTER=native` forbids the hand-off: a command the router
would give Python fails instead, before any request, with exit status 255
and one line on stderr naming the reason. That refusal is the observable
form of each routing decision, so every input that sends a native command
to Python has a refusal here, marked `native_only`: another AWS CLI ignores
the variable, and a run that forces the Python route skips them.

A command the router keeps native under forced native renders upstream's
own output, so those tests are not `native_only`: another AWS CLI, or the
Python route, renders the same bytes.
"""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import awscrt.s3
import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer

from credhelpers import credential_runtime, run_command
from tests.blackbox.utils import run_cli

pytestmark = pytest.mark.asyncio

ROUTER: Final = "AWS_CLI_NATIVE_ROUTER"
# The name the AWS CLI's TransferManagerFactory locks while it runs the
# CRT client (awscli/customizations/s3/factory.py).
CRT_PROCESS_LOCK: Final = "aws-cli"
# A longer app id than the native user-agent header holds.
LONG_APP_ID: Final = "a" * 3000


def refusal(reason: str) -> bytes:
    """The line forced native routing prints for `reason`."""
    return (
        f"aws: {ROUTER}=native: native implementation unavailable "
        f"({reason}); Python fallback disabled\n"
    ).encode()


@pytest_asyncio.fixture
async def routing_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        yield server, env


async def assert_refused(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    arguments: list[str],
    reason: str,
    *,
    cwd: Path,
) -> None:
    env[ROUTER] = "native"
    result = await run_command([aws_cli, *arguments], env, cwd=cwd)
    assert result == (b"", refusal(reason), 255), result[1].decode()
    assert not server.requests


# The command line's own verdicts, before any configuration is read.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "arguments,reason",
    [
        (["ec2", "describe-instances", "--help"], "unsupported_command"),
        (["s3", "website", "-h"], "unsupported_subcommand"),
        (["--version"], "version_requested"),
        (["s3", "ls", "help"], "help_requested"),
        (
            [
                "s3",
                "cp",
                "missing-source",
                "s3://bucket/key",
                "--sse-c-copy-source",
                "AES256",
            ],
            "unsupported_option",
        ),
        # Upstream compiles any `--query` ahead of the leftover `-h`.
        (["--query", "X", "s3", "ls", "-h"], "python_only_global"),
        (
            ["s3", "--query", "X", "cp", "local", "s3://bucket/key", "-h"],
            "python_only_global",
        ),
        (["s3", "cp", "s3://source/key", "s3://destination/key"],
         "unsupported_operand"),
        (
            ["s3", "cp", "local", "s3://bucket/key", "--content-type",
             "fileb://local"],
            "unsupported_value",
        ),
    ],
    ids=[
        "unsupported-command",
        "unsupported-subcommand",
        "version",
        "help",
        "unsupported-option",
        "query-before-help",
        "query-in-s3",
        "s3-to-s3-copy",
        "fileb-content-type",
    ],
)
async def test_forced_native_refuses_a_python_command_line(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    arguments: list[str],
    reason: str,
) -> None:
    server, env = routing_runtime
    (tmp_path / "local").write_bytes(b"local\n")
    # An empty profile has no section, so a verdict that waited for the
    # configuration would be the profile lookup's instead.
    env["AWS_PROFILE"] = ""
    await assert_refused(aws_cli, server, env, arguments, reason, cwd=tmp_path)


# The environment, shared files, and globals the router hands to Python
# once it reads the configuration. A None variable is unset: botocore reads
# REQUESTS_CA_BUNDLE only without AWS_CA_BUNDLE.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "variables,config,arguments,reason",
    [
        ({"AWS_CLI_ERROR_FORMAT": "json"}, "", ["s3", "ls", "-h"],
         "structured_error_format"),
        ({"AWS_CLI_AUTO_PROMPT": "on"}, "", ["s3", "ls"], "auto_prompt"),
        # `s3 ls` follows botocore's retries, whose single attempt the CRT's
        # standard strategy cannot express, and botocore's client rejects a
        # retry mode other than standard or adaptive.
        ({"AWS_MAX_ATTEMPTS": "1"}, "", ["s3", "ls"], "retry_setting"),
        ({"AWS_RETRY_MODE": "legacy"}, "", ["s3", "ls"], "retry_setting"),
        ({"AWS_CLI_OUTPUT_ENCODING": "utf-16"}, "", ["s3", "ls", "-h"],
         "output_encoding"),
        ({}, "no section header\n", ["s3", "cp"], "config_parse_failure"),
        ({}, "[default]\ncli_history = enabled\n", ["s3", "ls", "-h"],
         "history_enabled"),
        # botocore rejects a blank CA bundle and reports a bundle it cannot
        # open with its own error; the CRT would say only "Invalid file
        # path."
        ({"AWS_CA_BUNDLE": " "}, "", ["s3", "ls"], "network_setting"),
        ({"AWS_CA_BUNDLE": "./missing-ca.pem"}, "", ["s3", "ls"],
         "network_setting"),
        ({"REQUESTS_CA_BUNDLE": "", "AWS_CA_BUNDLE": None}, "", ["s3", "ls"],
         "network_setting"),
        # Upstream's transfer configuration rejects an unreadable rate.
        ({}, "[default]\ns3 =\n  target_bandwidth = fast\n",
         ["s3", "cp", "local", "s3://bucket/key"], "transfer_setting"),
        # botocore rejects a region its format check refuses before it
        # builds a client.
        ({"AWS_REGION": "bad!"}, "", ["s3", "ls"], "endpoint_setting"),
        ({"AWS_SDK_UA_APP_ID": LONG_APP_ID}, "", ["s3", "ls"],
         "user_agent_setting"),
        ({}, "[plugins]\n", ["s3", "ls"], "plugins"),
        ({"AWS_PROFILE": "missing"}, "", ["s3", "ls"], "profile_lookup"),
        ({}, "", ["--ca-bundle", "./missing-ca.pem", "s3", "ls"],
         "python_only_global"),
        # urllib3 rejects a negative connect timeout when the client is built.
        ({}, "", ["--cli-connect-timeout", "-5", "s3", "ls"],
         "python_only_global"),
    ],
    ids=[
        "structured-error-format",
        "auto-prompt",
        "one-attempt",
        "legacy-retry-mode",
        "output-encoding",
        "malformed-config",
        "history",
        "blank-ca-bundle",
        "missing-ca-bundle",
        "blank-requests-ca-bundle",
        "unreadable-target-bandwidth",
        "invalid-region",
        "long-app-id",
        "plugins",
        "missing-profile",
        "ca-bundle-flag",
        "negative-connect-timeout",
    ],
)
async def test_forced_native_refuses_a_python_setting(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    variables: dict[str, str | None],
    config: str,
    arguments: list[str],
    reason: str,
) -> None:
    server, env = routing_runtime
    (tmp_path / "local").write_bytes(b"local\n")
    Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
    for name, value in variables.items():
        if value is None:
            del env[name]
        else:
            env[name] = value
    await assert_refused(aws_cli, server, env, arguments, reason, cwd=tmp_path)


# Python honors a mixed-case spelling in `os.environ` order, which the
# native reader does not model. Windows names have no case.
@pytest.mark.native_only
@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows environment names ignore case"
)
async def test_forced_native_refuses_a_mixed_case_proxy_variable(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = routing_runtime
    env["Http_Proxy"] = "http://127.0.0.1:9"
    await assert_refused(
        aws_cli, server, env, ["s3", "ls"], "network_setting", cwd=tmp_path
    )


# botocore expands a variable reference in either shared file's path
# (configloader.py:142-143); the native reader of the same files does not.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "key", ["AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"]
)
async def test_forced_native_refuses_a_variable_in_a_shared_file_path(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
) -> None:
    server, env = routing_runtime
    env[key] = str(tmp_path / "$UNSET_SHARED_FILE")
    await assert_refused(
        aws_cli, server, env, ["s3", "ls"], "shared_file_path", cwd=tmp_path
    )


# A credential helper beside static keys the profile also holds is the
# native chain's, which asks it before the config file's keys as botocore
# does (credentials.py:135-149): a helper that cannot be started fails the
# command before any request.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "arguments",
    [
        ["s3", "ls", "s3://bucket"],
        ["s3", "cp", "s3://bucket/key", "./never-written"],
    ],
    ids=["ls", "cp"],
)
async def test_forced_native_runs_a_credential_process_before_config_keys(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    arguments: list[str],
) -> None:
    server, env = routing_runtime
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[profile work]\n"
        "region = us-east-1\n"
        "credential_process = ./missing-credential-helper\n"
        "aws_access_key_id = config-key\n"
        "aws_secret_access_key = config-secret\n",
        encoding="utf-8",
    )
    env[ROUTER] = "native"
    stdout, stderr, returncode = await run_command(
        [aws_cli, "--profile", "work", *arguments], env, cwd=tmp_path
    )
    assert (stdout, returncode) == (b"", 255), stderr.decode()
    assert stderr and b"native implementation unavailable" not in stderr
    assert not server.requests
    assert not (tmp_path / "never-written").exists()


# While another AWS CLI holds the CRT process lock, upstream resolves
# `auto` to its classic client (customizations/s3/factory.py:198-211,
# 328-335), which only the Python route has.
@pytest.mark.native_only
async def test_forced_native_refuses_while_another_crt_client_runs(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = routing_runtime
    lock = awscrt.s3.CrossProcessLock(CRT_PROCESS_LOCK)
    lock.acquire()
    try:
        await assert_refused(
            aws_cli,
            server,
            env,
            ["s3", "cp", "s3://bucket/key", "./never-written"],
            "crt_client_running",
            cwd=tmp_path,
        )
    finally:
        lock.release()
    assert not (tmp_path / "never-written").exists()


# Global options `s3 ls` and `s3 cp` ignore or never read leave the command
# native, so the leftover `-h` fails as upstream's parser fails it. `-h` is
# no option of the AWS CLI's: `--help` is a global that asks for help.
@pytest.mark.parametrize(
    "arguments",
    [
        ["--output", "json", "s3", "ls", "-h"],
        ["s3", "--no-paginate", "ls", "-h"],
        ["s3", "ls", "--output", "yaml", "--no-paginate", "-h"],
        ["s3", "--color", "on", "ls", "-h"],
        ["s3", "ls", "--no-cli-pager", "-h"],
        ["--no-cli-pager", "s3", "cp", "local", "s3://bucket/key", "-h"],
        ["s3", "cp", "local", "s3://bucket/key", "--color", "on", "-h"],
    ],
    ids=[
        "output-json",
        "no-paginate",
        "output-yaml",
        "color",
        "no-cli-pager",
        "cp-no-cli-pager",
        "cp-color",
    ],
)
async def test_ignored_globals_stay_native_to_the_leftover_option(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    arguments: list[str],
) -> None:
    server, env = routing_runtime
    # The error format comes from the environment, so the empty profile,
    # which a profile lookup would refuse, shows the parse fails first.
    env.update(
        {"AWS_PROFILE": "", "AWS_CLI_ERROR_FORMAT": "enhanced", ROUTER: "native"}
    )
    stdout, stderr, rc = await run_command(
        [aws_cli, *arguments], env, cwd=tmp_path
    )
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert stderr.decode() == (
        "\naws: [ERROR]: An error occurred (ParamValidation): "
        "Unknown options: -h\n"
    )
    assert not server.requests


# An unknown router value means the default route; none changes what
# `--version` prints.
@pytest.mark.parametrize("mode", ["auto", "python", "unknown"])
async def test_router_values_other_than_native_run_the_command(
    aws_cli: str,
    routing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    mode: str,
) -> None:
    server, env = routing_runtime
    env[ROUTER] = mode
    stdout, stderr, rc = await run_cli(aws_cli, ["--version"], env)
    assert (rc, stderr) == (0, b""), stderr.decode()
    assert stdout.startswith(b"aws-cli/2."), stdout
    assert not server.requests
