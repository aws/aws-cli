"""What `s3 cp` prints, and what it moves, under each output mode.

Each test runs one command against the in-memory bucket of s3store.py and
asserts the result lines the upstream printer writes, the exit status, the
local files, the stored objects, and the operations sent. Progress redraws
depend on speed and timing, so the result lines are compared with them
stripped, and the progress itself is checked against upstream's formats.
"""

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from nethelpers import refusing_port
from s3store import (
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    without_cwd,
    write_tree,
)

BUCKET: Final = "bucket"
LOOPBACK: Final = "127.0.0.1"
# Every PutObject into this bucket is refused with AccessDenied.
DENIED_BUCKET: Final = "denied-bucket"

# Glacier objects by key: the storage class, and the HeadObject Restore
# value where a restore was requested. Unlisted objects are STANDARD.
# ListObjectsV2 reports only the class: upstream never asks for restore
# status in a listing.
RESTORED: Final = (
    'ongoing-request="false", expiry-date="Fri, 21 Dec 2012 00:00:00 GMT"'
)
RESTORING: Final = 'ongoing-request="true"'
# An archived key whose basename climbs out of a directory destination,
# outside "glacier/" so the recursive cases never list it.
ESCAPE_KEY: Final = "escape/.."
GLACIER_STORAGE: Final[dict[str, tuple[str, str | None]]] = {
    "glacier/instant.txt": ("GLACIER_IR", None),
    "glacier/frozen.txt": ("GLACIER", None),
    "glacier/deep.txt": ("DEEP_ARCHIVE", None),
    "glacier/restored.txt": ("GLACIER", RESTORED),
    "glacier/restoring.txt": ("DEEP_ARCHIVE", RESTORING),
    ESCAPE_KEY: ("GLACIER", None),
}
GLACIER_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "glacier/standard.txt"): pattern_bytes("standard", 300),
    **{
        (BUCKET, key): pattern_bytes(key, 300 + index)
        for index, key in enumerate(GLACIER_STORAGE)
    },
}
# Keys a recursive download under "recursive/" lists: a folder marker,
# keys with `..` segments, and a key URL encoding changes.
RECURSIVE_OBJECTS: Final[dict[str, bytes]] = {
    "recursive/../escape": b"outside",
    "recursive/empty": b"",
    "recursive/folder/": b"",
    "recursive/nested/a b+%": b"encoded key",
    "recursive/nested/z": b"last page",
    "recursive/object": pattern_bytes("object", 20),
    "recursive/safe/../normalized": b"lexical",
}
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): pattern_bytes("object", 2048),
    # Small enough to arrive in one read, so its first progress update
    # moves every byte.
    (BUCKET, "download/small.txt"): pattern_bytes("small", 20),
    **{(BUCKET, key): body for key, body in RECURSIVE_OBJECTS.items()},
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
    (BUCKET, "tree/b.txt"): pattern_bytes("tree b", 1500),
    (BUCKET, "tree/nested/c.txt"): pattern_bytes("tree c", 700),
    **GLACIER_OBJECTS,
}
DOWNLOAD_BODY: Final = SEED_OBJECTS[(BUCKET, "download/object.txt")]
SMALL_BODY: Final = SEED_OBJECTS[(BUCKET, "download/small.txt")]
TREE: Final = {
    key: body
    for (_, key), body in SEED_OBJECTS.items()
    if key.startswith("tree/")
}
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
UPLOAD_TREE: Final[dict[str, bytes]] = {
    "src/one.txt": pattern_bytes("one", 400),
    "src/two.txt": pattern_bytes("two", 1200),
    "src/sub/three.txt": pattern_bytes("three", 50),
}

# Local paths `write_tree` cannot create, by kind: sources upstream's file
# generator skips, a FIFO, a symlink to the null character device, and a
# file or directory its owner may not read; and a destination directory
# its owner may not write.
FIFO: Final = "fifo"
DEVICE_LINK: Final = "device-link"
UNREADABLE_FILE: Final = "unreadable-file"
UNREADABLE_DIRECTORY: Final = "unreadable-directory"
UNWRITABLE_DIRECTORY: Final = "unwritable-directory"
UNREADABLE_KINDS: Final = frozenset({UNREADABLE_FILE, UNREADABLE_DIRECTORY})
DIRECTORY_KINDS: Final = frozenset(
    {UNREADABLE_DIRECTORY, UNWRITABLE_DIRECTORY}
)

# Loose shape of any progress segment, used to strip progress from stdout.
PROGRESS_SEGMENT: Final = re.compile(
    r"^Completed .* file\(s\) remaining( \(calculating\.\.\.\))? *$"
)
# Exact upstream formats (awscli/customizations/s3/results.py:323-332).
_SIZE: Final = r"(?:1 Byte|\d+ Bytes|\d+\.\d (?:KiB|MiB|GiB|TiB|PiB|EiB))"
_REMAINING: Final = r"(?P<remaining>~?\d+) file\(s\) remaining"
_CALCULATING: Final = r"(?P<calculating> \(calculating\.\.\.\))?"
BYTE_PROGRESS: Final = re.compile(
    rf"Completed (?P<completed>{_SIZE})/(?P<expected>~?{_SIZE}) "
    rf"\({_SIZE}/s\) with {_REMAINING}{_CALCULATING} *"
)
FILE_PROGRESS: Final = re.compile(
    rf"Completed \d+ file\(s\) with {_REMAINING}{_CALCULATING} *"
)
HUMANIZE_SUFFIXES: Final = ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB")


@dataclass(frozen=True)
class OutputMode:
    name: str
    flags: tuple[str, ...]
    # Whether the mode draws progress, which is stripped before comparing.
    shows_progress: bool = False
    # Whether the printer writes result lines for completed transfers, and
    # whether it writes anything at all: --quiet installs no printer and
    # --only-show-errors drops successes (s3handler.py:120-134).
    shows_successes: bool = True
    shows_errors: bool = True


