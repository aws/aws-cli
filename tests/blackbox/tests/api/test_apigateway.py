"""API Gateway commands' requests (upstream tests/functional/apigateway)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_put_integration_sends_every_argument(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "apigateway put-integration --rest-api-id api-id"
        " --resource-id resource-id --http-method GET --type HTTP"
        " --integration-http-method GET --uri https://api.endpoint.com",
        {
            "restApiId": "api-id",
            "resourceId": "resource-id",
            "httpMethod": "GET",
            "type": "HTTP",
            "integrationHttpMethod": "GET",
            "uri": "https://api.endpoint.com",
        },
    )
