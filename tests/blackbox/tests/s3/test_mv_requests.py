"""`s3 mv`'s requests (upstream tests/functional/s3/test_mv_command.py).

Upstream's classic-client tests run on the classic client its base class
pins. Native hands most of their commands to the Python CLI: moves from
S3 to S3, access point operands, and the other options they test. The
no-overwrite uploads and the no-overwrite download onto an existing file,
which native runs, also run on the CRT client (`transfer_api`), whose
requests there match the classic client's. Upstream's CRT client tests
assert what the CRT client was asked to send; here the requests on the
wire are asserted, the CRT client's told apart by their User-Agent.
Upstream's module also collects the sync case-conflict tests it imports,
which test_sync_requests.py ports.
"""

import base64
import tempfile
import zlib
from pathlib import Path
from typing import Any, Final

import pytest

from apihelpers import ApiSession, Call, Reply
from s3params import (
    access_denied_error_response,
    complete_mpu_request,
    copy_object_request,
    create_mpu_request,
    create_mpu_response,
    delete_object_request,
    get_object_request,
    get_object_response,
    get_object_tagging_request,
    get_object_tagging_response,
    head_object_request,
    head_object_response,
    list_objects_response,
    precondition_failed_error_response,
    put_object_tagging_request,
    upload_part_copy_request,
    upload_part_copy_response,
)

pytestmark = pytest.mark.asyncio


def filesystem_is_case_insensitive() -> bool:
    """Whether a temporary directory's names ignore case, as upstream's
    `skip_if_case_sensitive` decides."""
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "aws-cli-tmp-file").touch()
        return (Path(directory) / "AWS-CLI-TMP-FILE").exists()


CASE_INSENSITIVE: Final = filesystem_is_case_insensitive()
needs_case_insensitive_filesystem: Final = pytest.mark.skipif(
    not CASE_INSENSITIVE,
    reason="This test requires a case-insensitive filesystem.",
)

MIB: Final = 1024**2
# The body upstream's GetObject fixture serves; its HeadObject and
# listing fixtures say 100 bytes, so these say 3 instead.
BODY: Final = b"foo"
HEAD: Final = head_object_response(ContentLength=len(BODY))
GET: Final = get_object_response(BODY)
# S3's DeleteObject answer: 204 with its request ids. The CRT client
# rejects a 204 without headers.
DELETED: Final = Reply(
    headers={"x-amz-request-id": "REQUESTID", "x-amz-id-2": "HOSTID"}
)
# S3 answers a failed condition with 412; upstream's fixture with 400.
PRECONDITION_FAILED: Final = Reply(
    precondition_failed_error_response(), status=412
)
# Upstream's CRT client tests run in this region.
CRT_REGION: Final = "us-west-2"
CRT_HOST: Final = f"bucket.s3.{CRT_REGION}.amazonaws.com"
# The CRT client appends its name to the User-Agent of each request it
# sends.
CRT_USER_AGENT: Final = "CRTS3NativeClient/"


def crc32(body: bytes) -> str:
    """The base64 CRC32 S3 names a body's checksum with."""
    return base64.b64encode(zlib.crc32(body).to_bytes(4, "big")).decode()


def sent_by_crt(call: Call) -> bool:
    return CRT_USER_AGENT in call.request.headers.get("user-agent", "")


def wire_requests(
    calls: tuple[Call, ...],
) -> list[tuple[str, str, str, bool]]:
    """Each request's method, host, and target, and whether the CRT client
    sent it: upstream's CRT tests tell the CRT client's requests from
    botocore's."""
    return [
        (
            call.request.method,
            call.request.headers.get("host", ""),
            call.request.target,
            sent_by_crt(call),
        )
        for call in calls
    ]


def write_file(directory: Path, name: str, content: bytes) -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


@pytest.mark.parametrize(
    "destination",
    [
        pytest.param("s3://bucket/key", id="same-key"),
        pytest.param("s3://bucket/", id="implied-name"),
    ],
)
async def test_mv_refuses_object_onto_itself(
    s3api: ApiSession, destination: str
) -> None:
    result = await s3api.run(
        f"s3 mv s3://bucket/key {destination}", expected_rc=252
    )
    assert "Cannot mv a file onto itself" in result.stderr, result.describe()