QUIET: Final = OutputMode(
    "quiet", ("--quiet",), shows_successes=False, shows_errors=False
)
ONLY_SHOW_ERRORS: Final = OutputMode(
    "only-show-errors", ("--only-show-errors",), shows_successes=False
)
NO_PROGRESS: Final = OutputMode("no-progress", ("--no-progress",))
DEFAULT: Final = OutputMode("default", (), shows_progress=True)
PROGRESS_FREQUENCY: Final = OutputMode(
    "progress-frequency", ("--progress-frequency", "1"), shows_progress=True
)
PROGRESS_MULTILINE: Final = OutputMode(
    "progress-multiline", ("--progress-multiline",), shows_progress=True
)
# Longer than any transfer here, so only the first update is due
# (results.py:481-497).
PROGRESS_FREQUENCY_HOUR: Final = OutputMode(
    "progress-frequency-hour",
    ("--progress-frequency", "3600"),
    shows_progress=True,
)
ALL_MODES: Final = (
    QUIET,
    ONLY_SHOW_ERRORS,
    NO_PROGRESS,
    DEFAULT,
    PROGRESS_FREQUENCY,
    PROGRESS_MULTILINE,
)
PROGRESS_MODES: Final = (DEFAULT, PROGRESS_FREQUENCY, PROGRESS_MULTILINE)


@dataclass(frozen=True)
class Case:
    name: str
    arguments: tuple[str, ...]
    returncode: int = 0
    local_files: Mapping[str, bytes] = field(default_factory=dict[str, bytes])
    # Sources `make_special_files` creates after `local_files`, by kind.
    special_files: Mapping[str, str] = field(default_factory=dict[str, str])
    downloaded_files: Mapping[str, bytes] = field(
        default_factory=dict[str, bytes]
    )
    uploaded_objects: Mapping[ObjectKey, bytes] = field(
        default_factory=dict[ObjectKey, bytes]
    )
    # Result lines, with their terminators, as a printer that shows
    # everything writes them: successes on stdout, warnings and failures on
    # stderr. A mode drops what its printer does not show.
    successes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    # Result lines complete in a nondeterministic order.
    multi_file: bool = False
    # Size of the one object a successful single-file case moves; its last
    # progress segment must report this final total.
    final_total_bytes: int | None = None
    # A successful transfer always draws progress on the upstream printer.
    draws_progress: bool = False
    # Every (operation, status) answered, sorted.
    responses: tuple[tuple[str, int], ...] = ()


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


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def make_special_files(root: Path, specials: Mapping[str, str]) -> None:
    """Create each special source; skip where this identity can't be denied.

    An unreadable file keeps the bytes `write_tree` gave it. A privileged
    identity reads it anyway, which would make the fixture readable, so the
    case skips rather than assert on a readable source.
    """
    if specials and os.name == "nt":
        pytest.skip("special and unreadable sources are POSIX fixtures")
    for name, kind in specials.items():
        path = root / name
        if kind == FIFO:
            os.mkfifo(path)
        elif kind == DEVICE_LINK:
            path.symlink_to(os.devnull)
        elif kind == UNREADABLE_FILE:
            path.chmod(0)
        elif kind == UNREADABLE_DIRECTORY:
            path.mkdir()
            path.chmod(0)
        elif kind == UNWRITABLE_DIRECTORY:
            path.mkdir()
            path.chmod(0o500)
        else:
            raise ValueError(f"unknown special source kind {kind}")
        if (kind in UNREADABLE_KINDS and os.access(path, os.R_OK)) or (
            kind == UNWRITABLE_DIRECTORY and os.access(path, os.W_OK)
        ):
            release_special_files(root, specials)
            pytest.skip("this identity reads files their mode denies")


def release_special_files(root: Path, specials: Mapping[str, str]) -> None:
    """Give denied paths their access back for `read_tree` and cleanup."""
    for name, kind in specials.items():
        path = root / name
        if kind in UNREADABLE_KINDS | {UNWRITABLE_DIRECTORY} and (
            path.exists()
        ):
            path.chmod(0o700 if kind in DIRECTORY_KINDS else 0o600)


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    *,
    local_files: Mapping[str, bytes] | None = None,
    special_files: Mapping[str, str] | None = None,
    directory_links: Mapping[str, str] | None = None,
) -> Run:
    """Run `aws <arguments>` in tmp_path/work against the seeded bucket."""
    special_files = special_files or {}
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    write_tree(work, local_files or {})
    for name, target in (directory_links or {}).items():
        (work / target).mkdir(parents=True, exist_ok=True)
        (work / name).symlink_to(target, target_is_directory=True)
    make_special_files(work, special_files)
    store = InMemoryS3(
        SEED_OBJECTS,
        storage=GLACIER_STORAGE,
        denied_buckets=frozenset({DENIED_BUCKET}),
    )
    try:
        async with s3_runtime(store, tmp_path) as (_, env):
            # Bounded by run_command's timeout, so a CLI that opened a FIFO
            # fails instead of hanging.
            stdout, stderr, returncode = await run_command(
                [aws_cli, *arguments],
                env,
                cwd=work,
                stdin=None,
            )
    finally:
        release_special_files(work, special_files)
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        local_files=read_tree(work),
        store=store,
    )


def result_lines(text: str, *, progress: bool) -> list[str]:
    """Keep result lines and terminators, excluding progress redraws.

    Upstream pads each result line to the length of the progress line it
    overwrites, and that length depends on the speed text
    (results.py:563-568).
    """
    lines: list[str] = []
    progress_width = 0
    for match in re.finditer(r"([^\r\n]*)(\r\n|\r|\n|$)", text):
        segment, terminator = match.groups()
        if not segment and not terminator:
            continue
        if progress and PROGRESS_SEGMENT.fullmatch(segment):
            progress_width = len(segment) if terminator == "\r" else 0
            continue
        if progress_width and segment == " " * progress_width:
            continue
        lines.append(segment.rstrip(" ") + terminator)
        progress_width = 0
    return lines


def shown_output(
    run: Run, mode: OutputMode, *, multi_file: bool
) -> tuple[list[str], list[str]]:
    """The run's (stdout, stderr) result lines, progress stripped."""
    if mode.shows_progress:
        stdout = result_lines(run.stdout, progress=True)
        # Progress never goes to stderr, but its lines are padded too.
        stderr = result_lines(run.stderr, progress=False)
    else:
        stdout = run.stdout.splitlines(keepends=True)
        stderr = run.stderr.splitlines(keepends=True)
    if multi_file:
        stdout.sort()
        stderr.sort()
    return stdout, stderr


