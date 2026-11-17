"""Downloads under each native download setting.

The profile's `s3` block carries settings only native reads:
`download_writer`, which picks who writes each downloaded object (the CRT
itself, or the pwrite or mmap native writer), the writer's `download_writer_*`
tuning, `max_in_flight`, `io_workers`, and `download_numa_pool`, which picks
the CRT client's buffer pool. Upstream ignores them all
(transferconfig.py:107-118 reads only the keys it knows), so whatever a
valid value selects, a download must leave the same bytes and print the same
lines. An invalid value is native's own error, so those tests are
`native_only`. `target_bandwidth` is a key both read.

Each object of the ranged downloads is above the 8 MiB multipart threshold,
and one recursive object crosses the 64 MiB size below which native hands
recursive objects to the CRT; the small download is one GetObject. Which
writer and pool a setting selects is covered by the unit tests in
crates/s3/src/config/tests.rs and crates/s3/src/cp/native/crt_backend/tests.rs.
"""

import os
import platform
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from localstub import HTTPResponse

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3store import (
    InMemoryS3,
    ObjectKey,
    etag_of,
    pattern_bytes,
    read_tree,
    s3_runtime,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "settings-bucket"
MIB: Final = 1024 * 1024
SINGLE: Final = pattern_bytes("single", 9 * MIB + 1)
SMALL: Final = pattern_bytes("small", 9 * MIB + 3)
LARGE: Final = pattern_bytes("large", 64 * MIB + 5)
OBJECTS: Final = {
    (BUCKET, "single/object.bin"): SINGLE,
    (BUCKET, "tree/small.bin"): SMALL,
    (BUCKET, "tree/large.bin"): LARGE,
}
SHAPES: Final = [
    pytest.param(
        ["s3", "cp", f"s3://{BUCKET}/single/object.bin", "object.bin"],
        {"object.bin": SINGLE},
        [f"download: s3://{BUCKET}/single/object.bin to .{os.sep}object.bin"],
        id="single",
    ),
    pytest.param(
        ["s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"],
        {"tree/large.bin": LARGE, "tree/small.bin": SMALL},
        [
            f"download: s3://{BUCKET}/tree/large.bin to tree{os.sep}large.bin",
            f"download: s3://{BUCKET}/tree/small.bin to tree{os.sep}small.bin",
        ],
        id="recursive",
    ),
]
# mmap exists only where the platform maps files: Linux.
SETTINGS: Final = [
    pytest.param("download_writer = crt", id="crt-writer"),
    pytest.param("download_writer = pwrite", id="pwrite-writer"),
    pytest.param(
        "download_writer = mmap",
        id="mmap-writer",
        marks=pytest.mark.skipif(
            sys.platform != "linux", reason="mmap writes only on Linux"
        ),
    ),
    pytest.param(
        "download_writer = crt\n  download_numa_pool = disabled",
        id="crt-writer-default-pool",
    ),
    pytest.param(
        "download_writer = pwrite\n  download_numa_pool = disabled",
        id="pwrite-writer-default-pool",
    ),
]


@pytest.mark.parametrize(("arguments", "files", "lines"), SHAPES)
@pytest.mark.parametrize("settings", SETTINGS)
async def test_cp_ranged_download_is_exact_under_each_download_setting(
    aws_cli: str,
    tmp_path: Path,
    settings: str,
    arguments: list[str],
    files: dict[str, bytes],
    lines: list[str],
) -> None:
    store = InMemoryS3(OBJECTS)
    work = tmp_path / "work"
    work.mkdir()
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            f"[default]\ns3 =\n  {settings}\n", encoding="utf-8"
        )
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
        )

    assert (returncode, stderr) == (0, b""), stderr
    assert sorted(stdout.decode().splitlines()) == lines
    assert read_tree(work) == files
    assert store.failures == []
    assert {name for name, _ in store.responses} <= {
        "HeadObject",
        "GetObject",
        "ListObjectsV2",
    }
    assert all(status in (200, 206) for _, status in store.responses)


# The object every setting below downloads whole, in one GetObject.
SMALL_KEY: Final = "object"
SMALL_OBJECT: Final = pattern_bytes("object", 20)
SMALL_DOWNLOAD: Final = (
    f"download: s3://{BUCKET}/{SMALL_KEY} to .{os.sep}output\n"
)
# A host without NUMA nodes cannot place a writer on one.
WITHOUT_NUMA: Final = pytest.mark.skipif(
    not Path("/sys/devices/system/node/node0").exists(),
    reason="the host has no NUMA nodes",
)
# Native maps files and opens them for direct I/O only on Linux, and
# elsewhere fails a download whose settings require either writer.
LINUX_MMAP: Final = pytest.mark.skipif(
    sys.platform != "linux", reason="mmap writes only on Linux"
)
LINUX_DIRECT: Final = pytest.mark.skipif(
    sys.platform != "linux", reason="direct I/O writes only on Linux"
)


