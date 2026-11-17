"""`s3 sync` requests, output, and files (upstream
tests/functional/s3/test_sync_command.py).

Syncs between a local directory and a bucket run on both clients'
environments (`transfer_api`): `[classic]` is upstream's, which every route
hands to Python, and `[crt]` the one native runs by default and the Python
route runs on upstream's CRT client. That client heads each object it
downloads and then fetches it with a ranged, conditional GetObject, and
sends an upload's checksum in a trailer with no algorithm header. Syncs
between buckets, access points, and `--no-follow-symlinks` are Python's on
every route and run on the classic client only (`s3api`).

A listing's Size is the size of the body its object serves, which
upstream's fixtures (Size 100, body b"foo") did not need.
"""

import base64
import hashlib
import os
import shutil
import sys
import tempfile
import zlib
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest
from awscrt import checksums
from localstub import HTTPResponse

from apihelpers import ApiSession, CommandRun, Reply
from s3params import (
    Params,
    Request,
    complete_mpu_request,
    copy_object_request,
    create_mpu_request,
    create_mpu_response,
    delete_object_request,
    get_object_response,
    get_object_tagging_request,
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

ETAG: Final = '"foo-1"'
BODY: Final = b"foo"
MP_THRESHOLD: Final = 8 * 1024 * 1024
DIRECTORY_BUCKET: Final = "testdirectorybucket--usw2-az1--x-s3"
ACCESS_POINT_ARN: Final = (
    "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
)
ACCESS_POINT_HOST: Final = (
    "endpoint-123456789012.s3-accesspoint.us-west-2.amazonaws.com"
)
# Upstream's BaseS3CLIRunnerTest region.
RUNNER_REGION: Final = "us-west-2"
ALGORITHMS: Final = [
    "CRC32",
    "CRC32C",
    "CRC64NVME",
    "SHA1",
    "SHA256",
    "SHA512",
    "XXHASH3",
    "XXHASH64",
    "XXHASH128",
]
CRT_USER_AGENT: Final = "CRTS3NativeClient/"
# An empty page as S3 writes it: IsTruncated keeps the serializer from
# writing upstream's empty page as a self-closing root, which S3 never
# sends.
EMPTY_PAGE: Final = {
    "CommonPrefixes": [],
    "Contents": [],
    "IsTruncated": False,
}


def _probe_case_insensitive() -> bool:
    # awscli.testutils' CASE_INSENSITIVE, probed the same way.
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "aws-cli-tmp-file").write_bytes(b"")
        return (Path(directory) / "AWS-CLI-TMP-FILE").exists()


CASE_INSENSITIVE: Final = _probe_case_insensitive()
requires_case_insensitive: Final = pytest.mark.skipif(
    not CASE_INSENSITIVE,
    reason="This test requires a case-insensitive filesystem.",
)


def uses_crt(api: ApiSession) -> bool:
    """Whether `api` prefers the CRT client, `transfer_api`'s `[crt]`."""
    config = api.config_path.read_text(encoding="utf-8")
    return "preferred_transfer_client = crt" in config


def checksum(algorithm: str, body: bytes) -> str:
    """`body`'s checksum in the base64 form S3's headers carry."""
    match algorithm:
        case "CRC32":
            digest = zlib.crc32(body).to_bytes(4, "big")
        case "CRC32C":
            digest = checksums.crc32c(body).to_bytes(4, "big")
        case "CRC64NVME":
            digest = checksums.crc64nvme(body).to_bytes(8, "big")
        case "SHA1" | "SHA256" | "SHA512":
            digest = hashlib.new(algorithm.lower(), body).digest()
        case "XXHASH3":
            digest = checksums.XXHash.compute_xxhash3_64(body)
        case "XXHASH64":
            digest = checksums.XXHash.compute_xxhash64(body)
        case "XXHASH128":
            digest = checksums.XXHash.compute_xxhash3_128(body)
        case _:
            raise ValueError(f"unknown checksum algorithm {algorithm}")
    return base64.b64encode(digest).decode()


def listing(bucket: str, prefix: str = "", **override: Any) -> Request:
    """The ListObjectsV2 request sync sends for `bucket`/`prefix`."""
    return list_objects_request(
        bucket, Prefix=prefix, EncodingType="url", **override
    )


def put_request(
    api: ApiSession,
    bucket: str,
    key: str,
    body: bytes,
    algorithm: str = "CRC64NVME",
    **override: Any,
) -> Request:
    """The PutObject an upload of `body` sends. botocore names the
    algorithm in a header; the CRT client sends only the trailer, on a
    body of known length."""
    params: Params = {
        "Bucket": bucket,
        "Key": key,
        f"Checksum{algorithm}": checksum(algorithm, body),
        "Body": body,
    }
    if uses_crt(api):
        params["ContentLength"] = len(body)
    else:
        params["ChecksumAlgorithm"] = algorithm
    params.update(override)
    return "PutObject", params