async def test_mv_dryrun_sends_only_head_object(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 mv s3://bucket/key.txt s3://bucket/key2.txt --dryrun",
        replies=[head_object_response()],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert (
        "(dryrun) move: s3://bucket/key.txt to s3://bucket/key2.txt"
        in result.stdout
    ), result.describe()


async def test_mv_website_redirect_is_not_a_paramfile(
    s3api: ApiSession,
) -> None:
    source = write_file(s3api.cwd, "foo.txt", b"mycontent")
    result = await s3api.run(
        [
            "s3",
            "mv",
            str(source),
            "s3://bucket/key.txt",
            "--website-redirect",
            "http://someserver",
        ],
        replies=[{"ETag": '"c8afdb36c52cf4727836669019e69222"'}],
    )
    assert result.operations == ["PutObject"], result.describe()
    assert result.calls[0].params["WebsiteRedirectLocation"] == (
        "http://someserver"
    ), result.describe()


async def test_mv_copy_passes_metadata_directive(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 mv s3://bucket/key.txt s3://bucket/key2.txt"
        " --metadata-directive REPLACE",
        replies=[
            head_object_response(ETag='"foo"'),
            {"CopyObjectResult": {"ETag": '"foo-1"'}},
            DELETED,
        ],
    )
    assert result.operations == [
        "HeadObject",
        "CopyObject",
        "DeleteObject",
    ], result.describe()
    assert (
        result.calls[1].params["MetadataDirective"] == "REPLACE"
    ), result.describe()


async def test_mv_upload_sends_no_metadata_directive(
    s3api: ApiSession,
) -> None:
    source = write_file(s3api.cwd, "foo.txt", b"mycontent")
    result = await s3api.run(
        [
            "s3",
            "mv",
            str(source),
            "s3://bucket",
            "--metadata-directive",
            "REPLACE",
        ],
        replies=[{"ETag": '"c8afdb36c52cf4727836669019e69222"'}],
    )
    assert result.operations == ["PutObject"], result.describe()
    assert "MetadataDirective" not in result.calls[0].params


async def test_mv_download_with_request_payer(s3api: ApiSession) -> None:
    result = await s3api.run(
        [
            "s3",
            "mv",
            "s3://mybucket/mykey",
            str(s3api.cwd),
            "--request-payer",
        ],
        replies=[HEAD, GET, DELETED],
    )
    assert result.operations_with_params == [
        head_object_request(
            "mybucket",
            "mykey",
            ChecksumMode="ENABLED",
            RequestPayer="requester",
        ),
        # botocore asks for the response checksum after upstream's
        # capture.
        get_object_request(
            "mybucket",
            "mykey",
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        ),
        delete_object_request("mybucket", "mykey", RequestPayer="requester"),
    ], result.describe()
    assert (s3api.cwd / "mykey").read_bytes() == BODY


async def test_mv_copy_with_request_payer(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 mv s3://sourcebucket/sourcekey s3://mybucket/mykey"
        " --request-payer",
        replies=[head_object_response(), {}, DELETED],
    )
    assert result.operations_with_params == [
        head_object_request(
            "sourcebucket",
            "sourcekey",
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        ),
        copy_object_request(
            "sourcebucket",
            "sourcekey",
            "mybucket",
            "mykey",
            RequestPayer="requester",
        ),
        delete_object_request(
            "sourcebucket", "sourcekey", RequestPayer="requester"
        ),
    ], result.describe()


# A tag set too large for a copy's header, so the copy puts it after.
LARGE_TAG_SET: Final = {"tag-key": "val" * 3000}
METADATA: Final = {"tag-key": "tag-value"}
PUT_TAGGING, PUT_TAGGING_PARAMS = put_object_tagging_request(
    "bucket", "key", LARGE_TAG_SET
)
COPY_PROPS_REQUESTS: Final = [
    head_object_request("sourcebucket", "sourcekey", ChecksumMode="ENABLED"),
    get_object_tagging_request("sourcebucket", "sourcekey"),
    create_mpu_request("bucket", "key", Metadata=METADATA),
    upload_part_copy_request(
        "sourcebucket",
        "sourcekey",
        "bucket",
        "key",
        "upload_id",
        CopySourceRange=f"bytes=0-{8 * MIB - 1}",
        PartNumber=1,
        CopySourceIfMatch='"foo-1"',
    ),
    complete_mpu_request("bucket", "key", "upload_id", 1),
    # botocore adds its default request checksum after upstream's capture.
    (PUT_TAGGING, {**PUT_TAGGING_PARAMS, "ChecksumAlgorithm": "CRC64NVME"}),
]


def copy_props_replies(put_tagging: Reply) -> list[Any]:
    return [
        head_object_response(Metadata=METADATA, ContentLength=8 * MIB),
        get_object_tagging_response(LARGE_TAG_SET),
        create_mpu_response("upload_id"),
        upload_part_copy_response(),
        {},
        put_tagging,
        DELETED,
    ]


async def test_mv_copy_props_default_copies_tags_then_deletes_source(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        "s3 mv s3://sourcebucket/sourcekey s3://bucket/key"
        " --copy-props default",
        replies=copy_props_replies(Reply()),
    )
    assert result.operations_with_params == [
        *COPY_PROPS_REQUESTS,
        delete_object_request("sourcebucket", "sourcekey"),
    ], result.describe()


async def test_mv_failed_put_tagging_deletes_the_copy_not_the_source(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        "s3 mv s3://sourcebucket/sourcekey s3://bucket/key"
        " --copy-props default",
        replies=copy_props_replies(
            Reply(access_denied_error_response(), status=403)
        ),
        expected_rc=1,
    )
    assert result.operations_with_params == [
        *COPY_PROPS_REQUESTS,
        delete_object_request("bucket", "key"),
    ], result.describe()


async def test_mv_upload_with_checksum_algorithm_crc32(
    s3api: ApiSession,
) -> None:
    source = write_file(s3api.cwd, "foo.txt", b"contents")
    result = await s3api.run(
        [
            "s3",
            "mv",
            str(source),
            "s3://bucket/key.txt",
            "--checksum-algorithm",
            "CRC32",
        ],
    )
    assert result.operations == ["PutObject"], result.describe()
    params = result.calls[0].params
    assert (params["ChecksumAlgorithm"], params["ChecksumCRC32"]) == (
        "CRC32",
        crc32(b"contents"),
    ), result.describe()


async def test_mv_download_with_checksum_mode_crc32(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        [
            "s3",
            "mv",
            "s3://bucket/foo",
            str(s3api.cwd),
            "--checksum-mode",
            "ENABLED",
        ],
        replies=[
            HEAD,
            # Upstream's fixture names a placeholder; botocore checks the
            # checksum of the body on the wire.
            {"ETag": "foo-1", "ChecksumCRC32": crc32(BODY), "Body": BODY},
            DELETED,
        ],
    )
    assert result.operations[1] == "GetObject", result.describe()
    assert (
        result.calls[1].params["ChecksumMode"] == "ENABLED"
    ), result.describe()


@pytest.mark.parametrize(
    (
        "content",
        "destination",
        "replies",
        "operations",
        "conditional",
        "moved",
    ),
    [
        pytest.param(
            b"contents",
            "s3://bucket",
            None,
            ["PutObject"],
            0,
            True,
            id="absent",
        ),
        pytest.param(
            b"mycontent",
            "s3://bucket/foo.txt",
            [PRECONDITION_FAILED],
            ["PutObject"],
            0,
            False,
            id="present",
        ),
        pytest.param(
            b"a" * 10 * MIB,
            "s3://bucket",
            [
                {"UploadId": "foo"},
                {"ETag": '"foo-1"'},
                {"ETag": '"foo-2"'},
                {},
            ],
            [
                "CreateMultipartUpload",
                "UploadPart",
                "UploadPart",
                "CompleteMultipartUpload",
            ],
            3,
            True,
            id="multipart-absent",
        ),
        pytest.param(
            b"a" * 10 * MIB,
            "s3://bucket",
            [
                {"UploadId": "foo"},
                {"ETag": '"foo-1"'},
                {"ETag": '"foo-2"'},
                PRECONDITION_FAILED,
                {},
            ],
            [
                "CreateMultipartUpload",
                "UploadPart",
                "UploadPart",
                "CompleteMultipartUpload",
                "AbortMultipartUpload",
            ],
            3,
            False,
            id="multipart-present",
        ),
    ],
)
async def test_mv_no_overwrite_upload(
    transfer_api: ApiSession,
    content: bytes,
    destination: str,
    replies: list[Any] | None,
    operations: list[str],
    conditional: int,
    moved: bool,
) -> None:
    source = write_file(transfer_api.cwd, "foo.txt", content)
    result = await transfer_api.run(
        ["s3", "mv", str(source), destination, "--no-overwrite"],
        replies=replies,
    )
    assert result.operations == operations, result.describe()
    assert (
        result.calls[conditional].params["IfNoneMatch"] == "*"
    ), result.describe()
    assert source.exists() == (not moved)


LARGE_COPY_OPERATIONS: Final = [
    "HeadObject",
    "GetObjectTagging",
    "CreateMultipartUpload",
    "UploadPartCopy",
    "UploadPartCopy",
    "CompleteMultipartUpload",
]


def large_copy_replies(complete: Reply | dict[str, Any]) -> list[Any]:
    return [
        head_object_response(ContentLength=10 * MIB),
        get_object_tagging_response({}),
        create_mpu_response("foo"),
        upload_part_copy_response(),
        upload_part_copy_response(),
        complete,
    ]


@pytest.mark.parametrize(
    ("args", "replies", "operations", "conditional"),
    [
        pytest.param(
            "s3://bucket1/key.txt s3://bucket2/key1.txt",
            [head_object_response(), {}, DELETED],
            ["HeadObject", "CopyObject", "DeleteObject"],
            1,
            id="small-absent",
        ),
        pytest.param(
            "s3://bucket1/key.txt s3://bucket2/key.txt",
            [head_object_response(), PRECONDITION_FAILED],
            ["HeadObject", "CopyObject"],
            1,
            id="small-present",
        ),
        pytest.param(
            "s3://bucket1/key1.txt s3://bucket/key.txt",
            [*large_copy_replies({}), DELETED],
            [*LARGE_COPY_OPERATIONS, "DeleteObject"],
            5,
            id="large-absent",
        ),
        pytest.param(
            "s3://bucket1/key1.txt s3://bucket/key1.txt",
            [*large_copy_replies(PRECONDITION_FAILED), {}],
            [*LARGE_COPY_OPERATIONS, "AbortMultipartUpload"],
            5,
            id="large-present",
        ),
    ],
)
async def test_mv_no_overwrite_copy(
    s3api: ApiSession,
    args: str,
    replies: list[Any],
    operations: list[str],
    conditional: int,
) -> None:
    result = await s3api.run(f"s3 mv {args} --no-overwrite", replies=replies)
    assert result.operations == operations, result.describe()
    assert (
        result.calls[conditional].params["IfNoneMatch"] == "*"
    ), result.describe()


async def test_mv_no_overwrite_download_of_absent_file(
    s3api: ApiSession,
) -> None:
    target = s3api.cwd / "foo.txt"
    result = await s3api.run(
        ["s3", "mv", "s3://bucket/foo.txt", str(target), "--no-overwrite"],
        replies=[HEAD, GET, DELETED],
    )
    assert result.operations == [
        "HeadObject",
        "GetObject",
        "DeleteObject",
    ], result.describe()
    assert target.read_bytes() == BODY


async def test_mv_no_overwrite_download_keeps_existing_file(
    transfer_api: ApiSession,
) -> None:
    target = write_file(transfer_api.cwd, "foo.txt", b"existing content")
    result = await transfer_api.run(
        ["s3", "mv", "s3://bucket/foo.txt", str(target), "--no-overwrite"],
        replies=[head_object_response()],
    )
    assert result.operations == ["HeadObject"], result.describe()
    assert target.read_bytes() == b"existing content"


async def test_mv_upload_on_crt_client_puts_the_file(
    s3crt: ApiSession,
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = CRT_REGION
    source = write_file(s3crt.cwd, "myfile", b"mycontent")
    result = await s3crt.run(["s3", "mv", str(source), "s3://bucket/key"])
    assert wire_requests(result.calls) == [
        ("PUT", CRT_HOST, "/key", True)
    ], result.describe()
    assert result.calls[0].params["Body"] == b"mycontent", result.describe()
    assert not source.exists()


async def test_mv_download_on_crt_client_gets_the_key(
    s3crt: ApiSession,
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = CRT_REGION
    target = s3crt.cwd / "myfile"
    content = b"content"
    head = head_object_response(ContentLength=len(content))
    result = await s3crt.run(
        ["s3", "mv", "s3://bucket/key", str(target)],
        replies=[head, get_object_response(content), DELETED],
    )
    # botocore sends the HeadObject that sizes the move and the delete;
    # the HEAD reports no full-object checksum, so the CRT client sends
    # only its GET.
    assert wire_requests(result.calls) == [
        ("HEAD", CRT_HOST, "/key", False),
        ("GET", CRT_HOST, "/key", True),
        ("DELETE", CRT_HOST, "/key", False),
    ], result.describe()
    assert target.read_bytes() == content


async def test_mv_copy_on_crt_client_runs_the_classic_client(
    s3crt: ApiSession,
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = CRT_REGION
    result = await s3crt.run(
        ["s3", "mv", "s3://bucket/key", "s3://otherbucket/"],
        replies=[
            head_object_response(),
            {"CopyObjectResult": {"ETag": '"foo-1"'}},
            DELETED,
        ],
    )
    assert result.operations == [
        "HeadObject",
        "CopyObject",
        "DeleteObject",
    ], result.describe()
    assert not any(map(sent_by_crt, result.calls)), result.describe()


ACCESS_POINT_ARN: Final = (
    "arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint"
)
OUTPOST_ACCESS_POINT_ARN: Final = (
    "arn:aws:s3-outposts:us-east-1:123456789012:outpost/"
    "op-foobar/accesspoint/myaccesspoint"
)
MRAP_ARN: Final = "arn:aws:s3::123456789012:accesspoint/foobar.mrap"
ACCESS_POINT_ALIAS: Final = "myaccesspoint-foobar-s3alias"
OUTPOST_ALIAS: Final = "myaccesspoint-foobar--op-s3"
VALIDATE: Final = "--validate-same-s3-paths"
CALLER: Final = {"Account": "123456789012"}
SAME_BUCKET: Final = {"Bucket": "bucket"}
DIFFERENT_BUCKET: Final = {"Bucket": "differentbucket"}
MOVE_REPLIES: Final = [head_object_response(), {}, DELETED]
MOVE_OPERATIONS: Final = ["HeadObject", "CopyObject", "DeleteObject"]


def mrap_listing(alias: str, buckets: list[str]) -> dict[str, Any]:
    return {
        "AccessPoints": [
            {
                "Alias": alias,
                "Regions": [{"Bucket": bucket} for bucket in buckets],
            }
        ]
    }


@pytest.mark.parametrize(
    ("args", "env", "replies"),
    [
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ARN}/key {VALIDATE}",
            {},
            [SAME_BUCKET],
            id="access-point-arn",
        ),
        pytest.param(
            f"s3://{ACCESS_POINT_ARN}/key s3://bucket/key {VALIDATE}",
            {},
            [SAME_BUCKET],
            id="access-point-arn-as-source",
        ),
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ARN}/key",
            {"AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS": "true"},
            [SAME_BUCKET],
            id="access-point-arn-with-env-var",
        ),
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ARN}/ {VALIDATE}",
            {},
            [SAME_BUCKET],
            id="access-point-arn-base-key",
        ),
        pytest.param(
            f"s3://bucket/prefix/key s3://{ACCESS_POINT_ARN}/prefix/"
            f" {VALIDATE}",
            {},
            [SAME_BUCKET],
            id="access-point-arn-base-prefix",
        ),
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ALIAS}/key {VALIDATE}",
            {},
            [CALLER, SAME_BUCKET],
            id="access-point-alias",
        ),
        pytest.param(
            f"s3://bucket/key s3://{OUTPOST_ACCESS_POINT_ARN}/key {VALIDATE}",
            {},
            [SAME_BUCKET],
            id="outpost-access-point-arn",
        ),
        pytest.param(
            f"s3://bucket/key s3://{MRAP_ARN}/key {VALIDATE}",
            {},
            [mrap_listing("foobar.mrap", ["differentbucket", "bucket"])],
            id="mrap-arn",
        ),
    ],
)
async def test_mv_validation_refuses_paths_resolving_to_the_source(
    s3api: ApiSession,
    args: str,
    env: dict[str, str],
    replies: list[Any],
) -> None:
    s3api.env.update(env)
    result = await s3api.run(
        f"s3 mv {args}", replies=replies, expected_rc=252
    )
    assert "Cannot mv a file onto itself" in result.stderr, result.describe()


