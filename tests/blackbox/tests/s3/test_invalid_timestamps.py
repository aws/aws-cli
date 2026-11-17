"""A local file whose mtime upstream's datetime cannot hold.

Upstream's file generator reads each local file's mtime with
`datetime.fromtimestamp(st_mtime, tzlocal())` (utils.py:253-276). When
that raises, it warns that the file has an invalid timestamp and lists the
file with the epoch as its mtime (filegenerator.py:246-266), and the warning
makes the command exit 2. It does so for every local file a command lists:
an upload's sources and a sync download's destination. The generator runs
ahead of the filters and the sync comparator (subcommands.py:1394-1401), so
a file they drop still warns.

Which mtimes it cannot hold depends on the platform. Windows' `gmtime_s`
refuses any time before 1970; elsewhere only one past year 9999, or before
year 1, fails. A filesystem may clamp such an mtime instead of holding it:
Linux holds one past year 9999 on tmpfs, and macOS's APFS holds none, so a
test that needs one runs on a filesystem that holds it or is skipped.
"""

import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import (
    LAST_MODIFIED,
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    s3_runtime,
    without_cwd,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
WARNING: Final = (
    "warning: File has an invalid timestamp. Passing epoch time as timestamp."
)
SECOND: Final = 1_000_000_000
DAY: Final = 86400 * SECOND
EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


def since_epoch(moment: datetime) -> int:
    """`moment` in nanoseconds since the epoch."""
    return int((moment - EPOCH).total_seconds()) * SECOND


# An mtime upstream cannot hold here: one in 1960 on Windows, and elsewhere
# one in year 10000, past it in every local offset.
INVALID: Final = (
    since_epoch(datetime(1960, 1, 1, tzinfo=UTC))
    if sys.platform == "win32"
    else since_epoch(datetime(9999, 12, 31, tzinfo=UTC)) + 2 * DAY
)
# An mtime every platform holds, an hour before the store's LastModified.
VALID: Final = since_epoch(LAST_MODIFIED) - 3600 * SECOND
BAD: Final = pattern_bytes("bad", 300)
GOOD: Final = pattern_bytes("good", 500)
# A segment of the progress line the default printer redraws.
PROGRESS_SEGMENT: Final = re.compile(r"Completed .* file\(s\) remaining.*")


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    store: InMemoryS3

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
            for request in self.store.received
        ]

    def keys(self, operation: str) -> list[str]:
        """The keys `operation` named, sorted: transfers run concurrently."""
        return sorted(
            key for name, key in self.requests() if name == operation
        )

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


@pytest.fixture
def work(tmp_path: Path) -> Iterator[Path]:
    """The working directory every command runs in, on a filesystem that
    holds INVALID: the test's own, or Linux's tmpfs."""
    roots = [tmp_path]
    if sys.platform == "linux":
        roots.append(Path("/dev/shm"))
    for root in roots:
        if not root.is_dir():
            continue
        parent = Path(tempfile.mkdtemp(dir=root))
        try:
            if holds(parent, INVALID):
                path = parent / "work"
                path.mkdir()
                yield path
                return
        finally:
            shutil.rmtree(parent)
    pytest.skip("no filesystem here holds an mtime upstream cannot read")


def write(path: Path, body: bytes, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    os.utime(path, ns=(mtime, mtime))


def write_sources(work: Path) -> None:
    """src/bad.txt, which upstream cannot read the mtime of, and
    src/good.txt, which it can."""
    write(work / "src" / "bad.txt", BAD, INVALID)
    write(work / "src" / "good.txt", GOOD, VALID)


async def run_s3(
    aws_cli: str, work: Path, store: InMemoryS3, *arguments: str
) -> Run:
    """Run `aws s3 <arguments>` once in `work` against `store`."""
    async with s3_runtime(store, work.parent) as (_, env):
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        store=store,
    )


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def upload_line(name: str, verb: str = "upload") -> str:
    return f"{verb}: {local('src', name)} to s3://{BUCKET}/up/{name}"


