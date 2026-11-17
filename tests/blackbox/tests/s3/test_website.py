"""`s3 website`'s requests (upstream
tests/functional/s3/test_website_command.py)."""

from typing import Any

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("args", "configuration"),
    [
        pytest.param(
            "--index-document index.html",
            {"IndexDocument": {"Suffix": "index.html"}},
            id="index-document",
        ),
        pytest.param(
            "--error-document mykey",
            {"ErrorDocument": {"Key": "mykey"}},
            id="error-document",
        ),
    ],
)
async def test_website_configuration(
    s3api: ApiSession, args: str, configuration: dict[str, Any]
) -> None:
    # botocore names its default request checksum after upstream's
    # in-process capture.
    await s3api.assert_params_for_cmd(
        f"s3 website s3://mybucket {args}",
        {
            "WebsiteConfiguration": configuration,
            "Bucket": "mybucket",
            "ChecksumAlgorithm": "CRC64NVME",
        },
    )
