from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import (
    InMemoryS3,
    ObjectKey,
    pattern_bytes,
    s3_runtime,
    write_tree,
)

# ZS3_TRANSFER_STATS is native's own diagnostic: when a command ends, it
# adds one line of `key=value` fields to stderr describing the run.
pytestmark = [pytest.mark.asyncio, pytest.mark.native_only]

BUCKET: Final = "bucket"
UPLOAD_FILE: Final = pattern_bytes("upload", 14)
LISTED_OBJECT: Final = pattern_bytes("object", 20)


async def run_with_stats(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    store: InMemoryS3,
    *,
    local_files: Mapping[str, bytes] | None = None,
    config: str = "",
) -> tuple[str, str, int]:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env["ZS3_TRANSFER_STATS"] = "1"
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments], env, cwd=work, stdin=None
        )
    return stdout.decode(), stderr.decode(), returncode


def stats_fields(stderr: str, prefix: str) -> dict[str, str]:
    """The fields of the one stats line on stderr, which starts `prefix`."""
    lines = stderr.splitlines()
    assert len(lines) == 1, stderr
    assert lines[0].startswith(prefix), stderr
    fields: dict[str, str] = {}
    for field in lines[0].removeprefix(prefix).split():
        key, _, value = field.partition("=")
        fields[key] = value
    return fields


def selected(fields: Mapping[str, str], keys: Sequence[str]) -> dict[str, str]:
    """The fields that describe the run, without its timings."""
    return {key: fields[key] for key in keys if key in fields}


# One file under max_in_flight = 1: one upload submitted and succeeded,
# never more than one in flight.
async def test_transfer_stats_describe_a_recursive_upload(
    aws_cli: str, tmp_path: Path
) -> None:
    store = InMemoryS3()
    stdout, stderr, returncode = await run_with_stats(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "inputs",
            f"s3://{BUCKET}/upload/",
            "--recursive",
            "--quiet",
        ],
        store,
        local_files={"inputs/object": UPLOAD_FILE},
        config="[default]\ns3 =\n  max_in_flight = 1\n",
    )
    assert (returncode, stdout) == (0, ""), stderr
    keys = (
        "direction",
        "submitted",
        "succeeded",
        "failed",
        "skipped",
        "in_flight_hwm",
    )
    assert selected(stats_fields(stderr, "zs3_transfer_stats "), keys) == {
        "direction": "upload",
        "submitted": "1",
        "succeeded": "1",
        "failed": "0",
        "skipped": "0",
        "in_flight_hwm": "1",
    }
    expected: dict[ObjectKey, bytes] = {(BUCKET, "upload/object"): UPLOAD_FILE}
    assert store.objects == expected
    assert store.operations() == ["PutObject"]


async def test_list_stats_describe_a_recursive_listing(
    aws_cli: str, tmp_path: Path
) -> None:
    store = InMemoryS3({(BUCKET, "object"): LISTED_OBJECT})
    stdout, stderr, returncode = await run_with_stats(
        aws_cli,
        tmp_path,
        ["s3", "ls", f"s3://{BUCKET}/object", "--recursive"],
        store,
    )
    assert (returncode, stdout) == (
        0,
        "2026-01-02 03:04:05         20 object\n",
    ), stderr
    fields = stats_fields(stderr, "zs3-list-stats: ")
    assert selected(fields, ("pages", "keys")) == {"pages": "1", "keys": "1"}
    assert store.operations() == ["ListObjectsV2"]
