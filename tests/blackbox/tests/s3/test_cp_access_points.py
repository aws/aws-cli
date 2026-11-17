"""`s3 cp` with access point and Multi-Region Access Point ARNs (upstream
tests/functional/s3/test_cp_command.py, TestAccesspointCPCommand).

Upstream compares the ARN given as each request's Bucket. On the wire the
ARN is the request's host, so these tests compare the host each request
went to and the parameters it carried, Bucket aside; a copy's source
carries the ARN itself. Uploads and downloads run on both clients; native
takes no ARN operand, so on either route the CRT client's are upstream's.
"""

from typing import Any, Final

import pytest

from apihelpers import ApiSession, CommandRun
from s3params import (
    Request,
    copy_object_request,
    get_object_request,
    get_object_response,
    head_object_request,
    head_object_response,
    list_objects_request,
    list_objects_response,
    put_object_request,
)

pytestmark = pytest.mark.asyncio

ACCESS_POINT: Final = "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
ACCESS_POINT_HOST: Final = (
    "endpoint-123456789012.s3-accesspoint.us-west-2.amazonaws.com"
)
DEST_ACCESS_POINT: Final = f"{ACCESS_POINT}-dest"
DEST_ACCESS_POINT_HOST: Final = (
    "endpoint-dest-123456789012.s3-accesspoint.us-west-2.amazonaws.com"
)
MRAP_HOST: Final = "mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com"
CONTENT: Final = b"mycontent"
# The CRC64NVME checksum of CONTENT, base64-encoded.
CONTENT_CRC64NVME: Final = "ysNHqmfTPZ0="

type HostRequest = tuple[str, str, dict[str, Any]]


def sent(run: CommandRun) -> list[HostRequest]:
    """Each request's operation, host, and parameters but Bucket, which
    the host names."""
    return [
        (
            call.operation,
            call.request.headers.get("host", ""),
            {k: v for k, v in call.params.items() if k != "Bucket"},
        )
        for call in run.calls
    ]


def at(host: str, request: Request) -> HostRequest:
    operation, params = request
    return (
        operation,
        host,
        {k: v for k, v in params.items() if k != "Bucket"},
    )


def on_crt(api: ApiSession) -> bool:
    return "preferred_transfer_client = crt" in api.config_path.read_text()


def upload_request(api: ApiSession, key: str) -> Request:
    operation, params = put_object_request(
        "", key, Body=CONTENT, ChecksumCRC64NVME=CONTENT_CRC64NVME
    )
    if on_crt(api):
        # The CRT client sends the length and names the checksum only in
        # its trailer.
        del params["ChecksumAlgorithm"]
        params["ContentLength"] = len(CONTENT)
    return operation, params


def download_requests(api: ApiSession) -> list[Request]:
    """A download's requests after its listing or HEAD; botocore enables
    the classic GET's checksum mode after upstream's capture."""
    if not on_crt(api):
        return [get_object_request("", "mykey", ChecksumMode="ENABLED")]
    # The listing or HEAD reported no full-object checksum, so the CRT
    # client sends no HEAD of its own: it asks for its first 8 MiB part,
    # conditioned on the ETag the listing or HEAD found.
    return [
        get_object_request(
            "",
            "mykey",
            ChecksumMode="enabled",
            IfMatch='"foo-1"',
            Range="bytes=0-8388607",
        ),
    ]


async def test_upload(transfer_api: ApiSession) -> None:
    (transfer_api.cwd / "myfile").write_bytes(CONTENT)
    run = await transfer_api.run(f"s3 cp myfile s3://{ACCESS_POINT}/mykey")
    assert sent(run) == [
        at(ACCESS_POINT_HOST, upload_request(transfer_api, "mykey"))
    ], run.describe()


async def test_recursive_upload(transfer_api: ApiSession) -> None:
    (transfer_api.cwd / "dir").mkdir()
    (transfer_api.cwd / "dir" / "myfile").write_bytes(CONTENT)
    run = await transfer_api.run(
        f"s3 cp dir s3://{ACCESS_POINT}/ --recursive"
    )
    assert sent(run) == [
        at(ACCESS_POINT_HOST, upload_request(transfer_api, "myfile"))
    ], run.describe()


async def test_download(transfer_api: ApiSession) -> None:
    # The HEAD's ContentLength is the 3-byte body served.
    head = head_object_response(ContentLength=3)
    run = await transfer_api.run(
        f"s3 cp s3://{ACCESS_POINT}/mykey .",
        replies=[head, get_object_response()],
    )
    assert sent(run) == [
        at(
            ACCESS_POINT_HOST,
            head_object_request("", "mykey", ChecksumMode="ENABLED"),
        ),
        *[
            at(ACCESS_POINT_HOST, request)
            for request in download_requests(transfer_api)
        ],
    ], run.describe()
    assert (transfer_api.cwd / "mykey").read_bytes() == b"foo"


async def test_recursive_download(transfer_api: ApiSession) -> None:
    run = await transfer_api.run(
        f"s3 cp s3://{ACCESS_POINT} . --recursive",
        replies=[
            list_objects_response(["mykey"], Size=3),
            get_object_response(),
        ],
    )
    # botocore asks for URL-encoded keys after upstream's capture.
    assert sent(run) == [
        at(ACCESS_POINT_HOST, list_objects_request("", EncodingType="url")),
        *[
            at(ACCESS_POINT_HOST, request)
            for request in download_requests(transfer_api)
        ],
    ], run.describe()
    assert (transfer_api.cwd / "mykey").read_bytes() == b"foo"


async def test_copy(s3api: ApiSession) -> None:
    run = await s3api.run(
        f"s3 cp s3://{ACCESS_POINT}/mykey s3://{DEST_ACCESS_POINT}",
        replies=[head_object_response(), {}],
    )
    assert sent(run) == [
        at(
            ACCESS_POINT_HOST,
            head_object_request("", "mykey", ChecksumMode="ENABLED"),
        ),
        at(
            DEST_ACCESS_POINT_HOST,
            copy_object_request(ACCESS_POINT, "mykey", "", "mykey"),
        ),
    ], run.describe()


async def test_recursive_copy(s3api: ApiSession) -> None:
    run = await s3api.run(
        f"s3 cp s3://{ACCESS_POINT} s3://{DEST_ACCESS_POINT} --recursive",
        replies=[list_objects_response(["mykey"]), {}],
    )
    assert sent(run) == [
        at(ACCESS_POINT_HOST, list_objects_request("", EncodingType="url")),
        at(
            DEST_ACCESS_POINT_HOST,
            copy_object_request(ACCESS_POINT, "mykey", "", "mykey"),
        ),
    ], run.describe()


@pytest.mark.parametrize(
    "mrap",
    [
        pytest.param(
            "arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap",
            id="colon",
        ),
        pytest.param(
            "arn:aws:s3::123456789012:accesspoint/mfzwi23gnjvgw.mrap",
            id="slash",
        ),
    ],
)
async def test_accepts_mrap_arns(
    transfer_api: ApiSession, mrap: str
) -> None:
    (transfer_api.cwd / "myfile").write_bytes(CONTENT)
    run = await transfer_api.run(f"s3 cp myfile s3://{mrap}/mykey")
    assert sent(run) == [
        at(MRAP_HOST, upload_request(transfer_api, "mykey"))
    ], run.describe()
