import asyncio
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse, ResponderContext

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3helpers import completion_lines, user_agent_parts
from s3store import (
    LAST_MODIFIED,
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    without_cwd,
    write_tree,
)
from tests.blackbox.utils import (
    list_objects_xml,
    run_cli,
    xml_response,
)


async def sync_delete_txt_only(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    destination: Path,
    flags: list[str],
) -> bytes:
    server, env = transfer_runtime
    server.set_response_sequence([xml_response(list_objects_xml())])
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "sync",
            "s3://bucket/",
            str(destination),
            "--delete",
            "--exclude",
            "*",
            "--include",
            "*.txt",
            "--no-progress",
            *flags,
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["GET"]
    return stdout


def write_destination(tmp_path: Path) -> tuple[Path, Path, Path]:
    destination = tmp_path / "destination"
    destination.mkdir()
    kept = destination / "keep.bin"
    removed = destination / "remove.txt"
    kept.write_bytes(b"keep")
    removed.write_bytes(b"remove")
    return destination, kept, removed


@pytest.mark.asyncio
async def test_sync_delete_removes_included_file_and_keeps_excluded(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    destination, kept, removed = write_destination(tmp_path)
    stdout = await sync_delete_txt_only(
        aws_cli, transfer_runtime, destination, []
    )
    assert kept.read_bytes() == b"keep"
    assert not removed.exists()
    assert completion_lines(stdout) == [
        f"delete: {os.path.relpath(removed)}"
    ]


@pytest.mark.asyncio
async def test_sync_delete_dryrun_reports_delete_and_keeps_all_files(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    destination, kept, removed = write_destination(tmp_path)
    stdout = await sync_delete_txt_only(
        aws_cli, transfer_runtime, destination, ["--dryrun"]
    )
    assert kept.read_bytes() == b"keep"
    assert removed.read_bytes() == b"remove"
    assert completion_lines(stdout) == [
        f"(dryrun) delete: {os.path.relpath(removed)}"
    ]


# The default `s3 sync`, with no option: a recursive transfer of each source
# file or object the destination lacks or holds in another version. Upstream
# lists both sides in key order and pairs their entries by the name below
# each root (comparator.py:35-151); a pair is transferred when the sizes
# differ or the local side is the newer (syncstrategy/base.py:233-262), and
# an entry only the destination has is left alone.

BUCKET: Final = "bucket"
# The LastModified of every object the store holds, unless a test gives it
# another, in epoch seconds.
STORE_TIME: Final = int(LAST_MODIFIED.timestamp())
SECOND: Final = 1_000_000_000
HOUR: Final = 3600 * SECOND
ACCESS_DENIED: Final = (
    "An error occurred (AccessDenied) when calling the {operation} "
    "operation: Access Denied"
)
# A segment of the progress line the default printer redraws.
PROGRESS_SEGMENT: Final = re.compile(r"Completed .* file\(s\) remaining.*")
# Feature ids of the User-Agent's m/ component (botocore/useragent.py).
PAGINATOR: Final = "C"
RETRY_STANDARD: Final = "E"
S3_TRANSFER: Final = "G"
REQUEST_CRC64: Final = "W"
REQUEST_WHEN_SUPPORTED: Final = "Z"
RESPONSE_WHEN_SUPPORTED: Final = "b"
CRT_AUTO: Final = "Ag"

UPLOAD_TREE: Final[dict[str, bytes]] = {
    "src/one.txt": pattern_bytes("one", 400),
    "src/two.txt": pattern_bytes("two", 1200),
    "src/sub/three.txt": pattern_bytes("three", 50),
}
# The objects under "tree/", with the folder markers the S3 console creates
# for the prefix and a subfolder: zero-size keys ending in "/".
TREE: Final[dict[str, bytes]] = {
    "tree/": b"",
    "tree/a.txt": pattern_bytes("tree a", 100),
    "tree/b.txt": pattern_bytes("tree b", 1500),
    "tree/folder/": b"",
    "tree/nested/c.txt": pattern_bytes("tree c", 700),
}
# Keys a sync of "up/" or "tree/" leaves alone, two sharing their first
# characters.
OUTSIDE: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "upstairs.txt"): pattern_bytes("upstairs", 10),
    (BUCKET, "treehouse.txt"): pattern_bytes("treehouse", 10),
    (BUCKET, "other/d.txt"): pattern_bytes("other d", 20),
}
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    **{(BUCKET, key): body for key, body in TREE.items()},
    **OUTSIDE,
}
# Same-size bodies that differ, so the content shows which side won.
REMOTE: Final = pattern_bytes("remote", 300)
CHANGED: Final = pattern_bytes("changed", 300)
RESIZED: Final = pattern_bytes("changed", 301)


@dataclass(frozen=True)
class Pair:
    """A name both sides hold: the local file, its mtime as an offset from
    the object's LastModified in nanoseconds, and the object."""

    local: bytes
    offset: int
    remote: bytes
    # Whether the source side replaces the destination's, which upload and
    # download decide alike: the local side is newer to the microsecond
    # Python rounds its float mtime to (utils.py:253-276), or the sizes
    # differ.
    transfers: bool


PAIRS: Final[dict[str, Pair]] = {
    "same.txt": Pair(REMOTE, -HOUR, REMOTE, transfers=False),
    "older.txt": Pair(CHANGED, -HOUR, REMOTE, transfers=False),
    "same-time.txt": Pair(CHANGED, 0, REMOTE, transfers=False),
    "newer.txt": Pair(CHANGED, HOUR, REMOTE, transfers=True),
    "resized.txt": Pair(RESIZED, -HOUR, REMOTE, transfers=True),
    "half-second-newer.txt": Pair(
        CHANGED, SECOND // 2, REMOTE, transfers=True
    ),
    "half-second-older.txt": Pair(
        CHANGED, -SECOND // 2, REMOTE, transfers=False
    ),
    # 400ns rounds to the object's microsecond and 600ns past it.
    "rounds-to-same.txt": Pair(CHANGED, 400, REMOTE, transfers=False),
    "rounds-to-newer.txt": Pair(CHANGED, 600, REMOTE, transfers=True),
    "sub/same.txt": Pair(REMOTE, -HOUR, REMOTE, transfers=False),
    "sub/newer.txt": Pair(CHANGED, HOUR, REMOTE, transfers=True),
}
# More names than one listing page holds at ListObjectsV2's default MaxKeys,
# and one name in each page that differs.
PAGED: Final = [f"f{index:04d}.txt" for index in range(1001)]
PAGED_CHANGED: Final = ["f0500.txt", "f1000.txt"]
# Names whose key order is not the order of their paths' components: "-"
# and "." sort before "/", and "0" after it.
ORDERED: Final = [
    "a-b.txt",
    "a.txt",
    "a/b.txt",
    "a/c/d.txt",
    "a0.txt",
    "ab/x.txt",
    "b.txt",
    "z/ü.txt",
    "é.txt",
]


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    store: InMemoryS3
    # The requests this run sent, in arrival order.
    received: list[ReconstructedRequest]

    def report(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"requests: {self.requests()}\n"
            f"failures: {self.store.failures}\n"
        )

    def requests(self) -> list[tuple[str, str]]:
        """Each request's operation and key, or a listing's prefix."""
        return [
            (
                request.operation_model.name,
                request.params.get("Key", request.params.get("Prefix", "")),
            )
            for request in self.received
        ]

    def keys(self, operation: str) -> list[str]:
        """The keys `operation` named, sorted: transfers run concurrently."""
        return sorted(key for name, key in self.requests() if name == operation)

    def stdout_lines(self) -> list[str]:
        return result_lines(self.stdout)

    def stderr_lines(self) -> list[str]:
        return result_lines(self.stderr)


