"""The checksums `s3 cp` sends with uploads and checks on downloads.

`s3 cp` runs the CRT client here, which the profile prefers, and the AWS
CLI hands it the checksum settings in place of botocore's own handlers
(s3transfer/crt.py:1494-1534, 1548-1588, 1602-1635): an upload carries a
CRC64NVME trailer, and a multipart upload declares the algorithm and
lists each part's checksum, unless request_checksum_calculation is
when_required; a download asks for the object's checksum and checks it,
unless response_checksum_validation is when_required. The bucket is
s3store.py's ScriptedS3, which answers checksum mode with the stored
CRC64NVME it is given, as S3 does.
"""

import base64
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import awscrt.checksums
import pytest

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3store import (
    ObjectKey,
    ScriptedS3,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
MIB: Final = 1024 * 1024
PREFIX: Final = "checksum/"
FILES: Final[Mapping[str, bytes]] = {
    "kib.bin": pattern_bytes("kib.bin", 1024),
    # Above the threshold of either profile below.
    "seventeen.bin": pattern_bytes("seventeen.bin", 17 * MIB),
}
OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, f"{PREFIX}{name}"): body for name, body in FILES.items()
}
CRT_BLOCK: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
# The CRT client's own part size, or 5 MiB parts above 6 MiB.
CONFIGS: Final = {
    "crt": CRT_BLOCK,
    "chunked": (
        CRT_BLOCK
        + "  multipart_chunksize = 5MB\n  multipart_threshold = 6MB\n"
    ),
}
WHEN_REQUIRED: Final = "when_required"
MODES: Final = ["when_supported", WHEN_REQUIRED]
# The request headers that carry or ask for a checksum.
CHECKSUM_HEADERS: Final = (
    "content-encoding",
    "content-md5",
    "x-amz-checksum-algorithm",
    "x-amz-checksum-crc64nvme",
    "x-amz-checksum-mode",
    "x-amz-content-sha256",
    "x-amz-sdk-checksum-algorithm",
    "x-amz-trailer",
)
TRANSFER_OPERATIONS: Final = frozenset(
    {"PutObject", "CreateMultipartUpload", "UploadPart"}
)
# A well-formed CRC64NVME no object here has.
WRONG_CRC64NVME: Final = "AAAAAAAAAAA="
MISMATCH: Final = (
    "AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH: response checksum header does "
    "not match calculated checksum"
)


def crc64nvme(body: bytes) -> str:
    digest = awscrt.checksums.crc64nvme(body).to_bytes(8, byteorder="big")
    return base64.b64encode(digest).decode()


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: ScriptedS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )


def checksum_headers(request: ReconstructedRequest) -> dict[str, str]:
    headers = request.wire_request.headers
    return {
        name: value
        for name in CHECKSUM_HEADERS
        if (value := headers.get(name)) is not None
    }


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    store: ScriptedS3,
    *,
    config: str,
    environment: Mapping[str, str],
    local_files: Mapping[str, bytes] | None = None,
) -> Run:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment)
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "cp", *arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
            timeout=60.0,
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


# The CRT signs no payload hash; a checksum goes in an aws-chunked trailer.
UNSIGNED: Final = {"x-amz-content-sha256": "UNSIGNED-PAYLOAD"}
TRAILER: Final = {
    "content-encoding": "aws-chunked",
    "x-amz-content-sha256": "STREAMING-UNSIGNED-PAYLOAD-TRAILER",
    "x-amz-trailer": "x-amz-checksum-crc64nvme",
}
# The part size of a 17 MiB upload: the CRT's own 8 MiB, or the profile's.
PART_SIZES: Final = {"crt": 8 * MIB, "chunked": 5 * MIB}

UploadShape = tuple[str, int, dict[str, str], str | None]


