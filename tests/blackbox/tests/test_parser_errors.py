import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer

from credhelpers import credential_env
from s3helpers import failing_stream, run_cli_with_streams
from tests.blackbox.utils import mock_server, run_cli

# The AWS CLI reports a command line it cannot parse as a ParamValidation
# error (awscli/errorhandler.py:179-182) and exits 252 before any request.
PARAM_VALIDATION_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (ParamValidation): "
)


# MainArgParser's usage (awscli/argparser.py:18-28), which names the program
# `aws` whatever the binary's file name, `aws.exe` on Windows included.
MAIN_USAGE: Final = (
    "usage: aws [options] <command> <subcommand> [<subcommand> ...] "
    "[parameters]\n"
    "To see help text, you can run:\n"
    "\n"
    "  aws help\n"
    "  aws <command> help\n"
    "  aws <command> <subcommand> help\n"
)


@pytest_asyncio.fixture
async def parse_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with mock_server() as (server, proxy):
        env = credential_env(proxy, tmp_path)
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        yield server, env


# argparse's errors end with the main usage (awscli/argparser.py:104-116).
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,message",
    [
        ([], "the following arguments are required: command"),
        (["s3", "cp"], "the following arguments are required: paths"),
        (["s3", "cp", "file"], "the following arguments are required: paths"),
        (
            ["s3", "ls", "--page-size"],
            "argument --page-size: expected one argument",
        ),
    ],
    ids=[
        "missing-command",
        "cp-missing-operands",
        "cp-missing-destination",
        "missing-option-value",
    ],
)
async def test_parse_error_prints_message_and_main_usage(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
    message: str,
) -> None:
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert stderr.decode() == (
        f"{PARAM_VALIDATION_PREFIX}{message}\n\n{MAIN_USAGE}"
    )
    assert not server.requests


@pytest.mark.asyncio
async def test_parse_error_for_missing_subcommand_prints_service_usage(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    # The command's own usage and argparse's message, each on an
    # `aws: [ERROR]: ` line of its own; the usage names the program `aws`
    # too (customizations/commands.py:336-342).
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, ["s3"], env, timeout=20)
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert stderr.decode() == (
        f"{PARAM_VALIDATION_PREFIX}usage: aws [options] s3 <subcommand> "
        "[parameters]\n"
        "aws: [ERROR]: too few arguments\n"
    )
    assert not server.requests


@pytest.mark.asyncio
async def test_parse_error_for_extra_ls_operand_names_it_unknown(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    # `s3 ls` takes one path, so the second is left over as an option.
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "a", "b"], env, timeout=20
    )
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert stderr.decode() == f"{PARAM_VALIDATION_PREFIX}Unknown options: b\n"
    assert not server.requests


# A missing option value fails in the parser before any request, whether
# the native renderer or the Python CLI reports it; `--version` is a
# control option that exits before arguments are validated, and `--help`
# is another, which test_help_wins_over_a_missing_option_value covers. S3
# renders natively and Lambda reaches the embedded CLI with the original
# argv.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,option",
    [
        (["s3", "cp", "--page-size", "--recursive"], "--page-size"),
        (["s3", "cp", "--page-size", "--"], "--page-size"),
        (["s3", "cp", "--page-size"], "--page-size"),
        (
            ["lambda", "invoke", "--function-name", "--region", "us-east-1"],
            "--function-name",
        ),
        (["lambda", "invoke", "--function-name", "--"], "--function-name"),
        (["lambda", "invoke", "--function-name"], "--function-name"),
    ],
    ids=[
        "s3-flag",
        "s3-separator",
        "s3-end",
        "lambda-flag",
        "lambda-separator",
        "lambda-end",
    ],
)
async def test_parse_error_for_a_missing_option_value(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
    option: str,
) -> None:
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert f"argument {option}: expected one argument" in stderr.decode()
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        ["s3", "cp", "--page-size", "--version"],
        ["lambda", "invoke", "--function-name", "--version"],
    ],
    ids=["s3", "lambda"],
)
async def test_version_wins_over_a_missing_option_value(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
) -> None:
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert (rc, stderr) == (0, b""), stderr.decode()
    assert stdout.startswith(b"aws-cli/2."), stdout
    assert not server.requests


# `--help` renders the command's help page even when the option before it
# lacks its value: the AWS CLI parses its globals again in help mode, and
# the command renders help before it parses its own options. Each case
# names a synopsis line of the page. The pager is pinned so a developer's
# own MANPAGER or PAGER cannot decide whether the page reaches stdout;
# Windows' default, `more`, streams to a pipe.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,synopsis",
    [
        (["s3", "cp", "--page-size", "--help"], "[--page-size <value>]"),
        (
            ["lambda", "invoke", "--function-name", "--help"],
            "--function-name <value>",
        ),
    ],
    ids=["s3", "lambda"],
)
async def test_help_wins_over_a_missing_option_value(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
    synopsis: str,
) -> None:
    server, env = parse_runtime
    env["MANPAGER"] = "more" if sys.platform == "win32" else "/bin/cat"
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert rc == 0, stderr.decode()
    assert synopsis in stdout.decode()
    assert not server.requests


