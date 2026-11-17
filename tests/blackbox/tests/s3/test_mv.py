import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from localstub import HTTPResponse

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3helpers import user_agent_parts
from s3store import (
    REQUEST_IDS,
    InMemoryS3,
    ObjectKey,
    ScriptedS3,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    without_cwd,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
# Every PutObject and DeleteObject in this bucket is refused with
# AccessDenied; its objects can still be read.
DENIED_BUCKET: Final = "denied-bucket"
# The objects under "tree/", with the folder markers the S3 console creates
# for the prefix and a subfolder: zero-size keys ending in "/".
TREE: Final[dict[str, bytes]] = {
    "tree/": b"",
    "tree/a.txt": pattern_bytes("tree a", 100),
    "tree/b.txt": pattern_bytes("tree b", 1500),
    "tree/folder/": b"",
    "tree/nested/c.txt": pattern_bytes("tree c", 700),
}
# A recursive download skips folder markers (filegenerator.py:344-379), so
# a move of "tree/" leaves them in the bucket.
TREE_FILES: Final = sorted(key for key in TREE if not key.endswith("/"))
# Keys a move of "tree/" leaves alone, one sharing its first characters.
OUTSIDE: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "treehouse.txt"): pattern_bytes("treehouse", 10),
    (BUCKET, "other/d.txt"): pattern_bytes("other d", 20),
}
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    **{(BUCKET, key): body for key, body in TREE.items()},
    **OUTSIDE,
}
DENIED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (DENIED_BUCKET, key): body for key, body in TREE.items()
}
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
UPLOAD_TREE: Final[dict[str, bytes]] = {
    "src/one.txt": pattern_bytes("one", 400),
    "src/two.txt": pattern_bytes("two", 1200),
    "src/sub/three.txt": pattern_bytes("three", 50),
}
ACCESS_DENIED: Final = (
    "An error occurred (AccessDenied) when calling the {operation} "
    "operation: Access Denied"
)
GLACIER_WARNING: Final = (
    "warning: Skipping file s3://{bucket}/{key}. Object is of storage class "
    "GLACIER. Unable to perform download operations on GLACIER objects. You "
    "must restore the object to be able to perform the operation. See aws "
    "s3 download help for additional parameter options to ignore or force "
    "these transfers."
)
# A segment of the progress line the default printer redraws.
PROGRESS_SEGMENT: Final = re.compile(r"Completed .* file\(s\) remaining.*")


@dataclass(frozen=True)
class OutputMode:
    name: str
    flags: tuple[str, ...]
    # --only-show-errors drops successes and --quiet installs no printer
    # at all (s3handler.py:120-134).
    shows_successes: bool = True
    shows_errors: bool = True


NO_PROGRESS: Final = OutputMode("no-progress", ("--no-progress",))
# Draws progress, which `result_lines` strips.
DEFAULT: Final = OutputMode("default", ())
ONLY_SHOW_ERRORS: Final = OutputMode(
    "only-show-errors", ("--only-show-errors",), shows_successes=False
)
QUIET: Final = OutputMode(
    "quiet", ("--quiet",), shows_successes=False, shows_errors=False
)
MODES: Final = [
    pytest.param(mode, id=mode.name)
    for mode in (NO_PROGRESS, DEFAULT, ONLY_SHOW_ERRORS, QUIET)
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
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def requests(self) -> list[tuple[str, str]]:
        """Each request's operation and key, or a listing's prefix, in
        arrival order."""
        return [
            (
                request.operation_model.name,
                request.params.get("Key", request.params.get("Prefix", "")),
            )
            for request in self.store.received
        ]

    def keys(self, operation: str) -> list[str]:
        """The keys `operation` named, sorted: recursive moves run
        concurrently."""
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


async def run_mv(
    aws_cli: str,
    work: Path,
    store: InMemoryS3,
    *arguments: str,
    config: str = "",
    environment: Mapping[str, str] | None = None,
) -> Run:
    """Run `aws s3 mv <arguments>` once in `work` against `store`."""
    async with s3_runtime(store, work.parent) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "mv", *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        store=store,
    )