def result_lines(stream: str) -> list[str]:
    """The result lines a stream holds, sorted, with the progress the
    default printer redraws, and the padding that overwrites it
    (results.py:563-568), stripped."""
    return sorted(
        segment.rstrip(" ")
        for segment in re.split(r"\r\n|\r|\n", stream)
        if segment.strip() and not PROGRESS_SEGMENT.fullmatch(segment)
    )


@pytest.fixture
def work(tmp_path: Path) -> Path:
    """The working directory every command runs in."""
    path = tmp_path / "work"
    path.mkdir()
    return path


async def run_sync(
    aws_cli: str,
    work: Path,
    store: InMemoryS3,
    *arguments: str,
    environment: Mapping[str, str] | None = None,
) -> Run:
    """Run `aws s3 sync <arguments>` once in `work` against `store`."""
    start = len(store.received)
    async with s3_runtime(store, work.parent) as (_, env):
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "sync", *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        store=store,
        received=store.received[start:],
    )


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def stamp(path: Path, offset: int) -> None:
    """Sets the mtime of `path` `offset` ns from the store's LastModified."""
    mtime = STORE_TIME * SECOND + offset
    os.utime(path, ns=(mtime, mtime))


def write_stamped(path: Path, body: bytes, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    stamp(path, offset)


def upload_line(name: str, prefix: str = "up/") -> str:
    return f"upload: {local('src', *name.split('/'))} to s3://{BUCKET}/{prefix}{name}"


def download_line(name: str, prefix: str = "tree/") -> str:
    return (
        f"download: s3://{BUCKET}/{prefix}{name} to "
        + local("dest", *name.split("/"))
    )


class DeniedListingS3(InMemoryS3):
    """Refuses every ListObjectsV2 with AccessDenied."""

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        if reconstructed.operation_model.name == "ListObjectsV2":
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        return super().dispatch(reconstructed)


# How long the store holds a transfer: long enough that the listing's next
# page fails while the transfers its first page paired are still in flight.
HELD_SECONDS: Final = 2
# Sources the first listing page pairs for transfer: their names sort before
# every PAGED name, so each is paired before the second page is requested.
CANCELED: Final = ["a0.txt", "a1.txt", "a2.txt"]


class RefusedNextPageS3(InMemoryS3):
    """Refuses each ListObjectsV2 continuation with AccessDenied, and holds
    every other request for HELD_SECONDS before answering it."""

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        if "list-type=" not in context.request.effective_path:
            await asyncio.sleep(HELD_SECONDS)
        return await super().respond(context)

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        if (
            reconstructed.operation_model.name == "ListObjectsV2"
            and "ContinuationToken" in reconstructed.params
        ):
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        return super().dispatch(reconstructed)


def assert_canceled(run: Run, canceled: list[str]) -> None:
    """The run ended on the refused page's fatal error, and the transfers in
    flight were canceled instead of completing.

    Upstream's transfer manager cancels its transfers when the comparator
    raises the listing's error (s3transfer/crt.py:495-499), and its CRT
    client reports each cancellation, in no fixed order, before the error.
    The native client reports only the error: the parity gap failures.txt
    ledgers for cp's repeated continuation token. Either way none of them
    completes.
    """
    report = run.report()
    error = ACCESS_DENIED.format(operation="ListObjectsV2")
    *lines, fatal = [
        line.rstrip(" ") for line in run.stderr.splitlines() if line.strip()
    ] or [""]
    assert (run.returncode, run.stdout_lines(), fatal) == (
        1,
        [],
        f"fatal error: {error}",
    ), report
    assert len(set(lines)) == len(lines), report
    assert set(lines) <= set(canceled), report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("destination", "prefix"),
    [
        pytest.param(f"s3://{BUCKET}/up", "up/", id="prefix"),
        pytest.param(f"s3://{BUCKET}/up/", "up/", id="trailing-slash"),
        pytest.param(f"s3://{BUCKET}", "", id="bucket"),
    ],
)
async def test_sync_upload_uploads_every_file_the_destination_lacks(
    aws_cli: str, work: Path, destination: str, prefix: str
) -> None:
    write_tree(work, UPLOAD_TREE)
    run = await run_sync(
        aws_cli, work, InMemoryS3(OUTSIDE), "src", destination
    )
    report = run.report()
    names = [name.removeprefix("src/") for name in UPLOAD_TREE]
    uploaded = {
        (BUCKET, prefix + name.removeprefix("src/")): body
        for name, body in UPLOAD_TREE.items()
    }
    assert run.store.failures == [], report
    # The destination is listed, as a directory, before anything is
    # uploaded; with the bucket root it holds every outside object, which
    # stays.
    assert run.requests()[0] == ("ListObjectsV2", prefix), report
    assert run.keys("ListObjectsV2") == [prefix], report
    assert run.keys("PutObject") == sorted(key for _, key in uploaded), report
    expected = sorted(upload_line(name, prefix) for name in names)
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        expected,
        "",
    ), report
    assert run.store.objects == {**OUTSIDE, **uploaded}, report


@pytest.mark.asyncio
async def test_sync_upload_uploads_files_that_differ_in_size_or_are_newer(
    aws_cli: str, work: Path
) -> None:
    for name, pair in PAIRS.items():
        write_stamped(work / "src" / name, pair.local, pair.offset)
    write_stamped(work / "src" / "local-only.txt", CHANGED, -HOUR)
    objects = {
        **{(BUCKET, f"up/{name}"): pair.remote for name, pair in PAIRS.items()},
        (BUCKET, "up/remote-only.txt"): REMOTE,
    }
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), "src", f"s3://{BUCKET}/up/"
    )
    report = run.report()
    uploads = sorted(
        [name for name, pair in PAIRS.items() if pair.transfers]
        + ["local-only.txt"]
    )
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", "up/"), report
    assert run.keys("ListObjectsV2") == ["up/"], report
    assert run.keys("PutObject") == [f"up/{name}" for name in uploads], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(upload_line(name) for name in uploads),
        "",
    ), report
    # An object only the destination holds stays.
    assert run.store.objects == {
        **objects,
        **{
            (BUCKET, f"up/{name}"): (work / "src" / name).read_bytes()
            for name in uploads
        },
    }, report


@pytest.mark.asyncio
async def test_sync_upload_twice_uploads_nothing_the_second_time(
    aws_cli: str, work: Path
) -> None:
    for name, body in UPLOAD_TREE.items():
        write_stamped(work / name, body, -HOUR)
    store = InMemoryS3()
    first = await run_sync(aws_cli, work, store, "src", f"s3://{BUCKET}/up")
    second = await run_sync(aws_cli, work, store, "src", f"s3://{BUCKET}/up")
    report = first.report() + second.report()
    assert store.failures == [], report
    assert (first.returncode, len(first.keys("PutObject"))) == (
        0,
        len(UPLOAD_TREE),
    ), report
    # Each object is now newer than its file and the same size.
    assert second.requests() == [("ListObjectsV2", "up/")], report
    assert (second.returncode, second.stdout, second.stderr) == (
        0,
        "",
        "",
    ), report


