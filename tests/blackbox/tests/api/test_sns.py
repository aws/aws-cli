"""SNS create-platform-application's requests (upstream
tests/functional/sns)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        pytest.param(
            "PlatformCredential=foo,PlatformPrincipal=bar",
            {"PlatformCredential": "foo", "PlatformPrincipal": "bar"},
            id="gcm-shorthand",
        ),
        pytest.param(
            '{"PlatformCredential":"AIzaSyClE2lcV2zEKTLYYo645zfk2jhQPFeyxDo",'
            '"PlatformPrincipal":"There+is+no+principal+for+GCM"}',
            {
                "PlatformCredential": (
                    "AIzaSyClE2lcV2zEKTLYYo645zfk2jhQPFeyxDo"
                ),
                "PlatformPrincipal": "There+is+no+principal+for+GCM",
            },
            id="gcm-json",
        ),
    ],
)
async def test_create_platform_application_sends_attributes(
    api: ApiSession, attributes: str, expected: dict[str, str]
) -> None:
    await api.assert_params_for_cmd(
        "sns create-platform-application --name gcmpushapp --platform GCM"
        f" --attributes {attributes}",
        {"Name": "gcmpushapp", "Platform": "GCM", "Attributes": expected},
    )