async def test_mv_validation_cannot_resolve_outpost_alias(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        f"s3 mv s3://bucket/key s3://{OUTPOST_ALIAS}/key {VALIDATE}",
        expected_rc=252,
    )
    assert (
        "Can't resolve underlying bucket name" in result.stderr
    ), result.describe()


async def test_mv_validation_fails_without_mrap_alias(
    s3api: ApiSession,
) -> None:
    result = await s3api.run(
        f"s3 mv s3://bucket/key s3://{MRAP_ARN}/key {VALIDATE}",
        replies=[mrap_listing("baz.mrap", ["differentbucket", "bucket"])],
        expected_rc=252,
    )
    assert result.stderr == (
        "\naws: [ERROR]: An error occurred (ParamValidation): "
        "Couldn't find multi-region access point with alias foobar.mrap "
        "in account 123456789012\n"
    ), result.describe()


@pytest.mark.parametrize(
    ("args", "resolution", "lookups"),
    [
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ARN}/key",
            [DIFFERENT_BUCKET],
            ["GetAccessPoint"],
            id="access-point-arn",
        ),
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ALIAS}/key",
            [CALLER, DIFFERENT_BUCKET],
            ["GetCallerIdentity", "GetAccessPoint"],
            id="access-point-alias",
        ),
        pytest.param(
            f"s3://bucket/key s3://{OUTPOST_ACCESS_POINT_ARN}/key",
            [DIFFERENT_BUCKET],
            ["GetAccessPoint"],
            id="outpost-access-point-arn",
        ),
        pytest.param(
            f"s3://bucket/key s3://{MRAP_ARN}/key",
            [mrap_listing("foobar.mrap", ["differentbucket"])],
            ["ListMultiRegionAccessPoints"],
            id="mrap-arn",
        ),
    ],
)
async def test_mv_validation_moves_to_a_different_bucket(
    s3api: ApiSession,
    args: str,
    resolution: list[Any],
    lookups: list[str],
) -> None:
    result = await s3api.run(
        f"s3 mv {args} {VALIDATE}", replies=[*resolution, *MOVE_REPLIES]
    )
    assert (
        result.operations == [*lookups, *MOVE_OPERATIONS]
    ), result.describe()


