"""`s3 cp`'s requests for single uploads, downloads, and copies (upstream
tests/functional/s3/test_cp_command.py, TestCPCommand).

Each test runs one command against scripted S3 replies and asserts its
exit status, the output upstream checks, every request it sends, and for
a download the file it writes or leaves alone. Uploads and downloads run
on both transfer clients (`transfer_api`): the classic client upstream
pins, and the CRT client, which native runs by default and upstream's CRT
client runs on the Python route. Copies between buckets, and the other
commands native hands to Python whichever client is preferred, run on the
classic client alone.
"""

import base64
import errno
import hashlib
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest
from awscrt.checksums import XXHash, crc32, crc32c, crc64nvme

from apihelpers import (
    CRT_TRANSFER_CONFIG,
    ApiSession,
    Reply,
    ReplyLike,
    argv,
)
from s3params import (
    Params,
    Request,
    copy_object_request,
    create_mpu_request,
    get_object_request,
    get_object_tagging_request,
    get_object_tagging_response,
    head_object_request,
    head_object_response,
    list_objects_request,
    precondition_failed_error_response,
    upload_part_copy_request,
)

pytestmark = pytest.mark.asyncio

MB: Final = 1024**2
# The part size of every multipart transfer here, on either client.
PART_SIZE: Final = 8 * MB
BODY: Final = b"mycontent"
LARGE_BODY: Final = b"a" * 10 * MB
PUT_OBJECT_REPLY: Final = {"ETag": '"c8afdb36c52cf4727836669019e69222"'}
# A 256-bit SSE-C key that is not UTF-8, as upstream's fileb:// tests use.
SSE_C_KEY: Final = (
    b"K\xc9G\xe1\xf9&\xee\xd1\x03\xf3\xd4\x10\x18o9E\xc2\xaeD"
    b"\x89(\x18\xea\xda\xf6\x81\xc3\xd2\x9d\\\xa8\xe6"
)
PRECONDITION_FAILED: Final = Reply(
    precondition_failed_error_response(), status=412
)


def on_crt(session: ApiSession) -> bool:
    """Whether `session`'s config prefers the CRT transfer client."""
    return session.config_path.read_text() == CRT_TRANSFER_CONFIG


def checksum(algorithm: str, body: bytes) -> str:
    """`body`'s checksum in `algorithm`, base64-encoded as S3 sends it."""
    match algorithm:
        case "CRC32":
            digest = crc32(body).to_bytes(4, "big")
        case "CRC32C":
            digest = crc32c(body).to_bytes(4, "big")
        case "CRC64NVME":
            digest = crc64nvme(body).to_bytes(8, "big")
        case "SHA1" | "SHA256" | "SHA512":
            digest = hashlib.new(algorithm.lower(), body).digest()
        case "XXHASH3":
            digest = XXHash.compute_xxhash3_64(body)
        case "XXHASH64":
            digest = XXHash.compute_xxhash64(body)
        case "XXHASH128":
            digest = XXHash.compute_xxhash3_128(body)
        case _:
            raise ValueError(f"no checksum algorithm {algorithm}")
    return base64.b64encode(digest).decode()


def sent_body(
    session: ApiSession, body: bytes, algorithm: str = "CRC64NVME"
) -> Params:
    """The parameters a request that carries `body` sends with it: the
    body and its checksum, with the checksum's algorithm from the classic
    client and the body's length from the CRT client."""
    params: Params = {
        "Body": body,
        f"Checksum{algorithm}": checksum(algorithm, body),
    }
    if on_crt(session):
        params["ContentLength"] = len(body)
    else:
        params["ChecksumAlgorithm"] = algorithm
    return params


def write_file(session: ApiSession, name: str, body: bytes) -> Path:
    path = session.cwd / name
    path.write_bytes(body)
    return path


def shown(session: ApiSession, path: Path) -> str:
    """`path` as a result line shows it, relative to the working
    directory (upstream's `relative_path`)."""
    return os.path.join(os.path.relpath(path.parent, session.cwd), path.name)


def put_object(key: str, params: Params, bucket: str = "bucket") -> Request:
    return "PutObject", {"Bucket": bucket, "Key": key, **params}


@dataclass(frozen=True)
class Upload:
    """A single upload of `BODY` from foo.txt: the destination and
    options, the key it names, and the PutObject parameters the options
    add."""

    destination: str = "s3://bucket/key.txt"
    args: tuple[str, ...] = ()
    key: str = "key.txt"
    params: Params = field(default_factory=dict)
    algorithm: str = "CRC64NVME"


def checksum_upload(algorithm: str) -> Any:
    return pytest.param(
        Upload(args=("--checksum-algorithm", algorithm), algorithm=algorithm),
        id=f"checksum-algorithm-{algorithm.lower()}",
    )


def storage_class_upload(storage_class: str) -> Any:
    return pytest.param(
        Upload(
            args=("--storage-class", storage_class),
            params={"StorageClass": storage_class},
        ),
        id=f"storage-class-{storage_class.lower().replace('_', '-')}",
    )


