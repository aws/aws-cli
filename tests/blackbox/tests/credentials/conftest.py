# Fixtures and proxy safety checks shared by the credential suites. Each
# test here resolves credentials through a provider whose requests must
# reach localstub, never real AWS.
import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from credhelpers import (
    TEST_COMMAND_ENV_VAR,
    Sandbox,
    Stub,
    export_credentials_command,
    reaches_imds_through_proxy,
    reaches_sts_through_proxy,
)
from tests.blackbox.utils import mock_server


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)


@pytest_asyncio.fixture
async def stub() -> AsyncIterator[Stub]:
    async with mock_server() as (server, proxy):
        yield server, proxy


def cli_under_test() -> str:
    """The binary upstream's `aws_cli` fixture names, for session scope.

    A session fixture cannot use the function-scoped `aws_cli` fixture,
    so this resolves the command the same way.
    """
    command = os.environ.get(TEST_COMMAND_ENV_VAR) or shutil.which("aws")
    if command is None:
        pytest.fail(
            f"No AWS CLI binary found: set {TEST_COMMAND_ENV_VAR} to its "
            "path or make `aws` available on PATH.",
            pytrace=False,
        )
    return command


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def sts_routes_through_proxy(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Fail the requesting test if the CLI sends STS around HTTPS_PROXY.

    Every module whose tests can reach STS requests it through
    `pytestmark`, so a CLI without web-identity support fails only those
    modules. It fails (never pytest.exit) unless one `aws configure
    export-credentials` run with a web-identity profile sent its STS call
    through the TLS intercept proxy; a session fixture that fails errors
    every test that uses it.
    """
    aws_cli = cli_under_test()
    workdir = tmp_path_factory.mktemp("sts-proxy-safety")
    if not await reaches_sts_through_proxy(
        export_credentials_command(aws_cli), workdir
    ):
        pytest.fail(
            f"{aws_cli!r} does not route its STS call through HTTPS_PROXY; "
            "export-credentials tests would reach real AWS",
            pytrace=False,
        )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def imds_routes_through_proxy(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Fail the requesting test unless the CLI sends IMDS via HTTP_PROXY.

    Requested by every test that enables IMDS, whose runs would otherwise
    contact the real link-local endpoint if the CLI ignored HTTP_PROXY,
    and on an EC2-hosted runner fetch real instance credentials. The
    check never makes that first contact itself: its first run points
    IMDS at a `.invalid` endpoint, which never resolves, and must send
    `PUT http://imds-proxy-check.invalid/latest/api/token` to the
    HTTP_PROXY stub. Only then do runs with the default IPv4 and the IPv6
    endpoints have to send their token PUTs there too.
    """
    aws_cli = cli_under_test()
    workdir = tmp_path_factory.mktemp("imds-proxy-safety")
    if not await reaches_imds_through_proxy(
        export_credentials_command(aws_cli), workdir
    ):
        pytest.fail(
            f"{aws_cli!r} does not send its IMDS token request through "
            "HTTP_PROXY in absolute form",
            pytrace=False,
        )
