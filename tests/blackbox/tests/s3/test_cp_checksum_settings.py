"""The checksum settings `s3 cp` takes: --checksum-algorithm and
--checksum-mode.

Upstream maps --checksum-algorithm onto an upload's ChecksumAlgorithm and
--checksum-mode onto a download's ChecksumMode, skipping either when empty
(customizations/s3/utils.py:486-616). Under the CRT client, which the
profile prefers here, s3transfer hands both to the CRT in place of
botocore's handlers (s3transfer/crt.py:1494-1534, 1548-1588, 1602-1635): an
upload given an algorithm sends that algorithm's checksum in a trailer,
whatever request_checksum_calculation says, and a download given the mode
checks the object's checksum, whatever response_checksum_validation says.
A single download's file generator sends the mode with its HeadObject
(filegenerator.py:393-401). Each setting belongs to one direction, and
upstream refuses it on the other before any request
(subcommands.py:1832-1842, 1935-1948).
"""

import base64
import hashlib
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
    # Three 5 MiB parts, the last short.
    "eleven.bin": pattern_bytes("eleven.bin", 11 * MIB),
}
OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, f"{PREFIX}{name}"): body for name, body in FILES.items()
}
# 5 MiB parts above 6 MiB.
CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = crt\n"
    "  multipart_chunksize = 5MB\n  multipart_threshold = 6MB\n"
)
PART_SIZE: Final = 5 * MIB
WHEN_REQUIRED: Final = "when_required"
MODES: Final = ["when_supported", WHEN_REQUIRED]
TRANSFER_OPERATIONS: Final = frozenset(
    {"PutObject", "CreateMultipartUpload", "UploadPart"}
)
# A well-formed CRC64NVME no object here has.
WRONG_CRC64NVME: Final = "AAAAAAAAAAA="
MISMATCH: Final = (
    "AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH: response checksum header does "
    "not match calculated checksum"
)


def crc(function, size: int):
    return lambda body: function(body).to_bytes(size, byteorder="big")


XXHASH: Final = awscrt.checksums.XXHash
# Each algorithm the option names, with the digest S3 takes for it.
DIGESTS: Final = {
    "CRC32": crc(awscrt.checksums.crc32, 4),
    "CRC32C": crc(awscrt.checksums.crc32c, 4),
    "SHA1": lambda body: hashlib.sha1(body).digest(),
    "SHA256": lambda body: hashlib.sha256(body).digest(),
    "CRC64NVME": crc(awscrt.checksums.crc64nvme, 8),
    "SHA512": lambda body: hashlib.sha512(body).digest(),
    "XXHASH64": XXHASH.compute_xxhash64,
    "XXHASH3": XXHASH.compute_xxhash3_64,
    "XXHASH128": XXHASH.compute_xxhash3_128,
}


def checksum(algorithm: str, body: bytes) -> str:
    return base64.b64encode(DIGESTS[algorithm](body)).decode()


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


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    store: ScriptedS3,
    *,
    environment: Mapping[str, str],
    local_files: Mapping[str, bytes] | None = None,
) -> Run:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(CONFIG, encoding="utf-8")
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


def setting(variable: str, mode: str) -> dict[str, str]:
    return {variable: mode} if mode == WHEN_REQUIRED else {}


def checksum_headers(
    request: ReconstructedRequest, algorithm: str
) -> dict[str, str]:
    """The request headers that carry or ask for a checksum."""
    names = (
        "content-encoding",
        "content-md5",
        "x-amz-checksum-algorithm",
        f"x-amz-checksum-{algorithm.lower()}",
        "x-amz-checksum-mode",
        "x-amz-checksum-type",
        "x-amz-content-sha256",
        "x-amz-sdk-checksum-algorithm",
        "x-amz-trailer",
    )
    headers = request.wire_request.headers
    return {
        name: value for name in names if (value := headers.get(name)) is not None
    }


UNSIGNED: Final = {"x-amz-content-sha256": "UNSIGNED-PAYLOAD"}
# botocore's FLEXIBLE_CHECKSUMS_REQ_<algorithm> feature ids
# (botocore/useragent.py:70-106).
REQUEST_ALGORITHM_FEATURES: Final = frozenset(
    {"U", "V", "W", "X", "Y", "AE", "AF", "AG", "AH", "AI"}
)


def request_algorithm_features(request: ReconstructedRequest) -> frozenset[str]:
    """The request checksum algorithms the request's User-Agent names."""
    user_agent = request.wire_request.headers.get("user-agent", "")
    features = next(
        (
            component[2:].split(",")
            for component in user_agent.split()
            if component.startswith("m/")
        ),
        [],
    )
    return frozenset(features) & REQUEST_ALGORITHM_FEATURES

UploadShape = tuple[str, int, dict[str, str], str | None]