@pytest.mark.parametrize(
    "destination",
    [
        pytest.param(f"{ACCESS_POINT_ARN}/key2", id="access-point-arn-key"),
        pytest.param(
            f"{ACCESS_POINT_ARN}/prefix/", id="access-point-arn-prefix"
        ),
        pytest.param(f"{ACCESS_POINT_ALIAS}/key2", id="access-point-alias"),
        pytest.param(
            f"{OUTPOST_ACCESS_POINT_ARN}/key2", id="outpost-access-point-arn"
        ),
        pytest.param(f"{OUTPOST_ALIAS}/key2", id="outpost-alias"),
        pytest.param(f"{MRAP_ARN}/key2", id="mrap-arn"),
    ],
)
async def test_mv_validation_skipped_when_keys_differ(
    s3api: ApiSession, destination: str
) -> None:
    result = await s3api.run(
        f"s3 mv s3://bucket/key s3://{destination} {VALIDATE}",
        replies=MOVE_REPLIES,
    )
    assert result.operations == MOVE_OPERATIONS, result.describe()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(
            f"s3://bucket/key s3://{ACCESS_POINT_ARN}/key", id="destination"
        ),
        pytest.param(
            f"s3://{ACCESS_POINT_ARN}/key s3://bucket/key", id="source"
        ),
    ],
)
async def test_mv_warns_without_validation(
    s3api: ApiSession, args: str
) -> None:
    result = await s3api.run(f"s3 mv {args}", replies=MOVE_REPLIES)
    assert (
        "warning: Provided s3 paths may resolve" in result.stderr
    ), result.describe()