def download_requests(
    api: ApiSession, bucket: str, key: str, etag: str = ETAG
) -> list[Request]:
    """The requests a download of one listed object sends. The listing
    reports no full-object checksum, so the CRT client sends no HEAD of its
    own: it asks for its first 8 MiB part, conditioned on the listed ETag."""
    if not uses_crt(api):
        get = {"Bucket": bucket, "Key": key, "ChecksumMode": "ENABLED"}
        return [("GetObject", get)]
    return [
        (
            "GetObject",
            {
                "Bucket": bucket,
                "Key": key,
                "IfMatch": etag,
                "Range": "bytes=0-8388607",
                "ChecksumMode": "enabled",
            },
        ),
    ]


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Upstream's FileCreator root: a directory apart from the one the
    command runs in."""
    path = tmp_path / "files"
    path.mkdir()
    return path


async def test_website_redirect_ignore_paramfile(
    transfer_api: ApiSession, root: Path
) -> None:
    write(root / "foo.txt", "mycontent")
    run = await transfer_api.run(
        [
            "s3",
            "sync",
            str(root),
            "s3://bucket/key.txt",
            "--website-redirect",
            "http://someserver",
        ],
        replies=[
            EMPTY_PAGE,
            {"ETag": '"c8afdb36c52cf4727836669019e69222"'},
        ],
    )
    # The address is sent as given, not read as a parameter file.
    assert run.operations_with_params == [
        listing("bucket", "key.txt/"),
        put_request(
            transfer_api,
            "bucket",
            "key.txt/foo.txt",
            b"mycontent",
            ContentType="text/plain",
            WebsiteRedirectLocation="http://someserver",
        ),
    ], run.describe()


async def test_no_recursive_option(s3api: ApiSession) -> None:
    # Upstream's command line dropped `s3 sync`, so it tested an unknown
    # command; this is the sync it meant.
    run = await s3api.run(
        "s3 sync . s3://mybucket --recursive", expected_rc=252
    )
    assert "--recursive" in run.stderr, run.describe()
    assert run.calls == (), run.describe()


async def test_sync_from_non_existant_directory(
    transfer_api: ApiSession, root: Path
) -> None:
    run = await transfer_api.run(
        ["s3", "sync", str(root / "fakedir"), "s3://bucket/"],
        expected_rc=255,
    )
    assert "does not exist" in run.stderr, run.describe()
    assert run.calls == (), run.describe()


async def test_sync_to_non_existant_directory(
    transfer_api: ApiSession, root: Path
) -> None:
    etag = '"c8afdb36c52cf4727836669019e69222-"'
    page = {
        "CommonPrefixes": [],
        "Contents": [
            {
                "Key": "foo.txt",
                "Size": 3,
                "LastModified": "2014-01-09T20:45:49.000Z",
                "ETag": etag,
            }
        ],
    }
    destination = root / "fakedir"
    await transfer_api.run(
        ["s3", "sync", "s3://bucket/", str(destination)],
        replies=[
            page,
            {"ETag": etag, "Body": BODY},
        ],
    )
    assert (destination / "foo.txt").read_bytes() == BODY


async def test_dryrun_sync(transfer_api: ApiSession, root: Path) -> None:
    full_path = write(root / "file.txt", "mycontent")
    run = await transfer_api.run(
        ["s3", "sync", str(root), "s3://bucket/", "--dryrun"],
        replies=[EMPTY_PAGE],
    )
    assert run.operations_with_params == [listing("bucket")], run.describe()
    # Upstream's relative_path: relative to the directory the CLI runs in.
    shown = os.path.relpath(full_path, transfer_api.cwd)
    assert (
        f"(dryrun) upload: {shown} to s3://bucket/file.txt" in run.stdout
    ), run.describe()


async def test_glacier_sync_with_force_glacier(
    transfer_api: ApiSession, root: Path
) -> None:
    page = {
        "Contents": [
            {
                "Key": "foo/bar.txt",
                "LastModified": "00:00:00Z",
                "StorageClass": "GLACIER",
                "Size": len(BODY),
                "ETag": ETAG,
            },
        ],
        "CommonPrefixes": [],
    }
    run = await transfer_api.run(
        [
            "s3",
            "sync",
            "s3://bucket/foo",
            str(root),
            "--force-glacier-transfer",
        ],
        replies=[page, get_object_response(BODY)],
    )
    assert run.operations_with_params == [
        listing("bucket", "foo/"),
        *download_requests(transfer_api, "bucket", "foo/bar.txt"),
    ], run.describe()
    assert (root / "bar.txt").read_bytes() == BODY


GLACIER_PAGE: Final = {
    "Contents": [
        {
            "Key": "foo",
            "Size": 100,
            "LastModified": "00:00:00Z",
            "StorageClass": "GLACIER",
        },
        {
            "Key": "bar",
            "Size": 100,
            "LastModified": "00:00:00Z",
            "StorageClass": "DEEP_ARCHIVE",
        },
    ]
}


@pytest.mark.parametrize(
    ("flags", "expected_rc", "warnings"),
    [
        pytest.param(
            [],
            2,
            ["GLACIER", "s3://bucket/foo", "s3://bucket/bar"],
            id="warns",
        ),
        pytest.param(
            ["--ignore-glacier-warnings"],
            0,
            None,
            id="ignore-glacier-warnings",
        ),
    ],
)
async def test_handles_glacier_incompatible_operations(
    transfer_api: ApiSession,
    root: Path,
    flags: list[str],
    expected_rc: int,
    warnings: list[str] | None,
) -> None:
    run = await transfer_api.run(
        ["s3", "sync", "s3://bucket/", str(root), *flags],
        replies=[GLACIER_PAGE],
        expected_rc=expected_rc,
    )
    # Neither object is downloaded: both need a restore first.
    assert run.operations == ["ListObjectsV2"], run.describe()
    if warnings is None:
        assert run.stderr == "", run.describe()
    else:
        for text in warnings:
            assert text in run.stderr, run.describe()


def holds(directory: Path, mtime: int) -> bool:
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


# An mtime the CLI's datetime cannot hold: one before 1970 on Windows, and
# elsewhere one past year 9999 in every zone.
INVALID_MTIME: Final = (
    int(datetime(1960, 1, 1, tzinfo=UTC).timestamp()) * 10**9
    if sys.platform == "win32"
    else (int(datetime(9999, 12, 31, tzinfo=UTC).timestamp()) + 2 * 86400)
    * 10**9
)


@pytest.fixture
def invalid_mtime_root(tmp_path: Path) -> Iterator[Path]:
    """A directory on a filesystem that holds INVALID_MTIME: the test's
    own, or Linux's tmpfs."""
    candidates = [tmp_path]
    if sys.platform == "linux":
        candidates.append(Path("/dev/shm"))
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        parent = Path(tempfile.mkdtemp(dir=candidate))
        try:
            if holds(parent, INVALID_MTIME):
                path = parent / "files"
                path.mkdir()
                yield path
                return
        finally:
            shutil.rmtree(parent)
    pytest.skip("no filesystem here holds an mtime the CLI cannot read")