def expected_upload(
    body: bytes, algorithm: str
) -> tuple[list[UploadShape], list[list[tuple[int, str]]]]:
    """Each upload request's checksum headers and checksum, in operation and
    part order, and the part checksums CompleteMultipartUpload lists: the
    CRT's trailer of the chosen algorithm, and on a multipart upload the
    algorithm CreateMultipartUpload declares."""
    trailer = {
        "content-encoding": "aws-chunked",
        "x-amz-content-sha256": "STREAMING-UNSIGNED-PAYLOAD-TRAILER",
        "x-amz-trailer": f"x-amz-checksum-{algorithm.lower()}",
    }
    if len(body) <= 6 * MIB:
        return [("PutObject", 0, trailer, checksum(algorithm, body))], []
    parts = [
        body[start : start + PART_SIZE]
        for start in range(0, len(body), PART_SIZE)
    ]
    checksums = [checksum(algorithm, part) for part in parts]
    shapes: list[UploadShape] = [
        (
            "CreateMultipartUpload",
            0,
            {"x-amz-checksum-algorithm": algorithm, **UNSIGNED},
            None,
        )
    ]
    shapes += [
        ("UploadPart", number, trailer, part_checksum)
        for number, part_checksum in enumerate(checksums, start=1)
    ]
    return shapes, [list(enumerate(checksums, start=1))]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", ["kib.bin", "eleven.bin"])
@pytest.mark.parametrize("algorithm", DIGESTS)
async def test_cp_upload_sends_the_chosen_checksum(
    aws_cli: str, tmp_path: Path, algorithm: str, name: str, mode: str
) -> None:
    body = FILES[name]
    key = f"{PREFIX}{name}"
    store = ScriptedS3()
    run = await run_cp(
        aws_cli,
        tmp_path,
        (name, f"s3://{BUCKET}/{key}", "--checksum-algorithm", algorithm),
        store,
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
    member = f"Checksum{algorithm}"
    shapes = sorted(
        (
            request.operation_model.name,
            request.params.get("PartNumber", 0),
            checksum_headers(request, algorithm),
            request.params.get(member),
        )
        for request in store.received
        if request.operation_model.name in TRANSFER_OPERATIONS
    )
    completed = [
        [
            (part["PartNumber"], part.get(member))
            for part in request.params["MultipartUpload"]["Parts"]
        ]
        for request in store.received
        if request.operation_model.name == "CompleteMultipartUpload"
    ]
    assert (shapes, completed) == expected_upload(body, algorithm), report
    # botocore never sees the algorithm, which the CRT applies, so each
    # request names botocore's own: CRC64NVME, unless it calculates none.
    assert {
        request_algorithm_features(request)
        for request in store.received
        if request.operation_model.name in TRANSFER_OPERATIONS
    } == {frozenset({"W"}) if mode != WHEN_REQUIRED else frozenset()}, report


DOWNLOADS: Final = [
    pytest.param(
        (f"s3://{BUCKET}/{PREFIX}kib.bin", "kib.bin"),
        {"kib.bin": FILES["kib.bin"]},
        id="single",
    ),
    pytest.param(
        (f"s3://{BUCKET}/{PREFIX}eleven.bin", "eleven.bin"),
        {"eleven.bin": FILES["eleven.bin"]},
        id="ranged",
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


Read = tuple[str, str, str | None]


def object_reads(run: Run) -> list[Read]:
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


def validating_reads(files: Mapping[str, bytes]) -> list[Read]:
    """The sorted reads of a validating download.

    The CRT asks for the checksum on every GET in lowercase. A single
    download's file generator asks with its HeadObject in uppercase, and
    the CRT checks a ranged object against the checksum that HeadObject
    reported. A listing names a ranged object's full-object checksum but
    not its value, so the CRT looks each listed one up with a HeadObject
    of its own first (s3transfer/crt.py
    `_configure_full_object_checksum_validation`).
    """
    reads: list[Read] = []
    for body in files.values():
        if len(body) <= 6 * MIB:
            reads.append(("GetObject", "", "enabled"))
            continue
        reads += [
            (
                "GetObject",
                f"bytes={start}-{min(start + PART_SIZE, len(body)) - 1}",
                "enabled",
            )
            for start in range(0, len(body), PART_SIZE)
        ]
        if len(files) > 1:
            reads.append(("HeadObject", "", "enabled"))
    if len(files) == 1:
        reads.append(("HeadObject", "", "ENABLED"))
    return sorted(reads, key=lambda read: (read[0], read[1], read[2] or ""))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("arguments", "files"), DOWNLOADS)
async def test_cp_download_with_checksum_mode_checks_the_checksum(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    files: dict[str, bytes],
    mode: str,
) -> None:
    store = ScriptedS3(
        OBJECTS,
        checksums={
            key: checksum("CRC64NVME", body) for key, body in OBJECTS.items()
        },
    )
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*arguments, "--checksum-mode", "ENABLED"),
        store,
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
    assert object_reads(run) == validating_reads(files), report


# One object's stored checksum is wrong. Without the mode a when_required
# download asks for no checksum, so none comes back to mismatch; with it the
# CRT fails that download, and the AWS CLI reports str(AwsCrtError) and
# leaves no partial file. The small object's GET answers with its checksum.
# A ranged GET answers with none, so the CRT checks the whole object against
# the checksum it was given: the one the command's HeadObject reported, or
# for a listed object the one its own HeadObject finds.
@pytest.mark.parametrize(
    ("arguments", "files", "bad_name"),
    [
        pytest.param(*DOWNLOADS[0].values, "kib.bin", id="single"),
        pytest.param(*DOWNLOADS[1].values, "eleven.bin", id="ranged"),
        pytest.param(*DOWNLOADS[2].values, "kib.bin", id="recursive"),
        pytest.param(
            *DOWNLOADS[2].values, "eleven.bin", id="recursive-ranged"
        ),
    ],
)
async def test_cp_download_with_checksum_mode_fails_a_mismatch(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    files: dict[str, bytes],
    bad_name: str,
) -> None:
    bad = (BUCKET, f"{PREFIX}{bad_name}")
    store = ScriptedS3(
        OBJECTS,
        checksums={
            key: WRONG_CRC64NVME if key == bad else checksum("CRC64NVME", body)
            for key, body in OBJECTS.items()
        },
    )
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*arguments, "--checksum-mode", "ENABLED"),
        store,
        environment={"AWS_RESPONSE_CHECKSUM_VALIDATION": WHEN_REQUIRED},
    )
    report = run.describe()
    assert store.failures == [], report
    failed = next(name for name in files if name.endswith(bad_name))
    shown = download_line(failed).partition(" to ")[2]
    landed = {name: body for name, body in files.items() if name != failed}
    assert (run.returncode, sorted(run.stdout.splitlines()), run.stderr) == (
        1,
        sorted(download_line(name) for name in landed),
        f"download failed: s3://{BUCKET}/{PREFIX}{bad_name} to {shown} "
        f"{MISMATCH}\n",
    ), report
    assert run.local_files == landed, report
    # The CRT looked up only what a listing named: a single ranged object
    # was checked against the checksum it was given.
    assert object_reads(run) == validating_reads(files), report


