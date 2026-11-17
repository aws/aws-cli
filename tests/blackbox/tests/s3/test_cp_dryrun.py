"""What `s3 cp --dryrun` reports, and what it leaves alone.

Upstream's transfer request submitters (customizations/s3/s3handler.py)
check for a dry run only after a source has passed every warning handler.
The file generator still lists the bucket, heads a single object, and walks
and inspects local sources. Each handler still warns about, or silently
skips, what it would skip without the flag: a Glacier object, a key that
references a parent directory, an existing destination under
--no-overwrite, and a source the walk cannot read. A source that passes
them becomes a DryRunResult in place of its transfer, which every printer
except --quiet's writes on stdout as `(dryrun) <type>: <source> to
<destination>`, --only-show-errors' included.

Nothing is queued. No request goes out beyond the listing and the HEAD,
and nothing local is created except the root of a recursive download,
which the command makes before it lists anything. An upload's own request
never exists, so neither do the failures only that request reports: the
endpoint rules' refusal, a key botocore cannot encode, and a directory
read as a file. A download's HEAD or listing still carries them. The exit
status counts only the warnings.

Each test runs one command against the in-memory bucket of s3store.py and
asserts the exit status, the output, the local tree, and the requests.
"""

import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
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

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
DOTTED_BUCKET: Final = "bucket.with.dots"
BODY: Final = pattern_bytes("body", 300)
# The rules refuse to address a dotted bucket's S3 Accelerate host.
ACCELERATE_CONFIG: Final = "[default]\ns3 =\n  use_accelerate_endpoint = true\n"
PATH_STYLE: Final = "Path-style addressing cannot be used with S3 Accelerate"
# Upstream's MAX_UPLOAD_SIZE (customizations/s3/utils.py): 10,000 parts of
# 5 GiB, which its human_readable_size prints as 48.8 TiB.
MAX_UPLOAD_SIZE: Final = 5 * 1024**3 * 10_000
# What upstream's file-count progress prints while no transfer is queued
# and the file generator has not finished (results.py).
CALCULATING: Final = "Completed 0 file(s) with ~0 file(s) remaining (calculating...)"


@dataclass(frozen=True)
class OutputMode:
    name: str
    flags: tuple[str, ...]
    # --quiet installs no printer; every other printer writes dry runs.
    prints: bool = True


OUTPUT_MODES: Final = [
    pytest.param(OutputMode("default", ()), id="default"),
    pytest.param(OutputMode("no-progress", ("--no-progress",)), id="no-progress"),
    pytest.param(
        OutputMode("only-show-errors", ("--only-show-errors",)),
        id="only-show-errors",
    ),
    pytest.param(OutputMode("quiet", ("--quiet",), prints=False), id="quiet"),
]


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    work: Path
    store: InMemoryS3

    def describe(self) -> str:
        return (
            f"rc={self.returncode}\nstdout={self.stdout!r}\n"
            f"stderr={self.stderr!r}\n"
            f"operations={self.store.operations()}\n"
            f"failures={self.store.failures}"
        )

    def stored(self) -> dict[str, bytes]:
        return {key: body for (_, key), body in self.store.objects.items()}


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    *,
    local_files: Mapping[str, bytes] | None = None,
    objects: Mapping[ObjectKey, bytes] | None = None,
    storage: Mapping[str, tuple[str, str | None]] | None = None,
    config: str = "",
) -> Run:
    """Run `aws <arguments>` in tmp_path/work against a seeded bucket.

    The output names the working directory as `<cwd>`.
    """
    work = tmp_path / "work"
    work.mkdir(parents=True, exist_ok=True)
    write_tree(work, local_files or {})
    store = InMemoryS3(objects, storage=storage)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments], env, cwd=work, stdin=None
        )
    assert not store.failures, store.failures
    return Run(
        returncode,
        decoded(without_cwd(stdout, work)),
        decoded(without_cwd(stderr, work)),
        work,
        store,
    )


def local(name: str) -> str:
    """A relative local path as result lines show it, with os.sep: upstream
    joins the relpath of its directory, `.` for the working directory."""
    directory, _, basename = name.rpartition("/")
    return os.path.join(*(directory or ".").split("/"), basename)


def dry_upload(source: str, key: str, bucket: str = BUCKET) -> str:
    return f"(dryrun) upload: {local(source)} to s3://{bucket}/{key}\n"


