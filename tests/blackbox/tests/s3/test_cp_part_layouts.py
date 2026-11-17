"""The requests `s3 cp` splits a transfer into: its part layout.

Each test copies objects on either side of a part size and multipart
threshold, alone and in a recursive copy, against the in-memory bucket of
s3store.py, and asserts the requests the bucket answered: each download's
GetObject ranges and each upload's PutObject or UploadPart sizes, along
with the result lines and the bytes moved.

A configured multipart_chunksize and multipart_threshold fix the layout
(customizations/s3/factory.py:418-430). Without them, `auto` gives a host
the CRT is not tuned for the classic client's 8 MiB defaults
(factory.py:476-479, transferconfig.py DEFAULTS), and leaves a tuned host,
or a profile that prefers `crt`, to the CRT client's own sizes: dynamic
download ranges, and uploads in 8 MiB parts above an 8 MiB threshold, the
larger of its default part and 5 MiB (aws-c-s3 s3_client.c).
"""

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import awscrt.s3
import pytest

from credhelpers import run_command
from s3store import (
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
MIB: Final = 1024 * 1024
PREFIX: Final = "layout/"
SIZES: Final[Mapping[str, int]] = {
    "kib.bin": 1024,
    "six.bin": 6 * MIB,
    "six-plus-one.bin": 6 * MIB + 1,
    "seventeen.bin": 17 * MIB,
}
FILES: Final[Mapping[str, bytes]] = {
    name: pattern_bytes(name, size) for name, size in SIZES.items()
}
OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, f"{PREFIX}{name}"): body for name, body in FILES.items()
}
CRT_BLOCK: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
CHUNKED_CONFIG: Final = (
    CRT_BLOCK + "  multipart_chunksize = 5MB\n  multipart_threshold = 6MB\n"
)
# Whether `auto` keeps the CRT client's own sizes on this host.
TUNED_HOST: Final = awscrt.s3.is_optimized_for_system()

# A download's GetObject Range headers in start order; None for one
# unranged request.
GetLayout = tuple[str | None, ...]
# An upload's PutObject body size, or its UploadPart sizes in part order.
UploadLayout = tuple[str, tuple[int, ...]]


def ranges(size: int, part_size: int) -> GetLayout:
    return tuple(
        f"bytes={start}-{min(start + part_size, size) - 1}"
        for start in range(0, size, part_size)
    )


def parts(size: int, part_size: int) -> tuple[int, ...]:
    return tuple(
        min(part_size, size - start) for start in range(0, size, part_size)
    )


@dataclass(frozen=True)
class Layout:
    name: str
    config: str
    # The fixed download part size and threshold, or None where the CRT
    # client chooses the ranges.
    download: tuple[int, int] | None
    # The upload part size and threshold.
    upload: tuple[int, int]

    def expected_get(self, size: int) -> GetLayout | None:
        if self.download is None:
            return None
        part_size, threshold = self.download
        return (None,) if size <= threshold else ranges(size, part_size)

    def expected_upload(self, size: int) -> UploadLayout:
        part_size, threshold = self.upload
        if size <= threshold:
            return ("PutObject", (size,))
        return ("UploadPart", parts(size, part_size))


EIGHT: Final = (8 * MIB, 8 * MIB)
LAYOUTS: Final = [
    pytest.param(
        Layout(
            "chunked", CHUNKED_CONFIG, (5 * MIB, 6 * MIB), (5 * MIB, 6 * MIB)
        ),
        id="crt-5mb-parts-6mb-threshold",
    ),
    pytest.param(Layout("crt", CRT_BLOCK, None, EIGHT), id="crt-defaults"),
    pytest.param(
        Layout("auto", "", None if TUNED_HOST else EIGHT, EIGHT),
        id="auto-defaults",
    ),
]


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: InMemoryS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def get_layout(self, key: str) -> GetLayout:
        found: list[str | None] = [
            request.params.get("Range")
            for request in self.store.received
            if request.operation_model.name == "GetObject"
            and request.params.get("Key") == key
        ]

        def start(byte_range: str | None) -> int:
            if byte_range is None:
                return -1
            return int(byte_range.partition("=")[2].partition("-")[0])

        return tuple(sorted(found, key=start))

    def upload_layout(self, key: str) -> UploadLayout:
        puts = []
        uploaded: list[tuple[int, int]] = []
        for request in self.store.received:
            if request.params.get("Key") != key:
                continue
            body = request.params.get("Body", b"")
            if request.operation_model.name == "PutObject":
                puts.append(len(body))
            elif request.operation_model.name == "UploadPart":
                uploaded.append((request.params["PartNumber"], len(body)))
        if puts:
            return ("PutObject", tuple(puts))
        return ("UploadPart", tuple(size for _, size in sorted(uploaded)))


def coverage_errors(layout: GetLayout, size: int) -> list[str]:
    """Whether the ranges read the object once, in order, end to end.

    A size-discovery GET may ask for a whole part before the client knows
    the object's length; S3 cuts its response at the last byte.
    """
    if layout == (None,):
        return []
    next_byte = 0
    for byte_range in layout:
        if byte_range is None or not byte_range.startswith("bytes="):
            return [f"not a byte range: {byte_range!r} in {layout}"]
        first, _, last = byte_range.removeprefix("bytes=").partition("-")
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
        if start != next_byte or not start <= end < size:
            return [f"ranges do not tile {size} bytes: {layout}"]
        next_byte = end + 1
    if next_byte != size:
        return [f"ranges stop short of {size} bytes: {layout}"]
    return []


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    config: str,
    *,
    objects: Mapping[ObjectKey, bytes] | None = None,
    local_files: Mapping[str, bytes] | None = None,
) -> Run:
    work = tmp_path / "work"
    work.mkdir(parents=True)
    write_tree(work, local_files or {})
    store = InMemoryS3(objects)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
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