@pytest.mark.asyncio
async def test_sync_upload_pairs_files_across_destination_listing_pages(
    aws_cli: str, work: Path
) -> None:
    for name in PAGED:
        changed = name in PAGED_CHANGED
        write_stamped(
            work / "src" / name,
            b"diff" if changed else b"same",
            HOUR if changed else -HOUR,
        )
    objects = {(BUCKET, f"up/{name}"): b"same" for name in PAGED}
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), "src", f"s3://{BUCKET}/up/"
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("ListObjectsV2") == ["up/", "up/"], report
    assert run.keys("PutObject") == [
        f"up/{name}" for name in PAGED_CHANGED
    ], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(upload_line(name) for name in PAGED_CHANGED),
        "",
    ), report


@pytest.mark.asyncio
async def test_sync_upload_pairs_names_in_key_order(
    aws_cli: str, work: Path
) -> None:
    for name in ORDERED:
        write_stamped(work / "src" / name, b"same", -HOUR)
    # Only the source has it, between names both sides hold.
    write_stamped(work / "src" / "a" / "bb.txt", b"new", -HOUR)
    objects = {(BUCKET, f"up/{name}"): b"same" for name in ORDERED}
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), "src", f"s3://{BUCKET}/up/"
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("PutObject") == ["up/a/bb.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [upload_line("a/bb.txt")],
        "",
    ), report


@pytest.mark.asyncio
async def test_sync_upload_of_an_empty_directory_still_lists_the_destination(
    aws_cli: str, work: Path
) -> None:
    (work / "src").mkdir()
    objects = {(BUCKET, f"up/{name}"): b"same" for name in PAGED}
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), "src", f"s3://{BUCKET}/up/"
    )
    report = run.report()
    assert run.store.failures == [], report
    # Upstream pairs every listed object with no file, so it lists them
    # all, and leaves them alone.
    assert run.requests() == [("ListObjectsV2", "up/")] * 2, report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert run.store.objects == objects, report


@pytest.mark.asyncio
async def test_sync_upload_from_a_missing_directory_fails_before_any_request(
    aws_cli: str, work: Path
) -> None:
    run = await run_sync(
        aws_cli, work, InMemoryS3(), "missing", f"s3://{BUCKET}/up/"
    )
    report = run.report()
    assert run.requests() == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        255,
        "",
        "\naws: [ERROR]: The user-provided path missing does not exist.\n",
    ), report


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="a mode-000 file"
)
async def test_sync_upload_warns_about_unreadable_files_and_uploads_the_rest(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, UPLOAD_TREE)
    locked = work / "src" / "locked.txt"
    locked.write_bytes(b"locked")
    locked.chmod(0)
    try:
        run = await run_sync(
            aws_cli,
            work,
            InMemoryS3({(BUCKET, "up/locked.txt"): b"other"}),
            "src",
            f"s3://{BUCKET}/up/",
        )
    finally:
        locked.chmod(0o600)
    report = run.report()
    names = sorted(name.removeprefix("src/") for name in UPLOAD_TREE)
    assert run.store.failures == [], report
    assert run.keys("PutObject") == [f"up/{name}" for name in names], report
    # A warning makes the command exit 2.
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        sorted(upload_line(name) for name in names),
        [
            "warning: Skipping file <cwd>/src/locked.txt. "
            "File/Directory is not readable."
        ],
    ), report
    assert run.store.objects[(BUCKET, "up/locked.txt")] == b"other", report


@pytest.mark.asyncio
async def test_sync_upload_refused_destination_listing_is_fatal(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, UPLOAD_TREE)
    store = DeniedListingS3()
    run = await run_sync(aws_cli, work, store, "src", f"s3://{BUCKET}/up/")
    report = run.report()
    error = ACCESS_DENIED.format(operation="ListObjectsV2")
    assert store.failures == [], report
    assert run.requests() == [("ListObjectsV2", "up/")], report
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"fatal error: {error}\n",
    ), report
    assert store.objects == {}, report


@pytest.mark.asyncio
async def test_sync_upload_failed_destination_listing_page_cancels_uploads(
    aws_cli: str, work: Path
) -> None:
    # The PAGED objects are only at the destination, so pairing the last
    # file, which sorts after them all, needs the listing's second page.
    for name in [*CANCELED, "z.txt"]:
        write_stamped(work / "src" / name, b"new", 0)
    objects = {(BUCKET, f"up/{name}"): b"same" for name in PAGED}
    store = RefusedNextPageS3(objects)
    run = await run_sync(aws_cli, work, store, "src", f"s3://{BUCKET}/up/")
    report = run.report()
    assert store.failures == [], report
    assert run.keys("ListObjectsV2") == ["up/", "up/"], report
    assert_canceled(
        run,
        [
            f"upload failed: {local('src', name)} to s3://{BUCKET}/up/{name} "
            "AWS_ERROR_S3_CANCELED: Request successfully cancelled"
            for name in CANCELED
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "prefix"),
    [
        pytest.param(f"s3://{BUCKET}/tree", "tree/", id="prefix"),
        pytest.param(f"s3://{BUCKET}/tree/", "tree/", id="trailing-slash"),
        pytest.param(f"s3://{BUCKET}", "", id="bucket"),
    ],
)
@pytest.mark.parametrize(
    "existing", [False, True], ids=["missing-directory", "empty-directory"]
)
async def test_sync_download_downloads_every_object_but_folder_markers(
    aws_cli: str, work: Path, source: str, prefix: str, existing: bool
) -> None:
    dest = work / "dest"
    if existing:
        dest.mkdir()
    run = await run_sync(
        aws_cli, work, InMemoryS3(SEED_OBJECTS), source, "dest"
    )
    report = run.report()
    files = sorted(
        key[len(prefix) :]
        for _, key in SEED_OBJECTS
        if key.startswith(prefix) and not key.endswith("/")
    )
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", prefix), report
    assert run.keys("ListObjectsV2") == [prefix], report
    assert run.keys("GetObject") == [prefix + name for name in files], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(download_line(name, prefix) for name in files),
        "",
    ), report
    assert read_tree(dest) == {
        name: SEED_OBJECTS[(BUCKET, prefix + name)] for name in files
    }, report
    # A folder marker makes no directory, and each file takes its object's
    # LastModified.
    directories = sorted(
        path.relative_to(dest).as_posix()
        for path in dest.rglob("*")
        if path.is_dir()
    )
    assert directories == sorted(
        {
            parent
            for name in files
            for parent in (
                "/".join(name.split("/")[:depth])
                for depth in range(1, name.count("/") + 1)
            )
        }
    ), report
    assert {
        name: (dest / name).stat().st_mtime_ns for name in files
    } == {name: STORE_TIME * SECOND for name in files}, report