def without(
    objects: Mapping[ObjectKey, bytes], *keys: str
) -> dict[ObjectKey, bytes]:
    return {
        (bucket, key): body
        for (bucket, key), body in objects.items()
        if key not in keys
    }


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def local_entries(root: Path) -> list[str]:
    """Every file and directory under `root`, sorted, as POSIX paths."""
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def shown(mode: OutputMode, lines: list[str], *, errors: bool) -> list[str]:
    """`lines` if the mode's printer writes them, else nothing."""
    visible = mode.shows_errors if errors else mode.shows_successes
    return sorted(lines) if visible else []


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("destination", "key"),
    [
        pytest.param(f"s3://{BUCKET}/up/moved.txt", "up/moved.txt", id="key"),
        # A prefix ending in "/" or a bucket root takes the source's name.
        pytest.param(f"s3://{BUCKET}/up/", "up/a.txt", id="prefix"),
        pytest.param(f"s3://{BUCKET}", "a.txt", id="bucket"),
    ],
)
async def test_mv_upload_moves_the_file_to_its_key(
    aws_cli: str, work: Path, mode: OutputMode, destination: str, key: str
) -> None:
    write_tree(work, {"a.txt": UPLOAD_FILE})
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        "a.txt",
        destination,
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests() == [("PutObject", key)], report
    expected = [f"move: {local('.', 'a.txt')} to s3://{BUCKET}/{key}"]
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        shown(mode, expected, errors=False),
        "",
    ), report
    assert run.store.objects == {**SEED_OBJECTS, (BUCKET, key): UPLOAD_FILE}
    assert local_entries(work) == [], report


@pytest.mark.parametrize("mode", MODES)
async def test_mv_recursive_upload_moves_every_file_and_keeps_directories(
    aws_cli: str, work: Path, mode: OutputMode
) -> None:
    write_tree(work, UPLOAD_TREE)
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        "src",
        f"s3://{BUCKET}/up",
        "--recursive",
        *mode.flags,
    )
    report = run.report()
    uploaded = {
        (BUCKET, "up/" + name.removeprefix("src/")): body
        for name, body in UPLOAD_TREE.items()
    }
    assert run.store.failures == [], report
    assert run.keys("PutObject") == sorted(key for _, key in uploaded), report
    expected = [
        f"move: {local(*name.split('/'))} to s3://{BUCKET}/up/"
        + name.removeprefix("src/")
        for name in UPLOAD_TREE
    ]
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        shown(mode, expected, errors=False),
        "",
    ), report
    assert run.store.objects == {**SEED_OBJECTS, **uploaded}, report
    # Only the files go: the walk's directories stay, empty.
    assert local_entries(work) == ["src", "src/sub"], report


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("destination", "path"),
    [
        pytest.param("moved.txt", "moved.txt", id="file"),
        # An existing directory, or a name ending in a separator, takes the
        # key's basename.
        pytest.param(".", "a.txt", id="directory"),
        pytest.param(f"out{os.sep}", "out/a.txt", id="trailing-separator"),
    ],
)
async def test_mv_download_moves_the_object_to_its_file(
    aws_cli: str, work: Path, mode: OutputMode, destination: str, path: str
) -> None:
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/tree/a.txt",
        destination,
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    # The source is deleted only after its download.
    assert run.requests() == [
        ("HeadObject", "tree/a.txt"),
        ("GetObject", "tree/a.txt"),
        ("DeleteObject", "tree/a.txt"),
    ], report
    shown_path = local(*path.split("/"))
    if os.sep not in shown_path:
        shown_path = local(".", shown_path)
    expected = [f"move: s3://{BUCKET}/tree/a.txt to {shown_path}"]
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        shown(mode, expected, errors=False),
        "",
    ), report
    assert read_tree(work) == {path: TREE["tree/a.txt"]}, report
    assert run.store.objects == without(SEED_OBJECTS, "tree/a.txt"), report


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "source",
    [
        pytest.param(f"s3://{BUCKET}/tree", id="prefix"),
        pytest.param(f"s3://{BUCKET}/tree/", id="trailing-slash"),
    ],
)
async def test_mv_recursive_download_moves_every_object_but_folder_markers(
    aws_cli: str, work: Path, mode: OutputMode, source: str
) -> None:
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        source,
        "dest",
        "--recursive",
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", "tree/"), report
    assert run.keys("GetObject") == TREE_FILES, report
    assert run.keys("DeleteObject") == TREE_FILES, report
    expected = [
        f"move: s3://{BUCKET}/{key} to "
        + local("dest", *key.removeprefix("tree/").split("/"))
        for key in TREE_FILES
    ]
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        shown(mode, expected, errors=False),
        "",
    ), report
    assert read_tree(work) == {
        "dest/" + key.removeprefix("tree/"): TREE[key] for key in TREE_FILES
    }, report
    assert run.store.objects == without(SEED_OBJECTS, *TREE_FILES), report