def assert_moved(run: Run, lines: list[str]) -> None:
    report = run.describe()
    assert run.store.failures == [], report
    # Concurrent transfers finish, and print, in any order.
    assert (run.returncode, sorted(run.stdout.splitlines()), run.stderr) == (
        0,
        sorted(lines),
        "",
    ), report


def assert_downloaded(run: Run, layout: Layout, name: str) -> None:
    report = run.describe()
    key = f"{PREFIX}{name}"
    got = run.get_layout(key)
    assert coverage_errors(got, SIZES[name]) == [], report
    expected = layout.expected_get(SIZES[name])
    if expected is not None:
        assert got == expected, report


@pytest.mark.parametrize("layout", LAYOUTS)
async def test_cp_single_transfers_split_into_parts(
    aws_cli: str, tmp_path: Path, layout: Layout
) -> None:
    for name, body in FILES.items():
        key = f"{PREFIX}{name}"
        run = await run_cp(
            aws_cli,
            tmp_path / f"download-{name}",
            (f"s3://{BUCKET}/{key}", name),
            layout.config,
            objects={(BUCKET, key): body},
        )
        assert_moved(
            run, [f"download: s3://{BUCKET}/{key} to .{os.sep}{name}"]
        )
        assert run.local_files == {name: body}, run.describe()
        assert_downloaded(run, layout, name)

        run = await run_cp(
            aws_cli,
            tmp_path / f"upload-{name}",
            (name, f"s3://{BUCKET}/{key}"),
            layout.config,
            local_files={name: body},
        )
        assert_moved(run, [f"upload: .{os.sep}{name} to s3://{BUCKET}/{key}"])
        assert run.store.objects == {(BUCKET, key): body}, run.describe()
        assert run.upload_layout(key) == layout.expected_upload(SIZES[name]), (
            run.describe()
        )


@pytest.mark.parametrize("layout", LAYOUTS)
async def test_cp_recursive_transfers_split_into_parts(
    aws_cli: str, tmp_path: Path, layout: Layout
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path / "download",
        (f"s3://{BUCKET}/{PREFIX}", "down", "--recursive"),
        layout.config,
        objects=OBJECTS,
    )
    assert_moved(
        run,
        [
            f"download: s3://{BUCKET}/{PREFIX}{name} to down{os.sep}{name}"
            for name in FILES
        ],
    )
    assert run.local_files == {
        f"down/{name}": body for name, body in FILES.items()
    }, run.describe()
    for name in FILES:
        assert_downloaded(run, layout, name)

    run = await run_cp(
        aws_cli,
        tmp_path / "upload",
        ("up", f"s3://{BUCKET}/{PREFIX}", "--recursive"),
        layout.config,
        local_files={f"up/{name}": body for name, body in FILES.items()},
    )
    assert_moved(
        run,
        [
            f"upload: up{os.sep}{name} to s3://{BUCKET}/{PREFIX}{name}"
            for name in FILES
        ],
    )
    assert run.store.objects == OBJECTS, run.describe()
    for name, size in SIZES.items():
        assert run.upload_layout(f"{PREFIX}{name}") == layout.expected_upload(
            size
        ), run.describe()


# direct_io with a part size that is no multiple of the page size: the CRT
# client, which gets it as a file I/O option (factory.py:405-413), writes
# such parts buffered. One recursive object passes 64 MiB.
UNALIGNED_DIRECT_CONFIG: Final = (
    CRT_BLOCK + "  direct_io = true\n  multipart_chunksize = 5000000\n"
)
DIRECT_FILES: Final[Mapping[str, bytes]] = {
    name: pattern_bytes(name, size)
    for name, size in {
        "seventeen-plus-one.bin": 17 * MIB + 1,
        "sixty-four-plus-three.bin": 64 * MIB + 3,
    }.items()
}
DIRECT_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, f"direct/{name}"): body for name, body in DIRECT_FILES.items()
}


@pytest.mark.parametrize(
    ("arguments", "files", "lines"),
    [
        pytest.param(
            (
                f"s3://{BUCKET}/direct/seventeen-plus-one.bin",
                "seventeen-plus-one.bin",
            ),
            {"seventeen-plus-one.bin": DIRECT_FILES["seventeen-plus-one.bin"]},
            [
                f"download: s3://{BUCKET}/direct/seventeen-plus-one.bin to "
                f".{os.sep}seventeen-plus-one.bin"
            ],
            id="single",
        ),
        pytest.param(
            (f"s3://{BUCKET}/direct/", "down", "--recursive"),
            {f"down/{name}": body for name, body in DIRECT_FILES.items()},
            [
                f"download: s3://{BUCKET}/direct/{name} to down{os.sep}{name}"
                for name in DIRECT_FILES
            ],
            id="recursive",
        ),
    ],
)
async def test_cp_direct_io_with_unaligned_parts_downloads_exactly(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    files: dict[str, bytes],
    lines: list[str],
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        arguments,
        UNALIGNED_DIRECT_CONFIG,
        objects=DIRECT_OBJECTS,
    )
    assert_moved(run, lines)
    assert run.local_files == files, run.describe()
    for local in files:
        name = local.removeprefix("down/")
        got = run.get_layout(f"direct/{name}")
        assert coverage_errors(got, len(DIRECT_FILES[name])) == [], (
            run.describe()
        )