@pytest.mark.asyncio
async def test_sync_download_downloads_objects_that_differ_in_size_or_are_older(
    aws_cli: str, work: Path
) -> None:
    dest = work / "dest"
    for name, pair in PAIRS.items():
        write_stamped(dest / name, pair.local, pair.offset)
    write_stamped(dest / "local-only.txt", CHANGED, -HOUR)
    objects = {
        **{
            (BUCKET, f"tree/{name}"): pair.remote
            for name, pair in PAIRS.items()
        },
        (BUCKET, "tree/remote-only.txt"): REMOTE,
    }
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), f"s3://{BUCKET}/tree/", "dest"
    )
    report = run.report()
    downloads = sorted(
        [name for name, pair in PAIRS.items() if pair.transfers]
        + ["remote-only.txt"]
    )
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", "tree/"), report
    assert run.keys("ListObjectsV2") == ["tree/"], report
    assert run.keys("GetObject") == [
        f"tree/{name}" for name in downloads
    ], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(download_line(name) for name in downloads),
        "",
    ), report
    # A file only the destination holds stays, and so does every file that
    # is not older than its object: a download replaces only what is newer.
    kept = {name: pair.local for name, pair in PAIRS.items()}
    kept["local-only.txt"] = CHANGED
    assert read_tree(dest) == {
        **kept,
        **{name: objects[(BUCKET, f"tree/{name}")] for name in downloads},
    }, report
    offsets = {name: pair.offset for name, pair in PAIRS.items()}
    offsets["local-only.txt"] = -HOUR
    assert {
        name: (dest / name).stat().st_mtime_ns for name in read_tree(dest)
    } == {
        name: STORE_TIME * SECOND + (0 if name in downloads else offset)
        for name, offset in {**offsets, "remote-only.txt": 0}.items()
    }, report


@pytest.mark.asyncio
async def test_sync_download_twice_downloads_nothing_the_second_time(
    aws_cli: str, work: Path
) -> None:
    store = InMemoryS3(SEED_OBJECTS)
    first = await run_sync(aws_cli, work, store, f"s3://{BUCKET}/tree", "dest")
    second = await run_sync(aws_cli, work, store, f"s3://{BUCKET}/tree", "dest")
    report = first.report() + second.report()
    files = sorted(
        key for key in TREE if not key.endswith("/")
    )
    assert store.failures == [], report
    assert (first.returncode, first.keys("GetObject")) == (0, files), report
    # Each file took its object's LastModified, so it is not newer.
    assert second.requests() == [("ListObjectsV2", "tree/")], report
    assert (second.returncode, second.stdout, second.stderr) == (
        0,
        "",
        "",
    ), report


@pytest.mark.asyncio
async def test_sync_download_pairs_objects_across_listing_pages(
    aws_cli: str, work: Path
) -> None:
    dest = work / "dest"
    for name in PAGED:
        changed = name in PAGED_CHANGED
        write_stamped(
            dest / name, b"diff" if changed else b"same", HOUR if changed else 0
        )
    objects = {(BUCKET, f"tree/{name}"): b"same" for name in PAGED}
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), f"s3://{BUCKET}/tree/", "dest"
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("ListObjectsV2") == ["tree/", "tree/"], report
    assert run.keys("GetObject") == [
        f"tree/{name}" for name in PAGED_CHANGED
    ], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(download_line(name) for name in PAGED_CHANGED),
        "",
    ), report
    assert {name: (dest / name).read_bytes() for name in PAGED_CHANGED} == {
        name: b"same" for name in PAGED_CHANGED
    }, report


@pytest.mark.asyncio
async def test_sync_download_pairs_names_in_key_order(
    aws_cli: str, work: Path
) -> None:
    for name in ORDERED:
        write_stamped(work / "dest" / name, b"same", 0)
    objects = {
        **{(BUCKET, f"tree/{name}"): b"same" for name in ORDERED},
        # Only the source has it, between names both sides hold.
        (BUCKET, "tree/a/bb.txt"): b"new",
    }
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), f"s3://{BUCKET}/tree/", "dest"
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("GetObject") == ["tree/a/bb.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [download_line("a/bb.txt")],
        "",
    ), report


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="a FIFO and mode-000 files",
)
@pytest.mark.parametrize(
    "listed", [True, False], ids=["objects", "empty-listing"]
)
async def test_sync_download_warns_about_destination_files_it_cannot_read(
    aws_cli: str, work: Path, listed: bool
) -> None:
    dest = work / "dest"
    dest.mkdir()
    locked = [dest / "locked.txt", dest / "sub" / "kept.txt"]
    for path in locked:
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"old")
        path.chmod(0)
    os.mkfifo(dest / "pipe")
    objects = (
        {
            (BUCKET, "tree/a.txt"): pattern_bytes("a", 100),
            (BUCKET, "tree/locked.txt"): pattern_bytes("locked", 200),
        }
        if listed
        else {}
    )
    try:
        run = await run_sync(
            aws_cli,
            work,
            InMemoryS3(objects),
            f"s3://{BUCKET}/tree/",
            "dest",
        )
    finally:
        for path in locked:
            path.chmod(0o600)
    report = run.report()
    # The walk of the destination skips what it cannot read with a warning,
    # even with nothing listed, so an object of the same name reads as
    # missing there and is downloaded over it.
    downloads = ["a.txt", "locked.txt"] if listed else []
    assert run.store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{name}" for name in downloads]
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        sorted(download_line(name) for name in downloads),
        [
            "warning: Skipping file <cwd>/dest/locked.txt. "
            "File/Directory is not readable.",
            "warning: Skipping file <cwd>/dest/pipe. File is character "
            "special device, block special device, FIFO, or socket.",
            "warning: Skipping file <cwd>/dest/sub/kept.txt. "
            "File/Directory is not readable.",
        ],
    ), report
    assert (dest / "sub" / "kept.txt").read_bytes() == b"old", report
    assert (dest / "locked.txt").read_bytes() == (
        objects[(BUCKET, "tree/locked.txt")] if listed else b"old"
    ), report
    assert stat.S_ISFIFO((dest / "pipe").lstat().st_mode), report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing", [False, True], ids=["missing-directory", "unreadable-file"]
)
async def test_sync_download_refused_listing_is_fatal_before_any_walk(
    aws_cli: str, work: Path, existing: bool
) -> None:
    dest = work / "dest"
    if existing:
        if os.name != "posix" or os.geteuid() == 0:
            pytest.skip("a mode-000 file")
        dest.mkdir()
        (dest / "locked.txt").write_bytes(b"old")
        (dest / "locked.txt").chmod(0)
    store = DeniedListingS3(SEED_OBJECTS)
    try:
        run = await run_sync(
            aws_cli, work, store, f"s3://{BUCKET}/tree/", "dest"
        )
    finally:
        if existing:
            (dest / "locked.txt").chmod(0o600)
    report = run.report()
    error = ACCESS_DENIED.format(operation="ListObjectsV2")
    assert store.failures == [], report
    assert run.requests() == [("ListObjectsV2", "tree/")], report
    # The listing fails before the destination is walked, so nothing warns
    # about the file it cannot read; the missing destination was created
    # first.
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"fatal error: {error}\n",
    ), report
    assert dest.is_dir(), report