UPLOADS: Final = [
    pytest.param(Upload(), id="operations-used"),
    pytest.param(
        Upload(destination="s3://bucket/", key="foo.txt"),
        id="key-name-added-when-only-bucket-provided",
    ),
    pytest.param(
        Upload(destination="s3://bucket", key="foo.txt"),
        id="trailing-slash-appended",
    ),
    pytest.param(
        Upload(
            args=(
                "--grants",
                "read=id=foo",
                "full=id=bar",
                "readacl=id=biz",
                "writeacl=id=baz",
            ),
            params={
                "GrantRead": "id=foo",
                "GrantFullControl": "id=bar",
                "GrantReadACP": "id=biz",
                "GrantWriteACP": "id=baz",
            },
        ),
        id="grants",
    ),
    storage_class_upload("STANDARD_IA"),
    storage_class_upload("ONEZONE_IA"),
    storage_class_upload("INTELLIGENT_TIERING"),
    storage_class_upload("GLACIER"),
    storage_class_upload("DEEP_ARCHIVE"),
    pytest.param(
        Upload(
            args=("--website-redirect", "http://someserver"),
            params={"WebsiteRedirectLocation": "http://someserver"},
        ),
        id="website-redirect-ignore-paramfile",
    ),
    pytest.param(
        Upload(
            destination="s3://bucket/key2.txt",
            args=("--metadata", "KeyName=Value"),
            key="key2.txt",
            params={"Metadata": {"KeyName": "Value"}},
        ),
        id="metadata",
    ),
    pytest.param(
        Upload(args=("--sse",), params={"ServerSideEncryption": "AES256"}),
        id="sse",
    ),
    pytest.param(
        Upload(
            args=("--sse-c", "--sse-c-key", "foo"),
            params={
                "SSECustomerAlgorithm": "AES256",
                "SSECustomerKey": "foo",
            },
        ),
        id="sse-c",
    ),
    pytest.param(
        Upload(
            args=("--sse", "aws:kms", "--sse-kms-key-id", "foo"),
            params={
                "SSEKMSKeyId": "foo",
                "ServerSideEncryption": "aws:kms",
            },
        ),
        id="sse-kms-and-key-id",
    ),
    *(
        checksum_upload(algorithm)
        for algorithm in (
            "CRC32",
            "SHA1",
            "SHA256",
            "SHA512",
            "CRC32C",
            "CRC64NVME",
            "XXHASH3",
            "XXHASH64",
            "XXHASH128",
        )
    ),
]


async def assert_one_put_object(session: ApiSession, upload: Upload) -> None:
    source = write_file(session, "foo.txt", BODY)
    result = await session.run(
        ["s3", "cp", str(source), upload.destination, *upload.args],
        replies=[PUT_OBJECT_REPLY],
    )
    params = {
        "ContentType": "text/plain",
        **upload.params,
        **sent_body(session, BODY, upload.algorithm),
    }
    assert result.operations_with_params == [
        put_object(upload.key, params)
    ], result.describe()


@pytest.mark.parametrize("upload", UPLOADS)
async def test_upload_sends_one_put_object(
    transfer_api: ApiSession, upload: Upload
) -> None:
    await assert_one_put_object(transfer_api, upload)


@pytest.mark.parametrize(
    "upload",
    [
        # botocore sends `--expires 90` as the Expires timestamp 90 seconds
        # after the epoch.
        pytest.param(
            Upload(
                args=("--expires", "90"),
                params={"Expires": datetime(1970, 1, 1, 0, 1, 30, tzinfo=UTC)},
            ),
            id="expires",
        ),
        pytest.param(
            Upload(
                destination="s3://bucket",
                args=("--metadata-directive", "REPLACE"),
                key="foo.txt",
            ),
            id="no-metadata-directive-for-non-copy",
        ),
    ],
)
async def test_classic_upload_sends_one_put_object(
    s3api: ApiSession, upload: Upload
) -> None:
    # Native reads neither an epoch time for --expires nor
    # --metadata-directive, so only the classic client runs these.
    await assert_one_put_object(s3api, upload)


async def test_upload_with_sse_c_key_from_fileb(
    transfer_api: ApiSession,
) -> None:
    source = write_file(transfer_api, "foo.txt", BODY)
    key_path = write_file(transfer_api, "foo.key", SSE_C_KEY)
    result = await transfer_api.run(
        argv(
            "s3 cp {source} s3://bucket/key.txt --sse-c "
            "--sse-c-key fileb://{key_path}",
            source=source,
            key_path=key_path,
        ),
        replies=[PUT_OBJECT_REPLY],
    )
    params = {
        "ContentType": "text/plain",
        "SSECustomerAlgorithm": "AES256",
        "SSECustomerKey": SSE_C_KEY,
        **sent_body(transfer_api, BODY),
    }
    assert result.operations_with_params == [
        put_object("key.txt", params)
    ], result.describe()


async def test_dryrun_upload(transfer_api: ApiSession) -> None:
    source = write_file(transfer_api, "foo.txt", BODY)
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket/key.txt --dryrun", source=source),
        replies=[],
    )
    assert result.calls == (), result.describe()
    assert (
        f"(dryrun) upload: {shown(transfer_api, source)} to "
        "s3://bucket/key.txt" in result.stdout
    ), result.describe()


async def test_error_on_same_line_as_status(transfer_api: ApiSession) -> None:
    source = write_file(transfer_api, "foo.txt", BODY)
    error = {
        "Error": {
            "Code": "BucketNotExists",
            "Message": "Bucket does not exist",
        }
    }
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket-not-exist/key.txt", source=source),
        replies=[error],
        expected_rc=1,
    )
    params = {"ContentType": "text/plain", **sent_body(transfer_api, BODY)}
    assert result.operations_with_params == [
        put_object("key.txt", params, bucket="bucket-not-exist")
    ], result.describe()
    assert (
        f"upload failed: {shown(transfer_api, source)} to "
        "s3://bucket-not-exist/key.txt An error" in result.stderr
    ), result.describe()


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(PUT_OBJECT_REPLY, id="object-not-exists-on-target"),
        # The skipped upload is the command's success.
        pytest.param(PRECONDITION_FAILED, id="object-exists-on-target"),
    ],
)
async def test_no_overwrite_upload_puts_if_none_match(
    transfer_api: ApiSession, reply: ReplyLike
) -> None:
    source = write_file(transfer_api, "foo.txt", BODY)
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket --no-overwrite", source=source),
        replies=[reply],
    )
    params = {
        "ContentType": "text/plain",
        "IfNoneMatch": "*",
        **sent_body(transfer_api, BODY),
    }
    assert result.operations_with_params == [
        put_object("foo.txt", params)
    ], result.describe()


