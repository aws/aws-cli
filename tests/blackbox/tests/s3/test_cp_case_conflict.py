import asyncio
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from localstub import HTTPResponse, ResponderContext

from credhelpers import run_command
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

pytestmark = pytest.mark.asyncio

# `--case-conflict` on `s3 cp` and `s3 mv`. Upstream handles case conflicts
# only for a recursive download (subcommands.py:1659-1665), which it then
# runs as a sync (subcommands.py:1698-1726): it walks the destination
# directory and pairs each object with the file of the same name. An object
# the destination holds by that name is always transferred, and a file only
# the destination holds is kept. An object only the source holds is checked
# first (syncstrategy/caseconflict.py:34-60): when a download of the same
# case-folded name has not finished, or anything exists at its destination
# path, `skip` warns and leaves it, `warn` warns and downloads it, and
# `error` ends the command with the conflict as its fatal error. A warning
# is printed outside the results, so `--quiet` keeps it and the exit status
# ignores it. Every other transfer ignores the option.

BUCKET: Final = "bucket"
SECOND: Final = 1_000_000_000
HOUR: Final = 3600 * SECOND
CASE_DOC: Final = (
    "https://docs.aws.amazon.com/cli/latest/topic/s3-case-insensitivity.html"
)
CONFLICT: Final = (
    "because a file whose name differs only by case either exists or is "
    "being downloaded."
)
WARN_CONFLICT: Final = (
    "despite a file whose name differs only by case either existing or "
    "being downloaded. This behavior is not defined on case-insensitive "
    "filesystems and may result in overwriting existing files or race "
    "conditions between concurrent downloads. For more information, see "
    f"{CASE_DOC}."
)
# Keys that differ only by case: "A.txt" sorts first, so its download claims
# the case-folded name "a.txt" before "a.txt" is paired.
CASE_KEYS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "tree/A.txt"): b"upper",
    (BUCKET, "tree/a.txt"): b"lower",
}
# How long HeldGetS3 holds each download: long enough that the first of two
# is still in flight when the second is paired.
HELD_SECONDS: Final = 2
# A segment of the progress line the default printer redraws.
PROGRESS_SEGMENT: Final = re.compile(r"Completed .* file\(s\) remaining.*")


@dataclass(frozen=True)
class Command:
    name: str
    # The verb of each result line.
    verb: str
    # Whether each transferred source is deleted.
    moves: bool


COMMANDS: Final = [
    pytest.param(Command("cp", "download", moves=False), id="cp"),
    pytest.param(Command("mv", "move", moves=True), id="mv"),
]


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


class HeldGetS3(InMemoryS3):
    """Holds every GetObject for HELD_SECONDS before answering it."""

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        if request.method == "GET" and "list-type=" not in (
            request.effective_path
        ):
            await asyncio.sleep(HELD_SECONDS)
        return await super().respond(context)


@pytest.fixture
def work(tmp_path: Path) -> Path:
    """The working directory every command runs in."""
    path = tmp_path / "work"
    path.mkdir()
    return path


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


def case_sensitive(path: Path) -> bool:
    probe = path / "case-probe"
    probe.write_bytes(b"")
    try:
        return not (path / "CASE-PROBE").exists()
    finally:
        probe.unlink()


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def result_line(command: Command, name: str) -> str:
    destination = local("dest", *name.split("/"))
    return f"{command.verb}: s3://{BUCKET}/tree/{name} to {destination}"


def case_warning(verb: str, name: str, rest: str) -> str:
    """A conflict's warning: the object without its scheme, and the
    destination's absolute path (syncstrategy/caseconflict.py:62-89)."""
    destination = local("<cwd>", "dest", *name.split("/"))
    return f"warning: {verb} {BUCKET}/tree/{name} -> {destination} {rest}"