def expected_upload(
    body: bytes, config: str, mode: str
) -> tuple[list[UploadShape], list[list[tuple[int, str | None]]]]:
    """Each upload request's checksum headers and CRC64NVME, in operation
    and part order, and the part checksums CompleteMultipartUpload lists.

    Upstream leaves out botocore's Content-MD5 and checksum headers and has
    the CRT add the trailer (s3transfer/crt.py:1494-1534).
    """
    send = mode != WHEN_REQUIRED
    if len(body) <= 8 * MIB:
        return (
            [
                (
                    "PutObject",
                    0,
                    TRAILER if send else UNSIGNED,
                    crc64nvme(body) if send else None,
                )
            ],
            [],
        )
    size = PART_SIZES[config]
    parts = [body[start : start + size] for start in range(0, len(body), size)]
    checksums = [crc64nvme(part) if send else None for part in parts]
    create = (
        {"x-amz-checksum-algorithm": "CRC64NVME", **UNSIGNED}
        if send
        else UNSIGNED
    )
    shapes: list[UploadShape] = [("CreateMultipartUpload", 0, create, None)]
    shapes += [
        ("UploadPart", number, TRAILER if send else UNSIGNED, checksum)
        for number, checksum in enumerate(checksums, start=1)
    ]
    return shapes, [list(enumerate(checksums, start=1))]


def setting(variable: str, mode: str) -> dict[str, str]:
    return {variable: mode} if mode == WHEN_REQUIRED else {}


# A 1 KiB object is one PutObject under either profile; 17 MiB is a
# multipart upload under both.
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("name", "config"),
    [
        pytest.param("kib.bin", "crt", id="put"),
        pytest.param("seventeen.bin", "crt", id="multipart-crt"),
        pytest.param("seventeen.bin", "chunked", id="multipart-chunked"),
    ],
)
async def test_cp_upload_sends_crt_checksums(
    aws_cli: str, tmp_path: Path, name: str, config: str, mode: str
) -> None:
    body = FILES[name]
    key = f"{PREFIX}{name}"
    store = ScriptedS3()
    run = await run_cp(
        aws_cli,
        tmp_path,
        (name, f"s3://{BUCKET}/{key}"),
        store,
        config=CONFIGS[config],
        environment=setting("AWS_REQUEST_CHECKSUM_CALCULATION", mode),
        local_files={name: body},
    )
    report = run.describe()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        f"upload: .{os.sep}{name} to s3://{BUCKET}/{key}\n",
        "",
    ), report
    assert store.objects == {(BUCKET, key): body}, report
    shapes = sorted(
        (
            request.operation_model.name,
            request.params.get("PartNumber", 0),
            checksum_headers(request),
            request.params.get("ChecksumCRC64NVME"),
        )
        for request in store.received
        if request.operation_model.name in TRANSFER_OPERATIONS
    )
    completed = [
        [
            (part["PartNumber"], part.get("ChecksumCRC64NVME"))
            for part in request.params["MultipartUpload"]["Parts"]
        ]
        for request in store.received
        if request.operation_model.name == "CompleteMultipartUpload"
    ]
    assert (shapes, completed) == expected_upload(body, config, mode), report


DOWNLOADS: Final = [
    pytest.param(
        (f"s3://{BUCKET}/{PREFIX}kib.bin", "kib.bin"),
        {"kib.bin": FILES["kib.bin"]},
        id="single",
    ),
    pytest.param(
        (f"s3://{BUCKET}/{PREFIX}", "down", "--recursive"),
        {f"down/{name}": body for name, body in FILES.items()},
        id="recursive",
    ),
]


def download_line(destination: str) -> str:
    name = destination.removeprefix("down/")
    shown = (
        os.path.join("down", name)
        if destination.startswith("down/")
        else os.path.join(".", name)
    )
    return f"download: s3://{BUCKET}/{PREFIX}{name} to {shown}"


def object_reads(run: Run) -> list[tuple[str, str, str | None]]:
    """Each HeadObject and GetObject: its Range and its checksum mode."""
    reads = [
        (
            request.operation_model.name,
            request.params.get("Range", ""),
            request.wire_request.headers.get("x-amz-checksum-mode"),
        )
        for request in run.store.received
        if request.operation_model.name in {"HeadObject", "GetObject"}
    ]
    return sorted(reads, key=lambda read: (read[0], read[1], read[2] or ""))