def large_parts() -> list[bytes]:
    return [
        LARGE_BODY[start : start + PART_SIZE]
        for start in range(0, len(LARGE_BODY), PART_SIZE)
    ]


def multipart_upload(
    session: ApiSession,
    key: str,
    etags: Sequence[str],
    *,
    algorithm: str = "CRC64NVME",
    reply_checksums: bool = False,
    create: Params | None = None,
    complete: Params | None = None,
) -> list[Request]:
    """The requests `session`'s client sends to upload `LARGE_BODY` to
    s3://bucket/`key` when S3 answers its parts with `etags`, and with
    their checksums if `reply_checksums`.

    The classic client completes the upload with each part's ETag, and
    the checksum S3 returned for it if it did. The CRT client sends the
    ETag without its quotes, the checksum it computed, and the object's
    size.
    """
    crt = on_crt(session)
    requests: list[Request] = [
        create_mpu_request(
            "bucket",
            key,
            ChecksumAlgorithm=algorithm,
            ContentType="text/plain",
            **(create or {}),
        )
    ]
    completed: list[Params] = []
    for number, (part, etag) in enumerate(
        zip(large_parts(), etags, strict=True), start=1
    ):
        requests.append(
            (
                "UploadPart",
                {
                    "Bucket": "bucket",
                    "Key": key,
                    "PartNumber": number,
                    "UploadId": "foo",
                    **sent_body(session, part, algorithm),
                },
            )
        )
        entry: Params = {
            "ETag": etag.strip('"') if crt else etag,
            "PartNumber": number,
        }
        if crt or reply_checksums:
            entry[f"Checksum{algorithm}"] = checksum(algorithm, part)
        completed.append(entry)
    finished: Params = {
        "Bucket": "bucket",
        "Key": key,
        "UploadId": "foo",
        "MultipartUpload": {"Parts": completed},
        **(complete or {}),
    }
    if crt:
        finished["MpuObjectSize"] = len(LARGE_BODY)
    requests.append(("CompleteMultipartUpload", finished))
    return requests


def multipart_replies(
    etags: Sequence[str], algorithm: str | None = None
) -> list[ReplyLike]:
    """S3's answers to `multipart_upload`'s requests, with each part's
    checksum in `algorithm` if it is given."""
    replies: list[ReplyLike] = [{"UploadId": "foo"}]
    for part, etag in zip(large_parts(), etags, strict=True):
        reply: Params = {"ETag": etag}
        if algorithm is not None:
            reply[f"Checksum{algorithm}"] = checksum(algorithm, part)
        replies.append(reply)
    replies.append({})
    return replies


async def test_no_overwrite_multipart_upload_when_object_not_exists(
    transfer_api: ApiSession,
) -> None:
    source = write_file(transfer_api, "foo.txt", LARGE_BODY)
    etags = ['"foo-1"', '"foo-2"']
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket --no-overwrite", source=source),
        replies=multipart_replies(etags),
    )
    assert result.operations_with_params == multipart_upload(
        transfer_api, "foo.txt", etags, complete={"IfNoneMatch": "*"}
    ), result.describe()


async def test_no_overwrite_multipart_upload_when_object_exists(
    transfer_api: ApiSession,
) -> None:
    source = write_file(transfer_api, "foo.txt", LARGE_BODY)
    etags = ['"foo-1"', '"foo-2"']
    replies = [*multipart_replies(etags)[:-1], PRECONDITION_FAILED, {}]
    # The skipped upload is the command's success.
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket --no-overwrite", source=source),
        replies=replies,
    )
    abort = {"Bucket": "bucket", "Key": "foo.txt", "UploadId": "foo"}
    assert result.operations_with_params == [
        *multipart_upload(
            transfer_api, "foo.txt", etags, complete={"IfNoneMatch": "*"}
        ),
        ("AbortMultipartUpload", abort),
    ], result.describe()


async def test_metadata_with_multipart_upload(
    transfer_api: ApiSession,
) -> None:
    source = write_file(transfer_api, "foo.txt", LARGE_BODY)
    etags = ['"foo-1"', '"foo-2"']
    result = await transfer_api.run(
        argv(
            "s3 cp {source} s3://bucket/key2.txt --metadata KeyName=Value",
            source=source,
        ),
        replies=multipart_replies(etags),
    )
    assert result.operations_with_params == multipart_upload(
        transfer_api,
        "key2.txt",
        etags,
        create={"Metadata": {"KeyName": "Value"}},
    ), result.describe()