@dataclass(frozen=True)
class Download:
    returncode: int
    stdout: bytes
    stderr: bytes
    local_files: dict[str, bytes]
    store: InMemoryS3


async def download(
    aws_cli: str,
    tmp_path: Path,
    store: InMemoryS3,
    arguments: Sequence[str],
    settings: Sequence[str],
    environment: Mapping[str, str] | None = None,
) -> Download:
    """`aws <arguments> --no-progress` under the profile's `s3` settings."""
    work = tmp_path / "work"
    work.mkdir()
    block = "".join(f"  {setting}\n" for setting in settings)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            f"[default]\ns3 =\n{block}", encoding="utf-8"
        )
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
        )
    return Download(returncode, stdout, stderr, read_tree(work), store)


async def download_small_object(
    aws_cli: str, tmp_path: Path, settings: Sequence[str]
) -> Download:
    """`s3 cp` of the small object to `output`, under the `s3` settings."""
    return await download(
        aws_cli,
        tmp_path,
        InMemoryS3({(BUCKET, SMALL_KEY): SMALL_OBJECT}),
        ["s3", "cp", f"s3://{BUCKET}/{SMALL_KEY}", "output"],
        settings,
    )


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(["target_bandwidth = 1Gb/s"], id="target_bandwidth"),
        pytest.param(["max_in_flight = 2"], id="max_in_flight"),
        pytest.param(["io_workers = 1"], id="io_workers"),
        pytest.param(["download_writer = pwrite"], id="download_writer"),
        # A copy mode alone requires the mmap writer.
        pytest.param(
            ["download_writer_copy = memcpy"],
            id="download_writer_copy",
            marks=LINUX_MMAP,
        ),
        pytest.param(
            ["download_writer_prefault = disabled"],
            id="download_writer_prefault",
        ),
        pytest.param(
            ["download_writer_numa = disabled"], id="download_writer_numa"
        ),
        pytest.param(
            ["download_writer_numa = same-node"],
            id="download_writer_numa-same-node",
            marks=WITHOUT_NUMA,
        ),
        pytest.param(
            ["download_writer_numa = all-nodes"],
            id="download_writer_numa-all-nodes",
            marks=WITHOUT_NUMA,
        ),
        pytest.param(
            [
                "download_writer_node = auto",
                "download_writer_numa = same-node",
            ],
            id="download_writer_node",
            marks=WITHOUT_NUMA,
        ),
    ],
)
async def test_cp_small_download_is_exact_under_each_valid_setting(
    aws_cli: str, tmp_path: Path, settings: list[str]
) -> None:
    run = await download_small_object(aws_cli, tmp_path, settings)
    assert (run.returncode, run.stderr) == (0, b""), run.stderr
    assert run.stdout.decode() == SMALL_DOWNLOAD
    assert run.local_files == {"output": SMALL_OBJECT}
    assert run.store.failures == []
    assert run.store.operations() == ["HeadObject", "GetObject"]


# Native refuses an invalid value of its own settings before any request,
# naming the setting, the profile, and the values it accepts.
@pytest.mark.native_only
@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("max_in_flight", "0", "a positive integer"),
        ("io_workers", "0", "a positive integer"),
        ("download_writer", "other", "'pwrite', 'mmap', 'direct', or 'crt'"),
        ("download_writer_copy", "other", "'memcpy', 'nt', or 'rep'"),
        ("download_writer_prefault", "yes", "'enabled' or 'disabled'"),
        (
            "download_writer_numa",
            "other",
            "'disabled', 'same-node', or 'all-nodes'",
        ),
        (
            "download_writer_node",
            "bad",
            "'auto' or a node list like '0', '0,2', or '0-3'",
        ),
    ],
    ids=[
        "max_in_flight",
        "io_workers",
        "download_writer",
        "download_writer_copy",
        "download_writer_prefault",
        "download_writer_numa",
        "download_writer_node",
    ],
)
async def test_cp_download_refuses_invalid_native_setting(
    aws_cli: str, tmp_path: Path, key: str, value: str, expected: str
) -> None:
    run = await download_small_object(aws_cli, tmp_path, [f"{key} = {value}"])
    assert (run.returncode, run.stdout) == (1, b""), run.stderr
    assert run.stderr.decode() == (
        f'error: invalid s3.{key} in AWS config profile "default": '
        f"expected {expected}\n"
    )
    assert run.local_files == {}
    assert run.store.received == []