def dry_download(key: str, destination: str) -> str:
    return f"(dryrun) download: s3://{BUCKET}/{key} to {local(destination)}\n"


def glacier_warning(key: str) -> str:
    return (
        f"warning: Skipping file s3://{BUCKET}/{key}. Object is of storage "
        "class GLACIER. Unable to perform download operations on GLACIER "
        "objects. You must restore the object to be able to perform the "
        "operation. See aws s3 download help for additional parameter "
        "options to ignore or force these transfers.\n"
    )


def shown(lines: Sequence[str], mode: OutputMode) -> str:
    return "".join(lines) if mode.prints else ""


@pytest.mark.parametrize("mode", OUTPUT_MODES)
async def test_cp_dryrun_single_download_heads_its_object_and_writes_nothing(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/dir/key.txt",
            "local.txt",
            "--dryrun",
            *mode.flags,
        ],
        objects={(BUCKET, "dir/key.txt"): BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == shown(
        [dry_download("dir/key.txt", "local.txt")], mode
    ), run.describe()
    assert run.store.operations() == ["HeadObject"], run.describe()
    assert read_tree(run.work) == {}


@pytest.mark.parametrize("mode", OUTPUT_MODES)
async def test_cp_dryrun_recursive_upload_names_each_file_in_walk_order(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    # The walk sorts a directory's name with a separator after it, so
    # `nested-d.txt` comes before `nested/c.txt`.
    names = ("a.txt", "b.txt", "nested-d.txt", "nested/c.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--dryrun",
            *mode.flags,
        ],
        local_files={f"src/{name}": BODY for name in reversed(names)},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == shown(
        [dry_upload(f"src/{name}", f"prefix/{name}") for name in names], mode
    ), run.describe()
    assert run.store.operations() == []
    assert run.stored() == {}


@pytest.mark.parametrize("mode", OUTPUT_MODES)
async def test_cp_dryrun_recursive_download_creates_only_its_destination_root(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    # The command makes a missing destination root before it lists, dry run
    # or not; the directories under it come only with a download.
    keys = ("tree/a.txt", "tree/nested/b.txt", "tree/z.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "out/sub",
            "--recursive",
            "--dryrun",
            *mode.flags,
        ],
        objects={(BUCKET, key): BODY for key in keys},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == shown(
        [
            dry_download(key, "out/sub/" + key.removeprefix("tree/"))
            for key in keys
        ],
        mode,
    ), run.describe()
    assert run.store.operations() == ["ListObjectsV2"], run.describe()
    assert sorted(run.work.rglob("*")) == [
        run.work / "out",
        run.work / "out" / "sub",
    ]


async def test_cp_dryrun_single_download_creates_no_directory_destination(
    aws_cli: str, tmp_path: Path
) -> None:
    # A trailing separator names a directory, which only a download makes.
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/key.txt",
            f"missing{os.sep}dir{os.sep}",
            "--dryrun",
        ],
        objects={(BUCKET, "key.txt"): BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == dry_download("key.txt", "missing/dir/key.txt")
    assert run.store.operations() == ["HeadObject"]
    assert not (run.work / "missing").exists()


@pytest.mark.parametrize(
    ("arguments", "key", "destination"),
    [
        pytest.param(
            ("s3://bucket/key.txt", "blocker/local.txt"),
            "key.txt",
            "blocker/local.txt",
            id="single",
        ),
        pytest.param(
            ("s3://bucket/tree/", "out", "--recursive"),
            "tree/blocker/b.txt",
            "out/blocker/b.txt",
            id="recursive",
        ),
    ],
)
async def test_cp_dryrun_download_never_creates_its_parent_directory(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    key: str,
    destination: str,
) -> None:
    # A download through a file fails making its parent; a dry run never
    # makes it, so it reports the download instead.
    blocker = destination.rpartition("/")[0]
    run = await run_cp(
        aws_cli,
        tmp_path,
        ["s3", "cp", *arguments, "--no-progress", "--dryrun"],
        local_files={blocker: b"a file"},
        objects={(BUCKET, key): BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == dry_download(key, destination)
    assert read_tree(run.work) == {blocker: b"a file"}
    assert "GetObject" not in run.store.operations()


async def test_cp_dryrun_single_download_of_a_parent_basename_reports_it(
    aws_cli: str, tmp_path: Path
) -> None:
    # Upstream does not flag a bare `..` basename, which maps to the
    # directory's parent: a download sends its GET and creates nothing.
    run = await run_cp(
        aws_cli,
        tmp_path,
        ["s3", "cp", f"s3://{BUCKET}/up/..", ".", "--dryrun"],
        objects={(BUCKET, "up/.."): BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == dry_download("up/..", "..")
    assert run.store.operations() == ["HeadObject"]


@pytest.mark.parametrize(
    "mode",
    [
        param
        for param in OUTPUT_MODES
        if param.id in {"default", "no-progress", "quiet"}
    ],
)
async def test_cp_dryrun_recursive_download_still_warns_about_what_it_skips(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    # The listing's order: the parent reference, then the readable object,
    # then the Glacier one. Each warning redraws progress, and with nothing
    # queued, that progress counts no files and is never final. A dry run's
    # line pads over the progress before it, and redraws none.
    keys = ("tree/../escape.txt", "tree/a.txt", "tree/frozen.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "out",
            "--recursive",
            "--dryrun",
            *mode.flags,
        ],
        objects={(BUCKET, key): BODY for key in keys},
        storage={"tree/frozen.txt": ("GLACIER", None)},
    )
    escape = (
        "warning: Skipping file ../escape.txt. "
        "File references a parent directory.\n"
    )
    line = dry_download("tree/a.txt", "out/a.txt")
    expected_stdout = shown([line], mode)
    if mode.name == "default":
        width = len(CALCULATING)
        expected_stdout = (
            f"{CALCULATING}\r{line[:-1].ljust(width)}\n"
            f"{CALCULATING}\r{' ' * width}\n"
        )
    assert run.returncode == 2, run.describe()
    assert run.stdout == expected_stdout, run.describe()
    assert run.stderr == shown(
        [escape, glacier_warning("tree/frozen.txt")], mode
    ), run.describe()
    assert run.store.operations() == ["ListObjectsV2"]
    assert read_tree(run.work) == {}


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        pytest.param(
            ("s3://bucket/tree/a.txt", "a.txt"), [], id="single"
        ),
        pytest.param(
            ("s3://bucket/tree/", ".", "--recursive"),
            [dry_download("tree/b.txt", "b.txt")],
            id="recursive",
        ),
    ],
)
async def test_cp_dryrun_no_overwrite_silently_skips_existing_destinations(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    expected: list[str],
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        ["s3", "cp", *arguments, "--no-overwrite", "--dryrun"],
        local_files={"a.txt": b"old"},
        objects={(BUCKET, "tree/a.txt"): BODY, (BUCKET, "tree/b.txt"): BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == "".join(expected), run.describe()
    assert read_tree(run.work) == {"a.txt": b"old"}
    assert "GetObject" not in run.store.operations()


async def test_cp_dryrun_recursive_download_applies_filters(
    aws_cli: str, tmp_path: Path
) -> None:
    keys = ("tree/a.txt", "tree/b.bin", "tree/nested/c.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "out",
            "--recursive",
            "--exclude",
            "*.txt",
            "--include",
            "nested/*",
            "--dryrun",
        ],
        objects={(BUCKET, key): BODY for key in keys},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == (
        dry_download("tree/b.bin", "out/b.bin")
        + dry_download("tree/nested/c.txt", "out/nested/c.txt")
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink fixture")
async def test_cp_dryrun_recursive_upload_still_warns_about_skipped_sources(
    aws_cli: str, tmp_path: Path
) -> None:
    source = tmp_path / "work" / "src"
    source.mkdir(parents=True)
    (source / "dangling").symlink_to("absent")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            "--dryrun",
        ],
        local_files={"src/a.txt": BODY},
    )
    assert run.returncode == 2, run.describe()
    assert run.stdout == dry_upload("src/a.txt", "prefix/a.txt")
    assert run.stderr == (
        "warning: Skipping file <cwd>/src/dangling. File does not exist.\n"
    )
    assert run.store.operations() == []


async def test_cp_dryrun_upload_refused_by_the_endpoint_rules_is_reported(
    aws_cli: str, tmp_path: Path
) -> None:
    # The rules refuse each PutObject as it is sent, and a dry run sends
    # none.
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "upload.txt",
            f"s3://{DOTTED_BUCKET}/key.txt",
            "--no-progress",
            "--dryrun",
        ],
        local_files={"upload.txt": BODY},
        config=ACCELERATE_CONFIG,
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == dry_upload("upload.txt", "key.txt", DOTTED_BUCKET)
    assert run.store.operations() == []


async def test_cp_dryrun_single_upload_of_a_directory_is_reported(
    aws_cli: str, tmp_path: Path
) -> None:
    # Upstream queues a directory named without --recursive as one file,
    # and only the upload's read of it fails.
    (tmp_path / "work" / "src").mkdir(parents=True)
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/key.txt",
            "--no-progress",
            "--dryrun",
        ],
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == f"(dryrun) upload: src{os.sep} to s3://{BUCKET}/key.txt\n"
    assert run.store.operations() == []


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux names files with any bytes"
)
async def test_cp_dryrun_recursive_upload_reports_a_key_botocore_cannot_encode(
    aws_cli: str, tmp_path: Path
) -> None:
    # The key fails to encode only as its PutObject is serialized.
    name = os.fsdecode(b"\xff.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            "--dryrun",
        ],
        local_files={f"src/{name}": BODY},
    )
    assert (run.returncode, run.stderr) == (0, ""), run.describe()
    assert run.stdout == dry_upload(f"src/{name}", f"prefix/{name}")
    assert run.store.operations() == []


@pytest.mark.parametrize(
    ("arguments", "config"),
    [
        pytest.param(
            (f"s3://{DOTTED_BUCKET}/key.txt", "key.txt"),
            ACCELERATE_CONFIG,
            id="rules-single",
        ),
        pytest.param(
            (f"s3://{DOTTED_BUCKET}/", "out", "--recursive"),
            ACCELERATE_CONFIG,
            id="rules-recursive",
        ),
        pytest.param(
            (f"s3://{BUCKET}/key-".encode() + b"\xff", "out/"),
            "",
            id="undecodable-key",
            marks=pytest.mark.skipif(
                os.name != "posix", reason="POSIX byte arguments"
            ),
        ),
    ],
)
async def test_cp_dryrun_download_refusal_fails_as_without_it(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str | bytes, ...],
    config: str,
) -> None:
    # A download's HEAD or listing is refused before the dry run could
    # stand in for any transfer.
    command = ["s3", "cp", *map(os.fsdecode, arguments), "--no-progress"]
    actual = await run_cp(
        aws_cli, tmp_path / "dryrun", [*command, "--dryrun"], config=config
    )
    expected = await run_cp(aws_cli, tmp_path / "real", command, config=config)
    assert expected.returncode == 1, expected.describe()
    assert (actual.returncode, actual.stdout, actual.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    ), actual.describe()
    assert actual.store.operations() == [], actual.describe()


async def test_cp_dryrun_download_refused_by_the_rules_names_the_rule(
    aws_cli: str, tmp_path: Path
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{DOTTED_BUCKET}/key.txt",
            "key.txt",
            "--dryrun",
        ],
        config=ACCELERATE_CONFIG,
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"fatal error: {PATH_STYLE}\n",
    ), run.describe()