# `-h` is no option of the AWS CLI's, so the leftover option fails the
# parse whatever the operands are: the plain targets stay native, and the
# operand shapes only Python implements fail before they are looked at.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        ["s3", "-h"],
        ["s3", "ls", "bucket/prefix", "-h"],
        [
            "s3",
            "cp",
            "s3://source-bucket/source",
            "s3://destination-bucket/destination",
            "-h",
        ],
        [
            "s3",
            "ls",
            "s3://arn:aws:s3:us-east-1:123456789012:accesspoint/example",
            "-h",
        ],
        ["s3", "cp", "-", "s3://bucket/key", "-h"],
        ["s3", "cp", "s3:/bucket/key", "destination", "-h"],
    ],
    ids=[
        "s3",
        "ls-plain-target",
        "cp-s3-to-s3",
        "ls-access-point",
        "cp-stdin",
        "cp-single-slash",
    ],
)
async def test_parse_error_for_a_leftover_help_option(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
) -> None:
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert stderr.decode() == (
        f"{PARAM_VALIDATION_PREFIX}Unknown options: -h\n"
    )
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,message",
    [
        (["--output", "definitely-invalid", "s3", "ls"], "invalid choice"),
        (
            ["s3", "cp", "--debug"],
            "the following arguments are required: paths",
        ),
        (
            ["--endpoint-url", "http://localhost:4566", "s3", "cp"],
            "the following arguments are required: paths",
        ),
        (
            ["lambda", "invoke"],
            "the following arguments are required: --function-name, outfile",
        ),
        (
            ["lambda", "wait", "function-exists"],
            "the following arguments are required: --function-name",
        ),
        (["lambda", "wait"], "too few arguments"),
        (
            ["lambda", "list-functions", "--bogus-option", "value"],
            "Unknown options: --bogus-option, value",
        ),
        (["lambda", "bogus-operation"], "Found invalid choice 'bogus-operation'"),
        # The wizard registers its parser before the subcommand's.
        (["lambda", "wizard"], "too few arguments"),
        (
            ["lambda", "--debug"],
            "the following arguments are required: operation",
        ),
    ],
    ids=[
        "invalid-output",
        "cp-debug",
        "cp-endpoint-url",
        "lambda-invoke",
        "lambda-waiter",
        "lambda-wait",
        "lambda-unknown-option",
        "lambda-unknown-operation",
        "lambda-wizard",
        "lambda-debug",
    ],
)
async def test_parse_error_names_the_problem(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
    message: str,
) -> None:
    server, env = parse_runtime
    stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)
    assert (rc, stdout) == (252, b""), stderr.decode()
    assert message in stderr.decode()
    assert not server.requests


# Each native framing of a parse failure: a leftover token after a target,
# the bare int() error, and the legacy format. Forced native shows the
# command stayed native; another AWS CLI and the Python route ignore the
# variable and print the same bytes.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,status,stderr",
    [
        (
            ["s3", "ls", "s3://bucket", "--bogus"],
            252,
            f"{PARAM_VALIDATION_PREFIX}Unknown options: --bogus\n",
        ),
        (
            ["s3", "ls", "--page-size", "abc", "--bogus"],
            255,
            "\naws: [ERROR]: invalid literal for int() with base 10: 'abc'\n",
        ),
        (
            ["--cli-error-format", "legacy", "s3", "cp", "a", "b", "c"],
            252,
            "\naws: [ERROR]: Unknown options: c\n",
        ),
    ],
    ids=["leftover-option", "page-size-int", "legacy-format"],
)
async def test_native_parse_failures_render_as_upstream(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    arguments: list[str],
    status: int,
    stderr: str,
) -> None:
    server, env = parse_runtime
    # The error format comes from the environment, so the empty profile,
    # which a profile lookup would refuse, shows the parse fails first.
    env.update(
        AWS_PROFILE="",
        AWS_CLI_ERROR_FORMAT="enhanced",
        AWS_CLI_NATIVE_ROUTER="native",
    )
    result = await run_cli(aws_cli, arguments, env, timeout=20)
    assert result == (b"", stderr.encode(), status), result[1].decode()
    assert not server.requests


# A diagnostic that cannot be written, to a pipe whose reader has closed,
# still ends the command with status 1 rather than SIGPIPE, which the child
# gets at its default disposition, as a shell gives it.
@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="Windows has no SIGPIPE")
async def test_parse_failure_on_a_closed_stderr_exits_one(
    aws_cli: str,
    parse_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = parse_runtime
    with failing_stream("closed-pipe") as stderr:
        status = await run_cli_with_streams(
            aws_cli,
            ["s3", "cp", "only-one-path"],
            env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=stderr,
        )
    assert status == 1
    assert not server.requests