def expected_output(
    case: Case, mode: OutputMode
) -> tuple[list[str], list[str]]:
    stdout = list(case.successes) if mode.shows_successes else []
    stderr = list(case.errors) if mode.shows_errors else []
    if case.multi_file:
        stdout.sort()
        stderr.sort()
    return stdout, stderr


def human_readable_size(value: int) -> str:
    """Port of awscli/customizations/s3/utils.py:69 human_readable_size."""
    base = 1024
    size = float(value)
    if size == 1:
        return "1 Byte"
    if size < base:
        return f"{int(size)} Bytes"
    for index, suffix in enumerate(HUMANIZE_SUFFIXES):
        unit = base ** (index + 2)
        if round((size / unit) * base) < base:
            return f"{base * size / unit:.1f} {suffix}"
    raise ValueError(f"size out of range: {value}")


def progress_format_errors(segments: Sequence[str]) -> list[str]:
    errors: list[str] = []
    for segment in segments:
        match = BYTE_PROGRESS.fullmatch(segment) or FILE_PROGRESS.fullmatch(
            segment
        )
        if match is None:
            errors.append(f"not an upstream progress format: {segment!r}")
            continue
        # Upstream marks both totals as estimates exactly while calculating
        # (results.py:556-563).
        calculating = match["calculating"] is not None
        estimates = [match["remaining"]]
        if "expected" in match.re.groupindex:
            estimates.append(match["expected"])
        if any(value.startswith("~") != calculating for value in estimates):
            errors.append(f"estimate markers disagree: {segment!r}")
    return errors


def final_total_errors(segments: Sequence[str], size: int) -> list[str]:
    """The last progress segment of a single transfer reports every byte
    and its one file still remaining: its result line, which counts it,
    leaves no progress to redraw (results.py:422-429, 475-480)."""
    if not segments:
        return ["no progress segment was written"]
    last = segments[-1]
    match = BYTE_PROGRESS.fullmatch(last)
    total = human_readable_size(size)
    if match is None or match["calculating"] is not None:
        return [f"last progress segment is not final: {last!r}"]
    if match["completed"] != total or match["expected"] != total:
        return [f"last progress segment is not {total}/{total}: {last!r}"]
    if match["remaining"] != "1":
        return [f"last progress segment is not 1 file remaining: {last!r}"]
    return []


def terminator_errors(text: str, mode: OutputMode) -> list[str]:
    """Progress ends with '\\r', or a line ending when multiline.

    Line endings are folded to '\\n' on every host (results.py:540-549).
    """
    expected = "\n" if mode is PROGRESS_MULTILINE else "\r"
    errors: list[str] = []
    for match in re.finditer(r"([^\r\n]*)(\r\n|\r|\n|$)", text):
        segment, terminator = match.groups()
        if PROGRESS_SEGMENT.fullmatch(segment) and terminator != expected:
            errors.append(f"progress ends with {terminator!r}: {segment!r}")
    return errors


def progress_errors(run: Run, case: Case, mode: OutputMode) -> list[str]:
    segments = [
        segment
        for segment in re.split(r"[\r\n]", run.stdout)
        if PROGRESS_SEGMENT.match(segment)
    ]
    errors = progress_format_errors(segments)
    errors.extend(terminator_errors(run.stdout, mode))
    if mode is PROGRESS_MULTILINE:
        # Nothing is overwritten, so nothing is padded (results.py:540-551).
        errors.extend(
            f"padded multiline output: {line!r}"
            for line in run.stdout.splitlines()
            if line != line.rstrip(" ")
        )
    if case.final_total_bytes is not None:
        errors.extend(final_total_errors(segments, case.final_total_bytes))
    elif case.draws_progress and not segments:
        errors.append("no progress segment was written")
    return errors


def assert_run_meets_case(run: Run, case: Case, mode: OutputMode) -> None:
    report = run.describe()
    assert run.store.failures == [], report
    assert run.returncode == case.returncode, report
    assert run.local_files == {
        **case.local_files,
        **case.downloaded_files,
    }, report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **case.uploaded_objects,
    }, report
    assert sorted(run.store.responses) == list(case.responses), report
    assert shown_output(
        run, mode, multi_file=case.multi_file
    ) == expected_output(case, mode), report
    if mode.shows_progress:
        assert progress_errors(run, case, mode) == [], report


def upload_line(source: str, key: str, bucket: str = BUCKET) -> str:
    return f"upload: {source} to s3://{bucket}/{key}\n"


def download_line(key: str, destination: str) -> str:
    return f"download: s3://{BUCKET}/{key} to {destination}\n"


def skipped_line(path: str, reason: str) -> str:
    """A skipped local source's warning (utils.py:308-319)."""
    return f"warning: Skipping file {path}. {reason}\n"


# The file generator's reasons for skipping a local source
# (filegenerator.py:323-341).
SPECIAL_REASON: Final = (
    "File is character special device, block special device, FIFO, or socket."
)
UNREADABLE_REASON: Final = "File/Directory is not readable."
MISSING_REASON: Final = "File does not exist."

