"""WorkSpaces' workspace-request shorthand (upstream
tests/functional/workspaces)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("action", "member"),
    [
        pytest.param("reboot", "RebootWorkspaceRequests", id="reboot"),
        pytest.param("rebuild", "RebuildWorkspaceRequests", id="rebuild"),
        pytest.param(
            "terminate", "TerminateWorkspaceRequests", id="terminate"
        ),
    ],
)
async def test_workspace_ids_become_requests(
    api: ApiSession, action: str, member: str
) -> None:
    await api.assert_params_for_cmd(
        f"workspaces {action}-workspaces"
        f" --{action}-workspace-requests id1 id2 id3",
        {
            member: [
                {"WorkspaceId": "id1"},
                {"WorkspaceId": "id2"},
                {"WorkspaceId": "id3"},
            ]
        },
    )
