"""ECR's get-login-password command (upstream tests/functional/ecr)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_prints_login_password(api: ApiSession) -> None:
    reply = {
        "authorizationData": [
            {
                # "foo:bar": the command prints the part after the colon.
                "authorizationToken": "Zm9vOmJhcg==",
                "proxyEndpoint": "1235.ecr.us-east-1.io",
                "expiresAt": "2015-10-16T00:00:00Z",
            }
        ]
    }
    result = await api.run("ecr get-login-password", replies=[reply])
    assert result.stdout == "bar\n"
    assert result.operations_with_params == [("GetAuthorizationToken", {})]