UPLOAD_SINGLE: Final = Case(
    name="upload-single",
    arguments=("s3", "cp", "upload.txt", f"s3://{BUCKET}/up/upload.txt"),
    local_files={"upload.txt": UPLOAD_FILE},
    uploaded_objects={(BUCKET, "up/upload.txt"): UPLOAD_FILE},
    # A local source shows relative to the working directory
    # (s3handler.py:379-380, utils.py:363-376).
    successes=(upload_line(local(".", "upload.txt"), "up/upload.txt"),),
    final_total_bytes=len(UPLOAD_FILE),
    draws_progress=True,
    responses=(("PutObject", 200),),
)
DOWNLOAD_SINGLE: Final = Case(
    name="download-single",
    arguments=("s3", "cp", f"s3://{BUCKET}/download/object.txt", "object.txt"),
    downloaded_files={"object.txt": DOWNLOAD_BODY},
    successes=(
        download_line("download/object.txt", local(".", "object.txt")),
    ),
    final_total_bytes=len(DOWNLOAD_BODY),
    draws_progress=True,
    responses=(("GetObject", 200), ("HeadObject", 200)),
)
DOWNLOAD_SMALL: Final = Case(
    name="download-small",
    arguments=("s3", "cp", f"s3://{BUCKET}/download/small.txt", "small.txt"),
    downloaded_files={"small.txt": SMALL_BODY},
    successes=(download_line("download/small.txt", local(".", "small.txt")),),
    final_total_bytes=len(SMALL_BODY),
    draws_progress=True,
    responses=(("GetObject", 200), ("HeadObject", 200)),
)
# A destination directory that exists takes the key's basename.
DOWNLOAD_EXISTING_DIRECTORY: Final = Case(
    name="download-existing-directory",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/download/object.txt",
        "existing",
    ),
    local_files={"existing/keep.txt": b"keep"},
    downloaded_files={"existing/object.txt": DOWNLOAD_BODY},
    successes=(
        download_line("download/object.txt", local("existing", "object.txt")),
    ),
    responses=(("GetObject", 200), ("HeadObject", 200)),
)
# --no-overwrite skips a download whose destination exists once the
# HeadObject finds the object, printing nothing (s3handler.py:548-570).
DOWNLOAD_NO_OVERWRITE_EXISTING: Final = Case(
    name="download-no-overwrite-existing",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/download/object.txt",
        "object.txt",
        "--no-overwrite",
    ),
    local_files={"object.txt": b"existing destination"},
    responses=(("HeadObject", 200),),
)
DOWNLOAD_RECURSIVE: Final = Case(
    name="download-recursive",
    arguments=("s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"),
    downloaded_files=TREE,
    successes=tuple(
        download_line(key, local(*key.split("/"))) for key in TREE
    ),
    multi_file=True,
    draws_progress=True,
    responses=(("GetObject", 200),) * 3 + (("ListObjectsV2", 200),),
)
# One key per page. The key that climbs out of the destination is skipped
# with a warning and status 2, the folder marker is not a file, and the
# key with `..` inside the prefix is saved where it normalizes to
# (s3handler.py:354-368).
DOWNLOAD_RECURSIVE_PAGES: Final = Case(
    name="download-recursive-pages",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/recursive/",
        "output",
        "--recursive",
        "--page-size",
        "1",
    ),
    returncode=2,
    downloaded_files={
        "output/empty": b"",
        "output/nested/a b+%": RECURSIVE_OBJECTS["recursive/nested/a b+%"],
        "output/nested/z": RECURSIVE_OBJECTS["recursive/nested/z"],
        "output/object": RECURSIVE_OBJECTS["recursive/object"],
        "output/normalized": RECURSIVE_OBJECTS["recursive/safe/../normalized"],
    },
    successes=tuple(
        download_line(f"recursive/{key}", local("output", *saved))
        for key, saved in (
            ("empty", ("empty",)),
            ("nested/a b+%", ("nested", "a b+%")),
            ("nested/z", ("nested", "z")),
            ("object", ("object",)),
            ("safe/../normalized", ("normalized",)),
        )
    ),
    errors=(skipped_line("../escape", "File references a parent directory."),),
    multi_file=True,
    responses=(("GetObject", 200),) * 5 + (("ListObjectsV2", 200),) * 7,
)
# --no-overwrite skips each object whose destination exists, before its
# GetObject.
DOWNLOAD_RECURSIVE_NO_OVERWRITE: Final = Case(
    name="download-recursive-no-overwrite",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/tree/",
        "tree",
        "--recursive",
        "--no-overwrite",
    ),
    local_files={"tree/b.txt": b"preserve existing"},
    downloaded_files={
        key: body for key, body in TREE.items() if key != "tree/b.txt"
    },
    successes=tuple(
        download_line(key, local(*key.split("/")))
        for key in TREE
        if key != "tree/b.txt"
    ),
    multi_file=True,
    responses=(("GetObject", 200),) * 2 + (("ListObjectsV2", 200),),
)
# A destination directory the CLI may not write fails each object: the
# CRT client opens its file before any GetObject and reports the error by
# its number and name.
DOWNLOAD_RECURSIVE_UNWRITABLE: Final = Case(
    name="download-recursive-unwritable",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/download/",
        "locked",
        "--recursive",
    ),
    special_files={"locked": UNWRITABLE_DIRECTORY},
    returncode=1,
    errors=tuple(
        f"download failed: s3://{BUCKET}/download/{name} to "
        f"{local('locked', name)} 43 (AWS_ERROR_NO_PERMISSION): User does "
        "not have permission to perform the requested action.\n"
        for name in ("object.txt", "small.txt")
    ),
    multi_file=True,
    responses=(("ListObjectsV2", 200),),
)
UPLOAD_RECURSIVE: Final = Case(
    name="upload-recursive",
    arguments=("s3", "cp", "src", f"s3://{BUCKET}/up/", "--recursive"),
    local_files=UPLOAD_TREE,
    uploaded_objects={
        (BUCKET, f"up/{path.removeprefix('src/')}"): body
        for path, body in UPLOAD_TREE.items()
    },
    successes=tuple(
        upload_line(local(*path.split("/")), f"up/{path[len('src/') :]}")
        for path in UPLOAD_TREE
    ),
    multi_file=True,
    draws_progress=True,
    responses=(("PutObject", 200),) * 3,
)
# A missing key fails the HeadObject the file generator sends, and the
# printer reports it as a fatal error (filegenerator.py:400-413,
# results.py:448-451).
DOWNLOAD_MISSING_KEY: Final = Case(
    name="download-missing-key",
    arguments=(
        "s3",
        "cp",
        f"s3://{BUCKET}/download/missing.txt",
        "missing.txt",
    ),
    returncode=1,
    errors=(
        "fatal error: An error occurred (404) when calling the HeadObject "
        'operation: Key "download/missing.txt" does not exist\n',
    ),
    responses=(("HeadObject", 404),),
)
UPLOAD_DENIED: Final = Case(
    name="upload-denied",
    arguments=("s3", "cp", "upload.txt", f"s3://{DENIED_BUCKET}/upload.txt"),
    local_files={"upload.txt": UPLOAD_FILE},
    returncode=1,
    # results.py:335 and 432-440.
    errors=(
        "upload failed: "
        f"{local('.', 'upload.txt')} to s3://{DENIED_BUCKET}/upload.txt "
        "An error occurred (AccessDenied) when calling the PutObject "
        "operation: Access Denied\n",
    ),
    responses=(("PutObject", 403),),
)