@pytest.mark.skipif(os.name == "nt", reason="NTFS allocates unsparse files")
@pytest.mark.parametrize(
    ("arguments", "source", "key"),
    [
        pytest.param(
            ("huge.bin", f"s3://{BUCKET}/huge.bin"),
            "huge.bin",
            "huge.bin",
            id="single",
        ),
        pytest.param(
            ("src", f"s3://{BUCKET}/prefix/", "--recursive"),
            "src/huge.bin",
            "prefix/huge.bin",
            id="recursive",
        ),
    ],
)
async def test_cp_dryrun_upload_past_the_size_limit_warns_and_is_reported(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    source: str,
    key: str,
) -> None:
    # The size warning does not skip the file; it only counts for the
    # status.
    path = tmp_path / "work" / source
    path.parent.mkdir(parents=True)
    try:
        with path.open("wb") as file:
            file.truncate(MAX_UPLOAD_SIZE + 1)
    except OSError as error:
        # ext4 caps a file at 16 TiB.
        pytest.skip(f"the filesystem holds no sparse 48.8 TiB file: {error}")
    try:
        run = await run_cp(
            aws_cli,
            tmp_path,
            ["s3", "cp", *arguments, "--no-progress", "--dryrun"],
        )
    finally:
        path.unlink()
    assert run.returncode == 2, run.describe()
    assert run.stdout == dry_upload(source, key)
    assert run.stderr == (
        f"warning: File {local(source)} exceeds s3 upload limit of 48.8 TiB.\n"
    )
    assert run.store.operations() == []