async def test_warning_on_invalid_timestamp(
    transfer_api: ApiSession, invalid_mtime_root: Path
) -> None:
    # Upstream patched the file generator's stat; a real mtime past what
    # datetime holds takes the same branch.
    path = write(invalid_mtime_root / "foo.txt", "mycontent")
    os.utime(path, ns=(INVALID_MTIME, INVALID_MTIME))
    run = await transfer_api.run(
        ["s3", "sync", str(invalid_mtime_root), "s3://bucket/key.txt"],
        replies=[
            EMPTY_PAGE,
            {"ETag": '"c8afdb36c52cf4727836669019e69222"'},
        ],
        expected_rc=2,
    )
    # The file is still uploaded.
    assert run.operations == ["ListObjectsV2", "PutObject"], run.describe()
    assert "File has an invalid timestamp" in run.stderr, run.describe()


async def test_sync_with_delete_on_downloads(
    transfer_api: ApiSession, root: Path
) -> None:
    full_path = write(root / "foo.txt", "mycontent")
    run = await transfer_api.run(
        ["s3", "sync", "s3://bucket", str(root), "--delete"],
        replies=[EMPTY_PAGE],
    )
    assert run.operations_with_params == [listing("bucket")], run.describe()
    assert not full_path.exists()


async def test_request_payer(s3api: ApiSession) -> None:
    run = await s3api.run(
        "s3 sync s3://sourcebucket/ s3://mybucket --request-payer",
        replies=[
            list_objects_response(["mykey"]),
            EMPTY_PAGE,
            {},
        ],
    )
    assert run.operations_with_params == [
        listing("sourcebucket", RequestPayer="requester"),
        listing("mybucket", RequestPayer="requester"),
        copy_object_request(
            "sourcebucket",
            "mykey",
            "mybucket",
            "mykey",
            RequestPayer="requester",
        ),
    ], run.describe()


async def test_request_payer_with_deletes(s3api: ApiSession) -> None:
    run = await s3api.run(
        "s3 sync s3://sourcebucket/ s3://mybucket --request-payer --delete",
        replies=[
            EMPTY_PAGE,
            list_objects_response(["key-to-delete"]),
            {},
        ],
    )
    assert run.operations_with_params == [
        listing("sourcebucket", RequestPayer="requester"),
        listing("mybucket", RequestPayer="requester"),
        delete_object_request(
            "mybucket", "key-to-delete", RequestPayer="requester"
        ),
    ], run.describe()


