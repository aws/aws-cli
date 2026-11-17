"""Machine Learning's predict command (upstream
tests/functional/machinelearning)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_predict_sends_to_predict_endpoint(api: ApiSession) -> None:
    result = await api.assert_params_for_cmd(
        "machinelearning predict --ml-model-id ml-foo"
        " --record Foo=Bar,Biz=Baz"
        " --predict-endpoint https://myendpoint.amazonaws.com",
        {
            "MLModelId": "ml-foo",
            "Record": {"Foo": "Bar", "Biz": "Baz"},
            "PredictEndpoint": "https://myendpoint.amazonaws.com",
        },
    )
    # The request goes to the predict endpoint, not the service's own.
    assert result.calls[-1].request.headers["host"] == (
        "myendpoint.amazonaws.com"
    )
