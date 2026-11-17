# Fixtures shared by the S3 transfer test modules.
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer
from localstub.handlers import handle_expect_header

from apihelpers import (
    CRT_TRANSFER_CONFIG,
    S3_TRANSFER_CONFIG,
    ApiSession,
    api_session,
)
from credhelpers import credential_env
from tests.blackbox.utils import mock_server


@pytest_asyncio.fixture
async def transfer_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with mock_server(handle_expect_header) as (server, proxy):
        env = credential_env(proxy, tmp_path)
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        yield server, env


@pytest.fixture(
    params=[[], ["--no-progress"], ["--quiet"], ["--only-show-errors"]],
    ids=["default", "no-progress", "quiet", "errors-only"],
)
def output_flags(request: pytest.FixtureRequest) -> list[str]:
    return request.param


@pytest.fixture(
    params=[
        (["--exclude", "*", "--include", "*.txt"], ["a.txt", "nested/b.txt"]),
        (["--include", "*.txt", "--exclude", "*"], []),
        (
            ["--exclude", "*", "--include", "nested/*"],
            ["nested/b.txt", "nested/c.bin"],
        ),
        (
            ["--exclude", "*", "--include", "*.txt", "--exclude", "nested/*"],
            ["a.txt"],
        ),
    ],
    ids=["include-last", "exclude-last", "nested", "exclude-again"],
)
def filter_case(request: pytest.FixtureRequest) -> tuple[list[str], list[str]]:
    return request.param


@pytest_asyncio.fixture
async def s3api(aws_cli: str, tmp_path: Path) -> AsyncIterator[ApiSession]:
    """Upstream's S3 transfer test environment: the classic client, run
    serially, one attempt per request. Both routes run such a command on
    the in-tree AWS CLI."""
    async with api_session(aws_cli, tmp_path, S3_TRANSFER_CONFIG) as session:
        yield session


@pytest_asyncio.fixture
async def s3crt(aws_cli: str, tmp_path: Path) -> AsyncIterator[ApiSession]:
    """The same environment with the CRT client preferred and the default
    attempt count, so a command native supports runs on native by default
    and on upstream's CRT client on the Python route."""
    async with api_session(
        aws_cli, tmp_path, CRT_TRANSFER_CONFIG, single_attempt=False
    ) as session:
        yield session


@pytest_asyncio.fixture(params=["classic", "crt"])
async def transfer_api(
    request: pytest.FixtureRequest, aws_cli: str, tmp_path: Path
) -> AsyncIterator[ApiSession]:
    """`s3api`, then `s3crt`: a test both clients pass runs on each."""
    crt = request.param == "crt"
    async with api_session(
        aws_cli,
        tmp_path,
        CRT_TRANSFER_CONFIG if crt else S3_TRANSFER_CONFIG,
        single_attempt=not crt,
    ) as session:
        yield session