@pytest.mark.asyncio
async def test_sync_download_failed_listing_page_cancels_downloads(
    aws_cli: str, work: Path
) -> None:
    # The destination holds every PAGED object as it is, so the first page
    # pairs only the CANCELED objects for download, and the last PAGED
    # objects fall on the second page.
    dest = work / "dest"
    for name in PAGED:
        write_stamped(dest / name, b"same", 0)
    objects = {
        (BUCKET, f"tree/{name}"): b"new" if name in CANCELED else b"same"
        for name in [*CANCELED, *PAGED]
    }
    store = RefusedNextPageS3(objects)
    run = await run_sync(aws_cli, work, store, f"s3://{BUCKET}/tree/", "dest")
    report = run.report()
    assert store.failures == [], report
    assert run.keys("ListObjectsV2") == ["tree/", "tree/"], report
    assert_canceled(
        run,
        [
            f"download failed: s3://{BUCKET}/tree/{name} to "
            f"{local('dest', name)} "
            "AWS_ERROR_S3_CANCELED: Request successfully cancelled"
            for name in CANCELED
        ],
    )
    # A canceled download leaves no file, not even a partial one.
    assert sorted(path.name for path in dest.iterdir()) == PAGED, report


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["upload", "download"])
async def test_sync_user_agent_names_the_paginator_on_listings_only(
    aws_cli: str, work: Path, direction: str
) -> None:
    write_tree(work, UPLOAD_TREE)
    arguments = (
        ("src", f"s3://{BUCKET}/up/")
        if direction == "upload"
        else (f"s3://{BUCKET}/tree/", "dest")
    )
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_sync(
        aws_cli,
        work,
        store,
        *arguments,
        # The session id would open the session database under HOME.
        environment={"AWS_CLI_SESSION_ID_DISABLED": "true"},
    )
    report = run.report()
    assert store.failures == [], report
    assert run.returncode == 0, report
    transfer = {
        RETRY_STANDARD,
        REQUEST_WHEN_SUPPORTED,
        RESPONSE_WHEN_SUPPORTED,
        S3_TRANSFER,
        CRT_AUTO,
    }
    # Upstream lists either side through a paginator on the command's
    # thread, and transfers through the CRT client.
    expected = {
        "ListObjectsV2": transfer | {PAGINATOR},
        "PutObject": transfer | {REQUEST_CRC64},
        "GetObject": transfer,
    }
    seen = []
    for request in run.received:
        operation = request.operation_model.name
        user_agent = request.wire_request.headers.get("user-agent", "")
        seen.append(operation)
        assert user_agent_parts(user_agent) == (
            frozenset(expected[operation]),
            frozenset({"md/prompt#off", "md/command#s3.sync"}),
        ), f"{operation}: {user_agent}\n{report}"
    transfers = len(UPLOAD_TREE) if direction == "upload" else 3
    assert seen[0] == "ListObjectsV2", report
    assert sorted(seen[1:]) == [
        "PutObject" if direction == "upload" else "GetObject"
    ] * transfers, report


# The strategies upstream registers for a name both sides hold
# (syncstrategy/register.py:35-55). Each option overrides the default
# strategy, and of several the one registered last wins: --no-overwrite,
# then --exact-timestamps, then --size-only. --exact-timestamps changes only
# a download; an upload compares as the default does.
EXACT_SAME: Final = frozenset({"same-time.txt", "rounds-to-same.txt"})
STRATEGY_FLAGS: Final = [
    pytest.param(["--size-only"], "size-only", id="size-only"),
    pytest.param(
        ["--exact-timestamps"], "exact-timestamps", id="exact-timestamps"
    ),
    pytest.param(["--no-overwrite"], "no-overwrite", id="no-overwrite"),
    pytest.param(
        ["--exact-timestamps", "--size-only"],
        "exact-timestamps",
        id="exact-timestamps-over-size-only",
    ),
    pytest.param(
        ["--no-overwrite", "--size-only"],
        "no-overwrite",
        id="no-overwrite-over-size-only",
    ),
    pytest.param(
        ["--exact-timestamps", "--no-overwrite"],
        "no-overwrite",
        id="no-overwrite-over-exact-timestamps",
    ),
]


def strategy_transfers(rule: str, direction: str, name: str) -> bool:
    """Whether `rule` transfers the PAIRS name `name` in `direction`."""
    pair = PAIRS[name]
    resized = len(pair.local) != len(pair.remote)
    if rule == "no-overwrite":
        return False
    if rule == "size-only":
        return resized
    if rule == "exact-timestamps" and direction == "download":
        return resized or name not in EXACT_SAME
    return pair.transfers


@pytest.mark.asyncio
@pytest.mark.parametrize(("flags", "rule"), STRATEGY_FLAGS)
async def test_sync_upload_strategy_options_decide_names_both_sides_hold(
    aws_cli: str, work: Path, flags: list[str], rule: str
) -> None:
    for name, pair in PAIRS.items():
        write_stamped(work / "src" / name, pair.local, pair.offset)
    write_stamped(work / "src" / "local-only.txt", CHANGED, -HOUR)
    objects = {
        **{(BUCKET, f"up/{name}"): pair.remote for name, pair in PAIRS.items()},
        (BUCKET, "up/remote-only.txt"): REMOTE,
    }
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), "src", f"s3://{BUCKET}/up/", *flags
    )
    report = run.report()
    # A name only the source holds is uploaded whatever the strategy.
    uploads = sorted(
        [name for name in PAIRS if strategy_transfers(rule, "upload", name)]
        + ["local-only.txt"]
    )
    assert run.store.failures == [], report
    assert run.keys("ListObjectsV2") == ["up/"], report
    assert run.keys("PutObject") == [f"up/{name}" for name in uploads], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(upload_line(name) for name in uploads),
        "",
    ), report
    # Upstream hands --no-overwrite to the strategy alone, never to the
    # upload as a condition (subcommands.py:1650-1657).
    assert [
        request.params.get("IfNoneMatch")
        for request in run.received
        if request.operation_model.name == "PutObject"
    ] == [None] * len(uploads), report
    assert run.store.objects == {
        **objects,
        **{
            (BUCKET, f"up/{name}"): (work / "src" / name).read_bytes()
            for name in uploads
        },
    }, report


@pytest.mark.asyncio
@pytest.mark.parametrize(("flags", "rule"), STRATEGY_FLAGS)
async def test_sync_download_strategy_options_decide_names_both_sides_hold(
    aws_cli: str, work: Path, flags: list[str], rule: str
) -> None:
    dest = work / "dest"
    for name, pair in PAIRS.items():
        write_stamped(dest / name, pair.local, pair.offset)
    write_stamped(dest / "local-only.txt", CHANGED, -HOUR)
    objects = {
        **{
            (BUCKET, f"tree/{name}"): pair.remote
            for name, pair in PAIRS.items()
        },
        (BUCKET, "tree/remote-only.txt"): REMOTE,
    }
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        f"s3://{BUCKET}/tree/",
        "dest",
        *flags,
    )
    report = run.report()
    downloads = sorted(
        [name for name in PAIRS if strategy_transfers(rule, "download", name)]
        + ["remote-only.txt"]
    )
    assert run.store.failures == [], report
    assert run.keys("ListObjectsV2") == ["tree/"], report
    assert run.keys("GetObject") == [
        f"tree/{name}" for name in downloads
    ], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(download_line(name) for name in downloads),
        "",
    ), report
    kept = {name: pair.local for name, pair in PAIRS.items()}
    kept["local-only.txt"] = CHANGED
    assert read_tree(dest) == {
        **kept,
        **{name: objects[(BUCKET, f"tree/{name}")] for name in downloads},
    }, report


def ordered_lines(stream: str) -> list[str]:
    """The result lines a stream holds, in the order it printed them."""
    return [
        segment.rstrip(" ")
        for segment in re.split(r"\r\n|\r|\n", stream)
        if segment.strip() and not PROGRESS_SEGMENT.fullmatch(segment)
    ]


