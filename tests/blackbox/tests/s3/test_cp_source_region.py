"""`s3 cp --source-region` sends a copy's reads to the source bucket's
region and its writes to the destination's (upstream
tests/functional/s3/test_cp_command.py, TestCpSourceRegion).

Upstream's CLIRunner queues raw HTTP responses and checks that each was
used; these queue the same responses and check that every one answered a
request. The run is that runner's environment: region us-west-2 and the
classic client, run serially.
"""

from typing import Final

import pytest
from localstub import HTTPResponse

from apihelpers import ApiSession, CommandRun

pytestmark = pytest.mark.asyncio

MB: Final = 1024**2
MULTIPART_THRESHOLD: Final = 8 * MB
REGION: Final = "us-west-2"
SOURCE_REGION: Final = "af-south-1"
SOURCE_HOST: Final = f"sourcebucket.s3.{SOURCE_REGION}.amazonaws.com"
TARGET_HOST: Final = f"bucket.s3.{REGION}.amazonaws.com"


def head_object(size: int = 100) -> HTTPResponse:
    return HTTPResponse.raw(
        b"",
        headers={
            "Content-Length": str(size),
            "Last-Modified": "Thu, 11 Feb 2021 04:24:23 GMT",
            "ETag": "foobar",
        },
    )


def list_objects(keys: list[str], size: int = 100) -> HTTPResponse:
    contents = "".join(
        "<Contents>"
        "<LastModified>2015-12-08T18:26:43.000Z</LastModified>"
        f"<Key>{key}</Key><Size>{size}</Size><ETag>foobar</ETag>"
        "</Contents>"
        for key in keys
    )
    return xml(
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Prefix/>{contents}</ListBucketResult>"
    )


def xml(body: str) -> HTTPResponse:
    return HTTPResponse.raw(body.encode())


def copy_object() -> HTTPResponse:
    return xml("<CopyObjectResult></CopyObjectResult>")


def create_multipart_upload() -> HTTPResponse:
    return xml(
        "<InitiateMultipartUploadResult>"
        "  <Bucket>bucket</Bucket>"
        "  <Key>key</Key>"
        "  <UploadId>upload-id</UploadId>"
        "</InitiateMultipartUploadResult>"
    )


def upload_part_copy() -> HTTPResponse:
    return xml(
        "<CopyPartResult>"
        "  <LastModified>2022-09-30T17:20:13.000Z</LastModified>"
        "  <ETag>&quot;etag&quot;</ETag>"
        "</CopyPartResult>"
    )


def complete_multipart_upload() -> HTTPResponse:
    return xml(
        "<CompleteMultipartUploadResult></CompleteMultipartUploadResult>"
    )


def get_object_tagging(tags: dict[str, str] | None = None) -> HTTPResponse:
    tag_set = "".join(
        f"<Tag><Key>{key}</Key><Value>{value}</Value></Tag>"
        for key, value in (tags or {}).items()
    )
    return xml(f"<Tagging><TagSet>{tag_set}</TagSet></Tagging>")


def empty() -> HTTPResponse:
    return HTTPResponse.raw(b"")


def endpoints(run: CommandRun) -> list[tuple[str, str]]:
    """Each request's operation and the host it went to."""
    return [
        (call.operation, call.request.headers.get("host", ""))
        for call in run.calls
    ]


async def copy(
    api: ApiSession, source: str, replies: list[HTTPResponse], *extra: str
) -> CommandRun:
    api.env["AWS_DEFAULT_REGION"] = REGION
    run = await api.run(
        [
            "s3",
            "cp",
            source,
            "s3://bucket/",
            "--source-region",
            SOURCE_REGION,
            "--region",
            REGION,
            *extra,
        ],
        replies=replies,
    )
    # Every queued response answered a request.
    assert len(run.calls) == len(replies), run.describe()
    return run


async def test_respects_source_region_for_single_copy(
    s3api: ApiSession,
) -> None:
    run = await copy(
        s3api, "s3://sourcebucket/key", [head_object(), copy_object()]
    )
    assert endpoints(run) == [
        ("HeadObject", SOURCE_HOST),
        ("CopyObject", TARGET_HOST),
    ], run.describe()


async def test_respects_source_region_for_recursive_copy(
    s3api: ApiSession,
) -> None:
    run = await copy(
        s3api,
        "s3://sourcebucket/",
        [list_objects(["key"]), copy_object()],
        "--recursive",
    )
    assert endpoints(run) == [
        ("ListObjectsV2", SOURCE_HOST),
        ("CopyObject", TARGET_HOST),
    ], run.describe()


async def test_respects_source_region_for_copying_mp_object_tags(
    s3api: ApiSession,
) -> None:
    run = await copy(
        s3api,
        "s3://sourcebucket/key",
        [
            head_object(size=MULTIPART_THRESHOLD),
            get_object_tagging({"tag": "value" * (2 * 1024)}),
            create_multipart_upload(),
            upload_part_copy(),
            complete_multipart_upload(),
            empty(),
        ],
    )
    assert endpoints(run) == [
        ("HeadObject", SOURCE_HOST),
        ("GetObjectTagging", SOURCE_HOST),
        ("CreateMultipartUpload", TARGET_HOST),
        ("UploadPartCopy", TARGET_HOST),
        ("CompleteMultipartUpload", TARGET_HOST),
        ("PutObjectTagging", TARGET_HOST),
    ], run.describe()


async def test_respects_source_region_for_recursive_mp_copy(
    s3api: ApiSession,
) -> None:
    run = await copy(
        s3api,
        "s3://sourcebucket/",
        [
            list_objects(["key"], size=MULTIPART_THRESHOLD),
            head_object(size=MULTIPART_THRESHOLD),
            get_object_tagging(),
            create_multipart_upload(),
            upload_part_copy(),
            complete_multipart_upload(),
        ],
        "--recursive",
    )
    assert endpoints(run) == [
        ("ListObjectsV2", SOURCE_HOST),
        ("HeadObject", SOURCE_HOST),
        ("GetObjectTagging", SOURCE_HOST),
        ("CreateMultipartUpload", TARGET_HOST),
        ("UploadPartCopy", TARGET_HOST),
        ("CompleteMultipartUpload", TARGET_HOST),
    ], run.describe()