DESTINATION_SSE_C: Final = {
    "SSECustomerAlgorithm": "AES256",
    "SSECustomerKey": "destination-key",
}
SOURCE_SSE_C: Final = {
    "CopySourceSSECustomerAlgorithm": "AES256",
    "CopySourceSSECustomerKey": "source-key",
}
SSE_C_CASES: Final = [
    pytest.param([], {}, id="destination-key"),
    pytest.param(
        [
            "--sse-c-copy-source",
            "AES256",
            "--sse-c-copy-source-key",
            "source-key",
        ],
        SOURCE_SSE_C,
        id="different-keys",
    ),
]
SSE_C_FLAGS: Final = ["--sse-c", "AES256", "--sse-c-key", "destination-key"]


@pytest.mark.parametrize(("flags", "source_params"), SSE_C_CASES)
async def test_s3s3_sync_with_sse_c(
    s3api: ApiSession, flags: list[str], source_params: Params
) -> None:
    run = await s3api.run(
        [
            "s3",
            "sync",
            "s3://sourcebucket/",
            "s3://mybucket",
            *flags,
            *SSE_C_FLAGS,
        ],
        replies=[
            list_objects_response(["mykey"]),
            EMPTY_PAGE,
            {},
        ],
    )
    assert run.operations_with_params == [
        listing("sourcebucket"),
        listing("mybucket"),
        copy_object_request(
            "sourcebucket",
            "mykey",
            "mybucket",
            "mykey",
            **DESTINATION_SSE_C,
            **source_params,
        ),
    ], run.describe()


@pytest.mark.parametrize(("flags", "source_params"), SSE_C_CASES)
async def test_s3s3_sync_with_sse_c_multipart(
    s3api: ApiSession, flags: list[str], source_params: Params
) -> None:
    run = await s3api.run(
        [
            "s3",
            "sync",
            "s3://sourcebucket/",
            "s3://mybucket",
            *flags,
            *SSE_C_FLAGS,
        ],
        replies=[
            list_objects_response(["mykey"], Size=MP_THRESHOLD),
            EMPTY_PAGE,
            # The HeadObject of SetMetadataDirectivePropsSubscriber.
            head_object_response(ContentLength=MP_THRESHOLD),
            get_object_tagging_response({}),
            *mp_copy_responses(),
        ],
    )
    # The source's HeadObject takes its copy-source key, if any.
    head_params = {
        name.removeprefix("CopySource"): value
        for name, value in source_params.items()
    }
    assert run.operations_with_params == [
        listing("sourcebucket"),
        listing("mybucket"),
        head_object_request("sourcebucket", "mykey", **head_params),
        get_object_tagging_request("sourcebucket", "mykey"),
        create_mpu_request("mybucket", "mykey", **DESTINATION_SSE_C),
        upload_part_copy_request(
            "sourcebucket",
            "mykey",
            "mybucket",
            "mykey",
            "upload_id",
            PartNumber=1,
            CopySourceRange=f"bytes=0-{MP_THRESHOLD - 1}",
            CopySourceIfMatch=ETAG,
            **DESTINATION_SSE_C,
            **source_params,
        ),
        complete_mpu_request(
            "mybucket", "mykey", "upload_id", num_parts=1, **DESTINATION_SSE_C
        ),
    ], run.describe()


async def test_with_accesspoint_arn(s3api: ApiSession, root: Path) -> None:
    run = await s3api.run(
        ["s3", "sync", f"s3://{ACCESS_POINT_ARN}", str(root)],
        replies=[
            list_objects_response(["mykey"], Size=len(BODY)),
            get_object_response(BODY),
        ],
    )
    # The ARN reaches the wire as its access point's endpoint.
    assert [
        (call.operation, call.request.headers.get("host"))
        for call in run.calls
    ] == [
        ("ListObjectsV2", ACCESS_POINT_HOST),
        ("GetObject", ACCESS_POINT_HOST),
    ], run.describe()
    assert run.calls[1].params["Key"] == "mykey", run.describe()
    assert (root / "mykey").read_bytes() == BODY