# A destination that names only the bucket, or ends in `/`, takes the
# source's basename as its key (fileformat.py:98-123).
UPLOAD_KEY_CASES: Final = (
    Case(
        name="upload-bucket-root",
        arguments=("s3", "cp", "upload.txt", f"s3://{BUCKET}"),
        local_files={"upload.txt": UPLOAD_FILE},
        uploaded_objects={(BUCKET, "upload.txt"): UPLOAD_FILE},
        successes=(upload_line(local(".", "upload.txt"), "upload.txt"),),
        responses=(("PutObject", 200),),
    ),
    Case(
        name="upload-trailing-slash",
        arguments=("s3", "cp", "upload.txt", f"s3://{BUCKET}/prefix/"),
        local_files={"upload.txt": UPLOAD_FILE},
        uploaded_objects={(BUCKET, "prefix/upload.txt"): UPLOAD_FILE},
        successes=(
            upload_line(local(".", "upload.txt"), "prefix/upload.txt"),
        ),
        responses=(("PutObject", 200),),
    ),
)
# --no-overwrite makes the PutObject conditional (utils.py:597-599), and
# the bucket refuses it for a key it holds. A refused precondition is a
# skip, which prints nothing (results.py:125-139).
UPLOAD_NO_OVERWRITE_EXISTING: Final = Case(
    name="upload-no-overwrite-existing",
    arguments=(
        "s3",
        "cp",
        "upload.txt",
        f"s3://{BUCKET}/download/object.txt",
        "--no-overwrite",
    ),
    local_files={"upload.txt": UPLOAD_FILE},
    responses=(("PutObject", 412),),
)


def skipped_source_case(
    name: str,
    source: str,
    destination: str,
    specials: Mapping[str, str],
    reason: str,
    local_files: Mapping[str, bytes] | None = None,
    shown_suffix: str = "",
) -> Case:
    """A source the file generator skips: a warning by absolute path,
    status 2, and no request."""
    return Case(
        name=name,
        arguments=("s3", "cp", source, f"s3://{BUCKET}/{destination}"),
        local_files=local_files or {},
        special_files=specials,
        returncode=2,
        errors=(skipped_line(local("<cwd>", source) + shown_suffix, reason),),
    )


SKIPPED_SOURCE_CASES: Final = (
    skipped_source_case(
        "upload-fifo", "pipe", "up/pipe", {"pipe": FIFO}, SPECIAL_REASON
    ),
    skipped_source_case(
        "upload-device-symlink",
        "null-link",
        "up/",
        {"null-link": DEVICE_LINK},
        SPECIAL_REASON,
    ),
    skipped_source_case(
        "upload-unreadable-file",
        "locked.txt",
        "up/locked.txt",
        {"locked.txt": UNREADABLE_FILE},
        UNREADABLE_REASON,
        local_files={"locked.txt": UPLOAD_FILE},
    ),
    skipped_source_case(
        "upload-unreadable-directory",
        "locked",
        "up/locked",
        {"locked": UNREADABLE_DIRECTORY},
        UNREADABLE_REASON,
        # An existing directory gains a separator (fileformat.py:87-90).
        shown_suffix=os.sep,
    ),
)


def case_modes(
    cases: Sequence[Case], modes: Sequence[OutputMode]
) -> list[object]:
    return [
        pytest.param(case, mode, id=f"{case.name}-{mode.name}")
        for case in cases
        for mode in modes
    ]


# Single transfers under --quiet, --no-progress, and --only-show-errors are
# test_cp.py's test_cp_{upload,download}_success_* tests; here they run
# under the modes that draw progress, whose final total they check.
OUTPUT_CASES: Final = [
    *case_modes((UPLOAD_SINGLE, DOWNLOAD_SINGLE), PROGRESS_MODES),
    # The first update is drawn however long the frequency.
    *case_modes((DOWNLOAD_SMALL,), (PROGRESS_FREQUENCY_HOUR,)),
    *case_modes(UPLOAD_KEY_CASES, (NO_PROGRESS,)),
    *case_modes((UPLOAD_NO_OVERWRITE_EXISTING,), (NO_PROGRESS,)),
    *case_modes(
        (DOWNLOAD_EXISTING_DIRECTORY, DOWNLOAD_NO_OVERWRITE_EXISTING),
        (NO_PROGRESS,),
    ),
    # --quiet hides the parent-reference warning but keeps its status.
    *case_modes((DOWNLOAD_RECURSIVE_PAGES,), (NO_PROGRESS, QUIET)),
    *case_modes(
        (DOWNLOAD_RECURSIVE_NO_OVERWRITE, DOWNLOAD_RECURSIVE_UNWRITABLE),
        (NO_PROGRESS,),
    ),
    *case_modes((DOWNLOAD_RECURSIVE, UPLOAD_RECURSIVE), ALL_MODES),
    # A fatal error prints the same line under every printer but --quiet's.
    *case_modes((DOWNLOAD_MISSING_KEY,), (QUIET, ONLY_SHOW_ERRORS, DEFAULT)),
    # test_cp.py's upload failure tests cover the other modes.
    *case_modes((UPLOAD_DENIED,), (DEFAULT,)),
    # --no-progress prints a warning as --only-show-errors does, and the
    # progress modes differ from the default only in redraw timing and
    # terminators, which the transfer cases above check.
    *case_modes(SKIPPED_SOURCE_CASES, (QUIET, ONLY_SHOW_ERRORS, DEFAULT)),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("case", "mode"), OUTPUT_CASES)