@dataclass(frozen=True)
class DryRunCase:
    arguments: tuple[str, ...]
    lines: tuple[str, ...]
    # The requests a dry run still sends: a download's HeadObject or
    # listing.
    requests: tuple[tuple[str, str], ...] = ()


DRY_RUN_CASES: Final = {
    "upload": DryRunCase(
        ("a.txt", f"s3://{BUCKET}/up/a.txt"),
        (f"(dryrun) move: {local('.', 'a.txt')} to s3://{BUCKET}/up/a.txt",),
    ),
    "recursive-upload": DryRunCase(
        ("src", f"s3://{BUCKET}/up", "--recursive"),
        tuple(
            f"(dryrun) move: {local(*name.split('/'))} to s3://{BUCKET}/up/"
            + name.removeprefix("src/")
            for name in UPLOAD_TREE
        ),
    ),
    "download": DryRunCase(
        (f"s3://{BUCKET}/tree/a.txt", "a.txt"),
        (
            f"(dryrun) move: s3://{BUCKET}/tree/a.txt to "
            f"{local('.', 'a.txt')}",
        ),
        (("HeadObject", "tree/a.txt"),),
    ),
    "recursive-download": DryRunCase(
        (f"s3://{BUCKET}/tree/", "dest", "--recursive"),
        tuple(
            f"(dryrun) move: s3://{BUCKET}/{key} to "
            + local("dest", *key.removeprefix("tree/").split("/"))
            for key in TREE_FILES
        ),
        (("ListObjectsV2", "tree/"),),
    ),
}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", DRY_RUN_CASES)
async def test_mv_dryrun_reports_moves_and_changes_nothing(
    aws_cli: str, work: Path, mode: OutputMode, case: str
) -> None:
    dry_run = DRY_RUN_CASES[case]
    files = {"a.txt": UPLOAD_FILE, **UPLOAD_TREE}
    write_tree(work, files)
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        *dry_run.arguments,
        "--dryrun",
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests() == list(dry_run.requests), report
    # --only-show-errors drops successes, not dry run lines
    # (results.py:551-560).
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        shown(mode, list(dry_run.lines), errors=True),
        "",
    ), report
    assert run.store.objects == SEED_OBJECTS, report
    # A recursive download's destination is created before the dry run
    # (subcommands.py:1850-1855); nothing is written into it.
    assert read_tree(work) == files, report


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("arguments", "lines"),
    [
        pytest.param(
            ("a.txt", f"s3://{DENIED_BUCKET}/a.txt"),
            [(local(".", "a.txt"), "a.txt")],
            id="file",
        ),
        pytest.param(
            ("src", f"s3://{DENIED_BUCKET}/up", "--recursive"),
            [
                (local(*name.split("/")), "up/" + name.removeprefix("src/"))
                for name in UPLOAD_TREE
            ],
            id="recursive",
        ),
    ],
)
async def test_mv_refused_upload_keeps_the_file(
    aws_cli: str,
    work: Path,
    mode: OutputMode,
    arguments: tuple[str, ...],
    lines: list[tuple[str, str]],
) -> None:
    files = {"a.txt": UPLOAD_FILE, **UPLOAD_TREE}
    write_tree(work, files)
    store = InMemoryS3(denied_buckets=frozenset({DENIED_BUCKET}))
    run = await run_mv(aws_cli, work, store, *arguments, *mode.flags)
    report = run.report()
    error = ACCESS_DENIED.format(operation="PutObject")
    expected = [
        f"move failed: {path} to s3://{DENIED_BUCKET}/{key} {error}"
        for path, key in lines
    ]
    assert store.failures == [], report
    assert run.keys("PutObject") == sorted(key for _, key in lines), report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        1,
        [],
        shown(mode, expected, errors=True),
    ), report
    assert store.objects == {}, report
    assert read_tree(work) == files, report


