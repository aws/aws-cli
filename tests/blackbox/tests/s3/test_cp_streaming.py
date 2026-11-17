"""`s3 cp` to and from standard streams (upstream
tests/functional/s3/test_cp_command.py, TestStreamingCPCommand).

`-` as the source uploads stdin and as the destination writes the object
to stdout. The tests run in upstream's base environment, which pins the
classic client; test_cp_crt_client.py streams on the CRT client, whose
requests differ. The error tests drop the base environment's single
attempt: with it botocore says every error exhausted its attempts, which
upstream's run, with the default attempts, does not. Their errors are not
retried, so each is still a single request.
"""

import base64
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

import awscrt.checksums
import pytest
import pytest_asyncio

from apihelpers import ApiSession, Reply, api_session

pytestmark = pytest.mark.asyncio

BODY: Final = b"foo\n"
NO_SUCH_BUCKET: Final = Reply(
    {
        "Error": {
            "Code": "NoSuchBucket",
            "Message": "The specified bucket does not exist",
            "BucketName": "bucket",
        }
    },
    status=404,
)


@pytest_asyncio.fixture
async def stream_api(
    aws_cli: str, tmp_path: Path
) -> AsyncIterator[ApiSession]:
    """Upstream's base environment: the classic client pinned."""
    async with api_session(aws_cli, tmp_path) as session:
        yield session


def crc64nvme(body: bytes) -> str:
    digest = awscrt.checksums.crc64nvme(body).to_bytes(8, byteorder="big")
    return base64.b64encode(digest).decode()


@pytest.mark.parametrize(
    "options",
    [
        pytest.param([], id="unknown-size"),
        pytest.param(["--expected-size", "4"], id="expected-size"),
    ],
)
async def test_streaming_upload(
    stream_api: ApiSession, options: list[str]
) -> None:
    run = await stream_api.run(
        ["s3", "cp", "-", "s3://bucket/streaming.txt", *options],
        replies=[{"ETag": '"c8afdb36c52cf4727836669019e69222"'}],
        stdin=BODY,
    )
    assert run.operations_with_params == [
        (
            "PutObject",
            {
                "Bucket": "bucket",
                "Key": "streaming.txt",
                "ChecksumAlgorithm": "CRC64NVME",
                "ChecksumCRC64NVME": crc64nvme(BODY),
                "Body": BODY,
            },
        )
    ], run.describe()


async def test_streaming_upload_error(stream_api: ApiSession) -> None:
    del stream_api.env["AWS_MAX_ATTEMPTS"]
    run = await stream_api.run(
        "s3 cp - s3://bucket/streaming.txt",
        replies=[NO_SUCH_BUCKET],
        stdin=BODY,
        expected_rc=1,
    )
    assert (
        "An error occurred (NoSuchBucket) when calling the PutObject "
        "operation: The specified bucket does not exist"
    ) in run.stderr, run.describe()
    assert run.operations == ["PutObject"], run.describe()


async def test_streaming_download(stream_api: ApiSession) -> None:
    head = {
        "AcceptRanges": "bytes",
        "LastModified": "Tue, 12 Jul 2016 21:26:07 GMT",
        "ContentLength": 4,
        "ETag": '"d3b07384d113edec49eaa6238ad5ff00"',
        "Metadata": {},
        "ContentType": "binary/octet-stream",
    }
    run = await stream_api.run(
        "s3 cp s3://bucket/streaming.txt -",
        replies=[head, {**head, "Body": BODY}],
    )
    assert run.stdout == BODY.decode(), run.describe()
    assert run.operations == ["HeadObject", "GetObject"], run.describe()


async def test_streaming_download_error(stream_api: ApiSession) -> None:
    del stream_api.env["AWS_MAX_ATTEMPTS"]
    run = await stream_api.run(
        "s3 cp s3://bucket/streaming.txt -",
        replies=[NO_SUCH_BUCKET],
        expected_rc=1,
    )
    # A HEAD response has no body, so its error is named by its status;
    # upstream feeds the parsed NoSuchBucket error to botocore directly.
    assert (
        "An error occurred (404) when calling the HeadObject operation: "
        "Not Found"
    ) in run.stderr, run.describe()
    assert run.operations == ["HeadObject"], run.describe()


async def test_no_overwrite_cannot_be_used_with_streaming_download(
    stream_api: ApiSession,
) -> None:
    run = await stream_api.run(
        "s3 cp s3://bucket/streaming.txt - --no-overwrite", expected_rc=252
    )
    assert (
        "--no-overwrite parameter is not supported for streaming downloads"
    ) in run.stderr, run.describe()
    assert run.calls == (), run.describe()