async def test_cp_output_under_output_mode(
    aws_cli: str, tmp_path: Path, case: Case, mode: OutputMode
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [*case.arguments, *mode.flags],
        local_files=case.local_files,
        special_files=case.special_files,
    )
    assert_run_meets_case(run, case, mode)


# Each case's operand gains `link/.././`, where `link` points into
# elsewhere/subdir. The kernel resolves `link/..` to elsewhere, while
# upstream normalizes the operand lexically (fileformat.py:87) and so
# selects the working directory. Different bytes and names under elsewhere
# expose a route that traverses the link.
DECOY_FILES: Final = {
    "elsewhere/upload.txt": b"wrong upload bytes",
    "elsewhere/src/wrong.txt": b"wrong recursive tree",
}
NORMALIZED_CASES: Final = (
    UPLOAD_SINGLE,
    DOWNLOAD_SINGLE,
    DOWNLOAD_RECURSIVE,
    UPLOAD_RECURSIVE,
    Case(
        name="download-new-directory",
        arguments=("s3", "cp", f"s3://{BUCKET}/download/object.txt", "new/"),
        downloaded_files={"new/object.txt": DOWNLOAD_BODY},
        successes=(
            download_line("download/object.txt", local("new", "object.txt")),
        ),
        responses=(("GetObject", 200), ("HeadObject", 200)),
    ),
    DOWNLOAD_EXISTING_DIRECTORY,
    # The raw operand exists through the link, so the existence check
    # passes (subcommands.py:1843-1849), and the normalized one does not, so
    # the file generator skips it.
    Case(
        name="upload-normalized-missing",
        arguments=("s3", "cp", "upload.txt", f"s3://{BUCKET}/up/file"),
        returncode=2,
    ),
    # The normalized operand exists and the raw one does not, so the
    # existence check fails before any request.
    Case(
        name="upload-raw-missing",
        arguments=("s3", "cp", "only-here.txt", f"s3://{BUCKET}/up/file"),
        local_files={"only-here.txt": b"exists only after normalization"},
        returncode=255,
    ),
)


def normalized_operand_case(
    case: Case, leading_slashes: int, work: Path
) -> Case:
    """`case` with its local operand reached through `link/.././`.

    With leading slashes the operand is absolute: POSIX keeps exactly two
    leading slashes through normalization and collapses three or more.
    """
    index = 2 if case.name.startswith("upload") else 3
    prefix = ""
    if leading_slashes:
        real_work = os.path.realpath(work).lstrip("/")
        prefix = "/" * leading_slashes + f"{real_work}/"
    operand = f"{prefix}link/.././{case.arguments[index]}"
    arguments = list(case.arguments)
    arguments[index] = operand
    # How a warning names the work directory after without_cwd: the
    # normalized operand keeps a double slash ahead of it.
    shown_work = "/<cwd>" if leading_slashes == 2 else "<cwd>"
    errors = case.errors
    if case.name == "upload-normalized-missing":
        errors = (skipped_line(f"{shown_work}/upload.txt", MISSING_REASON),)
    elif case.name == "upload-raw-missing":
        # A general exception's message (subcommands.py:1846-1849,
        # errorhandler.py:391-399, errorformat.py:37-41).
        shown = operand.replace(os.path.realpath(work), "<cwd>")
        errors = (
            "\n",
            f"aws: [ERROR]: The user-provided path {shown} does not exist.\n",
        )
    return Case(
        name=case.name,
        arguments=tuple(arguments),
        returncode=case.returncode,
        local_files={**case.local_files, **DECOY_FILES},
        downloaded_files=case.downloaded_files,
        uploaded_objects=case.uploaded_objects,
        successes=case.successes,
        errors=errors,
        multi_file=case.multi_file,
        responses=case.responses,
    )


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="POSIX directory symlink fixture")
@pytest.mark.parametrize("case", NORMALIZED_CASES, ids=lambda c: c.name)
@pytest.mark.parametrize(
    "leading_slashes",
    (0, 1, 2, 3),
    ids=("relative", "absolute", "double-slash", "triple-slash"),
)
async def test_cp_normalizes_local_operands(
    aws_cli: str, tmp_path: Path, case: Case, leading_slashes: int
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    normalized = normalized_operand_case(case, leading_slashes, work)
    run = await run_cp(
        aws_cli,
        tmp_path,
        [*normalized.arguments, *NO_PROGRESS.flags],
        local_files=normalized.local_files,
        directory_links={"link": "elsewhere/subdir"},
    )
    assert_run_meets_case(run, normalized, NO_PROGRESS)
    if case is DOWNLOAD_RECURSIVE:
        # Upstream creates the raw destination before it lists
        # (subcommands.py:1850-1854), and that one goes through the link.
        assert (work / "elsewhere" / "tree").is_dir(), run.describe()


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name == "nt", reason="Windows parent operands use Python"
)
async def test_cp_recursive_download_prepares_raw_destination(
    aws_cli: str, tmp_path: Path
) -> None:
    # Upstream makes the raw destination (subcommands.py:1850-1854), and
    # the kernel refuses to traverse the regular file, before any request.
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "regular-file/../out",
            "--recursive",
            "--no-progress",
        ],
        local_files={"regular-file": b"not a directory"},
    )
    case = Case(
        name="download-invalid-raw-directory",
        arguments=(),
        local_files={"regular-file": b"not a directory"},
        returncode=255,
        errors=(
            "\n",
            # os.makedirs makes the parent `regular-file/..` first.
            "aws: [ERROR]: [Errno 20] Not a directory: 'regular-file/..'\n",
        ),
    )
    assert_run_meets_case(run, case, NO_PROGRESS)
    assert not (tmp_path / "work" / "out").exists(), run.describe()


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="POSIX root destination")
async def test_cp_recursive_download_accepts_normalized_root(
    aws_cli: str, tmp_path: Path
) -> None:
    # The empty prefix exercises root preparation and listing without
    # writing any objects into the filesystem root.
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/empty-prefix/",
            "/tmp/..",
            "--recursive",
            "--no-progress",
        ],
    )
    case = Case(
        name="download-root",
        arguments=(),
        responses=(("ListObjectsV2", 200),),
    )
    assert_run_meets_case(run, case, NO_PROGRESS)