@dataclass(frozen=True)
class Upload:
    """A command that uploads src/: its arguments, the files it names, and
    the verb its result lines use."""

    arguments: tuple[str, ...]
    names: tuple[str, ...]
    verb: str = "upload"


UPLOADS: Final = [
    pytest.param(
        Upload(
            ("cp", "src/bad.txt", f"s3://{BUCKET}/up/bad.txt"), ("bad.txt",)
        ),
        id="cp-single",
    ),
    pytest.param(
        Upload(
            ("cp", "src", f"s3://{BUCKET}/up/", "--recursive"),
            ("bad.txt", "good.txt"),
        ),
        id="cp-recursive",
    ),
    pytest.param(
        Upload(
            ("mv", "src/bad.txt", f"s3://{BUCKET}/up/bad.txt"),
            ("bad.txt",),
            verb="move",
        ),
        id="mv-single",
    ),
    pytest.param(
        Upload(
            ("mv", "src", f"s3://{BUCKET}/up/", "--recursive"),
            ("bad.txt", "good.txt"),
            verb="move",
        ),
        id="mv-recursive",
    ),
    pytest.param(
        Upload(("sync", "src", f"s3://{BUCKET}/up/"), ("bad.txt", "good.txt")),
        id="sync",
    ),
]


@pytest.mark.parametrize("upload", UPLOADS)
async def test_upload_warns_of_an_invalid_timestamp_and_still_uploads(
    aws_cli: str, work: Path, upload: Upload
) -> None:
    write_sources(work)
    run = await run_s3(
        aws_cli, work, InMemoryS3(), *upload.arguments, "--no-progress"
    )
    report = run.report()
    bodies = {"bad.txt": BAD, "good.txt": GOOD}
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        sorted(upload_line(name, upload.verb) for name in upload.names),
        [WARNING],
    ), report
    assert run.store.objects == {
        (BUCKET, f"up/{name}"): bodies[name] for name in upload.names
    }, report


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(
            (
                "cp",
                "src/bad.txt",
                f"s3://{BUCKET}/up/bad.txt",
                "--exclude",
                "*",
            ),
            id="cp-single",
        ),
        pytest.param(
            (
                "cp",
                "src",
                f"s3://{BUCKET}/up/",
                "--recursive",
                "--exclude",
                "bad.txt",
            ),
            id="cp-recursive",
        ),
        pytest.param(
            ("sync", "src", f"s3://{BUCKET}/up/", "--exclude", "bad.txt"),
            id="sync",
        ),
    ],
)
async def test_upload_warns_of_an_invalid_timestamp_the_filters_drop(
    aws_cli: str, work: Path, arguments: tuple[str, ...]
) -> None:
    write_sources(work)
    run = await run_s3(
        aws_cli, work, InMemoryS3(), *arguments, "--no-progress"
    )
    report = run.report()
    single = "src/bad.txt" in arguments
    expected = {} if single else {(BUCKET, "up/good.txt"): GOOD}
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        [] if single else [upload_line("good.txt")],
        [WARNING],
    ), report
    assert run.store.objects == expected, report


@pytest.mark.parametrize(
    ("flags", "shows_warning", "shows_successes", "uploads"),
    [
        pytest.param(
            ("--only-show-errors",), True, False, True, id="only-show-errors"
        ),
        pytest.param(("--quiet",), False, False, True, id="quiet"),
        pytest.param(("--dryrun",), True, True, False, id="dryrun"),
    ],
)
async def test_sync_upload_warns_of_an_invalid_timestamp_as_its_output_allows(
    aws_cli: str,
    work: Path,
    flags: tuple[str, ...],
    shows_warning: bool,
    shows_successes: bool,
    uploads: bool,
) -> None:
    write_sources(work)
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(),
        "sync",
        "src",
        f"s3://{BUCKET}/up/",
        *flags,
    )
    report = run.report()
    prefix = "(dryrun) " if "--dryrun" in flags else ""
    lines = [prefix + upload_line(name) for name in ("bad.txt", "good.txt")]
    # Under --quiet the warning still counts, so the exit is 2.
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        lines if shows_successes else [],
        [WARNING] if shows_warning else [],
    ), report
    assert run.keys("PutObject") == (
        ["up/bad.txt", "up/good.txt"] if uploads else []
    ), report


