"""`s3 cp --request-payer` requests (upstream
tests/functional/s3/test_cp_command.py, TestCpCommandWithRequesterPayer).

Every request of an upload, a download, or a copy names the requester as
the payer. Uploads and downloads run on both clients; the CRT client's
requests differ from the classic client's as its wire does: it sends a
Content-Length and names the checksum only in its trailer, lists each part's
checksum and the object size when it completes an upload, and ranges a
download's GETs by its part size, conditioned on the ETag the command's
HEAD or listing found. That HEAD or listing reports no full-object
checksum, so the CRT client sends no HEAD of its own. Copies run on the
classic client whichever client is preferred.
"""

import base64
from typing import Any, Final

import awscrt.checksums
import pytest
from localstub import HTTPResponse

from apihelpers import ApiSession
from s3params import (
    Request,
    complete_mpu_request,
    copy_object_request,
    create_mpu_request,
    get_object_request,
    get_object_response,
    get_object_tagging_response,
    head_object_request,
    head_object_response,
    list_objects_request,
    list_objects_response,
    mp_copy_responses,
    put_object_tagging_request,
    upload_part_copy_request,
    upload_part_copy_response,
)

pytestmark = pytest.mark.asyncio

MB: Final = 1024**2
MULTIPART_THRESHOLD: Final = 8 * MB
PAYER: Final = {"RequestPayer": "requester"}
CONTENT: Final = b"mycontent"
# The CRT client's download part size is its own unless configured
# (customizations/s3/factory.py:417-436); pinned, its ranges are the
# classic client's.
PINNED_PARTS: Final = "  multipart_chunksize = 8MB\n"


def on_crt(api: ApiSession) -> bool:
    return "preferred_transfer_client = crt" in api.config_path.read_text()


def crc64nvme(body: bytes) -> str:
    digest = awscrt.checksums.crc64nvme(body).to_bytes(8, byteorder="big")
    return base64.b64encode(digest).decode()


def part_response(body: bytes, start: int, size: int) -> HTTPResponse:
    """A ranged GET's 206 as S3 sends it, naming the object's size. The
    CRT client learns the size from its first part; the scripted service's
    own range would name only the part's."""
    end = start + len(body) - 1
    return HTTPResponse.raw(
        body,
        status=206,
        headers={
            "ETag": '"foo-1"',
            "Content-Range": f"bytes {start}-{end}/{size}",
        },
    )


def upload_request(
    api: ApiSession, operation: str, body: bytes, **params: Any
) -> Request:
    """A PutObject or UploadPart of `body` as the wire carries it."""
    wire = {**params, "Body": body, "ChecksumCRC64NVME": crc64nvme(body)}
    if on_crt(api):
        wire["ContentLength"] = len(body)
    else:
        wire["ChecksumAlgorithm"] = "CRC64NVME"
    return operation, wire



async def test_single_upload(transfer_api: ApiSession) -> None:
    (transfer_api.cwd / "myfile").write_bytes(CONTENT)
    run = await transfer_api.run(
        "s3 cp myfile s3://mybucket/mykey --request-payer"
    )
    assert run.operations_with_params == [
        upload_request(
            transfer_api,
            "PutObject",
            CONTENT,
            Bucket="mybucket",
            Key="mykey",
            **PAYER,
        )
    ], run.describe()


async def test_multipart_upload(transfer_api: ApiSession) -> None:
    body = b"a" * 10 * MB
    parts = [body[: 8 * MB], body[8 * MB :]]
    (transfer_api.cwd / "myfile").write_bytes(body)
    run = await transfer_api.run(
        "s3 cp myfile s3://mybucket/mykey --request-payer",
        replies=[
            {"UploadId": "myid"},
            {"ETag": '"myetag"'},
            {"ETag": '"myetag"'},
            {},
        ],
    )
    target = {"Bucket": "mybucket", "Key": "mykey", **PAYER}
    uploads = [
        upload_request(
            transfer_api,
            "UploadPart",
            part,
            **target,
            UploadId="myid",
            PartNumber=number,
        )
        for number, part in enumerate(parts, start=1)
    ]
    if on_crt(transfer_api):
        # The CRT client strips the ETag's quotes.
        complete = {
            **target,
            "UploadId": "myid",
            "MpuObjectSize": len(body),
            "MultipartUpload": {
                "Parts": [
                    {
                        "ETag": "myetag",
                        "PartNumber": number,
                        "ChecksumCRC64NVME": crc64nvme(part),
                    }
                    for number, part in enumerate(parts, start=1)
                ]
            },
        }
    else:
        complete = {
            **target,
            "UploadId": "myid",
            "MultipartUpload": {
                "Parts": [
                    {"ETag": '"myetag"', "PartNumber": 1},
                    {"ETag": '"myetag"', "PartNumber": 2},
                ]
            },
        }
    create = {**target, "ChecksumAlgorithm": "CRC64NVME"}
    assert run.operations_with_params == [
        ("CreateMultipartUpload", create),
        *uploads,
        ("CompleteMultipartUpload", complete),
    ], run.describe()


