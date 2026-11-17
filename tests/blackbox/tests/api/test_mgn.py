"""Application Migration Service commands' requests (upstream
tests/functional/mgn)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "option",
    [
        pytest.param("--source-server-i-ds", id="old-argname"),
        pytest.param("--source-server-ids", id="fixed-param-name"),
    ],
)
async def test_start_cutover_source_server_ids(
    api: ApiSession, option: str
) -> None:
    server_id = "a" * 50
    await api.assert_params_for_cmd(
        f"mgn start-cutover {option} {server_id}",
        {"sourceServerIDs": [server_id]},
    )