async def test_with_copy_props(s3api: ApiSession) -> None:
    upload_id = "upload_id"
    large_tag_set = {"tag-key": "val" * 3000}
    metadata = {"tag-key": "tag-value"}
    run = await s3api.run(
        "s3 sync s3://sourcebucket/ s3://bucket/ --copy-props default",
        replies=[
            list_objects_response(["key"], Size=MP_THRESHOLD),
            EMPTY_PAGE,
            # Upstream's head reply kept its default ContentLength of 100.
            head_object_response(
                ContentLength=MP_THRESHOLD, Metadata=metadata
            ),
            get_object_tagging_response(large_tag_set),
            create_mpu_response(upload_id),
            upload_part_copy_response(),
            {},
            {},
        ],
    )
    tagging_operation, tagging = put_object_tagging_request(
        "bucket", "key", large_tag_set
    )
    # botocore names the algorithm of the checksum it adds.
    tagging["ChecksumAlgorithm"] = "CRC64NVME"
    assert run.operations_with_params == [
        listing("sourcebucket"),
        listing("bucket"),
        head_object_request("sourcebucket", "key"),
        get_object_tagging_request("sourcebucket", "key"),
        create_mpu_request("bucket", "key", Metadata=metadata),
        upload_part_copy_request(
            "sourcebucket",
            "key",
            "bucket",
            "key",
            upload_id,
            CopySourceRange=f"bytes=0-{MP_THRESHOLD - 1}",
            PartNumber=1,
            CopySourceIfMatch=ETAG,
        ),
        complete_mpu_request("bucket", "key", upload_id, 1),
        # A tag set too large for the copy's header is put afterwards.
        (tagging_operation, tagging),
    ], run.describe()


@pytest.mark.parametrize("algorithm", ALGORITHMS)
async def test_upload_with_checksum_algorithm(
    transfer_api: ApiSession, root: Path, algorithm: str
) -> None:
    write(root / "foo.txt", "contents")
    run = await transfer_api.run(
        [
            "s3",
            "sync",
            str(root),
            "s3://bucket/",
            "--checksum-algorithm",
            algorithm,
        ]
    )
    assert run.operations_with_params == [
        listing("bucket"),
        put_request(
            transfer_api,
            "bucket",
            "foo.txt",
            b"contents",
            algorithm,
            ContentType="text/plain",
        ),
    ], run.describe()


async def test_copy_with_checksum_algorithm_update_sha1(
    s3api: ApiSession,
) -> None:
    source_page = {
        "Contents": [
            {
                "Key": "mykey",
                "LastModified": "00:00:00Z",
                "Size": 100,
                "ChecksumAlgorithm": "SHA1",
                "ETag": "myetag",
            }
        ],
        "CommonPrefixes": [],
    }
    run = await s3api.run(
        "s3 sync s3://src-bucket/ s3://dest-bucket/ "
        "--checksum-algorithm SHA1",
        replies=[
            source_page,
            EMPTY_PAGE,
            {"ChecksumSHA1": "sha1-checksum"},
        ],
    )
    assert run.operations_with_params == [
        listing("src-bucket"),
        listing("dest-bucket"),
        (
            "CopyObject",
            {
                "CopySource": {"Bucket": "src-bucket", "Key": "mykey"},
                "Bucket": "dest-bucket",
                "Key": "mykey",
                "ChecksumAlgorithm": "SHA1",
                "AnnotationDirective": "EXCLUDE",
            },
        ),
    ], run.describe()


@pytest.mark.parametrize("algorithm", ALGORITHMS)
async def test_download_with_checksum_mode(
    transfer_api: ApiSession, root: Path, algorithm: str
) -> None:
    # S3 lists only keys under the prefix asked for, which upstream's
    # "bucket" was not; the checksum is the body's, which the CLI checks.
    get = get_object_response(BODY)
    get[f"Checksum{algorithm}"] = checksum(algorithm, BODY)
    run = await transfer_api.run(
        [
            "s3",
            "sync",
            "s3://bucket/foo",
            str(root),
            "--checksum-mode",
            "ENABLED",
        ],
        replies=[
            list_objects_response(["foo/bucket"], Size=len(BODY)),
            get,
        ],
    )
    assert run.operations_with_params == [
        listing("bucket", "foo/"),
        *download_requests(transfer_api, "bucket", "foo/bucket"),
    ], run.describe()
    assert (root / "bucket").read_bytes() == BODY


@pytest.mark.parametrize(
    ("destination_keys", "uploads"),
    [
        pytest.param(["file.txt"], True, id="missing-at-destination"),
        pytest.param(["new_file.txt"], False, id="exists-at-destination"),
    ],
)
async def test_sync_upload_with_no_overwrite(
    transfer_api: ApiSession,
    root: Path,
    destination_keys: list[str],
    uploads: bool,
) -> None:
    write(root / "new_file.txt", "mycontent")
    run = await transfer_api.run(
        ["s3", "sync", str(root), "s3://bucket", "--no-overwrite"],
        replies=[
            list_objects_response(destination_keys),
            {"ETag": '"c8afdb36c52cf4727836669019e69222"'},
        ],
    )
    expected = [listing("bucket")]
    if uploads:
        expected.append(
            put_request(
                transfer_api,
                "bucket",
                "new_file.txt",
                b"mycontent",
                ContentType="text/plain",
            )
        )
    assert run.operations_with_params == expected, run.describe()


