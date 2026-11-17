import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse

from s3helpers import completion_lines
from tests.blackbox.utils import (
    list_objects_xml,
    put_object_response,
    run_cli,
    xml_response,
)

NAMES = ["a.txt", "ignored.bin", "nested/b.txt", "nested/c.bin"]


def write_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    for name in NAMES:
        (source / name).write_text(name)
    return source


async def upload_filtered(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    source: Path,
    command: list[str],
    listing: list[HTTPResponse],
    flags: list[str],
    selected: list[str],
) -> bytes:
    server, env = transfer_runtime
    server.set_response_sequence(listing)
    server.handler = lambda context: put_object_response()
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            command[0],
            str(source),
            "s3://bucket/prefix/",
            "--no-progress",
            *command[1:],
            *flags,
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    uploads = [r for r in server.requests if r.method == "PUT"]
    assert sorted(
        unquote(urlsplit(r.effective_path).path) for r in uploads
    ) == [f"/prefix/{name}" for name in selected]
    assert len(server.requests) == len(selected) + len(listing)
    return stdout


def completion(verb: str, source: Path, name: str) -> str:
    local = os.path.relpath(source / name)
    return f"{verb}: {local} to s3://bucket/prefix/{name}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command", "listing"),
    [
        pytest.param(["cp", "--recursive"], [], id="cp"),
        # Sync lists the destination before it uploads.
        pytest.param(["sync"], [xml_response(list_objects_xml())], id="sync"),
    ],
)
async def test_filters_upload_sends_selected_files_and_keeps_all_files(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    filter_case: tuple[list[str], list[str]],
    command: list[str],
    listing: list[HTTPResponse],
) -> None:
    flags, selected = filter_case
    source = write_source(tmp_path)
    stdout = await upload_filtered(
        aws_cli, transfer_runtime, source, command, listing, flags, selected
    )
    assert sorted(completion_lines(stdout)) == sorted(
        completion("upload", source, name) for name in selected
    )
    assert [(source / name).read_text() for name in NAMES] == NAMES


@pytest.mark.asyncio
async def test_filters_recursive_mv_moves_only_selected_files(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    filter_case: tuple[list[str], list[str]],
) -> None:
    flags, selected = filter_case
    source = write_source(tmp_path)
    stdout = await upload_filtered(
        aws_cli,
        transfer_runtime,
        source,
        ["mv", "--recursive"],
        [],
        flags,
        selected,
    )
    assert sorted(completion_lines(stdout)) == sorted(
        completion("move", source, name) for name in selected
    )
    remaining = [name for name in NAMES if name not in selected]
    assert [name for name in selected if (source / name).exists()] == []
    assert [(source / name).read_text() for name in remaining] == remaining
