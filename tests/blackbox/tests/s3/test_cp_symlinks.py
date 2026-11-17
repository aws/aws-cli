"""`s3 cp` downloads onto symlinks (upstream
tests/functional/s3/test_cp_command.py, TestCPDownloadNoFollowSymlinks).

With --no-follow-symlinks a download whose destination is a symlink, or
whose key maps through one, is skipped: writing it would follow the link.
By default the download replaces the link and leaves its target alone.
"""

import os
import platform
from pathlib import Path

import pytest

from apihelpers import ApiSession
from s3params import head_object_response, list_objects_response

pytestmark = [
    pytest.mark.asyncio,
    # As upstream's class: making a symlink on Windows takes a privilege.
    pytest.mark.skipif(
        platform.system() not in ("Darwin", "Linux"),
        reason="Symlink tests only supported on mac/linux",
    ),
]


def link_to_target(directory: Path) -> tuple[Path, Path]:
    target = directory / "target.txt"
    target.write_text("original")
    link = directory / "link.txt"
    os.symlink(target, link)
    return target, link


async def test_skips_download_onto_symlink(transfer_api: ApiSession) -> None:
    target, link = link_to_target(transfer_api.cwd)
    run = await transfer_api.run(
        ["s3", "cp", "s3://bucket/key.txt", str(link), "--no-follow-symlinks"],
        replies=[head_object_response()],
    )
    assert run.operations == ["HeadObject"], run.describe()
    assert link.is_symlink()
    assert target.read_text() == "original"


async def test_skips_download_onto_symlink_named_by_key(
    transfer_api: ApiSession,
) -> None:
    root = transfer_api.cwd
    os.symlink(root, root / "sub")
    run = await transfer_api.run(
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(root),
            "--recursive",
            "--no-follow-symlinks",
        ],
        replies=[list_objects_response(["sub/key.txt"])],
    )
    assert run.operations == ["ListObjectsV2"], run.describe()
    assert sorted(path.name for path in root.iterdir()) == ["sub"]


async def test_replaces_symlink_by_default(transfer_api: ApiSession) -> None:
    target, link = link_to_target(transfer_api.cwd)
    # The HEAD's ContentLength is the 8-byte body served.
    head = head_object_response(ContentLength=8)
    run = await transfer_api.run(
        ["s3", "cp", "s3://bucket/key.txt", str(link)],
        replies=[head, {"ETag": '"foo-1"', "Body": b"injected"}],
    )
    # The HEAD reports no full-object checksum, so the CRT client sends no
    # HEAD of its own before its GET.
    assert run.operations == ["HeadObject", "GetObject"], run.describe()
    assert not link.is_symlink()
    assert link.read_bytes() == b"injected"
    assert target.read_text() == "original"