@pytest.mark.parametrize(
    ("modified", "uploads"),
    [
        # The epoch is newer than an object of the day before, so the file
        # is uploaded, and older than one of the day after, so it is not;
        # its own mtime is newer, or older, than both. Upstream converts
        # the object's LastModified to local time (utils.py:404-405), which
        # on Windows refuses one before 1970 as it does an mtime, so there
        # the listing fails with `[Errno 22] Invalid argument` and only
        # native compares the earlier object.
        pytest.param(
            EPOCH - timedelta(days=1),
            True,
            id="object-before-epoch",
            marks=pytest.mark.native_only(sys.platform == "win32"),
        ),
        pytest.param(
            EPOCH + timedelta(days=1), False, id="object-after-epoch"
        ),
    ],
)
async def test_sync_upload_compares_an_invalid_timestamp_as_the_epoch(
    aws_cli: str, work: Path, modified: datetime, uploads: bool
) -> None:
    write(work / "src" / "bad.txt", BAD, INVALID)
    key: ObjectKey = (BUCKET, "up/bad.txt")
    remote = pattern_bytes("remote", len(BAD))
    store = InMemoryS3({key: remote}, last_modified={key: modified})
    run = await run_s3(
        aws_cli,
        work,
        store,
        "sync",
        "src",
        f"s3://{BUCKET}/up/",
        "--no-progress",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        [upload_line("bad.txt")] if uploads else [],
        [WARNING],
    ), report
    assert run.store.objects[key] == (BAD if uploads else remote), report


async def test_sync_download_warns_of_destination_invalid_timestamps(
    aws_cli: str, work: Path
) -> None:
    # The destination's bad.txt is the size of its object and compared as
    # the epoch, which is older than the object, so it stays; its own mtime
    # would be newer off Windows, and replaced. The destination's
    # excluded.txt warns too: it is listed before the filters drop it.
    write(work / "dest" / "bad.txt", BAD, INVALID)
    write(work / "dest" / "excluded.txt", BAD, INVALID)
    objects = {
        (BUCKET, "tree/bad.txt"): pattern_bytes("remote", len(BAD)),
        (BUCKET, "tree/good.txt"): GOOD,
    }
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(objects),
        "sync",
        f"s3://{BUCKET}/tree/",
        "dest",
        "--exclude",
        "excluded.txt",
        "--no-progress",
    )
    report = run.report()
    destination = local("dest", "good.txt")
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2,
        [f"download: s3://{BUCKET}/tree/good.txt to {destination}"],
        [WARNING, WARNING],
    ), report
    assert (work / "dest" / "bad.txt").read_bytes() == BAD, report
    assert (work / "dest" / "good.txt").read_bytes() == GOOD, report


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows cannot read a time before 1970"
)
async def test_sync_upload_compares_a_time_before_1970_as_it_is(
    aws_cli: str, tmp_path: Path
) -> None:
    # The file is older than its object, as the epoch would not be, so it
    # is not uploaded, and nothing warns.
    work = tmp_path / "work"
    before = since_epoch(datetime(1960, 1, 1, tzinfo=UTC))
    write(work / "src" / "old.txt", BAD, before)
    key: ObjectKey = (BUCKET, "up/old.txt")
    remote = pattern_bytes("remote", len(BAD))
    store = InMemoryS3(
        {key: remote}, last_modified={key: EPOCH - timedelta(days=1)}
    )
    run = await run_s3(
        aws_cli,
        work,
        store,
        "sync",
        "src",
        f"s3://{BUCKET}/up/",
        "--no-progress",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert run.store.objects == {key: remote}, report