# Upstream's Glacier rule (s3handler.py:333-351, fileinfo.py:81-115):
# GLACIER and DEEP_ARCHIVE objects are skipped before any GET unless
# restored (HeadObject only) or forced, with a warning and status 2 unless
# the warnings are ignored; GLACIER_IR is exempt.
GLACIER_FLAGS: Final = {
    "bare": (),
    "ignore": ("--ignore-glacier-warnings",),
    "force": ("--force-glacier-transfer",),
}
ARCHIVED_CLASSES: Final = frozenset({"GLACIER", "DEEP_ARCHIVE"})
FORBIDDEN_GET: Final = (
    "An error occurred (InvalidObjectState) when calling the GetObject "
    "operation: The operation is not valid for the object's storage class"
)

# How upstream's CRT client reports the file it cannot open: its error
# code and aws-c-common's text for it.
UNSEARCHABLE_OPEN_ERROR: Final = (
    "43 (AWS_ERROR_NO_PERMISSION): User does not have permission to "
    "perform the requested action."
)


def storage_class_of(key: str) -> str:
    return GLACIER_STORAGE.get(key, ("STANDARD", None))[0]


def readable(key: str) -> bool:
    """Port of upstream's `FileInfo._is_glacier_object`, negated."""
    restore = GLACIER_STORAGE.get(key, ("STANDARD", None))[1]
    return storage_class_of(key) not in ARCHIVED_CLASSES or (
        'ongoing-request="false"' in (restore or "")
    )


def glacier_warning(key: str) -> str:
    return (
        f"warning: Skipping file s3://{BUCKET}/{key}. Object is of storage "
        "class GLACIER. Unable to perform download operations on GLACIER "
        "objects. You must restore the object to be able to perform the "
        "operation. See aws s3 download help for additional parameter "
        "options to ignore or force these transfers.\n"
    )


def download_failed_line(key: str, destination: str, error: str) -> str:
    return f"download failed: s3://{BUCKET}/{key} to {destination} {error}\n"


def single_glacier_case(key: str, flags: str) -> Case:
    """A single download the HeadObject's metadata decides."""
    body = GLACIER_OBJECTS[(BUCKET, key)]
    skipped = not readable(key) and flags != "force"
    rejected = not readable(key) and flags == "force"
    shown = local(".", "object.txt")
    successes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    if skipped and flags == "bare":
        errors = (glacier_warning(key),)
    elif rejected:
        # A forced GET of an unrestored object fails with the service's 403.
        errors = (download_failed_line(key, shown, FORBIDDEN_GET),)
    elif not skipped:
        successes = (download_line(key, shown),)
    responses: tuple[tuple[str, int], ...] = (("HeadObject", 200),)
    if not skipped:
        responses = (("GetObject", 403 if rejected else 200), *responses)
    return Case(
        name=f"single-{key.removeprefix('glacier/')}-{flags}",
        arguments=(
            "s3",
            "cp",
            f"s3://{BUCKET}/{key}",
            "object.txt",
            *GLACIER_FLAGS[flags],
        ),
        downloaded_files={} if skipped or rejected else {"object.txt": body},
        returncode=2 if skipped and flags == "bare" else 1 if rejected else 0,
        successes=successes,
        errors=errors,
        responses=responses,
    )


def recursive_glacier_case(flags: str) -> Case:
    """A recursive download the listed storage classes decide."""
    keys = [key for _, key in GLACIER_OBJECTS if key.startswith("glacier/")]
    # A listing carries no restore state, so every archived object counts.
    archived = [
        key for key in keys if storage_class_of(key) in ARCHIVED_CLASSES
    ]
    if flags == "force":
        fetched = keys
        downloaded = [key for key in keys if readable(key)]
    else:
        fetched = downloaded = [key for key in keys if key not in archived]
    failed = [key for key in fetched if key not in downloaded]
    errors = [
        download_failed_line(key, local(*key.split("/")), FORBIDDEN_GET)
        for key in failed
    ]
    if flags == "bare":
        errors.extend(glacier_warning(key) for key in archived)
    return Case(
        name=f"recursive-{flags}",
        arguments=(
            "s3",
            "cp",
            f"s3://{BUCKET}/glacier/",
            "glacier",
            "--recursive",
            *GLACIER_FLAGS[flags],
        ),
        downloaded_files={
            key: GLACIER_OBJECTS[(BUCKET, key)] for key in downloaded
        },
        returncode=1 if failed else 2 if flags == "bare" else 0,
        successes=tuple(
            download_line(key, local(*key.split("/"))) for key in downloaded
        ),
        errors=tuple(errors),
        multi_file=True,
        responses=tuple(
            sorted(
                [
                    ("ListObjectsV2", 200),
                    *(("GetObject", 200) for _ in downloaded),
                    *(("GetObject", 403) for _ in failed),
                ]
            )
        ),
    )


def escape_glacier_case(flags: str) -> Case:
    """An archived key whose basename `..` climbs out of the destination.

    Upstream sends the HeadObject and applies the Glacier rule before it
    acts on the destination, so only a forced transfer gets that far.
    There, upstream does not flag a bare `..` basename, and the GET fails
    on the unrestored object.
    """
    forced = flags == "force"
    errors: tuple[str, ...] = ()
    if flags == "bare":
        errors = (glacier_warning(ESCAPE_KEY),)
    elif forced:
        errors = (
            download_failed_line(ESCAPE_KEY, local(".", ".."), FORBIDDEN_GET),
        )
    return Case(
        name=f"escape-{flags}",
        arguments=(
            "s3",
            "cp",
            f"s3://{BUCKET}/{ESCAPE_KEY}",
            ".",
            *GLACIER_FLAGS[flags],
        ),
        returncode=1 if forced else 0 if flags == "ignore" else 2,
        errors=errors,
        responses=(
            (("GetObject", 403), ("HeadObject", 200))
            if forced
            else (("HeadObject", 200),)
        ),
    )


