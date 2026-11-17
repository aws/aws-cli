"""ECR Public's get-login-password command (upstream
tests/functional/ecr_public)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_prints_login_password(api: ApiSession) -> None:
    reply = {
        "authorizationData": {
            # "foo:bar": the command prints the part after the colon.
            "authorizationToken": "Zm9vOmJhcg==",
            "expiresAt": "2015-10-16T00:00:00Z",
        }
    }
    result = await api.run("ecr-public get-login-password", replies=[reply])
    assert result.stdout == "bar\n"
    assert result.operations_with_params == [("GetAuthorizationToken", {})]