async def test_multipart_upload_with_checksum_algorithm_crc32(
    transfer_api: ApiSession,
) -> None:
    source = write_file(transfer_api, "foo.txt", LARGE_BODY)
    etags = ["foo-e1", "foo-e2"]
    # Upstream's parts answer with placeholder checksums; S3 answers with
    # each part's own.
    result = await transfer_api.run(
        argv(
            "s3 cp {source} s3://bucket/key2.txt --checksum-algorithm CRC32",
            source=source,
        ),
        replies=multipart_replies(etags, "CRC32"),
    )
    assert result.operations_with_params == multipart_upload(
        transfer_api,
        "key2.txt",
        etags,
        algorithm="CRC32",
        reply_checksums=True,
    ), result.describe()


async def test_upload_large_file_with_sse_kms_and_key_id(
    s3api: ApiSession,
) -> None:
    # Native does not take --copy-props, so only the classic client runs
    # this.
    source = write_file(s3api, "foo.txt", LARGE_BODY)
    etags = ['"foo"', '"foo"']
    result = await s3api.run(
        argv(
            "s3 cp {source} s3://bucket/key.txt --copy-props none "
            "--sse aws:kms --sse-kms-key-id foo",
            source=source,
        ),
        replies=multipart_replies(etags),
    )
    assert result.operations_with_params == multipart_upload(
        s3api,
        "key.txt",
        etags,
        create={"SSEKMSKeyId": "foo", "ServerSideEncryption": "aws:kms"},
    ), result.describe()


def download(session: ApiSession, key: str) -> list[Request]:
    """The requests `session`'s client sends to download the 3 bytes of
    s3://bucket/`key` after the command's HEAD or listing: one GetObject
    from the classic client, and from the CRT client a GetObject of its
    first part, conditioned on the ETag the HEAD or listing found. Those
    report no full-object checksum, so the CRT client sends no HEAD of its
    own."""
    if not on_crt(session):
        return [get_object_request("bucket", key, ChecksumMode="ENABLED")]
    return [
        get_object_request(
            "bucket",
            key,
            ChecksumMode="enabled",
            IfMatch='"foo-1"',
            Range="bytes=0-8388607",
        ),
    ]


@dataclass(frozen=True)
class Download:
    """A single download of s3://bucket/`key` to `target`, relative to the
    working directory, and the checksum the GetObject answer carries."""

    key: str
    target: str
    args: tuple[str, ...] = ()
    checksums: Params = field(default_factory=dict)


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            Download("key.txt", "."), id="operations-used-in-download-file"
        ),
        pytest.param(
            Download("foo.txt", "foo.txt", ("--no-overwrite",)),
            id="no-overwrite-when-single-object-does-not-exist-at-target",
        ),
        # Upstream's GetObject answers give a placeholder checksum, which
        # the CLI checks on the wire, and an ETag the HeadObject did not;
        # S3 sends the body's own checksum and the object's one ETag.
        pytest.param(
            Download(
                "foo",
                ".",
                ("--checksum-mode", "ENABLED"),
                {"ChecksumCRC32": checksum("CRC32", b"foo")},
            ),
            id="checksum-mode-crc32",
        ),
        pytest.param(
            Download(
                "foo",
                ".",
                ("--checksum-mode", "ENABLED"),
                {"ChecksumCRC32C": checksum("CRC32C", b"foo")},
            ),
            id="checksum-mode-crc32c",
        ),
    ],
)
async def test_download_sends_head_object_then_get_object(
    transfer_api: ApiSession, case: Download
) -> None:
    # Upstream's HeadObject says 100 bytes for the 3 its GetObject serves.
    head = head_object_response(ContentLength=3)
    get = {"ETag": '"foo-1"', "Body": b"foo", **case.checksums}
    target = transfer_api.cwd / case.target
    result = await transfer_api.run(
        ["s3", "cp", f"s3://bucket/{case.key}", str(target), *case.args],
        replies=[head, get],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", case.key, ChecksumMode="ENABLED"),
        *download(transfer_api, case.key),
    ], result.describe()
    written = target / case.key if target.is_dir() else target
    assert written.read_bytes() == b"foo"