def remaining(
    objects: Mapping[ObjectKey, bytes], command: Command, moved: list[str]
) -> dict[ObjectKey, bytes]:
    """The objects a run leaves: a move deletes each one it downloaded."""
    if not command.moves:
        return dict(objects)
    return {
        (bucket, key): body
        for (bucket, key), body in objects.items()
        if key.removeprefix("tree/") not in moved
    }


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("mode", ["ignore", "skip", "warn"])
async def test_case_conflict_with_an_object_in_flight(
    aws_cli: str, work: Path, command: Command, mode: str
) -> None:
    if not case_sensitive(work):
        pytest.skip("a case-insensitive filesystem holds one of the names")
    run = await run_s3(
        aws_cli,
        work,
        HeldGetS3(CASE_KEYS),
        command.name,
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
        "--case-conflict",
        mode,
    )
    report = run.report()
    downloads = ["A.txt"] if mode == "skip" else ["A.txt", "a.txt"]
    warnings = {
        "ignore": [],
        "skip": [case_warning("Skipping", "a.txt", CONFLICT)],
        "warn": [case_warning("Downloading", "a.txt", WARN_CONFLICT)],
    }[mode]
    assert run.store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{n}" for n in downloads], report
    deleted = downloads if command.moves else []
    assert run.keys("DeleteObject") == [f"tree/{n}" for n in deleted], report
    # The warning is printed, not counted: the command still exits 0.
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        0,
        sorted(result_line(command, name) for name in downloads),
        warnings,
    ), report
    assert read_tree(work / "dest") == {
        name: CASE_KEYS[(BUCKET, f"tree/{name}")] for name in downloads
    }, report
    assert run.store.objects == remaining(CASE_KEYS, command, downloads)


@pytest.mark.parametrize("command", COMMANDS)
async def test_case_conflict_error_cancels_the_downloads(
    aws_cli: str, work: Path, command: Command
) -> None:
    if not case_sensitive(work):
        pytest.skip("a case-insensitive filesystem holds one of the names")
    run = await run_s3(
        aws_cli,
        work,
        HeldGetS3(CASE_KEYS),
        command.name,
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
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
        f"{local('<cwd>', 'dest', 'a.txt')} {CONFLICT}",
    ), report
    # The download in flight is canceled, so a move deletes nothing.
    assert set(lines) <= {
        f"{command.verb} failed: s3://{BUCKET}/tree/A.txt to "
        f"{local('dest', 'A.txt')} "
        "AWS_ERROR_S3_CANCELED: Request successfully cancelled"
    }, report
    assert run.keys("DeleteObject") == [], report
    assert not (work / "dest" / "a.txt").exists(), report
    assert run.store.objects == CASE_KEYS, report


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("mode", ["skip", "warn"])
@pytest.mark.parametrize(
    "output",
    [
        pytest.param("--no-progress", id="no-progress"),
        pytest.param("--quiet", id="quiet"),
    ],
)
async def test_case_conflict_dryrun_holds_each_name_it_reports(
    aws_cli: str, work: Path, command: Command, mode: str, output: str
) -> None:
    # A dry run finishes no download, so the case-folded name a reported
    # object claims is never released (subscribers.py:121-132), and the
    # conflict is found whatever the filesystem.
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(CASE_KEYS),
        command.name,
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
        "--dryrun",
        "--case-conflict",
        mode,
        output,
    )
    report = run.report()
    reported = ["A.txt"] if mode == "skip" else ["A.txt", "a.txt"]
    warning = {
        "skip": case_warning("Skipping", "a.txt", CONFLICT),
        "warn": case_warning("Downloading", "a.txt", WARN_CONFLICT),
    }[mode]
    lines = [f"(dryrun) {result_line(command, name)}" for name in reported]
    assert run.store.failures == [], report
    assert run.requests() == [("ListObjectsV2", "tree/")], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        0,
        [] if output == "--quiet" else sorted(lines),
        [warning],
    ), report
    assert read_tree(work) == {}, report
    assert run.store.objects == CASE_KEYS, report