@pytest.mark.parametrize(
    ("local_name", "downloads"),
    [
        pytest.param(None, True, id="missing-at-destination"),
        pytest.param("new_file.txt", False, id="exists-at-destination"),
    ],
)
async def test_sync_download_with_no_overwrite(
    transfer_api: ApiSession,
    root: Path,
    local_name: str | None,
    downloads: bool,
) -> None:
    if local_name is not None:
        write(root / local_name, "My content")
    run = await transfer_api.run(
        ["s3", "sync", "s3://bucket/", str(root), "--no-overwrite"],
        replies=[
            list_objects_response(["new_file.txt"], Size=len(BODY)),
            get_object_response(BODY),
        ],
    )
    expected = [listing("bucket")]
    if downloads:
        expected += download_requests(transfer_api, "bucket", "new_file.txt")
    assert run.operations_with_params == expected, run.describe()
    assert (root / "new_file.txt").read_bytes() == (
        BODY if downloads else b"My content"
    )


@pytest.mark.parametrize(
    ("destination_keys", "copies"),
    [
        pytest.param(["file1.txt"], True, id="missing-at-destination"),
        pytest.param(
            ["new_file.txt", "file1.txt"], False, id="exists-at-destination"
        ),
    ],
)
async def test_sync_copy_with_no_overwrite(
    s3api: ApiSession, destination_keys: list[str], copies: bool
) -> None:
    run = await s3api.run(
        "s3 sync s3://bucket/ s3://bucket2/ --no-overwrite",
        replies=[
            list_objects_response(["new_file.txt"]),
            list_objects_response(destination_keys),
            {},
        ],
    )
    expected = [listing("bucket"), listing("bucket2")]
    if copies:
        expected.append(
            copy_object_request(
                "bucket", "new_file.txt", "bucket2", "new_file.txt"
            )
        )
    assert run.operations_with_params == expected, run.describe()


class SymlinkedDestination:
    """Upstream's TestSyncDownloadNoFollowSymlinks tree: dest/sub links to
    outside/, which holds escaped.txt."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.dest = root / "dest"
        self.dest.mkdir()
        self.outside = root / "outside"
        self.outside.mkdir()
        self.escaped = write(self.outside / "escaped.txt", "original")
        self.symlink = self.dest / "sub"
        self.symlink.symlink_to(self.outside)

    def listing_response(self, key: str) -> Params:
        content = {
            "Key": key,
            "Size": 8,
            "LastModified": "00:00:00Z",
            "ETag": ETAG,
        }
        return {"Contents": [content], "CommonPrefixes": []}


INJECTED: Final = b"injected"
skip_if_windows: Final = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink tests only supported on mac/linux",
)


@pytest.fixture
def symlinked(root: Path) -> SymlinkedDestination:
    return SymlinkedDestination(root)


@skip_if_windows
@pytest.mark.parametrize(
    "key",
    [
        pytest.param("sub/escaped.txt", id="through-symlink"),
        pytest.param("sub/../escaped.txt", id="parent-reference"),
        pytest.param(
            "missing/../sub/escaped.txt", id="missing-parent-reference"
        ),
    ],
)
async def test_no_follow_symlinks_skips_object(
    s3api: ApiSession, symlinked: SymlinkedDestination, key: str
) -> None:
    run = await s3api.run(
        [
            "s3",
            "sync",
            "s3://bucket",
            str(symlinked.dest),
            "--no-follow-symlinks",
        ],
        replies=[
            symlinked.listing_response(key),
            get_object_response(INJECTED),
        ],
    )
    assert run.operations == ["ListObjectsV2"], run.describe()
    assert symlinked.escaped.read_text(encoding="utf-8") == "original"
    assert symlinked.symlink.is_symlink()
    assert not (symlinked.root / "escaped.txt").exists()


@skip_if_windows
async def test_follows_symlink_by_default(
    transfer_api: ApiSession, symlinked: SymlinkedDestination
) -> None:
    key = "sub/escaped.txt"
    run = await transfer_api.run(
        ["s3", "sync", "s3://bucket", str(symlinked.dest)],
        replies=[
            symlinked.listing_response(key),
            get_object_response(INJECTED),
        ],
    )
    assert run.operations_with_params == [
        listing("bucket"),
        *download_requests(transfer_api, "bucket", key),
    ], run.describe()
    assert symlinked.escaped.read_text(encoding="utf-8") == "injected"
    assert symlinked.symlink.is_symlink()


def runner_list_objects_response(keys: Sequence[str]) -> HTTPResponse:
    """Upstream's add_botocore_list_objects_response, as its wire bytes."""
    body = (
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Prefix/>"
    )
    for key in keys:
        body += (
            "<Contents>"
            "<LastModified>2015-12-08T18:26:43.000Z</LastModified>"
            f"<Key>{key}</Key><Size>100</Size><ETag>foobar</ETag>"
            "</Contents>"
        )
    body += "</ListBucketResult>"
    return HTTPResponse.raw(body.encode())