async def test_no_overwrite_download_when_object_exists_at_target(
    transfer_api: ApiSession,
) -> None:
    target = write_file(transfer_api, "foo.txt", b"existing content")
    result = await transfer_api.run(
        argv(
            "s3 cp s3://bucket/foo.txt {target} --no-overwrite", target=target
        ),
        replies=[head_object_response()],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "foo.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert target.read_bytes() == b"existing content"


async def test_dryrun_download(transfer_api: ApiSession) -> None:
    target = transfer_api.cwd / "file.txt"
    result = await transfer_api.run(
        argv("s3 cp s3://bucket/key.txt {target} --dryrun", target=target),
        replies=[head_object_response()],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert (
        "(dryrun) download: s3://bucket/key.txt to "
        f"{shown(transfer_api, target)}" in result.stdout
    ), result.describe()
    assert not target.exists()


async def test_operations_used_in_recursive_download(
    transfer_api: ApiSession,
) -> None:
    # Upstream's listing also has an ETag, which ListObjectsV2's answer
    # has no member for.
    result = await transfer_api.run(
        argv(
            "s3 cp s3://bucket/key.txt {cwd} --recursive",
            cwd=transfer_api.cwd,
        ),
        replies=[{"Contents": [], "CommonPrefixes": []}],
    )
    assert result.operations_with_params == [
        list_objects_request(
            "bucket", Prefix="key.txt/", EncodingType="url"
        )
    ], result.describe()


def glacier_listing(**override: Any) -> Params:
    """A listing of foo/bar.txt in GLACIER. Upstream's entry also has a
    ContentLength, which a listing has no member for, and says 100 bytes
    for the 3 its GetObject serves."""
    content: Params = {
        "Key": "foo/bar.txt",
        "LastModified": "00:00:00Z",
        "StorageClass": "GLACIER",
        "Size": 3,
    }
    content.update(override)
    return {"Contents": [content], "CommonPrefixes": []}


async def test_recursive_glacier_download_with_force_glacier(
    transfer_api: ApiSession,
) -> None:
    get = {"ETag": '"foo-1"', "Body": b"foo"}
    result = await transfer_api.run(
        argv(
            "s3 cp s3://bucket/foo {cwd} --recursive --force-glacier-transfer",
            cwd=transfer_api.cwd,
        ),
        replies=[
            glacier_listing(ETag='"foo-1"'),
            get,
        ],
    )
    listing = list_objects_request(
        "bucket", Prefix="foo/", EncodingType="url"
    )
    assert result.operations_with_params == [
        listing,
        *download(transfer_api, "foo/bar.txt"),
    ], result.describe()
    assert (transfer_api.cwd / "bar.txt").read_bytes() == b"foo"


async def test_recursive_glacier_download_without_force_glacier(
    transfer_api: ApiSession,
) -> None:
    result = await transfer_api.run(
        argv(
            "s3 cp s3://bucket/foo {cwd} --recursive", cwd=transfer_api.cwd
        ),
        replies=[glacier_listing()],
        expected_rc=2,
    )
    assert result.operations_with_params == [
        list_objects_request("bucket", Prefix="foo/", EncodingType="url")
    ], result.describe()
    assert "GLACIER" in result.stderr, result.describe()
    assert list(transfer_api.cwd.iterdir()) == []


def glacier_head(storage_class: str, size: int) -> Params:
    return {
        "ContentLength": size,
        "LastModified": "00:00:00Z",
        "StorageClass": storage_class,
    }


@pytest.mark.parametrize(
    ("storage_class", "size"),
    [
        pytest.param("GLACIER", 100, id="glacier"),
        pytest.param("DEEP_ARCHIVE", 100, id="deep-archive"),
        pytest.param("GLACIER", 20 * MB, id="glacier-multipart-file"),
        pytest.param(
            "DEEP_ARCHIVE", 20 * MB, id="deep-archive-multipart-file"
        ),
    ],
)
async def test_warns_on_glacier_incompatible_download(
    transfer_api: ApiSession, storage_class: str, size: int
) -> None:
    result = await transfer_api.run(
        "s3 cp s3://bucket/key.txt .",
        replies=[glacier_head(storage_class, size)],
        expected_rc=2,
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert "GLACIER" in result.stderr, result.describe()
    assert list(transfer_api.cwd.iterdir()) == []


@pytest.mark.parametrize(
    "storage_class",
    [
        pytest.param("GLACIER", id="glacier"),
        pytest.param("DEEP_ARCHIVE", id="deep-archive"),
    ],
)
async def test_turn_off_glacier_warnings(
    transfer_api: ApiSession, storage_class: str
) -> None:
    result = await transfer_api.run(
        "s3 cp s3://bucket/key.txt . --ignore-glacier-warnings",
        replies=[glacier_head(storage_class, 20 * MB)],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert result.stderr == "", result.describe()
    assert list(transfer_api.cwd.iterdir()) == []


# A file the test's user may write but does not own, so the user may not
# set its times.
UNOWNED_FILE: Final = Path("/dev/null")


def setting_times_denial(path: Path) -> PermissionError | None:
    """The error that denies the test's user setting `path`'s times, None
    if the user may set them. The probe sets them to what they are."""
    try:
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except PermissionError as error:
        return error
    except OSError:
        return None
    return None


async def test_cp_fails_with_utime_errors_but_continues(
    s3api: ApiSession,
) -> None:
    # Upstream patches os.utime to fail; here the CLI downloads to a file
    # another user owns, as its warning supposes.
    denial = setting_times_denial(UNOWNED_FILE)
    if denial is None:
        pytest.skip(
            f"the test's user is not denied setting {UNOWNED_FILE}'s times"
        )
    result = await s3api.run(
        f"s3 cp s3://bucket/key.txt {UNOWNED_FILE}",
        replies=[
            head_object_response(ContentLength=3),
            {"ETag": '"foo-1"', "Body": b"foo"},
        ],
        expected_rc=2,
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED"),
        get_object_request("bucket", "key.txt", ChecksumMode="ENABLED"),
    ], result.describe()
    # Upstream explains EPERM, which Linux gives, and passes any other
    # error through as it is: macOS gives EACCES for /dev/null.
    reason = (
        "attempting to modify the utime"
        if denial.errno == errno.EPERM
        else str(denial)
    )
    assert reason in result.stderr, result.describe()


async def test_crt_download_to_dev_null_fails_creating_its_temporary_file(
    s3crt: ApiSession,
) -> None:
    # The CRT client downloads to a temporary file beside its target, and
    # cannot create one beside /dev/null, so it never reaches the utime
    # the classic client fails.
    directory = UNOWNED_FILE.parent
    if not directory.is_dir() or os.access(directory, os.W_OK):
        pytest.skip(f"the test's user may create files in {directory}")
    result = await s3crt.run(
        f"s3 cp s3://bucket/key.txt {UNOWNED_FILE}",
        replies=[head_object_response(ContentLength=3)],
        expected_rc=1,
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert (
        f"download failed: s3://bucket/key.txt to "
        f"{shown(s3crt, UNOWNED_FILE)} 43 (AWS_ERROR_NO_PERMISSION): User "
        "does not have permission to perform the requested action."
        in result.stderr
    ), result.describe()


SECOND: Final = 1_000_000_000
DAY: Final = 86400 * SECOND
EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


def since_epoch(moment: datetime) -> int:
    """`moment` in nanoseconds since the epoch."""
    return int((moment - EPOCH).total_seconds()) * SECOND


# An mtime upstream's datetime cannot hold: one in 1960 on Windows, and
# elsewhere one past year 9999 in every local offset.
INVALID_MTIME: Final = (
    since_epoch(datetime(1960, 1, 1, tzinfo=UTC))
    if sys.platform == "win32"
    else since_epoch(datetime(9999, 12, 31, tzinfo=UTC)) + 2 * DAY
)


def holds_mtime(directory: Path, mtime: int) -> bool:
    """Whether a file in `directory` keeps `mtime`, in nanoseconds."""
    probe = directory / "probe"
    probe.write_bytes(b"")
    try:
        os.utime(probe, ns=(mtime, mtime))
        return probe.stat().st_mtime_ns == mtime
    except (OSError, OverflowError):
        return False
    finally:
        probe.unlink()


@pytest.fixture
def invalid_mtime_dir(tmp_path: Path) -> Iterator[Path]:
    """A directory on a filesystem that holds `INVALID_MTIME`: the
    test's own, or Linux's tmpfs."""
    roots = [tmp_path]
    if sys.platform == "linux":
        roots.append(Path("/dev/shm"))
    for root in roots:
        if not root.is_dir():
            continue
        directory = Path(tempfile.mkdtemp(dir=root))
        try:
            if holds_mtime(directory, INVALID_MTIME):
                yield directory
                return
        finally:
            shutil.rmtree(directory)
    pytest.skip("no filesystem here holds an mtime upstream cannot read")


async def test_cp_with_error_and_warning_permissions(
    transfer_api: ApiSession, invalid_mtime_dir: Path
) -> None:
    # Upstream patches the file generator to read an invalid timestamp;
    # here the file has one.
    transfer_api.cwd = invalid_mtime_dir
    source = write_file(transfer_api, "foo.txt", b"bar")
    os.utime(source, ns=(INVALID_MTIME, INVALID_MTIME))
    error = {
        "Error": {
            "Code": "NoSuchBucket",
            "Message": "The specified bucket does not exist",
            "BucketName": "bucket",
        }
    }
    result = await transfer_api.run(
        argv("s3 cp {source} s3://bucket/foo.txt", source=source),
        replies=[Reply(error, status=404)],
        expected_rc=1,
    )
    params = {"ContentType": "text/plain", **sent_body(transfer_api, b"bar")}
    assert result.operations_with_params == [
        put_object("foo.txt", params)
    ], result.describe()
    assert "upload failed" in result.stderr, result.describe()
    assert "warning: File has an invalid timestamp." in result.stderr, (
        result.describe()
    )


async def test_cannot_use_recursive_with_stream(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 cp - s3://bucket/key.txt --recursive", expected_rc=252
    )
    assert result.calls == (), result.describe()
    assert (
        "Streaming currently is only compatible with non-recursive cp "
        "commands" in result.stderr
    ), result.describe()


@dataclass(frozen=True)
class Copy:
    """A single copy between buckets: its operands and options, the
    HeadObject and CopyObject parameters they add, and S3's answers."""

    source: tuple[str, str]
    destination: tuple[str, str]
    args: tuple[str, ...] = ()
    head: Params = field(default_factory=dict)
    copy: Params = field(default_factory=dict)
    head_reply: Params = field(default_factory=head_object_response)
    copy_reply: ReplyLike = field(default_factory=dict)
    annotations: bool = True


SINGLE_COPIES: Final = [
    # Upstream's CopyObject answers give their ETag outside the
    # CopyObjectResult it belongs to.
    pytest.param(
        Copy(
            ("bucket", "key.txt"),
            ("bucket", "key2.txt"),
            ("--metadata", "KeyName=Value"),
            copy={
                "Metadata": {"KeyName": "Value"},
                "MetadataDirective": "REPLACE",
            },
            head_reply=head_object_response(ETag='"foo"'),
            copy_reply={"CopyObjectResult": {"ETag": '"foo-1"'}},
        ),
        id="metadata-copy",
    ),
    pytest.param(
        Copy(
            ("bucket", "key.txt"),
            ("bucket", "key2.txt"),
            ("--metadata-directive", "REPLACE"),
            copy={"MetadataDirective": "REPLACE"},
            head_reply=head_object_response(ETag='"foo"'),
            copy_reply={"CopyObjectResult": {"ETag": '"foo-1"'}},
            # A metadata directive turns off the copy's properties,
            # annotations among them.
            annotations=False,
        ),
        id="metadata-directive-copy",
    ),
    pytest.param(
        Copy(
            ("bucket1", "key.txt"),
            ("bucket", "key.txt"),
            ("--no-overwrite",),
            copy={"IfNoneMatch": "*"},
            head_reply=head_object_response(ContentLength=5),
        ),
        id="no-overwrite-when-small-object-does-not-exist-on-target",
    ),
    pytest.param(
        Copy(
            ("bucket1", "key.txt"),
            ("bucket", "key.txt"),
            ("--no-overwrite",),
            copy={"IfNoneMatch": "*"},
            head_reply=head_object_response(ContentLength=5),
            copy_reply=PRECONDITION_FAILED,
        ),
        id="no-overwrite-when-small-object-exists-on-target",
    ),
    pytest.param(
        Copy(
            ("bucket-one", "key.txt"),
            ("bucket", "key.txt"),
            ("--sse-c", "--sse-c-key", "destination-key"),
            copy={
                "SSECustomerAlgorithm": "AES256",
                "SSECustomerKey": "destination-key",
            },
        ),
        id="s3s3-with-destination-sse-c",
    ),
    pytest.param(
        Copy(
            ("bucket-one", "key.txt"),
            ("bucket", "key.txt"),
            (
                "--sse-c-copy-source",
                "--sse-c-copy-source-key",
                "foo",
                "--sse-c",
                "--sse-c-key",
                "bar",
            ),
            head={"SSECustomerAlgorithm": "AES256", "SSECustomerKey": "foo"},
            copy={
                "SSECustomerAlgorithm": "AES256",
                "SSECustomerKey": "bar",
                "CopySourceSSECustomerAlgorithm": "AES256",
                "CopySourceSSECustomerKey": "foo",
            },
        ),
        id="s3s3-with-different-sse-c-keys",
    ),
    pytest.param(
        Copy(
            ("bucket", "key1.txt"),
            ("bucket", "key2.txt"),
            ("--sse", "aws:kms", "--sse-kms-key-id", "foo"),
            copy={"SSEKMSKeyId": "foo", "ServerSideEncryption": "aws:kms"},
            head_reply=head_object_response(ContentLength=5, ETag='"foo"'),
        ),
        id="sse-kms-and-key-id",
    ),
    pytest.param(
        Copy(
            ("bucket1", "key.txt"),
            ("bucket2", "key.txt"),
            ("--checksum-algorithm", "CRC32"),
            copy={"ChecksumAlgorithm": "CRC32"},
            copy_reply={
                "CopyObjectResult": {
                    "ETag": "foo-1",
                    "ChecksumCRC32": "Tq0H4g==",
                }
            },
        ),
        id="checksum-algorithm-crc32",
    ),
]


@pytest.mark.parametrize("case", SINGLE_COPIES)
async def test_copy_sends_head_object_then_copy_object(
    s3api: ApiSession, case: Copy
) -> None:
    source = "/".join(case.source)
    destination = "/".join(case.destination)
    result = await s3api.run(
        ["s3", "cp", f"s3://{source}", f"s3://{destination}", *case.args],
        replies=[case.head_reply, case.copy_reply],
    )
    operation, copy = copy_object_request(
        *case.source, *case.destination, **case.copy
    )
    if not case.annotations:
        del copy["AnnotationDirective"]
    assert result.operations_with_params == [
        head_object_request(*case.source, ChecksumMode="ENABLED", **case.head),
        (operation, copy),
    ], result.describe()


async def test_copy_with_sse_c_copy_source_key_from_fileb(
    s3api: ApiSession,
) -> None:
    key_path = write_file(s3api, "foo.key", SSE_C_KEY)
    head = {
        "AcceptRanges": "bytes",
        "LastModified": "Tue, 12 Jul 2016 21:26:07 GMT",
        "ContentLength": 4,
        "ETag": '"d3b07384d113edec49eaa6238ad5ff00"',
        "Metadata": {},
        "ContentType": "binary/octet-stream",
    }
    # Upstream's second answer is a GetObject's, which the copy never
    # sends; its third is the CopyObject's.
    result = await s3api.run(
        argv(
            "s3 cp s3://bucket-one/key.txt s3://bucket/key.txt "
            "--sse-c-copy-source --sse-c-copy-source-key fileb://{key_path}",
            key_path=key_path,
        ),
        replies=[head, {}],
    )
    assert result.operations_with_params == [
        head_object_request(
            "bucket-one",
            "key.txt",
            ChecksumMode="ENABLED",
            SSECustomerAlgorithm="AES256",
            SSECustomerKey=SSE_C_KEY,
        ),
        copy_object_request(
            "bucket-one",
            "key.txt",
            "bucket",
            "key.txt",
            CopySourceSSECustomerAlgorithm="AES256",
            CopySourceSSECustomerKey=SSE_C_KEY,
        ),
    ], result.describe()


async def test_dryrun_copy(s3api: ApiSession) -> None:
    result = await s3api.run(
        "s3 cp s3://bucket/key.txt s3://bucket/key2.txt --dryrun",
        replies=[head_object_response()],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "key.txt", ChecksumMode="ENABLED")
    ], result.describe()
    assert (
        "(dryrun) copy: s3://bucket/key.txt to s3://bucket/key2.txt"
        in result.stdout
    ), result.describe()


async def test_upload_unicode_path(s3api: ApiSession) -> None:
    # Upstream's second answer is the CopyObject's; its ETag belongs in
    # the CopyObjectResult.
    result = await s3api.run(
        "s3 cp s3://bucket/☃ s3://bucket/✓",
        replies=[
            head_object_response(ContentLength=10, ETag='"foo"'),
            {"CopyObjectResult": {"ETag": '"foo"'}},
        ],
    )
    assert result.operations_with_params == [
        head_object_request("bucket", "☃", ChecksumMode="ENABLED"),
        copy_object_request("bucket", "☃", "bucket", "✓"),
    ], result.describe()
    assert "copy: s3://bucket/☃ to s3://bucket/✓" in result.stdout, (
        result.describe()
    )
    assert "Completed 10 Bytes" in result.stdout, result.describe()


@dataclass(frozen=True)
class MultipartCopy:
    """A multipart copy: its options, the size HeadObject gives, the
    parameters the options add to each request, the ETags S3 answers
    with, and whether the copy reads the source's tags and finds its
    destination already there."""

    args: tuple[str, ...]
    size: int
    source: tuple[str, str] = ("bucket-one", "key.txt")
    destination: tuple[str, str] = ("bucket", "key.txt")
    head: Params = field(default_factory=dict)
    create: Params = field(default_factory=dict)
    part: Params = field(default_factory=dict)
    complete: Params = field(default_factory=dict)
    head_etag: str = '"foo-1"'
    part_etag: str = '"etag"'
    tagging: bool = True
    exists: bool = False

    def ranges(self) -> list[tuple[int, int]]:
        return [
            (start, min(start + PART_SIZE, self.size) - 1)
            for start in range(0, self.size, PART_SIZE)
        ]


def multipart_copy(case: MultipartCopy) -> list[Request]:
    """The requests the classic client sends for `case`."""
    requests: list[Request] = [
        head_object_request(*case.source, ChecksumMode="ENABLED", **case.head)
    ]
    if case.tagging:
        requests.append(get_object_tagging_request(*case.source))
    requests.append(create_mpu_request(*case.destination, **case.create))
    for number, (start, end) in enumerate(case.ranges(), start=1):
        requests.append(
            upload_part_copy_request(
                *case.source,
                *case.destination,
                "upload_id",
                PartNumber=number,
                CopySourceRange=f"bytes={start}-{end}",
                CopySourceIfMatch=case.head_etag,
                **case.part,
            )
        )
    bucket, key = case.destination
    parts = [
        {"ETag": case.part_etag, "PartNumber": number}
        for number in range(1, len(case.ranges()) + 1)
    ]
    complete: Params = {
        "Bucket": bucket,
        "Key": key,
        "UploadId": "upload_id",
        "MultipartUpload": {"Parts": parts},
        **case.complete,
    }
    requests.append(("CompleteMultipartUpload", complete))
    if case.exists:
        abort = {"Bucket": bucket, "Key": key, "UploadId": "upload_id"}
        requests.append(("AbortMultipartUpload", abort))
    return requests


def multipart_copy_replies(case: MultipartCopy) -> list[ReplyLike]:
    replies: list[ReplyLike] = [
        head_object_response(ContentLength=case.size, ETag=case.head_etag)
    ]
    if case.tagging:
        replies.append(get_object_tagging_response({}))
    replies.append({"UploadId": "upload_id"})
    replies += [
        {"CopyPartResult": {"ETag": case.part_etag}} for _ in case.ranges()
    ]
    if case.exists:
        replies += [PRECONDITION_FAILED, {}]
    else:
        replies.append({})
    return replies


SSE_C_DESTINATION: Final = {
    "SSECustomerAlgorithm": "AES256",
    "SSECustomerKey": "destination-key",
}
SSE_C_SOURCE: Final = {
    "SSECustomerAlgorithm": "AES256",
    "SSECustomerKey": "source-key",
}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            MultipartCopy(
                ("--no-overwrite",),
                10 * MB,
                source=("bucket1", "key.txt"),
                complete={"IfNoneMatch": "*"},
                exists=True,
            ),
            id="no-overwrite-when-large-object-exists-on-target",
        ),
        pytest.param(
            MultipartCopy(
                ("--no-overwrite",),
                10 * MB,
                source=("bucket1", "key.txt"),
                destination=("bucket", "key1.txt"),
                complete={"IfNoneMatch": "*"},
            ),
            id="no-overwrite-when-large-object-does-not-exist-on-target",
        ),
        # The source's 8 MiB, the multipart threshold, is one part.
        pytest.param(
            MultipartCopy(
                ("--sse-c", "--sse-c-key", "destination-key"),
                PART_SIZE,
                create=SSE_C_DESTINATION,
                part=SSE_C_DESTINATION,
                complete=SSE_C_DESTINATION,
            ),
            id="s3s3-with-destination-sse-c-multipart",
        ),
        pytest.param(
            MultipartCopy(
                (
                    "--sse-c-copy-source",
                    "--sse-c-copy-source-key",
                    "source-key",
                    "--sse-c",
                    "--sse-c-key",
                    "destination-key",
                ),
                PART_SIZE,
                head=SSE_C_SOURCE,
                create=SSE_C_DESTINATION,
                part={
                    **SSE_C_DESTINATION,
                    "CopySourceSSECustomerAlgorithm": "AES256",
                    "CopySourceSSECustomerKey": "source-key",
                },
                complete=SSE_C_DESTINATION,
            ),
            id="s3s3-with-different-sse-c-keys-multipart",
        ),
        pytest.param(
            MultipartCopy(
                (
                    "--copy-props",
                    "none",
                    "--sse",
                    "aws:kms",
                    "--sse-kms-key-id",
                    "foo",
                ),
                10 * MB,
                source=("bucket", "key1.txt"),
                destination=("bucket", "key2.txt"),
                create={
                    "SSEKMSKeyId": "foo",
                    "ServerSideEncryption": "aws:kms",
                },
                head_etag='"foo"',
                part_etag='"foo"',
                tagging=False,
            ),
            id="copy-large-file-with-sse-kms-and-key-id",
        ),
    ],
)
async def test_multipart_copy(s3api: ApiSession, case: MultipartCopy) -> None:
    source = "/".join(case.source)
    destination = "/".join(case.destination)
    result = await s3api.run(
        ["s3", "cp", f"s3://{source}", f"s3://{destination}", *case.args],
        replies=multipart_copy_replies(case),
    )
    assert result.operations_with_params == multipart_copy(case), (
        result.describe()
    )