LOWER_KEY: Final = "a.txt"
UPPER_KEY: Final = "A.txt"
# Upstream's listing says 100 bytes for each key; the GetObject fixture
# serves 3.
LISTING_ONE: Final = list_objects_response([UPPER_KEY], Size=len(BODY))
LISTING_BOTH: Final = list_objects_response(
    [UPPER_KEY, LOWER_KEY], Size=len(BODY)
)


@pytest.mark.parametrize(
    ("command", "existing", "mode", "replies", "rc", "message"),
    [
        pytest.param(
            "mv --recursive",
            True,
            "error",
            [LISTING_ONE],
            1,
            f"Failed to download bucket/{UPPER_KEY}",
            marks=needs_case_insensitive_filesystem,
            id="mv-error-existing-file",
        ),
        pytest.param(
            "mv --recursive",
            False,
            "error",
            # The first key's move may start before the conflict.
            [LISTING_BOTH, GET, DELETED],
            1,
            f"Failed to download bucket/{LOWER_KEY}",
            id="mv-error-conflict-in-s3",
        ),
        pytest.param(
            "mv --recursive",
            True,
            "warn",
            [LISTING_ONE, GET, DELETED],
            0,
            f"warning: Downloading bucket/{UPPER_KEY}",
            marks=needs_case_insensitive_filesystem,
            id="mv-warn-existing-file",
        ),
        pytest.param(
            "mv --recursive",
            True,
            "skip",
            [LISTING_ONE],
            0,
            f"warning: Skipping bucket/{UPPER_KEY}",
            marks=needs_case_insensitive_filesystem,
            id="mv-skip-existing-file",
        ),
        pytest.param(
            "mv --recursive",
            False,
            "skip",
            [LISTING_BOTH, GET, DELETED],
            0,
            f"warning: Skipping bucket/{LOWER_KEY}",
            id="mv-skip-conflict-in-s3",
        ),
        pytest.param(
            "mv --recursive",
            True,
            "ignore",
            [LISTING_ONE, GET, DELETED],
            0,
            None,
            id="mv-ignore-existing-file",
        ),
    ],
)
async def test_download_case_conflict(
    s3api: ApiSession,
    command: str,
    existing: bool,
    mode: str,
    replies: list[Any],
    rc: int,
    message: str | None,
) -> None:
    if existing:
        write_file(s3api.cwd, LOWER_KEY, b"mycontent")
    result = await s3api.run(
        [
            "s3",
            *command.split(),
            "s3://bucket",
            str(s3api.cwd),
            "--case-conflict",
            mode,
        ],
        replies=replies,
        expected_rc=rc,
    )
    if message is not None:
        assert message in result.stderr, result.describe()


@pytest.mark.parametrize("mode", ["error", "skip"])
async def test_mv_recursive_express_bucket_refuses_case_conflict_mode(
    s3api: ApiSession, mode: str
) -> None:
    result = await s3api.run(
        [
            *"s3 mv --recursive s3://bucket--usw2-az1--x-s3".split(),
            str(s3api.cwd),
            "--case-conflict",
            mode,
        ],
        expected_rc=252,
    )
    assert f"`{mode}` is not a valid value" in result.stderr, result.describe()
