"""`s3 ls` requests, output, and exit status (upstream
tests/functional/s3/test_ls_command.py).

The commands native supports run in both of `transfer_api`'s environments:
`[classic]` is upstream's, whose one attempt per request the default route
hands to Python, and `[crt]` the same with the default attempt count, which
native runs. `s3 ls` builds no transfer manager, so neither client setting
changes its requests.
"""

from datetime import UTC, datetime, timedelta, timezone
from typing import Final

import pytest

from apihelpers import ApiSession
from s3params import Params

pytestmark = pytest.mark.asyncio

LAST_MODIFIED: Final = "2014-01-09T20:45:49.000Z"
# Upstream prints LastModified in the local zone; a fixed zone eight hours
# west makes that shift visible and the same on every host.
ZONE: Final = "PST8"
LOCAL_TIME: Final = (
    datetime(2014, 1, 9, 20, 45, 49, tzinfo=UTC)
    .astimezone(timezone(timedelta(hours=-8)))
    .strftime("%Y-%m-%d %H:%M:%S")
)
ACCESS_POINT_ARN: Final = (
    "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
)


def objects_page(
    objects: list[tuple[str, int]], prefixes: list[str] | None = None
) -> Params:
    """A ListObjectsV2 page of `objects`, (key, size) pairs, and
    `prefixes`, its common prefixes."""
    page: Params = {
        "Contents": [
            {"Key": key, "Size": size, "LastModified": LAST_MODIFIED}
            for key, size in objects
        ]
    }
    if prefixes is not None:
        page["CommonPrefixes"] = [{"Prefix": p} for p in prefixes]
    return page


SIZES: Final = objects_page(
    [
        ("onebyte.txt", 1),
        ("onekilobyte.txt", 1024),
        ("onemegabyte.txt", 1024**2),
        ("onegigabyte.txt", 1024**3),
        ("oneterabyte.txt", 1024**4),
        ("onepetabyte.txt", 1024**5),
    ],
    [],
)


def local_line(size: str, name: str) -> str:
    return f"{LOCAL_TIME} {size} {name}\n"


async def test_operations_used_in_recursive_list(
    transfer_api: ApiSession,
) -> None:
    transfer_api.env["TZ"] = ZONE
    run = await transfer_api.run(
        "s3 ls s3://bucket/ --recursive",
        replies=[objects_page([("foo/bar.txt", 100)], [])],
    )
    # A recursive listing sends no delimiter.
    assert run.operations_with_params == [
        (
            "ListObjectsV2",
            {"Bucket": "bucket", "Prefix": "", "EncodingType": "url"},
        )
    ], run.describe()
    assert run.stdout == local_line("       100", "foo/bar.txt"), (
        run.describe()
    )


@pytest.mark.parametrize(
    ("cmd", "operation", "params"),
    [
        pytest.param(
            "s3 ls --page-size 8",
            "ListBuckets",
            {"MaxBuckets": 8},
            id="list-buckets-page-size",
        ),
        pytest.param(
            "s3 ls s3://bucket/ --page-size 8",
            "ListObjectsV2",
            {
                "Bucket": "bucket",
                "Prefix": "",
                "Delimiter": "/",
                "MaxKeys": 8,
                "EncodingType": "url",
            },
            id="list-objects-page-size",
        ),
        pytest.param(
            "s3 ls s3://bucket/ --page-size 8 --recursive",
            "ListObjectsV2",
            {
                "Bucket": "bucket",
                "Prefix": "",
                "MaxKeys": 8,
                "EncodingType": "url",
            },
            id="list-objects-page-size-recursive",
        ),
        pytest.param(
            "s3 ls s3://mybucket/foo/ --request-payer requester",
            "ListObjectsV2",
            {
                "Bucket": "mybucket",
                "Delimiter": "/",
                "RequestPayer": "requester",
                "EncodingType": "url",
                "Prefix": "foo/",
            },
            id="requester-pays",
        ),
        pytest.param(
            "s3 ls s3://mybucket/foo/ --request-payer",
            "ListObjectsV2",
            {
                "Bucket": "mybucket",
                "Delimiter": "/",
                "RequestPayer": "requester",
                "EncodingType": "url",
                "Prefix": "foo/",
            },
            id="requester-pays-no-args",
        ),
        pytest.param(
            "s3 ls --bucket-name-prefix myprefix",
            "ListBuckets",
            {"Prefix": "myprefix"},
            id="list-buckets-bucket-name-prefix",
        ),
        pytest.param(
            "s3 ls --bucket-region us-west-1",
            "ListBuckets",
            {"BucketRegion": "us-west-1"},
            id="list-buckets-bucket-region",
        ),
        pytest.param(
            "s3 ls s3://mybucket --bucket-name-prefix myprefix",
            "ListObjectsV2",
            {
                "Bucket": "mybucket",
                "Prefix": "",
                "Delimiter": "/",
                "EncodingType": "url",
            },
            id="list-objects-ignores-bucket-name-prefix",
        ),
        pytest.param(
            "s3 ls s3://mybucket --bucket-region us-west-1",
            "ListObjectsV2",
            {
                "Bucket": "mybucket",
                "Prefix": "",
                "Delimiter": "/",
                "EncodingType": "url",
            },
            id="list-objects-ignores-bucket-region",
        ),
    ],
)
async def test_ls_request_params(
    transfer_api: ApiSession, cmd: str, operation: str, params: Params
) -> None:
    replies = None
    if operation == "ListObjectsV2":
        replies = [objects_page([("onebyte.txt", 1)], [])]
    run = await transfer_api.run(cmd, replies=replies)
    assert run.operations_with_params == [(operation, params)], (
        run.describe()
    )