def expected_chunked_reads(
    files: Mapping[str, bytes], mode: str
) -> list[tuple[str, str, str | None]]:
    """The sorted reads of a download under 5 MiB parts above 6 MiB.

    The 1 KiB object is one GET whose response carries the checksum. The
    17 MiB object is ranged, and a validating CRT client reads its
    checksum with a HeadObject of its own first. A single download's
    HeadObject is the file generator's, which asks for the mode in
    uppercase (customizations/s3/filegenerator.py:400).
    """
    mode_header = None if mode == WHEN_REQUIRED else "enabled"
    reads: list[tuple[str, str, str | None]] = []
    for destination, body in files.items():
        if len(body) <= 6 * MIB:
            reads.append(("GetObject", "", mode_header))
            continue
        reads += [
            (
                "GetObject",
                f"bytes={start}-{min(start + 5 * MIB, len(body)) - 1}",
                mode_header,
            )
            for start in range(0, len(body), 5 * MIB)
        ]
        if mode_header is not None:
            reads.append(("HeadObject", "", mode_header))
    if len(files) == 1:
        reads.append(
            ("HeadObject", "", None if mode == WHEN_REQUIRED else "ENABLED")
        )
    return sorted(reads, key=lambda read: (read[0], read[1], read[2] or ""))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("config", CONFIGS)
@pytest.mark.parametrize(("arguments", "files"), DOWNLOADS)
async def test_cp_download_asks_for_checksums(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    files: dict[str, bytes],
    config: str,
    mode: str,
) -> None:
    store = ScriptedS3(
        OBJECTS,
        checksums={key: crc64nvme(body) for key, body in OBJECTS.items()},
    )
    run = await run_cp(
        aws_cli,
        tmp_path,
        arguments,
        store,
        config=CONFIGS[config],
        environment=setting("AWS_RESPONSE_CHECKSUM_VALIDATION", mode),
    )
    report = run.describe()
    assert store.failures == [], report
    # Concurrent transfers finish, and print, in any order.
    assert (run.returncode, sorted(run.stdout.splitlines()), run.stderr) == (
        0,
        sorted(download_line(destination) for destination in files),
        "",
    ), report
    assert run.local_files == files, report
    reads = object_reads(run)
    if config == "chunked":
        assert reads == expected_chunked_reads(files, mode), report
        return
    # The CRT client picks its own ranges; each GET asks for the checksum.
    # A validating client checks a single download against the checksum
    # the command's HeadObject reported, and looks each listed object up
    # first with its own HeadObject, spelling the mode in lowercase: the
    # listing names a full-object checksum but not its value.
    validating = mode != WHEN_REQUIRED
    listed = "--recursive" in arguments
    assert {sent for name, _, sent in reads if name == "GetObject"} == {
        "enabled" if validating else None
    }, report
    crt_heads = [
        read for read in reads if read == ("HeadObject", "", "enabled")
    ]
    assert len(crt_heads) == (len(files) if validating and listed else 0), report
    # A single download's file generator looks the object up as well.
    generator_heads = [
        read
        for read in reads
        if read[0] == "HeadObject" and read[2] != "enabled"
    ]
    assert generator_heads == (
        [("HeadObject", "", "ENABLED" if validating else None)]
        if len(files) == 1
        else []
    ), report


# The small object's stored checksum is wrong, the large one's right. The
# CRT client fails the download whose checksum does not match, and the AWS
# CLI reports str(AwsCrtError) and leaves no partial file; the others
# land. Without validation nothing is compared, as
# test_cp_download_asks_for_checksums shows: no request asks for the
# checksum, so none comes back to mismatch.
@pytest.mark.parametrize("config", CONFIGS)
@pytest.mark.parametrize(("arguments", "files"), DOWNLOADS)
async def test_cp_download_checksum_mismatch_fails_that_object(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    files: dict[str, bytes],
    config: str,
) -> None:
    bad = (BUCKET, f"{PREFIX}kib.bin")
    good = (BUCKET, f"{PREFIX}seventeen.bin")
    store = ScriptedS3(
        OBJECTS,
        checksums={bad: WRONG_CRC64NVME, good: crc64nvme(OBJECTS[good])},
    )
    run = await run_cp(
        aws_cli,
        tmp_path,
        arguments,
        store,
        config=CONFIGS[config],
        environment={},
    )
    report = run.describe()
    assert store.failures == [], report
    failed = next(name for name in files if name.endswith("kib.bin"))
    shown = download_line(failed).partition(" to ")[2]
    landed = {name: body for name, body in files.items() if name != failed}
    assert (run.returncode, sorted(run.stdout.splitlines()), run.stderr) == (
        1,
        sorted(download_line(name) for name in landed),
        f"download failed: s3://{BUCKET}/{PREFIX}kib.bin to {shown} "
        f"{MISMATCH}\n",
    ), report
    assert run.local_files == landed, report
