"""`s3 rb`'s requests (upstream tests/functional/s3/test_rb_command.py)."""

from typing import Final

import pytest

from apihelpers import ApiSession, Reply

pytestmark = pytest.mark.asyncio

# Upstream answers every request with an empty 500.
SERVER_ERROR: Final = Reply(status=500)


async def test_rb_sends_only_delete_bucket(s3api: ApiSession) -> None:
    result = await s3api.run("s3 rb s3://bucket")
    assert result.operations == ["DeleteBucket"], result.describe()


async def test_rb_force_empty_bucket_lists_then_deletes_bucket(
    s3api: ApiSession,
) -> None:
    result = await s3api.run("s3 rb s3://bucket --force")
    assert result.operations == [
        "ListObjectsV2",
        "DeleteBucket",
    ], result.describe()


async def test_rb_force_non_empty_bucket_deletes_objects_first(
    s3api: ApiSession,
) -> None:
    listing = {
        "Contents": [
            {
                "Key": "foo",
                "Size": 100,
                "LastModified": "2016-03-01T23:50:13.000Z",
            }
        ]
    }
    result = await s3api.run(
        "s3 rb s3://bucket --force", replies=[listing, {}, {}]
    )
    assert result.operations == [
        "ListObjectsV2",
        "DeleteObject",
        "DeleteBucket",
    ], result.describe()


async def test_rb_failure_exits_1(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 rb s3://bucket", replies=SERVER_ERROR, expected_rc=1
    )
    assert "remove_bucket failed:" in result.stderr, result.describe()


async def test_rb_force_with_failed_rm_stops_after_listing(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        "s3 rb s3://bucket --force", replies=SERVER_ERROR, expected_rc=255
    )
    assert "remove_bucket failed:" in result.stderr, result.describe()
    assert result.operations == ["ListObjectsV2"], result.describe()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param("bucket", id="no-uri-scheme"),
        pytest.param("s3://bucket/key --force", id="key-with-force"),
        pytest.param("s3://bucket/key", id="key"),
    ],
)
async def test_rb_rejects_path(s3api: ApiSession, args: str) -> None:
    await s3api.run(f"s3 rb {args}", expected_rc=252)