@pytest.mark.parametrize(
    ("cmd", "page", "expected_rc"),
    [
        pytest.param(
            "s3 ls s3://bucket/foo",
            objects_page([("foo/bar.txt", 100)], ["foo/"]),
            0,
            id="prefixes-and-objects",
        ),
        pytest.param(
            "s3 ls s3://bucket/foo",
            {"CommonPrefixes": [{"Prefix": "foo/"}]},
            0,
            id="only-prefixes",
        ),
        pytest.param(
            "s3 ls s3://bucket/foo",
            objects_page([("foo/bar.txt", 100)]),
            0,
            id="only-objects",
        ),
        # The user asked for no object, so an empty bucket is a success.
        pytest.param(
            "s3 ls s3://bucket", {}, 0, id="empty-bucket-no-key-given"
        ),
        pytest.param(
            "s3 ls s3://bucket/foo", {}, 1, id="no-objects-nor-prefixes"
        ),
    ],
)
async def test_ls_exit_status(
    transfer_api: ApiSession, cmd: str, page: Params, expected_rc: int
) -> None:
    await transfer_api.run(cmd, replies=[page], expected_rc=expected_rc)


async def test_success_rc_with_pagination(transfer_api: ApiSession) -> None:
    # Upstream's first page did not say it was truncated, so its second,
    # empty page was never asked for; this one does.
    first = objects_page([("foo/bar.txt", 100)], ["foo/"])
    first.update(IsTruncated=True, NextContinuationToken="token")
    run = await transfer_api.run(
        "s3 ls s3://bucket/foo", replies=[first, {}]
    )
    # An empty last page keeps the earlier pages' success.
    assert run.operations_with_params == [
        (
            "ListObjectsV2",
            {
                "Bucket": "bucket",
                "Prefix": "foo",
                "Delimiter": "/",
                "EncodingType": "url",
            },
        ),
        (
            "ListObjectsV2",
            {
                "Bucket": "bucket",
                "Prefix": "foo",
                "Delimiter": "/",
                "EncodingType": "url",
                "ContinuationToken": "token",
            },
        ),
    ], run.describe()


@pytest.mark.parametrize(
    ("flags", "lines"),
    [
        pytest.param(
            ["--human-readable"],
            [
                local_line("    1 Byte", "onebyte.txt"),
                local_line("   1.0 KiB", "onekilobyte.txt"),
                local_line("   1.0 MiB", "onemegabyte.txt"),
                local_line("   1.0 GiB", "onegigabyte.txt"),
                local_line("   1.0 TiB", "oneterabyte.txt"),
                local_line("   1.0 PiB", "onepetabyte.txt"),
            ],
            id="human-readable",
        ),
        pytest.param(
            ["--summarize"],
            ["Total Objects: 6\n", "Total Size: 1127000493261825\n"],
            id="summarize",
        ),
        pytest.param(
            ["--human-readable", "--summarize"],
            ["Total Objects: 6\n", "Total Size: 1.0 PiB\n"],
            id="summarize-human-readable",
        ),
    ],
)
async def test_ls_sizes(
    transfer_api: ApiSession, flags: list[str], lines: list[str]
) -> None:
    transfer_api.env["TZ"] = ZONE
    run = await transfer_api.run(
        ["s3", "ls", "s3://bucket/", *flags], replies=[SIZES]
    )
    for line in lines:
        assert line in run.stdout, run.describe()


@pytest.mark.parametrize(
    ("cmd", "contains", "lacks"),
    [
        pytest.param(
            "s3 ls --extra-argument-foo",
            ["Unknown options", "--extra-argument-foo"],
            "Maybe you meant",
            id="extra-arguments",
        ),
        pytest.param(
            "s3 ls s3://bucket --recurisve",
            ["Maybe you meant:\n  * --recursive (instead of --recurisve)"],
            None,
            id="misspelled-option",
        ),
        pytest.param(
            "s3 ls s3://bucket --regoin us-west-2",
            ["  * --region (instead of --regoin)"],
            None,
            id="misspelled-global-option",
        ),
    ],
)
async def test_ls_rejects_unknown_options(
    s3api: ApiSession, cmd: str, contains: list[str], lacks: str | None
) -> None:
    run = await s3api.run(cmd, expected_rc=252)
    for text in contains:
        assert text in run.stderr, run.describe()
    if lacks is not None:
        assert lacks not in run.stderr, run.describe()
    assert run.calls == (), run.describe()


async def test_accesspoint_arn(s3api: ApiSession) -> None:
    page = objects_page([("bar.txt", 100)], [])
    run = await s3api.run(f"s3 ls s3://{ACCESS_POINT_ARN}", replies=[page])
    # The ARN reaches the wire as its access point's endpoint.
    assert [
        (call.operation, call.request.headers.get("host"))
        for call in run.calls
    ] == [
        (
            "ListObjectsV2",
            "endpoint-123456789012.s3-accesspoint.us-west-2.amazonaws.com",
        )
    ], run.describe()