RUNNER_COPY_RESPONSE: Final = HTTPResponse.raw(
    b"<CopyObjectResult></CopyObjectResult>"
)


def virtual_host(bucket: str, region: str = RUNNER_REGION) -> str:
    return f"{bucket}.s3.{region}.amazonaws.com"


async def test_respects_source_region(s3api: ApiSession) -> None:
    s3api.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    source_region = "af-south-1"
    run = await s3api.run(
        [
            "s3",
            "sync",
            "s3://sourcebucket/",
            "s3://bucket/",
            "--region",
            RUNNER_REGION,
            "--source-region",
            source_region,
        ],
        replies=[
            runner_list_objects_response(["key"]),
            runner_list_objects_response([]),
            RUNNER_COPY_RESPONSE,
        ],
    )
    assert [
        (call.operation, call.request.headers.get("host"))
        for call in run.calls
    ] == [
        ("ListObjectsV2", virtual_host("sourcebucket", source_region)),
        ("ListObjectsV2", virtual_host("bucket")),
        ("CopyObject", virtual_host("bucket")),
    ], run.describe()


def crt_requests(run: CommandRun) -> list[tuple[str, str | None, str]]:
    """The transfer requests the CRT client sent: operation, host, and
    path. Native lists through the CRT too, so listings are left out."""
    return [
        (
            call.operation,
            call.request.headers.get("host"),
            call.request.effective_path,
        )
        for call in run.calls
        if CRT_USER_AGENT in call.request.headers.get("user-agent", "")
        and call.operation != "ListObjectsV2"
    ]


# Upstream's BaseCRTTransferClientTest wrote this to each download's file.
CRT_CONTENT: Final = b"content"


# S3's answer to an object request, with its request ids: the CRT client
# rejects a DeleteObject's 204 without them. It is serialized for the
# request it answers, so it answers a PutObject as well.
CRT_OBJECT_REPLY: Final = Reply(
    headers={"x-amz-request-id": "REQUESTID", "x-amz-id-2": "HOSTID"}
)