async def test_recursive_upload(transfer_api: ApiSession) -> None:
    (transfer_api.cwd / "dir").mkdir()
    (transfer_api.cwd / "dir" / "myfile").write_bytes(CONTENT)
    run = await transfer_api.run(
        "s3 cp dir s3://mybucket/ --request-payer --recursive"
    )
    assert run.operations_with_params == [
        upload_request(
            transfer_api,
            "PutObject",
            CONTENT,
            Bucket="mybucket",
            Key="myfile",
            **PAYER,
        )
    ], run.describe()


async def test_single_download(transfer_api: ApiSession) -> None:
    crt = on_crt(transfer_api)
    # The HEAD's ContentLength is the 3-byte body served.
    head = head_object_response(ContentLength=3)
    run = await transfer_api.run(
        "s3 cp s3://mybucket/mykey . --request-payer",
        replies=[head, get_object_response()],
    )
    command_head = head_object_request(
        "mybucket", "mykey", ChecksumMode="ENABLED", **PAYER
    )
    if crt:
        expected = [
            command_head,
            get_object_request(
                "mybucket",
                "mykey",
                ChecksumMode="enabled",
                IfMatch='"foo-1"',
                Range="bytes=0-8388607",
                **PAYER,
            ),
        ]
    else:
        # botocore enables the GET's checksum mode after the point
        # upstream captures its parameters.
        expected = [
            command_head,
            get_object_request(
                "mybucket", "mykey", ChecksumMode="ENABLED", **PAYER
            ),
        ]
    assert run.operations_with_params == expected, run.describe()
    assert (transfer_api.cwd / "mykey").read_bytes() == b"foo"


async def test_ranged_download(transfer_api: ApiSession) -> None:
    crt = on_crt(transfer_api)
    if crt:
        config = transfer_api.config_path.read_text() + PINNED_PARTS
        transfer_api.config_path.write_text(config)
    first, second = b"x" * 8 * MB, b"y" * 2 * MB
    run = await transfer_api.run(
        "s3 cp s3://mybucket/mykey . --request-payer",
        replies=[
            head_object_response(ContentLength=10 * MB),
            part_response(first, 0, 10 * MB),
            part_response(second, 8 * MB, 10 * MB),
        ],
    )
    mode = "enabled" if crt else "ENABLED"
    # The classic client leaves the last range open.
    last = "bytes=8388608-10485759" if crt else "bytes=8388608-"
    assert run.operations_with_params == [
        head_object_request(
            "mybucket", "mykey", ChecksumMode="ENABLED", **PAYER
        ),
        *[
            get_object_request(
                "mybucket",
                "mykey",
                ChecksumMode=mode,
                IfMatch='"foo-1"',
                Range=byte_range,
                **PAYER,
            )
            for byte_range in ("bytes=0-8388607", last)
        ],
    ], run.describe()
    assert (transfer_api.cwd / "mykey").read_bytes() == first + second


async def test_recursive_download(transfer_api: ApiSession) -> None:
    crt = on_crt(transfer_api)
    # The listed Size is the 3-byte body served.
    run = await transfer_api.run(
        "s3 cp s3://mybucket/ . --request-payer --recursive",
        replies=[
            list_objects_response(["mykey"], Size=3),
            get_object_response(),
        ],
    )
    # botocore asks for URL-encoded keys after upstream's capture.
    listing = list_objects_request("mybucket", EncodingType="url", **PAYER)
    if crt:
        expected = [
            listing,
            get_object_request(
                "mybucket",
                "mykey",
                ChecksumMode="enabled",
                IfMatch='"foo-1"',
                Range="bytes=0-8388607",
                **PAYER,
            ),
        ]
    else:
        expected = [
            listing,
            get_object_request(
                "mybucket", "mykey", ChecksumMode="ENABLED", **PAYER
            ),
        ]
    assert run.operations_with_params == expected, run.describe()
    assert (transfer_api.cwd / "mykey").read_bytes() == b"foo"