@pytest.mark.parametrize("command", COMMANDS)
async def test_case_conflict_skips_an_object_whose_path_exists(
    aws_cli: str, work: Path, command: Command
) -> None:
    # The walk names only the directory's file, so the object at the
    # directory's own path is one the destination lacks, and its path
    # exists.
    write_tree(work, {"dest/sub/x.txt": b"kept"})
    objects = {
        (BUCKET, "tree/other.txt"): pattern_bytes("other", 200),
        (BUCKET, "tree/sub"): pattern_bytes("sub", 100),
    }
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(objects),
        command.name,
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
        "--case-conflict",
        "skip",
        "--no-progress",
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.keys("GetObject") == ["tree/other.txt"], report
    deleted = ["tree/other.txt"] if command.moves else []
    assert run.keys("DeleteObject") == deleted, report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        0,
        [result_line(command, "other.txt")],
        [case_warning("Skipping", "sub", CONFLICT)],
    ), report
    assert read_tree(work / "dest") == {
        "other.txt": objects[(BUCKET, "tree/other.txt")],
        "sub/x.txt": b"kept",
    }, report
    assert run.store.objects == remaining(objects, command, ["other.txt"])


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("mode", ["skip", "warn", "error"])
async def test_case_conflict_replaces_files_of_the_same_name(
    aws_cli: str, work: Path, command: Command, mode: str
) -> None:
    # A file of the object's size that is newer than the object, which a
    # sync would keep, is replaced: a copy always transfers a name both
    # sides hold. A file only the destination holds is kept.
    objects = {
        (BUCKET, "tree/a.txt"): pattern_bytes("remote", 300),
        (BUCKET, "tree/b.txt"): pattern_bytes("b", 400),
    }
    write_tree(
        work,
        {"dest/a.txt": pattern_bytes("local", 300), "dest/extra.txt": b"x"},
    )
    newer = int(LAST_MODIFIED.timestamp()) * SECOND + HOUR
    os.utime(work / "dest" / "a.txt", ns=(newer, newer))
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(objects),
        command.name,
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
        "--case-conflict",
        mode,
        "--no-progress",
    )
    report = run.report()
    names = ["a.txt", "b.txt"]
    assert run.store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{n}" for n in names], report
    deleted = names if command.moves else []
    assert run.keys("DeleteObject") == [f"tree/{n}" for n in deleted], report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        0,
        [result_line(command, name) for name in names],
        [],
    ), report
    assert read_tree(work / "dest") == {
        "a.txt": objects[(BUCKET, "tree/a.txt")],
        "b.txt": objects[(BUCKET, "tree/b.txt")],
        "extra.txt": b"x",
    }, report
    assert run.store.objects == remaining(objects, command, names)


@dataclass(frozen=True)
class Transfer:
    arguments: tuple[str, ...]
    # The verb of a copy's result line; a move's is "move".
    verb: str
    # The requests the copy sends, each once, in order.
    requests: tuple[tuple[str, str], ...]
    # What a move adds: a download deletes its object after the GET.
    deletes: tuple[tuple[str, str], ...]
    # The result line's source and destination.
    shown: tuple[str, str]


# Transfers upstream checks for no conflict: neither a single object nor an
# upload pairs anything, so an object or file whose name differs only by
# case changes nothing.
TRANSFERS: Final = {
    "single-download": Transfer(
        (f"s3://{BUCKET}/tree/a.txt", "a.txt"),
        "download",
        (("HeadObject", "tree/a.txt"), ("GetObject", "tree/a.txt")),
        (("DeleteObject", "tree/a.txt"),),
        (f"s3://{BUCKET}/tree/a.txt", local(".", "a.txt")),
    ),
    "single-upload": Transfer(
        ("a.txt", f"s3://{BUCKET}/up/"),
        "upload",
        (("PutObject", "up/a.txt"),),
        (),
        (local(".", "a.txt"), f"s3://{BUCKET}/up/a.txt"),
    ),
    "recursive-upload": Transfer(
        ("src", f"s3://{BUCKET}/up/", "--recursive"),
        "upload",
        (("PutObject", "up/a.txt"),),
        (),
        (local("src", "a.txt"), f"s3://{BUCKET}/up/a.txt"),
    ),
}


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("transfer", TRANSFERS)
async def test_case_conflict_leaves_other_transfers_alone(
    aws_cli: str, work: Path, command: Command, transfer: str
) -> None:
    case = TRANSFERS[transfer]
    body = pattern_bytes("local", 100)
    write_tree(work, {"a.txt": body, "src/a.txt": body})
    objects = {
        (BUCKET, "tree/a.txt"): b"lower",
        (BUCKET, "up/A.txt"): b"upper",
    }
    run = await run_s3(
        aws_cli,
        work,
        InMemoryS3(objects),
        command.name,
        *case.arguments,
        "--case-conflict",
        "error",
        "--no-progress",
    )
    report = run.report()
    verb = "move" if command.moves else case.verb
    requests = [*case.requests, *(case.deletes if command.moves else ())]
    source, destination = case.shown
    assert run.store.failures == [], report
    # A CRT-preferred client may split a transfer, so each request is
    # counted once.
    assert list(dict.fromkeys(run.requests())) == requests, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"{verb}: {source} to {destination}"],
        "",
    ), report