@dataclass(frozen=True)
class Download:
    """Where a download of a key lands: the path under the working
    directory, and how result lines show it."""

    path: str
    shown: str


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("arguments", "downloads"),
    [
        pytest.param(
            (f"s3://{DENIED_BUCKET}/tree/a.txt", "a.txt"),
            {"tree/a.txt": Download("a.txt", local(".", "a.txt"))},
            id="object",
        ),
        pytest.param(
            (f"s3://{DENIED_BUCKET}/tree/", "dest", "--recursive"),
            {
                key: Download(
                    "dest/" + key.removeprefix("tree/"),
                    local("dest", *key.removeprefix("tree/").split("/")),
                )
                for key in TREE_FILES
            },
            id="recursive",
        ),
    ],
)
async def test_mv_refused_source_delete_fails_the_move_and_keeps_both_copies(
    aws_cli: str,
    work: Path,
    mode: OutputMode,
    arguments: tuple[str, ...],
    downloads: dict[str, Download],
) -> None:
    store = InMemoryS3(
        DENIED_OBJECTS, denied_buckets=frozenset({DENIED_BUCKET})
    )
    run = await run_mv(aws_cli, work, store, *arguments, *mode.flags)
    report = run.report()
    error = ACCESS_DENIED.format(operation="DeleteObject")
    expected = [
        f"move failed: s3://{DENIED_BUCKET}/{key} to {download.shown} {error}"
        for key, download in downloads.items()
    ]
    assert store.failures == [], report
    assert run.keys("DeleteObject") == sorted(downloads), report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        1,
        [],
        shown(mode, expected, errors=True),
    ), report
    # The download is not undone: the file stays beside its source.
    assert read_tree(work) == {
        download.path: TREE[key] for key, download in downloads.items()
    }, report
    assert store.objects == DENIED_OBJECTS, report


@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0,
    reason="a read-only directory does not deny unlinking on Windows or to "
    "root",
)
@pytest.mark.parametrize(
    ("arguments", "keys"),
    [
        pytest.param(
            (local("locked", "a.txt"), f"s3://{BUCKET}/a.txt"),
            {"a.txt": "a.txt"},
            id="file",
        ),
        pytest.param(
            ("locked", f"s3://{BUCKET}/up", "--recursive"),
            {"a.txt": "up/a.txt"},
            id="recursive",
        ),
    ],
)
async def test_mv_upload_whose_source_cannot_be_removed_fails_the_move(
    aws_cli: str,
    work: Path,
    arguments: tuple[str, ...],
    keys: dict[str, str],
) -> None:
    write_tree(work, {"locked/a.txt": UPLOAD_FILE})
    locked = work / "locked"
    locked.chmod(0o500)
    try:
        run = await run_mv(
            aws_cli, work, InMemoryS3(), *arguments, "--no-progress"
        )
    finally:
        locked.chmod(0o700)
    report = run.report()
    # os.remove's PermissionError, which names the absolute path the file
    # generator gave the upload (subscribers.py:183-187).
    error = (
        "[Errno 13] Permission denied: "
        f"'<cwd>{os.sep}{local('locked', 'a.txt')}'"
    )
    key = keys["a.txt"]
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr_lines()) == (
        1,
        "",
        [
            f"move failed: {local('locked', 'a.txt')} to s3://{BUCKET}/{key} "
            f"{error}"
        ],
    ), report
    # The upload itself succeeded.
    assert run.store.objects == {(BUCKET, key): UPLOAD_FILE}, report
    assert read_tree(work) == {"locked/a.txt": UPLOAD_FILE}, report