class DeniedDeleteS3(InMemoryS3):
    """Refuses every DeleteObject of a key ending in "denied.txt"."""

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        if reconstructed.operation_model.name == "DeleteObject" and (
            reconstructed.params["Key"].endswith("denied.txt")
        ):
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        return super().dispatch(reconstructed)


# Objects and files only the destination holds: before every source name,
# between them, below a directory, and after them all, so the comparator
# names one before its first source, while pairing, and once the source is
# done.
DESTINATION_ONLY: Final = [
    "a-first.txt",
    "gone.txt",
    "sub/gone.txt",
    "zz/last.txt",
]


@pytest.mark.asyncio
async def test_sync_upload_delete_removes_objects_the_source_lacks(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, UPLOAD_TREE)
    names = [name.removeprefix("src/") for name in UPLOAD_TREE]
    objects = {
        **OUTSIDE,
        **{(BUCKET, f"up/{name}"): b"only here" for name in DESTINATION_ONLY},
        # A folder marker is no file to pair, so it stays.
        (BUCKET, "up/folder/"): b"",
    }
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", "up/"), report
    assert run.keys("PutObject") == sorted(f"up/{n}" for n in names), report
    assert run.keys("DeleteObject") == [
        f"up/{name}" for name in DESTINATION_ONLY
    ], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            [upload_line(name) for name in names]
            + [f"delete: s3://{BUCKET}/up/{n}" for n in DESTINATION_ONLY]
        ),
        "",
    ), report
    assert run.store.objects == {
        **OUTSIDE,
        (BUCKET, "up/folder/"): b"",
        **{
            (BUCKET, f"up/{name.removeprefix('src/')}"): body
            for name, body in UPLOAD_TREE.items()
        },
    }, report


@pytest.mark.asyncio
async def test_sync_download_delete_removes_files_the_source_lacks(
    aws_cli: str, work: Path
) -> None:
    dest = work / "dest"
    for name in DESTINATION_ONLY:
        write_stamped(dest / name, b"only here", -HOUR)
    files = sorted(key.removeprefix("tree/") for key in TREE if key[-1] != "/")
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--delete",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{name}" for name in files], report
    assert run.keys("DeleteObject") == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            [download_line(name) for name in files]
            + [f"delete: {local('dest', *n.split('/'))}" for n in DESTINATION_ONLY]
        ),
        "",
    ), report
    assert read_tree(dest) == {
        name: SEED_OBJECTS[(BUCKET, f"tree/{name}")] for name in files
    }, report
    # A delete removes the file alone, never the directory it leaves empty.
    assert (dest / "sub").is_dir() and (dest / "zz").is_dir(), report


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["upload", "download"])
async def test_sync_delete_dryrun_reports_each_name_in_comparator_order(
    aws_cli: str, work: Path, direction: str
) -> None:
    # Only the source holds b.txt, both hold d.txt as it is, and only the
    # destination holds the rest.
    destination_only = ["a.txt", "c.txt", "e.txt"]
    if direction == "upload":
        write_stamped(work / "src" / "b.txt", b"new", -HOUR)
        write_stamped(work / "src" / "d.txt", b"same", -HOUR)
        objects = {
            (BUCKET, f"up/{name}"): b"same"
            for name in [*destination_only, "d.txt"]
        }
        arguments = ["src", f"s3://{BUCKET}/up/"]
        expected = [
            f"(dryrun) delete: s3://{BUCKET}/up/a.txt",
            f"(dryrun) {upload_line('b.txt')}",
            f"(dryrun) delete: s3://{BUCKET}/up/c.txt",
            f"(dryrun) delete: s3://{BUCKET}/up/e.txt",
        ]
    else:
        for name in [*destination_only, "d.txt"]:
            write_stamped(work / "dest" / name, b"same", 0)
        objects = {
            (BUCKET, "tree/b.txt"): b"new",
            (BUCKET, "tree/d.txt"): b"same",
        }
        arguments = [f"s3://{BUCKET}/tree/", "dest"]
        expected = [
            f"(dryrun) delete: {local('dest', 'a.txt')}",
            f"(dryrun) {download_line('b.txt')}",
            f"(dryrun) delete: {local('dest', 'c.txt')}",
            f"(dryrun) delete: {local('dest', 'e.txt')}",
        ]
    store = InMemoryS3(objects)
    before = read_tree(work)
    run = await run_sync(
        aws_cli, work, store, *arguments, "--delete", "--dryrun"
    )
    report = run.report()
    assert store.failures == [], report
    assert [name for name, _ in run.requests()] == ["ListObjectsV2"], report
    # A dry run reports each name as the comparator yields it: a delete
    # between the transfers.
    assert (run.returncode, ordered_lines(run.stdout), run.stderr) == (
        0,
        expected,
        "",
    ), report
    assert (store.objects, read_tree(work)) == (objects, before), report


@pytest.mark.asyncio
async def test_sync_upload_delete_keeps_what_the_filters_leave_out(
    aws_cli: str, work: Path
) -> None:
    for name in ["keep.txt", "skip.log", "sub/three.txt"]:
        write_stamped(work / "src" / name, b"new", -HOUR)
    objects = {
        (BUCKET, f"up/{name}"): b"only here"
        for name in ["old.txt", "old.log", "sub/old.txt"]
    }
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
        "--exclude",
        "*.log",
        "--exclude",
        "sub/*",
    )
    report = run.report()
    # Each pattern is rooted at the source and at the destination, so it
    # leaves out a file and an object alike (filters.py:94-149).
    assert run.store.failures == [], report
    assert run.keys("PutObject") == ["up/keep.txt"], report
    assert run.keys("DeleteObject") == ["up/old.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/up/old.txt", upload_line("keep.txt")],
        "",
    ), report
    assert run.store.objects == {
        (BUCKET, "up/keep.txt"): b"new",
        (BUCKET, "up/old.log"): b"only here",
        (BUCKET, "up/sub/old.txt"): b"only here",
    }, report


@pytest.mark.asyncio
async def test_sync_download_delete_keeps_what_the_filters_leave_out(
    aws_cli: str, work: Path
) -> None:
    dest = work / "dest"
    for name in ["stray.txt", "nested/old.txt", "stray.bin"]:
        write_stamped(dest / name, b"only here", -HOUR)
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/tree",
        "dest",
        "--delete",
        "--exclude",
        "nested/*",
        "--exclude",
        "*.bin",
        "--include",
        "b.txt",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("GetObject") == ["tree/a.txt", "tree/b.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            [download_line("a.txt"), download_line("b.txt")]
            + [f"delete: {local('dest', 'stray.txt')}"]
        ),
        "",
    ), report
    assert read_tree(dest) == {
        "a.txt": TREE["tree/a.txt"],
        "b.txt": TREE["tree/b.txt"],
        "nested/old.txt": b"only here",
        "stray.bin": b"only here",
    }, report