# The transfer client parses target_bandwidth as it is built, before any
# request (customizations/s3/transferconfig.py, RateConverter).
async def test_cp_download_refuses_invalid_target_bandwidth(
    aws_cli: str, tmp_path: Path
) -> None:
    run = await download_small_object(
        aws_cli, tmp_path, ["target_bandwidth = invalid"]
    )
    assert (run.returncode, run.stdout) == (255, b""), run.stderr
    assert run.stderr.decode() == (
        "\naws: [ERROR]: Invalid rate: invalid. The value must be expressed "
        "as an integer in terms of bytes per second (e.g. 10485760) or a "
        "rate in terms of bytes per second (e.g. 10MB/s or 800KB/s) or bits "
        "per second (e.g. 10Mb/s or 800Kb/s)\n"
    )
    assert run.local_files == {}
    assert run.store.received == []


# A multipart object whose last part is short of the 8 MiB part size.
UNALIGNED_SIZE: Final = 19 * MIB + 37
# The writers a download can name, each with NUMA placement off.
WRITERS: Final = [
    pytest.param("pwrite", id="pwrite"),
    pytest.param("mmap", id="mmap", marks=LINUX_MMAP),
    pytest.param("direct", id="direct", marks=LINUX_DIRECT),
]


def writer_settings(writer: str) -> list[str]:
    return [f"download_writer = {writer}", "download_writer_numa = disabled"]


def assert_ranged_gets_cover(store: InMemoryS3, key: str, body: bytes) -> None:
    """The object's GetObjects read each byte once, and any ranged one is
    conditioned on the object's ETag."""
    gets = [
        request.params
        for request in store.received
        if request.operation_model.name == "GetObject"
        and request.params["Key"] == key
    ]
    if len(gets) == 1 and "Range" not in gets[0]:
        return
    etag = etag_of(body)
    next_byte = 0
    for params in sorted(gets, key=lambda get: byte_range(get)[0]):
        start, end = byte_range(params)
        assert start == next_byte, gets
        next_byte = min(end, len(body) - 1) + 1
        assert params.get("IfMatch") == etag, params
    assert next_byte == len(body), gets


def byte_range(params: Mapping[str, object]) -> tuple[int, int]:
    value = params.get("Range")
    assert isinstance(value, str), params
    first, _, last = value.removeprefix("bytes=").partition("-")
    return int(first), int(last)


@pytest.mark.parametrize("writer", WRITERS)
@pytest.mark.parametrize(
    "size", [0, 20, UNALIGNED_SIZE], ids=["empty", "small", "unaligned"]
)
async def test_cp_download_is_exact_under_each_writer(
    aws_cli: str, tmp_path: Path, writer: str, size: int
) -> None:
    body = pattern_bytes("object", size)
    run = await download(
        aws_cli,
        tmp_path,
        InMemoryS3({(BUCKET, "object"): body}),
        ["s3", "cp", f"s3://{BUCKET}/object", "output"],
        writer_settings(writer),
    )
    assert (run.returncode, run.stderr) == (0, b""), run.stderr
    assert run.stdout.decode() == (
        f"download: s3://{BUCKET}/object to .{os.sep}output\n"
    )
    assert run.local_files == {"output": body}
    assert run.store.failures == []
    assert set(run.store.operations()) == {"HeadObject", "GetObject"}
    assert_ranged_gets_cover(run.store, "object", body)


def boundary_objects() -> dict[str, bytes]:
    """Objects on either side of the 64 MiB size below which native hands a
    recursive download's object to the CRT, and two small ones."""
    boundary = 64 * MIB
    pattern = pattern_bytes("boundary", boundary + 37)
    return {
        "empty": b"",
        "object": pattern_bytes("object", 20),
        "below-64m": pattern[: boundary - 1],
        "at-64m": pattern[:boundary],
        "above-64m": pattern,
    }


def boundary_settings(writer: str) -> list[str]:
    return ["max_in_flight = 4", "io_workers = 2", *writer_settings(writer)]