async def test_single_copy(s3api: ApiSession) -> None:
    run = await s3api.run(
        "s3 cp s3://sourcebucket/sourcekey s3://mybucket/mykey "
        "--request-payer",
        replies=[head_object_response(), {}],
    )
    assert run.operations_with_params == [
        head_object_request(
            "sourcebucket", "sourcekey", ChecksumMode="ENABLED", **PAYER
        ),
        copy_object_request(
            "sourcebucket", "sourcekey", "mybucket", "mykey", **PAYER
        ),
    ], run.describe()


async def test_multipart_copy(s3api: ApiSession) -> None:
    upload_id = "id"
    run = await s3api.run(
        "s3 cp s3://sourcebucket/sourcekey s3://mybucket/mykey "
        "--copy-props none --request-payer",
        replies=[
            head_object_response(ContentLength=10 * MB),
            {"UploadId": upload_id},
            upload_part_copy_response(),
            upload_part_copy_response(),
            {},
        ],
    )
    assert run.operations_with_params == [
        head_object_request(
            "sourcebucket", "sourcekey", ChecksumMode="ENABLED", **PAYER
        ),
        create_mpu_request("mybucket", "mykey", **PAYER),
        *[
            upload_part_copy_request(
                "sourcebucket",
                "sourcekey",
                "mybucket",
                "mykey",
                upload_id,
                PartNumber=number,
                CopySourceRange=byte_range,
                CopySourceIfMatch='"foo-1"',
                **PAYER,
            )
            for number, byte_range in (
                (1, "bytes=0-8388607"),
                (2, "bytes=8388608-10485759"),
            )
        ],
        complete_mpu_request(
            "mybucket", "mykey", upload_id, num_parts=2, **PAYER
        ),
    ], run.describe()


async def test_recursive_copy(s3api: ApiSession) -> None:
    run = await s3api.run(
        "s3 cp s3://sourcebucket/ s3://mybucket/ --request-payer --recursive",
        replies=[list_objects_response(["mykey"]), {}],
    )
    assert run.operations_with_params == [
        list_objects_request("sourcebucket", EncodingType="url", **PAYER),
        copy_object_request(
            "sourcebucket", "mykey", "mybucket", "mykey", **PAYER
        ),
    ], run.describe()


@pytest.mark.parametrize(
    "tags",
    [
        pytest.param({}, id="no-tags"),
        # Tags over 2 KiB do not fit the CreateMultipartUpload header, so
        # they are put on the new object afterwards.
        pytest.param({"tag-key": "value" * (2 * 1024)}, id="tags-exceed-2k"),
    ],
)
async def test_mp_copy_object(s3api: ApiSession, tags: dict[str, str]) -> None:
    run = await s3api.run(
        "s3 cp s3://sourcebucket/mykey s3://mybucket/mykey --request-payer",
        replies=[
            head_object_response(ContentLength=MULTIPART_THRESHOLD),
            get_object_tagging_response(tags),
            *mp_copy_responses(),
            *([{}] if tags else []),
        ],
    )
    operation, tagging = put_object_tagging_request("mybucket", "mykey", tags)
    # botocore names the checksum PutObjectTagging requires after
    # upstream's capture.
    tagging.update(ChecksumAlgorithm="CRC64NVME", **PAYER)
    assert run.operations_with_params == [
        head_object_request(
            "sourcebucket", "mykey", ChecksumMode="ENABLED", **PAYER
        ),
        (
            "GetObjectTagging",
            {"Bucket": "sourcebucket", "Key": "mykey", **PAYER},
        ),
        create_mpu_request("mybucket", "mykey", **PAYER),
        upload_part_copy_request(
            "sourcebucket",
            "mykey",
            "mybucket",
            "mykey",
            "upload_id",
            PartNumber=1,
            CopySourceRange="bytes=0-8388607",
            CopySourceIfMatch='"foo-1"',
            **PAYER,
        ),
        complete_mpu_request(
            "mybucket", "mykey", "upload_id", num_parts=1, **PAYER
        ),
        *([(operation, tagging)] if tags else []),
    ], run.describe()