async def test_upload_sync_using_crt_client(
    s3crt: ApiSession, root: Path
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    write(root / "myfile", "mycontent")
    run = await s3crt.run(
        ["s3", "sync", str(root), "s3://bucket/"],
        replies=[runner_list_objects_response([]), {}],
    )
    assert crt_requests(run) == [
        ("PutObject", virtual_host("bucket"), "/myfile"),
    ], run.describe()
    assert run.calls[-1].params["Body"] == b"mycontent", run.describe()


async def test_download_sync_using_crt_client(
    s3crt: ApiSession, root: Path
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    run = await s3crt.run(
        ["s3", "sync", "s3://bucket/", str(root)],
        replies=[
            list_objects_response(["key"], Size=len(CRT_CONTENT)),
            get_object_response(CRT_CONTENT),
        ],
    )
    # The listing reports no checksums, so the CRT client sends no HEAD.
    assert crt_requests(run) == [
        ("GetObject", virtual_host("bucket"), "/key"),
    ], run.describe()
    assert (root / "key").read_bytes() == CRT_CONTENT


async def test_upload_sync_with_delete_using_crt_client(
    s3crt: ApiSession, root: Path
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    write(root / "a-file", "mycontent")
    run = await s3crt.run(
        ["s3", "sync", str(root), "s3://bucket/", "--delete"],
        replies=[
            runner_list_objects_response(["delete-this"]),
            CRT_OBJECT_REPLY,
            CRT_OBJECT_REPLY,
        ],
    )
    # The upload and the delete run at once, so either may arrive first.
    assert sorted(crt_requests(run)) == [
        ("DeleteObject", virtual_host("bucket"), "/delete-this"),
        ("PutObject", virtual_host("bucket"), "/a-file"),
    ], run.describe()


async def test_download_sync_with_delete_using_crt_client(
    s3crt: ApiSession, root: Path
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    stale = write(root / "delete-this", "content")
    run = await s3crt.run(
        ["s3", "sync", "s3://bucket/", str(root), "--delete"],
        replies=[
            list_objects_response(["key"], Size=len(CRT_CONTENT)),
            get_object_response(CRT_CONTENT),
        ],
    )
    # The listing reports no checksums, so the CRT client sends no HEAD.
    assert crt_requests(run) == [
        ("GetObject", virtual_host("bucket"), "/key"),
    ], run.describe()
    # Upstream looked for the file in its own working directory.
    assert not stale.exists()


async def test_does_not_use_crt_client_for_copy_syncs(
    s3crt: ApiSession,
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = RUNNER_REGION
    run = await s3crt.run(
        "s3 sync s3://bucket/ s3://otherbucket/",
        replies=[
            runner_list_objects_response(["key"]),
            runner_list_objects_response([]),
            RUNNER_COPY_RESPONSE,
        ],
    )
    assert run.operations == [
        "ListObjectsV2",
        "ListObjectsV2",
        "CopyObject",
    ], run.describe()
    assert crt_requests(run) == [], run.describe()


@pytest.mark.parametrize(
    "paths",
    [
        pytest.param(["{root}", f"s3://{DIRECTORY_BUCKET}/"], id="upload"),
        pytest.param([f"s3://{DIRECTORY_BUCKET}/", "{root}"], id="download"),
        pytest.param(
            ["s3://bucket/", f"s3://{DIRECTORY_BUCKET}/"], id="copy"
        ),
        pytest.param(
            ["s3://bucket/", f"s3://{DIRECTORY_BUCKET}/", "--delete"],
            id="delete",
        ),
    ],
)
async def test_incompatible_with_directory_bucket(
    s3api: ApiSession, root: Path, paths: list[str]
) -> None:
    run = await s3api.run(
        ["s3", "sync", *(path.format(root=root) for path in paths)],
        expected_rc=252,
    )
    assert (
        "Cannot use sync command with a directory bucket." in run.stderr
    ), run.describe()
    assert run.calls == (), run.describe()


async def test_compatible_with_sync_with_local_directory_like_directory_bucket(
    transfer_api: ApiSession,
) -> None:
    run = await transfer_api.run(
        f"s3 sync s3://bucket/ {DIRECTORY_BUCKET}/",
        replies=[EMPTY_PAGE],
    )
    # The command validated and made its listing.
    assert run.operations == ["ListObjectsV2"], run.describe()


LOWER_KEY: Final = "a.txt"
UPPER_KEY: Final = "A.txt"


@pytest.mark.parametrize(
    ("mode", "expected_rc", "message", "downloads"),
    [
        pytest.param(
            "error",
            1,
            f"Failed to download bucket/{UPPER_KEY}",
            0,
            marks=requires_case_insensitive,
            id="error",
        ),
        pytest.param(
            "warn",
            0,
            f"warning: Downloading bucket/{UPPER_KEY}",
            1,
            marks=requires_case_insensitive,
            id="warn",
        ),
        pytest.param(
            "skip",
            0,
            f"warning: Skipping bucket/{UPPER_KEY}",
            0,
            marks=requires_case_insensitive,
            id="skip",
        ),
        pytest.param("ignore", 0, None, 1, id="ignore"),
    ],
)
async def test_case_conflict_with_existing_file(
    transfer_api: ApiSession,
    root: Path,
    mode: str,
    expected_rc: int,
    message: str | None,
    downloads: int,
) -> None:
    write(root / LOWER_KEY, "mycontent")
    run = await transfer_api.run(
        ["s3", "sync", "s3://bucket", str(root), "--case-conflict", mode],
        replies=[
            list_objects_response([UPPER_KEY], Size=len(BODY)),
            *[get_object_response(BODY) for _ in range(downloads)],
        ],
        expected_rc=expected_rc,
    )
    if message is not None:
        assert message in run.stderr, run.describe()


skip_rename_on_windows: Final = pytest.mark.skipif(
    sys.platform == "win32", reason="Can't rename to same file"
)


@pytest.mark.parametrize(
    ("mode", "expected_rc", "message", "downloads"),
    [
        pytest.param(
            "error",
            1,
            f"Failed to download bucket/{LOWER_KEY}",
            1,
            id="error",
        ),
        pytest.param(
            "warn",
            0,
            f"warning: Downloading bucket/{LOWER_KEY}",
            2,
            marks=skip_rename_on_windows,
            id="warn",
        ),
        pytest.param(
            "skip",
            0,
            f"warning: Skipping bucket/{LOWER_KEY}",
            1,
            id="skip",
        ),
        pytest.param(
            "ignore", 0, None, 2, marks=skip_rename_on_windows, id="ignore"
        ),
    ],
)
async def test_case_conflicts_in_s3(
    s3api: ApiSession,
    root: Path,
    mode: str,
    expected_rc: int,
    message: str | None,
    downloads: int,
) -> None:
    # "A.txt" lists first, so its download is under way when "a.txt" is
    # paired with it; under `error` it may be canceled before it is sent.
    # Only the classic client runs this: the CRT client interleaves two
    # downloads' requests, which replies in a fixed order cannot follow.
    run = await s3api.run(
        ["s3", "sync", "s3://bucket", str(root), "--case-conflict", mode],
        replies=[
            list_objects_response([UPPER_KEY, LOWER_KEY], Size=len(BODY)),
            *[get_object_response(BODY)] * downloads,
        ],
        expected_rc=expected_rc,
    )
    if message is not None:
        assert message in run.stderr, run.describe()
    if mode in ("error", "skip"):
        fetched = [
            call.params["Key"]
            for call in run.calls
            if call.operation == "GetObject"
        ]
        assert LOWER_KEY not in fetched, run.describe()
