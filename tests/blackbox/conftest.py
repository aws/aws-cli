"""Shared fixtures for blackbox tests."""

from __future__ import annotations

import asyncio
import os
import shutil

import pytest

from tests.blackbox.utils import cli_env, mock_server, run_cli
from localstub.server import HTTPResponse


def pytest_configure(config):
    """Heuristic to verify if the CLI binary routes traffic through
    HTTPS_PROXY before any test runs.

    If the proxy receives no request, the binary under test does not support
    HTTPS_PROXY and all tests would be invalid — fail the session immediately.
    """
    command = os.environ.get("AWS_TEST_COMMAND") or shutil.which("aws")
    if command is None:
        pytest.exit(
            "No AWS CLI binary found: set AWS_TEST_COMMAND to its path or "
            "make `aws` available on PATH.",
            returncode=1,
        )

    async def _verify():

        async with mock_server() as (server, proxy):
            server.set_response_sequence([
                HTTPResponse.raw(
                    b'<?xml version="1.0" ?>'
                    b"<Error><Code>AccessDenied</Code>"
                    b"<Message>Test</Message></Error>",
                    status=403,
                    headers={"Content-Type": "application/xml"},
                ),
            ])
            env = cli_env(proxy)
            await run_cli(command, ["s3", "ls"], env)
            return len(server.requests) > 0

    proxy_works = asyncio.run(_verify())
    if not proxy_works:
        pytest.exit(
            f"CLI binary {command!r} does not route traffic through "
            f"HTTPS_PROXY. All blackbox tests require proxy support to "
            f"prevent accidental calls to production AWS endpoints.",
            returncode=1,
        )


@pytest.fixture
def aws_cli() -> str:
    command = os.environ.get("AWS_TEST_COMMAND") or shutil.which("aws")
    if command is None:
        pytest.fail(
            "No AWS CLI binary found: set AWS_TEST_COMMAND to its path or "
            "make `aws` available on PATH."
        )
    return command


@pytest.fixture
def aws_config(tmp_path):
    """Factory fixture that writes an AWS config file and returns its path."""

    def _make(config_dict: dict[str, dict[str, str]]) -> str:
        lines = []
        for section, values in config_dict.items():
            lines.append(f"[{section}]")
            for key, val in values.items():
                lines.append(f"{key} = {val}")
            lines.append("")
        path = tmp_path / "config"
        path.write_text("\n".join(lines))
        return str(path)

    return _make
