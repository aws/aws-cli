# The fixture every service-command test module here runs its commands with.
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio

from apihelpers import ApiSession, api_session


@pytest_asyncio.fixture
async def api(aws_cli: str, tmp_path: Path) -> AsyncIterator[ApiSession]:
    async with api_session(aws_cli, tmp_path) as session:
        yield session