@pytest.mark.asyncio
async def test_sync_upload_failed_delete_fails_the_command(
    aws_cli: str, work: Path
) -> None:
    write_stamped(work / "src" / "b.txt", b"new", -HOUR)
    objects = {
        (BUCKET, "up/a-denied.txt"): b"only here",
        (BUCKET, "up/c.txt"): b"only here",
    }
    run = await run_sync(
        aws_cli,
        work,
        DeniedDeleteS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
    )
    report = run.report()
    error = ACCESS_DENIED.format(operation="DeleteObject")
    assert run.store.failures == [], report
    assert run.keys("DeleteObject") == ["up/a-denied.txt", "up/c.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        1,
        [f"delete: s3://{BUCKET}/up/c.txt", upload_line("b.txt")],
        [f"delete failed: s3://{BUCKET}/up/a-denied.txt {error}"],
    ), report
    assert run.store.objects == {
        (BUCKET, "up/a-denied.txt"): b"only here",
        (BUCKET, "up/b.txt"): b"new",
    }, report


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="a read-only directory"
)
async def test_sync_download_failed_delete_fails_the_command(
    aws_cli: str, work: Path
) -> None:
    dest = work / "dest"
    for name in ["locked/a.txt", "c.txt"]:
        write_stamped(dest / name, b"only here", -HOUR)
    (dest / "locked").chmod(0o555)
    try:
        run = await run_sync(
            aws_cli,
            work,
            InMemoryS3({(BUCKET, "tree/b.txt"): b"new"}),
            f"s3://{BUCKET}/tree/",
            "dest",
            "--delete",
        )
    finally:
        (dest / "locked").chmod(0o755)
    report = run.report()
    locked = local("dest", "locked", "a.txt")
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        1,
        sorted([download_line("b.txt"), f"delete: {local('dest', 'c.txt')}"]),
        [
            f"delete failed: {locked} [Errno 13] Permission denied: "
            f"'<cwd>/{locked}'"
        ],
    ), report
    assert read_tree(dest) == {"b.txt": b"new", "locked/a.txt": b"only here"}


class HeldGetS3(InMemoryS3):
    """Holds every GetObject for HELD_SECONDS before answering it, so the
    first of two downloads is still in flight when the second is paired."""

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        if request.method == "GET" and "list-type=" not in (
            request.effective_path
        ):
            await asyncio.sleep(HELD_SECONDS)
        return await super().respond(context)


def case_sensitive(path: Path) -> bool:
    probe = path / "case-probe"
    probe.write_bytes(b"")
    try:
        return not (path / "CASE-PROBE").exists()
    finally:
        probe.unlink()


CASE_DOC: Final = (
    "https://docs.aws.amazon.com/cli/latest/topic/s3-case-insensitivity.html"
)
# Keys that differ only by case: "A.txt" sorts first, so its download is
# in flight when "a.txt" is paired (syncstrategy/caseconflict.py:30-60).
CASE_KEYS: Final = {
    (BUCKET, "tree/A.txt"): b"upper",
    (BUCKET, "tree/a.txt"): b"lower",
}


def case_warning(verb: str, rest: str) -> str:
    return (
        f"warning: {verb} {BUCKET}/tree/a.txt -> <cwd>/dest/a.txt {rest}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["ignore", "skip", "warn"])
async def test_sync_download_case_conflict_with_an_object_in_flight(
    aws_cli: str, work: Path, mode: str
) -> None:
    if not case_sensitive(work):
        pytest.skip("a case-insensitive filesystem holds one of the names")
    run = await run_sync(
        aws_cli,
        work,
        HeldGetS3(CASE_KEYS),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--case-conflict",
        mode,
    )
    report = run.report()
    downloads = ["A.txt"] if mode == "skip" else ["A.txt", "a.txt"]
    warnings = {
        "ignore": [],
        "skip": [
            case_warning(
                "Skipping",
                "because a file whose name differs only by case either "
                "exists or is being downloaded.",
            )
        ],
        "warn": [
            case_warning(
                "Downloading",
                "despite a file whose name differs only by case either "
                "existing or being downloaded. This behavior is not defined "
                "on case-insensitive filesystems and may result in "
                "overwriting existing files or race conditions between "
                "concurrent downloads. For more information, see "
                f"{CASE_DOC}.",
            )
        ],
    }[mode]
    assert run.store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{n}" for n in downloads], report
    # The warning is printed, not counted: the command still exits 0.
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        0,
        sorted(download_line(name) for name in downloads),
        warnings,
    ), report
    assert read_tree(work / "dest") == {
        name: CASE_KEYS[(BUCKET, f"tree/{name}")] for name in downloads
    }, report


@pytest.mark.asyncio
async def test_sync_download_case_conflict_error_cancels_the_downloads(
    aws_cli: str, work: Path
) -> None:
    if not case_sensitive(work):
        pytest.skip("a case-insensitive filesystem holds one of the names")
    run = await run_sync(
        aws_cli,
        work,
        HeldGetS3(CASE_KEYS),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--case-conflict",
        "error",
    )
    report = run.report()
    *lines, fatal = [
        line.rstrip(" ") for line in run.stderr.splitlines() if line.strip()
    ] or [""]
    assert run.store.failures == [], report
    assert run.keys("GetObject") in (["tree/A.txt"], []), report
    assert (run.returncode, run.stdout_lines(), fatal) == (
        1,
        [],
        f"fatal error: Failed to download {BUCKET}/tree/a.txt -> "
        "<cwd>/dest/a.txt because a file whose name differs only by case "
        "either exists or is being downloaded.",
    ), report
    # The download in flight is canceled, as for a failed listing page.
    assert set(lines) <= {
        f"download failed: s3://{BUCKET}/tree/A.txt to "
        f"{local('dest', 'A.txt')} "
        "AWS_ERROR_S3_CANCELED: Request successfully cancelled"
    }, report
    assert not (work / "dest" / "a.txt").exists(), report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flag", "stdout"),
    [
        pytest.param("--quiet", False, id="quiet"),
        pytest.param("--only-show-errors", False, id="only-show-errors"),
        pytest.param("--no-progress", True, id="no-progress"),
    ],
)
async def test_sync_output_options_choose_what_is_printed(
    aws_cli: str, work: Path, flag: str, stdout: bool
) -> None:
    write_tree(work, UPLOAD_TREE)
    objects = {(BUCKET, "up/gone.txt"): b"only here"}
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
        flag,
    )
    report = run.report()
    names = [name.removeprefix("src/") for name in UPLOAD_TREE]
    lines = sorted(
        [upload_line(name) for name in names]
        + [f"delete: s3://{BUCKET}/up/gone.txt"]
    )
    assert run.store.failures == [], report
    assert run.keys("DeleteObject") == ["up/gone.txt"], report
    assert (run.returncode, run.stderr) == (0, ""), report
    if stdout:
        # No progress line is drawn between the results.
        assert run.stdout.splitlines() == ordered_lines(run.stdout), report
        assert sorted(run.stdout.splitlines()) == lines, report
    else:
        assert run.stdout == "", report


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["upload", "download"])
async def test_sync_page_size_pages_the_listing(
    aws_cli: str, work: Path, direction: str
) -> None:
    names = [f"f{index}.txt" for index in range(5)]
    if direction == "upload":
        for name in names:
            write_stamped(work / "src" / name, b"same", -HOUR)
        objects = {(BUCKET, f"up/{name}"): b"same" for name in names}
        arguments = ["src", f"s3://{BUCKET}/up/"]
    else:
        for name in names:
            write_stamped(work / "dest" / name, b"same", 0)
        objects = {(BUCKET, f"tree/{name}"): b"same" for name in names}
        arguments = [f"s3://{BUCKET}/tree/", "dest"]
    run = await run_sync(
        aws_cli, work, InMemoryS3(objects), *arguments, "--page-size", "2"
    )
    report = run.report()
    assert run.store.failures == [], report
    assert [
        (request.operation_model.name, request.params.get("MaxKeys"))
        for request in run.received
    ] == [("ListObjectsV2", 2)] * 3, report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report


