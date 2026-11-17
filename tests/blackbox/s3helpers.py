"""Output helpers for the S3 transfer blackbox tests."""

import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

import pytest
from localstub import AsyncHTTPTestServer

from harness_plugin import command_environment

# Each stdout every write fails on, with `type(e).__name__` and `str(e)` of
# the OSError CPython raises for the write. A Windows write error names no
# errno the native path reports, so it keeps a report of its own there.
FAILING_STDOUTS = [
    pytest.param(
        "full",
        "OSError",
        "[Errno 28] No space left on device",
        id="full",
        marks=pytest.mark.skipif(
            not os.path.exists("/dev/full"), reason="the host has no /dev/full"
        ),
    ),
    pytest.param(
        "closed-pipe",
        "BrokenPipeError",
        "[Errno 32] Broken pipe",
        id="closed-pipe",
        marks=pytest.mark.skipif(
            os.name == "nt", reason="a Windows write error names no errno"
        ),
    ),
    pytest.param(
        "read-only",
        "OSError",
        "[Errno 9] Bad file descriptor",
        id="read-only",
        marks=pytest.mark.skipif(
            os.name == "nt", reason="a Windows write error names no errno"
        ),
    ),
]

# The same descriptors as stderr. CPython reports nothing when its flush of
# stderr at exit fails, so only the status tells the failures apart.
FAILING_STDERRS = [
    pytest.param(param.values[0], id=param.id, marks=param.marks)
    for param in FAILING_STDOUTS
]


def assert_refused_before_request(
    result: tuple[bytes, bytes, int], server: AsyncHTTPTestServer
) -> None:
    """The command failed and sent no request."""
    stdout, stderr, rc = result
    assert rc != 0, stderr.decode()
    assert stdout == b"", stderr.decode()
    assert not server.requests


def completion_lines(stdout: bytes) -> list[str]:
    # Progress contains variable timings and carriage returns. Assert status
    # lines independently without snapshotting scheduling-dependent rates.
    return [
        line.strip()
        for line in stdout.decode().splitlines()
        if line.strip() and not line.startswith("Completed ")
    ]


@contextmanager
def failing_stream(kind: str) -> Iterator[int]:
    """A descriptor every write to fails on, as FAILING_STDOUTS names it.

    `full` is /dev/full, `closed-pipe` a pipe whose reader has closed, and
    `read-only` the null device opened without write access.
    """
    if kind == "full":
        descriptor = os.open("/dev/full", os.O_WRONLY)
    elif kind == "read-only":
        descriptor = os.open(os.devnull, os.O_RDONLY)
    else:
        reader, descriptor = os.pipe()
        os.close(reader)
    try:
        yield descriptor
    finally:
        os.close(descriptor)


async def run_cli_with_stdout(
    aws_cli: str, args: list[str], env: dict[str, str], stdout: int
) -> tuple[bytes, int]:
    """`run_cli` with stdout on the descriptor `stdout`: (stderr, status)."""
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        *args,
        env=command_environment(env),
        stdout=stdout,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    assert process.returncode is not None
    return stderr, process.returncode


async def run_cli_with_streams(
    aws_cli: str,
    args: list[str],
    env: dict[str, str],
    stdout: int,
    stderr: int,
) -> int:
    """`run_cli` with stdout and stderr on these descriptors: the status."""
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        *args,
        env=command_environment(env),
        stdout=stdout,
        stderr=stderr,
    )
    try:
        return await asyncio.wait_for(process.wait(), timeout=60)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise


async def run_cli_without_stdout(
    aws_cli: str, args: list[str], env: dict[str, str]
) -> tuple[bytes, int]:
    """`run_cli` with fd 1 closed before the CLI starts: (stderr, status)."""
    return await run_cli_with_stdout(
        "/bin/sh",
        ["-c", 'exec "$0" "$@" >&-', aws_cli, *args],
        env,
        asyncio.subprocess.DEVNULL,
    )


CRT_SUFFIX: Final = "CRTS3NativeClient/"
# The feature ids aws-c-s3 names itself (s3_util.c `s_feature_id_strings`),
# none of which botocore names.
CRT_FEATURES: Final = frozenset({"AX", "AY", "AZ", "Aa", "Ab", "Aj", "Al"})


def user_agent_parts(user_agent: str) -> tuple[frozenset[str], frozenset[str]]:
    """The feature ids and the CLI's md/ extras botocore names in a User-Agent.

    A User-Agent's components carry no meaning in their order, so both are
    sets. The ids are gathered from every m/ section, less the CRT's own:
    aws-c-s3 moves botocore's m/ section after its own components, merged
    with its own ids, on each request it sends (s3_util.c
    `aws_s3_init_user_agent_header_cached`).
    """
    components = user_agent.split()
    features = frozenset(
        feature
        for component in components
        if component.startswith("m/")
        for feature in component[2:].split(",")
    )
    extras = frozenset(
        component
        for component in components
        if component.startswith(("md/prompt#", "md/command#"))
    )
    return features - CRT_FEATURES, extras