async def test_mv_no_overwrite_upload_of_an_existing_key_keeps_the_file(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, {"a.txt": UPLOAD_FILE})
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_mv(
        aws_cli,
        work,
        store,
        "a.txt",
        f"s3://{BUCKET}/tree/a.txt",
        "--no-overwrite",
        "--no-progress",
    )
    report = run.report()
    assert store.failures == [], report
    assert store.responses == [("PutObject", 412)], report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert store.objects == SEED_OBJECTS, report
    assert read_tree(work) == {"a.txt": UPLOAD_FILE}, report


async def test_mv_no_overwrite_download_onto_an_existing_file_keeps_the_object(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, {"a.txt": b"existing"})
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_mv(
        aws_cli,
        work,
        store,
        f"s3://{BUCKET}/tree/a.txt",
        "a.txt",
        "--no-overwrite",
        "--no-progress",
    )
    report = run.report()
    assert store.failures == [], report
    assert run.requests() == [("HeadObject", "tree/a.txt")], report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert store.objects == SEED_OBJECTS, report
    assert read_tree(work) == {"a.txt": b"existing"}, report


@pytest.mark.parametrize(
    ("flags", "returncode", "stderr"),
    [
        # The warning names the download it skips, not the move.
        pytest.param(
            (),
            2,
            GLACIER_WARNING.format(bucket=BUCKET, key="tree/a.txt") + "\n",
            id="warn",
        ),
        pytest.param(("--ignore-glacier-warnings",), 0, "", id="ignore"),
    ],
)
async def test_mv_glacier_object_is_skipped_and_kept(
    aws_cli: str,
    work: Path,
    flags: tuple[str, ...],
    returncode: int,
    stderr: str,
) -> None:
    store = InMemoryS3(
        SEED_OBJECTS, storage={"tree/a.txt": ("GLACIER", None)}
    )
    run = await run_mv(
        aws_cli,
        work,
        store,
        f"s3://{BUCKET}/tree/a.txt",
        "a.txt",
        "--no-progress",
        *flags,
    )
    report = run.report()
    assert store.failures == [], report
    assert run.requests() == [("HeadObject", "tree/a.txt")], report
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        "",
        stderr,
    ), report
    assert store.objects == SEED_OBJECTS, report
    assert read_tree(work) == {}, report


async def test_mv_recursive_download_filters_select_what_moves(
    aws_cli: str, work: Path
) -> None:
    run = await run_mv(
        aws_cli,
        work,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/tree/",
        "dest",
        "--recursive",
        "--exclude",
        "*",
        "--include",
        "*.txt",
        "--exclude",
        "nested/*",
        "--no-progress",
    )
    report = run.report()
    moved = ["tree/a.txt", "tree/b.txt"]
    assert run.store.failures == [], report
    assert run.keys("DeleteObject") == moved, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [
            f"move: s3://{BUCKET}/{key} to "
            + local("dest", key.removeprefix("tree/"))
            for key in moved
        ],
        "",
    ), report
    assert read_tree(work) == {
        "dest/" + key.removeprefix("tree/"): TREE[key] for key in moved
    }, report
    assert run.store.objects == without(SEED_OBJECTS, *moved), report


async def test_mv_retries_a_failed_source_delete(
    aws_cli: str, work: Path
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS, failing=frozenset({"DeleteObject"}), failures=1
    )
    run = await run_mv(
        aws_cli,
        work,
        store,
        f"s3://{BUCKET}/tree/a.txt",
        "a.txt",
        "--no-progress",
    )
    report = run.report()
    assert store.failures == [], report
    assert [
        response for response in store.responses if response[0] == "DeleteObject"
    ] == [("DeleteObject", 500), ("DeleteObject", 204)], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        f"move: s3://{BUCKET}/tree/a.txt to {local('.', 'a.txt')}\n",
        "",
    ), report
    assert read_tree(work) == {"a.txt": TREE["tree/a.txt"]}, report
    assert store.objects == without(SEED_OBJECTS, "tree/a.txt"), report