UPLOAD_SETTINGS: Final = (
    "--content-type",
    "application/x-settings",
    "--cache-control",
    "max-age=60",
    "--metadata",
    "origin=settings",
    "--acl",
    "bucket-owner-full-control",
    "--storage-class",
    "STANDARD_IA",
    "--sse",
    "AES256",
    "--request-payer",
    "requester",
)


@pytest.mark.asyncio
async def test_sync_upload_sends_object_settings_and_the_payer(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, UPLOAD_TREE)
    objects = {(BUCKET, "up/gone.txt"): b"only here"}
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
        *UPLOAD_SETTINGS,
    )
    report = run.report()
    settings = {
        "ContentType": "application/x-settings",
        "CacheControl": "max-age=60",
        "Metadata": {"origin": "settings"},
        "ACL": "bucket-owner-full-control",
        "StorageClass": "STANDARD_IA",
        "ServerSideEncryption": "AES256",
        "RequestPayer": "requester",
    }
    assert run.store.failures == [], report
    assert run.returncode == 0, report
    sent = {
        (request.operation_model.name, request.params.get("Key", "")): {
            member: request.params[member]
            for member in settings
            if member in request.params
        }
        for request in run.received
    }
    # The destination's listing and each delete send the payer alone.
    assert sent == {
        ("ListObjectsV2", ""): {"RequestPayer": "requester"},
        ("DeleteObject", "up/gone.txt"): {"RequestPayer": "requester"},
        **{
            ("PutObject", f"up/{name.removeprefix('src/')}"): settings
            for name in UPLOAD_TREE
        },
    }, report


@pytest.mark.asyncio
async def test_sync_download_sends_the_customer_key_and_the_payer(
    aws_cli: str, work: Path
) -> None:
    key = b"0123456789abcdef0123456789abcdef"
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3({(BUCKET, "tree/a.txt"): b"remote"}),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--sse-c",
        "AES256",
        "--sse-c-key",
        key.decode(),
        "--request-payer",
        "requester",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.returncode == 0, report
    sent = [
        (
            request.operation_model.name,
            request.params.get("RequestPayer"),
            request.wire_request.headers.get(
                "x-amz-server-side-encryption-customer-algorithm"
            ),
        )
        for request in run.received
    ]
    assert sent == [
        ("ListObjectsV2", "requester", None),
        ("GetObject", "requester", "AES256"),
    ], report
    assert read_tree(work / "dest") == {"a.txt": b"remote"}, report


# The members an upload's grants and Content-Type send.
GRANT_AND_TYPE_MEMBERS: Final = (
    "ContentType",
    "GrantFullControl",
    "GrantRead",
    "GrantReadACP",
    "GrantWriteACP",
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flags", "members"),
    [
        pytest.param(
            (
                "--grants",
                "read=uri=http://acs.amazonaws.com/groups/global/AllUsers",
                "full=id=owner",
            ),
            {
                "ContentType": "text/plain",
                "GrantRead": "uri=http://acs.amazonaws.com/groups/global/AllUsers",
                "GrantFullControl": "id=owner",
            },
            id="grants",
        ),
        pytest.param(("--no-guess-mime-type",), {}, id="no-guess-mime-type"),
    ],
)
async def test_sync_upload_sends_grants_and_guessed_types_on_each_put(
    aws_cli: str,
    work: Path,
    flags: tuple[str, ...],
    members: dict[str, str],
) -> None:
    """Each PutObject carries the grants, and the type guessed unless
    --no-guess-mime-type; the destination's listing and each delete carry
    neither (utils.py:487-505, 589-603)."""
    write_tree(work, UPLOAD_TREE)
    objects = {(BUCKET, "up/gone.txt"): b"only here"}
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3(objects),
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
        *flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.returncode == 0, report
    sent = {
        (request.operation_model.name, request.params.get("Key", "")): {
            member: request.params[member]
            for member in GRANT_AND_TYPE_MEMBERS
            if member in request.params
        }
        for request in run.received
    }
    assert sent == {
        ("ListObjectsV2", ""): {},
        ("DeleteObject", "up/gone.txt"): {},
        **{
            ("PutObject", f"up/{name.removeprefix('src/')}"): members
            for name in UPLOAD_TREE
        },
    }, report


@pytest.mark.asyncio
async def test_sync_download_ignores_grants_even_malformed(
    aws_cli: str, work: Path
) -> None:
    """Only an upload maps --grants (utils.py:487-505), so a download
    neither sends nor checks them."""
    run = await run_sync(
        aws_cli,
        work,
        InMemoryS3({(BUCKET, "tree/a.txt"): b"remote"}),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--grants",
        "read=id=reader",
        "everyone",
        "--no-guess-mime-type",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [download_line("a.txt")],
        "",
    ), report
    assert run.requests() == [
        ("ListObjectsV2", "tree/"),
        ("GetObject", "tree/a.txt"),
    ], report
    assert [
        member
        for request in run.received
        for member in GRANT_AND_TYPE_MEMBERS
        if member in request.params
    ] == [], report
    assert read_tree(work / "dest") == {"a.txt": b"remote"}, report


GLACIER_WARNING: Final = (
    f"warning: Skipping file s3://{BUCKET}/tree/cold.txt. Object is of "
    "storage class GLACIER. Unable to perform download operations on "
    "GLACIER objects. You must restore the object to be able to perform the "
    "operation. See aws s3 download help for additional parameter options "
    "to ignore or force these transfers."
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flags", "returncode", "warnings", "gets"),
    [
        pytest.param([], 2, [GLACIER_WARNING], ["tree/a.txt"], id="default"),
        pytest.param(
            ["--ignore-glacier-warnings"],
            0,
            [],
            ["tree/a.txt"],
            id="ignore-glacier-warnings",
        ),
        pytest.param(
            ["--force-glacier-transfer"],
            1,
            [
                f"download failed: s3://{BUCKET}/tree/cold.txt to "
                f"{local('dest', 'cold.txt')} An error occurred "
                "(InvalidObjectState) when calling the GetObject operation: "
                "The operation is not valid for the object's storage class"
            ],
            ["tree/a.txt", "tree/cold.txt"],
            id="force-glacier-transfer",
        ),
    ],
)
async def test_sync_download_applies_the_glacier_rule(
    aws_cli: str,
    work: Path,
    flags: list[str],
    returncode: int,
    warnings: list[str],
    gets: list[str],
) -> None:
    objects = {
        (BUCKET, "tree/a.txt"): b"remote",
        (BUCKET, "tree/cold.txt"): b"frozen",
    }
    store = InMemoryS3(objects, storage={"tree/cold.txt": ("GLACIER", None)})
    run = await run_sync(
        aws_cli, work, store, f"s3://{BUCKET}/tree/", "dest", *flags
    )
    report = run.report()
    assert store.failures == [], report
    assert run.keys("GetObject") == gets, report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        returncode,
        [download_line("a.txt")],
        warnings,
    ), report