def refusal(option: str, allowed: str, received: str) -> str:
    return (
        "\naws: [ERROR]: An error occurred (ParamValidation): Expected "
        f"{option} parameter to be used with one of following path formats: "
        f"{allowed}. Instead, received {received}.\n"
    )


UPLOAD_ONLY: Final = refusal(
    "checksum-algorithm",
    "<LocalPath> <S3Uri>, <S3Uri> <S3Uri>",
    "<S3Uri> <LocalPath>",
)
DOWNLOAD_ONLY: Final = refusal(
    "checksum-mode", "<S3Uri> <LocalPath>", "<LocalPath> <S3Uri>"
)
# Each setting on the direction it does not belong to. Upstream checks it
# before the source exists, before it makes a recursive download's
# directory, and before the customer key settings.
REFUSALS: Final = [
    pytest.param(
        ("kib.bin", f"s3://{BUCKET}/up/kib.bin", "--checksum-mode", "ENABLED"),
        DOWNLOAD_ONLY,
        id="mode-upload",
    ),
    pytest.param(
        ("tree", f"s3://{BUCKET}/up/", "--recursive", "--checksum-mode", "ENABLED"),
        DOWNLOAD_ONLY,
        id="mode-recursive-upload",
    ),
    pytest.param(
        (
            "kib.bin",
            f"s3://{BUCKET}/up/kib.bin",
            "--dryrun",
            "--checksum-mode",
            "ENABLED",
        ),
        DOWNLOAD_ONLY,
        id="mode-dryrun",
    ),
    pytest.param(
        (
            "missing.bin",
            f"s3://{BUCKET}/up/missing.bin",
            "--checksum-mode",
            "ENABLED",
        ),
        DOWNLOAD_ONLY,
        id="mode-missing-source",
    ),
    pytest.param(
        (
            "kib.bin",
            f"s3://{BUCKET}/up/kib.bin",
            "--sse-c",
            "--checksum-mode",
            "ENABLED",
        ),
        DOWNLOAD_ONLY,
        id="mode-before-customer-key",
    ),
    pytest.param(
        (f"s3://{BUCKET}/{PREFIX}kib.bin", "kib.bin", "--checksum-algorithm", "CRC32"),
        UPLOAD_ONLY,
        id="algorithm-download",
    ),
    pytest.param(
        (
            f"s3://{BUCKET}/{PREFIX}",
            "missing-dir",
            "--recursive",
            "--checksum-algorithm",
            "SHA256",
        ),
        UPLOAD_ONLY,
        id="algorithm-recursive-download",
    ),
]


@pytest.mark.parametrize(("arguments", "stderr"), REFUSALS)
async def test_cp_refuses_a_checksum_setting_of_the_other_direction(
    aws_cli: str, tmp_path: Path, arguments: tuple[str, ...], stderr: str
) -> None:
    store = ScriptedS3(OBJECTS)
    local_files = {"kib.bin": FILES["kib.bin"], "tree/kib.bin": FILES["kib.bin"]}
    run = await run_cp(
        aws_cli,
        tmp_path,
        arguments,
        store,
        environment={},
        local_files=local_files,
    )
    report = run.describe()
    assert (run.returncode, run.stdout, run.stderr) == (252, "", stderr), report
    assert store.received == [], report
    # No directory is made for the refused recursive download.
    assert run.local_files == local_files, report