@pytest.mark.parametrize(
    "settings,environment",
    [
        pytest.param(["max_in_flight = 4"], {}, id="auto"),
        pytest.param(boundary_settings("pwrite"), {}, id="pwrite"),
        pytest.param(
            boundary_settings("mmap"), {}, id="mmap", marks=LINUX_MMAP
        ),
        pytest.param(
            boundary_settings("direct"), {}, id="direct", marks=LINUX_DIRECT
        ),
        pytest.param(
            boundary_settings("pwrite"),
            {"AWS_CRT_S3_MEMORY_LIMIT_IN_GIB": "1"},
            id="pwrite-memory-limit",
        ),
    ],
)
async def test_cp_recursive_download_is_exact_across_the_crt_boundary(
    aws_cli: str,
    tmp_path: Path,
    settings: list[str],
    environment: dict[str, str],
) -> None:
    objects = boundary_objects()
    run = await download(
        aws_cli,
        tmp_path,
        InMemoryS3(
            {(BUCKET, f"tree/{name}"): body for name, body in objects.items()}
        ),
        ["s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"],
        settings,
        environment,
    )
    assert (run.returncode, run.stderr) == (0, b""), run.stderr
    assert sorted(run.stdout.decode().splitlines()) == sorted(
        f"download: s3://{BUCKET}/tree/{name} to tree{os.sep}{name}"
        for name in objects
    )
    assert run.local_files == {
        f"tree/{name}": body for name, body in objects.items()
    }
    assert run.store.failures == []
    for name, body in objects.items():
        assert_ranged_gets_cover(run.store, f"tree/{name}", body)


# The fast copy modes exist only in x86_64 builds (FAST_MODES_AVAILABLE in
# crates/s3), which reject them elsewhere.
X86_64_ONLY: Final = pytest.mark.skipif(
    platform.machine().lower() not in ("x86_64", "amd64"),
    reason="the nt and rep copy modes exist only on x86_64",
)


@LINUX_MMAP
@pytest.mark.parametrize("prefault", ["enabled", "disabled"])
@pytest.mark.parametrize(
    "copy",
    [
        pytest.param("memcpy", id="memcpy"),
        pytest.param("nt", id="nt", marks=X86_64_ONLY),
        pytest.param("rep", id="rep", marks=X86_64_ONLY),
    ],
)
async def test_cp_recursive_mmap_download_is_exact_under_each_copy_mode(
    aws_cli: str, tmp_path: Path, copy: str, prefault: str
) -> None:
    objects = {
        "empty": b"",
        "object": pattern_bytes("object", UNALIGNED_SIZE),
    }
    run = await download(
        aws_cli,
        tmp_path,
        InMemoryS3(
            {(BUCKET, f"tree/{name}"): body for name, body in objects.items()}
        ),
        ["s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"],
        [
            *writer_settings("mmap"),
            f"download_writer_copy = {copy}",
            f"download_writer_prefault = {prefault}",
        ],
    )
    assert (run.returncode, run.stderr) == (0, b""), run.stderr
    assert run.local_files == {
        f"tree/{name}": body for name, body in objects.items()
    }
    assert run.store.failures == []
    assert_ranged_gets_cover(run.store, "tree/object", objects["object"])


class DenyingS3(InMemoryS3):
    """InMemoryS3 that denies every GetObject of `denied`."""

    def __init__(
        self, objects: Mapping[ObjectKey, bytes], denied: str
    ) -> None:
        super().__init__(objects)
        self.denied = denied

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        params = reconstructed.params
        if (
            reconstructed.operation_model.name == "GetObject"
            and params["Key"] == self.denied
        ):
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        return super().dispatch(reconstructed)


# One denied object fails the recursive download under a native writer
# while the other objects are written.
async def test_cp_recursive_writer_download_reports_one_denied_object(
    aws_cli: str, tmp_path: Path
) -> None:
    store = DenyingS3(
        {
            (BUCKET, "tree/empty"): b"",
            (BUCKET, "tree/object"): SMALL_OBJECT,
        },
        denied="tree/object",
    )
    run = await download(
        aws_cli,
        tmp_path,
        store,
        ["s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"],
        ["max_in_flight = 1", *writer_settings("pwrite")],
    )
    assert (run.returncode, run.stdout.decode(), run.stderr.decode()) == (
        1,
        f"download: s3://{BUCKET}/tree/empty to tree{os.sep}empty\n",
        f"download failed: s3://{BUCKET}/tree/object to tree{os.sep}object "
        "An error occurred (AccessDenied) when calling the GetObject "
        "operation: Access Denied\n",
    )
    assert run.local_files == {"tree/empty": b""}
    assert run.store.failures == []