@pytest.mark.skipif(os.name == "nt", reason="creates a symlink")
async def test_mv_recursive_upload_removes_a_symlink_not_its_target(
    aws_cli: str, work: Path
) -> None:
    write_tree(work, {"target.txt": UPLOAD_FILE, "src/plain.txt": b"plain"})
    (work / "src" / "link.txt").symlink_to(work / "target.txt")
    store = InMemoryS3()
    run = await run_mv(
        aws_cli,
        work,
        store,
        "src",
        f"s3://{BUCKET}/up",
        "--recursive",
        "--no-progress",
    )
    report = run.report()
    assert store.failures == [], report
    assert (run.returncode, run.stderr) == (0, ""), report
    # The walk follows the link for the upload's body, and the move then
    # removes the link it walked.
    assert store.objects == {
        (BUCKET, "up/link.txt"): UPLOAD_FILE,
        (BUCKET, "up/plain.txt"): b"plain",
    }, report
    assert local_entries(work) == ["src", "target.txt"], report
    assert read_tree(work) == {"target.txt": UPLOAD_FILE}, report


async def test_mv_missing_upload_source_fails_before_any_request(
    aws_cli: str, work: Path
) -> None:
    store = InMemoryS3()
    run = await run_mv(
        aws_cli, work, store, "missing.txt", f"s3://{BUCKET}/missing.txt"
    )
    report = run.report()
    assert (run.returncode, run.stdout) == (255, ""), report
    assert "The user-provided path missing.txt does not exist." in (
        run.stderr
    ), report
    assert store.received == [], report


@pytest.mark.parametrize(
    ("flags", "environment"),
    [
        pytest.param(("--validate-same-s3-paths",), {}, id="flag"),
        pytest.param(
            (),
            {"AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS": "true"},
            id="environment",
        ),
    ],
)
@pytest.mark.parametrize("direction", ["upload", "download"])
async def test_mv_path_validation_only_applies_between_s3_paths(
    aws_cli: str,
    work: Path,
    flags: tuple[str, ...],
    environment: dict[str, str],
    direction: str,
) -> None:
    write_tree(work, {"a.txt": UPLOAD_FILE})
    store = InMemoryS3(SEED_OBJECTS)
    if direction == "upload":
        operands = ("a.txt", f"s3://{BUCKET}/up/a.txt")
        line = f"move: {local('.', 'a.txt')} to s3://{BUCKET}/up/a.txt\n"
        objects = {**SEED_OBJECTS, (BUCKET, "up/a.txt"): UPLOAD_FILE}
        files: dict[str, bytes] = {}
    else:
        operands = (f"s3://{BUCKET}/tree/b.txt", "b.txt")
        line = f"move: s3://{BUCKET}/tree/b.txt to {local('.', 'b.txt')}\n"
        objects = without(SEED_OBJECTS, "tree/b.txt")
        files = {"a.txt": UPLOAD_FILE, "b.txt": TREE["tree/b.txt"]}
    run = await run_mv(
        aws_cli,
        work,
        store,
        *operands,
        "--no-progress",
        *flags,
        environment=environment,
    )
    report = run.report()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (0, line, ""), report
    assert store.objects == objects, report
    assert read_tree(work) == files, report


# botocore's feature ids (useragent.py:56-122).
RETRY_STANDARD: Final = "E"
S3_TRANSFER: Final = "G"
REQUEST_CRC64: Final = "W"
REQUEST_WHEN_SUPPORTED: Final = "Z"
RESPONSE_WHEN_SUPPORTED: Final = "b"
CRT_EXPLICIT: Final = "Ae"
CRT_AUTO: Final = "Ag"
CRT_CONFIG: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"


