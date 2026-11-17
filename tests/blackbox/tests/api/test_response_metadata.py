"""ResponseMetadata stays out of the output (upstream
tests/functional/test_response_metadata.py)."""

import json
from typing import Final

import pytest

from apihelpers import ApiSession, Reply

pytestmark = pytest.mark.asyncio

ERRORS: Final = [
    {
        "Key": "key",
        "VersionId": "version-id",
        "Code": "NoSuchVersion",
        "Message": "The specified version does not exist.",
    }
]


async def test_excludes_response_metadata_when_errors_key_present(
    api: ApiSession,
) -> None:
    # The request ids give botocore's parse a ResponseMetadata to drop.
    reply = Reply(
        {"Errors": ERRORS},
        headers={
            "x-amz-id-2": "REQUEST-ID-2",
            "x-amz-request-id": "REQUEST-ID",
        },
    )
    run = await api.run(
        [
            "s3api",
            "delete-objects",
            "--bucket",
            "bucket",
            "--delete",
            "Objects=[{Key=key,VersionId=version-id}]",
        ],
        replies=reply,
    )
    assert "ResponseMetadata" not in run.stdout
    assert json.loads(run.stdout) == {"Errors": ERRORS}
    assert run.operations == ["DeleteObjects"]
