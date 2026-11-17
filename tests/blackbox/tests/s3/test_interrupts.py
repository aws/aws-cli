import asyncio
import os
import signal
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, urlsplit

import pytest
from localstub import HTTPResponse, RecordedHTTPRequest, ResponderContext
from localstub.server import AbortTransmission, TransmissionStrategy, Writer

from harness_plugin import child_environment
from s3store import (
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

# On Windows, Ctrl-C reaches a console process as a console event rather
# than SIGINT.
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(os.name == "nt", reason="Ctrl-C is a console event"),
]

BUCKET: Final = "bucket"
OBJECT: Final = pattern_bytes("object", 20)
UPLOAD_FILE: Final = pattern_bytes("upload", 19 * 1024 * 1024 + 37)
TIMEOUT_SECONDS: Final = 60


def is_object_get(request: RecordedHTTPRequest) -> bool:
    return request.method == "GET" and urlsplit(
        request.effective_path
    ).path.endswith("/object")


def is_listing(request: RecordedHTTPRequest) -> bool:
    query = parse_qs(urlsplit(request.effective_path).query)
    return request.method == "GET" and "list-type" in query


def is_upload_start(request: RecordedHTTPRequest) -> bool:
    query = parse_qs(
        urlsplit(request.effective_path).query, keep_blank_values=True
    )
    return request.method == "POST" and "uploads" in query


class StallingS3(InMemoryS3):
    """InMemoryS3 that holds the first request `stalls` picks until the
    test releases it: before its response headers, or, with
    `HeldBody`, before its body. `held` is set once the request is held.
    """

    def __init__(
        self,
        objects: Mapping[ObjectKey, bytes],
        stalls: Callable[[RecordedHTTPRequest], bool],
        *,
        before_headers: bool,
    ) -> None:
        super().__init__(objects)
        self.stalls = stalls
        self.before_headers = before_headers
        self.held = asyncio.Event()
        self.released = asyncio.Event()
        self.held_body: bytes | None = None

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        response = await super().respond(context)
        first = not self.held.is_set() and self.held_body is None
        if first and self.stalls(context.request):
            if self.before_headers:
                self.held.set()
                await self.released.wait()
            elif isinstance(response.body, bytes):
                self.held_body = response.body
        return response

    async def hold(self) -> None:
        self.held.set()
        await self.released.wait()


class HeldBody(TransmissionStrategy):
    """Sends a held response's headers, then holds its body."""

    def __init__(self, store: StallingS3) -> None:
        self._store = store

    async def write_body(
        self, writer: Writer, body: bytes
    ) -> AbortTransmission | None:
        if body and body == self._store.held_body:
            await writer.drain()
            await self._store.hold()
        writer.write(body)
        await writer.drain()
        return None


@dataclass(frozen=True)
class Interrupted:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: StallingS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )


async def interrupt(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    store: StallingS3,
    *,
    interrupts: int = 1,
    local_files: Mapping[str, bytes] | None = None,
) -> Interrupted:
    """Run `aws <arguments>` and press Ctrl-C `interrupts` times once the
    store holds its request. A held body needs the bucket's plain-HTTP
    address: the TLS intercept proxy relays a response only once it has
    read all of it."""
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (server, env):
        endpoint: list[str] = []
        if not store.before_headers:
            server.set_transmission_strategy(HeldBody(store))
            endpoint = ["--endpoint-url", server.url.rstrip("/")]
            env["NO_PROXY"] = "127.0.0.1"
        process = await asyncio.create_subprocess_exec(
            aws_cli,
            *arguments,
            *endpoint,
            env=child_environment(env),
            cwd=work,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        output = asyncio.ensure_future(process.communicate())
        try:
            await asyncio.wait_for(store.held.wait(), TIMEOUT_SECONDS)
            for _ in range(interrupts):
                if process.returncode is not None:
                    break
                process.send_signal(signal.SIGINT)
                await asyncio.wait({output}, timeout=0.5)
            stdout, stderr = await asyncio.wait_for(output, TIMEOUT_SECONDS)
        finally:
            store.released.set()
            if process.returncode is None:
                process.kill()
            await process.wait()
    assert process.returncode is not None
    return Interrupted(
        returncode=process.returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


# The CRT client fails a transfer Ctrl-C cancels with its own error
# (s3transfer/crt.py), and the CLI exits 1.
CANCELLED: Final = "AWS_ERROR_S3_CANCELED: Request successfully cancelled\n"


# Ctrl-C cancels a download in flight and leaves no partial file, whether
# the object's response is held before its headers or before its body.
@pytest.mark.parametrize(
    "before_headers", [True, False], ids=["before-headers", "before-body"]
)
@pytest.mark.parametrize(
    "arguments,shown",
    [
        pytest.param(
            ("s3", "cp", f"s3://{BUCKET}/object", "output", "--no-progress"),
            f".{os.sep}output",
            id="single",
        ),
        pytest.param(
            (
                "s3",
                "cp",
                f"s3://{BUCKET}/",
                "output",
                "--recursive",
                "--no-progress",
            ),
            f"output{os.sep}object",
            id="recursive",
        ),
    ],
)
async def test_ctrl_c_cancels_a_download_in_flight(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    shown: str,
    before_headers: bool,
) -> None:
    store = StallingS3(
        {(BUCKET, "object"): OBJECT},
        is_object_get,
        before_headers=before_headers,
    )
    run = await interrupt(aws_cli, tmp_path, arguments, store)
    report = run.describe()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"download failed: s3://{BUCKET}/object to {shown} {CANCELLED}",
    ), report
    assert run.local_files == {}, report


# Ctrl-C while `s3 ls` waits for its page ends the command as the shell
# expects of SIGINT: a newline after any partial output, and status 130
# (clidriver.py, KeyboardInterrupt).
async def test_ctrl_c_ends_a_listing_in_flight(
    aws_cli: str, tmp_path: Path
) -> None:
    store = StallingS3(
        {(BUCKET, "object"): OBJECT}, is_listing, before_headers=True
    )
    run = await interrupt(aws_cli, tmp_path, ("s3", "ls", BUCKET), store)
    report = run.describe()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (130, "\n", ""), report


# Ctrl-C, pressed again while the CLI still runs, ends a multipart upload
# whose CreateMultipartUpload has not been answered, and nothing is stored.
async def test_ctrl_c_ends_an_upload_waiting_to_start(
    aws_cli: str, tmp_path: Path
) -> None:
    store = StallingS3({}, is_upload_start, before_headers=True)
    run = await interrupt(
        aws_cli,
        tmp_path,
        ("s3", "cp", "input", f"s3://{BUCKET}/new", "--no-progress"),
        store,
        interrupts=2,
        local_files={"input": UPLOAD_FILE},
    )
    report = run.describe()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"upload failed: .{os.sep}input to s3://{BUCKET}/new {CANCELLED}",
    ), report
    assert store.objects == {}, report
