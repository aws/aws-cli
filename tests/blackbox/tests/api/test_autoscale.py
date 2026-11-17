"""Auto Scaling commands' requests (upstream tests/functional/autoscale)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

TERMINATE = (
    "autoscaling terminate-instance-in-auto-scaling-group"
    " --instance-id i-12345678"
)


@pytest.mark.parametrize(
    ("flags", "decrement"),
    [
        pytest.param(" --should-decrement-desired-capacity", True, id="true"),
        pytest.param(
            " --no-should-decrement-desired-capacity", False, id="false"
        ),
        # The negated flag comes last, so it wins.
        pytest.param(
            " --should-decrement-desired-capacity"
            " --no-should-decrement-desired-capacity",
            False,
            id="last-arg-wins",
        ),
    ],
)
async def test_terminate_instance_sends_decrement_flag(
    api: ApiSession, flags: str, decrement: bool
) -> None:
    await api.assert_params_for_cmd(
        TERMINATE + flags,
        {
            "InstanceId": "i-12345678",
            "ShouldDecrementDesiredCapacity": decrement,
        },
    )