@pytest.mark.parametrize(
    ("config", "crt_feature"),
    [
        pytest.param("", CRT_AUTO, id="auto"),
        pytest.param(CRT_CONFIG, CRT_EXPLICIT, id="crt-preferred"),
    ],
)
@pytest.mark.parametrize(
    ("arguments", "operations"),
    [
        pytest.param(
            ("a.txt", f"s3://{BUCKET}/up/a.txt"), ["PutObject"], id="upload"
        ),
        pytest.param(
            (f"s3://{BUCKET}/tree/a.txt", "a.txt"),
            ["HeadObject", "GetObject", "DeleteObject"],
            id="download",
        ),
    ],
)
async def test_mv_user_agent_names_the_command(
    aws_cli: str,
    work: Path,
    config: str,
    crt_feature: str,
    arguments: tuple[str, ...],
    operations: list[str],
) -> None:
    write_tree(work, {"a.txt": UPLOAD_FILE})
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_mv(
        aws_cli,
        work,
        store,
        *arguments,
        "--no-progress",
        config=config,
        # The session id would open the session database under HOME.
        environment={"AWS_CLI_SESSION_ID_DISABLED": "true"},
    )
    report = run.report()
    assert store.failures == [], report
    assert run.returncode == 0, report
    source = {
        RETRY_STANDARD,
        REQUEST_WHEN_SUPPORTED,
        RESPONSE_WHEN_SUPPORTED,
        S3_TRANSFER,
    }
    seen = []
    for request in store.received:
        operation = request.operation_model.name
        user_agent = request.wire_request.headers.get("user-agent", "")
        seen.append(operation)
        if operation == "DeleteObject":
            # The source client deletes from the CRT's done callback,
            # outside the command's context, so it names only the features
            # it captured when it was created, before the transfer client's
            # (session.py:937, subscribers.py:132-160).
            expected = source
        elif operation == "PutObject":
            expected = source | {crt_feature, REQUEST_CRC64}
        else:
            expected = source | {crt_feature}
        assert user_agent_parts(user_agent) == (
            frozenset(expected),
            frozenset({"md/prompt#off", "md/command#s3.mv"}),
        ), f"{operation}: {user_agent}\n{report}"
    # A CRT-preferred client may send its own discovery HEAD and ranged
    # GETs, so each operation is counted once.
    assert list(dict.fromkeys(seen)) == operations, report


# The region the redirecting bucket lives in; the CLI is configured for
# us-east-1.
TARGET_REGION: Final = "us-west-2"
SIGNING_REGION: Final = re.compile(r"Credential=[^/]+/[^/]+/([^/]+)/s3/")


class RegionalS3(InMemoryS3):
    """A bucket in TARGET_REGION: a request signed for any other region gets
    S3's PermanentRedirect naming the region in its header. Records each
    request's operation, signing region, and status."""

    def __init__(self, objects: Mapping[ObjectKey, bytes]) -> None:
        super().__init__(objects)
        self.signed: list[tuple[str, str, int]] = []

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        operation = reconstructed.operation_model.name
        match = SIGNING_REGION.search(
            reconstructed.wire_request.headers.get("Authorization", "")
        )
        if match is None:
            raise AssertionError("request did not carry an S3 signing region")
        if operation == "HeadBucket":
            response = HTTPResponse.raw(
                b"", headers={"x-amz-bucket-region": TARGET_REGION}
            )
        elif match[1] != TARGET_REGION:
            response = HTTPResponse.raw(
                b"<Error><Code>PermanentRedirect</Code>"
                b"<Message>Wrong region</Message></Error>",
                status=301,
                headers={
                    "Content-Type": "application/xml",
                    "x-amz-bucket-region": TARGET_REGION,
                    **REQUEST_IDS,
                },
            )
        else:
            response = super().dispatch(reconstructed)
        self.signed.append((operation, match[1], response.status))
        return response


async def test_mv_download_deletes_its_source_in_the_bucket_region(
    aws_cli: str, work: Path
) -> None:
    store = RegionalS3(SEED_OBJECTS)
    run = await run_mv(
        aws_cli,
        work,
        store,
        f"s3://{BUCKET}/tree/a.txt",
        "a.txt",
        "--no-progress",
    )
    report = f"{run.report()}signed: {store.signed}\n"
    assert store.failures == [], report
    # Once the download found the bucket's region, the delete goes there.
    assert [
        signed for signed in store.signed if signed[0] == "DeleteObject"
    ] == [("DeleteObject", TARGET_REGION, 204)], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        f"move: s3://{BUCKET}/tree/a.txt to {local('.', 'a.txt')}\n",
        "",
    ), report
    assert read_tree(work) == {"a.txt": TREE["tree/a.txt"]}, report
    assert store.objects == without(SEED_OBJECTS, "tree/a.txt"), report