def unsearchable_glacier_case(flags: str) -> Case:
    """An archived source whose destination directory denies search.

    The Glacier rule decides first, so only a forced transfer reaches the
    destination. There, upstream's CRT client, which `auto` selects on
    every host, fails to open the file before it sends the GET.
    """
    forced = flags == "force"
    key = "glacier/frozen.txt"
    errors: tuple[str, ...] = ()
    if flags == "bare":
        errors = (glacier_warning(key),)
    elif forced:
        errors = (
            download_failed_line(
                key, local("locked", "object.txt"), UNSEARCHABLE_OPEN_ERROR
            ),
        )
    return Case(
        name=f"unsearchable-{flags}",
        arguments=(
            "s3",
            "cp",
            f"s3://{BUCKET}/{key}",
            "locked/object.txt",
            *GLACIER_FLAGS[flags],
        ),
        special_files={"locked": UNREADABLE_DIRECTORY},
        returncode=1 if forced else 0 if flags == "ignore" else 2,
        errors=errors,
        responses=(("HeadObject", 200),),
    )


GLACIER_CASES: Final = (
    # Readable objects download whatever the flags, so they run bare.
    single_glacier_case("glacier/instant.txt", "bare"),
    single_glacier_case("glacier/restored.txt", "bare"),
    *(
        single_glacier_case(key, "bare")
        for key in ("glacier/deep.txt", "glacier/restoring.txt")
    ),
    *(
        single_glacier_case("glacier/frozen.txt", flags)
        for flags in GLACIER_FLAGS
    ),
    *(recursive_glacier_case(flags) for flags in GLACIER_FLAGS),
    *(escape_glacier_case(flags) for flags in GLACIER_FLAGS),
    *(unsearchable_glacier_case(flags) for flags in GLACIER_FLAGS),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "mode"), case_modes(GLACIER_CASES, (QUIET, DEFAULT))
)
async def test_cp_glacier_handling(
    aws_cli: str, tmp_path: Path, case: Case, mode: OutputMode
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [*case.arguments, *mode.flags],
        special_files=case.special_files,
    )
    assert_run_meets_case(run, case, mode)


# The output flags a refused single upload runs under. Its totals are final
# before the request fails, so no progress reaches stdout under any of
# them; the failure line reaches stderr under all but `--quiet`.
REFUSED_UPLOAD_FLAGS: Final = [
    pytest.param([], id="default"),
    pytest.param(["--quiet"], id="quiet"),
    pytest.param(["--only-show-errors"], id="errors-only"),
    pytest.param(["--no-progress"], id="no-progress"),
    pytest.param(["--progress-frequency", "5"], id="progress-frequency"),
    pytest.param(["--progress-multiline"], id="progress-multiline"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("flags", REFUSED_UPLOAD_FLAGS)
async def test_cp_upload_to_a_refusing_endpoint_with_no_config_file(
    aws_cli: str, tmp_path: Path, flags: list[str]
) -> None:
    """A missing explicit config file is no error, so the upload reaches
    the endpoint, whose refusal it reports on the line upstream's printer
    writes. Forced native shows the command stays native under every flag:
    a hand-off would print the router's refusal instead. Another AWS CLI
    and the Python route ignore the variable. The reason that ends the
    line is the transport's, which the proxy tests in
    test_client_transport.py compare, so only the line's frame is
    compared here."""
    write_tree(tmp_path, {"object": b"object\n"})
    async with s3_runtime(InMemoryS3(), tmp_path) as (server, env):
        del env["HTTPS_PROXY"], env["HTTP_PROXY"]
        env["AWS_CONFIG_FILE"] = str(tmp_path / "missing" / "config")
        env["AWS_CLI_NATIVE_ROUTER"] = "native"
        with refusing_port() as port:
            endpoint = f"http://{LOOPBACK}:{port}"
            stdout, stderr, rc = await run_command(
                [
                    aws_cli,
                    "--endpoint-url",
                    endpoint,
                    "s3",
                    "cp",
                    "object",
                    f"s3://{BUCKET}/object",
                    *flags,
                ],
                env,
                cwd=tmp_path,
            )
    assert (rc, decoded(stdout)) == (1, ""), decoded(stderr)
    if flags == ["--quiet"]:
        assert decoded(stderr) == ""
    else:
        frame = f"upload failed: .{os.sep}object to s3://{BUCKET}/object "
        assert decoded(stderr).startswith(frame), decoded(stderr)
        assert decoded(stderr).count("\n") == 1, decoded(stderr)
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="directory modes are POSIX")
@pytest.mark.parametrize(
    "arguments,status,stderr",
    [
        pytest.param(
            ["s3://bucket/k", "unsearchable/out"],
            1,
            # A single download checks its source with HeadObject before it
            # touches its destination, so the refused endpoint fails it
            # first.
            "fatal error: Could not connect to the endpoint URL: "
            '"{endpoint}/bucket/k"\n',
            id="single",
        ),
        pytest.param(
            ["s3://bucket/p", "unsearchable/sub", "--recursive"],
            255,
            # A recursive download whose root cannot be created fails
            # before it lists anything.
            "\naws: [ERROR]: [Errno 13] Permission denied: "
            "'unsearchable/sub'\n",
            id="recursive",
        ),
    ],
)
async def test_cp_download_beneath_an_unsearchable_directory(
    aws_cli: str,
    tmp_path: Path,
    arguments: list[str],
    status: int,
    stderr: str,
) -> None:
    unsearchable = tmp_path / "unsearchable"
    unsearchable.mkdir()
    unsearchable.chmod(0o444)
    if os.access(unsearchable, os.X_OK):
        pytest.fail("the kernel ignores directory modes for this user")
    try:
        async with s3_runtime(InMemoryS3(), tmp_path) as (server, env):
            del env["HTTPS_PROXY"], env["HTTP_PROXY"]
            with refusing_port() as port:
                endpoint = f"http://{LOOPBACK}:{port}"
                result = await run_command(
                    [aws_cli, "--endpoint-url", endpoint, "s3", "cp", *arguments],
                    env,
                    cwd=tmp_path,
                )
    finally:
        unsearchable.chmod(0o755)
    assert result == (
        b"",
        stderr.format(endpoint=endpoint).encode(),
        status,
    ), result[1].decode()
    assert not server.requests
    assert list(unsearchable.iterdir()) == []
